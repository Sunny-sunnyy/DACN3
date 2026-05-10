# Báo cáo chi tiết: Xây dựng Mô hình Dự đoán Giá — "The Price Is Right"

> **Mục đích:** Tài liệu tự tham khảo, ghi lại toàn bộ quy trình từ dữ liệu thô đến mô hình production.  
> **Phạm vi:** Week 6 (Day 1–5) + Redemption DNN  
> **Ngày cập nhật:** 2026-05-08  
> **Thư mục code:** `scraping_data_tv/Data_processing_for_English_data/Code_Data_processing/`

---

## Hành trình tổng quan

```
Raw Amazon Data (~3M dòng)
    │
    ▼ Day 1 — Data Curation (lọc + làm sạch + lấy mẫu)
Filtered Dataset (820,000 items)
    │
    ▼ Day 2 — LLM Pre-processing (tiền xử lý bằng LLM)
Clean Summaries (item.summary)
    │
    ▼ Day 3 — Traditional ML Baselines (mô hình truyền thống)
XGBoost MAE = $68.23
    │
    ▼ Day 4 — Neural Network + Frontier LLMs
Vanilla NN MAE = $63.97 | Claude Opus 4.5 MAE = $47.10
    │
    ▼ Redemption — Deep Neural Network (ResNet-style)
DNN MAE = $46.49 ← Đánh bại Claude Opus 4.5!
```

---

## Day 1 — Data Curation (Thu thập và làm sạch dữ liệu)

### Mục tiêu
Lấy dữ liệu thô từ Amazon (~3M sản phẩm), lọc bỏ rác, chuẩn hóa, rồi lấy mẫu 820k items cân bằng để train model.

### Nguồn dữ liệu
- Dataset: `McAuley-Lab/Amazon-Reviews-2023` trên HuggingFace
- 8 categories: Automotive, Electronics, Office Products, Tools and Home Improvement, Cell Phones and Accessories, Toys and Games, Appliances, Musical Instruments
#### Link: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023
---

### File: `pricer/items.py` — Cấu trúc dữ liệu trung tâm

> **Vai trò:** Định nghĩa class `Item` — đơn vị dữ liệu xuyên suốt toàn dự án. - An Item is a data-point of a Product with a Price

```python
PREFIX = "Price is $"
QUESTION = "What does this cost to the nearest dollar?"

class Item(BaseModel):
    title: str
    category: str
    price: float
    full: Optional[str] = None      # Text thô sau khi scrub (Day 1)
    weight: Optional[float] = None  # Trọng lượng đã chuẩn hóa về pounds
    summary: Optional[str] = None   # Text sạch do LLM viết lại (Day 2)
    prompt: Optional[str] = None    # Prompt dùng cho fine-tuning
    id: Optional[int] = None
```

**Giải thích các field:**
- `full`: Text thô sau khi ghép title + description + features + details, đã xóa noise. Dùng ở Day 1-2.
- `summary`: Text sạch do LLM tóm tắt lại. Đây là input chính cho tất cả models từ Day 3 trở đi.
- `prompt`: Format dùng để fine-tune Llama: `"What does this cost?\n\n{text}\n\nPrice is ${price}.00"`

**Các method quan trọng:**

**`make_prompt(text) → str`**  
**Mục đích:** Tạo prompt fine-tuning cho Llama — ghép câu hỏi chuẩn + text mô tả + đáp án giá vào 1 chuỗi duy nhất theo format mà model được train để đọc.

**`test_prompt() → str`**  
**Mục đích:** Tạo prompt để evaluate mà không lộ đáp án — giống `make_prompt` nhưng bỏ phần giá ở cuối, dùng khi chạy inference để test model.

**`push_to_hub(name, train, val, test)` (class method)**  
**Mục đích:** Publish 3 splits (train/val/test) lên HuggingFace Hub dưới tên dataset chỉ định — cho phép load lại dataset từ bất kỳ máy nào mà không cần lưu file local.

**`from_hub(name) → (train, val, test)` (class method)**  
**Mục đích:** Load dataset từ HuggingFace Hub và chuyển đổi thành 3 list `Item` — đây là cách tất cả các notebook từ Day 3 trở đi lấy dữ liệu train/val/test.

**Lý do dùng Pydantic `BaseModel`:**  
Pydantic tự động validate kiểu dữ liệu khi tạo object. Nếu `price` không phải float, nó báo lỗi ngay — tránh data corruption âm thầm.

---

### File: `pricer/parser.py` — Lọc và làm sạch từng sản phẩm

> **Vai trò:** Nhận 1 datapoint thô từ Amazon → kiểm tra điều kiện → tạo `Item` hoặc trả về `None`.

**Hằng số lọc:**
```python
MIN_CHARS = 600    # Mô tả quá ngắn → không đủ thông tin để học giá
MIN_PRICE = 0.5    # Loại phụ kiện rác giá gần 0
MAX_PRICE = 999.49 # Loại hàng xa xỉ/công nghiệp (ngoài phạm vi tiêu dùng thông thường)
MAX_TEXT_EACH = 3000  # Giới hạn từng trường text
MAX_TEXT_TOTAL = 4000 # Giới hạn tổng text sau khi ghép

# Các trường cần xóa khỏi details (không cung cấp thông tin về giá)
REMOVALS = ["Part Number", "Best Sellers Rank", "Batteries Included?",
            "Batteries Required?", "Item model number"]
```

**Lý do chọn ngưỡng `MAX_PRICE = 999.49`:**  
Hàng tiêu dùng thông thường hiếm khi vượt $1000. Hàng trên mức này thường là thiết bị công nghiệp hoặc xa xỉ phẩm — model sẽ khó học vì quá ít mẫu và giá quá biến động.

**Các hàm:**

#### `simplify(text_list) → str`
**Mục đích:** Chuẩn hóa 1 trường text (có thể là list hoặc string) thành chuỗi đơn, xóa whitespace thừa và cắt theo giới hạn ký tự.
```python
# Xóa whitespace thừa và cắt text theo giới hạn MAX_TEXT_EACH
return str(text_list).replace("\n", " ").replace("\r", "")...strip()[:MAX_TEXT_EACH]
```
> Ghi chú: Hàm này xử lý cả list lẫn string vì Amazon trả về features dạng list Python.

#### `scrub(title, description, features, details) → str`
**Mục đích:** Ghép toàn bộ thông tin mô tả sản phẩm (title + description + features + details) thành 1 chuỗi sạch, loại bỏ noise như mã sản phẩm, key vô nghĩa, rồi cắt theo giới hạn tổng.
```python
# 1. Xóa các key vô nghĩa khỏi dict details
for remove in REMOVALS:
    details.pop(remove, None)

# 2. Ghép tất cả các trường thành 1 chuỗi
result = title + "\n" + simplify(description) + "\n" + simplify(features) + "\n" + json.dumps(details)

# 3. Xóa mã sản phẩm (Part Numbers) bằng Regex
pattern = r"\b(?=[A-Z0-9]{7,}\b)(?=.*[A-Z])(?=.*\d)[A-Z0-9]+\b"
# Pattern này khớp chuỗi có cả chữ HOA và số, dài ≥7 ký tự — đặc trưng của mã SKU/model
return re.sub(pattern, "", result).strip()[:MAX_TEXT_TOTAL]
```
> **Tại sao xóa Part Numbers?** Mã như "AP4980629", "WD12X10327" không mang thông tin về giá. Để lại sẽ tạo noise cho Bag of Words (mỗi mã là 1 từ riêng, không có ý nghĩa chung).

#### `get_weight(details) → float`
**Mục đích:** Lấy trọng lượng của 1 sản phẩm từ trường `Item Weight` trong details, rồi chuyển đổi về đơn vị pounds thống nhất. Trả về 0 nếu không có thông tin trọng lượng.
```python
# Chuyển đổi mọi đơn vị trọng lượng về pounds
weight_str = details.get("Item Weight")
# Xử lý: pounds, ounces, grams, milligrams, kilograms, hundredths of pounds
```
> **Lý do chuẩn hóa về pounds:** Amazon dùng nhiều đơn vị khác nhau tùy seller. Nếu không chuẩn hóa, Linear Regression sẽ nhầm 1 kg với 1 ounce — sai số khổng lồ.

#### `parse(datapoint, category) → Optional[Item]`
**Mục đích:** Cổng vào (entry point) của quá trình lọc — nhận 1 datapoint thô từ Amazon, kiểm tra toàn bộ điều kiện hợp lệ (giá, độ dài mô tả), rồi trả về `Item` nếu đạt hoặc `None` nếu loại bỏ.
```python
def parse(datapoint, category):
    try:
        price = float(datapoint["price"])  # Nếu price là string rỗng → ValueError → return None
    except ValueError:
        return None
    if MIN_PRICE <= price <= MAX_PRICE:    # Lọc giá hợp lệ
        full = scrub(title, description, features, details)
        if len(full) >= MIN_CHARS:         # Lọc mô tả quá ngắn
            return Item(title=title, category=category, price=price, full=full, weight=weight)
```
> **Lý do return `None` thay vì raise Exception:** Hàm này chạy song song cho hàng triệu records. Dùng None để bỏ qua datapoint lỗi mà không làm crash cả batch.

---

### File: `pricer/parser_v2.py` — Lọc và làm sạch từng sản phẩm (phiên bản nâng cao)

> **Vai trò:** Phiên bản nâng cao của `parser.py` — giữ nguyên interface `parse() → Item` nhưng bổ sung pipeline làm sạch text sâu hơn: xóa HTML, emoji, URL, stopwords, marketing spam, chuẩn hóa Unicode, lowercase.

**Dependencies bổ sung:** `beautifulsoup4` (xử lý HTML), `nltk` (stopwords tiếng Anh).

**Cách sử dụng:** Swap trong `loaders.py` chỉ cần đổi `from pricer.parser_v2 import parse`.

**Hằng số — Những thay đổi so với `parser.py`:**

```python
# Các trường cần xóa khỏi details (không cung cấp thông tin về giá)
REMOVALS = ["Part Number", "Best Sellers Rank", "Batteries Included?",
            "Batteries Required?", "Item model number"]

# NLTK English stopwords — load 1 lần khi import module
STOP_WORDS = set(stopwords.words("english"))
```

**Marketing Spam Patterns:**
```python
MARKETING_PHRASES = [
    r"click add to cart", r"add to cart now", r"buy now", r"order now",
    r"limited time offer", r"100% satisfaction guarantee",
    r"satisfaction guaranteed", r"money back guarantee",
    r"risk free", r"act now", r"best seller", r"free shipping",
    r"as seen on tv", r"scroll up and click", r"don't miss out",
    r"hurry up", r"what are you waiting for",
    r"makes a great gift", r"perfect gift", r"gift idea",
]
```
> **Tại sao xóa marketing spam?** Những cụm từ này xuất hiện ở mọi mức giá — sản phẩm $5 và $500 đều viết "Click Add to Cart". Để lại sẽ tạo false correlations trong BoW/TF-IDF, đặc biệt nếu một số seller spam nhiều hơn trong category nhất định.

**Regex Patterns (compiled 1 lần khi import):**
```python
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\S+@\S+\.\S+")
PRODUCT_CODE_PATTERN = re.compile(r"\b(?=[A-Z0-9]{7,}\b)(?=.*[A-Z])(?=.*\d)[A-Z0-9]+\b")
UPC_EAN_PATTERN = re.compile(r"\b\d{8,14}\b")           # Barcode UPC/EAN: 8-14 chữ số liên tiếp
REPEATED_PUNCT_PATTERN = re.compile(r"([!?.]){2,}")      # !!! → !, ... → .
EMPTY_BRACKETS_PATTERN = re.compile(r"\(\s*\)|\[\s*\]|\{\s*\}")  # (), [], {} rỗng
MULTI_SPACE_PATTERN = re.compile(r"\s{2,}")               # Gộp khoảng trắng
EMOJI_PATTERN = re.compile("[emoji unicode ranges]+")      # Emoticons, symbols, flags, dingbats
MISC_SYMBOLS_PATTERN = re.compile(r"[►▶▷◀◁◆◇○●■□▪▫✓✔✗✘...]")  # Arrows, bullets, checkmarks
```
> **Tại sao compile regex 1 lần?** `re.compile()` biên dịch pattern thành bytecode. Nếu gọi `re.sub(pattern, ...)` trực tiếp, Python phải compile lại mỗi lần — với 800k items × 10 patterns = 8 triệu lần compile thừa.

**Các hàm làm sạch (cleaning functions):**

#### `strip_html(text) → str`
**Mục đích:** Xóa toàn bộ HTML tags (`<br>`, `<p>`, `<b>`...) bằng BeautifulSoup, giải mã HTML entities (`&amp;` → `&`, `&#39;` → `'`, `&nbsp;` → space).
```python
def strip_html(text):
    soup = BeautifulSoup(text, "html.parser")
    clean = soup.get_text(separator=" ")      # Thay thế tags bằng space
    return html.unescape(clean)               # Decode HTML entities
```
> **Tại sao dùng BeautifulSoup thay vì regex?** HTML có thể nested, self-closing, malformed. Regex `<[^>]+>` bỏ sót nhiều trường hợp (ví dụ: `<br/>`, `<!-- comment -->`, `<div class="x">`). BeautifulSoup parse DOM tree → chính xác 100%.

#### `normalize_unicode(text) → str`
**Mục đích:** Chuẩn hóa Unicode về dạng NFKD (phân tách ký tự tổ hợp) và xóa control characters vô hình.
```python
def normalize_unicode(text):
    text = unicodedata.normalize("NFKD", text)  # "ﬁ" → "fi", "½" → "1/2"
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cc")
```
> **NFKD là gì?** Normalization Form Compatibility Decomposition — phân tách ký tự đặc biệt thành dạng tương đương ASCII. Ví dụ: ligature "ﬁ" thành "fi", fraction "½" thành chuỗi "1⁄2". Giúp tokenizer xử lý nhất quán.

#### `remove_emojis_and_symbols(text) → str`
**Mục đích:** Xóa toàn bộ emoji (😀, 🎉...) và misc symbols (★, ✓, ♥, →, ©, ™...) bằng Unicode range patterns.
> **Tại sao xóa symbols?** Sellers dùng ★★★★★, ✔, ► để decorate mô tả. Trong BoW, mỗi symbol trở thành 1 feature riêng không mang ý nghĩa về giá — chỉ tạo noise.

#### `remove_urls_and_emails(text) → str`
**Mục đích:** Xóa URLs (`https://...`, `www.xxx`) và email addresses. Các thông tin liên hệ seller không liên quan đến giá sản phẩm.

#### `remove_marketing_spam(text) → str`
**Mục đích:** Xóa 20+ cụm từ marketing phổ biến bằng regex pattern đã compile, case-insensitive.

#### `remove_codes(text) → str`
**Mục đích:** Xóa product codes (kế thừa từ `parser.py`) và bổ sung xóa UPC/EAN barcodes (chuỗi 8-14 chữ số liên tiếp).
> **Tại sao thêm UPC/EAN?** `parser.py` chỉ xóa mã có cả chữ và số (SKU). Nhưng nhiều listing còn chứa UPC (12 số) hoặc EAN (13 số) — đây là mã barcode, không mang ý nghĩa giá.

#### `collapse_punctuation(text) → str`
**Mục đích:** Gộp dấu câu lặp (`!!!` → `!`, `...` → `.`) và xóa ngoặc rỗng (`()`, `[]`, `{}`).

#### `remove_stopwords(text) → str`
**Mục đích:** Xóa stopwords tiếng Anh (the, is, at, which, on...) khỏi text đã lowercase.
```python
def remove_stopwords(text):
    words = text.split()
    return " ".join(w for w in words if w not in STOP_WORDS)
```
> **Trade-off khi xóa stopwords:** Giảm kích thước vocabulary → BoW/TF-IDF tập trung vào content words. Tuy nhiên, với transformer-based models (BERT, GPT), KHÔNG nên xóa stopwords vì model cần ngữ cảnh đầy đủ để hiểu ngữ nghĩa.

#### `normalize_whitespace(text) → str`
**Mục đích:** Gộp multiple spaces thành 1 space và strip đầu/cuối.

#### `clean_text(text) → str` — Pipeline tổng hợp
**Mục đích:** Gọi tuần tự tất cả cleaning functions theo đúng thứ tự — đây là hàm trung tâm được `simplify()` và `scrub()` sử dụng.
```python
def clean_text(text):
    text = strip_html(text)              # 1. Xóa HTML tags + decode entities
    text = normalize_unicode(text)        # 2. Chuẩn hóa Unicode NFKD
    text = remove_emojis_and_symbols(text)# 3. Xóa emoji + misc symbols
    text = remove_urls_and_emails(text)   # 4. Xóa URLs + emails
    text = remove_marketing_spam(text)    # 5. Xóa cụm marketing
    text = remove_codes(text)            # 6. Xóa mã sản phẩm + UPC/EAN
    text = collapse_punctuation(text)     # 7. Gộp dấu câu lặp
    text = text.lower()                  # 8. Lowercase
    text = remove_stopwords(text)         # 9. Xóa stopwords
    text = normalize_whitespace(text)     # 10. Gộp khoảng trắng
    return text
```
> **Thứ tự quan trọng:** `strip_html` phải chạy trước `remove_codes` (vì HTML entities có thể chứa số). `text.lower()` phải chạy trước `remove_stopwords` (vì STOP_WORDS là lowercase). `normalize_whitespace` chạy cuối vì các bước trước có thể tạo ra spaces thừa.

**Các hàm chính (kế thừa interface từ `parser.py`):**

#### `simplify(text_list) → str`
**Mục đích:** Giống `parser.py` nhưng gọi `clean_text()` thay vì chỉ xóa whitespace.

#### `scrub(title, description, features, details) → str`
**Mục đích:** Giống `parser.py` nhưng mỗi trường text đều đi qua `clean_text()` trước khi ghép.
```python
def scrub(title, description, features, details):
    for remove in REMOVALS:
        details.pop(remove, None)
    result = clean_text(title) + "\n"                     # Title qua full pipeline
    if description:
        result += simplify(description) + "\n"            # Description qua full pipeline
    if features:
        result += simplify(features) + "\n"               # Features qua full pipeline
    if details:
        result += clean_text(json.dumps(details)) + "\n"  # Details qua full pipeline
    return result.strip()[:MAX_TEXT_TOTAL]
```

#### `get_weight(details) → float` — Giữ nguyên logic từ `parser.py`

#### `parse(datapoint, category) → Optional[Item]` — Giữ nguyên interface từ `parser.py`

**So sánh tổng hợp `parser.py` vs `parser_v2.py`:**

| Cleaning step | `parser.py` | `parser_v2.py` |
|---|---|---|
| Whitespace normalization | `\n`, `\r`, `\t`, double space | Regex collapse toàn bộ multi-space |
| HTML tags | Không xử lý | BeautifulSoup strip toàn bộ |
| HTML entities | Không xử lý | `html.unescape()` (`&amp;` → `&`) |
| Unicode normalization | Không xử lý | NFKD + remove control chars |
| Emoji / Icons | Không xử lý | Regex pattern cho emoji + misc symbols |
| URL / Email | Không xử lý | Regex removal |
| Marketing spam | Không xử lý | 20+ phrases case-insensitive |
| Product codes | Regex 7+ alphanum | Giữ nguyên + thêm UPC/EAN (8-14 digits) |
| Stopwords | Không xử lý | NLTK English stopwords |
| Repeated punctuation | Không xử lý | `!!!` → `!`, `...` → `.`, xóa ngoặc rỗng |
| Lowercase | Không xử lý | Có |
| REMOVALS list | 5 fields | 10 fields |

> **Khi nào dùng `parser.py` vs `parser_v2.py`?**
> - `parser.py`: Khi muốn giữ text gần nguyên bản (cho LLM pre-processing ở Day 2 — LLM tự hiểu HTML, emoji).
> - `parser_v2.py`: Khi dùng text trực tiếp cho BoW/TF-IDF models (Day 3+) — cần text cực sạch để giảm vocabulary size và noise.

---

### File: `pricer/loaders.py` — Tải dữ liệu song song

> **Vai trò:** Load hàng triệu rows từ HuggingFace bằng đa tiến trình (multi-process) để giảm thời gian xử lý.

```python
CHUNK_SIZE = 1000  # Xử lý 1000 dòng mỗi lần — cân bằng giữa RAM và hiệu quả
WORKERS = max(os.cpu_count() - 1, 1)  # Dùng tất cả CPU trừ 1 nhân cho OS
```

**Các method của `ItemLoader`:**

#### `from_datapoint(datapoint)`
**Mục đích:** Chuyển đổi 1 dòng dữ liệu thô từ HuggingFace thành `Item` bằng cách gọi `parse()`. Trả về `None` nếu datapoint không hợp lệ.

#### `from_chunk(chunk)`
**Mục đích:** Xử lý 1 chunk gồm 1000 dòng liên tiếp — gọi `from_datapoint()` cho từng dòng rồi lọc bỏ các `None`. Đây là đơn vị công việc được phân phối cho mỗi process con.

#### `chunk_generator()`
**Mục đích:** Sinh (yield) từng chunk 1000 dòng từ dataset theo kiểu Generator (lười biếng) — không load toàn bộ dataset vào RAM cùng lúc, tiết kiệm bộ nhớ cho dataset hàng triệu dòng.

#### `load_in_parallel(workers)`
**Mục đích:** Hàm cốt lõi — phân phối các chunks cho nhiều process con chạy song song thông qua `ProcessPoolExecutor`. Thu thập và ghép kết quả từ tất cả processes lại.

#### `load(workers)`
**Mục đích:** Entry point của `ItemLoader` — tải dataset từ HuggingFace, chạy toàn bộ pipeline song song, in thống kê kết quả (số items hợp lệ, thời gian xử lý).

**Sơ đồ hoạt động:**
```
HuggingFace Dataset (94,327 rows cho Appliances)
    │
    ▼ chunk_generator()
[0:1000] → [1000:2000] → [2000:3000] → ... (95 chunks)
    │           │               │
    ▼           ▼               ▼
 Process 1   Process 2    Process 3  ...  (chạy song song)
    │           │               │
    └───────────┴───────────────┘
                │
                ▼ results.extend(batch)
         List[Item] (35,307 items hợp lệ)
```

**Tại sao dùng `ProcessPoolExecutor` thay vì `ThreadPoolExecutor`?**  
Python có GIL (Global Interpreter Lock) — chỉ cho phép 1 thread Python chạy tại một thời điểm. Với CPU-bound tasks như parsing text, `ThreadPoolExecutor` không giúp tăng tốc. `ProcessPoolExecutor` tạo ra các processes riêng biệt, mỗi process có Python interpreter riêng → thực sự chạy song song.

---

### Notebook: `day1.ipynb` — Luồng tổng thể Day 1

**Bước 1: Khám phá dữ liệu (EDA — Exploratory Data Analysis)**
```python
# Kiểm tra 1 datapoint thô
dataset[6]  # → dict với: title, features, description, price, details, images...

# Tìm sản phẩm đắt nhất → giúp quyết định ngưỡng MAX_PRICE
# Kết quả: TurboChef BULLET Microwave Oven → $21,095.62 (rõ ràng là thiết bị thương mại, loại bỏ)
```

**Bước 2: Load toàn bộ 8 categories**
```python
dataset_names = ["Automotive", "Electronics", "Office_Products",
                 "Tools_and_Home_Improvement", "Cell_Phones_and_Accessories",
                 "Toys_and_Games", "Appliances", "Musical_Instruments"]

items = []
for dataset_name in dataset_names:
    loader = ItemLoader(dataset_name)
    items.extend(loader.load())
# Kết quả: 2,933,577 items
```

**Bước 3: Deduplication (chống trùng lặp)**
```python
random.seed(42)
random.shuffle(items)  # Shuffle trước để dedup không bị bias theo thứ tự load

# Dedup theo title
seen = set()
items = [x for x in items if not (x.title in seen or seen.add(x.title))]

# Dedup theo full text (bắt trường hợp khác title nhưng cùng nội dung)
seen = set()
items = [x for x in items if not (x.full in seen or seen.add(x.full))]
# Kết quả: 2,887,890 items (bỏ ~46k bản trùng)
```
> **Tại sao shuffle trước khi dedup?** Nếu không shuffle, với mỗi cặp trùng, ta luôn giữ item đầu tiên theo thứ tự load (Automotive trước). Shuffle đảm bảo giữ ngẫu nhiên → phân phối category đều hơn.

**Bước 4: Weighted Sampling (lấy mẫu có trọng số)**
```python
SIZE = 820_000
prices = np.array([it.price for it in items])
categories = np.array([it.category for it in items])

# Chuẩn hóa giá về [0, 1]
p = (prices - prices.min()) / (prices.max() - prices.min() + 1e-9)

# Trọng số = giá bình phương → ưu tiên sản phẩm đắt
w = p**2

# Penalize (giảm trọng số) các category chiếm đa số
w[categories == "Tools_and_Home_Improvement"] *= 0.5   # Giảm 50%
w[categories == "Automotive"] *= 0.05                  # Giảm 95%

w = w / w.sum()  # Chuẩn hóa thành probability distribution
idx = np.random.choice(len(items), size=SIZE, replace=False, p=w)
sample = [items[i] for i in idx]
```

**Tại sao dùng `w = price²` thay vì `w = price`?**  
Hàm bậc hai tăng trưởng nhanh hơn → phân biệt rõ hơn giữa sản phẩm đắt và rẻ. Sản phẩm $100 được ưu tiên hơn sản phẩm $50 một cách rõ rệt hơn so với dùng linear weight. Kết quả: giá trung bình dataset tăng từ ~$59 lên ~$140 — gần với thực tế thị trường hơn.

**Kết quả số liệu:**

| Giai đoạn | Số mẫu |
|-----------|--------|
| Raw (8 categories) | 2,933,577 |
| Sau Deduplication (chống trùng lặp) | 2,887,890 |
| Final sample | 820,000 |
| Train / Val / Test | 800k / 10k / 10k |

**Dataset đã publish:** `SeanSunny/items_lite` (22k), `SeanSunny/items_full` (820k)

---

## Day 2 — Data Pre-processing (Tiền xử lý dữ liệu bằng LLM)

### Mục tiêu
Dùng LLM mạnh để "chắt lọc" text thô (`item.full`) thành summary sạch, chuẩn format (`item.summary`), có cấu trúc (Structured), ngắn gọn và giàu thông tin (High Signal-to-Noise Ratio). Kỹ thuật này gọi là Knowledge Distillation (chắt lọc kiến thức) — dùng model lớn để tạo data chất lượng cao cho model nhỏ hơn học.

### Vấn đề với `item.full`
```
WD12X10327 Rack Roller and stud assembly Kit (4 Pack) by AMI PARTS...
['【PARTS NUMBER】The dishwasher top rack wheels...', '【REPLACES PART】1811003, AP4980629, WD12X0330...']
{"Brand Name": "AMI PARTS", "Item Weight": "0.634 ounces"...}
```
→ Chứa: văn bản thô, không có cấu trúc, có mã sản phẩm còn sót, ngôn ngữ marketing, thông tin thừa, dấu câu còn sót.

→ Chứa các câu văn marketing như: 
- "Số lượng có hạn, mua ngay kẻo lỡ!" (Limited quantity, buy now!)
- "Chỉ còn vài sản phẩm trong kho." (Only a few left in stock.)
- "Ưu đãi kết thúc sau 24h." (Offer ends in 24 hours.)
- "Nhanh tay sở hữu ngay hôm nay." (Grab yours today.)
- "Chất lượng tuyệt hảo/hàng đầu." (Top-notch quality / Premium quality.)
- "Sản phẩm tốt nhất thị trường." (Best product on the market.)
- "Đảm bảo bạn sẽ hài lòng 100%." (100% satisfaction guaranteed.)
- "Hàng chính hãng, giá rẻ nhất." (Authentic goods, cheapest price.)
- "Thêm vào giỏ hàng ngay." (Add to cart now.)
- "Hãy nhấn nút mua để trải nghiệm sự khác biệt." (Click buy to experience the difference.)
- "Đừng bỏ lỡ cơ hội ngàn năm có một này." (Don't miss this once-in-a-lifetime opportunity.)




### Kết quả sau LLM pre-processing (`item.summary`)
```
Title: Dishwasher Top Rack Roller and Stud Assembly Kit
Category: Appliances
Brand: AMI PARTS
Description: Replacement wheel and stud assembly kit for dishwasher top racks.
Details: Includes 4 pieces, made from durable plastic, fits most major brands.
```
→ Sạch, chuẩn format, tập trung vào thông tin quan trọng.

---

### File: `pricer/preprocessor.py` — Tiền xử lý đồng bộ (1 item)

> **Vai trò:** Gọi LLM để rewrite 1 item text thành format chuẩn. Dùng trong production pipeline (`segment4/`).

```python
DEFAULT_MODEL_NAME = "groq/openai/gpt-oss-20b"
DEFAULT_REASONING_EFFORT = "low"  # "low" đủ cho task này, tiết kiệm chi phí

SYSTEM_PROMPT = """Create a concise description of a product. Respond only in this format...
Title: ...  Category: ...  Brand: ...  Description: 1 sentence.  Details: 1 sentence."""
```

**Class `Preprocessor`:**

#### `__init__(model_name, reasoning_effort)`
**Mục đích:** Khởi tạo preprocessor với model và cấu hình, đồng thời khởi tạo các bộ đếm theo dõi tổng token input, token output và chi phí tích lũy qua nhiều lần gọi API.

#### `messages_for(text) → list`
**Mục đích:** Đóng gói text thô vào format messages chuẩn của LiteLLM (list gồm system prompt + user message), sẵn sàng để gọi API.

#### `preprocess(text) → str`
**Mục đích:** Gọi LLM để viết lại text thô thành summary sạch theo format chuẩn (Title/Category/Brand/Description/Details), đồng thời cộng dồn thống kê token và chi phí sau mỗi lần gọi.

**Theo dõi chi phí:**
```python
self.total_input_tokens += response.usage.prompt_tokens
self.total_output_tokens += response.usage.completion_tokens
self.total_cost += response._hidden_params["response_cost"]
```
> Ghi chú: Tracking cost rất quan trọng khi chạy 800k items — giúp biết trước sẽ tốn bao nhiêu trước khi submit batch.

---

### File: `pricer/batch.py` — Xử lý hàng loạt (820k items)

> **Vai trò:** Xử lý 820k items bằng Groq Batch API — gửi 1 lần, server xử lý overnight, lấy kết quả sau.

**Tại sao dùng Batch API thay vì gọi đồng bộ?**
- Giảm 50% chi phí (batch discount)
- Không bị Rate Limit (giới hạn tốc độ gọi API)
- Không cần treo máy chờ (fire and forget)
- 820k × synchronous call ≈ cả ngày + $60. Batch: ~4 giờ + $30.

**Hằng số và config:**
```python
MODEL = "openai/gpt-oss-20b"  # Model trên Groq
BATCH_SIZE = 1_000             # 1000 items mỗi batch file
state = Path("batches.pkl")    # Lưu trạng thái để resume nếu bị ngắt
```

**Cấu trúc thư mục output:**
```
full/
├── batches/    # JSONL files gửi lên Groq
│   ├── 0_1000.jsonl
│   ├── 1000_2000.jsonl
│   └── ...
└── output/     # Kết quả tải về từ Groq
    ├── 0_1000.jsonl
    └── ...
```

**Class `Batch` — Methods theo thứ tự pipeline:**

#### `make_jsonl(item) → str`
**Mục đích:** Tạo 1 dòng JSON theo format chuẩn của Groq Batch API cho 1 item, bao gồm `custom_id` để định danh item và nội dung request gửi LLM.
```python
# Tạo 1 dòng JSON theo format Groq Batch API
{
    "custom_id": str(item.id),  # Quan trọng: dùng để map kết quả về item gốc
    "method": "POST",
    "url": "/v1/chat/completions",
    "body": {
        "model": MODEL,
        "messages": [system_prompt, {"role": "user", "content": item.full}],
        "reasoning_effort": "low"
    }
}
```
> **Tại sao cần `custom_id`?** Groq trả kết quả batch không theo thứ tự gửi. `custom_id = item.id` cho phép map chính xác response về đúng item, bất kể thứ tự.

#### `make_file()`
**Mục đích:** Ghi toàn bộ JSONL requests của 1 batch ra file trên disk, chuẩn bị sẵn để upload lên Groq server.

#### `send_file()`
**Mục đích:** Upload file JSONL lên Groq server và lưu lại `file_id` nhận được — ID này dùng để tạo batch job ở bước tiếp theo.

#### `submit_batch()`
**Mục đích:** Tạo batch job trên Groq từ file đã upload (dùng `file_id`), nhận `batch_id` để theo dõi trạng thái. Đây là lúc Groq bắt đầu xử lý các requests bất đồng bộ.

#### `is_ready() → bool`
**Mục đích:** Kiểm tra (poll) trạng thái của 1 batch job. Nếu `completed`, lưu lại `output_file_id` để tải kết quả. Trả về `True` khi xong, `False` khi vẫn đang xử lý.

#### `fetch_output()`
**Mục đích:** Tải file kết quả (JSONL) từ Groq server về disk sau khi batch đã completed.

#### `apply_output()`
**Mục đích:** Đọc file kết quả, dùng `custom_id` để tìm đúng item tương ứng, rồi gán nội dung LLM trả về vào `item.summary`. Đây là bước hoàn thành Knowledge Distillation (chắt lọc kiến thức).

**Class methods (chạy toàn bộ pipeline):**

#### `Batch.create(items, lite)`
**Mục đích:** Chia danh sách items thành các batch 1000 items, tạo object `Batch` cho từng phần và lưu vào danh sách chung `Batch.batches`.

#### `Batch.run()`
**Mục đích:** Chạy 3 bước đầu pipeline (make file → send → submit) cho tất cả batches theo thứ tự, sau đó server Groq xử lý bất đồng bộ.

#### `Batch.fetch()`
**Mục đích:** Poll tất cả batches chưa xong, tải và áp dụng kết quả ngay khi mỗi batch completed. In báo cáo số batch đã hoàn thành.

#### `Batch.save()`
**Mục đích:** Serialize trạng thái tất cả batches vào file pickle — cho phép resume từ điểm dừng nếu chương trình bị ngắt giữa chừng mà không mất tiến độ.

#### `Batch.load(items)`
**Mục đích:** Khôi phục trạng thái batches từ file pickle và gắn lại danh sách items (items không được lưu vào pickle để tiết kiệm dung lượng).

**Chi phí thực tế:**

| Dataset | Thời gian | Chi phí |
|---------|-----------|---------|
| Lite (22k) | Vài phút | < $1 |
| Full (820k) | Vài giờ | ~$30 |

---

## Day 3 — Evaluation Framework + Traditional ML Baselines

### Mục tiêu
Xây dựng hệ thống đánh giá chuẩn, rồi thử các mô hình truyền thống để có Baseline (đường cơ sở) so sánh.

**Triết lý "Start Simple" (bắt đầu từ đơn giản):**  
Mọi model phức tạp về sau phải đánh bại XGBoost. Nếu không qua được Baseline, nghĩa là có vấn đề ở đâu đó (data leakage, overfitting...).

---

### File: `pricer/evaluator.py` — Framework đánh giá

> **Vai trò:** Chạy 200 mẫu test song song, tính các metrics (MAE, MSE, r²), vẽ 2 biểu đồ phân tích kết quả.

**Hằng số:**
```python
WORKERS = 5        # 5 threads song song khi evaluate (I/O-bound nên thread phù hợp)
DEFAULT_SIZE = 200 # Đánh giá trên 200 mẫu test
```

**ANSI Color codes (in màu real-time trên terminal):**
```python
GREEN  = "\033[92m"   # Dự đoán tốt
YELLOW = "\033[93m"   # Dự đoán trung bình (hiển thị là "orange")
RED    = "\033[91m"   # Dự đoán tệ
RESET  = "\033[0m"
COLOR_MAP = {"red": RED, "orange": YELLOW, "green": GREEN}
```

---

**Class `Tester`:**

#### `__init__(predictor, data, title, size, workers)`
**Mục đích:** Khởi tạo Tester với model cần đánh giá và dữ liệu test. Chuẩn bị các list rỗng để thu thập kết quả trong quá trình chạy.
```python
def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE, workers=WORKERS):
    self.predictor = predictor   # Hàm nhận Item → trả về giá đoán (float hoặc string)
    self.data = data             # Test dataset (list of Item)
    self.title = title or self.make_title(predictor)
    self.size = size             # Số mẫu đánh giá (mặc định 200)
    self.titles = []             # Tên sản phẩm (rút gọn ≤ 40 ký tự)
    self.guesses = []            # Giá model đoán (float)
    self.truths = []             # Giá thực tế (float)
    self.errors = []             # |guess - truth| cho mỗi mẫu
    self.colors = []             # "green" / "orange" / "red" cho mỗi mẫu
    self.workers = workers
```

#### `make_title(predictor) → str` (staticmethod)
**Mục đích:** Tự động tạo tên hiển thị đẹp cho model từ tên hàm Python — tránh phải đặt tên thủ công cho từng model khi evaluate.
```python
@staticmethod
def make_title(predictor) -> str:
    return predictor.__name__.replace("__", ".").replace("_", " ").title().replace("Gpt", "GPT")
# Ví dụ: "gpt_4__1_nano" → "Gpt 4.1 Nano" → "GPT 4.1 Nano"
# Ví dụ: "random_pricer"  → "Random Pricer"
# Ví dụ: "xgb_model"      → "Xgb Model"
```

#### `post_process(value) → float` (staticmethod)
**Mục đích:** Chuẩn hóa output đa dạng của các models về kiểu float — LLM thường trả về string ("$180" hoặc "The price is $180."), trong khi Neural Network và truyền thống trả về float. Hàm này xử lý cả hai trường hợp.
```python
@staticmethod
def post_process(value):
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "")
        match = re.search(r"[-+]?\d*\.\d+|\d+", value)  # Tìm số đầu tiên trong chuỗi
        return float(match.group()) if match else 0      # Trả về 0 nếu không tìm thấy số
    else:
        return value  # Neural Net / XGBoost đã là float, trả thẳng
# Ví dụ: "$1,299.99"              → 1299.99
# Ví dụ: "The price is $45.00."  → 45.0
# Ví dụ: "Around $200 to $250"   → 200.0 (số đầu tiên)
```

#### `color_for(error, truth) → str`
**Mục đích:** Phân loại chất lượng dự đoán của 1 datapoint thành 3 mức màu dựa trên cả sai số tuyệt đối lẫn sai số tương đối — để hiển thị trực quan khi chạy và tô màu trên scatter plot.
```python
def color_for(self, error, truth):
    if error < 40 or error / truth < 0.2:    return "green"   # Sai số < $40 HOẶC < 20%
    elif error < 80 or error / truth < 0.4:  return "orange"  # Sai số < $80 HOẶC < 40%
    else:                                     return "red"     # Sai số lớn
```
> **Tại sao dùng cả tuyệt đối lẫn tương đối (điều kiện OR)?**  
> Một sản phẩm $500 có sai số $45 → tuyệt đối vượt $40 nhưng tương đối chỉ 9% → vẫn là dự đoán tốt → `green`.  
> Một sản phẩm $50 có sai số $15 → tuyệt đối tốt nhưng tương đối 30% → nằm ở ngưỡng `orange`.  
> Dùng OR để ưu tiên chiều có lợi hơn cho từng price range.

#### `run_datapoint(i) → tuple`
**Mục đích:** Xử lý toàn bộ pipeline cho 1 datapoint — gọi model dự đoán, chuẩn hóa output, tính sai số và phân loại màu. Đây là đơn vị công việc được phân phối song song bởi `ThreadPoolExecutor`.
```python
def run_datapoint(self, i):
    datapoint = self.data[i]
    value = self.predictor(datapoint)           # Gọi model → float hoặc string
    guess = self.post_process(value)            # Chuẩn hóa về float
    truth = datapoint.price                     # Giá thực tế
    error = abs(guess - truth)                  # Sai số tuyệt đối
    color = self.color_for(error, truth)        # Phân loại màu
    title = datapoint.title if len(datapoint.title) <= 40 else datapoint.title[:40] + "..."
    return title, guess, truth, error, color
```

#### `run()`
**Mục đích:** Điều phối toàn bộ quá trình evaluate — chạy `run_datapoint()` song song cho `size` mẫu, thu thập kết quả vào các list, in màu real-time ra terminal, rồi gọi `report()` khi xong.
```python
def run(self):
    with ThreadPoolExecutor(max_workers=self.workers) as ex:
        for title, guess, truth, error, color in tqdm(
            ex.map(self.run_datapoint, range(self.size)), total=self.size
        ):
            self.titles.append(title)
            self.guesses.append(guess)
            self.truths.append(truth)
            self.errors.append(error)
            self.colors.append(color)
            print(f"{COLOR_MAP[color]}${error:.0f} ", end="")  # In màu real-time
    self.report()
```
> **Tại sao dùng `ThreadPoolExecutor`** (không phải `ProcessPoolExecutor`)?  
> Evaluate LLM là I/O-bound: mỗi call đợi mạng trả về response. Thread đang chờ I/O sẽ nhả GIL, cho thread khác chạy → 5 threads gọi song song = tăng tốc ~5×. Ngược lại với CPU-bound task (parsing), ProcessPoolExecutor mới hiệu quả hơn.

#### `report()`
**Mục đích:** Tính 3 metrics tổng kết (MAE, MSE, r²), tạo tiêu đề chart, rồi gọi lần lượt 2 hàm vẽ biểu đồ.
```python
def report(self):
    average_error = sum(self.errors) / self.size          # MAE
    mse = mean_squared_error(self.truths, self.guesses)   # MSE
    r2  = r2_score(self.truths, self.guesses) * 100       # R² (nhân 100 để thành %)
    title = (
        f"{self.title} results<br>"
        f"<b>Error:</b> ${average_error:,.2f} "
        f"<b>MSE:</b> {mse:,.0f} "
        f"<b>r²:</b> {r2:.1f}%"
    )
    self.error_trend_chart()   # Biểu đồ 1
    self.chart(title)          # Biểu đồ 2
```

#### `evaluate(function, data, size, workers)` — Hàm tiện ích top-level
**Mục đích:** Wrapper một dòng để gọi nhanh mà không cần khởi tạo `Tester` thủ công — đây là hàm được dùng trực tiếp trong notebooks.
```python
def evaluate(function, data, size=DEFAULT_SIZE, workers=WORKERS):
    Tester(function, data, size=size, workers=workers).run()

# Cách dùng trong notebook:
evaluate(random_pricer, test)
evaluate(xgb_predict,   test)
evaluate(claude_opus,   test, workers=3)  # Ít thread hơn nếu API có rate limit
```

---

### Giải thích chi tiết 2 biểu đồ

Khi gọi `evaluate(random_pricer, test)`, sau khi chạy xong 200 samples, `report()` tự động vẽ 2 biểu đồ theo thứ tự: **Error Trend Chart trước**, **Scatter Plot sau**.

---

#### Biểu đồ 1 — Error Trend Chart (Running Average Error)

**Ví dụ output với Random Pricer:**
```
Title: "Random Pricer Error: $382.08 ± $37.47"
```

**Cách tính và ý nghĩa từng con số:**

**`$382.08` — MAE cuối cùng (Mean Absolute Error)**
```python
final_mean = running_means[-1]
# = sum(tất cả 200 errors) / 200
# = (|guess_1 - truth_1| + |guess_2 - truth_2| + ... + |guess_200 - truth_200|) / 200
```
Đây là giá trị MAE tích lũy tại n=200 — tức là trung bình sai số tuyệt đối trên toàn bộ 200 mẫu. Con số này cũng bằng `average_error` trong `report()`.

**`$37.47` — 95% Confidence Interval (Khoảng tin cậy 95%)**
```python
final_ci = ci[-1]
# ci[i] = 1.96 * (running_std[i] / sqrt(i+1))
# Tại n=200: ci[-1] = 1.96 * std_of_200_errors / sqrt(200)
```
Ý nghĩa: "Với 95% xác suất, MAE thực sự của model (nếu test trên vô hạn mẫu) nằm trong khoảng:
```
[$382.08 - $37.47, $382.08 + $37.47] = [$344.61, $419.55]
```
- `1.96` là z-score tương ứng 95% theo phân phối chuẩn (standard normal distribution)
- `std / sqrt(n)` là Standard Error of the Mean (SEM) — sai số chuẩn của ước lượng trung bình

> **Ý nghĩa thực tế:** CI rộng ($37.47) = kết quả kém tin cậy (model quá ngẫu nhiên). CI hẹp = kết quả ổn định. Nếu CI giữa 2 model chồng lên nhau → chênh lệch MAE giữa chúng chưa có ý nghĩa thống kê.

**Đường chính (màu đỏ đậm) — Running Mean Error:**
```python
running_sums = list(accumulate(self.errors))    # [e1, e1+e2, e1+e2+e3, ...]
x = list(range(1, n + 1))                       # [1, 2, 3, ..., 200]
running_means = [s / i for s, i in zip(running_sums, x)]
# running_means[0] = e1 / 1  (chỉ có 1 mẫu)
# running_means[7] = (e1+...+e8) / 8  (trung bình sau 8 mẫu)
# running_means[199] = tổng / 200 = MAE cuối
```
Đường này cho thấy MAE ước lượng "hội tụ" dần theo số mẫu. Ban đầu dao động mạnh (ít mẫu), càng về cuối càng ổn định.

**Vùng bóng xám (shaded band) — 95% CI band:**
```python
# Running standard deviation (tính thuần Python, không dùng numpy):
running_squares = list(accumulate(e * e for e in self.errors))
running_stds = [
    math.sqrt((sq_sum / i) - (mean ** 2))  # Var = E[X²] - (E[X])²
    for i, sq_sum, mean in zip(x, running_squares, running_means)
]
ci = [1.96 * (sd / math.sqrt(i)) for i, sd in zip(x, running_stds)]

upper = [m + c for m, c in zip(running_means, ci)]  # Biên trên
lower = [m - c for m, c in zip(running_means, ci)]  # Biên dưới

# Kỹ thuật Plotly để vẽ vùng bóng kín:
# x phải là [1,2,...,200, 200,199,...,1] → polygon đi qua upper rồi quay lại lower
fig.add_trace(go.Scatter(
    x = x + x[::-1],               # Đi từ trái sang phải (upper), rồi ngược lại (lower)
    y = upper + lower[::-1],        # Biên trên → nối → biên dưới ngược
    fill = "toself",                # Tô bên trong polygon
    fillcolor = "rgba(128,128,128,0.2)",
))
```
> `x[::-1]` là Python slice syntax để đảo ngược list — cần thiết để tạo polygon kín (closed polygon) mà Plotly điền màu bên trong.

**Hover text khi di chuột vào điểm bất kỳ:**
```
n = 8
Avg Error = $412.35
±95% CI = $58.20
```
- **`n = 8`**: bạn đang xem tại thời điểm đã xử lý 8 samples đầu tiên
- **`Avg Error = $412.35`**: `running_means[7]` = trung bình sai số của 8 mẫu đầu = `(e1+...+e8)/8`
- **`±95% CI = $58.20`**: `ci[7]` = `1.96 * std_8_samples / sqrt(8)` — CI rộng hơn nhiều so với cuối vì ít mẫu hơn

> **Quan sát:** CI thu hẹp dần khi n tăng (vì `sqrt(n)` ở mẫu số tăng). Đây là biểu hiện của Central Limit Theorem (định lý giới hạn trung tâm): ước lượng trung bình chính xác hơn khi có nhiều mẫu hơn.

---

#### Biểu đồ 2 — Scatter Plot (Predicted vs Actual)

**Title của biểu đồ:**
```
"Random Pricer results
Error: $382.08   MSE: 218,432   r²: -1.3%"
```

**Giải thích 3 metrics trong title:**

**1. `Error: $382.08` — MAE (Mean Absolute Error)**
```python
average_error = sum(self.errors) / self.size
# = sum(|guess_i - truth_i|) / 200
```
- Đơn vị: dollar ($) — dễ đọc, dễ hiểu
- Ý nghĩa: trung bình model sai bao nhiêu dollar cho mỗi sản phẩm
- Không phạt nặng outlier (sai $100 đóng góp đúng $100, không phải $10,000 như MSE)

**2. `MSE: 218,432` — Mean Squared Error**
```python
mse = mean_squared_error(self.truths, self.guesses)
# = sum((guess_i - truth_i)²) / 200
```
- Đơn vị: dollar² (bình phương dollar) — không có ý nghĩa trực tiếp về mặt đơn vị
- Ý nghĩa: phạt nặng những dự đoán sai lớn (outlier). Sai $100 → đóng góp 10,000 vào MSE. Sai $200 → đóng góp 40,000 (gấp 4 lần).
- `sqrt(MSE) = RMSE` (Root MSE) = $467 — gần với đơn vị dollar
- MSE lớn hơn MAE² nếu errors không đồng đều (có outlier). Ở đây: $382² = $146,000 < $218,432 → có nhiều dự đoán sai lớn kéo MSE lên.

**3. `r²: -1.3%` — Coefficient of Determination (Hệ số xác định)**

$R^2$ (Coefficient of Determination) - Hệ số xác định
- Ý nghĩa: Tỉ lệ % sự biến động của giá cả mà model giải thích được.

```python
r2 = r2_score(self.truths, self.guesses) * 100  # Nhân 100 để thành %
# r2_score tính: R² = 1 - SS_res / SS_tot
# SS_res = sum((truth_i - guess_i)²)     = tổng bình phương sai số của model
# SS_tot = sum((truth_i - mean_truth)²)  = tổng bình phương sai số của "đoán trung bình"
```

| R² | Ý nghĩa |
|----|---------|
| 100% | Model hoàn hảo — đoán đúng 100% |
| 50% | Model giải thích được 50% variance (phương sai) của giá |
| 0% | Model chỉ đoán bằng giá trị trung bình (tệ). |
| -1.3% | Model tệ hơn cả đoán trung bình (random pricer thì hiển nhiên) |

> **Tại sao Random Pricer có r² âm?**  
> Constant Pricer (luôn đoán $140.56) có r² = 0% vì `SS_res = SS_tot`.  
> Random Pricer đoán random → `SS_res > SS_tot` → R² < 0.

**Các thành phần của scatter plot:**

**Trục X — Actual Price (Giá thực tế):**  
Giá thực từ `datapoint.price` (float lấy từ Amazon dataset). Trục X và Y có cùng range `[0, max_val]` để đường y=x nằm chéo giữa.

**Trục Y — Predicted Price (Giá dự đoán):**  
Output từ `predictor(datapoint)` sau khi qua `post_process()`.

**Đường y = x (màu deepskyblue, nét đứt):**
```python
fig.add_trace(go.Scatter(
    x=[0, max_val],
    y=[0, max_val],
    mode="lines",
    line=dict(width=2, dash="dash", color="deepskyblue"),
    name="y = x",
))
```
Đường này biểu diễn "perfect prediction": nếu model đoán đúng hoàn toàn, tất cả điểm nằm trên đường này. Điểm nằm **trên** đường → model overestimate (đoán cao hơn thực). Điểm nằm **dưới** → underestimate.

**Màu sắc điểm (per `color_for()`):**
- Xanh: sai số < $40 hoặc < 20% → dự đoán tốt
- Cam: sai số < $80 hoặc < 40% → dự đoán trung bình
- Đỏ: sai số lớn → dự đoán tệ

**Hover text khi di chuột vào 1 điểm:**
```
Sony WH-1000XM5 Wireless Noise Cancel...
Guess=$234.00 Actual=$348.99
```
```python
df["hover"] = [
    f"{t}\nGuess=${g:,.2f} Actual=${y:,.2f}"
    for t, g, y in zip(df["title"], df["guess"], df["truth"])
]
# Gán customdata per trace (mỗi màu là 1 trace riêng trong Plotly):
for tr in fig.data:
    mask = df["color"] == tr.name
    tr.customdata = df.loc[mask, ["hover"]].to_numpy()
    tr.hovertemplate = "%{customdata[0]}<extra></extra>"
```
> `<extra></extra>` trong hovertemplate xóa phần "trace name" mặc định của Plotly — chỉ hiển thị đúng thông tin mình muốn.

**Đọc scatter plot như thế nào:**
```
Điểm rải khắp nơi (random)  → model không học được gì → r² âm
Điểm tập trung gần y=x      → model tốt → r² cao, MAE thấp
Điểm tập trung ở y=140      → model đoán giá trung bình mọi lúc → Constant Pricer
```

---

#### `plot_training_history(history)` — Training History Chart (dùng riêng cho DNN)
**Mục đích:** Vẽ 3 biểu đồ quan sát quá trình training DNN qua từng epoch — giúp phát hiện overfitting (Train Loss giảm nhưng Val Loss tăng) và xem learning rate schedule hoạt động đúng không.

```python
# history là dict với 4 keys, mỗi key là list có len = số epochs:
history = {
    "train_loss": [0.5486, 0.3817, 0.3225, 0.2804, 0.2447],
    "val_loss":   [0.4321, 0.4162, 0.4085, 0.3995, 0.3985],
    "val_mae":    [58.36,  56.98,  55.35,  53.70,  53.84],
    "lr":         [0.001, 0.000905, 0.000655, 0.000345, 0.0001],  # CosineAnnealing
}
```

- **Row 1 — Train vs Val Loss (normalized space):** Nếu train loss tiếp tục giảm nhưng val loss tăng → overfitting. Ở DNN này, cả hai đều giảm → training ổn định.
- **Row 2 — Validation MAE ($):** MAE thực tế trên val set (đơn vị dollar, sau de-normalize). Dùng để so sánh trực tiếp với models khác.
- **Row 3 — Learning Rate Schedule:** CosineAnnealing giảm lr từ 0.001 xuống 0 theo đường cosine. Giúp model "tinh chỉnh" nhỏ dần ở cuối training thay vì dao động quanh minimum.

---

### Notebook: `day3.ipynb` — Thực nghiệm các mô hình

**Load data:**
```python
train, val, test = Item.from_hub("SeanSunny/items_full")
# → 800k train, 10k val, 10k test
```

**Các mô hình và kết quả:**

#### 1. Random Pricer (đoán ngẫu nhiên)
```python
def random_pricer(item):
    return random.randrange(1, 1000)
# MAE = $382.08 — Baseline ngây thơ nhất
```

#### 2. Constant Pricer (luôn đoán giá trung bình)
```python
training_average = sum(prices) / len(prices)  # = $140.56
def constant_pricer(item):
    return training_average
# MAE = $106.18 — Bất kỳ model nào phải đánh bại con số này
```

#### 3. Linear Regression với Features thủ công
```python
def get_features(item):
    return {
        "weight": item.weight,
        "weight_unknown": 1 if item.weight == 0 else 0,  # Binary flag
        "text_length": len(item.summary)
    }
# MAE = $101.56
# Coefficients: weight=0.45, weight_unknown=-6.63, text_length=0.25
```
> Hệ số `weight_unknown = -6.63`: items không biết trọng lượng thường là phụ kiện rẻ tiền → đoán giá thấp hơn. LR tự học được điều này.

#### 4. NLP Linear Regression với Bag of Words (túi từ)
```python
vectorizer = CountVectorizer(max_features=2000, stop_words='english')
X = vectorizer.fit_transform(documents)  # Chỉ fit trên train!
regressor = LinearRegression()
regressor.fit(X, prices)
# MAE = $76.81 — Cải thiện lớn nhờ text features
```
> **Data Leakage (rò rỉ dữ liệu) cần tránh:** `vectorizer.fit()` chỉ được gọi trên `train`. Nếu fit trên toàn bộ data (train+test), model "biết trước" từ vựng của test set → MAE ảo thấp hơn thực tế.

**Giải thích chi tiết: Bag of Words + CountVectorizer + Linear Regression**

**Bag of Words (BoW) — Túi từ:**

**Định nghĩa:** BoW là kỹ thuật biểu diễn văn bản dưới dạng vector số bằng cách đếm tần suất xuất hiện của từng từ trong một từ điển cố định. Mỗi văn bản trở thành một vector có kích thước bằng số từ trong từ điển, bỏ qua hoàn toàn thứ tự từ.

**Ví dụ minh họa:**
```
Từ điển (vocabulary): ["guitar", "electric", "acoustic", "premium", "brand"]

Văn bản A: "electric guitar brand"   → [1, 1, 0, 0, 1]
Văn bản B: "acoustic guitar premium" → [1, 0, 1, 1, 0]
Văn bản C: "guitar guitar electric"  → [2, 1, 0, 0, 0]  (đếm số lần xuất hiện)
```

**Ưu điểm BoW:**
- Đơn giản, dễ implement, tính toán nhanh
- Hoạt động tốt với Linear Regression (mỗi từ = 1 feature độc lập)
- Interpretable: có thể xem hệ số (coefficient) của từng từ để biết từ nào ảnh hưởng giá

**Nhược điểm BoW:**
- Mất thứ tự từ: "guitar electric" = "electric guitar"
- Sparse vector: phần lớn phần tử = 0 (1 văn bản chỉ chứa vài trăm từ trong 2000 từ)
- Không hiểu ngữ nghĩa: "cheap" và "inexpensive" là 2 features hoàn toàn khác nhau

**CountVectorizer — Cơ chế hoạt động:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|----------|
| `max_features` | 2000 | Chỉ giữ 2000 từ xuất hiện nhiều nhất — giảm chiều vector, loại từ hiếm |
| `stop_words` | `'english'` | Loại bỏ stopwords (the, is, a, on...) vì không mang thông tin về giá |

**Quy trình 2 bước:**
1. `fit(train_documents)`: Học từ điển 2000 từ phổ biến nhất từ tập train
2. `transform(documents)`: Biến mỗi văn bản thành vector 2000 chiều (sparse matrix)

> **Tại sao chỉ 2000 từ?** Tập dữ liệu 800k items có hàng chục nghìn từ unique. Nhưng phần lớn là từ hiếm (xuất hiện <10 lần) — chúng không giúp model khái quát hóa. 2000 từ phổ biến nhất đã cover >90% thông tin hữu ích cho dự đoán giá.

**Linear Regression cho NLP — Định nghĩa toán học:**

Công thức: `y_hat = w1*x1 + w2*x2 + ... + w2000*x2000 + b`

Trong đó:
- `x_i` = số lần từ thứ `i` xuất hiện trong văn bản (hoặc 0/1 nếu binary)
- `w_i` = trọng số (weight/coefficient) mà model học được cho từ thứ `i`
- `b` = bias (hệ số tự do)
- `y_hat` = giá dự đoán

**Ý nghĩa trọng số:** Nếu `w["premium"] = +15.3` và `w["cheap"] = -8.7`, nghĩa là:
- Văn bản chứa từ "premium" → giá tăng ~$15.3
- Văn bản chứa từ "cheap" → giá giảm ~$8.7

**Hàm Loss — Ordinary Least Squares (OLS):**

`L = (1/n) * sum((y_i - y_hat_i)^2)` — tổng bình phương sai số.

Model tìm bộ trọng số `w` sao cho L nhỏ nhất. Có nghiệm chính xác (closed-form): `w = (X^T * X)^(-1) * X^T * y`. Với 800k samples x 2000 features, scikit-learn giải trong vài giây.

**Ưu điểm Linear Regression:** Nhanh, không cần iterative training. **Nhược điểm:** Chỉ học quan hệ tuyến tính — nếu "stainless steel kitchen" có giá khác "stainless steel watch", LR không bắt được interaction giữa các từ.


#### 5. Random Forest
```python
rf_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=4)
rf_model.fit(X[:15_000], prices[:15_000])  # Chỉ 15k subset vì chậm
# MAE = $72.28
```
> Random Forest = nhiều Decision Tree (cây quyết định) chạy song song, mỗi cây train trên random subset của data và features, kết quả cuối = average của tất cả cây.

**Giải thích chi tiết: Random Forest**

**Định nghĩa:** Random Forest là thuật toán Ensemble Learning (học tập hợp) kết hợp nhiều Decision Tree độc lập để đưa ra dự đoán chính xác hơn bất kỳ cây đơn lẻ nào.

**Thành phần cốt lõi — Decision Tree (Cây quyết định):**

Một Decision Tree chia dữ liệu bằng cách đặt câu hỏi nhị phân tại mỗi nút:
```
Từ "stainless" có xuất hiện không?
├── Có → Từ "professional" có không?
│         ├── Có → Giá ≈ $250
│         └── Không → Giá ≈ $120
└── Không → Từ "plastic" có không?
            ├── Có → Giá ≈ $25
            └── Không → Giá ≈ $80
```

**Kỹ thuật Bagging (Bootstrap Aggregating) — Trái tim của Random Forest:**

Random Forest kết hợp 2 kỹ thuật để giảm overfitting:

1. **Bootstrap sampling:** Mỗi cây train trên một sample ngẫu nhiên (có hoàn lại) từ dataset gốc. Cây 1 thấy items A, B, C, A. Cây 2 thấy items B, D, E, D.
2. **Random subspace:** Tại mỗi nút chia, cây chỉ xem xét một subset ngẫu nhiên của features (không phải toàn bộ 2000 từ). Đảm bảo các cây khác nhau → đa dạng hóa.
3. **Aggregating:** Kết quả cuối = Average dự đoán của tất cả cây → giảm variance (phương sai), tăng ổn định.

**Cấu hình và ý nghĩa tham số:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|----------|
| `n_estimators` | 100 | 100 cây quyết định — nhiều cây = ổn định hơn nhưng chậm hơn |
| `random_state` | 42 | Cố định seed → chạy lại cho kết quả giống nhau (reproducibility) |
| `n_jobs` | 4 | 4 CPU cores song song — RF song song tự nhiên vì các cây độc lập |

**Tại sao chỉ train trên 15k samples thay vì 800k?**

Random Forest lưu toàn bộ cấu trúc phân chia của mỗi cây trong bộ nhớ. Với 800k x 2000 features x 100 cây, thời gian training lên đến hàng giờ và RAM cần hàng chục GB. 15k subset là trade-off hợp lý giữa thời gian và kết quả.

**Ưu và nhược điểm:**

| Ưu điểm | Nhược điểm |
|---------|------------|
| Ít overfitting hơn single Decision Tree | Chậm với dataset lớn (800k) |
| Không cần chuẩn hóa features | Sử dụng nhiều RAM |
| Xử lý tốt non-linear relationships | Không hiệu quả với sparse, high-dimensional data (BoW 2000 chiều) |
| Dễ song song hóa | Kết quả khó interpret hơn Linear Regression |


#### 6. XGBoost (eXtreme Gradient Boosting — Tăng cường Gradient cực mạnh)
```python
xgb_model = xgb.XGBRegressor(n_estimators=1000, random_state=42, n_jobs=4, learning_rate=0.1)
xgb_model.fit(X, prices)  # Toàn bộ 800k samples
# MAE = $68.23 — Best Traditional ML
```
> **Điểm khác XGBoost với Random Forest:** RF xây cây song song độc lập. XGBoost xây cây tuần tự — mỗi cây tiếp theo tập trung sửa lỗi của cây trước (gradient descent trên tree space). Vì vậy XGBoost thường tốt hơn và nhanh hơn với dữ liệu tabular.

**Giải thích chi tiết: XGBoost (eXtreme Gradient Boosting)**

**Định nghĩa:** XGBoost là thuật toán Gradient Boosting — xây dựng cây quyết định tuần tự, mỗi cây mới tập trung sửa lỗi (residual) của tổng hợp các cây trước đó. Thuật toán thống trị các cuộc thi Kaggle từ 2015-2020 trước khi Deep Learning nổi lên.

**Nguyên lý Boosting — Khác biệt cốt lõi với Random Forest:**
```
Random Forest (Bagging):           XGBoost (Boosting):
Cây 1 ──┐                         Cây 1 → Sai số 1
Cây 2 ──┼── Average → Dự đoán        ↓
Cây 3 ──┘                         Cây 2 (sửa Sai số 1) → Sai số 2
                                     ↓
                                  Cây 3 (sửa Sai số 2) → ...
                                     ↓
                                  Tổng = Cây 1 + Cây 2 + Cây 3 + ...
```

**Cơ chế Gradient Boosting chi tiết:**

Tại mỗi iteration `t`:
1. Tính residual (phần sai): `r_i = y_i - y_hat_i(t-1)`
2. Fit một cây mới `f_t` lên residuals `r_i`
3. Cập nhật dự đoán: `y_hat_i(t) = y_hat_i(t-1) + eta * f_t(x_i)`

Trong đó `eta` (learning_rate) kiểm soát "mỗi cây đóng góp bao nhiêu".

**Cấu hình và ý nghĩa tham số:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|----------|
| `n_estimators` | 1000 | 1000 cây tuần tự — nhiều hơn RF vì mỗi cây nhỏ (weak learner) |
| `learning_rate` | 0.1 | Mỗi cây chỉ đóng góp 10% — tránh overfitting, cải thiện từ từ |
| `n_jobs` | 4 | Song song hóa ở mức feature selection trong mỗi cây |
| `random_state` | 42 | Reproducibility |

**Tại sao XGBoost train được trên 800k mà Random Forest chỉ 15k?**

XGBoost sử dụng histogram-based splitting — gom giá trị features vào bins (256 mặc định) thay vì xét từng giá trị. Giảm complexity đáng kể, tiết kiệm cả RAM lẫn thời gian. Ngoài ra, mỗi cây XGBoost nhỏ (max_depth mặc định = 6) — ít tốn bộ nhớ hơn cây đầy đủ của RF.

**Ưu và nhược điểm:**

| Ưu điểm | Nhược điểm |
|---------|------------|
| Hiệu quả nhất trên tabular/structured data | Không hiểu ngữ nghĩa (semantic) |
| Nhanh hơn RF trên dữ liệu lớn | Cần tuning nhiều hyperparameters |
| Built-in regularization (L1, L2) | Overfitting nếu n_estimators quá lớn |
| Xử lý missing values tự động | Tuần tự — không song song hoàn toàn |

**Tại sao XGBoost thắng Random Forest ($68 vs $72)?**
- XGBoost train trên toàn bộ 800k (RF chỉ 15k) → nhiều data = nhiều patterns.
- Boosting sửa lỗi iteratively → tối ưu hóa tốt hơn cho regression.
- XGBoost có regularization built-in mà RF không có ở mức tree level.


**Bảng kết quả Day 3:**

| Model | MAE | Ghi chú |
|-------|-----|---------|
| Random Pricer | $382.08 | Đoán ngẫu nhiên |
| Constant Pricer | $106.18 | Luôn đoán $140.56 |
| Linear Regression (manual) | $101.56 | 3 features thủ công |
| NLP Linear Regression | $76.81 | CountVectorizer 2000 từ |
| Random Forest | $72.28 | 100 cây, 15k samples |
| **XGBoost** | **$68.23** | 1000 cây, 800k samples |

---

## Day 4 — Neural Networks + Frontier LLMs

### Notebook: `day4.ipynb`

#### Cải tiến Vectorization (véc-tơ hóa): HashingVectorizer

```python
vectorizer = HashingVectorizer(n_features=5000, stop_words='english', binary=True)
X = vectorizer.fit_transform(documents)
```

**So sánh với CountVectorizer:**

| Tính năng | CountVectorizer | HashingVectorizer |
|-----------|-----------------|-------------------|
| Kích thước vector | 2000 | 5000 |
| Cần `fit()` | Có (học từ điển) | Không (stateless) |
| RAM usage | Cao (lưu từ điển) | Thấp |
| Reverse lookup | Được | Không được |
| `binary=True` | Không có | Có (chỉ 0/1, không đếm) |

> `binary=True`: Word "guitar" xuất hiện 1 lần hay 5 lần đều = 1. Phù hợp cho Neural Network hơn vì tránh bias với từ lặp nhiều.

**Giải thích chi tiết: HashingVectorizer và Hashing Trick**

**Hashing Trick (Kỹ thuật băm):**

Thay vì xây từ điển (vocabulary) rồi ánh xạ mỗi từ vào vị trí cố định, HashingVectorizer dùng hàm hash để tính vị trí:
```
hash("guitar") % 5000 = 1247  → position 1247 = 1
hash("premium") % 5000 = 3891 → position 3891 = 1
```

**Hash Collision (đụng độ):** Hai từ khác nhau có thể hash vào cùng vị trí: `hash("abc") % 5000 = hash("xyz") % 5000 = 42`. Xác suất collision thấp khi `n_features` đủ lớn (5000). Trade-off chấp nhận được để đổi lấy tốc độ và tiết kiệm RAM.

**Tại sao `binary=True` phù hợp cho Neural Network?**

Neural Network tự học trọng số (weights) cho mỗi feature. Nếu CountVectorizer đếm "guitar" xuất hiện 5 lần, giá trị 5 sẽ chiếm ưu thế so với các từ khác. Với `binary=True`, mọi từ đều bình đẳng (0 hoặc 1) — Neural Network tự quyết định từ nào quan trọng thông qua quá trình training weights.

**Tại sao tăng từ 2000 lên 5000 features?**

Neural Network có khả năng học non-linear relationships mạnh hơn Linear Regression. Nhiều features hơn = nhiều thông tin hơn cho NN khai thác. LR với 5000 features sparse dễ overfit, nhưng NN với hidden layers + ReLU xử lý tốt hơn.


#### Vanilla Neural Network (Mạng Neural cơ bản)

```python
class NeuralNetwork(nn.Module):
    def __init__(self, input_size):
        self.layer1 = nn.Linear(input_size, 128)  # 5000 → 128
        self.layer2 = nn.Linear(128, 64)
        # layer3 → layer7: nn.Linear(64, 64)
        self.layer8 = nn.Linear(64, 1)            # Output: 1 số (giá)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.relu(self.layer1(x))
        # ... qua 6 lớp ẩn với ReLU ...
        return self.layer8(x)  # Không có activation ở layer cuối (regression)
```

**Training loop (4 bước bất biến trong mọi Neural Network):**
```python
loss_function = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

for epoch in range(EPOCHS):
    for batch_X, batch_y in train_loader:
        optimizer.zero_grad()          # 1. Reset gradient từ batch trước

        outputs = model(batch_X)       # 2. Forward Pass — tính output
        loss = loss_function(outputs, batch_y)  # 3. Tính Loss (sai số)
        loss.backward()                # 4. Backward Pass — tính gradient
        optimizer.step()               # 5. Cập nhật weights
```

**Kết quả: MAE = $59.14** — Đánh bại XGBoost ($68.23)!

**Giải thích chi tiết các thành phần của Vanilla Neural Network**

**1. `nn.Linear(in_features, out_features)` — Lớp tuyến tính (Fully Connected Layer)**

**Định nghĩa:** Phép biến đổi tuyến tính `y = x * W^T + b`, trong đó:
- `W` là ma trận trọng số kích thước `(out_features, in_features)` — được khởi tạo ngẫu nhiên và cập nhật qua training
- `b` là bias vector kích thước `(out_features)` — mỗi neuron có 1 bias riêng
- Số parameters = `in_features * out_features + out_features`

**Ví dụ:** `nn.Linear(5000, 128)` có `5000 * 128 + 128 = 640,128` parameters.

**Ý nghĩa:** Mỗi neuron output nhận input từ tất cả neurons layer trước (fully connected), nhân với trọng số riêng, cộng bias → ra 1 giá trị. Layer này học "features nào quan trọng" và "kết hợp chúng như thế nào".

**2. `nn.ReLU()` — Rectified Linear Unit (Hàm kích hoạt)**

**Công thức:** `ReLU(x) = max(0, x)`
- Nếu `x > 0` → giữ nguyên `x`
- Nếu `x <= 0` → trả về `0`

**Tại sao cần hàm kích hoạt?**

Không có activation, nhiều lớp Linear xếp chồng vẫn chỉ là 1 phép biến đổi tuyến tính (Linear * Linear = Linear). ReLU phá vỡ tính tuyến tính → cho phép mạng học quan hệ phi tuyến phức tạp (ví dụ: "stainless steel" + "professional" → giá cao hơn nhiều so với tổng riêng lẻ).

**Tại sao ReLU thay vì Sigmoid/Tanh?**
- **Sigmoid** `1/(1+exp(-x))`: Output trong [0,1]. Vấn đề: gradient gần 0 khi `x` rất lớn/nhỏ → Vanishing Gradient → các lớp sâu không học được.
- **Tanh** `(exp(x)-exp(-x))/(exp(x)+exp(-x))`: Output trong [-1,1]. Cùng vấn đề Vanishing Gradient.
- **ReLU**: Gradient = 1 khi `x > 0` → không bao giờ biến mất. Tính toán cực nhanh (chỉ so sánh). Nhược điểm: "Dead ReLU" — neuron có `x < 0` mọi lúc sẽ gradient = 0 vĩnh viễn.

**3. `nn.MSELoss()` — Mean Squared Error Loss (Hàm mất mát)**

**Công thức:** `MSE = (1/n) * sum((y_pred_i - y_actual_i)^2)`

**Ý nghĩa:** Đo trung bình bình phương sai số giữa giá dự đoán và giá thực.

**Đặc điểm:**
- Phạt nặng outlier: sai $100 đóng góp 10,000, sai $200 đóng góp 40,000 (gấp 4 lần)
- Gradient luôn != 0 (khả vi mọi nơi) → thuận tiện cho gradient descent
- Phù hợp khi muốn model tránh sai lớn

**So sánh với L1Loss (MAE Loss):**
- L1Loss = `(1/n) * sum(|y_pred - y_actual|)` — robust hơn với outlier
- MSELoss phạt nặng outlier hơn — Vanilla NN dùng MSE, DNN Redemption chuyển sang L1 vì dữ liệu giá có nhiều outlier tự nhiên

**4. `optim.Adam(model.parameters(), lr=0.001)` — Optimizer (Thuật toán tối ưu)**

**Adam = Adaptive Moment Estimation** — kết hợp 2 ý tưởng:
1. **Momentum:** Giữ "quán tính" — nếu gradient liên tục cùng hướng, tăng tốc. Giống quả bóng lăn xuống dốc, càng lăn càng nhanh.
2. **Adaptive learning rate:** Mỗi parameter có learning rate riêng. Parameter ít cập nhật → lr lớn hơn. Parameter cập nhật nhiều → lr nhỏ hơn.

**Tham số `lr=0.001`:** Learning rate mặc định, kiểm soát kích thước bước nhảy mỗi lần cập nhật weights. Quá lớn → dao động không hội tụ. Quá nhỏ → hội tụ rất chậm.

**So sánh với SGD (Stochastic Gradient Descent):**
- SGD: `w = w - lr * gradient` — đơn giản nhưng cần tuning lr cẩn thận
- Adam: tự điều chỉnh lr cho từng parameter → ít cần tuning hơn, hội tụ nhanh hơn
- Adam là lựa chọn mặc định phổ biến nhất hiện nay cho Deep Learning

**5. Sơ đồ kiến trúc layer-by-layer:**
```
Input: Sparse Binary Vector [5000]
    │
    ▼ Layer 1: nn.Linear(5000, 128) + ReLU
[128]  ← Nén 5000 features xuống 128 chiều
    │
    ▼ Layer 2: nn.Linear(128, 64) + ReLU
[64]   ← Nén tiếp xuống 64 chiều
    │
    ▼ Layer 3-7: nn.Linear(64, 64) + ReLU  (×5 lớp giống nhau)
[64]   ← Giữ nguyên kích thước, học biểu diễn sâu hơn
    │
    ▼ Layer 8: nn.Linear(64, 1)  (KHÔNG có ReLU)
[1]    ← Output: giá dự đoán (regression → không giới hạn range)
```

**Tại sao layer cuối không có ReLU?**

ReLU ép output >= 0. Trong regression, model cần tự do dự đoán bất kỳ giá trị nào. Thêm activation ở output layer sẽ giới hạn range dự đoán — chỉ nên dùng ở hidden layers.

**Tổng số parameters: 669,249**
```
Layer 1: 5000 * 128 + 128 = 640,128
Layer 2: 128 * 64 + 64   = 8,256
Layer 3-7: (64*64+64) * 5 = 20,480
Layer 8: 64 * 1 + 1      = 65
Cộng: 669,249 (khớp với notebook)
```

**6. So sánh Vanilla NN vs Deep Neural Network (Redemption):**

| Đặc điểm | Vanilla NN (Day 4) | DNN Redemption |
|----------|-------------------|----------------|
| Số lớp | 8 (tất cả Linear + ReLU) | 10+ (Input + 8 ResidualBlocks + Output) |
| Hidden size | 128 → 64 (thu nhỏ dần) | 4096 (giữ nguyên xuyên suốt) |
| Parameters | 669,249 (~669K) | 289,128,449 (~289M) — gấp 432 lần |
| Skip Connection | Không có | Có — giải quyết Vanishing Gradient |
| LayerNorm | Không có | Có — ổn định phân phối activation |
| Dropout | Không có | 20% — chống overfitting |
| Loss | MSELoss | L1Loss — robust hơn với outlier |
| Optimizer | Adam (lr=0.001) | AdamW (lr=0.001, weight_decay=0.01) |
| LR Schedule | Không có | CosineAnnealingLR — giảm lr theo cosine |
| Gradient Clipping | Không có | max_norm=1.0 — ngăn gradient explosion |
| Target Transform | Raw price | Log-normalize — xử lý skewed distribution |
| Training data | 800k (raw) | 800k (normalized) |
| **MAE** | **$63.97** | **$46.49** |

**Tại sao DNN thắng Vanilla NN ($46 vs $64)?**
- **Skip Connection** cho phép train mạng sâu hơn mà không bị Vanishing Gradient
- **Log-normalize target** giúp model học đồng đều cho mọi price range (không bị dominated bởi sản phẩm đắt)
- **289M parameters** (gấp 432 lần) cho phép học patterns phức tạp hơn nhiều
- **L1Loss + AdamW + Gradient Clipping** = training ổn định và robust hơn

**Nhân vật đặc biệt: Human Baseline**
```python
human_predictions = []  # Đọc từ file human_out.csv
def human_pricer(item):
    idx = test.index(item)
    return human_predictions[idx]
# MAE = $87.62 — Model NLP cổ điển đã đánh bại con người!
```


#### Frontier LLMs (Mô hình ngôn ngữ lớn) — Zero-shot

```python
def messages_for(item):
    message = f"Estimate the price of this product. Respond with the price, no explanation\n\n{item.summary}"
    return [{"role": "user", "content": message}]

def gpt_4__1_nano(item):
    response = completion(model="openai/gpt-4.1-nano", messages=messages_for(item))
    return response.choices[0].message.content
# → "$180" (string) → post_process() → 180.0
```

**Kết quả Frontier Models (không train, chỉ dùng world knowledge):**

| Model | MAE |
|-------|-----|
| Claude Opus 4.5 | **$47.10** |
| Gemini 3 Pro | $50.54 |
| Grok 4.1 Fast | $57.62 |
| Gemini 2.5 Flash Lite | $58.68 |
| GPT-4.1 Nano | $62.51 |
| Vanilla Neural Network | $63.97 |

**Tại sao LLM Zero-shot đánh bại XGBoost trained trên 800k?**  
LLM có world knowledge từ pre-training trên internet — biết "Fender guitar" có giá khoảng bao nhiêu, "iPhone 15" khoảng bao nhiêu. XGBoost chỉ học từ pattern từ ngữ, không có semantic understanding (hiểu nghĩa ngữ nghĩa).

**Giải thích chi tiết: GPT-4.1 Nano và GPT-5.1**

**GPT-4.1 Nano (tương ứng GPT-4o-mini) — Mô hình nhanh, rẻ:**

```python
def gpt_4__1_nano(item):
    response = completion(model="openai/gpt-4.1-nano", messages=messages_for(item))
    return response.choices[0].message.content
```

**Đặc điểm:** Model nhỏ, tối ưu cho tốc độ và chi phí. MAE = $62.51 — đánh bại cả Vanilla NN ($63.97) và Human ($87.62) chỉ bằng world knowledge.

**GPT-5.1 — Mô hình mạnh nhất của OpenAI:**

```python
def gpt_5__1(item):
    response = completion(model="gpt-5.1", messages=messages_for(item), reasoning_effort='high', seed=42)
    return response.choices[0].message.content
```

**Đặc điểm:** Reasoning model mạnh nhất. Tham số `reasoning_effort='high'` bắt model suy nghĩ kỹ (chain-of-thought). Tuy nhiên, cho bài toán đoán giá, reasoning quá nhiều đôi khi gây "overthinking" — kết quả không nhất thiết tốt hơn.

**Kỹ thuật Zero-shot Inference:**

Không cần fine-tuning hay training. Chỉ cần 1 prompt đơn giản:
```python
def messages_for(item):
    message = f"Estimate the price of this product. Respond with the price, no explanation\n\n{item.summary}"
    return [{"role": "user", "content": message}]
```

LLM sử dụng kiến thức đã học trong quá trình pre-training (hàng trăm tỷ tokens từ internet) để ước lượng giá. Đây là sức mạnh của Transfer Learning — kiến thức học từ task A (đọc internet) chuyển sang task B (đoán giá).

**Công cụ: LiteLLM — Giao diện API thống nhất:**

Thư viện `litellm` cho phép gọi nhiều providers khác nhau (OpenAI, Anthropic, Google, xAI) bằng cùng 1 API. Chỉ cần đổi tham số `model` để chuyển từ GPT sang Claude sang Gemini mà không sửa code.

**Tham số `seed=42`:** Cố định output cho reproducibility (không phải tất cả providers đều hỗ trợ).


---

## Redemption — Deep Neural Network với Residual Blocks

### Mục tiêu
Xây mạng sâu 289 triệu parameters, train trên 800k samples — thử đánh bại Claude Opus 4.5 ($47.10).

---

### File: `pricer/deep_neural_network.py` — Kiến trúc mô hình

#### Class `ResidualBlock` — Khối cơ bản

**`__init__(hidden_size, dropout_prob)`**  
**Mục đích:** Xây dựng 1 residual block gồm 2 lớp Linear xen kẽ LayerNorm và ReLU — đây là đơn vị học cơ bản được lặp lại 8 lần trong DeepNeuralNetwork.

**`forward(x)`**  
**Mục đích:** Tính output của 1 residual block — biến đổi input qua các lớp, rồi cộng thêm chính input gốc (Skip Connection) trước khi qua ReLU cuối. Kỹ thuật này giải quyết vấn đề Vanishing Gradient (gradient biến mất) khi mạng quá sâu.

```python
class ResidualBlock(nn.Module):
    def __init__(self, hidden_size, dropout_prob):
        self.block = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),   # Ổn định phân phối activation
            nn.ReLU(),
            nn.Dropout(dropout_prob),    # Tắt ngẫu nhiên 20% neurons → tránh overfitting
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        residual = x           # Lưu input gốc
        out = self.block(x)    # Biến đổi qua các lớp
        out += residual        # Skip Connection (kết nối tắt): cộng input gốc vào
        return self.relu(out)
```

**Skip Connection (kết nối tắt) — Tại sao quan trọng?**  
Mạng sâu (nhiều lớp) bị "Vanishing Gradient (gradient biến mất)": khi lan truyền ngược (backprop), gradient nhân với nhiều số nhỏ → tiến gần về 0 → các lớp đầu không học được. Skip Connection tạo "đường tắt" cho gradient: `gradient = gradient_through_block + gradient_through_skip`. Phần skip luôn = 1, đảm bảo gradient không bao giờ = 0. Đây là ý tưởng cốt lõi của ResNet (2015).

**Giải thích chi tiết các thành phần trong ResidualBlock:**

**`nn.LayerNorm(hidden_size)` — Layer Normalization (Chuẩn hóa lớp):**

**Công thức:** `output = (x - mean(x)) / sqrt(var(x) + eps) * gamma + beta`
- `mean(x)` và `var(x)` tính trên tất cả features của 1 sample (1 hàng)
- `gamma` và `beta` là learnable parameters (được học qua training)
- `eps = 1e-5` tránh chia cho 0

**Tại sao cần LayerNorm?**

Không có normalization, activation values có thể trở nên rất lớn hoặc rất nhỏ khi đi qua nhiều lớp (Internal Covariate Shift). LayerNorm giữ phân phối activation ổn định quanh mean=0, std=1 → training nhanh hơn và ổn định hơn.

**LayerNorm vs BatchNorm:**
- **BatchNorm** chuẩn hóa theo batch (nhiều samples) — phụ thuộc batch size, không ổn định với batch nhỏ
- **LayerNorm** chuẩn hóa theo features (1 sample) — độc lập với batch size, phù hợp hơn cho NLP và mạng sâu

**`nn.Dropout(dropout_prob=0.2)` — Regularization:**

**Cơ chế:** Trong mỗi lần forward pass khi training, ngẫu nhiên tắt 20% neurons (set output = 0). Mỗi lần tắt những neurons khác nhau.

**Tại sao giúp chống overfitting?**
- Buộc mạng không được phụ thuộc vào bất kỳ neuron đơn lẻ nào
- Tương đương với training nhiều mạng con khác nhau và lấy trung bình (ensemble effect)
- **Khi inference** (`model.eval()`): Dropout tắt hoàn toàn — dùng toàn bộ neurons, nhân output với `(1 - dropout_prob)` để bù lại

**Luồng dữ liệu bên trong 1 ResidualBlock:**
```
Input x [4096]
    │
    ├─────────────────────────── (skip path: giữ nguyên x)
    │                                │
    ▼ Linear(4096, 4096)             │
    ▼ LayerNorm(4096)                │
    ▼ ReLU                           │
    ▼ Dropout(0.2)                   │
    ▼ Linear(4096, 4096)             │
    ▼ LayerNorm(4096)                │
    │                                │
    └──────────── (+) ───────────┘
                    │
                    ▼ ReLU
            Output [4096]
```


#### Class `DeepNeuralNetwork` — Kiến trúc tổng thể

**`__init__(input_size, num_layers, hidden_size, dropout_prob)`**  
**Mục đích:** Lắp ráp toàn bộ mạng DNN gồm 3 phần: Input Layer (chiếu từ 5000 features lên 4096 chiều), 8 Residual Blocks (học biểu diễn sâu), và Output Layer (nén xuống 1 số là giá dự đoán).

**`forward(x)`**  
**Mục đích:** Tính output của toàn bộ mạng — đưa input qua Input Layer → 8 Residual Blocks lần lượt → Output Layer để ra giá dự đoán cuối cùng.

```python
class DeepNeuralNetwork(nn.Module):
    def __init__(self, input_size, num_layers=10, hidden_size=4096, dropout_prob=0.2):
        # Input layer: 5000 → 4096
        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        # 8 Residual Blocks: 4096 → 4096 (giữ nguyên kích thước)
        self.residual_blocks = nn.ModuleList([
            ResidualBlock(hidden_size, dropout_prob) for _ in range(num_layers - 2)
        ])
        # Output layer: 4096 → 1
        self.output_layer = nn.Linear(hidden_size, 1)
```

**Sơ đồ kiến trúc:**
```
Input (5000 features)
    │
    ▼ Input Layer (Linear + LayerNorm + ReLU + Dropout)
[4096]
    │
    ▼ ResidualBlock × 8
[4096] ─────── (skip) ──────►
    │                         + → ReLU → [4096]
    └── Linear→LayerNorm→ReLU→Dropout→Linear→LayerNorm ──►
    │
    ▼ Output Layer (Linear)
[1] → predicted price
```

**Thông số:**
- 289,128,449 parameters (~289 triệu)
- Vanilla NN: 669,249 params → DNN gấp **432 lần**

**Ý nghĩa các tham số constructor:**

| Tham số | Mặc định | Ý nghĩa |
|---------|-----------|----------|
| `input_size` | 5000 | Số features từ HashingVectorizer |
| `num_layers` | 10 | Tổng số lớp: 1 input + 8 residual blocks + 1 output |
| `hidden_size` | 4096 | Kích thước ẩn xuyên suốt mạng — lớn hơn = nhiều parameters = học tốt hơn nhưng chậm hơn |
| `dropout_prob` | 0.2 | Tắt 20% neurons ngẫu nhiên mỗi forward pass |

**Tại sao `num_layers - 2`?** Từ `num_layers=10`, trừ 1 input layer và 1 output layer → còn 8 ResidualBlocks.

**`nn.ModuleList` vs Python list thường:**

`nn.ModuleList` đăng ký các sub-modules với PyTorch → `model.parameters()` bao gồm parameters của tất cả blocks. Python list thường không đăng ký → optimizer không cập nhật được weights của blocks.

#### Class `DeepNeuralNetworkRunner` — Training và Inference

**`setup()` — Chuẩn bị dữ liệu và model:**  
**Mục đích:** Khởi tạo toàn bộ pipeline training — vectorize text thành features, log-normalize giá, tạo model DNN, chọn device (CUDA/MPS/CPU), cấu hình optimizer và scheduler, rồi đóng gói thành DataLoader sẵn sàng để train.
```python
def setup(self):
    self.vectorizer = HashingVectorizer(n_features=5000, stop_words="english", binary=True)
    
    # Vectorize training data
    X_train_np = self.vectorizer.fit_transform(train_documents)
    self.X_train = torch.FloatTensor(X_train_np.toarray())
    
    # Log-normalize targets (chuẩn hóa giá theo log)
    y_train_log = torch.log(self.y_train + 1)  # log(price + 1)
    self.y_mean = y_train_log.mean()
    self.y_std = y_train_log.std()
    self.y_train_norm = (y_train_log - self.y_mean) / self.y_std  # Z-score normalization
    
    # AdamW với weight_decay để regularization
    self.optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    # Cosine Annealing LR: lr giảm dần theo đường cosine
    self.scheduler = CosineAnnealingLR(self.optimizer, T_max=10, eta_min=0)
```

**Tại sao Log-normalize giá?**  
Phân phối giá rất skewed (lệch phải): nhiều sản phẩm $10-100, ít sản phẩm $500-1000. MSE/L1 Loss trên raw price sẽ bị dominated bởi sản phẩm đắt. Log transform kéo phân phối về gần Gaussian → loss đồng đều hơn giữa các price ranges.

**Giải thích chi tiết: AdamW Optimizer**

```python
self.optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
```

**AdamW = Adam + Decoupled Weight Decay:**
- Giống Adam (Momentum + Adaptive LR) nhưng thêm **weight decay** đúng cách
- `weight_decay=0.01`: Mỗi step, weights được nhân với `(1 - lr * weight_decay)` → co nhỏ dần về 0
- Tác dụng: Regularization — ngăn weights trở nên quá lớn (overfitting)

**AdamW vs Adam:**
- **Adam** với L2 regularization: weight decay bị scale bởi adaptive learning rate → regularization không đều
- **AdamW**: weight decay độc lập với adaptive lr → regularization đồng đều hơn, kết quả tốt hơn
- AdamW được khuyến nghị là mặc định cho Deep Learning hiện đại (thay thế Adam)

**Giải thích chi tiết: CosineAnnealingLR**

```python
self.scheduler = CosineAnnealingLR(self.optimizer, T_max=10, eta_min=0)
```

**Cơ chế:** Giảm learning rate theo đường cosine từ giá trị ban đầu (0.001) xuống `eta_min` (0) trong `T_max` (10) epochs:
```
lr(t) = eta_min + 0.5 * (lr_init - eta_min) * (1 + cos(pi * t / T_max))

Epoch 1:  lr = 0.001000  (bước lớn — khám phá)
Epoch 3:  lr = 0.000655  (giảm dần)
Epoch 5:  lr = 0.000345  (bước nhỏ — tinh chỉnh)
Epoch 8:  lr = 0.000095  (gần minimum)
Epoch 10: lr = 0.000000  (dừng)
```

**Tại sao cosine thay vì giảm tuyến tính?**
- Cosine giảm nhanh lúc đầu (khi còn xa optimum), chậm lại cuối (tinh chỉnh gần optimum)
- Smooth hơn step decay (giảm đột ngột) → training ổn định hơn

**Giải thích chi tiết: Log-Normalization và De-normalization**

**Bước 1 — Log transform:** `y_log = log(price + 1)`
- `+1` để tránh `log(0)` (nếu giá = 0)
- Biến phân phối lệch phải (giá thường $10-100, ít $500+) thành gần Gaussian

**Bước 2 — Z-score normalize:** `y_norm = (y_log - mean) / std`
- Đưa về mean=0, std=1 → loss function hoạt động tốt hơn

**Khi inference — De-normalize:** `price = exp(pred * std + mean) - 1`
- Ngược lại quá trình normalize để ra giá thực tế ($)

**`model.train()` vs `model.eval()` — 2 chế độ của PyTorch:**

| Chế độ | Dropout | LayerNorm | Gradient |
|---------|---------|-----------|----------|
| `model.train()` | Bật (tắt 20% neurons ngẫu nhiên) | Dùng batch statistics | Tính gradient (cần cho backprop) |
| `model.eval()` | Tắt (dùng toàn bộ neurons) | Dùng running statistics | Thường kết hợp với `torch.no_grad()` |

`torch.no_grad()`: Tắt tính gradient hoàn toàn → tiết kiệm RAM và tăng tốc (không cần lưu computation graph).

**`DataLoader` và `TensorDataset` — Đóng gói dữ liệu:**

```python
self.train_dataset = TensorDataset(self.X_train, self.y_train_norm)
self.train_loader = DataLoader(self.train_dataset, batch_size=64, shuffle=True)
```

- `TensorDataset`: Ghép X (features) và y (target) thành cặp (x_i, y_i)
- `DataLoader`: Chia dataset thành batches, shuffle mỗi epoch
- `batch_size=64`: Mỗi lần forward pass xử lý 64 samples cùng lúc → tận dụng GPU parallelism
- `shuffle=True`: Xáo trộn thứ tự samples mỗi epoch → model không học thứ tự dữ liệu


**`train(epochs=5)` — Vòng lặp training nâng cao:**  
**Mục đích:** Chạy toàn bộ vòng lặp training — mỗi epoch duyệt qua toàn bộ train set theo batch, tính loss, backpropagation với gradient clipping, rồi đánh giá trên validation set và ghi lại lịch sử metrics để vẽ training chart sau.
```python
for epoch in range(1, epochs + 1):
    # Training phase
    self.model.train()
    for batch_X, batch_y in tqdm(self.train_loader):
        self.optimizer.zero_grad()
        outputs = self.model(batch_X)
        loss = self.loss_function(outputs, batch_y)  # L1Loss trên normalized space
        loss.backward()
        
        # Gradient Clipping (cắt gradient): ngăn gradient explode
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        
        self.optimizer.step()
    
    # Validation phase — không cần gradient
    self.model.eval()
    with torch.no_grad():
        val_outputs = self.model(self.X_val)
        # De-normalize về giá thực để tính MAE thực tế
        val_outputs_orig = torch.exp(val_outputs * self.y_std + self.y_mean) - 1
        mae = torch.abs(val_outputs_orig - self.y_val).mean()
    
    self.scheduler.step()  # Giảm learning rate theo cosine schedule
```

**Tại sao dùng L1Loss thay vì MSELoss?**  
MSELoss phạt nặng các outlier (sai số lớn bình phương). Dữ liệu giá có nhiều outlier tự nhiên. L1Loss (absolute error) robust hơn — không bị outlier "kéo" training quá mạnh.

**Giải thích chi tiết: Gradient Clipping**

```python
torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
```

**Vấn đề Gradient Explosion:** Với mạng 289M params và 10+ lớp, gradient có thể nhân lên rất lớn khi backprop qua nhiều lớp → weights cập nhật quá mạnh → training bất ổn (loss bất ngờ tăng vọt, NaN).

**Cơ chế clipping:**
1. Tính L2 norm của toàn bộ gradient: `total_norm = sqrt(sum(g_i^2))`
2. Nếu `total_norm > max_norm` (1.0): scale gradient xuống `g = g * (max_norm / total_norm)`
3. Nếu `total_norm <= max_norm`: giữ nguyên

Giống "giới hạn tốc độ" — bước cập nhật weights không bao giờ quá lớn, bất kể gradient tính ra bao nhiêu.


**`inference(item) → float`:**  
**Mục đích:** Dự đoán giá cho 1 sản phẩm mới — vectorize text summary, chạy forward pass qua model (không gradient), de-normalize kết quả về giá thực tế, đảm bảo giá không âm.
```python
def inference(self, item):
    self.model.eval()
    with torch.no_grad():
        vector = self.vectorizer.transform([item.summary])
        vector = torch.FloatTensor(vector.toarray()).to(self.device)
        pred = self.model(vector)[0]
        # De-normalize: exp(pred * std + mean) - 1
        result = torch.exp(pred * self.y_std + self.y_mean) - 1
    return max(0, result.item())  # Đảm bảo giá không âm
```

---

### Notebook: `redemption_train.ipynb` — Training thực tế

```python
runner = DeepNeuralNetworkRunner(train, val[:1000])
runner.setup()
# → "Deep Neural Network created with 289,128,449 parameters"
# → "Using cuda"
```

**Kết quả training (5 epochs, CUDA):**

| Epoch | Train Loss | Val Loss | Val MAE |
|-------|-----------|----------|---------|
| 1 | 0.5486 | 0.4321 | $58.36 |
| 2 | 0.3817 | 0.4162 | $56.98 |
| 3 | 0.3225 | 0.4085 | $55.35 |
| 4 | 0.2804 | 0.3995 | $53.70 |
| 5 | 0.2447 | 0.3985 | **$53.84** |

**Kết quả evaluate trên 200 test samples: MAE = $46.49** ← Đánh bại Claude Opus 4.5 ($47.10)!

**Model đã lưu:** `segment4/deep_neural_network.pth`

```python
runner.save('deep_neural_network.pth')  # Lưu state_dict
```

---

## Bảng xếp hạng cuối — "The Price Is Right" Leaderboard

| Hạng | Model | Loại | MAE |
|------|-------|------|-----|
| 1 | GPT-5.1 (giả định) | Frontier LLM | <$46 |
| **2** | **Deep Neural Network** | Specialized DL | **$46.49** |
| 3 | Claude Opus 4.5 | Frontier LLM | $47.10 |
| 4 | Gemini 3 Pro | Frontier LLM | $50.54 |
| 5 | Grok 4.1 Fast | Fast LLM | $57.62 |
| 6 | Gemini 2.5 Flash Lite | Fast LLM | $58.68 |
| 7 | GPT-4.1 Nano | Fast LLM | $62.51 |
| 8 | Vanilla Neural Network | Basic DL | $63.97 |
| 9 | XGBoost | Traditional ML | $68.23 |
| 10 | NLP Linear Regression | Traditional ML | $76.81 |
| 11 | Random Forest | Traditional ML | $72.28 |
| 12 | Human (giảng viên) | Con người | $87.62 |
| 13 | Constant Pricer | Trivial | $106.18 |
| 14 | Random Pricer | Trivial | $382.08 |

*Metric: MAE (Mean Absolute Error — Sai số tuyệt đối trung bình) trên 200 mẫu test*

---

## Bài học kỹ thuật cốt lõi

### 1. Data Quality > Model Complexity (Chất lượng dữ liệu > Độ phức tạp model)
Đầu tư $30 làm sạch dữ liệu qua LLM Batch API mang lại cải thiện lớn hơn nhiều so với tuning hyperparameter. "Garbage In, Garbage Out" — dữ liệu bẩn → model bẩn, bất kể kiến trúc nào.

### 2. Imbalanced Data (dữ liệu mất cân bằng) → Weighted Sampling (lấy mẫu có trọng số)
Automotive chiếm 33% nhưng phần lớn giá rẻ → model bias đoán thấp. `w = price²` + category penalty kéo phân phối về thực tế. Không xử lý → model production sẽ luôn underestimate (đoán thấp hơn thực tế).

### 3. Data Leakage (rò rỉ dữ liệu) — Nguy hiểm chết người
- `vectorizer.fit()` chỉ trên Train, không bao giờ trên Val/Test
- Deduplication (chống trùng lặp) TRƯỚC khi split train/val/test
- Shuffle trước khi dedup để tránh bias theo category

### 4. Specialized Model beats Generalist on Specific Task
DNN 289M params chỉ học 1 việc (đoán giá) → thắng Claude Opus 4.5 (hàng tỷ params biết mọi thứ). Trên task đủ hẹp với data đủ lớn, specialized model có lợi thế.

### 5. Skip Connection (kết nối tắt) = Giải pháp Vanishing Gradient
`out += residual` — 1 dòng code, nhưng cho phép train mạng 10+ lớp ổn định. Nền tảng của ResNet (2015) và hầu hết modern deep learning architecture.

### 6. Log Normalization cho skewed target
Giá có phân phối lệch → log transform giúp model học đồng đều hơn. De-normalize khi inference: `price = exp(pred * std + mean) - 1`.

### 7. Khi nào KHÔNG nên Fine-tune Frontier LLM
Fine-tune GPT-4o-mini trên 820k samples → kết quả tệ hơn. LLM đã có world knowledge về giá cả — 820k samples chỉ gây noise. Fine-tune LLM khi muốn thay đổi **style/format/behavior**, không phải knowledge.

---

## Sơ đồ file dependencies (phụ thuộc giữa các file)

```
day1.ipynb
    ├── pricer/items.py        (Item class, HuggingFace push/load)
    ├── pricer/parser.py       (parse, scrub, get_weight, simplify)
    └── pricer/loaders.py      (ItemLoader, ProcessPoolExecutor)

day2.ipynb
    ├── pricer/items.py        (Item.from_hub, item.full, item.summary)
    └── pricer/batch.py        (Batch class, Groq API pipeline)

day3.ipynb
    ├── pricer/items.py        (Item.from_hub)
    └── pricer/evaluator.py    (evaluate(), Tester class)

day4.ipynb
    ├── pricer/items.py
    └── pricer/evaluator.py

redemption_train.ipynb
    ├── pricer/items.py
    ├── pricer/evaluator.py    (evaluate(), plot_training_history())
    └── pricer/deep_neural_network.py  (DeepNeuralNetworkRunner)

[Production — segment4/]
    └── pricer/preprocessor.py    (Preprocessor, LiteLLM, đồng bộ)
    (deep_neural_network.py được copy sang segment4/price_agents/)
```

---

## Session 3 — DL Model Experiments (2026-05-10)

### Mục tiêu

Câu hỏi nghiên cứu cốt lõi: **Biểu diễn văn bản tốt hơn (semantic) có cải thiện độ chính xác so với HashingVec không?**

HashingVec DNN đạt MAE $46.02 — tốt hơn Claude Opus 4.5 ($47.10). Nhưng HashingVec không hiểu ngữ nghĩa: `"car"` ≠ `"automobile"`, `"cheap plastic"` ≠ `"economy grade"`. Câu hỏi: nếu encoder hiểu nghĩa từ hơn, model có dự đoán giá chính xác hơn không?

### Câu chuyện học thuật — 4 tầng tiến hóa

```
Tầng 0 — Baseline: HashingVec → ResNet DNN ($46.02)
    Đặc trưng: keyword presence, stateless, no semantics
    Vấn đề: "car" ≠ "automobile", không hiểu ngữ nghĩa

Tầng 1 — DNN Baseline mở rộng: HashingVec → DNN (15 epochs)
    Câu hỏi: DNN baseline còn cải thiện được không nếu train lâu hơn?

Tầng 2 — SentenceTransformer (frozen) → DNN  [Model 1 — Session cũ]
    Đặc trưng: dense semantic embedding 384-dim, pretrained
    Tiến bộ: "car" ≈ "automobile" — nhưng encoder không học từ dữ liệu giá

Tầng 3 — Fine-tuned DistilBERT / SentTrans E2E  [Model 2 & 3]
    Đặc trưng: encoder học representations tối ưu cho price prediction
    Tiến bộ: attention học cái gì quan trọng (brand, material, category)

Tầng 4 — Feature Fusion: HashingVec + SentTrans  [Model 4]
    Đặc trưng: kết hợp lexical signal + semantic signal
    Hypothesis: 2 nguồn thông tin bổ sung cho nhau
```

---

### Notebook: `redemption_train_15.ipynb` — DNN Baseline 15 Epochs

**Mục tiêu:** Kiểm tra xem DNN HashingVec ban đầu có còn cải thiện thêm nếu train thêm 10 epochs (từ 5 lên 15) không.

**Lưu ý kỹ thuật quan trọng:** `DeepNeuralNetworkRunner.train()` không có early stopping — model train đúng `epochs` được chỉ định, dùng val MAE để quan sát nhưng không dừng sớm. `CosineAnnealingLR(T_max=10)` — tức là scheduler được thiết kế cho 10 epochs, khi train 15 epochs LR sẽ hoàn thành 1 chu kỳ cosine (0→0) ở epoch 10 rồi bắt đầu tăng trở lại.

**Diễn biến training:**

```
Epoch  1: Val MAE $59.20 | LR 0.001000  ← Khởi đầu
Epoch  2: Val MAE $55.81 | LR 0.000976
Epoch  3: Val MAE $55.92 | LR 0.000905
Epoch  4: Val MAE $53.93 | LR 0.000794
Epoch  5: Val MAE $53.73 | LR 0.000655  ← So sánh: kết quả ban đầu dừng tại đây
Epoch  6: Val MAE $51.93 | LR 0.000500
Epoch  7: Val MAE $52.97 | LR 0.000345
Epoch  8: Val MAE $50.65 | LR 0.000206  ← Val MAE tốt nhất
Epoch  9: Val MAE $50.74 | LR 0.000095
Epoch 10: Val MAE $50.56 | LR 0.000024  ← LR gần về 0
Epoch 11: Val MAE $50.56 | LR 0.000000  ← LR = 0 (đáy cosine)
Epoch 12: Val MAE $50.71 | LR 0.000024  ← LR tăng trở lại (chu kỳ 2)
Epoch 13: Val MAE $51.33 | LR 0.000095
Epoch 14: Val MAE $50.92 | LR 0.000206
Epoch 15: Val MAE $52.29 | LR 0.000345  ← Val MAE tăng (LR quá cao cuối)
```

**Nhận xét:**
- Val MAE tốt nhất: $50.65 tại epoch 8 (vẫn tệ hơn test MAE $46.02 của lần train 5 epochs — val và test là 2 tập khác nhau)
- Sau epoch 10, LR tăng trở lại theo lịch Cosine → model dao động, không còn hội tụ
- Train 15 epochs với `CosineAnnealingLR(T_max=10)` không hợp lý về mặt scheduler — LR schedule được thiết kế cho 10 epochs, không phải 15
- **Test MAE: $47.55** — tệ hơn DNN 5 epochs ($46.02) do LR schedule không phù hợp

**Bài học:** Không thể đơn giản tăng epochs mà không điều chỉnh `T_max` theo. Để train 15 epochs, cần đặt `CosineAnnealingLR(T_max=15)`.

---

### File: `pricer/distilbert_model.py` — DistilBERT Regressor (Base Architecture)

> **Vai trò:** Định nghĩa kiến trúc DistilBERT cơ bản (V1 — CLS pooling). V2 và V3 kế thừa từ file này.

#### Kiến trúc

```
item.summary
    │
    ▼ DistilBertTokenizer (max_length=128, padding, truncation)
    │   input_ids: [batch, 128]
    │   attention_mask: [batch, 128]
    │
    ▼ DistilBertModel (6 transformer layers, 66M params)
    │   last_hidden_state: [batch, 128, 768]
    │
    ▼ CLS pooling: lấy token [:, 0, :] — token đặc biệt [CLS]
    │   cls_embedding: [batch, 768]
    │
    ▼ Regression Head
    │   LayerNorm(768)
    │   Linear(768 → 256) + GELU + Dropout(0.1)
    │   Linear(256 → 1)
    │
    ▼ price (normalized)
```

**Tại sao DistilBERT (không phải BERT-base)?**
- DistilBERT: 66M params, 6 layers — nhanh 2×, nhỏ hơn 40%, giữ 97% performance của BERT-base (110M params)
- Với 800k samples x 15 epochs, tốc độ quan trọng: DistilBERT tiết kiệm ~40% thời gian train

**Class `DistilBERTRegressor`:**

```python
class DistilBERTRegressor(nn.Module):
    def __init__(self, dropout_prob=0.1):
        self.encoder = DistilBertModel.from_pretrained("distilbert-base-uncased")
        # hidden_size = 768 (config của DistilBERT)
        self.head = nn.Sequential(
            nn.LayerNorm(768),
            nn.Linear(768, 256),
            nn.GELU(),           # GELU thay vì ReLU — smoother gradient
            nn.Dropout(0.1),
            nn.Linear(256, 1),
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls_embedding = outputs.last_hidden_state[:, 0, :]  # [CLS] token
        return self.head(cls_embedding)
```

**Class `DistilBERTRunner` — Kỹ thuật training:**

**1. Mixed Precision (fp16):**
```python
self.scaler = GradScaler(device="cuda")  # Chỉ tạo nếu CUDA available

with autocast("cuda"):           # Forward pass trong fp16
    outputs = self.model(...)
    loss = self.loss_function(outputs, targets)
self.scaler.scale(loss).backward()       # Scale gradient tránh underflow
self.scaler.unscale_(self.optimizer)     # Unscale trước clip
torch.nn.utils.clip_grad_norm_(...)      # Gradient clipping max_norm=1.0
self.scaler.step(self.optimizer)
self.scaler.update()
```
- **Tại sao fp16?** Giảm memory ~2×, tăng tốc ~2× trên GPU. Nhưng fp16 có range nhỏ → gradient có thể underflow về 0. `GradScaler` nhân loss với scale_factor lớn trước backward, rồi chia lại trước optimizer step.
- **Gradient clipping (`max_norm=1.0`):** Ngăn gradient exploding — nếu norm của gradient vượt 1.0, rescale toàn bộ về 1.0. Đặc biệt quan trọng với transformer fine-tuning.

**2. Discriminative Learning Rates:**
```python
optimizer = AdamW([
    {"params": self.model.encoder.parameters(), "lr": 2e-5},   # Nhỏ — encoder đã pretrained
    {"params": self.model.head.parameters(),    "lr": 1e-4},   # Lớn hơn — head train từ đầu
], weight_decay=0.01)
```
- **Lý do:** Encoder đã có kiến thức từ pretraining trên Wikipedia. LR lớn sẽ phá vỡ kiến thức đó (catastrophic forgetting). LR 2e-5 giúp encoder điều chỉnh nhẹ, không quên hẳn.
- Head (regression head) bắt đầu từ random weights → cần LR lớn hơn (1e-4) để học nhanh.

**3. Linear Warmup Schedule:**
```python
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=500,    # 500 steps đầu: LR tăng tuyến tính từ 0 → lr_max
    num_training_steps=total_steps  # Sau đó giảm tuyến tính về 0
)
```
- **Tại sao warmup?** Ở đầu training, gradient lớn và không ổn định. LR cao lúc đầu → update quá mạnh → phá vỡ pretrained encoder. Warmup giúp optimizer "làm quen" dần trước khi dùng LR đầy đủ.

**4. Log-normalize targets:**
```python
price = torch.log(torch.tensor(item.price, dtype=torch.float32) + 1)
price_norm = (price - y_mean) / y_std
```
- **Tại sao log?** Giá phân phối lệch phải (skewed right) — nhiều sản phẩm giá $10–$200, ít sản phẩm giá $500–$999. Log transform kéo phân phối về gần chuẩn hơn → L1 Loss hoạt động tốt hơn.
- **+1 trước log:** Tránh `log(0)` — nhưng thực tế giá đã được filter ≥ $0.5 từ Day 1.
- De-normalize khi tính MAE: `torch.exp(pred * y_std + y_mean) - 1`.

**Hyperparameters V1:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `max_length` | 128 | Cover 99.8% samples, power-of-2 aligned |
| `batch_size` | 32 | Nhỏ → nhiều gradient updates hơn |
| `encoder_lr` | 2e-5 | Nhỏ, tránh phá pretrained knowledge |
| `head_lr` | 1e-4 | Lớn hơn, head học từ đầu |
| `weight_decay` | 0.01 | L2 regularization trong AdamW |
| `warmup_steps` | 1000 | 1000 steps đầu LR tăng dần |
| `epochs` | 5 | Dừng sớm do time constraint |
| `patience` | 2 | Early stopping |

**Token Length Analysis (chạy trên 10k samples từ items_full):**
```
Min: 40   Max: 163   Mean: 81.9   Median: 81
P90: 99   P95: 105   P99: 118
≤ 128: 99.8%   > 128: 0.2% (25 samples)
```
→ `max_length=128` optimal: cover 99.8%, ít lãng phí memory padding.

**Kết quả V1:** Test MAE **$44.19** sau 5 epochs (val MAE vẫn giảm → chưa hội tụ).

---

### Notebook: `model2_distilbert_train_v2.ipynb` — DistilBERT V2 (Longer Training)

**File Python:** `pricer/distilbert_model_v2.py` — `DistilBERTRunnerV2` kế thừa `DistilBERTRunner`

**Mục tiêu:** V1 val MAE vẫn giảm đều tại epoch 5 ($47.42 → chưa plateau). Train thêm 10 epochs với patience=3 để hội tụ.

**Thay đổi so với V1:**

| Tham số | V1 | V2 | Lý do thay đổi |
|---------|----|----|---------------|
| `batch_size` | 32 | 128 | Lớn hơn → ổn định gradient hơn, tăng tốc |
| `epochs` | 5 | 15 | Train đến hội tụ |
| `patience` | 2 | 3 | Chịu đựng tốt hơn local minimum |
| `warmup_steps` | 1000 | 1000 | Giữ nguyên |

**Lưu ý notebook:** `runner.setup(batch_size=128)` — thực tế dùng batch=128, lớn hơn config mặc định 64. Val set cũng chỉ dùng `val[:1000]` (1000 mẫu, không phải toàn bộ 10k).

**Diễn biến training:**

```
Epoch  1: Val MAE $56.03 | Train 0.4730 | Val 0.4041
Epoch  2: Val MAE $53.59 | Train 0.3877 | Val 0.3899
Epoch  3: Val MAE $50.92 | Train 0.3534 | Val 0.3618
Epoch  4: Val MAE $49.45 | Train 0.3290 | Val 0.3591
Epoch  5: Val MAE $49.13 | Train 0.3084 | Val 0.3582  ← Kết quả V1 dừng đây
Epoch  6: Val MAE $49.64 | No improvement (1/3)
Epoch  7: Val MAE $48.33 | Train 0.2774 | Val 0.3539  ← New best
Epoch  8: Val MAE $47.07 | Train 0.2646 | Val 0.3433  ← New best
Epoch  9: Val MAE $46.60 | Train 0.2538 | Val 0.3414  ← New best
Epoch 10: Val MAE $45.75 | Train 0.2442 | Val 0.3407  ← New best
Epoch 11: Val MAE $45.62 | Train 0.2359 | Val 0.3385  ← New best
Epoch 12: Val MAE $46.35 | No improvement (1/3)
Epoch 13: Val MAE $45.28 | Train 0.2227 | Val 0.3370  ← New best (best overall)
Epoch 14: Val MAE $45.75 | No improvement (1/3)
Epoch 15: Val MAE $45.34 | No improvement (2/3)  ← Hết epochs, dừng
```

**Nhận xét:** Model không kích hoạt early stopping (patience counter không đạt 3 liên tiếp), chạy đủ 15 epochs. Val MAE dao động nhẹ ở cuối — model đã gần plateau. LR giảm dần về 0 theo linear schedule giúp model ổn định ở cuối.

**Test MAE: $46.57** — tệ hơn DistilBERT V1 ($44.19) mặc dù val MAE tốt hơn. Nguyên nhân: val[:1000] là subset nhỏ → noise cao hơn toàn bộ val set. Best val MAE $45.28 (epoch 13) được dùng làm checkpoint.

---

### File: `pricer/distilbert_model_v3.py` — DistilBERT V3 (Mean Pooling)

> **Vai trò:** Thay thế CLS pooling bằng mean pooling — lấy trung bình có trọng số của tất cả token embeddings thay vì chỉ dùng [CLS] token.

**Tại sao thử mean pooling:**

| | CLS Pooling | Mean Pooling |
|--|-------------|--------------|
| **Cơ chế** | Lấy embedding của token [CLS] đặc biệt | Trung bình toàn bộ token embeddings |
| **Pretrain task** | [CLS] được pretrain cho NSP (Next Sentence Prediction) — task classification | Mean pooling không có pretrain task cụ thể |
| **Thông tin** | Tập trung vào 1 vector đại diện | Phân tán đều qua tất cả tokens |
| **Dùng bởi** | BERT-base classification, DistilBERT V1/V2 | SentenceTransformers (all-MiniLM-L6-v2) |

**Nhiều nghiên cứu regression với BERT cho thấy mean pooling ≥ CLS**, đặc biệt khi fine-tuning từ pretrained checkpoint không được train với classification objective.

**Class `DistilBERTRegressorV3`:**

```python
class DistilBERTRegressorV3(nn.Module):
    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        # Mean pooling: trung bình có trọng số theo attention mask
        mask = attention_mask.unsqueeze(-1).float()   # [batch, 128, 1]
        mean_emb = (outputs.last_hidden_state * mask).sum(1) / mask.sum(1)
        #           [batch, 128, 768] * [batch, 128, 1]  → sum dim=1 → [batch, 768]
        #                                                 / [batch, 1]  (số token thực)
        return self.head(mean_emb)
```

**Tại sao nhân với mask rồi chia?**
- `attention_mask` = 1 ở token thực, 0 ở padding token
- Nhân: triệt tiêu embedding của padding tokens
- Chia tổng mask: tính trung bình chỉ trên token thực (không tính padding)
- Nếu không chia, câu ngắn (ít token thực) bị "pha loãng" bởi nhiều padding → embedding bị sai lệch

**Inheritance chain:**
```
DistilBERTRunner (V1)
    └── DistilBERTRunnerV2 (batch=64, 15 epochs)
            └── DistilBERTRunnerV3 (mean pooling, same training config)
                → super().setup() loads data, V2 optimizer config
                → thay thế self.model bằng DistilBERTRegressorV3()
                → tạo lại optimizer với model mới
```

### Notebook: `model2_distilbert_train_v3.ipynb` — DistilBERT V3 Training

**Diễn biến training:**

```
Epoch  1: Val MAE $56.15 | LR 0.00001887
Epoch  2: Val MAE $53.93 | LR 0.00001752
Epoch  3: Val MAE $50.88 | LR 0.00001617  ← New best
Epoch  4: Val MAE $50.89 | No improvement (1/3)
Epoch  5: Val MAE $48.52 | LR 0.00001348  ← New best
Epoch  6: Val MAE $48.30 | LR 0.00001213  ← New best
Epoch  7: Val MAE $48.12 | LR 0.00001078  ← New best
Epoch  8: Val MAE $47.52 | LR 0.00000943  ← New best
Epoch  9: Val MAE $47.05 | LR 0.00000809  ← New best
Epoch 10: Val MAE $45.50 | LR 0.00000674  ← New best (BEST)
Epoch 11: Val MAE $46.27 | No improvement (1/3)
Epoch 12: Val MAE $46.20 | No improvement (2/3)
Epoch 13: Val MAE $46.34 | No improvement (3/3)
→ Early stopping tại epoch 13. Best Val MAE: $45.50
```

**Nhận xét:** Early stopping kích hoạt tại epoch 13 (sau 3 lần liên tiếp không cải thiện từ epoch 10). Model hội tụ rõ ràng hơn V2 — plateau xuất hiện ở epoch 10-13.

**Sanity check mẫu:**
```
Product: Old Blood Noise Excess V2 Distortion Chorus/Delay Pedal
Actual:  $219.00
Predict: $222.34
Error:   $3.34   ← V3 đoán rất gần
```

**Test MAE: $45.21** — tốt hơn V2 ($46.57) và tốt hơn DNN baseline ($46.02). Mean pooling có lợi thế nhỏ so với CLS trong bài toán regression.

---

### File: `pricer/senttrans_e2e_model.py` — SentTrans End-to-End Fine-tuning

> **Vai trò:** Fine-tune toàn bộ encoder `all-MiniLM-L6-v2` (22M params) end-to-end cùng với regression head — khác với Model 1 (frozen encoder, pre-compute embeddings một lần).

**Đối chiếu với Model 1 (frozen SentTrans):**

```
Model 1 (frozen):
    item.summary → all-MiniLM-L6-v2 (FROZEN, pre-computed 1 lần) → 384-dim
    Training loop: chỉ update DNN head (203M params với hidden=4096)

Model 3 (E2E):
    item.summary → all-MiniLM-L6-v2 (FINE-TUNED, mỗi batch) → 384-dim
    Training loop: update cả encoder (22M) lẫn head (99K)
```

**Kiến trúc:**

```
item.summary
    │
    ▼ AutoTokenizer (all-MiniLM-L6-v2, max_length=128)
    │   input_ids: [batch, 128]
    │   attention_mask: [batch, 128]
    │
    ▼ AutoModel (all-MiniLM-L6-v2, 22M params, FINE-TUNED)
    │   last_hidden_state: [batch, 128, 384]
    │
    ▼ Mean Pooling (giống V3 nhưng 384-dim)
    │   mean_emb: [batch, 384]
    │
    ▼ Regression Head
    │   LayerNorm(384)
    │   Linear(384 → 256) + GELU + Dropout(0.1)
    │   Linear(256 → 1)
    │
    ▼ price (normalized)
```

**Tại sao dùng `AutoModel` thay vì `SentenceTransformer`?**
- `SentenceTransformer` là high-level wrapper có pooling và normalization tích hợp — khó kiểm soát gradient
- `AutoModel` từ `transformers` cho phép truy cập trực tiếp `last_hidden_state`, tự implement mean pooling → full control

**Hyperparameters:**

| Tham số | Giá trị | So sánh với DistilBERT |
|---------|---------|----------------------|
| `encoder_lr` | 5e-5 | Nhỏ hơn DistilBERT (2e-5 vs 5e-5)? Không — SentTrans nhỏ hơn (22M vs 66M), cho phép LR lớn hơn chút |
| `head_lr` | 1e-3 | Lớn hơn DistilBERT (1e-4) — head nhỏ hơn (99K vs 198K) |
| `batch_size` | 256 | Lớn hơn DistilBERT (128) — model nhỏ hơn → ít memory hơn |
| `warmup_steps` | 500 | Ít hơn DistilBERT (1000) — encoder nhỏ hơn, ít cần warmup |
| `epochs` | 15 | Tối đa 15 |
| `patience` | 3 | Early stopping |

**Class `SentTransE2ERunner` — Điểm khác biệt với DistilBERTRunner:**

- **Không có GradScaler (không có fp16):** Model nhỏ (22M) nên memory không phải vấn đề, bỏ qua complexity của mixed precision
- **`num_workers=4, pin_memory=True`** trong DataLoader: tokenize on-the-fly trong mỗi batch (không pre-compute như Model 1) — cần I/O hiệu quả
- **`batch_size * 2` cho val_loader:** Val không cần gradient → dùng batch lớn hơn để đánh giá nhanh hơn

### Notebook: `model3_senttrans_e2e_train.ipynb` — SentTrans E2E Training

**Model size:**
```
SentTrans E2E: 22,812,801 params
  encoder: 22,713,216 params (all-MiniLM-L6-v2)
  head:       99,585 params (LayerNorm + 2 Linear)
```

**Diễn biến training:**

```
Epoch  1: Val MAE $62.59 | LR 0.00004717  ← Bắt đầu cao hơn DistilBERT
Epoch  2: Val MAE $57.35 | LR 0.00004380
Epoch  3: Val MAE $53.41 | LR 0.00004043
Epoch  4: Val MAE $51.41 | LR 0.00003706
Epoch  5: Val MAE $50.01 | LR 0.00003369
Epoch  6: Val MAE $49.54 | LR 0.00003032  ← New best
Epoch  7: Val MAE $49.61 | No improvement (1/3)
Epoch  8: Val MAE $49.70 | No improvement (2/3)
Epoch  9: Val MAE $48.91 | LR 0.00002022  ← New best
Epoch 10: Val MAE $48.12 | LR 0.00001685  ← New best
Epoch 11: Val MAE $47.26 | LR 0.00001348  ← New best
Epoch 12: Val MAE $47.76 | No improvement (1/3)
Epoch 13: Val MAE $47.01 | LR 0.00000674  ← New best (BEST)
Epoch 14: Val MAE $47.70 | No improvement (1/3)
Epoch 15: Val MAE $47.21 | No improvement (2/3)  ← Hết epochs, dừng
```

**Nhận xét:**
- Val MAE epoch 1 ($62.59) cao hơn DistilBERT ($56.03) — SentTrans nhỏ hơn nhiều, học chậm hơn ban đầu
- Không trigger early stopping (patience counter không đạt 3 liên tiếp) — chạy đủ 15 epochs
- Val MAE giảm chậm và chưa thực sự plateau → model vẫn có thể cải thiện thêm nếu train thêm

**Sanity check:**
```
Product: Old Blood Noise Excess V2 Distortion Chorus/Delay Pedal
Actual:  $219.00
Predict: $286.12
Error:   $67.12  ← Sai hơn V3 ($3.34) trên sample này
```

**Test MAE: $44.44** — tốt hơn DistilBERT V1 ($44.19), V2 ($46.57), V3 ($45.21) và DNN baseline ($46.02). Fine-tuning encoder nhỏ (22M) đạt kết quả tốt hơn CLS fine-tuned DistilBERT lớn (66M) do mean pooling phù hợp hơn cho regression.

---

### File: `pricer/fusion_model.py` — Feature Fusion (HashingVec + SentTrans)

> **Vai trò:** Dual-tower architecture kết hợp 2 nguồn thông tin bổ sung: lexical signal từ HashingVec và semantic signal từ SentTrans frozen.

**Hypothesis cốt lõi:**

| Signal | Capture bởi | Ví dụ |
|--------|-------------|-------|
| Lexical (từ cụ thể) | HashingVec(5000) | `"samsung"`, `"bose"`, `"wireless"`, `"4k"`, `"stainless steel"` |
| Semantic (ngữ nghĩa) | SentTrans(384) frozen | `"premium quality"` ≈ `"high-end"`, `"economy grade"` ≈ `"budget"` |

**Kiến trúc:**

```
item.summary
    │
    ├─── HashingVectorizer(5000, binary=True, stop_words="english")
    │         hash_features: [batch, 5000]  (sparse binary)
    │         LayerNorm(5000)               ← Chuẩn hóa scale khác nhau
    │         Linear(5000 → 512) + ReLU + Dropout(0.2)
    │         hash_proj: [batch, 512]
    │
    └─── all-MiniLM-L6-v2 (FROZEN, pre-computed 1 lần)
              sem_features: [batch, 384]   (dense float)
              LayerNorm(384)               ← Chuẩn hóa scale khác nhau
              Linear(384 → 512) + ReLU + Dropout(0.2)
              sem_proj: [batch, 512]
              │
    ┌─────────┘────── concat([hash_proj, sem_proj]) ──────────────────────┐
    │                 fused: [batch, 1024]                                 │
    │                                                                       │
    │         Linear(1024 → 1024) + LayerNorm + ReLU + Dropout(0.2)        │
    │         4 × ResidualBlock(1024)                                       │
    │         Linear(1024 → 1)                                             │
    └───────────────────────────────────────────────────────────────────────┘
              price (normalized)
```

**Tại sao cần LayerNorm + projection riêng (không concat thẳng 5384-dim)?**
- `hash_features`: sparse binary [0,1] — range nhỏ, hầu hết = 0
- `sem_features`: dense float — range rộng, phân phối liên tục
- Nếu concat thẳng: 5000-dim lexical sẽ dominate gradient so với 384-dim semantic
- LayerNorm chuẩn hóa từng modality về mean=0, std=1 trước projection → cân bằng contribution

**Class `FusionDNN`:**

```python
class FusionDNN(nn.Module):
    def __init__(self, num_blocks=4, dropout_prob=0.2):
        self.hash_proj = nn.Sequential(
            nn.LayerNorm(HASH_DIM),        # 5000
            nn.Linear(HASH_DIM, PROJ_DIM), # 5000 → 512
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        self.sem_proj = nn.Sequential(
            nn.LayerNorm(SEM_DIM),         # 384
            nn.Linear(SEM_DIM, PROJ_DIM),  # 384 → 512
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        self.fusion_input = nn.Sequential(
            nn.Linear(FUSED_DIM, FUSED_DIM),  # 1024 → 1024
            nn.LayerNorm(FUSED_DIM),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
        )
        self.residual_blocks = nn.ModuleList(
            [ResidualBlock(FUSED_DIM, dropout_prob) for _ in range(num_blocks)]  # 4 blocks
        )
        self.output_layer = nn.Linear(FUSED_DIM, 1)  # 1024 → 1
```

**Tổng params:** 12,234,257 — nhỏ hơn nhiều so với DNN baseline (289M) vì chiều fused nhỏ (1024 vs 4096).

**Setup — Pre-compute cả 2 features:**
```python
# HashingVec: stateless, fit_transform nhanh
X_hash_train = vectorizer.fit_transform(train_docs).toarray()  # [800k, 5000]

# SentTrans frozen: batch_size=512, chạy ~10-15 phút cho 800k samples
X_sem_train = encoder.encode(texts, batch_size=512, show_progress_bar=True)  # [800k, 384]

# Cả 2 được pre-compute 1 lần → training loop chỉ chạy FusionDNN (nhanh)
```

**Hyperparameters:**

| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| `batch_size` | 512 (setup) / 256 (train) | Không có transformer overhead → batch lớn |
| `optimizer` | AdamW(lr=1e-3) | 1 LR cho toàn bộ (không discriminative) |
| `scheduler` | CosineAnnealingLR(T_max=15) | Cosine (không warmup — không có pretrained encoder) |
| `patience` | 3 | Early stopping |

### Notebook: `model4_fusion_train.ipynb` — Feature Fusion Training

**Diễn biến training:**

```
Epoch 1: Val MAE $62.36 | Train 0.5786 | Val 0.4589  ← Bắt đầu rất cao
Epoch 2: Val MAE $61.07 | Train 0.4190 | Val 0.4414
Epoch 3: Val MAE $58.74 | Train 0.3639 | Val 0.4226  ← New best (BEST)
Epoch 4: Val MAE $61.17 | No improvement (1/3)
Epoch 5: Val MAE $62.24 | No improvement (2/3)
Epoch 6: Val MAE $59.82 | No improvement (3/3)
→ Early stopping tại epoch 6. Best Val MAE: $58.74
```

**Sanity check:**
```
Product: Old Blood Noise Excess V2 Distortion Chorus/Delay Pedal
Actual:  $219.00
Predict: $150.63
Error:   $68.37  ← Underestimate đáng kể
```

**Test MAE: $51.55** — Tệ nhất trong các models mới, tệ hơn cả DNN baseline ($46.02).

**Phân tích thất bại:**

1. **Val set quá nhỏ (val[:1000]):** Early stopping dựa trên val MAE nhiều noise → trigger sớm tại epoch 6, model chưa hội tụ
2. **Model capacity quá nhỏ:** 12M params vs DNN 289M. Sau khi project xuống 512-dim mỗi modality, nhiều thông tin lexical bị mất (DNN dùng thẳng 5000-dim HashingVec → 4096-dim)
3. **Pre-compute SentTrans frozen + HashingVec:** Kết hợp frozen semantic signal với lexical không mang lại synergy như kỳ vọng. SentTrans frozen được train cho semantic similarity — representation của nó không optimal cho price prediction khi không được fine-tuned
4. **LR 1e-3 và CosineAnnealing:** Không có warmup → gradient lớn ở epoch đầu → val MAE cao. Tuy nhiên không đủ epoch để recover

---

### Tổng kết — Leaderboard Session 3

| Hạng | Model | Type | Params | Test MAE | Ghi chú |
|------|-------|------|--------|----------|---------|
| 1 | GPT 5.1 | Frontier LLM | — | **$44.06** | Zero-shot + RAG |
| 2 | SentTrans E2E | Fine-tuned LM | 22.8M | **$44.44** | Model 3 |
| 3 | DistilBERT V3 (mean pool) | Fine-tuned LM | 66.6M | $45.21 | Model 2 V3 |
| 4 | DistilBERT V2 (CLS) | Fine-tuned LM | 66.6M | $46.57 | Model 2 V2 |
| 5 | HashingVec DNN | Specialized DL | 289M | $46.02 | Baseline |
| 6 | Redemption 15 epochs | Specialized DL | 289M | $47.55 | DNN train thêm |
| 7 | DistilBERT V1 (5 epochs) | Fine-tuned LM | 66.6M | $44.19 | Chưa hội tụ |
| — | Feature Fusion | Hybrid DL | 12.2M | $51.55 | Model 4 — failed |

*Ghi chú: DistilBERT V1 $44.19 có thể do variability của 200-sample test — thực tế V1 chưa hội tụ, cần thêm epochs*

**Leaderboard tổng thể (tất cả models):**

| Hạng | Model | MAE |
|------|-------|-----|
| 1 | GPT 5.1 (Frontier + RAG) | $44.06 |
| 2 | SentTrans E2E | $44.44 |
| 3 | DistilBERT V1 (5 epochs) | $44.19 |
| 4 | SentTrans frozen (4096 hidden) | $43.78 |
| 5 | DistilBERT V3 (mean pool) | $45.21 |
| 6 | HashingVec DNN (5 epochs) | $46.02 |
| 7 | DistilBERT V2 (CLS, 15 epochs) | $46.57 |
| 8 | Claude Opus 4.5 | $47.10 |
| 9 | SentTrans frozen (1024 hidden) | $47.56 |
| 10 | Redemption DNN (15 epochs) | $47.55 |
| 11 | Neural Network (Vanilla, 8 layers) | $59.14 |
| 12 | GPT 4.1 Nano | $63.28 |
| 13 | XGBoost | $68.23 |
| 14 | NLP Linear Regression (BoW) | $76.81 |
| 15 | Random Forest | $73.04 |
| 16 | Linear Regression | $101.56 |
| 17 | Constant Pricer | $106.18 |

---

### Phân tích kết quả và bài học

**1. Tại sao HashingVec DNN vẫn mạnh?**

Ba lý do chính:
- **Dữ liệu đã được LLM pre-process:** Groq batch rewrite về format chuẩn `Title / Category / Brand / Description / Details`. Brand và Category đã explicit → HashingVec với 5000 features học statistical distribution brand→price cực tốt trên 800k samples.
- **Price prediction là keyword-driven:** `"bose"` → high price, `"anker"` → mid price, `"stainless steel"` → premium. HashingVec capture chính xác binary presence của các keywords này.
- **289M params overparametrized:** Với sparse binary input, model có capacity đủ lớn để memorize distribution giá theo từng keyword bucket.

**2. Tại sao SentTrans E2E ($44.44) tốt hơn DistilBERT lớn hơn ($46.57)?**

- SentTrans (22M) dùng **mean pooling** — phù hợp hơn cho regression so với CLS của DistilBERT V2
- DistilBERT V2 dùng **CLS token** — pretrained cho NSP classification task, không optimal cho regression
- V3 (mean pooling + DistilBERT) đạt $45.21 — cải thiện so với V2, gần với SentTrans E2E, xác nhận mean pooling là yếu tố quan trọng

**3. Tại sao Feature Fusion thất bại?**

- Frozen SentTrans không được fine-tune cho price prediction → semantic signal yếu
- Model capacity quá nhỏ (12M) so với baseline (289M)
- Val set nhỏ (1000 mẫu) → early stopping trigger sớm tại epoch 6, model chưa học đủ

**4. Kết luận về mean pooling vs CLS:**

| | CLS | Mean Pooling |
|--|-----|--------------|
| DistilBERT | $46.57 (V2) | $45.21 (V3) |
| SentTrans | — | $44.44 (E2E) |

Mean pooling nhất quán tốt hơn CLS cho bài toán regression giá. Phù hợp với literature: CLS được optimize cho classification, mean pooling capture toàn bộ thông tin câu tốt hơn cho regression.

**5. Redemption 15 epochs — lesson về LR schedule:**

Khi tăng epochs, phải tăng `T_max` theo. `CosineAnnealingLR(T_max=10)` với 15 epochs làm LR tăng trở lại sau epoch 10 → model dao động, không hội tụ tốt. Test MAE $47.55 tệ hơn 5 epochs ($46.02).

---

### Cập nhật File Structure

```
redemption_train_15.ipynb
    ├── pricer/items.py
    ├── pricer/evaluator.py
    └── pricer/deep_neural_network.py

model2_distilbert_train_v2.ipynb
    ├── pricer/items.py
    ├── pricer/evaluator.py
    ├── pricer/distilbert_model.py    (DistilBERTRunner base)
    └── pricer/distilbert_model_v2.py (DistilBERTRunnerV2)

model2_distilbert_train_v3.ipynb
    ├── pricer/items.py
    ├── pricer/evaluator.py
    ├── pricer/distilbert_model.py    (DistilBERTRunner)
    ├── pricer/distilbert_model_v2.py (DistilBERTRunnerV2)
    └── pricer/distilbert_model_v3.py (DistilBERTRunnerV3 + DistilBERTRegressorV3)

model3_senttrans_e2e_train.ipynb
    ├── pricer/items.py
    ├── pricer/evaluator.py
    └── pricer/senttrans_e2e_model.py (SentTransE2ERunner, SentTransE2ERegressor)

model4_fusion_train.ipynb
    ├── pricer/items.py
    ├── pricer/evaluator.py
    └── pricer/fusion_model.py        (FusionRunner, FusionDNN, ResidualBlock)
```

---

*Cập nhật: 2026-05-10*
