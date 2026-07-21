"""Deterministic Synthesizer — template-based Vietnamese answer generation.

Phase 5A: no model calls, no SDK. Generates Vietnamese answers from structured
tool evidence with strict no-hallucination rules.
Phase 5B will add an optional SDK provider behind the same SynthesizerOutput contract.
"""

from __future__ import annotations

from backend.synthesizer.schemas import (
    SummaryCard,
    SynthesizerInput,
    SynthesizerOutput,
)
from backend.tools.deal_search.schemas import ProductCandidate
from backend.tools.price_estimator.schemas import PriceEstimateOutput

# ── Warning translation: key prefix → Vietnamese message ─────────────
_WARNING_TRANSLATIONS: list[tuple[str, str]] = [
    ("frontier_unavailable", "Mo hinh dinh gia nang cao chua san sang, dang dung uoc tinh co ban."),
    ("specialist_unavailable", "Mo hinh chuyen gia chua san sang, dang dung uoc tinh thay the."),
    ("neural_unavailable", "Mo hinh hoc may chua san sang."),
    ("real_pricing_fallback_used", "Dang dung uoc tinh co ban (gia ban + 5%)."),
    ("no_products_found", "Khong tim thay san pham nao."),
    ("source_partial", "Chi tim duoc ket qua tu mot nguon."),
    ("ensemble_partial", "He thong dinh gia chua hoan chinh, dang dung uoc tinh co ban nhat."),
]


def _translate_warnings(warnings: list[str]) -> list[str]:
    """Translate technical warning codes to Vietnamese messages.

    Deduplicates by category — each warning prefix translates to at most
    one Vietnamese message.
    """
    seen_prefixes: set[str] = set()
    result: list[str] = []

    for w in warnings:
        # Extract the prefix before the first colon
        prefix = w.split(":", 1)[0] if ":" in w else w

        if prefix in seen_prefixes:
            continue
        seen_prefixes.add(prefix)

        # Find matching translation
        for warn_prefix, msg_vi in _WARNING_TRANSLATIONS:
            if prefix == warn_prefix or w.startswith(warn_prefix):
                result.append(msg_vi)
                break

    return result


def _build_highlight_vi(discount_usd: float | None, deal_score: str | None) -> str:
    """Generate a 1-line Vietnamese assessment for a product card."""
    if discount_usd is None and deal_score is None:
        return "Khong co du lieu de danh gia deal nay."

    score = deal_score or "ok"
    discount = discount_usd or 0.0

    score_labels = {
        "hot": "deal rat tot",
        "good": "deal tot",
        "ok": "deal tam duoc",
        "overpriced": "gia hoi cao so voi gia tri thuc",
    }
    label = score_labels.get(score, "deal tam duoc")

    if discount > 0:
        return f"Giam ${discount:.2f} — {label}."
    elif discount < 0:
        return f"Cao hon gia tri uoc tinh ${abs(discount):.2f} — {label}."
    else:
        return f"Gia ngang gia tri uoc tinh — {label}."


def _build_summary_cards(
    products: list[ProductCandidate],
    estimates: list[PriceEstimateOutput],
) -> list[SummaryCard]:
    """Build summary cards pairing products with their estimates.

    Sorted by discount descending (best deals first).
    """
    estimate_map: dict[int, PriceEstimateOutput] = {}
    for est in estimates:
        # Match by product index (estimates are in same order as products)
        idx = len(estimate_map)
        estimate_map[idx] = est

    cards: list[SummaryCard] = []
    for i, p in enumerate(products):
        est = estimate_map.get(i)
        if est:
            discount = est.discount_usd
            deal_score = est.deal_score
        else:
            discount = None
            deal_score = None

        cards.append(SummaryCard(
            source=p.source,
            title=p.title,
            sale_price_usd=p.sale_price_usd,
            estimated_value_usd=est.estimated_value_usd if est else None,
            discount_usd=discount,
            deal_score=deal_score,
            url=p.url,
            highlight_vi=_build_highlight_vi(discount, deal_score),
        ))

    # Sort by discount descending (best deals first, None last)
    cards.sort(
        key=lambda c: (c.discount_usd is None, -(c.discount_usd or 0))
    )
    return cards


def _build_answer_vi(
    message_vi: str,
    intent: str,
    products: list[ProductCandidate],
    estimates: list[PriceEstimateOutput],
    warnings_vi: list[str],
) -> str:
    """Build the main Vietnamese answer text from evidence."""
    n = len(products)

    # ── Unsupported intent ──
    if intent == "unsupported":
        return (
            "Minh la tro ly mua sam, hien tai minh ho tro tim kiem san pham "
            "va danh gia deal tu Amazon va BestBuy. Ban hay thu tim mot san "
            "pham cu the nhe. Vi du: \"Tim laptop gaming duoi 800 do\"."
        )

    # ── No results ──
    if n == 0:
        parts = ["Khong tim thay san pham nao phu hop voi yeu cau cua ban."]
        if warnings_vi:
            parts.append("Mot so luu y:")
            parts.extend(f"  - {w}" for w in warnings_vi)
        parts.append("Ban thu tim voi tu khoa khac nhe.")
        return "\n".join(parts)

    # ── 1 product ──
    if n == 1:
        p = products[0]
        price_str = f"${p.sale_price_usd:.2f}" if p.sale_price_usd else "khong ro gia"
        lines = [
            f"Minh tim duoc 1 san pham phu hop:",
            f"",
            f"  {p.title}",
            f"  Nguon: {p.source}",
            f"  Gia ban: {price_str}",
        ]
        if warnings_vi:
            lines.append("")
            lines.append("Luu y:")
            lines.extend(f"  - {w}" for w in warnings_vi)
        return "\n".join(lines)

    # ── Multiple products ──
    # Find best deal by discount (consistent with summary_cards ordering).
    best_idx = 0
    best_discount = -float("inf")
    for i in range(len(products)):
        est = estimates[i] if i < len(estimates) else None
        discount = est.discount_usd if est and est.discount_usd is not None else 0.0
        if discount > best_discount:
            best_discount = discount
            best_idx = i

    best_product = products[best_idx]
    lines = [
        f"Minh tim duoc {n} san pham phu hop. Noi bat nhat:",
        f"",
        f"  {best_product.title}",
        f"  Nguon: {best_product.source}",
    ]
    if best_product.sale_price_usd:
        lines.append(f"  Gia ban: ${best_product.sale_price_usd:.2f}")

    lines.append("")
    lines.append(f"Dua tren ket qua, day la {n} san pham dang xem xet. "
                  f"San pham {best_product.title} tu {best_product.source} "
                  f"noi bat nhat.")
    lines.append("")
    lines.append("Chi tiet tung san pham co trong danh sach ben duoi.")

    if warnings_vi:
        lines.append("")
        lines.append("Luu y:")
        lines.extend(f"  - {w}" for w in warnings_vi)

    return "\n".join(lines)


def deterministic_synthesize(input_data: SynthesizerInput) -> SynthesizerOutput:
    """Generate a Vietnamese answer from structured tool evidence.

    Strict evidence rules:
      - Never invent prices, URLs, specs, or discounts.
      - Product names stay in English.
      - Prices stay in USD.
      - Warnings are translated to Vietnamese for the user.

    Args:
        input_data: SynthesizerInput with products, estimates, and warnings.

    Returns:
        SynthesizerOutput with Vietnamese answer and summary cards.
    """
    warnings_vi = _translate_warnings(input_data.warnings)
    summary_cards = _build_summary_cards(
        input_data.products, input_data.price_estimates
    )
    answer_vi = _build_answer_vi(
        input_data.message_vi,
        input_data.intent,
        input_data.products,
        input_data.price_estimates,
        warnings_vi,
    )

    return SynthesizerOutput(
        answer_vi=answer_vi,
        summary_cards=summary_cards,
        warnings_vi=warnings_vi,
    )
