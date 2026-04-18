# %% [markdown]
# # Day 4 v6: PhoBERT Full Fine-tune (20 epochs) — Vietnamese Price Prediction
#
# **Changes from v5:**
# - LoRA REMOVED (failed in v5: 0.5729, insufficient capacity)
# - Epochs: 10 -> 20 (v5 cosine LR hit 0.00 at epoch 10, model still improving)
# - Early stopping patience: 3 -> 5
# - Keep: LayerNorm+GELU head, batch=96, num_workers=4, dropout=0.2
#
# **Pipeline:**
# - Phase 1: Load data + reuse v4/v5 caches
# - Phase 2: PhoBERT full fine-tune (20 epochs, patience=5)
# - Phase 3: PhoBERT embed -> PCA(256) -> LightGBM + Optuna
# - Phase 4: Frontier LLM zero-shot (gpt-4o-mini, gpt-5-nano, gpt-5-mini, 200 items)
# - Phase 5: Blending (v6 + v4 + Day3)
# - Phase 6: Summary + charts
#
# **Baseline:** v5-old best blended RMSLE=0.4191
#
# **Target:** RMSLE <= 0.40

# %% Install (uncomment on first run)
# !uv pip uninstall torch torchvision torchaudio
# !uv pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130

# %% Imports + Config
import os
import sys
import gc
import json
import joblib
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torch.amp import autocast, GradScaler
from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import FeatureUnion
from sklearn.decomposition import PCA
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.sparse import hstack
from scipy.optimize import minimize as scipy_minimize
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from transformers import AutoModel, AutoTokenizer, get_cosine_schedule_with_warmup
import lightgbm as lgb
import optuna

os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
optuna.logging.set_verbosity(optuna.logging.WARNING)

DAY4 = Path.cwd()
sys.path.insert(0, str(DAY4.parent))
from pricer_vi.items import Item
from pricer_vi.deep_neural_network import (
    DeepNeuralNetwork, MLP, predict_batch,
)
from pricer_vi.evaluator import plot_predictions

DATASET = "SeanSunny/items_tv_v6"
MAX_PRICE = 1_000_000
SEED = 42
PHOBERT_NAME = "vinai/phobert-base-v2"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)
    torch.backends.cudnn.deterministic = True

print(f"Device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"GPU: {torch.cuda.get_device_name()}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

WEIGHTS_V6 = DAY4 / "weights_v6"
WEIGHTS_V6.mkdir(exist_ok=True)
WEIGHTS_V5 = DAY4 / "weights_v5"
WEIGHTS_V4 = DAY4 / "weights"

ALL_RESULTS = {}
ALL_PREDS_VAL = {}
ALL_PREDS_TEST = {}

# %% Helpers
def rmsle(y_true, y_pred):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.clip(np.array(y_pred, dtype=float), 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def mape(y_true, y_pred):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    mask = y_true > 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate_and_store(y_true, y_pred, name, names=None):
    """Evaluate, print, plot, store in ALL_RESULTS."""
    r = plot_predictions(y_true, y_pred, title=name, names=names)
    print(f"\n{'='*60}")
    print(f"{name} ({len(y_true)} items)")
    print(f"  RMSLE:  {r['rmsle']:.4f}")
    print(f"  MAE:    {r['mae']:,.0f} VND")
    print(f"  MAPE:   {r['mape']:.1f}%")
    print(f"  R2:     {r['r2']:.1f}%")
    print(f"{'='*60}")
    ALL_RESULTS[name] = r
    return r


def plot_phobert_history(history, title):
    """Plot PhoBERT training: loss, RMSLE, MAE, LR."""
    epochs = list(range(1, len(history["train_loss"]) + 1))
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Loss (MSE)", "Val RMSLE", "Val MAE (VND)", "Learning Rate"),
    )
    fig.add_trace(go.Scatter(x=epochs, y=history["train_loss"], name="Train",
                             line=dict(color="steelblue")), row=1, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_loss"], name="Val",
                             line=dict(color="tomato")), row=1, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_rmsle"], name="RMSLE",
                             line=dict(color="tomato"), mode="lines+markers"), row=1, col=2)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_mae"], name="MAE",
                             line=dict(color="mediumseagreen"), mode="lines+markers"), row=2, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["lr"], name="LR",
                             line=dict(color="purple")), row=2, col=2)
    fig.update_layout(title=title, width=1000, height=600, template="plotly_white", showlegend=False)
    fig.show()


# ============================================================
# PHASE 1: LOAD DATA + CACHE (reuse v4/v5)
# ============================================================

# %% [markdown]
# ## Phase 1: Load Data + Reuse v4/v5 Cache

# %% Load data from HuggingFace
print("--- Loading data ---")
train_items, val_items, test_items = Item.from_hub(DATASET)

def filter_items(items, max_price=MAX_PRICE):
    return [it for it in items if 0 < it.price <= max_price]

train_items = filter_items(train_items)
val_items = filter_items(val_items)
test_items = filter_items(test_items)
print(f"Train: {len(train_items):,} | Val: {len(val_items):,} | Test: {len(test_items):,}")

train_summaries = [it.summary for it in train_items]
val_summaries = [it.summary for it in val_items]
test_summaries = [it.summary for it in test_items]

train_prices = np.array([it.price for it in train_items], dtype=np.float32)
val_prices = np.array([it.price for it in val_items], dtype=np.float32)
test_prices = np.array([it.price for it in test_items], dtype=np.float32)

train_categories = [it.category for it in train_items]
val_categories = [it.category for it in val_items]
test_categories = [it.category for it in test_items]

test_names = [it.title[:40] + "..." if len(it.title) > 40 else it.title for it in test_items]

# %% Category + Underthesea tokenize
print("--- Category one-hot ---")
cat_encoder = OneHotEncoder(sparse_output=True, handle_unknown="ignore")
cat_train = cat_encoder.fit_transform(np.array(train_categories).reshape(-1, 1))
cat_val = cat_encoder.transform(np.array(val_categories).reshape(-1, 1))
cat_test = cat_encoder.transform(np.array(test_categories).reshape(-1, 1))
print(f"Categories ({cat_train.shape[1]}): {cat_encoder.categories_[0].tolist()}")

UNDERTHESEA_CACHE = {
    "train": DAY4 / "tokenized_train_1m.pkl",
    "val": DAY4 / "tokenized_val_1m.pkl",
    "test": DAY4 / "tokenized_test_1m.pkl",
}
DAY3 = DAY4.parent / "day3"

def load_or_tokenize(summaries, cache_path, label=""):
    if cache_path.exists():
        print(f"  Loading cache: {cache_path.name}")
        return joblib.load(cache_path)
    day3_path = DAY3 / cache_path.name
    if day3_path.exists():
        print(f"  Copying from Day 3: {day3_path}")
        data = joblib.load(day3_path)
        joblib.dump(data, cache_path)
        return data
    print(f"  Tokenizing {label} ({len(summaries):,} docs)...")
    from underthesea import word_tokenize
    tokenized = [word_tokenize(s, format="text") for s in summaries]
    joblib.dump(tokenized, cache_path)
    return tokenized

print("\n--- Underthesea tokenize ---")
tok_train = load_or_tokenize(train_summaries, UNDERTHESEA_CACHE["train"], "train")
tok_val = load_or_tokenize(val_summaries, UNDERTHESEA_CACHE["val"], "val")
tok_test = load_or_tokenize(test_summaries, UNDERTHESEA_CACHE["test"], "test")

# %% PhoBERT tokenize
print("\n--- PhoBERT tokenize ---")
phobert_tokenizer = AutoTokenizer.from_pretrained(PHOBERT_NAME)

t0 = time.time()
phobert_enc_train = phobert_tokenizer(
    tok_train, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
phobert_enc_val = phobert_tokenizer(
    tok_val, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
phobert_enc_test = phobert_tokenizer(
    tok_test, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
print(f"  Train: {phobert_enc_train['input_ids'].shape} ({time.time()-t0:.1f}s)")

# %% Load v4 caches: AITeamVN embeddings + HashingVec + TF-IDF Arch C
EMB_AT = {
    "train": DAY4 / "aiteamvn_train.npy",
    "val": DAY4 / "aiteamvn_val.npy",
    "test": DAY4 / "aiteamvn_test.npy",
}

print("\n--- AITeamVN embeddings (v4 cache) ---")
at_emb = {}
for split, path in EMB_AT.items():
    if path.exists():
        at_emb[split] = np.load(path)
        print(f"  {split}: {at_emb[split].shape}")
    else:
        print(f"  WARNING: {path.name} not found -- v4 Model 2b blending will be skipped")

print("\n--- HashingVectorizer ---")
hv = HashingVectorizer(n_features=5000, binary=True, alternate_sign=False)
X_hv_val = hv.transform(val_summaries)
X_hv_test = hv.transform(test_summaries)
print(f"  HashingVec: {X_hv_test.shape}")

print("\n--- TF-IDF Arch C (for Day 3 LGB retrain) ---")
# Reuse v5 cache if exists, else create in v6
ARCH_C_CACHE_V5 = WEIGHTS_V5 / "arch_c_vectorizer.pkl"
ARCH_C_CACHE_V6 = WEIGHTS_V6 / "arch_c_vectorizer.pkl"
ARCH_C_CACHE = ARCH_C_CACHE_V5 if ARCH_C_CACHE_V5.exists() else ARCH_C_CACHE_V6

if ARCH_C_CACHE.exists():
    arch_c = joblib.load(ARCH_C_CACHE)
    print(f"  Loaded: {ARCH_C_CACHE}")
    X_c_train = arch_c.transform(tok_train)
else:
    t0 = time.time()
    arch_c = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=5000)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=5000)),
    ])
    X_c_train = arch_c.fit_transform(tok_train)
    joblib.dump(arch_c, ARCH_C_CACHE_V6)
    print(f"  Fitted Arch C: {X_c_train.shape} ({time.time()-t0:.1f}s)")
X_c_val = arch_c.transform(tok_val)
X_c_test = arch_c.transform(tok_test)

X_cc_train = hstack([X_c_train, cat_train])
X_cc_val = hstack([X_c_val, cat_val])
X_cc_test = hstack([X_c_test, cat_test])
print(f"  C+Cat: {X_cc_train.shape}")

# %% Phase 1 summary
print("\n" + "=" * 60)
print("PHASE 1 COMPLETE")
print(f"  Train: {len(train_items):,} | Val: {len(val_items):,} | Test: {len(test_items):,}")
print(f"  PhoBERT tokenized: {phobert_enc_train['input_ids'].shape}")
print(f"  AITeamVN: {'loaded' if at_emb else 'NOT available'}")
print(f"  Arch C+Cat: {X_cc_train.shape}")
print("=" * 60)


# ============================================================
# PHASE 2: PhoBERT FULL FINE-TUNE (20 epochs)
# ============================================================

# %% [markdown]
# ## Phase 2: PhoBERT Full Fine-tune (v6)
#
# **Key changes from v5:**
# - LoRA removed (failed: 0.5729)
# - Epochs: 10 -> 20 (cosine LR decay slower, LR ~5e-6 at epoch 10 instead of 0)
# - Patience: 3 -> 5 (allow model to recover from plateaus)
# - Same: LayerNorm+GELU head, batch=96, dropout=0.2, lr=2e-5, warmup=10%

# %% PhoBERT model + training infrastructure
def mean_pooling(model_output, attention_mask):
    """Mean pooling over last hidden state, masking padding tokens."""
    token_embeddings = model_output.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (token_embeddings * mask_expanded).sum(1) / mask_expanded.sum(1).clamp(min=1e-9)


class PhoBERTRegressor(nn.Module):
    """PhoBERT + mean pooling + LayerNorm + GELU regression head."""

    def __init__(self, model_name=PHOBERT_NAME):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.regressor = nn.Sequential(
            nn.LayerNorm(768),
            nn.Linear(768, 256),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(256, 1),
        )
        self._init_head()

    def _init_head(self):
        """Xavier init for GELU layers, small init for output."""
        for m in self.regressor:
            if isinstance(m, nn.Linear):
                if m.out_features == 1:
                    nn.init.normal_(m.weight, std=0.01)
                else:
                    nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = mean_pooling(outputs, attention_mask)
        return self.regressor(pooled)

    def extract_embeddings(self, input_ids, attention_mask):
        """Mean-pooled 768d embeddings (no grad, for Phase 3)."""
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        return mean_pooling(outputs, attention_mask)


class PhoBERTDataset(Dataset):
    def __init__(self, encodings, labels):
        self.input_ids = encodings["input_ids"]
        self.attention_mask = encodings["attention_mask"]
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.input_ids[idx], self.attention_mask[idx], self.labels[idx]

# %% train_phobert function
def train_phobert(model, train_enc, val_enc, train_prices_np, val_prices_np, device,
                  epochs=20, batch_size=96, lr=2e-5, weight_decay=0.01,
                  warmup_ratio=0.1, patience=5, max_grad_norm=1.0):
    """Train PhoBERT with normalized log-target, fp16, cosine LR, early stopping.

    Returns: (model, y_mean, y_std, history)
    """
    # Normalize target: log1p -> (x - mean) / std
    y_train_log = torch.log1p(torch.FloatTensor(train_prices_np))
    y_val_log = torch.log1p(torch.FloatTensor(val_prices_np))
    y_mean = y_train_log.mean()
    y_std = y_train_log.std()
    y_train_norm = (y_train_log - y_mean) / y_std
    y_val_norm = (y_val_log - y_mean) / y_std

    print(f"  Target normalize: mean={y_mean:.4f}, std={y_std:.4f}")
    print(f"  Norm range: [{y_train_norm.min():.2f}, {y_train_norm.max():.2f}]")

    train_loader = DataLoader(
        PhoBERTDataset(train_enc, y_train_norm),
        batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True,
    )

    model.to(device)
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr, weight_decay=weight_decay)

    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * warmup_ratio)
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    loss_fn = nn.MSELoss()
    scaler = GradScaler("cuda") if device.type == "cuda" else None

    n_params = sum(p.numel() for p in trainable_params)
    print(f"  Trainable: {n_params:,} params | Batch: {batch_size} | Steps/ep: {len(train_loader)}")
    print(f"  Total steps: {total_steps} | Warmup: {warmup_steps} | Epochs: {epochs}")

    history = {"train_loss": [], "val_loss": [], "val_rmsle": [], "val_mae": [], "lr": []}
    best_val_rmsle = float("inf")
    best_state = None
    patience_counter = 0

    val_ids = val_enc["input_ids"]
    val_mask = val_enc["attention_mask"]

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        epoch_losses = []

        for ids, mask, labels in train_loader:
            ids = ids.to(device)
            mask = mask.to(device)
            labels = labels.to(device).unsqueeze(1)

            optimizer.zero_grad()
            if scaler:
                with autocast(device_type="cuda"):
                    pred = model(ids, mask)
                    loss = loss_fn(pred, labels)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(trainable_params, max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
            else:
                pred = model(ids, mask)
                loss = loss_fn(pred, labels)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable_params, max_grad_norm)
                optimizer.step()

            scheduler.step()
            epoch_losses.append(loss.item())

        # Validation
        model.eval()
        val_preds = []
        with torch.no_grad():
            for i in range(0, len(val_ids), 64):
                b_ids = val_ids[i:i+64].to(device)
                b_mask = val_mask[i:i+64].to(device)
                if scaler:
                    with autocast(device_type="cuda"):
                        out = model(b_ids, b_mask)
                else:
                    out = model(b_ids, b_mask)
                val_preds.append(out.float().cpu())

        val_preds_t = torch.cat(val_preds)
        val_loss = loss_fn(val_preds_t, y_val_norm.unsqueeze(1)).item()

        # RMSLE in VND
        val_pred_vnd = torch.expm1(val_preds_t * y_std + y_mean).clamp(min=0).numpy().flatten()
        val_rmsle = rmsle(val_prices_np, val_pred_vnd)
        val_mae = float(np.mean(np.abs(val_prices_np - val_pred_vnd)))
        current_lr = scheduler.get_last_lr()[0]

        history["train_loss"].append(float(np.mean(epoch_losses)))
        history["val_loss"].append(val_loss)
        history["val_rmsle"].append(val_rmsle)
        history["val_mae"].append(val_mae)
        history["lr"].append(current_lr)

        elapsed = time.time() - t0
        print(
            f"  Epoch {epoch}/{epochs} ({elapsed:.0f}s) | "
            f"Train: {np.mean(epoch_losses):.4f} | "
            f"Val: {val_loss:.4f} | "
            f"RMSLE: {val_rmsle:.4f} | "
            f"MAE: {val_mae:,.0f} | "
            f"LR: {current_lr:.2e}"
        )

        if val_rmsle < best_val_rmsle:
            best_val_rmsle = val_rmsle
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
            print(f"    >> New best: RMSLE={best_val_rmsle:.4f}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"    >> Early stopping at epoch {epoch} (patience={patience})")
                break

    model.load_state_dict(best_state)
    model.to(device)
    print(f"  Restored best: Val RMSLE={best_val_rmsle:.4f}")
    return model, y_mean, y_std, history

# %% predict_phobert function
def predict_phobert(model, encodings, y_mean, y_std, device, batch_size=64):
    """Predict VND prices from PhoBERT encodings."""
    model.eval()
    ids = encodings["input_ids"]
    mask = encodings["attention_mask"]
    y_mean_d = y_mean.to(device) if hasattr(y_mean, 'to') else torch.tensor(y_mean).to(device)
    y_std_d = y_std.to(device) if hasattr(y_std, 'to') else torch.tensor(y_std).to(device)
    use_amp = device.type == "cuda"
    preds = []
    with torch.no_grad():
        for i in range(0, len(ids), batch_size):
            b_ids = ids[i:i+batch_size].to(device)
            b_mask = mask[i:i+batch_size].to(device)
            if use_amp:
                with autocast(device_type="cuda"):
                    out = model(b_ids, b_mask)
            else:
                out = model(b_ids, b_mask)
            pred_vnd = torch.expm1(out.float() * y_std_d + y_mean_d).clamp(min=0)
            preds.append(pred_vnd.cpu().numpy().flatten())
    return np.concatenate(preds)


# %% [markdown]
# ### Phase 2: Train PhoBERT (20 epochs, patience=5)

# %% Phase 2: Train
print("\n" + "#" * 60)
print("# Phase 2: PhoBERT Full Fine-tune (v6, 20 epochs)")
print("#" * 60)

PHOBERT_V6_PATH = WEIGHTS_V6 / "phobert_v6_full.pth"

if PHOBERT_V6_PATH.exists():
    print("Loading saved weights...")
    model_phobert = PhoBERTRegressor(PHOBERT_NAME)
    ckpt = torch.load(PHOBERT_V6_PATH, map_location=DEVICE, weights_only=False)
    model_phobert.load_state_dict(ckpt["state_dict"])
    model_phobert.to(DEVICE)
    y_mean_pb, y_std_pb = ckpt["y_mean"], ckpt["y_std"]
    hist_pb = ckpt.get("history")
    print(f"  Loaded: {PHOBERT_V6_PATH.name}")
else:
    model_phobert = PhoBERTRegressor(PHOBERT_NAME)
    model_phobert, y_mean_pb, y_std_pb, hist_pb = train_phobert(
        model_phobert, phobert_enc_train, phobert_enc_val,
        train_prices, val_prices, DEVICE,
        epochs=20, batch_size=96, lr=2e-5, patience=5,
    )
    torch.save({
        "state_dict": model_phobert.state_dict(),
        "y_mean": y_mean_pb, "y_std": y_std_pb, "history": hist_pb,
    }, PHOBERT_V6_PATH)
    print(f"  Saved: {PHOBERT_V6_PATH.name}")

# %% Phase 2: Evaluate
pred_pb_val = predict_phobert(model_phobert, phobert_enc_val, y_mean_pb, y_std_pb, DEVICE)
pred_pb_test = predict_phobert(model_phobert, phobert_enc_test, y_mean_pb, y_std_pb, DEVICE)
ALL_PREDS_VAL["v6-PhoBERT"] = pred_pb_val
ALL_PREDS_TEST["v6-PhoBERT"] = pred_pb_test

evaluate_and_store(test_prices, pred_pb_test, "v6-PhoBERT: full fine-tune (20ep)", test_names)
if hist_pb:
    plot_phobert_history(hist_pb, "v6: PhoBERT Full Fine-tune (20 epochs)")


# ============================================================
# PHASE 3: PhoBERT EMBEDDING -> PCA -> LightGBM + Optuna
# ============================================================

# %% [markdown]
# ## Phase 3: PhoBERT Embedding -> PCA(256) -> LightGBM + Optuna
#
# Extract mean-pooled embeddings from v6 PhoBERT, reduce to 256d with PCA,
# concat with category, then train LightGBM with Optuna hyperparameter search.

# %% Phase 3: Extract PhoBERT embeddings
print("\n" + "#" * 60)
print("# Phase 3: PhoBERT embed -> PCA(256) -> LGB + Optuna")
print("#" * 60)

PHOBERT_EMB_CACHE = {
    "train": WEIGHTS_V6 / "phobert_emb_train.npy",
    "val": WEIGHTS_V6 / "phobert_emb_val.npy",
    "test": WEIGHTS_V6 / "phobert_emb_test.npy",
}

def extract_phobert_embeddings(model, encodings, cache_path, device, batch_size=64):
    if cache_path.exists():
        print(f"  Loading cache: {cache_path.name}")
        return np.load(cache_path)

    model.eval()
    ids = encodings["input_ids"]
    mask = encodings["attention_mask"]
    embeddings = []

    print(f"  Extracting embeddings ({len(ids):,} items)...")
    with torch.no_grad():
        for i in range(0, len(ids), batch_size):
            b_ids = ids[i:i+batch_size].to(device)
            b_mask = mask[i:i+batch_size].to(device)
            emb = model.extract_embeddings(b_ids, b_mask)
            embeddings.append(emb.cpu().numpy())

    embeddings = np.concatenate(embeddings).astype(np.float32)
    np.save(cache_path, embeddings)
    print(f"  Saved: {cache_path.name} shape={embeddings.shape}")
    return embeddings

phobert_emb_train = extract_phobert_embeddings(
    model_phobert, phobert_enc_train, PHOBERT_EMB_CACHE["train"], DEVICE
)
phobert_emb_val = extract_phobert_embeddings(
    model_phobert, phobert_enc_val, PHOBERT_EMB_CACHE["val"], DEVICE
)
phobert_emb_test = extract_phobert_embeddings(
    model_phobert, phobert_enc_test, PHOBERT_EMB_CACHE["test"], DEVICE
)
print(f"  Embeddings: train={phobert_emb_train.shape} val={phobert_emb_val.shape}")

# Free PhoBERT from GPU
model_phobert.cpu()
torch.cuda.empty_cache()

# %% Phase 3: PCA + LGB + Optuna
print("\n--- PCA 768d -> 256d ---")
PCA_CACHE = WEIGHTS_V6 / "pca_256.pkl"
if PCA_CACHE.exists():
    pca = joblib.load(PCA_CACHE)
    print(f"  Loaded PCA: {PCA_CACHE.name}")
else:
    pca = PCA(n_components=256, random_state=SEED)
    pca.fit(phobert_emb_train)
    joblib.dump(pca, PCA_CACHE)
    print(f"  Fitted PCA: variance retained = {pca.explained_variance_ratio_.sum():.2%}")

pca_train = pca.transform(phobert_emb_train).astype(np.float32)
pca_val = pca.transform(phobert_emb_val).astype(np.float32)
pca_test = pca.transform(phobert_emb_test).astype(np.float32)

# Concat with category
cat_train_dense = cat_train.toarray().astype(np.float32)
cat_val_dense = cat_val.toarray().astype(np.float32)
cat_test_dense = cat_test.toarray().astype(np.float32)

X_pca_train = np.hstack([pca_train, cat_train_dense])
X_pca_val = np.hstack([pca_val, cat_val_dense])
X_pca_test = np.hstack([pca_test, cat_test_dense])
print(f"  Features: {X_pca_train.shape[1]} (256 PCA + {cat_train_dense.shape[1]} cat)")

y_train_log = np.log1p(train_prices)
y_val_log = np.log1p(val_prices)

print("\n--- LightGBM + Optuna (50 trials) ---")
LGB_V6_PATH = WEIGHTS_V6 / "lgb_v6_phobert_pca.pkl"
LGB_V6_PARAMS_PATH = WEIGHTS_V6 / "lgb_v6_best_params.json"

if LGB_V6_PATH.exists():
    lgb_v6 = joblib.load(LGB_V6_PATH)
    print(f"  Loaded: {LGB_V6_PATH.name}")
else:
    def objective_v6(trial):
        params = {
            "num_leaves": trial.suggest_int("num_leaves", 50, 300),
            "min_child_samples": trial.suggest_int("min_child_samples", 20, 100),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "bagging_freq": 5,
            "lambda_l1": trial.suggest_float("lambda_l1", 1e-3, 10.0, log=True),
            "lambda_l2": trial.suggest_float("lambda_l2", 1e-3, 10.0, log=True),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "n_estimators": 1500,
            "random_state": SEED,
            "n_jobs": 6,
            "verbose": -1,
        }
        m = lgb.LGBMRegressor(**params)
        m.fit(
            X_pca_train, y_train_log,
            eval_set=[(X_pca_val, y_val_log)],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
        )
        pred = np.clip(np.expm1(m.predict(X_pca_val)), 0, None)
        return rmsle(val_prices, pred)

    t0 = time.time()
    study = optuna.create_study(direction="minimize")
    study.optimize(objective_v6, n_trials=50, show_progress_bar=True)
    print(f"  Optuna done ({time.time()-t0:.0f}s): best val RMSLE={study.best_value:.4f}")
    print(f"  Best params: {study.best_params}")

    best_params = {
        **study.best_params,
        "bagging_freq": 5,
        "n_estimators": 1500,
        "random_state": SEED,
        "n_jobs": 6,
        "verbose": -1,
    }
    with open(LGB_V6_PARAMS_PATH, "w") as f:
        json.dump(study.best_params, f, indent=2)

    lgb_v6 = lgb.LGBMRegressor(**best_params)
    lgb_v6.fit(
        X_pca_train, y_train_log,
        eval_set=[(X_pca_val, y_val_log)],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )
    joblib.dump(lgb_v6, LGB_V6_PATH)
    print(f"  Saved: {LGB_V6_PATH.name}")

# %% Phase 3: Evaluate
pred_lgb_val = np.clip(np.expm1(lgb_v6.predict(X_pca_val)), 0, None)
pred_lgb_test = np.clip(np.expm1(lgb_v6.predict(X_pca_test)), 0, None)
ALL_PREDS_VAL["v6-PCA+LGB"] = pred_lgb_val
ALL_PREDS_TEST["v6-PCA+LGB"] = pred_lgb_test

evaluate_and_store(test_prices, pred_lgb_test, "v6-PCA+LGB: PhoBERT embed+PCA+LGB", test_names)


# ============================================================
# PHASE 4: FRONTIER LLM ZERO-SHOT (200 items)
# ============================================================

# %% [markdown]
# ## Phase 4: Frontier LLM Zero-shot (200 items)
#
# Test 3 OpenAI models on 200 random test items:
# - gpt-4o-mini
# - gpt-5-nano
# - gpt-5-mini

# %% Phase 4: Frontier LLM
print("\n" + "#" * 60)
print("# Phase 4: Frontier LLM Zero-shot (200 items)")
print("#" * 60)

from dotenv import load_dotenv
from litellm import completion
from pricer_vi.evaluator import evaluate

load_dotenv(override=True)
LLM_SIZE = 200
LLM_WORKERS = 3

SYSTEM_PROMPT = (
    "You are a price estimation expert for Vietnamese e-commerce products. "
    "Estimate the price in VND based on the product description. "
    "Respond with ONLY the number (integer), no currency symbol, no explanation."
)

def messages_for(item):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": item.summary},
    ]

LLM_RESULTS_PATH = WEIGHTS_V6 / "frontier_llm_results.json"

if LLM_RESULTS_PATH.exists():
    print("Loading saved LLM results...")
    with open(LLM_RESULTS_PATH) as f:
        llm_results = json.load(f)
    for name, r in llm_results.items():
        print(f"  {name}: RMSLE={r['rmsle']:.4f} | MAE={r['mae']:,.0f} | MAPE={r['mape']:.1f}%")
        ALL_RESULTS[f"LLM: {name}"] = r
else:
    def make_llm_fn(model_name):
        def fn(item):
            response = completion(model=f"openai/{model_name}", messages=messages_for(item))
            return response.choices[0].message.content
        return fn

    llm_models = ["gpt-4o-mini", "gpt-5-nano", "gpt-5-mini"]
    llm_results = {}

    for model_name in llm_models:
        print(f"\n--- {model_name} ({LLM_SIZE} items) ---")
        r = evaluate(make_llm_fn(model_name), test_items, size=LLM_SIZE, workers=LLM_WORKERS)
        llm_results[model_name] = r
        ALL_RESULTS[f"LLM: {model_name}"] = r
        print(f"  RMSLE={r['rmsle']:.4f} | MAE={r['mae']:,.0f} | MAPE={r['mape']:.1f}%")

    with open(LLM_RESULTS_PATH, "w") as f:
        json.dump(llm_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {LLM_RESULTS_PATH}")


# ============================================================
# PHASE 5: BLENDING BEST MODELS
# ============================================================

# %% [markdown]
# ## Phase 5: Blending Best Models
#
# Candidates:
# - v6-PhoBERT (full fine-tune, 20 epochs)
# - v6-PCA+LGB (PhoBERT embed + LGB)
# - v4 Model 2b (AITeamVN + MLP) -- if weights available
# - v4 Model 0a (DNN + HashingVec) -- if weights available
# - Day 3 LGB Tuned C -- retrained

# %% Phase 5: Reload v4 models + retrain Day 3 LGB
print("\n" + "#" * 60)
print("# Phase 5: Blending Best Models")
print("#" * 60)

# --- Reload v4 Model 2b: AITeamVN+MLP ---
v4_2b_path = WEIGHTS_V4 / "model_2b_mlp_aiteamvn.pth"
if v4_2b_path.exists() and "train" in at_emb:
    print("\n--- Reload v4 Model 2b: AITeamVN+MLP ---")
    input_dim_2b = at_emb["train"].shape[1] + cat_train.shape[1]
    model_2b = MLP(input_dim_2b, hidden_sizes=(512, 256, 128))
    ckpt_2b = torch.load(v4_2b_path, map_location=DEVICE, weights_only=True)
    model_2b.load_state_dict(ckpt_2b["state_dict"])
    model_2b.to(DEVICE)

    X_2b_val = torch.FloatTensor(np.hstack([at_emb["val"], cat_val_dense]))
    X_2b_test = torch.FloatTensor(np.hstack([at_emb["test"], cat_test_dense]))

    pred_2b_val = predict_batch(model_2b, X_2b_val, ckpt_2b["y_mean"], ckpt_2b["y_std"], DEVICE)
    pred_2b_test = predict_batch(model_2b, X_2b_test, ckpt_2b["y_mean"], ckpt_2b["y_std"], DEVICE)
    ALL_PREDS_VAL["v4-2b"] = pred_2b_val
    ALL_PREDS_TEST["v4-2b"] = pred_2b_test
    print(f"  v4-2b test RMSLE: {rmsle(test_prices, pred_2b_test):.4f}")
    del model_2b
    torch.cuda.empty_cache()
else:
    print("  v4 Model 2b: SKIPPED (weights or embeddings not available)")

# --- Reload v4 Model 0a: DNN+HashingVec ---
v4_0a_path = WEIGHTS_V4 / "model_0a_dnn_hv2048.pth"
if v4_0a_path.exists():
    print("\n--- Reload v4 Model 0a: DNN+HashingVec ---")
    X_hv_val_cat = torch.FloatTensor(hstack([X_hv_val, cat_val]).toarray())
    X_hv_test_cat = torch.FloatTensor(hstack([X_hv_test, cat_test]).toarray())
    input_dim_0a = X_hv_test_cat.shape[1]

    model_0a = DeepNeuralNetwork(input_dim_0a, hidden_size=2048, num_layers=10)
    ckpt_0a = torch.load(v4_0a_path, map_location=DEVICE, weights_only=True)
    model_0a.load_state_dict(ckpt_0a["state_dict"])
    model_0a.to(DEVICE)

    pred_0a_val = predict_batch(model_0a, X_hv_val_cat, ckpt_0a["y_mean"], ckpt_0a["y_std"], DEVICE)
    pred_0a_test = predict_batch(model_0a, X_hv_test_cat, ckpt_0a["y_mean"], ckpt_0a["y_std"], DEVICE)
    ALL_PREDS_VAL["v4-0a"] = pred_0a_val
    ALL_PREDS_TEST["v4-0a"] = pred_0a_test
    print(f"  v4-0a test RMSLE: {rmsle(test_prices, pred_0a_test):.4f}")
    del model_0a, X_hv_val_cat, X_hv_test_cat
    torch.cuda.empty_cache()
else:
    print("  v4 Model 0a: SKIPPED (weights not available)")

# --- Retrain Day 3 LGB Tuned C ---
print("\n--- Retrain Day 3 LGB Tuned C ---")
# Reuse v5 cache if exists
LGB_DAY3_PATH_V5 = WEIGHTS_V5 / "lgb_day3_retrain.pkl"
LGB_DAY3_PATH_V6 = WEIGHTS_V6 / "lgb_day3_retrain.pkl"
LGB_DAY3_PATH = LGB_DAY3_PATH_V5 if LGB_DAY3_PATH_V5.exists() else LGB_DAY3_PATH_V6

DAY3_BEST_PARAMS = {
    "num_leaves": 199,
    "min_child_samples": 50,
    "feature_fraction": 0.545,
    "lambda_l1": 0.021,
    "lambda_l2": 0.190,
    "learning_rate": 0.038,
    "n_estimators": 1500,
    "random_state": SEED,
    "n_jobs": 6,
    "verbose": -1,
}

if LGB_DAY3_PATH.exists():
    lgb_day3 = joblib.load(LGB_DAY3_PATH)
    print(f"  Loaded: {LGB_DAY3_PATH}")
else:
    t0 = time.time()
    lgb_day3 = lgb.LGBMRegressor(**DAY3_BEST_PARAMS)
    lgb_day3.fit(X_cc_train, y_train_log)
    joblib.dump(lgb_day3, LGB_DAY3_PATH_V6)
    print(f"  Trained Day 3 LGB ({time.time()-t0:.1f}s)")

pred_day3_val = np.clip(np.expm1(lgb_day3.predict(X_cc_val)), 0, None)
pred_day3_test = np.clip(np.expm1(lgb_day3.predict(X_cc_test)), 0, None)
ALL_PREDS_VAL["Day3-LGB"] = pred_day3_val
ALL_PREDS_TEST["Day3-LGB"] = pred_day3_test
print(f"  Day3-LGB test RMSLE: {rmsle(test_prices, pred_day3_test):.4f}")

# %% Phase 5: Weighted blending (scipy.minimize on val set)
print("\n--- Weighted Blending ---")
blend_names = list(ALL_PREDS_VAL.keys())
blend_val = [ALL_PREDS_VAL[n] for n in blend_names]
blend_test = [ALL_PREDS_TEST[n] for n in blend_names]
n_models = len(blend_names)

print(f"  Blending {n_models} models: {blend_names}")
for name in blend_names:
    r = rmsle(test_prices, ALL_PREDS_TEST[name])
    print(f"    {name}: test RMSLE={r:.4f}")

def blend_objective(w):
    w = np.abs(w)
    w = w / w.sum()
    pred = sum(wi * p for wi, p in zip(w, blend_val))
    return rmsle(val_prices, pred)

x0 = np.ones(n_models) / n_models
res = scipy_minimize(blend_objective, x0=x0, method="Nelder-Mead",
                     options={"maxiter": 5000, "xatol": 1e-6, "fatol": 1e-6})
opt_w = np.abs(res.x)
opt_w = opt_w / opt_w.sum()

print(f"\n  Optimized weights (val RMSLE={res.fun:.4f}):")
for name, w in zip(blend_names, opt_w):
    print(f"    {name}: {w:.3f}")

# Apply to test
blended_test = sum(w * p for w, p in zip(opt_w, blend_test))
blended_val = sum(w * p for w, p in zip(opt_w, blend_val))
ALL_PREDS_VAL["v6 Blended"] = blended_val
ALL_PREDS_TEST["v6 Blended"] = blended_test

# %% Phase 5: Evaluate blend
evaluate_and_store(test_prices, blended_test, "v6: Blended ensemble", test_names)

# Save blend config
blend_config = {
    "models": blend_names,
    "weights": opt_w.tolist(),
    "val_rmsle": res.fun,
    "test_rmsle": ALL_RESULTS["v6: Blended ensemble"]["rmsle"],
}
with open(WEIGHTS_V6 / "blend_config.json", "w") as f:
    json.dump(blend_config, f, indent=2, ensure_ascii=False)
print(f"  Saved blend config: {WEIGHTS_V6 / 'blend_config.json'}")


# ============================================================
# PHASE 6: SUMMARY
# ============================================================

# %% [markdown]
# ## Phase 6: Summary + Comparison

# %% Final summary table + charts
print("\n\n" + "=" * 70)
print("FINAL RESULTS -- Day 4 v6")
print("=" * 70)

# Add baselines for comparison
ALL_RESULTS["Baseline: v5-old Blended"] = {
    "rmsle": 0.4191, "mae": 0, "mape": 0, "r2": 0,
}
ALL_RESULTS["Baseline: Day 3 Blended (TF-IDF)"] = {
    "rmsle": 0.5164, "mae": 109_725, "mape": 44.0, "r2": 47.1,
}
ALL_RESULTS["Baseline: v4 AITeamVN+MLP"] = {
    "rmsle": 0.4986, "mae": 99_786, "mape": 39.0, "r2": 55.3,
}

df = pd.DataFrame(ALL_RESULTS).T
df = df.sort_values("rmsle")
df.index.name = "Model"
print(df.to_string(
    formatters={
        "rmsle": "{:.4f}".format,
        "mae": "{:,.0f}".format,
        "mape": "{:.1f}%".format,
        "r2": "{:.1f}%".format,
    }
))

best_name = df.index[0]
best_rmsle = df.iloc[0]["rmsle"]
print(f"\nBest model: {best_name} (RMSLE={best_rmsle:.4f})")
print(f"vs v5-old Blended (0.4191): {(0.4191 - best_rmsle) / 0.4191 * 100:+.1f}%")
print(f"vs v4 best (0.4986):        {(0.4986 - best_rmsle) / 0.4986 * 100:+.1f}%")
print(f"vs Day 3 (0.5164):          {(0.5164 - best_rmsle) / 0.5164 * 100:+.1f}%")
print(f"vs Target (0.40):           {'ACHIEVED' if best_rmsle <= 0.40 else f'gap {best_rmsle - 0.40:.4f}'}")

# Save all results
with open(WEIGHTS_V6 / "v6_results.json", "w") as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False)
print(f"\nResults saved: {WEIGHTS_V6 / 'v6_results.json'}")

# %% RMSLE comparison bar chart
fig_rmsle = go.Figure()
colors = []
for r in df["rmsle"]:
    if r <= 0.40:
        colors.append("mediumseagreen")
    elif r < 0.45:
        colors.append("steelblue")
    elif r < 0.50:
        colors.append("orange")
    else:
        colors.append("lightcoral")

fig_rmsle.add_trace(go.Bar(
    x=df.index, y=df["rmsle"], marker_color=colors,
    text=[f"{v:.4f}" for v in df["rmsle"]], textposition="outside",
))
fig_rmsle.add_hline(y=0.4191, line_dash="dash", line_color="red",
                    annotation_text="v5-old Blended (0.4191)")
fig_rmsle.add_hline(y=0.4986, line_dash="dash", line_color="orange",
                    annotation_text="v4 Best (0.4986)")
fig_rmsle.add_hline(y=0.40, line_dash="dash", line_color="green",
                    annotation_text="Target (0.40)")
fig_rmsle.update_layout(
    title="Day 4 v6: RMSLE Comparison (lower is better)",
    xaxis_title="Model", yaxis_title="RMSLE",
    width=1100, height=550, template="plotly_white",
    xaxis_tickangle=-30,
)
fig_rmsle.show()

# %% Multi-metric comparison
fig_multi = make_subplots(
    rows=2, cols=2,
    subplot_titles=("RMSLE (lower=better)", "MAE in VND (lower=better)",
                    "MAPE % (lower=better)", "R2 % (higher=better)"),
)
fig_multi.add_trace(go.Bar(x=df.index, y=df["rmsle"], name="RMSLE",
                           marker_color="steelblue"), row=1, col=1)
fig_multi.add_trace(go.Bar(x=df.index, y=df["mae"], name="MAE",
                           marker_color="tomato"), row=1, col=2)
fig_multi.add_trace(go.Bar(x=df.index, y=df["mape"], name="MAPE",
                           marker_color="orange"), row=2, col=1)
fig_multi.add_trace(go.Bar(x=df.index, y=df["r2"], name="R2",
                           marker_color="mediumseagreen"), row=2, col=2)
fig_multi.update_layout(
    title="Day 4 v6: All Metrics Comparison",
    width=1200, height=700, template="plotly_white", showlegend=False,
)
fig_multi.update_xaxes(tickangle=-30)
fig_multi.show()

print("\n--- Day 4 v6 COMPLETE ---")
print(f"Weights saved in: {WEIGHTS_V6}")
print("Files:", [f.name for f in WEIGHTS_V6.iterdir()])
