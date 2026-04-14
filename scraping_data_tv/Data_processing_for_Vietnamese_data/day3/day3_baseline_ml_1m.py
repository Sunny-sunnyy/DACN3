"""Day 3: Baseline ML — Vietnamese Price Prediction (<=1M VND).

Dataset: SeanSunny/items_tv_v6, filtered to price <= 1,000,000 VND.
Train: ~85K | Val: ~3.9K | Test: ~3.9K
Primary metric: RMSLE
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random
import time
import pickle

import numpy as np
from tqdm.auto import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor

from pricer_vi.items import Item
from pricer_vi.evaluator import evaluate

# =============================================================
# CONFIG
# =============================================================
SEED = 42
DATASET = "SeanSunny/items_tv_v6"
PRICE_THRESHOLD = 1_000_000
CACHE_DIR = Path(__file__).resolve().parent
USE_GPU = False  # GPU treo voi sparse matrix 85K x 10K, dung CPU

random.seed(SEED)
np.random.seed(SEED)

# =============================================================
# LOAD DATA + FILTER <= 1M VND
# =============================================================
print(f"Loading dataset: {DATASET}")
train, val, test = Item.from_hub(DATASET)
print(f"Raw: {len(train):,} train | {len(val):,} val | {len(test):,} test")

train = [item for item in train if item.price <= PRICE_THRESHOLD]
val = [item for item in val if item.price <= PRICE_THRESHOLD]
test = [item for item in test if item.price <= PRICE_THRESHOLD]
print(f"Filtered <= {PRICE_THRESHOLD:,} VND:")
print(f"  Train: {len(train):,} | Val: {len(val):,} | Test: {len(test):,}")

train_prices = [item.price for item in train]
prices = np.array(train_prices, dtype=float)
documents = [item.summary for item in train]

print(f"  Price range: {prices.min():,.0f} - {prices.max():,.0f} VND")
print(f"  Mean: {prices.mean():,.0f} | Median: {np.median(prices):,.0f} | Std: {prices.std():,.0f}")

# =============================================================
# STEP 3: BASELINES (Random, Mean, Median)
# =============================================================

# --- 3a: Random ---
print("\n" + "=" * 60)
print("STEP 3a: Random Pricer")
print("=" * 60)
min_price, max_price = min(train_prices), max(train_prices)


def random_pricer(item):
    return random.randint(min_price, max_price)


random.seed(SEED)
results_random = evaluate(random_pricer, test)

# --- 3b: Mean ---
print("\n" + "=" * 60)
print("STEP 3b: Mean Pricer")
print("=" * 60)
training_average = float(prices.mean())
print(f"Training average: {training_average:,.0f} VND")


def mean_pricer(item):
    return training_average


results_mean = evaluate(mean_pricer, test)

# --- 3c: Median ---
print("\n" + "=" * 60)
print("STEP 3c: Median Pricer")
print("=" * 60)
training_median = float(np.median(prices))
print(f"Training median: {training_median:,.0f} VND")


def median_pricer(item):
    return training_median


results_median = evaluate(median_pricer, test)

# =============================================================
# STEP 4: LR + TF-IDF — Architecture A (n-gram, no segmentation)
# =============================================================
print("\n" + "=" * 60)
print("STEP 4: LR + TF-IDF — Architecture A (bigram, no word segmentation)")
print("=" * 60)

t0 = time.time()
vectorizer_a = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
X_train_a = vectorizer_a.fit_transform(documents)
print(f"TF-IDF A: {X_train_a.shape[0]:,} x {X_train_a.shape[1]:,} ({time.time()-t0:.1f}s)")

t0 = time.time()
lr_model_a = LinearRegression()
lr_model_a.fit(X_train_a, prices)
print(f"LR A train: {time.time()-t0:.1f}s")


def lr_tfidf_arch_a(item):
    x = vectorizer_a.transform([item.summary])
    return max(lr_model_a.predict(x)[0], 0)


results_lr_a = evaluate(lr_tfidf_arch_a, test)

# =============================================================
# STEP 5: Underthesea Pre-tokenize + TF-IDF Architecture B
# =============================================================
print("\n" + "=" * 60)
print("STEP 5: Underthesea Tokenize + TF-IDF Architecture B")
print("=" * 60)

from underthesea import word_tokenize
from multiprocessing import Pool


def tokenize_one(text):
    return word_tokenize(text, format="text")


CACHE_DIR.mkdir(exist_ok=True)
cache_train = CACHE_DIR / "tokenized_train_1m.pkl"
cache_test = CACHE_DIR / "tokenized_test_1m.pkl"

# --- Tokenize train ---
if cache_train.exists():
    print(f"Loading cached: {cache_train}")
    with open(cache_train, "rb") as f:
        tokenized_train = pickle.load(f)
    print(f"  Loaded {len(tokenized_train):,} docs")
else:
    t0 = time.time()
    print(f"Tokenizing {len(documents):,} train docs (4 workers)...")
    with Pool(4) as p:
        tokenized_train = list(tqdm(
            p.imap(tokenize_one, documents, chunksize=500),
            total=len(documents), desc="Tokenize train",
        ))
    elapsed = time.time() - t0
    print(f"  Done: {elapsed:.1f}s")
    with open(cache_train, "wb") as f:
        pickle.dump(tokenized_train, f)
    print(f"  Saved: {cache_train} ({cache_train.stat().st_size / 1e6:.1f}MB)")

# --- Tokenize test ---
test_summaries = [item.summary for item in test]
if cache_test.exists():
    print(f"Loading cached: {cache_test}")
    with open(cache_test, "rb") as f:
        tokenized_test = pickle.load(f)
    print(f"  Loaded {len(tokenized_test):,} docs")
else:
    t0 = time.time()
    print(f"Tokenizing {len(test_summaries):,} test docs...")
    with Pool(4) as p:
        tokenized_test = list(tqdm(
            p.imap(tokenize_one, test_summaries, chunksize=100),
            total=len(test_summaries), desc="Tokenize test",
        ))
    elapsed = time.time() - t0
    print(f"  Done: {elapsed:.1f}s")
    with open(cache_test, "wb") as f:
        pickle.dump(tokenized_test, f)
    print(f"  Saved: {cache_test}")

tokenized_test_map = {item.summary: tok for item, tok in zip(test, tokenized_test)}

print(f"\nSample original:  {documents[0][:100]}")
print(f"Sample tokenized: {tokenized_train[0][:100]}")

# --- TF-IDF B ---
t0 = time.time()
vectorizer_b = TfidfVectorizer(max_features=10000)
X_train_b = vectorizer_b.fit_transform(tokenized_train)
print(f"\nTF-IDF B: {X_train_b.shape[0]:,} x {X_train_b.shape[1]:,} ({time.time()-t0:.1f}s)")

# --- LR B ---
t0 = time.time()
lr_model_b = LinearRegression()
lr_model_b.fit(X_train_b, prices)
print(f"LR B train: {time.time()-t0:.1f}s")


def lr_tfidf_arch_b(item):
    tokenized = tokenized_test_map.get(item.summary) or tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(lr_model_b.predict(x)[0], 0)


results_lr_b = evaluate(lr_tfidf_arch_b, test)

# =============================================================
# STEP 6: Ensemble Models (all use Architecture B)
# =============================================================

# --- 6a: Random Forest (subset) ---
print("\n" + "=" * 60)
print("STEP 6a: Random Forest (Arch B, subset 40K)")
print("=" * 60)

SUBSET_RF = 40_000
t0 = time.time()
rf_model = RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=6, verbose=1)
rf_model.fit(X_train_b[:SUBSET_RF], prices[:SUBSET_RF])
print(f"\nRF train: {time.time()-t0:.1f}s ({SUBSET_RF:,} samples)")


def random_forest_pricer(item):
    tokenized = tokenized_test_map.get(item.summary) or tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(0, rf_model.predict(x)[0])


results_rf = evaluate(random_forest_pricer, test)

# --- 6b: XGBoost (CPU, hist) ---
print("\n" + "=" * 60)
print("STEP 6b: XGBoost (Arch B, full data, CPU)")
print("=" * 60)

t0 = time.time()
pbar_xgb = tqdm(total=1000, desc="XGBoost")


class XGBProgress(xgb.callback.TrainingCallback):
    def after_iteration(self, model, epoch, evals_log):
        pbar_xgb.update(1)
        return False

    def after_training(self, model):
        pbar_xgb.close()
        return model


xgb_model = xgb.XGBRegressor(
    n_estimators=1000, learning_rate=0.1, random_state=SEED, n_jobs=6,
    tree_method="hist", callbacks=[XGBProgress()],
)
xgb_model.fit(X_train_b, prices)
print(f"XGBoost train: {time.time()-t0:.1f}s")


def xgboost_pricer(item):
    tokenized = tokenized_test_map.get(item.summary) or tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(0, xgb_model.predict(x)[0])


results_xgb = evaluate(xgboost_pricer, test)

# --- 6c: LightGBM ---
print("\n" + "=" * 60)
print("STEP 6c: LightGBM (Arch B, full data)")
print("=" * 60)

t0 = time.time()
pbar_lgb = tqdm(total=1000, desc="LightGBM")


def lgb_tqdm_cb(env):
    pbar_lgb.update(1)


lgb_model = lgb.LGBMRegressor(
    n_estimators=1000, learning_rate=0.1, random_state=SEED, n_jobs=6, verbose=-1,
)
lgb_model.fit(X_train_b, prices, callbacks=[lgb_tqdm_cb])
pbar_lgb.close()
print(f"LightGBM train: {time.time()-t0:.1f}s")


def lightgbm_pricer(item):
    tokenized = tokenized_test_map.get(item.summary) or tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(0, lgb_model.predict(x)[0])


results_lgb = evaluate(lightgbm_pricer, test)

# --- 6d: CatBoost (CPU) ---
print("\n" + "=" * 60)
print("STEP 6d: CatBoost (Arch B, full data, CPU)")
print("=" * 60)

t0 = time.time()
cb_model = CatBoostRegressor(
    iterations=1000, learning_rate=0.1, random_seed=SEED, verbose=100,
)
cb_model.fit(X_train_b, prices)
print(f"CatBoost train: {time.time()-t0:.1f}s")


def catboost_pricer(item):
    tokenized = tokenized_test_map.get(item.summary) or tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(0, cb_model.predict(x)[0])


results_cb = evaluate(catboost_pricer, test)

# =============================================================
# STEP 7: FINAL SUMMARY
# =============================================================
print("\n" + "=" * 75)
print(f"FINAL SUMMARY — Day 3 Baseline ML (<= {PRICE_THRESHOLD:,} VND)")
print("=" * 75)

all_results = [
    ("Random", results_random),
    ("Mean", results_mean),
    ("Median", results_median),
    ("LR + TF-IDF (Arch A)", results_lr_a),
    ("LR + TF-IDF (Arch B)", results_lr_b),
    ("Random Forest (Arch B)", results_rf),
    ("XGBoost (Arch B)", results_xgb),
    ("LightGBM (Arch B)", results_lgb),
    ("CatBoost (Arch B)", results_cb),
]

print(f"\n{'Model':<30} {'RMSLE':>10} {'MAE (VND)':>15} {'MAPE (%)':>10} {'R2 (%)':>10}")
print("-" * 75)
for name, res in all_results:
    print(
        f"{name:<30} {res['rmsle']:>10.4f} {res['mae']:>15,.0f} "
        f"{res['mape']:>10.1f} {res['r2']:>10.1f}"
    )

best_name, best_res = min(all_results, key=lambda x: x[1]["rmsle"])
print(f"\nBest model (RMSLE): {best_name} -- RMSLE={best_res['rmsle']:.4f}")
