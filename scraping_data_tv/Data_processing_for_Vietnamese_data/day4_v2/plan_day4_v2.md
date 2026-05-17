# Plan Day 4 v2 — Deep Learning: Vietnamese Price Prediction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train 5 deep learning models trên Vietnamese product data (269K samples), stack thành ensemble đạt MAE < 65k VND, đánh giá bằng `pricer_vi_2/evaluator.py`.

**Architecture:** 2 DNN sparse-input models (TF-IDF + HashingVec) + 1 frozen-encoder SentenceTransformer + 2 BERT fine-tune models (XLM-RoBERTa + PhoBERT) — tất cả dùng log1p+z-normalize target, L1Loss, ResidualBlock backbone. Ridge stacking trên val predictions để tối ưu MAE.

**Tech Stack:** PyTorch, transformers (HuggingFace), sentence-transformers, underthesea, lightgbm, scikit-learn, datasets, uv

**Ngày tạo:** 2026-05-17 | **Branch:** feature/day5-qlora-qwen
**Dataset:** `SeanSunny/items_tv_v9` | **GPU:** RTX 3090 Ti 24GB (vast.ai)

---

## 0. Tổng quan

### 0.1. Tại sao Day 4 v2?

| Giới hạn Day 3 v2 | Day 4 v2 giải quyết |
|---|---|
| LGB + TF-IDF: MAE 92.6k — ML ceiling | Deep learning học semantic features |
| Bag-of-words: không hiểu ngữ nghĩa | BERT models hiểu context tiếng Việt |
| Single model | Ensemble 5 models → MAE thấp hơn |

### 0.2. Mục tiêu định lượng

| Model | MAE target (k VND) |
|---|---|
| DNN + TF-IDF char_wb | < 80k |
| DNN + HashingVec 5000 | < 85k |
| Multilingual SentTrans + DNN | < 75k |
| XLM-RoBERTa fine-tune | < 70k |
| PhoBERT-v2 fine-tune | < 68k |
| **Ensemble Ridge (P0)** | **< 65k** |
| Ensemble (stretch) | < 60k |

### 0.3. Quyết định kỹ thuật cốt lõi

| Quyết định | Giá trị | Lý do |
|---|---|---|
| Target transform | `log1p(price)` → z-normalize | Mirror English Day 4 — DNN cần normalized target |
| Loss function | `nn.L1Loss()` | Tối ưu trực tiếp MAE |
| De-normalize | `exp(pred * std + mean) - 1` | Về original scale trước khi tính MAE |
| Primary metric | MAE (k VND) | Align Day 3 v2, align English |
| Evaluate | `pricer_vi_2/evaluator.py` (200 test samples) | Consistent với toàn pipeline |
| Stacking metric | MAE trên val set | Optimize đúng metric |
| Price unit | `round(price_vnd / 1000)` — range 5–1000 | Align English pipeline |
| Log1p policy | **CÓ dùng cho DNN** (khác Day 3 v2 LGB) | Gradient ổn định hơn cho DNN |

---

## 1. Dữ liệu

### 1.1. Dataset `SeanSunny/items_tv_v9`

| Split | Rows | Dùng cho |
|---|---|---|
| train | 269,112 | Train tất cả models |
| validation | 3,926 | Early stopping + stacking weights |
| test | 3,872 (lấy 200) | Final eval qua evaluator.py |

### 1.2. Input format (item.summary — 5 dòng cố định)

```
Tieu de: Ao thun nam cotton thoang mat
Danh muc: Thoi Trang
Thuong hieu: UniStyle
Mo ta: Ao cotton 100%, thoang mat, thich hop mac thuong ngay.
Thong so: Chat lieu Cotton 100%, size S-XXL, nhieu mau sac.
```

### 1.3. Load data (dùng `pricer_vi_2/items.py`)

```python
from pricer_vi_2.items import Item
train, val, test = Item.from_hub("SeanSunny/items_tv_v9")
train_docs = [item.summary for item in train]
train_prices = [item.price for item in train]  # float, range 5-1000
```

---

## 2. Kỹ thuật dùng chung cho tất cả DNN models

### 2.1. Target transform (bắt buộc cho Models 1–3)

```python
import torch, numpy as np

y_train = torch.FloatTensor([item.price for item in train]).unsqueeze(1)
y_val   = torch.FloatTensor([item.price for item in val]).unsqueeze(1)

y_train_log = torch.log(y_train + 1)       # log1p
y_val_log   = torch.log(y_val + 1)

y_mean = y_train_log.mean()               # scalar — lưu lại cho de-normalize
y_std  = y_train_log.std()

y_train_norm = (y_train_log - y_mean) / y_std
y_val_norm   = (y_val_log   - y_mean) / y_std
```

De-normalize khi evaluate:
```python
pred_orig = torch.exp(pred_norm * y_std + y_mean) - 1
mae = torch.abs(pred_orig - y_val).mean()
```

### 2.2. ResidualBlock + DeepNeuralNetwork (dùng lại từ English)

```python
# pricer_vi_2/dnn_sparse.py — ResidualBlock giống English deep_neural_network.py
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
```

### 2.3. Training loop chuẩn (Models 1–3)

```python
optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.01)
scheduler = CosineAnnealingLR(optimizer, T_max=10, eta_min=0)
loss_fn   = nn.L1Loss()

best_val_mae, patience_counter, best_state = float("inf"), 0, None

for epoch in range(1, 11):
    model.train()
    for batch_X, batch_y in train_loader:
        optimizer.zero_grad()
        out = model(batch_X.to(device))
        loss = loss_fn(out, batch_y.to(device))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
    scheduler.step()

    model.eval()
    with torch.no_grad():
        val_pred_norm = model(X_val_tensor.to(device))
        val_pred_orig = torch.exp(val_pred_norm * y_std + y_mean) - 1
        val_mae = torch.abs(val_pred_orig - y_val.to(device)).mean().item()

    if val_mae < best_val_mae:
        best_val_mae = val_mae
        best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        patience_counter = 0
    else:
        patience_counter += 1
        if patience_counter >= 3:
            model.load_state_dict(best_state)
            break
```

### 2.4. Evaluation chuẩn (tất cả models)

```python
from pricer_vi_2.evaluator import evaluate

def make_predictor(model, vectorizer, y_mean, y_std, device):
    def predictor(item):
        model.eval()
        with torch.no_grad():
            vec = vectorizer.transform([item.summary])
            x = torch.FloatTensor(vec.toarray()).to(device)
            pred_norm = model(x)[0]
            return max(0, (torch.exp(pred_norm * y_std + y_mean) - 1).item())
    return predictor

evaluate(make_predictor(model, vec, y_mean, y_std, device), test)
```

---

## 3. Folder Structure

```
Data_processing_for_Vietnamese_data/
├── day4_v2/
│   ├── plan_day4_v2.md                          # File này — CANONICAL
│   ├── day4_v2_01_dnn_tfidf.ipynb               # Task 2
│   ├── day4_v2_02_dnn_hashvec.ipynb             # Task 3
│   ├── day4_v2_03_senttrans.ipynb               # Task 4
│   ├── day4_v2_04_xlmr.ipynb                    # Task 5
│   ├── day4_v2_05_phobert.ipynb                 # Task 6
│   ├── day4_v2_06_ensemble.ipynb                # Task 7
│   ├── weights/
│   │   ├── dnn_tfidf.pth
│   │   ├── dnn_hashvec.pth
│   │   ├── senttrans_dnn.pth
│   │   ├── xlmr/                                # HF save_pretrained format
│   │   └── phobert/
│   ├── cache/
│   │   ├── phobert_seg_cache.pkl                # Word-seg 269K+3926 docs
│   │   └── senttrans_embeddings_train.pkl       # 269K × 384 float32
│   ├── val_predictions/
│   │   ├── dnn_tfidf_val.json                   # 3926 val predictions
│   │   ├── dnn_hashvec_val.json
│   │   ├── senttrans_val.json
│   │   ├── xlmr_val.json
│   │   └── phobert_val.json
│   ├── day4_v2_results.json                     # Kết quả tất cả models
│   └── day4_v2_summary.md
│
└── pricer_vi_2/
    ├── items.py                                 # Existing — KHÔNG SỬA
    ├── evaluator.py                             # Existing — KHÔNG SỬA
    ├── __init__.py                              # Existing
    ├── dnn_sparse.py                            # Task 1: ResidualBlock + PriceDNN + SparseDNNRunner
    ├── senttrans_model.py                       # Task 1: SentTransRunner
    ├── xlmr_model.py                            # Task 1: XLMRRunner
    └── phobert_model.py                         # Task 1: PhoBERTRunner
```

---

## Task 1: Tạo model files trong `pricer_vi_2/`

**Files:**
- Create: `pricer_vi_2/dnn_sparse.py`
- Create: `pricer_vi_2/senttrans_model.py`
- Create: `pricer_vi_2/xlmr_model.py`
- Create: `pricer_vi_2/phobert_model.py`

- [ ] **Step 1.1: Tạo `pricer_vi_2/dnn_sparse.py`**

```python
"""DNN runner for sparse input (TF-IDF / HashingVec) — Vietnamese price prediction."""
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torch.optim.lr_scheduler import CosineAnnealingLR
from scipy.sparse import spmatrix


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
    """Wraps a scipy sparse matrix + dense label tensor. Converts per-row on __getitem__."""

    def __init__(self, X_sparse: spmatrix, y_norm: torch.Tensor):
        self.X = X_sparse
        self.y = y_norm

    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, idx):
        x = torch.FloatTensor(self.X[idx].toarray().squeeze(0))
        return x, self.y[idx]


class SparseDNNRunner:
    """Train PriceDNN on sparse vectorizer features (TF-IDF or HashingVec)."""

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

    def setup(self, vectorizer, batch_size=256, num_blocks=8, hidden_size=4096):
        self.vectorizer = vectorizer
        train_docs = [item.summary for item in self.train_items]
        val_docs   = [item.summary for item in self.val_items]

        X_train = self.vectorizer.fit_transform(train_docs)
        X_val   = self.vectorizer.transform(val_docs)

        y_train = torch.FloatTensor([item.price for item in self.train_items]).unsqueeze(1)
        y_val   = torch.FloatTensor([item.price for item in self.val_items]).unsqueeze(1)

        y_train_log = torch.log(y_train + 1)
        self.y_mean = y_train_log.mean()
        self.y_std  = y_train_log.std()
        y_train_norm = (y_train_log - self.y_mean) / self.y_std

        # Val kept dense (small enough)
        self.X_val_dense = torch.FloatTensor(X_val.toarray())
        self.y_val = y_val
        self.y_val_norm = (torch.log(y_val + 1) - self.y_mean) / self.y_std

        dataset = SparseDataset(X_train, y_train_norm)
        self.train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

        input_size = X_train.shape[1]
        self.model = PriceDNN(input_size, num_blocks=num_blocks, hidden_size=hidden_size)
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"PriceDNN: {total_params:,} params | input_size={input_size}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using {self.device}")
        self.model.to(self.device)

    def train(self, epochs=10, patience=3):
        optimizer = optim.AdamW(self.model.parameters(), lr=1e-3, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=0)
        loss_fn = nn.L1Loss()
        self.history = {"train_loss": [], "val_mae": [], "lr": []}

        best_val_mae, patience_counter, best_state = float("inf"), 0, None

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
                val_pred_norm = self.model(self.X_val_dense.to(self.device))
                val_pred_orig = torch.exp(val_pred_norm * self.y_std + self.y_mean) - 1
                val_mae = torch.abs(val_pred_orig - self.y_val.to(self.device)).mean().item()

            avg_loss = float(np.mean(train_losses))
            lr = scheduler.get_last_lr()[0]
            self.history["train_loss"].append(avg_loss)
            self.history["val_mae"].append(val_mae)
            self.history["lr"].append(lr)
            print(f"Epoch {epoch}/{epochs} | train_loss={avg_loss:.4f} | val_mae={val_mae:.2f}k | lr={lr:.6f}")

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
        """Return raw val predictions (original scale) for stacking."""
        self.model.eval()
        with torch.no_grad():
            pred_norm = self.model(self.X_val_dense.to(self.device))
            return (torch.exp(pred_norm * self.y_std + self.y_mean) - 1).cpu().squeeze().tolist()

    def save(self, path):
        torch.save({"model_state_dict": self.model.state_dict(),
                    "y_mean": self.y_mean, "y_std": self.y_std}, path)

    def load(self, path):
        ckpt = torch.load(path, map_location=self.device)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.y_mean = ckpt["y_mean"]
        self.y_std  = ckpt["y_std"]
        self.model.to(self.device)

    def inference(self, item):
        self.model.eval()
        with torch.no_grad():
            vec = self.vectorizer.transform([item.summary])
            x = torch.FloatTensor(vec.toarray()).to(self.device)
            pred_norm = self.model(x)[0]
            return max(0.0, (torch.exp(pred_norm * self.y_std + self.y_mean) - 1).item())
```

- [ ] **Step 1.2: Tạo `pricer_vi_2/senttrans_model.py`**

```python
"""SentenceTransformer (frozen) + DNN regression head — Vietnamese price prediction."""
import pickle
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torch.optim.lr_scheduler import CosineAnnealingLR
from sentence_transformers import SentenceTransformer
from pricer_vi_2.dnn_sparse import PriceDNN


class SentTransRunner:
    """Pre-compute frozen embeddings then train lightweight DNN head."""

    def __init__(self, train_items, val_items):
        self.train_items = train_items
        self.val_items = val_items
        self.encoder = None
        self.model = None
        self.device = None
        self.y_mean = None
        self.y_std = None
        self.history = None
        np.random.seed(42)
        torch.manual_seed(42)

    def encode_and_cache(self, cache_path=None):
        """Pre-compute embeddings. Load from cache if exists."""
        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        self.encoder = SentenceTransformer(model_name)

        if cache_path and cache_path.exists():
            print(f"Loading embeddings from cache: {cache_path}")
            with open(cache_path, "rb") as f:
                cached = pickle.load(f)
            self.X_train = cached["train"]
            self.X_val   = cached["val"]
        else:
            print("Encoding train embeddings...")
            train_texts = [item.summary for item in self.train_items]
            val_texts   = [item.summary for item in self.val_items]
            self.X_train = torch.FloatTensor(
                self.encoder.encode(train_texts, show_progress_bar=True, batch_size=256)
            )
            self.X_val = torch.FloatTensor(
                self.encoder.encode(val_texts, show_progress_bar=True, batch_size=256)
            )
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, "wb") as f:
                    pickle.dump({"train": self.X_train, "val": self.X_val}, f)
                print(f"Embeddings cached to {cache_path}")

    def setup(self, batch_size=256, num_blocks=6):
        y_train = torch.FloatTensor([item.price for item in self.train_items]).unsqueeze(1)
        y_val   = torch.FloatTensor([item.price for item in self.val_items]).unsqueeze(1)

        y_train_log = torch.log(y_train + 1)
        self.y_mean = y_train_log.mean()
        self.y_std  = y_train_log.std()
        y_train_norm = (y_train_log - self.y_mean) / self.y_std
        self.y_val = y_val
        self.y_val_norm = (torch.log(y_val + 1) - self.y_mean) / self.y_std

        dataset = TensorDataset(self.X_train, y_train_norm)
        self.train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

        input_size = self.X_train.shape[1]  # 384
        self.model = PriceDNN(input_size, num_blocks=num_blocks)
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"SentTrans DNN head: {total_params:,} params | embedding_dim={input_size}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using {self.device}")
        self.model.to(self.device)

    def train(self, epochs=15, patience=3):
        optimizer = optim.AdamW(self.model.parameters(), lr=1e-3, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=0)
        loss_fn = nn.L1Loss()
        self.history = {"train_loss": [], "val_mae": [], "lr": []}

        best_val_mae, patience_counter, best_state = float("inf"), 0, None

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
                val_pred_norm = self.model(self.X_val.to(self.device))
                val_pred_orig = torch.exp(val_pred_norm * self.y_std + self.y_mean) - 1
                val_mae = torch.abs(val_pred_orig - self.y_val.to(self.device)).mean().item()

            avg_loss = float(np.mean(train_losses))
            lr = scheduler.get_last_lr()[0]
            self.history["train_loss"].append(avg_loss)
            self.history["val_mae"].append(val_mae)
            self.history["lr"].append(lr)
            print(f"Epoch {epoch}/{epochs} | train_loss={avg_loss:.4f} | val_mae={val_mae:.2f}k | lr={lr:.6f}")

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
        self.model.eval()
        with torch.no_grad():
            pred_norm = self.model(self.X_val.to(self.device))
            return (torch.exp(pred_norm * self.y_std + self.y_mean) - 1).cpu().squeeze().tolist()

    def save(self, path):
        torch.save({"model_state_dict": self.model.state_dict(),
                    "y_mean": self.y_mean, "y_std": self.y_std}, path)

    def load(self, path):
        ckpt = torch.load(path, map_location=self.device)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.y_mean = ckpt["y_mean"]
        self.y_std  = ckpt["y_std"]
        self.model.to(self.device)

    def inference(self, item):
        self.model.eval()
        with torch.no_grad():
            emb = self.encoder.encode([item.summary])
            x = torch.FloatTensor(emb).to(self.device)
            pred_norm = self.model(x)[0]
            return max(0.0, (torch.exp(pred_norm * self.y_std + self.y_mean) - 1).item())
```

- [ ] **Step 1.3: Tạo `pricer_vi_2/xlmr_model.py`**

```python
"""XLM-RoBERTa fine-tuned end-to-end for Vietnamese price regression."""
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torch.amp import autocast, GradScaler
from transformers import XLMRobertaModel, AutoTokenizer, get_linear_schedule_with_warmup

MAX_LENGTH = 128


class ViPriceDataset(Dataset):
    def __init__(self, items, tokenizer, y_mean, y_std):
        self.items = items
        self.tokenizer = tokenizer
        self.y_mean = y_mean
        self.y_std = y_std

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        item = self.items[idx]
        enc = self.tokenizer(
            item.summary, max_length=MAX_LENGTH,
            padding="max_length", truncation=True, return_tensors="pt",
        )
        price_log  = torch.log(torch.tensor(item.price, dtype=torch.float32) + 1)
        price_norm = (price_log - self.y_mean) / self.y_std
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "price":          price_norm,
        }


class XLMRRegressor(nn.Module):
    def __init__(self, dropout_prob=0.1):
        super().__init__()
        self.encoder = XLMRobertaModel.from_pretrained("xlm-roberta-base")
        hidden = self.encoder.config.hidden_size  # 768
        self.head = nn.Sequential(
            nn.LayerNorm(hidden),
            nn.Linear(hidden, 256),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(256, 1),
        )

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        return self.head(cls)


class XLMRRunner:
    def __init__(self, train_items, val_items):
        self.train_items = train_items
        self.val_items = val_items
        self.model = None
        self.tokenizer = None
        self.device = None
        self.y_mean = None
        self.y_std = None
        self.history = None
        np.random.seed(42)
        torch.manual_seed(42)

    def setup(self, batch_size=32):
        self.tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-base")

        prices = np.array([item.price for item in self.train_items], dtype=np.float32)
        y_log = np.log(prices + 1)
        self.y_mean = torch.tensor(y_log.mean(), dtype=torch.float32)
        self.y_std  = torch.tensor(y_log.std(),  dtype=torch.float32)

        val_prices = np.array([item.price for item in self.val_items], dtype=np.float32)
        self.y_val = torch.FloatTensor(val_prices).unsqueeze(1)

        train_ds = ViPriceDataset(self.train_items, self.tokenizer, self.y_mean, self.y_std)
        val_ds   = ViPriceDataset(self.val_items,   self.tokenizer, self.y_mean, self.y_std)
        self.train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=4, pin_memory=True)
        self.val_loader   = DataLoader(val_ds,   batch_size=batch_size * 2, shuffle=False, num_workers=4, pin_memory=True)

        self.model = XLMRRegressor()
        enc_params  = sum(p.numel() for p in self.model.encoder.parameters())
        head_params = sum(p.numel() for p in self.model.head.parameters())
        print(f"XLMRRegressor: encoder={enc_params:,} head={head_params:,}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using {self.device}")
        self.model.to(self.device)

        self.optimizer = optim.AdamW([
            {"params": self.model.encoder.parameters(), "lr": 2e-5},
            {"params": self.model.head.parameters(),    "lr": 1e-4},
        ], weight_decay=0.01)
        self.loss_fn = nn.L1Loss()
        self.scaler  = GradScaler("cuda") if self.device.type == "cuda" else None

    def train(self, epochs=5, patience=2, warmup_steps=500):
        total_steps = len(self.train_loader) * epochs
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
        )
        self.history = {"train_loss": [], "val_mae": [], "lr": []}
        best_val_mae, patience_counter, best_state = float("inf"), 0, None

        for epoch in range(1, epochs + 1):
            self.model.train()
            train_losses = []
            for batch in self.train_loader:
                ids  = batch["input_ids"].to(self.device)
                mask = batch["attention_mask"].to(self.device)
                y    = batch["price"].unsqueeze(1).to(self.device)
                self.optimizer.zero_grad()
                if self.scaler:
                    with autocast("cuda"):
                        out  = self.model(ids, mask)
                        loss = self.loss_fn(out, y)
                    self.scaler.scale(loss).backward()
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    out  = self.model(ids, mask)
                    loss = self.loss_fn(out, y)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.optimizer.step()
                self.scheduler.step()
                train_losses.append(loss.item())

            self.model.eval()
            val_preds = []
            with torch.no_grad():
                for batch in self.val_loader:
                    ids  = batch["input_ids"].to(self.device)
                    mask = batch["attention_mask"].to(self.device)
                    out  = self.model(ids, mask)
                    preds_orig = torch.exp(out * self.y_std + self.y_mean) - 1
                    val_preds.append(preds_orig.cpu())
            val_preds = torch.cat(val_preds)
            val_mae   = torch.abs(val_preds - self.y_val).mean().item()

            avg_loss = float(np.mean(train_losses))
            lr = self.scheduler.get_last_lr()[0]
            self.history["train_loss"].append(avg_loss)
            self.history["val_mae"].append(val_mae)
            self.history["lr"].append(lr)
            print(f"Epoch {epoch}/{epochs} | train_loss={avg_loss:.4f} | val_mae={val_mae:.2f}k | lr={lr:.8f}")

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
        self.model.eval()
        preds = []
        with torch.no_grad():
            for batch in self.val_loader:
                ids  = batch["input_ids"].to(self.device)
                mask = batch["attention_mask"].to(self.device)
                out  = self.model(ids, mask)
                preds.append((torch.exp(out * self.y_std + self.y_mean) - 1).cpu())
        return torch.cat(preds).squeeze().tolist()

    def save(self, path):
        import os; os.makedirs(path, exist_ok=True)
        self.model.encoder.save_pretrained(path)
        torch.save({"head_state_dict": self.model.head.state_dict(),
                    "y_mean": self.y_mean, "y_std": self.y_std}, f"{path}/head.pt")

    def load(self, path):
        self.model.encoder = XLMRobertaModel.from_pretrained(path)
        ckpt = torch.load(f"{path}/head.pt", map_location=self.device)
        self.model.head.load_state_dict(ckpt["head_state_dict"])
        self.y_mean = ckpt["y_mean"]
        self.y_std  = ckpt["y_std"]
        self.model.to(self.device)

    def inference(self, item):
        self.model.eval()
        with torch.no_grad():
            enc = self.tokenizer(item.summary, max_length=MAX_LENGTH,
                                  padding="max_length", truncation=True, return_tensors="pt")
            ids  = enc["input_ids"].to(self.device)
            mask = enc["attention_mask"].to(self.device)
            out  = self.model(ids, mask)[0]
            return max(0.0, (torch.exp(out * self.y_std + self.y_mean) - 1).item())
```

- [ ] **Step 1.4: Tạo `pricer_vi_2/phobert_model.py`**

```python
"""PhoBERT-v2 fine-tuned end-to-end for Vietnamese price regression.

IMPORTANT: Requires word segmentation with underthesea before tokenization.
Pre-segment all documents and cache to pkl before calling setup().
"""
import pickle
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from torch.utils.data import DataLoader, Dataset
from torch.amp import autocast, GradScaler
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

MAX_LENGTH = 128


def word_segment_and_cache(items, cache_path: Path):
    """Run underthesea word segmentation on all items. Cache result to pkl."""
    if cache_path.exists():
        print(f"Loading word-seg cache: {cache_path}")
        with open(cache_path, "rb") as f:
            return pickle.load(f)

    from underthesea import word_tokenize
    print(f"Word-segmenting {len(items)} documents (this takes ~30-60 min)...")
    segmented = []
    for i, item in enumerate(items):
        segmented.append(word_tokenize(item.summary, format="text"))
        if (i + 1) % 10000 == 0:
            print(f"  {i+1}/{len(items)} done")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "wb") as f:
        pickle.dump(segmented, f)
    print(f"Cached to {cache_path}")
    return segmented


class PhoBERTDataset(Dataset):
    def __init__(self, segmented_texts, prices, tokenizer, y_mean, y_std):
        self.texts = segmented_texts
        self.prices = prices
        self.tokenizer = tokenizer
        self.y_mean = y_mean
        self.y_std  = y_std

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx], max_length=MAX_LENGTH,
            padding="max_length", truncation=True, return_tensors="pt",
        )
        price_log  = torch.log(torch.tensor(self.prices[idx], dtype=torch.float32) + 1)
        price_norm = (price_log - self.y_mean) / self.y_std
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "price":          price_norm,
        }


class PhoBERTRegressor(nn.Module):
    def __init__(self, dropout_prob=0.1):
        super().__init__()
        self.encoder = AutoModel.from_pretrained("vinai/phobert-base-v2")
        hidden = self.encoder.config.hidden_size  # 768
        self.head = nn.Sequential(
            nn.LayerNorm(hidden),
            nn.Linear(hidden, 256),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(256, 1),
        )

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        return self.head(cls)


class PhoBERTRunner:
    def __init__(self, train_items, val_items):
        self.train_items = train_items
        self.val_items = val_items
        self.model = None
        self.tokenizer = None
        self.device = None
        self.y_mean = None
        self.y_std = None
        self.history = None
        np.random.seed(42)
        torch.manual_seed(42)

    def setup(self, train_seg, val_seg, batch_size=32):
        """
        Args:
            train_seg: list[str] — word-segmented train summaries (from cache)
            val_seg:   list[str] — word-segmented val summaries (from cache)
        """
        self.tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base-v2")

        train_prices = [item.price for item in self.train_items]
        val_prices   = [item.price for item in self.val_items]

        y_log = np.log(np.array(train_prices, dtype=np.float32) + 1)
        self.y_mean = torch.tensor(y_log.mean(), dtype=torch.float32)
        self.y_std  = torch.tensor(y_log.std(),  dtype=torch.float32)
        self.y_val  = torch.FloatTensor(val_prices).unsqueeze(1)

        train_ds = PhoBERTDataset(train_seg, train_prices, self.tokenizer, self.y_mean, self.y_std)
        val_ds   = PhoBERTDataset(val_seg,   val_prices,   self.tokenizer, self.y_mean, self.y_std)
        self.train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=4, pin_memory=True)
        self.val_loader   = DataLoader(val_ds,   batch_size=batch_size * 2, shuffle=False, num_workers=4, pin_memory=True)

        self.model = PhoBERTRegressor()
        enc_p  = sum(p.numel() for p in self.model.encoder.parameters())
        head_p = sum(p.numel() for p in self.model.head.parameters())
        print(f"PhoBERTRegressor: encoder={enc_p:,} head={head_p:,}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using {self.device}")
        self.model.to(self.device)

        self.optimizer = optim.AdamW([
            {"params": self.model.encoder.parameters(), "lr": 2e-5},
            {"params": self.model.head.parameters(),    "lr": 1e-4},
        ], weight_decay=0.01)
        self.loss_fn = nn.L1Loss()
        self.scaler  = GradScaler("cuda") if self.device.type == "cuda" else None

    def train(self, epochs=5, patience=2, warmup_steps=500):
        total_steps = len(self.train_loader) * epochs
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
        )
        self.history = {"train_loss": [], "val_mae": [], "lr": []}
        best_val_mae, patience_counter, best_state = float("inf"), 0, None

        for epoch in range(1, epochs + 1):
            self.model.train()
            train_losses = []
            for batch in self.train_loader:
                ids  = batch["input_ids"].to(self.device)
                mask = batch["attention_mask"].to(self.device)
                y    = batch["price"].unsqueeze(1).to(self.device)
                self.optimizer.zero_grad()
                if self.scaler:
                    with autocast("cuda"):
                        out  = self.model(ids, mask)
                        loss = self.loss_fn(out, y)
                    self.scaler.scale(loss).backward()
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    out  = self.model(ids, mask)
                    loss = self.loss_fn(out, y)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.optimizer.step()
                self.scheduler.step()
                train_losses.append(loss.item())

            self.model.eval()
            val_preds = []
            with torch.no_grad():
                for batch in self.val_loader:
                    ids  = batch["input_ids"].to(self.device)
                    mask = batch["attention_mask"].to(self.device)
                    out  = self.model(ids, mask)
                    preds_orig = torch.exp(out * self.y_std + self.y_mean) - 1
                    val_preds.append(preds_orig.cpu())
            val_preds = torch.cat(val_preds)
            val_mae   = torch.abs(val_preds - self.y_val).mean().item()

            avg_loss = float(np.mean(train_losses))
            lr = self.scheduler.get_last_lr()[0]
            self.history["train_loss"].append(avg_loss)
            self.history["val_mae"].append(val_mae)
            self.history["lr"].append(lr)
            print(f"Epoch {epoch}/{epochs} | train_loss={avg_loss:.4f} | val_mae={val_mae:.2f}k | lr={lr:.8f}")

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
        self.model.eval()
        preds = []
        with torch.no_grad():
            for batch in self.val_loader:
                ids  = batch["input_ids"].to(self.device)
                mask = batch["attention_mask"].to(self.device)
                out  = self.model(ids, mask)
                preds.append((torch.exp(out * self.y_std + self.y_mean) - 1).cpu())
        return torch.cat(preds).squeeze().tolist()

    def save(self, path):
        import os; os.makedirs(path, exist_ok=True)
        self.model.encoder.save_pretrained(path)
        torch.save({"head_state_dict": self.model.head.state_dict(),
                    "y_mean": self.y_mean, "y_std": self.y_std}, f"{path}/head.pt")

    def load(self, path):
        self.model.encoder = AutoModel.from_pretrained(path)
        ckpt = torch.load(f"{path}/head.pt", map_location=self.device)
        self.model.head.load_state_dict(ckpt["head_state_dict"])
        self.y_mean = ckpt["y_mean"]
        self.y_std  = ckpt["y_std"]
        self.model.to(self.device)

    def inference(self, item, seg_text: str):
        """seg_text: word-segmented version of item.summary."""
        self.model.eval()
        with torch.no_grad():
            enc = self.tokenizer(seg_text, max_length=MAX_LENGTH,
                                  padding="max_length", truncation=True, return_tensors="pt")
            ids  = enc["input_ids"].to(self.device)
            mask = enc["attention_mask"].to(self.device)
            out  = self.model(ids, mask)[0]
            return max(0.0, (torch.exp(out * self.y_std + self.y_mean) - 1).item())
```

- [ ] **Step 1.5: Commit**

```bash
git add scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi_2/dnn_sparse.py \
        scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi_2/senttrans_model.py \
        scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi_2/xlmr_model.py \
        scraping_data_tv/Data_processing_for_Vietnamese_data/pricer_vi_2/phobert_model.py \
        scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/plan_day4_v2.md
git commit -m "day4_v2: add model runners (dnn_sparse, senttrans, xlmr, phobert)"
```

---

## Task 2: Notebook 01 — DNN + TF-IDF char_wb 100K

**File:** `day4_v2/day4_v2_01_dnn_tfidf.ipynb`

- [ ] **Step 2.1: Setup cell**

```python
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path("../..").resolve()))

from pricer_vi_2.items import Item
from pricer_vi_2.evaluator import evaluate
from pricer_vi_2.dnn_sparse import SparseDNNRunner
from sklearn.feature_extraction.text import TfidfVectorizer

train, val, test = Item.from_hub("SeanSunny/items_tv_v9")
print(f"train={len(train)}, val={len(val)}, test={len(test)}")
```

- [ ] **Step 2.2: Train cell**

```python
vectorizer = TfidfVectorizer(
    analyzer="char_wb", ngram_range=(2, 4),
    max_features=100_000, sublinear_tf=True,
)

runner = SparseDNNRunner(train, val)
runner.setup(vectorizer, batch_size=256, num_blocks=8, hidden_size=4096)
history = runner.train(epochs=10, patience=3)
```

- [ ] **Step 2.3: Save weights + val predictions + test predictions**

```python
Path("weights").mkdir(exist_ok=True)
runner.save("weights/dnn_tfidf.pth")

Path("val_predictions").mkdir(exist_ok=True)

# Val predictions (3926 samples) — dùng cho stacking
val_preds = runner.val_predictions()
with open("val_predictions/dnn_tfidf_val.json", "w") as f:
    json.dump(val_preds, f)

# Test predictions (3872 samples) — dùng cho ensemble evaluation
import torch, numpy as np
test_docs = [item.summary for item in test]
X_test = runner.vectorizer.transform(test_docs)
runner.model.eval()
test_preds = []
with torch.no_grad():
    for i in range(0, len(test), 256):
        batch = torch.FloatTensor(X_test[i:i+256].toarray()).to(runner.device)
        pred_norm = runner.model(batch)
        pred_orig = torch.exp(pred_norm * runner.y_std + runner.y_mean) - 1
        test_preds.extend(pred_orig.cpu().squeeze().tolist())
with open("val_predictions/dnn_tfidf_test.json", "w") as f:
    json.dump(test_preds, f)
print(f"Val: {len(val_preds)} | Test: {len(test_preds)}")
```

- [ ] **Step 2.4: Plot training history**

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].plot(history["train_loss"], label="train_loss")
axes[0].set_title("Train Loss (L1, log-normalized space)")
axes[0].set_xlabel("Epoch"); axes[0].legend()
axes[1].plot(history["val_mae"], label="val_mae", color="orange")
axes[1].set_title("Val MAE (k VND, original scale)")
axes[1].set_xlabel("Epoch"); axes[1].legend()
plt.tight_layout(); plt.show()
```

- [ ] **Step 2.5: Evaluate trên test (200 samples)**

```python
def dnn_tfidf_predictor(item):
    return runner.inference(item)

evaluate(dnn_tfidf_predictor, test)
# Ghi lại MAE kết quả vào day4_v2_results.json
```

- [ ] **Step 2.6: Commit**

```bash
git add scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/
git commit -m "day4_v2 task2: DNN+TF-IDF char_wb notebook + weights"
```

---

## Task 3: Notebook 02 — DNN + HashingVec 5000

**File:** `day4_v2/day4_v2_02_dnn_hashvec.ipynb`

- [ ] **Step 3.1: Setup cell**

```python
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path("../..").resolve()))

from pricer_vi_2.items import Item
from pricer_vi_2.evaluator import evaluate
from pricer_vi_2.dnn_sparse import SparseDNNRunner
from sklearn.feature_extraction.text import HashingVectorizer

train, val, test = Item.from_hub("SeanSunny/items_tv_v9")
```

- [ ] **Step 3.2: Train cell**

```python
# binary=True: 0/1 không đếm frequency — phù hợp hơn cho DNN
# Không dùng stop_words vì Vietnamese
vectorizer = HashingVectorizer(n_features=5_000, binary=True)

runner = SparseDNNRunner(train, val)
runner.setup(vectorizer, batch_size=256, num_blocks=8, hidden_size=4096)
history = runner.train(epochs=10, patience=3)
```

- [ ] **Step 3.3: Save weights + val predictions + test predictions**

```python
Path("weights").mkdir(exist_ok=True)
runner.save("weights/dnn_hashvec.pth")
Path("val_predictions").mkdir(exist_ok=True)

val_preds = runner.val_predictions()
with open("val_predictions/dnn_hashvec_val.json", "w") as f:
    json.dump(val_preds, f)

import torch
test_docs = [item.summary for item in test]
X_test = runner.vectorizer.transform(test_docs)
runner.model.eval()
test_preds = []
with torch.no_grad():
    for i in range(0, len(test), 256):
        batch = torch.FloatTensor(X_test[i:i+256].toarray()).to(runner.device)
        pred_norm = runner.model(batch)
        pred_orig = torch.exp(pred_norm * runner.y_std + runner.y_mean) - 1
        test_preds.extend(pred_orig.cpu().squeeze().tolist())
with open("val_predictions/dnn_hashvec_test.json", "w") as f:
    json.dump(test_preds, f)
print(f"Val: {len(val_preds)} | Test: {len(test_preds)}")
```

- [ ] **Step 3.4: Evaluate trên test**

```python
def dnn_hashvec_predictor(item):
    return runner.inference(item)

evaluate(dnn_hashvec_predictor, test)
```

- [ ] **Step 3.5: Commit**

```bash
git add scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/
git commit -m "day4_v2 task3: DNN+HashingVec notebook + weights"
```

---

## Task 4: Notebook 03 — Multilingual SentenceTransformer + DNN

**File:** `day4_v2/day4_v2_03_senttrans.ipynb`

- [ ] **Step 4.1: Setup + pre-compute embeddings (cache)**

```python
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path("../..").resolve()))

from pricer_vi_2.items import Item
from pricer_vi_2.evaluator import evaluate
from pricer_vi_2.senttrans_model import SentTransRunner

train, val, test = Item.from_hub("SeanSunny/items_tv_v9")

runner = SentTransRunner(train, val)
cache_path = Path("cache/senttrans_embeddings_train.pkl")
runner.encode_and_cache(cache_path=cache_path)
# Lần đầu: ~30-60 phút. Lần sau: load từ cache ngay.
```

- [ ] **Step 4.2: Setup model + train**

```python
runner.setup(batch_size=256, num_blocks=6)
history = runner.train(epochs=15, patience=3)
```

- [ ] **Step 4.3: Save weights + val predictions + test predictions**

```python
Path("weights").mkdir(exist_ok=True)
runner.save("weights/senttrans_dnn.pth")
Path("val_predictions").mkdir(exist_ok=True)

val_preds = runner.val_predictions()
with open("val_predictions/senttrans_val.json", "w") as f:
    json.dump(val_preds, f)

# Encode test set then run DNN head
import torch
test_texts = [item.summary for item in test]
X_test = torch.FloatTensor(runner.encoder.encode(test_texts, show_progress_bar=True, batch_size=256))
runner.model.eval()
test_preds = []
with torch.no_grad():
    for i in range(0, len(X_test), 256):
        batch = X_test[i:i+256].to(runner.device)
        pred_norm = runner.model(batch)
        pred_orig = torch.exp(pred_norm * runner.y_std + runner.y_mean) - 1
        test_preds.extend(pred_orig.cpu().squeeze().tolist())
with open("val_predictions/senttrans_test.json", "w") as f:
    json.dump(test_preds, f)
print(f"Val: {len(val_preds)} | Test: {len(test_preds)}")
```

- [ ] **Step 4.4: Evaluate trên test**

```python
evaluate(runner.inference, test)
```

- [ ] **Step 4.5: Commit**

```bash
git add scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/
git commit -m "day4_v2 task4: SentTrans+DNN notebook + weights"
```

---

## Task 5: Notebook 04 — XLM-RoBERTa Fine-tune

**File:** `day4_v2/day4_v2_04_xlmr.ipynb`

- [ ] **Step 5.1: Setup**

```python
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path("../..").resolve()))

from pricer_vi_2.items import Item
from pricer_vi_2.evaluator import evaluate
from pricer_vi_2.xlmr_model import XLMRRunner

train, val, test = Item.from_hub("SeanSunny/items_tv_v9")

runner = XLMRRunner(train, val)
runner.setup(batch_size=32)
```

- [ ] **Step 5.2: Train**

```python
# ~10-15h trên 3090Ti
history = runner.train(epochs=5, patience=2, warmup_steps=500)
```

- [ ] **Step 5.3: Save + val predictions + test predictions**

```python
runner.save("weights/xlmr")
Path("val_predictions").mkdir(exist_ok=True)

val_preds = runner.val_predictions()
with open("val_predictions/xlmr_val.json", "w") as f:
    json.dump(val_preds, f)

# Test predictions — reuse tokenizer + model
import torch
from torch.utils.data import DataLoader
from pricer_vi_2.xlmr_model import ViPriceDataset

test_ds = ViPriceDataset(test, runner.tokenizer, runner.y_mean, runner.y_std)
test_loader = DataLoader(test_ds, batch_size=64, shuffle=False, num_workers=4, pin_memory=True)
runner.model.eval()
test_preds = []
with torch.no_grad():
    for batch in test_loader:
        ids  = batch["input_ids"].to(runner.device)
        mask = batch["attention_mask"].to(runner.device)
        out  = runner.model(ids, mask)
        pred_orig = torch.exp(out * runner.y_std + runner.y_mean) - 1
        test_preds.extend(pred_orig.cpu().squeeze().tolist())
with open("val_predictions/xlmr_test.json", "w") as f:
    json.dump(test_preds, f)
print(f"Val: {len(val_preds)} | Test: {len(test_preds)}")
```

- [ ] **Step 5.4: Evaluate trên test**

```python
evaluate(runner.inference, test)
```

- [ ] **Step 5.5: Commit**

```bash
git add scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/
git commit -m "day4_v2 task5: XLM-RoBERTa fine-tune notebook + weights"
```

---

## Task 6: Notebook 05 — PhoBERT-v2 Fine-tune

**File:** `day4_v2/day4_v2_05_phobert.ipynb`

- [ ] **Step 6.1: Word segmentation (cache — chạy 1 lần)**

```python
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path("../..").resolve()))

from pricer_vi_2.items import Item
from pricer_vi_2.phobert_model import word_segment_and_cache, PhoBERTRunner
from pricer_vi_2.evaluator import evaluate

train, val, test = Item.from_hub("SeanSunny/items_tv_v9")

# Segment train + val, cache to pkl
# Ước tính: 269K docs × ~0.1s/doc ≈ 7.5h (underthesea single-thread)
# Nếu quá chậm: dùng subset or multiprocessing với os.fork
train_seg = word_segment_and_cache(
    train, Path("cache/phobert_seg_train.pkl")
)
val_seg = word_segment_and_cache(
    val, Path("cache/phobert_seg_val.pkl")
)
print(f"Segmented: train={len(train_seg)}, val={len(val_seg)}")
print(f"Example: {train_seg[0][:100]}")
```

- [ ] **Step 6.2: Setup model**

```python
runner = PhoBERTRunner(train, val)
runner.setup(train_seg, val_seg, batch_size=32)
```

- [ ] **Step 6.3: Train**

```python
# ~10h trên 3090Ti (sau khi đã có cache)
history = runner.train(epochs=5, patience=2, warmup_steps=500)
```

- [ ] **Step 6.4: Save + val predictions + test predictions**

```python
runner.save("weights/phobert")
Path("val_predictions").mkdir(exist_ok=True)

val_preds = runner.val_predictions()
with open("val_predictions/phobert_val.json", "w") as f:
    json.dump(val_preds, f)

# Word-segment test set, then predict
test_seg = word_segment_and_cache(test, Path("cache/phobert_seg_test.pkl"))

import torch
from torch.utils.data import DataLoader
from pricer_vi_2.phobert_model import PhoBERTDataset

test_prices = [item.price for item in test]
test_ds = PhoBERTDataset(test_seg, test_prices, runner.tokenizer, runner.y_mean, runner.y_std)
test_loader = DataLoader(test_ds, batch_size=64, shuffle=False, num_workers=4, pin_memory=True)
runner.model.eval()
test_preds = []
with torch.no_grad():
    for batch in test_loader:
        ids  = batch["input_ids"].to(runner.device)
        mask = batch["attention_mask"].to(runner.device)
        out  = runner.model(ids, mask)
        pred_orig = torch.exp(out * runner.y_std + runner.y_mean) - 1
        test_preds.extend(pred_orig.cpu().squeeze().tolist())
with open("val_predictions/phobert_test.json", "w") as f:
    json.dump(test_preds, f)
print(f"Val: {len(val_preds)} | Test: {len(test_preds)}")
```

- [ ] **Step 6.5: Evaluate trên test**

```python
# Cần segment test text trước khi inference
from underthesea import word_tokenize

def phobert_predictor(item):
    seg = word_tokenize(item.summary, format="text")
    return runner.inference(item, seg)

evaluate(phobert_predictor, test)
```

- [ ] **Step 6.6: Commit**

```bash
git add scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/
git commit -m "day4_v2 task6: PhoBERT fine-tune notebook + weights"
```

---

## Task 7: Notebook 06 — Ridge Stacking Ensemble

**File:** `day4_v2/day4_v2_06_ensemble.ipynb`

- [ ] **Step 7.1: Load tất cả val predictions**

```python
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path("../..").resolve()))

from pricer_vi_2.items import Item
from pricer_vi_2.evaluator import evaluate
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

train, val, test = Item.from_hub("SeanSunny/items_tv_v9")
val_prices = np.array([item.price for item in val], dtype=np.float32)

model_names = ["dnn_tfidf", "dnn_hashvec", "senttrans", "xlmr", "phobert"]
val_preds = {}
for name in model_names:
    with open(f"val_predictions/{name}_val.json") as f:
        val_preds[name] = np.array(json.load(f), dtype=np.float32)

# Stack matrix: (3926, 5)
X_val_stack = np.column_stack([val_preds[n] for n in model_names])
print(f"Stacking matrix: {X_val_stack.shape}")

# Individual MAE
for name in model_names:
    mae = np.abs(val_preds[name] - val_prices).mean()
    print(f"  {name}: val_mae={mae:.2f}k")
```

- [ ] **Step 7.2: Fit Ridge stacker — optimize MAE**

```python
from sklearn.model_selection import cross_val_score
from sklearn.metrics import make_scorer, mean_absolute_error

mae_scorer = make_scorer(mean_absolute_error, greater_is_better=False)

# Grid search alpha
best_alpha, best_mae = None, float("inf")
for alpha in [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]:
    ridge = Ridge(alpha=alpha)
    scores = cross_val_score(ridge, X_val_stack, val_prices, cv=5, scoring=mae_scorer)
    cv_mae = -scores.mean()
    print(f"alpha={alpha}: CV MAE={cv_mae:.2f}k")
    if cv_mae < best_mae:
        best_mae, best_alpha = cv_mae, alpha

print(f"\nBest alpha={best_alpha}, CV MAE={best_mae:.2f}k")

# Fit trên toàn val set
stacker = Ridge(alpha=best_alpha)
stacker.fit(X_val_stack, val_prices)
print(f"Stacker weights: {dict(zip(model_names, stacker.coef_.round(3)))}")

val_ensemble_pred = stacker.predict(X_val_stack)
val_ensemble_mae  = np.abs(val_ensemble_pred - val_prices).mean()
print(f"Ensemble val MAE={val_ensemble_mae:.2f}k")
```

- [ ] **Step 7.3: Load test predictions từ tất cả 5 models**

```python
test_preds = {}
for name in model_names:
    with open(f"val_predictions/{name}_test.json") as f:
        test_preds[name] = np.array(json.load(f), dtype=np.float32)

# Test stack matrix: (3872, 5)
X_test_stack = np.column_stack([test_preds[n] for n in model_names])
test_prices_all = np.array([item.price for item in test], dtype=np.float32)

# Individual MAE trên toàn test set
print("=== Test MAE (toàn 3872 samples) ===")
for name in model_names:
    mae = np.abs(test_preds[name] - test_prices_all).mean()
    print(f"  {name}: {mae:.2f}k")

ensemble_test_pred = stacker.predict(X_test_stack)
ensemble_test_mae  = np.abs(ensemble_test_pred - test_prices_all).mean()
print(f"  ensemble: {ensemble_test_mae:.2f}k")
```

- [ ] **Step 7.4: Evaluate ensemble trên test (200 samples qua evaluator.py)**

```python
# Lấy 200 samples đầu của test (giống evaluator.py default)
N = 200
test_200 = test[:N]
test_stack_200 = X_test_stack[:N]   # (200, 5)

ensemble_200_preds = stacker.predict(test_stack_200)
ensemble_200_preds = np.maximum(0, ensemble_200_preds)  # clip >=0

pred_lookup = {id(item): float(ensemble_200_preds[i]) for i, item in enumerate(test_200)}

def ensemble_predictor(item):
    return pred_lookup[id(item)]

evaluate(ensemble_predictor, test)
```

- [ ] **Step 7.5: Save results JSON**

```python
results = {
    "dnn_tfidf":   {"val_mae": float(np.abs(val_preds["dnn_tfidf"]   - val_prices).mean())},
    "dnn_hashvec": {"val_mae": float(np.abs(val_preds["dnn_hashvec"] - val_prices).mean())},
    "senttrans":   {"val_mae": float(np.abs(val_preds["senttrans"]   - val_prices).mean())},
    "xlmr":        {"val_mae": float(np.abs(val_preds["xlmr"]        - val_prices).mean())},
    "phobert":     {"val_mae": float(np.abs(val_preds["phobert"]     - val_prices).mean())},
    "ensemble":    {
        "val_mae": val_ensemble_mae,
        "alpha": best_alpha,
        "weights": dict(zip(model_names, stacker.coef_.tolist())),
    },
}
with open("day4_v2_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(json.dumps(results, indent=2))
```

- [ ] **Step 7.6: Commit**

```bash
git add scraping_data_tv/Data_processing_for_Vietnamese_data/day4_v2/
git commit -m "day4_v2 task7: Ridge stacking ensemble + final results"
```

---

## 4. Kết quả thực tế (điền sau khi chạy)

| Model | Val MAE | Test MAE (200) | R² | Ghi chú |
|---|---|---|---|---|
| DNN + TF-IDF char_wb | — | — | — | |
| DNN + HashingVec | — | — | — | |
| Multilingual SentTrans | — | — | — | |
| XLM-RoBERTa | — | — | — | |
| PhoBERT-v2 | — | — | — | |
| **Ensemble Ridge** | — | — | — | |

---

## 5. Key Constraints

| Constraint | Giá trị |
|---|---|
| Primary metric | **MAE (k VND)** — KHÔNG dùng RMSLE |
| Evaluate | `pricer_vi_2/evaluator.py` — 200 test samples |
| Price unit | `round(price_vnd/1000)` — range 5–1000 |
| Target transform | `log1p(price)` + z-normalize (khác Day 3 v2 LGB) |
| Loss | `nn.L1Loss()` — trực tiếp tối ưu MAE |
| GPU | RTX 3090 Ti 24GB, vast.ai |
| num_workers | 0 với WSL2 local, 4 với vast.ai Linux |
| Stacking metric | MAE trên val set (3,926 samples) |
| KHÔNG sửa | `pricer_vi_2/items.py`, `pricer_vi_2/evaluator.py` |

---

*Tạo: 2026-05-17 — Day 4 v2 Deep Learning Vietnamese Price Prediction*
