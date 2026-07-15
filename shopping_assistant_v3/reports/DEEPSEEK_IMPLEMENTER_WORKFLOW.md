# DeepSeek Implementer Workflow

## Purpose

Use this file when the user assigns the current session to DeepSeek or another
implementation agent for Shopping Assistant V3.

The implementer builds the approved phase or milestone, runs verification, and
writes an implementation report. The implementer does not approve its own work
and does not commit or push unless Codex has approved that action.

## Required Context

Before implementing, read:

```text
shopping_assistant_v3/PROMPT_NEW_SESSION.md
shopping_assistant_v3/reports/DEEPSEEK_IMPLEMENTER_WORKFLOW.md
shopping_assistant_v3/reports/PROJECT_STATUS.md
shopping_assistant_v3/gameplan.md
shopping_assistant_v3/guides/architecture.md
shopping_assistant_v3/guides/agent_architecture.md
shopping_assistant_v3/reports/README.md
shopping_assistant_v3/reports/TEMPLATE_IMPLEMENTATION_REPORT.md
the relevant phase guide
relevant Codex review feedback, if resubmitting fixes
```

Also run:

```bash
git status --short
```

Preserve unrelated changes. Do not reset, delete, stage, commit, push, or
overwrite files outside the approved scope.

## Responsibilities

The implementer must:

- implement only the user-approved phase or milestone scope;
- follow the current phase guide and V3 architecture contracts;
- use mocks and fixtures by default;
- run the smallest relevant verification first;
- perform a self-check for security, data safety, reliability, and performance
  before handing work to Codex;
- write or update the implementer's own report in
  `shopping_assistant_v3/reports/`;
- respond to Codex feedback by changing code/docs and the implementer's own
  report as needed.

The implementer must not:

- edit Codex review files;
- update `PROJECT_STATUS.md`;
- update `gameplan.md` for routine status;
- commit or push without Codex approval;
- modify `segment4/` or `shopping_assistant_v2/` unless explicitly approved;
- run live Amazon/BestBuy scraping, paid model calls, AWS/Terraform/deploy
  commands, or dependency installs without explicit approval;
- read or print secrets from `.env`, credentials, keys, tokens, auth files, or
  `terraform.tfvars`.

## Implementation Report Rule

After each approved phase or milestone, write the implementer report using:

```text
shopping_assistant_v3/reports/TEMPLATE_IMPLEMENTATION_REPORT.md
```

Naming examples:

```text
shopping_assistant_v3/reports/phase_2_backend_api_and_database_report.md
shopping_assistant_v3/reports/phase_4a_mock_tools_report.md
```

The report must state:

- exact scope implemented;
- files created;
- files modified;
- commands run;
- tests run;
- verification evidence;
- known issues;
- deviations from the guide;
- whether any real network, scraping, model, deploy, or secret access happened.

## Mandatory Self-Check Before Handoff

Before saying a phase or milestone is ready for Codex review, the implementer
must check the changed scope for:

- security: no secrets are read, printed, logged, committed, or exposed through
  API responses; no live scraping, paid model calls, AWS/Terraform/deploy, or
  new network access happened unless the user explicitly approved it;
- data safety: persisted payloads, result payloads, URLs, user messages,
  tool/model errors, and internal exceptions are stored and returned only in
  intentional safe forms; user/API-visible errors are sanitized;
- reliability: job/status transitions cannot get stuck in the approved flow;
  idempotency and failure paths are tested; audit/log records include `job_id`
  where the guides require it;
- performance: the implementation does not add obvious avoidable slowness,
  unbounded work, uncontrolled threads, repeated expensive calls, or polling
  loops without documenting the local-MVP limitation and risk;
- tests: default tests use mocks/fixtures and do not require secrets, live
  scraping, paid model calls, AWS, Terraform, deployment, or external services.

The implementer report must include a short note for this self-check. If a risk
is accepted as local-MVP behavior, list it under `Known Issues` with severity
and explain why it does not block the current phase.

## Responding To Codex Feedback

When Codex writes a review file:

1. Read the Codex review file.
2. Fix every `blocker` and `major` finding unless the user explicitly changes
   scope.
3. Fix `minor` findings when they are cheap and local.
4. Update the implementer's report with:
   - what changed after review;
   - new commands/tests run;
   - remaining known issues.
5. Do not edit the Codex review file.
6. Hand the work back to Codex for another review.

## Commit And Push Rule

The implementer may inspect git status but must not commit or push by default.

If a commit or push seems necessary, stop and ask the user to have Codex review
and approve the action.
