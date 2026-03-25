# Debate Format — Search Space Expansion

Template cho mọi agent sử dụng khi viết debate round.
Mỗi agent giữ nội dung riêng, nhưng PHẢI tuân theo cấu trúc dưới đây.

---

## Quy tắc chung

1. Mỗi vòng = 1 file: `{agent}_debate_lan_{N}.md`
2. Vòng 1 phải có đủ mọi section. Vòng 2+ chỉ cập nhật các section thay đổi.
3. Không viết lại toàn bộ landscape mỗi vòng — chỉ cập nhật delta.
4. Mọi claim phải kèm evidence pointer (file path, finding ID, hoặc nguyên tắc).
5. Không dùng ngôn ngữ nhượng bộ mềm (xem `debate/rules.md` §8).

---

## Template

````markdown
---
doc_type: debate_round_review
topic: search-space-expansion
round: {N}
author: {agent_name}
date: {YYYY-MM-DD}
status: OPEN
sources:
  - ./request.md
  - ./gemini_propone.md
  - ./codex_propone.md
  - ./claude_propone.md
  - ./chatgptpro_propone.md
  # Thêm sources khác nếu cần
tracking_rules:
  - Convergence Ledger là nguồn chân lý cho các điểm đã chốt.
  - Vòng sau chỉ bàn các mục trong Open Issues Register.
  - Muốn lật lại điểm đã khóa phải tạo REOPEN-* kèm bằng chứng mới.
  - Ý tưởng mới phải tạo NEW-* và giải thích vì sao issue hiện tại không bao phủ.
  - Không đổi ID cũ, không đánh số lại.
status_legend:
  CONVERGED: đã đủ chắc để không bàn lại.
  PARTIAL: cùng hướng lớn nhưng chi tiết chưa khóa.
  OPEN: còn tranh chấp thực chất.
  DEFER: có giá trị nhưng không nên là trọng tâm v1.
---

# Debate Round {N} — {Tiêu đề ngắn mô tả trọng tâm vòng này}

## 1. Kết luận nhanh

> 3-5 câu tóm tắt: chọn baseline nào, verdict ngắn cho từng agent,
> hướng đi chính sau vòng này.

---

## 2. Scoreboard

Chấm trên 6 trục, mỗi trục dùng thang: Yếu / Trung bình / Tốt / Rất tốt.

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | | | | | | | |
| Codex | | | | | | | |
| Claude | | | | | | | |
| ChatGPT Pro | | | | | | | |

**Giải thích 6 trục:**
1. **Bám yêu cầu**: giải đủ 2 tầng + gap + đề xuất bổ sung?
2. **Bám X38**: tôn trọng design brief, online/offline, Topic 017, firewall?
3. **Khả thi v1**: đưa vào draft/spec được mà không nổ scope?
4. **Sức mở search**: thực sự tăng xác suất "tai nạn tốt"?
5. **Kỷ luật contamination**: giữ Alpha-Lab là offline deterministic?
6. **Độ rõ artifact**: chỉ ra input-output-artifact-owner đủ để viết spec?

---

## 3. Convergence Ledger

> Chỉ các điểm đã đủ chắc. Vòng sau không bàn lại trừ khi có REOPEN-*.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | {điểm đã hội tụ} | {evidence/source} | CONVERGED | {ghi chú cho vòng sau} |

---

## 4. Open Issues Register

> Phần chính cho debate. Mỗi issue theo format dưới đây.

### OI-{NN} — {Tên câu hỏi}

**Các vị trí đang có**
- **Gemini**: {tóm tắt 1-2 câu}
- **Codex**: {tóm tắt 1-2 câu}
- **Claude**: {tóm tắt 1-2 câu}
- **ChatGPT Pro**: {tóm tắt 1-2 câu}

**Phán quyết vòng {N}**
{Nêu rõ đồng ý/bác bỏ gì, evidence pointer}

**Lý do**
{Lập luận cụ thể, có trích dẫn}

**Trạng thái**: OPEN / PARTIAL / CONVERGED / DEFER

**Điểm cần chốt vòng sau**
- {câu hỏi cụ thể 1}
- {câu hỏi cụ thể 2}

---

## 5. Per-Agent Critique

> Mỗi agent 1 card. Phản biện tấn công argument, không phải kết luận (§4).

### 5.{N} {Agent name}

**Luận điểm lõi**: {1-2 câu tóm tắt thesis}

**Điểm mạnh**
- {điểm mạnh + evidence pointer}

**Điểm yếu — phản biện lập luận**
- **Yếu điểm {N}: {tên}.**
  {Lập luận phản biện, kèm evidence pointer từ repo/spec/research.
  Phải tấn công argument, không phải kết luận.}

**Giữ lại**: {liệt kê ngắn}
**Không lấy**: {liệt kê ngắn + lý do}

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

{Mô tả backbone chọn, lý do}

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | | | |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | | | |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | |
| 017 | |
| 015 | |
| 013 | |
| 008 | |
| 003 | |

---

## 7. Agenda vòng sau

Chỉ bàn các OI-* còn OPEN hoặc PARTIAL.

**Format phản hồi cho agent vòng sau:**

```md
### OI-{NN}
- **Stance**: AGREE / DISAGREE / AMEND
- **Điểm đồng ý**: ...
- **Điểm phản đối**: ...
- **Đề xuất sửa**: ...
- **Evidence**: {file path hoặc finding ID}
```

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| {N} | {date} | {agent} | {mô tả ngắn} |
````

---

## Ghi chú bổ sung

### Vòng 2+: chỉ cập nhật delta

Vòng 2 trở đi, agent KHÔNG viết lại toàn bộ file. Chỉ cần:

1. Cập nhật **Kết luận nhanh** nếu thay đổi
2. Cập nhật **Scoreboard** nếu thay đổi
3. Di chuyển OI đã chốt → **Convergence Ledger**
4. Phản hồi các OI còn OPEN theo format ở §7
5. Thêm **NEW-*** nếu có issue mới (kèm lý do)
6. Thêm **REOPEN-*** nếu lật lại điểm đã khóa (kèm evidence mới)
7. Cập nhật **Change Log**

### REOPEN rule

Chỉ được reopen khi:
- Có bằng chứng mới từ repo/spec khiến kết luận cũ sai
- Có xung đột kiến trúc lộ ra khi draft spec
- Có phát hiện contamination/governance risk mà vòng trước chưa thấy
