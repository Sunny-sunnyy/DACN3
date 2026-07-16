# router

Job orchestration và controlled intent routing. Phân loại message tiếng Việt
của user, tạo normalized English query, và gọi tools theo thứ tự cố định.
Không có free-form ReAct loop.

MVP chỉ thực thi `search_deals`. Các intents khác trả về safe Vietnamese
fallback. Contract: `shopping_assistant_v3/guides/agent_architecture.md`.

Được implement trong Phase 5 (orchestration skeleton có thể xuất hiện trong
Phase 3). Chưa có code.
