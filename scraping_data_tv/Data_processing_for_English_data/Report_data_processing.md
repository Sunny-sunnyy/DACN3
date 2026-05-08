# Report: Data Processing & Model Development — "The Price Is Right"

**Dự án:** DACN3 — AI Price Intelligence System  
**Phạm vi:** Week 6 (Day 1–5) — Từ dữ liệu thô đến mô hình dự đoán giá  
**Nguồn tài liệu:** `Data_processing_for_English_data.txt`, `day1–4.txt/.ipynb`, `pricer/*.py`

---

## Tổng quan hành trình

Toàn bộ Week 6 là một vòng R&D khép kín: bắt đầu từ dữ liệu thô Amazon → làm sạch → xây baseline → deep learning → so sánh frontier models. Mục tiêu duy nhất: giảm **Mean Absolute Error (MAE)** trong bài toán dự đoán giá sản phẩm từ mô tả văn bản.

```
Raw Amazon Data (~3M) → Filtering → Dedup → Weighted Sampling (820k)
    → LLM Pre-processing (Groq Batch API) → Clean Dataset (item.summary)
        → Baseline ML → Neural Network → Frontier LLM → DNN ResNet
```

---

## Day 1 — Data Curation

### Nguồn dữ liệu

Dataset: `McAuley-Lab/Amazon-Reviews-2023` từ Hugging Face.

8 categories:
- Automotive, Electronics, Office Products, Tools and Home Improvement
- Cell Phones and Accessories, Toys and Games, Appliances, Musical Instruments

### Quy trình xử lý (parser.py)

**Bước 1: Lọc cứng (Hard Filtering)**

```python
MIN_CHARS = 600       # Mô tả quá ngắn → thiếu thông tin để học
MIN_PRICE = 0.5       # Loại phụ kiện rác giá cực rẻ
MAX_PRICE = 999.49    # Loại hàng xa xỉ/công nghiệp (quy tắc thị trường tiêu dùng)
MAX_TEXT_EACH = 3000
MAX_TEXT_TOTAL = 4000
```

**Bước 2: Làm sạch văn bản (scrub)**

```python
REMOVALS = ["Part Number", "Best Sellers Rank", "Batteries Included?",
            "Batteries Required?", "Item model number"]

# Regex xóa mã sản phẩm vô nghĩa (chuỗi chữ hoa + số ≥ 7 ký tự)
pattern = r"\b(?=[A-Z0-9]{7,}\b)(?=.*\d)[A-Z0-9]+\b"
```

Hàm `scrub()` ghép `title + description + features + details` thành một chuỗi, xóa noise, cắt bớt nếu quá dài.

**Bước 3: Chuẩn hóa trọng lượng (get_weight)**

Chuyển đổi tất cả đơn vị (ounces, grams, kg...) về pounds để thống nhất.

### Cấu trúc dữ liệu (items.py)

```python
class Item(BaseModel):
    title: str
    category: str
    price: float
    full: Optional[str] = None    # Text thô đã ghép và làm sạch
    weight: Optional[float] = None
    summary: Optional[str] = None # Text được LLM viết lại (Day 2)
    prompt: Optional[str] = None  # Prompt cho fine-tuning
    id: Optional[int] = None

    def make_prompt(self, text: str):
        # Format: "What does this cost to the nearest dollar?\n\n{text}\n\nPrice is ${price}.00"
        self.prompt = f"{QUESTION}\n\n{text}\n\n{PREFIX}{round(self.price)}.00"
```

### Xử lý song song (loaders.py)

Vì dataset ~3M rows, dùng `ProcessPoolExecutor` (đa tiến trình, không phải đa luồng — tránh GIL):

```python
WORKERS = max(os.cpu_count() - 1, 1)  # Chừa 1 nhân cho OS

class ItemLoader:
    def chunk_generator(self):
        # Yield từng chunk 1000 dòng (tiết kiệm RAM — Generator pattern)
        for i in range(0, size, CHUNK_SIZE):
            yield self.dataset.select(range(i, min(i + CHUNK_SIZE, size)))

    def load_in_parallel(self, workers):
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for batch in tqdm(pool.map(self.from_chunk, self.chunk_generator())):
                results.extend(batch)
```

### Số liệu thực tế

| Giai đoạn | Số mẫu |
|-----------|--------|
| Raw total | ~2,933,577 |
| Sau deduplication | ~2,887,890 |
| Final (weighted sampling) | 820,000 |
| Train / Val / Test | 800k / 10k / 10k |

### Weighted Sampling — Giải quyết Imbalanced Data

Automotive chiếm ~33% raw data, phần lớn hàng giá rẻ → model sẽ bias đoán giá thấp.

**Giải pháp:**

```python
import numpy as np

# Chuẩn hóa giá về [0,1]
p = (prices - prices.min()) / (prices.max() - prices.min() + 1e-9)

# Trọng số = giá bình phương (ưu tiên hàng đắt)
w = p**2

# Penalize categories chiếm đa số
w[categories == "Tools_and_Home_Improvement"] *= 0.5   # -50%
w[categories == "Automotive"] *= 0.05                  # -95%

# Chuẩn hóa và lấy mẫu
w = w / w.sum()
idx = np.random.choice(len(items), size=820_000, replace=False, p=w)
```

Kết quả: Giá trung bình dataset tăng từ ~$59 lên ~$140.

**Deduplication** (tránh data leakage):
```python
seen = set()
items = [x for x in items if not (x.title in seen or seen.add(x.title))]
```

**Datasets đã publish lên HuggingFace:**
- `SeanSunny/items_lite` — 22k mẫu (Lite version)
- `SeanSunny/items_full` — 820k mẫu (Full version)

---

## Day 2 — Data Pre-processing với LLM (Groq Batch API)

### Vấn đề

Dữ liệu `full` text chứa nhiều noise: mã sản phẩm sót, ngôn ngữ quảng cáo, thông tin thừa. Model học từ dữ liệu bẩn sẽ bị nhiễu.

### Giải pháp: Knowledge Distillation qua Batch API

Dùng LLM mạnh (Groq: `openai/gpt-oss-20b`) để "chưng cất" dữ liệu thô thành summary sạch.

**System prompt:**
```
Create a concise description of a product. Respond only in this format. Do not include part numbers.
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features
```

Tại sao không dùng JSON? Vì format `Key: Value` tốn ít token hơn JSON (không có `{}`, `""`), tiết kiệm chi phí khi scale lên 800k items.

### Batch Processing Pipeline (batch.py)

```
1. Chunking:     Chia 820k items → 820 files JSONL (1000 items/file)
2. make_jsonl(): Tạo request object với custom_id = item.id
3. send_file():  Upload từng file lên Groq server
4. submit_batch(): Tạo Batch Job (completion_window="24h")
5. is_ready():   Poll trạng thái (completed/failed)
6. fetch_output(): Tải file kết quả về
7. apply_output(): Map custom_id → item.summary
```

**Code JSONL request format:**
```python
{
    "custom_id": str(item.id),
    "method": "POST",
    "url": "/v1/chat/completions",
    "body": {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": item.full}
        ],
        "reasoning_effort": "low"
    }
}
```

`custom_id` quan trọng vì kết quả batch trả về không theo thứ tự gửi.

### Lý do dùng Batch Mode

- Giảm 50% chi phí so với synchronous API calls
- Server provider lấp đầy thời gian rảnh (3AM) → discount
- "Fire and forget" — không cần treo máy chờ
- Không bị Rate Limit

### Chi phí thực tế

| Dataset | Thời gian | Chi phí |
|---------|-----------|---------|
| Lite (22k items) | Vài phút | < $1 |
| Full (820k items) | Vài giờ | ~$30 |

Synchronous sẽ tốn ~$60 và mất cả ngày.

### Kết quả

Trường `item.full` bị xóa (noise), chỉ giữ `item.summary` (signal). Dataset giảm từ ~500MB xuống ~250MB, mật độ thông tin tăng cao.

---

## Day 3 — Traditional ML Baselines

### Triết lý

"Start Simple" — thiết lập benchmark trước khi dùng Deep Learning. Mọi mô hình phức tạp sau này phải đánh bại con số này.

### Pipeline NLP cổ điển

```
item.summary (text) → Vectorizer → Sparse Matrix → ML Model → price (float)
```

**Vectorization: Bag of Words (CountVectorizer)**

```python
vectorizer = CountVectorizer(max_features=2000, stop_words='english')
# fit_transform chỉ chạy trên TRAIN — không chạy trên Val/Test (tránh data leakage)
X = vectorizer.fit_transform(documents)
```

Tạo Sparse Matrix: mỗi sản phẩm = vector 2000 chiều, mỗi chiều = số lần từ xuất hiện. Hầu hết là số 0 → dùng sparse representation để tiết kiệm RAM.

**Evaluation Framework (evaluator.py)**

```python
class Tester:
    WORKERS = 5
    DEFAULT_SIZE = 200

    def color_for(self, error, truth):
        if error < 40 or error / truth < 0.2: return "green"
        elif error < 80 or error / truth < 0.4: return "orange"
        else: return "red"

    def run(self):
        # Chạy song song 200 mẫu với ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for result in tqdm(ex.map(self.run_datapoint, range(self.size))):
                ...
        self.report()  # Scatter plot + Error Trend chart (Plotly)
```

### Kết quả các mô hình

| Model | MAE | Ghi chú |
|-------|-----|---------|
| Random Pricer | $382.08 | `random.randrange(1, 1000)` |
| Constant Pricer | $106.18 | Luôn trả về giá trung bình $140.56 |
| Linear Regression (manual features) | $101.56 | Features: weight, text_length |
| **NLP Linear Regression (BoW)** | **$76.81** | CountVectorizer 2000 từ |
| Random Forest | $72.28 | 100 trees, subset 15k |
| **XGBoost** | **$68.23** | 1000 trees, toàn bộ dataset |

**XGBoost config:**
```python
xgb_model = xgb.XGBRegressor(
    n_estimators=1000, random_state=42, n_jobs=4, learning_rate=0.1
)
xgb_model.fit(X, prices)  # X từ CountVectorizer, prices là np.array
```

**Random Forest** chỉ chạy 15k subset vì chậm hơn XGBoost nhiều.

**Nhận xét:** BoW không hiểu ngữ nghĩa ("good" ≠ "great"), không có ngữ cảnh ("Dog bites man" = "Man bites dog"). Nhưng đã đánh bại con người ($87.62)!

---

## Day 4 — Neural Networks & Frontier Models

### Cải tiến vectorization: HashingVectorizer

```python
from sklearn.feature_extraction.text import HashingVectorizer

vectorizer = HashingVectorizer(n_features=5000, binary=True)
# binary=True: chỉ 0/1, không đếm số lần (phù hợp cho NN)
# Stateless: không cần fit, không lưu từ điển → tiết kiệm RAM
```

Tăng từ 2000 → 5000 features. Nhược điểm: không thể reverse-lookup từ gốc.

### Vanilla Neural Network (PyTorch)

**Kiến trúc:**
```python
class NeuralNetwork(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.layer1 = nn.Linear(input_size, 128)
        self.layer2 = nn.Linear(128, 64)
        # layer3 → layer7: Linear(64, 64)
        self.layer8 = nn.Linear(64, 1)     # Output: 1 số (giá)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.layer1(x))
        # ... qua 6 lớp ẩn ...
        return self.layer8(x)
```

- 8 lớp, ~669,000 parameters
- Input: 5000 features từ HashingVectorizer

**Training Loop (4 bước bất biến):**
```python
loss_function = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

for epoch in range(EPOCHS):       # EPOCHS = 2
    for batch_X, batch_y in train_loader:  # batch_size=64
        optimizer.zero_grad()

        outputs = model(batch_X)           # 1. Forward Pass
        loss = loss_function(outputs, batch_y)  # 2. Loss Calculation
        loss.backward()                    # 3. Backward Pass
        optimizer.step()                   # 4. Optimization
```

**Kết quả: MAE = $63.97** — đánh bại toàn bộ ML truyền thống.

### Human Baseline

Giảng viên tự đoán giá 100 sản phẩm, lưu vào `human_out.csv`:
- MAE = **$87.62**
- Kết luận: ML truyền thống (BoW + XGBoost) đã đánh bại con người.

### Frontier Models (Zero-shot)

Dùng `litellm` để gọi API thống nhất:

```python
def messages_for(item):
    return [
        {"role": "system", "content": "Estimate the price. Respond with number only."},
        {"role": "user", "content": item.summary}
    ]

def claude_opus_4_5(item):
    response = completion(model="anthropic/claude-opus-4-5", messages=messages_for(item))
    return response.choices[0].message.content
```

**Bảng xếp hạng Day 4:**

| Hạng | Model | MAE |
|------|-------|-----|
| 1 | Claude Opus 4.5 | $47.10 |
| 2 | Gemini 3 Pro | $50.54 |
| 3 | Grok 4.1 Fast | $57.62 |
| 4 | Gemini 2.5 Flash Lite | $58.68 |
| 5 | GPT-4.1 Nano | $62.51 |
| 6 | Vanilla Neural Network | $63.97 |
| 7 | XGBoost | $68.23 |
| — | Human | $87.62 |

**Bài học quan trọng về Reasoning:** Bật `reasoning_effort='high'` với GPT-5.1 không cải thiện kết quả — đôi khi còn tệ hơn. Bài toán định giá cần "trực giác pattern recognition" hơn là "suy luận step-by-step".

**Tại sao LLM zero-shot thắng model train 800k?** LLM có world knowledge về giá cả sản phẩm từ training data khổng lồ. Khi nhìn "Guitar Acoustic Fender", nó biết range giá từ kiến thức internet.

---

## Day 5 — Fine-tuning thất bại & Deep Neural Network Redemption

### Fine-tuning Frontier Model thất bại

Thử fine-tune GPT-4o-mini trên dataset 820k → kết quả không cải thiện, thậm chí tệ hơn.

**Lý do:** Frontier model đã có world knowledge khổng lồ về giá cả. 820k samples chỉ như "muối bỏ bể", tạo thêm noise thay vì cải thiện. Overfitting vào dataset nhỏ, mất đi generalization từ pre-training.

**Khi nào NÊN fine-tune Frontier Model:**
1. Thay đổi Style/Tone/Format output
2. Dạy hành vi mới (behavior), không phải knowledge
3. Edge cases mà prompting không xử lý được

### Deep Neural Network với Residual Blocks

**Kiến trúc ResNet-style:**

```python
class ResidualBlock(nn.Module):
    def __init__(self, hidden_size, dropout_prob=0.2):
        self.block = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),    # Ổn định training
            nn.ReLU(),
            nn.Dropout(dropout_prob),     # Tránh overfitting
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        residual = x              # Lưu input gốc
        out = self.block(x)       # Xử lý qua các lớp
        out += residual           # Skip connection: cộng input gốc vào
        return self.relu(out)     # Kết quả cuối


class DeepNeuralNetwork(nn.Module):
    def __init__(self, input_size=5000, num_layers=10, hidden_size=4096, dropout_prob=0.2):
        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU()
        )
        self.residual_blocks = nn.ModuleList([
            ResidualBlock(hidden_size, dropout_prob) for _ in range(num_layers)
        ])
        self.output_layer = nn.Linear(hidden_size, 1)
```

**Thông số:**
- 10 Residual Blocks, hidden_size = 4096
- **289 triệu parameters** (so với 669k của Vanilla NN)
- Training: ~40 phút/epoch × 5 epochs = ~4 giờ trên GPU mạnh
- Data: Full 800k samples

**Tại sao Skip Connection quan trọng?**

Mạng sâu (nhiều lớp) bị "vanishing gradient" — đạo hàm giảm dần khi lan truyền ngược về đầu, các lớp đầu không học được. Skip connection tạo "đường tắt" cho gradient, giống như truyền tín hiệu thẳng từ đầu đến cuối, đảm bảo gradient không bị triệt tiêu.

**File model đã train sẵn:** `segment4/deep_neural_network.pth`

Để inference:
```python
runner = DeepNeuralNetworkRunner(device=device)
runner.load('deep_neural_network.pth')

def deep_neural_network(item):
    return runner.inference(item)
```

### Kết quả: MAE = $46.49 — đánh bại Claude Opus 4.5 ($47.10)!

---

## Bảng xếp hạng cuối — "The Price Is Right" Leaderboard

| Hạng | Model | Loại | MAE |
|------|-------|------|-----|
| 1 | GPT-5.1 (giả định) | Frontier LLM | <$46 |
| **2** | **Deep Neural Network** | **Specialized DL** | **$46.49** |
| 3 | Claude Opus 4.5 | Frontier LLM | $47.10 |
| 4 | Gemini 3 Pro | Frontier LLM | $50.54 |
| 5 | Grok 4.1 Fast | Fast LLM | $57.62 |
| 6 | Gemini 2.5 Flash Lite | Fast LLM | $58.68 |
| 7 | GPT-4.1 Nano | Fast LLM | $62.51 |
| 8 | Vanilla Neural Network | Basic DL | $63.97 |
| 9 | XGBoost | Traditional ML | $68.23 |
| 10 | NLP Linear Regression | Traditional ML | $76.81 |
| 11 | Random Forest | Traditional ML | $72.28 |
| 12 | Human (giảng viên) | Bio | $87.62 |
| 13 | Constant Pricer | Trivial | $106.18 |
| 14 | Random Pricer | Trivial | $382.08 |

*Metric: Mean Absolute Error (MAE) trên 200 mẫu test*

---

## Các bài học kỹ thuật cốt lõi

### 1. Garbage In, Garbage Out

Đầu tư $30 để làm sạch dữ liệu bằng LLM (Groq Batch) mang lại cải thiện lớn hơn nhiều so với tuning model. Signal-to-noise ratio của input quyết định 80% kết quả.

### 2. Specialized beats Generalist trên task cụ thể

DNN 289M params chỉ học định giá → thắng Claude Opus 4.5 (hàng tỷ params) biết mọi thứ. "Một nghề cho chín còn hơn chín nghề."

### 3. Fine-tuning: Knowledge vs Behavior

- **KHÔNG nên fine-tune** để dạy kiến thức mà model đã biết (giá cả sản phẩm)
- **NÊN fine-tune** để thay đổi: style, format, hành vi, edge cases

### 4. Data Leakage là nguy hiểm chết người

- `vectorizer.fit()` chỉ chạy trên Train, không bao giờ chạy trên Val/Test
- Deduplication trước khi split dataset
- Shuffle trước khi chia train/val/test

### 5. Weighted Sampling giải quyết Imbalanced Data

Dữ liệu không cân bằng (Automotive 33%) → model bị bias đoán giá thấp. Weighted sampling với `w = price²` kéo phân phối về gần thực tế.

### 6. Residual Connections cho phép train mạng sâu

`out += residual` — một dòng code, nhưng cho phép train mạng 10+ lớp mà không bị vanishing gradient. Đây là nền tảng của ResNet (2015) và mọi modern deep learning architecture.

---

## Cấu trúc file tham chiếu

```
scraping_data_tv/Data_processing_for_English_data/
├── Code_Data_processing/
│   ├── day1.ipynb          # EDA, filtering, dedup, weighted sampling
│   ├── day2.ipynb          # Groq Batch API pre-processing
│   ├── day3.ipynb          # Traditional ML baselines
│   ├── day4.ipynb          # Neural Network + Frontier Models
│   ├── redemption_train.ipynb  # Train DNN 289M params
│   └── pricer/
│       ├── items.py        # Item Pydantic model, HuggingFace push/load
│       ├── parser.py       # Filtering logic, scrub(), get_weight()
│       ├── loaders.py      # Parallel data loading (ProcessPoolExecutor)
│       ├── batch.py        # Groq Batch API pipeline
│       ├── evaluator.py    # Tester class, Plotly charts, MAE metric
│       ├── preprocessor.py # LiteLLM text rewriting
│       └── deep_neural_network.py  # ResidualBlock + DeepNeuralNetwork
└── Data_processing_for_English_data.txt  # Ghi chú học tập chi tiết (3078 dòng)
```

---

*Cập nhật: 2026-05-08*
