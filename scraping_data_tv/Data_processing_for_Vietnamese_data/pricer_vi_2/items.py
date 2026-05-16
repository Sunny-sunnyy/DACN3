from dataclasses import dataclass
from typing import Optional


@dataclass
class Item:
    """
    A Vietnamese product with price in thousands VND.
    price = round(price_vnd / 1000), range 5-1000.

    Usage in notebook:
        from datasets import load_dataset
        from pricer_vi_2.items import Item

        ds = load_dataset("SeanSunny/items_tv_v9")
        train = [Item(**row) for row in ds["train"]]
        val   = [Item(**row) for row in ds["validation"]]
        test  = [Item(**row) for row in ds["test"]]
    """

    title: str
    category: str
    brand: str
    summary: str
    price: float                        # round(price_vnd / 1000), range 5-1000
    price_vnd_true: Optional[int] = None  # raw VND — for verification only, not used as label

    def __repr__(self) -> str:
        return f"<{self.title} = {self.price}k VND>"

    @classmethod
    def from_hub(cls, dataset_name: str) -> tuple[list, list, list]:
        """Load train/val/test splits from HuggingFace Hub."""
        from datasets import load_dataset
        ds = load_dataset(dataset_name)
        train = [cls(**row) for row in ds["train"]]
        val   = [cls(**row) for row in ds["validation"]]
        test  = [cls(**row) for row in ds["test"]]
        return train, val, test
