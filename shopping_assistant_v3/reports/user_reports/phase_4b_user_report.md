# Phase 4B: Real Amazon/BestBuy Search Extraction

## 1. Phase Này Là Gì?

Phase 4B thêm khả năng search Amazon và BestBuy thật vào V3, nhưng đặt sau cờ
opt-in:

```text
ENABLE_REAL_SEARCH=true
```

Default vẫn là mock search từ Phase 4A. Nhờ vậy tests và demo local không bị phụ
thuộc vào mạng, website, hoặc scraping failures.

## 2. Trước Phase Này Hệ Thống Đang Thiếu Gì?

Phase 4A chỉ search trong `mock_products.json`. Nó tốt cho test nhưng chưa cho
biết hệ thống có thể lấy sản phẩm từ nguồn thật.

Phase 4B đưa logic từ prototype `segment4` sang V3 theo cách copy/adapt, không
direct import, không sửa `segment4/`.

## 3. Phase Này Đã Xây Được Gì?

Phase 4B tạo:

- BestBuy real search module.
- Amazon real search module.
- Real search orchestrator.
- Parser tests với HTML fixtures local.
- Opt-in live integration tests, skipped by default.
- Bounded warning grammar cho source failures.

Khi real search bật, worker có thể dùng search thật. Nếu một source fail, hệ
thống cố gắng giữ kết quả còn dùng được từ source khác và trả warning.

## 4. Chức Năng Hoạt Động Như Thế Nào?

Luồng search:

```text
deal_search(input)
  -> nếu ENABLE_REAL_SEARCH=false: đọc mock fixtures
  -> nếu ENABLE_REAL_SEARCH=true: gọi real_deal_search()
       -> BestBuy search nếu source cho phép
       -> Amazon search nếu source cho phép
       -> normalize về ProductCandidate
       -> trả products + warnings
```

BestBuy flow:

```text
search page
  -> Apollo SSR cache
  -> SKU ids
  -> priceBlocks API
  -> product details API
  -> ProductCandidate
```

Amazon flow hiện tại:

```text
search page HTML
  -> parse product cards
  -> lấy title, brand, prices, features nếu có
  -> ProductCandidate
```

Amazon product detail page scraping được để lại cho future milestone.

## 5. Kỹ Thuật Được Sử Dụng

- `curl_cffi` với Chrome impersonation cho real HTTP requests.
- `BeautifulSoup` để parse Amazon HTML.
- BestBuy internal APIs cho price/details.
- Parser functions tách riêng để test bằng local HTML fixtures.
- Warning sanitization để không trả raw exception, HTML, headers, hoặc stack
  trace cho user.
- Opt-in tests cho live search, skipped by default.

## 6. Các File Quan Trọng Và Mối Quan Hệ

```text
backend/tools/deal_search/tool.py
backend/tools/deal_search/real_search.py
backend/tools/deal_search/bestbuy_search.py
backend/tools/deal_search/amazon_search.py
backend/tools/deal_search/schemas.py
tests/fixtures/bestbuy_search_page.html
tests/fixtures/amazon_search_page.html
tests/test_real_search.py
tests/test_tools.py
```

Quan hệ:

- `tool.py` quyết định dùng mock path hay real path theo `ENABLE_REAL_SEARCH`.
- `real_search.py` điều phối Amazon và BestBuy.
- `bestbuy_search.py` chứa logic BestBuy real extraction.
- `amazon_search.py` chứa logic Amazon search-page extraction.
- `schemas.py` giữ output chung `ProductCandidate`.
- `tests/fixtures/*.html` cho parser tests không cần network.
- `test_real_search.py` là opt-in, dùng cho live search khi được phép.

## 7. Cách Tự Kiểm Tra

Default, không scrape live:

```bash
uv run pytest tests/test_tools.py -v
uv run pytest tests/test_real_search.py -v
uv run pytest tests/ -v
```

Khi Phase 4B được approve, default suite có:

```text
99 passed, 8 skipped
```

`8 skipped` là real search tests, chỉ chạy khi bạn bật real search rõ ràng.

## 8. Giới Hạn Hiện Tại

- Real search chạy tuần tự BestBuy rồi Amazon, chưa parallel.
- Timeout là per-request, chưa phải deadline toàn source.
- Amazon mới parse search page, chưa vào product detail page để enrich specs.
- Website có thể block hoặc đổi HTML bất cứ lúc nào.
- Pricing vẫn chưa real ở Phase 4B, trừ mock estimator từ 4A.

## 9. Phase Sau Sẽ Xây Tiếp Gì?

Phase 4C bắt đầu real price estimator extraction. Vì full ensemble từ
`segment4` nặng, Phase 4C được chia nhỏ. Milestone đầu tiên đã hoàn thành là
4C.1: deterministic formatter và neural adapter.

## 10. Tóm Tắt Ngắn

Phase 4B làm hệ thống có khả năng lấy sản phẩm thật từ Amazon/BestBuy, nhưng
vẫn giữ mock mode làm mặc định. Đây là cách cân bằng giữa product realism và
test safety.
