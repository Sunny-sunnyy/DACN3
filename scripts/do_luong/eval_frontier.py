"""So FrontierAgent (RAG Chroma + LLM) trên 200 mẫu test đầu của SeanSunny/items_full: gpt-5.1 ↔ gpt-6-luna none / low.
Mỗi cấu hình 2 lượt (đo nhiễu). Đầu vào = item.summary (như notebook w8/d2_gpt5rag_ensemble.ipynb).
Chạy từ segment4/: uv run python ../scripts/do_luong/eval_frontier.py
"""
import json
import os
import pickle
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True), override=True)
import chromadb
from price_agents.frontier_agent import FrontierAgent

PRICES = {"gpt-5.1": (1.25, 10.00), "gpt-6-luna": (0.10, 0.50), "gpt-6.1-terra": (1.00, 5.00)}  # USD / 1M token vào, ra (trang giá 29/10)
CONFIGS = [("gpt-5.1", "none"), ("gpt-6-luna", "none"), ("gpt-6-luna", "low")]
if len(sys.argv) > 1:  # vd: gpt-6.1-terra:none
    CONFIGS = [tuple(a.split(":")) for a in sys.argv[1:]]
OUT = "/tmp/prof/runs/eval_frontier" + ("_" + "_".join(sys.argv[1:]).replace(":", "-") if len(sys.argv) > 1 else "") + ".json"
RUNS = 1

TEST_FILE = "/tmp/prof/test200.pkl"
os.makedirs("/tmp/prof/runs", exist_ok=True)
if not os.path.exists(TEST_FILE):  # /tmp mất sau khi khởi động lại máy => tải lại 200 mẫu test đầu (streaming, không tải cả bộ)
    import itertools
    from datasets import load_dataset
    rows = list(itertools.islice(load_dataset("SeanSunny/items_full", split="test", streaming=True), 200))
    pickle.dump(rows, open(TEST_FILE, "wb"))
items = pickle.load(open(TEST_FILE, "rb"))
collection = chromadb.PersistentClient(path="products_vectorstore").get_or_create_collection("products")
agent = FrontierAgent(collection)


def run_config(model, effort):
    usage = {"in": 0, "out": 0}
    orig = agent.client.chat.completions.create

    def create(*a, **kw):
        kw["model"], kw["reasoning_effort"] = model, effort
        r = orig(*a, **kw)
        usage["in"] += r.usage.prompt_tokens
        usage["out"] += r.usage.completion_tokens
        return r

    agent.client.chat.completions.create = create

    def one(item):
        t = time.perf_counter()
        try:
            guess = agent.price(item["summary"])
            err = None
        except Exception as e:
            guess, err = 0.0, f"{type(e).__name__}: {str(e)[:100]}"
        return guess, time.perf_counter() - t, err

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(one, items))
    wall = time.perf_counter() - t0
    agent.client.chat.completions.create = orig

    guesses = [g for g, _, _ in results]
    errors = [abs(g - it["price"]) for g, it in zip(guesses, items)]
    pin, pout = PRICES[model]
    return {
        "model": model, "effort": effort, "mae": round(statistics.mean(errors), 2),
        "zeros": sum(1 for g in guesses if g <= 0), "api_errors": sum(1 for _, _, e in results if e),
        "median_call_s": round(statistics.median(s for _, s, _ in results), 2), "wall_s": round(wall, 1),
        "cost_usd": round((usage["in"] * pin + usage["out"] * pout) / 1e6, 4),
        "tok_out_per_call": round(usage["out"] / len(items), 1), "guesses": guesses,
        "first_error": next((e for _, _, e in results if e), None),
    }


all_runs = []
for run in range(RUNS):
    for model, effort in CONFIGS:
        r = run_config(model, effort)
        r["run"] = run + 1
        all_runs.append(r)
        print(json.dumps({k: v for k, v in r.items() if k != "guesses"}), flush=True)

json.dump(all_runs, open(OUT, "w"), indent=1)
print("\nTONG HOP (MAE | giá 0 | lỗi API | giây/lượt gọi (trung vị) | tiền 200 mẫu)")
for r in all_runs:
    print(f"{r['model']:11s} {r['effort']:5s} MAE ${r['mae']:.2f} | 0: {r['zeros']} | loi {r['api_errors']} | "
          f"{r['median_call_s']:.2f}s | ${r['cost_usd']:.4f}")
