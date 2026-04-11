# Huong dan cao du lieu Hasaki

## Tong quan

- **Trang:** hasaki.vn (my pham chinh hang)
- **Tech:** JSON API (khong can Selenium/Chrome)
- **Category:** Tat ca 130 categories map vao **"Lam Dep - Suc Khoe"**
- **Tong SP:** ~11,407 san pham (xem `hasaki_categories_report.md`)
- **Output:** Moi category 1 file rieng: `hasaki_category_{id}.jsonl` trong `scrap/data/`
- **Resume:** Neu bi ngat (Ctrl+C), chay lai cung lenh → **tu dong skip categories da cao xong** (kiem tra file da ton tai)
- **Block handling:** Tu dong doi 60s + rotate session khi bi 403/429
- **Schema:** `{title, price, features, brand, category}` — tuong thich Tiki pipeline

---

## Trang thai cao du lieu

Danh dau `[x]` khi da cao xong. Neu bi ngat, chay lai → scraper tu dong skip categories da co file.

### Cham Soc Da Mat (34 categories, ~6,306 SP)

| # | ID | Category | SP | Xong |
|---:|---:|---|---:|:---:|
| 1 | 1907 | My Pham High-End | 67 | [ ] |
| 2 | 48 | Tay Trang Mat | 306 | [ ] |
| 3 | 19 | Sua Rua Mat | 429 | [ ] |
| 4 | 35 | Tay Te Bao Chet Da Mat | 69 | [ ] |
| 5 | 1857 | Toner / Nuoc Can Bang Da | 157 | [ ] |
| 6 | 75 | Serum / Tinh Chat | 345 | [ ] |
| 7 | 2005 | Ho Tro Tri Mun | 101 | [ ] |
| 8 | 2266 | San Pham Dac Tri Khac | 38 | [ ] |
| 9 | 7 | Xit Khoang | 54 | [ ] |
| 10 | 2011 | Lotion / Sua Duong | 98 | [ ] |
| 11 | 9 | Kem / Gel / Dau Duong | 345 | [ ] |
| 12 | 298 | Serum / Kem Duong Mat | 21 | [ ] |
| 13 | 299 | Mat Na Mat | 12 | [ ] |
| 14 | 190 | Tay Te Bao Chet Moi | 10 | [ ] |
| 15 | 71 | Mat Na Moi | 16 | [ ] |
| 16 | 31 | Mat Na Giay | 634 | [ ] |
| 17 | 1859 | Mat Na Rua | 75 | [ ] |
| 18 | 69 | Mat Na Lot | 11 | [ ] |
| 19 | 68 | Mat Na Ngu | 24 | [ ] |
| 20 | 11 | Chong Nang Da Mat | 369 | [ ] |
| 21 | 1879 | Da Dau / Lo Chan Long To | 403 | [ ] |
| 22 | 1883 | Da Kho / Mat Nuoc | 543 | [ ] |
| 23 | 1881 | Da Lao Hoa | 275 | [ ] |
| 24 | 1877 | Da Mun | 433 | [ ] |
| 25 | 1885 | Da Nhay Cam / Kich Ung | 413 | [ ] |
| 26 | 1887 | Da Xin Mau | 554 | [ ] |
| 27 | 17 | Tham / Nam / Tan Nhang | 169 | [ ] |
| 28 | 2107 | Quang Tham & Bong Mat | 11 | [ ] |
| 29 | 2061 | Seo | 18 | [ ] |
| 30 | 1993 | Viem Da Co Dia | 2 | [ ] |
| 31 | 47 | Bong Tay Trang | 84 | [ ] |
| 32 | 1861 | Dung Cu / May Rua Mat | 40 | [ ] |
| 33 | 2063 | May Cham Soc Da | 2 | [ ] |
| 34 | 2202 | Dung Cu Cham Soc Khac | 14 | [ ] |
| 35 | 147 | Bo Cham Soc Da Mat | 231 | [ ] |

### Trang Diem (31 categories, ~2,146 SP)

| # | ID | Category | SP | Xong |
|---:|---:|---|---:|:---:|
| 36 | 55 | Kem Lot | 25 | [ ] |
| 37 | 178 | Kem Nen | 58 | [ ] |
| 38 | 108 | Phan Nen | 14 | [ ] |
| 39 | 53 | BB / CC Cream | 10 | [ ] |
| 40 | 252 | Phan Nuoc Cushion | 84 | [ ] |
| 41 | 54 | Che Khuyet Diem | 56 | [ ] |
| 42 | 56 | Ma Hong | 122 | [ ] |
| 43 | 191 | Tao Khoi / Highlight | 56 | [ ] |
| 44 | 57 | Phan Phu | 96 | [ ] |
| 45 | 2166 | Xit Khoa Makeup | 22 | [ ] |
| 46 | 51 | Ke May | 107 | [ ] |
| 47 | 58 | Ke Mat | 90 | [ ] |
| 48 | 60 | Phan Mat | 69 | [ ] |
| 49 | 109 | Mascara | 67 | [ ] |
| 50 | 25 | Son Duong Moi | 208 | [ ] |
| 51 | 49 | Son Kem / Tint | 458 | [ ] |
| 52 | 277 | Son Thoi | 151 | [ ] |
| 53 | 107 | Son Bong | 87 | [ ] |
| 54 | 38 | Tay Trang Mat / Moi | 15 | [ ] |
| 55 | 63 | Son Mong | 0 | [ ] |
| 56 | 62 | Nuoc Rua Mong | 0 | [ ] |
| 57 | 1849 | Dung Cu / Phu Kien Lam Mong | 12 | [ ] |
| 58 | 142 | Bong / Mut Trang Diem | 84 | [ ] |
| 59 | 140 | Co Trang Diem | 61 | [ ] |
| 60 | 141 | Bam Mi | 21 | [ ] |
| 61 | 2073 | Mi Gia | 39 | [ ] |
| 62 | 2170 | Mieng Dan Kich Mi | 11 | [ ] |
| 63 | 2071 | Nhip / Dao Cao | 40 | [ ] |
| 64 | 2067 | Giay Tham Dau | 9 | [ ] |
| 65 | 2176 | Dung Cu Trang Diem Khac | 22 | [ ] |
| 66 | 2174 | Bo Trang Diem | 52 | [ ] |

### Cham Soc Toc (15 categories, ~691 SP)

| # | ID | Category | SP | Xong |
|---:|---:|---|---:|:---:|
| 67 | 97 | Dau Goi | 219 | [ ] |
| 68 | 136 | Dau Xa | 96 | [ ] |
| 69 | 2146 | Dau Goi Kho | 37 | [ ] |
| 70 | 2150 | Dau Goi Xa 2in1 | 19 | [ ] |
| 71 | 2152 | Bo Goi Xa | 38 | [ ] |
| 72 | 2162 | Tay Te Bao Chet Da Dau | 9 | [ ] |
| 73 | 110 | Mat Na / Kem U Toc | 38 | [ ] |
| 74 | 102 | Serum / Dau Duong Toc | 78 | [ ] |
| 75 | 137 | Xit Duong Toc | 28 | [ ] |
| 76 | 296 | Thuoc Nhuom Toc | 36 | [ ] |
| 77 | 2101 | San Pham Tao Kieu Toc | 18 | [ ] |
| 78 | 2156 | May Say Toc | 2 | [ ] |
| 79 | 2160 | Luoc | 35 | [ ] |
| 80 | 133 | Bo Cham Soc Toc | 29 | [ ] |
| 81 | 2274 | Phu Kien Toc | 9 | [ ] |

### Cham Soc Co The (10 categories, ~1,000 SP)

| # | ID | Category | SP | Xong |
|---:|---:|---|---:|:---:|
| 82 | 26 | Sua Tam | 310 | [ ] |
| 83 | 2075 | Xa Phong | 7 | [ ] |
| 84 | 128 | Tay Te Bao Chet Body | 95 | [ ] |
| 85 | 65 | Duong Da Tay / Chan | 21 | [ ] |
| 86 | 1897 | Duong The | 226 | [ ] |
| 87 | 13 | Chong Nang Co The | 62 | [ ] |
| 88 | 1899 | Khu Mui | 219 | [ ] |
| 89 | 2037 | Kem Tay Long | 16 | [ ] |
| 90 | 2093 | Dung Cu Tay Long | 12 | [ ] |
| 91 | 2190 | Bo Cham Soc Co The | 32 | [ ] |

### Nuoc Hoa (5 categories, ~400 SP)

| # | ID | Category | SP | Xong |
|---:|---:|---|---:|:---:|
| 92 | 1937 | Nuoc Hoa Nu | 150 | [ ] |
| 93 | 205 | Nuoc Hoa Nam | 62 | [ ] |
| 94 | 2286 | Nuoc Hoa Cao Cap | 134 | [ ] |
| 95 | 278 | Xit Thom Toan Than | 47 | [ ] |
| 96 | 2178 | Nuoc Hoa Vung Kin | 7 | [ ] |

### Cham Soc Ca Nhan (23 categories, ~661 SP)

| # | ID | Category | SP | Xong |
|---:|---:|---|---:|:---:|
| 97 | 1903 | Bang Ve Sinh | 134 | [ ] |
| 98 | 207 | Dung Dich Ve Sinh | 64 | [ ] |
| 99 | 2194 | Duong Vung Kin | 7 | [ ] |
| 100 | 2196 | Mieng Dan Nguc | 9 | [ ] |
| 101 | 2029 | Ban Chai Danh Rang | 42 | [ ] |
| 102 | 2200 | Ban Chai Dien | 11 | [ ] |
| 103 | 2198 | Ho Tro Trang Rang | 9 | [ ] |
| 104 | 2025 | Kem Danh Rang | 153 | [ ] |
| 105 | 2035 | May Tam Nuoc | 16 | [ ] |
| 106 | 2033 | Nuoc Suc Mieng | 24 | [ ] |
| 107 | 2470 | Tam / Chi Nha Khoa | 8 | [ ] |
| 108 | 324 | Xit Thom Mieng | 3 | [ ] |
| 109 | 2047 | Chong Muoi | 15 | [ ] |
| 110 | 2043 | Khau Trang | 30 | [ ] |
| 111 | 2079 | Mat Na Xong Hoi | 4 | [ ] |
| 112 | 114 | Nuoc Rua Tay / Diet Khuan | 10 | [ ] |
| 113 | 2091 | San Pham Cham Soc Khac | 12 | [ ] |
| 114 | 2095 | Bot Cao Rau | 3 | [ ] |
| 115 | 2039 | Dao Cao Rau | 13 | [ ] |
| 116 | 2282 | May Cao Rau | 1 | [ ] |
| 117 | 2083 | Bao Cao Su | 33 | [ ] |
| 118 | 2087 | Gel Boi Tron | 4 | [ ] |
| 119 | 2097 | Khan Giay / Khan Uot | 56 | [ ] |

### Thuc Pham Chuc Nang (11 categories, ~136 SP)

| # | ID | Category | SP | Xong |
|---:|---:|---|---:|:---:|
| 120 | 194 | Lam Dep Da | 66 | [ ] |
| 121 | 302 | Lam Dep Toc | 5 | [ ] |
| 122 | 195 | Ho Tro Giam Can | 5 | [ ] |
| 123 | 309 | Bo Gan / Giai Ruou | 6 | [ ] |
| 124 | 312 | Dau Ca / Bo Mat | 8 | [ ] |
| 125 | 321 | Ho Tro Sinh Ly | 4 | [ ] |
| 126 | 308 | Ho Tro Tieu Hoa | 10 | [ ] |
| 127 | 311 | Ho Tro Tim Mach | 4 | [ ] |
| 128 | 307 | Ho Tro Xuong Khop | 4 | [ ] |
| 129 | 305 | Tang Suc De Khang | 10 | [ ] |
| 130 | 2186 | Vitamin / Khoang Chat | 14 | [ ] |

**TONG: 130 categories, ~11,407 SP**

---

## Thong so may tinh

| Thong so | Gia tri |
|---|---|
| CPU | i5-11400H @ 2.70GHz (12 threads) |
| RAM | 7.6 GB |
| Latency toi Hasaki | ~0.47s/request |
| **Workers de xuat** | **3** (an toan, khong overload server) |

### Benchmark toc do

| Workers | Toc do (SP/s) | Tang x | Uoc tinh 11K SP |
|---|---|---|---|
| 1 | 1.4 | 1x | ~2 gio |
| 3 | 3.7 | 2.6x | **~50 phut** |
| 5 | ~5-6 | ~4x | ~30 phut |

---

## Buoc 1: Chuan bi (1 lan)

```bash
cd tech2ai
uv sync
```

---

## Buoc 2: Cao tat ca 130 categories

```bash
# Cao tat ca — moi category 1 file rieng (hasaki_category_{id}.jsonl)
# Tu dong skip categories da cao xong
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --workers 3
```

**Neu bi ngat (Ctrl+C, mat mang):** Chay lai **CUNG LENH** tren → scraper tu dong skip categories da co file:
```
[1/130] Category My Pham High-End (id=1907) — SKIP (67 SP already saved)
[2/130] Category Tay Trang Mat (id=48) — SKIP (306 SP already saved)
...
[15/130] --- Category: Mat Na Moi (id=71) ---    ← tiep tuc tu day
```

**Hoac cao tung nhom (khuyen nghi):**

```bash
# Cao 10 categories dau tien (~1,664 SP, ~8 phut)
for id in 1907 48 19 35 1857 75 2005 2266 7 2011; do
  uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --category $id --workers 3
done

# Kiem tra ket qua
wc -l scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_category_*.jsonl
```

---

## Buoc 3: Kiem tra ket qua

```bash
# Dem tong SP da cao
wc -l scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_category_*.jsonl

# Xem 1 SP
head -1 scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_category_19.jsonl | \
    uv run python3 -c "import sys,json; d=json.loads(sys.stdin.read()); \
    print('title:', d['title']); print('price:', d['price']); \
    print('brand:', d['brand']); print('features:', len(d['features']), 'chars')"
```

---

## Buoc 4: Merge vao Tiki pipeline

```bash
cp scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_category_*.jsonl \
   scraping_data_tv/Tiki/Tiki_dataset_scrape/

uv run scraping_data_tv/Data_processing_for_Vietnamese_data/day1_data_curation.py
```

---

## Cac lenh tham khao

| Lenh | Muc dich | Output |
|------|----------|--------|
| `--test` | Test 1 category, 5 SP | `hasaki_test_{date}.jsonl` |
| `--report` | Scan categories, in so SP | `hasaki_categories_report.md` |
| `--category 11 --workers 3` | Cao 1 category | `hasaki_category_11.jsonl` |
| `--workers 3` | Cao tat ca (skip xong) | `hasaki_category_{id}.jsonl` x 130 |

---

## Xu ly su co

### Bi ngat giua chung (Ctrl+C)
- **Categories DA XONG** (co file): tu dong SKIP khi chay lai
- **Category DANG CAO** (chua xong): file bi thieu → xoa file do roi chay lai:
```bash
# Xoa file cua category dang cao do (vi du: id=75)
rm scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_category_75.jsonl
# Chay lai → chi cao lai category 75, skip cac category da xong
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --workers 3
```

### Hasaki rate-limit (429)
- Scraper tu doi 60s + rotate session
- Neu van bi: giam workers `--workers 1`

### Muon cao lai 1 category tu dau
```bash
# Xoa file cu roi chay lai
rm scraping_data_tv/e-commerce-sites-scraping/scrap/data/hasaki_category_11.jsonl
uv run scraping_data_tv/e-commerce-sites-scraping/scrap/hasaki_scraper.py --category 11 --workers 3
```

---

*Tao ngay: 2026-04-11. Hasaki API JSON, 130 categories, ~11,407 SP.*
