"""DNN for sparse input (TF-IDF / HashingVec) — Vietnamese price prediction.

Input: scipy sparse matrix from TF-IDF or HashingVec vectorizer.
Architecture: ResidualBlock × num_blocks, hidden_size=4096 (mirrors English redemption DNN).
Target: log1p(price) → z-normalize → nn.L1Loss.

_sparse: input matrix has 100K+ columns but most values are 0 (sparse matrix).
         Cannot .toarray() the full train set at once — SparseDataset converts per-row.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torch.optim.lr_scheduler import CosineAnnealingLR
from scipy.sparse import spmatrix
from tqdm import tqdm


class ResidualBlock(nn.Module):
    def __init__(self, hidden_size, dropout_prob=0.2):
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


class PriceDNN(nn.Module):
    def __init__(self, input_size, num_blocks=8, hidden_size=4096, dropout_prob=0.2):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        self.blocks = nn.ModuleList(
            [ResidualBlock(hidden_size, dropout_prob) for _ in range(num_blocks)]
        )
        self.output_layer = nn.Linear(hidden_size, 1)

    def forward(self, x):
        x = self.input_layer(x)
        for block in self.blocks:
            x = block(x)
        return self.output_layer(x)


class SparseDataset(Dataset):
    """Wraps scipy sparse matrix + label tensor. Converts one row at a time in __getitem__."""

    def __init__(self, X_sparse: spmatrix, y_norm: torch.Tensor):
        self.X = X_sparse
        self.y = y_norm

    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, idx):
        x = torch.FloatTensor(self.X[idx].toarray().squeeze(0))
        return x, self.y[idx]


class SparseDNNRunner:
    """Train PriceDNN on sparse vectorizer features (TF-IDF or HashingVec).

    Uses val[:1000] during training for fast epoch feedback (mirrors English pattern).
    val_predictions() runs on full stored val set (3926) for stacking.
    history keys: train_loss, val_loss, val_mae, lr — compatible with evaluator.plot_training_history.
    """

    def __init__(self, train_items, val_items):
        self.train_items = train_items
        self.val_items = val_items
        self.model = None
        self.vectorizer = None
        self.device = None
        self.y_mean = None
        self.y_std = None
        self.history = None

        np.random.seed(42)
        torch.manual_seed(42)

    def setup(self, vectorizer, batch_size=64, num_blocks=8, hidden_size=4096):
        self.vectorizer = vectorizer
        train_docs = [item.summary for item in self.train_items]
        val_docs_1k = [item.summary for item in self.val_items[:1000]]

        print("Fitting vectorizer on 269K train docs...")
        X_train = self.vectorizer.fit_transform(train_docs)
        X_val_1k = self.vectorizer.transform(val_docs_1k)
        print(f"Feature matrix: {X_train.shape}")

        y_train = torch.FloatTensor([item.price for item in self.train_items]).unsqueeze(1)
        y_val_1k = torch.FloatTensor([item.price for item in self.val_items[:1000]]).unsqueeze(1)

        y_train_log = torch.log(y_train + 1)
        self.y_mean = y_train_log.mean()
        self.y_std = y_train_log.std()
        y_train_norm = (y_train_log - self.y_mean) / self.y_std

        # Val 1K kept dense (1000 × 100K = ~400MB float32 — OK for 24GB GPU)
        self.X_val_1k = torch.FloatTensor(X_val_1k.toarray())
        self.y_val_1k = y_val_1k
        self.y_val_1k_norm = (torch.log(y_val_1k + 1) - self.y_mean) / self.y_std

        dataset = SparseDataset(X_train, y_train_norm)
        self.train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)

        input_size = X_train.shape[1]
        self.model = PriceDNN(input_size, num_blocks=num_blocks, hidden_size=hidden_size)
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"PriceDNN: {total_params:,} trainable params | input_size={input_size}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using {self.device}")
        self.model.to(self.device)

    def train(self, epochs=10, patience=3):
        optimizer = optim.AdamW(self.model.parameters(), lr=1e-3, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=0)
        loss_fn = nn.L1Loss()
        self.history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}

        best_val_mae, patience_counter, best_state = float("inf"), 0, None
        X_val_dev = self.X_val_1k.to(self.device)
        y_val_norm_dev = self.y_val_1k_norm.to(self.device)
        y_val_dev = self.y_val_1k.to(self.device)

        for epoch in range(1, epochs + 1):
            self.model.train()
            train_losses = []
            pbar = tqdm(self.train_loader, desc=f"Epoch {epoch}/{epochs}", leave=False)
            for batch_X, batch_y in pbar:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                out = self.model(batch_X)
                loss = loss_fn(out, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                train_losses.append(loss.item())
                pbar.set_postfix(loss=f"{loss.item():.4f}")
            scheduler.step()

            self.model.eval()
            with torch.no_grad():
                val_out_norm = self.model(X_val_dev)
                val_loss = loss_fn(val_out_norm, y_val_norm_dev).item()
                val_pred_orig = torch.exp(val_out_norm * self.y_std + self.y_mean) - 1
                val_mae = torch.abs(val_pred_orig - y_val_dev).mean().item()

            avg_loss = float(np.mean(train_losses))
            lr = scheduler.get_last_lr()[0]
            self.history["train_loss"].append(avg_loss)
            self.history["val_loss"].append(val_loss)
            self.history["val_mae"].append(val_mae)
            self.history["lr"].append(lr)
            print(
                f"Epoch {epoch}/{epochs} | "
                f"train_loss={avg_loss:.4f} | val_loss={val_loss:.4f} | "
                f"val_mae={val_mae:.2f}k | lr={lr:.6f}"
            )

            if val_mae < best_val_mae:
                best_val_mae = val_mae
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                patience_counter = 0
                print(f"  ** best val_mae={best_val_mae:.2f}k")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"  Early stopping. Best val_mae={best_val_mae:.2f}k")
                    self.model.load_state_dict(best_state)
                    self.model.to(self.device)
                    break

        return self.history

    def val_predictions(self):
        """Inference on full val set (3926 items) for stacking. Returns list[float]."""
        self.model.eval()
        val_docs = [item.summary for item in self.val_items]
        preds = []
        with torch.no_grad():
            for i in tqdm(range(0, len(val_docs), 256), desc="val_predictions", leave=False):
                x = torch.FloatTensor(
                    self.vectorizer.transform(val_docs[i:i + 256]).toarray()
                ).to(self.device)
                pred_orig = torch.exp(self.model(x) * self.y_std + self.y_mean) - 1
                preds.extend(pred_orig.cpu().squeeze().tolist())
        return preds

    def test_predictions(self, test_items):
        """Inference on test set for stacking. Returns list[float]."""
        self.model.eval()
        test_docs = [item.summary for item in test_items]
        preds = []
        with torch.no_grad():
            for i in tqdm(range(0, len(test_docs), 256), desc="test_predictions", leave=False):
                x = torch.FloatTensor(
                    self.vectorizer.transform(test_docs[i:i + 256]).toarray()
                ).to(self.device)
                pred_orig = torch.exp(self.model(x) * self.y_std + self.y_mean) - 1
                preds.extend(pred_orig.cpu().squeeze().tolist())
        return preds

    def save(self, path):
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "y_mean": self.y_mean,
            "y_std": self.y_std,
        }, path)

    def load(self, path):
        ckpt = torch.load(path, map_location=self.device)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.y_mean = ckpt["y_mean"]
        self.y_std = ckpt["y_std"]
        self.model.to(self.device)

    def inference(self, item):
        self.model.eval()
        with torch.no_grad():
            x = torch.FloatTensor(
                self.vectorizer.transform([item.summary]).toarray()
            ).to(self.device)
            pred_norm = self.model(x)[0]
            return max(5.0, (torch.exp(pred_norm * self.y_std + self.y_mean) - 1).item())
