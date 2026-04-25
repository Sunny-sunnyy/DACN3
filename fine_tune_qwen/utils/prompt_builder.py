def build_prompt(item: dict) -> str:
    """Build prompt from item dict using 'summary' column (always non-null in items_tv_v6)."""
    summary = (item.get("summary") or "").strip()
    return f"Sản phẩm này có giá bao nhiêu ?\n{summary}\n\nGiá là: "


def build_completion(price: float) -> str:
    """Completion = round(price/1000) as string for all splits (train/val/test)."""
    return str(int(round(price / 1000)))
