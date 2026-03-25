# X34 Debate

Thư mục chứa các phiên tranh luận khoa học cho X34.

## Layout

```text
debate/
  README.md
  rules.md
  debate-index.md
  prompt_template.md

  001-x34-findings/        # Các phát hiện của X34
    findings-under-review.md
    final-resolution.md
    codex/
    claude_code/
```

## Quy tắc đặt tên topic slug

Format: `NNN-<mô-tả-ngắn>`

- `NNN` — số thứ tự 3 chữ số, zero-padded (`001`, `002`, ...). Đảm bảo `ls` luôn hiển thị đúng thứ tự thời gian.
- `<mô-tả-ngắn>` — kebab-case, 2-5 từ, mô tả nội dung đợt tranh luận.

Quy tắc bổ sung:
- Không tái sử dụng số đã dùng (kể cả topic bị hủy).
- Slug không chứa topic ID (topic ID ghi trong file, không ghi trong tên thư mục).

## Start here

1. [rules.md](rules.md) — quy tắc tranh luận
2. [debate-index.md](debate-index.md) — chỉ mục toàn cục các topic
3. Mở thư mục topic tương ứng để xem chi tiết
