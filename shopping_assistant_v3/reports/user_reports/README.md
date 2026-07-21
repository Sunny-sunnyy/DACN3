# Báo Cáo Người Dùng Cuối - Shopping Assistant V3

## Mục Đích

Thư mục này dành cho bạn đọc như chủ dự án, không phải như reviewer kỹ thuật.
Các file ở đây giải thích từng phase đã xây được gì, vì sao cần phase đó, code
đang hoạt động ra sao, file nào quan trọng, và giới hạn nào vẫn còn.

Các báo cáo kỹ thuật gốc vẫn nằm ở `shopping_assistant_v3/reports/`. Chúng chứa
nhiều chi tiết review, command, test, và implementation evidence. Bộ báo cáo
này là bản dễ đọc hơn, giúp bạn nắm dự án mà không cần đọc hết code.

## Trạng Thái Hiện Tại

Shopping Assistant V3 hiện đã hoàn thành tới:

```text
Phase 5A: Router And Synthesizer - Deterministic Path
```

Nói ngắn gọn: backend local đã có API, database, async worker, mock search và
mock pricing pipeline, real Amazon/BestBuy search opt-in, real neural/frontier/
specialist pricing boundaries opt-in, Router tiếng Việt deterministic,
Synthesizer tiếng Việt deterministic, progress steps, summary cards, và
agent_runs audit cho Router/Synthesizer. Frontend chat, optional OpenAI Agents
SDK providers, demo flow cuối cùng, và production roadmap vẫn là các milestone
sau.

## Nên Đọc Theo Thứ Tự Nào?

| File | Nên đọc khi bạn muốn hiểu |
|---|---|
| `phase_1_user_report.md` | V3 bắt đầu như thế nào, folder nào được tạo, vì sao project được reset lại. |
| `phase_2_user_report.md` | Backend API và SQLite database được dựng ra sao. |
| `phase_3_user_report.md` | Vì sao cần async job và worker xử lý nền. |
| `phase_4a_user_report.md` | Mock search/pricing tools hoạt động thế nào để test không cần mạng. |
| `phase_4b_user_report.md` | Real Amazon/BestBuy search được đưa vào V3 như opt-in feature ra sao. |
| `phase_4c1_user_report.md` | Real neural price estimator boundary hoạt động thế nào và còn thiếu gì. |
| `phase_4c2_user_report.md` | Frontier pricing dùng ChromaDB + OpenAI được đưa vào V3 như opt-in boundary ra sao. |
| `phase_4c3_user_report.md` | Specialist pricing dùng Modal được đưa vào V3 như opt-in boundary ra sao và ensemble 3 model hoạt động thế nào. |
| `phase_5a_user_report.md` | Router tiếng Việt, Synthesizer tiếng Việt, progress steps, summary cards, và audit rows deterministic hoạt động ra sao. |

## Bức Tranh Lớn Của Hệ Thống Hiện Tại

Luồng hiện tại của backend:

```text
User message
  -> POST /api/chat-jobs
  -> tạo job trong SQLite
  -> local worker xử lý job
  -> Router hiểu intent và tạo query_en
  -> search tool tìm sản phẩm
  -> price estimator định giá
  -> Synthesizer tổng hợp câu trả lời tiếng Việt từ evidence
  -> lưu products, estimates, audit logs
  -> GET /api/chat-jobs/{job_id} trả kết quả
```

MVP backend đã có câu trả lời tiếng Việt deterministic từ Synthesizer. Người
dùng cuối vẫn chưa có frontend chat hoàn chỉnh; phần đó thuộc Phase 6.

## Những Quy Tắc An Toàn Đang Được Giữ

- Default tests không scrape Amazon/BestBuy.
- Default tests không gọi OpenAI, Modal, hoặc model API tốn phí.
- Không commit file model weights `.pth`.
- Không đọc hoặc in secrets.
- Real search cần `ENABLE_REAL_SEARCH=true`.
- Real model pricing cần `ENABLE_REAL_MODEL_CALLS=true` và config riêng.
- Frontier pricing cần `PRICER_CHROMADB_PATH`, `PRICER_FRONTIER_MODEL_ID`, và
  API key được set trong local env.
- Specialist pricing cần `PRICER_SPECIALIST_SERVICE`,
  `PRICER_SPECIALIST_CLASS`, Modal dependency, và Modal auth/config local.

## Milestone Tiếp Theo

Milestone được phép tiếp theo là:

```text
Phase 5B: Optional OpenAI Agents SDK Router/Synthesizer Providers
```

Phase này sẽ thêm optional model-backed Router/Synthesizer providers bằng
OpenAI Agents SDK, nhưng deterministic Phase 5A vẫn là default/fallback. Không
nên bắt đầu nếu chưa chốt scope, cost, tracing, dependency, secret handling,
verification plan, và cách xử lý test harness cho `tests/test_api.py` sau khi
Codex sandbox gặp timeout với `TestClient`/AnyIO threadpool nhưng local
unsandboxed tests vẫn pass.
