Dưới đây là bản tổng hợp chi tiết quy trình thực hiện Web Scraping trên Shopee bằng Python dựa trên video hướng dẫn, được trình bày từng bước một cách khoa học:

# Link: https://www.youtube.com/watch?v=WsU9kIPTi04

### 1. Chuẩn bị môi trường và Cài đặt thư viện
Bạn cần cài đặt 4 thư viện chính thông qua Terminal trong Visual Studio Code:
* **Selenium:** Dùng để điều khiển trình duyệt tự động (vì Shopee dùng JavaScript để tải nội dung).
* **BeautifulSoup4 (bs4):** Dùng để trích xuất (parsing) dữ liệu từ mã nguồn HTML.
* **Pandas:** Dùng để quản lý dữ liệu dưới dạng bảng (DataFrame).
* **Openpyxl:** Thư viện hỗ trợ Pandas xuất dữ liệu ra file Excel.

**Câu lệnh cài đặt:**
```bash
pip install selenium bs4 pandas openpyxl
```

### 2. Tải và Thiết lập Chrome Driver
* **Kiểm tra phiên bản Chrome:** Vào `Settings` -> `About Chrome` để xem phiên bản (ví dụ: 102).
* **Tải Driver:** Truy cập trang chủ Chrome Driver, tải đúng phiên bản tương ứng với trình duyệt và hệ điều hành (thường là Win32 cho Windows).
* **Cài đặt:** Giải nén file `chromedriver.exe` và bỏ vào cùng thư mục với file code Python của bạn.



### 3. Quy trình Code chi tiết (Step-by-Step)

#### Bước 1: Khai báo thư viện và Cấu hình Selenium
Thiết lập các tùy chọn cho trình duyệt như chạy ngầm (`headless`) và kích thước cửa sổ để đảm bảo hiển thị đủ 5 cột sản phẩm.

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import pandas as pd
import time

opsi = webdriver.ChromeOptions()
opsi.add_argument('--headless') # Chạy ngầm không mở cửa sổ trình duyệt
servis = Service('chromedriver.exe')
driver = webdriver.Chrome(service=servis, options=opsi)
```

#### Bước 2: Kỹ thuật cuộn trang (Scrolling) - Rất quan trọng
Shopee sử dụng cơ chế "Lazy Load", dữ liệu chỉ hiện ra khi bạn cuộn trang xuống. Trong video, tác giả sử dụng một vòng lặp JavaScript để cuộn 6 lần, mỗi lần 500 pixel để tải hết 60 sản phẩm.



#### Bước 3: Lấy mã nguồn và Parsing dữ liệu
Sau khi cuộn để tải hết dữ liệu, dùng Selenium lấy `page_source` và đưa vào BeautifulSoup để bóc tách.

#### Bước 4: Xác định các thẻ HTML (Inspect Element)
Đây là bước thủ công nhưng quan trọng nhất. Bạn cần tìm các `class` đặc trưng của Shopee:
* **Khu vực sản phẩm:** Tìm thẻ Div bao quanh một item (thường có class liên quan đến `shopee-search-item-result__item`).
* **Tên sản phẩm:** Thẻ Div với class cụ thể (ví dụ trong clip là `ie3a6...`).
* **Giá:** Thẻ Span.
* **Hình ảnh:** Thẻ `img` lấy thuộc tính `src`.
* **Link sản phẩm:** Thẻ `a` lấy thuộc tính `href` (cần cộng thêm tiền tố `https://shopee.co.id`).
* **Số lượng bán & Vị trí:** Các thẻ Div tương ứng.

#### Bước 5: Xử lý ngoại lệ (Exception Handling)
Dữ liệu trên web không phải lúc nào cũng đầy đủ. Bạn cần dùng câu lệnh `if` để kiểm tra:
* Nếu `terjual` (đã bán) là `None`, chương trình sẽ không gọi hàm `.get_text()` để tránh lỗi crash code.

### 4. Lưu dữ liệu vào Excel
Dữ liệu sau khi thu thập được đưa vào các danh sách (List), sau đó tạo thành một Dictionary và chuyển sang Pandas DataFrame để xuất file.

```python
df = pd.DataFrame({
    'Nama': list_nama,
    'Harga': list_harga,
    'Link': list_link
})
df.to_excel('macbook.xlsx', index=False)
```

### 5. Những lưu ý "phải biết" để thành công
1.  **Window Size:** Phải set kích thước cửa sổ (ví dụ: 1300x800) để Selenium "thấy" được dữ liệu.
2.  **Time Sleep:** Cần có khoảng nghỉ (`time.sleep`) giữa các lần cuộn trang để máy chủ Shopee kịp phản hồi dữ liệu.
3.  **Base URL:** Khi lấy link sản phẩm, Shopee chỉ trả về đường dẫn tương đối (vế sau), bạn phải tự cộng thêm chuỗi `https://shopee.co.id` vào phía trước.
4.  **Kiểm tra tính chính xác:** Luôn dùng `driver.save_screenshot('home.png')` để kiểm tra xem bot của bạn đang thực sự nhìn thấy gì trên trang web.