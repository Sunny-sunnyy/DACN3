# Scripts

Local helper scripts for Shopping Assistant V3.

Conventions:

- Scripts must be deterministic and local: no network, no model calls, no
  scraping, no secrets.
- Python scripts run via `uv run`. Shell scripts run via `bash`.

## Available Scripts

| Script | Purpose |
|---|---|
| `verify_setup.sh` | Verify the Phase 1 runtime folder structure exists. |

Usage:

```bash
bash shopping_assistant_v3/scripts/verify_setup.sh
```
