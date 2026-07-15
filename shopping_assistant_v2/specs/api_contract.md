# Spec: API Contract

## Purpose

Define the FastAPI contract for the local MVP.

## Base URL

Local backend:

```text
http://localhost:8000
```

## Endpoints

### `GET /health`

Returns backend health.

Response:

```json
{
  "status": "ok",
  "service": "shopping-assistant-v2"
}
```

### `POST /api/chat-jobs`

Creates a job and returns immediately.

Request:

```json
{
  "message": "Tìm laptop gaming dưới 800 đô",
  "conversation_id": null,
  "source": "All",
  "max_results_per_source": 6
}
```

Validation:

- `message`: string, 2 to 1000 chars.
- `conversation_id`: nullable string.
- `source`: one of `All`, `Amazon`, `BestBuy`.
- `max_results_per_source`: integer, 1 to 20.

Response:

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Job created. Poll status endpoint for results."
}
```

### `GET /api/chat-jobs/{job_id}`

Returns job status and safe result summary.

Pending/running response:

```json
{
  "job_id": "uuid",
  "status": "running",
  "created_at": "iso8601",
  "started_at": "iso8601",
  "completed_at": null,
  "result": null,
  "error_message": null
}
```

Completed response:

```json
{
  "job_id": "uuid",
  "status": "completed",
  "created_at": "iso8601",
  "started_at": "iso8601",
  "completed_at": "iso8601",
  "result": {
    "answer_vi": "Đây là các lựa chọn đáng chú ý...",
    "products": [
      {
        "source": "Amazon",
        "title": "Example laptop",
        "brand": "Example",
        "sale_price_usd": 699.99,
        "estimated_value_usd": 890.0,
        "discount_usd": 190.01,
        "deal_score": "good",
        "url": "https://www.amazon.com/..."
      }
    ],
    "warnings": []
  },
  "error_message": null
}
```

Failed response:

```json
{
  "job_id": "uuid",
  "status": "failed",
  "result": null,
  "error_message": "Search failed. Try again later."
}
```

### `GET /api/chat-jobs/{job_id}/events`

Optional local debug endpoint.

Returns latest agent/tool events for the job.

## Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request.",
    "details": []
  }
}
```

## Auth

MVP:

- no real auth.
- backend assigns `demo_user`.

Later:

- Clerk JWT required.
- all job reads enforce owner check.

## Acceptance Criteria

- API returns `job_id` immediately.
- API never blocks for scraper/model completion.
- Job result shape matches frontend contract.
- Errors are safe and do not expose stack traces.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
