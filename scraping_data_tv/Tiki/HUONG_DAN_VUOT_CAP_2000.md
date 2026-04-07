# Huong Dan Vuot Gioi Han 2000 SP/Query

## Van de

Tiki Listing API (`/api/v2/products?category=X`) **cap ket qua o 2000 SP** (50 pages x 40 items/page).

Vi du: Sub-category "Dung cu nha bep" (1951) co **14,478 SP** nhung API chi tra ve **2000 SP**.
Nghia la mat **~86% du lieu**.

27 sub-categories bi anh huong, tong mat ~200K SP.

---

## Ket qua test thuc te (sub 1951 — Dung cu nha bep, 14,478 SP)

Test ngay 2026-04-07 voi script `step1/04_test_overcap_solutions.py`:

### Phuong an 1: Sort Rotation

**How:** Them param `sort` vao URL. Moi kieu sort tra ve tap SP khac nhau.

```
                       Query binh thuong
                       category=1951
                       -> 2000 SP (default sort)
                       
  sort=price_asc -----> 2000 SP (re nhat truoc)     -> ID moi: 116/120
  sort=price_desc ----> 2000 SP (dat nhat truoc)     -> ID moi: 120/120
  sort=newest --------> 2000 SP (moi nhat truoc)     -> ID moi: 120/120
  sort=top_seller ----> 2000 SP (ban chay nhat)      -> ID moi:   0/120  (trung voi default)
```

**Ket qua:** Chi test 3 pages dau moi sort -> merge ra **476 IDs duy nhat** (tu 5x120=600 tong cong).

**Neu chay full 50 pages moi sort:** co the lay duoc ~5,000-7,000 SP (ước tinh 30-50% trung).

| Uu diem | Nhuoc diem |
|---------|------------|
| De implement (chi them 1 param) | Trung lap cao (~30-50%) |
| Chay nhanh | Chi lay duoc ~5-7K/14K SP |
| It risk bi block | Khong dam bao coverage |

---

### Phuong an 2: Price-Range Slicing (HIEU QUA NHAT)

**How:** Them param `price=min,max` de chia 1 sub-category thanh nhieu khoang gia nho.
Moi khoang gia la 1 query rieng, moi cai toi da 2000 SP.

```
Sub 1951 (14,478 SP)
  |
  |-- price=0,50000        -> 2,000 SP  !! van OVER_CAP
  |-- price=50000,100000   -> 2,000 SP  !! van OVER_CAP
  |-- price=100000,200000  -> 2,000 SP  !! van OVER_CAP
  |-- price=200000,500000  -> 2,000 SP  !! van OVER_CAP
  |-- price=500000,1000000 -> 2,000 SP  !! van OVER_CAP
  |-- price=1000000,2000000-> 1,636 SP  OK
  |-- price=2000000,5000000-> 1,726 SP  OK
  |-- price=5000000,50M    ->   573 SP  OK
  |
  TONG REACHABLE = 13,935 SP  (96% cua 14,478 !)
```

**Van de:** 5/8 khoang gia van >2000 SP -> can chia nho hon (adaptive slicing).

Vi du chia nho khoang 0-50K thanh 0-20K va 20K-50K, tuong tu cho cac khoang khac.
Khi do co the lay duoc **100% cua 14,478 SP**.

| Uu diem | Nhuoc diem |
|---------|------------|
| Coverage cao nhat (96-100%) | Nhieu listing requests (8-20 query/sub) |
| Phu hop price prediction (trai deu gia) | Can adaptive logic khi 1 slice van >2000 |
| Khong phuc tap | Tang thoi gian listing 5-10x |

---

### Phuong an 3: Sub-Sub-Category Drilling

**How:** Goi API voi `aggregations=2` de lay danh sach sub-sub-categories (cap duoi).
Moi sub-sub nho hon -> nhieu cai <2000 SP.

```
Sub 1951 (Dung cu nha bep, 14,478 SP)
  |
  |-- 1986  Phu kien nha bep           4,136 SP  !! OVER_CAP
  |-- 53052 Noi va chao                2,247 SP  !! OVER_CAP
  |-- 23128 Dung cu chua dung thuc pham 2,169 SP  !! OVER_CAP
  |-- 8319  Dao, keo va phu kien       1,635 SP  OK
  |-- 5433  Dung cu lam banh           1,419 SP  OK
  |-- 11808 Bep nuong, vi nuong        1,402 SP  OK
  |-- 6305  Ke nha bep                 1,011 SP  OK
  |-- 68034 Bo hop com va phu kien       191 SP  OK
  |-- 23132 Thung dung gao               131 SP  OK
  |-- 1934  Am nuoc cac loai              112 SP  OK
  |-- 69962 Nap day & PK lo vi song       17 SP  OK
  |-- 70058 Giay tham dau an                8 SP  OK
  |
  9/12 sub-sub < 2000 SP (OK)
  3/12 sub-sub > 2000 SP (can chia tiep)
  TONG REACHABLE = 11,926 SP  (82%)
```

**Van de:** 3 sub-sub van >2000, can ket hop voi Price Slicing de xu ly chung.

| Uu diem | Nhuoc diem |
|---------|------------|
| Du lieu co category chi tiet hon | 3/12 van OVER_CAP |
| Nhieu sub-sub da <2000 (khong can xu ly) | Phuc tap (recursive) |
| Coverage 82% chi voi 1 cap | Can them 1 buoc scan |

---

## So sanh

| Phuong an | Reachable (test 1951) | Coverage | Do kho | Uu tien |
|-----------|----------------------|----------|--------|---------|
| Baseline (khong lam gi) | 2,000 | 14% | - | - |
| Sort Rotation | ~5,000-7,000 (uoc tinh) | 35-48% | De | 3 |
| **Price-Range Slicing** | **13,935** | **96%** | Trung binh | **1** |
| Sub-Sub Drilling | 11,926 | 82% | Kho | 2 |

---

## Khuyen nghi: Price-Range Slicing + Adaptive

Pipeline listing moi:

```
Cho moi sub-category:
  1. Query binh thuong -> neu total <= 2000: lay nhu cu (khong doi)
  2. Neu total > 2000:
     a. Chia thanh 8 khoang gia (0-50K, 50K-100K, ..., 5M-50M)
     b. Query tung khoang
     c. Neu khoang nao van >2000: chia doi khoang do (adaptive)
     d. Merge tat ca IDs, dedup
  3. Filter price (50K-50M)
  4. Lay detail nhu cu
```

Uoc tinh: tang tong listing requests tu ~2,500 len ~10,000-15,000
nhung lay duoc 96-100% SP thay vi 14%.

Thoi gian listing them: ~2-4 gio (voi delay 0.3s/request).
Detail van la bottleneck chinh: 100K SP x 0.5s = ~14 gio.

---

## File lien quan

- `step1/04_test_overcap_solutions.py` — script test (chay lai bat cu luc nao)
- `tiki_categories_report.csv` — bang danh muc voi OVER_CAP status
- `tiki_categories_report.md` — bang danh muc (Markdown)
- `tiki_scraper/scraper.py` — scraper chinh (can cap nhat listing logic)
