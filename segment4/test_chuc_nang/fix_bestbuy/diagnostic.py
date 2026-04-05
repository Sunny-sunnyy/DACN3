"""
Diagnostic script: Tim root cause tai sao BestBuy product pages fail tu WSL2.

Test 7 approaches theo thu tu:
1. Current network state (MTU, interface info)
2. curl command-line with HTTP/1.1
3. requests library (baseline - expected to fail)
4. httpx with HTTP/1.1 only
5. curl_cffi (impersonate Chrome TLS fingerprint)
6. Playwright Chromium with --disable-http2
7. Playwright Firefox

Chay: cd segment4 && uv run base/fix_bestbuy_tocdo_thang3/diagnostic.py
"""

import subprocess
import time
import asyncio

# URLs to test
HOMEPAGE = "https://www.bestbuy.com"
PRODUCT_URL = "https://www.bestbuy.com/product/asus-zenbook-a14-14-fhd-oled-laptop-copilot-pc-snapdragon-x-plus-16gb-ram-512gb-ssd-zabriskie-beige/JJGGLH86J4"


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_1_network_state():
    """Check current MTU, interface, DNS."""
    section("TEST 1: Network State")

    commands = [
        ("MTU", "ip link show eth0 | grep mtu"),
        ("DNS", "cat /etc/resolv.conf | grep nameserver"),
        ("Route", "ip route | head -3"),
        ("TCP MTU probing", "sysctl net.ipv4.tcp_mtu_probing"),
    ]

    for label, cmd in commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            print(f"  {label}: {result.stdout.strip()}")
        except Exception as e:
            print(f"  {label}: ERROR - {e}")


def test_2_curl_http1():
    """Test curl with forced HTTP/1.1."""
    section("TEST 2: curl --http1.1")

    for label, url in [("Homepage", HOMEPAGE), ("Product", PRODUCT_URL)]:
        print(f"\n  {label}: {url[:60]}...")
        try:
            result = subprocess.run(
                [
                    "curl", "-s", "-o", "/dev/null",
                    "-w", "HTTP_CODE:%{http_code} TIME:%{time_total}s SIZE:%{size_download}",
                    "--http1.1",
                    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "-H", "Accept-Language: en-US,en;q=0.9",
                    "-L",  # follow redirects
                    "--connect-timeout", "10",
                    "--max-time", "15",
                    url,
                ],
                capture_output=True, text=True, timeout=20,
            )
            print(f"    Result: {result.stdout}")
            if result.returncode != 0:
                print(f"    curl exit code: {result.returncode}")
                if result.stderr:
                    print(f"    stderr: {result.stderr[:200]}")
        except Exception as e:
            print(f"    ERROR: {e}")


def test_3_requests():
    """Test Python requests (baseline - expected to fail)."""
    section("TEST 3: Python requests (baseline)")

    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for label, url in [("Homepage", HOMEPAGE), ("Product", PRODUCT_URL)]:
        print(f"\n  {label}: {url[:60]}...")
        start = time.time()
        try:
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            elapsed = time.time() - start
            print(f"    Status: {resp.status_code} | Size: {len(resp.content)} bytes | Time: {elapsed:.1f}s")
            print(f"    Title snippet: {resp.text[resp.text.find('<title'):resp.text.find('</title>')+8][:100]}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"    FAILED ({elapsed:.1f}s): {type(e).__name__}: {e}")


def test_4_httpx_http1():
    """Test httpx with HTTP/1.1 only (no HTTP/2)."""
    section("TEST 4: httpx (HTTP/1.1 only)")

    try:
        import httpx
    except ImportError:
        print("  httpx not installed. Skipping.")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for label, url in [("Homepage", HOMEPAGE), ("Product", PRODUCT_URL)]:
        print(f"\n  {label}: {url[:60]}...")
        start = time.time()
        try:
            # http2=False is default, explicit for clarity
            with httpx.Client(http2=False, follow_redirects=True, timeout=15.0, headers=headers) as client:
                resp = client.get(url)
                elapsed = time.time() - start
                print(f"    Status: {resp.status_code} | Size: {len(resp.content)} bytes | Time: {elapsed:.1f}s")
                print(f"    HTTP version: {resp.http_version}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"    FAILED ({elapsed:.1f}s): {type(e).__name__}: {e}")


def test_5_curl_cffi():
    """Test curl_cffi with Chrome impersonation."""
    section("TEST 5: curl_cffi (impersonate Chrome)")

    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        print("  curl_cffi not installed. Skipping.")
        print("  Install with: uv add curl_cffi")
        return

    for label, url in [("Homepage", HOMEPAGE), ("Product", PRODUCT_URL)]:
        print(f"\n  {label}: {url[:60]}...")
        start = time.time()
        try:
            resp = curl_requests.get(url, impersonate="chrome", timeout=15, allow_redirects=True)
            elapsed = time.time() - start
            print(f"    Status: {resp.status_code} | Size: {len(resp.content)} bytes | Time: {elapsed:.1f}s")
            # Check if we got actual content or redirect/block page
            text = resp.text
            if "<title>" in text:
                title_start = text.find("<title>") + 7
                title_end = text.find("</title>")
                print(f"    Page title: {text[title_start:title_end][:100]}")
            # Check for sale indicators
            if "savings" in text.lower() or "save $" in text.lower() or "was $" in text.lower():
                print(f"    Sale indicators found!")
        except Exception as e:
            elapsed = time.time() - start
            print(f"    FAILED ({elapsed:.1f}s): {type(e).__name__}: {e}")


async def test_6_playwright_chromium():
    """Test Playwright Chromium with --disable-http2."""
    section("TEST 6: Playwright Chromium (--disable-http2)")

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-http2",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = await context.new_page()

        for label, url in [("Homepage", HOMEPAGE), ("Product", PRODUCT_URL)]:
            print(f"\n  {label}: {url[:60]}...")
            start = time.time()
            try:
                resp = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                elapsed = time.time() - start
                status = resp.status if resp else "None"
                title = await page.title()
                print(f"    Status: {status} | Time: {elapsed:.1f}s | Title: {title[:80]}")
            except Exception as e:
                elapsed = time.time() - start
                print(f"    FAILED ({elapsed:.1f}s): {type(e).__name__}: {e}")

        await browser.close()


async def test_7_playwright_firefox():
    """Test Playwright Firefox."""
    section("TEST 7: Playwright Firefox")

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = await context.new_page()

        for label, url in [("Homepage", HOMEPAGE), ("Product", PRODUCT_URL)]:
            print(f"\n  {label}: {url[:60]}...")
            start = time.time()
            try:
                resp = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                elapsed = time.time() - start
                status = resp.status if resp else "None"
                title = await page.title()
                print(f"    Status: {status} | Time: {elapsed:.1f}s | Title: {title[:80]}")
            except Exception as e:
                elapsed = time.time() - start
                print(f"    FAILED ({elapsed:.1f}s): {type(e).__name__}: {e}")

        await browser.close()


async def main():
    print("BestBuy WSL2 Network Diagnostic")
    print(f"Product URL: {PRODUCT_URL[:60]}...")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    test_1_network_state()
    test_2_curl_http1()
    test_3_requests()
    test_4_httpx_http1()
    test_5_curl_cffi()
    await test_6_playwright_chromium()
    await test_7_playwright_firefox()

    section("DONE - Review results above")


if __name__ == "__main__":
    asyncio.run(main())
