# Báo cáo: Xây dựng Hệ thống AI Price Intelligence — "The Price Is Right"

> **Mục đích:** Tài liệu chi tiết về quá trình xây dựng toàn bộ hệ thống production, từ việc triển khai mô hình đã fine-tune lên cloud cho đến hai ứng dụng hoàn chỉnh: ứng dụng autonomous quét deal tự động và ứng dụng tìm kiếm keyword theo yêu cầu.
> **Phạm vi:** Week 8 (Day 1–5) — từ Specialist Agent đầu tiên đến Multi-Source Deal Finder hoàn chỉnh
> **Ngày cập nhật:** 2026-05-11
> **Thư mục code chính:** `segment4/`
> **Hai ứng dụng:** `price_is_right.py` (Autonomous) và `search_key.py` (Keyword Search)

---

## Hành trình tổng quan

```
Week 7: Fine-tune Llama 3.2 3B (QLoRA) → SeanSunny/price-2026-final
    │
    ▼ Day 1 — Triển khai mô hình lên Modal Serverless
SpecialistAgent kết nối với Pricer service trên cloud T4 GPU
    │
    ▼ Day 2 — RAG Pipeline + EnsembleAgent
FrontierAgent (GPT-5.1 + ChromaDB) + EnsembleAgent (3 models, MAE $29.9)
    │
    ▼ Day 3 — ScannerAgent + MessagingAgent
Structured Outputs (Pydantic) + Push Notification (Pushover)
    │
    ▼ Day 4 — PlanningAgent + AutonomousPlanningAgent
Orchestrator điều phối toàn bộ: Quét RSS → Định giá → Notify
    │
    ▼ Day 5 — price_is_right.py + search_key.py hoàn chỉnh
Gradio UI, BestBuy + Amazon scraping, Multi-Source pipeline
```

---

## Chi tiết từng ngày học — Week 8 Day 1–5

### Day 1 (`d1_specialist_agent.ipynb`) — Triển khai model lên Modal

**Mục tiêu:** Kết nối mô hình fine-tuned Llama 3.2 3B (đã train ở Week 7) vào hệ thống thực tế bằng cách deploy lên Modal Serverless. Kiểm chứng rằng model chạy đúng trên cloud GPU, sau đó tích hợp `Preprocessor` để chuẩn hóa đầu vào.

**Thực nghiệm cốt lõi — Proof that code runs on the cloud:**

```python
# Kiểm tra sự khác biệt local vs remote
with app.run():
    hello.local()   # → 'Hello from Da Nang, VN!!'    (máy local)
    hello.remote()  # → 'Hello from Ashburn, Virginia, US!!'  (cloud Modal)
    hello_europe.remote()  # → 'Hello from Frankfurt am Main, DE!!'
```

Đây là bài test đơn giản nhưng then chốt: chứng minh rằng cùng một đoạn Python, khi gọi `.remote()`, thực sự chạy trên máy chủ khác nằm ở Virginia (US) hoặc Frankfurt (EU). Bước tiếp theo là gọi model thực sự từ đó.

**Kết quả thực tế:**
- Fine-tuned model dự đoán HyperX mic (sau preprocessing): **$90**
- SpecialistAgent dự đoán iPhone 16 Pro Max: **$700**
- Preprocessing với Groq chuyển mô tả thô → format chuẩn `Title/Category/Brand/Description/Details`

**Vấn đề gặp phải:**
- Windows: lỗi encoding `cp1252` khi Modal in emoji → fix: `set PYTHONIOENCODING=utf-8`
- Cold Start lần đầu tốn ~10 phút (Modal phải build Docker image, download model từ HuggingFace)
- `MIN_CONTAINERS = 0` (default): container tắt sau 2 phút idle → mọi request sau đó phải chịu cold start

---

### Day 2 (`d2_gpt5rag_ensemble.ipynb`) — RAG Pipeline + EnsembleAgent

**Mục tiêu:** Xây dựng `FrontierAgent` dùng GPT-5.1 với dữ liệu tham chiếu từ ChromaDB (RAG), sau đó ghép 3 models thành `EnsembleAgent` với weighted average.

**Thực nghiệm RAG:**

```python
# Tìm 5 sản phẩm tương tự trong ChromaDB 800K items
def find_similars(item):
    vec = encoder.encode(item.summary)   # all-MiniLM-L6-v2 → 384-dim vector
    results = collection.query(query_embeddings=vec.tolist(), n_results=5)
    return results['documents'][0], [m['price'] for m in results['metadatas'][0]]
```

Khi hỏi giá "Old Blood Noise Excess V2 Distortion Pedal" (giá thật $219), RAG trả về 5 sản phẩm: reverb pedal cùng hãng, Boss Mega Distortion, delay pedal... Tất cả trong khoảng $100-250. GPT-5.1 có context thực tế này → dự đoán **$229** (sai $10).

**Kết quả thực tế trên một item cụ thể (Shure MV7+):**
| Model | Dự đoán |
|-------|---------|
| SpecialistAgent (Modal) | $299 |
| FrontierAgent (GPT-5.1+RAG) | $289 |
| NeuralNetworkAgent (DNN) | $187.66 |
| **EnsembleAgent (80/10/10)** | **$279.87** |

**Visualization TSNE:** Khi plot 800 điểm ngẫu nhiên từ ChromaDB xuống 3D bằng t-SNE, các category tự động tụ thành cluster tách biệt — chứng tỏ `all-MiniLM-L6-v2` hiểu ngữ nghĩa sâu. Đây cũng là biểu đồ 3D hiển thị trong Gradio của `price_is_right.py`. Lưu ý: plot 800,000 điểm gần crash máy → giới hạn `MAXIMUM_DATAPOINTS = 10,000` trong notebook, và `max_datapoints=800` trong production.

---

### Day 3 (`d3_scan_and_mess.ipynb`) — ScannerAgent + MessagingAgent

**Mục tiêu:** Xây dựng "đôi mắt" và "miệng" của hệ thống — ScannerAgent tự tìm deals từ RSS, MessagingAgent tự viết và gửi notification.

**Kết quả scan thực tế (một lần chạy):**
GPT-5-mini lọc từ 25 deals thô → chọn 5 deals tốt nhất:
- YLZKIX Gaming PC (Ryzen 5 5600 + RX 6600): **$790**
- Oukitel P2001 Plus 2048Wh Power Station: **$569**
- Ningmei Ryzen 7 Gaming Desktop: **$629**
- Refurb Dell Latitude 7430 Touch Laptop: **$399**
- Samsung HW-Q990D 11.1.4ch Soundbar: **$1,000**

**Edge case quan trọng:** Deal "Newegg Up to 70% off Gaming PCs" — rule lọc nói loại bỏ "Up to X% off", nhưng bên trong description có PC cụ thể với giá $790. GPT-5-mini đủ thông minh để trích xuất deal cụ thể đó, không bỏ qua toàn bộ.

**Lý do `reasoning_effort="minimal"`:** Bài toán chọn deals chỉ cần đọc hiểu văn bản và so sánh — không cần suy luận chuỗi dài. `minimal` giảm ~50% cost và latency so với default, với chất lượng chọn deal tương đương.

---

### Day 4 (`d4_plan_agent.ipynb`) — AutonomousPlanningAgent

**Mục tiêu:** Xây dựng bộ não điều phối — thay vì hard-code "luôn scan rồi estimate rồi notify", GPT-5.1 tự quyết định thứ tự và điều kiện gọi các tool.

**Quá trình học theo 3 bước:**

**Bước 1:** Prototype với fake functions để hiểu cơ chế Tool Use (Function Calling):
```python
# Giả lập 3 tools với kết quả cứng để test flow
def scan_the_internet_for_bargains() -> str:
    return json.dumps({"deals": [{"title": "Hisense TV", "price": 178}, ...]})
```

**Bước 2:** Viết Agent Loop thủ công:
```python
done = False
while not done:
    response = openai.chat.completions.create(model="gpt-5.1", messages=messages, tools=tools)
    if response.choices[0].finish_reason == "tool_calls":
        # GPT muốn gọi tool → thực hiện và trả kết quả vào messages
        results = handle_tool_call(response.choices[0].message)
        messages.extend(results)
    else:
        done = True  # GPT trả lời cuối cùng, không gọi tool nữa
```

**Bước 3:** Dùng OpenAI Agents SDK (`@function_tool` decorator) để thay thế loop thủ công.

**Quan sát quan trọng:** GPT-5.1 tự quyết định gọi `estimate_true_value` 4 lần (cho 4 deals), rồi chỉ gọi `notify_user_of_deal` **một lần** cho deal tốt nhất — đúng với instruction "only call this one time". Không cần code cứng logic này.

---

### Day 5 (`day5.ipynb`) — Gradio UI + Production

**Mục tiêu:** Đưa toàn bộ hệ thống vào một Gradio app hoàn chỉnh có thể demo được.

**Quá trình build UI từng bước:**

```python
# Bước 1: Blank UI
with gr.Blocks(title="The Price is Right", fill_width=True) as ui:
    gr.Markdown("## The Price is Right")
ui.launch()

# Bước 2: Thêm Dataframe hiển thị deals (static data trước)
opportunities_dataframe = gr.Dataframe(
    headers=["Description", "Price", "Estimate", "Discount", "URL"],
    wrap=True,
    max_height=400  # Lưu ý: `height` bị deprecated trong Gradio v5, phải dùng `max_height`
)

# Bước 3: Wire Gradio events vào agent pipeline
ui.load(run_with_logging, ...)    # Chạy ngay khi UI load
timer = gr.Timer(value=300)
timer.tick(run_with_logging, ...) # Chạy lại mỗi 5 phút
```

**Lỗi Gradio v5 phát hiện trong class:** `height` parameter của `gr.Dataframe` bị deprecated → dùng `max_height`. Đây là ví dụ điển hình về "API thay đổi theo phiên bản" — tài liệu cũ không còn chính xác.

---

## Phần 1: Triết lý thiết kế hệ thống (Week 8 Day 1)

### 1.1 Từ Notebook đến Production

Trước Week 8, toàn bộ quá trình train model, phân tích dữ liệu, và thử nghiệm đều diễn ra trong Jupyter Notebook — môi trường lý tưởng để khám phá nhưng không phù hợp cho sản phẩm chạy 24/7. Nhiệm vụ của Week 8 là "đưa mọi thứ lên môi trường Production thực tế."

Hai thách thức cốt lõi:

**Thứ nhất — Nơi chạy model:** Mô hình Llama 3.2 3B fine-tuned nặng ~2.2GB (4-bit) không thể chạy trên laptop thông thường trong khi phục vụ request. Cần hạ tầng GPU cloud.

**Thứ hai — Kiến trúc hệ thống:** Cần tổ chức code sao cho mỗi thành phần có trách nhiệm độc lập, dễ debug, dễ mở rộng, và có thể thay thế từng phần mà không ảnh hưởng toàn bộ.

### 1.2 Quyết định kiến trúc: Build from First Principles

Thay vì dùng framework có sẵn như LangChain hay CrewAI, hệ thống được xây từ nguyên lý cơ bản — viết code Python gọi trực tiếp các API LLM, quản lý orchestration bằng logic thuần Python. Lý do:

- Framework ẩn quá nhiều chi tiết kỹ thuật, khi có lỗi khó debug
- Mỗi agent thực chất chỉ là một lời gọi LLM có cấu trúc — không cần abstraction phức tạp
- Kiểm soát hoàn toàn luồng dữ liệu, chi phí API, và latency

### 1.3 Định nghĩa Agent trong dự án này

Hệ thống có 3 loại "agent" với mức độ tự chủ khác nhau:

| Loại | Ví dụ | Mô tả |
|------|-------|-------|
| **LLM Wrapper** | SpecialistAgent, FrontierAgent | Wrapper xung quanh một lời gọi LLM, che giấu chi tiết kỹ thuật |
| **Workflow Agent** | EnsembleAgent, PlanningAgent | Điều phối nhiều agents con theo logic cứng (hard-coded) |
| **Autonomous Agent** | AutonomousPlanningAgent | GPT tự quyết định gọi tool nào, khi nào, theo thứ tự nào |

---

## Phần 2: Modal Serverless — Đưa Model lên Cloud (Day 1)

### 2.1 Tại sao cần Modal?

Sau khi fine-tune, model Llama 3.2 3B cần GPU T4 để inference với tốc độ hợp lý. Các lựa chọn:

- **GPU riêng:** Tốn $200-500/tháng dù model không chạy liên tục
- **Google Colab:** Không thể tích hợp vào ứng dụng web, giới hạn thời gian chạy
- **Modal (Serverless):** Chỉ trả tiền khi container đang xử lý request. Container tắt khi không có request, bật lại khi cần. Chi phí: ~$30 credit miễn phí/tháng là đủ.

### 2.2 Kiến trúc Modal Service (`pricer_service2.py`)

Modal sử dụng mô hình "Infrastructure as Code" — toàn bộ cấu hình GPU, thư viện, và model đều được khai báo trong Python:

```python
# Định nghĩa môi trường: OS + thư viện AI
image = (
    modal.Image.debian_slim()
    .pip_install("torch", "transformers", "bitsandbytes", "accelerate", "peft")
)

# Kết nối với HuggingFace Token (lưu trong Modal Secrets, không hard-code)
secrets = [modal.Secret.from_name("huggingface-secret")]

@app.cls(gpu="T4", image=image, secrets=secrets, timeout=1800)
class Pricer:

    @modal.enter()
    def setup(self):
        """Chạy 1 lần khi container khởi động — load model vào RAM GPU."""
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4"
        )
        # Base model Llama 3.2 3B (4-bit NF4, ~2.2GB VRAM)
        base_model = AutoModelForCausalLM.from_pretrained(
            "meta-llama/Llama-3.2-3B",
            quantization_config=quant_config,
            device_map="auto"
        )
        # Gắn LoRA adapter fine-tuned của chúng ta vào base model
        self.model = PeftModel.from_pretrained(base_model, "SeanSunny/price-2026-final")
        self.tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B")

    @modal.method()
    def price(self, description: str) -> float:
        """Inference: nhận mô tả sản phẩm, trả về giá dự đoán."""
        prompt = f"What does this cost to the nearest dollar?\n\n{description}\n\nPrice is $"
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=8)
        generated = output_ids[0, inputs["input_ids"].shape[1]:]
        decoded = self.tokenizer.decode(generated, skip_special_tokens=True)
        # Trích xuất số từ output (ví dụ: "280.00" → 280.0)
        match = re.search(r"\d+(?:\.\d+)?", decoded)
        return float(match.group()) if match else 0.0
```

**Điểm mấu chốt:** Decorator `@modal.enter()` tách biệt phần nặng (load model, ~30-60s) với phần nhẹ (inference, ~1-2s). Model được load 1 lần và giữ trong RAM GPU suốt vòng đời container. Các request tiếp theo chỉ tốn thời gian inference.

**Cold Start vs Warm Start:**
- Cold Start (lần đầu sau khi container ngủ): ~30-60s — phải load model từ HuggingFace cache
- Warm Start (container đang chạy): ~1-2s — model đã có sẵn trong VRAM

**Triển khai:**
```bash
modal deploy pricer_service2.py
# Tạo endpoint cố định: "pricer-service" trên Dashboard Modal
```

---

## Phần 3: Kiến trúc Agent — Base Class và Logging (Day 1)

### 3.1 `agent.py` — Nền tảng cho toàn bộ hệ thống

Tất cả agents kế thừa từ một class duy nhất:

```python
class Agent:
    """Abstract base class với colored logging."""

    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    RESET = '\033[0m'

    name: str = ""
    color: str = WHITE

    def log(self, message):
        """Log với màu đặc trưng của từng agent."""
        text = f"[{self.name}] {message}"
        logging.info(self.color + text + self.RESET)
```

**Tại sao cần màu sắc?** Khi hệ thống chạy, terminal hiển thị log từ 5-6 agents song song. Màu sắc riêng biệt giúp nhận diện agent nào đang làm gì trong vài giây — không cần đọc tên. Ví dụ: log màu đỏ luôn là SpecialistAgent, màu vàng là EnsembleAgent.

| Agent | Màu |
|-------|-----|
| Specialist Agent | Đỏ (RED) |
| Frontier Agent | Vàng (YELLOW) |
| Ensemble Agent | Vàng (YELLOW) |
| Scanner Agent | Xanh lam nhạt (CYAN) |
| Planning Agent | Xanh lá (GREEN) |
| Messaging Agent | Tím (MAGENTA) |

---

## Phần 4: SpecialistAgent — Kết nối Local ↔ Cloud (Day 1)

`specialist_agent.py` là ví dụ điển hình của mẫu thiết kế **Proxy/Facade**: agent này không chứa model, không có logic inference — nó chỉ là một "điều khiển từ xa" trỏ tới Modal:

```python
class SpecialistAgent(Agent):
    name = "Specialist Agent"
    color = Agent.RED

    def __init__(self):
        self.log("Specialist Agent is initializing - connecting to modal")
        # Kết nối tới service đã deploy (không tải model về local)
        Pricer = modal.Cls.from_name("pricer-service", "Pricer")
        self.pricer = Pricer()
        self.log("Specialist Agent is ready")

    def price(self, description: str) -> float:
        self.log("Specialist Agent is calling remote fine-tuned model")
        # RPC call: gửi description lên Modal, đợi kết quả float trả về
        result = self.pricer.price.remote(description)
        self.log(f"Specialist Agent completed - predicting ${result:.2f}")
        return result
```

**Lợi ích của thiết kế này:** Phần còn lại của hệ thống (EnsembleAgent, PlanningAgent) chỉ thấy `specialist.price(description) → float`. Chúng không biết — và không cần biết — rằng bên dưới là một GPU T4 đang chạy ở đâu đó trên cloud Modal. Nếu sau này muốn chuyển từ Modal sang AWS SageMaker, chỉ cần sửa file `specialist_agent.py`.

---

## Phần 5: FrontierAgent — RAG với ChromaDB (Day 2)

### 5.1 Triết lý Training Time vs Inference Time

Đây là điểm quan trọng nhất của Day 2: hai cách khác nhau để "dạy" LLM biết giá sản phẩm:

| Cách | Kỹ thuật | Thời điểm nạp kiến thức | Ưu điểm | Nhược điểm |
|------|----------|--------------------------|----------|------------|
| **Training time** | Fine-tuning (Week 7) | Lúc train | Nhanh khi inference | Tốn kém để cập nhật |
| **Inference time** | RAG (Day 2) | Lúc hỏi | Dữ liệu luôn mới | Tốn thêm thời gian lookup |

SpecialistAgent dùng training time — model đã "nhớ" giá từ 800k sản phẩm vào trọng số. FrontierAgent dùng inference time — mỗi lần hỏi, nó tra cứu 5 sản phẩm tương tự trong ChromaDB rồi "mớm" thông tin đó cho GPT-5.1.

### 5.2 ChromaDB Vector Store — Cơ sở dữ liệu ngữ nghĩa

**Xây dựng (một lần, ngoài runtime):**
- 800,000 sản phẩm Amazon được embed bằng `sentence-transformers/all-MiniLM-L6-v2`
- Mỗi sản phẩm → vector 384 chiều biểu diễn ngữ nghĩa
- Lưu vào ChromaDB Persistent Client tại `segment4/products_vectorstore/`

**t-SNE Visualization:** Khi vẽ 800 điểm dữ liệu ngẫu nhiên xuống 3D (dùng t-SNE), các sản phẩm cùng category tự động tụ thành cluster rõ ràng — chứng tỏ all-MiniLM-L6-v2 hiểu ngữ nghĩa sâu, không chỉ dựa trên từ khóa. Đây cũng là biểu đồ 3D hiển thị trong Gradio dashboard của `price_is_right.py`.

### 5.3 `frontier_agent.py` — Logic RAG thủ công

```python
class FrontierAgent(Agent):
    MODEL = "gpt-5.1"

    def __init__(self, collection):
        self.client = OpenAI()
        self.collection = collection           # ChromaDB collection (800K products)
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def find_similars(self, description: str):
        """Bước Retrieval: tìm 5 sản phẩm gần nhất trong ChromaDB."""
        self.log("Performing RAG search to find 5 similar products")
        vector = self.model.encode([description])
        results = self.collection.query(
            query_embeddings=vector.astype(float).tolist(),
            n_results=5
        )
        documents = results["documents"][0][:]
        prices = [m["price"] for m in results["metadatas"][0][:]]
        return documents, prices

    def make_context(self, similars, prices) -> str:
        """Bước Augmentation: tạo context chèn vào prompt."""
        message = "To provide context, here are similar products:\n\n"
        for similar, price in zip(similars, prices):
            message += f"Potentially related product:\n{similar}\nPrice is ${price:.2f}\n\n"
        return message

    def price(self, description: str) -> float:
        """Bước Generation: gửi description + context cho GPT-5.1."""
        documents, prices = self.find_similars(description)
        message = f"Estimate the price. Respond with the price only.\n\n{description}\n\n"
        message += self.make_context(documents, prices)
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=[{"role": "user", "content": message}],
            seed=42,
            reasoning_effort="none",   # Tắt thinking để tiết kiệm thời gian
        )
        return self.get_price(response.choices[0].message.content)
```

**Ví dụ thực tế:** Khi hỏi giá "Old Blood Noise Distortion Pedal", RAG trả về 5 sản phẩm: một reverb pedal cùng hãng, một Boss Mega Distortion, một delay pedal... Tất cả đều là guitar effects trong khoảng giá $100-250. GPT-5.1 nhận thông tin đó và đưa ra dự đoán cực chính xác — không phải vì nó biết giá từ training, mà vì nó có context thực tế.

---

## Phần 6: EnsembleAgent — Kết hợp sức mạnh 3 models (Day 2)

### 6.1 Lý thuyết Ensemble

Mỗi model có điểm mạnh và điểm yếu riêng:
- **FrontierAgent:** Giỏi suy luận ngữ nghĩa và có dữ liệu tham chiếu thực tế từ ChromaDB
- **SpecialistAgent:** Được train chuyên sâu trên 800k sản phẩm Amazon, nhận biết pattern giá
- **NeuralNetworkAgent:** Tính toán thống kê thuần túy từ 289M params, ít bị ảo giác (hallucination)

Nếu một model đoán sai xa (ví dụ FrontierAgent hallucinate), hai model kia sẽ kéo kết quả về gần giá trị thực. Trên tập test 200 mẫu, Ensemble đạt MAE $29.9 — tốt hơn bất kỳ model đơn lẻ nào.

### 6.2 Preprocessor — Chuẩn hóa đầu vào

Trước khi gửi vào các model, văn bản mô tả sản phẩm được LLM viết lại theo format chuẩn:

```python
SYSTEM_PROMPT = """Create a concise description of a product. Respond only in this format:
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features"""

class Preprocessor:
    def __init__(self):
        # Mặc định: ollama/llama3.2 (miễn phí, chạy local)
        # Hoặc dùng PRICER_PREPROCESSOR_MODEL env var để chọn model khác
        self.model_name = os.getenv("PRICER_PREPROCESSOR_MODEL", "ollama/llama3.2")

    def preprocess(self, text: str) -> str:
        """LLM viết lại text thành format chuẩn. Có fallback nếu LLM gọi thất bại."""
        try:
            response = completion(model=self.model_name, messages=self.messages_for(text))
            return response.choices[0].message.content
        except Exception as e:
            logging.warning(f"[Preprocessor] LLM failed, using raw text: {e}")
            return text  # Fallback: trả về text gốc thay vì crash
```

**Tại sao cần preprocessing?** Dữ liệu khi inference (từ RSS feed, BestBuy API, Amazon HTML) có định dạng rất khác dữ liệu lúc training (đã được Groq Batch API chuẩn hóa ở Week 6 Day 2). Preprocessing đảm bảo format giống nhau ở training time và inference time — đây là nguyên tắc "treat inference data the same as training data."

**Lưu ý thực tế:** Groq API đôi khi trả về lỗi 522 (timeout). Vì vậy Preprocessor có try-except: nếu LLM call thất bại, trả về text gốc thay vì crash toàn bộ pipeline.

### 6.3 `ensemble_agent.py` — Code thực tế

```python
class EnsembleAgent(Agent):
    name = "Ensemble Agent"
    color = Agent.YELLOW

    def __init__(self, collection):
        self.log("Initializing Ensemble Agent")
        self.specialist = SpecialistAgent()           # Modal remote call
        self.frontier = FrontierAgent(collection)    # GPT-5.1 + ChromaDB
        self.neural_network = NeuralNetworkAgent()   # Local PyTorch DNN
        self.preprocessor = Preprocessor()           # LiteLLM text rewrite
        self.log("Ensemble Agent is ready")

    def price(self, description: str) -> float:
        self.log("Running Ensemble Agent - preprocessing text")
        rewrite = self.preprocessor.preprocess(description)
        self.log(f"Pre-processed text using {self.preprocessor.model_name}")

        specialist = self.specialist.price(rewrite)        # ~1-2s (warm) hoặc ~60s (cold)
        frontier = self.frontier.price(rewrite)            # ~3-5s (RAG + GPT call)
        neural_network = self.neural_network.price(rewrite) # ~0.1s (local PyTorch)

        # Weighted average: 80% GPT + 10% Llama + 10% DNN
        combined = frontier * 0.8 + specialist * 0.1 + neural_network * 0.1
        self.log(f"Ensemble Agent complete - returning ${combined:.2f}")
        return combined
```

### 6.4 NeuralNetworkAgent — DNN local

```python
class NeuralNetworkAgent(Agent):
    def __init__(self):
        self.neural_network = DeepNeuralNetworkInference()
        self.neural_network.setup()
        # Load 289M params từ file .pth (~1GB)
        self.neural_network.load("deep_neural_network.pth")

    def price(self, description: str) -> float:
        return self.neural_network.inference(description)
```

`DeepNeuralNetworkInference` dùng `HashingVectorizer(n_features=5000, binary=True)` để chuyển text thành vector rồi đưa vào DNN 10 lớp ResidualBlocks. Kết quả được de-normalize: `exp(pred * std + mean) - 1` để trả về giá thực (giá đã log-transform lúc training).

---

## Phần 7: ScannerAgent — Đôi mắt của hệ thống (Day 3)

### 7.1 Structured Outputs — Biến văn bản thô thành data có cấu trúc

Bài học Day 3 giới thiệu kỹ thuật quan trọng nhất cho việc xây dựng agent thực tế: thay vì viết Regex phức tạp để trích xuất thông tin từ HTML/RSS, dùng LLM với Pydantic để parse data.

**Vấn đề truyền thống:** Câu "Giảm $50 từ giá gốc $200 — chỉ còn $150" yêu cầu Regex rất phức tạp để hiểu rằng giá thực là $150, không phải $200 hay $50.

**Giải pháp Structured Outputs:** Định nghĩa schema bằng Pydantic, OpenAI tự động đảm bảo kết quả khớp 100% schema (Constrained Decoding — mỗi token được sinh ra phải hợp lệ theo JSON Schema, không thể có sai cú pháp).

### 7.2 Data Models (`deals.py`)

```python
class Deal(BaseModel):
    """Pydantic model — một sản phẩm đã qua LLM processing."""
    product_description: str
    price: float
    url: str

class DealSelection(BaseModel):
    """Output của ScannerAgent — top 5 deals từ RSS."""
    deals: List[Deal]

class Opportunity(BaseModel):
    """Output của EnsembleAgent — deal + ước lượng giá thực."""
    deal: Deal
    estimate: float
    discount: float        # = estimate - deal.price

class ScrapedDeal:
    """Raw data từ RSS feed (dùng bởi price_is_right.py)."""
    title: str
    summary: str
    url: str
    details: str
    features: str

    @classmethod
    def fetch(cls) -> List["ScrapedDeal"]:
        """Fetch từ 5 DealNews RSS categories bằng feedparser."""
        feeds = [
            "https://www.dealnews.com/c142/Electronics/?rss=1",
            "https://www.dealnews.com/c39/Computers/?rss=1",
            "https://www.dealnews.com/f1912/Smart-Home/?rss=1",
            "https://www.dealnews.com/c238/Automotive/?rss=1",
            "https://www.dealnews.com/c196/Home-Garden/?rss=1",
        ]
        # feedparser.parse() mỗi feed, BeautifulSoup loại bỏ HTML tags
```

### 7.3 `scanner_agent.py` — Scan RSS + GPT filter

```python
class ScannerAgent(Agent):
    MODEL = "gpt-5-mini"
    name = "Scanner Agent"
    color = Agent.CYAN

    SYSTEM_PROMPT = """You identify and summarize the 5 most detailed deals from a list.
    CRITICAL PRICING RULES:
    1. "Off" is NOT the actual price — only include when final checkout price is explicit.
    2. EXCLUDE "Up to X% off" general sale events.
    3. EXCLUDE trade-in deals ("$700 off w/ trade-in").
    """

    def fetch_deals(self, memory) -> List[ScrapedDeal]:
        """Lấy deals từ RSS, loại bỏ những cái đã có trong memory."""
        urls = [opp.deal.url for opp in memory]
        scraped = ScrapedDeal.fetch()   # ~25 deals từ 5 feeds
        return [s for s in scraped if s.url not in urls]

    def scan(self, memory=[]) -> Optional[DealSelection]:
        """GPT-5-mini chọn top 5 deals tốt nhất bằng Structured Outputs."""
        scraped = self.fetch_deals(memory)
        if not scraped:
            return None
        user_prompt = self.USER_PROMPT_PREFIX
        user_prompt += "\n\n".join([scrape.describe() for scrape in scraped])
        user_prompt += "\n\nInclude exactly 5 deals, no more."

        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=DealSelection,   # Structured Output
            reasoning_effort="minimal",      # Nhanh và rẻ
        )
        result = result.choices[0].message.parsed
        result.deals = [deal for deal in result.deals if deal.price > 0]
        return result
```

**Reasoning effort "minimal":** GPT-5-mini với `reasoning_effort="minimal"` giảm thời gian suy nghĩ xuống mức tối thiểu — phù hợp vì bài toán chọn deal chỉ cần đọc hiểu văn bản, không cần suy luận phức tạp. Tiết kiệm chi phí và thời gian.

---

## Phần 8: MessagingAgent — Push Notification (Day 3)

### 8.1 Pushover API

Pushover là dịch vụ push notification đơn giản: gọi một API endpoint duy nhất là thông báo xuất hiện trên điện thoại, kèm âm thanh tùy chọn.

### 8.2 `messaging_agent.py`

```python
class MessagingAgent(Agent):
    name = "Messaging Agent"
    color = Agent.MAGENTA
    MODEL = "gpt-5-nano"    # Model nhỏ nhất, đủ dùng để viết text marketing

    def push(self, text: str):
        """Gửi notification qua Pushover API."""
        payload = {
            "user": self.pushover_user,
            "token": self.pushover_token,
            "message": text,
            "sound": "cashregister",   # Tiếng máy tính tiền khi deal tốt
        }
        requests.post("https://api.pushover.net/1/messages.json", data=payload)

    def craft_message(self, description, deal_price, estimated_true_value) -> str:
        """Dùng GPT-5-nano viết tin nhắn marketing hài hước, tạo FOMO."""
        user_prompt = f"""Summarize this deal in 2-3 sentences for a push notification.
Item: {description}
Deal Price: {deal_price}
Estimated True Value: {estimated_true_value}
Use hilarious, high-energy tone. Create major FOMO. Respond ONLY with the message."""
        response = completion(model=self.MODEL, messages=[{"role": "user", "content": user_prompt}])
        return response.choices[0].message.content

    def notify(self, description, deal_price, estimated_true_value, url):
        """Craft message + push. Dùng bởi AutonomousPlanningAgent và MultiSourcePlanningAgent."""
        text = self.craft_message(description, deal_price, estimated_true_value)
        self.push(text[:200] + "... " + url)

    def alert(self, opportunity: Opportunity):
        """Format đơn giản + push. Dùng bởi PlanningAgent (simple mode)."""
        text = f"Deal Alert! Price=${opportunity.deal.price:.2f}, "
        text += f"Estimate=${opportunity.estimate:.2f}, Discount=${opportunity.discount:.2f} :"
        text += opportunity.deal.product_description[:10] + "... " + opportunity.deal.url
        self.push(text)
```

**Hai phương thức notify:** `notify()` dùng GPT để viết tin nhắn sáng tạo (cho autonomous mode), `alert()` dùng format đơn giản không tốn API call (cho simple mode khi cần tiết kiệm).

---

## Phần 9: Planning Agents — Bộ não điều phối (Day 4)

### 9.1 PlanningAgent — Simple Mode (Hard-coded Workflow)

```python
class PlanningAgent(Agent):
    name = "Planning Agent"
    color = Agent.GREEN
    DEAL_THRESHOLD = 50    # Notify nếu discount > $50

    def __init__(self, collection):
        self.scanner = ScannerAgent()
        self.ensemble = EnsembleAgent(collection)
        self.messenger = MessagingAgent()

    def plan(self, memory=[]) -> Optional[Opportunity]:
        """Sequential workflow — không có AI orchestration."""
        # 1. Scan RSS
        selection = self.scanner.scan(memory=memory)
        if not selection:
            return None

        # 2. Estimate all 5 deals
        opportunities = []
        for deal in selection.deals[:5]:
            estimate = self.ensemble.price(deal.product_description)
            discount = estimate - deal.price
            opportunities.append(Opportunity(deal=deal, estimate=estimate, discount=discount))

        # 3. Chọn deal tốt nhất (sort by discount)
        opportunities.sort(key=lambda opp: opp.discount, reverse=True)
        best = opportunities[0]

        # 4. Notify nếu đủ tốt
        if best.discount > self.DEAL_THRESHOLD:
            self.messenger.alert(best)

        return best if best.discount > self.DEAL_THRESHOLD else None
```

Workflow cứng: luôn scan → estimate tất cả → chọn tốt nhất → notify. Không có sự linh hoạt, nhưng dễ debug và ổn định.

### 9.2 AutonomousPlanningAgent — GPT-5.1 làm Controller

Đây là điểm khác biệt lớn nhất: thay vì hard-code "luôn scan rồi estimate rồi notify", GPT-5.1 tự quyết định thứ tự và điều kiện gọi các tool.

**Function Tools:** Ba hàm được expose cho GPT như công cụ:

```python
@function_tool
def scan_the_internet_for_bargains() -> str:
    """Scan RSS feeds và trả về JSON của DealSelection."""
    results = planner.scanner.scan(memory=planner.memory)
    return results.model_dump_json() if results else ""

@function_tool
def estimate_true_value(description: str) -> str:
    """Estimate giá một sản phẩm, trả về JSON {description, estimated_true_value}."""
    estimate = planner.ensemble.price(description)
    return json.dumps({"description": description, "estimated_true_value": estimate})

@function_tool
def notify_user_of_deal(description, deal_price, estimated_true_value, url) -> str:
    """Gửi push notification và tạo Opportunity object."""
    planner.messenger.notify(description, deal_price, estimated_true_value, url)
    deal = Deal(product_description=description, price=deal_price, url=url)
    discount = estimated_true_value - deal_price
    planner.opportunity = Opportunity(deal=deal, estimate=estimated_true_value, discount=discount)
    return "notification sent"
```

**Task prompt cho GPT-5.1:**
```
You are an Autonomous AI Agent. Your mission:
1. Scan the internet for bargains.
2. For each deal, estimate its true value.
3. Pick the single most compelling deal (price << estimated value).
4. Send a push notification and write to sandbox/deals.md.
You must only notify about ONE deal. Then respond OK.
```

**MCP Server (Model Context Protocol):** AutonomousPlanningAgent còn được tích hợp MCP Filesystem Server — cho phép GPT-5.1 đọc và ghi file `sandbox/deals.md` như thể đó là một tool thông thường. Không cần code thêm file I/O thủ công.

```python
async def go(self):
    async with MCPServerStdio(params=files_params, client_session_timeout_seconds=60) as server:
        agent = Agent(
            name="Planner",
            model=self.MODEL,
            tools=self.get_tools(),
            mcp_servers=[server],   # GPT có thể write file qua MCP
        )
        reply = await Runner.run(agent, self.task)
    return reply.final_output
```

### 9.3 So sánh hai Planning Agents

| Đặc điểm | PlanningAgent | AutonomousPlanningAgent |
|----------|---------------|-------------------------|
| **Điều phối** | Code cứng (Python) | GPT-5.1 tự quyết định |
| **Linh hoạt** | Thấp — luôn estimate đủ 5 deals | Cao — GPT có thể chỉ estimate 3 deals tốt nhất |
| **MCP Support** | Không | Có (write file) |
| **Chi phí** | Thấp hơn | Cao hơn (thêm GPT-5.1 call) |
| **Dễ debug** | Có — luồng đơn giản | Khó — phụ thuộc vào GPT reasoning |
| **Default trong production** | Không | Có |

---

## Phần 10: App 1 — price_is_right.py (Autonomous Deal Hunter)

### 10.1 Tổng quan

`price_is_right.py` là ứng dụng autonomous: sau khi khởi động, nó tự chạy mỗi 5 phút mà không cần người dùng tương tác. Mục tiêu: tìm deals từ DealNews RSS → estimate giá → notify nếu đủ tốt.

### 10.2 DealAgentFramework — Quản lý trạng thái

```python
class DealAgentFramework:
    DB = "products_vectorstore"
    MEMORY_FILENAME = "memory.json"

    def __init__(self):
        client = chromadb.PersistentClient(path=self.DB)
        self.memory = self.read_memory()     # Load deals đã xử lý
        self.collection = client.get_or_create_collection('products')
        self.planner = None                  # Lazy init

    def read_memory(self) -> List[Opportunity]:
        """Load memory.json — danh sách deals đã gửi notification (tránh duplicate)."""
        if os.path.exists(self.MEMORY_FILENAME):
            with open(self.MEMORY_FILENAME, "r") as file:
                data = json.load(file)
            return [Opportunity(**item) for item in data]
        return []

    def write_memory(self) -> None:
        """Append deal mới vào memory.json."""
        data = [opportunity.dict() for opportunity in self.memory]
        with open(self.MEMORY_FILENAME, "w") as file:
            json.dump(data, file, indent=2)

    def run(self) -> List[Opportunity]:
        """Chạy một cycle: scan → estimate → notify → save."""
        self.init_agents_as_needed()
        result = self.planner.plan(memory=self.memory)
        if result:
            self.memory.append(result)
            self.write_memory()
        return self.memory

    @classmethod
    def get_plot_data(cls, max_datapoints=800):
        """Lấy data cho 3D t-SNE visualization."""
        client = chromadb.PersistentClient(path=cls.DB)
        collection = client.get_or_create_collection('products')
        result = collection.get(include=['embeddings', 'documents', 'metadatas'], limit=max_datapoints)
        vectors = np.array(result['embeddings'])
        categories = [m['category'] for m in result['metadatas']]
        colors = [COLORS[CATEGORIES.index(c)] for c in categories]
        tsne = TSNE(n_components=3, random_state=42, n_jobs=-1)
        reduced_vectors = tsne.fit_transform(vectors)
        return result['documents'], reduced_vectors, colors
```

**Memory system:** `memory.json` lưu danh sách deals đã xử lý. Mỗi cycle, ScannerAgent lọc bỏ các URL đã có trong memory — đảm bảo người dùng không nhận notification trùng lặp về cùng một deal.

### 10.3 Gradio UI của price_is_right.py

```python
class App:
    def run(self):
        with gr.Blocks(title="The Price is Right") as ui:

            # Bảng deals: Description | Price | Estimate | Discount | URL
            opportunities_dataframe = gr.Dataframe(
                headers=["Deals found so far", "Price", "Estimate", "Discount", "URL"],
                row_count=10,
            )

            # Logs HTML + Plot 3D t-SNE
            with gr.Row():
                logs = gr.HTML()
                plot = gr.Plot(value=get_plot())   # t-SNE visualization của ChromaDB

            # Load lần đầu + Timer mỗi 5 phút
            ui.load(run_with_logging, inputs=[log_data], outputs=[log_data, logs, opportunities_dataframe])
            timer = gr.Timer(value=300, active=True)
            timer.tick(run_with_logging, inputs=[log_data], outputs=[log_data, logs, opportunities_dataframe])

            # Click vào row → gửi notification thủ công
            opportunities_dataframe.select(do_select)
```

**Real-time logging:** Pipeline chạy trong thread riêng (`threading.Thread`), logs được đưa vào `queue.Queue`. Main thread poll queue mỗi 0.1s và yield log updates cho Gradio — tạo hiệu ứng streaming log real-time mà không block UI.

### 10.4 Workflow chi tiết

```
[Khởi động]
    │
    ├─ Load ChromaDB (800K products)
    ├─ Load memory.json (deals đã xử lý)
    └─ Vẽ 3D t-SNE plot (800 điểm ngẫu nhiên)
    │
    ▼ [Mỗi 5 phút hoặc khi load]
    │
[Step 1] ScannerAgent.scan(memory)
    ├─ Fetch 5 DealNews RSS categories (~25 deals)
    ├─ Lọc bỏ URLs đã có trong memory
    └─ GPT-5-mini chọn top 5 deals (Structured Outputs)
    │
[Step 2] EnsembleAgent.price() cho mỗi deal
    ├─ Preprocessor: LiteLLM viết lại text
    ├─ FrontierAgent: GPT-5.1 + RAG (ChromaDB) → 80%
    ├─ SpecialistAgent: Llama-3.2-3B (Modal T4) → 10%
    └─ NeuralNetworkAgent: PyTorch DNN (local) → 10%
    │
[Step 3] Sort by discount (cao nhất đầu)
    │
[Step 4] if best.discount > $50:
    └─ MessagingAgent.notify() → Pushover push notification
    │
[Step 5] Append best deal vào memory.json
         Update Gradio dataframe
    │
[Sleep 5 phút] ──────────────────────────► [Lặp lại từ Step 1]
```

---

## Phần 11: App 2 — search_key.py (Multi-Source Deal Finder)

### 11.1 Tổng quan

`search_key.py` là ứng dụng tương tác: người dùng nhập keyword → hệ thống tìm kiếm song song trên BestBuy và Amazon → trả về top 3 deals với ước lượng giá thực. Đây là ứng dụng được phát triển sau, mở rộng từ `price_is_right.py` để hỗ trợ scraping thực tế từ hai nguồn thay vì chỉ RSS.

### 11.2 Thách thức kỹ thuật: Scraping BestBuy và Amazon từ WSL2

**Vấn đề:** Cả BestBuy và Amazon đều dùng hệ thống phát hiện bot tinh vi. Requests HTTP thông thường từ WSL2 bị chặn ngay lập tức.

**Giải pháp: `curl_cffi` với Chrome impersonation**

`curl_cffi` là thư viện HTTP có thể giả lập TLS fingerprint của Chrome — cách mà các trang web phát hiện bot. Bằng cách dùng `impersonate="chrome"`, request của chúng ta trông giống hệt request từ trình duyệt Chrome thực sự.

```python
from curl_cffi import requests as cffi_requests

session = cffi_requests.Session(impersonate="chrome")
# Từ đây, mọi request từ session này đều có TLS fingerprint của Chrome
response = session.get("https://www.bestbuy.com/...", headers=headers)
```

### 11.3 BestBuy Scraping (`bestbuy_deals.py`)

BestBuy product pages bị chặn từ WSL2 (HTTP/2 + Akamai CDN). Giải pháp: dùng internal APIs thay vì scrape HTML.

**3 API endpoints của BestBuy được dùng:**

| API | Endpoint | Dữ liệu lấy về |
|-----|----------|----------------|
| Search | `/site/searchpage.jsp` | Apollo SSR cache → list `{skuId, pdpUrl}` |
| Price Blocks | `/api/3.0/priceBlocks` | price, brand, name, onSale (batch cho nhiều SKU) |
| Product Details | `/api/v2/product/<skuId>` | features, clean URL |

```python
def search_filter_scrape_bestbuy(keyword: str, max_results: int = 6) -> List[ScrapedBestBuyDeal]:
    """Pipeline BestBuy hoàn chỉnh."""
    session = _init_session()         # curl_cffi + bypass country selection

    # 1. Search: GET searchpage.jsp → parse Apollo SSR cache → {skuId, url}
    sku_list = search_bestbuy(session, keyword)

    # 2. Filter: GET priceBlocks API → chỉ lấy sản phẩm onSale = True
    price_data = get_price_blocks(session, [s["skuId"] for s in sku_list])
    on_sale = [p for p in price_data if p.get("onSale")][:max_results]

    # 3. Scrape details: GET v2 product API → features + clean URL
    deals = []
    for item in on_sale:
        details = get_product_details(session, item["skuId"])
        deals.append(ScrapedBestBuyDeal(
            title=item["name"], brand=item["brand"],
            price=item["price"], features=details["features"], url=details["url"]
        ))
    return deals
```

### 11.4 Amazon Scraping (`amazon_deals.py`)

Amazon dùng HTML parsing thay vì internal APIs:

```python
def search_filter_scrape_amazon(keyword: str, max_results: int = 6) -> List[ScrapedAmazonDeal]:
    """Pipeline Amazon hoàn chỉnh."""
    session = init_amazon_session()   # curl_cffi + POST set ZIP 96150 (để có giá USD)

    # Search: GET search page, parse HTML → list products
    search_results = search_amazon(session, keyword)

    # Filter on_sale only
    on_sale = [r for r in search_results if r.get("on_sale")][:max_results]

    deals = []
    for item in on_sale:
        # Approach A: specs từ search page đủ dài (>= 50 chars) → dùng luôn
        # Approach B: specs ngắn → GET product page để lấy #feature-bullets
        if len(item.get("specs", "")) < 50:
            item["specs"] = scrape_product_page(session, item["url"])

        deals.append(ScrapedAmazonDeal(
            title=item["title"], brand=item.get("brand", ""),
            price=item["price"], features=item["specs"], url=item["url"]
        ))
    return deals
```

**Hai Approach:** Approach A nhanh (không cần request thêm), Approach B tốn thêm 2-3s mỗi sản phẩm nhưng lấy được thông số đầy đủ từ trang sản phẩm.

**ZIP Code 96150:** Đây là ZIP của Lake Tahoe, California — được dùng để ép Amazon hiển thị giá USD thay vì giá theo vùng. Trick này được POST qua API khi khởi tạo session.

### 11.5 MultiSourcePlanningAgent — Pipeline 4 bước

```python
class MultiSourcePlanningAgent(Agent):
    name = "Multi-Source Planning Agent"
    color = Agent.GREEN
    DEAL_THRESHOLD = 100    # Auto-notify nếu discount > $100

    def plan(self, keyword: str, max_urls: int = 6, source: str = "All") -> List[Opportunity]:
        """Pipeline hoàn chỉnh: search → combine → select → estimate."""
        pipeline_start = time.time()

        # Step 1: Search + Filter + Scrape (BestBuy + Amazon song song)
        t0 = time.time()
        if source == "All":
            with ThreadPoolExecutor(max_workers=2) as executor:
                bb_future = executor.submit(self._bestbuy_pipeline, keyword, max_urls)
                az_future = executor.submit(self._amazon_pipeline, keyword, max_urls)
                bb_deals = bb_future.result()
                az_deals = az_future.result()
        # source == "BestBuy" hoặc "Amazon": chạy chỉ một nguồn
        self.log(f"[TIMER] Step 1 completed in {time.time() - t0:.1f}s")

        # Step 2: Combine → UnifiedScrapedDeal pool
        unified_deals = self.combine(bb_deals, az_deals)

        # Step 3: GPT-5-nano chọn top 3 deals từ pool hỗn hợp
        deal_selection = self.select_top_deals(unified_deals)

        # Step 4: EnsembleAgent estimate cho mỗi deal
        opportunities = self.estimate_prices(deal_selection)

        # Auto-notify nếu deal tốt nhất vượt threshold
        if opportunities and opportunities[0].discount > self.DEAL_THRESHOLD:
            best = opportunities[0]
            self.messenger.notify(...)

        total = time.time() - pipeline_start
        self.log(f"Pipeline completed! Total: {total:.1f}s ({total/60:.1f} min)")
        return opportunities
```

**ThreadPoolExecutor:** BestBuy và Amazon scraping chạy song song — giảm thời gian Step 1 từ ~12-20s xuống còn ~6-8s (bottleneck là nguồn chậm hơn).

### 11.6 UnifiedScrapedDeal — Chuẩn hóa 2 nguồn

Sau khi scrape, BestBuy deals và Amazon deals có format khác nhau. `UnifiedScrapedDeal` chuẩn hóa về format chung:

```python
class UnifiedScrapedDeal:
    source: str   # "BestBuy" hoặc "Amazon"
    title: str
    brand: str
    price: float
    features: str
    url: str

    @classmethod
    def from_bestbuy(cls, deal: ScrapedBestBuyDeal) -> "UnifiedScrapedDeal":
        return cls(source="BestBuy", title=deal.title, ...)

    @classmethod
    def from_amazon(cls, deal: ScrapedAmazonDeal) -> "UnifiedScrapedDeal":
        return cls(source="Amazon", title=deal.title, ...)

    def describe(self) -> str:
        """Format cho LLM prompt: [Source] Title\nBrand\nPrice\nFeatures\nURL"""
        return f"[{self.source}] {self.title}\nBrand: {self.brand}\nPrice: ${self.price:.2f}\n..."
```

### 11.7 MultiSourceScannerAgent — Chọn top 3 từ pool hỗn hợp

```python
class MultiSourceScannerAgent(Agent):
    MODEL = "gpt-5-nano"   # Model rẻ nhất, reasoning_effort="minimal"

    def scan(self, unified_deals: List[UnifiedScrapedDeal]) -> Optional[DealSelection]:
        """GPT-5-nano chọn 3 deals có description chi tiết nhất từ pool BestBuy + Amazon."""
        prompt = self._build_prompt(unified_deals)  # describe() mỗi deal
        result = self.openai.chat.completions.parse(
            model=self.MODEL,
            messages=[{"role": "system", "content": self.SYSTEM_PROMPT},
                       {"role": "user", "content": prompt}],
            response_format=DealSelection,
            reasoning_effort="minimal",
        )
        return result.choices[0].message.parsed
```

Prompt yêu cầu GPT prefix tên deal bằng `[BestBuy]` hoặc `[Amazon]` — giúp biết nguồn khi hiển thị kết quả.

### 11.8 Gradio UI của search_key.py

```python
class App:
    def run(self):
        with gr.Blocks(title="Multi-Source Deal Finder") as ui:
            # Input: keyword + max_urls + source (All/BestBuy/Amazon)
            keyword_input = gr.Textbox(label="What are you looking for?")
            max_urls_input = gr.Number(label="Max URLs (per source)", value=6)
            source_input = gr.Radio(choices=["All", "BestBuy", "Amazon"], value="All")
            search_btn = gr.Button("Search", variant="primary")

            # Output: HTML table + logs
            results_table = gr.HTML()    # clickable URLs, color-coded by discount
            logs_html = gr.HTML()        # real-time pipeline logs (dark theme)

            # Push Notification thủ công
            deal_index = gr.Number(label="Deal # to notify (0 = best)")
            push_btn = gr.Button("Send Push Notification")
```

**HTML Table thay vì Dataframe:** `search_key.py` dùng `gr.HTML` thay vì `gr.Dataframe` cho bảng kết quả — vì cần URL clickable và color-coding theo mức discount (HOT DEAL/Good Deal/OK/Overpriced).

**Threading + Queue logging:** Giống `price_is_right.py`, pipeline chạy trong thread riêng và stream logs real-time qua queue. Ngoài ra, `search_key.py` có một `QueueHandler` riêng được tích hợp vào Python logging system — mọi `logging.info()` trong bất kỳ agent nào cũng tự động xuất hiện trong logs panel của Gradio.

---

## Phần 12: Kiến trúc 3 tầng tổng thể

### 12.1 Sơ đồ toàn hệ thống

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TẦNG UI (User Interface)                            │
│                                                                               │
│  price_is_right.py (Gradio)           search_key.py (Gradio)                 │
│  ├─ Dataframe (deals history)         ├─ HTML table (top 3 deals)            │
│  ├─ Logs HTML (real-time)             ├─ Logs HTML (real-time)               │
│  ├─ 3D Plot (t-SNE ChromaDB)         └─ Push notification button             │
│  └─ Timer (5 min auto-refresh)                                               │
└─────────────────────────┬────────────────────────────────┬───────────────────┘
                          │                                │
                          ▼                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TẦNG FRAMEWORK (Orchestrator)                          │
│                                                                               │
│  DealAgentFramework                   MultiSourceFramework                   │
│  ├─ ChromaDB init                     ├─ ChromaDB init                       │
│  ├─ memory.json (read/write)          └─ Lazy init MultiSourcePlanningAgent │
│  └─ Lazy init AutonomousPlanningAgent                                        │
└─────────────────────────┬────────────────────────────────┬───────────────────┘
                          │                                │
                          ▼                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TẦNG AGENT (Business Logic)                          │
│                                                                               │
│  AutonomousPlanningAgent              MultiSourcePlanningAgent               │
│  ├─ ScannerAgent (RSS feeds)          ├─ BestBuyDeals (curl_cffi + APIs)    │
│  ├─ EnsembleAgent                     ├─ AmazonDeals (curl_cffi + HTML)     │
│  │   ├─ Preprocessor (LiteLLM)       ├─ UnifiedScrapedDeal (normalize)     │
│  │   ├─ FrontierAgent (GPT+RAG)      ├─ MultiSourceScannerAgent (GPT-nano) │
│  │   ├─ SpecialistAgent (Modal)       └─ EnsembleAgent (shared)             │
│  │   └─ NeuralNetworkAgent (local)                                           │
│  └─ MessagingAgent (Pushover)                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                                    │
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  OpenAI      │  │  Modal       │  │  ChromaDB    │  │  Pushover    │   │
│  │  GPT-5.1     │  │  T4 GPU      │  │  800K items  │  │  Push API    │   │
│  │  GPT-5-mini  │  │  Llama-3.2   │  │  384-dim     │  │              │   │
│  │  GPT-5-nano  │  │  3B QLoRA    │  │  vectors     │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │  BestBuy     │  │  Amazon      │  │  DealNews    │                      │
│  │  Internal    │  │  HTML+curl   │  │  RSS Feeds   │                      │
│  │  APIs        │  │  cffi        │  │  5 categories│                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phần 13: Các kỹ thuật quan trọng

### 13.1 Structured Outputs với Pydantic

Kỹ thuật cốt lõi để tích hợp LLM vào hệ thống phần mềm. Thay vì parse string thủ công bằng Regex, sử dụng Pydantic để đảm bảo LLM trả về data đúng format 100%:

```python
# Định nghĩa schema
class DealSelection(BaseModel):
    deals: List[Deal]

# Gọi OpenAI với response_format=DealSelection
result = openai.chat.completions.parse(
    model="gpt-5-mini",
    messages=[...],
    response_format=DealSelection,   # Key: ép LLM trả về JSON khớp schema
)
deal_selection = result.choices[0].message.parsed  # Đã là Python object, không cần json.loads()
```

**Cơ chế Constrained Decoding:** OpenAI chuyển Pydantic schema sang JSON Schema, rồi dùng token-level masking khi generate — mỗi token được sinh ra phải hợp lệ theo schema. Không thể có JSON sai cú pháp.

### 13.2 LiteLLM — Multi-provider abstraction

`preprocessor.py` và `messaging_agent.py` dùng LiteLLM thay vì OpenAI SDK trực tiếp:

```python
from litellm import completion

# LiteLLM hỗ trợ hàng chục providers với cùng API interface
response = completion(
    model="ollama/llama3.2",   # Local Ollama (miễn phí)
    # hoặc "gpt-5-nano"        # OpenAI
    # hoặc "groq/openai/..."   # Groq
    messages=[...]
)
```

Lợi ích: có thể đổi model preprocessor bằng cách thay đổi env var `PRICER_PREPROCESSOR_MODEL` mà không cần sửa code.

### 13.3 Real-time Log Streaming trong Gradio

Pattern này được dùng trong cả hai ứng dụng:

```python
def _run_pipeline(self, query, initial_log):
    """Generator pattern: yield UI updates trong khi pipeline đang chạy."""
    log_q = queue.Queue()
    result_q = queue.Queue()
    setup_logging(log_q)    # Redirect logging.info() vào queue

    def worker():
        opps = self.framework.run(query, self.max_urls, self.source)
        result_q.put(opps)

    thread = threading.Thread(target=worker)
    thread.start()

    while thread.is_alive() or not result_q.empty():
        # Poll log queue mỗi 0.1s, yield update lên Gradio
        while True:
            try:
                log_data.append(log_q.get_nowait())
            except queue.Empty:
                break
        yield current_table, "Processing...", html_for_logs(log_data)
        time.sleep(0.1)
```

Gradio hỗ trợ generator functions — mỗi `yield` cập nhật UI ngay lập tức mà không cần chờ pipeline xong. Người dùng thấy log stream theo thời gian thực.

### 13.4 Lazy Initialization

Cả `DealAgentFramework` và `MultiSourceFramework` đều dùng lazy initialization cho agents:

```python
def init_agents_as_needed(self):
    """Chỉ khởi tạo agents khi cần — không block thời gian startup."""
    if not self.planner:
        self.planner = AutonomousPlanningAgent(self.collection)
        # Lúc này mới tạo SpecialistAgent → kết nối Modal
        # Mới tạo NeuralNetworkAgent → load 1GB DNN weights
```

Lý do: load DNN weights (~1GB) và kết nối Modal mất 30-60s. Nếu khởi tạo ngay khi start, UI sẽ bị trắng hàng phút. Lazy init cho phép Gradio hiển thị giao diện ngay, chỉ tạo agents khi người dùng thực sự cần.

---

## Phần 14: Setup và Chạy

### 14.1 Yêu cầu

- Python 3.12, `uv` package manager
- API keys: `OPENAI_API_KEY` (bắt buộc), `PUSHOVER_USER` + `PUSHOVER_TOKEN` (tùy chọn)
- Node.js 18+ (cho MCP Filesystem server trong AutonomousPlanningAgent)
- Modal account với `pricer-service` đã deploy

### 14.2 Triển khai Modal Service (một lần)

```bash
cd segment4

# Setup Modal token
uv run modal token set --token-id <ID> --token-secret <SECRET>

# Deploy Pricer service lên Modal cloud
uv run modal deploy price_agents/khong_su_dung/pricer_service2.py

# Kiểm tra service đã chạy
uv run modal app list
```

### 14.3 Environment Variables (`segment4/.env`)

```env
OPENAI_API_KEY=sk-xxx              # Bắt buộc (cho GPT calls và ScannerAgent)
PUSHOVER_USER=xxx                  # Tùy chọn (push notification)
PUSHOVER_TOKEN=xxx                 # Tùy chọn
PRICER_PREPROCESSOR_MODEL=ollama/llama3.2  # Tùy chọn, default: Ollama local
GROQ_API_KEY=xxx                   # Tùy chọn (nếu dùng Groq cho preprocessor)
HF_TOKEN=hf_xxx                    # Cần cho Modal deploy (tải Llama từ HuggingFace)
```

### 14.4 Chạy ứng dụng

```bash
cd tech2ai && uv sync

# App 1: Autonomous Deal Hunter
cd segment4 && uv run price_is_right.py
# → http://127.0.0.1:7860 — tự động chạy mỗi 5 phút

# App 2: Multi-Source Deal Finder
cd segment4 && uv run search_key.py
# → http://127.0.0.1:7860 — nhập keyword để tìm kiếm
```

---

## Phần 15: Hiệu năng và Chi phí

### 15.1 Thời gian thực thi

**price_is_right.py (mỗi cycle 5 phút):**

```
Tổng: ~60-90 giây

  ├── Fetch RSS feeds (5 categories):        5-10s
  ├── GPT-5-mini chọn top 5:                3-5s
  ├── EnsembleAgent × 5 deals:
  │   ├── Preprocessor (5 × Ollama local):  15-20s
  │   ├── FrontierAgent (5 × GPT-5.1+RAG): 10-15s
  │   ├── SpecialistAgent (5 × Modal):      10-20s
  │   │   └─ Cold start lần đầu:           +30-60s
  │   └── NeuralNetworkAgent (5 × local):   1-2s
  └── Notification (nếu có):                1-2s
```

**search_key.py (mỗi search):**

```
Tổng: ~70-100 giây

  ├── Step 1: Search+Filter+Scrape (parallel):
  │   ├── BestBuy (curl_cffi + APIs):       4-8s
  │   └── Amazon (curl_cffi + HTML):        2-14s
  │   Thực tế: max(BestBuy, Amazon) ≈ 6-8s
  ├── Step 2: Combine (UnifiedScrapedDeal): <1s
  ├── Step 3: GPT-5-nano chọn top 3:       5-10s
  └── Step 4: EnsembleAgent × 3 deals:     40-60s
```

### 15.2 Chi phí ước tính

**price_is_right.py:**

| Component | Model | Chi phí/cycle |
|-----------|-------|---------------|
| Scanner | GPT-5-mini | ~$0.002 |
| Frontier (5 calls) | GPT-5.1 | ~$0.010 |
| Specialist (5 calls) | Modal T4 | ~$0.010 |
| Messaging | GPT-5-nano | ~$0.001 |
| Preprocessor | Ollama local | $0 |
| Neural Network | Local | $0 |
| **Tổng/cycle** | | **~$0.023** |
| **Daily (288 cycles)** | | **~$6.62** |

**search_key.py:** ~$0.015/search (3 deals thay vì 5).

---

## Phần 16: Chi tiết các file hỗ trợ chưa được giải thích đầy đủ

### `log_utils.py` — Chuyển đổi ANSI sang HTML

**Mục đích:** Giữ nguyên màu sắc ANSI từ terminal logging khi hiển thị trong Gradio HTML panel. Không có file này, logs trong Gradio sẽ hiển thị chuỗi escape code thô như `\033[31m` thay vì màu đỏ.

```python
# Mapping: ANSI code → màu HEX để dùng trong CSS
mapper = {
    BG_BLACK+RED:     "#dd0000",   # SpecialistAgent (đỏ)
    BG_BLACK+GREEN:   "#00dd00",   # PlanningAgent (xanh lá)
    BG_BLACK+YELLOW:  "#dddd00",   # EnsembleAgent, FrontierAgent (vàng)
    BG_BLACK+BLUE:    "#0000ee",
    BG_BLACK+MAGENTA: "#aa00dd",   # MessagingAgent (tím)
    BG_BLACK+CYAN:    "#00dddd",   # ScannerAgent (xanh lam nhạt)
    BG_BLACK+WHITE:   "#87CEEB",   # Agent thông thường
    BG_BLUE+WHITE:    "#ff7800"    # Highlight đặc biệt (cam)
}

def reformat(message: str) -> str:
    """Thay thế ANSI codes bằng HTML span tags với màu tương ứng."""
    for ansi_code, hex_color in mapper.items():
        message = message.replace(ansi_code, f'<span style="color: {hex_color}">')
    message = message.replace(RESET, '</span>')
    return message
```

**Chuỗi xử lý:** `Agent.log()` → Python `logging.info()` (với ANSI codes) → `QueueHandler` đẩy vào queue → `html_for_logs()` gọi `reformat()` → HTML `<span>` có màu → Gradio hiển thị.

---

### `bestbuy_untils/gradio_helpers.py` — Hệ thống streaming logs real-time

**Mục đích:** Cung cấp các tiện ích để Gradio hiển thị logs từ pipeline chạy trong background thread theo thời gian thực.

**`class QueueHandler(logging.Handler)`**

**Mục đích:** Custom handler cho Python `logging` module — thay vì ghi ra terminal (StreamHandler) hoặc file (FileHandler), nó đưa mỗi log record vào một `queue.Queue`. Điều này cho phép pipeline chạy trong background thread truyền logs sang main thread một cách thread-safe.

```python
class QueueHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        """Mỗi khi logging.info() được gọi, record đi vào queue thay vì stdout."""
        self.log_queue.put(self.format(record))
```

**`setup_logging(log_queue)`**

**Mục đích:** Cấu hình root logger dùng `QueueHandler`. Hàm này cần được gọi trước khi chạy pipeline trong thread — sau đó mọi `logging.info()` từ bất kỳ agent nào đều tự động vào queue. Không cần sửa code bên trong các agents.

Lưu ý quan trọng: hàm này xóa các `QueueHandler` cũ trước khi thêm mới — tránh trường hợp gọi nhiều lần tạo duplicate handlers làm mỗi log xuất hiện nhiều lần.

**`html_for_logs(log_data, max_logs=25)`**

**Mục đích:** Convert list log messages thành HTML styled với dark background (#1a1a2e) để hiển thị trong Gradio. Chỉ lấy 25 logs gần nhất để tránh panel quá dài. Gọi `reformat()` từ `log_utils.py` để giữ màu ANSI.

**`opportunities_to_html(opportunities)`**

**Mục đích:** Convert list `Opportunity` thành HTML table có URL clickable và color-coding theo mức discount:
- `discount > $200` → HOT
- `discount > $100` → Good
- `discount > $0` → OK
- `discount ≤ 0` → Overpriced

Lý do dùng `gr.HTML` thay vì `gr.Dataframe`: Gradio Dataframe không hỗ trợ clickable URL links. HTML table custom cho phép `<a href="..." target="_blank">` để người dùng mở link trực tiếp.

---

### `price_agents/deals.py` — Data Models chi tiết

**`extract(html_snippet: str) → str`**

**Mục đích:** Làm sạch HTML từ RSS feed. DealNews RSS trả về HTML raw trong trường `summary` (chứa tags `<div>`, `<span>`, v.v.). BeautifulSoup tìm `div.snippet.summary` rồi trích xuất text thuần. Loại bỏ newlines để text nằm trên một dòng.

**`ScrapedDeal.__init__(entry: Dict)`**

**Mục đích:** Khởi tạo deal từ một RSS entry. Bước quan trọng: sau khi lấy URL từ RSS, method này cố gắng fetch thêm trang web deal để lấy phần `details` và `features` đầy đủ hơn. Có fallback: nếu request timeout hoặc trang web không có `content-section`, dùng summary từ RSS làm details.

**Cơ chế tách details/features:**
```python
if "Features" in content:
    self.details, self.features = content.split("Features", 1)
else:
    self.details = content
    self.features = ""
```
DealNews format trang sản phẩm thường có section "Features" chia đôi nội dung — phần trước là mô tả tổng quát (details), phần sau là bullet points tính năng (features).

**`ScrapedDeal.truncate()`**

**Mục đích:** Giới hạn độ dài để tránh gửi quá nhiều tokens cho LLM. `title` tối đa 100 chars, `details` và `features` mỗi cái 500 chars. Thông tin quan trọng (brand, model, giá) thường nằm ở đầu — cắt đuôi ít mất thông tin.

**`ScrapedDeal.describe() → str`**

**Mục đích:** Tạo text đẹp để đưa vào LLM prompt. Format: `Title: ... / Details: ... / Features: ... / URL: ...`. Dùng bởi `ScannerAgent.scan()` khi tạo prompt gửi cho GPT-5-mini.

**`ScrapedDeal.fetch(show_progress=False) → List[ScrapedDeal]`**

**Mục đích:** Fetch toàn bộ deals từ 5 RSS feeds của DealNews. Mỗi feed lấy tối đa 5 entries → tổng ~25 deals. `time.sleep(0.05)` giữa mỗi deal để không spam requests quá nhanh. `show_progress=True` hiển thị `tqdm` progress bar (dùng trong notebook, tắt trong production để tránh nhiễu logs).

**`Deal(BaseModel)` — Field descriptions**

Field `product_description` có Pydantic `Field(description=...)` rất chi tiết:
```python
product_description: str = Field(
    description="""Your clearly expressed summary in 3-4 sentences.
    Details of the item are much more important than why it's a good deal.
    Avoid mentioning discounts and coupons; focus on the item itself."""
)
```
Description này được OpenAI Structured Outputs dùng như một phần của JSON Schema — GPT đọc nó và biết cần viết mô tả sản phẩm trung lập, không đề cập deal/discount. Đây là kỹ thuật prompt engineering thông qua schema thay vì system prompt.

**`DealSelection(BaseModel)`**

Field `deals` yêu cầu GPT chọn các deals "có description chi tiết nhất, giá rõ ràng nhất, và là deal thực sự tốt". Ràng buộc này nằm trong schema — không cần nhắc lại trong prompt.

---

### `bestbuy_untils/unified_deal.py` — Chuẩn hóa 2 nguồn

**`UnifiedScrapedDeal.from_bestbuy(deal)` và `from_amazon(deal)`**

**Mục đích:** Factory methods chuyển đổi từ format riêng của từng nguồn (`ScrapedBestBuyDeal`, `ScrapedAmazonDeal`) sang format chung. Đây là mẫu **Adapter pattern** — phần còn lại của hệ thống chỉ làm việc với `UnifiedScrapedDeal`, không biết nguồn gốc.

Truncation trong `__init__`: `title` giới hạn 200 chars, `features` giới hạn 1500 chars. Lý do: BestBuy API v2 đôi khi trả về `features` rất dài (list bullet điểm hàng trăm dòng). 1500 chars đủ để GPT hiểu sản phẩm mà không waste tokens.

**`UnifiedScrapedDeal.describe() → str`**

**Mục đích:** Format deal cho LLM prompt trong `MultiSourceScannerAgent.scan()`. Prefix `[BestBuy]` hoặc `[Amazon]` trong output giúp GPT-5-nano khi trả về `DealSelection` biết cần giữ prefix này trong `product_description`. Từ đó người dùng biết deal đến từ nguồn nào.

---

## Phần 17: Leaderboard và kết quả thực nghiệm

### Ensemble vs từng model đơn lẻ

Kết quả trên 200 mẫu test (cùng test set, `set_seed(42)`):

| Model | Loại | MAE | Ghi chú |
|-------|------|-----|---------|
| **EnsembleAgent** | Combo | **$29.9** | Production model — tốt nhất |
| FrontierAgent (GPT-5.1+RAG) | LLM | $44.06 | Đứng 1 trong leaderboard toàn khóa |
| Fine-tuned Llama 3.2 3B | LLM | $39.85 | Chỉ số tốt nhất Week 7, nhưng đây là test set Week 6 |
| HashingVec DNN (5 epochs) | DL | $46.02 | Baseline production hiện tại |
| Claude Opus 4.5 (zero-shot) | LLM | $47.10 | Human-level reference |
| Human (giảng viên) | Bio | $87.62 | Baseline con người |

**Tại sao Ensemble ($29.9) tốt hơn FrontierAgent đơn lẻ ($44.06)?**

Mỗi model có điểm mù riêng:
- FrontierAgent đôi khi "hallucinate" giá xa thực tế khi ChromaDB không tìm được sản phẩm tương tự tốt
- SpecialistAgent có thể fail với sản phẩm ngoài phân phối của training data
- NeuralNetworkAgent bị kéo về giá trung bình khi gặp sản phẩm đặc thù

Khi 3 models dự đoán cùng lúc, các lỗi cực đoan (outliers) bị kéo về gần giá thực. Trọng số 80/10/10 ưu tiên FrontierAgent vì nó có context thực tế từ RAG — nhưng 20% còn lại đủ để điều chỉnh khi FrontierAgent sai.

### Kết quả scraping thực tế

**BestBuy:**
- Thời gian pipeline: ~4-8 giây cho 6 sản phẩm on-sale
- Tỷ lệ thành công: ~90% (đôi khi BestBuy rate-limit hoặc Apollo cache không có)

**Amazon:**
- Approach A (search page only): ~2 giây — hoạt động với laptop, TV, điện thoại (specs đủ dài)
- Approach B (product page): ~14 giây — cần thiết với headphones, accessories (specs ngắn)
- Tỷ lệ thành công: ~80% (CAPTCHA đôi khi trigger, zip 96150 giảm thiểu nhưng không loại bỏ hoàn toàn)

---

## Tổng kết

Hệ thống "The Price Is Right" là kết quả của 8 tuần học — từ dataset thô 3 triệu sản phẩm Amazon đến hai ứng dụng production hoàn chỉnh:

| Thành tựu | Chi tiết |
|-----------|---------|
| **Ensemble MAE** | $29.9 — tốt hơn mọi model đơn lẻ, tốt hơn cả Claude Opus 4.5 ($47.10) |
| **Hai ứng dụng** | Autonomous (RSS-based) + Interactive (keyword search) |
| **Hai nguồn scraping** | BestBuy (internal APIs) + Amazon (HTML parsing), song song |
| **Ba models** | GPT-5.1+RAG (80%) + Llama fine-tuned (10%) + DNN (10%) |
| **Deployment** | Modal serverless T4 GPU, chỉ tốn tiền khi chạy |
| **UI** | Gradio với real-time logs, 3D visualization ChromaDB |

Điểm kỹ thuật nổi bật nhất: toàn bộ hệ thống được xây từ nguyên lý cơ bản (no LangChain, no CrewAI), sử dụng Python thuần kết hợp với các API mạnh (OpenAI Structured Outputs, Modal Serverless, MCP Protocol) — cho phép kiểm soát hoàn toàn và dễ debug khi có vấn đề.
