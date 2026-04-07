"""
Step 1 - V3: Test Shopee API voi cookies tu browser.

HUONG DAN lay cookies:
1. Mo Chrome, truy cap: https://shopee.vn/search?keyword=tai+nghe
2. F12 -> Network tab -> Filter "search_items" -> Reload page
3. Click vao request "search_items?..." -> Headers tab
4. Tim dong "Cookie:" -> Copy TOAN BO gia tri (chuoi dai)
5. Paste vao file: step1/cookies.txt (1 dong duy nhat)
6. Chay script nay: uv run scraping_data_tv/Shopee/step1/02_test_with_cookies.py
"""

import json
from pathlib import Path

from curl_cffi import requests as curl_requests

OUTPUT_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
COOKIE_FILE = Path(__file__).parent / "cookies.txt"

KEYWORD = "tai nghe"


def load_cookies():
    """Doc cookies tu file cookies.txt."""
    if not COOKIE_FILE.exists():
        print(f"ERROR: File {COOKIE_FILE} khong ton tai!")
        print(f"Hay tao file va paste cookies tu browser vao.")
        return None

    cookie_str = COOKIE_FILE.read_text().strip()
    if not cookie_str:
        print("ERROR: File cookies.txt rong!")
        return None

    print(f"Loaded cookies: {len(cookie_str)} chars")
    return cookie_str


def test_search_with_cookies(cookie_str):
    """Goi Search API voi cookies tu browser."""
    session = curl_requests.Session(impersonate="chrome")

    session.headers.update({
        "Accept": "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://shopee.vn/search?keyword=tai+nghe",
        "X-Requested-With": "XMLHttpRequest",
        "X-API-SOURCE": "pc",
        "X-Shopee-Language": "vi",
        "Cookie": cookie_str,
    })

    print(f"\n[1] Calling Search API: keyword='{KEYWORD}'...")
    resp = session.get(
        "https://shopee.vn/api/v4/search/search_items",
        params={
            "keyword": KEYWORD,
            "limit": 60,
            "newest": 0,
            "by": "relevancy",
            "order": "desc",
            "page_type": "search",
            "scenario": "PAGE_GLOBAL_SEARCH",
            "version": 2,
        },
        timeout=15,
    )

    print(f"  Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"  FAILED! Response: {resp.text[:500]}")
        return None

    data = resp.json()
    items = data.get("items", [])
    total = data.get("total_count", "N/A")
    print(f"  Total count: {total}")
    print(f"  Items in page: {len(items)}")

    if not items:
        print(f"  No items! Keys: {list(data.keys())}")
        print(f"  Response (first 1000): {json.dumps(data, ensure_ascii=False)[:1000]}")
        return data

    # In 5 san pham dau
    print(f"\n  --- First 5 products ---")
    for i, item in enumerate(items[:5]):
        product = item.get("item_basic", item)
        name = product.get("name", "N/A")
        price_raw = product.get("price", 0)
        price_min = product.get("price_min", 0)
        price_max = product.get("price_max", 0)

        # Normalize price (Shopee nhan 100,000)
        price = price_raw / 100_000 if price_raw > 100_000 else price_raw
        p_min = price_min / 100_000 if price_min > 100_000 else price_min
        p_max = price_max / 100_000 if price_max > 100_000 else price_max

        shop_id = product.get("shopid", "N/A")
        item_id = product.get("itemid", "N/A")
        sold = product.get("historical_sold", product.get("sold", "N/A"))

        print(f"\n  [{i+1}] {name}")
        print(f"      Price: {price:,.0f} VND (min: {p_min:,.0f}, max: {p_max:,.0f})")
        print(f"      Shop: {shop_id}, Item: {item_id}, Sold: {sold}")

    return data


def test_product_detail(cookie_str, shop_id, item_id):
    """Thu goi Product Detail API."""
    session = curl_requests.Session(impersonate="chrome")
    session.headers.update({
        "Accept": "application/json",
        "Referer": f"https://shopee.vn/product/{shop_id}/{item_id}",
        "X-Requested-With": "XMLHttpRequest",
        "X-API-SOURCE": "pc",
        "X-Shopee-Language": "vi",
        "Cookie": cookie_str,
    })

    print(f"\n[2] Calling Product Detail API: shop={shop_id}, item={item_id}...")
    resp = session.get(
        "https://shopee.vn/api/v4/item/get",
        params={"itemid": item_id, "shopid": shop_id},
        timeout=15,
    )

    print(f"  Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"  FAILED! Response: {resp.text[:500]}")
        return None

    data = resp.json()
    item_data = data.get("data", data)

    # Extract key fields
    name = item_data.get("name", "N/A")
    description = item_data.get("description", "")
    brand = ""
    attributes = item_data.get("attributes", [])
    for attr in attributes:
        if attr.get("name") in ("Thuong hieu", "Thương hiệu", "Brand"):
            brand = attr.get("value", "")

    categories = item_data.get("categories", [])
    cat_str = " > ".join(c.get("display_name", "") for c in categories)

    print(f"\n  Product: {name}")
    print(f"  Brand: {brand}")
    print(f"  Category: {cat_str}")
    print(f"  Description (first 300 chars): {description[:300]}")
    print(f"  Attributes: {len(attributes)} items")
    for attr in attributes[:5]:
        print(f"    - {attr.get('name', '')}: {attr.get('value', '')}")

    return data


def save_json(data, filename):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  Saved: {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    print("=" * 60)
    print("Shopee API Test - With Browser Cookies")
    print("=" * 60)

    cookie_str = load_cookies()
    if not cookie_str:
        exit(1)

    # Test Search API
    search_data = test_search_with_cookies(cookie_str)
    if search_data:
        save_json(search_data, "search_with_cookies.json")

        # Test Product Detail API voi san pham dau tien
        items = search_data.get("items", [])
        if items:
            first = items[0].get("item_basic", items[0])
            shop_id = first.get("shopid")
            item_id = first.get("itemid")

            if shop_id and item_id:
                detail_data = test_product_detail(cookie_str, shop_id, item_id)
                if detail_data:
                    save_json(detail_data, "product_detail_sample.json")

    print(f"\n{'=' * 60}")
    if search_data and search_data.get("items"):
        print("SUCCESS! Cookies work. Search API + Product Detail API OK.")
        print("Next: write scraper with pagination + checkpoint.")
    else:
        print("FAILED. Cookies may be expired or invalid.")
        print("Try getting fresh cookies from browser.")
    print("=" * 60)
