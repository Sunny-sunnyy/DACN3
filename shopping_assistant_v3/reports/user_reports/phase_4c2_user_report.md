# Phase 4C.2: Frontier Pricing Adapter

## 1. Phase Này Là Gì?

Phase 4C.2 thêm Frontier price estimator vào real pricing path của V3.
Frontier là component mạnh nhất trong ensemble prototype `segment4`: nó dùng
ChromaDB để tìm sản phẩm tương tự, rồi gọi model OpenAI để ước lượng giá USD.

Phase này vẫn là opt-in. Default mock pricing không đổi và không gọi model thật.

## 2. Trước Phase Này Hệ Thống Đang Thiếu Gì?

Sau Phase 4C.1, real pricing mới có neural adapter và fallback 5%. Hệ thống
chưa có RAG pricing từ ChromaDB, nên chưa tận dụng được vectorstore 800K+
sản phẩm đã có ở prototype.

## 3. Phase Này Đã Xây Được Gì?

Phase 4C.2 tạo:

- `FrontierPriceAdapter`.
- Config `PRICER_CHROMADB_PATH`.
- Config `PRICER_FRONTIER_MODEL_ID`.
- Optional dependency group `frontier`.
- Opt-in Frontier smoke tests.
- Priority mới trong real pricing: Frontier > Neural > fallback 5%.

ChromaDB data không được copy vào V3. User tự trỏ path tới vectorstore khi muốn
chạy thật.

## 4. Chức Năng Hoạt Động Như Thế Nào?

Khi `ENABLE_REAL_MODEL_CALLS=false`, pricing vẫn dùng mock fixture hoặc fallback
10% như Phase 4A.

Khi `ENABLE_REAL_MODEL_CALLS=true`, real pricing chạy:

```text
format product evidence
  -> try Frontier adapter
  -> if Frontier succeeds, use Frontier value and skip Neural
  -> if Frontier fails, try Neural adapter
  -> if both fail, use 5% fallback markup
```

Nếu Frontier chạy được, result có warning:

```text
ensemble_partial:frontier_only
specialist_unavailable:deferred_to_4c3
```

Điều này nói rõ hệ thống chưa phải full ensemble vì Specialist vẫn chưa có.

## 5. Kỹ Thuật Được Sử Dụng

- ChromaDB `PersistentClient`.
- Collection name `products`.
- SentenceTransformer `sentence-transformers/all-MiniLM-L6-v2`.
- OpenAI Python SDK direct.
- Lazy import để mock path không kéo dependency nặng.
- `get_collection`, không dùng `get_or_create_collection`, để tránh tạo nhầm
  collection rỗng.

Optional install:

```bash
uv sync --extra frontier
```

Opt-in env:

```text
ENABLE_REAL_MODEL_CALLS=true
PRICER_CHROMADB_PATH=/path/to/products_vectorstore
PRICER_FRONTIER_MODEL_ID=gpt-5.1
OPENAI_API_KEY=<set locally>
```

Không paste API key vào chat hoặc report.

## 6. Các File Quan Trọng

```text
backend/tools/price_estimator/frontier/adapter.py
backend/tools/price_estimator/real_estimator.py
backend/shared/config.py
tests/test_real_pricing.py
tests/test_real_pricing_frontier.py
```

Quan hệ:

- `adapter.py` chứa Frontier boundary và lazy-load ChromaDB/OpenAI.
- `real_estimator.py` quyết định dùng Frontier, Neural, hay fallback.
- `config.py` chứa path/model config.
- `test_real_pricing.py` kiểm tra default mock-safe behavior.
- `test_real_pricing_frontier.py` là opt-in smoke test, skipped mặc định.

## 7. Cách Tự Kiểm Tra

Default verification không cần ChromaDB, OpenAI, secrets, hoặc network:

```bash
uv run pytest tests/ -v
```

Kết quả approved:

```text
148 passed, 16 skipped
```

Opt-in Frontier smoke test chỉ chạy khi đã chuẩn bị vectorstore, model id, API
key trong local env, và frontier extras:

```bash
ENABLE_REAL_MODEL_CALLS=true \
PRICER_CHROMADB_PATH=/path/to/products_vectorstore \
PRICER_FRONTIER_MODEL_ID=gpt-5.1 \
OPENAI_API_KEY=<set locally> \
uv run pytest tests/test_real_pricing_frontier.py -v
```

## 8. Giới Hạn Hiện Tại

- SpecialistAgent vẫn chưa được extract.
- Full ensemble formula `frontier*0.8 + specialist*0.1 + neural*0.1` chưa bật.
- Frontier real mode cần ChromaDB vectorstore local và OpenAI API key.
- OpenAI direct là intentional deviation; LiteLLM được để dành cho Router và
  Synthesizer ở Phase 5.

## 9. Phase Sau Sẽ Xây Tiếp Gì?

Milestone tiếp theo được phép là Phase 4C.3: Specialist price estimator
extraction. Phase đó cần brainstorming riêng vì Specialist trong prototype là
Modal remote wrapper.

## 10. Tóm Tắt Ngắn

Phase 4C.2 đưa Frontier pricing vào V3 theo cách sạch và opt-in. Default tests
vẫn an toàn, không gọi model thật. Khi bật real mode đúng config, Frontier dùng
ChromaDB và OpenAI để ước lượng giá, rồi hệ thống fallback có kiểm soát nếu
Frontier không available.
