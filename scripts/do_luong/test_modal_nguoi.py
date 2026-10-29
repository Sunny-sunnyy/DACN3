"""Modal nguội + 3 lời gọi song song (như Bước 4): cả nhóm phải xong ~10-15 s, không phải ~30 s."""
import subprocess
import sys
import threading
import time

sys.path.insert(0, ".")
from price_agents.specialist_agent import SpecialistAgent


def containers():
    out = subprocess.run(["uv", "run", "modal", "container", "list"], capture_output=True, text=True, timeout=60).stdout
    return out.count("pricer-service")


t0 = time.perf_counter()
while containers() and time.perf_counter() - t0 < 400:
    time.sleep(15)
print(f"containers now {containers()} (waited {time.perf_counter() - t0:.0f}s)")

agent = SpecialistAgent(timeout_seconds=10)
start = time.perf_counter()


def call(i):
    t = time.perf_counter()
    try:
        r = agent.price(f"Title: test product {i}\nCategory: Electronics")
        print(f"deal {i}: OK ${r:.0f} at {time.perf_counter() - start:.1f}s")
    except Exception as e:
        print(f"deal {i}: {type(e).__name__} after {time.perf_counter() - t:.1f}s (at {time.perf_counter() - start:.1f}s) | {e}")


threads = [threading.Thread(target=call, args=(i,)) for i in range(3)]
for th in threads:
    th.start()
for th in threads:
    th.join()
print(f"group done in {time.perf_counter() - start:.1f}s")
