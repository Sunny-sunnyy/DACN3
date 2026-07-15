# shared

Config, structured logging, common schemas, guardrails, error types, and retry
helpers shared across backend modules.

Rule: `shared/` must not import from `api/`, `router/`, `tools/`, or
`synthesizer/`.

Implemented in Phase 2 and later. No code yet.
