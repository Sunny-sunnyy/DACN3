"""
Step 1 - V4: Test Shopee API bang cach copy TOAN BO headers tu browser.

HUONG DAN:
1. Mo Chrome, vao shopee.vn/search?keyword=tai+nghe (da login + xac thuc CAPTCHA)
2. F12 -> Network -> filter "search_items" -> Reload
3. Right-click vao request search_items -> Copy -> Copy as cURL (bash)
4. Paste vao file: step1/curl_command.txt
5. Chay script nay
"""

import json
import re
import shlex
from pathlib import Path

from curl_cffi import requests as curl_requests

OUTPUT_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CURL_FILE = Path(__file__).parent / "curl_command.txt"


def parse_curl_command(curl_str):
    """Parse curl command thanh URL + headers dict."""
    # Extract URL
    url_match = re.search(r"curl\s+'([^']+)'", curl_str)
    if not url_match:
        url_match = re.search(r'curl\s+"([^"]+)"', curl_str)
    if not url_match:
        print("ERROR: Khong tim thay URL trong curl command!")
        return None, {}

    url = url_match.group(1)

    # Extract headers
    headers = {}
    header_matches = re.findall(r"-H\s+'([^']+)'", curl_str)
    if not header_matches:
        header_matches = re.findall(r'-H\s+"([^"]+)"', curl_str)

    for h in header_matches:
        if ": " in h:
            key, value = h.split(": ", 1)
            headers[key] = value

    return url, headers


def test_with_full_headers():
    """Goi API voi toan bo headers tu browser."""
    if not CURL_FILE.exists():
        print(f"ERROR: File {CURL_FILE} khong ton tai!")
        print("Hay copy curl command tu browser va paste vao file nay.")
        return None

    curl_str = CURL_FILE.read_text().strip()
    if not curl_str:
        print("ERROR: File curl_command.txt rong!")
        return None

    print(f"Loaded curl command: {len(curl_str)} chars")

    url, headers = parse_curl_command(curl_str)
    if not url:
        return None

    print(f"\nURL: {url[:100]}...")
    print(f"Headers count: {len(headers)}")
    print("Headers found:")
    for k, v in headers.items():
        display_val = v[:60] + "..." if len(v) > 60 else v
        print(f"  {k}: {display_val}")

    # Goi API voi curl_cffi
    print(f"\n[1] Calling API with full browser headers...")
    session = curl_requests.Session(impersonate="chrome")

    resp = session.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"  FAILED! Response: {resp.text[:500]}")
        return None

    data = resp.json()

    # Debug: in toan bo structure de hieu response
    print(f"\n  --- DEBUG: Response structure ---")
    print(f"  Top-level keys: {list(data.keys())}")
    for key in data.keys():
        val = data[key]
        if isinstance(val, list):
            print(f"  '{key}': list[{len(val)}]")
            if val:
                first = val[0]
                if isinstance(first, dict):
                    print(f"    First item keys: {list(first.keys())}")
        elif isinstance(val, dict):
            print(f"  '{key}': dict keys={list(val.keys())[:10]}")
        else:
            print(f"  '{key}': {type(val).__name__} = {str(val)[:100]}")

    # Save full response for manual inspection
    debug_path = OUTPUT_DIR / "debug_full_response.json"
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  Full response saved to: {debug_path}")

    # Try different keys to find items
    items = (
        data.get("items")
        or data.get("item")
        or data.get("data", {}).get("items") if isinstance(data.get("data"), dict) else None
        or []
    )
    total = data.get("total_count", data.get("nomore", "N/A"))
    print(f"\n  Total/nomore: {total}")
    print(f"  Items found: {len(items)}")

    if items:
        print(f"\n  --- First 5 products ---")
        for i, item in enumerate(items[:5]):
            product = item.get("item_basic", item)
            name = product.get("name", "N/A")
            price_raw = product.get("price", 0)
            price = price_raw / 100_000 if price_raw > 100_000 else price_raw
            shop_id = product.get("shopid", "N/A")
            item_id = product.get("itemid", "N/A")
            sold = product.get("historical_sold", product.get("sold", "N/A"))
            print(f"\n  [{i+1}] {name}")
            print(f"      Price: {price:,.0f} VND | Shop: {shop_id} | Item: {item_id} | Sold: {sold}")

    return data


def test_pagination(headers_from_curl):
    """Test pagination: goi page 2."""
    if not headers_from_curl:
        return

    curl_str = CURL_FILE.read_text().strip()
    url, headers = parse_curl_command(curl_str)

    # Doi offset sang page 2
    if "newest=0" in url:
        url_page2 = url.replace("newest=0", "newest=60")
    else:
        url_page2 = url + "&newest=60"

    print(f"\n[2] Testing pagination (page 2)...")
    session = curl_requests.Session(impersonate="chrome")
    resp = session.get(url_page2, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        items = data.get("items", [])
        print(f"  Items page 2: {len(items)}")
        if items:
            product = items[0].get("item_basic", items[0])
            print(f"  First item page 2: {product.get('name', 'N/A')}")
    else:
        print(f"  FAILED: {resp.text[:300]}")


def test_product_detail(search_data):
    """Test Product Detail API voi item dau tien."""
    items = search_data.get("items", [])
    if not items:
        return

    first = items[0].get("item_basic", items[0])
    shop_id = first.get("shopid")
    item_id = first.get("itemid")

    curl_str = CURL_FILE.read_text().strip()
    _, headers = parse_curl_command(curl_str)

    # Doi Referer
    headers["Referer"] = f"https://shopee.vn/product/{shop_id}/{item_id}"

    print(f"\n[3] Testing Product Detail API: shop={shop_id}, item={item_id}...")
    session = curl_requests.Session(impersonate="chrome")
    resp = session.get(
        "https://shopee.vn/api/v4/item/get",
        params={"itemid": item_id, "shopid": shop_id},
        headers=headers,
        timeout=15,
    )
    print(f"  Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        item_data = data.get("data", data)
        name = item_data.get("name", "N/A")
        desc = item_data.get("description", "")
        attrs = item_data.get("attributes", [])
        cats = item_data.get("categories", [])

        print(f"  Name: {name}")
        print(f"  Description: {desc[:200]}...")
        print(f"  Categories: {' > '.join(c.get('display_name', '') for c in cats)}")
        print(f"  Attributes ({len(attrs)}):")
        for a in attrs[:5]:
            print(f"    - {a.get('name', '')}: {a.get('value', '')}")

        save_json(data, "product_detail_sample.json")
    else:
        print(f"  FAILED: {resp.text[:300]}")


def save_json(data, filename):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    print("=" * 60)
    print("Shopee API Test - Full Headers from cURL")
    print("=" * 60)

    search_data = test_with_full_headers()

    if search_data and search_data.get("items"):
        save_json(search_data, "search_full_headers.json")
        test_pagination(search_data)
        test_product_detail(search_data)

        print(f"\n{'=' * 60}")
        print("SUCCESS! Full headers approach works.")
        print("Next step: build scraper with these headers.")
        print("Note: Headers/cookies se het han sau 1-2 gio.")
        print("Can co giai phap tu dong refresh (Selenium).")
        print("=" * 60)
    else:
        print(f"\n{'=' * 60}")
        print("FAILED. Even full headers don't work.")
        print("Shopee may require encrypted tokens from JS runtime.")
        print("Next: switch to Selenium approach.")
        print("=" * 60)
