"""Analyze raw category distribution from all JSONL files to plan category merging."""

import json
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent / "Tiki" / "Tiki_dataset_scrape"


def main():
    # Collect parent categories and sub-categories
    parent_counter = Counter()
    sub_counter = Counter()
    parent_to_subs = defaultdict(Counter)
    source_counter = Counter()

    total = 0
    for f in sorted(DATA_DIR.glob("*.jsonl")):
        is_kaggle = "kaggle" in f.name
        source = "kaggle" if is_kaggle else "scraper"

        for line in open(f, encoding="utf-8"):
            row = json.loads(line)
            raw_cat = row.get("category", "")
            parts = raw_cat.split(" > ")
            parent = parts[0] if parts else raw_cat
            sub = parts[1] if len(parts) > 1 else "(no sub)"

            parent_counter[parent] += 1
            sub_counter[raw_cat] += 1
            parent_to_subs[parent][sub] += 1
            source_counter[source] += 1
            total += 1

    print(f"Total: {total:,} SP")
    print(f"  Scraper: {source_counter['scraper']:,}")
    print(f"  Kaggle:  {source_counter['kaggle']:,}")
    print(f"  Parent categories: {len(parent_counter)}")
    print()

    print("=" * 80)
    print("PARENT CATEGORY DISTRIBUTION (sorted by count)")
    print("=" * 80)
    for cat, cnt in parent_counter.most_common():
        pct = cnt / total * 100
        bar = "#" * int(pct)
        print(f"  {cnt:>7,} ({pct:5.1f}%) | {cat}")

    print()
    print("=" * 80)
    print("DETAILED: PARENT -> SUB-CATEGORIES")
    print("=" * 80)
    for parent, cnt in parent_counter.most_common():
        print(f"\n--- {parent} ({cnt:,} SP) ---")
        for sub, sub_cnt in parent_to_subs[parent].most_common(10):
            print(f"    {sub_cnt:>6,} | {sub}")
        remaining = len(parent_to_subs[parent]) - 10
        if remaining > 0:
            print(f"    ... and {remaining} more sub-categories")


if __name__ == "__main__":
    main()
