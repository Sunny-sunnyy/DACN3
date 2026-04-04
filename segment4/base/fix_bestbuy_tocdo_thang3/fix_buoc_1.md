# Step 1 Fix: BestBuy Filter - Debug Log

**Date:** 2026-04-04
**Branch:** claudedev
**Status:** NOT DONE

---

## Problem

BestBuy product pages cannot be loaded from WSL Ubuntu. All methods fail.

### Methods Tried

| # | Method | Result |
|---|--------|--------|
| 1 | `requests.get()` | Timeout 10/10 |
| 2 | Playwright Chromium `page.goto()` | `ERR_HTTP2_PROTOCOL_ERROR` |
| 3 | Playwright + `--disable-http2` | Same error |
| 4 | Playwright + full headers + stealth + remove webdriver | Same error |
| 5 | Playwright + visit homepage first + select US | Homepage OK (200), product pages still fail |
| 6 | Playwright Firefox | Homepage OK (200), product pages `NS_ERROR_NET_INTERRUPT` |
| 7 | Windows Chrome via `executable_path` | `Remote debugging pipe not open` (WSL doesn't support pipe) |
| 8 | Windows Chrome via CDP (remote debugging port) | `ECONNREFUSED` - WSL2 and Windows have separate network stacks |
| 9 | JS navigation (`window.location.href`, `assign`, `replace`, click link) | Same error - same HTTP/2 connection |
| 10 | `fetch()` from within browser page | `Failed to fetch` |
| 11 | BestBuy internal API endpoints (12 tested) | Only `/api/3.0/priceBlocks` returns 200, but SKU format incompatible (ProductNotFoundException) |
| 12 | Reduce MTU from 1500 to 1350 | Not yet verified with `page.goto()` (script at that point was API test) |

### Key Findings

1. **Homepage bestbuy.com always loads** (status 200) from WSL - both Chromium and Firefox
2. **Product pages (`/product/...`) and search pages (`/site/...`) always fail** from WSL
3. **Windows Chrome accesses the same URLs fine** - the issue is WSL networking
4. **BestBuy uses Akamai CDN** (23.53.209.3, e5816.x.akamaiedge.net)
5. **Country selection page** appears due to Vietnam IP - must click "United States" first. URL after selection: `https://www.bestbuy.com/?intl=nosplash`
6. **WSL and Windows clocks are in sync** (~9s difference) - not a TLS issue
7. **`curl` from WSL returns HTTP Code 000** for all BestBuy URLs (including homepage), but Playwright loads homepage fine
8. **API `/api/3.0/priceBlocks`** returns 200 but SKU `JJGGLH86J4` is not found (ProductNotFoundException) - new SKU format incompatible with old API
9. **MTU may be root cause** - homepage (small response) works, product pages (large response) fail. Hypothesis: WSL2 virtual network fragments large packets, breaking HTTP/2 frames
