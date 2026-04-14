"""Day 2: LLM Preprocessing — Test script (items 21-30 via preprocessor)."""

from dotenv import load_dotenv

load_dotenv(override=True)

from pricer_vi.items import Item
from pricer_vi.preprocessor import Preprocessor

HF_DATASET = "SeanSunny/items_raw_tv_v4"
START = 21
END = 31


def main():
    print(f"Loading from {HF_DATASET}...")
    train, val, test = Item.from_hub(HF_DATASET)
    items = train + val + test
    print(f"Loaded {len(items):,} items\n")

    # Assign IDs
    for index, item in enumerate(items):
        item.id = index

    preprocessor = Preprocessor()

    for i in range(START, END):
        item = items[i]
        print(f"{'='*80}")
        print(f"[{i}] {item.category} | {item.price:,} VND | brand={item.brand}")
        print(f"TITLE: {item.title}")
        print(f"FULL (first 200 chars): {item.full[:200]}")
        print()

        summary = preprocessor.preprocess(item)
        print(f"SUMMARY:\n{summary}")
        print()

    print(f"{'='*80}")
    print(f"Total input tokens:  {preprocessor.total_input_tokens:,}")
    print(f"Total output tokens: {preprocessor.total_output_tokens:,}")
    print(f"Total cost:          ${preprocessor.total_cost:.4f}")
    avg_cost = preprocessor.total_cost / (END - START)
    est_full = avg_cost * len(items)
    print(f"Avg cost per item:   ${avg_cost:.6f}")
    print(f"Estimated full cost: ${est_full:.2f} for {len(items):,} items")


if __name__ == "__main__":
    main()
