"""Model 1: SentenceTransformer (frozen) + Regression DNN with ResidualBlocks.

Pre-computes dense 384-dim semantic embeddings, then trains a lightweight
regression head (1024-dim, 6 ResidualBlocks) to predict log-normalized price.
"""

import numpy as np
from tqdm.notebook import tqdm
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import CosineAnnealingLR
from sentence_transformers import SentenceTransformer


class ResidualBlock(nn.Module):
    """Two-layer residual block with LayerNorm, ReLU, and Dropout."""

    def __init__(self, hidden_size, dropout_prob):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(self.block(x) + x)


class SentTransDNN(nn.Module):
    """Regression head: projects 384-dim embeddings through ResidualBlocks to price."""

    def __init__(self, input_size=384, num_blocks=6, hidden_size=1024, dropout_prob=0.2):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        self.residual_blocks = nn.ModuleList(
            [ResidualBlock(hidden_size, dropout_prob) for _ in range(num_blocks)]
        )
        self.output_layer = nn.Linear(hidden_size, 1)

    def forward(self, x):
        x = self.input_layer(x)
        for block in self.residual_blocks:
            x = block(x)
        return self.output_layer(x)


class SentTransRunner:
    """Training and inference runner for SentenceTransformer + DNN."""

    def __init__(self, train, val):
        self.train_data = train
        self.val_data = val
        self.model = None
        self.encoder = None
        self.device = None
        self.loss_function = None
        self.optimizer = None
        self.scheduler = None
        self.y_mean = None
        self.y_std = None
        self.history = None

        np.random.seed(42)
        torch.manual_seed(42)
        torch.cuda.manual_seed(42)

    def _encode_texts(self, items, desc="Encoding"):
        """Encode item summaries to 384-dim dense embeddings using frozen SentenceTransformer."""
        texts = [item.summary for item in items]
        embeddings = self.encoder.encode(texts, show_progress_bar=True, batch_size=256)
        return torch.FloatTensor(embeddings)

    def setup(self):
        """Load encoder, pre-compute embeddings, create DNN head."""
        print("Loading SentenceTransformer encoder (frozen)...")
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")

        print("Pre-computing train embeddings...")
        self.X_train = self._encode_texts(self.train_data)
        y_train_np = np.array([float(item.price) for item in self.train_data])
        self.y_train = torch.FloatTensor(y_train_np).unsqueeze(1)

        print("Pre-computing val embeddings...")
        self.X_val = self._encode_texts(self.val_data)
        y_val_np = np.array([float(item.price) for item in self.val_data])
        self.y_val = torch.FloatTensor(y_val_np).unsqueeze(1)

        # Log-normalize targets
        y_train_log = torch.log(self.y_train + 1)
        y_val_log = torch.log(self.y_val + 1)
        self.y_mean = y_train_log.mean()
        self.y_std = y_train_log.std()
        self.y_train_norm = (y_train_log - self.y_mean) / self.y_std
        self.y_val_norm = (y_val_log - self.y_mean) / self.y_std

        input_size = self.X_train.shape[1]
        self.model = SentTransDNN(input_size=input_size)
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"SentTrans DNN created with {total_params:,} trainable parameters")

        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        print(f"Using {self.device}")

        self.model.to(self.device)
        self.loss_function = nn.L1Loss()
        self.optimizer = optim.AdamW(self.model.parameters(), lr=1e-3, weight_decay=0.01)
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=15, eta_min=0)

        self.train_dataset = TensorDataset(self.X_train, self.y_train_norm)
        self.train_loader = DataLoader(self.train_dataset, batch_size=256, shuffle=True)

    def train(self, epochs=15, patience=3):
        """Train with early stopping on validation MAE."""
        self.history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}
        best_val_mae = float("inf")
        best_state = None
        patience_counter = 0

        for epoch in range(1, epochs + 1):
            self.model.train()
            train_losses = []

            for batch_X, batch_y in tqdm(self.train_loader, desc=f"Epoch {epoch}/{epochs}"):
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)

                self.optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = self.loss_function(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()
                train_losses.append(loss.item())

            # Validation
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(self.X_val.to(self.device))
                val_loss = self.loss_function(val_outputs, self.y_val_norm.to(self.device))
                val_outputs_orig = torch.exp(val_outputs * self.y_std + self.y_mean) - 1
                mae = torch.abs(val_outputs_orig - self.y_val.to(self.device)).mean()

            avg_train_loss = np.mean(train_losses)
            current_lr = self.scheduler.get_last_lr()[0]

            self.history["train_loss"].append(avg_train_loss)
            self.history["val_loss"].append(val_loss.item())
            self.history["val_mae"].append(mae.item())
            self.history["lr"].append(current_lr)

            print(f"Epoch [{epoch}/{epochs}]")
            print(f"  Train Loss: {avg_train_loss:.4f}, Val Loss: {val_loss.item():.4f}")
            print(f"  Val MAE: ${mae.item():.2f}, LR: {current_lr:.6f}")

            # Early stopping
            if mae.item() < best_val_mae:
                best_val_mae = mae.item()
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

            self.scheduler.step()

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
            embedding = self.encoder.encode([item.summary])
            embedding = torch.FloatTensor(embedding).to(self.device)
            pred = self.model(embedding)[0]
            result = torch.exp(pred * self.y_std + self.y_mean) - 1
        return max(0, result.item())
