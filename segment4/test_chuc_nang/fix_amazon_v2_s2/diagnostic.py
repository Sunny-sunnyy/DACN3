"""
Diagnostic: Test curl_cffi access to Amazon from WSL2.

Tests:
1. Homepage access (get cookies)
2. Search page (parse product cards)
3. Product page (get features)
4. CAPTCHA detection
5. ZIP code 96150 setting via API

Chay: cd segment4 && uv run test_chuc_nang/fix_amazon_v2_s2/diagnostic.py
"""

import time
import json
import logging
from curl_cffi import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

HOMEPAGE = "https://www.amazon.com"
SEARCH_URL = "https://www.amazon.com/s?k=laptop+gaming"
PRODUCT_URL = "https://www.amazon.com/dp/B0DZZWMB2L"
ZIP_CODE = "96150"


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_captcha(html: str) -> bool:
    """Check if response contains CAPTCHA."""
    captcha_signs = [
        "/errors/validateCaptcha",
        "Type the characters you see in this image",
        "api-services-support@amazon.com",
        "Sorry, we just need to make sure you're not a robot",
    ]
    for sign in captcha_signs:
        if sign in html:
            return True
    return False


def test_1_homepage(session):
    """Test basic access to Amazon homepage."""
    section("TEST 1: Homepage")
    start = time.time()
    resp = session.get(HOMEPAGE, timeout=15)
    elapsed = time.time() - start

    html = resp.text
    has_captcha = check_captcha(html)
    has_title = "<title>" in html.lower()

    print(f"  Status: {resp.status_code}")
    print(f"  Size: {len(html):,} bytes")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Has <title>: {has_title}")
    print(f"  CAPTCHA: {has_captcha}")
    print(f"  Cookies: {len(session.cookies)} cookies set")

    if has_captcha:
        print("  [FAIL] Amazon returned CAPTCHA")
    elif resp.status_code == 200 and has_title:
        print("  [OK] Homepage accessible")
    else:
        print(f"  [FAIL] Unexpected response")


def test_2_search_page(session):
    """Test search page access and product card parsing."""
    section("TEST 2: Search page")
    start = time.time()
    resp = session.get(SEARCH_URL, timeout=15)
    elapsed = time.time() - start

    html = resp.text
    has_captcha = check_captcha(html)

    # Count product cards
    count_results = html.count('data-component-type="s-search-result"')
    count_asin = html.count('data-asin="')
    count_price = html.count('a-price-whole')

    print(f"  Status: {resp.status_code}")
    print(f"  Size: {len(html):,} bytes")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  CAPTCHA: {has_captcha}")
    print(f"  Search results: {count_results}")
    print(f"  ASINs found: {count_asin}")
    print(f"  Prices found: {count_price}")

    if has_captcha:
        print("  [FAIL] CAPTCHA on search page")
    elif count_results >= 10:
        print(f"  [OK] Search page works - {count_results} products found")
    elif count_results > 0:
        print(f"  [WARN] Only {count_results} products, may need pagination")
    else:
        print("  [FAIL] No products found in search results")


def test_3_product_page(session):
    """Test product page access."""
    section("TEST 3: Product page")
    start = time.time()
    resp = session.get(PRODUCT_URL, timeout=15)
    elapsed = time.time() - start

    html = resp.text
    has_captcha = check_captcha(html)
    has_title = "productTitle" in html
    has_features = "feature-bullets" in html
    has_price = "a-price" in html

    print(f"  Status: {resp.status_code}")
    print(f"  Size: {len(html):,} bytes")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  CAPTCHA: {has_captcha}")
    print(f"  Has #productTitle: {has_title}")
    print(f"  Has #feature-bullets: {has_features}")
    print(f"  Has price: {has_price}")

    if has_captcha:
        print("  [FAIL] CAPTCHA on product page")
    elif has_title and has_price:
        print("  [OK] Product page accessible")
    else:
        print("  [WARN] Product page partially loaded or blocked")


def test_4_set_zip_code(session):
    """Test setting ZIP code via Amazon's delivery location API."""
    section("TEST 4: Set ZIP code 96150")

    # Amazon uses this endpoint to change delivery location
    url = "https://www.amazon.com/gp/delivery/ajax/address-change.html"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.amazon.com/",
        "Anti-Csrftoken-A2z": "",  # May need actual token
    }
    data = {
        "locationType": "LOCATION_INPUT",
        "zipCode": ZIP_CODE,
        "storeContext": "generic",
        "deviceType": "web",
        "pageType": "Search",
        "actionSource": "glow",
    }

    start = time.time()
    resp = session.post(url, data=data, headers=headers, timeout=15)
    elapsed = time.time() - start

    print(f"  Status: {resp.status_code}")
    print(f"  Size: {len(resp.text):,} bytes")
    print(f"  Time: {elapsed:.1f}s")

    try:
        result = resp.json()
        print(f"  Response JSON keys: {list(result.keys())}")
        is_valid = result.get("isValidAddress")
        print(f"  isValidAddress: {is_valid}")
        if is_valid:
            print("  [OK] ZIP code set successfully")
        else:
            print(f"  [WARN] ZIP response: {json.dumps(result, indent=2)[:300]}")
    except Exception:
        # Check if HTML response
        if "validateCaptcha" in resp.text:
            print("  [FAIL] CAPTCHA on ZIP code API")
        else:
            print(f"  [WARN] Non-JSON response: {resp.text[:200]}")


def test_5_search_after_zip(session):
    """Test search page AFTER setting ZIP code - prices should reflect US location."""
    section("TEST 5: Search page AFTER ZIP code set")
    start = time.time()
    resp = session.get(SEARCH_URL, timeout=15)
    elapsed = time.time() - start

    html = resp.text
    has_captcha = check_captcha(html)
    count_results = html.count('data-component-type="s-search-result"')

    # Check delivery location indicator
    has_delivery = "Deliver to" in html or ZIP_CODE in html

    print(f"  Status: {resp.status_code}")
    print(f"  Size: {len(html):,} bytes")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  CAPTCHA: {has_captcha}")
    print(f"  Products: {count_results}")
    print(f"  ZIP {ZIP_CODE} in page: {has_delivery}")

    if has_captcha:
        print("  [FAIL] CAPTCHA")
    elif count_results >= 10 and has_delivery:
        print("  [OK] Search with US location works")
    elif count_results >= 10:
        print("  [OK] Search works, but ZIP may not be reflected")
    else:
        print(f"  [WARN] Only {count_results} products")


def test_6_impersonate_variants(session_class):
    """Test different impersonate variants if default fails."""
    section("TEST 6: Impersonate variants")

    variants = ["chrome", "chrome120", "chrome131", "safari", "safari_ios"]
    for variant in variants:
        try:
            s = session_class(impersonate=variant)
            start = time.time()
            resp = s.get(SEARCH_URL, timeout=10)
            elapsed = time.time() - start
            has_captcha = check_captcha(resp.text)
            count = resp.text.count('data-component-type="s-search-result"')
            status = "CAPTCHA" if has_captcha else f"{count} products"
            print(f"  {variant:15s} -> {resp.status_code} | {elapsed:.1f}s | {status}")
        except Exception as e:
            print(f"  {variant:15s} -> ERROR: {e}")


def main():
    print("Amazon curl_cffi Diagnostic")
    print("=" * 60)

    # Create session with Chrome impersonation (same pattern as BestBuy)
    session = curl_requests.Session(impersonate="chrome")

    test_1_homepage(session)
    test_2_search_page(session)
    test_3_product_page(session)
    test_4_set_zip_code(session)
    test_5_search_after_zip(session)
    test_6_impersonate_variants(curl_requests.Session)

    print("\n" + "=" * 60)
    print("  DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
