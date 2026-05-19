"""Vietnamese product item loader for fine-tuning.

Loads HuggingFace dataset `SeanSunny/items_prompts_tv_4` into typed Item objects.
Price is exposed in two units: K VND (e.g. 55.0) for model output scale,
and raw VND (e.g. 55000) for display.
"""
import re
from dataclasses import dataclass

from datasets import load_dataset

DATASET_NAME = "SeanSunny/items_prompts_tv_4"


@dataclass
class Item:
    title: str
    price: float    # K VND - e.g. 55.0 for 55,000 VND
    price_vnd: int  # raw VND - e.g. 55000
    prompt: str


def _parse_title(prompt: str) -> str:
    m = re.search(r"Tiêu đề:\s*(.+)", prompt)
    return m.group(1).strip() if m else "Unknown"


def load_items(split: str, size: int | None = None) -> list[Item]:
    """Load HuggingFace split into list[Item].

    Args:
        split: "train", "validation", or "test"
        size:  max items to load (None = all)
    """
    ds = load_dataset(DATASET_NAME, split=split)
    if size is not None:
        ds = ds.select(range(min(size, len(ds))))
    return [
        Item(
            title=_parse_title(row["prompt"]),
            price=int(row["price_vnd_true"]) / 1000,
            price_vnd=int(row["price_vnd_true"]),
            prompt=row["prompt"],
        )
        for row in ds
    ]
