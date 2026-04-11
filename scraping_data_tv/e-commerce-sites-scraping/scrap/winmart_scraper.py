"""WinMart.vn scraper — JSON API -> JSONL output.

Output schema matches Tiki pipeline: {title, price, features, brand, category}
All products map to "Bach Hoa" for the price prediction dataset.

Features:
- Pagination until items list is empty (API totalCount unreliable)
- Per-category JSONL files (resume support)
- Global dedup by product name
- Report mode: list all categories with product counts
- HTML stripping for longDescription

API: api-crownx.winmart.vn/it/api/web/v3/item/category
NOTE: API may timeout from non-VN IPs. Run from VN network.
"""

import html as html_module
import json
import re
import time
import argparse
import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Config ---
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

API_BASE = "https://api-crownx.winmart.vn/it/api/web/v3"
CATEGORY_ENDPOINT = f"{API_BASE}/item/category"

HEADERS = {
    "authorization": "Bearer",
    "x-api-merchant": "WCM",
    "origin": "https://winmart.vn",
    "referer": "https://winmart.vn/",
    "accept": "application/json",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

PAGE_SIZE = 100  # API supports up to 100
DELAY_BETWEEN_PAGES = 0.5
DELAY_BETWEEN_CATEGORIES = 1.0
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Parent-level category slugs from WinMart sitemap.
# Parent slugs aggregate all sub-category products (confirmed via API test).
# Using parents avoids empty leaf-slug responses from certain storeCode.
# Format: (slug, display_name)
CATEGORIES = [
    ("sua-cac-loai--c08", "Sua cac loai"),
    ("rau-cu-trai-cay--c02", "Rau cu trai cay"),
    ("hoa-pham-tay-rua--c10", "Hoa pham tay rua"),
    ("cham-soc-ca-nhan--c11", "Cham soc ca nhan"),
    ("thit-hai-san-tuoi--c03", "Thit, hai san tuoi"),
    ("banh-keo--c07", "Banh keo"),
    ("do-uong-co-con--c31", "Do uong co con"),
    ("do-uong-giai-khat--c09", "Do uong giai khat"),
    ("mi-thuc-pham-an-lien--c34", "Mi, thuc pham an lien"),
    ("thuc-pham-che-bien--c04", "Thuc pham che bien"),
    ("thuc-pham-kho--c06", "Thuc pham kho"),
    ("gia-vi--c35", "Gia vi"),
    ("thuc-pham-dong-lanh--c05", "Thuc pham dong lanh"),
    ("trung-dau-hu--c33", "Trung, dau hu"),
    ("cham-soc-be--c12", "Cham soc be"),
    ("do-dung-gia-dinh--c25", "Do dung gia dinh"),
    ("dien-gia-dung--c26", "Dien gia dung"),
    ("van-phong-pham-do-choi--c27", "Van phong pham, do choi"),
]


def _make_session() -> requests.Session:
    """Create a session with retry logic."""
    session = requests.Session()
    retry = Retry(total=MAX_RETRIES, backoff_factor=1.0, status_forcelist=[500, 502, 503])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_module.unescape(text)
    text = re.sub(r"\\n|\\r|\\t", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_page(
    session: requests.Session, slug: str, page: int, page_size: int = PAGE_SIZE
) -> list[dict]:
    """Fetch one page of products. Returns items list (empty = no more pages)."""
    params = {
        "orderByDesc": "true",
        "pageNumber": page,
        "pageSize": page_size,
        "slug": slug,
        "storeCode": "1535",
        "storeGroupCode": "1998",
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(CATEGORY_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return data.get("items", [])
            if resp.status_code in (403, 429):
                wait = 30 * (attempt + 1)
                print(f"  BLOCKED ({resp.status_code}), waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"  HTTP {resp.status_code} for {slug} page {page}")
            return []
        except requests.exceptions.Timeout:
            wait = 10 * (attempt + 1)
            print(f"  TIMEOUT for {slug} p{page}, waiting {wait}s (attempt {attempt+1})")
            time.sleep(wait)
        except Exception as e:
            print(f"  Error fetching {slug} p{page}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
    return []


def parse_item(item: dict, display_name: str) -> dict | None:
    """Convert a WinMart API item to JSONL record."""
    name = (item.get("name") or "").strip()
    price = item.get("price")
    if not name or not price or int(price) <= 0:
        return None

    brand = (item.get("brandName") or "").strip()

    # Build features from short + long description
    parts = []
    short_desc = _strip_html(item.get("shortDescription", ""))
    if short_desc and short_desc != name:
        parts.append(short_desc)

    long_desc = _strip_html(item.get("longDescription", ""))
    if long_desc:
        if len(long_desc) > 2000:
            long_desc = long_desc[:2000]
        parts.append(long_desc)

    features = " | ".join(parts)

    # Build category path from mch hierarchy
    mch_parts = []
    for level in range(1, 6):
        mch_name = item.get(f"mch{level}Name", "")
        if mch_name:
            mch_parts.append(mch_name)
    if mch_parts:
        category = " > ".join(mch_parts)
    else:
        cat_name = item.get("categoryName", display_name)
        category = f"Bach Hoa Online > {cat_name}"

    return {
        "title": name,
        "price": int(price),
        "features": features,
        "brand": brand,
        "category": category,
    }


def scrape_category(
    session: requests.Session,
    slug: str,
    display_name: str,
    output_file: Path,
    page_size: int = PAGE_SIZE,
    max_products: int = 0,
) -> int:
    """Scrape all products in a category, write to JSONL file."""
    print(f"\n--- Category: {display_name} (slug={slug}) ---")

    count = 0
    seen_names = set()
    page = 1
    t_start = time.time()

    with open(output_file, "w", encoding="utf-8") as f:
        while True:
            items = fetch_page(session, slug, page=page, page_size=page_size)
            if not items:
                break

            for item in items:
                row = parse_item(item, display_name)
                if row and row["title"] not in seen_names:
                    seen_names.add(row["title"])
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
                    if max_products > 0 and count >= max_products:
                        break

            if max_products > 0 and count >= max_products:
                break

            if page % 3 == 0:
                elapsed = time.time() - t_start
                print(f"  Page {page}: {count} saved ({elapsed:.1f}s)")

            page += 1
            time.sleep(DELAY_BETWEEN_PAGES)

    elapsed = time.time() - t_start
    print(f"  Done: {count} products in {elapsed:.1f}s ({page-1} pages)")
    return count


def generate_report(session: requests.Session, page_size: int = PAGE_SIZE):
    """Scan all categories by fetching all pages, write report."""
    print(f"\nScanning {len(CATEGORIES)} categories...\n")
    print(f"{'Slug':<40} | {'Count':>6} | Name")
    print("-" * 70)

    results = []
    total_products = 0

    for slug, name in CATEGORIES:
        # Count all items by paginating
        count = 0
        page = 1
        while True:
            items = fetch_page(session, slug, page=page, page_size=page_size)
            if not items:
                break
            count += len(items)
            page += 1
            time.sleep(DELAY_BETWEEN_PAGES)

        results.append({"slug": slug, "name": name, "count": count})
        total_products += count
        print(f"{slug:<40} | {count:>6} | {name}")
        time.sleep(DELAY_BETWEEN_CATEGORIES)

    print(f"\n{'='*70}")
    print(f"TOTAL: {len(results)} categories, {total_products:,} products")

    # Write report
    report_file = SCRIPT_DIR / "winmart_categories_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# WinMart Categories Report\n\n")
        f.write(f"**Cap nhat:** {datetime.date.today().isoformat()}\n")
        f.write(f"**Tong categories:** {len(results)}\n")
        f.write(f"**Tong san pham:** {total_products:,}\n")
        f.write(f"**pageSize:** {page_size}\n")
        f.write(f"**Category map:** Tat ca -> Bach Hoa\n\n")
        f.write("---\n\n")
        f.write("| # | Slug | Name | So SP |\n")
        f.write("|---:|---|---|---:|\n")
        for i, r in enumerate(sorted(results, key=lambda x: x["count"], reverse=True), 1):
            f.write(f"| {i} | `{r['slug']}` | {r['name']} | {r['count']:,} |\n")
        f.write(f"\n**Tong:** {total_products:,} SP\n\n")
        f.write("---\n\n")
        f.write("*Tao tu dong boi `winmart_scraper.py --report`*\n")

    print(f"\nReport saved: {report_file}")


def test_api(session: requests.Session):
    """Quick test: fetch products from a known category to verify API."""
    slug = "rau-cu-trai-cay--c02"
    print(f"Testing API with slug: {slug}")
    print()

    items = fetch_page(session, slug, page=1, page_size=5)
    if not items:
        print("FAILED: No items returned. API may be blocked from non-VN IPs.")
        print("Try running from a VN network.")
        return

    print(f"SUCCESS! Got {len(items)} items on page 1")
    print()

    for i, item in enumerate(items):
        row = parse_item(item, "Rau cu trai cay")
        if row:
            print(f"  Product {i+1}:")
            print(f"    title: {row['title']}")
            print(f"    price: {row['price']:,} VND")
            print(f"    brand: {row['brand']}")
            print(f"    category: {row['category']}")
            feat_preview = row["features"][:120] + "..." if len(row["features"]) > 120 else row["features"]
            print(f"    features: {feat_preview}")
            print()

    # Test pagination
    print("Testing pagination...")
    total = 0
    page = 1
    while True:
        items = fetch_page(session, slug, page=page, page_size=100)
        if not items:
            break
        total += len(items)
        page += 1
        time.sleep(DELAY_BETWEEN_PAGES)
    print(f"  Total items in '{slug}': {total} ({page-1} pages)")


def main():
    parser = argparse.ArgumentParser(description="WinMart.vn scraper")
    parser.add_argument("--test", action="store_true", help="Test API connectivity + pagination")
    parser.add_argument("--report", action="store_true", help="Generate categories report (count all)")
    parser.add_argument("--max", type=int, default=0, help="Max products per category (0 = all)")
    parser.add_argument("--slug", type=str, default="", help="Scrape only this category slug")
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE, help=f"Products per page (default: {PAGE_SIZE})")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = _make_session()

    if args.test:
        test_api(session)
        return

    if args.report:
        generate_report(session, page_size=args.page_size)
        return

    # Scraping mode
    categories = CATEGORIES
    if args.slug:
        categories = [(s, n) for s, n in CATEGORIES if s == args.slug]
        if not categories:
            print(f"Slug '{args.slug}' not found in CATEGORIES list")
            return

    print(f"Output dir: {DATA_DIR}")
    print(f"Categories: {len(categories)}, pageSize: {args.page_size}")
    if args.max > 0:
        print(f"Max products per category: {args.max}")

    total = 0
    skipped = 0
    t_start = time.time()

    for idx, (slug, name) in enumerate(categories):
        slug_clean = slug.split("--")[0]
        out_file = DATA_DIR / f"winmart_{slug_clean}.jsonl"

        # Skip if file already exists (resume support)
        if out_file.exists() and out_file.stat().st_size > 0:
            line_count = sum(1 for _ in open(out_file, encoding="utf-8"))
            print(f"\n[{idx+1}/{len(categories)}] {name} ({slug}) — SKIP ({line_count} SP already)")
            skipped += 1
            continue

        print(f"\n[{idx+1}/{len(categories)}]", end="")
        count = scrape_category(
            session, slug, name, out_file,
            page_size=args.page_size,
            max_products=args.max,
        )
        total += count
        time.sleep(DELAY_BETWEEN_CATEGORIES)

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"DONE: {total} products scraped, {skipped} categories skipped")
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"Output dir: {DATA_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
