# shared

Config, structured logging, schemas chung, guardrails, error types, và retry
helpers dùng chung giữa các backend modules.

Quy tắc: `shared/` không được import từ `api/`, `router/`, `tools/`, hoặc
`synthesizer/`.

Được implement trong Phase 2 và các phase sau. Chưa có code.
