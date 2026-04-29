"""Push items_tv_v9 lên HuggingFace.

Schema: title, category, brand, summary (merged), price (round/1000), price_vnd_true
- Train: 85,727 orig (items_tv_v7 filtered) + 183,385 aug (items_tv_v8) = 269,112
- Val/Test: items_tv_v7 filtered price <= 1M
No aug_version column.
"""
import gc
import os
import random

import numpy as np
from datasets import Dataset, DatasetDict, Features, Value, load_dataset
from dotenv import load_dotenv
from huggingface_hub import login
from tqdm.auto import tqdm

SCRIPT_DIR = __file__.rsplit("/", 1)[0] if "/" in __file__ else "."

SOURCE_TV7 = "SeanSunny/items_tv_v7"
SOURCE_TV8 = "SeanSunny/items_tv_v8"
OUTPUT_TV9 = "SeanSunny/items_tv_v9"

MAX_PRICE = 1_000_000
SEED = 42

V9_FEATURES = Features({
    "title":          Value("string"),
    "category":       Value("string"),
    "brand":          Value("string"),
    "summary":        Value("string"),
    "price":          Value("int64"),
    "price_vnd_true": Value("int64"),
})

random.seed(SEED)
np.random.seed(SEED)

load_dotenv(os.path.join(SCRIPT_DIR, "..", ".env"))
HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN not set in .env")
login(HF_TOKEN)
print("HF login OK")

# ---------------------------------------------------------------------------
# Step 1: Load items_tv_v7
# ---------------------------------------------------------------------------
print(f"\n[1/5] Loading {SOURCE_TV7} ...")
ds_v7 = load_dataset(SOURCE_TV7)
train_v7 = list(ds_v7["train"])
val_v7   = list(ds_v7["validation"])
test_v7  = list(ds_v7["test"])
print(f"  train={len(train_v7):,} | val={len(val_v7):,} | test={len(test_v7):,}")
del ds_v7
gc.collect()

# ---------------------------------------------------------------------------
# Step 2: Load items_tv_v8 train (aug rows)
# ---------------------------------------------------------------------------
print(f"\n[2/5] Loading {SOURCE_TV8} train ...")
ds_v8 = load_dataset(SOURCE_TV8)
train_v8 = list(ds_v8["train"])
print(f"  aug train={len(train_v8):,}")
del ds_v8
gc.collect()

# ---------------------------------------------------------------------------
# Step 3: Build train rows
# ---------------------------------------------------------------------------
print("\n[3/5] Building train rows ...")

# Orig rows: filter price <= 1M from v7 train, use `summary` as summary
orig_rows = []
for row in tqdm(train_v7, desc="  orig rows"):
    if row["price"] > MAX_PRICE:
        continue
    orig_rows.append({
        "title":          row["title"],
        "category":       row["category"],
        "brand":          row.get("brand") or "",
        "summary":        row["summary"],
        "price":          int(round(row["price"] / 1000)),
        "price_vnd_true": int(row["price"]),
    })
print(f"  orig rows: {len(orig_rows):,}")

del train_v7
gc.collect()

# Aug rows: from v8 train, use `summary_version2` as summary
aug_rows = []
skipped = 0
for row in tqdm(train_v8, desc="  aug rows"):
    sv2 = row.get("summary_version2") or ""
    if not sv2:
        skipped += 1
        continue
    if row["price"] > MAX_PRICE:
        skipped += 1
        continue
    aug_rows.append({
        "title":          row["title"],
        "category":       row["category"],
        "brand":          row.get("brand") or "",
        "summary":        sv2,
        "price":          int(round(row["price"] / 1000)),
        "price_vnd_true": int(row["price"]),
    })
print(f"  aug rows: {len(aug_rows):,} | skipped: {skipped}")

del train_v8
gc.collect()

combined_train = orig_rows + aug_rows
random.seed(SEED)
random.shuffle(combined_train)
print(f"  combined train: {len(orig_rows):,} + {len(aug_rows):,} = {len(combined_train):,}")

del orig_rows, aug_rows
gc.collect()

# ---------------------------------------------------------------------------
# Step 4: Build val/test rows (filter price <= 1M from v7)
# ---------------------------------------------------------------------------
print("\n[4/5] Building val/test rows ...")

def make_split_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        if row["price"] > MAX_PRICE:
            continue
        out.append({
            "title":          row["title"],
            "category":       row["category"],
            "brand":          row.get("brand") or "",
            "summary":        row["summary"],
            "price":          int(round(row["price"] / 1000)),
            "price_vnd_true": int(row["price"]),
        })
    return out

val_rows  = make_split_rows(val_v7)
test_rows = make_split_rows(test_v7)
print(f"  val: {len(val_rows):,} | test: {len(test_rows):,}")

del val_v7, test_v7
gc.collect()

# ---------------------------------------------------------------------------
# Step 5: Push items_tv_v9
# ---------------------------------------------------------------------------
print(f"\n[5/5] Pushing {OUTPUT_TV9} ...")

prices_train = [r["price_vnd_true"] for r in combined_train]
print(f"  price_vnd_true range: {min(prices_train):,} — {max(prices_train):,} VND")

ds_v9 = DatasetDict({
    "train":      Dataset.from_list(combined_train, features=V9_FEATURES),
    "validation": Dataset.from_list(val_rows,       features=V9_FEATURES),
    "test":       Dataset.from_list(test_rows,      features=V9_FEATURES),
})
print(f"  {ds_v9}")

ds_v9.push_to_hub(OUTPUT_TV9, private=True, max_shard_size="20MB")
print(f"\nDone. Pushed: https://huggingface.co/datasets/{OUTPUT_TV9}")
print(f"  train={len(combined_train):,} | val={len(val_rows):,} | test={len(test_rows):,}")
