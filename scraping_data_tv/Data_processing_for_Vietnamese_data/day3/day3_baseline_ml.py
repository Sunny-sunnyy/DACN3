"""Day 3: Baseline ML — Vietnamese Price Prediction.

Steps 3-5: Baselines + Linear Regression + TF-IDF (Architecture A & B).
Dataset: SeanSunny/items_tv_v6 (120K items: 110K train / 5K val / 5K test)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random
import time
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression
from pricer_vi.items import Item
from pricer_vi.evaluator import evaluate

SEED = 42
DATASET = "SeanSunny/items_tv_v6"

# --- Load data ---
print(f"Loading dataset: {DATASET}")
train, val, test = Item.from_hub(DATASET)
print(f"Loaded {len(train):,} train, {len(val):,} val, {len(test):,} test items")
print(f"Sample: {test[0]}")
print(f"Price range: {min(i.price for i in train):,} - {max(i.price for i in train):,} VND")

train_prices = [item.price for item in train]
prices = np.array(train_prices, dtype=float)
documents = [item.summary for item in train]

# ============================================================
# STEP 3: Baselines
# ============================================================

# --- Baseline 1: Random Pricer ---
print("\n" + "=" * 60)
print("BASELINE 1: Random Pricer")
print("=" * 60)

min_price = min(train_prices)
max_price = max(train_prices)


def random_pricer(item):
    return random.randint(min_price, max_price)


random.seed(SEED)
np.random.seed(SEED)
results_random = evaluate(random_pricer, test)

# --- Baseline 2: Mean Pricer ---
print("\n" + "=" * 60)
print("BASELINE 2: Mean Pricer")
print("=" * 60)

training_average = sum(train_prices) / len(train_prices)
print(f"Training average price: {training_average:,.0f} VND")


def mean_pricer(item):
    return training_average


results_mean = evaluate(mean_pricer, test)

# --- Baseline 3: Median Pricer ---
print("\n" + "=" * 60)
print("BASELINE 3: Median Pricer")
print("=" * 60)

training_median = float(np.median(train_prices))
print(f"Training median price: {training_median:,.0f} VND")


def median_pricer(item):
    return training_median


results_median = evaluate(median_pricer, test)

# ============================================================
# STEP 4: Linear Regression + TF-IDF — Architecture A
# TF-IDF with bigram, no word segmentation
# ============================================================
print("\n" + "=" * 60)
print("STEP 4: LR + TF-IDF — Architecture A (n-gram, no segmentation)")
print("=" * 60)

np.random.seed(SEED)
t0 = time.time()

vectorizer_a = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
X_train_a = vectorizer_a.fit_transform(documents)
print(f"TF-IDF A: {X_train_a.shape[0]:,} docs x {X_train_a.shape[1]:,} features")
print(f"Vectorization time: {time.time() - t0:.1f}s")

selected_words_a = vectorizer_a.get_feature_names_out()
print(f"Sample features: {list(selected_words_a[2500:2520])}")

t0 = time.time()
lr_model_a = LinearRegression()
lr_model_a.fit(X_train_a, prices)
print(f"Training time: {time.time() - t0:.1f}s")


def lr_tfidf_arch_a(item):
    x = vectorizer_a.transform([item.summary])
    return max(lr_model_a.predict(x)[0], 0)


results_lr_a = evaluate(lr_tfidf_arch_a, test)

# ============================================================
# STEP 5: Linear Regression + TF-IDF — Architecture B
# Underthesea pre-tokenize + TF-IDF
# ============================================================
print("\n" + "=" * 60)
print("STEP 5: LR + TF-IDF — Architecture B (underthesea pre-tokenize)")
print("=" * 60)

from underthesea import word_tokenize
from multiprocessing import Pool


def tokenize_one(text):
    """Tokenize Vietnamese text using underthesea."""
    return word_tokenize(text, format="text")


# Pre-tokenize train set (multiprocessing)
np.random.seed(SEED)
t0 = time.time()
print(f"Pre-tokenizing {len(documents):,} documents with underthesea (4 workers)...")
with Pool(4) as p:
    tokenized_train = p.map(tokenize_one, documents)
print(f"Tokenization time: {time.time() - t0:.1f}s")
print(f"Sample original:  {documents[0][:100]}")
print(f"Sample tokenized: {tokenized_train[0][:100]}")

t0 = time.time()
vectorizer_b = TfidfVectorizer(max_features=5000)
X_train_b = vectorizer_b.fit_transform(tokenized_train)
print(f"TF-IDF B: {X_train_b.shape[0]:,} docs x {X_train_b.shape[1]:,} features")
print(f"Vectorization time: {time.time() - t0:.1f}s")

selected_words_b = vectorizer_b.get_feature_names_out()
print(f"Sample features: {list(selected_words_b[2500:2520])}")

t0 = time.time()
lr_model_b = LinearRegression()
lr_model_b.fit(X_train_b, prices)
print(f"Training time: {time.time() - t0:.1f}s")

# Pre-tokenize test set (underthesea is not thread-safe)
t0 = time.time()
test_summaries = [item.summary for item in test]
print(f"Pre-tokenizing {len(test_summaries):,} test documents...")
with Pool(4) as p:
    tokenized_test = p.map(tokenize_one, test_summaries)
tokenized_test_map = {item.summary: tok for item, tok in zip(test, tokenized_test)}
print(f"Test tokenization time: {time.time() - t0:.1f}s")


def lr_tfidf_arch_b(item):
    if item.summary in tokenized_test_map:
        tokenized = tokenized_test_map[item.summary]
    else:
        tokenized = tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(lr_model_b.predict(x)[0], 0)


results_lr_b = evaluate(lr_tfidf_arch_b, test)

# ============================================================
# STEP 6: Ensemble Models (using Architecture B vectorization)
# ============================================================

from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor

# --- Random Forest ---
print("\n" + "=" * 60)
print("STEP 6a: Random Forest (Arch B, subset=20K)")
print("=" * 60)

np.random.seed(SEED)
SUBSET_RF = 20_000
t0 = time.time()
rf_model = RandomForestRegressor(n_estimators=100, random_state=SEED, n_jobs=4)
rf_model.fit(X_train_b[:SUBSET_RF], prices[:SUBSET_RF])
print(f"Training time: {time.time() - t0:.1f}s (on {SUBSET_RF:,} samples)")


def random_forest_pricer(item):
    if item.summary in tokenized_test_map:
        tokenized = tokenized_test_map[item.summary]
    else:
        tokenized = tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(0, rf_model.predict(x)[0])


results_rf = evaluate(random_forest_pricer, test)

# --- XGBoost ---
print("\n" + "=" * 60)
print("STEP 6b: XGBoost (Arch B, full data)")
print("=" * 60)

np.random.seed(SEED)
t0 = time.time()
xgb_model = xgb.XGBRegressor(
    n_estimators=1000, learning_rate=0.1, random_state=SEED, n_jobs=4
)
xgb_model.fit(X_train_b, prices)
print(f"Training time: {time.time() - t0:.1f}s")


def xgboost_pricer(item):
    if item.summary in tokenized_test_map:
        tokenized = tokenized_test_map[item.summary]
    else:
        tokenized = tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(0, xgb_model.predict(x)[0])


results_xgb = evaluate(xgboost_pricer, test)

# --- LightGBM ---
print("\n" + "=" * 60)
print("STEP 6c: LightGBM (Arch B, full data)")
print("=" * 60)

np.random.seed(SEED)
t0 = time.time()
lgb_model = lgb.LGBMRegressor(
    n_estimators=1000, learning_rate=0.1, random_state=SEED, n_jobs=4, verbose=-1
)
lgb_model.fit(X_train_b, prices)
print(f"Training time: {time.time() - t0:.1f}s")


def lightgbm_pricer(item):
    if item.summary in tokenized_test_map:
        tokenized = tokenized_test_map[item.summary]
    else:
        tokenized = tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(0, lgb_model.predict(x)[0])


results_lgb = evaluate(lightgbm_pricer, test)

# --- CatBoost ---
print("\n" + "=" * 60)
print("STEP 6d: CatBoost (Arch B, full data)")
print("=" * 60)

np.random.seed(SEED)
t0 = time.time()
cb_model = CatBoostRegressor(
    iterations=1000, learning_rate=0.1, random_seed=SEED, verbose=0
)
cb_model.fit(X_train_b, prices)
print(f"Training time: {time.time() - t0:.1f}s")


def catboost_pricer(item):
    if item.summary in tokenized_test_map:
        tokenized = tokenized_test_map[item.summary]
    else:
        tokenized = tokenize_one(item.summary)
    x = vectorizer_b.transform([tokenized])
    return max(0, cb_model.predict(x)[0])


results_cb = evaluate(catboost_pricer, test)

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 75)
print("FINAL SUMMARY: All Models (Steps 3-6)")
print("=" * 75)
print(f"{'Model':<30} {'RMSLE':>10} {'MAE (VND)':>15} {'MAPE (%)':>10} {'R2 (%)':>10}")
print("-" * 75)
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
for name, res in all_results:
    print(
        f"{name:<30} {res['rmsle']:>10.4f} {res['mae']:>15,.0f} "
        f"{res['mape']:>10.1f} {res['r2']:>10.1f}"
    )

# Find best model by RMSLE
best_name, best_res = min(all_results, key=lambda x: x[1]["rmsle"])
print(f"\nBest model (by RMSLE): {best_name} — RMSLE={best_res['rmsle']:.4f}")

