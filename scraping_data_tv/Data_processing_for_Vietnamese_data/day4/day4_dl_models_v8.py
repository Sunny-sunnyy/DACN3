# %% [markdown]
# # Day 4 v8: PhoBERT-large + mDeBERTa + Category Heads + Weighted Sampler
#
# **Target:** RMSLE <= 0.38
#
# **Created:** 2026-04-23 — BEFORE v7 results. v8 is independent.
# - If v7 < 0.40: v8 adds 2 stronger models to push further down.
# - If v7 >= 0.40: v8 is the primary fallback.
#
# **Data:** Train=85,727 | Val=3,926 | Test=3,872 | 8 categories | Price<=1M VND
#
# **Hardware:** RTX 3090 Ti 24GB | 64GB RAM | AMD Ryzen 9 3900X 12-Core
#
# **New vs v7:**
# - PhoBERT-large (370M, 24L, 1024d) with gradient_checkpointing
# - mDeBERTa-v3-base (184M, 12L, 768d, disentangled attention)
# - WeightedRandomSampler (price-bin stratified, 10 bins)
# - Category-specific regression heads (8 heads instead of 1 shared)
# - Transductive PCA (fit on train+val+test embeddings)
# - Fixed LGB meta early-stopping (held-out 20% of val set)
# - Stacking pool: up to 9 models (7 from v7 + 2 new)
#
# **Baselines:** v6 Blended=0.4187 | v7 expected=0.39-0.41 (not run yet)

# %% Install (uncomment on first run)
# !uv pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130
# !uv add transformers sentence-transformers accelerate lightgbm scikit-learn plotly underthesea

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
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
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
from pricer_vi.deep_neural_network import DeepNeuralNetwork, MLP, predict_batch
from pricer_vi.evaluator import plot_predictions

DATASET = "SeanSunny/items_tv_v6"
MAX_PRICE = 1_000_000
SEED = 42

# Model names
PHOBERT_LARGE_NAME = "vinai/phobert-large"      # 370M, 24L, 1024d — same tokenizer as base-v2
PHOBERT_BASE_NAME  = "vinai/phobert-base-v2"    # for reloading v7 models
DEBERTA_NAME       = "microsoft/mdeberta-v3-base"  # 184M, 12L, 768d
XLMR_NAME          = "FacebookAI/xlm-roberta-base"
AITEAMVN_NAME      = "AITeamVN/Vietnamese_Embedding"

# Batch sizes for 3090 Ti 24GB
# Baseline: AITeamVN 568M 24L batch=32 no-R-Drop = 7.8/24GB VRAM
# PhoBERT-large 370M 24L batch=48 R-Drop (2x forward) ≈ 13GB — no GC needed
# mDeBERTa 184M 12L batch=128 no-R-Drop ≈ 8GB
PHOBERT_LARGE_BATCH = 48   # R-Drop 2x = 96 forward/step; GC disabled
DEBERTA_BATCH       = 128  # no R-Drop; plenty of VRAM headroom

# Training hyperparams (proven from v7)
EPOCHS        = 12
PATIENCE      = 3
BASE_LR       = 2e-5
LLRD_DECAY    = 0.9
WEIGHT_DECAY  = 0.02
WARMUP_RATIO  = 0.1
HUBER_DELTA   = 1.0
RDROP_ALPHA   = 0.5
AUX_ALPHA     = 0.1
EMA_DECAY     = 0.999
DROPOUT       = 0.2

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True  # faster kernel selection (fixed seq_len=256)

print(f"Device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"GPU: {torch.cuda.get_device_name()}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

WEIGHTS_V8 = DAY4 / "weights_v8"
WEIGHTS_V7 = DAY4 / "weights_v7"
WEIGHTS_V6 = DAY4 / "weights_v6"
WEIGHTS_V5 = DAY4 / "weights_v5"
WEIGHTS_V4 = DAY4 / "weights"
WEIGHTS_V8.mkdir(exist_ok=True)

ALL_RESULTS    = {}
ALL_PREDS_VAL  = {}
ALL_PREDS_TEST = {}


# %% Metric helpers
def rmsle(y_true, y_pred):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.clip(np.array(y_pred, dtype=float), 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def evaluate_and_store(y_true, y_pred, name, names=None):
    r = plot_predictions(y_true, y_pred, title=name, names=names)
    print(f"\n{'='*60}")
    print(f"{name} ({len(y_true)} items)")
    print(f"  RMSLE: {r['rmsle']:.4f}  MAE: {r['mae']:,.0f} VND  MAPE: {r['mape']:.1f}%  R2: {r['r2']:.1f}%")
    print(f"{'='*60}")
    ALL_RESULTS[name] = r
    return r


def plot_bert_history(history, title):
    epochs = list(range(1, len(history["train_loss"]) + 1))
    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=("Loss", "Val RMSLE", "Val MAE (VND)", "Learning Rate"))
    fig.add_trace(go.Scatter(x=epochs, y=history["train_loss"], name="Train",
                             line=dict(color="steelblue")), row=1, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_loss"], name="Val",
                             line=dict(color="tomato")), row=1, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_rmsle"], mode="lines+markers",
                             line=dict(color="tomato")), row=1, col=2)
    fig.add_trace(go.Scatter(x=epochs, y=history["val_mae"], mode="lines+markers",
                             line=dict(color="mediumseagreen")), row=2, col=1)
    fig.add_trace(go.Scatter(x=epochs, y=history["lr"],
                             line=dict(color="purple")), row=2, col=2)
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
val_items   = filter_items(val_items)
test_items  = filter_items(test_items)
print(f"Train: {len(train_items):,} | Val: {len(val_items):,} | Test: {len(test_items):,}")

train_summaries = [it.summary for it in train_items]
val_summaries   = [it.summary for it in val_items]
test_summaries  = [it.summary for it in test_items]

train_prices = np.array([it.price for it in train_items], dtype=np.float32)
val_prices   = np.array([it.price for it in val_items],   dtype=np.float32)
test_prices  = np.array([it.price for it in test_items],  dtype=np.float32)

train_categories = [it.category for it in train_items]
val_categories   = [it.category for it in val_items]
test_categories  = [it.category for it in test_items]

test_names = [it.title[:40] + "..." if len(it.title) > 40 else it.title for it in test_items]

# %% Category encoders
print("--- Category encoders ---")
cat_encoder = OneHotEncoder(sparse_output=True, handle_unknown="ignore")
cat_train   = cat_encoder.fit_transform(np.array(train_categories).reshape(-1, 1))
cat_val     = cat_encoder.transform(np.array(val_categories).reshape(-1, 1))
cat_test    = cat_encoder.transform(np.array(test_categories).reshape(-1, 1))

cat_label_encoder = LabelEncoder()
cat_label_train = cat_label_encoder.fit_transform(train_categories)
cat_label_val   = cat_label_encoder.transform(val_categories)
cat_label_test  = cat_label_encoder.transform(test_categories)
NUM_CATEGORIES  = len(cat_label_encoder.classes_)
print(f"Categories ({NUM_CATEGORIES}): {list(cat_label_encoder.classes_)}")

# %% Underthesea tokenize (PhoBERT family reuses same cache)
UNDERTHESEA_CACHE = {
    "train": DAY4 / "tokenized_train_1m.pkl",
    "val":   DAY4 / "tokenized_val_1m.pkl",
    "test":  DAY4 / "tokenized_test_1m.pkl",
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
tok_val   = load_or_tokenize(val_summaries,   UNDERTHESEA_CACHE["val"],   "val")
tok_test  = load_or_tokenize(test_summaries,  UNDERTHESEA_CACHE["test"],  "test")

# %% PhoBERT-large tokenize (same tokenizer as phobert-base-v2)
print("\n--- PhoBERT-large tokenize (reuse base-v2 tokenizer) ---")
phobert_large_tokenizer = AutoTokenizer.from_pretrained(PHOBERT_LARGE_NAME)
t0 = time.time()
pbl_enc_train = phobert_large_tokenizer(
    tok_train, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
pbl_enc_val = phobert_large_tokenizer(
    tok_val, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
pbl_enc_test = phobert_large_tokenizer(
    tok_test, truncation=True, padding="max_length", max_length=256, return_tensors="pt"
)
print(f"  Train: {pbl_enc_train['input_ids'].shape} ({time.time()-t0:.1f}s)")

# %% mDeBERTa-v3-base tokenize (raw summaries, no word segmentation needed)
print("\n--- mDeBERTa-v3-base tokenize ---")
deberta_tokenizer = AutoTokenizer.from_pretrained(DEBERTA_NAME)
t0 = time.time()
deb_enc_train = deberta_tokenizer(
    train_summaries, truncation=True, padding="max_length", max_length=256,
    return_tensors="pt", return_token_type_ids=False,
)
deb_enc_val = deberta_tokenizer(
    val_summaries, truncation=True, padding="max_length", max_length=256,
    return_tensors="pt", return_token_type_ids=False,
)
deb_enc_test = deberta_tokenizer(
    test_summaries, truncation=True, padding="max_length", max_length=256,
    return_tensors="pt", return_token_type_ids=False,
)
print(f"  Train: {deb_enc_train['input_ids'].shape} ({time.time()-t0:.1f}s)")

# %% Legacy data for pool (AITeamVN frozen embs, HashingVec, TF-IDF Arch C)
EMB_AT_FROZEN = {
    "train": DAY4 / "aiteamvn_train.npy",
    "val":   DAY4 / "aiteamvn_val.npy",
    "test":  DAY4 / "aiteamvn_test.npy",
}
print("\n--- AITeamVN frozen embeddings (v4 cache) ---")
at_emb_frozen = {}
for split, path in EMB_AT_FROZEN.items():
    if path.exists():
        at_emb_frozen[split] = np.load(path)
        print(f"  {split}: {at_emb_frozen[split].shape}")
    else:
        print(f"  WARNING: {path.name} not found — v4-2b model will be skipped")

print("\n--- HashingVectorizer (for v4-0a) ---")
hv = HashingVectorizer(n_features=5000, binary=True, alternate_sign=False)
X_hv_val  = hv.transform(val_summaries)
X_hv_test = hv.transform(test_summaries)

print("\n--- TF-IDF Arch C (for Day3-LGB) ---")
ARCH_C_CACHE = next(
    (p for p in [WEIGHTS_V6 / "arch_c_vectorizer.pkl",
                 WEIGHTS_V5 / "arch_c_vectorizer.pkl",
                 WEIGHTS_V8 / "arch_c_vectorizer.pkl"]
     if p.exists()), None
)
if ARCH_C_CACHE:
    arch_c = joblib.load(ARCH_C_CACHE)
    print(f"  Loaded: {ARCH_C_CACHE}")
    X_c_train = arch_c.transform(tok_train)
else:
    print("  Fitting Arch C (word bigram + char_wb 3-5)...")
    arch_c = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=5000)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=5000)),
    ])
    X_c_train = arch_c.fit_transform(tok_train)
    joblib.dump(arch_c, WEIGHTS_V8 / "arch_c_vectorizer.pkl")
    print(f"  Fitted: {X_c_train.shape}")

X_c_val  = arch_c.transform(tok_val)
X_c_test = arch_c.transform(tok_test)
X_cc_train = hstack([X_c_train, cat_train])
X_cc_val   = hstack([X_c_val,   cat_val])
X_cc_test  = hstack([X_c_test,  cat_test])
cat_val_dense  = cat_val.toarray().astype(np.float32)
cat_test_dense = cat_test.toarray().astype(np.float32)

print("\n=== PHASE 1 DONE ===")


# ============================================================
# PHASE 2: MODEL CLASSES + TRAINING UTILITIES
# ============================================================

# %% [markdown]
# ## Phase 2: Model Classes + Training Utilities

# %% mean_pooling (same as v7)
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output.last_hidden_state
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (token_embeddings * mask_expanded).sum(1) / mask_expanded.sum(1).clamp(min=1e-9)


# %% v7-compatible model class (for reloading v7 weights)
class BERTMultiTaskRegressorV7(nn.Module):
    """Single shared price head — matches v7 saved weights."""

    def __init__(self, model_name, num_categories, dropout=0.2):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        h = self.bert.config.hidden_size
        self.price_head = nn.Sequential(
            nn.LayerNorm(h), nn.Linear(h, 256), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(256, 1),
        )
        self.category_head = nn.Linear(h, num_categories)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = mean_pooling(outputs, attention_mask)
        return self.price_head(pooled), self.category_head(pooled)

    def extract_embeddings(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        return mean_pooling(outputs, attention_mask)


# %% v8 model class — category-specific regression heads
class BERTCatHeadRegressor(nn.Module):
    """Per-category regression heads + aux classification head.

    Each of the 8 categories gets its own Linear head, reducing
    cross-category price distribution noise.
    Gradient checkpointing optionally enabled for large models.
    """

    def __init__(self, model_name, num_categories, dropout=0.2,
                 use_gradient_checkpointing=False):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        if use_gradient_checkpointing:
            self.bert.config.use_cache = False
            self.bert.gradient_checkpointing_enable()
        h = self.bert.config.hidden_size
        self.num_categories = num_categories
        self.price_heads = nn.ModuleList([
            nn.Sequential(
                nn.LayerNorm(h), nn.Linear(h, 256), nn.GELU(),
                nn.Dropout(dropout), nn.Linear(256, 1),
            ) for _ in range(num_categories)
        ])
        self.category_head = nn.Linear(h, num_categories)
        self._init_heads()

    def _init_heads(self):
        for head in self.price_heads:
            for m in head:
                if isinstance(m, nn.Linear):
                    nn.init.normal_(m.weight, std=0.01) if m.out_features == 1 \
                        else nn.init.xavier_normal_(m.weight)
                    nn.init.zeros_(m.bias)
        nn.init.xavier_normal_(self.category_head.weight)
        nn.init.zeros_(self.category_head.bias)

    def forward(self, input_ids, attention_mask, cat_ids=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = mean_pooling(outputs, attention_mask)
        cat_logits = self.category_head(pooled)
        # Stack all 8 head outputs, then gather the one matching each sample's category
        all_preds = torch.stack([h(pooled) for h in self.price_heads], dim=1)  # [B, 8, 1]
        if cat_ids is not None:
            idx = cat_ids.view(-1, 1, 1).expand(-1, 1, 1)
            price_pred = all_preds.gather(1, idx).squeeze(1)  # [B, 1]
        else:
            price_pred = all_preds.mean(dim=1)  # fallback: average all heads
        return price_pred, cat_logits

    def extract_embeddings(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        return mean_pooling(outputs, attention_mask)


# %% Dataset (same as v7)
class MultiTaskDataset(Dataset):
    def __init__(self, encodings, price_labels, cat_labels):
        self.input_ids     = encodings["input_ids"]
        self.attention_mask = encodings["attention_mask"]
        self.price_labels  = price_labels
        self.cat_labels    = cat_labels

    def __len__(self):
        return len(self.price_labels)

    def __getitem__(self, idx):
        return (self.input_ids[idx], self.attention_mask[idx],
                self.price_labels[idx], self.cat_labels[idx])


# %% WeightedRandomSampler by price bin (NEW in v8)
def make_price_sampler(prices, n_bins=10):
    """Upsample rare price bins to reduce mid-price bias in RMSLE."""
    log_p = np.log1p(prices)
    bins  = pd.qcut(log_p, q=n_bins, labels=False, duplicates="drop")
    counts = np.bincount(bins)
    w = 1.0 / counts[bins].astype(np.float64)
    w /= w.sum()
    return WeightedRandomSampler(
        weights=torch.DoubleTensor(w), num_samples=len(w), replacement=True
    )


# %% LLRD param groups for v8 (handles ModuleList price_heads + 24-layer models)
def build_llrd_param_groups_v8(model, base_lr=2e-5, decay=0.9, weight_decay=0.02):
    """Layer-wise LR decay for BERTCatHeadRegressor (works for 12 and 24 layers)."""
    groups = []
    no_decay = ("bias", "LayerNorm.weight")

    # All head parameters
    head_params = []
    for head in model.price_heads:
        head_params += list(head.named_parameters())
    head_params += list(model.category_head.named_parameters())
    groups.append({
        "params": [p for n, p in head_params if not any(nd in n for nd in no_decay)],
        "lr": base_lr, "weight_decay": weight_decay,
    })
    groups.append({
        "params": [p for n, p in head_params if any(nd in n for nd in no_decay)],
        "lr": base_lr, "weight_decay": 0.0,
    })

    # Encoder layers (top=high LR, bottom=low LR)
    bert = model.bert
    num_layers = len(bert.encoder.layer)
    for i, layer in enumerate(bert.encoder.layer):
        lr_i = base_lr * (decay ** (num_layers - i - 1))
        lp = list(layer.named_parameters())
        groups.append({
            "params": [p for n, p in lp if not any(nd in n for nd in no_decay)],
            "lr": lr_i, "weight_decay": weight_decay,
        })
        groups.append({
            "params": [p for n, p in lp if any(nd in n for nd in no_decay)],
            "lr": lr_i, "weight_decay": 0.0,
        })

    # Embeddings (lowest LR)
    emb_lr = base_lr * (decay ** num_layers)
    ep = list(bert.embeddings.named_parameters())
    groups.append({
        "params": [p for n, p in ep if not any(nd in n for nd in no_decay)],
        "lr": emb_lr, "weight_decay": weight_decay,
    })
    groups.append({
        "params": [p for n, p in ep if any(nd in n for nd in no_decay)],
        "lr": emb_lr, "weight_decay": 0.0,
    })

    if hasattr(bert, "pooler") and bert.pooler is not None:
        groups.append({
            "params": list(bert.pooler.parameters()),
            "lr": base_lr, "weight_decay": weight_decay,
        })
    return groups


# %% Training function v8
def train_bert_v8(
    model, train_enc, val_enc, train_prices_np, val_prices_np,
    cat_label_train_np, cat_label_val_np, device,
    epochs=EPOCHS, batch_size=32, base_lr=BASE_LR, llrd_decay=LLRD_DECAY,
    weight_decay=WEIGHT_DECAY, warmup_ratio=WARMUP_RATIO, patience=PATIENCE,
    max_grad_norm=1.0, huber_delta=HUBER_DELTA, rdrop_alpha=RDROP_ALPHA,
    aux_alpha=AUX_ALPHA, ema_decay=EMA_DECAY, use_rdrop=True,
    use_weighted_sampler=True,
):
    """Train BERTCatHeadRegressor with LLRD+R-Drop+EMA+Huber+WeightedSampler."""
    y_train_log  = torch.log1p(torch.FloatTensor(train_prices_np))
    y_val_log    = torch.log1p(torch.FloatTensor(val_prices_np))
    y_mean = y_train_log.mean()
    y_std  = y_train_log.std()
    y_train_norm = (y_train_log - y_mean) / y_std
    y_val_norm   = (y_val_log  - y_mean) / y_std
    cat_train_t  = torch.LongTensor(cat_label_train_np)
    cat_val_t    = torch.LongTensor(cat_label_val_np)

    print(f"  Target: mean={y_mean:.4f}, std={y_std:.4f}")
    print(f"  Norm range: [{y_train_norm.min():.2f}, {y_train_norm.max():.2f}]")

    dataset = MultiTaskDataset(train_enc, y_train_norm, cat_train_t)
    if use_weighted_sampler:
        sampler = make_price_sampler(train_prices_np)
        train_loader = DataLoader(dataset, batch_size=batch_size, sampler=sampler,
                                  num_workers=0, pin_memory=True)
    else:
        train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                                  num_workers=0, pin_memory=True)

    model.to(device)
    param_groups = build_llrd_param_groups_v8(model, base_lr=base_lr,
                                               decay=llrd_decay, weight_decay=weight_decay)
    optimizer    = torch.optim.AdamW(param_groups)
    total_steps  = len(train_loader) * epochs
    warmup_steps = int(total_steps * warmup_ratio)
    scheduler    = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    ema_model = AveragedModel(model, multi_avg_fn=get_ema_multi_avg_fn(ema_decay))
    ema_model.to(device)

    huber            = nn.HuberLoss(delta=huber_delta)
    ce               = nn.CrossEntropyLoss()
    mse_consistency  = nn.MSELoss()
    scaler           = GradScaler("cuda") if device.type == "cuda" else None

    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    print(f"  Params: {n_train:,}/{n_total:,} trainable | Batch: {batch_size}")
    print(f"  Steps/ep: {len(train_loader)} | Total: {total_steps} | Warmup: {warmup_steps}")
    num_layers = len(model.bert.encoder.layer)
    print(f"  LLRD: {num_layers}L, base={base_lr:.1e}, decay={llrd_decay}, "
          f"emb_lr={base_lr*(llrd_decay**num_layers):.2e}")
    print(f"  R-Drop={'ON alpha='+str(rdrop_alpha) if use_rdrop else 'OFF'} | "
          f"Aux={aux_alpha} | EMA={ema_decay} | WeightedSampler={use_weighted_sampler}")

    history = {"train_loss": [], "val_loss": [], "val_rmsle": [], "val_mae": [], "lr": []}
    best_val_rmsle  = float("inf")
    best_ema_state  = None
    patience_counter = 0

    val_ids  = val_enc["input_ids"]
    val_mask = val_enc["attention_mask"]

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        epoch_losses = []

        for ids, mask, price_lbl, cat_lbl in train_loader:
            ids       = ids.to(device)
            mask      = mask.to(device)
            price_lbl = price_lbl.to(device).unsqueeze(1)
            cat_lbl   = cat_lbl.to(device)

            optimizer.zero_grad()
            if scaler:
                with autocast(device_type="cuda"):
                    pred1, cat1 = model(ids, mask, cat_ids=cat_lbl)
                    loss_price  = huber(pred1, price_lbl)
                    loss_cat    = ce(cat1, cat_lbl)
                    if use_rdrop:
                        pred2, cat2 = model(ids, mask, cat_ids=cat_lbl)
                        loss_price  = (loss_price + huber(pred2, price_lbl)) / 2
                        loss_cat    = (loss_cat   + ce(cat2, cat_lbl))   / 2
                        loss_cons   = mse_consistency(pred1, pred2)
                        loss = loss_price + aux_alpha * loss_cat + rdrop_alpha * loss_cons
                    else:
                        loss = loss_price + aux_alpha * loss_cat
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
            else:
                pred1, cat1 = model(ids, mask, cat_ids=cat_lbl)
                loss_price  = huber(pred1, price_lbl)
                loss_cat    = ce(cat1, cat_lbl)
                if use_rdrop:
                    pred2, cat2 = model(ids, mask, cat_ids=cat_lbl)
                    loss_price  = (loss_price + huber(pred2, price_lbl)) / 2
                    loss_cat    = (loss_cat   + ce(cat2, cat_lbl))   / 2
                    loss_cons   = mse_consistency(pred1, pred2)
                    loss = loss_price + aux_alpha * loss_cat + rdrop_alpha * loss_cons
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
        val_preds, val_losses = [], []
        cat_val_dev = cat_val_t.to(device)
        with torch.no_grad():
            for i in range(0, len(val_ids), 64):
                b_ids  = val_ids[i:i+64].to(device)
                b_mask = val_mask[i:i+64].to(device)
                b_cat  = cat_val_dev[i:i+64]
                b_price = y_val_norm[i:i+64].to(device).unsqueeze(1)
                if scaler:
                    with autocast(device_type="cuda"):
                        pred, _ = ema_model(b_ids, b_mask, cat_ids=b_cat)
                else:
                    pred, _ = ema_model(b_ids, b_mask, cat_ids=b_cat)
                val_losses.append(huber(pred.float(), b_price).item())
                val_preds.append(pred.float().cpu())

        val_preds_t = torch.cat(val_preds)
        val_loss    = float(np.mean(val_losses))
        val_pred_vnd = torch.expm1(val_preds_t * y_std + y_mean).clamp(min=0).numpy().flatten()
        val_rmsle   = rmsle(val_prices_np, val_pred_vnd)
        val_mae     = float(np.mean(np.abs(val_prices_np - val_pred_vnd)))
        current_lr  = scheduler.get_last_lr()[0]

        history["train_loss"].append(float(np.mean(epoch_losses)))
        history["val_loss"].append(val_loss)
        history["val_rmsle"].append(val_rmsle)
        history["val_mae"].append(val_mae)
        history["lr"].append(current_lr)

        print(
            f"  Epoch {epoch:2d}/{epochs} ({time.time()-t0:.0f}s) | "
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


# %% Predict functions
def predict_bert_v8(model, encodings, cat_labels, y_mean, y_std, device, batch_size=64):
    """Predict with BERTCatHeadRegressor (passes cat_ids per sample)."""
    model.eval()
    ids   = encodings["input_ids"]
    mask  = encodings["attention_mask"]
    cat_t = torch.LongTensor(cat_labels)
    y_mean_d = y_mean.to(device) if hasattr(y_mean, "to") else torch.tensor(y_mean).to(device)
    y_std_d  = y_std.to(device)  if hasattr(y_std,  "to") else torch.tensor(y_std).to(device)
    preds = []
    with torch.no_grad():
        for i in range(0, len(ids), batch_size):
            b_ids  = ids[i:i+batch_size].to(device)
            b_mask = mask[i:i+batch_size].to(device)
            b_cat  = cat_t[i:i+batch_size].to(device)
            if device.type == "cuda":
                with autocast(device_type="cuda"):
                    out = model(b_ids, b_mask, cat_ids=b_cat)
            else:
                out = model(b_ids, b_mask, cat_ids=b_cat)
            pred = out[0] if isinstance(out, tuple) else out
            pred_vnd = torch.expm1(pred.float() * y_std_d + y_mean_d).clamp(min=0)
            preds.append(pred_vnd.cpu().numpy().flatten())
    return np.concatenate(preds)


def predict_bert_v7(model, encodings, y_mean, y_std, device, batch_size=64):
    """Predict with v7-style model (single shared price head, no cat_ids)."""
    model.eval()
    ids  = encodings["input_ids"]
    mask = encodings["attention_mask"]
    y_mean_d = y_mean.to(device) if hasattr(y_mean, "to") else torch.tensor(y_mean).to(device)
    y_std_d  = y_std.to(device)  if hasattr(y_std,  "to") else torch.tensor(y_std).to(device)
    preds = []
    with torch.no_grad():
        for i in range(0, len(ids), batch_size):
            b_ids  = ids[i:i+batch_size].to(device)
            b_mask = mask[i:i+batch_size].to(device)
            if device.type == "cuda":
                with autocast(device_type="cuda"):
                    out = model(b_ids, b_mask)
            else:
                out = model(b_ids, b_mask)
            pred = out[0] if isinstance(out, tuple) else out
            pred_vnd = torch.expm1(pred.float() * y_std_d + y_mean_d).clamp(min=0)
            preds.append(pred_vnd.cpu().numpy().flatten())
    return np.concatenate(preds)


def extract_embeddings_bert(model, encodings, cache_path, device, batch_size=64):
    """Extract mean-pooled embeddings (works for both v7 and v8 model classes)."""
    if cache_path.exists():
        print(f"  Loading cache: {cache_path.name}")
        return np.load(cache_path)
    model.eval()
    ids  = encodings["input_ids"]
    mask = encodings["attention_mask"]
    inner = model.module if isinstance(model, AveragedModel) else model
    embeddings = []
    with torch.no_grad():
        for i in range(0, len(ids), batch_size):
            b_ids  = ids[i:i+batch_size].to(device)
            b_mask = mask[i:i+batch_size].to(device)
            emb = inner.extract_embeddings(b_ids, b_mask)
            embeddings.append(emb.cpu().numpy())
    embeddings = np.concatenate(embeddings).astype(np.float32)
    np.save(cache_path, embeddings)
    print(f"  Saved: {cache_path.name} shape={embeddings.shape}")
    return embeddings


print("=== PHASE 2 HELPERS DEFINED ===")


# ============================================================
# PHASE 3: PhoBERT-large++ (LLRD + R-Drop + EMA + Huber + CatHeads + WeightedSampler)
# ============================================================

# %% [markdown]
# ## Phase 3: PhoBERT-large++ Training
#
# vinai/phobert-large: 370M params, 24 layers, 1024d hidden.
# Baseline from v7: AITeamVN 568M batch=32 no-R-Drop = 7.8/24GB.
# PhoBERT-large 370M batch=48 R-Drop (2x forward) ≈ 13GB — gradient_checkpointing OFF.
# GC disabled: saves 20-30% training time, VRAM still safe.

# %% Train PhoBERT-large++
print("\n" + "#" * 60)
print("# Phase 3: PhoBERT-large++ (370M, 24L, gradient_checkpointing)")
print("#" * 60)

PBL_V8_PATH = WEIGHTS_V8 / "phobert_large_v8.pth"
PBL_EMB = {
    "train": WEIGHTS_V8 / "pbl_v8_emb_train.npy",
    "val":   WEIGHTS_V8 / "pbl_v8_emb_val.npy",
    "test":  WEIGHTS_V8 / "pbl_v8_emb_test.npy",
}

if PBL_V8_PATH.exists():
    print("Loading saved PhoBERT-large++ weights...")
    model_pbl = BERTCatHeadRegressor(
        PHOBERT_LARGE_NAME, NUM_CATEGORIES, dropout=DROPOUT,
        use_gradient_checkpointing=False,  # not needed for inference
    )
    ema_pbl = AveragedModel(model_pbl, multi_avg_fn=get_ema_multi_avg_fn(EMA_DECAY))
    ckpt = torch.load(PBL_V8_PATH, map_location=DEVICE, weights_only=False)
    ema_pbl.load_state_dict(ckpt["ema_state_dict"])
    ema_pbl.to(DEVICE)
    y_mean_pbl, y_std_pbl = ckpt["y_mean"], ckpt["y_std"]
    hist_pbl = ckpt.get("history")
    print(f"  Loaded: {PBL_V8_PATH.name}")
else:
    model_pbl = BERTCatHeadRegressor(
        PHOBERT_LARGE_NAME, NUM_CATEGORIES, dropout=DROPOUT,
        use_gradient_checkpointing=False,  # disabled: batch=48 uses ~13GB, safe on 24GB
    )
    ema_pbl, y_mean_pbl, y_std_pbl, hist_pbl = train_bert_v8(
        model_pbl, pbl_enc_train, pbl_enc_val,
        train_prices, val_prices,
        cat_label_train, cat_label_val, DEVICE,
        epochs=EPOCHS, batch_size=PHOBERT_LARGE_BATCH, base_lr=BASE_LR,
        patience=PATIENCE, use_rdrop=True, use_weighted_sampler=True,
    )
    torch.save({
        "ema_state_dict": ema_pbl.state_dict(),
        "y_mean": y_mean_pbl, "y_std": y_std_pbl, "history": hist_pbl,
    }, PBL_V8_PATH)
    print(f"  Saved: {PBL_V8_PATH.name}")

# %% Evaluate PhoBERT-large++
pred_pbl_val  = predict_bert_v8(ema_pbl, pbl_enc_val,  cat_label_val,  y_mean_pbl, y_std_pbl, DEVICE)
pred_pbl_test = predict_bert_v8(ema_pbl, pbl_enc_test, cat_label_test, y_mean_pbl, y_std_pbl, DEVICE)
ALL_PREDS_VAL["v8-PhoBERT-large++"]  = pred_pbl_val
ALL_PREDS_TEST["v8-PhoBERT-large++"] = pred_pbl_test
evaluate_and_store(test_prices, pred_pbl_test,
                   "v8-PhoBERT-large++: 370M+LLRD+R-Drop+EMA+CatHead+Sampler", test_names)
if hist_pbl:
    plot_bert_history(hist_pbl, "v8 PhoBERT-large++ Training")

# %% Extract PhoBERT-large++ embeddings (for PCA+LGB in Phase 5)
print("\n--- Extract PhoBERT-large++ embeddings ---")
pbl_emb_train = extract_embeddings_bert(ema_pbl, pbl_enc_train, PBL_EMB["train"], DEVICE)
pbl_emb_val   = extract_embeddings_bert(ema_pbl, pbl_enc_val,   PBL_EMB["val"],   DEVICE)
pbl_emb_test  = extract_embeddings_bert(ema_pbl, pbl_enc_test,  PBL_EMB["test"],  DEVICE)

# Free GPU
ema_pbl.cpu()
del model_pbl, ema_pbl
torch.cuda.empty_cache()
gc.collect()


# ============================================================
# PHASE 4: mDeBERTa-v3-base++ (LLRD + EMA + Huber + CatHeads + WeightedSampler)
# ============================================================

# %% [markdown]
# ## Phase 4: mDeBERTa-v3-base++ Training
#
# microsoft/mdeberta-v3-base: 184M params, 12 layers, 768d.
# Disentangled attention (position + content separate).
# No R-Drop (architecture difference from BERT-style attention).
# batch=80 on 3090 Ti 24GB.

# %% Train mDeBERTa-v3-base++
print("\n" + "#" * 60)
print("# Phase 4: mDeBERTa-v3-base++ (184M, disentangled attention)")
print("#" * 60)

DEB_V8_PATH = WEIGHTS_V8 / "deberta_v8.pth"

if DEB_V8_PATH.exists():
    print("Loading saved mDeBERTa++ weights...")
    model_deb = BERTCatHeadRegressor(DEBERTA_NAME, NUM_CATEGORIES, dropout=DROPOUT)
    ema_deb   = AveragedModel(model_deb, multi_avg_fn=get_ema_multi_avg_fn(EMA_DECAY))
    ckpt = torch.load(DEB_V8_PATH, map_location=DEVICE, weights_only=False)
    ema_deb.load_state_dict(ckpt["ema_state_dict"])
    ema_deb.to(DEVICE)
    y_mean_deb, y_std_deb = ckpt["y_mean"], ckpt["y_std"]
    hist_deb = ckpt.get("history")
    print(f"  Loaded: {DEB_V8_PATH.name}")
else:
    model_deb = BERTCatHeadRegressor(DEBERTA_NAME, NUM_CATEGORIES, dropout=DROPOUT)
    ema_deb, y_mean_deb, y_std_deb, hist_deb = train_bert_v8(
        model_deb, deb_enc_train, deb_enc_val,
        train_prices, val_prices,
        cat_label_train, cat_label_val, DEVICE,
        epochs=EPOCHS, batch_size=DEBERTA_BATCH, base_lr=BASE_LR,
        patience=PATIENCE, use_rdrop=False,  # no R-Drop for DeBERTa
        use_weighted_sampler=True,
    )
    torch.save({
        "ema_state_dict": ema_deb.state_dict(),
        "y_mean": y_mean_deb, "y_std": y_std_deb, "history": hist_deb,
    }, DEB_V8_PATH)
    print(f"  Saved: {DEB_V8_PATH.name}")

# %% Evaluate mDeBERTa++
pred_deb_val  = predict_bert_v8(ema_deb, deb_enc_val,  cat_label_val,  y_mean_deb, y_std_deb, DEVICE)
pred_deb_test = predict_bert_v8(ema_deb, deb_enc_test, cat_label_test, y_mean_deb, y_std_deb, DEVICE)
ALL_PREDS_VAL["v8-mDeBERTa++"]  = pred_deb_val
ALL_PREDS_TEST["v8-mDeBERTa++"] = pred_deb_test
evaluate_and_store(test_prices, pred_deb_test,
                   "v8-mDeBERTa++: 184M+LLRD+EMA+CatHead+Sampler", test_names)
if hist_deb:
    plot_bert_history(hist_deb, "v8 mDeBERTa++ Training")

# Free GPU
ema_deb.cpu()
del model_deb, ema_deb
torch.cuda.empty_cache()
gc.collect()


# ============================================================
# PHASE 5: RELOAD v7 POOL + TRANSDUCTIVE PCA + PCA+LGB
# ============================================================

# %% [markdown]
# ## Phase 5: Reload v7 Pool + Transductive PCA + PCA+LGB

# %% 5a: Reload v7 BERT models (if available)
print("\n" + "#" * 60)
print("# Phase 5: Reload v7 pool + PCA+LGB")
print("#" * 60)

def try_load_v7_bert(model_name, weight_path, enc_val, enc_test,
                     cat_val_np, cat_test_np, pool_key):
    """Load a v7 EMA model and add its predictions to the pool."""
    if not weight_path.exists():
        print(f"  SKIP {pool_key}: {weight_path.name} not found")
        return False
    print(f"\n--- Loading {pool_key} from {weight_path.name} ---")
    base = BERTMultiTaskRegressorV7(model_name, NUM_CATEGORIES, dropout=DROPOUT)
    ema  = AveragedModel(base, multi_avg_fn=get_ema_multi_avg_fn(EMA_DECAY))
    ckpt = torch.load(weight_path, map_location=DEVICE, weights_only=False)
    ema.load_state_dict(ckpt["ema_state_dict"])
    ema.to(DEVICE)
    y_m, y_s = ckpt["y_mean"], ckpt["y_std"]
    pv = predict_bert_v7(ema, enc_val,  y_m, y_s, DEVICE)
    pt = predict_bert_v7(ema, enc_test, y_m, y_s, DEVICE)
    ALL_PREDS_VAL[pool_key]  = pv
    ALL_PREDS_TEST[pool_key] = pt
    print(f"  {pool_key} test RMSLE: {rmsle(test_prices, pt):.4f}")
    ema.cpu()
    del base, ema
    torch.cuda.empty_cache()
    gc.collect()
    return True

# PhoBERT-base++ from v7
phobert_v7_tokenizer = AutoTokenizer.from_pretrained(PHOBERT_BASE_NAME)
tok_val_pb = phobert_v7_tokenizer(tok_val,  truncation=True, padding="max_length",
                                   max_length=256, return_tensors="pt")
tok_test_pb = phobert_v7_tokenizer(tok_test, truncation=True, padding="max_length",
                                    max_length=256, return_tensors="pt")
try_load_v7_bert(PHOBERT_BASE_NAME, WEIGHTS_V7 / "phobert_v7.pth",
                 tok_val_pb, tok_test_pb, cat_label_val, cat_label_test, "v7-PhoBERT++")

# XLM-R++ from v7
xlmr_tokenizer = AutoTokenizer.from_pretrained(XLMR_NAME)
xlmr_enc_val  = xlmr_tokenizer(val_summaries,  truncation=True, padding="max_length",
                                max_length=256, return_tensors="pt")
xlmr_enc_test = xlmr_tokenizer(test_summaries, truncation=True, padding="max_length",
                                max_length=256, return_tensors="pt")
try_load_v7_bert(XLMR_NAME, WEIGHTS_V7 / "xlmr_v7.pth",
                 xlmr_enc_val, xlmr_enc_test, cat_label_val, cat_label_test, "v7-XLM-R++")

# AITeamVN++ from v7
aiteamvn_tokenizer = AutoTokenizer.from_pretrained(AITEAMVN_NAME)
at_enc_val  = aiteamvn_tokenizer(val_summaries,  truncation=True, padding="max_length",
                                  max_length=256, return_tensors="pt")
at_enc_test = aiteamvn_tokenizer(test_summaries, truncation=True, padding="max_length",
                                  max_length=256, return_tensors="pt")
try_load_v7_bert(AITEAMVN_NAME, WEIGHTS_V7 / "aiteamvn_v7.pth",
                 at_enc_val, at_enc_test, cat_label_val, cat_label_test, "v7-AITeamVN++")

del tok_val_pb, tok_test_pb, xlmr_enc_val, xlmr_enc_test, at_enc_val, at_enc_test
torch.cuda.empty_cache(); gc.collect()

# %% 5b: v4-2b (AITeamVN frozen + MLP)
print("\n--- v4-2b: AITeamVN frozen + MLP ---")
V4_2B_PATH = WEIGHTS_V4 / "model_2b_mlp_aiteamvn.pth"
if V4_2B_PATH.exists() and "train" in at_emb_frozen:
    ckpt_2b = torch.load(V4_2B_PATH, map_location=DEVICE, weights_only=False)
    model_2b = MLP(input_dim=1024, hidden_dims=[512, 256, 128], dropout=0.3)
    model_2b.load_state_dict(ckpt_2b["model_state"])
    model_2b.to(DEVICE).eval()
    y_m2b, y_s2b = ckpt_2b["y_mean"], ckpt_2b["y_std"]
    pred_2b_val  = predict_batch(model_2b, torch.FloatTensor(at_emb_frozen["val"]),
                                 y_m2b, y_s2b, DEVICE)
    pred_2b_test = predict_batch(model_2b, torch.FloatTensor(at_emb_frozen["test"]),
                                 y_m2b, y_s2b, DEVICE)
    ALL_PREDS_VAL["v4-2b"]  = pred_2b_val
    ALL_PREDS_TEST["v4-2b"] = pred_2b_test
    print(f"  v4-2b test RMSLE: {rmsle(test_prices, pred_2b_test):.4f}")
    del model_2b
    torch.cuda.empty_cache()
else:
    print(f"  SKIP v4-2b: weights or embeddings not found")

# %% 5c: v4-0a (DNN + HashingVec)
print("\n--- v4-0a: DNN + HashingVec ---")
V4_0A_PATH = WEIGHTS_V4 / "model_0a_dnn_hv2048.pth"
if V4_0A_PATH.exists():
    ckpt_0a = torch.load(V4_0A_PATH, map_location=DEVICE, weights_only=False)
    model_0a = DeepNeuralNetwork(input_dim=5000)
    model_0a.load_state_dict(ckpt_0a["model_state"])
    model_0a.to(DEVICE).eval()
    y_m0a, y_s0a = ckpt_0a["y_mean"], ckpt_0a["y_std"]
    X_hv_val_cat  = hstack([X_hv_val,  cat_val]).toarray().astype(np.float32)
    X_hv_test_cat = hstack([X_hv_test, cat_test]).toarray().astype(np.float32)
    pred_0a_val  = predict_batch(model_0a, torch.FloatTensor(X_hv_val_cat),  y_m0a, y_s0a, DEVICE)
    pred_0a_test = predict_batch(model_0a, torch.FloatTensor(X_hv_test_cat), y_m0a, y_s0a, DEVICE)
    ALL_PREDS_VAL["v4-0a"]  = pred_0a_val
    ALL_PREDS_TEST["v4-0a"] = pred_0a_test
    print(f"  v4-0a test RMSLE: {rmsle(test_prices, pred_0a_test):.4f}")
    del model_0a, X_hv_val_cat, X_hv_test_cat
    torch.cuda.empty_cache()
else:
    print(f"  SKIP v4-0a: {V4_0A_PATH.name} not found")

# %% 5d: Day3-LGB
print("\n--- Day3-LGB ---")
LGB_DAY3_PATH = next(
    (p for p in [WEIGHTS_V7 / "lgb_day3_retrain.pkl",
                 WEIGHTS_V6 / "lgb_day3_retrain.pkl",
                 WEIGHTS_V5 / "lgb_day3_retrain.pkl"]
     if p.exists()), None
)
DAY3_LGB_PARAMS = dict(
    n_estimators=1500, num_leaves=173, min_child_samples=50,
    feature_fraction=0.689, lambda_l1=0.011, lambda_l2=0.155,
    learning_rate=0.032, random_state=SEED, n_jobs=6, verbose=-1,
)
if LGB_DAY3_PATH:
    lgb_day3 = joblib.load(LGB_DAY3_PATH)
    print(f"  Loaded Day3-LGB from {LGB_DAY3_PATH}")
else:
    print("  Retraining Day3-LGB (Arch C + category)...")
    lgb_day3 = lgb.LGBMRegressor(**DAY3_LGB_PARAMS)
    lgb_day3.fit(X_cc_train, np.log1p(train_prices))
    joblib.dump(lgb_day3, WEIGHTS_V8 / "lgb_day3_retrain.pkl")
    print("  Saved: lgb_day3_retrain.pkl")
pred_day3_val  = np.expm1(lgb_day3.predict(X_cc_val))
pred_day3_test = np.expm1(lgb_day3.predict(X_cc_test))
ALL_PREDS_VAL["Day3-LGB"]  = pred_day3_val
ALL_PREDS_TEST["Day3-LGB"] = pred_day3_test
print(f"  Day3-LGB test RMSLE: {rmsle(test_prices, pred_day3_test):.4f}")

# %% 5e: v7-PCA+LGB (if saved) or retrain with PhoBERT-large++ embeddings (v8-PCA+LGB)
print("\n--- v8-PCA+LGB: PhoBERT-large++ embed + Transductive PCA(256) + LGB ---")

V8_PCA_LGB_PATH = WEIGHTS_V8 / "lgb_v8_pbl_pca.pkl"
V8_PCA_PATH     = WEIGHTS_V8 / "pca_v8_transductive.pkl"

# Transductive PCA: fit on train+val+test to align embedding space
if V8_PCA_PATH.exists():
    pca_trans = joblib.load(V8_PCA_PATH)
    print(f"  Loaded transductive PCA: {V8_PCA_PATH.name}")
else:
    print("  Fitting transductive PCA(256) on train+val+test embeddings...")
    all_embs = np.vstack([pbl_emb_train, pbl_emb_val, pbl_emb_test])
    pca_trans = PCA(n_components=256, random_state=SEED)
    pca_trans.fit(all_embs)
    joblib.dump(pca_trans, V8_PCA_PATH)
    expl = pca_trans.explained_variance_ratio_.sum()
    print(f"  PCA fitted: 256 components, {expl:.1%} variance explained")
    del all_embs
    gc.collect()

X_pca_train = pca_trans.transform(pbl_emb_train).astype(np.float32)
X_pca_val   = pca_trans.transform(pbl_emb_val).astype(np.float32)
X_pca_test  = pca_trans.transform(pbl_emb_test).astype(np.float32)

# Append category one-hot
X_pca_cat_train = np.hstack([X_pca_train, cat_train.toarray().astype(np.float32)])
X_pca_cat_val   = np.hstack([X_pca_val,   cat_val_dense])
X_pca_cat_test  = np.hstack([X_pca_test,  cat_test_dense])

V7_PCA_LGB_PATH = WEIGHTS_V7 / "lgb_v7_phobert_pca.pkl"
if V8_PCA_LGB_PATH.exists():
    lgb_pca = joblib.load(V8_PCA_LGB_PATH)
    print(f"  Loaded: {V8_PCA_LGB_PATH.name}")
elif V7_PCA_LGB_PATH.exists():
    # Reuse v7 LGB params but refit on v8 PCA features
    print("  Refitting LGB on v8 transductive PCA features (v7 params)...")
    v7_lgb_params = json.load(open(WEIGHTS_V6 / "lgb_v6_best_params.json")) \
        if (WEIGHTS_V6 / "lgb_v6_best_params.json").exists() else {}
    lgb_pca = lgb.LGBMRegressor(
        n_estimators=1000, num_leaves=127, min_child_samples=30,
        feature_fraction=0.8, lambda_l2=0.1, learning_rate=0.05,
        random_state=SEED, n_jobs=6, verbose=-1,
        **{k: v for k, v in v7_lgb_params.items()
           if k not in ("n_estimators", "random_state", "verbose", "n_jobs")}
    )
    lgb_pca.fit(X_pca_cat_train, np.log1p(train_prices))
    joblib.dump(lgb_pca, V8_PCA_LGB_PATH)
    print(f"  Saved: {V8_PCA_LGB_PATH.name}")
else:
    print("  Training LGB on v8-PCA features (default params)...")
    lgb_pca = lgb.LGBMRegressor(
        n_estimators=1000, num_leaves=127, min_child_samples=30,
        feature_fraction=0.8, lambda_l2=0.1, learning_rate=0.05,
        random_state=SEED, n_jobs=6, verbose=-1,
    )
    lgb_pca.fit(X_pca_cat_train, np.log1p(train_prices))
    joblib.dump(lgb_pca, V8_PCA_LGB_PATH)
    print(f"  Saved: {V8_PCA_LGB_PATH.name}")

pred_pca_val  = np.expm1(lgb_pca.predict(X_pca_cat_val))
pred_pca_test = np.expm1(lgb_pca.predict(X_pca_cat_test))
ALL_PREDS_VAL["v8-PCA+LGB"]  = pred_pca_val
ALL_PREDS_TEST["v8-PCA+LGB"] = pred_pca_test
evaluate_and_store(test_prices, pred_pca_test,
                   "v8-PCA+LGB: PhoBERT-large++ embed + transductive PCA + LGB", test_names)

del pbl_emb_train, X_pca_train, X_pca_cat_train
gc.collect()

print(f"\n=== STACKING POOL: {len(ALL_PREDS_VAL)} models ===")
for name in ALL_PREDS_VAL:
    print(f"  {name:35s}: test RMSLE = {rmsle(test_prices, ALL_PREDS_TEST[name]):.4f}")


# ============================================================
# PHASE 6: STACKING META-LEARNERS (FIXED LGB EARLY STOPPING)
# ============================================================

# %% [markdown]
# ## Phase 6: Stacking Meta-learners
#
# Meta-train: val predictions (3,926 items x N_models, log-space).
# Meta-test:  test predictions (3,872 items x N_models, log-space).
#
# Fix vs v7: LGB meta uses held-out 20% of val for early stopping
# instead of training on val and evaluating on the same val set.

# %% Stacking setup
print("\n" + "#" * 60)
print("# Phase 6: Stacking Meta-learners (Ridge + ElasticNet + LGB)")
print("#" * 60)

base_names = list(ALL_PREDS_VAL.keys())
print(f"\n  Base models ({len(base_names)}): {base_names}")

X_meta_val_log  = np.column_stack([np.log1p(ALL_PREDS_VAL[n])  for n in base_names])
X_meta_test_log = np.column_stack([np.log1p(ALL_PREDS_TEST[n]) for n in base_names])
y_val_log_np    = np.log1p(val_prices)

print(f"  Meta features: val {X_meta_val_log.shape}, test {X_meta_test_log.shape}")

# %% Meta 1: Ridge
print("\n--- Meta 1: Ridge (alpha=1.0) ---")
ridge = Ridge(alpha=1.0, random_state=SEED)
ridge.fit(X_meta_val_log, y_val_log_np)
pred_ridge_val  = np.clip(np.expm1(ridge.predict(X_meta_val_log)),  0, None)
pred_ridge_test = np.clip(np.expm1(ridge.predict(X_meta_test_log)), 0, None)
print(f"  Ridge val RMSLE:  {rmsle(val_prices, pred_ridge_val):.4f}")
print(f"  Ridge test RMSLE: {rmsle(test_prices, pred_ridge_test):.4f}")
print(f"  Coefs: {dict(zip(base_names, ridge.coef_.round(3)))}")

# %% Meta 2: ElasticNet
print("\n--- Meta 2: ElasticNet (alpha=0.001, l1=0.5) ---")
enet = ElasticNet(alpha=0.001, l1_ratio=0.5, random_state=SEED, max_iter=5000)
enet.fit(X_meta_val_log, y_val_log_np)
pred_enet_val  = np.clip(np.expm1(enet.predict(X_meta_val_log)),  0, None)
pred_enet_test = np.clip(np.expm1(enet.predict(X_meta_test_log)), 0, None)
print(f"  ElasticNet val RMSLE:  {rmsle(val_prices, pred_enet_val):.4f}")
print(f"  ElasticNet test RMSLE: {rmsle(test_prices, pred_enet_test):.4f}")
print(f"  Coefs: {dict(zip(base_names, enet.coef_.round(3)))}")

# %% Meta 3: LGB — FIXED early stopping (held-out 20% of val)
print("\n--- Meta 3: LightGBM (held-out 20% val for early stopping) ---")
n_meta  = len(X_meta_val_log)
n_train_meta = int(n_meta * 0.8)   # 3140 samples for meta-train
# Use stratified split by price bin to maintain distribution
log_p_bins = pd.qcut(y_val_log_np, q=5, labels=False, duplicates="drop")
from sklearn.model_selection import train_test_split
idx_meta_tr, idx_meta_es = train_test_split(
    np.arange(n_meta), test_size=0.2, random_state=SEED, stratify=log_p_bins
)
X_lgb_tr, X_lgb_es = X_meta_val_log[idx_meta_tr], X_meta_val_log[idx_meta_es]
y_lgb_tr, y_lgb_es = y_val_log_np[idx_meta_tr],    y_val_log_np[idx_meta_es]

lgb_meta = lgb.LGBMRegressor(
    n_estimators=300, num_leaves=15, min_child_samples=20,
    learning_rate=0.03, feature_fraction=0.9, bagging_fraction=0.9,
    bagging_freq=3, lambda_l2=1.0, random_state=SEED, n_jobs=6, verbose=-1,
)
lgb_meta.fit(
    X_lgb_tr, y_lgb_tr,
    eval_set=[(X_lgb_es, y_lgb_es)],
    callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(0)],
)
pred_lgb_meta_val  = np.clip(np.expm1(lgb_meta.predict(X_meta_val_log)),  0, None)
pred_lgb_meta_test = np.clip(np.expm1(lgb_meta.predict(X_meta_test_log)), 0, None)
print(f"  LGB-meta val RMSLE:  {rmsle(val_prices, pred_lgb_meta_val):.4f}")
print(f"  LGB-meta test RMSLE: {rmsle(test_prices, pred_lgb_meta_test):.4f}")
print(f"  Best iteration: {lgb_meta.best_iteration_}")

# %% Final: Average of 3 meta-learners
print("\n--- Final: Average(Ridge, ElasticNet, LGB-meta) ---")
pred_stacked_val  = (pred_ridge_val  + pred_enet_val  + pred_lgb_meta_val)  / 3
pred_stacked_test = (pred_ridge_test + pred_enet_test + pred_lgb_meta_test) / 3
ALL_PREDS_VAL["v8 Stacked"]  = pred_stacked_val
ALL_PREDS_TEST["v8 Stacked"] = pred_stacked_test
evaluate_and_store(test_prices, pred_stacked_test,
                   "v8: Stacked (Ridge+EN+LGB avg)", test_names)

# %% Weighted blend baseline for comparison
print("\n--- Baseline: Weighted Blend (scipy.minimize on val) ---")
blend_val  = [ALL_PREDS_VAL[n]  for n in base_names]
blend_test = [ALL_PREDS_TEST[n] for n in base_names]

def blend_objective(w):
    w = np.abs(w) / np.abs(w).sum()
    return rmsle(val_prices, sum(wi * p for wi, p in zip(w, blend_val)))

res = scipy_minimize(blend_objective, x0=np.ones(len(base_names)) / len(base_names),
                     method="Nelder-Mead", options={"maxiter": 5000})
opt_w = np.abs(res.x) / np.abs(res.x).sum()
print(f"  Blend val RMSLE: {res.fun:.4f}")
print(f"  Weights: {dict(zip(base_names, opt_w.round(3)))}")
blend_test_pred = sum(w * p for w, p in zip(opt_w, blend_test))
ALL_PREDS_TEST["v8 Weighted Blend"] = blend_test_pred
evaluate_and_store(test_prices, blend_test_pred, "v8: Weighted Blend", test_names)

# %% Save stacking config
stacking_config = {
    "base_models":      base_names,
    "ridge_coefs":      dict(zip(base_names, ridge.coef_.tolist())),
    "enet_coefs":       dict(zip(base_names, enet.coef_.tolist())),
    "lgb_best_iter":    int(lgb_meta.best_iteration_) if lgb_meta.best_iteration_ else 300,
    "blend_weights":    dict(zip(base_names, opt_w.tolist())),
    "stacked_test_rmsle": ALL_RESULTS["v8: Stacked (Ridge+EN+LGB avg)"]["rmsle"],
    "blend_test_rmsle":   ALL_RESULTS["v8: Weighted Blend"]["rmsle"],
}
with open(WEIGHTS_V8 / "stacking_config_v8.json", "w") as f:
    json.dump(stacking_config, f, indent=2, ensure_ascii=False)
print(f"\n  Saved: {WEIGHTS_V8 / 'stacking_config_v8.json'}")


# ============================================================
# PHASE 7: FINAL SUMMARY + CHARTS
# ============================================================

# %% [markdown]
# ## Phase 7: Final Summary

# %% Add historical baselines for comparison
print("\n" + "=" * 70)
print("FINAL RESULTS — Day 4 v8")
print("=" * 70)

ALL_RESULTS["Baseline: v6 Blended"]     = {"rmsle": 0.4187, "mae": 82_766,  "mape": 33.2, "r2": 67.6}
ALL_RESULTS["Baseline: v5-old Blended"] = {"rmsle": 0.4191, "mae": 84_550,  "mape": 33.6, "r2": 67.2}
ALL_RESULTS["Baseline: v4 AITeamVN+MLP"]= {"rmsle": 0.4986, "mae": 99_786,  "mape": 39.0, "r2": 55.3}
ALL_RESULTS["Baseline: Day3 Blended"]   = {"rmsle": 0.5164, "mae": 109_725, "mape": 44.0, "r2": 47.1}

df = pd.DataFrame(ALL_RESULTS).T.sort_values("rmsle")
df.index.name = "Model"
print(df.to_string(formatters={
    "rmsle": "{:.4f}".format, "mae": "{:,.0f}".format,
    "mape": "{:.1f}%".format, "r2": "{:.1f}%".format,
}))

best_name  = df.index[0]
best_rmsle = df.iloc[0]["rmsle"]
print(f"\nBest model: {best_name} (RMSLE={best_rmsle:.4f})")
print(f"vs v6 Blended (0.4187): {(0.4187 - best_rmsle) / 0.4187 * 100:+.1f}%")
print(f"vs Target (0.38):       {'ACHIEVED' if best_rmsle <= 0.38 else f'gap {best_rmsle - 0.38:.4f}'}")
print(f"vs Target (0.40):       {'ACHIEVED' if best_rmsle <= 0.40 else f'gap {best_rmsle - 0.40:.4f}'}")

with open(WEIGHTS_V8 / "v8_results.json", "w") as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False)
print(f"\nResults saved: {WEIGHTS_V8 / 'v8_results.json'}")

# %% RMSLE comparison chart
fig = go.Figure()
colors = ["mediumseagreen" if r <= 0.38 else "steelblue" if r <= 0.40
          else "orange" if r < 0.45 else "lightcoral"
          for r in df["rmsle"]]
fig.add_trace(go.Bar(
    x=df.index, y=df["rmsle"], marker_color=colors,
    text=[f"{v:.4f}" for v in df["rmsle"]], textposition="outside",
))
fig.add_hline(y=0.38,   line_dash="dash", line_color="mediumseagreen", annotation_text="v8 Target (0.38)")
fig.add_hline(y=0.40,   line_dash="dash", line_color="steelblue",      annotation_text="v7 Target (0.40)")
fig.add_hline(y=0.4187, line_dash="dash", line_color="red",            annotation_text="v6 Blended (0.4187)")
fig.update_layout(
    title="Day 4 v8: RMSLE Comparison (lower is better)",
    xaxis_title="Model", yaxis_title="RMSLE",
    width=1200, height=600, template="plotly_white", xaxis_tickangle=-30,
)
fig.show()

# %% Multi-metric chart
fig2 = make_subplots(rows=2, cols=2,
                     subplot_titles=("RMSLE (lower=better)", "MAE VND (lower=better)",
                                     "MAPE % (lower=better)", "R2 % (higher=better)"))
fig2.add_trace(go.Bar(x=df.index, y=df["rmsle"], marker_color="steelblue"),     row=1, col=1)
fig2.add_trace(go.Bar(x=df.index, y=df["mae"],   marker_color="tomato"),         row=1, col=2)
fig2.add_trace(go.Bar(x=df.index, y=df["mape"],  marker_color="orange"),         row=2, col=1)
fig2.add_trace(go.Bar(x=df.index, y=df["r2"],    marker_color="mediumseagreen"), row=2, col=2)
fig2.update_layout(title="Day 4 v8: All Metrics", width=1300, height=750,
                   template="plotly_white", showlegend=False)
fig2.update_xaxes(tickangle=-30)
fig2.show()

print("\n--- Day 4 v8 COMPLETE ---")
print(f"Weights saved in: {WEIGHTS_V8}")
print("Files:", [f.name for f in WEIGHTS_V8.iterdir()])
