"""
Step 1 - Selenium: Scrape Shopee search results bang browser that.

Approach: Selenium mo trang search (KHONG can login) -> scroll lazy-load -> parse HTML.
Shopee hien san pham binh thuong khi chua login.
"""

import json
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

OUTPUT_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KEYWORD = "tai nghe"
SEARCH_URL = f"https://shopee.vn/search?keyword={KEYWORD.replace(' ', '+')}"


def create_driver():
    """Tao Chrome driver."""
    options = Options()
    # KHONG dung headless truoc — de debug, thay browser lam gi
    # options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Tat webdriver detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)

    # Override navigator.webdriver = false
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    return driver


def scroll_page(driver, scroll_count=6, scroll_px=800, delay=2):
    """Scroll trang de load lazy content (Shopee dung lazy loading)."""
    print(f"  Scrolling {scroll_count} times ({scroll_px}px each, {delay}s delay)...")
    for i in range(scroll_count):
        driver.execute_script(f"window.scrollBy(0, {scroll_px});")
        time.sleep(delay)
        print(f"    Scroll {i+1}/{scroll_count} done")


def parse_products(html):
    """Parse HTML search results bang BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    products = []

    # Tim tat ca product cards — Shopee dung nhieu class names khac nhau
    # Thu nhieu selectors de tim dung
    selectors = [
        "li.shopee-search-item-result__item",
        "div.shopee-search-item-result__item",
        "div[data-sqe='item']",
        "a[data-sqe='link']",
    ]

    items = []
    for selector in selectors:
        items = soup.select(selector)
        if items:
            print(f"  Found {len(items)} items with selector: '{selector}'")
            break

    if not items:
        # Fallback: tim tat ca links co chua "-i." (Shopee product URL pattern)
        links = soup.find_all("a", href=True)
        product_links = [a for a in links if "-i." in a.get("href", "")]
        print(f"  Fallback: found {len(product_links)} product links")

        if not product_links:
            # Debug: luu HTML de xem structure
            debug_path = OUTPUT_DIR / "debug_page.html"
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Saved HTML for debug: {debug_path}")
            return products

        items = product_links

    for item in items:
        try:
            # Tim link san pham
            link_el = item if item.name == "a" else item.find("a", href=True)
            href = link_el.get("href", "") if link_el else ""

            # Build full URL
            if href and not href.startswith("http"):
                href = "https://shopee.vn" + href

            # Extract item_id va shop_id tu URL pattern: -i.{shop_id}.{item_id}
            shop_id, item_id = "", ""
            if "-i." in href:
                parts = href.split("-i.")[-1].split("?")[0].split(".")
                if len(parts) >= 2:
                    shop_id, item_id = parts[0], parts[1]

            # Tim ten san pham (thuong trong div hoac span)
            name = ""
            # Thu nhieu cach
            name_el = item.find("div", class_=lambda c: c and "ie3A" in str(c))
            if not name_el:
                name_el = item.find("div", {"data-sqe": "name"})
            if not name_el:
                # Tim text dai nhat trong item (thuong la ten san pham)
                texts = [t.get_text(strip=True) for t in item.find_all(["div", "span"]) if t.get_text(strip=True)]
                if texts:
                    name = max(texts, key=len)
            if name_el:
                name = name_el.get_text(strip=True)

            # Tim gia
            price_text = ""
            price_el = item.find("span", class_=lambda c: c and "price" in str(c).lower()) if item else None
            if not price_el:
                # Tim span co noi dung giong gia (co dau cham, so)
                for span in item.find_all("span"):
                    text = span.get_text(strip=True)
                    if any(c.isdigit() for c in text) and ("." in text or "d" in text.lower()):
                        price_text = text
                        break
            if price_el:
                price_text = price_el.get_text(strip=True)

            if name or href:
                products.append({
                    "name": name,
                    "price_text": price_text,
                    "url": href,
                    "shop_id": shop_id,
                    "item_id": item_id,
                })
        except Exception as e:
            continue

    return products


def main():
    print("=" * 60)
    print("Shopee Selenium Test")
    print(f"URL: {SEARCH_URL}")
    print("=" * 60)

    driver = create_driver()

    try:
        # 1. Mo trang search
        print(f"\n[1] Opening search page...")
        driver.get(SEARCH_URL)

        # 2. Doi trang load
        print("[2] Waiting for page to load...")
        time.sleep(5)

        # 3. Check co bi redirect sang login khong
        current_url = driver.current_url
        print(f"  Current URL: {current_url}")
        if "login" in current_url.lower() or "verify" in current_url.lower():
            print("  WARNING: Redirected to login/verify page!")
            print("  Thu lai voi non-headless mode de login thu cong.")
            # Screenshot
            ss_path = OUTPUT_DIR / "screenshot_login.png"
            driver.save_screenshot(str(ss_path))
            print(f"  Screenshot saved: {ss_path}")
            return

        # 4. Screenshot truoc khi scroll
        ss_path = OUTPUT_DIR / "screenshot_before_scroll.png"
        driver.save_screenshot(str(ss_path))
        print(f"  Screenshot saved: {ss_path}")

        # 5. Scroll de load lazy content
        print("\n[3] Scrolling to load products...")
        scroll_page(driver, scroll_count=6, scroll_px=800, delay=2)

        # 6. Screenshot sau khi scroll
        ss_path = OUTPUT_DIR / "screenshot_after_scroll.png"
        driver.save_screenshot(str(ss_path))
        print(f"  Screenshot saved: {ss_path}")

        # 7. Lay HTML va parse
        print("\n[4] Parsing HTML...")
        html = driver.page_source
        products = parse_products(html)

        print(f"\n  Total products parsed: {len(products)}")

        if products:
            # In 5 san pham dau
            print(f"\n  --- First 5 products ---")
            for i, p in enumerate(products[:5]):
                print(f"  [{i+1}] {p['name'][:80]}")
                print(f"      Price: {p['price_text']}")
                print(f"      URL: {p['url'][:80]}")
                print(f"      Shop: {p['shop_id']}, Item: {p['item_id']}")

            # Save
            save_path = OUTPUT_DIR / "selenium_products.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved {len(products)} products to {save_path}")

            print(f"\n{'=' * 60}")
            print(f"SUCCESS! Got {len(products)} products via Selenium.")
            print(f"{'=' * 60}")
        else:
            print(f"\n{'=' * 60}")
            print("No products found. Check screenshots and debug_page.html")
            print(f"{'=' * 60}")

    finally:
        driver.quit()
        print("\nBrowser closed.")


if __name__ == "__main__":
    main()
