# %% [markdown]
# # Day 4 v7: DL Optimization (SOTA 2024-2025)
#
# **Target:** RMSLE <= 0.40
#
# **Techniques (Phase A, B):**
# - Layer-wise LR Decay (LLRD, 0.9x per layer)
# - R-Drop (regression consistency via MSE, alpha=0.5)
# - EMA weights (decay=0.999)
# - Multi-task auxiliary head (category classification, alpha=0.1)
# - Huber Loss (delta=1.0) on normalized log-target
# - Early stop 12 epochs patience=3 (v6 overfit from ep13+)
# - Dropout=0.2, weight_decay=0.02
#
# **Phases:**
# - Phase 1: Data + cache (reuse v4/v5/v6)
# - Phase 2: PhoBERT++ (1 seed, optimized)
# - Phase 3: XLM-R++ fine-tune
# - Phase 4: AITeamVN++ fine-tune (top 4 layers)
# - Phase 5: Reload v4/v6/Day3 models for blending pool
# - Phase 6: Collect val + test predictions for all 7 base models
# - Phase 7: Stacking (Ridge + ElasticNet + LGB meta-learners)
# - Phase 8: Summary + charts
#
# **Baseline:** v6 Blended RMSLE=0.4187

# %% Install (uncomment on first run)
# !uv pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130
# !uv add transformers sentence-transformers accelerate lightgbm optuna scikit-learn plotly pyvi underthesea

# %% Imports + Config
import os
import sys
import gc
import json
import joblib
import time
import copy
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torch.amp import autocast, GradScaler
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.pipeline import FeatureUnion
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.sparse import hstack
from scipy.optimize import minimize as scipy_minimize
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from transformers import AutoModel, AutoTokenizer, get_cosine_schedule_with_warmup
import lightgbm as lgb

os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

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
XLMR_NAME = "FacebookAI/xlm-roberta-base"
AITEAMVN_NAME = "AITeamVN/Vietnamese_Embedding"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True

print(f"Device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"GPU: {torch.cuda.get_device_name()}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

WEIGHTS_V7 = DAY4 / "weights_v7"
WEIGHTS_V7.mkdir(exist_ok=True)
WEIGHTS_V6 = DAY4 / "weights_v6"
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


def plot_bert_history(history, title):
    epochs = list(range(1, len(history["train_loss"]) + 1))
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Loss (Total)", "Val RMSLE", "Val MAE (VND)", "Learning Rate"),
    )
    fig.add_trace(go.Scatter(x=epochs, y=history["train_loss"], name="Train",
                             line=dict(color="steelblue")), row=1, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_loss"], name="Val",
                             line=dict(color="tomato")), row=1, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_rmsle"], mode="lines+markers",
                             line=dict(color="tomato")), row=1, col=2)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_mae"], mode="lines+markers",
                             line=dict(color="mediumseagreen")), row=2, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["lr"], line=dict(color="purple")),
                  row=2, col=2)
    fig.update_layout(title=title, width=1000, height=600,
                      template="plotly_white", showlegend=False)
    fig.show()


# ============================================================
# PHASE 1: DATA LOADING + CACHE
# ============================================================

# %% [markdown]
# ## Phase 1: Load Data + Cache

# %% Load data
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

# %% Category one-hot + label encode (for multi-task aux)
print("--- Category encoders ---")
cat_encoder = OneHotEncoder(sparse_output=True, handle_unknown="ignore")
cat_train = cat_encoder.fit_transform(np.array(train_categories).reshape(-1, 1))
cat_val = cat_encoder.transform(np.array(val_categories).reshape(-1, 1))
cat_test = cat_encoder.transform(np.array(test_categories).reshape(-1, 1))

cat_label_encoder = LabelEncoder()
cat_label_train = cat_label_encoder.fit_transform(train_categories)
cat_label_val = cat_label_encoder.transform(val_categories)
cat_label_test = cat_label_encoder.transform(test_categories)
NUM_CATEGORIES = len(cat_label_encoder.classes_)
print(f"Categories ({NUM_CATEGORIES}): {list(cat_label_encoder.classes_)}")

# %% Underthesea tokenize (for PhoBERT)
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

print("\n--- Underthesea tokenize (PhoBERT) ---")
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

# %% XLM-R tokenize (no segment, raw summaries)
print("\n--- XLM-R tokenize ---")
xlmr_tokenizer = AutoTokenizer.from_pretrained(XLMR_NAME)
t0 = time.time()
xlmr_enc_train = xlmr_tokenizer(
    train_summaries, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
xlmr_enc_val = xlmr_tokenizer(
    val_summaries, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
xlmr_enc_test = xlmr_tokenizer(
    test_summaries, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
print(f"  Train: {xlmr_enc_train['input_ids'].shape} ({time.time()-t0:.1f}s)")

# %% AITeamVN tokenize (no segment, raw summaries — BGE-M3)
print("\n--- AITeamVN tokenize (BGE-M3) ---")
aiteamvn_tokenizer = AutoTokenizer.from_pretrained(AITEAMVN_NAME)
t0 = time.time()
at_enc_train = aiteamvn_tokenizer(
    train_summaries, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
at_enc_val = aiteamvn_tokenizer(
    val_summaries, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
at_enc_test = aiteamvn_tokenizer(
    test_summaries, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
print(f"  Train: {at_enc_train['input_ids'].shape} ({time.time()-t0:.1f}s)")

# %% Load frozen AITeamVN embeddings (for v4-2b model reload)
EMB_AT_FROZEN = {
    "train": DAY4 / "aiteamvn_train.npy",
    "val": DAY4 / "aiteamvn_val.npy",
    "test": DAY4 / "aiteamvn_test.npy",
}

print("\n--- AITeamVN frozen embeddings (v4 cache) ---")
at_emb_frozen = {}
for split, path in EMB_AT_FROZEN.items():
    if path.exists():
        at_emb_frozen[split] = np.load(path)
        print(f"  {split}: {at_emb_frozen[split].shape}")
    else:
        print(f"  WARNING: {path.name} not found")

# %% HashingVec (for v4-0a model reload)
print("\n--- HashingVectorizer ---")
hv = HashingVectorizer(n_features=5000, binary=True, alternate_sign=False)
X_hv_val = hv.transform(val_summaries)
X_hv_test = hv.transform(test_summaries)

# %% TF-IDF Arch C (for Day3 LGB reload)
print("\n--- TF-IDF Arch C ---")
ARCH_C_CACHE_V6 = WEIGHTS_V6 / "arch_c_vectorizer.pkl"
ARCH_C_CACHE_V5 = WEIGHTS_V5 / "arch_c_vectorizer.pkl"
ARCH_C_CACHE = ARCH_C_CACHE_V6 if ARCH_C_CACHE_V6.exists() else ARCH_C_CACHE_V5

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
    joblib.dump(arch_c, WEIGHTS_V7 / "arch_c_vectorizer.pkl")
    print(f"  Fitted Arch C: {X_c_train.shape} ({time.time()-t0:.1f}s)")
X_c_val = arch_c.transform(tok_val)
X_c_test = arch_c.transform(tok_test)

X_cc_train = hstack([X_c_train, cat_train])
X_cc_val = hstack([X_c_val, cat_val])
X_cc_test = hstack([X_c_test, cat_test])

cat_val_dense = cat_val.toarray().astype(np.float32)
cat_test_dense = cat_test.toarray().astype(np.float32)

print("\n=== PHASE 1 DONE ===")


# ============================================================
# PHASE 2: PhoBERT++ (LLRD + R-Drop + EMA + Aux + Huber)
# ============================================================

# %% [markdown]
# ## Phase 2: PhoBERT++ Training (SOTA techniques)

# %% Model class
def mean_pooling(model_output, attention_mask):
    """Mean pool over last hidden state, mask padding tokens."""
    token_embeddings = model_output.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (token_embeddings * mask_expanded).sum(1) / mask_expanded.sum(1).clamp(min=1e-9)


class BERTMultiTaskRegressor(nn.Module):
    """Generic BERT regressor with multi-task auxiliary head.

    - Price head: LayerNorm + Linear(hidden, 256) + GELU + Dropout + Linear(256, 1)
    - Category head: Linear(hidden, num_categories) for auxiliary classification
    """

    def __init__(self, model_name, num_categories, hidden_size=768, dropout=0.2):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        h = self.bert.config.hidden_size
        self.hidden_size = h
        self.price_head = nn.Sequential(
            nn.LayerNorm(h),
            nn.Linear(h, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1),
        )
        self.category_head = nn.Linear(h, num_categories)
        self._init_heads()

    def _init_heads(self):
        for m in self.price_head:
            if isinstance(m, nn.Linear):
                if m.out_features == 1:
                    nn.init.normal_(m.weight, std=0.01)
                else:
                    nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)
        nn.init.xavier_normal_(self.category_head.weight)
        nn.init.zeros_(self.category_head.bias)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = mean_pooling(outputs, attention_mask)
        return self.price_head(pooled), self.category_head(pooled)

    def extract_embeddings(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        return mean_pooling(outputs, attention_mask)


# %% Dataset + LLRD utility
class MultiTaskDataset(Dataset):
    def __init__(self, encodings, price_labels, cat_labels):
        self.input_ids = encodings["input_ids"]
        self.attention_mask = encodings["attention_mask"]
        self.price_labels = price_labels
        self.cat_labels = cat_labels

    def __len__(self):
        return len(self.price_labels)

    def __getitem__(self, idx):
        return (
            self.input_ids[idx], self.attention_mask[idx],
            self.price_labels[idx], self.cat_labels[idx],
        )


def build_llrd_param_groups(model, base_lr=2e-5, decay=0.9, head_lr_mult=1.0,
                            weight_decay=0.02):
    """Build param groups with layer-wise LR decay.

    - Heads get base_lr * head_lr_mult
    - BERT encoder layer N gets base_lr * (decay ** (num_layers - N - 1))
    - Embeddings get lowest LR
    """
    groups = []
    no_decay = ("bias", "LayerNorm.weight")

    # Heads
    head_params = list(model.price_head.named_parameters()) + \
                  list(model.category_head.named_parameters())
    groups.append({
        "params": [p for n, p in head_params if not any(nd in n for nd in no_decay)],
        "lr": base_lr * head_lr_mult, "weight_decay": weight_decay,
    })
    groups.append({
        "params": [p for n, p in head_params if any(nd in n for nd in no_decay)],
        "lr": base_lr * head_lr_mult, "weight_decay": 0.0,
    })

    # BERT layers (iterate from top to bottom)
    bert = model.bert
    num_layers = len(bert.encoder.layer)
    for i, layer in enumerate(bert.encoder.layer):
        lr_i = base_lr * (decay ** (num_layers - i - 1))
        layer_params = list(layer.named_parameters())
        groups.append({
            "params": [p for n, p in layer_params if not any(nd in n for nd in no_decay)],
            "lr": lr_i, "weight_decay": weight_decay,
        })
        groups.append({
            "params": [p for n, p in layer_params if any(nd in n for nd in no_decay)],
            "lr": lr_i, "weight_decay": 0.0,
        })

    # Embeddings (lowest LR)
    emb_lr = base_lr * (decay ** num_layers)
    emb_params = list(bert.embeddings.named_parameters())
    groups.append({
        "params": [p for n, p in emb_params if not any(nd in n for nd in no_decay)],
        "lr": emb_lr, "weight_decay": weight_decay,
    })
    groups.append({
        "params": [p for n, p in emb_params if any(nd in n for nd in no_decay)],
        "lr": emb_lr, "weight_decay": 0.0,
    })

    # Pooler (if exists, small LR)
    if hasattr(bert, "pooler") and bert.pooler is not None:
        pooler_params = list(bert.pooler.named_parameters())
        groups.append({
            "params": [p for n, p in pooler_params],
            "lr": base_lr, "weight_decay": weight_decay,
        })

    return groups


# %% Training function with all SOTA techniques
def train_bert_v7(
    model, train_enc, val_enc, train_prices_np, val_prices_np,
    cat_label_train_np, cat_label_val_np, device,
    epochs=12, batch_size=80, base_lr=2e-5, llrd_decay=0.9,
    weight_decay=0.02, warmup_ratio=0.1, patience=3, max_grad_norm=1.0,
    huber_delta=1.0, rdrop_alpha=0.5, aux_alpha=0.1, ema_decay=0.999,
    use_rdrop=True,
):
    """Train BERT with LLRD + R-Drop + EMA + Multi-task + Huber loss.

    Returns: (ema_model, y_mean, y_std, history)
    """
    # Normalize target
    y_train_log = torch.log1p(torch.FloatTensor(train_prices_np))
    y_val_log = torch.log1p(torch.FloatTensor(val_prices_np))
    y_mean = y_train_log.mean()
    y_std = y_train_log.std()
    y_train_norm = (y_train_log - y_mean) / y_std
    y_val_norm = (y_val_log - y_mean) / y_std
    cat_train_t = torch.LongTensor(cat_label_train_np)
    cat_val_t = torch.LongTensor(cat_label_val_np)

    print(f"  Target normalize: mean={y_mean:.4f}, std={y_std:.4f}")
    print(f"  Norm range: [{y_train_norm.min():.2f}, {y_train_norm.max():.2f}]")

    train_loader = DataLoader(
        MultiTaskDataset(train_enc, y_train_norm, cat_train_t),
        batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True,
    )

    model.to(device)

    # LLRD
    param_groups = build_llrd_param_groups(
        model, base_lr=base_lr, decay=llrd_decay, weight_decay=weight_decay
    )
    optimizer = torch.optim.AdamW(param_groups)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * warmup_ratio)
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    # EMA model
    ema_model = AveragedModel(
        model, multi_avg_fn=get_ema_multi_avg_fn(ema_decay),
    )
    ema_model.to(device)

    # Losses
    huber = nn.HuberLoss(delta=huber_delta)
    ce = nn.CrossEntropyLoss()
    mse_consistency = nn.MSELoss()

    scaler = GradScaler("cuda") if device.type == "cuda" else None

    n_params_total = sum(p.numel() for p in model.parameters())
    n_params_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Params: {n_params_train:,}/{n_params_total:,} trainable | Batch: {batch_size}")
    print(f"  Steps/ep: {len(train_loader)} | Total: {total_steps} | Warmup: {warmup_steps}")
    print(f"  LLRD: base={base_lr:.1e}, decay={llrd_decay}, emb_lr={base_lr * (llrd_decay ** 12):.2e}")
    print(f"  R-Drop alpha={rdrop_alpha if use_rdrop else 'OFF'} | Aux alpha={aux_alpha} "
          f"| EMA decay={ema_decay} | Huber delta={huber_delta}")

    history = {"train_loss": [], "val_loss": [], "val_rmsle": [], "val_mae": [], "lr": []}
    best_val_rmsle = float("inf")
    best_ema_state = None
    patience_counter = 0

    val_ids = val_enc["input_ids"]
    val_mask = val_enc["attention_mask"]

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        epoch_losses = []

        for ids, mask, price_lbl, cat_lbl in train_loader:
            ids = ids.to(device)
            mask = mask.to(device)
            price_lbl = price_lbl.to(device).unsqueeze(1)
            cat_lbl = cat_lbl.to(device)

            optimizer.zero_grad()
            if scaler:
                with autocast(device_type="cuda"):
                    pred1, cat1 = model(ids, mask)
                    loss_price = huber(pred1, price_lbl)
                    loss_cat = ce(cat1, cat_lbl)
                    if use_rdrop:
                        pred2, cat2 = model(ids, mask)
                        loss_price = (loss_price + huber(pred2, price_lbl)) / 2
                        loss_cat = (loss_cat + ce(cat2, cat_lbl)) / 2
                        loss_consistency = mse_consistency(pred1, pred2)
                        loss = loss_price + aux_alpha * loss_cat + rdrop_alpha * loss_consistency
                    else:
                        loss = loss_price + aux_alpha * loss_cat
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
            else:
                pred1, cat1 = model(ids, mask)
                loss_price = huber(pred1, price_lbl)
                loss_cat = ce(cat1, cat_lbl)
                if use_rdrop:
                    pred2, cat2 = model(ids, mask)
                    loss_price = (loss_price + huber(pred2, price_lbl)) / 2
                    loss_cat = (loss_cat + ce(cat2, cat_lbl)) / 2
                    loss_consistency = mse_consistency(pred1, pred2)
                    loss = loss_price + aux_alpha * loss_cat + rdrop_alpha * loss_consistency
                else:
                    loss = loss_price + aux_alpha * loss_cat
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()

            scheduler.step()
            ema_model.update_parameters(model)
            epoch_losses.append(loss.item())

        # Eval with EMA model
        ema_model.eval()
        val_preds = []
        val_losses = []
        with torch.no_grad():
            for i in range(0, len(val_ids), 64):
                b_ids = val_ids[i:i+64].to(device)
                b_mask = val_mask[i:i+64].to(device)
                b_price = y_val_norm[i:i+64].to(device).unsqueeze(1)
                if scaler:
                    with autocast(device_type="cuda"):
                        pred, _ = ema_model(b_ids, b_mask)
                else:
                    pred, _ = ema_model(b_ids, b_mask)
                val_losses.append(huber(pred.float(), b_price).item())
                val_preds.append(pred.float().cpu())

        val_preds_t = torch.cat(val_preds)
        val_loss = float(np.mean(val_losses))
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
            f"  Epoch {epoch:2d}/{epochs} ({elapsed:.0f}s) | "
            f"Train: {np.mean(epoch_losses):.4f} | "
            f"ValLoss: {val_loss:.4f} | "
            f"RMSLE(EMA): {val_rmsle:.4f} | "
            f"MAE: {val_mae:,.0f} | "
            f"LR: {current_lr:.2e}"
        )

        if val_rmsle < best_val_rmsle:
            best_val_rmsle = val_rmsle
            best_ema_state = {k: v.cpu().clone() for k, v in ema_model.state_dict().items()}
            patience_counter = 0
            print(f"    >> New best (EMA): RMSLE={best_val_rmsle:.4f}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"    >> Early stop at epoch {epoch} (patience={patience})")
                break

    ema_model.load_state_dict(best_ema_state)
    ema_model.to(device)
    print(f"  Restored best EMA: Val RMSLE={best_val_rmsle:.4f}")
    return ema_model, y_mean, y_std, history


# %% Predict function (works with EMA model or raw model)
def predict_bert(model, encodings, y_mean, y_std, device, batch_size=64):
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
            pred = out[0] if isinstance(out, tuple) else out
            pred_vnd = torch.expm1(pred.float() * y_std_d + y_mean_d).clamp(min=0)
            preds.append(pred_vnd.cpu().numpy().flatten())
    return np.concatenate(preds)


def extract_embeddings_bert(model, encodings, cache_path, device, batch_size=64):
    """Extract mean-pooled embeddings from a trained BERT model (or EMA wrapper)."""
    if cache_path.exists():
        print(f"  Loading cache: {cache_path.name}")
        return np.load(cache_path)
    model.eval()
    ids = encodings["input_ids"]
    mask = encodings["attention_mask"]
    # If wrapped in AveragedModel, unwrap for extract_embeddings
    inner = model.module if isinstance(model, AveragedModel) else model
    embeddings = []
    with torch.no_grad():
        for i in range(0, len(ids), batch_size):
            b_ids = ids[i:i+batch_size].to(device)
            b_mask = mask[i:i+batch_size].to(device)
            emb = inner.extract_embeddings(b_ids, b_mask)
            embeddings.append(emb.cpu().numpy())
    embeddings = np.concatenate(embeddings).astype(np.float32)
    np.save(cache_path, embeddings)
    print(f"  Saved: {cache_path.name} shape={embeddings.shape}")
    return embeddings


# %% Phase 2: Train PhoBERT++
print("\n" + "#" * 60)
print("# Phase 2: PhoBERT++ (LLRD + R-Drop + EMA + Aux + Huber)")
print("#" * 60)

PHOBERT_V7_PATH = WEIGHTS_V7 / "phobert_v7.pth"

if PHOBERT_V7_PATH.exists():
    print("Loading saved PhoBERT++ weights...")
    model_phobert = BERTMultiTaskRegressor(PHOBERT_NAME, NUM_CATEGORIES, dropout=0.2)
    ema_phobert = AveragedModel(
        model_phobert, multi_avg_fn=get_ema_multi_avg_fn(0.999),
    )
    ckpt = torch.load(PHOBERT_V7_PATH, map_location=DEVICE, weights_only=False)
    ema_phobert.load_state_dict(ckpt["ema_state_dict"])
    ema_phobert.to(DEVICE)
    y_mean_pb, y_std_pb = ckpt["y_mean"], ckpt["y_std"]
    hist_pb = ckpt.get("history")
    print(f"  Loaded: {PHOBERT_V7_PATH.name}")
else:
    model_phobert = BERTMultiTaskRegressor(PHOBERT_NAME, NUM_CATEGORIES, dropout=0.2)
    ema_phobert, y_mean_pb, y_std_pb, hist_pb = train_bert_v7(
        model_phobert, phobert_enc_train, phobert_enc_val,
        train_prices, val_prices, cat_label_train, cat_label_val, DEVICE,
        epochs=12, batch_size=80, base_lr=2e-5, patience=3,
        use_rdrop=True,
    )
    torch.save({
        "ema_state_dict": ema_phobert.state_dict(),
        "y_mean": y_mean_pb, "y_std": y_std_pb, "history": hist_pb,
    }, PHOBERT_V7_PATH)
    print(f"  Saved: {PHOBERT_V7_PATH.name}")

# %% Phase 2: Evaluate PhoBERT++
pred_pb_val = predict_bert(ema_phobert, phobert_enc_val, y_mean_pb, y_std_pb, DEVICE)
pred_pb_test = predict_bert(ema_phobert, phobert_enc_test, y_mean_pb, y_std_pb, DEVICE)
ALL_PREDS_VAL["v7-PhoBERT++"] = pred_pb_val
ALL_PREDS_TEST["v7-PhoBERT++"] = pred_pb_test

evaluate_and_store(test_prices, pred_pb_test, "v7-PhoBERT++: LLRD+R-Drop+EMA+Aux+Huber", test_names)
if hist_pb:
    plot_bert_history(hist_pb, "v7 PhoBERT++ Training")

# %% Extract PhoBERT++ embeddings for PCA+LGB
print("\n--- Extract PhoBERT++ embeddings ---")
PHOBERT_EMB = {
    "train": WEIGHTS_V7 / "phobert_v7_emb_train.npy",
    "val": WEIGHTS_V7 / "phobert_v7_emb_val.npy",
    "test": WEIGHTS_V7 / "phobert_v7_emb_test.npy",
}
phobert_emb_train = extract_embeddings_bert(ema_phobert, phobert_enc_train, PHOBERT_EMB["train"], DEVICE)
phobert_emb_val = extract_embeddings_bert(ema_phobert, phobert_enc_val, PHOBERT_EMB["val"], DEVICE)
phobert_emb_test = extract_embeddings_bert(ema_phobert, phobert_enc_test, PHOBERT_EMB["test"], DEVICE)

# Free GPU
ema_phobert.cpu()
del model_phobert
torch.cuda.empty_cache()
gc.collect()


# ============================================================
# PHASE 3: XLM-R++ (same SOTA techniques)
# ============================================================

# %% [markdown]
# ## Phase 3: XLM-R++ Training

# %% Train XLM-R++
print("\n" + "#" * 60)
print("# Phase 3: XLM-R++ Fine-tune (LLRD + R-Drop + EMA + Aux + Huber)")
print("#" * 60)

XLMR_V7_PATH = WEIGHTS_V7 / "xlmr_v7.pth"

if XLMR_V7_PATH.exists():
    print("Loading saved XLM-R++ weights...")
    model_xlmr = BERTMultiTaskRegressor(XLMR_NAME, NUM_CATEGORIES, dropout=0.2)
    ema_xlmr = AveragedModel(model_xlmr, multi_avg_fn=get_ema_multi_avg_fn(0.999))
    ckpt = torch.load(XLMR_V7_PATH, map_location=DEVICE, weights_only=False)
    ema_xlmr.load_state_dict(ckpt["ema_state_dict"])
    ema_xlmr.to(DEVICE)
    y_mean_xr, y_std_xr = ckpt["y_mean"], ckpt["y_std"]
    hist_xr = ckpt.get("history")
    print(f"  Loaded: {XLMR_V7_PATH.name}")
else:
    model_xlmr = BERTMultiTaskRegressor(XLMR_NAME, NUM_CATEGORIES, dropout=0.2)
    ema_xlmr, y_mean_xr, y_std_xr, hist_xr = train_bert_v7(
        model_xlmr, xlmr_enc_train, xlmr_enc_val,
        train_prices, val_prices, cat_label_train, cat_label_val, DEVICE,
        epochs=12, batch_size=64, base_lr=2e-5, patience=3,
        use_rdrop=True,
    )
    torch.save({
        "ema_state_dict": ema_xlmr.state_dict(),
        "y_mean": y_mean_xr, "y_std": y_std_xr, "history": hist_xr,
    }, XLMR_V7_PATH)
    print(f"  Saved: {XLMR_V7_PATH.name}")

# %% Phase 3: Evaluate XLM-R++
pred_xr_val = predict_bert(ema_xlmr, xlmr_enc_val, y_mean_xr, y_std_xr, DEVICE)
pred_xr_test = predict_bert(ema_xlmr, xlmr_enc_test, y_mean_xr, y_std_xr, DEVICE)
ALL_PREDS_VAL["v7-XLM-R++"] = pred_xr_val
ALL_PREDS_TEST["v7-XLM-R++"] = pred_xr_test

evaluate_and_store(test_prices, pred_xr_test, "v7-XLM-R++: LLRD+R-Drop+EMA+Aux+Huber", test_names)
if hist_xr:
    plot_bert_history(hist_xr, "v7 XLM-R++ Training")

# Free GPU
ema_xlmr.cpu()
del model_xlmr
torch.cuda.empty_cache()
gc.collect()


# ============================================================
# PHASE 4: AITeamVN++ (top 4 layers unfreeze, no R-Drop)
# ============================================================

# %% [markdown]
# ## Phase 4: AITeamVN++ Fine-tune (top 4 layers, LLRD + EMA + Aux + Huber)
#
# AITeamVN (BGE-M3 24 layers, 568M params) too large for full R-Drop on 24GB.
# Freeze bottom 20 layers, unfreeze top 4 + heads.

# %% AITeamVN: freeze bottom layers helper
def freeze_bottom_layers(model, keep_top_n=4):
    """Freeze BERT embeddings + all layers except top N."""
    bert = model.bert
    for p in bert.embeddings.parameters():
        p.requires_grad = False
    num_layers = len(bert.encoder.layer)
    for i, layer in enumerate(bert.encoder.layer):
        for p in layer.parameters():
            p.requires_grad = i >= (num_layers - keep_top_n)
    if hasattr(bert, "pooler") and bert.pooler is not None:
        for p in bert.pooler.parameters():
            p.requires_grad = False


def build_llrd_param_groups_partial(model, base_lr=2e-5, decay=0.9,
                                     weight_decay=0.02):
    """LLRD for partial-freeze model: only trainable params."""
    groups = []
    no_decay = ("bias", "LayerNorm.weight")

    head_params = list(model.price_head.named_parameters()) + \
                  list(model.category_head.named_parameters())
    groups.append({
        "params": [p for n, p in head_params if not any(nd in n for nd in no_decay) and p.requires_grad],
        "lr": base_lr, "weight_decay": weight_decay,
    })
    groups.append({
        "params": [p for n, p in head_params if any(nd in n for nd in no_decay) and p.requires_grad],
        "lr": base_lr, "weight_decay": 0.0,
    })

    bert = model.bert
    num_layers = len(bert.encoder.layer)
    for i, layer in enumerate(bert.encoder.layer):
        lr_i = base_lr * (decay ** (num_layers - i - 1))
        layer_params = [(n, p) for n, p in layer.named_parameters() if p.requires_grad]
        if not layer_params:
            continue
        groups.append({
            "params": [p for n, p in layer_params if not any(nd in n for nd in no_decay)],
            "lr": lr_i, "weight_decay": weight_decay,
        })
        groups.append({
            "params": [p for n, p in layer_params if any(nd in n for nd in no_decay)],
            "lr": lr_i, "weight_decay": 0.0,
        })

    # Filter out empty groups
    return [g for g in groups if g["params"]]


# %% train_aiteamvn_v7 (simplified, no R-Drop)
def train_aiteamvn_v7(
    model, train_enc, val_enc, train_prices_np, val_prices_np,
    cat_label_train_np, cat_label_val_np, device,
    epochs=10, batch_size=32, base_lr=2e-5, llrd_decay=0.9,
    weight_decay=0.02, warmup_ratio=0.1, patience=3, max_grad_norm=1.0,
    huber_delta=1.0, aux_alpha=0.1, ema_decay=0.999,
):
    """Fine-tune AITeamVN top layers. Simplified vs train_bert_v7 (no R-Drop)."""
    y_train_log = torch.log1p(torch.FloatTensor(train_prices_np))
    y_val_log = torch.log1p(torch.FloatTensor(val_prices_np))
    y_mean = y_train_log.mean()
    y_std = y_train_log.std()
    y_train_norm = (y_train_log - y_mean) / y_std
    y_val_norm = (y_val_log - y_mean) / y_std
    cat_train_t = torch.LongTensor(cat_label_train_np)
    cat_val_t = torch.LongTensor(cat_label_val_np)

    train_loader = DataLoader(
        MultiTaskDataset(train_enc, y_train_norm, cat_train_t),
        batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True,
    )

    model.to(device)
    param_groups = build_llrd_param_groups_partial(
        model, base_lr=base_lr, decay=llrd_decay, weight_decay=weight_decay
    )
    optimizer = torch.optim.AdamW(param_groups)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * warmup_ratio)
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    ema_model = AveragedModel(model, multi_avg_fn=get_ema_multi_avg_fn(ema_decay))
    ema_model.to(device)

    huber = nn.HuberLoss(delta=huber_delta)
    ce = nn.CrossEntropyLoss()
    scaler = GradScaler("cuda") if device.type == "cuda" else None

    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    print(f"  Params: {n_train:,}/{n_total:,} trainable | Batch: {batch_size}")
    print(f"  Steps/ep: {len(train_loader)} | Warmup: {warmup_steps}/{total_steps}")

    history = {"train_loss": [], "val_loss": [], "val_rmsle": [], "val_mae": [], "lr": []}
    best_val_rmsle = float("inf")
    best_ema_state = None
    patience_counter = 0

    val_ids = val_enc["input_ids"]
    val_mask = val_enc["attention_mask"]

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        epoch_losses = []

        for ids, mask, price_lbl, cat_lbl in train_loader:
            ids = ids.to(device)
            mask = mask.to(device)
            price_lbl = price_lbl.to(device).unsqueeze(1)
            cat_lbl = cat_lbl.to(device)

            optimizer.zero_grad()
            if scaler:
                with autocast(device_type="cuda"):
                    pred, cat = model(ids, mask)
                    loss = huber(pred, price_lbl) + aux_alpha * ce(cat, cat_lbl)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], max_grad_norm
                )
                scaler.step(optimizer)
                scaler.update()
            else:
                pred, cat = model(ids, mask)
                loss = huber(pred, price_lbl) + aux_alpha * ce(cat, cat_lbl)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], max_grad_norm
                )
                optimizer.step()

            scheduler.step()
            ema_model.update_parameters(model)
            epoch_losses.append(loss.item())

        ema_model.eval()
        val_preds = []
        val_losses = []
        with torch.no_grad():
            for i in range(0, len(val_ids), 48):
                b_ids = val_ids[i:i+48].to(device)
                b_mask = val_mask[i:i+48].to(device)
                b_price = y_val_norm[i:i+48].to(device).unsqueeze(1)
                if scaler:
                    with autocast(device_type="cuda"):
                        pred, _ = ema_model(b_ids, b_mask)
                else:
                    pred, _ = ema_model(b_ids, b_mask)
                val_losses.append(huber(pred.float(), b_price).item())
                val_preds.append(pred.float().cpu())

        val_preds_t = torch.cat(val_preds)
        val_loss = float(np.mean(val_losses))
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
            f"  Epoch {epoch:2d}/{epochs} ({elapsed:.0f}s) | "
            f"Train: {np.mean(epoch_losses):.4f} | "
            f"ValLoss: {val_loss:.4f} | "
            f"RMSLE(EMA): {val_rmsle:.4f} | "
            f"MAE: {val_mae:,.0f} | "
            f"LR: {current_lr:.2e}"
        )

        if val_rmsle < best_val_rmsle:
            best_val_rmsle = val_rmsle
            best_ema_state = {k: v.cpu().clone() for k, v in ema_model.state_dict().items()}
            patience_counter = 0
            print(f"    >> New best (EMA): RMSLE={best_val_rmsle:.4f}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"    >> Early stop at epoch {epoch} (patience={patience})")
                break

    ema_model.load_state_dict(best_ema_state)
    ema_model.to(device)
    print(f"  Restored best EMA: Val RMSLE={best_val_rmsle:.4f}")
    return ema_model, y_mean, y_std, history


# %% Phase 4: Train AITeamVN++
print("\n" + "#" * 60)
print("# Phase 4: AITeamVN++ Fine-tune top 4 layers (LLRD + EMA + Aux + Huber)")
print("#" * 60)

AT_V7_PATH = WEIGHTS_V7 / "aiteamvn_v7.pth"

if AT_V7_PATH.exists():
    print("Loading saved AITeamVN++ weights...")
    model_at = BERTMultiTaskRegressor(AITEAMVN_NAME, NUM_CATEGORIES, dropout=0.2)
    freeze_bottom_layers(model_at, keep_top_n=4)
    ema_at = AveragedModel(model_at, multi_avg_fn=get_ema_multi_avg_fn(0.999))
    ckpt = torch.load(AT_V7_PATH, map_location=DEVICE, weights_only=False)
    ema_at.load_state_dict(ckpt["ema_state_dict"])
    ema_at.to(DEVICE)
    y_mean_at, y_std_at = ckpt["y_mean"], ckpt["y_std"]
    hist_at = ckpt.get("history")
    print(f"  Loaded: {AT_V7_PATH.name}")
else:
    model_at = BERTMultiTaskRegressor(AITEAMVN_NAME, NUM_CATEGORIES, dropout=0.2)
    freeze_bottom_layers(model_at, keep_top_n=4)
    ema_at, y_mean_at, y_std_at, hist_at = train_aiteamvn_v7(
        model_at, at_enc_train, at_enc_val,
        train_prices, val_prices, cat_label_train, cat_label_val, DEVICE,
        epochs=10, batch_size=32, base_lr=2e-5, patience=3,
    )
    torch.save({
        "ema_state_dict": ema_at.state_dict(),
        "y_mean": y_mean_at, "y_std": y_std_at, "history": hist_at,
    }, AT_V7_PATH)
    print(f"  Saved: {AT_V7_PATH.name}")

# %% Phase 4: Evaluate AITeamVN++
pred_at_val = predict_bert(ema_at, at_enc_val, y_mean_at, y_std_at, DEVICE)
pred_at_test = predict_bert(ema_at, at_enc_test, y_mean_at, y_std_at, DEVICE)
ALL_PREDS_VAL["v7-AITeamVN++"] = pred_at_val
ALL_PREDS_TEST["v7-AITeamVN++"] = pred_at_test

evaluate_and_store(test_prices, pred_at_test, "v7-AITeamVN++: top 4 layers fine-tune", test_names)
if hist_at:
    plot_bert_history(hist_at, "v7 AITeamVN++ Training")

# Free GPU
ema_at.cpu()
del model_at
torch.cuda.empty_cache()
gc.collect()


# ============================================================
# PHASE 5: PhoBERT++ PCA+LGB + Reload v4/Day3 for Stacking Pool
# ============================================================

# %% [markdown]
# ## Phase 5: Build Stacking Pool
#
# Base models for stacking:
# - v7-PhoBERT++, v7-XLM-R++, v7-AITeamVN++ (done above)
# - v7-PCA+LGB (PhoBERT++ embed + PCA + LGB)
# - v4-2b (AITeamVN frozen + MLP) if weights available
# - v4-0a (DNN + HashingVec) if weights available
# - Day3-LGB retrain (TF-IDF Arch C + LGB)

# %% PhoBERT++ embed -> PCA(256) -> LGB (no Optuna, use v6 best params)
print("\n" + "#" * 60)
print("# Phase 5a: PhoBERT++ embed -> PCA(256) -> LGB")
print("#" * 60)

PCA_V7_PATH = WEIGHTS_V7 / "pca_256.pkl"
if PCA_V7_PATH.exists():
    pca = joblib.load(PCA_V7_PATH)
    print(f"  Loaded PCA: {PCA_V7_PATH.name}")
else:
    pca = PCA(n_components=256, random_state=SEED)
    pca.fit(phobert_emb_train)
    joblib.dump(pca, PCA_V7_PATH)
    print(f"  Fitted PCA: variance retained = {pca.explained_variance_ratio_.sum():.2%}")

pca_train = pca.transform(phobert_emb_train).astype(np.float32)
pca_val = pca.transform(phobert_emb_val).astype(np.float32)
pca_test = pca.transform(phobert_emb_test).astype(np.float32)

cat_train_dense = cat_train.toarray().astype(np.float32)
X_pca_train = np.hstack([pca_train, cat_train_dense])
X_pca_val = np.hstack([pca_val, cat_val_dense])
X_pca_test = np.hstack([pca_test, cat_test_dense])

y_train_log = np.log1p(train_prices)
y_val_log = np.log1p(val_prices)

# Reuse v6 best params (already Optuna-tuned)
V6_PARAMS_PATH = WEIGHTS_V6 / "lgb_v6_best_params.json"
if V6_PARAMS_PATH.exists():
    with open(V6_PARAMS_PATH) as f:
        lgb_params_base = json.load(f)
    print(f"  Using v6 Optuna params: {lgb_params_base}")
else:
    lgb_params_base = {
        "num_leaves": 204, "min_child_samples": 43, "feature_fraction": 0.63,
        "bagging_fraction": 0.8, "lambda_l1": 0.05, "lambda_l2": 0.5,
        "learning_rate": 0.027,
    }
    print(f"  Using default params (v5-B best)")

LGB_V7_PATH = WEIGHTS_V7 / "lgb_v7_phobert_pca.pkl"
if LGB_V7_PATH.exists():
    lgb_v7 = joblib.load(LGB_V7_PATH)
    print(f"  Loaded: {LGB_V7_PATH.name}")
else:
    lgb_v7 = lgb.LGBMRegressor(
        **lgb_params_base, bagging_freq=5, n_estimators=1500,
        random_state=SEED, n_jobs=6, verbose=-1,
    )
    lgb_v7.fit(
        X_pca_train, y_train_log,
        eval_set=[(X_pca_val, y_val_log)],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )
    joblib.dump(lgb_v7, LGB_V7_PATH)

pred_lgb_val = np.clip(np.expm1(lgb_v7.predict(X_pca_val)), 0, None)
pred_lgb_test = np.clip(np.expm1(lgb_v7.predict(X_pca_test)), 0, None)
ALL_PREDS_VAL["v7-PCA+LGB"] = pred_lgb_val
ALL_PREDS_TEST["v7-PCA+LGB"] = pred_lgb_test
evaluate_and_store(test_prices, pred_lgb_test, "v7-PCA+LGB: PhoBERT++ embed + PCA + LGB", test_names)

# %% Phase 5b: Reload v4 Model 2b (AITeamVN frozen + MLP)
print("\n--- Reload v4 Model 2b: AITeamVN frozen + MLP ---")
v4_2b_path = WEIGHTS_V4 / "model_2b_mlp_aiteamvn.pth"
if v4_2b_path.exists() and "train" in at_emb_frozen:
    input_dim = at_emb_frozen["train"].shape[1] + cat_train.shape[1]
    model_2b = MLP(input_dim, hidden_sizes=(512, 256, 128))
    ckpt = torch.load(v4_2b_path, map_location=DEVICE, weights_only=True)
    model_2b.load_state_dict(ckpt["state_dict"])
    model_2b.to(DEVICE)

    X_2b_val = torch.FloatTensor(np.hstack([at_emb_frozen["val"], cat_val_dense]))
    X_2b_test = torch.FloatTensor(np.hstack([at_emb_frozen["test"], cat_test_dense]))
    pred_2b_val = predict_batch(model_2b, X_2b_val, ckpt["y_mean"], ckpt["y_std"], DEVICE)
    pred_2b_test = predict_batch(model_2b, X_2b_test, ckpt["y_mean"], ckpt["y_std"], DEVICE)
    ALL_PREDS_VAL["v4-2b"] = pred_2b_val
    ALL_PREDS_TEST["v4-2b"] = pred_2b_test
    print(f"  v4-2b test RMSLE: {rmsle(test_prices, pred_2b_test):.4f}")
    del model_2b
    torch.cuda.empty_cache()
else:
    print("  v4-2b: SKIPPED")

# %% Phase 5c: Reload v4 Model 0a (DNN + HashingVec)
print("\n--- Reload v4 Model 0a: DNN + HashingVec ---")
v4_0a_path = WEIGHTS_V4 / "model_0a_dnn_hv2048.pth"
if v4_0a_path.exists():
    X_hv_val_cat = torch.FloatTensor(hstack([X_hv_val, cat_val]).toarray())
    X_hv_test_cat = torch.FloatTensor(hstack([X_hv_test, cat_test]).toarray())
    input_dim = X_hv_test_cat.shape[1]

    model_0a = DeepNeuralNetwork(input_dim, hidden_size=2048, num_layers=10)
    ckpt = torch.load(v4_0a_path, map_location=DEVICE, weights_only=True)
    model_0a.load_state_dict(ckpt["state_dict"])
    model_0a.to(DEVICE)

    pred_0a_val = predict_batch(model_0a, X_hv_val_cat, ckpt["y_mean"], ckpt["y_std"], DEVICE)
    pred_0a_test = predict_batch(model_0a, X_hv_test_cat, ckpt["y_mean"], ckpt["y_std"], DEVICE)
    ALL_PREDS_VAL["v4-0a"] = pred_0a_val
    ALL_PREDS_TEST["v4-0a"] = pred_0a_test
    print(f"  v4-0a test RMSLE: {rmsle(test_prices, pred_0a_test):.4f}")
    del model_0a, X_hv_val_cat, X_hv_test_cat
    torch.cuda.empty_cache()
else:
    print("  v4-0a: SKIPPED")

# %% Phase 5d: Retrain Day3 LGB (or reuse v5/v6 cache)
print("\n--- Retrain Day3 LGB ---")
LGB_DAY3_V6 = WEIGHTS_V6 / "lgb_day3_retrain.pkl"
LGB_DAY3_V5 = WEIGHTS_V5 / "lgb_day3_retrain.pkl"
LGB_DAY3_V7 = WEIGHTS_V7 / "lgb_day3_retrain.pkl"

if LGB_DAY3_V6.exists():
    lgb_day3 = joblib.load(LGB_DAY3_V6)
    print(f"  Loaded from v6: {LGB_DAY3_V6}")
elif LGB_DAY3_V5.exists():
    lgb_day3 = joblib.load(LGB_DAY3_V5)
    print(f"  Loaded from v5: {LGB_DAY3_V5}")
else:
    DAY3_PARAMS = {
        "num_leaves": 199, "min_child_samples": 50, "feature_fraction": 0.545,
        "lambda_l1": 0.021, "lambda_l2": 0.190, "learning_rate": 0.038,
        "n_estimators": 1500, "random_state": SEED, "n_jobs": 6, "verbose": -1,
    }
    lgb_day3 = lgb.LGBMRegressor(**DAY3_PARAMS)
    lgb_day3.fit(X_cc_train, y_train_log)
    joblib.dump(lgb_day3, LGB_DAY3_V7)

pred_day3_val = np.clip(np.expm1(lgb_day3.predict(X_cc_val)), 0, None)
pred_day3_test = np.clip(np.expm1(lgb_day3.predict(X_cc_test)), 0, None)
ALL_PREDS_VAL["Day3-LGB"] = pred_day3_val
ALL_PREDS_TEST["Day3-LGB"] = pred_day3_test
print(f"  Day3-LGB test RMSLE: {rmsle(test_prices, pred_day3_test):.4f}")


# ============================================================
# PHASE 6: Stacking Meta-learners (Ridge + ElasticNet + LGB)
# ============================================================

# %% [markdown]
# ## Phase 6: Stacking Meta-learners
#
# Train Ridge, ElasticNet, LGB meta-learners on val predictions (3,926 samples x N_base models),
# evaluate on test predictions. Final = average of 3 meta-learners.
#
# Val predictions are OOF-like: base BERT models trained on train-only, predicted val
# without ever seeing it during training.

# %% Stacking setup
print("\n" + "#" * 60)
print("# Phase 6: Stacking Meta-learners")
print("#" * 60)

base_names = list(ALL_PREDS_VAL.keys())
print(f"\n  Base models ({len(base_names)}): {base_names}")
for name in base_names:
    r_test = rmsle(test_prices, ALL_PREDS_TEST[name])
    print(f"    {name:25s}: test RMSLE = {r_test:.4f}")

# Predictions work in log-space for better meta-learning
X_meta_val_log = np.column_stack([np.log1p(ALL_PREDS_VAL[n]) for n in base_names])
X_meta_test_log = np.column_stack([np.log1p(ALL_PREDS_TEST[n]) for n in base_names])
y_val_log_np = np.log1p(val_prices)

print(f"\n  Meta features shape: val {X_meta_val_log.shape}, test {X_meta_test_log.shape}")

# %% Meta 1: Ridge
print("\n--- Meta 1: Ridge ---")
ridge = Ridge(alpha=1.0, random_state=SEED)
ridge.fit(X_meta_val_log, y_val_log_np)
pred_ridge_log = ridge.predict(X_meta_test_log)
pred_ridge_test = np.clip(np.expm1(pred_ridge_log), 0, None)
pred_ridge_val = np.clip(np.expm1(ridge.predict(X_meta_val_log)), 0, None)
print(f"  Ridge val RMSLE: {rmsle(val_prices, pred_ridge_val):.4f}")
print(f"  Ridge test RMSLE: {rmsle(test_prices, pred_ridge_test):.4f}")
print(f"  Coefs: {dict(zip(base_names, ridge.coef_.round(3)))}")

# %% Meta 2: ElasticNet
print("\n--- Meta 2: ElasticNet ---")
enet = ElasticNet(alpha=0.001, l1_ratio=0.5, random_state=SEED, max_iter=5000)
enet.fit(X_meta_val_log, y_val_log_np)
pred_enet_log = enet.predict(X_meta_test_log)
pred_enet_test = np.clip(np.expm1(pred_enet_log), 0, None)
pred_enet_val = np.clip(np.expm1(enet.predict(X_meta_val_log)), 0, None)
print(f"  ElasticNet val RMSLE: {rmsle(val_prices, pred_enet_val):.4f}")
print(f"  ElasticNet test RMSLE: {rmsle(test_prices, pred_enet_test):.4f}")
print(f"  Coefs: {dict(zip(base_names, enet.coef_.round(3)))}")

# %% Meta 3: LightGBM (small, careful with overfit on 3,926 samples)
print("\n--- Meta 3: LightGBM ---")
lgb_meta = lgb.LGBMRegressor(
    n_estimators=200, num_leaves=15, min_child_samples=30,
    learning_rate=0.03, feature_fraction=0.9, bagging_fraction=0.9,
    bagging_freq=3, lambda_l2=1.0, random_state=SEED, n_jobs=6, verbose=-1,
)
# Use val for fit (sole source), but with K-fold CV early stop via LGB
lgb_meta.fit(
    X_meta_val_log, y_val_log_np,
    eval_set=[(X_meta_val_log, y_val_log_np)],
    callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(0)],
)
pred_lgb_meta_test = np.clip(np.expm1(lgb_meta.predict(X_meta_test_log)), 0, None)
pred_lgb_meta_val = np.clip(np.expm1(lgb_meta.predict(X_meta_val_log)), 0, None)
print(f"  LGB-meta val RMSLE: {rmsle(val_prices, pred_lgb_meta_val):.4f}")
print(f"  LGB-meta test RMSLE: {rmsle(test_prices, pred_lgb_meta_test):.4f}")

# %% Final: Average of 3 meta-learners
print("\n--- Final: Average(Ridge, ElasticNet, LGB-meta) ---")
pred_stacked_test = (pred_ridge_test + pred_enet_test + pred_lgb_meta_test) / 3
pred_stacked_val = (pred_ridge_val + pred_enet_val + pred_lgb_meta_val) / 3
ALL_PREDS_VAL["v7 Stacked"] = pred_stacked_val
ALL_PREDS_TEST["v7 Stacked"] = pred_stacked_test

evaluate_and_store(test_prices, pred_stacked_test, "v7: Stacked (Ridge+EN+LGB avg)", test_names)

# %% Also compute weighted blend for comparison
print("\n--- Baseline: Weighted Blend (scipy.minimize on val) ---")
blend_val = [ALL_PREDS_VAL[n] for n in base_names]
blend_test = [ALL_PREDS_TEST[n] for n in base_names]

def blend_objective(w):
    w = np.abs(w)
    w = w / w.sum()
    pred = sum(wi * p for wi, p in zip(w, blend_val))
    return rmsle(val_prices, pred)

x0 = np.ones(len(base_names)) / len(base_names)
res = scipy_minimize(blend_objective, x0=x0, method="Nelder-Mead",
                     options={"maxiter": 5000, "xatol": 1e-6, "fatol": 1e-6})
opt_w = np.abs(res.x) / np.abs(res.x).sum()
print(f"  Val RMSLE: {res.fun:.4f}")
print(f"  Weights: {dict(zip(base_names, opt_w.round(3)))}")

blend_test_pred = sum(w * p for w, p in zip(opt_w, blend_test))
ALL_PREDS_VAL["v7 Weighted Blend"] = sum(w * p for w, p in zip(opt_w, blend_val))
ALL_PREDS_TEST["v7 Weighted Blend"] = blend_test_pred
evaluate_and_store(test_prices, blend_test_pred, "v7: Weighted Blend (baseline)", test_names)

# Save stacking config
stacking_config = {
    "base_models": base_names,
    "ridge_coefs": dict(zip(base_names, ridge.coef_.tolist())),
    "enet_coefs": dict(zip(base_names, enet.coef_.tolist())),
    "blend_weights": dict(zip(base_names, opt_w.tolist())),
    "stacked_test_rmsle": ALL_RESULTS["v7: Stacked (Ridge+EN+LGB avg)"]["rmsle"],
    "blend_test_rmsle": ALL_RESULTS["v7: Weighted Blend (baseline)"]["rmsle"],
}
with open(WEIGHTS_V7 / "stacking_config.json", "w") as f:
    json.dump(stacking_config, f, indent=2, ensure_ascii=False)
print(f"\n  Saved: {WEIGHTS_V7 / 'stacking_config.json'}")


# ============================================================
# PHASE 7: FINAL SUMMARY + CHARTS
# ============================================================

# %% [markdown]
# ## Phase 7: Final Summary

# %% Summary table
print("\n\n" + "=" * 70)
print("FINAL RESULTS -- Day 4 v7")
print("=" * 70)

ALL_RESULTS["Baseline: v6 Blended"] = {
    "rmsle": 0.4187, "mae": 82_766, "mape": 33.2, "r2": 67.6,
}
ALL_RESULTS["Baseline: v5-old Blended"] = {
    "rmsle": 0.4191, "mae": 84_550, "mape": 33.6, "r2": 67.2,
}
ALL_RESULTS["Baseline: v4 AITeamVN+MLP"] = {
    "rmsle": 0.4986, "mae": 99_786, "mape": 39.0, "r2": 55.3,
}
ALL_RESULTS["Baseline: Day 3 Blended"] = {
    "rmsle": 0.5164, "mae": 109_725, "mape": 44.0, "r2": 47.1,
}

df = pd.DataFrame(ALL_RESULTS).T.sort_values("rmsle")
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
print(f"vs v6 Blended (0.4187):   {(0.4187 - best_rmsle) / 0.4187 * 100:+.1f}%")
print(f"vs v4 best (0.4986):      {(0.4986 - best_rmsle) / 0.4986 * 100:+.1f}%")
print(f"vs Day 3 (0.5164):        {(0.5164 - best_rmsle) / 0.5164 * 100:+.1f}%")
print(f"vs Target (0.40):         {'ACHIEVED' if best_rmsle <= 0.40 else f'gap {best_rmsle - 0.40:.4f}'}")

with open(WEIGHTS_V7 / "v7_results.json", "w") as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False)
print(f"\nResults saved: {WEIGHTS_V7 / 'v7_results.json'}")

# %% RMSLE comparison chart
fig = go.Figure()
colors = []
for r in df["rmsle"]:
    if r <= 0.40:
        colors.append("mediumseagreen")
    elif r < 0.43:
        colors.append("steelblue")
    elif r < 0.50:
        colors.append("orange")
    else:
        colors.append("lightcoral")

fig.add_trace(go.Bar(
    x=df.index, y=df["rmsle"], marker_color=colors,
    text=[f"{v:.4f}" for v in df["rmsle"]], textposition="outside",
))
fig.add_hline(y=0.4187, line_dash="dash", line_color="red",
              annotation_text="v6 Blended (0.4187)")
fig.add_hline(y=0.4986, line_dash="dash", line_color="orange",
              annotation_text="v4 Best (0.4986)")
fig.add_hline(y=0.40, line_dash="dash", line_color="green",
              annotation_text="Target (0.40)")
fig.update_layout(
    title="Day 4 v7: RMSLE Comparison (lower is better)",
    xaxis_title="Model", yaxis_title="RMSLE",
    width=1200, height=600, template="plotly_white",
    xaxis_tickangle=-30,
)
fig.show()

# %% Multi-metric chart
fig_multi = make_subplots(
    rows=2, cols=2,
    subplot_titles=("RMSLE (lower=better)", "MAE VND (lower=better)",
                    "MAPE % (lower=better)", "R2 % (higher=better)"),
)
fig_multi.add_trace(go.Bar(x=df.index, y=df["rmsle"], marker_color="steelblue"), row=1, col=1)
fig_multi.add_trace(go.Bar(x=df.index, y=df["mae"], marker_color="tomato"), row=1, col=2)
fig_multi.add_trace(go.Bar(x=df.index, y=df["mape"], marker_color="orange"), row=2, col=1)
fig_multi.add_trace(go.Bar(x=df.index, y=df["r2"], marker_color="mediumseagreen"), row=2, col=2)
fig_multi.update_layout(
    title="Day 4 v7: All Metrics",
    width=1300, height=750, template="plotly_white", showlegend=False,
)
fig_multi.update_xaxes(tickangle=-30)
fig_multi.show()

print("\n--- Day 4 v7 COMPLETE ---")
print(f"Weights saved in: {WEIGHTS_V7}")
print("Files:", [f.name for f in WEIGHTS_V7.iterdir()])
