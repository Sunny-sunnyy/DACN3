# Notebook Companion - Shopping Assistant V3

Thư mục này chứa notebook companion cho các approved user reports của Shopping
Assistant V3.

Mỗi notebook chạy trên current codebase đã approve tới Phase 5A, nhưng nội
dung focus vào phase tương ứng. Đây không phải historical checkout theo từng
commit phase.

## Cách Dùng

Mở notebook bằng VS Code hoặc Jupyter và chọn Python environment của
`shopping_assistant_v3`. Nếu bạn chưa chuẩn bị môi trường:

```bash
cd shopping_assistant_v3
uv sync --extra dev
```

Notebook dùng hai kiểu cell:

- Markdown cells: mục tiêu, expected output, cách đọc kết quả, lỗi thường gặp,
  safety notes.
- Python cells: chạy terminal commands qua `subprocess.run(...)` hoặc gọi trực
  tiếp Python APIs để hiểu contract.

Outputs trong notebook được để trống trong repo. Expected output nằm trong
Markdown để tránh lưu log/path local hoặc dữ liệu nhạy cảm.

## Safety

- Default notebook cells không gọi live Amazon/BestBuy scraping.
- Default notebook cells không gọi OpenAI, Modal, AWS, Terraform, hoặc deploy.
- Real-mode cells chỉ chạy nếu env flags/config đã bật rõ.
- Không paste API keys, Modal tokens, hoặc secrets vào notebook.
- Không commit notebook outputs nếu cell output chứa path/log local.

## Notebook Index

| Notebook | Phase |
|---|---|
| `phase_1_project_setup.ipynb` | Phase 1 Project Setup |
| `phase_2_backend_api_and_database.ipynb` | Phase 2 Backend API And Database |
| `phase_3_async_jobs.ipynb` | Phase 3 Async Jobs |
| `phase_4a_mock_tools.ipynb` | Phase 4A Mock Search/Pricing Tools |
| `phase_4b_real_search.ipynb` | Phase 4B Real Amazon/BestBuy Search Extraction |
| `phase_4c1_neural_pricing.ipynb` | Phase 4C.1 Real Pricing Neural Adapter |
| `phase_4c2_frontier_pricing.ipynb` | Phase 4C.2 Frontier Pricing Adapter |
| `phase_4c3_specialist_pricing.ipynb` | Phase 4C.3 Specialist Pricing Adapter |
| `phase_5a_router_synthesizer.ipynb` | Phase 5A Router And Synthesizer Deterministic |
