"""Day 3 v3: ML Optimization — Vietnamese Price Prediction (<=1M VND).

Improvements over v2:
- Log-transform target: train on log1p(price), align with RMSLE metric
- Category feature: one-hot encoding + TF-IDF (scipy hstack)
- Architecture C: word + char_wb hybrid TF-IDF (FeatureUnion)
- Ridge/Lasso instead of vanilla LR
- LightGBM hyperparameter tuning (Optuna)
- Weighted blending of top models
- Full test evaluation (3,872 items)

Dataset: SeanSunny/items_tv_v6, filtered <= 1,000,000 VND.
Target RMSLE: <= 0.45
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random
import time
import pickle

import numpy as np
from tqdm.auto import tqdm
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import FeatureUnion
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor

from pricer_vi.items import Item
from pricer_vi.evaluator import evaluate, rmsle

# =============================================================
# CONFIG
# =============================================================
SEED = 42
DATASET = "SeanSunny/items_tv_v6"
PRICE_THRESHOLD = 1_000_000
CACHE_DIR = Path(__file__).resolve().parent
EVAL_SIZE = "all"  # Full test set (3,872 items)

random.seed(SEED)
np.random.seed(SEED)

# =============================================================
# LOAD DATA + FILTER
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
val_prices = [item.price for item in val]
prices = np.array(train_prices, dtype=float)
documents = [item.summary for item in train]
categories_train = [[item.category] for item in train]

print(f"  Price range: {prices.min():,.0f} - {prices.max():,.0f} VND")
print(f"  Mean: {prices.mean():,.0f} | Median: {np.median(prices):,.0f}")

# Log-transform target
log_prices = np.log1p(prices)
print(f"  Log price range: {log_prices.min():.2f} - {log_prices.max():.2f}")
print(f"  Log mean: {log_prices.mean():.2f} | Log median: {np.median(log_prices):.2f}")

# =============================================================
# TOKENIZATION (load cache or tokenize)
# =============================================================
print("\n" + "=" * 60)
print("TOKENIZATION: Underthesea (load cache)")
print("=" * 60)

from underthesea import word_tokenize
from multiprocessing import Pool


def tokenize_one(text):
    return word_tokenize(text, format="text")


cache_train = CACHE_DIR / "tokenized_train_1m.pkl"
cache_test = CACHE_DIR / "tokenized_test_1m.pkl"
cache_val = CACHE_DIR / "tokenized_val_1m.pkl"

# Tokenize train
if cache_train.exists():
    print(f"Loading cached: {cache_train}")
    with open(cache_train, "rb") as f:
        tokenized_train = pickle.load(f)
else:
    t0 = time.time()
    print(f"Tokenizing {len(documents):,} train docs (4 workers)...")
    with Pool(4) as p:
        tokenized_train = list(tqdm(
            p.imap(tokenize_one, documents, chunksize=500),
            total=len(documents), desc="Tokenize train",
        ))
    print(f"  Done: {time.time()-t0:.1f}s")
    with open(cache_train, "wb") as f:
        pickle.dump(tokenized_train, f)
    print(f"  Saved: {cache_train}")

# Tokenize test
test_summaries = [item.summary for item in test]
if cache_test.exists():
    print(f"Loading cached: {cache_test}")
    with open(cache_test, "rb") as f:
        tokenized_test = pickle.load(f)
else:
    t0 = time.time()
    print(f"Tokenizing {len(test_summaries):,} test docs...")
    with Pool(4) as p:
        tokenized_test = list(tqdm(
            p.imap(tokenize_one, test_summaries, chunksize=100),
            total=len(test_summaries), desc="Tokenize test",
        ))
    print(f"  Done: {time.time()-t0:.1f}s")
    with open(cache_test, "wb") as f:
        pickle.dump(tokenized_test, f)

# Tokenize val
val_summaries = [item.summary for item in val]
if cache_val.exists():
    print(f"Loading cached: {cache_val}")
    with open(cache_val, "rb") as f:
        tokenized_val = pickle.load(f)
else:
    t0 = time.time()
    print(f"Tokenizing {len(val_summaries):,} val docs...")
    with Pool(4) as p:
        tokenized_val = list(tqdm(
            p.imap(tokenize_one, val_summaries, chunksize=100),
            total=len(val_summaries), desc="Tokenize val",
        ))
    print(f"  Done: {time.time()-t0:.1f}s")
    with open(cache_val, "wb") as f:
        pickle.dump(tokenized_val, f)

tokenized_test_map = {item.summary: tok for item, tok in zip(test, tokenized_test)}

# =============================================================
# FEATURE ENGINEERING
# =============================================================
print("\n" + "=" * 60)
print("FEATURE ENGINEERING")
print("=" * 60)

# --- Architecture B: Underthesea + TF-IDF word ---
t0 = time.time()
vectorizer_b = TfidfVectorizer(max_features=10000)
X_text_train = vectorizer_b.fit_transform(tokenized_train)
X_text_test = vectorizer_b.transform(tokenized_test)
X_text_val = vectorizer_b.transform(tokenized_val)
print(f"Arch B (word): {X_text_train.shape} ({time.time()-t0:.1f}s)")

# --- Architecture C: word + char_wb hybrid ---
t0 = time.time()
arch_c = FeatureUnion([
    ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=5000)),
    ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=5000)),
])
X_text_c_train = arch_c.fit_transform(tokenized_train)
X_text_c_test = arch_c.transform(tokenized_test)
X_text_c_val = arch_c.transform(tokenized_val)
print(f"Arch C (word+char): {X_text_c_train.shape} ({time.time()-t0:.1f}s)")

# --- Category one-hot ---
cat_encoder = OneHotEncoder(sparse_output=True, handle_unknown="ignore")
X_cat_train = cat_encoder.fit_transform(categories_train)
X_cat_test = cat_encoder.transform([[item.category] for item in test])
X_cat_val = cat_encoder.transform([[item.category] for item in val])
print(f"Category: {X_cat_train.shape[1]} features ({list(cat_encoder.categories_[0])})")

# --- Combined: text + category ---
X_bc_train = hstack([X_text_train, X_cat_train])
X_bc_test = hstack([X_text_test, X_cat_test])
X_bc_val = hstack([X_text_val, X_cat_val])
print(f"Arch B + Cat: {X_bc_train.shape}")

X_cc_train = hstack([X_text_c_train, X_cat_train])
X_cc_test = hstack([X_text_c_test, X_cat_test])
X_cc_val = hstack([X_text_c_val, X_cat_val])
print(f"Arch C + Cat: {X_cc_train.shape}")

# =============================================================
# HELPER: evaluate with log-transform
# =============================================================


def evaluate_log_model(model, X_test_matrix, test_data, title):
    """Evaluate a model trained on log1p(price)."""
    pred_log = model.predict(X_test_matrix)
    pred_price = np.expm1(pred_log)
    pred_price = np.clip(pred_price, 0, None)

    y_true = np.array([item.price for item in test_data], dtype=float)
    rmsle_val = rmsle(y_true, pred_price)
    mae_val = float(np.mean(np.abs(y_true - pred_price)))
    mask = y_true > 0
    mape_val = float(np.mean(np.abs((y_true[mask] - pred_price[mask]) / y_true[mask])) * 100)
    from sklearn.metrics import r2_score
    r2_val = r2_score(y_true, pred_price) * 100

    print(f"\n{title} ({len(test_data)} items):")
    print(f"  RMSLE:  {rmsle_val:.4f}")
    print(f"  MAE:    {mae_val:,.0f} VND")
    print(f"  MAPE:   {mape_val:.1f}%")
    print(f"  R2:     {r2_val:.1f}%")
    return {"rmsle": rmsle_val, "mae": mae_val, "mape": mape_val, "r2": r2_val}


# =============================================================
# PHASE 1: Log-transform — re-train all models
# =============================================================
print("\n" + "=" * 75)
print("PHASE 1: Log-transform target (all models)")
print("=" * 75)

results = {}

# --- Baselines (no log needed, same as v2) ---
print("\n--- Baselines ---")
training_median = float(np.median(prices))


def median_pricer(item):
    return training_median


results["Median (baseline)"] = evaluate(median_pricer, test, size=EVAL_SIZE)

# --- Ridge (Arch B + Cat, log) ---
print("\n--- Ridge (Arch B + Cat, log) ---")
t0 = time.time()
ridge_model = Ridge(alpha=1.0)
ridge_model.fit(X_bc_train, log_prices)
print(f"Ridge train: {time.time()-t0:.1f}s")
results["Ridge (B+Cat, log)"] = evaluate_log_model(ridge_model, X_bc_test, test, "Ridge (B+Cat, log)")

# --- Ridge (Arch C + Cat, log) ---
print("\n--- Ridge (Arch C + Cat, log) ---")
t0 = time.time()
ridge_c = Ridge(alpha=1.0)
ridge_c.fit(X_cc_train, log_prices)
print(f"Ridge C train: {time.time()-t0:.1f}s")
results["Ridge (C+Cat, log)"] = evaluate_log_model(ridge_c, X_cc_test, test, "Ridge (C+Cat, log)")

# --- LR (Arch B + Cat, log) for comparison ---
print("\n--- LR (Arch B + Cat, log) ---")
t0 = time.time()
lr_log = LinearRegression()
lr_log.fit(X_bc_train, log_prices)
print(f"LR log train: {time.time()-t0:.1f}s")
results["LR (B+Cat, log)"] = evaluate_log_model(lr_log, X_bc_test, test, "LR (B+Cat, log)")

# --- Random Forest (Arch B + Cat, log, subset) ---
print("\n--- Random Forest (Arch B + Cat, log) ---")
SUBSET_RF = 40_000
t0 = time.time()
rf_log = RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=6, verbose=1)
rf_log.fit(X_bc_train[:SUBSET_RF], log_prices[:SUBSET_RF])
print(f"\nRF train: {time.time()-t0:.1f}s ({SUBSET_RF:,} samples)")
results["RF (B+Cat, log)"] = evaluate_log_model(rf_log, X_bc_test, test, "RF (B+Cat, log)")

# --- XGBoost (Arch B + Cat, log) ---
print("\n--- XGBoost (Arch B + Cat, log) ---")
t0 = time.time()
pbar_xgb = tqdm(total=1000, desc="XGBoost")


class XGBProgress(xgb.callback.TrainingCallback):
    def after_iteration(self, model, epoch, evals_log):
        pbar_xgb.update(1)
        return False

    def after_training(self, model):
        pbar_xgb.close()
        return model


xgb_log = xgb.XGBRegressor(
    n_estimators=1000, learning_rate=0.1, random_state=SEED, n_jobs=6,
    tree_method="hist", callbacks=[XGBProgress()],
)
xgb_log.fit(X_bc_train, log_prices)
print(f"XGBoost train: {time.time()-t0:.1f}s")
results["XGBoost (B+Cat, log)"] = evaluate_log_model(xgb_log, X_bc_test, test, "XGBoost (B+Cat, log)")

# --- LightGBM (Arch B + Cat, log) ---
print("\n--- LightGBM (Arch B + Cat, log) ---")
t0 = time.time()
pbar_lgb = tqdm(total=1000, desc="LightGBM")


def lgb_tqdm_cb(env):
    pbar_lgb.update(1)


lgb_log = lgb.LGBMRegressor(
    n_estimators=1000, learning_rate=0.1, random_state=SEED, n_jobs=6, verbose=-1,
)
lgb_log.fit(X_bc_train, log_prices, callbacks=[lgb_tqdm_cb])
pbar_lgb.close()
print(f"LightGBM train: {time.time()-t0:.1f}s")
results["LightGBM (B+Cat, log)"] = evaluate_log_model(lgb_log, X_bc_test, test, "LightGBM (B+Cat, log)")

# --- CatBoost (Arch B + Cat, log) ---
print("\n--- CatBoost (Arch B + Cat, log) ---")
t0 = time.time()
cb_log = CatBoostRegressor(
    iterations=1000, learning_rate=0.1, random_seed=SEED, verbose=100,
)
cb_log.fit(X_bc_train, log_prices)
print(f"CatBoost train: {time.time()-t0:.1f}s")
results["CatBoost (B+Cat, log)"] = evaluate_log_model(cb_log, X_bc_test, test, "CatBoost (B+Cat, log)")

# --- LightGBM (Arch C + Cat, log) ---
print("\n--- LightGBM (Arch C + Cat, log) ---")
t0 = time.time()
pbar_lgb2 = tqdm(total=1000, desc="LightGBM C")


def lgb_tqdm_cb2(env):
    pbar_lgb2.update(1)


lgb_c_log = lgb.LGBMRegressor(
    n_estimators=1000, learning_rate=0.1, random_state=SEED, n_jobs=6, verbose=-1,
)
lgb_c_log.fit(X_cc_train, log_prices, callbacks=[lgb_tqdm_cb2])
pbar_lgb2.close()
print(f"LightGBM C train: {time.time()-t0:.1f}s")
results["LightGBM (C+Cat, log)"] = evaluate_log_model(lgb_c_log, X_cc_test, test, "LightGBM (C+Cat, log)")

# =============================================================
# PHASE 3: LightGBM Hyperparameter Tuning (Optuna)
# =============================================================
print("\n" + "=" * 75)
print("PHASE 3: LightGBM Optuna Tuning (Arch B + Cat, log)")
print("=" * 75)

import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)

log_val_prices = np.log1p(np.array(val_prices, dtype=float))


def objective(trial):
    params = {
        "num_leaves": trial.suggest_int("num_leaves", 50, 200),
        "min_child_samples": trial.suggest_int("min_child_samples", 50, 200),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.3, 0.7),
        "lambda_l1": trial.suggest_float("lambda_l1", 0.01, 1.0, log=True),
        "lambda_l2": trial.suggest_float("lambda_l2", 0.01, 1.0, log=True),
        "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.1, log=True),
        "n_estimators": 1500,
        "random_state": SEED,
        "n_jobs": 6,
        "verbose": -1,
    }
    model = lgb.LGBMRegressor(**params)
    model.fit(X_bc_train, log_prices)
    pred_log = model.predict(X_bc_val)
    pred_price = np.clip(np.expm1(pred_log), 0, None)
    return rmsle(np.array(val_prices, dtype=float), pred_price)


N_TRIALS = 50
print(f"Running {N_TRIALS} Optuna trials on validation set ({len(val):,} items)...")
t0 = time.time()
study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)
print(f"Optuna done: {time.time()-t0:.1f}s")
print(f"Best val RMSLE: {study.best_value:.4f}")
print(f"Best params: {study.best_params}")

# Train best model on full train, evaluate on test
print("\n--- Best LightGBM (tuned, Arch B + Cat, log) ---")
best_params = study.best_params
best_params["n_estimators"] = 1500
best_params["random_state"] = SEED
best_params["n_jobs"] = 6
best_params["verbose"] = -1

t0 = time.time()
lgb_tuned = lgb.LGBMRegressor(**best_params)
lgb_tuned.fit(X_bc_train, log_prices)
print(f"Best LightGBM train: {time.time()-t0:.1f}s")
results["LightGBM Tuned (B+Cat, log)"] = evaluate_log_model(
    lgb_tuned, X_bc_test, test, "LightGBM Tuned (B+Cat, log)",
)

# Also try tuned params with Arch C
print("\n--- Best LightGBM (tuned, Arch C + Cat, log) ---")
t0 = time.time()
lgb_tuned_c = lgb.LGBMRegressor(**best_params)
lgb_tuned_c.fit(X_cc_train, log_prices)
print(f"Best LightGBM C train: {time.time()-t0:.1f}s")
results["LightGBM Tuned (C+Cat, log)"] = evaluate_log_model(
    lgb_tuned_c, X_cc_test, test, "LightGBM Tuned (C+Cat, log)",
)

# =============================================================
# PHASE 4: Weighted Blending
# =============================================================
print("\n" + "=" * 75)
print("PHASE 4: Weighted Blending (top models)")
print("=" * 75)

from scipy.optimize import minimize as scipy_minimize

# Get predictions on val set for weight optimization
pred_lgb_val = np.clip(np.expm1(lgb_tuned.predict(X_bc_val)), 0, None)
pred_xgb_val = np.clip(np.expm1(xgb_log.predict(X_bc_val)), 0, None)
pred_cb_val = np.clip(np.expm1(cb_log.predict(X_bc_val)), 0, None)
pred_lgb_c_val = np.clip(np.expm1(lgb_tuned_c.predict(X_cc_val)), 0, None)

val_true = np.array(val_prices, dtype=float)
val_preds = [pred_lgb_val, pred_xgb_val, pred_cb_val, pred_lgb_c_val]
model_names_blend = ["LightGBM Tuned B", "XGBoost B", "CatBoost B", "LightGBM Tuned C"]


def blend_rmsle(weights):
    w = np.abs(weights)
    w = w / w.sum()
    blended = sum(wi * p for wi, p in zip(w, val_preds))
    return rmsle(val_true, blended)


result_opt = scipy_minimize(blend_rmsle, x0=[0.4, 0.2, 0.2, 0.2], method="Nelder-Mead")
best_weights = np.abs(result_opt.x)
best_weights = best_weights / best_weights.sum()

print(f"Optimal weights (val):")
for name, w in zip(model_names_blend, best_weights):
    print(f"  {name}: {w:.3f}")
print(f"Val blend RMSLE: {result_opt.fun:.4f}")

# Apply to test set
pred_lgb_test = np.clip(np.expm1(lgb_tuned.predict(X_bc_test)), 0, None)
pred_xgb_test = np.clip(np.expm1(xgb_log.predict(X_bc_test)), 0, None)
pred_cb_test = np.clip(np.expm1(cb_log.predict(X_bc_test)), 0, None)
pred_lgb_c_test = np.clip(np.expm1(lgb_tuned_c.predict(X_cc_test)), 0, None)

test_preds = [pred_lgb_test, pred_xgb_test, pred_cb_test, pred_lgb_c_test]
blended_test = sum(w * p for w, p in zip(best_weights, test_preds))
test_true = np.array([item.price for item in test], dtype=float)

blend_rmsle_val = rmsle(test_true, blended_test)
blend_mae = float(np.mean(np.abs(test_true - blended_test)))
mask = test_true > 0
blend_mape = float(np.mean(np.abs((test_true[mask] - blended_test[mask]) / test_true[mask])) * 100)
from sklearn.metrics import r2_score
blend_r2 = r2_score(test_true, blended_test) * 100

print(f"\nBlended ({len(test):,} test items):")
print(f"  RMSLE:  {blend_rmsle_val:.4f}")
print(f"  MAE:    {blend_mae:,.0f} VND")
print(f"  MAPE:   {blend_mape:.1f}%")
print(f"  R2:     {blend_r2:.1f}%")
results["Blended (4 models)"] = {"rmsle": blend_rmsle_val, "mae": blend_mae, "mape": blend_mape, "r2": blend_r2}

# =============================================================
# FINAL SUMMARY
# =============================================================
print("\n" + "=" * 75)
print(f"FINAL SUMMARY — Day 3 v3 ML Optimization (<= {PRICE_THRESHOLD:,} VND)")
print("=" * 75)

print(f"\n{'Model':<35} {'RMSLE':>10} {'MAE (VND)':>15} {'MAPE (%)':>10} {'R2 (%)':>10}")
print("-" * 80)
for name, res in sorted(results.items(), key=lambda x: x[1]["rmsle"]):
    print(
        f"{name:<35} {res['rmsle']:>10.4f} {res['mae']:>15,.0f} "
        f"{res['mape']:>10.1f} {res['r2']:>10.1f}"
    )

best_name = min(results, key=lambda k: results[k]["rmsle"])
best_res = results[best_name]
print(f"\nBest model: {best_name} -- RMSLE={best_res['rmsle']:.4f}")

# V2 comparison
print("\n--- v2 vs v3 ---")
print(f"v2 best (LightGBM, 200 items):  RMSLE=0.5799")
print(f"v3 best ({best_name}): RMSLE={best_res['rmsle']:.4f}")
improvement = (0.5799 - best_res["rmsle"]) / 0.5799 * 100
print(f"Improvement: {improvement:.1f}%")
