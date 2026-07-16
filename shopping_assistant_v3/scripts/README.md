# Scripts

Các local helper scripts cho Shopping Assistant V3.

Conventions:

- Scripts phải deterministic và local: không network, không model calls, không
  scraping, không secrets.
- Python scripts chạy qua `uv run`. Shell scripts chạy qua `bash`.

## Scripts Hiện Có

| Script | Mục đích |
|---|---|
| `verify_setup.sh` | Xác minh cấu trúc runtime folder của Phase 1 tồn tại. |

Cách dùng:

```bash
bash shopping_assistant_v3/scripts/verify_setup.sh
```
