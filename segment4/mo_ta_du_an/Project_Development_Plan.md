# Kế hoạch phát triển dự án: Trợ lý mua sắm thông minh tiếng Việt

**Phiên bản:** 1.0
**Ngày tạo:** 06/04/2026
**Thời gian dự kiến:** 8 tháng (04/2026 – 12/2026)
**Mục đích:** Đồ án tốt nghiệp

---

## 1. Tổng quan dự án

### 1.1. Mô tả

Xây dựng hệ thống trợ lý mua sắm thông minh tiếng Việt sử dụng kiến trúc multi-agent, có khả năng:

- Hỏi đáp tự nhiên bằng tiếng Việt về sản phẩm, giá cả, so sánh
- Tự động kích hoạt pipeline tìm kiếm sản phẩm khi người dùng yêu cầu
- Ước giá sản phẩm bằng ensemble ML (LLM fine-tuned + DNN)
- So sánh giá giữa nhiều sàn TMĐT Việt Nam
- Tư vấn sản phẩm phù hợp nhu cầu người dùng

### 1.2. Nguồn gốc

Dự án phát triển từ hệ thống "AI Price Intelligence System" (tiếng Anh, thị trường Mỹ) — một multi-agent system tìm deal trên BestBuy/Amazon, ước giá bằng ML ensemble, và gửi push notification. Phiên bản mới sẽ chuyển hoàn toàn sang tiếng Việt, thị trường Việt Nam, và nâng cấp từ pipeline search đơn thuần thành trợ lý hội thoại thông minh.

### 1.3. Kiến trúc tổng thể

Sử dụng kiến trúc hybrid B+C:

- **Tầng B (Router):** Qwen2.5-7B-Instruct phân loại intent người dùng thành 4 nhánh (hỏi đáp / tìm sản phẩm / so sánh giá / tư vấn), mỗi nhánh có agent chuyên biệt.
- **Tầng C (ReAct):** Nhánh tìm sản phẩm được nâng cấp thành ReAct agent — LLM tự lập kế hoạch nhiều bước (Thought → Action → Observe → lặp lại), tự quyết định gọi tool nào và bao nhiêu lần.
- **Ensemble ước giá:** Giữ nguyên kiến trúc 3 mô hình (Frontier 80% + Specialist 10% + DNN 10%), thay bằng các mô hình fine-tuned trên dữ liệu tiếng Việt.

### 1.4. Tech stack (toàn bộ open-source)

| Thành phần | Công nghệ |
|---|---|
| LLM chính (orchestrator + synthesizer) | Qwen2.5-7B-Instruct, serve bằng vLLM |
| LLM ước giá (frontier) | Qwen2.5-7B fine-tuned QLoRA cho bài toán định giá |
| LLM specialist | Qwen2.5-3B fine-tuned QLoRA, deploy trên Modal/Vast.ai |
| DNN | PyTorch ResidualBlock network (~289M params) |
| Vector DB | ChromaDB + multilingual-e5-base embeddings |
| Web scraping | curl_cffi (Chrome impersonation) + BeautifulSoup4 |
| UI | Gradio (giai đoạn đầu) → React/Next.js (nếu có thời gian) |
| Package manager | uv |
| GPU training | Vast.ai / Google Colab Pro (A100) |
| Serving inference | vLLM trên Vast.ai hoặc máy có GPU |

---

## 2. Các giai đoạn thực hiện

### Giai đoạn 1: Thu thập & xử lý dữ liệu tiếng Việt (tháng 1-3)

**Mục tiêu:** Xây dựng bộ dataset 1M+ sản phẩm tiếng Việt chất lượng cao, sẵn sàng cho training.

#### Bước 1.1: Khảo sát và lựa chọn nguồn dữ liệu (tuần 1-2)

- Tìm kiếm dataset có sẵn trên Kaggle, HuggingFace (ưu tiên nếu có)
- Nếu không có hoặc không đủ, xác định API/HTML structure của các sàn TMĐT:
  - Shopee: API internal (shopee.vn/api/v4/search/search_items)
  - Thế Giới Di Động: HTML parsing (thegioididong.com)
  - Tiki: API (tiki.vn/api/v2/products)
  - Lazada: API (lazada.vn)
  - CellphoneS: HTML parsing
  - FPT Shop: HTML parsing
- Thuê máy trên Vast.ai hoặc VPS đủ mạnh để cào dữ liệu (cần IP Việt Nam hoặc proxy VN)

#### Bước 1.2: Xây dựng pipeline cào dữ liệu (tuần 2-5)

- Viết scraper cho từng nguồn bằng curl_cffi + BeautifulSoup4
- Mỗi scraper cần xử lý: anti-bot bypass, pagination, rate limiting, retry logic
- Cấu trúc dữ liệu thu được cho mỗi sản phẩm:
  - title (tên sản phẩm)
  - category (danh mục)
  - price (giá bán)
  - description (mô tả chi tiết)
  - features (tính năng/thông số kỹ thuật)
  - brand (thương hiệu)
  - source (nguồn: Shopee/TGDĐ/Tiki/...)
  - url (đường dẫn sản phẩm)
- Mục tiêu: cào tối thiểu 1.5M sản phẩm thô từ tất cả nguồn

#### Bước 1.3: Làm sạch và xử lý dữ liệu (tuần 5-8)

Áp dụng quy trình tương tự tuần 6 khóa học (parser.py + items.py), adapt cho tiếng Việt:

- **Bộ lọc giá:** Khoảng giá 50.000đ – 50.000.000đ (tập trung hàng tiêu dùng phổ thông)
- **Bộ lọc văn bản:** Loại bỏ mô tả < 200 ký tự (quá ngắn, thiếu thông tin)
- **Làm sạch text:**
  - Xóa mã sản phẩm vô nghĩa (SKU, barcode)
  - Chuẩn hóa Unicode tiếng Việt (NFC normalization)
  - Xử lý text lẫn lộn Việt-Anh (rất phổ biến trên Shopee)
  - Xóa emoji, ký tự đặc biệt thừa
  - Cắt bớt nếu quá dài (max 4000 ký tự)
- **Deduplication:** Loại trùng lặp theo title + description (tránh data leakage)
- **EDA (Exploratory Data Analysis):**
  - Phân phối giá theo danh mục
  - Phân phối độ dài mô tả
  - Kiểm tra mất cân bằng danh mục

#### Bước 1.4: Weighted sampling và chia dataset (tuần 8-9)

- Áp dụng weighted sampling (bình phương giá) để cân bằng phân phối giá
- Penalize các danh mục chiếm đa số (tương tự Automotive trong dataset cũ)
- Chia tập dữ liệu:
  - Full version: 800K train / 10K validation / 10K test
  - Lite version: 20K train / 1K validation / 1K test
- Đẩy lên HuggingFace Hub

#### Bước 1.5: Xây dựng ChromaDB tiếng Việt (tuần 9-10)

- Sử dụng multilingual-e5-base (thay vì all-MiniLM-L6-v2) cho embedding tiếng Việt
- Embed toàn bộ 1M+ sản phẩm vào ChromaDB
- Test similarity search bằng tiếng Việt để đảm bảo chất lượng

#### Bước 1.6: Tiền xử lý dữ liệu bằng LLM (tuần 10-12)

- Sử dụng Qwen2.5-7B (hoặc GPT-nano nếu cần tiết kiệm) để rewrite mô tả sản phẩm thành format chuẩn:
  - Tiêu đề | Danh mục | Thương hiệu | Mô tả | Thông số kỹ thuật
- Dùng Batch API hoặc vLLM batch processing để xử lý hàng loạt
- Tạo prompt-completion pairs cho fine-tuning (format: "Sản phẩm này giá bao nhiêu?\n\n{mô tả}\n\nGiá: {giá}đ")

**Tiêu chí hoàn thành giai đoạn 1:**

- [ ] Dataset 800K+ sản phẩm đã làm sạch, chia tách train/val/test
- [ ] ChromaDB với 1M+ embeddings tiếng Việt, similarity search hoạt động chính xác
- [ ] Dataset đã được push lên HuggingFace Hub
- [ ] EDA report hoàn chỉnh (biểu đồ phân phối, thống kê)

---

### Giai đoạn 2: Huấn luyện mô hình tiếng Việt (tháng 3-5)

**Mục tiêu:** Fine-tune các mô hình ước giá trên dữ liệu tiếng Việt, đạt MAE cạnh tranh.

#### Bước 2.1: Baseline models (tuần 1-2)

Thiết lập mốc chuẩn trước khi fine-tune (tương tự Day 3 tuần 6):

- Random baseline: đoán giá ngẫu nhiên trong khoảng phân phối
- Constant baseline: luôn đoán giá trung bình
- Linear Regression: sklearn trên features đơn giản (độ dài text, category encoding)
- XGBoost: trên features nâng cao (TF-IDF + metadata)

#### Bước 2.2: DNN tiếng Việt (tuần 2-4)

- Giữ nguyên kiến trúc ResidualBlock từ deep_neural_network.py
- Thay đổi input features:
  - Text embeddings từ multilingual-e5-base (thay vì all-MiniLM)
  - Category encoding cho danh mục tiếng Việt
  - Numerical features (cân nặng nếu có, độ dài mô tả, ...)
- Training trên GPU cloud (Vast.ai):
  - 5 epochs, batch size tùy GPU
  - Dự kiến 4-6 giờ cho full dataset
  - Lưu model weights → deep_neural_network_vn.pth

#### Bước 2.3: Fine-tune Qwen2.5-7B cho ước giá — Frontier Agent (tuần 3-6)

Đây là mô hình quan trọng nhất (chiếm 80% trong ensemble):

- Base model: Qwen2.5-7B
- Kỹ thuật: QLoRA (4-bit quantization + LoRA adapters)
- Cấu hình khởi đầu:
  - rank = 32, alpha = 64
  - target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]
  - learning_rate = 2e-4
- Dữ liệu: Full dataset (800K prompts tiếng Việt)
- Platform: Vast.ai hoặc Colab Pro A100
- Đánh giá trên validation set sau mỗi epoch, chọn checkpoint tốt nhất
- Nếu kết quả chưa đủ tốt → tăng rank lên 128/256, thêm MLP layers

#### Bước 2.4: Fine-tune Qwen2.5-3B — Specialist Agent (tuần 5-7)

- Base model: Qwen2.5-3B (nhỏ hơn, chạy nhanh hơn)
- QLoRA tương tự bước 2.3 nhưng rank nhỏ hơn (16-32)
- Deploy lên Modal hoặc Vast.ai serverless
- Vai trò: specialist trong ensemble (10%)

#### Bước 2.5: Đánh giá và tối ưu ensemble (tuần 7-8)

- Chạy tất cả mô hình trên test set, đo MAE cho từng model
- So sánh với baseline và với kết quả dự án cũ (tiếng Anh)
- Tối ưu ensemble weights (thay vì cố định 80/10/10, thử grid search)
- Hyperparameter optimization nếu còn thời gian:
  - Learning rate, rank, alpha, batch size
  - Target modules (chỉ attention vs all-linear)
  - Số epochs

**Tiêu chí hoàn thành giai đoạn 2:**

- [ ] DNN đã train, sai số tốt hơn baseline ML truyền thống
- [ ] Qwen-pricer (7B) fine-tuned, MAE cạnh tranh trên dữ liệu tiếng Việt
- [ ] Qwen-specialist (3B) fine-tuned, deploy được trên cloud
- [ ] Ensemble hoạt động end-to-end, weights đã tối ưu
- [ ] Bảng so sánh kết quả tất cả mô hình (leaderboard)

---

### Giai đoạn 3: Xây dựng pipeline scraping sàn TMĐT Việt Nam (tháng 4-6)

**Mục tiêu:** Thay thế BestBuy/Amazon bằng các sàn TMĐT Việt Nam, scraping real-time hoạt động ổn định.

*Giai đoạn này chạy song song với giai đoạn 2.*

#### Bước 3.1: Shopee scraper (tuần 1-3)

- Reverse-engineer Shopee API (search, product detail, price)
- Xử lý anti-bot: cookie rotation, rate limiting, proxy nếu cần
- Output: ShopeeScrapedDeal (title, brand, price, features, url, source="Shopee")

#### Bước 3.2: Thế Giới Di Động / CellphoneS / FPT Shop scraper (tuần 2-4)

- HTML parsing bằng curl_cffi + BeautifulSoup4
- Các trang này ít chống bot hơn Shopee → đơn giản hơn
- Output: tương tự ShopeeScrapedDeal nhưng source khác

#### Bước 3.3: Tiki / Lazada scraper (tuần 3-5)

- Tiki có API tương đối mở, Lazada có thể cần reverse-engineer
- Output: tương tự các scraper trên

#### Bước 3.4: Unified deal format (tuần 5-6)

- Tạo UnifiedScrapedDeal chuẩn hóa từ tất cả nguồn (tương tự unified_deal.py hiện tại)
- Các trường: title, brand, price, features, url, source, category
- Method describe() cho LLM prompt

#### Bước 3.5: Tích hợp vào pipeline (tuần 6-7)

- Thay thế bestbuy_deals.py / amazon_deals.py bằng các scraper mới
- ThreadPoolExecutor chạy song song tất cả nguồn
- MultiSourceScannerAgent sử dụng Qwen thay GPT-5-nano để chọn top deals

**Tiêu chí hoàn thành giai đoạn 3:**

- [ ] Ít nhất 3 nguồn scraping hoạt động ổn định (Shopee + TGDĐ + 1 nguồn khác)
- [ ] UnifiedScrapedDeal chuẩn hóa đúng từ tất cả nguồn
- [ ] Pipeline search → filter → scrape chạy trong < 15s cho mỗi nguồn
- [ ] Xử lý được các edge case (CAPTCHA, timeout, sản phẩm hết hàng)

---

### Giai đoạn 4: Xây dựng chatbot trợ lý mua sắm (tháng 5-7)

**Mục tiêu:** Biến hệ thống thành trợ lý hội thoại thông minh với kiến trúc hybrid B+C.

#### Bước 4.1: Serve Qwen2.5-7B-Instruct (tuần 1)

- Cài đặt vLLM trên máy có GPU (hoặc Vast.ai)
- Serve model qua API endpoint (OpenAI-compatible format)
- Test tốc độ inference: mục tiêu < 2s cho response đầu tiên

#### Bước 4.2: Router agent — Mode B (tuần 1-3)

Xây dựng intent classifier bằng structured output:

- System prompt yêu cầu Qwen phân loại tin nhắn thành 4 intent:
  - HOI_DAP: câu hỏi kiến thức sản phẩm ("pin lithium khác gì pin polymer?")
  - TIM_SAN_PHAM: yêu cầu tìm sản phẩm ("tìm laptop dưới 15 triệu")
  - SO_SANH: so sánh giá/sản phẩm ("iPhone 16 ở Shopee hay TGDĐ rẻ hơn?")
  - TU_VAN: tư vấn mua sắm ("nên mua máy giặt hãng nào?")
- Output format: JSON {intent, keyword, max_price, category, entities}
- Slot filling: trích xuất keyword, ngân sách, danh mục từ câu hỏi
- Test accuracy trên 100+ câu hỏi mẫu tiếng Việt

#### Bước 4.3: Các agent chuyên biệt (tuần 2-4)

**QA Agent (hỏi đáp):**

- Nhận câu hỏi → query ChromaDB tìm sản phẩm liên quan → Qwen sinh câu trả lời kèm context
- Kỹ thuật: RAG cơ bản (retrieve top 5 → inject vào prompt → generate)

**Search Agent (tìm sản phẩm):**

- Kết nối pipeline scraping (giai đoạn 3) + ensemble ước giá (giai đoạn 2)
- Giữ nguyên luồng 4 bước: search → select → estimate → result

**Compare Agent (so sánh giá):**

- Nhận tên sản phẩm cụ thể → scrape giá từ nhiều nguồn song song
- Trả về bảng so sánh: nguồn | giá | link | ghi chú (khuyến mãi, freeship...)

**Advisor Agent (tư vấn):**

- Nhận nhu cầu người dùng → query ChromaDB tìm specs phù hợp
- Kết hợp kiến thức tổng quát của Qwen + dữ liệu cụ thể từ RAG
- Sinh gợi ý có giải thích ("Với nhu cầu lập trình, bạn cần RAM ≥ 8GB vì...")

#### Bước 4.4: Conversation memory (tuần 3-4)

- SQLite lưu lịch sử hội thoại (user_id, role, content, timestamp)
- Giữ 10 tin nhắn gần nhất trong context window
- Xử lý coreference: "cái laptop hồi nãy" → resolve về sản phẩm đã nhắc
- Sliding window khi context quá dài (summarize lịch sử cũ)

#### Bước 4.5: Response synthesizer (tuần 4-5)

- Qwen-7B nhận kết quả từ agent + lịch sử chat → sinh câu trả lời tiếng Việt tự nhiên
- Prompt engineering để đảm bảo:
  - Trả lời đúng trọng tâm câu hỏi
  - Có dẫn nguồn (giá từ đâu, sản phẩm ở sàn nào)
  - Giọng văn thân thiện, dễ hiểu
  - Kết quả có bảng so sánh khi cần

#### Bước 4.6: ReAct upgrade cho Search Agent — Mode C (tuần 5-7)

Nâng cấp nhánh tìm sản phẩm từ pipeline cứng thành ReAct loop:

- System prompt dạng ReAct:
  ```
  Bạn là trợ lý mua sắm. Khi nhận yêu cầu, hãy suy nghĩ từng bước:
  Thought: [phân tích yêu cầu, xác định cần thông tin gì]
  Action: [chọn tool phù hợp từ danh sách]
  Observation: [kết quả từ tool]
  ... (lặp lại nếu cần thêm thông tin)
  Final Answer: [câu trả lời tổng hợp]
  ```
- Danh sách tools available:
  - search_products(keyword, max_price, sources)
  - estimate_price(product_description)
  - query_rag(query)
  - compare_prices(product_name, sources)
- Safety: max_iterations = 5 (tránh lặp vô hạn), timeout = 60s
- Fallback: nếu ReAct loop thất bại → chuyển về pipeline cứng mode B

#### Bước 4.7: Chat UI (tuần 6-7)

- Gradio Chatbot interface:
  - Chat window chính (streaming response)
  - Sidebar hiển thị kết quả sản phẩm dạng card
  - Real-time logs (tùy chọn hiển thị)
- Hoặc nếu có thời gian: React/Next.js frontend đẹp hơn

**Tiêu chí hoàn thành giai đoạn 4:**

- [ ] Router phân loại đúng intent ≥ 90% trên test set 100 câu
- [ ] Hội thoại tự nhiên, giữ được ngữ cảnh qua nhiều lượt chat
- [ ] ReAct agent tự lập kế hoạch đúng cho câu hỏi phức tạp
- [ ] Response bằng tiếng Việt mượt mà, có dẫn nguồn
- [ ] End-to-end: từ câu hỏi → kết quả sản phẩm + ước giá < 90s

---

### Giai đoạn 5: Hoàn thiện, testing & viết báo cáo (tháng 7-8)

**Mục tiêu:** Hệ thống ổn định, có benchmark đầy đủ, báo cáo đồ án hoàn chỉnh.

#### Bước 5.1: Testing toàn diện (tuần 1-2)

- Unit test cho từng agent
- Integration test cho pipeline end-to-end
- Stress test: 50 câu hỏi liên tiếp, kiểm tra memory leak, crash
- Edge case test:
  - Câu hỏi ngoài phạm vi ("thời tiết hôm nay thế nào?")
  - Keyword không tìm được sản phẩm
  - Sàn TMĐT bị block/CAPTCHA
  - Câu hỏi tiếng Anh lẫn tiếng Việt
  - Giá ngoài khoảng dataset training
- Tạo test set 200 câu hỏi đa dạng, ghi nhận kết quả

#### Bước 5.2: Benchmark và đánh giá (tuần 2-3)

**Đánh giá ước giá (định lượng):**

| Metric | Mô tả |
|---|---|
| MAE (Mean Absolute Error) | Sai số giá tuyệt đối trung bình (VND) |
| MAPE (Mean Absolute Percentage Error) | Phần trăm sai số trung bình |
| Median Error | Sai số trung vị (ít bị ảnh hưởng bởi outlier) |
| R² Score | Hệ số xác định, đo mức độ giải thích biến thiên giá |

Bảng leaderboard so sánh:

| Model | MAE (VND) | MAPE (%) |
|---|---|---|
| Random baseline | ? | ? |
| Linear Regression | ? | ? |
| XGBoost | ? | ? |
| DNN tiếng Việt | ? | ? |
| Qwen-specialist (3B) | ? | ? |
| Qwen-pricer (7B) | ? | ? |
| Ensemble | ? | ? |

**Đánh giá chatbot (định tính + định lượng):**

| Metric | Cách đo |
|---|---|
| Intent accuracy | Tỷ lệ phân loại đúng trên 200 câu test |
| Task completion rate | Tỷ lệ hoàn thành yêu cầu end-to-end |
| Response latency | Thời gian từ câu hỏi đến câu trả lời |
| Response quality | Đánh giá thủ công 1-5 điểm (đúng, đủ, tự nhiên) |
| ReAct efficiency | Số bước trung bình để hoàn thành yêu cầu |
| Conversation coherence | Giữ ngữ cảnh đúng qua 5+ lượt chat |

#### Bước 5.3: Deploy demo (tuần 3-4)

- Deploy hệ thống trên Vast.ai hoặc server có GPU
- Tạo demo video 5-10 phút showcase các tính năng
- Chuẩn bị kịch bản demo cho buổi bảo vệ:
  - Hỏi đáp thông thường → RAG agent
  - Tìm sản phẩm cụ thể → search pipeline + ước giá
  - Câu hỏi phức tạp → ReAct multi-step reasoning
  - So sánh giá giữa các sàn

#### Bước 5.4: Viết báo cáo đồ án (tuần 3-6)

Cấu trúc báo cáo đề xuất:

1. **Giới thiệu:** Bối cảnh, vấn đề, mục tiêu
2. **Cơ sở lý thuyết:**
   - Large Language Models và Fine-tuning
   - QLoRA (Quantized Low-Rank Adaptation)
   - Kiến trúc Multi-Agent
   - ReAct (Reasoning + Acting)
   - Retrieval-Augmented Generation (RAG)
   - Ensemble Learning
3. **Phân tích và thiết kế:**
   - Kiến trúc tổng thể (sơ đồ hybrid B+C)
   - Thiết kế dữ liệu
   - Thiết kế từng agent
4. **Triển khai:**
   - Thu thập và xử lý dữ liệu (pipeline, sampling, cleaning)
   - Huấn luyện mô hình (DNN, QLoRA fine-tuning, hyperparameter tuning)
   - Xây dựng pipeline scraping
   - Xây dựng hệ thống chatbot
5. **Kết quả và đánh giá:**
   - Leaderboard ước giá
   - Đánh giá chatbot
   - So sánh với hệ thống gốc (tiếng Anh)
6. **Kết luận:** Đóng góp, hạn chế, hướng phát triển

#### Bước 5.5: Chuẩn bị bảo vệ (tuần 5-6)

- Slide trình bày (15-20 slide)
- Demo live
- Chuẩn bị câu hỏi phản biện phổ biến:
  - Tại sao chọn Qwen thay vì Llama/Vistral?
  - Tại sao cần multi-agent thay vì một LLM đơn?
  - Khi sàn TMĐT thay đổi cấu trúc HTML thì sao?
  - Chi phí vận hành hệ thống là bao nhiêu?
  - So sánh với các giải pháp chatbot mua sắm hiện có?

**Tiêu chí hoàn thành giai đoạn 5:**

- [ ] Test set 200 câu hỏi, kết quả được ghi nhận đầy đủ
- [ ] Leaderboard ước giá hoàn chỉnh với tất cả mô hình
- [ ] Demo hoạt động ổn định, có video backup
- [ ] Báo cáo đồ án hoàn chỉnh ≥ 60 trang
- [ ] Slide và kịch bản bảo vệ sẵn sàng

---

## 3. Tiêu chí thành công tổng thể

### 3.1. Tiêu chí kỹ thuật bắt buộc (Must-have)

| # | Tiêu chí | Mục tiêu |
|---|---|---|
| 1 | Dataset tiếng Việt | ≥ 800K sản phẩm đã làm sạch |
| 2 | ChromaDB tiếng Việt | ≥ 1M sản phẩm embedded, search chính xác |
| 3 | Fine-tuned LLM | Qwen-pricer MAE thấp hơn baseline ML |
| 4 | DNN tiếng Việt | Train thành công, tham gia ensemble |
| 5 | Ensemble ước giá | Hoạt động end-to-end, kết quả tốt hơn từng model đơn lẻ |
| 6 | Scraping ≥ 3 sàn VN | Shopee + TGDĐ + 1 sàn khác, ổn định |
| 7 | Router phân loại intent | ≥ 90% accuracy |
| 8 | Hội thoại tiếng Việt | Giữ ngữ cảnh ≥ 5 lượt chat |
| 9 | Pipeline end-to-end | Từ câu hỏi → kết quả < 120s |
| 10 | Toàn bộ open-source | Không phụ thuộc API trả phí nào |

### 3.2. Tiêu chí nâng cao (Nice-to-have)

| # | Tiêu chí | Ghi chú |
|---|---|---|
| 1 | ReAct multi-step reasoning | Agent tự lập kế hoạch cho câu hỏi phức tạp |
| 2 | So sánh giá real-time | Compare agent hoạt động ≥ 3 sàn |
| 3 | Advisor agent | Tư vấn dựa trên nhu cầu |
| 4 | React/Next.js frontend | Giao diện đẹp thay vì Gradio |
| 5 | Push notification | Thông báo khi có deal tốt (giữ từ dự án cũ) |
| 6 | Ensemble MAE < baseline model riêng lẻ | Chứng minh ensemble thực sự hiệu quả |
| 7 | Hyperparameter optimization | Grid search / Optuna cho fine-tuning |

### 3.3. Tiêu chí đồ án tốt nghiệp

| # | Tiêu chí | Mục tiêu |
|---|---|---|
| 1 | Tính mới | Kết hợp multi-agent + ensemble ML + RAG + ReAct cho bài toán mua sắm VN |
| 2 | Tính thực tiễn | Giải quyết nhu cầu thực: so sánh giá, ước giá, tư vấn mua sắm |
| 3 | Độ sâu kỹ thuật | Fine-tune LLM, train DNN, xây kiến trúc agent |
| 4 | Khả năng mở rộng | Dễ thêm nguồn dữ liệu, thêm agent, thêm tính năng |
| 5 | Trình bày rõ ràng | Báo cáo, sơ đồ, demo đầy đủ |

---

## 4. Rủi ro và phương án dự phòng

| Rủi ro | Xác suất | Tác động | Phương án dự phòng |
|---|---|---|---|
| Sàn TMĐT block scraping | Cao | Mất nguồn dữ liệu real-time | Chuẩn bị nhiều nguồn (≥ 5), proxy rotation, fallback sang nguồn khác |
| Fine-tune Qwen không hiệu quả cho tiếng Việt | Trung bình | Ước giá kém | Thử Vistral hoặc SeaLLM (model cho Đông Nam Á), hoặc tăng dataset |
| Hết budget GPU | Thấp | Không train được model lớn | Dùng Lite version (20K), giảm rank LoRA, dùng Colab free |
| Qwen-7B quá chậm cho realtime chat | Trung bình | UX kém | Giảm xuống Qwen-3B cho router, chỉ dùng 7B cho synthesizer |
| ChromaDB không tìm đúng sản phẩm tiếng Việt | Thấp | RAG quality kém | Thử BAAI/bge-m3 thay vì e5-base, hoặc fine-tune embedding model |
| Không đủ thời gian 8 tháng | Trung bình | Thiếu tính năng | Ưu tiên must-have trước, nice-to-have làm sau |

---

## 5. Lịch trình tổng quan (Gantt Chart dạng text)

```
Tháng:    1     2     3     4     5     6     7     8
          |-----|-----|-----|-----|-----|-----|-----|
GĐ1 Data: ████████████████████
GĐ2 Train:            ████████████████
GĐ3 Scrape:           ██████████████████
GĐ4 Chat:                    ██████████████████
GĐ5 Final:                                ████████
```

Lưu ý: Giai đoạn 2 và 3 chạy song song. Giai đoạn 4 bắt đầu khi có kết quả sơ bộ từ GĐ2+3.

---

## 6. Tài nguyên cần thiết

| Tài nguyên | Chi phí ước tính | Ghi chú |
|---|---|---|
| Vast.ai GPU (training) | ~$50-100/tháng | RTX 3090/4090 cho QLoRA |
| Vast.ai GPU (inference) | ~$30-50/tháng | Serve vLLM cho demo |
| VPS cào dữ liệu | ~$10-20/tháng | VPS Việt Nam cho proxy |
| Colab Pro (backup) | ~$10/tháng | A100 khi cần |
| HuggingFace Hub | Miễn phí | Lưu dataset + model |
| **Tổng cộng** | **~$100-180/tháng** | **~$800-1400 cho 8 tháng** |

---

*Tài liệu này sẽ được cập nhật khi có thay đổi trong quá trình thực hiện.*
