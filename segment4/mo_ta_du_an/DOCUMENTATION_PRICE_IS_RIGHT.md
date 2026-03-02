# 🎯 THE PRICE IS RIGHT - AUTONOMOUS DEAL HUNTER

## 📌 Tổng quan dự án

**Tên dự án:** The Price is Right - Autonomous Agent Framework  
**Tên file chính:** `price_is_right.py`  
**Phiên bản:** v4.0 (Original Architecture)  
**Ngày cập nhật:** 2026-02-07  
**Ngôn ngữ:** Python 3.10+

### Mục tiêu dự án

Dự án này là một **hệ thống Autonomous AI Agent** tự động:

1. **Quét RSS feeds** từ DealNews.com mỗi 5 phút
2. **Lọc và chọn** 5 deals tốt nhất bằng GPT-5-mini
3. **Ước lượng giá trị thực** bằng Ensemble AI (3 models)
4. **Tự động gửi notification** qua Pushover khi phát hiện deal tốt
5. **Lưu trữ lịch sử** vào memory.json và ghi file deals.md

**Điểm đặc biệt:** Hệ thống chạy **hoàn toàn tự động** (autonomous) sau khi khởi động, không cần input từ người dùng.

---

## 🎯 Đầu vào và Đầu ra

### Đầu vào (Input)

| Input | Mô tả | Nguồn |
|-------|-------|-------|
| **RSS Feeds** | 5 categories từ DealNews.com | Tự động fetch |
| **memory.json** | Deals đã xử lý (tránh duplicate) | Local file |
| **ChromaDB** | 800K products đã embed | Vector database |

**RSS Feed Categories:**
- Electronics
- Computers
- Smart Home
- Automotive
- Home & Garden

### Đầu ra (Output)

| Output | Mô tả |
|--------|-------|
| **Gradio Dashboard** | Bảng deals real-time + logs + 3D visualization |
| **Push Notification** | Thông báo Pushover khi có deal tốt (discount > $50) |
| **memory.json** | Lưu deals đã xử lý |
| **sandbox/deals.md** | File markdown mô tả deal (Autonomous mode) |

### Ví dụ Output (memory.json)

```json
[
  {
    "deal": {
      "product_description": "Samsung Galaxy Watch Ultra 47mm LTE Titanium...",
      "price": 350.0,
      "url": "https://www.dealnews.com/..."
    },
    "estimate": 773.81,
    "discount": 423.81
  }
]
```

---

## 🔄 Workflow - Luồng hoạt động

### Sơ đồ tổng quan

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      AUTONOMOUS DEAL HUNTER WORKFLOW                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  [Khởi động]                                                                  │
│      │                                                                        │
│      ▼                                                                        │
│  ╔══════════════════════════════════════╗                                    │
│  ║  0. LOAD RESOURCES                   ║                                    │
│  ║  ├── ChromaDB (400K products)        ║                                    │
│  ║  ├── memory.json (deals đã xử lý)    ║                                    │
│  ║  └── t-SNE 3D visualization          ║                                    │
│  ╚══════════════════════════════════════╝                                    │
│      │                                                                        │
│      ▼                                                                        │
│  ╔══════════════════════════════════════╗                                    │
│  ║  1. SCAN RSS FEEDS                   ║  ← ScannerAgent (GPT-5-mini)       │
│  ║  ├── Fetch từ 5 DealNews categories  ║                                    │
│  ║  ├── Loại bỏ URLs đã có trong memory ║                                    │
│  ║  └── GPT chọn top 5 deals            ║                                    │
│  ╚══════════════════════════════════════╝                                    │
│      │                                                                        │
│      ▼                                                                        │
│  ╔══════════════════════════════════════╗                                    │
│  ║  2. ESTIMATE PRICES                  ║  ← EnsembleAgent (3 models)        │
│  ║  ├── Preprocessor (chuẩn hóa text)   ║                                    │
│  ║  ├── FrontierAgent: GPT-5.1 + RAG    ║  → 80% weight                      │
│  ║  ├── SpecialistAgent: Llama (Modal)  ║  → 10% weight                      │
│  ║  └── NeuralNetworkAgent: PyTorch DNN ║  → 10% weight                      │
│  ╚══════════════════════════════════════╝                                    │
│      │                                                                        │
│      ▼                                                                        │
│  ╔══════════════════════════════════════╗                                    │
│  ║  3. CALCULATE DISCOUNT               ║                                    │
│  ║     discount = estimate - deal_price ║                                    │
│  ║     Sort by discount (cao nhất đầu)  ║                                    │
│  ╚══════════════════════════════════════╝                                    │
│      │                                                                        │
│      ├── discount > $50 ─────────────────────────────────────┐               │
│      │                                                       ▼               │
│      │                                    ╔════════════════════════════════╗ │
│      │                                    ║  4. NOTIFY USER               ║ │
│      │                                    ║  ├── MessagingAgent (Pushover)║ │
│      │                                    ║  └── GPT craft message        ║ │
│      │                                    ╚════════════════════════════════╝ │
│      │                                                       │               │
│      ◄───────────────────────────────────────────────────────┘               │
│      │                                                                        │
│      ▼                                                                        │
│  ╔══════════════════════════════════════╗                                    │
│  ║  5. SAVE TO MEMORY                   ║                                    │
│  ║  ├── Append best deal to memory.json ║                                    │
│  ║  └── Update Gradio dashboard         ║                                    │
│  ╚══════════════════════════════════════╝                                    │
│      │                                                                        │
│      ▼                                                                        │
│  [Sleep 5 phút] ────────────────────────────────────────────► [Lặp lại]      │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Chi tiết 2 chế độ hoạt động

#### Mode 1: PlanningAgent (Simple)

```
PlanningAgent.plan()
    │
    ├── 1. scanner.scan() → DealSelection (5 deals)
    │       └── Fetch RSS → Filter memory → GPT select top 5
    │
    ├── 2. For each deal: ensemble.price()
    │       └── preprocessor → frontier + specialist + neural
    │
    ├── 3. Sort by discount
    │
    ├── 4. If best.discount > $50:
    │       └── messenger.alert(best)
    │
    └── 5. Return best deal or None
```

#### Mode 2: AutonomousPlanningAgent (Advanced - MCP)

```
AutonomousPlanningAgent.plan()
    │
    ├── Uses OpenAI GPT-5.1 as Controller
    │
    ├── Tools available (function_tool):
    │   ├── scan_the_internet_for_bargains()
    │   ├── estimate_true_value(description)
    │   └── notify_user_of_deal(description, price, estimate, url)
    │
    ├── MCP Server: Filesystem (write sandbox/deals.md)
    │
    └── Agent tự quyết định:
        ├── Khi nào scan
        ├── Estimate bao nhiêu deals
        ├── Chọn deal nào để notify
        └── Viết file markdown
```

---

## 📁 Cấu trúc thư mục và Files

### Sơ đồ thư mục

```
segment4/
│
├── price_is_right.py                    # 🎯 ENTRY POINT - Gradio UI
├── deal_agent_framework.py              # 📦 FRAMEWORK - Điều phối trung tâm
├── pricer_service2.py                   # ☁️ MODAL SERVICE - Fine-tuned Llama
│
├── memory.json                          # 💾 PERSISTENT MEMORY - Deals đã xử lý
├── deep_neural_network.pth              # 🧠 MODEL WEIGHTS - PyTorch DNN
│
├── sandbox/                             # 📂 SANDBOX cho MCP Filesystem
│   └── deals.md                         # File markdown (Autonomous mode)
│
├── products_vectorstore/                # 📊 CHROMADB - 400K products
│   └── chroma.sqlite3
│
├── price_agents/                        # 🤖 THƯ MỤC CHỨA TẤT CẢ AGENTS
│   ├── __init__.py
│   ├── agent.py                         # Base class cho tất cả agents
│   ├── deals.py                         # Data classes (Deal, Opportunity)
│   ├── preprocessor.py                  # Làm sạch text trước khi estimate
│   │
│   ├── planning_agent.py                # Orchestrator (Simple mode)
│   ├── autonomous_planning_agent.py     # Orchestrator (Autonomous mode)
│   │
│   ├── scanner_agent.py                 # Scan RSS feeds + GPT select
│   ├── ensemble_agent.py                # Kết hợp 3 models dự đoán giá
│   ├── messaging_agent.py               # Gửi push notification
│   │
│   ├── frontier_agent.py                # GPT-5.1 + RAG
│   ├── specialist_agent.py              # Fine-tuned Llama (Modal)
│   ├── neural_network_agent.py          # Wrapper cho PyTorch DNN
│   └── deep_neural_network.py           # PyTorch model architecture
│
└── log_utils.py                         # 🔧 Utility - Log formatting
```

---

## 📄 Chi tiết từng File

### 1. Tầng UI (User Interface)

#### `price_is_right.py` - Entry Point (~168 dòng)

**Mục đích:** Chứa Gradio UI với dashboard real-time.

**Class chính:**
```python
class App:
    """Gradio App for The Price is Right."""
    
    def __init__(self):
        self.agent_framework = None
    
    def get_agent_framework(self):
        """Lazy init DealAgentFramework."""
        if not self.agent_framework:
            self.agent_framework = DealAgentFramework()
        return self.agent_framework
    
    def run(self):
        """Build và launch Gradio UI với:
        - Dataframe: Danh sách deals
        - Logs: Real-time logs với màu sắc
        - Plot: 3D t-SNE visualization của ChromaDB
        - Timer: Auto-refresh mỗi 5 phút
        """
```

**UI Components:**
| Component | Mô tả |
|-----------|-------|
| `opportunities_dataframe` | Bảng deals: Description, Price, Estimate, Discount, URL |
| `logs` | HTML panel hiển thị real-time logs |
| `plot` | Plotly 3D scatter plot (t-SNE của 800 products) |
| `timer` | gr.Timer interval=300s (5 phút) |

**Event Handlers:**
- `ui.load()` → Chạy pipeline lần đầu khi load
- `timer.tick()` → Chạy pipeline mỗi 5 phút
- `opportunities_dataframe.select()` → Gửi notification khi click row

---

### 2. Tầng Framework (Orchestrator)

#### `deal_agent_framework.py` - Điều phối trung tâm (~110 dòng)

**Mục đích:** Quản lý resources, memory, agents.

**Class chính:**
```python
class DealAgentFramework:
    """Framework orchestrator."""
    
    DB = "products_vectorstore"       # ChromaDB path
    MEMORY_FILENAME = "memory.json"   # Persistent memory
    
    def __init__(self):
        # 1. Init logging
        # 2. Load .env
        # 3. Connect ChromaDB
        # 4. Load memory từ JSON
        # 5. planner = None (lazy init)
    
    def init_agents_as_needed(self):
        """Lazy init AutonomousPlanningAgent."""
        if not self.planner:
            self.planner = AutonomousPlanningAgent(self.collection)
    
    def read_memory() → List[Opportunity]
        """Load deals từ memory.json."""
    
    def write_memory()
        """Save deals vào memory.json."""
    
    def run() → List[Opportunity]
        """Chạy pipeline và update memory."""
    
    @classmethod
    def get_plot_data(max_datapoints)
        """Lấy data cho 3D visualization:
        - Fetch embeddings từ ChromaDB
        - Apply t-SNE để giảm xuống 3D
        - Color theo category
        """
```

**Memory Format (memory.json):**
```python
[
    {
        "deal": {
            "product_description": "...",
            "price": 350.0,
            "url": "https://..."
        },
        "estimate": 773.81,
        "discount": 423.81
    },
    ...
]
```

---

### 3. Tầng Planning Agents

#### `price_agents/planning_agent.py` - Simple Orchestrator (~57 dòng)

**Mục đích:** Điều phối workflow theo cách truyền thống (sequential).

```python
class PlanningAgent(Agent):
    """Simple Planning Agent - sequential workflow."""
    
    DEAL_THRESHOLD = 50  # Notify nếu discount > $50
    
    def __init__(self, collection):
        self.scanner = ScannerAgent()
        self.ensemble = EnsembleAgent(collection)
        self.messenger = MessagingAgent()
    
    def run(deal: Deal) → Opportunity:
        """Process 1 deal: estimate + calculate discount."""
        estimate = self.ensemble.price(deal.product_description)
        discount = estimate - deal.price
        return Opportunity(deal, estimate, discount)
    
    def plan(memory) → Optional[Opportunity]:
        """Full workflow:
        1. scanner.scan() → 5 deals
        2. For each: run() → estimate
        3. Sort by discount
        4. If best > threshold: notify
        5. Return best or None
        """
```

#### `price_agents/autonomous_planning_agent.py` - Advanced Orchestrator (~143 dòng)

**Mục đích:** Dùng GPT-5.1 làm controller, tự quyết định workflow.

```python
# Tools cho GPT sử dụng
@function_tool
def scan_the_internet_for_bargains() → str:
    """Tool 1: Scan RSS feeds → DealSelection JSON."""

@function_tool
def estimate_true_value(description: str) → str:
    """Tool 2: Estimate giá → JSON {description, estimate}."""

@function_tool
def notify_user_of_deal(description, price, estimate, url) → str:
    """Tool 3: Gửi notification + tạo Opportunity."""


class AutonomousPlanningAgent(BaseAgent):
    """Autonomous Agent với GPT-5.1 làm brain."""
    
    MODEL = "gpt-5.1"
    
    task = """
    You are an Autonomous AI Agent...
    1. First scan the internet for bargains
    2. For each deal, estimate its true value
    3. Pick the most compelling deal and notify user
    4. Write to sandbox/deals.md
    """
    
    def plan(memory) → Optional[Opportunity]:
        """GPT-5.1 tự điều phối:
        - Gọi tools theo thứ tự tự quyết
        - Sử dụng MCP Filesystem để write file
        - Return Opportunity hoặc None
        """
```

**MCP Server Integration:**
```python
# Filesystem MCP server
files_params = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", sandbox_path]
}

async with MCPServerStdio(params=files_params) as server:
    agent = Agent(
        model="gpt-5.1",
        tools=[scan, estimate, notify],
        mcp_servers=[server]  # Để write sandbox/deals.md
    )
```

---

### 4. Tầng Scanning

#### `price_agents/scanner_agent.py` - RSS Scanner (~125 dòng)

**Mục đích:** Fetch deals từ RSS feeds và chọn top 5 bằng GPT.

```python
class ScannerAgent(Agent):
    """Scan RSS feeds và select deals."""
    
    MODEL = "gpt-5-mini"
    
    SYSTEM_PROMPT = """
    You identify and summarize the 5 most detailed deals...
    
    CRITICAL PRICING RULES:
    1. "Off" is NOT the actual price
    2. EXCLUDE "Up to X% off" general sales
    3. EXCLUDE trade-in deals
    """
    
    def fetch_deals(memory) → List[ScrapedDeal]:
        """Fetch từ 5 RSS feeds, loại bỏ đã có trong memory."""
        urls = [opp.deal.url for opp in memory]
        scraped = ScrapedDeal.fetch()  # ~25 deals
        return [s for s in scraped if s.url not in urls]
    
    def scan(memory) → Optional[DealSelection]:
        """GPT-5-mini chọn top 5:
        1. fetch_deals()
        2. Tạo prompt với deal descriptions
        3. Call OpenAI Structured Outputs
        4. Return DealSelection
        """
```

**RSS Feed Sources (deals.py):**
```python
feeds = [
    "https://www.dealnews.com/c142/Electronics/?rss=1",
    "https://www.dealnews.com/c39/Computers/?rss=1",
    "https://www.dealnews.com/f1912/Smart-Home/?rss=1",
    "https://www.dealnews.com/c238/Automotive/?rss=1",
    "https://www.dealnews.com/c196/Home-Garden/?rss=1",
]
```

---

### 5. Tầng AI Estimation (Ensemble)

#### `price_agents/ensemble_agent.py` - Combiner (~41 dòng)

**Mục đích:** Kết hợp 3 models để dự đoán giá.

```python
class EnsembleAgent(Agent):
    """Ensemble 3 models với weighted average."""
    
    def __init__(self, collection):
        self.preprocessor = Preprocessor()    # Chuẩn hóa text
        self.frontier = FrontierAgent(collection)  # 80%
        self.specialist = SpecialistAgent()   # 10%
        self.neural_network = NeuralNetworkAgent()  # 10%
    
    def price(description: str) → float:
        # 1. Preprocess text
        rewrite = self.preprocessor.preprocess(description)
        
        # 2. Get predictions từ 3 models
        frontier = self.frontier.price(rewrite)
        specialist = self.specialist.price(rewrite)
        neural = self.neural_network.price(rewrite)
        
        # 3. Weighted average
        combined = frontier * 0.8 + specialist * 0.1 + neural * 0.1
        return combined
```

#### `price_agents/frontier_agent.py` - GPT + RAG (~97 dòng)

**Mục đích:** Dùng GPT-5.1 với RAG từ ChromaDB.

```python
class FrontierAgent(Agent):
    """GPT-5.1 + RAG với 5 similar products."""
    
    MODEL = "gpt-5.1"
    
    def __init__(self, collection):
        self.client = OpenAI()
        self.collection = collection  # ChromaDB
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
    
    def find_similars(description) → (documents, prices):
        """RAG: Tìm 5 sản phẩm tương tự trong ChromaDB."""
        vector = self.model.encode([description])
        results = self.collection.query(vector, n_results=5)
        return results['documents'], results['metadatas']['price']
    
    def price(description) → float:
        """1. Tìm 5 similar products
           2. Tạo prompt với context
           3. Call GPT-5.1
           4. Extract price từ response
        """
```

#### `price_agents/specialist_agent.py` - Fine-tuned Llama (~30 dòng)

**Mục đích:** Gọi remote Llama-3.2-3B fine-tuned trên Modal.

```python
class SpecialistAgent(Agent):
    """Fine-tuned Llama running on Modal."""
    
    def __init__(self):
        # Connect to Modal service
        Pricer = modal.Cls.from_name("pricer-service", "Pricer")
        self.pricer = Pricer()
    
    def price(description: str) → float:
        """Remote call to Modal."""
        return self.pricer.price.remote(description)
```

#### `pricer_service2.py` - Modal Service (~80 dòng)

**Mục đích:** Define Modal serverless function cho fine-tuned Llama.

```python
@app.cls(gpu="T4", image=image, secrets=secrets)
class Pricer:
    @modal.enter()
    def setup(self):
        """Load model khi container start:
        - Base: meta-llama/Llama-3.2-3B
        - LoRA: SeanSunny/price-2026-final
        - Quant: 4-bit NF4
        """
    
    @modal.method()
    def price(description: str) → float:
        """Generate price prediction:
        Prompt: "What does this cost? {description} Price is $"
        """
```

#### `price_agents/neural_network_agent.py` - PyTorch DNN (~30 dòng)

**Mục đích:** Wrapper cho local PyTorch neural network.

```python
class NeuralNetworkAgent(Agent):
    """Local PyTorch DNN for price prediction."""
    
    def __init__(self):
        self.neural_network = DeepNeuralNetworkInference()
        self.neural_network.setup()
        self.neural_network.load("deep_neural_network.pth")
    
    def price(description: str) → float:
        return self.neural_network.inference(description)
```

#### `price_agents/deep_neural_network.py` - Model Architecture (~102 dòng)

**Mục đích:** Define PyTorch model architecture.

```python
class DeepNeuralNetwork(nn.Module):
    """10-layer DNN với Residual Blocks."""
    
    def __init__(self, input_size=5000, num_layers=10, hidden_size=4096):
        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        self.residual_blocks = nn.ModuleList([
            ResidualBlock(hidden_size) for _ in range(num_layers - 2)
        ])
        self.output_layer = nn.Linear(hidden_size, 1)


class DeepNeuralNetworkInference:
    """Inference wrapper."""
    
    def setup(self):
        self.vectorizer = HashingVectorizer(n_features=5000)
        self.model = DeepNeuralNetwork(5000)
        # Auto-detect: cuda > mps > cpu
    
    def inference(text) → float:
        vector = self.vectorizer.transform([text])
        pred = self.model(vector)
        # De-normalize: exp(pred * std + mean) - 1
        return result
```

---

### 6. Tầng Messaging

#### `price_agents/messaging_agent.py` - Notifications (~73 dòng)

**Mục đích:** Gửi push notification qua Pushover.

```python
class MessagingAgent(Agent):
    """Push notification via Pushover API."""
    
    MODEL = "gpt-5-nano"  # Cho craft_message
    
    def __init__(self):
        self.pushover_user = os.getenv("PUSHOVER_USER")
        self.pushover_token = os.getenv("PUSHOVER_TOKEN")
    
    def push(text: str):
        """Gửi notification với sound=cashregister."""
        requests.post("https://api.pushover.net/1/messages.json", {
            "user": self.pushover_user,
            "token": self.pushover_token,
            "message": text,
            "sound": "cashregister"
        })
    
    def alert(opportunity: Opportunity):
        """Format và gửi alert đơn giản."""
    
    def craft_message(description, price, estimate) → str:
        """Dùng GPT-5-nano viết message vui nhộn với FOMO."""
    
    def notify(description, price, estimate, url):
        """Craft message rồi push."""
```

---

### 7. Tầng Base và Data Models

#### `price_agents/agent.py` - Base Class (~33 dòng)

```python
class Agent:
    """Abstract base class với colored logging."""
    
    RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = ...
    
    name: str = ""
    color: str = WHITE
    
    def log(message):
        """Log với màu identify agent."""
```

#### `price_agents/deals.py` - Data Classes (~152 dòng)

```python
class ScrapedDeal:
    """Raw deal từ RSS feed."""
    title, summary, url, details, features
    
    @classmethod
    def fetch() → List[ScrapedDeal]:
        """Fetch từ 5 RSS feeds (feedparser)."""


class Deal(BaseModel):
    """Pydantic model cho processed deal."""
    product_description: str
    price: float
    url: str


class DealSelection(BaseModel):
    """GPT output - top 5 deals."""
    deals: List[Deal]


class Opportunity(BaseModel):
    """Deal + estimate + discount."""
    deal: Deal
    estimate: float
    discount: float
```

#### `price_agents/preprocessor.py` - Text Cleaning (~49 dòng)

```python
class Preprocessor:
    """Chuẩn hóa text trước khi estimate."""
    
    MODEL = "ollama/llama3.2"  # Hoặc GPT
    
    SYSTEM_PROMPT = """
    Create a concise description:
    Title: ...
    Category: ...
    Brand: ...
    Description: 1 sentence
    Details: 1 sentence
    """
    
    def preprocess(text) → str:
        """LLM rewrite text thành format chuẩn."""
```

---

## 🔗 Sơ đồ liên kết giữa các Files

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PRICE IS RIGHT - FILE DEPENDENCIES                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      price_is_right.py (UI)                              │   │
│  │                              │                                           │   │
│  │                    imports ↓                                            │   │
│  │              deal_agent_framework.py                                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                │                                                │
│                        imports ↓                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                deal_agent_framework.py (Framework)                       │   │
│  │                              │                                           │   │
│  │                    imports ↓                                            │   │
│  │    ┌────────────────────────┴────────────────────────┐                  │   │
│  │    ▼                                                 ▼                  │   │
│  │  planning_agent.py                   autonomous_planning_agent.py       │   │
│  │  (Simple mode)                       (Autonomous mode - DEFAULT)        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                │                                                │
│                        imports ↓                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    PlanningAgent Sub-agents                              │   │
│  │                                                                          │   │
│  │    ┌──────────────┬──────────────┬──────────────────┐                   │   │
│  │    ▼              ▼              ▼                  │                   │   │
│  │  scanner_agent  ensemble_agent  messaging_agent    │                   │   │
│  │    │              │              │                  │                   │   │
│  │    │              │              └──► Pushover API  │                   │   │
│  │    │              │                                 │                   │   │
│  │    │              ├──► preprocessor.py              │                   │   │
│  │    │              │                                 │                   │   │
│  │    │              ├──► frontier_agent.py ───► ChromaDB + GPT-5.1       │   │
│  │    │              │                                 │                   │   │
│  │    │              ├──► specialist_agent.py ──► Modal (Llama)           │   │
│  │    │              │                                 │                   │   │
│  │    │              └──► neural_network_agent.py ──► deep_neural_network │   │
│  │    │                                                │                   │   │
│  │    └──► deals.py (ScrapedDeal, DealSelection)      │                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         EXTERNAL SERVICES                                │   │
│  │                                                                          │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │   │
│  │  │   DealNews     │  │   Modal        │  │   Pushover     │            │   │
│  │  │   RSS Feeds    │  │   (Llama GPU)  │  │   (Push API)   │            │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘            │   │
│  │                                                                          │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │   │
│  │  │   OpenAI       │  │   ChromaDB     │  │   Ollama       │            │   │
│  │  │   GPT-5.1/mini │  │   (400K docs)  │  │   (Llama local)│            │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Cách Setup và Chạy

### 1. Yêu cầu hệ thống

- Python 3.10+
- Node.js 18+ (cho MCP servers)
- GPU recommended (cho Neural Network)
- Modal account (cho SpecialistAgent)

### 2. Cài đặt dependencies

```bash
cd segment4

# Cài đặt Python packages
uv sync

# Deploy Modal service (lần đầu)
modal deploy pricer_service2.py
```

### 3. Cấu hình Environment Variables

Tạo file `.env` trong folder `segment4/`:

```env
# OpenAI API Key (bắt buộc)
OPENAI_API_KEY=sk-xxx...

# Pushover Notification (bắt buộc)
PUSHOVER_USER=xxx
PUSHOVER_TOKEN=xxx

# HuggingFace Token (cho Modal download model)
HF_TOKEN=hf_xxx...

# Preprocessor Model (tùy chọn)
PRICER_PREPROCESSOR_MODEL=ollama/llama3.2
```

### 4. Chạy ứng dụng

```bash
cd segment4
uv run price_is_right.py
```

Ứng dụng sẽ:
1. Mở browser tại `http://127.0.0.1:7860`
2. Load ChromaDB và hiển thị 3D plot
3. Tự động scan deals lần đầu
4. Repeat mỗi 5 phút

---

## 🕐 Thời gian thực thi (Latency per Cycle)

```
Total Cycle Time: ~60-90 giây

  ├── Fetch RSS feeds:                    5-10s
  ├── GPT-5-mini select top 5:            3-5s
  ├── Preprocess (5 deals × local LLM):   15-20s
  ├── FrontierAgent (5 deals):            10-15s
  │   ├── RAG search ChromaDB:            1-2s each
  │   └── GPT-5.1 estimate:               2-3s each
  ├── SpecialistAgent (5 deals, Modal):   10-20s
  │   └── Cold start: +30-60s lần đầu
  ├── NeuralNetworkAgent (5 deals, local): 1-2s
  └── Notification (if needed):            1-2s
```

---

## 💰 Chi phí ước tính (Cost)

| Component | Model | Cost per Cycle |
|-----------|-------|----------------|
| Scanner | GPT-5-mini | ~$0.002 |
| Frontier (5 calls) | GPT-5.1 | ~$0.01 |
| Specialist (5 calls) | Modal T4 | ~$0.01 |
| Messaging | GPT-5-nano | ~$0.001 |
| Preprocess | Ollama local | $0 |
| Neural Network | Local | $0 |
| **Total per cycle** | | **~$0.023** |
| **Daily (288 cycles)** | | **~$6.62** |
| **Monthly** | | **~$200** |

---

## 📊 So sánh 2 Modes

| Feature | PlanningAgent | AutonomousPlanningAgent |
|---------|---------------|-------------------------|
| **Control** | Hard-coded logic | GPT-5.1 decides |
| **Flexibility** | Low | High |
| **MCP Support** | No | Yes (Filesystem) |
| **File Writing** | No | Yes (deals.md) |
| **Cost** | Lower | Higher (+GPT-5.1) |
| **Debugging** | Easier | Harder |
| **Current Default** | ❌ | ✅ |

---

## 🎯 Tóm tắt

| Mục | Chi tiết |
|-----|----------|
| **Mục tiêu** | Tự động tìm deals từ RSS feeds |
| **Input** | RSS feeds từ DealNews.com |
| **Output** | Push notification + Dashboard + memory.json |
| **Công nghệ AI** | GPT-5.1, GPT-5-mini, Llama-3.2-3B, PyTorch DNN |
| **Ensemble** | 80% Frontier + 10% Specialist + 10% Neural |
| **Threshold** | Notify nếu discount > $50 |
| **Database** | ChromaDB (400K products) |
| **UI** | Gradio với 3D visualization |
| **Frequency** | Auto-run mỗi 5 phút |
| **Cost** | ~$0.02/cycle, ~$200/month |

---

## 📚 Files Training Data (Reference)

Các files này được sử dụng để train models (không nằm trong runtime):

| File | Purpose |
|------|---------|
| `train_price_predictor.ipynb` | Train PyTorch DNN |
| `train_llama_lora.ipynb` | Fine-tune Llama-3.2-3B với LoRA |
| `build_vectorstore.ipynb` | Build ChromaDB từ 400K products |
| `data/labeled_data.pkl` | Dataset cho training |

---

*Documentation generated on 2026-02-07*
