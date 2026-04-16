# %% [markdown]
# # Day 4: Deep Learning Models — Vietnamese Price Prediction
#
# **6 model families, ~12 experiments:**
# - Model 0: DNN ResidualBlock (HashingVec / TF-IDF, hidden=2048->4096)
# - Model 1: PhoBERT-base-v2 fine-tune (regression head)
# - Model 2: Vietnamese Embedding + MLP (dangvantuan / AITeamVN)
# - Model 3: XLM-RoBERTa-base fine-tune (multilingual)
# - Model 4: Vietnamese Embedding + LightGBM (hybrid DL+ML)
# - Model 5: Vietnamese Embedding + DNN ResidualBlock
#
# **Dataset:** SeanSunny/items_tv_v6 filtered <= 1M VND
# **Baseline (Day 3):** Blended RMSLE=0.5164

# %% Imports
import os
import sys
import json
import joblib
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.sparse import hstack

os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

# Notebook: dung Path.cwd() thay vi __file__
DAY4 = Path.cwd()
sys.path.insert(0, str(DAY4.parent))
from pricer_vi.items import Item
from pricer_vi.deep_neural_network import (
    DeepNeuralNetwork, MLP, train_torch_model, predict_batch, plot_training_history,
)

# %% Config
DATASET = "SeanSunny/items_tv_v6"
MAX_PRICE = 1_000_000
SEED = 42
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)

print(f"Device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"GPU: {torch.cuda.get_device_name()}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

ALL_RESULTS = {}
ALL_HISTORIES = {}

WEIGHTS_DIR = DAY4 / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)


def save_torch_weights(model, y_mean, y_std, name):
    """Save model state_dict + normalization params."""
    path = WEIGHTS_DIR / f"{name}.pth"
    torch.save({"state_dict": model.state_dict(), "y_mean": y_mean, "y_std": y_std}, path)
    print(f"  Saved weights: {path.name}")


def load_torch_weights(model, name, device):
    """Load model state_dict + normalization params. Returns (model, y_mean, y_std) or None."""
    path = WEIGHTS_DIR / f"{name}.pth"
    if not path.exists():
        return None
    ckpt = torch.load(path, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["state_dict"])
    model.to(device)
    print(f"  Loaded weights: {path.name}")
    return model, ckpt["y_mean"], ckpt["y_std"]


# %% Helper: metrics
def rmsle(y_true, y_pred):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.clip(np.array(y_pred, dtype=float), 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def mape(y_true, y_pred):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    mask = y_true > 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate_batch(y_true, y_pred, name="Model"):
    """Evaluate predictions, print metrics, store in ALL_RESULTS."""
    r = {
        "rmsle": rmsle(y_true, y_pred),
        "mae": mean_absolute_error(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "r2": r2_score(y_true, y_pred) * 100,
    }
    print(f"\n{'='*60}")
    print(f"{name} ({len(y_true)} items)")
    print(f"  RMSLE:  {r['rmsle']:.4f}")
    print(f"  MAE:    {r['mae']:,.0f} VND")
    print(f"  MAPE:   {r['mape']:.1f}%")
    print(f"  R2:     {r['r2']:.1f}%")
    print(f"{'='*60}")
    ALL_RESULTS[name] = r
    return r


# ============================================================
# PHASE 1: LOAD DATA + TOKENIZE + EMBED + VECTORIZE (CACHE)
# ============================================================

# %% Phase 1a: Load data from HuggingFace
print("\n--- Phase 1a: Loading data ---")
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

# %% Phase 1b: Category one-hot encoding
print("\n--- Phase 1b: Category one-hot ---")
cat_encoder = OneHotEncoder(sparse_output=True, handle_unknown="ignore")
cat_train = cat_encoder.fit_transform(np.array(train_categories).reshape(-1, 1))
cat_val = cat_encoder.transform(np.array(val_categories).reshape(-1, 1))
cat_test = cat_encoder.transform(np.array(test_categories).reshape(-1, 1))
print(f"Categories: {cat_encoder.categories_[0].tolist()}")
print(f"One-hot features: {cat_train.shape[1]}")

# %% Phase 1c: Underthesea tokenize + cache
UNDERTHESEA_CACHE = {
    "train": DAY4 / "tokenized_train_1m.pkl",
    "val": DAY4 / "tokenized_val_1m.pkl",
    "test": DAY4 / "tokenized_test_1m.pkl",
}

DAY3 = DAY4.parent / "day3"

def load_or_tokenize_underthesea(summaries, cache_path, label=""):
    if cache_path.exists():
        print(f"  Loading underthesea cache: {cache_path.name}")
        return joblib.load(cache_path)
    day3_path = DAY3 / cache_path.name
    if day3_path.exists():
        print(f"  Loading Day 3 cache: {day3_path}")
        data = joblib.load(day3_path)
        joblib.dump(data, cache_path)
        return data
    print(f"  Tokenizing {label} ({len(summaries):,} docs) with underthesea...")
    from underthesea import word_tokenize
    tokenized = [word_tokenize(s, format="text") for s in summaries]
    joblib.dump(tokenized, cache_path)
    print(f"  Saved: {cache_path.name}")
    return tokenized

print("\n--- Phase 1c: Underthesea tokenize ---")
tok_train = load_or_tokenize_underthesea(train_summaries, UNDERTHESEA_CACHE["train"], "train")
tok_val = load_or_tokenize_underthesea(val_summaries, UNDERTHESEA_CACHE["val"], "val")
tok_test = load_or_tokenize_underthesea(test_summaries, UNDERTHESEA_CACHE["test"], "test")

# %% Phase 1d: pyvi tokenize + cache (for dangvantuan embedding)
PYVI_CACHE = {
    "train": DAY4 / "pyvi_tokenized_train.pkl",
    "val": DAY4 / "pyvi_tokenized_val.pkl",
    "test": DAY4 / "pyvi_tokenized_test.pkl",
}

def load_or_tokenize_pyvi(summaries, cache_path, label=""):
    if cache_path.exists():
        print(f"  Loading pyvi cache: {cache_path.name}")
        return joblib.load(cache_path)
    print(f"  Tokenizing {label} ({len(summaries):,} docs) with pyvi...")
    from pyvi.ViTokenizer import tokenize
    tokenized = [tokenize(s) for s in summaries]
    joblib.dump(tokenized, cache_path)
    print(f"  Saved: {cache_path.name}")
    return tokenized

print("\n--- Phase 1d: pyvi tokenize ---")
pyvi_train = load_or_tokenize_pyvi(train_summaries, PYVI_CACHE["train"], "train")
pyvi_val = load_or_tokenize_pyvi(val_summaries, PYVI_CACHE["val"], "val")
pyvi_test = load_or_tokenize_pyvi(test_summaries, PYVI_CACHE["test"], "test")

# %% Phase 1e: dangvantuan embedding extraction + cache
EMB_DV = {
    "train": DAY4 / "dangvantuan_train.npy",
    "val": DAY4 / "dangvantuan_val.npy",
    "test": DAY4 / "dangvantuan_test.npy",
}

def load_or_embed_dangvantuan(texts_dict, cache_dict):
    all_loaded = all(p.exists() for p in cache_dict.values())
    if all_loaded:
        print("  Loading dangvantuan cache...")
        return {k: np.load(v) for k, v in cache_dict.items()}

    print("  Loading dangvantuan/vietnamese-embedding model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("dangvantuan/vietnamese-embedding", device="cuda")
    model.max_seq_length = 256

    test_emb = model.encode(["test"], show_progress_bar=False)
    print(f"  Test encode OK: shape={test_emb.shape}, max_seq_length={model.max_seq_length}")

    result = {}
    for split, texts in texts_dict.items():
        path = cache_dict[split]
        if path.exists():
            print(f"  Loading cache: {path.name}")
            result[split] = np.load(path)
        else:
            print(f"  Encoding {split} ({len(texts):,} docs)...")
            emb = model.encode(texts, batch_size=64, show_progress_bar=True,
                               normalize_embeddings=True)
            np.save(path, emb.astype(np.float32))
            print(f"  Saved: {path.name} shape={emb.shape}")
            result[split] = emb
    del model
    torch.cuda.empty_cache()
    return result

print("\n--- Phase 1e: dangvantuan embeddings ---")
dv_emb = load_or_embed_dangvantuan(
    {"train": pyvi_train, "val": pyvi_val, "test": pyvi_test}, EMB_DV
)

# %% Phase 1f: AITeamVN embedding extraction + cache
EMB_AT = {
    "train": DAY4 / "aiteamvn_train.npy",
    "val": DAY4 / "aiteamvn_val.npy",
    "test": DAY4 / "aiteamvn_test.npy",
}

def load_or_embed_aiteamvn(texts_dict, cache_dict):
    all_loaded = all(p.exists() for p in cache_dict.values())
    if all_loaded:
        print("  Loading AITeamVN cache...")
        return {k: np.load(v) for k, v in cache_dict.items()}

    print("  Loading AITeamVN/Vietnamese_Embedding model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("AITeamVN/Vietnamese_Embedding", device="cuda")
    model.max_seq_length = 256

    test_emb = model.encode(["test"], show_progress_bar=False)
    print(f"  Test encode OK: shape={test_emb.shape}, max_seq_length={model.max_seq_length}")

    result = {}
    for split, texts in texts_dict.items():
        path = cache_dict[split]
        if path.exists():
            print(f"  Loading cache: {path.name}")
            result[split] = np.load(path)
        else:
            print(f"  Encoding {split} ({len(texts):,} docs)...")
            emb = model.encode(texts, batch_size=64, show_progress_bar=True)
            np.save(path, emb.astype(np.float32))
            print(f"  Saved: {path.name} shape={emb.shape}")
            result[split] = emb
    del model
    torch.cuda.empty_cache()
    return result

print("\n--- Phase 1f: AITeamVN embeddings ---")
at_emb = load_or_embed_aiteamvn(
    {"train": train_summaries, "val": val_summaries, "test": test_summaries}, EMB_AT
)

# %% Phase 1g: HashingVectorizer + cache
HV_CACHE = DAY4 / "hashing_vectorizer.pkl"

print("\n--- Phase 1g: HashingVectorizer ---")
if HV_CACHE.exists():
    hv = joblib.load(HV_CACHE)
    print("  Loaded HashingVectorizer cache")
else:
    hv = HashingVectorizer(n_features=5000, binary=True, alternate_sign=False)
    joblib.dump(hv, HV_CACHE)
    print("  Created HashingVectorizer (stateless)")

X_hv_train = hv.transform(train_summaries)
X_hv_val = hv.transform(val_summaries)
X_hv_test = hv.transform(test_summaries)
print(f"  HashingVec shape: {X_hv_train.shape}")

# %% Phase 1h: TF-IDF Vectorizer + cache
TFIDF_CACHE = DAY4 / "tfidf_vectorizer.pkl"

print("\n--- Phase 1h: TF-IDF Vectorizer ---")
if TFIDF_CACHE.exists():
    tfidf = joblib.load(TFIDF_CACHE)
    print("  Loaded TF-IDF cache")
    X_tfidf_train = tfidf.transform(tok_train)
else:
    tfidf = TfidfVectorizer(max_features=10_000, ngram_range=(1, 2), sublinear_tf=True)
    X_tfidf_train = tfidf.fit_transform(tok_train)
    joblib.dump(tfidf, TFIDF_CACHE)
    print("  Fitted TF-IDF and saved cache")

X_tfidf_val = tfidf.transform(tok_val)
X_tfidf_test = tfidf.transform(tok_test)
print(f"  TF-IDF shape: {X_tfidf_train.shape}")

# %% Phase 1 complete
print("\n" + "=" * 60)
print("PHASE 1 COMPLETE — All data loaded and cached")
print(f"  Underthesea tokenized: {len(tok_train):,} train")
print(f"  pyvi tokenized: {len(pyvi_train):,} train")
print(f"  dangvantuan embeddings: {dv_emb['train'].shape}")
print(f"  AITeamVN embeddings: {at_emb['train'].shape}")
print(f"  HashingVec: {X_hv_train.shape}")
print(f"  TF-IDF: {X_tfidf_train.shape}")
print("=" * 60)


# ============================================================
# PHASE 2: MODEL 0 — DNN ResidualBlock (bag-of-words)
# ============================================================

# %% Helper: prepare DNN data
def prepare_dnn_data(X_sparse, cat_sparse, prices, add_cat=True):
    """Convert sparse features + category to dense torch tensor."""
    if add_cat:
        X = hstack([X_sparse, cat_sparse]).toarray()
    else:
        X = X_sparse.toarray() if hasattr(X_sparse, 'toarray') else X_sparse
    return (
        torch.FloatTensor(X),
        torch.FloatTensor(prices).unsqueeze(1),
    )


# %% Phase 2: Model 0a — DNN + HashingVec (hidden=2048)
print("\n\n" + "#" * 60)
print("# MODEL 0a: DNN + HashingVec (hidden=2048)")
print("#" * 60)

X_tr, y_tr = prepare_dnn_data(X_hv_train, cat_train, train_prices)
X_va, y_va = prepare_dnn_data(X_hv_val, cat_val, val_prices)
X_te, y_te = prepare_dnn_data(X_hv_test, cat_test, test_prices)

model_0a = DeepNeuralNetwork(X_tr.shape[1], hidden_size=2048, num_layers=10)
cached = load_torch_weights(model_0a, "model_0a_dnn_hv2048", DEVICE)
if cached:
    model_0a, y_mean_0a, y_std_0a = cached
    hist_0a = None
else:
    model_0a, y_mean_0a, y_std_0a, hist_0a = train_torch_model(
        model_0a, X_tr, y_tr, X_va, y_va, DEVICE, epochs=5, batch_size=64
    )
    save_torch_weights(model_0a, y_mean_0a, y_std_0a, "model_0a_dnn_hv2048")
pred_0a = predict_batch(model_0a, X_te, y_mean_0a, y_std_0a, DEVICE)
evaluate_batch(test_prices, pred_0a, "Model 0a: DNN+HashingVec (h=2048)")
if hist_0a:
    plot_training_history(hist_0a, "Model 0a: DNN+HashingVec (h=2048)")
    ALL_HISTORIES["0a"] = hist_0a

del model_0a, X_tr, X_va, X_te
torch.cuda.empty_cache()

# %% Phase 2: Model 0b — DNN + TF-IDF (hidden=2048)
print("\n\n" + "#" * 60)
print("# MODEL 0b: DNN + TF-IDF (hidden=2048)")
print("#" * 60)

X_tr, y_tr = prepare_dnn_data(X_tfidf_train, cat_train, train_prices)
X_va, y_va = prepare_dnn_data(X_tfidf_val, cat_val, val_prices)
X_te, y_te = prepare_dnn_data(X_tfidf_test, cat_test, test_prices)

model_0b = DeepNeuralNetwork(X_tr.shape[1], hidden_size=2048, num_layers=10)
cached = load_torch_weights(model_0b, "model_0b_dnn_tfidf2048", DEVICE)
if cached:
    model_0b, y_mean_0b, y_std_0b = cached
    hist_0b = None
else:
    model_0b, y_mean_0b, y_std_0b, hist_0b = train_torch_model(
        model_0b, X_tr, y_tr, X_va, y_va, DEVICE, epochs=5, batch_size=64
    )
    save_torch_weights(model_0b, y_mean_0b, y_std_0b, "model_0b_dnn_tfidf2048")
pred_0b = predict_batch(model_0b, X_te, y_mean_0b, y_std_0b, DEVICE)
evaluate_batch(test_prices, pred_0b, "Model 0b: DNN+TF-IDF (h=2048)")
if hist_0b:
    plot_training_history(hist_0b, "Model 0b: DNN+TF-IDF (h=2048)")
    ALL_HISTORIES["0b"] = hist_0b

del model_0b
torch.cuda.empty_cache()

# %% Phase 2: Model 0c — DNN best vectorizer (hidden=4096)
print("\n\n" + "#" * 60)
print("# MODEL 0c: DNN best vectorizer (hidden=4096)")
print("#" * 60)
print("Using TF-IDF (same data as 0b, reuse X_tr/X_va/X_te)")

model_0c = DeepNeuralNetwork(X_tr.shape[1], hidden_size=4096, num_layers=10)
cached = load_torch_weights(model_0c, "model_0c_dnn_tfidf4096", DEVICE)
if cached:
    model_0c, y_mean_0c, y_std_0c = cached
    hist_0c = None
else:
    model_0c, y_mean_0c, y_std_0c, hist_0c = train_torch_model(
        model_0c, X_tr, y_tr, X_va, y_va, DEVICE, epochs=5, batch_size=64
    )
    save_torch_weights(model_0c, y_mean_0c, y_std_0c, "model_0c_dnn_tfidf4096")
pred_0c = predict_batch(model_0c, X_te, y_mean_0c, y_std_0c, DEVICE)
evaluate_batch(test_prices, pred_0c, "Model 0c: DNN+TF-IDF (h=4096)")
if hist_0c:
    plot_training_history(hist_0c, "Model 0c: DNN+TF-IDF (h=4096)")
    ALL_HISTORIES["0c"] = hist_0c

best_0 = min(
    [("0a", ALL_RESULTS.get("Model 0a: DNN+HashingVec (h=2048)", {}).get("rmsle", 99)),
     ("0b", ALL_RESULTS.get("Model 0b: DNN+TF-IDF (h=2048)", {}).get("rmsle", 99)),
     ("0c", ALL_RESULTS.get("Model 0c: DNN+TF-IDF (h=4096)", {}).get("rmsle", 99))],
    key=lambda x: x[1]
)
print(f"\nBest Model 0 variant: {best_0[0]} (RMSLE={best_0[1]:.4f})")

del model_0c, X_tr, X_va, X_te, y_tr, y_va, y_te
torch.cuda.empty_cache()


# ============================================================
# PHASE 3: EMBEDDING-BASED MODELS (MLP / LightGBM / DNN)
# ============================================================

# %% Helper: prepare embedding data
prices_dict = {"train": train_prices, "val": val_prices, "test": test_prices}
cat_dict = {"train": cat_train, "val": cat_val, "test": cat_test}

def make_embed_tensors(emb_dict):
    """Combine embeddings + category -> {split: (X_tensor, y_tensor)}."""
    result = {}
    for split in ("train", "val", "test"):
        cat_dense = cat_dict[split].toarray().astype(np.float32)
        X = np.hstack([emb_dict[split], cat_dense])
        y = prices_dict[split]
        result[split] = (torch.FloatTensor(X), torch.FloatTensor(y).unsqueeze(1))
    return result


# %% Phase 3: Model 2a — dangvantuan embed + MLP
print("\n\n" + "#" * 60)
print("# MODEL 2a: dangvantuan embedding + MLP")
print("#" * 60)

dv_data = make_embed_tensors(dv_emb)
input_dim = dv_data["train"][0].shape[1]
print(f"Input dim: {input_dim} (768 embedding + {cat_train.shape[1]} category)")

model_2a = MLP(input_dim, hidden_sizes=(512, 256, 128))
cached = load_torch_weights(model_2a, "model_2a_mlp_dangvantuan", DEVICE)
if cached:
    model_2a, y_mean_2a, y_std_2a = cached
    hist_2a = None
else:
    model_2a, y_mean_2a, y_std_2a, hist_2a = train_torch_model(
        model_2a, dv_data["train"][0], dv_data["train"][1],
        dv_data["val"][0], dv_data["val"][1], DEVICE,
        epochs=30, batch_size=128, lr=0.001, use_scheduler=False,
    )
    save_torch_weights(model_2a, y_mean_2a, y_std_2a, "model_2a_mlp_dangvantuan")
pred_2a = predict_batch(model_2a, dv_data["test"][0], y_mean_2a, y_std_2a, DEVICE)
evaluate_batch(test_prices, pred_2a, "Model 2a: dangvantuan+MLP")
if hist_2a:
    plot_training_history(hist_2a, "Model 2a: dangvantuan+MLP")
    ALL_HISTORIES["2a"] = hist_2a

del model_2a
torch.cuda.empty_cache()

# %% Phase 3: Model 2b — AITeamVN embed + MLP
print("\n\n" + "#" * 60)
print("# MODEL 2b: AITeamVN embedding + MLP")
print("#" * 60)

at_data = make_embed_tensors(at_emb)
input_dim = at_data["train"][0].shape[1]
print(f"Input dim: {input_dim} (1024 embedding + {cat_train.shape[1]} category)")

model_2b = MLP(input_dim, hidden_sizes=(512, 256, 128))
cached = load_torch_weights(model_2b, "model_2b_mlp_aiteamvn", DEVICE)
if cached:
    model_2b, y_mean_2b, y_std_2b = cached
    hist_2b = None
else:
    model_2b, y_mean_2b, y_std_2b, hist_2b = train_torch_model(
        model_2b, at_data["train"][0], at_data["train"][1],
        at_data["val"][0], at_data["val"][1], DEVICE,
        epochs=30, batch_size=128, lr=0.001, use_scheduler=False,
    )
    save_torch_weights(model_2b, y_mean_2b, y_std_2b, "model_2b_mlp_aiteamvn")
pred_2b = predict_batch(model_2b, at_data["test"][0], y_mean_2b, y_std_2b, DEVICE)
evaluate_batch(test_prices, pred_2b, "Model 2b: AITeamVN+MLP")
if hist_2b:
    plot_training_history(hist_2b, "Model 2b: AITeamVN+MLP")
    ALL_HISTORIES["2b"] = hist_2b

del model_2b
torch.cuda.empty_cache()

# %% Phase 3: Model 4a — dangvantuan embed + LightGBM
print("\n\n" + "#" * 60)
print("# MODEL 4a: dangvantuan embedding + LightGBM")
print("#" * 60)

import lightgbm as lgb

dv_X_train = np.hstack([dv_emb["train"], cat_train.toarray()])
dv_X_val = np.hstack([dv_emb["val"], cat_val.toarray()])
dv_X_test = np.hstack([dv_emb["test"], cat_test.toarray()])
y_train_log = np.log1p(train_prices)
y_val_log = np.log1p(val_prices)

lgb_4a_path = WEIGHTS_DIR / "model_4a_lgb_dangvantuan.pkl"
if lgb_4a_path.exists():
    lgb_4a = joblib.load(lgb_4a_path)
    print(f"  Loaded weights: {lgb_4a_path.name}")
    lgb_4a_eval = None
else:
    lgb_4a_eval = {}
    lgb_4a = lgb.LGBMRegressor(
        n_estimators=1000, learning_rate=0.1, num_leaves=31,
        n_jobs=6, random_state=SEED, verbose=-1,
    )
    lgb_4a.fit(
        dv_X_train, y_train_log,
        eval_set=[(dv_X_train, y_train_log), (dv_X_val, y_val_log)],
        eval_metric="l1",
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(200),
                   lgb.record_evaluation(lgb_4a_eval)],
    )
    joblib.dump(lgb_4a, lgb_4a_path)
    print(f"  Saved weights: {lgb_4a_path.name}")
pred_4a = np.expm1(lgb_4a.predict(dv_X_test))
evaluate_batch(test_prices, pred_4a, "Model 4a: dangvantuan+LightGBM")

if lgb_4a_eval:
    fig_4a = go.Figure()
    fig_4a.add_trace(go.Scatter(y=lgb_4a_eval["valid_0"]["l1"], name="Train L1", line=dict(color="steelblue")))
    fig_4a.add_trace(go.Scatter(y=lgb_4a_eval["valid_1"]["l1"], name="Val L1", line=dict(color="tomato")))
    fig_4a.update_layout(title="Model 4a: dangvantuan+LightGBM Learning Curve",
                         xaxis_title="Boosting Round", yaxis_title="L1 (log-space)",
                         width=700, height=400, template="plotly_white")
    fig_4a.show()

# %% Phase 3: Model 4b — AITeamVN embed + LightGBM
print("\n\n" + "#" * 60)
print("# MODEL 4b: AITeamVN embedding + LightGBM")
print("#" * 60)

at_X_train = np.hstack([at_emb["train"], cat_train.toarray()])
at_X_val = np.hstack([at_emb["val"], cat_val.toarray()])
at_X_test = np.hstack([at_emb["test"], cat_test.toarray()])

lgb_4b_path = WEIGHTS_DIR / "model_4b_lgb_aiteamvn.pkl"
if lgb_4b_path.exists():
    lgb_4b = joblib.load(lgb_4b_path)
    print(f"  Loaded weights: {lgb_4b_path.name}")
    lgb_4b_eval = None
else:
    lgb_4b_eval = {}
    lgb_4b = lgb.LGBMRegressor(
        n_estimators=1000, learning_rate=0.1, num_leaves=31,
        n_jobs=6, random_state=SEED, verbose=-1,
    )
    lgb_4b.fit(
        at_X_train, y_train_log,
        eval_set=[(at_X_train, y_train_log), (at_X_val, y_val_log)],
        eval_metric="l1",
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(200),
                   lgb.record_evaluation(lgb_4b_eval)],
    )
    joblib.dump(lgb_4b, lgb_4b_path)
    print(f"  Saved weights: {lgb_4b_path.name}")
pred_4b = np.expm1(lgb_4b.predict(at_X_test))
evaluate_batch(test_prices, pred_4b, "Model 4b: AITeamVN+LightGBM")

if lgb_4b_eval:
    fig_4b = go.Figure()
    fig_4b.add_trace(go.Scatter(y=lgb_4b_eval["valid_0"]["l1"], name="Train L1", line=dict(color="steelblue")))
    fig_4b.add_trace(go.Scatter(y=lgb_4b_eval["valid_1"]["l1"], name="Val L1", line=dict(color="tomato")))
    fig_4b.update_layout(title="Model 4b: AITeamVN+LightGBM Learning Curve",
                         xaxis_title="Boosting Round", yaxis_title="L1 (log-space)",
                         width=700, height=400, template="plotly_white")
    fig_4b.show()

# %% Phase 3: Model 5a — dangvantuan embed + DNN ResidualBlock
print("\n\n" + "#" * 60)
print("# MODEL 5a: dangvantuan embedding + DNN ResidualBlock")
print("#" * 60)

input_dim = dv_data["train"][0].shape[1]
model_5a = DeepNeuralNetwork(input_dim, hidden_size=1024, num_layers=6, dropout_prob=0.2)
cached = load_torch_weights(model_5a, "model_5a_dnn_dangvantuan", DEVICE)
if cached:
    model_5a, y_mean_5a, y_std_5a = cached
    hist_5a = None
else:
    model_5a, y_mean_5a, y_std_5a, hist_5a = train_torch_model(
        model_5a, dv_data["train"][0], dv_data["train"][1],
        dv_data["val"][0], dv_data["val"][1], DEVICE,
        epochs=10, batch_size=64, lr=0.001,
    )
    save_torch_weights(model_5a, y_mean_5a, y_std_5a, "model_5a_dnn_dangvantuan")
pred_5a = predict_batch(model_5a, dv_data["test"][0], y_mean_5a, y_std_5a, DEVICE)
evaluate_batch(test_prices, pred_5a, "Model 5a: dangvantuan+DNN")
if hist_5a:
    plot_training_history(hist_5a, "Model 5a: dangvantuan+DNN")
    ALL_HISTORIES["5a"] = hist_5a

del model_5a
torch.cuda.empty_cache()

# %% Phase 3: Model 5b — AITeamVN embed + DNN ResidualBlock
print("\n\n" + "#" * 60)
print("# MODEL 5b: AITeamVN embedding + DNN ResidualBlock")
print("#" * 60)

input_dim = at_data["train"][0].shape[1]
model_5b = DeepNeuralNetwork(input_dim, hidden_size=1024, num_layers=6, dropout_prob=0.2)
cached = load_torch_weights(model_5b, "model_5b_dnn_aiteamvn", DEVICE)
if cached:
    model_5b, y_mean_5b, y_std_5b = cached
    hist_5b = None
else:
    model_5b, y_mean_5b, y_std_5b, hist_5b = train_torch_model(
        model_5b, at_data["train"][0], at_data["train"][1],
        at_data["val"][0], at_data["val"][1], DEVICE,
        epochs=10, batch_size=64, lr=0.001,
    )
    save_torch_weights(model_5b, y_mean_5b, y_std_5b, "model_5b_dnn_aiteamvn")
pred_5b = predict_batch(model_5b, at_data["test"][0], y_mean_5b, y_std_5b, DEVICE)
evaluate_batch(test_prices, pred_5b, "Model 5b: AITeamVN+DNN")
if hist_5b:
    plot_training_history(hist_5b, "Model 5b: AITeamVN+DNN")
    ALL_HISTORIES["5b"] = hist_5b

del model_5b
torch.cuda.empty_cache()


# ============================================================
# PHASE 4: MODEL 1 — PhoBERT-base-v2 fine-tune
# ============================================================

# %% Phase 4: Model 1 — PhoBERT fine-tune
print("\n\n" + "#" * 60)
print("# MODEL 1: PhoBERT-base-v2 fine-tune (regression)")
print("#" * 60)

from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    TrainingArguments, Trainer,
)
from torch.utils.data import Dataset as TorchDataset

PHOBERT_NAME = "vinai/phobert-base-v2"
PHOBERT_DIR = DAY4 / "phobert_best"

class PriceDataset(TorchDataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels
    def __len__(self):
        return len(self.labels)
    def __getitem__(self, idx):
        item = {k: v[idx] for k, v in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item

print("Loading PhoBERT tokenizer...")
phobert_tokenizer = AutoTokenizer.from_pretrained(PHOBERT_NAME)

print("Tokenizing with PhoBERT tokenizer...")
enc_train = phobert_tokenizer(tok_train, truncation=True, padding=True, max_length=256, return_tensors="pt")
enc_val = phobert_tokenizer(tok_val, truncation=True, padding=True, max_length=256, return_tensors="pt")
enc_test = phobert_tokenizer(tok_test, truncation=True, padding=True, max_length=256, return_tensors="pt")

y_train_log_t = torch.log1p(torch.FloatTensor(train_prices))
y_val_log_t = torch.log1p(torch.FloatTensor(val_prices))
y_test_log_t = torch.log1p(torch.FloatTensor(test_prices))

ds_train = PriceDataset(enc_train, y_train_log_t)
ds_val = PriceDataset(enc_val, y_val_log_t)
ds_test = PriceDataset(enc_test, y_test_log_t)

phobert_trained = PHOBERT_DIR.exists() and (PHOBERT_DIR / "config.json").exists()
if phobert_trained:
    print(f"  Loading saved PhoBERT from {PHOBERT_DIR}")
    phobert_model = AutoModelForSequenceClassification.from_pretrained(
        str(PHOBERT_DIR), num_labels=1, problem_type="regression"
    )
else:
    print("Loading PhoBERT model (num_labels=1 -> regression)...")
    phobert_model = AutoModelForSequenceClassification.from_pretrained(
        PHOBERT_NAME, num_labels=1, problem_type="regression"
    )

    training_args = TrainingArguments(
        output_dir=str(PHOBERT_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        weight_decay=0.01,
        fp16=torch.cuda.is_available(),
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        logging_steps=100,
        seed=SEED,
        report_to="none",
    )

    trainer = Trainer(
        model=phobert_model,
        args=training_args,
        train_dataset=ds_train,
        eval_dataset=ds_val,
    )

    print("Training PhoBERT...")
    trainer.train()
    trainer.save_model(str(PHOBERT_DIR))
    phobert_tokenizer.save_pretrained(str(PHOBERT_DIR))
    print(f"Saved: {PHOBERT_DIR}")

    # Plot PhoBERT training loss from Trainer logs
    phobert_log = pd.DataFrame(trainer.state.log_history)
    fig_pho = make_subplots(rows=1, cols=2, subplot_titles=("Training Loss", "Eval Loss"))
    if "loss" in phobert_log.columns:
        train_log = phobert_log.dropna(subset=["loss"])
        fig_pho.add_trace(
            go.Scatter(x=train_log["step"], y=train_log["loss"], mode="lines",
                       name="Train Loss", line=dict(color="steelblue")),
            row=1, col=1,
        )
    if "eval_loss" in phobert_log.columns:
        eval_log = phobert_log.dropna(subset=["eval_loss"])
        fig_pho.add_trace(
            go.Scatter(x=eval_log["step"], y=eval_log["eval_loss"], mode="lines+markers",
                       name="Eval Loss", line=dict(color="tomato")),
            row=1, col=2,
        )
    fig_pho.update_xaxes(title_text="Step", row=1, col=1)
    fig_pho.update_xaxes(title_text="Step", row=1, col=2)
    fig_pho.update_yaxes(title_text="MSE Loss (log-space)", row=1, col=1)
    fig_pho.update_yaxes(title_text="MSE Loss (log-space)", row=1, col=2)
    fig_pho.update_layout(title="Model 1: PhoBERT-v2 Training Curves", width=900, height=400, template="plotly_white")
    fig_pho.show()
    del trainer

# Evaluate
print("Evaluating PhoBERT on test set...")
phobert_model.eval()
phobert_model.to(DEVICE)
pred_1_log = []
batch_size = 32
for i in range(0, len(test_items), batch_size):
    batch_enc = {k: v[i:i+batch_size].to(DEVICE) for k, v in enc_test.items()}
    with torch.no_grad():
        out = phobert_model(**batch_enc)
        pred_1_log.extend(out.logits.cpu().numpy().flatten())

pred_1 = np.expm1(np.array(pred_1_log))
pred_1 = np.clip(pred_1, 0, None)
evaluate_batch(test_prices, pred_1, "Model 1: PhoBERT-v2 fine-tune")

del phobert_model
torch.cuda.empty_cache()


# ============================================================
# PHASE 5: MODEL 3 — XLM-RoBERTa fine-tune
# ============================================================

# %% Phase 5: Model 3 — XLM-RoBERTa fine-tune
print("\n\n" + "#" * 60)
print("# MODEL 3: XLM-RoBERTa-base fine-tune (regression)")
print("#" * 60)

XLMR_NAME = "FacebookAI/xlm-roberta-base"
XLMR_DIR = DAY4 / "xlmr_best"

print("Loading XLM-R tokenizer...")
xlmr_tokenizer = AutoTokenizer.from_pretrained(XLMR_NAME)

print("Tokenizing with XLM-R tokenizer...")
xlmr_enc_train = xlmr_tokenizer(train_summaries, truncation=True, padding=True, max_length=256, return_tensors="pt")
xlmr_enc_val = xlmr_tokenizer(val_summaries, truncation=True, padding=True, max_length=256, return_tensors="pt")
xlmr_enc_test = xlmr_tokenizer(test_summaries, truncation=True, padding=True, max_length=256, return_tensors="pt")

xlmr_ds_train = PriceDataset(xlmr_enc_train, y_train_log_t)
xlmr_ds_val = PriceDataset(xlmr_enc_val, y_val_log_t)

xlmr_trained = XLMR_DIR.exists() and (XLMR_DIR / "config.json").exists()
if xlmr_trained:
    print(f"  Loading saved XLM-R from {XLMR_DIR}")
    xlmr_model = AutoModelForSequenceClassification.from_pretrained(
        str(XLMR_DIR), num_labels=1, problem_type="regression"
    )
else:
    print("Loading XLM-R model (num_labels=1 -> regression)...")
    xlmr_model = AutoModelForSequenceClassification.from_pretrained(
        XLMR_NAME, num_labels=1, problem_type="regression"
    )

    xlmr_args = TrainingArguments(
        output_dir=str(XLMR_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        weight_decay=0.01,
        fp16=torch.cuda.is_available(),
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        logging_steps=100,
        seed=SEED,
        report_to="none",
    )

    xlmr_trainer = Trainer(
        model=xlmr_model,
        args=xlmr_args,
        train_dataset=xlmr_ds_train,
        eval_dataset=xlmr_ds_val,
    )

    print("Training XLM-R...")
    xlmr_trainer.train()
    xlmr_trainer.save_model(str(XLMR_DIR))
    xlmr_tokenizer.save_pretrained(str(XLMR_DIR))
    print(f"Saved: {XLMR_DIR}")

    # Plot XLM-R training loss from Trainer logs
    xlmr_log = pd.DataFrame(xlmr_trainer.state.log_history)
    fig_xlmr = make_subplots(rows=1, cols=2, subplot_titles=("Training Loss", "Eval Loss"))
    if "loss" in xlmr_log.columns:
        train_log = xlmr_log.dropna(subset=["loss"])
        fig_xlmr.add_trace(
            go.Scatter(x=train_log["step"], y=train_log["loss"], mode="lines",
                       name="Train Loss", line=dict(color="steelblue")),
            row=1, col=1,
        )
    if "eval_loss" in xlmr_log.columns:
        eval_log = xlmr_log.dropna(subset=["eval_loss"])
        fig_xlmr.add_trace(
            go.Scatter(x=eval_log["step"], y=eval_log["eval_loss"], mode="lines+markers",
                       name="Eval Loss", line=dict(color="tomato")),
            row=1, col=2,
        )
    fig_xlmr.update_xaxes(title_text="Step", row=1, col=1)
    fig_xlmr.update_xaxes(title_text="Step", row=1, col=2)
    fig_xlmr.update_yaxes(title_text="MSE Loss (log-space)", row=1, col=1)
    fig_xlmr.update_yaxes(title_text="MSE Loss (log-space)", row=1, col=2)
    fig_xlmr.update_layout(title="Model 3: XLM-R Training Curves", width=900, height=400, template="plotly_white")
    fig_xlmr.show()
    del xlmr_trainer

# Evaluate
print("Evaluating XLM-R on test set...")
xlmr_model.eval()
xlmr_model.to(DEVICE)
pred_3_log = []
for i in range(0, len(test_items), batch_size):
    batch_enc = {k: v[i:i+batch_size].to(DEVICE) for k, v in xlmr_enc_test.items()}
    with torch.no_grad():
        out = xlmr_model(**batch_enc)
        pred_3_log.extend(out.logits.cpu().numpy().flatten())

pred_3 = np.expm1(np.array(pred_3_log))
pred_3 = np.clip(pred_3, 0, None)
evaluate_batch(test_prices, pred_3, "Model 3: XLM-R fine-tune")

del xlmr_model
torch.cuda.empty_cache()


# ============================================================
# PHASE 7: SUMMARY + CHARTS
# ============================================================

# %% Phase 7: Summary comparison table
print("\n\n" + "=" * 70)
print("FINAL RESULTS — Day 4 Deep Learning + Day 3 Baseline")
print("=" * 70)

ALL_RESULTS["Day 3 Baseline (Blended)"] = {
    "rmsle": 0.5164, "mae": 109_725, "mape": 44.0, "r2": 47.1
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

# Save results
results_path = DAY4 / "day4_results.json"
with open(results_path, "w") as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False)
print(f"\nResults saved: {results_path}")

best_name = df.index[0]
best_rmsle = df.iloc[0]["rmsle"]
print(f"\nBest model: {best_name} (RMSLE={best_rmsle:.4f})")
print(f"Day 3 baseline: RMSLE=0.5164")
print(f"Improvement: {(0.5164 - best_rmsle) / 0.5164 * 100:.1f}%")

# %% Phase 7: RMSLE comparison bar chart
fig_rmsle = go.Figure()
colors = ["mediumseagreen" if r < 0.5164 else "lightcoral" for r in df["rmsle"]]
fig_rmsle.add_trace(go.Bar(
    x=df.index, y=df["rmsle"], marker_color=colors,
    text=[f"{v:.4f}" for v in df["rmsle"]], textposition="outside",
))
fig_rmsle.add_hline(y=0.5164, line_dash="dash", line_color="red",
                    annotation_text="Day 3 Baseline (0.5164)")
fig_rmsle.add_hline(y=0.40, line_dash="dash", line_color="green",
                    annotation_text="Target (0.40)")
fig_rmsle.update_layout(
    title="Day 4: RMSLE Comparison (lower is better)",
    xaxis_title="Model", yaxis_title="RMSLE",
    width=1000, height=500, template="plotly_white",
    xaxis_tickangle=-30,
)
fig_rmsle.show()

# %% Phase 7: Multi-metric comparison chart
fig_multi = make_subplots(
    rows=2, cols=2,
    subplot_titles=("RMSLE (lower=better)", "MAE in VND (lower=better)",
                    "MAPE % (lower=better)", "R2 % (higher=better)"),
)
fig_multi.add_trace(go.Bar(x=df.index, y=df["rmsle"], name="RMSLE", marker_color="steelblue"), row=1, col=1)
fig_multi.add_trace(go.Bar(x=df.index, y=df["mae"], name="MAE", marker_color="tomato"), row=1, col=2)
fig_multi.add_trace(go.Bar(x=df.index, y=df["mape"], name="MAPE", marker_color="orange"), row=2, col=1)
fig_multi.add_trace(go.Bar(x=df.index, y=df["r2"], name="R2", marker_color="mediumseagreen"), row=2, col=2)
fig_multi.update_layout(
    title="Day 4: All Metrics Comparison",
    width=1100, height=700, template="plotly_white",
    showlegend=False,
)
fig_multi.update_xaxes(tickangle=-30)
fig_multi.show()
