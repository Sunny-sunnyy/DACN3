# Xây Dựng Dữ Liệu Huấn Luyện: Từ Thu Thập đến Data Augmentation

**Dự án:** Ước giá sản phẩm tiếng Việt (DACN3)
**Mô hình:** QLoRA fine-tune Qwen3.5-4B-Base
**Ngày hoàn thành:** 2026-04-29

---

## Tổng Quan Pipeline

Toàn bộ quá trình xây dựng dữ liệu trải qua 4 giai đoạn nối tiếp nhau:

```
[4 nguồn web]         [Day 1]              [Day 2]             [Bước chuẩn bị]
Tiki + Kaggle    →   Làm sạch        →   LLM viết        →   Lọc giá &       →  items_prompts_tv_3
Hasaki + WinMart     + Sampling          Summary 5 dòng      build prompt        (85,727 mẫu)
158,362 SP thô       110,000 SP          items_tv_v6                                    │
                     items_raw_tv_v6                                                    │
                                                                                        ▼
                                                                               [Data Augmentation]
                                                                               LLM paraphrase
                                                                               × 1–5 lần/bucket
                                                                                        │
                                                                                        ▼
                                                                               items_prompts_tv_4
                                                                               (269,112 mẫu)
```

---

## Giai Đoạn 1 — Thu Thập Dữ Liệu (Day 1)

### 1.1 Nguồn dữ liệu

| Nguồn | Phương pháp | Số sản phẩm | Đặc điểm |
|---|---|---|---|
| Tiki (scraper) | Crawl 111/113 danh mục | 102,117 | Mô tả dài 2K–3K ký tự, chất lượng cao |
| Kaggle | CSV công khai | 41,603 | Mô tả ngắn ~188 ký tự, chủ yếu Thời Trang |
| Hasaki | Crawl 128/130 danh mục | 11,410 | Tập trung Làm Đẹp – Sức Khỏe |
| WinMart | Crawl 18 danh mục | 3,232 | Hàng FMCG giá thấp 5K–50K VND |
| **Tổng** | | **158,362** | |

Tất cả dữ liệu thô được lưu dưới dạng JSONL, mỗi sản phẩm gồm: `title`, `category`, `price`, `full` (toàn bộ mô tả gốc), `brand`.

### 1.2 Pipeline làm sạch (9 bước)

```
Dữ liệu thô  →  [1] NFC normalize  →  [2] Lọc HTML entities  →  [3] Xóa emoji
             →  [4] Xóa SKU/mã SP   →  [5] Chuẩn hóa khoảng trắng
             →  [6] Lọc giá 1K–50M VND  →  [7] Lọc tối thiểu 50 ký tự
             →  [8] Dedup theo title  →  [9] Dedup theo full text
```

**Kết quả dedup:** 158,362 → 146,850 sản phẩm (loại bỏ 11,512 = 7.3% trùng lặp).

### 1.3 Weighted Sampling — Cân bằng dữ liệu

**Vấn đề:** Phân phối category mất cân bằng nặng — Thời Trang chiếm 38% raw (chủ yếu từ Kaggle, chất lượng thấp), Bách Hóa bị ép vì giá quá rẻ.

**Giải pháp:** Kết hợp hai cơ chế:

- **price² weighting:** Ưu tiên sản phẩm giá cao (giúp model học được khoảng giá đa dạng).
- **Category penalty:** Giảm tỷ lệ các nhóm quá nhiều.

```python
CATEGORY_PENALTIES = {
    "Thời Trang":          0.40,  # 38% raw → 25% final
    "Nhà Cửa - Đời Sống":  0.60,  # 22% raw → 25% final
}
```

**Kết quả sau sampling:**

| Category | Trước (raw %) | Sau (final %) |
|---|---|---|
| Thời Trang | 38% | 25% |
| Nhà Cửa - Đời Sống | 22% | 25% |
| Điện Tử - Công Nghệ | 15% | 19% |
| Làm Đẹp - Sức Khỏe | 14% | 13% |
| Mẹ và Bé | 5% | 6% |
| Điện Lạnh - Gia Dụng | 4% | 5% |
| Bách Hóa | 5% | 5% |
| Ô Tô - Xe Máy | 2% | 2% |

**Dataset đầu ra:** `SeanSunny/items_raw_tv_v6` — 110,000 sản phẩm (100K train / 5K val / 5K test).

---

## Giai Đoạn 2 — LLM Preprocessing: Chuẩn Hóa Mô Tả (Day 2)

### 2.1 Vấn đề cần giải quyết

Dữ liệu gốc có hai vấn đề:
1. **Bimodal text length:** Kaggle/WinMart ~200 ký tự; Tiki scraper ~3,000 ký tự — không đồng đều.
2. **Chất lượng không nhất quán:** Mô tả gốc có nơi rất dài (lặp từ, liệt kê thừa), có nơi quá ngắn.

### 2.2 Giải pháp: LLM viết tóm tắt chuẩn hóa

Dùng **Groq Batch API** với model `gpt-oss-20b` để viết lại mỗi sản phẩm thành định dạng 5 dòng cố định:

```
Tiêu đề:    [giữ nguyên từ data gốc — chính xác 100%]
Danh mục:   [giữ nguyên từ data gốc — chính xác 100%]
Thương hiệu:[giữ nguyên từ data gốc — chính xác 100%]
Mô tả:      [LLM tạo — 1 câu súc tích]
Thông số:   [LLM tạo — 1 câu về tính năng nổi bật]
```

> **Thiết kế quan trọng:** LLM chỉ phụ trách 2 dòng cuối, 3 dòng đầu lấy từ data gốc. Điều này đảm bảo thông tin danh mục/thương hiệu luôn chính xác, chỉ phần mô tả mới được "tổng hợp".

**Ví dụ thực tế:**

```
Tiêu đề: Ổ khóa đĩa hợp kim siêu chịu lực
Danh mục: Phụ kiện xe máy
Thương hiệu: PaKaSa
Mô tả: Ổ khóa đĩa chống trộm, cốt inox 100% và chất liệu hợp kim siêu chịu lực, kèm 2 chìa khóa.
Thông số: Khả năng chịu lực cao, không bị gỉ, cấu trúc ruột bi, bảo hành 6 tháng.
```

### 2.3 Quy trình xử lý batch

```
110,000 sản phẩm  →  Chia thành 120 batch (1,000 items/batch)
                  →  Upload JSONL lên Groq  →  Submit batch jobs
                  →  Poll status mỗi 60s   →  Download kết quả
                  →  Build summary 5 dòng  →  Push HF Hub
```

| Thông số | Giá trị |
|---|---|
| Tổng items xử lý | 120,000 |
| Batch API model | `openai/gpt-oss-20b` |
| Số batch | 120 |
| Avg tokens/item | ~640 input + 97 output |
| Chi phí ước tính | ~$9–10 |
| Thời gian tổng | ~20–30 phút |

**Dataset đầu ra:** `SeanSunny/items_tv_v6` — 110,000 sản phẩm, cột `summary` 5 dòng.

---

## Giai Đoạn 3 — Xây Dựng Dataset Fine-Tuning (items_prompts_tv_3)

### 3.1 Lọc giá

Chỉ giữ sản phẩm có `price <= 1,000,000 VND` (tập trung vào hàng tiêu dùng phổ thông, loại outlier đắt tiền).

| Split | Trước lọc | Sau lọc | Loại bỏ |
|---|---|---|---|
| Train | 110,000 | 85,727 | 24,273 (22%) |
| Val | 5,000 | 3,926 | 1,074 (21%) |
| Test | 5,000 | 3,872 | 1,128 (22%) |

### 3.2 Định dạng prompt/completion

Mỗi sản phẩm được chuyển thành cặp (prompt, completion) cho LLM fine-tuning:

```
[PROMPT]
Sản phẩm này có giá bao nhiêu ?
Tiêu đề: Ổ khóa đĩa hợp kim siêu chịu lực
Danh mục: Phụ kiện xe máy
Thương hiệu: PaKaSa
Mô tả: Ổ khóa đĩa chống trộm, cốt inox 100%...
Thông số: Khả năng chịu lực cao, bảo hành 6 tháng.

Giá là:

[COMPLETION]
60
```

> **Lý do completion = `round(price / 1000)`:** Đưa giá về đơn vị nghìn đồng giúp model generate số ngắn (2–4 chữ số) thay vì số 6–7 chữ số, giảm max_new_tokens từ ~8 xuống còn 4 token.

**Dataset đầu ra:** `SeanSunny/items_prompts_tv_3`

| Split | Rows | Price mean | Price median |
|---|---|---|---|
| Train | 85,727 | ~450K VND | ~250K VND |
| Val | 3,926 | ~450K VND | ~250K VND |
| Test | 3,872 | ~450K VND | ~250K VND |

---

## Giai Đoạn 4 — Data Augmentation (items_prompts_tv_4)

### 4.1 Tại sao cần augmentation?

Sau khi train Qwen3.5-4B với 85,727 mẫu (v3), kết quả:
- RMSLE = **0.4426** — chưa đạt mục tiêu < 0.38
- MAE = 80,100 VND — gần bằng Day4 v8 (79,853 VND)

**Phân tích failure modes:**

| Lỗi | Ví dụ | Nguyên nhân |
|---|---|---|
| Bỏ qua số định lượng trong title | "0.6ml" → predict 600K thay vì 60K | Thiếu mẫu sản phẩm mini size |
| Anchor theo category mean | Tất cả tui xách → 100–300K bất kể chi tiết | Distribution train không đủ đa dạng |
| Under-predict outlier > 500K | LEGO 999K → predict 259K | < 5% mẫu train có giá > 500K |

**Kết luận:** Vấn đề chính là **thiếu dữ liệu đa dạng**, đặc biệt ở hai đầu phân phối giá. Augmentation là đòn bẩy lớn nhất (benchmark tiếng Anh đạt MAE $39 với 800K mẫu so với 110K của ta).

### 4.2 Chiến lược augmentation: Price Bucket Multiplier A5

Ý tưởng: **tăng số lượng mẫu theo mức độ khó học** của từng nhóm giá.

```
items_tv_v7 = merge(items_raw_tv_v6.full + items_tv_v6.summary)  ← 110K items
    │
    ▼
Filter price <= 1M VND → 85,727 items
    │
    ▼
Phân bucket + gán multiplier
    │
    ├─ [<50K VND]      × 5 lần  — hàng rẻ, model hay bias cao
    ├─ [50–100K VND]   × 3 lần  — phổ biến nhưng thiếu đa dạng
    ├─ [100–200K VND]  × 2 lần  — cần thêm biến thể
    ├─ [200–500K VND]  × 1 lần  — đã đủ, KHÔNG augment
    └─ [500K–1M VND]   × 4 lần  — outlier tail, hard cases
    │
    ▼
~185,584 LLM requests
```

**Phân tích lý do từng bucket:**

| Bucket | Giá | Multiplier | Lý do |
|---|---|---|---|
| Siêu rẻ | < 50K VND | **5×** | FMCG (pin, tăm, dây buộc) — model luôn predict quá cao do anchor mean |
| Rẻ | 50–100K | **3×** | Đa dạng category (phụ kiện, văn phòng phẩm) — cần nhiều biến thể |
| Trung bình | 100–200K | **2×** | Nhóm phổ biến nhất — tăng thêm để cân bằng với nhóm rẻ mới thêm |
| Phổ thông | 200–500K | **1×** | Đã có đủ mẫu học từ 85K gốc, không tăng thêm |
| Đắt | 500K–1M | **4×** | Chiếm < 5% train gốc, nhưng lỗi outlier rất nghiêm trọng (RMSLE nhạy với %) |

### 4.3 Cơ chế augmentation bằng LLM

**Nguyên tắc:** Giữ nguyên 3 dòng header (thông tin không thể sai), **chỉ viết lại 2 dòng Mô tả + Thông số** theo cách khác.

```
Dữ liệu gốc:
  Tiêu đề: [giữ nguyên] ─────────────┐
  Danh mục: [giữ nguyên] ────────────┤  → Output augmented
  Thương hiệu: [giữ nguyên] ─────────┘     Tiêu đề: [giữ nguyên]
  Mô tả: [LLM viết lại khác đi] ─────┐     Danh mục: [giữ nguyên]
  Thông số: [LLM viết lại khác đi] ──┘     Thương hiệu: [giữ nguyên]
                                            Mô tả: [phiên bản mới]
                                            Thông số: [phiên bản mới]
```

**System prompt (nội dung chính):**
```
Dựa vào thông tin sản phẩm gốc và tóm tắt hiện tại, hãy viết lại 'Mô tả' và 'Thông số' theo cách khác.
Yêu cầu:
- Giữ nguyên ý nghĩa, nhưng dùng từ ngữ và cách diễn đạt khác.
- Không được viết giống với Mô tả/Thông số hiện tại.
- Chỉ trả lời đúng 2 dòng theo định dạng sau, không thêm gì khác:
Mô tả: [1 câu mô tả sản phẩm]
Thông số: [1 câu về tính năng nổi bật]
```

**User message gồm 2 phần:**
1. `full` — toàn bộ mô tả gốc từ trang web (~2K ký tự): cung cấp ngữ cảnh đầy đủ
2. Tóm tắt hiện tại (`Mô tả` + `Thông số` gốc): để LLM viết lại khác đi

### 4.4 Hạ tầng xử lý batch

**Vấn đề về quy mô:** 185,584 requests không thể gọi API đơn lẻ (quá chậm và đắt). Giải pháp dùng **Groq Batch API** — gửi file JSONL, Groq xử lý bất đồng bộ, lấy kết quả sau.

```
185,584 requests
    │
    ▼
Chia thành 186 batch files (≤ 1,000 requests/file)
    │
    ▼
Upload từng file JSONL lên Groq → Submit batch job
    │
    ▼
Poll status (mỗi 60s) cho đến khi tất cả completed
    │
    ▼
Download 186 output files → Parse từng dòng JSONL
    │
    ▼
183,385 augmented summaries (2,199 failed = 1.2%)
```

Mỗi request được đánh `custom_id = f"{item_idx}_{version}"` để sau khi nhận kết quả có thể ghép lại đúng với sản phẩm gốc.

**Cơ chế resume:** State (batch_id, done flag) được pickle vào `batches_aug_v3.pkl`. Nếu kernel crash giữa chừng, có thể load state và tiếp tục fetch mà không phải submit lại.

### 4.5 Kết quả augmentation

| Chỉ số | Giá trị |
|---|---|
| Tổng requests gửi đi | 185,584 |
| Số batch | 186 |
| Responses nhận về | 185,583 (missing 1) |
| Parse thành công | **183,385** |
| Parse thất bại (format sai) | 2,198 (1.2%) |
| Model sử dụng | `openai/gpt-oss-20b` |

**Lý do parse thất bại (1.2%):** LLM đôi khi thêm giải thích thừa, đặt prefix sai, hoặc viết quá nhiều dòng — regex không nhận dạng được, bỏ qua mẫu đó.

### 4.6 Build dataset cuối cùng

```
items_prompts_tv_3 (train: 85,727)   ← giữ nguyên, không xáo trộn
        +
augmented_examples (183,385)         ← completion = round(price/1000), prompt từ summary_v2
        │
        ▼ shuffle(seed=42)
items_prompts_tv_4 (train: 269,112)
items_prompts_tv_4 (val: 3,926)      ← giữ nguyên từ tv_3
items_prompts_tv_4 (test: 3,872)     ← giữ nguyên từ tv_3
```

---

## Tổng Hợp Toàn Bộ Pipeline

### Bảng dataset theo từng giai đoạn

| Dataset (HF Hub) | Bước tạo | Train | Val | Test | Cột chính |
|---|---|---|---|---|---|
| `items_raw_tv_v6` | Day 1 | 100,000 | 5,000 | 5,000 | title, category, price, full, brand |
| `items_tv_v6` | Day 2 | 110,000 | 5,000 | 5,000 | + summary (5 dòng) |
| `items_tv_v7` | Aug prep | 110,000 | 5,000 | 5,000 | + full được merge lại |
| `items_tv_v8` | Aug output | 183,385 | 5,000 | 5,000 | + summary_version2, aug_version |
| `items_prompts_tv_3` | Fine-tune prep | 85,727 | 3,926 | 3,872 | prompt, completion, price_vnd_true |
| **`items_prompts_tv_4`** | **Augmentation** | **269,112** | **3,926** | **3,872** | prompt, completion, price_vnd_true |

### Luồng dữ liệu tóm tắt

```
158,362 SP thô
    → làm sạch + dedup + sampling  →  110,000 SP  (items_raw_tv_v6)
    → LLM chuẩn hóa summary        →  110,000 SP  (items_tv_v6)
    → lọc giá + build prompt        →   85,727 mẫu (items_prompts_tv_3)
    → augmentation 183,385 mẫu mới →  269,112 mẫu (items_prompts_tv_4)
                                         ▲
                                  3.15× số mẫu gốc
```

### Chi phí LLM

| Giai đoạn | Model | Requests | Chi phí ước tính |
|---|---|---|---|
| Day 2 — chuẩn hóa summary | gpt-oss-20b | 120,000 | ~$9–10 |
| Stage 2 — augmentation | gpt-oss-20b | 185,584 | ~$3–5 |
| **Tổng** | | **305,584** | **~$13–15** |

---

## Tác Động Dự Kiến Lên Kết Quả Training

| Version | Dataset train | RMSLE | Ghi chú |
|---|---|---|---|
| v1 smoke | 20,000 (subset tv_3) | 0.6084 | Chỉ 2 epoch, r=32 |
| v3 full | 85,727 (tv_3) | 0.4426 | 3 epoch, r=64, 7 modules |
| v4-scratch *(mục tiêu)* | 269,112 (tv_4) | **0.36–0.40** | r=128, DoRA, RSLoRA |
| Target | — | **< 0.38** | Mục tiêu Day 5 |
| Day4 v8 (baseline) | — | 0.4004 | Stacked 8 models |

**Lý thuyết:** Với 3.15× dữ liệu + đa dạng hóa Mô tả/Thông số, model được kỳ vọng:
- Giảm lỗi anchor theo category mean (nhiều biến thể mô tả hơn cho cùng 1 sản phẩm)
- Cải thiện khả năng xử lý outlier giá thấp và cao (multiplier 5× và 4×)
- Tổng quan: RMSLE giảm thêm ~0.04–0.06 so với v3 (ước tính từ scaling law)


### Thông tin bổ sung: toàn bộ file code thực hiện ( đọc thêm nếu thấy cần thiết )

tech2ai/scraping_data_tv/Tiki
tech2ai/scraping_data_tv/Data_processing_for_Vietnamese_data/day1
tech2ai/scraping_data_tv/Data_processing_for_Vietnamese_data/day2
tech2ai/fine_tune_qwen/01_prepare_dataset.ipynb
tech2ai/fine_tune_qwen/08_augment_dataset_v4_version3.ipynb
tech2ai/fine_tune_qwen/08_augment_dataset_v4_version4.ipynb

