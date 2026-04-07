"""
Step 1: Thu nghiem Tiki API v2
Muc tieu: Goi thu 2 endpoints, xem response format va data quality.

Test 1: Listing API — lay danh sach san pham theo category
Test 2: Detail API — lay thong tin chi tiet 1 san pham
Test 3: Pagination — thu lay 2-3 pages lien tiep
"""

import json
from pathlib import Path
from curl_cffi import requests as curl_requests

DATA_DIR = Path(__file__).parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://tiki.vn",
}

# Category ID 8594: Thiet bi so / Phu kien cong nghe (tuong doi nhieu san pham)
# Category ID 1789: Dien thoai - May tinh bang
# Category ID 1846: Laptop - Thiet bi IT
# Category ID 4221: Dien tu - Dien lanh
TEST_CATEGORY_ID = 8594
TEST_CATEGORY_NAME = "phu_kien_so"


def test_listing_api():
    """Test 1: Listing API — lay danh sach san pham theo category."""
    print("=" * 60)
    print("TEST 1: Listing API")
    print("=" * 60)

    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(BASE_HEADERS)

    url = "https://tiki.vn/api/v2/products"
    params = {
        "category": TEST_CATEGORY_ID,
        "limit": 10,  # chi lay 10 san pham de test
        "page": 1,
        "include": "advertisement",
        "aggregations": 1,
    }

    print(f"GET {url}")
    print(f"Params: {params}")
    resp = session.get(url, params=params, timeout=15)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"FAILED! Response: {resp.text[:500]}")
        return None

    data = resp.json()

    # Save full response
    out_file = DATA_DIR / "test_listing_response.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved full response to {out_file}")

    # Phan tich response
    print(f"\nTop-level keys: {list(data.keys())}")

    items = data.get("data", [])
    print(f"So san pham trong response: {len(items)}")

    if items:
        first = items[0]
        print(f"\nFields cua san pham dau tien:")
        for key in sorted(first.keys()):
            val = first[key]
            if isinstance(val, str) and len(val) > 100:
                val = val[:100] + "..."
            print(f"  {key}: {val}")

        # Check cac fields quan trong
        print(f"\n--- Fields quan trong ---")
        print(f"  id:    {first.get('id')}")
        print(f"  name:  {first.get('name', '')[:80]}")
        print(f"  price: {first.get('price')}")
        print(f"  brand: {first.get('brand_name', 'N/A')}")
        print(f"  url:   https://tiki.vn/{first.get('url_path', 'N/A')}")

    paging = data.get("paging", {})
    print(f"\nPaging info: {paging}")

    session.close()
    return data


def test_detail_api(product_id: int):
    """Test 2: Detail API — lay thong tin chi tiet 1 san pham."""
    print("\n" + "=" * 60)
    print(f"TEST 2: Detail API (product_id={product_id})")
    print("=" * 60)

    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(BASE_HEADERS)

    url = f"https://tiki.vn/api/v2/products/{product_id}"
    print(f"GET {url}")
    resp = session.get(url, timeout=15)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"FAILED! Response: {resp.text[:500]}")
        return None

    data = resp.json()

    # Save full response
    out_file = DATA_DIR / f"test_detail_{product_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved full response to {out_file}")

    # Phan tich response
    print(f"\nTop-level keys: {sorted(data.keys())}")

    print(f"\n--- Fields quan trong ---")
    print(f"  id:          {data.get('id')}")
    print(f"  name:        {data.get('name', '')[:80]}")
    print(f"  price:       {data.get('price')}")
    print(f"  brand:       {data.get('brand', {}).get('name', 'N/A')}")
    print(f"  url_path:    {data.get('url_path', 'N/A')[:80]}")
    print(f"  short_desc:  {data.get('short_description', '')[:100]}")

    # Description
    desc = data.get("description", "")
    print(f"  description: {len(desc)} chars")
    if desc:
        print(f"    preview:   {desc[:150]}...")

    # Specifications / features
    specs = data.get("specifications", [])
    print(f"  specifications: {len(specs)} groups")
    for group in specs[:2]:  # chi in 2 groups dau
        group_name = group.get("name", "")
        attrs = group.get("attributes", [])
        print(f"    [{group_name}]: {len(attrs)} attributes")
        for attr in attrs[:3]:
            print(f"      - {attr.get('code')}: {attr.get('value', '')[:60]}")

    # Breadcrumbs (categories)
    breadcrumbs = data.get("breadcrumbs", [])
    if breadcrumbs:
        cats = " > ".join(b.get("name", "") for b in breadcrumbs)
        print(f"  categories:  {cats}")

    session.close()
    return data


def test_pagination():
    """Test 3: Pagination — lay 3 pages lien tiep, dem tong san pham."""
    print("\n" + "=" * 60)
    print("TEST 3: Pagination (3 pages)")
    print("=" * 60)

    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(BASE_HEADERS)

    total_products = 0
    for page in range(1, 4):
        url = "https://tiki.vn/api/v2/products"
        params = {
            "category": TEST_CATEGORY_ID,
            "limit": 40,
            "page": page,
            "include": "advertisement",
            "aggregations": 1,
        }
        resp = session.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"  Page {page}: FAILED (status {resp.status_code})")
            break

        data = resp.json()
        items = data.get("data", [])
        paging = data.get("paging", {})
        total_products += len(items)

        print(f"  Page {page}: {len(items)} san pham (total in paging: {paging.get('total', '?')})")

        if not items:
            print("  -> Het san pham, dung lai.")
            break

    print(f"\nTong: {total_products} san pham tu {page} pages")
    session.close()


if __name__ == "__main__":
    # Test 1: Listing
    listing_data = test_listing_api()

    # Test 2: Detail — lay product_id tu listing
    if listing_data and listing_data.get("data"):
        first_product_id = listing_data["data"][0]["id"]
        test_detail_api(first_product_id)
    else:
        # Fallback: thu voi 1 product ID co dinh
        print("\nKhong lay duoc listing, thu detail voi product_id co dinh...")
        test_detail_api(203396268)

    # Test 3: Pagination
    test_pagination()

    print("\n" + "=" * 60)
    print("DONE! Kiem tra folder data/raw/ de xem raw JSON responses.")
    print("=" * 60)
