"""Push items_tv_v8 và items_prompts_tv_4 lên HuggingFace.

Chạy sau khi Groq batch đã hoàn thành (output_aug_v3/ đã có đủ file).
Không cần GPU, không cần Groq API.

Pipeline:
  1. Load items_tv_v7 từ HF → filter → parse → bucket multipliers
  2. Load batch state + rebuild request_list
  3. Đọc output_aug_v3/ → rebuild aug_results
  4. Build v8_rows → free RAM → push items_tv_v8
  5. Build aug prompts → load items_prompts_tv_3 → combine → push items_prompts_tv_4
"""
import gc
import json
import os
import pickle
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from datasets import Dataset, DatasetDict, Features, Value, load_dataset
from dotenv import load_dotenv
from huggingface_hub import login
from tqdm.auto import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent

SOURCE_TV7 = "SeanSunny/items_tv_v7"
OUTPUT_TV8 = "SeanSunny/items_tv_v8"
SOURCE_TV3 = "SeanSunny/items_prompts_tv_3"
OUTPUT_TV4 = "SeanSunny/items_prompts_tv_4"

MAX_PRICE     = 1_000_000
QUESTION_FULL = "Sản phẩm này có giá bao nhiêu ?"
PRICE_PREF    = "\n\nGiá là: "
SEED          = 42
MODEL         = "openai/gpt-oss-20b"
BATCH_SIZE    = 1_000

OUTPUT_FOLDER = SCRIPT_DIR / "output_aug_v3"
STATE_FILE    = SCRIPT_DIR / "batches_aug_v3.pkl"

V8_FEATURES = Features({
    "title":            Value("string"),
    "category":         Value("string"),
    "price":            Value("int64"),
    "brand":            Value("string"),
    "summary":          Value("string"),
    "summary_version2": Value("string"),
    "aug_version":      Value("int64"),
})

random.seed(SEED)
np.random.seed(SEED)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
load_dotenv(SCRIPT_DIR.parent / ".env")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN not set in .env")
login(HF_TOKEN)
print("HF login OK")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def parse_summary(summary: str):
    """Returns (header, body) tuple or None if format unrecognised."""
    if not summary:
        return None
    header_lines, body_lines = [], []
    for line in summary.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(("Tiêu đề:", "Tieu de:")):
            header_lines.append(line)
        elif line.startswith(("Danh mục:", "Danh muc:")):
            header_lines.append(line)
        elif line.startswith(("Thương hiệu:", "Thuong hieu:")):
            header_lines.append(line)
        elif line.startswith(("Mô tả:", "Mo ta:")):
            body_lines.append(line)
        elif line.startswith(("Thông số:", "Thong so:")):
            body_lines.append(line)
    if len(header_lines) == 3 and len(body_lines) == 2:
        return "\n".join(header_lines), "\n".join(body_lines)
    return None


def parse_aug_output(llm_text: str):
    """Extract (mo_ta, thong_so) from LLM output or return None."""
    mo_ta = thong_so = None
    for line in llm_text.strip().split("\n"):
        line = line.strip()
        if line.startswith(("Mô tả:", "Mo ta:")):
            mo_ta = re.sub(r'^(M[oô] t[aả]):?\s*', '', line).strip()
        elif line.startswith(("Thông số:", "Thong so:")):
            thong_so = re.sub(r'^(Th[oô]ng s[oố]):?\s*', '', line).strip()
    if mo_ta and thong_so:
        return mo_ta, thong_so
    return None


def build_user_message(full_text: str, body: str) -> str:
    return f"Thông tin sản phẩm gốc:\n{full_text}\n\n---\nTóm tắt hiện tại:\n{body}"


# ---------------------------------------------------------------------------
# Batch state dataclass (must match original for unpickling)
# ---------------------------------------------------------------------------
@dataclass
class AugBatch:
    start: int
    end: int
    filename: str
    file_id: Optional[str] = None
    batch_id: Optional[str] = None
    output_file_id: Optional[str] = None
    done: bool = False


# ---------------------------------------------------------------------------
# Step 1: Load items_tv_v7
# ---------------------------------------------------------------------------
print(f"\n[1/7] Loading {SOURCE_TV7} ...")
ds_v7 = load_dataset(SOURCE_TV7)
train_v7 = list(ds_v7["train"])
val_v7   = list(ds_v7["validation"])
test_v7  = list(ds_v7["test"])
print(f"  train={len(train_v7):,} | val={len(val_v7):,} | test={len(test_v7):,}")

# Verify schema
s = train_v7[0]
assert s.get("full"),    "full column missing in items_tv_v7"
assert s.get("summary"), "summary column missing in items_tv_v7"

# ---------------------------------------------------------------------------
# Step 2: Filter + parse_summary + bucket multipliers
# ---------------------------------------------------------------------------
print("[2/7] Filter + parse + bucket multipliers ...")
train_filtered = [row for row in train_v7 if row["price"] <= MAX_PRICE]
for idx, row in enumerate(train_filtered):
    row["_idx"] = idx
print(f"  train_filtered: {len(train_filtered):,} / {len(train_v7):,}")

BUCKETS = [
    ("<50K",     0,          50_000,   5),
    ("50-100K",  50_000,    100_000,   3),
    ("100-200K", 100_000,   200_000,   2),
    ("200-500K", 200_000,   500_000,   1),
    ("500K-1M",  500_000, 1_000_001,   4),
]
prices_arr = np.array([row["price"] for row in train_filtered])
bucket_multipliers: dict[int, int] = {}
for name, lo, hi, mult in BUCKETS:
    for idx in np.where((prices_arr >= lo) & (prices_arr < hi))[0]:
        bucket_multipliers[int(idx)] = mult
assert len(bucket_multipliers) == len(train_filtered), "Bucket multipliers incomplete"

# ---------------------------------------------------------------------------
# Step 3: Load batch state + rebuild request_list
# ---------------------------------------------------------------------------
print(f"[3/7] Loading batch state from {STATE_FILE} ...")
with STATE_FILE.open("rb") as f:
    batches: list[AugBatch] = pickle.load(f)
done_count = sum(1 for b in batches if b.done)
print(f"  Batches: {done_count}/{len(batches)} done")

request_list = []
skipped = 0
for idx, row in enumerate(tqdm(train_filtered, desc="  Rebuilding request_list")):
    result = parse_summary(row["summary"])
    if result is None:
        skipped += 1
        continue
    _, body = result
    full_text = row["full"] or ""
    for v in range(bucket_multipliers[idx]):
        request_list.append((idx, v, build_user_message(full_text, body)))
print(f"  request_list: {len(request_list):,} | skipped: {skipped}")

# ---------------------------------------------------------------------------
# Step 4: Read output files → rebuild aug_results
# ---------------------------------------------------------------------------
print(f"[4/7] Reading output files from {OUTPUT_FOLDER} ...")
output_files = list(OUTPUT_FOLDER.glob("aug_*.jsonl"))
print(f"  Files found: {len(output_files)} / {len(batches)} batches")

missing_files = [b.filename for b in batches if not (OUTPUT_FOLDER / b.filename).exists()]
if missing_files:
    print(f"  WARNING: {len(missing_files)} missing files: {missing_files[:5]}")

aug_results: dict[tuple[int, int], str] = {}
for batch in tqdm(batches, desc="  Reading outputs"):
    out_path = OUTPUT_FOLDER / batch.filename
    if not out_path.exists():
        continue
    with out_path.open(encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            cid = obj["custom_id"]
            parts = cid.split("_")
            item_idx, version = int(parts[0]), int(parts[1])
            aug_results[(item_idx, version)] = (
                obj["response"]["body"]["choices"][0]["message"]["content"]
            )
print(f"  Collected: {len(aug_results):,} / {len(request_list):,} | missing: {len(request_list) - len(aug_results)}")

# ---------------------------------------------------------------------------
# Step 5: Build v8_rows
# ---------------------------------------------------------------------------
print("[5/7] Building v8_rows ...")
v8_rows = []
build_ok = build_fail = 0

for (item_idx, version), llm_text in tqdm(aug_results.items(), desc="  Building v8 rows"):
    row = train_filtered[item_idx]
    result = parse_summary(row["summary"])
    if result is None:
        build_fail += 1
        continue
    header, _ = result
    parsed = parse_aug_output(llm_text)
    if parsed is None:
        build_fail += 1
        continue
    mo_ta, thong_so = parsed
    new_body = f"Mô tả: {mo_ta}\nThông số: {thong_so}"
    v8_rows.append({
        "title":            row["title"],
        "category":         row["category"],
        "price":            row["price"],
        "brand":            row.get("brand"),
        "summary":          row["summary"],
        "summary_version2": f"{header}\n{new_body}",
        "aug_version":      version,
    })
    build_ok += 1

print(f"  v8_rows: {build_ok:,} OK | {build_fail} failed")

# Free heavy objects no longer needed
del train_v7, aug_results, request_list
gc.collect()
print("  RAM freed: train_v7, aug_results, request_list")

# ---------------------------------------------------------------------------
# Step 6: Push items_tv_v8
# ---------------------------------------------------------------------------
print(f"[6/7] Pushing {OUTPUT_TV8} ...")

def strip_full(rows: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if k != "full"} for r in rows]

def make_val_test_rows(rows: list[dict]) -> list[dict]:
    """Val/test keep v7 columns, add summary_version2=None, aug_version=None."""
    return [{
        "title":            r["title"],
        "category":         r["category"],
        "price":            r["price"],
        "brand":            r.get("brand"),
        "summary":          r["summary"],
        "summary_version2": None,
        "aug_version":      None,
    } for r in rows]

ds_v8 = DatasetDict({
    "train":      Dataset.from_list(strip_full(v8_rows),         features=V8_FEATURES),
    "validation": Dataset.from_list(make_val_test_rows(val_v7),  features=V8_FEATURES),
    "test":       Dataset.from_list(make_val_test_rows(test_v7), features=V8_FEATURES),
})
print(f"  {ds_v8}")
ds_v8.push_to_hub(OUTPUT_TV8, private=True, max_shard_size="20MB")
print(f"  Pushed: https://huggingface.co/datasets/{OUTPUT_TV8}")

del ds_v8, val_v7, test_v7
gc.collect()
print("  RAM freed: ds_v8, val_v7, test_v7")

# ---------------------------------------------------------------------------
# Step 7: Build items_prompts_tv_4
# ---------------------------------------------------------------------------
print(f"[7/7] Building and pushing {OUTPUT_TV4} ...")

# Build aug prompts from v8_rows
aug_examples = []
for row in tqdm(v8_rows, desc="  Building aug prompts"):
    sv2 = row["summary_version2"]
    if not sv2:
        continue
    aug_examples.append({
        "prompt":         f"{QUESTION_FULL}\n{sv2}{PRICE_PREF}",
        "completion":     str(int(round(row["price"] / 1000))),
        "price_vnd_true": int(row["price"]),
    })
print(f"  Aug prompts: {len(aug_examples):,}")

del v8_rows, train_filtered
gc.collect()
print("  RAM freed: v8_rows, train_filtered")

# Load original tv_3
print(f"  Loading {SOURCE_TV3} ...")
ds_tv3    = load_dataset(SOURCE_TV3)
orig_train = list(ds_tv3["train"])
orig_val   = list(ds_tv3["val"])
orig_test  = list(ds_tv3["test"])
print(f"  orig train={len(orig_train):,} | val={len(orig_val):,} | test={len(orig_test):,}")
assert set(orig_train[0].keys()) == {"prompt", "completion", "price_vnd_true"}, "Schema mismatch tv_3"

del ds_tv3
gc.collect()

# Combine + shuffle
combined_train = orig_train + aug_examples
random.seed(SEED)
random.shuffle(combined_train)
print(f"  Combined: {len(orig_train):,} orig + {len(aug_examples):,} aug = {len(combined_train):,}")

assert all(ex["prompt"] for ex in combined_train), "Empty prompt found"
assert all(ex["completion"] for ex in combined_train), "Empty completion found"
prices_check = [ex["price_vnd_true"] for ex in combined_train]
print(f"  Price range: {min(prices_check):,} — {max(prices_check):,} VND")

ds_tv4 = DatasetDict({
    "train": Dataset.from_list(combined_train),
    "val":   Dataset.from_list(orig_val),
    "test":  Dataset.from_list(orig_test),
})
print(f"  {ds_tv4}")
ds_tv4.push_to_hub(OUTPUT_TV4, private=True, max_shard_size="20MB")
print(f"  Pushed: https://huggingface.co/datasets/{OUTPUT_TV4}")

print(f"\nDone. items_prompts_tv_4 train size: {len(combined_train):,}")
