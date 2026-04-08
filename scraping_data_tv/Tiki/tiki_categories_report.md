# Tiki Categories Report

**Cap nhat:** 2026-04-08, 20:00
**Tong categories:** 49
**Da hoan thanh:** 28/49
**Tong SP da cao:** ~23,700
**Con lai:** 21 categories (~220K uoc tinh, thuc te ~50-70K do nhieu SP bi xoa)
**Ty le SP thuc te:** ~20-80% tuy category (cong nghe thap, bach hoa/dien lanh cao)

---

## Trang thai cac categories

### DONE — 28 categories (~23,700 SP)

| ID | Category | Uoc tinh | Da cao | Trang thai |
|------:|---|-------:|-------:|:---:|
| 8129 | Linh Kien May Tinh - Phu Kien May Tinh | 12,475 | 9,638 | DONE |
| 2663 | Thiet Bi Mang | 1,447 | 835 | DONE |
| 8039 | Thiet Bi Deo Thong Minh | 1,038 | 594 | DONE |
| 28432 | Thiet Bi Thong Minh va Linh Kien | 774 | 471 | DONE |
| 8060 | Thiet Bi Luu Tru | 327 | 208 | DONE |
| 8093 | PC - May Tinh Bo | 48 | 41 | DONE |
| 8085 | Laptop | 21 | 0 | DONE |
| 5015 | Tivi | 161 | 92 | DONE |
| 3862 | May giat | 238 | 167 | DONE |
| 3865 | May lanh - May dieu hoa | 309 | 159 | DONE |
| 2328 | Tu lanh | 295 | 225 | DONE |
| 3866 | May nuoc nong | 214 | 145 | DONE |
| 3864 | May rua chen | 190 | 87 | DONE |
| 26568 | Am thanh & Phu kien Tivi | 286 | 198 | DONE |
| 8431 | Xe dap | 342 | 215 | DONE |
| 1594 | Cham soc ca nhan | 1,343 | 707 | DONE |
| 1592 | Cham soc co the | 1,030 | 579 | DONE |
| 1591 | Cham soc toc va da dau | 961 | 597 | DONE |
| 1595 | Nuoc hoa | 714 | 435 | DONE |
| 8168 | The thao - Da ngoai | 263 | 228 | DONE |
| 4421 | Do An Vat | 1,691 | 80 | DONE |
| 4422 | Gia Vi va Che Bien | 1,554 | 702 | DONE |
| 8214 | Phu Kien Dien Thoai va May Tinh Bang | 79,004 | ~5,000 | DONE |
| 8215 | Thiet Bi Am Thanh va Phu Kien | 2,508 | ~800 | DONE |
| 2306 | Dung cu lam dep | 2,670 | ~900 | DONE |
| 22998 | Do uong | 2,741 | ~900 | DONE |
| 15074 | Thuc pham Dong hop va Kho | 2,789 | ~900 | DONE |
| 5451 | Cham soc thu cung | 2,796 | 891 | DONE |

---

### TODO — 21 categories (~220K uoc tinh, thuc te ~50-70K)

| ID | Category | Uoc tinh | Trang thai | Ghi chu |
|------:|---|-------:|:---:|---|
| 2150 | Noi that | 19,569 | TODO | May thue |
| 1974 | Sua chua nha cua | 19,486 | TODO | May thue |
| 1951 | Dung cu nha bep | 14,486 | TODO | May thue |
| 7741 | Van phong pham | 13,740 | TODO | May thue |
| 24832 | Phu kien - Cham soc xe | 10,120 | TODO | May thue |
| 1973 | Trang tri nha cua | 9,908 | TODO | May thue |
| 1954 | Do dung phong an | 8,185 | TODO | May thue |
| 1884 | Do dung nha bep | 7,220 | TODO | May thue |
| 1966 | Do dung va thiet bi nha tam | 6,750 | TODO | May thue |
| 5250 | Do choi | 6,492 | TODO | May thue |
| 2223 | Ngoai troi & san vuon | 5,967 | TODO | May thue |
| 975 | Phu kien thoi trang nu | 5,797 | TODO | May thue |
| 2015 | Den & thiet bi chieu sang | 5,724 | TODO | May thue |
| 28670 | Phu kien may tinh va Laptop | 4,960 | TODO | May ca nhan |
| 1946 | Thiet bi gia dinh | 4,772 | TODO | May ca nhan |
| 1582 | Cham soc da mat | 4,318 | TODO | May ca nhan |
| 8370 | Mat kinh | 3,749 | TODO | May ca nhan |
| 12884 | Thiet Bi Van Phong - Ngoai Vi | 3,542 | TODO | May ca nhan |
| 27550 | Phu kien thoi trang nam | 2,911 | TODO | May ca nhan |
| 11601 | Do dung cho be | 2,832 | TODO | May ca nhan |
| 11601 | Do dung cho be | 2,832 | TODO | May ca nhan |
| 27550 | Phu kien thoi trang nam | 2,911 | TODO | May ca nhan |

---

## Lenh chay

```bash
# Chay 1 category
uv run scraping_data_tv/Tiki/run_scraper.py --category <ID> --workers 3

# Chay tat ca (tu dong skip DONE)
uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 5

# Xem trang thai
uv run python -c "
import json
from pathlib import Path
for f in sorted(Path('scraping_data_tv/Tiki/checkpoints').glob('*.json')):
    d = json.loads(f.read_text())
    status = 'DONE' if d.get('complete') else f'{len(d[\"done_ids\"])} SP (dang cao)'
    print(f'{f.stem}: {status}')
"
```

---

*Cap nhat: 2026-04-08 20:00 — 28/49 complete, ~23,700 SP. May thue + may ca nhan chay song song.*
