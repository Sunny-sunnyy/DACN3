"""
Step 1 - Playwright + Stealth: Anti-detection tot hon Selenium.

Playwright co co che chong detect rieng, ket hop stealth plugin.
Dung persistent context de luu session (login 1 lan, dung lai nhieu lan).
"""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

OUTPUT_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR = str(Path(__file__).parent / "playwright_profile")

KEYWORD = "tai nghe"
SEARCH_URL = f"https://shopee.vn/search?keyword={KEYWORD.replace(' ', '+')}"


def scrape_shopee():
    with sync_playwright() as p:
        # Persistent context + Stealth anti-detect
        stealth = Stealth()
        context = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            viewport={"width": 1400, "height": 900},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        # Apply stealth to context
        stealth.apply_stealth_sync(context)

        page = context.pages[0] if context.pages else context.new_page()

        # 1. Mo search page
        print(f"\n[1] Opening: {SEARCH_URL}")
        page.goto(SEARCH_URL, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        current_url = page.url
        print(f"  URL: {current_url[:100]}")

        # Neu bi redirect login
        if "login" in current_url.lower():
            print("\n  Bi redirect sang login!")
            print("  Browser da mo — hay LOGIN thu cong trong browser.")
            print("  Sau khi login xong va thay san pham, nhan Enter o day...")
            input("  >> Enter: ")

            # Sau khi login, quay lai search page
            current_url = page.url
            if "search" not in current_url:
                page.goto(SEARCH_URL, wait_until="networkidle", timeout=30000)
                time.sleep(3)

        # Screenshot
        ss = OUTPUT_DIR / "screenshot_pw.png"
        page.screenshot(path=str(ss))
        print(f"  Screenshot: {ss}")

        # 2. Scroll lazy-load
        print("\n[2] Scrolling to load products...")
        for i in range(8):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(1.5)
            print(f"    Scroll {i+1}/8")

        # Screenshot sau scroll
        ss2 = OUTPUT_DIR / "screenshot_pw_after.png"
        page.screenshot(path=str(ss2))
        print(f"  Screenshot after scroll: {ss2}")

        # 3. Parse HTML
        print("\n[3] Parsing products...")
        html = page.content()

        # Save HTML
        html_path = OUTPUT_DIR / "search_pw.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  HTML saved: {html_path} ({len(html):,} chars)")

        # Parse product links
        products = []
        seen = set()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "-i." not in href:
                continue

            clean_url = href.split("?")[0]
            if clean_url.startswith("/"):
                clean_url = "https://shopee.vn" + clean_url
            if clean_url in seen:
                continue
            seen.add(clean_url)

            # IDs
            shop_id, item_id = "", ""
            try:
                parts = href.split("-i.")[-1].split("?")[0].split(".")
                if len(parts) >= 2:
                    shop_id, item_id = parts[0], parts[1]
            except Exception:
                pass

            name = a.get_text(separator=" ", strip=True)[:200]

            products.append({
                "name": name,
                "url": clean_url,
                "shop_id": shop_id,
                "item_id": item_id,
            })

        print(f"  Products found: {len(products)}")

        if products:
            print(f"\n  --- First 10 products ---")
            for i, p in enumerate(products[:10]):
                print(f"  [{i+1}] {p['name'][:70] or '(no name)'}")
                print(f"      Shop: {p['shop_id']}, Item: {p['item_id']}")

            save_path = OUTPUT_DIR / "products_playwright.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved: {save_path}")

            print(f"\n{'=' * 60}")
            print(f"SUCCESS! {len(products)} products via Playwright!")
            print(f"Session saved. Lan sau KHONG can login lai.")
            print(f"{'=' * 60}")
        else:
            print(f"\n  No products. Check screenshots + HTML.")

        context.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Shopee Test - Playwright + Stealth")
    print("=" * 60)
    scrape_shopee()
