# Implementation Reports

Thư mục này lưu implementation evidence và handoff reports cho Shopping
Assistant V3.

Reports là bắt buộc sau mỗi implementation phase hoặc milestone đã được phê
duyệt. Chúng giúp reviewer kiểm tra những gì đã thay đổi trước khi project
chuyển sang phase tiếp theo.

## Workflow

Với mỗi phase:

1. Implementer đọc `gameplan.md`, architecture guides, và current phase guide.
2. Implementer brainstorm với user trước khi code.
3. Implementer chỉ thực hiện approved scope.
4. Implementer viết report bằng `TEMPLATE_IMPLEMENTATION_REPORT.md`.
5. Reviewer đọc report trước.
6. Reviewer kiểm tra code/files khi cần.
7. Reviewer trả về findings mức blocker/major/minor.
8. Implementer sửa các vấn đề bắt buộc.
9. Reviewer approve hoặc request changes.
10. Sau khi approve, reviewer cập nhật `gameplan.md` và guides liên quan nếu
    implementation đã làm thay đổi thực tế.
11. User quyết định có commit/push hay không.

Không chuyển sang phase tiếp theo cho tới khi phase hiện tại có evidence và
review.

## Naming

Dùng:

```text
phase_<number>_<short_name>_report.md
```

Ví dụ:

```text
phase_1_project_setup_report.md
phase_2_backend_api_and_database_report.md
phase_3_async_jobs_report.md
phase_4a_mock_tools_report.md
phase_4b_real_search_report.md
phase_4c_real_pricing_report.md
```

## Quy Tắc Cập Nhật Tài Liệu

Sau khi approval, cập nhật docs khi:

- một planned item đã được implement;
- API/schema/tool behavior đã thay đổi;
- verification commands đã thay đổi;
- phase order đã thay đổi;
- một risk đã được xử lý hoặc mới được phát hiện;
- mock behavior đã trở thành real behavior;
- một future task không còn chính xác.

Không bao giờ cập nhật docs để claim functionality đã hoàn thành trừ khi
implementation và verification chứng minh điều đó.
