"""
Buoc 1: Tim BestBuy API endpoint hoat dong tu WSL.

Da biet: /api/3.0/priceBlocks tra ve 200 nhung SKU format sai.
Thu nhieu API endpoints de tim cach lay product data + pricing.

Chay: cd segment4 && uv run base/fix_bestbuy_tocdo_thang3/fix_buoc_1.py
"""

import json
import time
import asyncio
from playwright.async_api import async_playwright


TEST_URLS = [
    "https://www.bestbuy.com/product/asus-zenbook-a14-14-fhd-oled-laptop-copilot-pc-snapdragon-x-plus-16gb-ram-512gb-ssd-zabriskie-beige/JJGGLH86J4",
    "https://www.bestbuy.com/product/asus-zenbook-14-14-fhd-oled-touch-screen-laptop-intel-core-ultra-7-16gb-ram-512gb-ssd-jasper-gray/JJGGLH7HXW",
]

SKUS = [url.rstrip("/").split("/")[-1] for url in TEST_URLS]

# Try many API endpoints
MULTI_FETCH_JS = """
async (sku) => {
    const results = {};
    const targets = [
        // Pricing APIs
        { name: 'priceBlocks', url: `/api/3.0/priceBlocks?skus=${sku}` },
        { name: 'pricing_v1', url: `/pricing/v1/price/item?skuId=${sku}` },

        // Product detail APIs
        { name: 'pdp_v1', url: `/api/3.0/product/${sku}` },
        { name: 'pdp_offers', url: `/api/3.0/product/offers?skus=${sku}` },

        // Catalog/search APIs
        { name: 'typeahead', url: `/api/1.0/typeahead?query=${sku}` },
        { name: 'search_api', url: `/api/3.0/search?query=${sku}` },

        // Falkor/GraphQL style APIs
        { name: 'tcfb_sku', url: `/api/tcfb/model.json?paths=[["shop","scds","v2","page","ten498702","702","product","${sku}"]]` },
        { name: 'gateway', url: `/gateway/graphql` },

        // Product page data APIs
        { name: 'pdp_data', url: `/site/product-detail/api/v1/products/${sku}` },
        { name: 'catalog', url: `/api/3.0/catalog/products/${sku}` },

        // V2 endpoints
        { name: 'v2_pricing', url: `/api/v2/pricing?skuId=${sku}` },
        { name: 'fulfillment', url: `/fulfillment/v1/availability?skuId=${sku}` },
    ];

    for (const t of targets) {
        try {
            const start = Date.now();
            const opts = {
                credentials: 'include',
                headers: { 'Accept': 'application/json,text/html,*/*' },
            };

            // Special case for GraphQL
            if (t.name === 'gateway') {
                opts.method = 'POST';
                opts.headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify({
                    query: `{ product(skuId: "${sku}") { skuId name regularPrice currentPrice onSale percentSavings } }`
                });
            }

            const resp = await fetch(t.url, opts);
            const elapsed = Date.now() - start;
            const ct = resp.headers.get('content-type') || '';

            let body = '';
            try {
                body = await resp.text();
            } catch(e) {}

            results[t.name] = {
                status: resp.status,
                time_ms: elapsed,
                content_type: ct.substring(0, 50),
                body: body.substring(0, 300),
            };
        } catch (e) {
            results[t.name] = { error: e.message };
        }
    }
    return results;
}
"""


async def main():
    print("=" * 60)
    print("Tim BestBuy API endpoints hoat dong")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        # Load homepage + select US
        print("\nLoading homepage...")
        await page.goto("https://www.bestbuy.com", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        title = await page.title()
        if "International" in title or "Select" in title:
            us = page.locator('a:has-text("United States")')
            if await us.count() > 0:
                await us.first.click()
                await page.wait_for_timeout(3000)
        print(f"Title: {await page.title()}\n")

        # Test with first SKU only (save time)
        sku = SKUS[0]
        print(f"Testing SKU: {sku}")
        print("-" * 60)

        results = await page.evaluate(MULTI_FETCH_JS, sku)

        for name, info in results.items():
            if "error" in info:
                print(f"{name:15s} | FAIL | {info['error'][:60]}")
            else:
                status = info['status']
                ms = info['time_ms']
                body = info['body'].replace('\n', ' ').replace('\r', '')[:150]
                marker = "<--" if status == 200 else ""
                print(f"{name:15s} | {status} | {ms:4d}ms | {body[:120]}... {marker}")

        # Now try searching by product name instead of SKU
        print(f"\n{'='*60}")
        print("Thu search theo ten san pham")
        print(f"{'='*60}")

        search_terms = ["asus zenbook a14 oled snapdragon", "JJGGLH86J4"]
        for term in search_terms:
            print(f"\nSearch: '{term}'")
            search_js = f"""
            async () => {{
                try {{
                    const resp = await fetch('/api/1.0/typeahead?query={term}', {{
                        credentials: 'include',
                        headers: {{ 'Accept': 'application/json' }},
                    }});
                    return {{ status: resp.status, body: await resp.text() }};
                }} catch(e) {{
                    return {{ error: e.message }};
                }}
            }}
            """
            r = await page.evaluate(search_js)
            if "error" in r:
                print(f"  FAIL: {r['error']}")
            else:
                print(f"  Status: {r['status']}")
                print(f"  Body: {r['body'][:300]}")

        await page.wait_for_timeout(3000)
        await browser.close()

    print("\nDONE")


if __name__ == "__main__":
    asyncio.run(main())
