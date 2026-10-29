"""Cào BestBuy + Amazon cho các từ khoá (song song như pipeline), lưu pool UnifiedScrapedDeal ra pickle
để đo bước chọn deal (Bước 3) trên cùng một đầu vào. Không nạp mô hình, không gọi LLM.
Chạy từ segment4/: uv run python ../scripts/do_luong/save_pools.py "air fryer" "wireless headphones"
"""
import logging
import os
import pickle
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(message)s")
from price_agents.bestbuy_deals import search_filter_scrape_bestbuy
from price_agents.amazon_deals import search_filter_scrape_amazon
from bestbuy_untils.unified_deal import UnifiedScrapedDeal

os.makedirs("/tmp/prof/pools", exist_ok=True)


def timed(fn, *a):
    t = time.perf_counter()
    r = fn(*a)
    return r, time.perf_counter() - t


for i, kw in enumerate(sys.argv[1:]):
    if i:
        time.sleep(5)  # Amazon: request thưa
    with ThreadPoolExecutor(max_workers=2) as ex:
        bb_f = ex.submit(timed, search_filter_scrape_bestbuy, kw, 6)
        az_f = ex.submit(timed, search_filter_scrape_amazon, kw, 6)
        (bb, bb_s), (az, az_s) = bb_f.result(), az_f.result()
    pool = [UnifiedScrapedDeal.from_bestbuy(d) for d in bb] + [UnifiedScrapedDeal.from_amazon(d) for d in az]
    path = f"/tmp/prof/pools/{kw.replace(' ', '_')}.pkl"
    with open(path, "wb") as f:
        pickle.dump(pool, f)
    print(f"POOL '{kw}': BestBuy {len(bb)} ({bb_s:.1f}s) | Amazon {len(az)} ({az_s:.1f}s) -> {path}")
