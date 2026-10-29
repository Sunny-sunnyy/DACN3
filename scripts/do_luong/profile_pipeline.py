"""Đo thời gian từng hàm trong pipeline search_key (không sửa code dự án: bọc hàm từ bên ngoài).
Chạy từ segment4/: uv run python ../scripts/do_luong/profile_pipeline.py "<keyword>" <label>
Ghi kết quả JSON vào /tmp/prof/runs/<label>__<keyword>.json để so trước / sau.
"""
import functools
import json
import os
import sys
import threading
import time

sys.path.insert(0, ".")
T0 = time.perf_counter()
EVENTS = []  # (name, start, end, thread, extra)


def timed(name, fn, extra_fn=None):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        s = time.perf_counter()
        r = None
        try:
            r = fn(*a, **kw)
            return r
        finally:
            e = time.perf_counter()
            extra = ""
            if extra_fn:
                try:
                    extra = extra_fn(r)
                except Exception:
                    pass
            EVENTS.append((name, s - T0, e - T0, threading.current_thread().name[:12], extra))
    return wrapper


def wrap_if(obj, attr, name, extra_fn=None):
    if hasattr(obj, attr):
        setattr(obj, attr, timed(name, getattr(obj, attr), extra_fn))


import price_agents.bestbuy_deals as bb
import price_agents.amazon_deals as az

for mod, names in [(bb, ["_init_session", "search_bestbuy", "get_price_blocks", "get_product_details"]),
                   (az, ["_get_waf_cookies", "search_amazon", "scrape_product_page"])]:
    for n in names:
        wrap_if(mod, n, f"{mod.__name__.split('.')[-1][:2]}.{n}")

from multi_source_framework import MultiSourceFramework
if len(sys.argv) > 3 and sys.argv[3] == "warm":
    from price_agents.specialist_agent import wake_up_modal
    wake_up_modal()  # như lúc mở app Gradio
    EVENTS.append(("wake_up_modal", time.perf_counter() - T0, time.perf_counter() - T0, "Main", ""))

t = time.perf_counter()
fw = MultiSourceFramework()
EVENTS.append(("framework_init(chroma)", t - T0, time.perf_counter() - T0, "Main", ""))
t = time.perf_counter()
fw.init_agents_as_needed()
EVENTS.append(("init_agents(models)", t - T0, time.perf_counter() - T0, "Main", ""))

pl = fw.planner
NOTIFIED = []
pl.messenger.notify = lambda *a, **kw: (NOTIFIED.append(kw or a), print(">>> [TEST] Pushover bi chan"))
wrap_if(pl, "_bestbuy_pipeline", "STEP1.bestbuy_total", lambda r: f"{len(r)} deals")
wrap_if(pl, "_amazon_pipeline", "STEP1.amazon_total", lambda r: f"{len(r)} deals")

usage = lambda r: f"in {r.usage.prompt_tokens} tok / out {r.usage.completion_tokens} tok"
comp = pl.multi_scanner.openai.chat.completions
comp.parse = timed("STEP3.select_llm", comp.parse, usage)

ens = pl.ensemble
wrap_if(ens.preprocessor, "preprocess", "S4.preprocess(groq)")
wrap_if(ens.specialist, "price", "S4.specialist(modal)", lambda r: f"${r:.0f}")
wrap_if(ens.frontier, "find_similars", "S4.frontier.rag(chroma)")
fcomp = ens.frontier.client.chat.completions
fcomp.create = timed("S4.frontier.gpt51", fcomp.create, usage)
wrap_if(ens.neural_network, "price", "S4.neural(dnn)", lambda r: f"${r:.0f}")
wrap_if(ens, "price", "S4.ensemble_one_deal", lambda r: f"${r:.0f}")

for step in ["search_and_scrape", "combine", "select_top_deals", "estimate_prices"]:
    wrap_if(pl, step, f"== {step}")

kw = sys.argv[1] if len(sys.argv) > 1 else "wireless headphones"
label = sys.argv[2] if len(sys.argv) > 2 else "run"
t = time.perf_counter()
opps = fw.run(kw, 6, "All")
total = time.perf_counter() - t

print("\n" + "=" * 100)
print(f"KEYWORD '{kw}' | label {label} | pipeline {total:.1f}s | {len(opps)} opportunities")
print(f"{'ham':32s} {'bat dau':>8s} {'ket thuc':>8s} {'mat':>6s}  {'luong':12s} ghi chu")
for name, s, e, th, extra in sorted(EVENTS, key=lambda x: x[1]):
    print(f"{name:32s} {s:8.1f} {e:8.1f} {e - s:6.1f}  {th:12s} {extra}")
for o in opps:
    print(f"  ${o.deal.price:>7.2f} -> est ${o.estimate:>7.2f} | {o.deal.product_description[:60]} | {o.deal.url[:70]}")

os.makedirs("/tmp/prof/runs", exist_ok=True)
out = f"/tmp/prof/runs/{label}__{kw.replace(' ', '_')}.json"
with open(out, "w") as f:
    json.dump({
        "keyword": kw, "label": label, "pipeline_seconds": round(total, 1),
        "events": [dict(name=n, start=round(s, 2), end=round(e, 2), sec=round(e - s, 2), thread=th, extra=x)
                   for n, s, e, th, x in EVENTS],
        "opportunities": [dict(price=o.deal.price, estimate=o.estimate, discount=o.discount,
                               description=o.deal.product_description, url=o.deal.url) for o in opps],
        "notified": len(NOTIFIED),
    }, f, indent=1, ensure_ascii=False)
print("SAVED", out)
