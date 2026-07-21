"""Deterministic Router — keyword-based Vietnamese intent classification.

Phase 5A: no model calls, no SDK. Replaces the old _normalize_query() bridge.
Phase 5B will add an optional SDK provider behind the same RouterOutput contract.
"""

from __future__ import annotations

import re

from backend.router.schemas import IntentEnum, RouterOutput

# ── Vietnamese stop words — stripped during query extraction ──────────
_STOP_WORDS: set[str] = {
    "tìm", "tim", "mua", "cho", "giúp", "giup", "mình", "minh",
    "tôi", "toi", "với", "voi", "cần", "can", "muốn", "muon",
    "một", "mot", "cái", "cai", "nào", "nao", "giá", "gia",
    "bán", "ban", "có", "co", "không", "khong", "nhé", "nhe",
    "ạ", "a", "nhỉ", "nhi", "đi", "di", "vậy", "vay",
    "là", "la", "ở", "o", "đang", "dang", "rẻ", "re",
    "tốt", "tot", "nha", "hàng", "hang", "loại", "loai",
    # Price-related words kept for pattern matching: dưới, trên, khoảng, đô, usd
}

# ── Shopping intent keywords ─────────────────────────────────────────
_SHOPPING_KEYWORDS: set[str] = {
    "tìm", "tim", "mua", "deal", "sale", "giá", "gia",
    "laptop", "điện thoại", "dien thoai", "tai nghe", "headphone",
    "earphone", "máy tính", "may tinh", "computer", "tablet",
    "máy tính bảng", "may tinh bang", "đồng hồ", "dong ho", "watch",
    "tivi", "tv", "màn hình", "man hinh", "monitor",
    "bàn phím", "ban phim", "keyboard", "chuột", "chuot", "mouse",
    "loa", "speaker", "máy ảnh", "may anh", "camera",
    "tủ lạnh", "tu lanh", "máy giặt", "may giat",
    "gaming", "console", "ps5", "xbox", "nintendo",
    "router", "modem", "ổ cứng", "o cung", "ssd", "ram",
    "card", "gpu", "cpu", "màn", "man",
}

# ── Vi → En category mapping ─────────────────────────────────────────
_VI_TO_EN: dict[str, str] = {
    "điện thoại": "phone",
    "dien thoai": "phone",
    "tai nghe": "headphones",
    "headphone": "headphones",
    "earphone": "earphones",
    "máy tính": "computer",
    "may tinh": "computer",
    "laptop": "laptop",
    "máy tính bảng": "tablet",
    "may tinh bang": "tablet",
    "đồng hồ": "watch",
    "dong ho": "watch",
    "tivi": "tv",
    "màn hình": "monitor",
    "man hinh": "monitor",
    "bàn phím": "keyboard",
    "ban phim": "keyboard",
    "chuột": "mouse",
    "chuot": "mouse",
    "loa": "speaker",
    "máy ảnh": "camera",
    "may anh": "camera",
    "tủ lạnh": "refrigerator",
    "tu lanh": "refrigerator",
    "máy giặt": "washing machine",
    "may giat": "washing machine",
    "ổ cứng": "hard drive",
    "o cung": "hard drive",
    "card đồ họa": "graphics card",
    "card do hoa": "graphics card",
}

# ── Price patterns ───────────────────────────────────────────────────
_PRICE_PATTERNS: list[tuple[str, str]] = [
    (r"dưới\s+(\d+)\s*(?:đô|do|usd|dollar|dollars|đ)", r"under \1 dollars"),
    (r"duoi\s+(\d+)\s*(?:đô|do|usd|dollar|dollars|đ)", r"under \1 dollars"),
    (r"trên\s+(\d+)\s*(?:đô|do|usd|dollar|dollars|đ)", r"above \1 dollars"),
    (r"tren\s+(\d+)\s*(?:đô|do|usd|dollar|dollars|đ)", r"above \1 dollars"),
    (r"khoảng\s+(\d+)\s*(?:đô|do|usd|dollar|dollars|đ)", r"around \1 dollars"),
    (r"khoang\s+(\d+)\s*(?:đô|do|usd|dollar|dollars|đ)", r"around \1 dollars"),
    (r"(\d+)\s*(?:đô|do|usd|dollar|dollars|đ)", r"\1 dollars"),
]


def _has_shopping_intent(message_lower: str) -> bool:
    """Check if the message contains any shopping-related keyword."""
    for kw in _SHOPPING_KEYWORDS:
        if kw in message_lower:
            return True
    return False


def _detect_source(message_lower: str) -> str:
    """Detect source preference from message."""
    has_amazon = any(w in message_lower for w in ("amazon",))
    has_bestbuy = any(w in message_lower for w in ("bestbuy", "best buy"))
    if has_amazon and not has_bestbuy:
        return "Amazon"
    if has_bestbuy and not has_amazon:
        return "BestBuy"
    return "All"


def _extract_query_en(message_lower: str) -> str:
    """Extract English-like search tokens from Vietnamese message.

    1. Lowercase + strip non-alphanumeric (keep spaces).
    2. Remove Vietnamese stop words.
    3. Replace Vi category words with En equivalents.
    4. Apply price pattern translations.
    """
    # Remove punctuation, keep letters/numbers/spaces
    cleaned = re.sub(r"[^\w\s]", " ", message_lower)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Tokenize
    tokens = cleaned.split()

    # Remove stop words
    tokens = [t for t in tokens if t not in _STOP_WORDS]

    if not tokens:
        return ""

    # Reconstruct text
    text = " ".join(tokens)

    # Apply Vi→En category mappings (longest match first)
    sorted_mappings = sorted(_VI_TO_EN.items(), key=lambda x: -len(x[0]))
    for vi_word, en_word in sorted_mappings:
        text = text.replace(vi_word, en_word)

    # Apply price pattern translations
    for pattern, replacement in _PRICE_PATTERNS:
        text = re.sub(pattern, replacement, text)

    # Clean up double spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def deterministic_route(message_vi: str) -> RouterOutput:
    """Classify Vietnamese user message and produce RouterOutput.

    MVP Phase 5A:
      - Only "search_deals" intent is executable.
      - All other intents return UNSUPPORTED with needs_tool=False.
      - No model calls, no SDK.

    Args:
        message_vi: Raw Vietnamese user message (1-1000 chars).

    Returns:
        RouterOutput with intent, query_en, source, and confidence.
    """
    message_lower = message_vi.strip().lower()

    # Check for shopping intent
    has_intent = _has_shopping_intent(message_lower)
    query_en = _extract_query_en(message_lower)
    source = _detect_source(message_lower)

    if has_intent and query_en:
        return RouterOutput(
            intent=IntentEnum.SEARCH_DEALS,
            query_en=query_en,
            source=source,
            max_results_per_source=5,
            confidence=0.7,
            needs_tool=True,
        )

    if has_intent:
        # Shopping keywords found but query extraction produced nothing useful.
        # Use raw message as query_en as fallback.
        return RouterOutput(
            intent=IntentEnum.SEARCH_DEALS,
            query_en=message_lower,
            source=source,
            max_results_per_source=5,
            confidence=0.5,
            needs_tool=True,
        )

    # No shopping intent detected → unsupported
    return RouterOutput(
        intent=IntentEnum.UNSUPPORTED,
        query_en="",
        source="All",
        max_results_per_source=0,
        confidence=0.3,
        needs_tool=False,
    )
