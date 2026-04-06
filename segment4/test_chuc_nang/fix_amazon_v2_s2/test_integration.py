"""
Phase 4: Integration test - BestBuy + Amazon parallel pipeline.

Tests:
1. Amazon search_filter_scrape_amazon() works standalone
2. BestBuy search_filter_scrape_bestbuy() works standalone
3. Both run in parallel via ThreadPoolExecutor
4. UnifiedScrapedDeal conversion works for both sources

Run: cd segment4 && uv run test_chuc_nang/fix_amazon_v2_s2/test_integration.py
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add segment4/ to sys.path so imports work from any working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from price_agents.amazon_deals import search_filter_scrape_amazon, ScrapedAmazonDeal
from price_agents.bestbuy_deals import search_filter_scrape_bestbuy, ScrapedBestBuyDeal
from bestbuy_untils.unified_deal import UnifiedScrapedDeal


KEYWORD = "laptop gaming"
MAX_RESULTS = 6


def test_amazon_standalone():
    """Test Amazon pipeline standalone."""
    print("\n" + "=" * 60)
    print("  TEST 1: Amazon standalone")
    print("=" * 60)

    t0 = time.time()
    deals = search_filter_scrape_amazon(KEYWORD, max_results=MAX_RESULTS)
    elapsed = time.time() - t0

    print(f"\n  Results: {len(deals)} deals in {elapsed:.1f}s")
    for i, d in enumerate(deals, 1):
        print(f"  [{i}] ${d.price:.2f} | {d.title[:70]}")
        print(f"       Brand: {d.brand or 'N/A'} | Features: {len(d.features)} chars")

    assert len(deals) > 0, "Amazon returned 0 deals"
    assert all(isinstance(d, ScrapedAmazonDeal) for d in deals)
    assert all(d.price > 0 for d in deals)
    print(f"\n  PASS - {len(deals)} deals, {elapsed:.1f}s")
    return deals


def test_bestbuy_standalone():
    """Test BestBuy pipeline standalone."""
    print("\n" + "=" * 60)
    print("  TEST 2: BestBuy standalone")
    print("=" * 60)

    t0 = time.time()
    deals = search_filter_scrape_bestbuy(KEYWORD, max_results=MAX_RESULTS)
    elapsed = time.time() - t0

    print(f"\n  Results: {len(deals)} deals in {elapsed:.1f}s")
    for i, d in enumerate(deals, 1):
        print(f"  [{i}] ${d.price:.2f} | {d.title[:70]}")
        print(f"       Brand: {d.brand or 'N/A'} | Features: {len(d.features)} chars")

    assert len(deals) > 0, "BestBuy returned 0 deals"
    assert all(isinstance(d, ScrapedBestBuyDeal) for d in deals)
    assert all(d.price > 0 for d in deals)
    print(f"\n  PASS - {len(deals)} deals, {elapsed:.1f}s")
    return deals


def test_parallel():
    """Test BestBuy + Amazon in parallel."""
    print("\n" + "=" * 60)
    print("  TEST 3: Parallel BestBuy + Amazon")
    print("=" * 60)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=2) as executor:
        bb_future = executor.submit(search_filter_scrape_bestbuy, KEYWORD, MAX_RESULTS)
        az_future = executor.submit(search_filter_scrape_amazon, KEYWORD, MAX_RESULTS)

        bb_deals = bb_future.result()
        az_deals = az_future.result()

    elapsed = time.time() - t0
    print(f"\n  BestBuy: {len(bb_deals)} deals")
    print(f"  Amazon:  {len(az_deals)} deals")
    print(f"  Total:   {len(bb_deals) + len(az_deals)} deals in {elapsed:.1f}s")

    assert len(bb_deals) + len(az_deals) > 0, "Both sources returned 0 deals"
    print(f"\n  PASS - parallel completed in {elapsed:.1f}s")
    return bb_deals, az_deals


def test_unified_conversion(bb_deals, az_deals):
    """Test UnifiedScrapedDeal conversion."""
    print("\n" + "=" * 60)
    print("  TEST 4: UnifiedScrapedDeal conversion")
    print("=" * 60)

    unified = []
    for d in bb_deals:
        unified.append(UnifiedScrapedDeal.from_bestbuy(d))
    for d in az_deals:
        unified.append(UnifiedScrapedDeal.from_amazon(d))

    print(f"\n  Unified pool: {len(unified)} products")
    for u in unified:
        print(f"  [{u.source}] ${u.price:.2f} | {u.title[:60]}")

    assert len(unified) == len(bb_deals) + len(az_deals)
    assert all(u.source in ("BestBuy", "Amazon") for u in unified)
    assert all(u.price > 0 for u in unified)

    # Test describe() works (used by MultiSourceScannerAgent)
    for u in unified[:2]:
        desc = u.describe()
        assert "Source:" in desc
        assert "Price:" in desc

    print(f"\n  PASS - {len(unified)} unified deals")


if __name__ == "__main__":
    print("Phase 4 Integration Test")
    print(f"Keyword: '{KEYWORD}' | Max results: {MAX_RESULTS}")

    total_start = time.time()

    # Test 1+2: standalone (sequential for clarity)
    az_deals = test_amazon_standalone()
    bb_deals = test_bestbuy_standalone()

    # Test 3: parallel
    bb_parallel, az_parallel = test_parallel()

    # Test 4: unified conversion
    test_unified_conversion(bb_parallel, az_parallel)

    total = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"  ALL TESTS PASSED in {total:.1f}s")
    print("=" * 60)
