"""Build and push SeanSunny/items_prompts_tv_2 to HuggingFace.

Changes vs v1:
- completion = round(price/1000) for ALL splits (train/val/test)
- No category column
- train/val filtered price <= 1,000,000 VND; test kept full
- prompt built from 'summary' column
"""
import os
import random
import numpy as np
from datasets import load_dataset, DatasetDict

SOURCE = "SeanSunny/items_tv_v6"
OUTPUT = "SeanSunny/items_prompts_tv_2"
MAX_PRICE = 1_000_000
SEED = 42

HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN not set.")

random.seed(SEED)
np.random.seed(SEED)

# --- Load ---
print(f"Loading {SOURCE} ...")
ds = load_dataset(SOURCE)
val_key = "val" if "val" in ds else "validation"
print(ds)

# --- Filter ---
def filter_price(split):
    return split.filter(lambda x: float(x["price"]) <= MAX_PRICE, num_proc=1)

n_train = len(ds["train"])
n_val   = len(ds[val_key])

train_f = filter_price(ds["train"])
val_f   = filter_price(ds[val_key])
test_f  = ds["test"]

print(f"Train: {n_train:,} -> {len(train_f):,} (dropped {n_train - len(train_f):,})")
print(f"Val  : {n_val:,} -> {len(val_f):,} (dropped {n_val - len(val_f):,})")
print(f"Test : {len(test_f):,} -> {len(test_f):,} (no filter)")

# --- Build examples ---
def build_example(item: dict) -> dict:
    summary = (item.get("summary") or "").strip()
    price = float(item["price"])
    return {
        "prompt": f"Sản phẩm này có giá bao nhiêu ?\n{summary}\n\nGiá là: ",
        "completion": str(int(round(price / 1000))),
        "price_vnd_true": int(round(price)),
    }

def process(split):
    return split.map(build_example, remove_columns=split.column_names,
                     desc="Building prompts", num_proc=1)

print("\nBuilding prompts ...")
out = DatasetDict({
    "train": process(train_f),
    "val":   process(val_f),
    "test":  process(test_f),
})
print(out)
print(f"Schema: {out['train'].column_names}")

# --- Stats ---
for name, split in out.items():
    import pandas as pd
    df = split.to_pandas()
    prices = df["price_vnd_true"]
    print(f"\n{name} ({len(df):,}): mean={prices.mean():.0f}, "
          f"median={prices.median():.0f}, min={prices.min():,}, max={prices.max():,}")
    print(f"  completion sample: {df['completion'].sample(5, random_state=42).tolist()}")

# --- Push ---
print(f"\nPushing to {OUTPUT} ...")
out.push_to_hub(OUTPUT, token=HF_TOKEN)
print("Done.")
