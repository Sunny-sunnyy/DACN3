"""Build and push SeanSunny/items_prompts_tv_3 to HuggingFace.

Changes vs v2:
- test also filtered price <= 1,000,000 VND (same as train/val)
- All 3 splits: completion = round(price/1000), no category column
"""
import os
import random
import numpy as np
from datasets import load_dataset, DatasetDict

SOURCE = "SeanSunny/items_tv_v6"
OUTPUT = "SeanSunny/items_prompts_tv_3"
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

# --- Filter all 3 splits ---
def filter_price(split):
    return split.filter(lambda x: float(x["price"]) <= MAX_PRICE, num_proc=1)

sizes_before = {
    "train": len(ds["train"]),
    "val":   len(ds[val_key]),
    "test":  len(ds["test"]),
}

train_f = filter_price(ds["train"])
val_f   = filter_price(ds[val_key])
test_f  = filter_price(ds["test"])

for name, split, n_before in [
    ("train", train_f, sizes_before["train"]),
    ("val",   val_f,   sizes_before["val"]),
    ("test",  test_f,  sizes_before["test"]),
]:
    print(f"{name:5s}: {n_before:,} -> {len(split):,} (dropped {n_before - len(split):,})")

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
import pandas as pd
for name, split in out.items():
    df = split.to_pandas()
    prices = df["price_vnd_true"]
    print(f"\n{name} ({len(df):,}): mean={prices.mean():.0f}, "
          f"median={prices.median():.0f}, min={prices.min():,}, max={prices.max():,}")
    print(f"  completion sample: {df['completion'].sample(5, random_state=42).tolist()}")

# --- Push ---
print(f"\nPushing to {OUTPUT} ...")
out.push_to_hub(OUTPUT, token=HF_TOKEN)
print("Done.")
