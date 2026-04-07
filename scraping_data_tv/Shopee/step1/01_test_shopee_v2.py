"""
Step 1 - V2: Test Shopee API voi nhieu ky thuat bypass khac nhau.
V1 bi 403 vi thieu cookies. Thu cac approach:
  A) Them nhieu headers hon (User-Agent, Accept, etc)
  B) Goi qua URL search page truoc (khong phai API)
  C) Thu API endpoint khac
"""

import json
from pathlib import Path

from curl_cffi import requests as curl_requests

OUTPUT_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KEYWORD = "tai nghe"


def approach_a_full_headers():
    """Approach A: Full browser headers, visit homepage first."""
    print("\n" + "=" * 60)
    print("APPROACH A: Full browser headers")
    print("=" * 60)

    session = curl_requests.Session(impersonate="chrome")

    # Full browser-like headers
    session.headers.update({
        "Accept": "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://shopee.vn/search?keyword=tai+nghe",
        "X-Requested-With": "XMLHttpRequest",
        "X-API-SOURCE": "pc",
        "X-Shopee-Language": "vi",
        "X-CSRFToken": "",
    })

    # 1. Visit homepage
    print("[1] GET homepage...")
    resp = session.get("https://shopee.vn/", timeout=15)
    print(f"  Status: {resp.status_code}, Cookies: {len(session.cookies)}")
    for c in session.cookies:
        print(f"  Cookie: {c.name}={c.value[:30]}...")

    # 2. Visit search page (HTML) to trigger more cookies
    print("[2] GET search page HTML...")
    resp = session.get(
        f"https://shopee.vn/search?keyword={KEYWORD}",
        timeout=15,
    )
    print(f"  Status: {resp.status_code}, Cookies: {len(session.cookies)}")

    # 3. Call search API
    print("[3] GET search API...")
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
    print(f"  Response (first 500): {resp.text[:500]}")

    if resp.status_code == 200:
        try:
            data = resp.json()
            items = data.get("items", [])
            print(f"  Items count: {len(items)}")
            if items:
                save_json(data, "approach_a_response.json")
                return data
        except json.JSONDecodeError:
            pass

    return None


def approach_b_direct_search_api():
    """Approach B: Thu cac API endpoint khac cua Shopee."""
    print("\n" + "=" * 60)
    print("APPROACH B: Alternative API endpoints")
    print("=" * 60)

    session = curl_requests.Session(impersonate="chrome")

    # Shopee co the co cac API versions khac
    endpoints = [
        "https://shopee.vn/api/v4/search/search_items",
        "https://shopee.vn/api/v2/search_items/",
        "https://shopee.vn/api/v4/recommend/recommend",
    ]

    # Visit homepage first
    print("[1] GET homepage...")
    session.get("https://shopee.vn/", timeout=15)

    for i, url in enumerate(endpoints):
        print(f"\n[{i+2}] Testing: {url}")
        try:
            resp = session.get(
                url,
                params={"keyword": KEYWORD, "limit": 10, "newest": 0},
                timeout=15,
            )
            print(f"  Status: {resp.status_code}")
            print(f"  Response (first 300): {resp.text[:300]}")
        except Exception as e:
            print(f"  Error: {e}")

    return None


def approach_c_mobile_api():
    """Approach C: Thu Shopee mobile API (thuong it strict hon)."""
    print("\n" + "=" * 60)
    print("APPROACH C: Mobile API attempt")
    print("=" * 60)

    session = curl_requests.Session(impersonate="chrome")

    # Mobile-like headers
    session.headers.update({
        "User-Agent": "ShopeeVN/3.0 (Android; Mobile)",
        "Accept": "application/json",
        "X-API-SOURCE": "rn",
        "X-Shopee-Language": "vi",
    })

    print("[1] Trying mobile search endpoint...")
    try:
        resp = session.get(
            "https://shopee.vn/api/v4/search/search_items",
            params={
                "keyword": KEYWORD,
                "limit": 30,
                "newest": 0,
                "by": "relevancy",
                "order": "desc",
            },
            timeout=15,
        )
        print(f"  Status: {resp.status_code}")
        print(f"  Response (first 500): {resp.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    return None


def approach_d_cookie_from_browser():
    """Approach D: Huong dan lay cookie tu browser that."""
    print("\n" + "=" * 60)
    print("APPROACH D: Manual cookie extraction guide")
    print("=" * 60)
    print("""
Neu tat ca approach tu dong deu that bai, ban co the:

1. Mo Chrome, truy cap shopee.vn/search?keyword=tai+nghe
2. F12 -> Network tab -> Filter "search_items"
3. Click vao request -> Copy "Cookie" header
4. Paste vao file: step1/cookies.txt
5. Script se doc cookies tu file do va dung cho cac request

Hoac:
1. F12 -> Console -> document.cookie
2. Copy ket qua va paste vao cookies.txt
""")


def save_json(data, filename):
    output_path = OUTPUT_DIR / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {output_path} ({output_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    print("=" * 60)
    print("Shopee API Test - V2 (Multiple Approaches)")
    print("=" * 60)

    # Thu tung approach
    result = approach_a_full_headers()

    if not result:
        result = approach_b_direct_search_api()

    if not result:
        approach_c_mobile_api()

    if not result:
        approach_d_cookie_from_browser()

    print("\n" + "=" * 60)
    if result:
        print("SUCCESS! Raw data saved.")
    else:
        print("All automated approaches failed.")
        print("Recommendation: Extract cookies from browser (Approach D)")
        print("or switch to Selenium approach.")
    print("=" * 60)
