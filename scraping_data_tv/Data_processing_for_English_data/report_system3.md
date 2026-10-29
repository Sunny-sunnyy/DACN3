# Báo cáo: Hệ thống AI Price Intelligence — "The Price Is Right" (bản 3)

> **Mục đích:** Trình bày hệ thống tìm deal và ước lượng giá trị thật của sản phẩm — bài toán, kiến trúc, cách từng khâu hoạt động, vì sao chọn cách làm đó, kết quả đo được và giới hạn còn lại.
> **Phạm vi:** Đồ án DACN3 — từ dữ liệu và mô hình (tóm tắt) đến hai ứng dụng đang chạy, kèm đợt tối ưu ngày 28–29/10/2026.

**Nhãn:** 29/10/2026 · segment4/ · search_key.py · price_is_right.py
**Thẻ giá:** Sony WH-1000XM5 — BestBuy | 228,00 | 313,92 | 85,92 | Một deal thật từ lượt đo ngày 29/10/2026, từ khoá "wireless headphones". Mô hình chỉ đọc mô tả, không nhìn giá bán.

**Cách đọc báo cáo này.** Mỗi khâu được giải thích theo cùng một thứ tự: *bài toán* (khâu này giải quyết việc gì) → *cơ chế*
(nó chạy thế nào) → *vì sao chọn cách này* (và cách nào đã bị bỏ) → *khi nào nó hỏng*. Cuối mỗi phần có **một câu tự kiểm**:
trả lời được mà không cần nhìn lại là đã hiểu phần đó. Số liệu luôn ghi kèm **đo ngày nào, trên dữ liệu gì**; chỗ nào chỉ là
suy luận thì ghi rõ là suy luận.

**Thay đổi so với bản 2 (11/05/2026):** viết lại theo hệ thống hiện tại thay vì theo từng ngày học; mô hình OpenAI chuyển hết
sang gpt-6-luna; cách vượt lớp chặn Amazon đổi hẳn; thêm xử lý song song, chống sập, giữ ấm Modal; thời gian một lượt tìm từ
70–107 giây còn 21–34 giây. Bản 2 vẫn giữ nguyên ở `report_system.md` / `report_system2.html` để đối chiếu.

---

## Phần 1: Bài toán và hành trình

### 1.1 Bài toán

Trên các trang bán hàng, một sản phẩm "đang giảm giá" chưa chắc đã rẻ: giá gạch ngang có thể bị đẩy lên, hoặc giá gốc vốn đã
thấp hơn mức shop ghi. Hệ thống trả lời câu hỏi: **"Với mô tả này, sản phẩm đáng giá bao nhiêu?"** — rồi so với giá bán để biết
deal có thật sự tốt không.

- **Đầu vào:** một từ khoá (app 1) hoặc tin khuyến mãi từ RSS của DealNews (app 2).
- **Đầu ra:** tối đa 3 deal (app 1) / 5 deal (app 2), mỗi deal có giá bán, **giá ước lượng**, **discount = giá ước − giá bán**;
  discount lớn thì gửi thông báo đẩy lên điện thoại (Pushover).
- Mô hình **không nhìn giá bán** khi ước giá — chỉ nhìn mô tả sản phẩm. Nếu nhìn giá bán, nó sẽ có xu hướng đoán gần giá đó và
  mất ý nghĩa so sánh.

### 1.2 Hành trình: dữ liệu → mô hình → hệ thống

| Giai đoạn | Làm gì | Kết quả chính | Chi tiết |
|---|---|---|---|
| Thu thập dữ liệu | Amazon Reviews 2023 (McAuley-Lab), **8 nhóm hàng**: Automotive, Electronics, Office Products, Tools & Home Improvement, Cell Phones & Accessories, Toys & Games, Appliances, Musical Instruments | ~2,93 triệu sản phẩm → bỏ trùng còn ~2,89 triệu | `Report_data_processing_v2.md` (Day 1) |
| Lọc và lấy mẫu | giữ giá **$0,5–$999,49**, mô tả đủ dài; lấy mẫu có trọng số `giá²`, giảm trọng số nhóm Automotive (×0,05) và Tools (×0,5) để không lệch về hàng rẻ | **820.000** sản phẩm (800k train / 10k val / 10k test); giá trung bình ~$59 → ~$140 | như trên |
| Tiền xử lý bằng LLM | viết lại mỗi sản phẩm theo khuôn `Title / Category / Brand / Description / Details`, bỏ mã linh kiện | dataset `SeanSunny/items_full` trên HuggingFace | Day 2 |
| Mô hình | từ đoán ngẫu nhiên tới mạng nơ-ron sâu, LLM, fine-tune | bảng 1.3 | Day 3–5, `report_fine_tune_llm.md` |
| Hệ thống | đưa mô hình thành 2 ứng dụng có giao diện, cào dữ liệu thật, thông báo | Phần 2–3 | báo cáo này |
| Tối ưu | đo, sửa lỗi, tăng tốc, chống sập | Phần 4 | báo cáo này |

### 1.3 So sánh mô hình (lúc huấn luyện)

Sai số tuyệt đối trung bình (**MAE** — trung bình |giá đoán − giá thật|, càng thấp càng tốt) trên **200 mẫu test**, số lấy từ
các báo cáo huấn luyện:

| Mô hình | MAE | Ghi chú |
|---|---|---|
| Đoán ngẫu nhiên | $382,08 | mốc dưới |
| Luôn đoán giá trung bình | $106,18 | mốc không dùng mô hình |
| XGBoost (đặc trưng từ chữ) | $68,23 | mô hình truyền thống tốt nhất |
| Claude Opus 4.5 (không huấn luyện thêm) | $47,10 | LLM tiên tiến, hỏi thẳng |
| DNN 289 triệu tham số (HashingVectorizer → 8 khối residual) | $46,02 | chạy trên máy, dùng trong ensemble |
| GPT-5.1 + RAG | $44,06 | Frontier ban đầu |
| Llama-3.2-3B fine-tune QLoRA | $39,85 | adapter ~73 MB, chạy trên Modal |
| **Ensemble 0,8 × Frontier + 0,1 × Llama + 0,1 × DNN** | **$29,9** | dùng trong hệ thống |

**Vì sao ensemble tốt hơn từng mô hình:** ba mô hình sai theo những cách khác nhau (LLM có kiến thức chung, Llama học khuôn giá
của đúng dữ liệu này, DNN bám vào từ khoá); trung bình có trọng số làm các sai lệch ngược chiều triệt tiêu một phần.

> **Tự kiểm:** Vì sao dữ liệu huấn luyện chỉ giữ hàng dưới $999,49, và điều đó ảnh hưởng thế nào khi người dùng tìm "laptop"?

---

## Phần 2: Kiến trúc tổng thể

### 2.1 Ba tầng

```
Tầng giao diện   search_key.py / price_is_right.py           (Gradio, cổng 7860)
Tầng framework   multi_source_framework.py / deal_agent_framework.py
                 (mở ChromaDB, nạp agent một lần, giữ kết quả, memory.json của app 2)
Tầng agent       price_agents/ + bestbuy_untils/
                 mỗi agent một việc: cào, chọn deal, ước giá, viết tin nhắn, điều phối
```

Mỗi agent kế thừa lớp `Agent` (log có màu theo agent) và làm **một việc**. Phần điều phối (`MultiSourcePlanningAgent`,
`PlanningAgent`) là code Python viết thẳng các bước — không để LLM tự quyết thứ tự, vì các bước luôn cố định.

### 2.2 Hai ứng dụng

| | App 1 — `search_key.py` | App 2 — `price_is_right.py` |
|---|---|---|
| Kích hoạt | người dùng nhập từ khoá | tự chạy mỗi 5 phút |
| Nguồn deal | cào BestBuy + Amazon | RSS DealNews (5 chuyên mục) |
| Chọn deal | gpt-6-luna chọn 3 | gpt-6-luna chọn 5 |
| Ước giá | ensemble (dùng chung) | ensemble (dùng chung) |
| Thông báo | discount > $100 | discount > $50 |
| Nhớ | không | `memory.json` để không báo trùng |

### 2.3 Luồng dữ liệu của app 1

```
Mở app ── luồng nền: đánh thức Modal ‖ nạp mô hình (~9–20 s) ── giữ ấm Modal
   │
Từ khoá
   │
Bước 1  Cào song song   BestBuy (API nội bộ)  ‖  Amazon (trình duyệt ngầm lấy cookie → curl_cffi)
   │                    → mỗi nguồn ≤ N sản phẩm đang sale + trạng thái ok / empty / blocked / error
Bước 2  Gộp             → một danh sách chung; gộp hàng trùng (giữ bản rẻ nhất)
Bước 3  Chọn deal       → gpt-6-luna trả số thứ tự 3 deal + tóm tắt; code lấy giá / URL thật
Bước 4  Ước giá         → 3 deal song song; mỗi deal: viết lại mô tả → Llama ‖ Frontier ‖ DNN → trung bình có trọng số
   │
Bảng kết quả (sắp theo discount) → discount > $100 và link đúng shop → gửi Pushover
```

### 2.4 Mô hình nào chạy ở đâu

| Thành phần | Chạy ở | Vì sao |
|---|---|---|
| gpt-6-luna (chọn deal, Frontier, tin nhắn) | OpenAI API | LLM lớn, trả tiền theo token, rất rẻ |
| gpt-oss-20b (viết lại mô tả) | Groq qua LiteLLM | nhanh (0,3–1,1 s / lần) |
| Llama-3.2-3B fine-tune | Modal, GPU T4 | theo thiết kế của khoá học: mô hình chạy trên GPU thuê, chỉ tính tiền khi máy bật [suy luận: GPU 4 GB của máy User đã dùng cho DNN + bộ mã hoá câu] |
| DNN, SentenceTransformer, ChromaDB | máy User (GPU) | nhỏ, nhanh (DNN 0,1–0,2 s; tìm RAG 0,0–0,3 s) |

> **Tự kiểm:** Ở Bước 4, vì sao 3 mô hình có thể chạy cùng lúc, nhưng Bước 3 và Bước 4 thì không thể chạy song song với nhau?

---

## Phần 3: Từng khâu theo lớp

### 3.1 Cào dữ liệu BestBuy và Amazon

**Bài toán.** Lấy danh sách sản phẩm **đang giảm giá** khớp từ khoá, kèm tên, hãng, giá, mô tả tính năng, link — từ hai trang
có lớp chống bot, chạy trên máy WSL2 đặt tại Việt Nam.

**Cơ chế — BestBuy.** Trang sản phẩm của BestBuy chặn request từ WSL2, nhưng các API JSON nội bộ thì không:

1. Mở trang chủ với `?intl=nosplash` để bỏ qua bước chọn quốc gia.
2. Tải trang tìm kiếm, lấy mọi mã sản phẩm (SKU) theo **đúng thứ tự trên trang** (liên quan nhất trước).
3. Gọi API giá theo **lô 25 SKU** → tên, hãng, giá hiện tại, giá gốc; **"đang sale" = `pricingType == "onSale"`**.
4. Với mỗi SKU đang sale, gọi API chi tiết → danh sách tính năng + link chuẩn. Đủ số deal thì dừng sớm.

**Cơ chế — Amazon.** Amazon bật **AWS WAF**: trang đầu tiên trả một đoạn JavaScript bắt trình duyệt tự chứng minh là người
thật. Thư viện `curl_cffi` giả được "dấu vân tay" mạng của Chrome nhưng **không chạy JavaScript**, nên một mình nó không qua.
Cách làm là **lai**:

1. Mở Chromium chạy ngầm (Playwright), vào trang chủ, chờ cookie `aws-waf-token` (~1,6 s), đóng trình duyệt.
2. Chép cookie sang `curl_cffi`, thêm cookie `i18n-prefs=USD` để ép giá đô la.
3. Tìm kiếm bằng link `/s?k=…&ref=nb_sb_noss` kèm header `Referer` — giống như bấm ô tìm kiếm trên trang chủ.
4. Đọc từng thẻ sản phẩm: **"đang sale" = có giá gạch ngang lớn hơn giá hiện tại**; mở trang chi tiết lấy tính năng.

**Vì sao chọn cách này.**

- Dùng trình duyệt thật cho mọi bước thì chắc chắn qua, nhưng chậm (6,3 s mỗi lần tìm, phải giữ trình duyệt mở). Cách lai chỉ
  dùng trình duyệt **một lần** để lấy cookie, phần còn lại nhanh như request thường (1,3–1,8 s / lần tìm) [đã đo 28/10].
- Với BestBuy, gọi API nhanh và ổn định hơn đọc HTML, lại không bị chặn.

**Khi nào hỏng.**

- **Amazon đổi lớp chặn** bất kỳ lúc nào. Ngày 28/10 đổi sang WAF (code cũ ra 0 sản phẩm); ngày 29/10 trang chủ hiện trang trung
  gian "Continue shopping" làm code chờ vô ích 20 giây (đã sửa — Phần 4).
- **Chặn mềm:** Amazon trả trang bình thường (mã 200) nhưng không có sản phẩm — gặp 3 lần trong khoảng 8 lượt ngày 29/10. Code
  thử lại một lần với cookie mới; vẫn rỗng thì báo nguồn đó `empty`.
- **Gửi request dồn dập** → bị chặn IP tạm thời. Thử nghiệm Amazon phải thưa, có nghỉ.
- **Giá VND:** IP Việt Nam làm Amazon hiện giá VND; code cũ đọc nhầm thành đô la. Nay chuỗi giá không có `$` bị bỏ qua.
- **Lỗi BestBuy đã gặp (28/10):** API giá **âm thầm chỉ trả 25 SKU** mỗi lần dù gửi nhiều hơn → trước đó chỉ 25 / 200+ sản phẩm
  được kiểm giá (`wireless headphones` ra 2 deal thay vì 6).

> **Tự kiểm:** Vì sao `curl_cffi` qua được lớp chặn của BestBuy nhưng không qua được AWS WAF của Amazon nếu không có trình duyệt?

### 3.2 Chọn deal bằng LLM (Bước 3)

**Bài toán.** Từ 8–12 sản phẩm của hai nguồn, chọn 3 deal có mô tả rõ ràng và tóm tắt lại thành câu để đưa cho ensemble.

**Cơ chế.**

1. **Gộp hàng trùng** trước: cùng nguồn và (cùng link, hoặc cùng tên khi bỏ các từ chỉ màu) → giữ bản rẻ nhất. Ví dụ 29/10:
   BestBuy trả 5 màu tai nghe WH-1000XM5 **cùng một link** nhưng giá $228–$298 → giữ bản $228; danh sách 12 → 8.
2. Mỗi sản phẩm được đánh số `Deal 1`, `Deal 2`… trong prompt (không kèm link).
3. gpt-6-luna trả về theo khuôn cố định (**structured output**): `deal_number` + câu tóm tắt.
4. **Code** lấy giá, link, tên gốc từ danh sách đã cào và ghép mô tả `[Nguồn] <tên gốc>. <tóm tắt>`.

**Vì sao chọn cách này.**

- Bản cũ để mô hình **tự chép lại** giá và link vào câu trả lời — có thể chép sai; một lượt đo còn trả **8 deal** dù được dặn
  tối đa 3. Nguyên tắc mới: **mô hình chỉ chọn, code giữ con số**.
- Tên gốc ghép vào vì luna có lúc tóm tắt "This 6-quart air fryer…" mất cả hãng lẫn tên mẫu — ensemble mất thông tin hãng
  (một nồi chiên Ninja $229,99 bị ước $167, lượt có tên ước $212).
- Mức suy luận `none` thay vì `low`: đo trên cùng danh sách deal, 2 từ khoá × 3 lượt — `none` 4,2–4,3 s, `low` 4,6–5,3 s, cả hai
  6 / 6 lượt đủ 3 deal khác nhau, 0 lần sai giá / link.

**Khi nào hỏng.** Tiêu chí chọn vẫn là "mô tả chi tiết nhất, giá rõ ràng" — **chưa phải "giảm nhiều nhất"**; chưa có mốc so với
một luật đơn giản không dùng LLM (ví dụ "3 deal giảm nhiều nhất") để chứng minh LLM đáng dùng ở bước này.

> **Tự kiểm:** Nếu LLM trả về `deal_number = 15` trong khi danh sách chỉ có 8 deal, hệ thống xử lý thế nào, và vì sao an toàn hơn cách cũ?

### 3.3 Ensemble ước giá (Bước 4)

**Bài toán.** Ước giá trị thật của từng deal từ mô tả, đủ nhanh để người dùng không phải chờ lâu.

**Cơ chế.**

1. **Viết lại mô tả** (gpt-oss-20b trên Groq) theo khuôn `Title / Category / Brand / Description / Details` — đúng khuôn dữ liệu
   lúc huấn luyện, để mô hình nhận đầu vào quen thuộc. Lỗi thì dùng mô tả gốc.
2. Ba mô hình chạy **cùng lúc** trên cùng mô tả đã viết lại:

| Mô hình | Trọng số | Cách ước |
|---|---|---|
| **Frontier** | 80 % | tìm **5 sản phẩm giống nhất** trong ChromaDB (800.000 sản phẩm train, kèm giá thật) → đưa vào prompt của gpt-6-luna (`low`) làm ngữ cảnh → luna trả một con số. Đây là **RAG** (truy xuất rồi sinh câu trả lời) |
| **Specialist** | 10 % | Llama-3.2-3B fine-tune; prompt `"What does this cost to the nearest dollar? … Price is $"`, sinh tối đa 5 token. Tokenizer của Llama mã hoá mỗi số 0–999 thành **một token**, nên bài toán gần như "chọn 1 trong ~1.000 số" |
| **DNN** | 10 % | biến chữ thành vector 5.000 chiều bằng HashingVectorizer → mạng 8 khối residual → giá (đã log-hoá khi huấn luyện) |

**Bước 3 — kết hợp:** `giá = 0,8 × Frontier + 0,1 × Llama + 0,1 × DNN`. Mô hình nào **lỗi hoặc trả 0** thì bị bỏ, trọng số chia lại
   cho các mô hình còn lại. Ví dụ: Frontier $150, DNN $100, Llama quá giờ → (0,8 × 150 + 0,1 × 100) / 0,9 = **$144,44**.

**Bước 4 — song song:** 3 deal cũng chạy cùng lúc.

**Vì sao chọn cách này.**

- **Frontier đổi GPT-5.1 → gpt-6-luna `low`** (29/10). Đo trên 200 mẫu test đầu của `items_full`, cùng cách RAG, mỗi cấu hình
  1 lượt:

| Cấu hình Frontier | MAE | Tiền cho 200 lời gọi |
|---|---|---|
| GPT-5.1 `none` (cũ) | $31,16 | $0,179 |
| gpt-6-luna `none` | $31,42 | $0,013 |
| **gpt-6-luna `low` (chọn)** | **$29,69** | **$0,018** |
| gpt-6.1-terra `none` | $28,51 | $0,130 |

  So từng mẫu, khoảng dao động 95 % của mọi chênh lệch đều chứa 0 → **không cấu hình nào chắc chắn tốt hơn hay kém hơn GPT-5.1**
  với 200 mẫu. Chọn luna `low` vì **không kém**, rẻ hơn GPT-5.1 ~10 lần, rẻ hơn terra ~7 lần, và cả hệ thống dùng chung một mô hình.
  (MAE $31 ở đây thấp hơn $44,06 của bảng 1.3 — khác cách / tập đánh giá; so sánh trong bảng này là trên cùng 200 mẫu.)
- **Coi 0 là lỗi:** Frontier và Llama trả 0 khi không đọc ra được con số. Trước đây số 0 đi thẳng vào trung bình, kéo kết quả
  xuống ~20 % giá thật mà không ai biết.

**Khi nào hỏng.**

- **Ngoài vùng huấn luyện:** hàng trên $999 (laptop, TV) bị ước thấp; nhóm hàng không có trong dữ liệu (đồ bếp như nồi chiên
  không dầu) làm RAG kéo về sản phẩm sai loại — kiểm 29/10: 20 sản phẩm gần nhất của "air fryer" là rơ-le điện.
- **Llama hay lặp lại vài giá** ($60, $220, $350…) cho các sản phẩm khác nhau — đã thấy trong log, chưa phân tích nguyên nhân.
- **Modal nguội:** Llama mất 32–46 s để bật máy; search_key chỉ chờ 10 s rồi bỏ Llama ở lượt đó (mục 3.5, Phần 4).

> **Tự kiểm:** Nếu cả Frontier lẫn Llama đều lỗi, giá ước của deal đó lấy từ đâu, và nó đáng tin tới mức nào?

### 3.4 Thông báo

**Bài toán.** Báo cho người dùng khi có deal thật sự tốt, không báo nhầm, không gửi link lạ.

**Cơ chế.** Deal tốt nhất có discount vượt ngưỡng ($100 ở app 1, $50 ở app 2) → gpt-6-luna viết 2–3 câu vui, gây tò mò →
Pushover gửi lên điện thoại kèm link. Có nút gửi tay trong giao diện.

**Vì sao chọn cách này.**

- **Kiểm tên miền trước khi gửi:** chỉ gửi khi link thuộc `bestbuy.com` / `amazon.com`. Lý do: chữ trên trang bán hàng là
  **dữ liệu không đáng tin** và được đưa vào prompt của LLM; app lại có đường gửi ra ngoài. Ghép hai điều đó là đủ để một trang
  "dụ" hệ thống gửi link lạ tới điện thoại. Link vốn do code dựng nên đây là lớp kiểm thêm.
- **Gửi lỗi không làm mất kết quả:** Pushover có giới hạn chờ 15 s; trả mã khác 200 thì ghi lỗi, bảng kết quả vẫn hiện.

**Khi nào hỏng.** Thông báo chỉ tốt bằng giá ước: ước sai thì báo nhầm. Chưa đếm tỉ lệ báo nhầm / bỏ lỡ (Phần 6).

> **Tự kiểm:** Vì sao kiểm tên miền vẫn cần, dù link do code dựng chứ không do LLM viết?

### 3.5 Giao diện, nạp mô hình và giữ ấm Modal

**Bài toán.** Lần tìm đầu tiên không phải chờ nạp mô hình; Llama trên Modal sẵn sàng khi cần mà không tốn tiền GPU vô ích.

**Cơ chế.**

- **Luồng nền khi mở app:** đánh thức Modal ngay (gửi một lời gọi không chờ kết quả), đồng thời nạp ChromaDB + mô hình
  (~9–20 s) trong lúc người dùng gõ từ khoá. Có khoá để lần bấm Search sớm không tạo ra hai bộ mô hình.
- **Giữ ấm:** Modal tự tắt máy sau 60 s rảnh. App ping mỗi 50 s; **ngừng sau 15 phút không có lượt tìm**, tự bật lại khi có lượt
  tìm mới; tắt app là ngừng.
- **Chờ Llama tối đa 10 s** (chỉ app 1). Quá giờ thì bỏ Llama ở deal đó, 45 s sau đó bỏ qua luôn (máy đang khởi động).
- **Ô Status** hiện trạng thái từng nguồn (`BestBuy: ok (6), Amazon: ok (6)`) và báo lỗi nếu pipeline hỏng (trước đây giao
  diện treo "Processing..." mãi).

**Vì sao chọn cách này.** Cách tốt hơn là bảo Modal tự giữ máy lâu hơn (đổi cấu hình phía server), nhưng **Modal không cho tạo
app GPU mới khi tài khoản chưa gắn thẻ** (29/10) → giữ ấm từ phía app. Chi phí: ~$0,59 / giờ chỉ trong lúc app mở và có người
tìm trong 15 phút gần nhất; mở app mà không tìm gì thì tối đa ~$0,16.

**Khi nào hỏng.** Bấm Search ngay sau khi mở app (trước ~40 s) thì máy Modal chưa bật xong → lượt đầu thiếu Llama. App 2 không
giữ ấm nên mỗi lần quét đầu phải chờ máy bật (giữ hành vi cũ, không giới hạn chờ).

> **Tự kiểm:** Modal tính tiền theo cái gì, và vì sao "giữ ấm" lại tốn tiền dù máy gần như không làm gì?

---

## Phần 4: Đợt tối ưu 28–29/10/2026

### 4.1 Cách làm

1. **Đo mốc trước khi sửa** — script bọc từng hàm từ bên ngoài (không sửa code) đo thời gian, chặn Pushover khi đo.
2. **Sửa từng thứ một**, mỗi thứ một commit; mốc quay lại là tag `moc-truoc-toi-uu-2026-10-29`.
3. **Kiểm hồi quy sau mỗi bước** trên cùng 2 từ khoá: không lỗi · cả hai nguồn có deal · 3 deal khác nhau · giá USD > 0 · giá ước
   hợp lý so với mốc · có số thời gian.
4. **Cố định đầu vào khi so mô hình:** cào một lần, lưu danh sách deal, so mọi cấu hình trên cùng danh sách (web đổi từng phút).
5. **Kiểm chéo:** một agent AI mới, không biết gì về quá trình sửa, đọc toàn bộ thay đổi — tìm ra **3 lỗi thật** mà các lượt đo
   bỏ sót (Modal nguội + 3 deal song song chờ ~30 s; app 2 bị đổi hành vi ngoài ý muốn; app 2 có thể treo khi gửi tin lỗi) →
   đã sửa và thử lại với Modal thật.

### 4.2 Trước và sau

| Chỗ | Trước | Sau | Nguyên nhân gốc → cách sửa |
|---|---|---|---|
| Lấy cookie Amazon | 22–44 s | ~5 s | chờ ô tìm kiếm 20 s trên trang "Continue shopping" rồi vứt cookie → chờ 3 s, dùng cookie có sẵn |
| Lần Search đầu | +~22 s nạp mô hình | 0 s | nạp lười ở lần bấm đầu → nạp ở luồng nền khi mở app |
| Llama (Modal) | 31,5–46 s mỗi lượt máy nguội | ~0,9 s khi ấm; nguội thì bỏ sau 10–14 s | Modal tắt máy sau 60 s → đánh thức + ping + giới hạn chờ |
| Bước 4 (3 deal) | 33–40 s | ~4 s | tuần tự cả deal lẫn mô hình → song song 2 tầng |
| Bước 3 | 3,3–4,4 s, có lượt trả 8 deal | 3,7–5,1 s, luôn ≤ 3 deal | đổi sang luna, chọn theo số thứ tự |
| **Cả một lượt tìm** | **69,5 s** (`wireless headphones`) / **106,7 s** (`air fryer`) | **21,3 s** / **30,2 s**; chạy app thật (`laptop`) 27,1 s | |

### 4.3 Xử lý song song — vì sao an toàn

- Dùng **luồng (thread)** chứ không dùng async: gần như toàn bộ thời gian là **chờ mạng** (OpenAI, Groq, Modal, hai trang web);
  phần tính toán trên máy rất ngắn. Luồng cho lợi ích tương đương mà không phải viết lại code.
- **Khoá** ở những chỗ dùng chung tài nguyên: model GPU trên máy (DNN, bộ mã hoá câu + ChromaDB) chạy lần lượt; các lời gọi Llama
  **xếp hàng** để Modal không bật thêm máy nguội (tốn tiền, không nhanh hơn) — máy ấm chỉ ~0,9 s mỗi lời gọi.
- **Cố ý chưa song song** trang chi tiết Amazon: gửi dồn dập dễ bị chặn IP. Đây là chỗ chậm lớn nhất còn lại (13–19 s).

### 4.4 Đã thử và không dùng

| Phương án | Kết quả | Vì sao không dùng |
|---|---|---|
| App Modal mới (giữ ấm 10 phút phía server, tối đa 1 máy, ghim phiên bản thư viện) | chưa chạy được | Modal từ chối deploy app GPU mới khi chưa gắn thẻ |
| gpt-6-luna `low` cho Bước 3 | 4,6–5,3 s, cùng chất lượng | `none` nhanh hơn |
| gpt-6.1-terra cho Frontier | MAE $28,51 | không phân biệt được với luna low, đắt hơn ~7 lần |
| gpt-6-luna `none` cho Frontier | MAE $31,42 | luna low sát hơn ~$1,7, tiền chênh rất nhỏ |

### 4.5 Bài học

1. **Đo trước khi đoán:** chỗ chậm nhất buổi sáng (cookie Amazon chờ 20 s vô ích) không nằm trong danh sách dự đoán ban đầu —
   chỉ lộ ra khi đo từng hàm.
2. **"HTTP 200" không có nghĩa là có dữ liệu** (trang chặn mềm của Amazon); **"không có" khác "bị chặn"** — nay mỗi nguồn báo
   trạng thái riêng.
3. **Mô hình chỉ đề xuất, code giữ con số** — áp ở Bước 3 (giá / link) và ensemble (số 0 là lỗi).
4. **Hàm dùng chung phải kiểm mọi bên gọi:** đổi giới hạn chờ Llama suýt làm app 2 gần như luôn mất Llama.
5. **Một người đọc độc lập** bắt được lỗi mà người sửa và các lượt đo đều bỏ sót.

> **Tự kiểm:** Vì sao phải cố định danh sách deal trước khi so gpt-5-nano với gpt-6-luna, thay vì mỗi lượt cào lại từ đầu?

---

## Phần 5: Kết quả và đánh giá

### 5.1 Một lượt chạy thật (User chạy app, từ khoá `laptop`, 29/10)

| Deal | Giá bán | Giá ước | Discount |
|---|---|---|---|
| [Amazon] Acer Aspire 14 AI Copilot+ PC | $597,86 | $864,73 | $266,87 → **tự gửi thông báo** |
| [BestBuy] HP OmniBook X Flip 2-in-1 | $649,99 | $887,05 | $237,06 |
| [BestBuy] HP Victus 15.6" Gaming Laptop | $949,99 | $979,55 | $29,56 |

Cả lượt 27,1 s: cào 11,2 s · chọn deal 5,1 s · ước giá 8,3 s (máy Modal vừa bật xong). Với laptop cần đọc kết quả cẩn thận: dữ
liệu huấn luyện là hàng 2023 giá ≤ $999, nên giá ước của các máy mới, đắt chưa đáng tin (mục 3.3, Phần 6).

### 5.2 Số đo tổng hợp

| Chỉ số | Giá trị | Điều kiện đo |
|---|---|---|
| Thời gian một lượt tìm | 21–34 s | 2 từ khoá, Modal đã đánh thức, 29/10 |
| MAE Frontier (luna low) | $29,69 | 200 mẫu test, 1 lượt |
| MAE ensemble (bản GPT-5.1) | $29,9 | 200 mẫu test, lúc huấn luyện |
| RAM đỉnh | ~3,9 GB | khi chạy pipeline |
| Tiền OpenAI mỗi lượt tìm | ~$0,001 | ước từ số token đã đo |
| Tiền GPU Modal mỗi lượt (máy ấm) | ~$0,0005 | 3 lời gọi × ~0,9 s × $0,000164 / s |

### 5.3 Chưa đo (ghi thẳng để không hiểu nhầm)

- **MAE của cả ensemble sau khi đổi Frontier sang luna** — mới đo riêng Frontier.
- **Độ đúng của giá ước trên sản phẩm cào thật hôm nay** — MAE chỉ đo trên dữ liệu Amazon 2023 đã xử lý.
- **Tỉ lệ báo nhầm / bỏ lỡ** của thông báo.
- **App 2 (`price_is_right.py`) chạy lại sau đợt sửa** — mới kiểm bằng đọc code và chạy thử từng phần.

> **Tự kiểm:** MAE $29,69 cho biết điều gì về giá ước của một laptop $1.200 cào từ BestBuy hôm nay — và không cho biết điều gì?

---

## Phần 6: Giới hạn và hướng phát triển

| Giới hạn | Ảnh hưởng | Hướng tiếp |
|---|---|---|
| Dữ liệu huấn luyện: 8 nhóm hàng, giá ≤ $999, năm 2023 | laptop / TV đắt bị ước thấp; đồ bếp không có trong dữ liệu | thêm nhóm hàng và khoảng giá khi huấn luyện lại; trước mắt hướng người dùng tới nhóm hàng phù hợp |
| Chưa có thước đo trên hàng cào thật | chưa biết giá ước cho sản phẩm hôm nay sai bao nhiêu | bộ 15–20 sản phẩm có giá tham chiếu, chấm bằng code |
| Giá gốc của shop có cào được nhưng chưa dùng | Bước 3 không thấy, bảng không hiện để đối chiếu với giá AI | đưa giá gốc vào danh sách deal và bảng kết quả |
| Bước 3 chọn theo "mô tả chi tiết", chưa có mốc không dùng LLM | chưa chứng minh LLM đáng dùng ở bước này | so với luật "3 deal giảm nhiều nhất" |
| Trang chi tiết Amazon mở lần lượt | Bước 1 còn 11–26 s | mở song song 2–3 trang, mỗi luồng một session, đo tỉ lệ bị chặn |
| Llama hay lặp lại vài giá | đóng góp 10 % kém tin cậy | thử 10–20 sản phẩm đa dạng, so khuôn đầu vào với lúc huấn luyện |
| Amazon thay đổi lớp chặn | có thể ra 0 deal bất kỳ lúc nào | trạng thái nguồn đã báo rõ; theo dõi tỉ lệ thành công |
| Chưa lưu lịch sử | tìm lại sản phẩm cũ vẫn phải ước lại | lưu kết quả vào SQLite — vừa nhanh hơn, vừa có lịch sử giá |

> **Tự kiểm:** Trong các hướng trên, hướng nào nên làm trước nếu mục tiêu là "giá ước đáng tin hơn", và vì sao không phải "chạy nhanh hơn"?

---

## Phụ lục

### A. Cài đặt và chạy

```bash
cd tech2ai
uv sync                                  # cài thư viện theo uv.lock
uv run playwright install chromium       # trình duyệt chạy ngầm để lấy cookie Amazon
cd segment4
uv run search_key.py                     # app 1 → http://127.0.0.1:7860
uv run price_is_right.py                 # app 2
```

File `.env` ở `tech2ai/.env`: `OPENAI_API_KEY`, `GROQ_API_KEY`, `PRICER_PREPROCESSOR_MODEL=groq/openai/gpt-oss-20b`,
`PUSHOVER_USER`, `PUSHOVER_TOKEN`, `HF_TOKEN`. Modal đọc token ở `~/.modal.toml`; app `pricer-service` đã deploy sẵn.
**Mẹo:** mở app rồi đợi ~40 s mới tìm lượt đầu để Llama có mặt; nên thử các từ khoá như `noise cancelling headphones`,
`soundbar`, `gaming monitor`, `digital piano` (giá $100–$500, nằm trong vùng dữ liệu huấn luyện).

### B. Thuật ngữ

| Thuật ngữ | Nghĩa trong dự án |
|---|---|
| **MAE** | sai số tuyệt đối trung bình: trung bình của \|giá đoán − giá thật\| trên tập test |
| **RAG** | truy xuất rồi sinh: tìm sản phẩm giống trong ChromaDB, đưa vào prompt để LLM ước giá |
| **Ensemble** | kết hợp nhiều mô hình bằng trung bình có trọng số |
| **Fine-tune / QLoRA** | huấn luyện thêm một mô hình có sẵn; QLoRA = nén mô hình gốc 4-bit + chỉ huấn luyện một adapter nhỏ (~73 MB) |
| **Structured output** | bắt LLM trả lời theo khuôn dữ liệu cố định (Pydantic) thay vì văn bản tự do |
| **Reasoning effort** | mức "suy nghĩ" trước khi trả lời của gpt-6-luna (`none`, `low`, …); cao hơn thì chậm và tốn hơn, không chắc tốt hơn |
| **Cold start** | thời gian máy GPU trên Modal khởi động lại sau khi đã tắt (32–46 s) |
| **AWS WAF** | lớp chống bot của Amazon, bắt trình duyệt chạy JavaScript để nhận cookie |
| **Chặn mềm** | trang trả mã 200 bình thường nhưng không có dữ liệu |
| **Kiểm hồi quy** | chạy lại các trường hợp cũ để chắc thay đổi mới không làm hỏng thứ đang chạy tốt |
| **Nhiễu** | chênh lệch giữa các lần chạy lặp lại mà không đổi gì — chênh lệch nhỏ hơn nhiễu thì chưa kết luận được |

### C. Tài liệu liên quan

- `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md` — tài liệu kỹ thuật app 1 (từng file, từng hàm, cơ chế chi tiết).
- `segment4/mo_ta_du_an/DOCUMENTATION_PRICE_IS_RIGHT.md` — tài liệu app 2.
- `scraping_data_tv/Data_processing_for_English_data/Report_data_processing_v2.md` — dữ liệu, mô hình truyền thống, DNN.
- `scraping_data_tv/Data_processing_for_English_data/report_fine_tune_llm.md` — fine-tune Llama 3.2 bằng QLoRA.
- `docs/changelog/README.md` — từng thay đổi code ngày 29/10 kèm số trước / sau và phương án đã thử.
- `scripts/do_luong/` — script đo dùng lại: cả pipeline, MAE Frontier, từ khoá có trong vùng dữ liệu không.

### D. Lịch sử báo cáo

| Bản | Ngày | Nội dung |
|---|---|---|
| 1 — `report_system.md` | 11/05/2026 | theo từng ngày học Week 8, kèm nhiều code |
| 2 — `report_system2.html` | 26/09/2026 | bản HTML (giao diện) của bản 1 [suy luận từ nội dung và ngày sửa file] |
| **3 — `report_system3.md` / `.html`** | **29/10/2026** | **viết lại theo hệ thống hiện tại + đợt tối ưu 28–29/10** |
