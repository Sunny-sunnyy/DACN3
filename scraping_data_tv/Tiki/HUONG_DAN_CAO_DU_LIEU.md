# Huong dan cao du lieu Tiki tren may thue

## Tong quan

- **Muc tieu:** Cao ~100K san pham tu Tiki VN
- **Thoi gian:** ~6-10 gio voi 5 workers
- **Output:** JSONL files trong folder `Tiki_dataset_scrape/`
- **Khong can WSL**, chay truc tiep tren Windows
- **Tu dong xu ly OVER_CAP:** Categories >2000 SP duoc chia khoang gia tu dong (Price-Range Slicing)

---

## Buoc 1: Cai dat moi truong (1 lan duy nhat, ~5 phut)

### 1.1. Cai Python 3.12+

Tai va cai tu: https://www.python.org/downloads/release/python-31313/

Kiem tra:
```cmd
python --version
```

Cài git: https://git-scm.com/install/windows
cài vscode: https://code.visualstudio.com/download

### 1.2. Cai uv (package manager)

Mo PowerShell (Run as Administrator):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Kiem tra:
```cmd
uv --version
```

### 1.3. Clone repo va cai dependencies

```cmd
git clone https://github.com/Sunny-sunnyy/DACN3.git
cd DACN3/tech2ai
uv sync
```

Chi can `uv sync` — tu dong cai tat ca thu vien can thiet:
- `curl_cffi` (HTTP client, Chrome impersonation)
- `pydantic` (data models)
- `tqdm` (progress bar)
- Va cac dependencies khac cua project

---

## Buoc 2: Chay scraper

### 2.1. Test truoc (2 phut)

```cmd
cd DACN3\tech2ai
uv run scraping_data_tv/Tiki/run_scraper.py --test
```

Ket qua mong doi:
```
=== TEST MODE: Tivi, 50 san pham ===
...
Done: ~30-50 san pham
```

Neu thanh cong -> chuyen sang buoc 2.2.

### 2.2. Cao tat ca 47 categories (~6-10 gio voi 5 workers)

```cmd
uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 5
```

Scraper se:
- Chay tuan tu 47 sub-categories
- **Tu dong xu ly OVER_CAP** (27 categories >2000 SP): chia khoang gia, lay ~96-100% SP
- Hien thi progress: so SP, toc do, ETA (thoi gian con lai)
- Tu dong save checkpoint moi 100 SP
- Neu bi ngat (mat mang, tat may...) -> chay lai lenh tren, se resume tu cho dang

### 2.3. Cac lenh khac (tuy chon)

```cmd
# Cao 1 category cu the
uv run scraping_data_tv/Tiki/run_scraper.py --category 1795

# Gioi han so SP moi category (nhanh hon, it data hon)
uv run scraping_data_tv/Tiki/run_scraper.py --all --max 500

# Cao 1 category voi ten tu dat
uv run scraping_data_tv/Tiki/run_scraper.py --category 1795 --name "Dien thoai"
```

---

## Buoc 3: Kiem tra ket qua

### 3.1. Kiem tra files output

Sau khi chay xong, kiem tra folder:
```
tech2ai/scraping_data_tv/Tiki/Tiki_dataset_scrape/
    tiki_8129.jsonl      # Linh kien may tinh
    tiki_8214.jsonl      # Phu kien dien thoai
    tiki_2150.jsonl      # Noi that
    tiki_1951.jsonl      # Dung cu nha bep
    ...                  # 47 files JSONL
```

### 3.2. Dem tong so san pham

Mo PowerShell:
```powershell
# Dem tong dong (= tong san pham) trong tat ca JSONL files
Get-ChildItem "scraping_data_tv\Tiki\Tiki_dataset_scrape\*.jsonl" | ForEach-Object { (Get-Content $_.FullName).Count } | Measure-Object -Sum
```

Hoac dung Python:
```cmd
uv run python -c "from pathlib import Path; files = list(Path('scraping_data_tv/Tiki/Tiki_dataset_scrape').glob('*.jsonl')); total = sum(sum(1 for _ in open(f, encoding='utf-8')) for f in files); print(f'Tong: {total:,} san pham tu {len(files)} files')"
```

### 3.3. Xem thu 1 san pham

```cmd
uv run python -c "import json; line = open('scraping_data_tv/Tiki/Tiki_dataset_scrape/tiki_1795.jsonl', encoding='utf-8').readline(); p = json.loads(line); print(json.dumps(p, ensure_ascii=False, indent=2))"
```

---

## Buoc 4: Tai files ve may ca nhan

### Files CAN tai ve:

```
scraping_data_tv/Tiki/Tiki_dataset_scrape/    <-- DU LIEU CHINH (tat ca JSONL)
scraping_data_tv/Tiki/checkpoints/             <-- Checkpoint (de resume neu can)
```

### Files KHONG can tai:

```
scraping_data_tv/Tiki/step1/                   # Scripts test, khong can
scraping_data_tv/Tiki/Github/                  # Repos tham khao, khong can
scraping_data_tv/Tiki/Docs/                    # Docs, khong can
```

### Cach tai:

**Cach 1: Nen zip roi tai (nhanh nhat)**

Mo PowerShell tren may thue:
```powershell
cd DACN3\tech2ai

# Zip du lieu JSONL
Compress-Archive -Path "scraping_data_tv\Tiki\Tiki_dataset_scrape" -DestinationPath "Tiki_dataset_scrape.zip"

# Zip checkpoints (can thiet de resume buoi sau)
Compress-Archive -Path "scraping_data_tv\Tiki\checkpoints" -DestinationPath "Tiki_checkpoints.zip"
```

Sau do tai 2 file zip ve may ca nhan (qua Remote Desktop, Google Drive, hoac scp):
- `Tiki_dataset_scrape.zip` — du lieu san pham
- `Tiki_checkpoints.zip` — tien do (de resume neu can cao tiep)

**Cach 2: Push len GitHub**

```cmd
cd DACN3\tech2ai
git add scraping_data_tv/Tiki/Tiki_dataset_scrape/
git commit -m "Them du lieu Tiki 100K san pham"
git push
```

Sau do `git pull` tren may ca nhan. Luu y: GitHub gioi han file 100MB, JSONL thuong nho hon nhieu.

**Cach 3: Push len HuggingFace (tot nhat cho dataset lon)**

```cmd
uv add datasets huggingface_hub
uv run python -c "
from datasets import load_dataset
ds = load_dataset('json', data_files='scraping_data_tv/Tiki/Tiki_dataset_scrape/*.jsonl')
ds.push_to_hub('YOUR_USERNAME/tiki-products-vn')
"
```

---

## Cao nhieu buoi (sang/chieu) tren may thue khac nhau

Scraper co checkpoint tu dong — khi chay lai se **bo qua san pham da cao** va tiep tuc tu cho dang.

Da test thuc te:
```
Lan 1: cao 30 SP  -> checkpoint luu 30 IDs
Lan 2: chay lai   -> "Resuming: 30 already done, To scrape: 73 items"
Ket qua: 30 + 73 = 103 SP (dung, khong trung lap)
```

### Quy trinh: Buoi sang cao -> Luu -> Buoi chieu cao tiep

**Buoi sang (may thue 1):**

```cmd
:: 1. Clone repo + cai dat
git clone https://github.com/Sunny-sunnyy/DACN3.git
cd DACN3\tech2ai
uv sync

:: 2. Chay scraper
uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 3

:: 3. KHI MUON DUNG: nhan Ctrl+C (scraper tu dong save checkpoint)

:: 4. TRUOC KHI TRA MAY: push data + checkpoint len GitHub
git add scraping_data_tv/Tiki/Tiki_dataset_scrape/ scraping_data_tv/Tiki/checkpoints/
git commit -m "Du lieu Tiki buoi sang - XX san pham"
git push
```

**Buoi chieu (may thue 2, hoac cung may):**

```cmd
:: 1. Clone hoac pull code moi nhat (co checkpoint + data tu buoi sang)
git clone https://github.com/Sunny-sunnyy/DACN3.git
cd DACN3\tech2ai
uv sync

:: Hoac neu cung may:
git pull

:: 2. Chay lai CUNG LENH — scraper tu dong resume
uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 3
:: Se hien: "Resuming: XX already done" cho cac category da cao

:: 3. Khi xong hoac muon dung: push lai
git add scraping_data_tv/Tiki/Tiki_dataset_scrape/ scraping_data_tv/Tiki/checkpoints/
git commit -m "Du lieu Tiki buoi chieu - XX san pham"
git push
```

### Luu y quan trong

- **LUON push truoc khi tra may** — mat checkpoint = cao lai tu dau
- **Ctrl+C an toan** — scraper save checkpoint moi 100 SP, mat toi da ~100 SP gan nhat
- **Khong can sua gi** — cung 1 lenh `--all --workers 3`, scraper tu biet bo qua SP da cao
- **2 files can push**: `Tiki_dataset_scrape/` (data) + `checkpoints/` (tien do)
- **Checkpoint chi luu Step 3 (Detail), KHONG luu Step 1 (Listing).** Khi chay lai, Step 1 (lay danh sach IDs) se chay lai tu dau — mat ~10 phut cho categories OVER_CAP. Step 3 moi resume tu checkpoint (bo qua SP da cao). Khong mat data, chi mat thoi gian listing lai.

---

## Price-Range Slicing (tu dong)

Scraper tu dong phat hien va xu ly categories >2000 SP:

```
Category total: 14,478 (OVER_CAP 2000) — using Price-Range Slicing
    Range 0-50,000: 2,500 SP
    -> Splitting: 0-25,000 | 25,000-50,000
        Range 0-25,000: 1,200 SP       ← OK, lay binh thuong
        Range 25,000-50,000: 1,300 SP   ← OK, lay binh thuong
    Range 50,000-100,000: 1,800 SP      ← OK
    ...
  Slicing done: 13,935 unique items (coverage: 96%)
```

- 27/47 categories se dung Price-Range Slicing tu dong
- 20/47 categories <2000 SP → lay binh thuong (khong doi)
- **Khong can thao tac gi them** — scraper tu xu ly

---

## Tong chi phi uoc tinh

| May thue | Workers | Toc do | Thoi gian 100K | Chi phi |
|----------|---------|--------|----------------|---------|
| RTX 4060 Ti (5K/h) | 3 | ~3 SP/s | ~9 gio | ~45,000d |
| RTX 4060 Ti (5K/h) | 5 | ~4.5 SP/s | ~6 gio | ~30,000d |
| RTX 3090 (8K/h) | 3 | ~4 SP/s | ~7 gio | ~56,000d |
| RTX 3090 (8K/h) | 5 | ~6 SP/s | ~4.5 gio | ~36,000d |

Luu y: Thoi gian listing tang ~2-4 gio do Price-Range Slicing (nhieu query hon).
Detail van la bottleneck chinh (~80% tong thoi gian).

Chia thanh 2-3 buoi (sang/chieu): tong chi phi tuong duong, chi khac la resume giua cac buoi.

---

## Xu ly su co

### Scraper bi ngat giua chung (Ctrl+C, mat mang, tat may)
Chay lai cung lenh — tu dong resume tu checkpoint:
```cmd
uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 3
```

Category da hoan thanh se skip ngay (khong chay lai listing):
```
=== [8129] Linh Kien May Tinh — already complete (9568 products), skipping ===
```

### Bi Tiki block (403/429)
Scraper tu dong doi 5 phut roi retry. Neu block lien tuc:
- Giam workers: `--workers 1`
- Hoac doi 30 phut roi chay lai

### Loi mang / timeout
Scraper tu dong retry 3 lan. Neu van loi: kiem tra mang, chay lai.

### Kiem tra tien do giua chung
```cmd
:: Dem tong SP da cao
uv run python -c "from pathlib import Path; files=list(Path('scraping_data_tv/Tiki/Tiki_dataset_scrape').glob('*.jsonl')); total=sum(sum(1 for _ in open(f,encoding='utf-8')) for f in files); print(f'Tong: {total:,} SP tu {len(files)} files')"

:: Xem trang thai tat ca categories (DONE / dang cao)
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

## Tham khao nhanh

| Lenh | Muc dich |
|------|----------|
| `uv run run_scraper.py --test` | Test nhanh (Tivi, 50 SP, 1 phut) |
| `uv run run_scraper.py --all --workers 3` | Cao tat ca, 3 workers (~10 gio) |
| `uv run run_scraper.py --all --workers 5` | Cao tat ca, 5 workers (~6 gio) |
| `uv run run_scraper.py --all --max 500 --workers 3` | Gioi han 500 SP/cat (~3 gio) |
| `uv run run_scraper.py --category 1795 --workers 3` | Cao 1 category |
| `uv run run_scraper.py --category 1951 --workers 3` | Test OVER_CAP (Dung cu nha bep, 14K SP) |

| Folder | Noi dung | Push len GitHub? |
|--------|---------|-----------------|
| `Tiki_dataset_scrape/` | Du lieu JSONL | **CO — bat buoc** |
| `checkpoints/` | Tien do resume | **CO — bat buoc** |
| `tiki_scraper/` | Code scraper | Da co san |
| `step1/`, `Github/`, `Docs/` | Test, tham khao | Khong can |

---

*Tao ngay: 2026-04-07. Cap nhat: Adaptive Price-Range Slicing, concurrent workers, resume guide.*
