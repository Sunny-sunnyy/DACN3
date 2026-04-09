"""Convert Kaggle Tiki CSV files to JSONL format matching scraper output."""

import csv
import json
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "Tiki_dataset_1"
OUTPUT_DIR = Path(__file__).parent / "Tiki_dataset_scrape"

BRAND_MAP = {
    "men_bags": "túi xách nam",
    "women_bags": "túi xách nữ",
    "backpacks_suitcases": "Balo vali",
    "fashion_accessories": "phụ kiện thời trang",
    "men_shoes": "giày nam",
    "women_shoes": "giày nữ",
}


def _clean(text: str) -> str:
    """Remove unusual line terminators (U+2028 LS, U+2029 PS)."""
    return text.strip().replace("\u2028", " ").replace("\u2029", " ")


def convert_file(csv_path: Path, brand: str, output_path: Path) -> int:
    """Convert one CSV file to JSONL. Returns number of rows written."""
    count = 0
    with (
        open(csv_path, encoding="utf-8") as fin,
        open(output_path, "w", encoding="utf-8") as fout,
    ):
        reader = csv.DictReader(fin)
        for row in reader:
            record = {
                "title": _clean(row["name"]),
                "brand": brand,
                "price": int(float(row["price"])),
                "features": _clean(row["description"]),
                "category": _clean(row["category"]),
            }
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main():
    total = 0
    for csv_path in sorted(INPUT_DIR.glob("*.csv")):
        key = csv_path.stem.replace("vietnamese_tiki_products_", "")
        brand = BRAND_MAP.get(key)
        if brand is None:
            print(f"SKIP: {csv_path.name} — no brand mapping for '{key}'")
            continue

        output_path = OUTPUT_DIR / f"tiki_kaggle_{key}.jsonl"
        count = convert_file(csv_path, brand, output_path)
        total += count
        print(f"{csv_path.name} -> {output_path.name}: {count:,} SP (brand: {brand})")

    print(f"\nTong: {total:,} SP tu {len(BRAND_MAP)} files")


if __name__ == "__main__":
    main()
