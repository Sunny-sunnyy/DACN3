# Don dep thu muc segment4/

**Date:** 2026-04-05

---

## XOA (git rm -r)

```bash
# 1. ghi_chu/ — snapshot cu (2026-03-02), toan bo da co trong git history
git rm -r segment4/ghi_chu/

# 2. test cu trong test_chuc_nang/ — trung lap voi ghi_chu/, da co git history
git rm -r segment4/test_chuc_nang/test_amazon/
git rm -r segment4/test_chuc_nang/test_chuc_nang_v2/

# 3. sandbox/ — chi co deals.md (1KB), khong dung
git rm -r segment4/sandbox/
```

## MOVE vao khong_su_dung/ (git mv)

```bash
# 4. Notebook thuc nghiem cu (2026-02-03), khong ai import
git mv segment4/experiment-preprocessing.ipynb segment4/khong_su_dung/

# 5. BestBuy Scanner Agent — dung Brave MCP, da thay bang curl_cffi + APIs
#    Khong con duoc import boi bat ky file active nao
git mv segment4/price_agents/bestbuy_scanner_agent.py segment4/khong_su_dung/
```

## KHONG THAY DOI

| File/Dir | Ly do giu |
|----------|-----------|
| `price_agents/` (17 files con lai) | Active agents |
| `bestbuy_untils/` (4 files) | Active utilities |
| `bestbuy_untils/clarification_agent.py` | Van duoc import boi `gradio_helpers.py` dong 20 |
| `test_chuc_nang/plan_fix.md` | Plan fix dang active |
| `test_chuc_nang/fix_bestbuy/` | Code + notebooks buoc 1 |
| `khong_su_dung/` (11 files cu) | Da duoc sap xep |
| `mo_ta_du_an/` | Documentation |
| `products_vectorstore/` | ChromaDB data |

## COMMIT

```bash
git add -A
git commit -m "Don dep: xoa ghi_chu/, test cu, sandbox. Move experiment notebook + bestbuy_scanner_agent vao khong_su_dung/"
git push origin claudedev
```

## KET QUA

Truoc: 11 thu muc, ~160 files
Sau: 7 thu muc, ~50 active files + 13 files trong khong_su_dung/
