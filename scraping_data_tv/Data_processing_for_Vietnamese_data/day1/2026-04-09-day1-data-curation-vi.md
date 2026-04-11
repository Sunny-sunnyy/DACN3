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
- [x] **Task 5:** Run v1 pipeline — 120K load, 114K dedup, 110K sample, 100K/5K/5K split
- [x] **Task 6:** Push v1 to HuggingFace Hub — `SeanSunny/items_raw_tv`
- [x] **Task 7:** Category penalty applied (Thoi Trang 0.40, Nha Cua 0.60)
- [x] **Task 8:** WinMart data added (3,232 SP), CATEGORY_MAP fixed
- [x] **Task 9:** v4 config finalized: TRAIN_SIZE=110K, total=120K, HF=v4
- [x] **Task 10:** Notebook `day1_data_curation.ipynb` created
- [ ] **Task 11:** Chay notebook va push HF Hub `SeanSunny/items_raw_tv_v4`

---

## Buoc tiep theo: Day 2 — LLM rewrite

**Day 0-1 HOAN TAT (2026-04-11).** Khong can cao them data.

**Buoc tiep:**
1. Chay `day1_data_curation.ipynb` → push HF Hub v4
2. Day 2: LLM rewrite (Groq Batch API)
3. Day 3: Baseline ML
4. Day 4: DNN + Frontier LLM

**Xem prompt Day 2 tai:** `scraping_data_tv/Tiki/SESSION_HANDOFF.md` (Prompt A)

*Cap nhat: 2026-04-11 — Day 0-1 HOAN TAT. v4 config: 110K train, 120K total, HF=v4. Notebook da tao. Buoc tiep: Day 2 LLM rewrite.*

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

---

## CẬP NHẬT 2026-04-11: Re-run Day 1 v4 (thêm WinMart + Hasaki data)

### 1. Dữ liệu đầu vào

| Nguồn | Files | SP | Ghi chú |
|---|---:|---:|---|
| Tiki Scraper (111 categories) | ~239 JSONL | ~102,117 | Features dài, chất lượng tốt |
| Tiki Kaggle (6 files) | 6 JSONL | 41,603 | Features ngắn (~188 chars) |
| Hasaki | ~128 JSONL? | 11,410 | Làm Đẹp - Sức Khỏe |
| **WinMart (MỚI)** | 18 JSONL | 3,232 | Bách Hóa (FMCG), 18 categories |
| **Tổng** | **263** | **158,362** | |

### 2. Kết quả pipeline

| Bước | Kết quả | Ghi chú |
|---|---|---|
| Load + parse | ~157,722 items (8 categories) | Loại ~640 items không hợp lệ |
| EDA before dedup | 15 biểu đồ | Price avg 1,034,152 VND, median 224,000 |
| Dedup (title + full) | ~146,850 items | Loại ~10,872 (6.9%) |
| EDA after dedup | 15 biểu đồ | |
| Weighted sampling | 110,000 items | price^2 + penalty Thời Trang 0.40, Nhà Cửa 0.60 |
| Split | 100K train / 5K val / 5K test | |
| Push HF Hub | `SeanSunny/items_raw_tv_v3` | **Cần đổi tên sang v4** |

### 3. Phân phối category — So sánh v3 vs v4

#### Trước dedup (raw)

| Category | v3 (trước WinMart) | v4 (sau WinMart) | Thay đổi |
|---|---:|---:|---|
| Thời Trang | ~56,170 | 56,170 | Không đổi |
| Nhà Cửa - Đời Sống | ~33,355 | 33,355 | Không đổi |
| Điện Tử - Công Nghệ | ~22,977 | 22,977 | Không đổi |
| Làm Đẹp - Sức Khỏe | ~21,032 | 21,032 | Không đổi (Hasaki đã có từ v3) |
| **Bách Hóa** | **~4,900** | **8,137** | **+3,237 (WinMart)** |
| Mẹ và Bé | ~7,312 | 7,312 | Không đổi |
| Điện Lạnh và Gia Dụng | ~6,097 | 6,097 | Không đổi |
| Ô Tô - Xe Máy | ~2,642 | 2,642 | Không đổi |

#### Sau sampling (final dataset)

| Category | v4 Items | % | Nhận xét |
|---|---:|---:|---|
| Thời Trang | 27,851 | 25% | Penalty 0.40 hoạt động tốt (giảm từ 36% raw) |
| Nhà Cửa - Đời Sống | 27,313 | 25% | Penalty 0.60 (giảm từ 22% raw — tăng nhẹ do SP đắt) |
| Điện Tử - Công Nghệ | 20,517 | 19% | Ổn định, SP đắt nên price^2 ưu tiên |
| Làm Đẹp - Sức Khỏe | 14,113 | 13% | Tăng mạnh nhờ Hasaki (11K items) |
| Mẹ và Bé | 6,364 | 6% | Ổn |
| Điện Lạnh và Gia Dụng | 5,871 | 5% | Ổn |
| **Bách Hóa** | **5,538** | **5%** | **Tăng nhưng bị price^2 ép (xem phân tích)** |
| Ô Tô - Xe Máy | 2,433 | 2% | Category nhỏ nhất, chấp nhận |

### 4. Phân tích chi tiết

#### Bách Hóa — Mục tiêu đạt nhưng bị price^2 weighting ép

- Raw: 4,900 (v3) → **8,137** (v4) — WinMart đóng góp +3,237 items
- Sau dedup: **8,073** — gần như không mất (WinMart data ít trùng)
- Sau sampling: **5,538** — mất 31% do price^2 weighting
- **Nguyên nhân:** FMCG giá rẻ (5K-50K VND), price^2 weighting ưu tiên SP đắt tiền, nên FMCG bị gạt bớt
- **Kết luận:** Mục tiêu 7,500 SP Bach Hoa **đạt ở raw level** nhưng weighted sampling cắt xuống 5,538

#### Penalty system hoạt động ổn

- Thời Trang: 36% raw → 25% sample (penalty 0.40 hiệu quả)
- Nhà Cửa: 22% raw → 25% sample (penalty 0.60 nhưng SP đắt nên price^2 bù lại)
- Phân phối tổng thể cân đối hơn v3 (gap lớn nhất/nhỏ nhất: 11.5x vs 19.5x trước)

#### Text length vẫn bimodal

- Avg 1,742 chars (after sampling), highest 3,256
- 2 đỉnh rõ ràng: ~250 chars (Kaggle + WinMart FMCG) và ~3,000 chars (Tiki scraper)
- WinMart thêm data vào đỉnh thấp (~50-200 chars features)
- **Day 2 LLM rewrite sẽ chuẩn hóa tất cả** — không cần xử lý thêm

#### Price distribution

- Raw: avg 1,034,152 VND, median 224,000 VND
- After sampling: avg 1,413,521 VND, median 350,000 VND
- price^2 weighting đẩy median lên 56% — hoạt động đúng mục đích

### 5. Vấn đề cần quyết định

1. **HF_DATASET_NAME:** Hiện vẫn là `v3`. Nên đổi sang `v4` trước khi push.

2. **Bach Hoa bị ép bởi price^2:** 8,073 (sau dedup) → 5,538 (sau sampling). Có 2 lựa chọn:
   - **(A) Chấp nhận 5,538** — đủ để train, Day 2 LLM rewrite sẽ cải thiện chất lượng
   - **(B) Thêm category boost cho Bach Hoa** — ngược penalty, VD `"Bách Hóa": 1.5` để bù price^2

3. **TRAIN_SIZE = 100,000:** Plan đề xuất giảm xuống 80,000 nhưng code vẫn giữ 100K. Cần xác nhận.

### 6. Config hiện tại trong `day1_data_curation.py`

```python
HF_DATASET_NAME = "SeanSunny/items_raw_tv_v3"  # Cần đổi sang v4
TRAIN_SIZE = 100_000     # Plan nói 80K nhưng code giữ 100K
VAL_SIZE = 5_000
TEST_SIZE = 5_000
CATEGORY_PENALTIES = {
    "Thời Trang": 0.40,
    "Nhà Cửa - Đời Sống": 0.60,
}
```

---

*Cập nhật: 2026-04-11 20:34. Day 1 v4 re-run DONE với WinMart data. Bách Hóa tăng thành công (8,137 raw). Cần quyết định: đổi HF name v4, Bach Hoa boost, TRAIN_SIZE.*