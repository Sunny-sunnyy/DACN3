"""
Step 1 - undetected-chromedriver: Bypass Shopee bot detection.
Selenium bi detect -> redirect login. undetected-chromedriver patch Chrome
de khong bi phat hien la bot.
"""

import json
import time
from pathlib import Path

import undetected_chromedriver as uc
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KEYWORD = "tai nghe"
SEARCH_URL = f"https://shopee.vn/search?keyword={KEYWORD.replace(' ', '+')}"


def create_driver():
    """Tao undetected Chrome driver."""
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1400,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # KHONG dung headless truoc — de thay browser
    # options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, version_main=145)
    return driver


def scroll_page(driver, scroll_count=6, scroll_px=800, delay=2):
    """Scroll de load lazy content."""
    print(f"  Scrolling {scroll_count} times...")
    for i in range(scroll_count):
        driver.execute_script(f"window.scrollBy(0, {scroll_px});")
        time.sleep(delay)
        print(f"    Scroll {i+1}/{scroll_count}")


def parse_products_from_html(html):
    """Parse san pham tu HTML."""
    soup = BeautifulSoup(html, "html.parser")
    products = []

    # Tim tat ca product links (Shopee URL pattern: -i.{shop_id}.{item_id})
    all_links = soup.find_all("a", href=True)
    product_links = []
    seen_urls = set()

    for a in all_links:
        href = a.get("href", "")
        if "-i." in href and href not in seen_urls:
            seen_urls.add(href)
            product_links.append(a)

    print(f"  Found {len(product_links)} unique product links")

    for a in product_links:
        href = a.get("href", "")
        full_url = href if href.startswith("http") else "https://shopee.vn" + href

        # Extract shop_id, item_id
        shop_id, item_id = "", ""
        try:
            parts = href.split("-i.")[-1].split("?")[0].split(".")
            if len(parts) >= 2:
                shop_id, item_id = parts[0], parts[1]
        except Exception:
            pass

        # Tim text content trong link (ten san pham)
        text_content = a.get_text(strip=True)

        # Tim gia trong parent element
        parent = a.parent
        price_text = ""
        if parent:
            for el in parent.find_all(["span", "div"]):
                t = el.get_text(strip=True)
                # Gia Shopee thuong co format: "123.000" hoac "d" prefix
                if t and any(c.isdigit() for c in t) and len(t) < 30:
                    if "." in t or "d" in t.lower() or "000" in t:
                        price_text = t
                        break

        if text_content or full_url:
            products.append({
                "name": text_content[:200] if text_content else "",
                "price_text": price_text,
                "url": full_url.split("?")[0],  # Remove query params
                "shop_id": shop_id,
                "item_id": item_id,
            })

    return products


def main():
    print("=" * 60)
    print("Shopee Test - undetected-chromedriver")
    print(f"URL: {SEARCH_URL}")
    print("=" * 60)

    print("\n[1] Creating undetected Chrome driver...")
    driver = create_driver()

    try:
        # 1. Mo trang
        print(f"\n[2] Opening: {SEARCH_URL}")
        driver.get(SEARCH_URL)
        time.sleep(5)

        # 2. Check URL
        current_url = driver.current_url
        print(f"  Current URL: {current_url[:100]}")

        if "login" in current_url.lower() or "verify" in current_url.lower():
            print("\n  WARNING: Bi redirect sang login!")
            ss = OUTPUT_DIR / "screenshot_uc_login.png"
            driver.save_screenshot(str(ss))
            print(f"  Screenshot: {ss}")
            print("  undetected-chromedriver van bi detect.")
            print("  Thu: mo browser KHONG headless, login thu cong 1 lan.")
            return

        # 3. Screenshot truoc scroll
        ss = OUTPUT_DIR / "screenshot_uc_before.png"
        driver.save_screenshot(str(ss))
        print(f"  Screenshot before scroll: {ss}")

        # 4. Scroll
        print("\n[3] Scrolling to load products...")
        scroll_page(driver, scroll_count=6, scroll_px=800, delay=2)

        # 5. Screenshot sau scroll
        ss = OUTPUT_DIR / "screenshot_uc_after.png"
        driver.save_screenshot(str(ss))
        print(f"  Screenshot after scroll: {ss}")

        # 6. Parse
        print("\n[4] Parsing products...")
        html = driver.page_source
        products = parse_products_from_html(html)

        # Save HTML for debug
        html_path = OUTPUT_DIR / "search_page.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  HTML saved: {html_path} ({len(html):,} chars)")

        print(f"\n  Total products: {len(products)}")

        if products:
            print(f"\n  --- First 10 products ---")
            for i, p in enumerate(products[:10]):
                name_display = p["name"][:70] if p["name"] else "(no name)"
                print(f"  [{i+1}] {name_display}")
                print(f"      Price: {p['price_text']} | Shop: {p['shop_id']} | Item: {p['item_id']}")

            save_path = OUTPUT_DIR / "selenium_uc_products.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved: {save_path}")

            print(f"\n{'=' * 60}")
            print(f"SUCCESS! {len(products)} products scraped!")
            print(f"{'=' * 60}")
        else:
            print(f"\n{'=' * 60}")
            print("No products. Check screenshots + search_page.html")
            print(f"{'=' * 60}")

    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    main()
