# Day 2 v2: LLM Preprocessing — Re-run voi 5 truong

**Ngay:** 2026-04-13
**Trang thai:** DANG THUC HIEN
**Branch:** `feature/data-preprocessing-vi`
**Input:** `SeanSunny/items_raw_tv_v4` (120K items: 110K train / 5K val / 5K test)
**Output:** `SeanSunny/items_tv_v5`

---

## 1. Van de

Day 2 v1 dung SYSTEM_PROMPT 2 truong (Mo ta + Thong so), giu nguyen title/category/brand tu data goc.

**Van de phat hien:** 28% titles (33,583/120K) chua SKU codes gay nhieu:
- `TEBAT870`, `UG11672DV101TK`, `X550 X550A X550C X550J X540La K450 K450C`...
- Khong the loai bang regex vi mot so codes la thong so co nghia: `1500W`, `SPF50`, `1080P`, `500ML`

**Quyet dinh:** De LLM rewrite toan bo 5 truong (giong pipeline tieng Anh). LLM se:
- Rewrite title → loai SKU codes, giu thong so co nghia
- Rewrite category, brand, mo ta, thong so

**Ly do rewrite toan bo (khong giu data goc):**
- Khi inference, du lieu cung se di qua LLM rewrite truoc → format nhat quan giua train va inference
- Neu giu category goc, luc inference co the xuat hien category la ngoai du kien → anh huong model
- LLM dong vai tro **normalizer** — chuan hoa input thanh format sach, nhat quan

---

## 2. Thay doi so voi Day 2 v1

| | Day 2 v1 | Day 2 v2 (lan nay) |
|---|---|---|
| **SYSTEM_PROMPT** | 2 truong (Mo ta, Thong so) | 5 truong (Tieu de, Danh muc, Thuong hieu, Mo ta, Thong so) |
| **Title** | Data goc (co SKU codes) | LLM rewrite (sach) |
| **Category** | Data goc (8 categories chinh xac) | LLM rewrite (co the khac ten nhung nhat quan) |
| **Brand** | Data goc | LLM rewrite |
| **Cot full (input cho LLM)** | title + features | title + features + brand + category |
| **build_summary()** | Ghep 3 truong goc + 2 truong LLM | Dung toan bo output LLM |
| **Raw dataset** | items_raw_tv_v4 | items_raw_tv_v5 (full co brand + category) |
| **Output dataset** | items_tv_v4 | items_tv_v5 |

---

## 3. SYSTEM_PROMPT moi

Tham khao English SYSTEM_PROMPT:
```
Create a concise description of a product. Respond only in this format. Do not include part numbers.
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features
```

Vietnamese SYSTEM_PROMPT (5 truong):
```
Tao mo ta ngan gon cho mot san pham. Chi tra loi dung 5 dong theo dinh dang sau. Khong bao gom ma san pham hay ma noi bo.
Tieu de: Viet lai tieu de ngan gon, chinh xac
Danh muc: Phan loai san pham
Thuong hieu: Ten thuong hieu
Mo ta: 1 cau mo ta san pham
Thong so: 1 cau ve tinh nang noi bat
```

**Luu y:** Khong liet ke 8 categories trong prompt — de LLM tu phan loai.
Khi inference, LLM cung se tu phan loai → nhat quan.

---

## 4. Cot full (input cho LLM)

**Hien tai (v4):**
```
full = scrub(title, features)  # title + features (cleaned)
```

**Moi (v5):**
```
full = scrub(title, features) + "\nThuong hieu: {brand}" + "\nDanh muc: {category}"
```

VD:
```
May hut am Airdog Hakawa M320 Cong Nghe Khi Nen Dung Cho Phong 60m2
May hut am nhiet dien, cong suat 440W, dung tich binh 6,5L, hut 20L/ngay...
Thuong hieu: Hakawa Airdog
Danh muc: Dien Lanh va Gia Dung
```

---

## 5. Cac buoc thuc hien

### Step 1: Tao items_raw_tv_v5
- Load items_raw_tv_v4 tu HF Hub
- Voi moi item: full = full_cu + "\nThuong hieu: {brand}" + "\nDanh muc: {category}"
- Brand rong → "Khong ro"
- Push len HF Hub: SeanSunny/items_raw_tv_v5
- **Tieu chi:** 120K items, full co 4 phan (title, features, brand, category)

### Step 2: Design SYSTEM_PROMPT moi + update code
- Viet SYSTEM_PROMPT 5 truong (Vietnamese)
- Update `preprocessor.py`: SYSTEM_PROMPT moi, build_summary() dung toan bo LLM output
- Update `batch.py` neu can
- **Tieu chi:** Import thanh cong, SYSTEM_PROMPT in dung 5 truong

### Step 3: Test tren 10-20 items
- Chay Preprocessor.preprocess() tren 10-20 items
- Kiem tra:
  - SKU codes da bi loai khoi title?
  - Category co hop ly? (khong can trung 100% voi 8 categories goc)
  - Brand chinh xac?
  - Mo ta + Thong so chat luong?
- **Tieu chi:** >= 80% items cho ket qua tot

### Step 4: Full batch processing (120K items)
- Batch.create() → Batch.run() → Batch.save() → Batch.fetch()
- 120 batches x 1000 items
- Resubmit failed batches neu co
- **Tieu chi:** 120/120 batches done, missing summaries < 100

### Step 5: Validate + Build prompts + Push
- Check missing summaries (muc tieu: 0)
- Xem vi du summary tu nhieu categories
- make_prompt() cho tung item
- Clean up: full = None, brand = None, id = None
- Push SeanSunny/items_tv_v5
- **Tieu chi:** 120K items, 3 splits, summary + prompt co data

### Step 6: Cap nhat docs
- Cap nhat plan_data_preprocessing_vi.md
- Cap nhat SESSION_HANDOFF.md
- **Tieu chi:** Docs phan anh dung trang thai moi

---

## 6. Summary format moi (output cuoi cung)

```
Tieu de: [LLM rewritten — sach, khong SKU codes]
Danh muc: [LLM rewritten — phan loai tu LLM]
Thuong hieu: [LLM rewritten]
Mo ta: [LLM generated]
Thong so: [LLM generated]
```

**Prompt format (khong doi):**
```
San pham nay gia bao nhieu?

[summary 5 dong]

Gia: [price VND]
```

---

## 7. Chi phi va thoi gian uoc tinh

| Hang muc | Uoc tinh |
|---|---|
| Groq API cost | ~$5 cho 120K items |
| Thoi gian Step 1 (tao v5) | ~5 phut |
| Thoi gian Step 3 (test) | ~5 phut |
| Thoi gian Step 4 (batch) | ~6 gio (Groq processing) |
| Thoi gian Step 5 (push) | ~5 phut |

---

## 8. Ket qua kiem chung

| Step | Trang thai | Ket qua | Ghi chu |
|---|---|---|---|
| 1. items_raw_tv_v5 | | | |
| 2. SYSTEM_PROMPT + code | | | |
| 3. Test 10-20 items | | | |
| 4. Full batch 120K | | | |
| 5. Validate + push | | | |
| 6. Cap nhat docs | | | |

---

*Tao: 2026-04-13. Buoc tiep: Step 1 tao items_raw_tv_v5.*
