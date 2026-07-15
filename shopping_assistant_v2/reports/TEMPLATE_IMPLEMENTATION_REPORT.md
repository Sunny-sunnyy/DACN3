# Implementation Report Template

**Phase:** `<phase number and name>`  
**Implementer agent:** `<agent/model/tool>`  
**Date:** `<YYYY-MM-DD>`  
**Branch:** `<git branch>`  
**Commit reviewed:** `<commit hash or "not committed yet">`

---

## 1. Goal

State the exact goal of this phase.

Example:

```text
Implement Phase 2: Local Backend Foundation with FastAPI health endpoint,
SQLite job creation, and job status polling.
```

---

## 2. Context Read Before Implementation

List the docs/specs/guides read before coding.

Required:

- `shopping_assistant_v2/PROMPT_NEW_SESSION.md`
- `shopping_assistant_v2/PROJECT_DEVELOPMENT_PLAN_V2.md`
- `shopping_assistant_v2/PROJECT_STRUCTURE_AND_IMPLEMENTATION_ORDER.md`
- Relevant `plans/*.md`
- Relevant `specs/*.md`
- Relevant `guides/*.md`

If any required doc was skipped, explain why.

---

## 3. Brainstorming Summary

Summarize the implementation approach agreed with the user before coding.

Include:

- assumptions;
- chosen option;
- rejected options;
- scope boundaries;
- validation criteria.

---

## 4. Files Created

List all new files.

```text
path/to/file.py - purpose
path/to/file.md - purpose
```

---

## 5. Files Modified

List all modified files.

```text
path/to/file.py - what changed and why
path/to/file.md - what changed and why
```

---

## 6. Implementation Details

Describe what was implemented.

Keep this factual and specific:

- new modules;
- key functions/classes;
- API endpoints;
- schemas;
- database changes;
- job lifecycle changes;
- frontend components;
- tool/agent behavior.

Do not overstate. If something is only mocked, say it is mocked.

---

## 7. Deviations From Plans/Specs/Guides

List any deviation from existing documentation.

For each deviation:

```text
Original doc expectation:
Actual implementation:
Reason:
Should docs be updated? yes/no
```

If there are no deviations, write:

```text
No intentional deviations.
```

---

## 8. Verification Performed

List commands/tests run.

Use exact commands:

```bash
uv run pytest ...
npm run ...
curl ...
```

For each command:

- result: pass/fail;
- important output summary;
- known warnings.

If tests were not run, explain why.

---

## 9. Manual Validation

Describe any manual checks.

Example:

```text
Created a chat job through API.
Confirmed status moved from pending to completed.
Confirmed result payload matched specs/api_contract.md.
```

---

## 10. Remaining Risks

List known risks, gaps, or unresolved questions.

Classify:

- Blocker
- Major
- Minor

---

## 11. Suggested Reviewer Focus

Tell the reviewer what to inspect first.

Examples:

- API contract compatibility.
- Database schema correctness.
- Job status idempotency.
- Whether docs need updating.
- Whether implementation over-expanded scope.

---

## 12. Docs That May Need Updates

List docs/specs/guides that may now be stale.

Example:

```text
specs/api_contract.md - endpoint response now includes events_count.
guides/2_backend_api.md - verify section should include new smoke test.
```

If none:

```text
No documentation updates appear necessary.
```

---

## 13. Recommended Next Step

Choose one:

```text
A. Ready for reviewer approval.
B. Needs implementer fixes before reviewer approval.
C. Needs user decision before continuing.
```

Explain why.

---

## 14. Reviewer Decision

Reviewer fills this in.

```text
Decision: approved / changes requested / blocked
Reviewer:
Date:
Required changes:
Docs to update after approval:
```

---

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this report if a better approach is found.
