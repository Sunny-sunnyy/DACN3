# CH-20261029-07 — Frontier GPT-5.1 ⇒ gpt-6-luna `low`

29/10/2026 · Claude Code (Opus) · nhánh `toi-uu-search-key` · commit `ae00fa3` (terra), `4d7aaf2` (luna low)

## Giải thích ngắn
Frontier là mô hình quyết 80 % giá ước. User muốn chuyển cả dự án sang luna; trước khi đổi, đo sai số trên 200 sản phẩm test
cho 4 cấu hình. Không cấu hình nào kém GPT-5.1; terra và luna low không phân biệt được ⇒ chọn luna low vì rẻ hơn terra ~7
lần và cả dự án dùng chung một mô hình.

## A. Trước
`frontier_agent.py`: `MODEL = "gpt-5.1"` (bị ghi đè lại trong `__init__`), `reasoning_effort="none"` viết cứng.

## B. Sau
- `MODEL` / `REASONING_EFFORT` là thuộc tính lớp, bỏ dòng ghi đè; hiện `gpt-6-luna` / `low`.
- Đo (`scripts/do_luong/eval_frontier.py`): 200 mẫu test đầu `SeanSunny/items_full`, cùng RAG Chroma, đầu vào `summary`,
  1 lượt / cấu hình (User muốn ít lượt):

| Cấu hình | MAE | Giây / lượt gọi (trung vị) | Tiền 200 mẫu |
|---|---|---|---|
| gpt-5.1 none (cũ) | $31,16 | 0,98 | $0,179 |
| luna none | $31,42 | 1,23 | $0,013 |
| **luna low (chọn)** | **$29,69** | 1,75 | **$0,018** |
| terra none | $28,51 | 1,35 | $0,130 |

- So từng mẫu với gpt-5.1 (khoảng 95 % của chênh lệch): luna none −2,62…+3,14; luna low −4,61…+1,67; terra −5,72…+0,42
  (sát hơn 87 / kém hơn 50 mẫu); terra − luna low −4,47…+2,11 ⇒ mọi khoảng chứa 0: **không kém, chưa chứng minh tốt hơn**.
- Gọi thử qua đúng đường code app: WH-1000XM5 ⇒ $399,99.

## C. Còn tồn tại
- 1 lượt / cấu hình ⇒ chưa đo nhiễu; MAE $31 khác $44,06 của bảng xếp hạng cũ (khác cách / tập đánh giá).
- `price_is_right` dùng chung `FrontierAgent` ⇒ cũng đổi.
- Pipeline đầy đủ chưa chạy lại sau đổi; bước tiền xử lý vẫn là Groq `gpt-oss-20b`.

## D. Kiểm độc lập
Chưa đọc diff độc lập (thay đổi 3 dòng); quyết định dựa trên số đo ở trên.

**Đã thử, chưa áp dụng:** terra none (đắt hơn ~7 lần, không phân biệt được); luna none (kém luna low ~$1,7).
