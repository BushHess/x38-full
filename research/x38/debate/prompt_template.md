## Prompt A — Mở phiên

Gửi cho bên mở đầu. Sửa `{TOPIC_DIR}` bằng thư mục topic thực tế.

Trước khi viết:
- Tôn trọng `AGENTS.md` nếu môi trường đã nạp; nếu chưa, đọc `AGENTS.md`.
- Đọc `docs/online_vs_offline.md` (bắt buộc).
- Đọc `x38_RULES.md` để xác nhận authority order:
  `published/ > debate/{TOPIC_DIR}/ > docs/design_brief.md > PLAN.md`.
- Nếu `debate/{TOPIC_DIR}/final-resolution.md` đã tồn tại thì DỪNG:
  topic đã CLOSED, không mở debate mới.
- Follow `AGENTS.md` for environment boundaries (working directory, git root, Python root).

```
ROUND 1 — Mở phiên

- Bối cảnh: Chúng ta đang thiết kế kiến trúc cho Alpha-Lab — một framework
  offline để nghiên cứu và phát triển thuật toán trading từ nền trắng.
  Framework này kế thừa phương pháp từ V4→V8 (x37) nhưng biên dịch thành
  pipeline tự động thay vì dựa vào AI conversation.

- Thiết kế tổng quan: `docs/design_brief.md`
- Danh sách các điểm cần tranh luận: `debate/{TOPIC_DIR}/findings-under-review.md`
- Quy tắc tranh luận: `debate/rules.md`
- Chỉ mục topic: `debate/debate-index.md` (navigation/status hint, không phải source of truth cho rounds)
- Tài liệu authority trong topic dir: `debate/{TOPIC_DIR}/README.md`,
  `findings-under-review.md` (OPEN topics), `final-resolution.md` (CLOSED topics)
- Pre-debate input (read-only reference, KHÔNG phải authority): `input_*.md` (nếu có)

Tài liệu tham khảo (read-only) — bảng đầy đủ trong `x38_RULES.md` §7.
Evidence coverage tracker: `docs/evidence_coverage.md`

Các bên tranh luận: Claude Code ↔ Codex

Nhiệm vụ:
1. Đọc `AGENTS.md` (nếu cần), `docs/online_vs_offline.md`, `x38_RULES.md`,
   `debate/rules.md`, `debate/{TOPIC_DIR}/findings-under-review.md`, và evidence
   liên quan đến topic.
2. Đọc `debate/{TOPIC_DIR}/README.md` và `input_*.md` nếu có.
3. Với mỗi issue có `current_status = Open`, đưa ra critique kèm:
   - classification (Sai thiết kế / Thiếu sót / Judgment call)
   - evidence pointer (file path + dòng, hoặc nguyên tắc kỹ thuật)
   - lập luận tấn công argument, không phải kết luận
4. Kết thúc bằng bảng trạng thái theo mẫu trong rules.md §11.

Sau khi bạn nêu ý kiến, tôi sẽ chuyển cho bên kia phản biện.
```

---

## Prompt B — Vòng phản biện tiếp theo

Gửi cho bên nhận phản biện. Sửa round number, `{TOPIC_DIR}`, và đường dẫn
artifact cho khớp vòng hiện tại.

Trước khi viết:
- Nếu `debate/{TOPIC_DIR}/final-resolution.md` đã tồn tại thì DỪNG:
  topic đã CLOSED, không viết thêm round artifact.
- Đọc `AGENTS.md` (nếu chưa có trong context), `docs/online_vs_offline.md`,
  `x38_RULES.md`, và `debate/rules.md`.

```
ROUND N — Phản biện

- Bối cảnh: Chúng ta đang thiết kế kiến trúc cho Alpha-Lab — một framework
  offline để nghiên cứu và phát triển thuật toán trading từ nền trắng.

- Thiết kế tổng quan: `docs/design_brief.md`
- Danh sách các điểm cần tranh luận: `debate/{TOPIC_DIR}/findings-under-review.md`
- Quy tắc tranh luận: `debate/rules.md`
- Chỉ mục topic: `debate/debate-index.md` (chỉ để định hướng topic, không thay cho round history)

Tài liệu tham khảo (read-only): bảng đầy đủ trong `x38_RULES.md` §7.
Evidence coverage tracker: `docs/evidence_coverage.md`

Các bên tranh luận: Claude Code ↔ Codex

- Ý kiến mới nhất của bên kia: `debate/{TOPIC_DIR}/{agent}/round-N_[message-type].md`

Nhiệm vụ:
1. Đọc artifact trên, đối chiếu với `findings-under-review.md`, các round gần nhất
   trong topic dir, và tài liệu tham khảo liên quan.
2. Phản biện từng issue, kèm evidence pointer cụ thể.
3. Nhắc lại các quy tắc bắt buộc:
   - Tấn công argument, không phải kết luận (§4).
   - Trước khi chấp nhận, phải steel-man vị trí cũ theo §7.
   - Cấm ngôn ngữ nhượng bộ mềm (§8).
   - Không mở topic mới sau round 1 (§12).
4. Kết thúc bằng bảng trạng thái cập nhật.

Sau khi bạn nêu ý kiến, tôi sẽ chuyển cho bên kia phản biện tiếp.
```

---

## Prompt C — Chốt và áp dụng

Dùng khi mọi issue đã Converged hoặc Judgment call (hoặc đạt max rounds).

Điều kiện tiên quyết:
- TẤT CẢ issues trong scope phải là Converged hoặc Judgment call.
- Human researcher đã quyết định mọi Judgment call.
- Codex closure audit (Prompt C từ phía Codex) nên hoàn thành trước khi possible.

```
Chốt — Áp dụng thay đổi

- Bảng trạng thái vòng cuối: `debate/{TOPIC_DIR}/{agent}/round-N_[message-type].md`
- Đọc thêm: TẤT CẢ round files trong topic dir + `judgment-call-deliberation.md` (nếu có).

Bước 1 — TẠO hoặc ĐỒNG BỘ `final-resolution.md`:
  - Nếu chưa có: tạo theo Template D bên dưới.
  - Nếu đã có: coi là hồ sơ closure authoritative.
    Chỉ sửa khi human researcher phê duyệt rõ ràng.

Bước 2 — CẬP NHẬT `findings-under-review.md`:
  - Cập nhật `current_status` cho từng issue đã chốt.
  - Ghi round/ngày chốt nếu schema cho phép.
  - KHÔNG tạo field ad-hoc (ví dụ `review_status`) — dùng field hiện có.

Bước 3 — CẬP NHẬT `debate-index.md` + topic `README.md`:
  - Đổi status topic sang CLOSED khi closure lần đầu.
  - Đồng bộ summary với `final-resolution.md`.

Bước 4 — TẠO/CẬP NHẬT draft spec trong `drafts/`:
  - Chuyển quyết định thiết kế đã hội tụ thành spec sections.
  - Mỗi quyết định phải truy vết: Issue ID → final-resolution.md → evidence.

Bước 5 — KIỂM TRA không trôi trạng thái:
  - `README.md`, `debate-index.md`, `EXECUTION_PLAN.md` đều phản ánh CLOSED.

Quy tắc áp dụng theo loại:

a. HỘI TỤ THẬT (Converged + steel-man đã xác nhận):
   → Áp dụng quyết định thiết kế vào `drafts/`.
   → Cập nhật `current_status = Converged`, ghi round đã chốt.

b. JUDGMENT CALL:
   → Ghi cả hai vị trí:
     NOTE (Judgment call, round N): [tradeoff]
     Lựa chọn: [X] — Lý do: [...]
     Decision owner: [tên]
   → Cập nhật `current_status = Judgment call`.

c. Issue còn Open, hội tụ giả, hoặc không rõ ràng:
   → KHÔNG áp dụng. Giữ nguyên, ghi chú lý do chưa chốt.
```

---

## Template D — final-resolution.md

Tạo file này trong topic dir khi **mọi** issue đã Converged hoặc Judgment call.

```markdown
# Final Resolution — {Topic Name}

**Topic ID**: X38-T-{NN}
**Closed**: YYYY-MM-DD
**Rounds**: N
**Participants**: claude_code, codex

## Decisions

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| X38-{CODE}-01 | ... | Accepted / Modified / Rejected | Converged / Judgment call | N |
| ... | ... | ... | ... | ... |

## Key design decisions (for drafts/)

### Decision 1: {tên quyết định}

**Accepted position**: ...
**Rejected alternative**: ...
**Rationale**: ... (evidence pointer)

### Decision 2: ...

## Unresolved tradeoffs (for human review)

- {tradeoff 1}: {hai vị trí}, decision owner = human researcher
- ...

## Draft impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `architecture_spec.md` | §X | Create / Update |
| ... | ... | ... |
```
