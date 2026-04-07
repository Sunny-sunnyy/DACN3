"""
Step 1: Test Shopee Search API
Thu goi shopee.vn/api/v4/search/search_items bang curl_cffi.
Muc tieu: xem API co tra ve data khong, bi block khong.
"""

import json
import time
from pathlib import Path

from curl_cffi import requests as curl_requests

# ============================================================
# CONFIG
# ============================================================
KEYWORD = "tai nghe"
OUTPUT_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://shopee.vn/api/v4/search/search_items"

SEARCH_PARAMS = {
    "keyword": KEYWORD,
    "limit": 60,
    "newest": 0,
    "by": "relevancy",
    "order": "desc",
    "page_type": "search",
    "scenario": "PAGE_GLOBAL_SEARCH",
    "version": 2,
}


# ============================================================
# FUNCTIONS
# ============================================================
def init_session():
    """Tao curl_cffi session voi Chrome impersonation."""
    session = curl_requests.Session(impersonate="chrome")
    session.headers.update({
        "Referer": "https://shopee.vn",
        "X-Requested-With": "XMLHttpRequest",
        "X-API-SOURCE": "pc",
    })
    # Visit homepage de lay cookies
    print("[1/4] Visiting shopee.vn homepage to get cookies...")
    resp = session.get("https://shopee.vn", timeout=15)
    print(f"  Homepage status: {resp.status_code}")
    print(f"  Cookies: {len(session.cookies)} cookies received")
    return session


def test_search(session):
    """Thu goi Search API, return raw JSON response."""
    print(f"\n[2/4] Calling Search API: keyword='{KEYWORD}'...")
    resp = session.get(SEARCH_URL, params=SEARCH_PARAMS, timeout=15)
    print(f"  Status: {resp.status_code}")
    print(f"  Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    print(f"  Response size: {len(resp.content)} bytes")

    if resp.status_code != 200:
        print(f"  ERROR: Non-200 status code!")
        print(f"  Response text (first 500 chars): {resp.text[:500]}")
        return None

    try:
        data = resp.json()
    except json.JSONDecodeError:
        print("  ERROR: Response is not JSON!")
        print(f"  Response text (first 500 chars): {resp.text[:500]}")
        return None

    return data


def analyze_search_response(data):
    """Phan tich response tu Search API."""
    print("\n[3/4] Analyzing search response...")

    if data is None:
        print("  No data to analyze.")
        return []

    # In top-level keys
    print(f"  Top-level keys: {list(data.keys())}")

    # Check error
    if "error" in data:
        print(f"  Error code: {data.get('error')}")
        print(f"  Error msg: {data.get('error_msg', 'N/A')}")

    # Tim items trong response
    items = data.get("items") or data.get("item") or []
    total = data.get("total_count", "N/A")
    print(f"  Total count: {total}")
    print(f"  Items in this page: {len(items)}")

    if not items:
        print("  WARNING: No items found! Shopee may be blocking or API structure changed.")
        # In raw response de debug
        print(f"  Full response (first 2000 chars):")
        print(f"  {json.dumps(data, ensure_ascii=False)[:2000]}")
        return []

    # In 3 san pham dau tien
    print(f"\n  --- First 3 products ---")
    for i, item in enumerate(items[:3]):
        # Shopee co the wrap item trong "item_basic" hoac truc tiep
        product = item.get("item_basic", item)
        name = product.get("name", "N/A")
        price = product.get("price", 0)
        price_normalized = price / 100_000 if price > 100_000 else price
        shop_id = product.get("shopid", "N/A")
        item_id = product.get("itemid", "N/A")
        sold = product.get("historical_sold", product.get("sold", "N/A"))

        print(f"\n  [{i+1}] {name}")
        print(f"      Price raw: {price} -> Normalized: {price_normalized:,.0f} VND")
        print(f"      Shop ID: {shop_id}, Item ID: {item_id}")
        print(f"      Sold: {sold}")

    return items


def save_response(data, filename="search_response.json"):
    """Luu raw response ra file."""
    output_path = OUTPUT_DIR / filename
    print(f"\n[4/4] Saving raw response to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved! ({output_path.stat().st_size:,} bytes)")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Shopee API Test - Step 1")
    print("=" * 60)

    session = init_session()
    data = test_search(session)

    if data:
        items = analyze_search_response(data)
        save_response(data)

        if items:
            print(f"\n{'=' * 60}")
            print(f"SUCCESS: Got {len(items)} items from Search API!")
            print(f"Next: test product detail API, then pagination.")
            print(f"{'=' * 60}")
        else:
            print(f"\n{'=' * 60}")
            print(f"WARNING: API returned data but no items.")
            print(f"Check data/raw/search_response.json for full response.")
            print(f"{'=' * 60}")
    else:
        print(f"\n{'=' * 60}")
        print(f"FAILED: Could not get data from Shopee API.")
        print(f"Next: try Selenium+BS4 approach or investigate headers.")
        print(f"{'=' * 60}")
