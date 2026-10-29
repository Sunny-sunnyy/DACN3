---
name: practical-project-coding
description: Dùng khi thiết kế cách cài đặt, viết, debug, refactor, review hoặc kiểm code trong repo tech2ai (search_key / price_is_right, cào BestBuy + Amazon, chọn deal bằng LLM, ensemble ước giá, Modal, Gradio, Pushover). Code rõ ràng, đơn giản, phức tạp chỉ khi có lý do đo được; thay đổi đúng phạm vi; chạy thật với dịch vụ thật; giải thích được cho User. Không dùng cho việc chỉ viết tài liệu hay câu hỏi chung. So phương án / đo trước–sau ⇒ dùng thêm run-experiment.
---

# Practical project coding — tech2ai

Chuyển thể 29/10/2026 từ skill cùng tên của một repo khác của User; bổ sung bài học thật của tech2ai. Luật trong
`session_prompt/CACH_LAM_VIEC.md` và lời User thắng skill này khi khác nhau. Nguyên tắc chung về cách viết (nghĩ trước, thay đổi đúng chỗ): skill
`karpathy-guidelines` — skill này là phần riêng của repo. Chỗ karpathy nói "viết test rồi cho pass": ở repo này "test" = phép
kiểm **chạy thật** (cổng 3), không mock.

## Mục đích

Giải quyết đúng nhu cầu thật bằng code rõ ràng, có kiểm chứng tương xứng. Phức tạp được chấp nhận khi nó giải một vấn đề
thật, cách trực tiếp không đủ, lợi ích đo được. Không dùng kỹ thuật vì nó "hiện đại" hay "có thể cần sau này".
Việc nhỏ, rõ ⇒ sửa nhỏ + kiểm đúng chỗ, không biến skill thành thủ tục.

## Ngôn ngữ

- Tên hàm, biến, class, schema **tiếng Anh**; ghi chú / docstring **tiếng Việt**, chỉ ghi *vì sao* (lý do, ràng buộc, số đo,
  sự cố), không diễn giải lại câu lệnh. Viết theo cách của code xung quanh.

## Cổng 1 — Trước khi sửa

- Xác định hành vi hiện tại (đọc code + **chạy thật** nếu cần), hành vi mong muốn, luồng dữ liệu bị ảnh hưởng.
- **Nói ra giả định**; nhiều cách hiểu thì trình bày, không chọn lặng lẽ. Có cách đơn giản hơn thì nói.
- Tiêu chí thành công quan sát được (ví dụ: "2 từ khoá, cả hai nguồn có deal, 3 deal giá USD > 0, thời gian ↓").
- **Tìm mọi bên gọi** của hàm / class sắp đổi — `EnsembleAgent`, `SpecialistAgent`, `MessagingAgent`, `deals.py` dùng
  chung cho **cả search_key lẫn price_is_right** (29/10: đổi timeout Llama làm price_is_right gần như luôn bỏ Llama — chỉ
  agent con đọc diff mới bắt được).

## Cổng 2 — Khi sửa

**Luồng dữ liệu trực tiếp:** `input → biến đổi → dependency → side effect → output / lỗi` đọc theo được. Không thêm registry,
factory, wrapper, cache, retry, lớp cấu hình khi chưa có vấn đề quan sát được.

**Chỉ phức tạp khi trả lời được 5 câu:** vấn đề thật là gì; vì sao cách trực tiếp không đủ; lợi ích cụ thể; kiểm chứng ra
sao; vì sao đáng. Không trả lời được ⇒ giữ cách trực tiếp.

| Được phức tạp (ví dụ thật của repo) | Không được (phòng xa) |
|---|---|
| Bước 4 song song 3 deal × 3 mô hình — đo 33–40 s ⇒ ~4 s | retry cho lỗi chưa từng thấy |
| khoá cho DNN / encode + Chroma khi chạy song song — một model GPU dùng chung giữa luồng | lớp cấu hình cho thứ chỉ có một giá trị |
| gộp hàng trùng — BestBuy trả 5 màu một mẫu cùng URL, giá khác nhau | app / interface mới "để sau này đổi" khi chỉ có một cài đặt |
| giữ ấm Modal phía app — cold start 32–46 s, không deploy được app mới | fallback âm thầm sang mô hình khác rồi coi là thành công |

**Code giữ con số:** giá, URL, tiền, ngưỡng do code lấy / tính; LLM chỉ chọn (trả ID) hoặc viết lời (29/10: nano chép lại
giá / URL và có lượt trả 8 deal dù yêu cầu 3).

**Xử lý lỗi có mục đích:** chỉ bắt lỗi khi lỗi xảy ra được **và** bên gọi phản ứng hữu ích (bỏ một mô hình rồi chia lại trọng
số; bỏ một deal; báo "blocked"). Log tên lỗi + nội dung ngắn. Không nuốt lỗi; không biến lỗi thành giá trị giả (giá 0 lặng lẽ
kéo ước lượng xuống); "không thấy" ≠ "không có" ≠ "bị chặn".

**Thay đổi đúng chỗ:** mỗi dòng đổi truy được về yêu cầu / nguyên nhân / việc kiểm. Không "dọn" code lân cận; code chết có
từ trước ⇒ ghi lại, không xoá.

## Cổng 3 — Kiểm chứng

- **Chạy đường thật**, không mock / fake / stub dependency (OpenAI, Groq, Modal, Chroma, BestBuy, Amazon đều gọi thật).
  Logic thuần (gộp trùng, chia trọng số, kiểm tên miền) kiểm bằng đầu vào nhỏ offline — đó không phải bằng chứng cho phần
  tích hợp.
- **Pushover phải chặn khi đo** (script đo thay `messenger.notify`); chạy app thật thì nói User trước vì có tin thật.
- **Amazon: request thưa, có `sleep`**; dồn dập ⇒ bị chặn IP (28/10, 29/10 gặp trang 200 rỗng). Đo xong lưu pool deal
  (pickle) để đo các bước sau khỏi cào lại.
- Việc nặng (pipeline nạp torch + DNN 1,1 GB ≈ 3,9 GB RAM, Modal, huấn luyện): **một việc một lúc, luôn `timeout`**.
- Thay đổi có thể làm chậm / tốn RAM (song song, đọc dữ liệu lớn) ⇒ ghi **thời gian + RAM đỉnh** (`/usr/bin/time -f %M`).
- Đo thời gian bằng `time.perf_counter()` — đồng hồ WSL có lúc nhảy lùi (29/10: thời gian âm khi dùng `time.time()`).
- Không chạy được ⇒ ghi đúng `NOT RUN` / `PARTIAL` / `FAIL`.

## Cổng 4 — Tự review và bàn giao

- Đọc lại diff: đúng phạm vi; không phức tạp thừa; không lộ secret / raw exception; **kiểu xuống dòng không đổi** (nhiều file
  trong `segment4/price_agents/` là CRLF — sửa bằng script Python phải giữ `\r\n`, nếu không cả file thành diff).
- Việc vừa / lớn: giao **agent con ngữ cảnh mới đọc diff** trước khi commit (không đưa kết luận của mình, chỉ đưa code +
  mục tiêu); kiểm từng phát hiện trước khi sửa, không sửa theo mù (Claude Code có thêm skill máy `receiving-code-review`).
  Agent không có agent con ⇒ ghi "chưa kiểm độc lập" và đề nghị User mở một phiên agent khác đọc diff.
- Bàn giao ngắn: đổi gì · đã chạy gì · số trước ⇒ sau · phần chưa kiểm · **"Giải thích ngắn" lời thường** (làm gì, vì sao,
  ảnh hưởng gì) — User phải tự nói lại được.

## Môi trường (tech2ai)

Môi trường, bẫy kỹ thuật, an toàn (`uv run`, `.env`, CRLF, `perf_counter`, Amazon, Modal, luna, repo công khai):
`session_prompt/CACH_LAM_VIEC.md` mục 4, 7 — không chép lại ở đây. Thêm riêng cho code: script ngoài repo nạp khoá bằng
`load_dotenv(find_dotenv(usecwd=True))` và chạy từ `segment4/`; script đo dùng lại ⇒ `scripts/do_luong/`.
