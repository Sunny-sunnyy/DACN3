"""
Buoc 1: Test lay du lieu BestBuy tu WSL2 qua curl_cffi + APIs.

Pipeline:
1. curl_cffi GET search page -> parse Apollo cache -> lay skuIds + clean pdpUrls
2. GET /api/3.0/priceBlocks?skus=... -> price, brand, name, onSale
3. GET /api/v2/product/SKU -> features (noi dung khi click nut "Features", KHONG phai "About this item")
4. Combine thanh ScrapedBestBuyDeal objects

Giai thich:
- SKU (Stock Keeping Unit) la ma so noi bo cua BestBuy (VD: 6609085).
  APIs cua BestBuy chi nhan SKU dang so, khong nhan slug (VD: JJGGLQVR83).
- curl_cffi impersonate Chrome de bypass anti-bot (requests/httpx deu bi block tu WSL2).
- Product pages (/product/...) bi block do HTTP/2 loi tu WSL2,
  nhung search pages va APIs hoat dong binh thuong.

Chay: cd segment4 && uv run base/fix_bestbuy_tocdo_thang3/buoc1.py
"""

import re
import time
import logging
from curl_cffi import requests as curl_requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step 1: Search page -> lay danh sach skuId + pdpUrl tu Apollo SSR cache
# ---------------------------------------------------------------------------

def search_bestbuy(session, keyword: str) -> list[dict]:
    """Search BestBuy, parse Apollo cache, return list of {skuId, pdpUrl}."""
    url = f"https://www.bestbuy.com/site/searchpage.jsp?st={keyword.replace(' ', '+')}"
    log.info(f"[Step 1] Search: {url}")

    resp = session.get(url, timeout=20)
    log.info(f"  Status: {resp.status_code} | Size: {len(resp.content):,} bytes")

    text = resp.text
    products = {}

    # Tim tat ca skuId dang so (6-8 digits) xuat hien trong Apollo cache
    all_skus = set(re.findall(r'"skuId":"(\d{5,8})"', text))

    # Tim pdpUrl cho tung skuId - chi lay URL "new" (khong co openbox/refurbished)
    for sku_id in all_skus:
        # Pattern: skuId -> pdpUrl (chi match URL khong co "openbox")
        pattern = rf'"skuId":"{sku_id}"\}},"pdpUrl":"(https://www\.bestbuy\.com/product/[^"]+)"'
        for m in re.finditer(pattern, text):
            pdp_url = m.group(1)
            # Bo qua URL openbox/refurbished
            if "openbox" in pdp_url or "refurbished" in pdp_url:
                continue
            # Lam sach URL: bo /sku/XXXXX o cuoi neu co
            clean_url = re.sub(r'/sku/\d+/?$', '', pdp_url)
            products[sku_id] = {"skuId": sku_id, "pdpUrl": clean_url}
            break

    # Neu khong tim thay pdpUrl, van giu skuId (se dung API de lay thong tin)
    for sku_id in all_skus:
        if sku_id not in products:
            products[sku_id] = {"skuId": sku_id, "pdpUrl": ""}

    result = list(products.values())
    log.info(f"  Found {len(result)} unique SKUs ({len([p for p in result if p['pdpUrl']])} with URLs)")
    return result


# ---------------------------------------------------------------------------
# Step 2: priceBlocks API -> price, brand, name, onSale (batch request)
# ---------------------------------------------------------------------------

def get_price_blocks(session, sku_ids: list[str]) -> dict:
    """Batch fetch price+brand+name for multiple SKUs. Returns {skuId: data}."""
    # priceBlocks API co the xu ly nhieu SKU cung luc
    skus_param = ",".join(sku_ids)
    url = f"https://www.bestbuy.com/api/3.0/priceBlocks?skus={skus_param}"
    log.info(f"[Step 2] priceBlocks: {len(sku_ids)} SKUs")

    resp = session.get(url, timeout=15, headers={"Accept": "application/json"})
    log.info(f"  Status: {resp.status_code}")

    results = {}
    for item in resp.json():
        sku = item.get("sku", {})
        if "error" in item:
            sku_id = item.get("skuId", "?")
            log.info(f"  SKU {sku_id}: INACTIVE/ERROR - skip")
            continue

        sku_id = sku.get("buttonState", {}).get("skuId", "")
        price_data = sku.get("price", {})
        price_domain = price_data.get("priceDomain", {})

        results[sku_id] = {
            "brand": sku.get("brand", {}).get("brand", ""),
            "name": sku.get("names", {}).get("short", ""),
            "currentPrice": price_data.get("currentPrice", 0),
            "regularPrice": price_data.get("regularPrice", 0),
            "savingsAmount": price_data.get("savingsAmount", 0),
            "totalSavingsPercent": price_domain.get("totalSavingsPercent", 0),
            "onSale": price_data.get("pricingType") == "onSale",
        }

    log.info(f"  Got price data for {len(results)}/{len(sku_ids)} SKUs")
    return results


# ---------------------------------------------------------------------------
# Step 3: v2 product API -> features (noi dung nut "Features", KHONG phai "About this item")
# ---------------------------------------------------------------------------

def get_product_details(session, sku_id: str) -> dict:
    """Fetch features + URL for a single SKU from /api/v2/product/.

    Returns dict with:
    - features: noi dung nut "Features" (KHONG phai "About this item")
    - url: clean product URL (tu links.seoPdpUrl.href)
    """
    url = f"https://www.bestbuy.com/api/v2/product/{sku_id}"
    resp = session.get(url, timeout=10, headers={"Accept": "application/json"})

    if resp.status_code != 200:
        return {"features": "", "url": ""}

    data = resp.json()

    # URL tu links.seoPdpUrl.href
    product_url = data.get("links", {}).get("seoPdpUrl", {}).get("href", "")

    # features[] = noi dung khi click nut "Features" tren product page
    features_list = data.get("features", [])
    parts = []
    for f in features_list:
        title = f.get("title", "")
        desc = f.get("description", "")
        if title and desc:
            parts.append(f"{title}: {desc}")
        elif title:
            parts.append(title)

    return {"features": ". ".join(parts), "url": product_url}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    keyword = "laptop"

    print("=" * 60)
    print(f"BestBuy Scraper Test - keyword: '{keyword}'")
    print("=" * 60)

    start_total = time.time()

    # Init session + bypass country selection
    session = curl_requests.Session(impersonate="chrome")
    log.info("\n[Init] Bypass country selection...")
    resp = session.get("https://www.bestbuy.com/?intl=nosplash", timeout=15)
    log.info(f"  Homepage: {resp.status_code} | Cookies: {len(session.cookies)}")

    # Step 1: Search -> lay skuIds
    print()
    start = time.time()
    apollo_products = search_bestbuy(session, keyword)
    log.info(f"  Time: {time.time() - start:.1f}s")

    if not apollo_products:
        log.info("No products found. Exiting.")
        return

    # Step 2: priceBlocks (batch) -> price, brand, name, onSale
    print()
    start = time.time()
    sku_ids = [p["skuId"] for p in apollo_products]
    price_data = get_price_blocks(session, sku_ids)
    log.info(f"  Time: {time.time() - start:.1f}s")

    # Filter: chi lay san pham ON SALE
    sale_skus = [sku for sku, data in price_data.items() if data["onSale"]]
    log.info(f"\n  ON SALE: {len(sale_skus)} / {len(price_data)} products")

    if not sale_skus:
        log.info("No sale products found. Showing all products instead.")
        sale_skus = list(price_data.keys())[:5]

    # Limit to 10 for testing
    sale_skus = sale_skus[:10]

    # Step 3: v2 product API -> features + URL (per SKU, top 5 only)
    sale_skus = sale_skus[:5]
    print()
    start = time.time()
    log.info(f"[Step 3] Fetching features + URL for {len(sale_skus)} products...")
    product_details = {}
    for i, sku in enumerate(sale_skus, 1):
        details = get_product_details(session, sku)
        product_details[sku] = details
        name = price_data[sku]["name"][:50]
        has_feat = "YES" if details["features"] else "NO"
        has_url = "YES" if details["url"] else "NO"
        log.info(f"  [{i}/{len(sale_skus)}] SKU {sku} | feat={has_feat} url={has_url} | {name}...")
    log.info(f"  Time: {time.time() - start:.1f}s")

    # Combine into final results
    print()
    print("=" * 60)
    print("RESULTS: ScrapedBestBuyDeal objects")
    print("=" * 60)

    for i, sku in enumerate(sale_skus, 1):
        pd = price_data[sku]
        details = product_details.get(sku, {})

        print(f"\n--- Deal {i} ---")
        print(f"  title:    {pd['name']}")
        print(f"  brand:    {pd['brand']}")
        print(f"  price:    ${pd['currentPrice']} (was ${pd['regularPrice']}, save ${pd['savingsAmount']})")
        print(f"  features: {details['features'][:300]}..." if details.get("features") else "  features: (none)")
        print(f"  url:      {details.get('url') or 'N/A'}")
        print(f"  on_sale:  {pd['onSale']}")

    total_time = time.time() - start_total
    print(f"\n{'=' * 60}")
    print(f"Total time: {total_time:.1f}s")
    print(f"Products found: {len(apollo_products)}")
    print(f"With price data: {len(price_data)}")
    print(f"On sale: {len([s for s in price_data.values() if s['onSale']])}")
    print(f"With features: {len([d for d in product_details.values() if d['features']])}")
    print(f"With URL: {len([d for d in product_details.values() if d['url']])}")


if __name__ == "__main__":
    main()
