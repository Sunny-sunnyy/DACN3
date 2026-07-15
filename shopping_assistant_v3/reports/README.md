# Implementation Reports

This folder stores implementation evidence and handoff reports for Shopping
Assistant V3.

Reports are mandatory after every implementation phase or approved milestone.
They let the reviewer inspect what changed before the project moves to the next
phase.

## Workflow

For each phase:

1. Implementer reads `gameplan.md`, architecture guides, and the current phase
   guide.
2. Implementer brainstorms with the user before coding.
3. Implementer performs only the approved scope.
4. Implementer writes a report using `TEMPLATE_IMPLEMENTATION_REPORT.md`.
5. Reviewer reads the report first.
6. Reviewer inspects code/files as needed.
7. Reviewer returns blocker/major/minor findings.
8. Implementer fixes required issues.
9. Reviewer approves or requests changes.
10. After approval, reviewer updates `gameplan.md` and relevant guides if
    implementation changed reality.
11. User decides whether to commit/push.

Do not move to the next phase until the current phase has evidence and review.

## Naming

Use:

```text
phase_<number>_<short_name>_report.md
```

Examples:

```text
phase_1_project_setup_report.md
phase_2_backend_api_and_database_report.md
phase_3_async_jobs_report.md
phase_4a_mock_tools_report.md
phase_4b_real_search_report.md
phase_4c_real_pricing_report.md
```

## Documentation Update Rule

After approval, update docs when:

- a planned item is now implemented;
- API/schema/tool behavior changed;
- verification commands changed;
- phase order changed;
- a risk was resolved or discovered;
- mock behavior became real behavior;
- a future task is no longer accurate.

Never update docs to claim functionality is complete unless implementation and
verification prove it.

