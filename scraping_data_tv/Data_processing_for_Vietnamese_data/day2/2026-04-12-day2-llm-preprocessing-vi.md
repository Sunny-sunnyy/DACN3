# Day 2: LLM Preprocessing (Vietnamese) — Huong dan chay

**Ngay:** 2026-04-12
**Trang thai:** SAN SANG CHAY
**Branch:** `feature/data-preprocessing-vi`

---

## 1. Tong quan

Dung LLM rewrite 120K product descriptions thanh format chuan 5 truong.

**Cach hoat dong:**
- LLM (`gpt-oss-20b`) chi tao **2 truong**: Mo ta + Thong so
- **3 truong con lai** (Tieu de, Danh muc, Thuong hieu) lay tu data goc (chinh xac 100%)
- `build_summary()` ghep 5 truong thanh 1 chuoi summary

**Vi du summary sau xu ly:**
```
Tieu de: May hut am Airdog Hakawa M320 Cong Nghe Khi Nen Dung Cho Phong 60m2
Danh muc: Dien Lanh va Gia Dung
Thuong hieu: Hakawa Airdog
Mo ta: May hut am nhiet dien lam lanh hieu qua cho phong 60m2.
Thong so: Hut 20L/ngay, dung tich binh 6,5L, cong suat 440W.
```

---

## 2. Cau truc files

```
Data_processing_for_Vietnamese_data/
    pricer_vi/
        __init__.py
        items.py              # Item model, make_prompt(), push_to_hub()
        parser.py             # Day 1: 9-step Vietnamese cleaning
        preprocessor.py       # SYSTEM_PROMPT (2 truong), build_summary(), Preprocessor class
        batch.py              # Batch class — Groq Batch API workflow
    day2_llm_preprocessing_v2.ipynb   # <<< NOTEBOOK CHINH — CHAY FILE NAY
    day2_llm_preprocessing.py         # Test script (da chay items 21-30)
    day2_llm_preprocessing.ipynb      # Notebook cu (v1, khong dung nua)
    batches_vi/              # [TU TAO] JSONL files gui len Groq (120 files)
    output_vi/               # [TU TAO] Ket qua tra ve tu Groq (120 files)
    batches_vi.pkl           # [TU TAO] State file cho resume
    jsonl_vi/                # [TU TAO] Test batch files (Section 3)
```

**Giai thich cac folder tu tao khi chay:**

| Folder/File | Khi nao tao | Noi dung | Kich thuoc uoc tinh |
|---|---|---|---|
| `batches_vi/` | `Batch.run()` | 120 file JSONL (0_1000.jsonl, 1000_2000.jsonl, ...) — request gui Groq | ~500MB |
| `output_vi/` | `Batch.fetch()` | 120 file JSONL — response tu Groq (chua Mo ta + Thong so) | ~50MB |
| `batches_vi.pkl` | `Batch.save()` | Pickle state (batch_ids, done flags) cho resume | ~1MB |
| `jsonl_vi/` | Section 3 (optional) | Test batch files nho | ~1MB |

---

## 3. Dieu kien truoc khi chay

- [x] `GROQ_API_KEY` trong `.env` (da xac nhan)
- [x] HF dataset `SeanSunny/items_raw_tv_v4` da push (120K items)
- [x] `HF_TOKEN` trong `.env` (de push ket qua len HF Hub)
- [x] Cac packages: `litellm`, `groq`, `datasets`, `huggingface_hub`, `pydantic`, `tqdm`, `python-dotenv`

Kiem tra nhanh:
```bash
cd scraping_data_tv/Data_processing_for_Vietnamese_data
uv run python -c "from pricer_vi.batch import Batch; print('OK')"
```

---

## 4. Huong dan chay tung buoc

### Buoc 1: Mo notebook

Mo file `day2_llm_preprocessing_v2.ipynb` trong IDE (VS Code / JupyterLab).

### Buoc 2: Chay imports + Load data (Section 1)

Chay 4 cell dau tien:
1. Imports + load_dotenv
2. Load dataset tu HF Hub (120K items) — mat ~30 giay
3. Assign IDs (0 den 119,999)
4. Inspect raw data (kiem tra item[0])

**Kiem tra:** output phai hien "Loaded 120,000 items"

### Buoc 3: Test single item (Section 2)

Chay 2 cell:
1. In SYSTEM_PROMPT (phai hien chi 2 dong: Mo ta + Thong so)
2. Test LLM tren item[0] — xem LLM response va final summary

**Kiem tra:** Summary phai co 5 dong (3 dong tu data goc + 2 dong tu LLM)

### Buoc 4: Test batch nho (Section 3) — OPTIONAL

**Bo qua neu da test o v1.** Neu muon test lai:
1. Tao file JSONL 10 items
2. Upload + submit batch
3. Check status (chay lai cho den "completed")
4. Fetch results — xem 10 summaries

### Buoc 5: Full batch processing (Section 4) — BUOC CHINH

**Day la buoc ton thoi gian va chi phi nhat.**

Cell 1: Reset summaries + `Batch.create(items)`
- Output: "Created 120 batches"

Cell 2: `Batch.run()`
- Tao 120 file JSONL trong `batches_vi/`
- Upload tung file len Groq
- Submit 120 batches
- **Thoi gian:** ~5-15 phut (tuy toc do mang)
- Output: "Submitted 120 batches"

**QUAN TRONG:** Ngay sau khi `Batch.run()` xong, chay `Batch.save()` de luu state truoc khi lam gi khac. Neu kernel crash truoc khi save, ban mat batch_ids va phai submit lai.

Cell 3: `Batch.fetch()` — **CHAY NHIEU LAN**
- Groq xu ly batches khong dong thoi, can vai phut
- Chay lai cell nay cho den khi: "Finished 120 of 120 batches"
- Moi lan chay, cac batch da done se bi skip
- **Thoi gian:** Thuong 2-5 phut la xong het 120 batches

Cell 4: `Batch.save()` — luu state sau khi fetch xong

### Buoc 6: Kiem tra ket qua (Section 5)

1. Check missing summaries — **muc tieu: 0 missing**
2. Xem vi du summary tu nhieu categories

**Neu co missing summaries:** Chay `Batch.fetch()` them lan nua. Neu van con missing, co the do Groq loi 1 so items — chap nhan neu < 100 items.

### Buoc 7: Build prompts + Clean up + Push (Section 6)

3 cell cuoi cung:

1. `make_prompt(summary)` — tao prompt cho fine-tuning
   - Format: "San pham nay gia bao nhieu?\n\n[summary]\n\nGia: [price]"

2. Clean up: `full = None`, `brand = None`, `id = None`
   - Chi giu: title, category, price, summary, prompt

3. Push len HF Hub: `SeanSunny/items_tv_v4` (110K train / 5K val / 5K test)
   - **Thoi gian:** ~2-5 phut

---

## 5. Resume khi bi ngat giua chung

**Truong hop 1: Kernel crash SAU Batch.run() + Batch.save()**

```python
# Chay lai tu cell 1 den cell "Assign IDs" (load data + assign IDs)
# Sau do:
Batch.load(items)  # Uncomment cell resume
Batch.fetch()      # Tiep tuc fetch
```

**Truong hop 2: Kernel crash SAU Batch.run() nhung CHUA save**

Batch IDs bi mat. Phai chay lai tu `Batch.create()` va `Batch.run()`.
Chi phi Groq se tinh them (batches cu van chay tren Groq nhung khong lay ket qua duoc).

=> **Loi khuyen:** Luon `Batch.save()` ngay sau `Batch.run()`.

**Truong hop 3: Kernel crash SAU Batch.fetch() 1 phan**

```python
Batch.load(items)  # Load state — cac batch da done duoc danh dau
Batch.fetch()      # Chi fetch cac batch chua done
```

---

## 6. Chi phi va thoi gian uoc tinh

| Hang muc | Uoc tinh |
|---|---|
| Groq API cost | ~$9-10 cho 120K items |
| Avg tokens/item | ~640 input + 97 output |
| Thoi gian Batch.run() | ~5-15 phut (upload 120 files) |
| Thoi gian Batch.fetch() | ~2-5 phut (Groq xu ly) |
| Thoi gian push HF Hub | ~2-5 phut |
| **Tong thoi gian** | **~15-30 phut** |

---

## 7. Kiem tra sau khi hoan thanh

1. **HF Hub:** Truy cap `https://huggingface.co/datasets/SeanSunny/items_tv_v4`
   - Phai co 3 splits: train (110K), validation (5K), test (5K)
   - Cot: title, category, price, full (null), brand (null), summary (co data), prompt (co data), id (null)

2. **Summary format:** Moi summary phai co 5 dong:
   ```
   Tieu de: [tu data goc]
   Danh muc: [tu data goc — 1 trong 8 categories]
   Thuong hieu: [tu data goc hoac "Khong ro"]
   Mo ta: [tu LLM]
   Thong so: [tu LLM]
   ```

3. **Prompt format:**
   ```
   San pham nay gia bao nhieu?

   [summary 5 dong]

   Gia: [price VND]
   ```

---

## 8. Luu y quan trong

1. **Khong chay dong thoi 2 notebook** tren cung du lieu — Batch class dung class-level state, se conflict.

2. **Khong dong notebook/kernel khi Batch.run() dang chay** — se mat batch_ids. Neu phai dong, chay `Batch.save()` truoc.

3. **Section 3 (test batch) la optional** — bo qua de tiet kiem thoi gian neu da test o notebook v1.

4. **Groq rate limits:** 120 batches x 1000 items = 120K API calls. Groq xu ly batch theo queue, khong bi rate limit nhu API thong thuong.

5. **Disk space:** `batches_vi/` + `output_vi/` chiem ~550MB. Sau khi push HF Hub thanh cong, co the xoa 2 folder nay.

---

*Tao: 2026-04-12. Buoc tiep sau Day 2: Day 3 Baseline ML (XGBoost, LightGBM, CatBoost).*
