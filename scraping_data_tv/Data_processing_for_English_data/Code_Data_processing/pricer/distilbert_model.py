"""Model 2: Fine-tuned DistilBERT end-to-end for price prediction.

Tokenizes item.summary with DistilBERT tokenizer (max_length=128),
fine-tunes the full encoder with discriminative learning rates,
and trains a lightweight regression head on [CLS] embeddings.
Uses mixed precision (fp16) for speed and memory efficiency.
"""

import numpy as np
from tqdm.notebook import tqdm
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torch.amp import autocast, GradScaler
from transformers import DistilBertModel, DistilBertTokenizer, get_linear_schedule_with_warmup


MAX_LENGTH = 128


class PriceDataset(Dataset):
    """Tokenized dataset for DistilBERT price prediction."""

    def __init__(self, items, tokenizer, y_mean, y_std):
        self.items = items
        self.tokenizer = tokenizer
        self.y_mean = y_mean
        self.y_std = y_std

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        item = self.items[idx]
        encoding = self.tokenizer(
            item.summary,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        # Log-normalize price
        price = torch.log(torch.tensor(item.price, dtype=torch.float32) + 1)
        price_norm = (price - self.y_mean) / self.y_std

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "price": price_norm,
        }


class DistilBERTRegressor(nn.Module):
    """DistilBERT encoder + regression head for price prediction."""

    def __init__(self, dropout_prob=0.1):
        super().__init__()
        self.encoder = DistilBertModel.from_pretrained("distilbert-base-uncased")
        hidden_size = self.encoder.config.hidden_size  # 768
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Linear(hidden_size, 256),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(256, 1),
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls_embedding = outputs.last_hidden_state[:, 0, :]  # [CLS] token
        return self.head(cls_embedding)


class DistilBERTRunner:
    """Training and inference runner for fine-tuned DistilBERT."""

    def __init__(self, train, val):
        self.train_data = train
        self.val_data = val
        self.tokenizer = None
        self.model = None
        self.device = None
        self.optimizer = None
        self.scheduler = None
        self.scaler = None
        self.y_mean = None
        self.y_std = None
        self.history = None

        np.random.seed(42)
        torch.manual_seed(42)
        torch.cuda.manual_seed(42)

    def setup(self, batch_size=32):
        """Load DistilBERT, create dataloaders, configure optimizer."""
        self.batch_size = batch_size

        print("Loading DistilBERT tokenizer...")
        self.tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")

        # Compute log-normalize stats from train
        prices = np.array([float(item.price) for item in self.train_data])
        y_log = np.log(prices + 1)
        self.y_mean = torch.tensor(y_log.mean(), dtype=torch.float32)
        self.y_std = torch.tensor(y_log.std(), dtype=torch.float32)

        val_prices = np.array([float(item.price) for item in self.val_data])
        self.y_val = torch.FloatTensor(val_prices).unsqueeze(1)

        # Datasets
        train_dataset = PriceDataset(self.train_data, self.tokenizer, self.y_mean, self.y_std)
        val_dataset = PriceDataset(self.val_data, self.tokenizer, self.y_mean, self.y_std)
        self.train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
        self.val_loader = DataLoader(val_dataset, batch_size=batch_size * 2, shuffle=False, num_workers=4, pin_memory=True)

        # Model
        print("Loading DistilBERT model...")
        self.model = DistilBERTRegressor()
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        encoder_params = sum(p.numel() for p in self.model.encoder.parameters() if p.requires_grad)
        head_params = sum(p.numel() for p in self.model.head.parameters() if p.requires_grad)
        print(f"DistilBERT Regressor: {total_params:,} params (encoder: {encoder_params:,}, head: {head_params:,})")

        # Device
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        print(f"Using {self.device}")

        self.model.to(self.device)
        self.loss_function = nn.L1Loss()

        # Discriminative learning rates
        self.optimizer = optim.AdamW(
            [
                {"params": self.model.encoder.parameters(), "lr": 2e-5},
                {"params": self.model.head.parameters(), "lr": 1e-4},
            ],
            weight_decay=0.01,
        )

        # Mixed precision scaler
        self.scaler = GradScaler(device="cuda") if self.device.type == "cuda" else None

    def train(self, epochs=5, patience=2, warmup_steps=1000):
        """Train with early stopping, mixed precision, gradient clipping."""
        total_steps = len(self.train_loader) * epochs
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
        )

        self.history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}
        best_val_mae = float("inf")
        best_state = None
        patience_counter = 0

        for epoch in range(1, epochs + 1):
            self.model.train()
            train_losses = []

            for batch in tqdm(self.train_loader, desc=f"Epoch {epoch}/{epochs}"):
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                targets = batch["price"].unsqueeze(1).to(self.device)

                self.optimizer.zero_grad()

                if self.scaler:
                    with autocast("cuda"):
                        outputs = self.model(input_ids, attention_mask)
                        loss = self.loss_function(outputs, targets)
                    self.scaler.scale(loss).backward()
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    outputs = self.model(input_ids, attention_mask)
                    loss = self.loss_function(outputs, targets)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.optimizer.step()

                self.scheduler.step()
                train_losses.append(loss.item())

            # Validation
            self.model.eval()
            val_preds = []
            val_losses = []
            with torch.no_grad():
                for batch in self.val_loader:
                    input_ids = batch["input_ids"].to(self.device)
                    attention_mask = batch["attention_mask"].to(self.device)
                    targets = batch["price"].unsqueeze(1).to(self.device)

                    outputs = self.model(input_ids, attention_mask)
                    val_loss = self.loss_function(outputs, targets)
                    val_losses.append(val_loss.item())

                    # De-normalize to original price scale
                    preds_orig = torch.exp(outputs * self.y_std + self.y_mean) - 1
                    val_preds.append(preds_orig.cpu())

            val_preds = torch.cat(val_preds)
            mae = torch.abs(val_preds - self.y_val).mean().item()
            avg_train_loss = np.mean(train_losses)
            avg_val_loss = np.mean(val_losses)
            current_lr = self.scheduler.get_last_lr()[0]

            self.history["train_loss"].append(avg_train_loss)
            self.history["val_loss"].append(avg_val_loss)
            self.history["val_mae"].append(mae)
            self.history["lr"].append(current_lr)

            print(f"Epoch [{epoch}/{epochs}]")
            print(f"  Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
            print(f"  Val MAE: ${mae:.2f}, LR: {current_lr:.8f}")

            # Early stopping
            if mae < best_val_mae:
                best_val_mae = mae
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                patience_counter = 0
                print(f"  ** New best Val MAE: ${best_val_mae:.2f}")
            else:
                patience_counter += 1
                print(f"  No improvement ({patience_counter}/{patience})")
                if patience_counter >= patience:
                    print(f"Early stopping at epoch {epoch}. Best Val MAE: ${best_val_mae:.2f}")
                    self.model.load_state_dict(best_state)
                    self.model.to(self.device)
                    break

        return self.history

    def save(self, path):
        """Save model weights + normalization stats."""
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "y_mean": self.y_mean,
                "y_std": self.y_std,
            },
            path,
        )

    def load(self, path):
        """Load model weights + normalization stats."""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.y_mean = checkpoint["y_mean"]
        self.y_std = checkpoint["y_std"]
        self.model.to(self.device)

    def inference(self, item):
        """Predict price for a single item."""
        self.model.eval()
        with torch.no_grad():
            encoding = self.tokenizer(
                item.summary,
                max_length=MAX_LENGTH,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )
            input_ids = encoding["input_ids"].to(self.device)
            attention_mask = encoding["attention_mask"].to(self.device)
            pred = self.model(input_ids, attention_mask)[0]
            result = torch.exp(pred * self.y_std + self.y_mean) - 1
        return max(0, result.item())
