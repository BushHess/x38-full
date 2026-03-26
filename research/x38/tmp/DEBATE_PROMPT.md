# NHIỆM VỤ: Debate vòng 6 — Search Space Expansion cho Alpha-Lab Framework

## BẠN LÀ: Claude Code

---

## BỐI CẢNH

Bốn agent (Gemini, Codex, Claude Code, ChatGPT Pro) đang tranh biện về cơ chế
khám phá thuật toán (search space expansion) cho Alpha-Lab Framework (x38).

Thư mục làm việc: /var/www/trading-bots/btc-spot-dev/research/x38

Yêu cầu gốc:
  docs/search-space-expansion/request.md

Bốn proposal ban đầu:
    docs/search-space-expansion/debate/gemini/gemini_propone.md
    docs/search-space-expansion/debate/codex/codex_propone.md
    docs/search-space-expansion/debate/claude/claude_propone.md
    docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md

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

Debate vòng 3:
    docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md
    docs/search-space-expansion/debate/codex/codex_debate_lan_3.md
    docs/search-space-expansion/debate/claude/claude_debate_lan_3.md
    docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md

Debate vòng 4:
    docs/search-space-expansion/debate/gemini/gemini_debate_lan_4.md
    docs/search-space-expansion/debate/codex/codex_debate_lan_4.md
    docs/search-space-expansion/debate/claude/claude_debate_lan_4.md
    docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md

Debate vòng 5:
    docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md
    docs/search-space-expansion/debate/codex/codex_debate_lan_5.md
    docs/search-space-expansion/debate/claude/claude_debate_lan_5.md
    docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_5.md

---

## ĐỌC BẮT BUỘC TRƯỚC KHI VIẾT

1. docs/search-space-expansion/template/DEBATE_FORMAT.md                — format đầu ra bắt buộc
2. docs/search-space-expansion/request.md                               — yêu cầu gốc
3. Bốn proposal ở trên                                                  — nội dung cần phản biện
4. Các debate files vòng trước từ cả 4 agents                           — nếu vòng 2+
5. docs/online_vs_offline.md                                            — offline/online invariant
6. docs/design_brief.md                                                 — thiết kế tổng quan
7. debate/rules.md                                                      — quy tắc tranh luận

---

## NHIỆM VỤ CỤ THỂ

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

## ĐẦU RA

Lưu vào file:
  docs/search-space-expansion/debate/claude/claude_debate_lan_6.md

---

## POST-DEBATE

1. Agent được chỉ định viết tài liệu tổng hợp tự chứa (self-contained synthesis).
2. Synthesis tuân theo format `final-resolution.md` của x38.
3. Đưa vào `debate/{NNN-slug}/` như topic thường, với:
   - 4-agent debate rounds = evidence (không debate lại)
   - Closure-audit bởi 1 x38 agent
4. Các OI bị DEFER → mở issue trong topic tương ứng hoặc topic mới.

---

## ĐIỀU KIỆN DỪNG

Khi TẤT CẢ OI-* đã chuyển sang CONVERGED hoặc DEFER ở cả 4 agents:
  → Debate kết thúc.
  → Nội dung Convergence Ledger + Interim Merge Direction của vòng cuối
    chính là kết luận chung.

## USE FOR CODEX

MULTI-AGENT REVIEW (lightweight):
Use a small review council on the SAME disagreement set.
- Lead Reviewer: drafts the main reply and owns final synthesis.
- Challenger: tests for wrong-target attacks, stale opponent modeling, false convergence, and missing counter-evidence.
- Evidence Checker: verifies that each citation supports the exact claim made and does not overreach.
- Rule Auditor: checks compliance with `debate/rules.md`, especially §§4, 7, 8, 11, 12.

Keep only claims that survive challenge, evidence check, and rule audit.
Do not include internal council dialogue in the final artifact.


ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` is the git root. Git root is `/var/www/trading-bots/btc-spot-dev/`.
