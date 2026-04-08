"""
Tiki Scraper — Listing API -> Filter -> Detail API (concurrent) -> Save JSONL

Usage:
    from tiki_scraper.scraper import scrape_category, scrape_all
    products = scrape_category(8129, "Linh Kien May Tinh", max_products=1000, workers=3)
"""

import json
import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from curl_cffi import requests as curl_requests

from .config import (
    BASE_HEADERS,
    BATCH_SLEEP_EVERY,
    BATCH_SLEEP_SECONDS,
    BLOCK_WAIT_SECONDS,
    CHECKPOINT_EVERY,
    DEFAULT_WORKERS,
    DETAIL_DELAY,
    LISTING_DELAY,
    LISTING_LIMIT,
    MAX_RETRIES,
    MIN_FEATURES_LENGTH,
    PRICE_MAX,
    PRICE_MIN,
)
from .models import TikiProduct

logger = logging.getLogger(__name__)

# --- Price-Range Slicing constants ---
OVER_CAP = 2000  # Tiki listing API max results per query
MIN_PRICE_RANGE_VND = 1000  # Smallest range before Sort Rotation fallback
INITIAL_PRICE_RANGES = [
    (0, 50_000),
    (50_000, 100_000),
    (100_000, 200_000),
    (200_000, 500_000),
    (500_000, 1_000_000),
    (1_000_000, 2_000_000),
    (2_000_000, 5_000_000),
    (5_000_000, 50_000_000),
]
SORT_OPTIONS = [
    {},
    {"sort": "price,asc"},
    {"sort": "price,desc"},
    {"sort": "newest"},
]

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "Tiki_dataset_scrape"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"

# Thread-safe lock for file writing and checkpoint
_write_lock = threading.Lock()

# Thread-local storage for session reuse (1 session per worker thread)
_thread_local = threading.local()


def _new_session() -> curl_requests.Session:
    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(BASE_HEADERS)
    return session


def _strip_html(html: str) -> str:
    """Remove HTML tags, collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_features(detail: dict) -> str:
    """Combine description + specifications into a single features string."""
    parts = []

    short_desc = detail.get("short_description", "")
    if short_desc:
        parts.append(_strip_html(short_desc))

    desc = detail.get("description", "")
    if desc:
        parts.append(_strip_html(desc))

    specs = detail.get("specifications", [])
    for group in specs:
        attrs = group.get("attributes", [])
        for attr in attrs:
            name = attr.get("name", "")
            value = attr.get("value", "")
            if name and value:
                parts.append(f"{name}: {value}")

    return " | ".join(parts)


def _extract_brand(detail: dict) -> str:
    """Extract brand from detail response."""
    brand_obj = detail.get("brand", {})
    if isinstance(brand_obj, dict) and brand_obj.get("name"):
        return brand_obj["name"]
    for group in detail.get("specifications", []):
        for attr in group.get("attributes", []):
            if attr.get("code") == "brand":
                return attr.get("value", "")
    return ""


def _extract_category(detail: dict) -> str:
    """Extract category path from breadcrumbs (max 3 levels, skip product name)."""
    breadcrumbs = detail.get("breadcrumbs", [])
    if not breadcrumbs:
        return ""
    names = [b.get("name", "") for b in breadcrumbs if b.get("name")]
    if len(names) > 1:
        names = names[:-1]
    return " > ".join(names[:3])


# --- Listing API ---

def fetch_listing_page(
    session: curl_requests.Session,
    category_id: int,
    page: int,
    extra_params: dict | None = None,
) -> tuple[list[dict], int]:
    """Fetch one page of listings. Returns (items, total_count)."""
    url = "https://tiki.vn/api/v2/products"
    params = {
        "category": category_id,
        "limit": LISTING_LIMIT,
        "page": page,
        "include": "advertisement",
        "aggregations": 1,
    }
    if extra_params:
        params.update(extra_params)

    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                total = data.get("paging", {}).get("total", 0)
                return items, total
            if resp.status_code in (403, 429):
                logger.warning(
                    "Listing page %d: status %d, waiting %ds...",
                    page, resp.status_code, BLOCK_WAIT_SECONDS,
                )
                time.sleep(BLOCK_WAIT_SECONDS)
                continue
            logger.warning("Listing page %d: status %d", page, resp.status_code)
            return [], 0
        except Exception as e:
            logger.warning("Listing page %d attempt %d: %s", page, attempt + 1, e)
            time.sleep(5)

    return [], 0


def fetch_all_product_ids(
    session: curl_requests.Session,
    category_id: int,
    max_products: int | None = None,
    extra_params: dict | None = None,
) -> list[dict]:
    """Paginate listing API, return list of {id, name, price} for filtering."""
    all_items = []
    page = 1
    max_pages = OVER_CAP // LISTING_LIMIT  # 50 pages max

    while page <= max_pages:
        items, total = fetch_listing_page(session, category_id, page, extra_params)
        if not items:
            break

        all_items.extend(items)
        logger.info(
            "  Listing page %d: +%d items (total so far: %d, API total: %d)",
            page, len(items), len(all_items), total,
        )

        if max_products and len(all_items) >= max_products:
            all_items = all_items[:max_products]
            break

        # Stop when we have all items OR reached max pages
        if len(all_items) >= total:
            break

        page += 1
        time.sleep(random.uniform(*LISTING_DELAY))

    return all_items


# --- Detail API ---

def _get_thread_session() -> curl_requests.Session:
    """Get or create a session for the current worker thread (reused across requests)."""
    if not hasattr(_thread_local, "session"):
        _thread_local.session = _new_session()
        _thread_local.request_count = 0
    _thread_local.request_count += 1
    # Rotate session periodically to avoid stale connections
    from .config import SESSION_ROTATE_EVERY
    if _thread_local.request_count % SESSION_ROTATE_EVERY == 0:
        _thread_local.session.close()
        _thread_local.session = _new_session()
    return _thread_local.session


def fetch_product_detail(product_id: int) -> dict | None:
    """Fetch full product detail. Uses thread-local session (reused per worker)."""
    url = f"https://tiki.vn/api/v2/products/{product_id}"
    session = _get_thread_session()

    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (403, 429):
                logger.warning(
                    "Detail %d: status %d, waiting %ds...",
                    product_id, resp.status_code, BLOCK_WAIT_SECONDS,
                )
                time.sleep(BLOCK_WAIT_SECONDS)
                # Rotate session after rate limit
                _thread_local.session.close()
                _thread_local.session = _new_session()
                session = _thread_local.session
                continue
            if resp.status_code == 404:
                return None
            logger.warning("Detail %d: status %d", product_id, resp.status_code)
            return None
        except json.JSONDecodeError:
            # Response is not JSON (HTML redirect, deleted product) — skip, no retry
            logger.warning("Detail %d: non-JSON response (skipped)", product_id)
            return None
        except Exception as e:
            logger.warning("Detail %d attempt %d: %s", product_id, attempt + 1, e)
            time.sleep(2)

    return None


def _process_one_product(product_id: int, category_id: int) -> TikiProduct | None:
    """Fetch detail + extract fields for 1 product. Thread-safe."""
    time.sleep(random.uniform(*DETAIL_DELAY))

    detail = fetch_product_detail(product_id)
    if not detail:
        return None

    features = _extract_features(detail)
    if not features or len(features) < MIN_FEATURES_LENGTH:
        return None

    brand = _extract_brand(detail)
    category = _extract_category(detail)
    url_path = detail.get("url_path", "")
    url = f"https://tiki.vn/{url_path}" if url_path else ""
    price = detail.get("price", 0)

    return TikiProduct(
        product_id=product_id,
        title=detail.get("name", ""),
        brand=brand,
        price=price,
        features=features,
        url=url,
        category=category,
        category_id=category_id,
    )


# --- Adaptive Price-Range Slicing ---

def _fetch_listing_total(
    session: curl_requests.Session,
    category_id: int,
    extra_params: dict | None = None,
) -> int:
    """Quick query to get total count for a category + optional price range."""
    _, total = fetch_listing_page(session, category_id, page=1, extra_params=extra_params)
    return total


def _sort_rotation_merge(
    session: curl_requests.Session,
    category_id: int,
    price_min: int,
    price_max: int,
) -> list[dict]:
    """Fallback: query with multiple sort orders, merge + dedup by ID."""
    seen_ids = set()
    merged = []

    for sort_params in SORT_OPTIONS:
        params = {"price": f"{price_min},{price_max}", **sort_params}
        items = fetch_all_product_ids(session, category_id, extra_params=params)
        new_count = 0
        for item in items:
            pid = item.get("id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                merged.append(item)
                new_count += 1
        sort_name = sort_params.get("sort", "default")
        logger.info(
            "    Sort Rotation [%s]: +%d items, %d new (total unique: %d)",
            sort_name, len(items), new_count, len(merged),
        )
        time.sleep(random.uniform(*LISTING_DELAY))

    return merged


def _slice_recursive(
    session: curl_requests.Session,
    category_id: int,
    price_min: int,
    price_max: int,
    depth: int = 0,
) -> list[dict]:
    """Recursive price slicing. Split range in half until total <= OVER_CAP."""
    params = {"price": f"{price_min},{price_max}"}
    total = _fetch_listing_total(session, category_id, extra_params=params)
    time.sleep(random.uniform(*LISTING_DELAY))

    indent = "  " * (depth + 2)
    logger.info("%sRange %s-%s: %d SP", indent, f"{price_min:,}", f"{price_max:,}", total)

    if total == 0:
        return []

    if total < OVER_CAP:
        items = fetch_all_product_ids(session, category_id, extra_params=params)
        return items

    # Range too small to split further — use Sort Rotation fallback
    if (price_max - price_min) < MIN_PRICE_RANGE_VND:
        logger.info("%s-> Sort Rotation fallback (range < %d VND)", indent, MIN_PRICE_RANGE_VND)
        return _sort_rotation_merge(session, category_id, price_min, price_max)

    # Split in half
    mid = (price_min + price_max) // 2
    mid = mid // 1000 * 1000  # Round to 1000 VND
    if mid <= price_min:
        mid = price_min + 1000
    if mid >= price_max:
        return _sort_rotation_merge(session, category_id, price_min, price_max)

    logger.info("%s-> Splitting: %s-%s | %s-%s", indent, f"{price_min:,}", f"{mid:,}", f"{mid:,}", f"{price_max:,}")
    left = _slice_recursive(session, category_id, price_min, mid, depth + 1)
    right = _slice_recursive(session, category_id, mid, price_max, depth + 1)

    # Merge + dedup
    seen_ids = {item["id"] for item in left}
    merged = list(left)
    for item in right:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            merged.append(item)

    return merged


def fetch_all_ids_with_slicing(
    session: curl_requests.Session,
    category_id: int,
    max_products: int | None = None,
) -> list[dict]:
    """Fetch all product IDs, using price-range slicing for OVER_CAP categories."""
    # First try normal listing
    _, total = fetch_listing_page(session, category_id, page=1)

    if total < OVER_CAP:
        logger.info("  Category total: %d (under cap) — normal listing", total)
        return fetch_all_product_ids(session, category_id, max_products)

    # total >= OVER_CAP — API caps at 2000, real total is likely higher
    logger.info("  Category total: %d (OVER_CAP, real total likely higher) — using Price-Range Slicing", total)

    seen_ids = set()
    all_items = []

    for p_min, p_max in INITIAL_PRICE_RANGES:
        items = _slice_recursive(session, category_id, p_min, p_max)
        for item in items:
            pid = item.get("id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_items.append(item)

    logger.info("  Slicing done: %d unique items (baseline was capped at %d)", len(all_items), OVER_CAP)

    if max_products and len(all_items) > max_products:
        all_items = all_items[:max_products]

    return all_items


# --- Checkpoint ---

def _checkpoint_path(category_id: int) -> Path:
    return CHECKPOINT_DIR / f"cat_{category_id}_progress.json"


def load_checkpoint(category_id: int) -> set[int]:
    cp = _checkpoint_path(category_id)
    if cp.exists():
        data = json.loads(cp.read_text())
        return set(data.get("done_ids", []))
    return set()


def save_checkpoint(category_id: int, done_ids: set[int]):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    cp = _checkpoint_path(category_id)
    cp.write_text(json.dumps({"done_ids": list(done_ids)}))


# --- Main scrape ---

def scrape_category(
    category_id: int,
    category_name: str,
    max_products: int | None = None,
    output_dir: Path | None = None,
    workers: int = DEFAULT_WORKERS,
) -> list[TikiProduct]:
    """Scrape one category with concurrent detail fetching."""
    out_dir = output_dir or DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"tiki_{category_id}.jsonl"

    logger.info("=== Scraping [%d] %s (workers=%d) ===", category_id, category_name, workers)

    session = _new_session()

    # Step 1: Listing (with automatic price-range slicing for OVER_CAP)
    logger.info("Step 1: Fetching listing...")
    raw_items = fetch_all_ids_with_slicing(session, category_id, max_products)
    session.close()
    logger.info("  Got %d items from listing", len(raw_items))

    # Step 2: Filter by price
    filtered = [
        item for item in raw_items
        if PRICE_MIN <= (item.get("price") or 0) <= PRICE_MAX
    ]
    logger.info("Step 2: After price filter: %d items (removed %d)", len(filtered), len(raw_items) - len(filtered))

    # Load checkpoint
    done_ids = load_checkpoint(category_id)
    if done_ids:
        logger.info("  Resuming: %d already done", len(done_ids))

    to_scrape = [item for item in filtered if item["id"] not in done_ids]
    logger.info("  To scrape: %d items", len(to_scrape))

    if not to_scrape:
        logger.info("  Nothing to scrape, skipping.")
        return []

    # Step 3: Detail API — concurrent
    products = []
    done_count = 0
    detail_start = time.time()
    logger.info("Step 3: Fetching details (workers=%d)...", workers)

    product_ids = [item["id"] for item in to_scrape]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_process_one_product, pid, category_id): pid
            for pid in product_ids
        }

        for future in as_completed(futures):
            pid = futures[future]
            done_count += 1

            try:
                product = future.result()
            except Exception as e:
                logger.warning("  Product %d error: %s", pid, e)
                product = None

            with _write_lock:
                done_ids.add(pid)

                if product:
                    products.append(product)
                    with open(out_file, "a", encoding="utf-8") as f:
                        f.write(product.model_dump_json() + "\n")

                # Checkpoint
                if done_count % CHECKPOINT_EVERY == 0:
                    save_checkpoint(category_id, done_ids)

                # Batch sleep (moi BATCH_SLEEP_EVERY requests, tat ca workers pause)
                if done_count % BATCH_SLEEP_EVERY == 0:
                    time.sleep(BATCH_SLEEP_SECONDS)

            # Progress log
            if done_count % 50 == 0:
                elapsed = time.time() - detail_start
                speed = done_count / elapsed
                remaining = (len(to_scrape) - done_count) / speed if speed > 0 else 0
                eta_min, eta_sec = divmod(int(remaining), 60)
                eta_hour, eta_min = divmod(eta_min, 60)
                logger.info(
                    "  Progress: %d/%d done, %d saved | %.1f SP/s | ETA: %dh %dm %ds",
                    done_count, len(to_scrape), len(products),
                    speed, eta_hour, eta_min, eta_sec,
                )

    # Final checkpoint
    save_checkpoint(category_id, done_ids)

    total_time = time.time() - detail_start
    t_min, t_sec = divmod(int(total_time), 60)
    t_hour, t_min = divmod(t_min, 60)
    speed = len(products) / total_time if total_time > 0 else 0

    logger.info("=== Done [%d] %s ===", category_id, category_name)
    logger.info("  Total: %d products saved to %s", len(products), out_file)
    logger.info("  Time: %dh %dm %ds (%.1f SP/s)", t_hour, t_min, t_sec, speed)

    return products


def scrape_all(
    categories: list[tuple[int, str, int]] | None = None,
    max_per_category: int | None = None,
    workers: int = DEFAULT_WORKERS,
) -> list[TikiProduct]:
    """Scrape all categories in config. Returns all products."""
    from .config import SCRAPE_CATEGORIES

    cats = categories or SCRAPE_CATEGORIES
    all_products = []
    all_start = time.time()

    for idx, (cat_id, cat_name, _est) in enumerate(cats, 1):
        logger.info("--- Category %d/%d ---", idx, len(cats))
        products = scrape_category(
            cat_id, cat_name, max_products=max_per_category, workers=workers,
        )
        all_products.extend(products)

        elapsed = time.time() - all_start
        e_h, e_m = divmod(int(elapsed) // 60, 60)
        logger.info(
            "  Running total: %d products | Elapsed: %dh %dm | Categories: %d/%d",
            len(all_products), e_h, e_m, idx, len(cats),
        )

    total_time = time.time() - all_start
    t_h, t_m = divmod(int(total_time) // 60, 60)
    t_s = int(total_time) % 60
    speed = len(all_products) / total_time if total_time > 0 else 0

    logger.info("=" * 60)
    logger.info("ALL DONE")
    logger.info("  Total products: %d", len(all_products))
    logger.info("  Categories: %d", len(cats))
    logger.info("  Total time: %dh %dm %ds", t_h, t_m, t_s)
    logger.info("  Avg speed: %.1f SP/s", speed)
    logger.info("  Workers: %d", workers)
    logger.info("=" * 60)

    return all_products
