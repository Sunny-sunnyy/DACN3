# Spec: Tool Contracts

## Purpose

Define stable tool interfaces for search and pricing.

## Tool: `deal_search_tool`

### Responsibility

Search Amazon and/or BestBuy and return normalized product candidates.

It must not generate Vietnamese final answers.

### Input

```json
{
  "query_en": "gaming laptop under 800 dollars",
  "source": "All",
  "max_results_per_source": 6
}
```

Validation:

- `query_en`: non-empty English search query.
- `source`: `All`, `Amazon`, `BestBuy`.
- `max_results_per_source`: 1 to 20.

### Output

```json
{
  "products": [
    {
      "source": "BestBuy",
      "title": "Example Laptop",
      "brand": "Example",
      "sale_price_usd": 699.99,
      "url": "https://www.bestbuy.com/...",
      "features": "16GB RAM, RTX GPU...",
      "raw_source_payload": {}
    }
  ],
  "warnings": []
}
```

### Failure Modes

- source blocked.
- no results.
- parse failed.
- network timeout.

Failures should return warnings if another source still produced results.

## Tool: `price_estimator_tool`

### Responsibility

Estimate fair value in USD using the English ensemble pipeline.

It must not search the web. It receives product candidates.

### Input

```json
{
  "product": {
    "source": "Amazon",
    "title": "Example Laptop",
    "brand": "Example",
    "sale_price_usd": 699.99,
    "features": "16GB RAM, RTX GPU",
    "url": "https://www.amazon.com/..."
  }
}
```

### Output

```json
{
  "estimated_value_usd": 890.0,
  "discount_usd": 190.01,
  "deal_score": "good",
  "confidence": null,
  "model_breakdown": {
    "frontier": 900.0,
    "specialist": 850.0,
    "neural": 880.0
  },
  "warnings": []
}
```

### Deal Score

Recommended MVP score:

- `hot`: discount >= 200.
- `good`: discount >= 100.
- `ok`: discount > 0.
- `overpriced`: discount <= 0.

## Mock Mode

Both tools must support fixture/mock mode for local tests.

Environment flags:

- `ENABLE_REAL_SEARCH=false`
- `ENABLE_REAL_MODEL_CALLS=false`

## Source Of Truth

Tool outputs are source of truth for:

- URLs.
- prices.
- product titles.
- features.

The Synthesizer cannot invent these fields.

## Acceptance Criteria

- Tool input/output schemas are validated.
- Mock mode works without network/model calls.
- Real mode is opt-in.
- Warnings are preserved for frontend display.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
