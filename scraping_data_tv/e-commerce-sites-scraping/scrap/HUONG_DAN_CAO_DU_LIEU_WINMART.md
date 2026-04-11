# Huong dan cao du lieu WinMart

## Tong quan

- **Trang:** winmart.vn (sieu thi WinMart / WinMart+)
- **Tech:** JSON API (khong can Selenium/Chrome)
- **API:** `api-crownx.winmart.vn/it/api/web/v3/item/category`
- **Category:** Tat ca 18 categories map vao **"Bach Hoa"**
- **Tong SP:** ~3,238 san pham (xem `winmart_categories_report.md`)
- **Output:** Moi category 1 file rieng: `winmart_{slug}.jsonl` trong `scrap/data/`
- **Resume:** Neu bi ngat (Ctrl+C), chay lai cung lenh → **tu dong skip categories da cao xong** (kiem tra file da ton tai)
- **Block handling:** Tu dong doi 30-90s khi bi 403/429
- **Schema:** `{title, price, features, brand, category}` — tuong thich Tiki pipeline
- **LUU Y:** API co the bi timeout tu server ngoai VN — da test OK tu WSL hien tai

---

## Trang thai cao du lieu

Danh dau `[x]` khi da cao xong. Neu bi ngat, chay lai → scraper tu dong skip categories da co file.

### Thuc pham (10 categories, ~1,862 SP)

| # | Slug | Category | SP | Xong |
|---:|---|---|---:|:---:|
| 1 | `banh-keo--c07` | Banh keo | 467 | [ ] |
| 2 | `sua-cac-loai--c08` | Sua cac loai | 301 | [ ] |
| 3 | `gia-vi--c35` | Gia vi | 269 | [ ] |
| 4 | `mi-thuc-pham-an-lien--c34` | Mi, thuc pham an lien | 215 | [ ] |
| 5 | `thuc-pham-kho--c06` | Thuc pham kho | 160 | [ ] |
| 6 | `thuc-pham-che-bien--c04` | Thuc pham che bien | 152 | [ ] |
| 7 | `rau-cu-trai-cay--c02` | Rau cu trai cay | 147 | [ ] |
| 8 | `thuc-pham-dong-lanh--c05` | Thuc pham dong lanh | 110 | [ ] |
| 9 | `thit-hai-san-tuoi--c03` | Thit, hai san tuoi | 54 | [ ] |
| 10 | `trung-dau-hu--c33` | Trung, dau hu | 23 | [ ] |

### Do uong (2 categories, ~355 SP)

| # | Slug | Category | SP | Xong |
|---:|---|---|---:|:---:|
| 11 | `do-uong-giai-khat--c09` | Do uong giai khat | 313 | [ ] |
| 12 | `do-uong-co-con--c31` | Do uong co con | 42 | [ ] |

### Cham soc & Gia dinh (4 categories, ~898 SP)

| # | Slug | Category | SP | Xong |
|---:|---|---|---:|:---:|
| 13 | `cham-soc-ca-nhan--c11` | Cham soc ca nhan | 514 | [ ] |
| 14 | `do-dung-gia-dinh--c25` | Do dung gia dinh | 217 | [ ] |
| 15 | `hoa-pham-tay-rua--c10` | Hoa pham tay rua | 119 | [ ] |
| 16 | `cham-soc-be--c12` | Cham soc be | 48 | [ ] |

### Khac (2 categories, ~87 SP)

| # | Slug | Category | SP | Xong |
|---:|---|---|---:|:---:|
| 17 | `van-phong-pham-do-choi--c27` | Van phong pham, do choi | 75 | [ ] |
| 18 | `dien-gia-dung--c26` | Dien gia dung | 12 | [ ] |

**TONG: 18 categories, ~3,238 SP**

---

## Buoc 1: Chuan bi (1 lan)

```bash
cd tech2ai
uv sync
```

---

## Buoc 2: Test API (xac nhan ket noi)

```bash
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/winmart_scraper.py --test
```

Ket qua mong doi:
```
Testing API with slug: rau-cu-trai-cay--c02

SUCCESS! Got 5 items on page 1

  Product 1:
    title: Dua hau Hac My Nhan (Long An)
    price: 29,900 VND
    brand: DUA HAU
    ...
Testing pagination...
  Total items in 'rau-cu-trai-cay--c02': 147 (2 pages)
```

Neu FAILED → API bi timeout tu server ngoai VN → chay tu may local (mang VN).

---

## Buoc 3: Cao tat ca 18 categories

```bash
# Cao tat ca — moi category 1 file rieng (winmart_{slug}.jsonl)
# Tu dong skip categories da cao xong
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/winmart_scraper.py
```

**Thoi gian uoc tinh:** ~5-10 phut (API nhe, 0.5s/page, ~50 pages tong cong)

**Neu bi ngat (Ctrl+C, mat mang):** Chay lai **CUNG LENH** tren → scraper tu dong skip categories da co file:
```
[1/18] Sua cac loai (sua-cac-loai--c08) — SKIP (301 SP already)
[2/18] Rau cu trai cay (rau-cu-trai-cay--c02) — SKIP (147 SP already)
...
[8/18]
--- Category: Thuc pham kho (slug=thuc-pham-kho--c06) ---     ← tiep tuc tu day
```

**Hoac cao tung category:**
```bash
# Cao 1 category cu the (vi du: banh keo)
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/winmart_scraper.py --slug "banh-keo--c07"

# Gioi han so SP (test nhanh)
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/winmart_scraper.py --slug "banh-keo--c07" --max 10
```

---

## Buoc 4: Kiem tra ket qua

```bash
# Dem tong SP da cao
wc -l scraping_data_tv/e-commerce-sites-scraping/scrap/data/winmart_*.jsonl

# Xem 1 SP mau
head -1 scraping_data_tv/e-commerce-sites-scraping/scrap/data/winmart_banh-keo.jsonl | \
    uv run python3 -c "import sys,json; d=json.loads(sys.stdin.read()); \
    print('title:', d['title']); print('price:', d['price']); \
    print('brand:', d['brand']); print('category:', d['category']); \
    print('features:', len(d['features']), 'chars')"
```

---

## Buoc 5: Merge vao Tiki pipeline

```bash
# Copy tat ca JSONL files vao thu muc chung
cp scraping_data_tv/e-commerce-sites-scraping/scrap/data/winmart_*.jsonl \
   scraping_data_tv/Tiki/Tiki_dataset_scrape/

# Re-run Day 1 pipeline
uv run scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py
```

---

## Cac lenh tham khao

| Lenh | Muc dich | Output |
|------|----------|--------|
| `--test` | Test API, 5 SP + pagination count | (in ra terminal) |
| `--report` | Scan categories, dem SP, tao report.md | `winmart_categories_report.md` |
| `--slug "banh-keo--c07"` | Cao 1 category | `winmart_banh-keo.jsonl` |
| `--slug "..." --max 10` | Cao 1 category, gioi han 10 SP | `winmart_*.jsonl` |
| `--page-size 40` | Doi pageSize (default: 100) | - |
| (khong co flag) | Cao TAT CA 18 categories | `winmart_*.jsonl` x 18 |

---

## Xu ly su co

### Bi ngat giua chung (Ctrl+C)
- **Categories DA XONG** (co file): tu dong SKIP khi chay lai
- **Category DANG CAO** (chua xong): file bi chua day du → xoa file do roi chay lai:
```bash
# Xoa file cua category dang cao do (vi du: banh-keo--c07)
rm scraping_data_tv/e-commerce-sites-scraping/scrap/data/winmart_banh-keo.jsonl
# Chay lai → chi cao lai category do, skip cac category da xong
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/winmart_scraper.py
```

### API timeout
- Mac dinh timeout = 30s, retry 3 lan
- Neu van bi timeout: co the do server ngoai VN → chay tu may local (mang VN)

### API bi 403/429
- Scraper tu dong doi 30-90s roi thu lai
- Neu van bi: tang delay giua cac pages (sua `DELAY_BETWEEN_PAGES` trong code)

### Muon cao lai 1 category tu dau
```bash
# Xoa file cu roi chay lai
rm scraping_data_tv/e-commerce-sites-scraping/scrap/data/winmart_banh-keo.jsonl
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/winmart_scraper.py --slug "banh-keo--c07"
```

---

## So sanh voi Hasaki scraper

| | Hasaki | WinMart |
|---|---|---|
| **API** | listing (get IDs) + detail (per product) | category listing (all data in 1 call) |
| **So requests** | ~11K (1 per product) | ~50 (pages only) |
| **Toc do** | ~3.7 SP/s (3 workers) | ~50 SP/s (single thread) |
| **Thoi gian** | ~50 phut | ~5-10 phut |
| **Features quality** | Rat tot (~2000 chars) | Trung binh (~50-500 chars) |
| **Anti-bot** | 403/429 (co) | Gan nhu khong co |
| **Concurrency** | Can ThreadPoolExecutor | Khong can (API nhe) |
| **Category dung** | Leaf categories (130) | Parent categories (18) |

---

## Thong tin API ky thuat

**Endpoint:**
```
GET https://api-crownx.winmart.vn/it/api/web/v3/item/category
    ?orderByDesc=true
    &pageNumber={page}
    &pageSize={size}
    &slug={category-slug}
    &storeCode=1535
    &storeGroupCode=1998
```

**Headers bat buoc:**
| Header | Gia tri | Ghi chu |
|---|---|---|
| `authorization` | `Bearer` | Token rong — KHONG CAN AUTH |
| `x-api-merchant` | `WCM` | BAT BUOC |
| `origin` | `https://winmart.vn` | CORS check |
| `referer` | `https://winmart.vn/` | CORS check |
| `accept` | `application/json` | |

**Response data fields:**
- `name`: ten san pham day du
- `price`: gia goc (VND) — DUNG CHO DATASET
- `salePrice`: gia khuyen mai
- `brandName`: thuong hieu
- `shortDescription`: mo ta ngan
- `longDescription`: mo ta dai (HTML — can strip tags)
- `mch1Name`–`mch5Name`: 5 cap category hierarchy
- `categoryName`: ten category
- `uom`: don vi tinh (KG, Goi, Thung, Chai...)

---

*Tao ngay: 2026-04-11. WinMart API JSON, 18 categories, ~3,238 SP.*
