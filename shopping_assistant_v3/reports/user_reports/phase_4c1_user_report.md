# Phase 4C.1: Real Pricing Neural Adapter

## 1. Phase Này Là Gì?

Phase 4C.1 là bước đầu tiên của real price estimator. Nó chưa extract full
ensemble từ `segment4`, mà chỉ dựng boundary real pricing và đưa neural model
local vào như component thật đầu tiên.

Real pricing được bật bằng:

```text
ENABLE_REAL_MODEL_CALLS=true
```

Default vẫn là mock pricing từ Phase 4A.

## 2. Trước Phase Này Hệ Thống Đang Thiếu Gì?

Sau Phase 4B, search có thể lấy sản phẩm thật, nhưng pricing vẫn là fixture
hoặc rule 10%. V3 chưa có đường đi rõ ràng để gọi model định giá thật.

Prototype `segment4` có ensemble gồm:

```text
Preprocessor -> FrontierAgent -> SpecialistAgent -> NeuralNetworkAgent
```

Nhưng full flow này nặng:

- Frontier cần ChromaDB vectorstore, SentenceTransformer, OpenAI.
- Specialist là Modal remote service.
- Preprocessor là LiteLLM model call.
- Neural dùng PyTorch local và file weights lớn.

Phase 4C.1 chọn staged extraction: làm boundary trước, extract neural trước,
hoãn Frontier và Specialist.

## 3. Phase Này Đã Xây Được Gì?

Phase 4C.1 tạo:

- Deterministic formatter thay cho LiteLLM Preprocessor.
- Neural adapter lazy-load model và dependencies.
- Copy/adapt neural network math từ `segment4`.
- Real estimator orchestrator.
- Optional dependency group `neural`.
- Safe fallback khi thiếu weights hoặc thiếu dependencies.
- Tests mock-only và opt-in neural smoke tests.

Không copy file `deep_neural_network.pth` vào V3. File weights phải được cung
cấp bằng env path riêng.

## 4. Chức Năng Hoạt Động Như Thế Nào?

Luồng pricing:

```text
estimate_price(input)
  -> nếu ENABLE_REAL_MODEL_CALLS=false:
       dùng mock fixture hoặc fallback 10%
  -> nếu ENABLE_REAL_MODEL_CALLS=true:
       estimate_price_real(product)
         -> format_product_for_pricing(product)
         -> NeuralPriceAdapter.estimate(text)
         -> assemble PriceEstimateOutput
```

Nếu neural chạy được:

```text
estimated_value_usd = neural_value
model_breakdown.neural = neural_value
warnings gồm ensemble_partial:neural_only
```

Nếu neural không chạy được:

```text
estimated_value_usd = sale_price * 1.05
deal_score = ok
warnings gồm real_pricing_fallback_used:sale_price_markup
```

Frontend hoặc Synthesizer sau này sẽ thấy rõ đây là partial ensemble, không phải
full price ensemble.

## 5. Kỹ Thuật Được Sử Dụng

- Deterministic formatter, không model call.
- PyTorch DNN copy/adapt từ `segment4`.
- `HashingVectorizer` từ scikit-learn.
- Lazy import để mock path không kéo `torch`, `sklearn`, `numpy`.
- Optional dependencies:

```text
uv sync --extra neural
```

- Env config:

```text
PRICER_NEURAL_WEIGHTS_PATH=/path/to/deep_neural_network.pth
```

- Warning grammar dạng `key:value`.

## 6. Các File Quan Trọng Và Mối Quan Hệ

```text
backend/tools/price_estimator/tool.py
backend/tools/price_estimator/real_estimator.py
backend/tools/price_estimator/formatter.py
backend/tools/price_estimator/neural/adapter.py
backend/tools/price_estimator/neural/deep_neural_network.py
backend/shared/config.py
tests/test_real_pricing.py
tests/test_real_pricing_neural.py
```

Quan hệ:

- `tool.py` quyết định mock path hay real path theo `ENABLE_REAL_MODEL_CALLS`.
- `real_estimator.py` gọi formatter và neural adapter, rồi tạo
  `PriceEstimateOutput`.
- `formatter.py` biến `ProductCandidate` thành text structured.
- `neural/adapter.py` là lớp an toàn: lazy-load model, trả result hoặc
  error_code.
- `neural/deep_neural_network.py` chứa neural architecture và inference math.
- `config.py` thêm `PRICER_NEURAL_WEIGHTS_PATH`.
- `test_real_pricing.py` kiểm tra default behavior không cần neural deps.
- `test_real_pricing_neural.py` là opt-in smoke test, skipped mặc định.

## 7. Cách Tự Kiểm Tra

Default, không cần weights và không gọi model thật:

```bash
uv run pytest tests/test_real_pricing.py -v
uv run pytest tests/ -v
```

Khi Phase 4C.1 được approve, kết quả cuối:

```text
127 passed, 12 skipped
```

Opt-in neural smoke test chỉ chạy khi bạn chủ động chuẩn bị:

```bash
ENABLE_REAL_MODEL_CALLS=true \
PRICER_NEURAL_WEIGHTS_PATH=/path/to/deep_neural_network.pth \
uv run pytest tests/test_real_pricing_neural.py -v
```

Nếu chưa cài neural extras hoặc chưa có weights path, test sẽ skip.

## 8. Giới Hạn Hiện Tại

- Chưa có FrontierAgent real extraction.
- Chưa có SpecialistAgent Modal integration.
- Chưa có full ensemble formula `frontier*0.8 + specialist*0.1 + neural*0.1`.
- Neural weights không được bundle trong repo vì file rất lớn.
- Nếu neural thiếu weights/deps, hệ thống dùng fallback 5% và warning rõ ràng.

## 9. Phase Sau Sẽ Xây Tiếp Gì?

Phase 4C.2 sẽ bàn về Frontier pricing extraction. Đây là phần khó hơn vì cần
ChromaDB vectorstore, SentenceTransformer, và OpenAI calls. Phase này phải
brainstorm riêng trước khi implement.

## 10. Tóm Tắt Ngắn

Phase 4C.1 mở đường cho real pricing nhưng không làm quá rộng. Nó tạo boundary
đúng, giữ mock mode an toàn, thêm neural adapter lazy-load, và nói rõ những
component nào còn thiếu. Đây là bước trung gian cần thiết trước khi full
ensemble có thể hoạt động.
