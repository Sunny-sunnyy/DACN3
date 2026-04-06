"""
Test source selection logic for search_and_scrape().

Tests 3 options: "All", "BestBuy", "Amazon"
Verifies that:
- "BestBuy" -> only calls BestBuy pipeline, no Amazon
- "Amazon" -> only calls Amazon pipeline, no BestBuy
- "All" -> calls both in parallel (ThreadPoolExecutor)
"""

import sys
import time
import logging

sys.path.insert(0, "../../")  # segment4/

from price_agents.bestbuy_deals import ScrapedBestBuyDeal, search_filter_scrape_bestbuy
from price_agents.amazon_deals import ScrapedAmazonDeal, search_filter_scrape_amazon
from bestbuy_untils.unified_deal import UnifiedScrapedDeal
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

KEYWORD = "laptop"
MAX_RESULTS = 3


def search_and_scrape(keyword: str, max_results: int = 6, source: str = "All"):
    """Modified search_and_scrape with source parameter."""
    if source == "All":
        log.info(f"Source: BestBuy + Amazon (parallel)")
        with ThreadPoolExecutor(max_workers=2) as executor:
            bb_future = executor.submit(search_filter_scrape_bestbuy, keyword, max_results)
            az_future = executor.submit(search_filter_scrape_amazon, keyword, max_results)
            bb_deals = bb_future.result()
            az_deals = az_future.result()
    elif source == "BestBuy":
        log.info(f"Source: BestBuy")
        bb_deals = search_filter_scrape_bestbuy(keyword, max_results)
        az_deals = []
    elif source == "Amazon":
        log.info(f"Source: Amazon")
        bb_deals = []
        az_deals = search_filter_scrape_amazon(keyword, max_results)
    else:
        raise ValueError(f"Invalid source: {source}. Must be 'All', 'BestBuy', or 'Amazon'.")

    return bb_deals, az_deals


def test_source(source: str):
    """Test a single source option."""
    print(f"\n{'='*60}")
    print(f"TEST: source='{source}' | keyword='{KEYWORD}' | max={MAX_RESULTS}")
    print(f"{'='*60}")

    t0 = time.time()
    bb_deals, az_deals = search_and_scrape(KEYWORD, MAX_RESULTS, source)
    elapsed = time.time() - t0

    # Convert to unified
    unified = []
    for d in bb_deals:
        unified.append(UnifiedScrapedDeal.from_bestbuy(d))
    for d in az_deals:
        unified.append(UnifiedScrapedDeal.from_amazon(d))

    # Print results
    print(f"\nResults: {len(bb_deals)} BestBuy + {len(az_deals)} Amazon = {len(unified)} total")
    print(f"Time: {elapsed:.1f}s")

    for i, u in enumerate(unified):
        print(f"  [{u.source}] {u.title[:60]}... ${u.price:.2f}")

    # Assertions
    if source == "BestBuy":
        assert len(az_deals) == 0, f"Amazon should be empty, got {len(az_deals)}"
        print("PASS: Amazon list is empty")
    elif source == "Amazon":
        assert len(bb_deals) == 0, f"BestBuy should be empty, got {len(bb_deals)}"
        print("PASS: BestBuy list is empty")
    elif source == "All":
        print(f"INFO: BestBuy={len(bb_deals)}, Amazon={len(az_deals)}")

    print(f"PASS: source='{source}' completed in {elapsed:.1f}s")
    return elapsed


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("../../.env", override=True)

    times = {}
    for src in ["BestBuy", "Amazon", "All"]:
        times[src] = test_source(src)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for src, t in times.items():
        print(f"  {src:10s}: {t:.1f}s")
    print(f"\n  All should be ~= max(BestBuy, Amazon), not sum")
    print(f"  max(BB, AZ) = {max(times['BestBuy'], times['Amazon']):.1f}s vs All = {times['All']:.1f}s")
