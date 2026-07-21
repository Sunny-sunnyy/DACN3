# Phase 4C.3 User Report - Specialist Price Estimator

## 1. Mục Tiêu

Phase 4C.3 đưa Specialist price estimator từ prototype `segment4` vào V3 dưới
dạng opt-in boundary. Specialist trong prototype là Modal remote wrapper gọi
fine-tuned Llama pricer service.

Mục tiêu của phase này không phải deploy hoặc train Modal service. Mục tiêu là
tạo adapter an toàn để V3 có thể gọi Specialist nếu local env đã cấu hình sẵn,
nhưng default mode vẫn chạy mock-only.

## 2. Vấn Đề Phase Này Giải Quyết

Trước 4C.3, real pricing có Frontier và Neural boundary nhưng chưa có
Specialist. Vì vậy full ensemble formula gốc chưa thể chạy đủ ba tín hiệu.

Sau 4C.3, V3 có đủ ba adapter:

- Frontier: ChromaDB RAG + OpenAI.
- Specialist: Modal fine-tuned model.
- Neural: local PyTorch DNN.

## 3. Chức Năng Đã Có

- Thêm `SpecialistPriceAdapter`.
- Adapter lazy-import `modal`, nên default tests không cần Modal dependency.
- Nếu thiếu config hoặc thiếu dependency, adapter trả safe warning thay vì
  crash.
- Real estimator thử Frontier, Specialist, và Neural khi real model mode bật.
- Khi cả ba model available, estimator dùng formula:

```text
0.8 * frontier + 0.1 * specialist + 0.1 * neural
```

- Nếu thiếu một hoặc nhiều model, estimator dùng priority fallback:

```text
frontier > specialist > neural > 5% sale-price markup
```

## 4. Kỹ Thuật Dùng

Specialist adapter đọc config từ env:

```text
PRICER_SPECIALIST_SERVICE
PRICER_SPECIALIST_CLASS
```

Dependency `modal` là optional extra trong `pyproject.toml`. Không có runtime
import từ `segment4`.

## 5. Luồng Hoạt Động

```text
price_estimator_tool
  -> real_estimator nếu ENABLE_REAL_MODEL_CALLS=true
  -> format product evidence
  -> try Frontier adapter
  -> try Specialist adapter
  -> try Neural adapter
  -> assemble estimate, breakdown, deal score, warnings
```

Default path khi `ENABLE_REAL_MODEL_CALLS=false` vẫn là fixture/mock pricing.

## 6. File Quan Trọng

```text
backend/tools/price_estimator/specialist/adapter.py
backend/tools/price_estimator/real_estimator.py
tests/test_real_pricing.py
tests/test_real_pricing_specialist.py
tests/test_real_pricing_specialist_smoke.py
```

## 7. Cách Tự Kiểm Tra

Default verification:

```bash
cd shopping_assistant_v3
uv run pytest tests/test_real_pricing.py tests/test_real_pricing_specialist.py -q --tb=short
uv run pytest tests/ -q --tb=short
```

Expected result đã được Codex review:

```text
72 passed for focused real-pricing tests
171 passed, 18 skipped for full default suite
```

Opt-in Specialist smoke tests chỉ chạy khi bạn tự bật real model mode và đã cấu
hình Modal local:

```bash
ENABLE_REAL_MODEL_CALLS=true \
PRICER_SPECIALIST_SERVICE=<set locally> \
PRICER_SPECIALIST_CLASS=<set locally> \
uv run pytest tests/test_real_pricing_specialist_smoke.py -q --tb=short
```

Không paste Modal token hoặc secrets vào chat, docs, logs, hoặc reports.

## 8. Giới Hạn Hiện Tại

- V3 không deploy hoặc train Modal service.
- Real Specialist cần Modal dependency, Modal auth/config local, và service
  đang tồn tại.
- Default tests không chứng minh service Modal thật hoạt động; chúng chỉ chứng
  minh boundary, fallback, lazy import, và safety behavior.
- Router tiếng Việt và Synthesizer tiếng Việt vẫn chưa implement; chúng thuộc
  Phase 5.

## 9. Phase Sau Sẽ Xây Tiếp Gì?

Milestone tiếp theo được phép là Phase 5: Router And Synthesizer.

Direction đã được chốt: dùng hybrid controlled OpenAI Agents SDK như optional
model-backed layer cho Router/Synthesizer, trong khi FastAPI worker vẫn giữ
pipeline deterministic và gọi search/pricing tools theo thứ tự cố định.

## 10. Tóm Tắt Ngắn

Phase 4C.3 hoàn tất real pricing boundary cho MVP. V3 hiện có mock-safe default
pricing, opt-in real search, và opt-in three-model pricing ensemble. Project
sẵn sàng chuyển sang Phase 5 sau brainstorming và approval riêng.
