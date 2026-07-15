# Spec: Frontend Contract

## Purpose

Define what the Next.js frontend must render and how it interacts with the backend.

## Core Page

MVP has one primary page:

```text
Chat Assistant Page
```

## User Flow

```text
User enters Vietnamese message
-> frontend calls POST /api/chat-jobs
-> frontend receives job_id
-> frontend polls GET /api/chat-jobs/{job_id}
-> frontend renders status and result
```

## Components

Required:

- `ChatPanel`
- `JobStatus`
- `ProductResults`
- `ProductCard`
- `DebugLogPanel`

## Product Card Schema

Frontend receives:

```json
{
  "source": "Amazon",
  "title": "Example Laptop",
  "brand": "Example",
  "sale_price_usd": 699.99,
  "estimated_value_usd": 890.0,
  "discount_usd": 190.01,
  "deal_score": "good",
  "url": "https://www.amazon.com/..."
}
```

## UI States

Required states:

- `idle`: no job.
- `submitting`: request in flight.
- `pending`: job created.
- `running`: worker processing.
- `completed`: show answer and cards.
- `failed`: show safe error.

## Polling

Recommended MVP polling:

- every 1 second while pending/running.
- stop on completed/failed.
- show timeout warning after long wait.

## Error Display

Frontend should show:

- validation error.
- backend unavailable.
- job failed.
- partial source warnings.

Do not show stack traces.

## Accessibility

Minimum:

- inputs have labels.
- buttons have readable text.
- status updates are visible.
- links open safely.

## Acceptance Criteria

- User can submit Vietnamese message.
- Product cards render correctly from backend response.
- Failed job does not break UI.
- Debug job_id is visible for troubleshooting.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
