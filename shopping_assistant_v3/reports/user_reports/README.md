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
Phase 4C.3: Specialist Price Estimator Extraction - Specialist Adapter + Boundary
```

Nói ngắn gọn: backend local đã có API, database, async worker, mock search và
mock pricing pipeline, real Amazon/BestBuy search opt-in, real neural pricing
boundary opt-in, Frontier pricing boundary opt-in qua ChromaDB + OpenAI, và
Specialist pricing boundary opt-in qua Modal. Khi cả ba pricing adapters
available, real estimator có thể dùng ensemble formula gốc. Frontend chat,
Router tiếng Việt, Synthesizer tiếng Việt, demo flow cuối cùng, và production
roadmap vẫn là các phase sau.

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

## Bức Tranh Lớn Của Hệ Thống Hiện Tại

Luồng hiện tại của backend:

```text
User message
  -> POST /api/chat-jobs
  -> tạo job trong SQLite
  -> local worker xử lý job
  -> search tool tìm sản phẩm
  -> price estimator định giá
  -> lưu products, estimates, audit logs
  -> GET /api/chat-jobs/{job_id} trả kết quả
```

MVP vẫn đang ở backend/tool foundation. Người dùng cuối chưa có frontend chat
hoàn chỉnh. Câu trả lời tiếng Việt hiện tại vẫn là placeholder từ worker, chưa
phải Synthesizer thật. Điều đó đúng với phase order: Router và Synthesizer sẽ
đến ở Phase 5, Frontend chat ở Phase 6.

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
Phase 5: Router And Synthesizer
```

Phase này sẽ thêm Router cho tiếng Việt, Synthesizer trả lời tiếng Việt từ
evidence, deterministic progress steps, và optional hybrid controlled OpenAI
Agents SDK path. Không nên bắt đầu nếu chưa chốt scope, cost, tracing,
dependency, secret handling, và verification plan.
