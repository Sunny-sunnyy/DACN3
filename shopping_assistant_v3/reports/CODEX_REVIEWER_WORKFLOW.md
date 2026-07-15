# Codex Reviewer Workflow

## Purpose

Use this file when the user assigns the current session to Codex as the reviewer
and gatekeeper for Shopping Assistant V3.

Codex is not the default implementer. Codex reviews what the implementer
submitted, writes review feedback, approves or blocks phase movement, updates
the project status after approval, then commits and pushes the approved unit
when requested or when the workflow explicitly calls for it.

## Required Context

Before reviewing, read:

```text
shopping_assistant_v3/PROMPT_NEW_SESSION.md
shopping_assistant_v3/reports/CODEX_REVIEWER_WORKFLOW.md
shopping_assistant_v3/reports/PROJECT_STATUS.md
shopping_assistant_v3/gameplan.md
shopping_assistant_v3/guides/architecture.md
shopping_assistant_v3/guides/agent_architecture.md
shopping_assistant_v3/reports/README.md
shopping_assistant_v3/reports/TEMPLATE_IMPLEMENTATION_REPORT.md
the relevant phase guide
the implementer's phase or milestone report
```

Also run:

```bash
git status --short
```

Preserve unrelated user or implementer changes. Do not reset, delete, stage, or
overwrite unrelated files.

## Responsibilities

Codex must:

- review the implementer's report and the files it claims changed;
- inspect relevant code, docs, tests, and verification evidence;
- write a separate Codex review file in `shopping_assistant_v3/reports/`;
- ask for corrections when findings block approval;
- update `PROJECT_STATUS.md` only after approval;
- commit and push the complete approved unit when the phase or milestone is
  accepted.

Codex may make small finalization edits only when they are required for
approval or when the user explicitly asks. Examples:

- update `PROJECT_STATUS.md`;
- fix a status or governance doc that Codex owns;
- make a narrow documentation correction needed to finalize approval.

Codex must not:

- edit the implementer's report file;
- act as the phase implementer by default;
- modify `segment4/` or `shopping_assistant_v2/` unless explicitly approved;
- update `gameplan.md` for routine phase status;
- run live scraping, paid model calls, deploy commands, or dependency installs
  without explicit approval;
- read or print secrets from `.env`, credentials, keys, tokens, auth files, or
  `terraform.tfvars`.

## Review File Naming

For each phase or milestone, write:

```text
shopping_assistant_v3/reports/phase_<id>_<short_name>_codex_review.md
```

Examples:

```text
shopping_assistant_v3/reports/phase_2_backend_api_and_database_codex_review.md
shopping_assistant_v3/reports/phase_4a_mock_tools_codex_review.md
```

## Review Decision Levels

Use exactly one decision:

- `approved` - the phase or milestone can be committed and the project may move
  to the next allowed phase.
- `changes_requested` - implementation is close, but required fixes remain.
- `blocked` - review cannot continue or the implementation violates a hard gate.

Use finding severity:

- `blocker` - must be fixed before any approval.
- `major` - must be fixed before approval unless the user explicitly accepts
  the risk.
- `minor` - should be fixed, but Codex may approve if it does not affect phase
  correctness.

## Review File Structure

Use this structure:

```markdown
# Codex Review: Phase <id> <name>

Decision: approved / changes_requested / blocked
Reviewer: Codex
Date: YYYY-MM-DD
Implementer report: <path>

## Summary

## Findings

- blocker/major/minor: <file:line if available> - <finding>

If no findings:

No blocker or major findings.

## Verification

Commands run and important results.

## Scope Check

State whether scope stayed inside the approved phase or milestone.

## Required Changes

Only for `changes_requested` or `blocked`.

## Approval Notes

Only for `approved`.
```

## Approval And Commit Rule

After approval, the commit should include the complete reviewed unit:

- implementation files for the phase or milestone;
- the implementer's report;
- Codex's review file;
- `PROJECT_STATUS.md`;
- any approved docs updates required to keep current status accurate.

Do not include unrelated untracked files.

Before commit:

```bash
git status --short
git diff --cached --name-only
```

After commit:

```bash
git push
```

Report the commit hash and any unrelated remaining worktree changes.

