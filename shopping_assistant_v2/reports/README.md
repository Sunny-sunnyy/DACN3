# Implementation Reports

This folder stores phase handoff reports written by the implementer agent.

## Workflow

Recommended roles:

- DeepSeek v4 Pro in Claude Code CLI: implementer.
- Codex GPT-5.5 High: reviewer/architect.
- User: product owner and final decision maker.

## Required Flow

For each phase:

1. Implementer reads `shopping_assistant_v2/PROMPT_NEW_SESSION.md`.
2. Implementer reads the relevant plans, specs, and guides.
3. Implementer brainstorms with the user before coding.
4. Implementer performs only one approved phase or feature.
5. Implementer writes an implementation report using `TEMPLATE_IMPLEMENTATION_REPORT.md`.
6. User sends the report to the reviewer.
7. Reviewer reads the report first.
8. Reviewer reads code only when needed.
9. Reviewer returns findings: blocker, major, minor.
10. Implementer fixes issues.
11. Reviewer approves the phase.
12. After approval, reviewer updates the relevant docs/specs/guides to reflect what is now true.
13. User approves commit/push.

## Report Naming

Use:

```text
phase_<number>_<short_name>_report.md
```

Examples:

```text
phase_2_backend_api_report.md
phase_3_async_jobs_report.md
phase_4_mock_tools_report.md
```

## Reviewer Documentation Update Rule

After a phase is approved, the reviewer must update stale documentation based on the implementation report and inspected code.

The reviewer should update docs when:

- a planned item is now implemented;
- an API/schema/tool contract changed;
- a guide verify command changed;
- a phase order changed;
- a risk is resolved or newly discovered;
- a mock became real;
- a future task is no longer accurate.

Do not update docs to claim functionality is complete unless implementation and verification prove it.

## Brainstorming And Research Gate

Before implementation, coding agents must run a focused brainstorming/research pass to validate assumptions, simplify scope, and update this document if a better approach is found.
