"""Hasaki.vn scraper — JSON API → JSONL output.

Output schema matches Tiki pipeline: {title, price, features, brand, category}
All products map to "Lam Dep - Suc Khoe" for the price prediction dataset.

Supports concurrent workers via ThreadPoolExecutor.
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

DELAY_LISTING = 0.3  # seconds between listing requests
DELAY_DETAIL = 0.3   # seconds between detail requests per worker

SKIP_CATEGORIES = {"Mini / Sample"}


def _make_session() -> requests.Session:
    """Create a session with retry logic (thread-safe via one session per thread)."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503])
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


# Thread-local sessions for concurrent workers
_thread_local = threading.local()


def _get_thread_session() -> requests.Session:
    """Get or create a requests.Session for the current thread."""
    if not hasattr(_thread_local, "session"):
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
    resp = session.get(HOME_API)
    resp.raise_for_status()
    data = resp.json()
    menu = data.get("cate_menu", [])

    all_cats = []
    for top_node in menu:
        all_cats.extend(_collect_leaf_categories(top_node))

    print(f"Found {len(all_cats)} leaf categories")
    return all_cats


def get_product_ids(session: requests.Session, cat_id: str) -> list[int]:
    """Fetch all product IDs for a category via listing pagination."""
    ids = []
    page = 1
    while True:
        url = LISTING_API.format(cat_id=cat_id, page=page)
        resp = session.get(url)
        resp.raise_for_status()
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
    url = PRODUCT_API.format(prod_id=prod_id)
    resp = session.get(url)
    resp.raise_for_status()
    prod = resp.json()

    name = prod.get("name", "").strip()
    price = prod.get("price")
    if not name or not price or int(price) <= 0:
        return None

    brand_info = prod.get("brand", {})
    brand = brand_info.get("name", "") if isinstance(brand_info, dict) else ""

    features = build_features(prod)
    can_buy = prod.get("can_buy", True)
    if not can_buy:
        return None

    time.sleep(DELAY_DETAIL)

    return {
        "title": name,
        "price": int(price),
        "features": features,
        "brand": brand,
        "category": f"Làm Đẹp - Sức Khỏe > {cat_path}",
    }


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

    # Step 1: Get product IDs
    prod_ids = get_product_ids(session, cat_id)
    if not prod_ids:
        print(f"  No products found, skipping")
        return 0

    if max_products > 0:
        prod_ids = prod_ids[:max_products]

    print(f"  Found {len(prod_ids)} product IDs, workers={workers}")

    # Step 2: Fetch details with concurrent workers
    count = 0
    errors = 0
    t_start = time.time()
    file_lock = threading.Lock()

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
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = _make_session()

    categories = get_categories(session)

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

    date_str = datetime.date.today().isoformat()
    suffix = "_test" if args.test else ""
    output_file = DATA_DIR / f"hasaki{suffix}_{date_str}.jsonl"

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


if __name__ == "__main__":
    main()
