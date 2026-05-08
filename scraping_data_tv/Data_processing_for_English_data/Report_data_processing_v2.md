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

> **Vai trò:** Định nghĩa class `Item` — đơn vị dữ liệu xuyên suốt toàn dự án.

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
Dùng LLM mạnh để "chắt lọc" text thô (`item.full`) thành summary sạch, chuẩn format (`item.summary`). Kỹ thuật này gọi là Knowledge Distillation (chắt lọc kiến thức) — dùng model lớn để tạo data chất lượng cao cho model nhỏ hơn học.

### Vấn đề với `item.full`
```
WD12X10327 Rack Roller and stud assembly Kit (4 Pack) by AMI PARTS...
['【PARTS NUMBER】The dishwasher top rack wheels...', '【REPLACES PART】1811003, AP4980629, WD12X0330...']
{"Brand Name": "AMI PARTS", "Item Weight": "0.634 ounces"...}
```
→ Chứa: mã sản phẩm còn sót, emoji, ngôn ngữ marketing, thông tin thừa.

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

> **Vai trò:** Chạy 200 mẫu test song song, tính MAE, vẽ charts.

**Hằng số:**
```python
WORKERS = 5        # 5 threads song song khi evaluate
DEFAULT_SIZE = 200 # Đánh giá trên 200 mẫu test
```

**Class `Tester`:**

#### `__init__(predictor, data, title, size, workers)`
```python
# predictor: hàm nhận Item, trả về giá đoán (float)
# Lưu lists: titles, guesses, truths, errors, colors
```

#### `make_title(predictor) → str` (staticmethod)
**Mục đích:** Tự động tạo tên hiển thị đẹp cho model từ tên hàm Python — tránh phải đặt tên thủ công cho từng model khi evaluate.
```python
# predictor.__name__ = "gpt_4__1_nano" → "GPT 4.1 Nano"
```

#### `post_process(value) → float` (staticmethod)
**Mục đích:** Chuẩn hóa output đa dạng của các models về kiểu float — LLM thường trả về string ("$180"), trong khi Neural Network trả về float. Hàm này xử lý cả hai trường hợp.
```python
# Nếu là string: xóa "$", "," → tìm số bằng regex
# Ví dụ: "$1,299.99" → 1299.99
```

#### `color_for(error, truth) → str`
**Mục đích:** Phân loại chất lượng dự đoán của 1 datapoint thành 3 mức màu (xanh/cam/đỏ) dựa trên cả sai số tuyệt đối lẫn sai số tương đối, để hiển thị trực quan khi chạy evaluate.
```python
if error < 40 or error / truth < 0.2:  return "green"   # Sai số < $40 hoặc < 20%
elif error < 80 or error / truth < 0.4: return "orange"  # Sai số < $80 hoặc < 40%
else:                                    return "red"     # Sai số lớn
```
> Ghi chú: Dùng cả giá trị tuyệt đối ($40) lẫn tỷ lệ (20%) vì $40 sai số với sản phẩm $50 rất khác với $40 sai số với sản phẩm $500.

#### `run_datapoint(i) → tuple`
**Mục đích:** Xử lý toàn bộ pipeline cho 1 datapoint — gọi model dự đoán, chuẩn hóa output, tính sai số và phân loại màu. Đây là đơn vị công việc được gọi song song bởi `ThreadPoolExecutor`.
```python
value = self.predictor(datapoint)
guess = self.post_process(value)
error = abs(guess - truth)
```

#### `run()`
**Mục đích:** Điều phối toàn bộ quá trình evaluate — chạy `run_datapoint()` song song cho `size` mẫu, in kết quả màu real-time, rồi gọi `report()` để vẽ charts tổng kết.
```python
with ThreadPoolExecutor(max_workers=self.workers) as ex:
    for title, guess, truth, error, color in tqdm(ex.map(self.run_datapoint, range(self.size))):
        print(f"{COLOR_MAP[color]}${error:.0f} ", end="")  # In màu real-time
self.report()
```
> **Tại sao dùng `ThreadPoolExecutor`** (chứ không phải `ProcessPoolExecutor`)?  
> Evaluate là I/O-bound (gọi API LLM, mỗi call đợi network). ThreadPoolExecutor phù hợp hơn vì GIL không ảnh hưởng khi thread đang chờ I/O.

#### `chart(title)` — Scatter Plot (Predicted vs Actual)
**Mục đích:** Vẽ biểu đồ phân tán so sánh giá dự đoán vs giá thực tế — model tốt sẽ có các điểm nằm gần đường `y = x`. Màu sắc điểm phản ánh chất lượng từng dự đoán.
- Trục X: Actual Price (giá thực), Trục Y: Predicted Price (giá đoán)
- Màu điểm: xanh/cam/đỏ theo `color_for()`
- Đường `y = x` (dashed): model hoàn hảo nằm trên đường này
- Hover text: tên sản phẩm + giá đoán + giá thực

#### `error_trend_chart()` — Running Average Error Chart
**Mục đích:** Vẽ biểu đồ MAE tích lũy theo từng sample kèm 95% Confidence Interval (khoảng tin cậy) — giúp đánh giá liệu 200 samples có đủ để kết luận tin cậy chưa.
```python
# Tính running mean và 95% Confidence Interval
running_means = [sum/i for sum, i in ...]
ci = [1.96 * (std / sqrt(i)) for ...]  # 1.96 = z-score cho 95% CI
```
> Nếu đường running mean vẫn dao động mạnh ở cuối → cần tăng số mẫu test để có kết quả chắc chắn hơn.

#### `plot_training_history(history)` — Training History Chart
**Mục đích:** Vẽ 3 biểu đồ quan sát quá trình training DNN qua từng epoch — giúp phát hiện overfitting (Train Loss giảm nhưng Val Loss tăng) và xem learning rate schedule hoạt động đúng không.
- Row 1: Train Loss vs Val Loss qua từng epoch
- Row 2: Validation MAE ($) qua từng epoch
- Row 3: Learning Rate schedule (CosineAnnealing)

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

#### 5. Random Forest
```python
rf_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=4)
rf_model.fit(X[:15_000], prices[:15_000])  # Chỉ 15k subset vì chậm
# MAE = $72.28
```
> Random Forest = nhiều Decision Tree (cây quyết định) chạy song song, mỗi cây train trên random subset của data và features, kết quả cuối = average của tất cả cây.

#### 6. XGBoost (eXtreme Gradient Boosting — Tăng cường Gradient cực mạnh)
```python
xgb_model = xgb.XGBRegressor(n_estimators=1000, random_state=42, n_jobs=4, learning_rate=0.1)
xgb_model.fit(X, prices)  # Toàn bộ 800k samples
# MAE = $68.23 — Best Traditional ML
```
> **Điểm khác XGBoost với Random Forest:** RF xây cây song song độc lập. XGBoost xây cây tuần tự — mỗi cây tiếp theo tập trung sửa lỗi của cây trước (gradient descent trên tree space). Vì vậy XGBoost thường tốt hơn và nhanh hơn với dữ liệu tabular.

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

**Kết quả: MAE = $63.97** — Đánh bại XGBoost ($68.23)!

**Nhân vật đặc biệt: Human Baseline**
```python
# Giảng viên tự đoán giá 100 sản phẩm → lưu vào human_out.csv
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

*Cập nhật: 2026-05-08*
