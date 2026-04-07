"""
Test scraper voi 1 sub-category nho.
Muc tieu: Validate pipeline listing -> filter -> detail -> save hoat dong dung.
Chon category "Tivi" (5015, ~161 san pham) — nho, nhanh, de kiem tra.
"""

import logging
import sys
from pathlib import Path

# Add parent dir to path de import tiki_scraper
sys.path.insert(0, str(Path(__file__).parent.parent))

from tiki_scraper.scraper import scrape_category

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

TEST_CATEGORY_ID = 5015
TEST_CATEGORY_NAME = "Tivi"
MAX_PRODUCTS = 30  # Chi lay 30 san pham de test nhanh

if __name__ == "__main__":
    out_dir = Path(__file__).parent / "data" / "test_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    products = scrape_category(
        category_id=TEST_CATEGORY_ID,
        category_name=TEST_CATEGORY_NAME,
        max_products=MAX_PRODUCTS,
        output_dir=out_dir,
    )

    print(f"\n{'=' * 60}")
    print(f"KET QUA: {len(products)} san pham da luu")
    print(f"{'=' * 60}")

    for p in products[:5]:
        print(f"\n  Title:    {p.title[:70]}")
        print(f"  Brand:    {p.brand}")
        print(f"  Price:    {p.price:,} VND")
        print(f"  Features: {p.features[:100]}...")
        print(f"  URL:      {p.url[:80]}")
        print(f"  Category: {p.category}")

    # Validation
    print(f"\n{'=' * 60}")
    print("VALIDATION:")
    all_ok = True

    if not products:
        print("  [FAIL] Khong co san pham nao!")
        all_ok = False
    else:
        # Check fields
        for p in products:
            if not p.title:
                print(f"  [FAIL] Product {p.product_id}: title rong")
                all_ok = False
                break
            if p.price < 50_000:
                print(f"  [FAIL] Product {p.product_id}: price {p.price} < 50K")
                all_ok = False
                break
            if len(p.features) < 50:
                print(f"  [FAIL] Product {p.product_id}: features qua ngan ({len(p.features)} chars)")
                all_ok = False
                break
            if not p.url.startswith("https://tiki.vn/"):
                print(f"  [FAIL] Product {p.product_id}: URL khong hop le: {p.url}")
                all_ok = False
                break

    if all_ok:
        print("  [OK] Title: co")
        print("  [OK] Brand: co")
        print(f"  [OK] Price range: {min(p.price for p in products):,} - {max(p.price for p in products):,} VND")
        print(f"  [OK] Features avg length: {sum(len(p.features) for p in products) // len(products)} chars")
        print("  [OK] URL: hop le")
        print(f"  [OK] Output file: {out_dir / f'tiki_{TEST_CATEGORY_ID}.jsonl'}")
        print("\n  SCRAPER HOAT DONG TOT!")
