# Implementation Report Template

## Phase

`<phase number and name>`

Implementer:

Date:

Branch:

Commit reviewed: `<commit hash or "not committed yet">`

## Tóm Tắt

Nêu chính xác những gì đã được implement.

Nói rõ behavior là mocked, fixture-based, partial, hay real.

## Files Đã Tạo

```text
path/to/file - mục đích
```

## Files Đã Sửa

```text
path/to/file - thay đổi gì và vì sao
```

## Commands Đã Chạy

Liệt kê các command chính xác.

```bash
uv run pytest ...
npm run ...
curl ...
```

Với mỗi command, ghi pass/fail và tóm tắt output quan trọng.

## Tests Đã Chạy

Liệt kê automated tests và kết quả.

Nếu tests không được chạy, giải thích lý do.

## Bằng Chứng Verification

Mô tả manual checks và evidence.

Ví dụ:

- Tạo một chat job qua API.
- Xác nhận status chuyển từ `pending` sang `completed`.
- Xác nhận result payload khớp phase guide.
- Xác nhận logs có `job_id`.
- Xác nhận không có real network/model call nào được thực hiện.

## Known Issues

Phân loại từng item:

- Blocker
- Major
- Minor

Nếu không có, ghi:

```text
Không có known issues.
```

## Deviations From Guide

Với mỗi deviation:

```text
Guide expectation:
Actual implementation:
Reason:
Should docs be updated? yes/no
```

Nếu không có, ghi:

```text
Không có intentional deviations.
```

## Suggested Doc Updates

Liệt kê docs/guides có thể đã stale.

Ví dụ:

```text
gameplan.md - update Current Phase Status.
guides/2_backend_api_and_database.md - verify command changed.
```

Nếu không có, ghi:

```text
Không thấy cần documentation updates.
```

## Reviewer Checklist

Reviewer nên kiểm tra:

- Scope nằm trong approved phase.
- Không có file `segment4/` nào thay đổi trừ khi được approve rõ.
- Không có file `shopping_assistant_v2/` nào thay đổi.
- Không có secrets nào bị đọc, in, hoặc commit.
- Default tests không gọi paid APIs hoặc live scraping.
- API/schema/tool contracts khớp guide liên quan.
- Failure paths lưu safe errors.
- Logs/audit events có `job_id` ở nơi bắt buộc.
- Docs phản ánh thay đổi thực tế được cập nhật sau approval.

Reviewer decision:

```text
Decision: approved / changes requested / blocked
Reviewer:
Date:
Required changes:
Docs to update after approval:
```
