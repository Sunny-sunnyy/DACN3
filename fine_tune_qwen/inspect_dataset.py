"""Inspect SeanSunny/items_tv_v6 — show columns, dtypes, sample rows."""
from datasets import load_dataset

ds = load_dataset("SeanSunny/items_tv_v6")
train = ds["train"]

print("=== Splits ===")
print(ds)

print("\n=== Columns ===")
for col in train.column_names:
    print(f"  {col}")

print("\n=== Sample row 0 (raw) ===")
row = train[0]
for k, v in row.items():
    val_str = str(v)[:200]
    print(f"  [{k}]  {val_str}")

print("\n=== Sample row 0 — check 'summary' field ===")
summary = row.get("summary") or row.get("text") or row.get("description") or "(not found)"
print(summary[:500])

print("\n=== Non-null counts (first 1000 rows) ===")
df = train.select(range(1000)).to_pandas()
for col in df.columns:
    non_null = df[col].notna().sum()
    sample_val = df[col].dropna().iloc[0] if non_null > 0 else None
    sample_str = str(sample_val)[:100] if sample_val is not None else "N/A"
    print(f"  {col:30s}  non-null={non_null}/1000  sample={sample_str}")
