# %% [markdown]
# # Day 4: Frontier LLM — Vietnamese Price Prediction (Zero-shot)
#
# Test 3 OpenAI models (200 items each):
# - gpt-4o-mini
# - gpt-5-nano
# - gpt-5-mini
#
# **Dataset:** SeanSunny/items_tv_v6 filtered <= 1M VND (test set only)

# %% Imports
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
from litellm import completion

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pricer_vi.items import Item
from pricer_vi.evaluator import evaluate

# %% Config
load_dotenv(override=True)

DAY4 = Path(__file__).resolve().parent
DATASET = "SeanSunny/items_tv_v6"
MAX_PRICE = 1_000_000
SIZE = 200
WORKERS = 3

# %% Load test data
print("Loading data...")
_, _, test_items = Item.from_hub(DATASET)
test_items = [it for it in test_items if 0 < it.price <= MAX_PRICE]
print(f"Test items: {len(test_items):,} (evaluate {SIZE})")

# %% Prompt template
SYSTEM_PROMPT = (
    "You are a price estimation expert for Vietnamese e-commerce products. "
    "Estimate the price in VND based on the product description. "
    "Respond with ONLY the number (integer), no currency symbol, no explanation."
)

def messages_for(item):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": item.summary},
    ]

# %% Test prompt with 1 item
print("\n--- Testing prompt ---")
sample = test_items[0]
print(f"Product: {sample.title}")
print(f"Actual price: {sample.price:,} VND")
response = completion(model="openai/gpt-4o-mini", messages=messages_for(sample))
print(f"LLM response: {response.choices[0].message.content}")

# %% Model functions
def gpt_4o_mini(item):
    response = completion(model="openai/gpt-4o-mini", messages=messages_for(item))
    return response.choices[0].message.content

def gpt_5_nano(item):
    response = completion(model="openai/gpt-5-nano", messages=messages_for(item))
    return response.choices[0].message.content

def gpt_5_mini(item):
    response = completion(model="openai/gpt-5-mini", messages=messages_for(item))
    return response.choices[0].message.content

# %% Evaluate gpt-4o-mini
print("\n\n" + "#" * 60)
print("# GPT-4o-mini (200 items)")
print("#" * 60)
results_4o_mini = evaluate(gpt_4o_mini, test_items, size=SIZE, workers=WORKERS)

# %% Evaluate gpt-5-nano
print("\n\n" + "#" * 60)
print("# GPT-5-nano (200 items)")
print("#" * 60)
results_5_nano = evaluate(gpt_5_nano, test_items, size=SIZE, workers=WORKERS)

# %% Evaluate gpt-5-mini
print("\n\n" + "#" * 60)
print("# GPT-5-mini (200 items)")
print("#" * 60)
results_5_mini = evaluate(gpt_5_mini, test_items, size=SIZE, workers=WORKERS)

# %% Summary
print("\n\n" + "=" * 60)
print("FRONTIER LLM RESULTS (200 items each)")
print("=" * 60)

all_results = {
    "gpt-4o-mini": results_4o_mini,
    "gpt-5-nano": results_5_nano,
    "gpt-5-mini": results_5_mini,
}

for name, r in all_results.items():
    print(f"\n{name}:")
    print(f"  RMSLE: {r['rmsle']:.4f} | MAE: {r['mae']:,.0f} VND | MAPE: {r['mape']:.1f}% | R2: {r['r2']:.1f}%")

# Save results
results_path = DAY4 / "day4_frontier_llm_results.json"
with open(results_path, "w") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {results_path}")
