"""
Chay Tiki scraper.

Usage:
    # Test: cao 1 category, 50 san pham
    uv run scraping_data_tv/Tiki/run_scraper.py --test

    # Cao 1 category (vd: Tivi, max 200 san pham, 3 workers)
    uv run scraping_data_tv/Tiki/run_scraper.py --category 5015 --max 200 --workers 3

    # Cao TAT CA categories (47 categories, ~100K san pham)
    uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 3

    # Cao tat ca, gioi han moi category
    uv run scraping_data_tv/Tiki/run_scraper.py --all --max 500 --workers 5
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tiki_scraper.config import DEFAULT_WORKERS, SCRAPE_CATEGORIES
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
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"So workers song song (default: {DEFAULT_WORKERS}). WSL2: 1-3, May thue: 3-5",
    )
    args = parser.parse_args()

    w = args.workers

    if args.test:
        print(f"=== TEST MODE: Tivi, 50 san pham, workers={w} ===\n")
        products = scrape_category(5015, "Tivi", max_products=50, workers=w)
        print(f"\nDone: {len(products)} san pham")
        print(f"Luu tai: scraping_data_tv/Tiki/Tiki_dataset_scrape/tiki_5015.jsonl")

    elif args.all:
        total_est = sum(c[2] for c in SCRAPE_CATEGORIES)
        print(f"=== SCRAPE ALL: {len(SCRAPE_CATEGORIES)} categories, ~{total_est:,} san pham, workers={w} ===")
        if args.max:
            print(f"    Gioi han: {args.max} san pham/category")
        print(f"    Output: scraping_data_tv/Tiki/Tiki_dataset_scrape/\n")
        products = scrape_all(max_per_category=args.max, workers=w)
        print(f"\nDone: {len(products)} san pham tong cong")

    elif args.category:
        cat_name = args.name or "Unknown"
        if cat_name == "Unknown":
            for cid, cname, _ in SCRAPE_CATEGORIES:
                if cid == args.category:
                    cat_name = cname
                    break
        print(f"=== Scrape [{args.category}] {cat_name}, workers={w} ===\n")
        products = scrape_category(args.category, cat_name, max_products=args.max, workers=w)
        print(f"\nDone: {len(products)} san pham")
        print(f"Luu tai: scraping_data_tv/Tiki/Tiki_dataset_scrape/tiki_{args.category}.jsonl")

    else:
        parser.print_help()
        print("\nVi du:")
        print("  uv run scraping_data_tv/Tiki/run_scraper.py --test")
        print("  uv run scraping_data_tv/Tiki/run_scraper.py --category 1795 --workers 3")
        print("  uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 3")
        print("  uv run scraping_data_tv/Tiki/run_scraper.py --all --max 500 --workers 5")


if __name__ == "__main__":
    main()
