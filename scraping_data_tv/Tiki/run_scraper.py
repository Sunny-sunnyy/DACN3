"""
Chay Tiki scraper.

Usage:
    # Test: cao 1 category, 50 san pham
    uv run scraping_data_tv/Tiki/run_scraper.py --test

    # Cao 1 category cu the (vd: Tivi, max 200 san pham)
    uv run scraping_data_tv/Tiki/run_scraper.py --category 5015 --max 200

    # Cao TAT CA categories (47 categories, ~100K san pham, ~33 gio)
    uv run scraping_data_tv/Tiki/run_scraper.py --all

    # Cao tat ca nhung gioi han moi category (vd: 500/category)
    uv run scraping_data_tv/Tiki/run_scraper.py --all --max 500
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tiki_scraper.config import SCRAPE_CATEGORIES
from tiki_scraper.scraper import scrape_all, scrape_category

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(description="Tiki Scraper")
    parser.add_argument("--test", action="store_true", help="Test: cao Tivi, 50 san pham")
    parser.add_argument("--all", action="store_true", help="Cao tat ca 47 categories")
    parser.add_argument("--category", type=int, help="Cao 1 category theo ID")
    parser.add_argument("--max", type=int, default=None, help="So san pham toi da moi category")
    parser.add_argument("--name", type=str, default=None, help="Ten category (neu ID khong co trong config)")
    args = parser.parse_args()

    if args.test:
        print("=== TEST MODE: Tivi, 50 san pham ===\n")
        products = scrape_category(5015, "Tivi", max_products=50)
        print(f"\nDone: {len(products)} san pham")
        print(f"Luu tai: scraping_data_tv/Tiki/Tiki_dataset_scrape/tiki_5015.jsonl")

    elif args.all:
        total_est = sum(c[2] for c in SCRAPE_CATEGORIES)
        print(f"=== SCRAPE ALL: {len(SCRAPE_CATEGORIES)} categories, ~{total_est:,} san pham ===")
        if args.max:
            print(f"    Gioi han: {args.max} san pham/category")
        print(f"    Output: scraping_data_tv/Tiki/Tiki_dataset_scrape/\n")
        products = scrape_all(max_per_category=args.max)
        print(f"\nDone: {len(products)} san pham tong cong")

    elif args.category:
        # Tim ten category — ho tro ca --name tu dong
        cat_name = args.name or "Unknown"
        if cat_name == "Unknown":
            for cid, cname, _ in SCRAPE_CATEGORIES:
                if cid == args.category:
                    cat_name = cname
                    break
        print(f"=== Scrape [{args.category}] {cat_name} ===\n")
        products = scrape_category(args.category, cat_name, max_products=args.max)
        print(f"\nDone: {len(products)} san pham")
        print(f"Luu tai: scraping_data_tv/Tiki/Tiki_dataset_scrape/tiki_{args.category}.jsonl")

    else:
        parser.print_help()
        print("\nVi du:")
        print("  uv run scraping_data_tv/Tiki/run_scraper.py --test")
        print("  uv run scraping_data_tv/Tiki/run_scraper.py --category 5015 --max 200")
        print("  uv run scraping_data_tv/Tiki/run_scraper.py --all")
        print("  uv run scraping_data_tv/Tiki/run_scraper.py --all --max 500")


if __name__ == "__main__":
    main()
