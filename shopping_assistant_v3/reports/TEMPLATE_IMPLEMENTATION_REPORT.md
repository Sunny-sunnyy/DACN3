# Implementation Report Template

## Phase

`<phase number and name>`

Implementer:

Date:

Branch:

Commit reviewed: `<commit hash or "not committed yet">`

## Summary

State exactly what was implemented.

Be explicit if behavior is mocked, fixture-based, partial, or real.

## Files Created

```text
path/to/file - purpose
```

## Files Modified

```text
path/to/file - what changed and why
```

## Commands Run

List exact commands.

```bash
uv run pytest ...
npm run ...
curl ...
```

For each command, include pass/fail and important output summary.

## Tests Run

List automated tests and result.

If tests were not run, explain why.

## Verification Evidence

Describe manual checks and evidence.

Examples:

- Created a chat job through API.
- Confirmed status moved from `pending` to `completed`.
- Confirmed result payload matched the phase guide.
- Confirmed logs include `job_id`.
- Confirmed no real network/model call was made.

## Known Issues

Classify each item:

- Blocker
- Major
- Minor

If none, write:

```text
No known issues.
```

## Deviations From Guide

For each deviation:

```text
Guide expectation:
Actual implementation:
Reason:
Should docs be updated? yes/no
```

If none, write:

```text
No intentional deviations.
```

## Suggested Doc Updates

List docs/guides that may now be stale.

Examples:

```text
gameplan.md - update Current Phase Status.
guides/2_backend_api_and_database.md - verify command changed.
```

If none, write:

```text
No documentation updates appear necessary.
```

## Reviewer Checklist

Reviewer should inspect:

- Scope stayed within the approved phase.
- No `segment4/` files changed unless explicitly approved.
- No `shopping_assistant_v2/` files changed.
- No secrets were read, printed, or committed.
- Default tests do not call paid APIs or live scraping.
- API/schema/tool contracts match the relevant guide.
- Failure paths store safe errors.
- Logs/audit events include `job_id` where required.
- Docs that changed reality are updated after approval.

Reviewer decision:

```text
Decision: approved / changes requested / blocked
Reviewer:
Date:
Required changes:
Docs to update after approval:
```

