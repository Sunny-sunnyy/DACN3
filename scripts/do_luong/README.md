# Script đo (dùng lại được)

Chạy **từ `segment4/`** (để import `price_agents`, thấy `products_vectorstore/`). Kết quả JSON ghi ở `/tmp/prof/` (mất khi
khởi động lại máy — chép ra nơi khác nếu cần giữ). Không sửa code dự án: các script bọc hàm từ bên ngoài. Có gọi API trả phí.

| Script | Đo gì | Lệnh | Tốn |
|---|---|---|---|
| `profile_pipeline.py` | Cả pipeline search_key, thời gian từng hàm, kết quả 3 deal; Pushover bị chặn | `uv run python ../scripts/do_luong/profile_pipeline.py "wireless headphones" <nhãn> [warm]` (`warm` = đánh thức Modal trước, như lúc mở app) | vài cent; ~3,9 GB RAM; 20–110 s |
| `save_pools.py` | Cào BestBuy + Amazon, lưu pool deal (pickle) để đo Bước 3 trên cùng đầu vào | `uv run python ../scripts/do_luong/save_pools.py "air fryer" "wireless headphones"` | 0 API LLM; request Amazon (để thưa) |
| `eval_frontier.py` | MAE của FrontierAgent (RAG + LLM) trên 200 mẫu test đầu `SeanSunny/items_full` | `uv run python ../scripts/do_luong/eval_frontier.py [model:effort ...]` (mặc định gpt-5.1 none, luna none, luna low) | $0,01–0,18 / cấu hình; ~40 s |
| `test_modal_nguoi.py` | Đợi Modal tắt rồi gọi 3 lời Llama song song (kiểm timeout + bỏ qua khi máy nguội) | `uv run python ../scripts/do_luong/test_modal_nguoi.py` | ~1 phút GPU; đợi tới 6 phút |

Luôn đặt `timeout` khi chạy, ví dụ `timeout 500 uv run python …`. Kết quả 29/10: `session_prompt/archive/SESSION_HANDOFF_OPTIMIZE.md`
mục 3.4 và `docs/changelog/`.
