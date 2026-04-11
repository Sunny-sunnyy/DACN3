# Day 1: Data Curation (Vietnamese) — Implementation Log

**Ngay:** 2026-04-09
**Trang thai:** HOAN THANH — da push len HuggingFace Hub
**Branch:** `feature/data-preprocessing-vi`
**HuggingFace:** `SeanSunny/items_raw_tv`

---

## Ket qua thuc hien

### Pipeline da chay thanh cong

| Buoc | Mo ta | Ket qua |
|---|---|---|
| Load | 54 JSONL files (48 scraper + 6 Kaggle) | 120,528 items |
| Clean | 9-step Vietnamese cleaning pipeline | Loc gia (1K-50M VND), min 50 chars, NFC, emoji, SKU, HTML entities |
| Dedup | Dedup by title + dedup by full text | 114,778 items (mat 5,750 = 4.8%) |
| EDA | 15 bieu do (before dedup, after dedup, after sampling) | Xem phan tich ben duoi |
| Weighted sampling | price^2 weighting, khong co category penalty | 110,000 items |
| Split | Stratified shuffle | 100K train / 5K val / 5K test |
| Push | HuggingFace Hub | `SeanSunny/items_raw_tv` |

### Files da tao

| File | Trang thai |
|---|---|
| `pricer_vi/__init__.py` | DONE |
| `pricer_vi/items.py` | DONE — Pydantic Item model (VND), push/load HF Hub |
| `pricer_vi/parser.py` | DONE — 9-step Vietnamese cleaning, parse function |
| `day1_data_curation.py` | DONE — Full pipeline script |
| `day1_data_curation.ipynb` | DONE — Notebook da chay, co output |
| `output/` | DONE — 15 bieu do EDA (PNG) |

### Thong ke du lieu (sau dedup, truoc sampling)

| Chi tieu | Gia tri |
|---|---|
| Tong items | 114,778 |
| Price avg | 1,145,771 VND |
| Price median | 232,000 VND |
| Price range | 1,000 - 50,000,000 VND |
| Text length avg | 1,426 chars |
| Text length max | 3,256 chars |
| Categories | 14 |

### Thong ke du lieu (sau sampling)

| Chi tieu | Gia tri |
|---|---|
| Tong items | 110,000 |
| Price avg | 1,194,877 VND (tang nhe do price^2 weighting) |
| Price median | 250,000 VND |
| Train / Val / Test | 100,000 / 5,000 / 5,000 |

### Phan phoi category (sau sampling, chua co penalty)

| Category | Items | % |
|---|---|---|
| Thoi Trang | 32,759 | 30% |
| Nha Cua - Doi Song | 25,639 | 23% |
| Laptop - May Vi Tinh - Linh Kien | 12,548 | 11% |
| Thiet Bi So - Phu Kien So | 10,090 | 9% |
| Lam Dep - Suc Khoe | 5,873 | 5% |
| Do Choi - Me & Be | 4,463 | 4% |
| Dien Gia Dung | 4,581 | 4% |
| Phu kien thoi trang | 4,519 | 4% |
| Bach Hoa Online | 4,359 | 4% |
| Phu Kien thoi trang | 2,441 | 2% |
| Nha Sach Tiki | 1,670 | 2% |
| O To - Xe May - Xe Dap | 1,058 | 1% |
| Dien Tu - Dien Lanh | 1,058 | 1% |

---

## Phan tich EDA

### Diem manh

1. **Price distribution tot** — log-scale hinh chuong, peak 100K-300K VND. Price^2 weighting day SP dat len thanh cong.
2. **14 categories da dang** — tu dien tu, thoi trang, nha cua, den bach hoa, lam dep, do choi.
3. **Dedup hieu qua** — 4.8% trung lap, hop ly cho 54 files tu 2 nguon khac nhau.
4. **Price vs text length** — khong tuong quan tuyen tinh, giong tieng Anh. Model phai hoc tu noi dung, khong phai do dai.

### Van de can luu y

1. **Text length bimodal** — 2 dinh ro rang: ~200-300 chars (Kaggle data) va ~800-3200 chars (scraper data). Nguyen nhan: Kaggle features ngan (~188 chars), scraper features dai (3-5K chars, cat o 3000). **Khong can sua** — Day 2 LLM rewrite se chuan hoa tat ca thanh ~200-400 chars summary.

2. **Thoi Trang chiem 30%** — qua lon so voi phan phoi deu (~7%/category). Du lieu Kaggle (41K SP thoi trang) co chat luong thap hon scraper (features ngan, brand la ten the loai chung). **Can penalize** — xem phan quyet dinh ben duoi.

3. **Nha Cua - Doi Song chiem 23%** — hoi cao nhung du lieu scraper chat luong tot. Co the penalize nhe (0.7).

### So sanh voi du lieu tieng Anh

| Chi tieu | Tieng Anh (Amazon) | Tieng Viet (Tiki+Kaggle) |
|---|---|---|
| Raw data | 2,933,577 | 120,528 |
| Sau dedup | 2,887,890 (1.5% trung) | 114,778 (4.8% trung) |
| Sampling | 820,000 | 110,000 |
| Categories | ~30 | 14 |
| Price range | $0.50-$999.49 | 1K-50M VND |
| Category penalty | Automotive 0.05, Tools 0.5 | Chua ap dung |
| Text length | Dong deu (1 nguon) | Bimodal (2 nguon) |

**Ket luan:** Du lieu VN nho hon 24x nhung 110K la du cho fine-tune LLM. Chat luong pipeline tuong duong tieng Anh. Van de chinh la mat can bang category va bimodal text length — ca hai se duoc giai quyet (penalty + LLM rewrite).

---

## Quyet dinh con treo

### Category penalty — CAN QUYET DINH TRUOC KHI CHUYEN DAY 2

**De xuat:**
```python
CATEGORY_PENALTIES = {
    "Thoi Trang": 0.4,          # 30% -> ~15%
    "Nha Cua - Doi Song": 0.7,  # 23% -> ~17%
}
```

**Ly do:**
- Thoi Trang 30% qua nhieu, model se bi bias
- Kaggle data chat luong thap hon (features ngan, brand chung)
- Tieng Anh penalty Automotive 0.05 (manh hon nhieu)
- Penalty 0.4 giam Thoi Trang ve ~15%, van giu du data

**Neu bat penalty:** Can re-run pipeline (day1_data_curation.py) va re-push len HF Hub.

---

## Checklist hoan thanh

- [x] **Task 1:** Create pricer_vi/items.py — Pydantic Item model
- [x] **Task 2:** Create pricer_vi/parser.py — 9-step Vietnamese cleaning
- [x] **Task 3:** Test parser on real data — OK
- [x] **Task 4:** Create day1_data_curation.py — Full pipeline script
- [x] **Task 5:** Run full pipeline — 120K load, 114K dedup, 110K sample, 100K/5K/5K split
- [x] **Task 6:** Create day1_data_curation.ipynb — Notebook da chay, co output
- [x] **Task 7:** Push to HuggingFace Hub — `SeanSunny/items_raw_tv`
- [ ] **(Pending)** Quyet dinh va ap dung category penalty, re-run neu can

---

## Buoc tiep theo: Day 0 — Thu thap them du lieu

**Quyet dinh (2026-04-10):** Cao them du lieu truoc khi chuyen Day 2.

**Ly do:** 9 categories muc tieu, moi cat >= 10K. Hien tai 3 categories < 5K (Dien Lanh 1K, O To 2.4K, Bach Hoa 4.4K).

**Thu tu uu tien:**
1. **Tiki** (73 categories chua cao) — da co scraper, chi them config
2. **Scraper co san** (Hasaki, BiboMart, CoopMart...) — test + convert CSV→JSONL
3. **Scraper moi** (TGDD, FPT, Meta.vn) — viet tu dau

**Sau khi co du data:** Re-run Day 1 pipeline voi 9 categories, penalties, TRAIN_SIZE=80K.

**Chi tiet:** Xem `plan_data_preprocessing_vi.md` (Day 0).

---

## Prompt cho session moi (Day 0)

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Data_processing_for_Vietnamese_data/plan_data_preprocessing_vi.md" — plan chi tiet (Day 0-4), 9 categories muc tieu, danh sach Tiki categories can them
2. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai hien tai
3. "scraping_data_tv/Tiki/tiki_scraper/config.py" — 49 categories da cao
4. "scraping_data_tv/Tiki/tiki_scraper/scraper.py" — pipeline scraper hien tai
5. "scraping_data_tv/e-commerce-sites-scraping/" — code scraper co san (Hasaki, BiboMart, CoopMart...)
6. "scraping_data_tv/Data_processing_for_Vietnamese_data/day1/2026-04-09-day1-data-curation-vi.md" — ket qua Day 1 (EDA, phan tich)

Buoc tiep: Them 73 Tiki categories vao config.py, chay scraper. Sau do test scraper co san (Hasaki, BiboMart...).
Hay hoi toi nhung cau hoi can thiet.
```

*Cap nhat: 2026-04-10 — Day 1 DONE. EDA reviewed. Chuyen sang Day 0 (thu thap them du lieu) truoc khi re-run Day 1.*

---

## CẬP NHẬT 2026-04-10: Hoàn tất thu thập Tiki & Re-run Day 1 Pipeline

### 1. Trạng thái thu thập dữ liệu Tiki (ĐÃ HOÀN TẤT)
- Chạy scraper thành công 111/113 categories (thu được **102,117 sản phẩm** thô).
- Tích hợp thêm dataset Kaggle (**41,603 sản phẩm**).
- Tổng data Raw đạt **143,263 sản phẩm**. 
- Quyết định **không cào thêm** 3 categories còn sót lại của Tiki vì số lượng quá ít (~150 SP), không đáng kể.

### 2. Phân tích & Xử lý thành công Data Imbalance và lỗi Category "Root"
- Dataset Kaggle có hơn 41k dữ liệu mang category là "Root" hoặc sub-category quá chi tiết. Đã map toàn bộ 100% dữ liệu Kaggle này về danh mục "Thời Trang".
- Bóp gọn 168 parent categories nhỏ lẻ thô thành **8 categories** chuẩn.
- Áp dụng các ngoại lệ (Override) linh hoạt theo đúng Business Logic: Đưa *Thể thao* vào *Nhà Cửa - Đời Sống*, *Quà lưu niệm* vào *Mẹ và Bé*, v.v.

### 3. Nhận xét sau khi Re-run `day1_data_curation.py`
- **Deduplication:** Xử lý mất ~6,700 dòng dữ liệu trùng lặp, giữ lại tập 136,545 sản phẩm sạch.
- **Weighted Sampling (90,000 SP - 80k train / 5k val / 5k test):** Hệ thống Penalty hoạt động **cực kỳ xuất sắc**:
  - "Thời Trang" (nhận mức phạt 0.35) đã ép dữ liệu giảm mạnh từ 56,170 (39.2% RAW) xuống mức cân bằng 21,659 (24.1% Valid). 
  - "Nhà Cửa - Đời Sống" (nhận mức phạt 0.50) được duy trì hợp lý ở mức 24,054 (26.7%).
  - Các danh mục còn lại (Điện tử, Làm đẹp, Mẹ và Bé...) được bảo toàn lượng phân bố một cách lý tưởng.
- Dataset cuối cùng hoàn toàn sạch sẽ, cân xứng, sẵn sàng đẩy lên Hub bản V2 (`SeanSunny/items_raw_tv_v2`).

### 4. Kết quả biểu đồ EDA (`output/`)
- Mọi quan sát từ `01_before_dedup`, `02_after_dedup` cho đến `03_after_sampling` trực quan xác định biểu đồ Bar Chart và Pie Chart đã đi từ trạng thái "biến dạng" (Thời trang chiếm gần một nửa tròn xoe) sửa về trạng thái phẳng (flat/balanced) hơn nhiều.


## Cần cào thêm dữ liệu từ các trang khác như Hasaki, BiboMart, CoopMart... để tăng số lượng dữ liệu cho các danh mục còn thiếu. 