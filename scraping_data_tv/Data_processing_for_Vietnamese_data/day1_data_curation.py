"""Day 1: Data Curation — Load, clean, dedup, EDA, weighted sampling, split, push to HF Hub.

Updated 2026-04-10: 8 categories, category mapping, sub-category overrides.
"""

import json
import random
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

from pricer_vi.items import Item
from pricer_vi.parser import parse

# --- Configuration ---
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "Tiki" / "Tiki_dataset_scrape"
OUTPUT_DIR = SCRIPT_DIR / "output"
RANDOM_SEED = 42
HF_DATASET_NAME = "SeanSunny/items_raw_tv_v3"
TRAIN_SIZE = 100_000
VAL_SIZE = 5_000
TEST_SIZE = 5_000

# --- 8 Target Categories ---
# Map Tiki parent categories (from category.split(" > ")[0]) to 8 targets.
# None = drop the category.
CATEGORY_MAP = {
    # === Thoi Trang (gop tat ca fashion + phu kien + balo) ===
    "Thời Trang": "Thời Trang",
    "Thời trang nữ": "Thời Trang",
    "Thời trang nam": "Thời Trang",
    "Phụ kiện thời trang": "Thời Trang",
    "Balo và Vali": "Thời Trang",
    # === Nha Cua - Doi Song (gop cham soc nha cua) ===
    "Nhà Cửa - Đời Sống": "Nhà Cửa - Đời Sống",
    "Chăm sóc nhà cửa": "Nhà Cửa - Đời Sống",
    # === Dien Tu - Cong Nghe ===
    "Laptop - Máy Vi Tính - Linh kiện": "Điện Tử - Công Nghệ",
    "Thiết Bị Số - Phụ Kiện Số": "Điện Tử - Công Nghệ",
    # === Lam Dep - Suc Khoe ===
    "Làm Đẹp - Sức Khỏe": "Làm Đẹp - Sức Khỏe",
    # === Me va Be (gop Do Choi) ===
    "Đồ Chơi - Mẹ & Bé": "Mẹ và Bé",
    # === Dien Lanh va Gia Dung ===
    "Điện Gia Dụng": "Điện Lạnh và Gia Dụng",
    "Điện Tử - Điện Lạnh": "Điện Lạnh và Gia Dụng",
    # === Bach Hoa ===
    "Bách Hóa Online": "Bách Hóa",
    # === O To - Xe May ===
    "Ô Tô - Xe Máy - Xe Đạp": "Ô Tô - Xe Máy",
    # === BO ===
    "Nhà Sách Tiki": None,
}

# Sub-category overrides: items whose Tiki parent is wrong for our mapping.
# Check sub-category (parts[1]) to re-route specific items.
# Format: substring in sub-category → target category
SUBCATEGORY_OVERRIDES = {
    "Thể thao": "Nhà Cửa - Đời Sống",       # Tiki parent: Lam Dep, but we want: Nha Cua
    "Quà lưu niệm": "Mẹ và Bé",              # Tiki parent: Nha Sach, but we want: Me va Be
    "Văn phòng phẩm": "Nhà Cửa - Đời Sống",  # Tiki parent: Nha Sach, rescue into Nha Cua
}

# Weighted sampling: category penalties
CATEGORY_PENALTIES = {
    "Thời Trang": 0.40,
    "Nhà Cửa - Đời Sống": 0.60,
}


def _map_category(raw_cat: str, is_kaggle: bool) -> str | None:
    """Map a raw category string to one of 8 target categories, or None to drop."""
    if is_kaggle:
        return "Thời Trang"

    parts = raw_cat.split(" > ")
    parent = parts[0]
    sub = parts[1] if len(parts) > 1 else ""

    # Check sub-category overrides first (higher priority)
    for keyword, target in SUBCATEGORY_OVERRIDES.items():
        if keyword in sub or keyword in parent:
            return target

    # Map by parent category
    if parent in CATEGORY_MAP:
        return CATEGORY_MAP[parent]

    # Unknown parent — warn and drop
    return None


def load_all_items() -> list[Item]:
    """Load all JSONL files, parse into Item objects with 8-category mapping."""
    items = []
    dropped_cats = Counter()
    for filepath in sorted(DATA_DIR.glob("*.jsonl")):
        is_kaggle = "kaggle" in filepath.name
        count = 0
        for line in open(filepath, encoding="utf-8"):
            datapoint = json.loads(line)
            raw_cat = datapoint.get("category", "")
            category = _map_category(raw_cat, is_kaggle)
            if category is None:
                dropped_cats[raw_cat.split(" > ")[0] if " > " in raw_cat else raw_cat] += 1
                continue
            item = parse(datapoint, category)
            if item:
                items.append(item)
                count += 1
        print(f"  {filepath.name}: {count:,} items")

    if dropped_cats:
        print(f"\nDropped categories:")
        for cat, cnt in dropped_cats.most_common():
            print(f"  {cat}: {cnt:,} items")
    return items


def deduplicate(items: list[Item]) -> list[Item]:
    """Shuffle and remove duplicates by title, then by full text."""
    random.seed(RANDOM_SEED)
    random.shuffle(items)

    seen = set()
    items = [x for x in tqdm(items, desc="Dedup by title")
             if not (x.title in seen or seen.add(x.title))]

    seen = set()
    items = [x for x in tqdm(items, desc="Dedup by full")
             if not (x.full in seen or seen.add(x.full))]

    return items


def plot_eda(items: list[Item], prefix: str = ""):
    """Generate EDA charts matching English day1.ipynb pattern."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lengths = [len(item.full) for item in items]
    prices = [item.price for item in items]

    # 1. Text length histogram
    plt.figure(figsize=(15, 6))
    plt.title(f"Text length: Avg {sum(lengths)/len(lengths):,.0f} and highest {max(lengths):,}\n")
    plt.xlabel("Length (chars)")
    plt.ylabel("Count")
    plt.hist(lengths, rwidth=0.7, color="skyblue", bins=range(0, min(max(lengths) + 100, 6000), 100))
    plt.savefig(OUTPUT_DIR / f"{prefix}length_distribution.png", dpi=100, bbox_inches="tight")
    plt.close()

    # 2. Price histogram (log-scale for VND)
    plt.figure(figsize=(15, 6))
    plt.title(f"Prices (VND): Avg {sum(prices)/len(prices):,.0f}, Median {int(np.median(prices)):,}\n")
    plt.xlabel("Price (VND)")
    plt.ylabel("Count")
    log_bins = np.logspace(np.log10(max(min(prices), 1)), np.log10(max(prices) + 1), 50)
    plt.hist(prices, rwidth=0.7, color="blueviolet", bins=log_bins)
    plt.xscale("log")
    plt.savefig(OUTPUT_DIR / f"{prefix}price_distribution.png", dpi=100, bbox_inches="tight")
    plt.close()

    # 3. Category bar chart
    cat_counts = Counter([item.category for item in items])
    categories = list(cat_counts.keys())
    counts = [cat_counts[c] for c in categories]

    plt.figure(figsize=(15, 6))
    plt.bar(categories, counts, color="goldenrod")
    plt.title("How many in each category")
    plt.xlabel("Categories")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    for i, v in enumerate(counts):
        plt.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{prefix}category_distribution.png", dpi=100, bbox_inches="tight")
    plt.close()

    # 4. Category pie chart
    plt.figure(figsize=(12, 10))
    plt.pie(counts, labels=categories, autopct="%1.0f%%", startangle=90)
    centre_circle = plt.Circle((0, 0), 0.70, fc="white")
    plt.gcf().gca().add_artist(centre_circle)
    plt.title("Categories")
    plt.axis("equal")
    plt.savefig(OUTPUT_DIR / f"{prefix}category_pie.png", dpi=100, bbox_inches="tight")
    plt.close()

    # 5. Price vs text length scatter
    plt.figure(figsize=(15, 8))
    plt.scatter(lengths, prices, s=0.2, color="red")
    plt.xlabel("Text length (chars)")
    plt.ylabel("Price (VND)")
    plt.title("Is there a simple correlation with text length?")
    plt.savefig(OUTPUT_DIR / f"{prefix}price_vs_length.png", dpi=100, bbox_inches="tight")
    plt.close()

    # Print stats
    print(f"\n--- EDA Stats ({prefix.strip('_') or 'raw'}) ---")
    print(f"Total items: {len(items):,}")
    print(f"Price: min={min(prices):,}, max={max(prices):,}, avg={sum(prices)/len(prices):,.0f}, median={int(np.median(prices)):,}")
    print(f"Text length: min={min(lengths)}, max={max(lengths):,}, avg={sum(lengths)/len(lengths):,.0f}")
    print(f"Categories: {len(cat_counts)}")
    for cat, cnt in cat_counts.most_common():
        print(f"  {cat}: {cnt:,} ({cnt/len(items)*100:.1f}%)")


def weighted_sample(items: list[Item]) -> list[Item]:
    """Apply price^2 weighting and category penalties."""
    total = len(items)
    target_size = TRAIN_SIZE + VAL_SIZE + TEST_SIZE

    if total <= target_size:
        print(f"Total items ({total:,}) <= target ({target_size:,}), using all items")
        sample_size = total
    else:
        sample_size = target_size

    np.random.seed(RANDOM_SEED)
    prices = np.array([it.price for it in items], dtype=float)
    categories = np.array([it.category for it in items])

    # Normalize prices to [0, 1]
    p = (prices - prices.min()) / (prices.max() - prices.min() + 1e-9)

    # Price^2 weighting — boost expensive items
    w = p ** 2

    # Category penalties
    for cat, penalty in CATEGORY_PENALTIES.items():
        w[categories == cat] *= penalty

    # Normalize to probability distribution
    w = w / w.sum()

    idx = np.random.choice(len(items), size=sample_size, replace=False, p=w)
    return [items[i] for i in idx]


def split_dataset(items: list[Item]) -> tuple[list[Item], list[Item], list[Item]]:
    """Split into train/val/test."""
    random.seed(RANDOM_SEED)
    random.shuffle(items)

    test = items[:TEST_SIZE]
    val = items[TEST_SIZE:TEST_SIZE + VAL_SIZE]
    train = items[TEST_SIZE + VAL_SIZE:]
    return train, val, test


def main():
    print("=== Day 1: Data Curation ===\n")

    # Step 1: Load
    print("Step 1: Loading all JSONL files...")
    items = load_all_items()
    print(f"\nLoaded: {len(items):,} items")

    # Step 2: EDA before dedup
    print("\nStep 2: EDA (before dedup)...")
    plot_eda(items, prefix="01_before_dedup_")

    # Step 3: Dedup
    print("\nStep 3: Deduplication...")
    before = len(items)
    items = deduplicate(items)
    print(f"After dedup: {len(items):,} items (removed {before - len(items):,})")

    # Step 4: EDA after dedup
    print("\nStep 4: EDA (after dedup)...")
    plot_eda(items, prefix="02_after_dedup_")

    # Step 5: Weighted sampling
    print("\nStep 5: Weighted sampling...")
    sample = weighted_sample(items)
    print(f"Sample size: {len(sample):,}")

    # Step 6: Final shuffle
    random.seed(RANDOM_SEED)
    random.shuffle(sample)

    # Step 7: Split
    print("\nStep 7: Split dataset...")
    train, val, test = split_dataset(sample)
    print(f"Train: {len(train):,}, Val: {len(val):,}, Test: {len(test):,}")

    # Step 8: EDA after sampling
    print("\nStep 8: EDA (after sampling)...")
    plot_eda(sample, prefix="03_after_sampling_")

    # Step 9: Push to HuggingFace Hub
    print(f"\nStep 9: Push to HuggingFace Hub ({HF_DATASET_NAME})...")
    try:
        from huggingface_hub import login
        from dotenv import load_dotenv
        import os
        load_dotenv(override=True)
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            login(hf_token, add_to_git_credential=True)
            Item.push_to_hub(HF_DATASET_NAME, train, val, test)
            print(f"Pushed to {HF_DATASET_NAME}")
        else:
            print("HF_TOKEN not found in .env, skipping push")
    except Exception as e:
        print(f"Push failed: {e}")
        print("You can push manually later from the notebook")

    print(f"\nCharts saved to: {OUTPUT_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()
