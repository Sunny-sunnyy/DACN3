Berikut là bản tổng hợp nội dung chính từ video hướng dẫn scraping dữ liệu Shopee bằng Python và Apify.


# Link: https://www.youtube.com/watch?v=oAzTbsH-58I

### 📌 Tổng quan về dự án
Video hướng dẫn cách vượt qua hệ thống bảo mật chặt chẽ của Shopee (thường chặn bot/coding) bằng cách sử dụng công cụ trung gian là **Apify**.

---

### 🛠️ Các công cụ cần chuẩn bị
1.  **Visual Studio Code (VS Code):** Môi trường lập trình.
2.  **Ngôn ngữ Python:** Sử dụng các thư viện `apify-client`, `json`, và `pandas`.
3.  **Tài khoản Apify:** Đăng ký tại [apify.com](https://apify.com), vào phần **Store** để sử dụng Actor có sẵn.
4.  **Apify API Token:** Lấy trong phần *Settings > API & Integration* của Apify để kết nối code Python với server Apify.

---

### 🚀 Các bước thực hiện chính

#### 1. Thiết lập môi trường và Khởi tạo Client
* Tạo file `main.py`.
* Khai báo API Token để kết nối với Apify.
* Tạo danh sách các URL sản phẩm Shopee mà bạn muốn lấy dữ liệu.

#### 2. Sử dụng "Actor" trên Apify
* **Actor** là các chương trình có sẵn trên Apify được tối ưu để crawl dữ liệu. 
* Trong video sử dụng actor: **Shopee Product Scraper** (của tác giả `YWL FFF 2014`).
* **Lưu ý:** Việc sử dụng Actor này tiêu tốn "Usage" (đơn vị tính phí của Apify), ví dụ: giá cho mỗi 1000 kết quả.

#### 3. Xử lý dữ liệu thô
Dữ liệu từ Shopee trả về rất chi tiết nhưng cần được lọc lại:
* **Thông tin sản phẩm:** ID, tên, URL, mô tả.
* **Đánh giá & Vị trí:** Rating, tổng số review, địa điểm gửi hàng (*Ship from location*).
* **Hình ảnh:** Lấy URL ảnh chính và danh sách các ảnh phụ.
* **Xử lý giá tiền (Quan trọng):** Giá từ API Shopee thường dư 5 chữ số (ví dụ: 100.000 có thể hiển thị là 10.000.000.000). Cần **chia cho 100.000** để đưa về giá trị thực tế.



#### 4. Xuất dữ liệu
* Dữ liệu ban đầu trả về dạng **JSON**.
* Sử dụng thư viện **Pandas** để chuyển đổi danh sách kết quả (`results`) thành một Data Frame.
* Xuất dữ liệu ra file **Excel/CSV** để dễ dàng quản lý và phân tích.

---

### 💡 Những lưu ý "phải biết"
* **Tại sao dùng Apify?** Shopee có cơ chế chống crawl rất mạnh. Nếu dùng các thư viện như Selenium hay BeautifulSoup thuần túy, bạn rất dễ bị phát hiện và chặn IP. Apify giúp giải quyết vấn đề proxy và giả lập trình duyệt.
* **Cấu trúc dữ liệu:** Khi lặp qua các item (`for item in client...`), bạn cần chỉ định đúng các trường (fields) dữ liệu như `display_name` cho danh mục hoặc các sub-fields cho thông tin vận chuyển.
* **Kiểm tra kết quả:** Luôn chạy thử với 1-2 URL trước khi chạy số lượng lớn để tránh lãng phí chi phí "Usage" trên Apify nếu code xử lý dữ liệu bị lỗi.

---
**Kết quả cuối cùng:** Bạn sẽ có một file Excel chứa đầy đủ: Tên sản phẩm, Giá (đã xử lý), Link ảnh, Mô tả, Rating và Địa phương bán hàng.

Trong video, tác giả có hướng dẫn khá chi tiết các bước thực hiện trực tiếp trong code. Dưới đây là quy trình thực hiện cụ thể được rút trích từ nội dung video:

### 1. Cài đặt và Khai báo Thư viện
Bạn cần cài đặt và import 3 thư viện chính:
* `apify-client`: Để kết nối với server Apify.
* `json`: Để xử lý dữ liệu cấu trúc.
* `pandas`: Để chuyển đổi dữ liệu sang dạng bảng (Excel/DataFrame).

### 2. Thiết lập Kết nối API
* Truy cập Apify, vào **Settings** -> **API & Integration** để copy mã **API Token**.
* Trong code, khởi tạo biến `client = ApifyClient("MÃ_TOKEN_CỦA_BẠN")`.

### 3. Chuẩn bị Input (URL sản phẩm)
* Truy cập Shopee trên trình duyệt, tìm kiếm sản phẩm mong muốn.
* Copy đường link (URL) của sản phẩm đó.
* Trong Python, tạo một list chứa các link này: `product_urls = ["link_1", "link_2"]`.

### 4. Gọi "Actor" và Chạy Crawl
* Tìm kiếm Actor có tên **Shopee Product Scraper** trên Apify Store.
* Chọn tab **API** -> **Python** để lấy mã nguồn mẫu.
* Sử dụng lệnh `client.actor("ID_CỦA_ACTOR").call(run_input=...)` để bắt đầu quá trình lấy dữ liệu từ server Shopee về server Apify.

### 5. Lọc và Xử lý Dữ liệu (Công đoạn quan trọng nhất)
Tác giả hướng dẫn tạo một vòng lặp `for` để trích xuất các trường dữ liệu cụ thể vì dữ liệu thô rất nặng:
* **Xử lý giá:** Lấy giá trị tiền và **chia cho 100,000** (do Shopee trả về dư 5 chữ số 0).
* **Trích xuất thông tin:** Lấy tên từ field `item_basic`, lấy vị trí từ field `shipping`, và lấy danh mục từ `categories`.
* **Lưu vào danh sách:** Đưa tất cả các thông tin đã lọc vào một list trống (ví dụ: `results = []`) bằng lệnh `.append()`.

### 6. Chuyển đổi và Xuất File
* Dùng Pandas để chuyển list `results` thành DataFrame: `df = pd.DataFrame(results)`.
* Sử dụng lệnh `df.to_csv()` hoặc `df.to_excel()` để lưu dữ liệu về máy.
* Chạy chương trình bằng lệnh: `python main.py` trong Terminal của VS Code.

---
> **Lưu ý từ video:** Tác giả nhấn mạnh việc sử dụng **Apify Actor** là chìa khóa vì nó giúp vượt qua cơ chế chặn bot của Shopee mà các cách crawl thông thường không làm được.