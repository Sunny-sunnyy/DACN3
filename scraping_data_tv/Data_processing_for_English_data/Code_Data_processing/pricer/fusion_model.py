"""Model 4: Feature Fusion — HashingVectorizer(5000) + SentTrans(384) concat.

Combines two complementary representations:
- HashingVec: lexical/keyword signal (presence of "Samsung", "wireless", "4K")
- SentTrans:  semantic signal (dense 384-dim, frozen all-MiniLM-L6-v2)

Each modality is projected to 512-dim separately (with LayerNorm to handle
scale difference between sparse binary 5000-dim and dense float 384-dim),
then concatenated to 1024-dim and passed through ResidualBlocks.

SentTrans encoder stays frozen — only the fusion DNN is trained.
"""

import numpy as np
from tqdm.notebook import tqdm
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import CosineAnnealingLR
from sklearn.feature_extraction.text import HashingVectorizer
from sentence_transformers import SentenceTransformer


HASH_DIM = 5000
SEM_DIM = 384
PROJ_DIM = 512  # Each modality projected to this size before concat
FUSED_DIM = PROJ_DIM * 2  # 1024


class ResidualBlock(nn.Module):
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


class FusionDNN(nn.Module):
    """Dual-tower fusion: HashingVec(5000) + SentTrans(384) → price."""

    def __init__(self, num_blocks=4, dropout_prob=0.2):
        super().__init__()
        # Project each modality to PROJ_DIM separately
        self.hash_proj = nn.Sequential(
            nn.LayerNorm(HASH_DIM),
            nn.Linear(HASH_DIM, PROJ_DIM),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        self.sem_proj = nn.Sequential(
            nn.LayerNorm(SEM_DIM),
            nn.Linear(SEM_DIM, PROJ_DIM),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        # Fusion: concat → ResidualBlocks
        self.fusion_input = nn.Sequential(
            nn.Linear(FUSED_DIM, FUSED_DIM),
            nn.LayerNorm(FUSED_DIM),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        self.residual_blocks = nn.ModuleList(
            [ResidualBlock(FUSED_DIM, dropout_prob) for _ in range(num_blocks)]
        )
        self.output_layer = nn.Linear(FUSED_DIM, 1)

    def forward(self, hash_x, sem_x):
        h = self.hash_proj(hash_x)
        s = self.sem_proj(sem_x)
        fused = torch.cat([h, s], dim=1)
        fused = self.fusion_input(fused)
        for block in self.residual_blocks:
            fused = block(fused)
        return self.output_layer(fused)


class FusionRunner:
    """Training and inference runner for Feature Fusion model."""

    def __init__(self, train, val):
        self.train_data = train
        self.val_data = val
        self.vectorizer = None
        self.encoder = None
        self.model = None
        self.device = None
        self.y_mean = None
        self.y_std = None
        self.history = None

        np.random.seed(42)
        torch.manual_seed(42)
        torch.cuda.manual_seed(42)

    def _encode_texts(self, items):
        texts = [item.summary for item in items]
        embeddings = self.encoder.encode(texts, show_progress_bar=True, batch_size=512)
        return torch.FloatTensor(embeddings)

    def setup(self, batch_size=256):
        self.batch_size = batch_size

        print("Setting up HashingVectorizer...")
        self.vectorizer = HashingVectorizer(n_features=HASH_DIM, stop_words="english", binary=True)
        train_docs = [item.summary for item in self.train_data]
        X_hash_train = torch.FloatTensor(self.vectorizer.fit_transform(train_docs).toarray())
        val_docs = [item.summary for item in self.val_data]
        X_hash_val = torch.FloatTensor(self.vectorizer.transform(val_docs).toarray())

        print("Loading SentenceTransformer encoder (frozen)...")
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        print("Pre-computing train SentTrans embeddings...")
        X_sem_train = self._encode_texts(self.train_data)
        print("Pre-computing val SentTrans embeddings...")
        X_sem_val = self._encode_texts(self.val_data)

        y_train_np = np.array([float(item.price) for item in self.train_data])
        y_val_np = np.array([float(item.price) for item in self.val_data])
        self.y_train = torch.FloatTensor(y_train_np).unsqueeze(1)
        self.y_val = torch.FloatTensor(y_val_np).unsqueeze(1)

        # Log-normalize targets
        y_train_log = torch.log(self.y_train + 1)
        y_val_log = torch.log(self.y_val + 1)
        self.y_mean = y_train_log.mean()
        self.y_std = y_train_log.std()
        y_train_norm = (y_train_log - self.y_mean) / self.y_std
        y_val_norm = (y_val_log - self.y_mean) / self.y_std

        self.X_hash_val = X_hash_val
        self.X_sem_val = X_sem_val
        self.y_val_norm = y_val_norm

        train_dataset = TensorDataset(X_hash_train, X_sem_train, y_train_norm)
        self.train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        print(f"Using {self.device}")

        self.model = FusionDNN()
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"Fusion DNN: {total_params:,} trainable parameters")
        self.model.to(self.device)
        self.loss_function = nn.L1Loss()
        self.optimizer = optim.AdamW(self.model.parameters(), lr=1e-3, weight_decay=0.01)
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=15, eta_min=0)

    def train(self, epochs=15, patience=3):
        self.history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}
        best_val_mae = float("inf")
        best_state = None
        patience_counter = 0

        X_hash_val = self.X_hash_val.to(self.device)
        X_sem_val = self.X_sem_val.to(self.device)
        y_val_norm = self.y_val_norm.to(self.device)

        for epoch in range(1, epochs + 1):
            self.model.train()
            train_losses = []

            for batch_hash, batch_sem, batch_y in tqdm(self.train_loader, desc=f"Epoch {epoch}/{epochs}"):
                batch_hash = batch_hash.to(self.device)
                batch_sem = batch_sem.to(self.device)
                batch_y = batch_y.to(self.device)

                self.optimizer.zero_grad()
                outputs = self.model(batch_hash, batch_sem)
                loss = self.loss_function(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()
                train_losses.append(loss.item())

            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_hash_val, X_sem_val)
                val_loss = self.loss_function(val_outputs, y_val_norm)
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
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "y_mean": self.y_mean,
                "y_std": self.y_std,
            },
            path,
        )

    def load(self, path):
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.y_mean = checkpoint["y_mean"]
        self.y_std = checkpoint["y_std"]
        self.model.to(self.device)

    def inference(self, item):
        """Predict price for a single item."""
        self.model.eval()
        with torch.no_grad():
            hash_vec = torch.FloatTensor(
                self.vectorizer.transform([item.summary]).toarray()
            ).to(self.device)
            sem_vec = torch.FloatTensor(
                self.encoder.encode([item.summary])
            ).to(self.device)
            pred = self.model(hash_vec, sem_vec)[0]
            result = torch.exp(pred * self.y_std + self.y_mean) - 1
        return max(0, result.item())
