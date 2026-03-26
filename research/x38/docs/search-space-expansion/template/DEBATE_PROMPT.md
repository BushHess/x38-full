# Prompt Template — Search Space Expansion Debate

Thay các biến `{...}` trước khi gửi cho agent.

---

## Biến cần thay

| Biến | Ý nghĩa | Ví dụ |
|------|---------|-------|
| `{AGENT}` | Tên agent nhận prompt | `claude`, `codex`, `gemini`, `chatgptpro` |
| `{N}` | Số vòng hiện tại | `1`, `2`, `3` |
| `{PREVIOUS_FILES}` | Danh sách debate files vòng trước (bỏ trống nếu vòng 1) | Xem ví dụ bên dưới |

---

## Prompt

```
NHIỆM VỤ: Debate vòng {N} — Search Space Expansion cho Alpha-Lab Framework

BẠN LÀ: {AGENT}

---

BỐI CẢNH

Bốn agent (Gemini, Codex, Claude Code, ChatGPT Pro) đang tranh biện về cơ chế
khám phá thuật toán (search space expansion) cho Alpha-Lab Framework (x38).

Yêu cầu gốc:
  docs/search-space-expansion/request.md

Bốn proposal ban đầu:
  docs/search-space-expansion/debate/gemini/gemini_propone.md
  docs/search-space-expansion/debate/codex/codex_propone.md
  docs/search-space-expansion/debate/claude/claude_propone.md
  docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md

{PREVIOUS_FILES}

---

ĐỌC BẮT BUỘC TRƯỚC KHI VIẾT

1. docs/search-space-expansion/template/DEBATE_FORMAT.md  — format đầu ra bắt buộc
2. docs/search-space-expansion/request.md        — yêu cầu gốc
3. Bốn proposal ở trên                          — nội dung cần phản biện
4. {PREVIOUS_FILES}                              — nếu vòng 2+
5. docs/online_vs_offline.md                     — offline/online invariant
6. docs/design_brief.md                          — thiết kế tổng quan
7. debate/rules.md                               — quy tắc tranh luận

---

NHIỆM VỤ CỤ THỂ

Vòng 1:
  - Đọc tất cả 4 proposals.
  - Phản biện trung thực, khách quan, có trách nhiệm — KỂ CẢ tự phản biện
    proposal của chính mình.
  - Viết đầu ra ĐÚNG format trong DEBATE_FORMAT.md (đủ 8 sections).
  - Mọi claim phải kèm evidence pointer (file path, finding ID, nguyên tắc).
  - Tấn công argument, không tấn công kết luận (debate/rules.md §4).

Vòng 2+:
  - Đọc tất cả debate files vòng trước từ cả 4 agents.
  - Chỉ bàn các mục trong Open Issues Register (OI-*) còn OPEN hoặc PARTIAL.
  - KHÔNG viết lại toàn bộ landscape — chỉ cập nhật delta.
  - Muốn lật lại điểm đã CONVERGED: tạo REOPEN-* kèm bằng chứng mới.
  - Ý tưởng mới: tạo NEW-* kèm lý do.
  - Phản hồi từng OI theo format:
      ### OI-{NN}
      - Stance: AGREE / DISAGREE / AMEND
      - Điểm đồng ý: ...
      - Điểm phản đối: ...
      - Đề xuất sửa: ...
      - Evidence: {file path hoặc finding ID}

---

ĐẦU RA

Lưu vào file:
  docs/search-space-expansion/debate/{AGENT}/{AGENT}_debate_lan_{N}.md

---

ĐIỀU KIỆN DỪNG

Khi TẤT CẢ OI-* đã chuyển sang CONVERGED hoặc DEFER ở cả 4 agents:
  → Debate kết thúc.
  → Nội dung Convergence Ledger + Interim Merge Direction của vòng cuối
    chính là kết luận chung.
```

---

## Ví dụ cụ thể

### Gửi vòng 1 cho Claude

Thay:
- `{AGENT}` = `claude`
- `{N}` = `1`
- `{PREVIOUS_FILES}` = *(bỏ trống hoặc ghi "Không có — đây là vòng 1.")*

### Gửi vòng 2 cho Gemini

Thay:
- `{AGENT}` = `gemini`
- `{N}` = `2`
- `{PREVIOUS_FILES}` =
  ```
  Debate vòng 1 (đọc tất cả):
    docs/search-space-expansion/debate/gemini/gemini_debate_lan_1.md
    docs/search-space-expansion/debate/codex/codex_debate_lan_1.md
    docs/search-space-expansion/debate/claude/claude_debate_lan_1.md
    docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md
  ```

### Gửi vòng 3 cho Codex

Thay:
- `{AGENT}` = `codex`
- `{N}` = `3`
- `{PREVIOUS_FILES}` =
  ```
  Debate vòng 1:
    docs/search-space-expansion/debate/gemini/gemini_debate_lan_1.md
    docs/search-space-expansion/debate/codex/codex_debate_lan_1.md
    docs/search-space-expansion/debate/claude/claude_debate_lan_1.md
    docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md

  Debate vòng 2:
    docs/search-space-expansion/debate/gemini/gemini_debate_lan_2.md
    docs/search-space-expansion/debate/codex/codex_debate_lan_2.md
    docs/search-space-expansion/debate/claude/claude_debate_lan_2.md
    docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md
  ```
