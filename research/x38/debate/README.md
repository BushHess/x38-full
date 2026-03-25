# X38 Debate — Alpha-Lab Architecture Design

Tranh luận kiến trúc giữa Claude Code và Codex để thống nhất thiết kế
framework offline nghiên cứu thuật toán trading.

## Quick Start

1. Đọc `rules.md` — quy tắc tranh luận
2. Đọc `debate-index.md` — chỉ mục topics
3. Đọc `../docs/design_brief.md` — thiết kế sơ bộ (input)
4. Mở topic cần tranh luận trong `NNN-slug/`
5. Dùng `prompt_template.md` để tạo prompt cho mỗi vòng

## Files

| File | Mục đích |
|------|----------|
| `rules.md` | 19 quy tắc tranh luận (kế thừa từ x34, mở rộng cho x38) |
| `prompt_template.md` | 3 mẫu prompt: mở phiên, phản biện, chốt |
| `debate-index.md` | Chỉ mục toàn cục |
| `NNN-slug/` | Mỗi topic một thư mục |

## Participants

| Agent | Role |
|-------|------|
| `claude_code` | Architect (đã thiết kế sơ bộ) + critic |
| `codex` | Reviewer + adversarial critic |

## Workflow

```
design_brief.md → debate topics → rounds → convergence → drafts/ → published/
```

## Operational Procedure — Chạy một vòng debate

### Chuẩn bị (trước Round 1)

1. Đảm bảo evidence đủ cho topic (xem `../docs/evidence_coverage.md`)
2. Đảm bảo `findings-under-review.md` đã có trong topic dir
3. Đọc pre-debate inputs nếu có (`input_*.md`)

### Chạy Round N

```text
1. Human copy prompt từ prompt_template.md (Prompt A cho Round 1, Prompt B cho Round 2+)
   → Thay {TOPIC_DIR} bằng thư mục topic thực tế (ví dụ: 004-meta-knowledge)
   → Gửi cho agent mở đầu (Round 1: claude_code hoặc codex tuỳ chọn)

2. Agent viết response → Human lưu vào:
     {TOPIC_DIR}/{agent}/round-N_{message-type}.md
   Ví dụ: 004-meta-knowledge/codex/round-1_opening-critique.md

3. Human copy Prompt B + đường dẫn response ở bước 2
   → Gửi cho agent đối phương

4. Agent đối phương viết rebuttal → Human lưu vào:
     {TOPIC_DIR}/{other_agent}/round-N_{message-type}.md

5. Lặp bước 3-4 cho đến khi:
   - Mọi issue Converged hoặc Judgment call → dùng Prompt C (chốt)
   - Đạt max_rounds (mặc định 6) → mọi Open → Judgment call → Prompt C

6. Sau khi chốt:
   - Cập nhật debate-index.md (status → CLOSED)
   - Tạo final-resolution.md trong topic dir
   - Cập nhật/tạo draft tương ứng trong drafts/
```

### Quy ước

- **Human là trọng tài**: copy responses giữa agents, không sửa nội dung
- **Mỗi round**: cả hai agents đều nộp file, cùng ngày nếu có thể
- **Pre-debate inputs** (`input_*.md`): nằm ở root topic dir, không trong
  `claude_code/` hay `codex/` (vì là material chung, không phải round artifact)
