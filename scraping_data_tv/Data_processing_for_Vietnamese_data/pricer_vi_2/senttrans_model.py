"""SentenceTransformer (frozen) + DNN regression head — Vietnamese price prediction.

Encoder: intfloat/multilingual-e5-small (512-token limit, 384-dim).
Architecture: frozen encoder → 384-dim dense embedding → PriceDNN (6 ResidualBlocks).
Target: log1p(price) → z-normalize → nn.L1Loss.

Reuses PriceDNN from deep_neural_network_sparse.py.
Pre-compute embeddings once then train lightweight DNN head only.
"""

import pickle
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import CosineAnnealingLR
from sentence_transformers import SentenceTransformer

from pricer_vi_2.deep_neural_network_sparse import PriceDNN


ENCODER_NAME = "intfloat/multilingual-e5-small"


class SentTransRunner:
    """Pre-compute frozen multilingual embeddings then train lightweight DNN head.

    Uses val[:1000] during training for fast epoch feedback (mirrors English pattern).
    val_predictions() / test_predictions() use full stored embeddings for stacking.
    history keys: train_loss, val_loss, val_mae, lr — compatible with evaluator.plot_training_history.
    """

    def __init__(self, train_items, val_items):
        self.train_items = train_items
        self.val_items = val_items
        self.encoder = None
        self.model = None
        self.device = None
        self.y_mean = None
        self.y_std = None
        self.history = None
        self.X_train = None
        self.X_val = None

        np.random.seed(42)
        torch.manual_seed(42)

    def encode_and_cache(self, cache_path=None, encode_batch_size=256):
        """Pre-compute embeddings for train + full val. Load from cache if exists."""
        print(f"Loading encoder: {ENCODER_NAME}")
        self.encoder = SentenceTransformer(ENCODER_NAME)

        if cache_path and cache_path.exists():
            print(f"Loading embeddings from cache: {cache_path}")
            with open(cache_path, "rb") as f:
                cached = pickle.load(f)
            self.X_train = cached["train"]
            self.X_val = cached["val"]
        else:
            print(f"Encoding train embeddings (269K) — ~10 min on GPU...")
            train_texts = [item.summary for item in self.train_items]
            self.X_train = torch.FloatTensor(
                self.encoder.encode(train_texts, show_progress_bar=True, batch_size=encode_batch_size)
            )
            print("Encoding val embeddings (3926)...")
            val_texts = [item.summary for item in self.val_items]
            self.X_val = torch.FloatTensor(
                self.encoder.encode(val_texts, show_progress_bar=True, batch_size=encode_batch_size)
            )
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, "wb") as f:
                    pickle.dump({"train": self.X_train, "val": self.X_val}, f)
                print(f"Embeddings cached to {cache_path}")

        print(f"Train: {self.X_train.shape} | Val: {self.X_val.shape}")

    def setup(self, batch_size=256, num_blocks=6):
        y_train = torch.FloatTensor([item.price for item in self.train_items]).unsqueeze(1)
        y_val_1k = torch.FloatTensor([item.price for item in self.val_items[:1000]]).unsqueeze(1)

        y_train_log = torch.log(y_train + 1)
        self.y_mean = y_train_log.mean()
        self.y_std = y_train_log.std()
        y_train_norm = (y_train_log - self.y_mean) / self.y_std

        self.y_val_1k = y_val_1k
        self.y_val_1k_norm = (torch.log(y_val_1k + 1) - self.y_mean) / self.y_std

        dataset = TensorDataset(self.X_train, y_train_norm)
        self.train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

        input_size = self.X_train.shape[1]  # 384
        self.model = PriceDNN(input_size, num_blocks=num_blocks)
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"SentTrans DNN head: {total_params:,} trainable params | embedding_dim={input_size}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using {self.device}")
        self.model.to(self.device)

    def train(self, epochs=15, patience=3):
        optimizer = optim.AdamW(self.model.parameters(), lr=1e-3, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=0)
        loss_fn = nn.L1Loss()
        self.history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}

        best_val_mae, patience_counter, best_state = float("inf"), 0, None
        X_val_dev = self.X_val[:1000].to(self.device)
        y_val_norm_dev = self.y_val_1k_norm.to(self.device)
        y_val_dev = self.y_val_1k.to(self.device)

        for epoch in range(1, epochs + 1):
            self.model.train()
            train_losses = []
            for batch_X, batch_y in self.train_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                out = self.model(batch_X)
                loss = loss_fn(out, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                train_losses.append(loss.item())
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
        """Inference on full val set (3926) using cached embeddings. Returns list[float]."""
        self.model.eval()
        preds = []
        with torch.no_grad():
            for i in range(0, len(self.X_val), 256):
                batch = self.X_val[i:i + 256].to(self.device)
                pred_orig = torch.exp(self.model(batch) * self.y_std + self.y_mean) - 1
                preds.extend(pred_orig.cpu().squeeze().tolist())
        return preds

    def test_predictions(self, test_items, encode_batch_size=256):
        """Encode test set and run DNN head. Returns list[float]."""
        self.model.eval()
        test_texts = [item.summary for item in test_items]
        X_test = torch.FloatTensor(
            self.encoder.encode(test_texts, show_progress_bar=True, batch_size=encode_batch_size)
        )
        preds = []
        with torch.no_grad():
            for i in range(0, len(X_test), 256):
                batch = X_test[i:i + 256].to(self.device)
                pred_orig = torch.exp(self.model(batch) * self.y_std + self.y_mean) - 1
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
            emb = torch.FloatTensor(self.encoder.encode([item.summary])).to(self.device)
            pred_norm = self.model(emb)[0]
            return max(5.0, (torch.exp(pred_norm * self.y_std + self.y_mean) - 1).item())
