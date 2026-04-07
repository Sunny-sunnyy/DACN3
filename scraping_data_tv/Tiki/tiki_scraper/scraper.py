"""
Tiki Scraper — Listing API -> Filter -> Detail API -> Save JSONL

Usage:
    from tiki_scraper.scraper import scrape_category, scrape_all
    products = scrape_category(8129, "Linh Kien May Tinh", max_products=1000)
"""

import json
import logging
import random
import re
import time
from pathlib import Path

from curl_cffi import requests as curl_requests

from .config import (
    BASE_HEADERS,
    BATCH_SLEEP_EVERY,
    BATCH_SLEEP_SECONDS,
    BLOCK_WAIT_SECONDS,
    CHECKPOINT_EVERY,
    DETAIL_DELAY,
    LISTING_DELAY,
    LISTING_LIMIT,
    MAX_RETRIES,
    MIN_FEATURES_LENGTH,
    PRICE_MAX,
    PRICE_MIN,
    SESSION_ROTATE_EVERY,
)
from .models import TikiProduct

logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "Tiki_dataset_scrape"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"


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

    # Short description
    short_desc = detail.get("short_description", "")
    if short_desc:
        parts.append(_strip_html(short_desc))

    # Full description
    desc = detail.get("description", "")
    if desc:
        parts.append(_strip_html(desc))

    # Specifications
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
    # Fallback: tim trong specifications
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
    # Breadcrumb cuoi la ten san pham -> bo di, lay toi da 3 cap
    names = [b.get("name", "") for b in breadcrumbs if b.get("name")]
    if len(names) > 1:
        names = names[:-1]  # bo ten san pham
    return " > ".join(names[:3])


# --- Listing API ---

def fetch_listing_page(
    session: curl_requests.Session,
    category_id: int,
    page: int,
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
) -> list[dict]:
    """Paginate listing API, return list of {id, name, price} for filtering."""
    all_items = []
    page = 1

    while True:
        items, total = fetch_listing_page(session, category_id, page)
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

        if len(items) < LISTING_LIMIT:
            break  # last page

        page += 1
        time.sleep(random.uniform(*LISTING_DELAY))

    return all_items


# --- Detail API ---

def fetch_product_detail(
    session: curl_requests.Session,
    product_id: int,
) -> dict | None:
    """Fetch full product detail. Returns raw JSON dict or None."""
    url = f"https://tiki.vn/api/v2/products/{product_id}"

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
                continue
            if resp.status_code == 404:
                return None
            logger.warning("Detail %d: status %d", product_id, resp.status_code)
            return None
        except Exception as e:
            logger.warning("Detail %d attempt %d: %s", product_id, attempt + 1, e)
            time.sleep(5)

    return None


# --- Checkpoint ---

def _checkpoint_path(category_id: int) -> Path:
    return CHECKPOINT_DIR / f"cat_{category_id}_progress.json"


def load_checkpoint(category_id: int) -> set[int]:
    """Load set of already-scraped product IDs."""
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
) -> list[TikiProduct]:
    """
    Scrape one category: listing -> filter -> detail -> save.
    Returns list of TikiProduct.
    """
    out_dir = output_dir or DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"tiki_{category_id}.jsonl"

    logger.info("=== Scraping [%d] %s ===", category_id, category_name)

    session = _new_session()
    request_count = 0

    # Step 1: Listing — get all product IDs
    logger.info("Step 1: Fetching listing...")
    raw_items = fetch_all_product_ids(session, category_id, max_products)
    logger.info("  Got %d items from listing", len(raw_items))

    # Step 2: Filter by price
    filtered = [
        item for item in raw_items
        if PRICE_MIN <= (item.get("price") or 0) <= PRICE_MAX
    ]
    logger.info("Step 2: After price filter: %d items (removed %d)", len(filtered), len(raw_items) - len(filtered))

    # Load checkpoint (resume)
    done_ids = load_checkpoint(category_id)
    if done_ids:
        logger.info("  Resuming: %d already done", len(done_ids))

    to_scrape = [item for item in filtered if item["id"] not in done_ids]
    logger.info("  To scrape: %d items", len(to_scrape))

    # Step 3: Detail API for each product
    products = []
    logger.info("Step 3: Fetching details...")

    for i, item in enumerate(to_scrape):
        pid = item["id"]

        # Session rotation
        request_count += 1
        if request_count % SESSION_ROTATE_EVERY == 0:
            session.close()
            session = _new_session()
            logger.info("  Rotated session at request #%d", request_count)

        # Batch sleep
        if request_count % BATCH_SLEEP_EVERY == 0:
            time.sleep(BATCH_SLEEP_SECONDS)

        detail = fetch_product_detail(session, pid)
        if not detail:
            done_ids.add(pid)
            continue

        # Extract fields
        features = _extract_features(detail)
        brand = _extract_brand(detail)
        category = _extract_category(detail)
        url_path = detail.get("url_path", "")
        url = f"https://tiki.vn/{url_path}" if url_path else ""
        price = detail.get("price", 0)

        # Validate
        if not features or len(features) < MIN_FEATURES_LENGTH:
            done_ids.add(pid)
            continue

        product = TikiProduct(
            product_id=pid,
            title=detail.get("name", ""),
            brand=brand,
            price=price,
            features=features,
            url=url,
            category=category,
            category_id=category_id,
        )
        products.append(product)
        done_ids.add(pid)

        # Append to JSONL
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(product.model_dump_json() + "\n")

        # Checkpoint
        if len(done_ids) % CHECKPOINT_EVERY == 0:
            save_checkpoint(category_id, done_ids)

        # Progress log
        if (i + 1) % 50 == 0:
            logger.info("  Progress: %d/%d done, %d saved", i + 1, len(to_scrape), len(products))

        time.sleep(random.uniform(*DETAIL_DELAY))

    # Final checkpoint
    save_checkpoint(category_id, done_ids)
    session.close()

    logger.info(
        "=== Done [%d] %s: %d products saved to %s ===",
        category_id, category_name, len(products), out_file,
    )
    return products


def scrape_all(
    categories: list[tuple[int, str, int]] | None = None,
    max_per_category: int | None = None,
) -> list[TikiProduct]:
    """Scrape all categories in config. Returns all products."""
    from .config import SCRAPE_CATEGORIES

    cats = categories or SCRAPE_CATEGORIES
    all_products = []

    for cat_id, cat_name, _est in cats:
        products = scrape_category(cat_id, cat_name, max_products=max_per_category)
        all_products.extend(products)
        logger.info("Total so far: %d products", len(all_products))

    logger.info("=== ALL DONE: %d products from %d categories ===", len(all_products), len(cats))
    return all_products
