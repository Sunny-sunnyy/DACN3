PROMPT_TEMPLATE = """Sản phẩm này có giá bao nhiêu ?
Tiêu đề: {title}
Danh mục: {category}
Thương hiệu: {brand}
Mô tả: {description}
Thông số: {features}

Giá là: """


def build_prompt(item: dict) -> str:
    return PROMPT_TEMPLATE.format(
        title=item.get("title") or "",
        category=item.get("category") or "",
        brand=item.get("brand") or "Không rõ",
        description=item.get("description") or "Không có mô tả",
        features=item.get("features") or "Không có thông số",
    )


def build_completion(price: float, for_test: bool = False) -> str:
    """Train/val: round(price/1000) as string. Test: int(price) as string."""
    if for_test:
        return str(int(round(price)))
    return str(int(round(price / 1000)))
