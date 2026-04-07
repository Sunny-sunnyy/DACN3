"""
Step 1 - Chrome Profile: Dung Chrome profile that cua user.

Approach: Dung profile Chrome da co session (cookies, login state).
Browser se giong het Chrome binh thuong -> khong bi detect.

QUAN TRONG: Dong het cua so Chrome truoc khi chay script nay!
(Chrome khong cho 2 process dung cung 1 profile)
"""

import json
import time
import os
from pathlib import Path

import undetected_chromedriver as uc
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KEYWORD = "tai nghe"
SEARCH_URL = f"https://shopee.vn/search?keyword={KEYWORD.replace(' ', '+')}"

# Chrome profile path tren Windows (WSL2 co the truy cap)
# Thu nhieu path pho bien
CHROME_PROFILE_PATHS = [
    os.path.expanduser("~") + "/.config/google-chrome",                          # Linux
    "/mnt/c/Users/" + os.environ.get("USER", "") + "/AppData/Local/Google/Chrome/User Data",  # WSL2 -> Windows
]


def find_chrome_profile():
    """Tim Chrome profile path."""
    for path in CHROME_PROFILE_PATHS:
        if os.path.exists(path):
            print(f"  Found Chrome profile: {path}")
            return path
    return None


def create_driver_with_profile(profile_path):
    """Tao Chrome driver voi user profile."""
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1400,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")

    driver = uc.Chrome(options=options, version_main=145)
    return driver


def create_driver_fresh():
    """Tao Chrome driver moi, user login thu cong."""
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1400,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Luu profile vao folder local de reuse session
    local_profile = str(Path(__file__).parent / "chrome_profile")
    options.add_argument(f"--user-data-dir={local_profile}")

    driver = uc.Chrome(options=options, version_main=145)
    return driver


def scroll_page(driver, scroll_count=6, scroll_px=800, delay=2):
    """Scroll lazy-load."""
    print(f"  Scrolling {scroll_count} times...")
    for i in range(scroll_count):
        driver.execute_script(f"window.scrollBy(0, {scroll_px});")
        time.sleep(delay)
        print(f"    Scroll {i+1}/{scroll_count}")


def parse_products(html):
    """Parse san pham tu HTML search page."""
    soup = BeautifulSoup(html, "html.parser")
    products = []
    seen = set()

    # Tim tat ca links chua product URL pattern
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "-i." not in href:
            continue

        # Clean URL
        clean_url = href.split("?")[0]
        if clean_url.startswith("/"):
            clean_url = "https://shopee.vn" + clean_url

        if clean_url in seen:
            continue
        seen.add(clean_url)

        # Extract IDs
        shop_id, item_id = "", ""
        try:
            id_part = href.split("-i.")[-1].split("?")[0]
            parts = id_part.split(".")
            if len(parts) >= 2:
                shop_id, item_id = parts[0], parts[1]
        except Exception:
            pass

        # Name: lay text content
        name = a.get_text(separator=" ", strip=True)[:200]

        products.append({
            "name": name,
            "url": clean_url,
            "shop_id": shop_id,
            "item_id": item_id,
        })

    return products


def main():
    print("=" * 60)
    print("Shopee Test - Chrome Profile / Manual Login")
    print("=" * 60)

    # Thu dung Chrome profile co san
    profile_path = find_chrome_profile()

    if profile_path:
        print(f"\n  QUAN TRONG: Hay DONG het Chrome truoc khi tiep tuc!")
        print(f"  Profile: {profile_path}")
        input("  Nhan Enter khi da dong Chrome...")

        try:
            driver = create_driver_with_profile(profile_path)
        except Exception as e:
            print(f"  Loi dung profile: {e}")
            print(f"  Thu tao profile moi...")
            driver = create_driver_fresh()
    else:
        print("\n  Khong tim thay Chrome profile. Tao profile moi.")
        print("  Browser se mo, ban co the login Shopee neu can.")
        driver = create_driver_fresh()

    try:
        # 1. Mo search page
        print(f"\n[1] Opening: {SEARCH_URL}")
        driver.get(SEARCH_URL)
        time.sleep(5)

        current_url = driver.current_url
        print(f"  URL: {current_url[:100]}")

        # Neu bi redirect login, cho user login thu cong
        if "login" in current_url.lower():
            print("\n  Bi redirect sang login page.")
            print("  Hay login thu cong trong browser vua mo.")
            print("  Sau khi login xong va thay trang search, nhan Enter...")
            input("  >> Enter: ")
            time.sleep(3)
            current_url = driver.current_url
            print(f"  URL sau login: {current_url[:100]}")

            # Quay lai trang search neu can
            if "search" not in current_url:
                driver.get(SEARCH_URL)
                time.sleep(5)

        # 2. Screenshot
        ss = OUTPUT_DIR / "screenshot_profile.png"
        driver.save_screenshot(str(ss))
        print(f"  Screenshot: {ss}")

        # 3. Scroll
        print("\n[2] Scrolling...")
        scroll_page(driver, scroll_count=6, scroll_px=800, delay=2)

        # 4. Parse
        print("\n[3] Parsing...")
        html = driver.page_source
        products = parse_products(html)
        print(f"  Products found: {len(products)}")

        # Save HTML
        html_path = OUTPUT_DIR / "search_page_profile.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        if products:
            print(f"\n  --- First 10 products ---")
            for i, p in enumerate(products[:10]):
                print(f"  [{i+1}] {p['name'][:70] or '(no name)'}")
                print(f"      URL: {p['url'][:70]}")

            save_path = OUTPUT_DIR / "products_profile.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved: {save_path}")

            print(f"\n{'=' * 60}")
            print(f"SUCCESS! {len(products)} products!")
            print(f"Profile saved. Lan sau khong can login lai.")
            print(f"{'=' * 60}")
        else:
            print(f"\n  Check screenshot + HTML file de debug.")

    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    main()
