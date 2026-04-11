"""Hasaki.vn scraper — JSON API -> JSONL output.

Output schema matches Tiki pipeline: {title, price, features, brand, category}
All products map to "Lam Dep - Suc Khoe" for the price prediction dataset.

Features:
- ThreadPoolExecutor workers with thread-local sessions
- Block handling (403/429): wait + session rotation
- Timing: speed (SP/s), ETA per category, global stats
- File naming: hasaki_category_{id}.jsonl per category, or hasaki_all_{date}.jsonl
"""

import html as html_module
import json
import re
import time
import argparse
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Config ---
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

HOME_API = "https://hasaki.vn/wap/v2/master/?page=newHeaderHome"
LISTING_API = (
    "https://hasaki.vn/wap/v2/catalog/category/get-listing-product"
    "?cat={cat_id}&p={page}&product_list_limit=40&more_data=1&lstType=1&lstId=0"
)
PRODUCT_API = "https://hasaki.vn/wap/v2/product/detail?id={prod_id}"

DELAY_LISTING = 0.3
DELAY_DETAIL = 0.3
BLOCK_WAIT_SECONDS = 60  # Wait when 403/429
MAX_RETRIES = 3
BATCH_SLEEP_EVERY = 100  # Pause every N products
BATCH_SLEEP_SECONDS = 2

SKIP_CATEGORIES = {"Mini / Sample"}


def _make_session() -> requests.Session:
    """Create a session with retry logic."""
    session = requests.Session()
    retry = Retry(total=MAX_RETRIES, backoff_factor=1.0, status_forcelist=[500, 502, 503])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    })
    return session


_thread_local = threading.local()
_request_count = 0
_request_lock = threading.Lock()


def _get_thread_session() -> requests.Session:
    """Thread-local session with rotation every 200 requests."""
    if not hasattr(_thread_local, "session"):
        _thread_local.session = _make_session()
        _thread_local.count = 0
    _thread_local.count += 1
    if _thread_local.count % 200 == 0:
        _thread_local.session.close()
        _thread_local.session = _make_session()
    return _thread_local.session


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_module.unescape(text)
    text = re.sub(r"\\n|\\r|\\t", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _collect_leaf_categories(node: dict, parent_path: str = "") -> list[dict]:
    """Recursively collect leaf categories from the Hasaki menu tree."""
    name = node.get("name", "")
    cat_id = node.get("id", "")
    path = f"{parent_path} > {name}" if parent_path else name

    if name in SKIP_CATEGORIES:
        return []

    children = node.get("child", [])
    if not children:
        return [{"id": cat_id, "name": name, "path": path}]

    leaves = []
    for child in children:
        leaves.extend(_collect_leaf_categories(child, path))
    return leaves


def get_categories(session: requests.Session) -> list[dict]:
    """Fetch all leaf categories from the Hasaki home API."""
    print("Fetching categories from Hasaki API...")
    resp = session.get(HOME_API, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    menu = data.get("cate_menu", [])

    all_cats = []
    for top_node in menu:
        all_cats.extend(_collect_leaf_categories(top_node))

    print(f"Found {len(all_cats)} leaf categories")
    return all_cats


def _fetch_with_block_handling(session: requests.Session, url: str) -> requests.Response:
    """Fetch URL with 403/429 block detection and wait."""
    for attempt in range(MAX_RETRIES):
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            return resp
        if resp.status_code in (403, 429):
            print(f"  BLOCKED ({resp.status_code}), waiting {BLOCK_WAIT_SECONDS}s... (attempt {attempt+1})")
            time.sleep(BLOCK_WAIT_SECONDS)
            session.close()
            session = _make_session()
            continue
        resp.raise_for_status()
    return resp


def get_product_ids(session: requests.Session, cat_id: str) -> list[int]:
    """Fetch all product IDs for a category via listing pagination."""
    ids = []
    page = 1
    while True:
        url = LISTING_API.format(cat_id=cat_id, page=page)
        resp = _fetch_with_block_handling(session, url)
        listing = resp.json().get("listing", [])
        if not listing:
            break
        for item in listing:
            pid = item.get("id")
            if pid:
                ids.append(int(pid))
        page += 1
        time.sleep(DELAY_LISTING)
    return ids


def get_product_count(session: requests.Session, cat_id: str) -> int:
    """Quick count: fetch 1 page of listing, return total product IDs found."""
    ids = []
    page = 1
    while True:
        url = LISTING_API.format(cat_id=cat_id, page=page)
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                break
            listing = resp.json().get("listing", [])
            if not listing:
                break
            ids.extend(listing)
            page += 1
            time.sleep(DELAY_LISTING)
        except Exception:
            break
    return len(ids)


def build_features(prod: dict) -> str:
    """Build features string from product detail JSON."""
    parts = []

    short_desc = _strip_html(prod.get("short_description", ""))
    if short_desc:
        parts.append(short_desc)

    attrs = prod.get("attribute_show", [])
    if attrs:
        for attr in attrs:
            label = attr.get("label", "")
            val = attr.get("val", "")
            if val and val is not False and str(val).strip():
                parts.append(f"{label}: {val}")

    description = _strip_html(prod.get("description", ""))
    if description:
        if len(description) > 2000:
            description = description[:2000]
        parts.append(description)

    return " | ".join(parts)


def scrape_product_worker(prod_id: int, cat_path: str) -> dict | None:
    """Fetch a single product detail (called from thread worker)."""
    session = _get_thread_session()

    for attempt in range(MAX_RETRIES):
        try:
            url = PRODUCT_API.format(prod_id=prod_id)
            resp = session.get(url, timeout=15)

            if resp.status_code == 200:
                prod = resp.json()

                name = prod.get("name", "").strip()
                price = prod.get("price")
                if not name or not price or int(price) <= 0:
                    return None

                can_buy = prod.get("can_buy", True)
                if not can_buy:
                    return None

                brand_info = prod.get("brand", {})
                brand = brand_info.get("name", "") if isinstance(brand_info, dict) else ""
                features = build_features(prod)

                time.sleep(DELAY_DETAIL)
                return {
                    "title": name,
                    "price": int(price),
                    "features": features,
                    "brand": brand,
                    "category": f"Làm Đẹp - Sức Khỏe > {cat_path}",
                }

            if resp.status_code in (403, 429):
                print(f"  Product {prod_id}: BLOCKED ({resp.status_code}), waiting {BLOCK_WAIT_SECONDS}s...")
                time.sleep(BLOCK_WAIT_SECONDS)
                _thread_local.session.close()
                _thread_local.session = _make_session()
                session = _thread_local.session
                continue

            if resp.status_code == 404:
                return None

            return None

        except requests.exceptions.JSONDecodeError:
            return None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
            else:
                print(f"  Product {prod_id}: failed after {MAX_RETRIES} attempts: {e}")
                return None

    return None


def scrape_category(
    session: requests.Session,
    cat: dict,
    output_file: Path,
    max_products: int = 0,
    workers: int = 1,
) -> int:
    """Scrape all products in a category, append to JSONL file."""
    cat_id = cat["id"]
    cat_path = cat["path"]
    cat_name = cat["name"]

    print(f"\n--- Category: {cat_name} (id={cat_id}) ---")

    prod_ids = get_product_ids(session, cat_id)
    if not prod_ids:
        print(f"  No products found, skipping")
        return 0

    if max_products > 0:
        prod_ids = prod_ids[:max_products]

    print(f"  Found {len(prod_ids)} product IDs, workers={workers}")

    count = 0
    errors = 0
    t_start = time.time()
    file_lock = threading.Lock()
    batch_count = 0

    with open(output_file, "a", encoding="utf-8") as f:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(scrape_product_worker, pid, cat_path): pid
                for pid in prod_ids
            }
            for i, future in enumerate(as_completed(futures)):
                pid = futures[future]
                try:
                    row = future.result()
                    if row:
                        with file_lock:
                            f.write(json.dumps(row, ensure_ascii=False) + "\n")
                            count += 1
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        print(f"  Error on product {pid}: {type(e).__name__}: {e}")

                # Batch sleep to avoid overloading server
                batch_count += 1
                if batch_count % BATCH_SLEEP_EVERY == 0:
                    time.sleep(BATCH_SLEEP_SECONDS)

                if (i + 1) % 50 == 0:
                    elapsed = time.time() - t_start
                    speed = (i + 1) / elapsed if elapsed > 0 else 0
                    remaining = (len(prod_ids) - i - 1) / speed if speed > 0 else 0
                    print(
                        f"  Progress: {i+1}/{len(prod_ids)} "
                        f"({count} saved, {speed:.1f} SP/s, "
                        f"ETA {remaining:.0f}s)"
                    )

    elapsed = time.time() - t_start
    speed = count / elapsed if elapsed > 0 else 0
    print(f"  Done: {count} products in {elapsed:.1f}s ({speed:.1f} SP/s), {errors} errors")
    return count


def main():
    parser = argparse.ArgumentParser(description="Hasaki.vn scraper")
    parser.add_argument("--test", action="store_true", help="Test mode: 1 category, 5 products")
    parser.add_argument("--max", type=int, default=0, help="Max products per category (0 = all)")
    parser.add_argument("--category", type=str, default="", help="Scrape only this category ID")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent workers (default: 1)")
    parser.add_argument("--report", action="store_true", help="Generate categories report (no scraping)")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = _make_session()
    categories = get_categories(session)

    # Report mode: list all categories with product counts
    if args.report:
        generate_report(session, categories)
        return

    # Filter
    if args.category:
        categories = [c for c in categories if str(c["id"]) == args.category]
        if not categories:
            print(f"Category {args.category} not found")
            return

    if args.test:
        categories = categories[:1]
        max_per_cat = args.max if args.max > 0 else 5
        workers = 1
    else:
        max_per_cat = args.max
        workers = args.workers

    # Output file naming
    date_str = datetime.date.today().isoformat()
    if args.test:
        output_file = DATA_DIR / f"hasaki_test_{date_str}.jsonl"
    elif args.category:
        output_file = DATA_DIR / f"hasaki_category_{args.category}.jsonl"
    else:
        output_file = DATA_DIR / f"hasaki_all_{date_str}.jsonl"

    print(f"\nOutput: {output_file}")
    print(f"Categories: {len(categories)}, workers: {workers}")
    if max_per_cat > 0:
        print(f"Max products per category: {max_per_cat}")

    total = 0
    t_global = time.time()

    for idx, cat in enumerate(categories):
        print(f"\n[{idx+1}/{len(categories)}]", end="")
        count = scrape_category(session, cat, output_file, max_per_cat, workers)
        total += count

    elapsed = time.time() - t_global
    speed = total / elapsed if elapsed > 0 else 0
    print(f"\n{'='*60}")
    print(f"DONE: {total} products total in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"Speed: {speed:.1f} SP/s")
    print(f"Output: {output_file}")
    print(f"{'='*60}")


def generate_report(session: requests.Session, categories: list[dict]):
    """Scan all categories, count products, write report markdown."""
    print(f"\nScanning {len(categories)} categories for product counts...\n")
    print(f"{'ID':>8} | {'Count':>6} | {'Category'}")
    print("-" * 70)

    results = []
    total_products = 0

    for cat in categories:
        cat_id = cat["id"]
        cat_name = cat["name"]
        cat_path = cat["path"]
        count = get_product_count(session, cat_id)
        results.append({"id": cat_id, "name": cat_name, "path": cat_path, "count": count})
        total_products += count
        print(f"{cat_id:>8} | {count:>6} | {cat_path}")
        time.sleep(DELAY_LISTING)

    print(f"\n{'='*70}")
    print(f"TOTAL: {len(results)} categories, {total_products:,} products")

    # Group by parent category
    parent_groups = {}
    for r in results:
        parts = r["path"].split(" > ")
        parent = parts[0] if parts else "Other"
        parent_groups.setdefault(parent, []).append(r)

    # Write report markdown
    report_file = SCRIPT_DIR / "hasaki_categories_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Hasaki Categories Report\n\n")
        f.write(f"**Cap nhat:** {datetime.date.today().isoformat()}\n")
        f.write(f"**Tong leaf categories:** {len(results)}\n")
        f.write(f"**Tong san pham uoc tinh:** {total_products:,}\n")
        f.write(f"**Category map:** Tat ca -> Lam Dep - Suc Khoe\n\n")
        f.write("---\n\n")

        for parent, cats in parent_groups.items():
            parent_total = sum(c["count"] for c in cats)
            f.write(f"### {parent} ({len(cats)} sub-categories, {parent_total:,} SP)\n\n")
            f.write(f"| ID | Category | So SP |\n")
            f.write(f"|---:|---|---:|\n")
            for c in sorted(cats, key=lambda x: x["count"], reverse=True):
                f.write(f"| {c['id']} | {c['name']} | {c['count']:,} |\n")
            f.write(f"\n")

        f.write("---\n\n")
        f.write(f"*Tao tu dong boi `hasaki_scraper.py --report`*\n")

    print(f"\nReport saved: {report_file}")


if __name__ == "__main__":
    main()
