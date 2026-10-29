# CH-20261029-01 — Amazon: không chờ ô tìm kiếm 20 s, giữ cookie WAF

29/10/2026 · Claude Code (Opus) · nhánh `toi-uu-search-key` · commit `4f22fe0`

## Giải thích ngắn
Để vượt lớp chặn bot của Amazon, app mở trình duyệt ngầm lấy cookie. Amazon nay hiện một trang trung gian "Continue
shopping" không có ô tìm kiếm, nên app chờ ô tìm kiếm tới hết 20 giây, báo lỗi và **vứt luôn cookie đã lấy được**. Giờ có
cookie là dùng ngay: phần lấy cookie từ ~22 giây còn ~5 giây.

## A. Trước
- 4/4 lần (mốc sáng 29/10) `wait_for_selector("#twotabsearchtextbox")` hết 20 s; `air fryer` mở trình duyệt 2 lần ⇒ Amazon 63,7 s.
- Dò (`/tmp/prof/probe_amazon.py`): token `aws-waf-token` có sau 1,6 s; trang chỉ có "Click the button below to continue
  shopping"; tìm kiếm có cookie 16 sản phẩm, không cookie vẫn 12.

## B. Sau
- `price_agents/amazon_deals.py` `_get_waf_cookies`: chờ ô tìm kiếm tối đa `WAIT_SEARCH_BOX_MS = 3000`, hết giờ thì log
  "interstitial page" và dùng cookie đang có.
- Đo lại 2 từ khoá: lấy cookie 5,0–5,1 s, cả hai ra đủ 6 deal Amazon.

## C. Còn tồn tại
- Amazon vẫn có lúc trả trang 200 không sản phẩm (2,4 KB khi chưa có token; ~282 KB khi có token) — 3 lần / ~8 lượt 29/10;
  code thử lại 1 lần; nay log tiêu đề + chữ đầu trang để nhận dạng (CH-20261029-04 kèm dòng log).
- 6 trang chi tiết vẫn mở tuần tự (0,5–4,1 s / trang).

## D. Kiểm độc lập
Agent con ngữ cảnh mới đọc diff cả nhánh: không phát hiện vấn đề ở phần này.
