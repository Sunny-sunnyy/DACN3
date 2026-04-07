# Step 1: Thu nghiem lay raw data tu Shopee VN

**Ngay:** 2026-04-07
**Muc tieu:** Tim cach lay raw data san pham tu shopee.vn
**Ket qua:** Tat ca approach tu dong deu bi Shopee chong bot chan. Can nghien cuu them.

---

## Tong ket cac approach da thu

### Approach 1: curl_cffi + Shopee Search API (00_test_shopee_api.py)
- **Ket qua:** 403 Forbidden, error 90309999
- **Nguyen nhan:** curl_cffi khong chay JavaScript -> khong nhan duoc cookies tu Shopee (cookies = 0). Shopee set cookies qua JS.
- **File:** `00_test_shopee_api.py`

### Approach 2: curl_cffi + Full browser headers (01_test_shopee_v2.py)
- Thu nhieu ky thuat: full headers, nhieu API endpoints, mobile API
- **Ket qua:** Tat ca deu 403, error 90309999
- Shopee API v2 tra 404 (khong con ton tai)
- **File:** `01_test_shopee_v2.py`

### Approach 3: curl_cffi + Cookies tu browser (02_test_with_cookies.py)
- Lay cookies tu Chrome DevTools (F12 -> Network -> Copy Cookie header)
- **Ket qua:** 403 nhung `"is_login":true` -> cookies hoat dong (Shopee nhan dien da login)
- **Nguyen nhan:** Shopee yeu cau them cac headers bao mat do JavaScript tao ra (af-ac-enc-dat, af-ac-enc-sz-token, x-sap-sec...), chi cookies khong du
- **File:** `02_test_with_cookies.py`

### Approach 4: curl_cffi + TOAN BO headers tu cURL command (03_test_full_headers.py)
- Copy toan bo request bang "Copy as cURL (bash)" tu DevTools
- Bao gom: cookies + af-ac-enc-dat + af-ac-enc-sz-token + x-sap-sec + x-csrftoken + 22 headers
- **Ket qua:** Status 200 NHUNG response van la error 90309999
- **Nguyen nhan:** Cac security tokens (af-ac-enc-dat, x-sap-sec...) la ONE-TIME USE hoac het han trong vai giay. Khong the copy-paste duoc.
- **File:** `03_test_full_headers.py`

### Approach 5: Selenium (04_test_selenium.py)
- Dung Selenium WebDriver mo Chrome that
- **Ket qua:** Bi redirect sang trang login (`/buyer/login`)
- **Nguyen nhan:** Shopee detect Selenium qua `navigator.webdriver = true` va cac dau hieu khac
- **File:** `04_test_selenium.py`

### Approach 6: undetected-chromedriver (05_test_undetected.py, 06_test_chrome_profile.py)
- `undetected-chromedriver` tu dong patch Chrome de an `navigator.webdriver`
- Thu ca 2 cach: profile moi va Chrome profile co san
- **Ket qua:** Van bi redirect sang login
- **Luu y:** ChromeDriver version phai match Chrome (Chrome 145 -> `version_main=145`)
- Chrome profile tu Linux (`~/.config/google-chrome`) bi loi "session not created: chrome not reachable"
- Profile moi: van bi redirect login
- **File:** `05_test_undetected.py`, `06_test_chrome_profile.py`

### Approach 7: Playwright + Stealth (07_test_playwright.py)
- Playwright voi `playwright-stealth` plugin (anti-detection)
- Persistent context de luu session
- **Ket qua:** Van bi redirect sang login
- Khi login thu cong trong browser, sau do nhan Enter thi page da bi close (loi TargetClosedError)
- **Luu y:** `playwright-stealth` v2 dung `Stealth` class, khong phai `stealth_sync`
  - Dung: `stealth.apply_stealth_sync(context)` 
  - Sai: `stealth_sync(page)` (khong ton tai)
- **File:** `07_test_playwright.py`

---

## Phan tich chong bot cua Shopee

Shopee co **nhieu lop chong bot** rat manh:

1. **JavaScript cookies:** Cookies duoc set boi JS runtime, khong qua HTTP response headers -> curl_cffi (khong chay JS) khong nhan duoc
2. **Encrypted security tokens:** `af-ac-enc-dat`, `af-ac-enc-sz-token`, `x-sap-sec` la cac token do JS tao ra, one-time use, het han nhanh
3. **Bot detection:** Phat hien Selenium (`navigator.webdriver`), Playwright, va ca undetected-chromedriver
4. **Login wall:** Khi detect bot hoac DevTools, bat buoc login + CAPTCHA (chon hinh)
5. **CAPTCHA:** Sau khi login, co the yeu cau xac thuc hinh anh (chon xe dap, cau thang...)

### Quan sat quan trong tu user:
- **Chrome binh thuong (khong DevTools):** Search page hien san pham KHONG can login
- **Chrome + F12 (DevTools):** Bat dang nhap
- **Sau dang nhap + CAPTCHA:** Moi xem duoc search results trong DevTools
- URL khi chua login: `shopee.vn/search?keyword=tai+nghe`
- URL sau login: `shopee.vn/search?keyword=tai+nghe&is_from_signup=true`

---

## Huong di tiep (can nghien cuu)

### Option A: Playwright persistent + login thu cong (sua loi hien tai)
- Fix loi TargetClosedError (page bi dong khi login redirect)
- Sau khi login 1 lan, session duoc luu -> cac lan sau khong can login
- Can xu ly: login -> CAPTCHA -> search page -> scroll -> parse
- **Uu diem:** Mien phi, kiem soat duoc
- **Nhuoc diem:** Can login thu cong lan dau, session co the het han

### Option B: Dung Chrome CDP (Chrome DevTools Protocol)
- Mo Chrome that (bang tay), login Shopee binh thuong
- Ket noi Playwright/Selenium vao Chrome da mo qua CDP
- `chrome --remote-debugging-port=9222`
- Playwright: `browser = p.chromium.connect_over_cdp("http://localhost:9222")`
- **Uu diem:** Dung chinh browser that cua user, khong bi detect
- **Nhuoc diem:** Can mo Chrome truoc, giu Chrome chay

### Option C: Apify (dich vu tra phi)
- Dung Shopee Product Scraper Actor tren Apify
- Apify xu ly proxy, anti-bot, CAPTCHA tu dong
- **Uu diem:** De dung, on dinh, scale duoc
- **Nhuoc diem:** Ton phi, phu thuoc dich vu ben thu 3

### Option D: Tim dataset co san
- Kaggle, HuggingFace co the co dataset Shopee VN
- Khong can cao, chi can download va xu ly
- **Uu diem:** Nhanh nhat, khong bi block
- **Nhuoc diem:** Du lieu co the cu, khong du truong thong tin

### Option E: Nghien cuu sau hon ve Shopee anti-bot
- Tim hieu cach tao `af-ac-enc-dat`, `x-sap-sec` tokens
- Reverse engineer Shopee JS runtime
- **Uu diem:** Giai phap lau dai
- **Nhuoc diem:** Rat kho, ton thoi gian

---

## Dependencies da cai

```bash
uv add selenium              # Selenium WebDriver
uv add undetected-chromedriver  # Anti-detect Chrome
uv add playwright playwright-stealth  # Playwright + stealth
uv run playwright install chromium    # Playwright Chromium browser
```

## Luu y ky thuat

- Chrome version hien tai: **145.0.7632.75**
- undetected-chromedriver can chi dinh version: `uc.Chrome(version_main=145)`
- playwright-stealth v2 API: `Stealth().apply_stealth_sync(context)`, KHONG phai `stealth_sync(page)`
- WSL2 co the truy cap Windows Chrome profile tai: `/mnt/c/Users/{username}/AppData/Local/Google/Chrome/User Data`
- Linux Chrome profile tai: `~/.config/google-chrome` (nhung bi loi khi dung voi undetected-chromedriver)

## Ket qua nghien cuu internet (2026-04-07)

### Nguon tham khao:
- [How to Scrape Shopee in 2026: 4 Easy Methods](https://roundproxies.com/blog/scrape-shopee/)
- [Advanced Anti-Bot Bypass Guide](https://www.bluetickconsultants.com/how-to-scrape-shopee-at-scale-advanced-anti-bot-bypass-guide/)
- [shopee-captcha-solver (GitHub)](https://github.com/gbiz123/shopee-captcha-solver)
- [Shopee Scraping Teardown (ScrapeOps)](https://scrapeops.io/websites/shopee/)
- [Shopee Scraper Toolkit 2025](https://kameleo.io/blog/shopee-scraper-toolkit)
- [Playwright Stealth for Scraping (ZenRows)](https://www.zenrows.com/blog/playwright-stealth)

### Tai sao cac approach truoc that bai:
1. **curl_cffi:** Shopee YEU CAU JavaScript de tao anti-bot tokens. Khong co JS runtime -> khong bao gio qua duoc.
2. **Selenium:** Expose `navigator.webdriver = true` + nhieu automation flags khac
3. **undetected-chromedriver:** Shopee detect hon ca webdriver flag — check canvas fingerprints, WebGL, behavioral patterns
4. **Playwright+stealth (lan dau):** Stealth chua duoc apply dung cach + thieu canvas randomization + thieu persistent context

### Giai phap can thu tiep:

**Option 1: Playwright + Stealth + Canvas + Persistent (FREE)**
- Dung `launch_persistent_context()` voi `user_data_dir` that
- Apply stealth TRUOC KHI navigate
- Them canvas fingerprint randomization bang init script
- Locale `vi-VN`, timezone `Asia/Ho_Chi_Minh`
- Headed mode (khong headless) cho lan dau login
- Sau khi login 1 lan, persistent context luu session -> khong can login lai
- Rate limit: 20 req/phut, delay 5-10s giua searches

**Option 2: Nodriver (FREE, moi hon undetected-chromedriver)**
- Library `nodriver` — "latest advancement in undetected automation"
- Duoc recommend boi shopee-captcha-solver repo
- Chua thu, can nghien cuu them

**Option 3: CDP — Chrome DevTools Protocol (FREE)**
- Mo Chrome that (bang tay), login binh thuong
- Ket noi Playwright vao Chrome qua `remote-debugging-port=9222`
- Shopee khong phan biet duoc vi la Chrome that cua user

**Option 4: SadCaptcha (TRA PHI)**
- Service tu dong giai CAPTCHA Shopee (puzzle, slide, image)
- Tich hop Playwright/Selenium bang 1 dong code
- Can API key tra phi

**Option 5: Nodriver (FREE, moi nhat)**
- `nodriver` la ke thua cua undetected-chromedriver, dung CDP truc tiep
- Khong can ChromeDriver binary, chi can Python + Chrome
- Loai bo hau het automation fingerprints (navigator.webdriver, JS checks)
- Async architecture, duoc recommend cho 2026
- Install: `pip install nodriver`
- Docs: https://oxylabs.io/blog/nodriver-web-scraping

---

## Dich vu tra phi va Dataset co san

### A. Dich vu Scraping API (tra phi)

| Dich vu | Gia | Free trial | Ho tro VN | Ghi chu |
|---------|-----|------------|-----------|---------|
| **Apify** | ~$0.50/1K requests | $5 free credits | Co (8 nuoc) | 2 actors: "Shopee API Scraper" va "Best Shopee Scraper" ($30/thang) |
| **Scrapeless** | Pay-per-success | Co (khong can the) | Chua ro | 99.98% success rate, 80M+ IPs |
| **Bright Data** | $1.50/1K requests | Co | Co | Ma giam gia APIS25 (25% off 6 thang). Co ban dataset san: $250/100K records |
| **SOAX** | $1/1K requests | Chua ro | Chua ro | Re nhat trong cac API services |
| **ScrapingBee** | Chua ro | 1000 free calls | Chua ro | |
| **SadCaptcha** | Tra phi API key | Khong | N/A | Chi giai CAPTCHA, khong scrape. Tich hop Playwright/Selenium |
| **Piloterr** | Chua ro | Co | Chua ro | Shopee Product Scraper API |

### B. Dataset co san (MIEN PHI hoac re)

| Dataset | Nguon | So luong | Quoc gia | Truong du lieu | Link |
|---------|-------|---------|---------|----------------|------|
| **Rebrowser Shopee Dataset** | HuggingFace + Kaggle | 22.1M records (10/2025 - 02/2026) | SEA (co VN) | item_id, name, price, price_before_discount, variants, stock, ratings, seller info | [HuggingFace](https://huggingface.co/datasets/rebrowser/shopee-dataset) / [Kaggle](https://www.kaggle.com/datasets/rebrowser/shopee-dataset) |
| **Shopee.vn Phone Dataset** | Kaggle | Chua ro | Vietnam | Dien thoai | [Kaggle](https://www.kaggle.com/datasets/joehidney/shopeevn-phone-product-dataset) |
| **Shopee Sales Data** | Kaggle | Chua ro | Chua ro | Sales 04-05/2023 | [Kaggle](https://www.kaggle.com/datasets/yoongsin/shopee-sample-data) |
| **Bright Data Shopee Dataset** | Bright Data | Co ban | SEA | Full product data | $250/100K records |

**Luu y Rebrowser dataset:**
- 22M+ records nhung sample chi 30K (0.14%). Full dataset can tra phi Rebrowser
- Cap nhat hang ngay, giu 30 ngay gan nhat
- Export CSV/JSON/JSONL/Parquet
- Co du lieu VN nhung chua ro ti le bao nhieu

### C. De xuat approach theo ngan sach

**Mien phi hoan toan:**
1. Thu Nodriver (option 5) — kha nang thanh cong cao nhat trong cac tool free
2. Thu CDP — ket noi vao Chrome that cua user (option 3)
3. Download Rebrowser sample (30K records) tu HuggingFace — co the du cho MVP

**Ngan sach thap ($5-30):**
1. Apify free tier ($5 credits) — thu scrape 5K-10K san pham
2. Bright Data free trial — thu scrape voi proxy rotation
3. Mua them Rebrowser data neu sample khong du

**Ngan sach trung binh ($30-100):**
1. Apify "Best Shopee Scraper" ($30/thang) — scrape khong gioi han
2. SOAX API ($1/1K) — 100K san pham = ~$100

---

## Files trong folder step1/

```
step1/
    00_test_shopee_api.py      # curl_cffi basic
    01_test_shopee_v2.py       # curl_cffi nhieu approach
    02_test_with_cookies.py    # curl_cffi + cookies tu browser
    03_test_full_headers.py    # curl_cffi + full cURL headers
    04_test_selenium.py        # Selenium basic
    05_test_undetected.py      # undetected-chromedriver
    06_test_chrome_profile.py  # undetected-chromedriver + Chrome profile
    07_test_playwright.py      # Playwright + Stealth
    cookies.txt                # Cookies tu browser (het han)
    curl_command.txt           # Full cURL command tu browser
    step1_notes.md             # File nay
    data/raw/                  # Output files (JSON, HTML, screenshots)
```
