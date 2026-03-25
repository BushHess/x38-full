# Findings Under Review — Philosophy & Mission Claims

**Topic ID**: X38-T-07
**Opened**: 2026-03-22
**Split from**: Topic 000 (X38-T-00)
**Author**: claude_code (architect)

4 findings về triết lý nền tảng và mô hình claim. Kết luận tại đây là
prerequisite cho MỌI topic khác.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-07: "Full rediscovery automated" = aspiration, chưa fact
- C-08: 3-tier claim DIAGNOSIS hội tụ; naming cần debate
- C-10: F-01 cần operationalize qua firewall, không standalone
- C-12: Bounded recalibration prima facie bất tương thích với firewall

---

## F-01: Triết lý — kế thừa methodology, không kế thừa đáp án

- **issue_id**: X38-D-01
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0 (pre-debate)
- **current_status**: Converged

**Nội dung**:

Framework tuân theo triết lý: "kế thừa cách nghiên cứu, không kế thừa đáp án."

Cụ thể:
- Framework KHÔNG hứa "cho ra thuật toán tốt nhất" — hứa tìm candidate mạnh nhất
  TRONG search space đã khai báo, hoặc trung thực kết luận NO_ROBUST_IMPROVEMENT.
- `NO_ROBUST_IMPROVEMENT` là verdict hợp lệ ngang hàng với `INTERNAL_ROBUST_CANDIDATE`
  và `CLEAN_OOS_CONFIRMED` — không phải failure mode.
- "Tốt hơn online" = rộng hơn, reproducible hơn, ít contamination hơn, audit tốt hơn.
  KHÔNG phải "luôn cho ra thuật toán tốt hơn."

**Evidence**:
- RESEARCH_PROMPT_V6.md line 7-13 [extra-archive]: "The target is not a claim of global optimum."
- PROMPT_FOR_V7_HANDOFF.md line 56-59 [extra-archive]: search space là mở, không ưu tiên winner cũ.
- CONVERGENCE_STATUS_V3.md line 5 [extra-archive]: "có hội tụ ở cấp family, chưa hội tụ ở cấp exact winner."
- Human researcher verbal input (2026-03-18) [no file archive — decision_owner direct input]:
  "Nếu ép framework phải luôn ra thuật toán tốt nhất, sẽ đi ngược triết lý V4/V5/V6/V7."
- **V8 result (2026-03-19)** [extra-archive]: V8 winner (D1 momentum family) khác hoàn toàn
  V7 winner (D1 volatility clustering family). Governance tốt nhất
  (V8 protocol) vẫn KHÔNG đảm bảo exact winner convergence. Đây là constraint
  cơ bản: different procedurally-blind sessions produce different exact winners on same data.

**Câu hỏi mở**: Triết lý này có đủ rõ ràng? Có edge case nào mà nó gây hại?
V8 evidence strengthens F-01: even the best-governed session doesn't guarantee
winner stability, confirming "tìm candidate mạnh nhất TRONG search space" is the
correct framing.

---

## F-20: 3-tier claim separation — Mission / Campaign / Certification

- **issue_id**: X38-D-20
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from Claude Code ↔ Codex cross-audit)
- **current_status**: Converged

**Nội dung**:

x38 hiện tại có sự mơ hồ ngữ nghĩa giữa "tìm thuật toán tốt nhất" (mission),
"strongest internal leader" (campaign output), và "scientifically validated"
(clean OOS). Ba khái niệm này cần tách thành ba tầng claim rõ ràng:

| Tầng | Claim | Ai/Cái gì quyết định | Verdict cao nhất |
|------|-------|----------------------|------------------|
| **Mission** | Tìm thuật toán tốt nhất | Vòng lặp vô hạn NV1→NV2 | Không có verdict riêng — là mục tiêu dài hạn |
| **Campaign** | Strongest leader trong declared search space | x38 pipeline, convergence analysis | `INTERNAL_ROBUST_CANDIDATE` hoặc `NO_ROBUST_IMPROVEMENT` |
| **Certification** | Winner đã được xác nhận bằng independent evidence | Clean OOS (appended data) | `CLEAN_OOS_CONFIRMED` / `CLEAN_OOS_INCONCLUSIVE` / `CLEAN_OOS_FAIL` |

Tách này cho phép x38 giữ mission ambitious ("tìm cho bằng được thuật toán
tốt nhất") mà không overclaim ở campaign level. Campaign output
`INTERNAL_ROBUST_CANDIDATE` là verdict hợp lệ — nhưng rõ ràng chưa phải
certification.

**Hiện trạng trong x38**:
- PLAN.md:7-11 nói mission "tìm cho bằng được thuật toán trading tốt nhất"
- PLAN.md:209-214 nói framework chỉ hứa "candidate mạnh nhất TRONG search space"
- PLAN.md:451-475 phân biệt nghiên cứu (bắt buộc) vs Clean OOS (conditional)
- Nhưng ba tầng CHƯA được formalize thành semantic model rõ ràng

**Evidence**:
- PLAN.md:7-11, 45-49, 209-218, 451-475: sự mơ hồ hiện tại
- CONVERGENCE_STATUS_V3.md:5-10 [extra-archive]: hội tụ family nhưng chưa hội tụ exact
- PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-82 [extra-archive]: clean OOS ≠ internal evidence
- Claude Code ↔ Codex cross-audit (2026-03-21) → xem C-08
  (`../000-framework-proposal/findings-under-review.md:32`): cả hai đồng thuận
  tách này là cần thiết

**Câu hỏi mở**:
- Tên chính thức cho mỗi tầng? (Mission/Campaign/Certification? Hay thuật ngữ
  khác phù hợp hơn với x38?)
- Campaign verdict `INTERNAL_ROBUST_CANDIDATE` có cần thêm qualifier
  `FAMILY_CONVERGED_EXACT_UNRESOLVED` cho trường hợp archive exhausted?

---

## F-22: Phase 1 value classification on exhausted archives

- **issue_id**: X38-D-22
- **classification**: Judgment call
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from Claude Code ↔ Codex cross-audit)
- **current_status**: Converged

**Nội dung**:

Khi x38 Phase 1 chạy trên archive đã exhausted (BTC: V1-V8 + x0-x32 đã
touch toàn bộ file), Phase 1 tạo ra loại evidence nào?

Phân loại đề xuất:

| Loại evidence | Phase 1 tạo được? | Ví dụ |
|---------------|-------------------|-------|
| **Coverage/process evidence** | Có | "50K+ features scanned, all converge on D1 slow family" |
| **Deterministic convergence** | Có | "N deterministic sessions produce same leader" |
| **Clean adjudication evidence** | Không | Cần appended data (Phase 2) |

Coverage/process evidence có giá trị thật — nó xác nhận (hoặc bác bỏ) rằng
exhaustive scan tìm ra cùng family mà human-guided research đã tìm. Nhưng nó
KHÔNG thay thế clean adjudication.

**Tại sao cần formalize**: Nếu không rõ Phase 1 trên exhausted archive tạo
loại evidence nào, dễ overclaim "x38 đã xác nhận winner" khi thực tế chỉ có
coverage confirmation.

**Evidence**:
- PLAN.md:497-498: "Same-file methodological tightening cải thiện governance,
  KHÔNG tạo clean OOS evidence mới"
- CONVERGENCE_STATUS_V3.md:126-134 [extra-archive]: V8 có thể làm rõ family convergence,
  không thể làm rõ exact winner
- Claude Code ↔ Codex cross-audit (2026-03-21) → xem C-07, C-08
  (`../000-framework-proposal/findings-under-review.md:31-32`): converged trên
  phân loại này

**Câu hỏi mở**:
- Coverage confirmation có đủ để nâng campaign verdict từ
  `INTERNAL_ROBUST_CANDIDATE` lên sub-state nào? Hay verdict không đổi?
- Nếu exhaustive scan KHÔNG tìm ra cùng family (bất ngờ), đây là evidence
  mạnh hơn nhiều — cần protocol cho trường hợp này

---

## F-25: Regime-aware policy structure

- **issue_id**: X38-D-25
- **classification**: Judgment call
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from Claude Code ↔ Codex cross-audit)
- **current_status**: Converged

**Nội dung**:

x38 mission nói "tìm thuật toán tốt nhất" — ngầm giả định tồn tại MỘT
thuật toán thống trị. Nhưng nếu market có regime heterogeneity mạnh, có thể
không có single policy thắng tất cả regimes.

**Câu hỏi thiết kế**:

> Search space của x38 có cho phép một single frozen policy với explicit
> regime-aware structure (ví dụ: if regime=bull then strategy_A, if
> regime=chop then strategy_B), hay x38 chỉ chấp nhận stationary
> one-policy answer?

**Evidence từ lineage**:

- V8 protocol (RESEARCH_PROMPT_V8.md:469-475 [extra-archive]) **cấm** regime-specific
  parameter sets trong main scientific search
- Nhưng V8 **cho phép** layered policies (RESEARCH_PROMPT_V8.md:312 [extra-archive]) —
  miễn là chúng pass ablation paired evidence
- Pre-existing candidate [extra-archive] profits tất cả observed regimes →
  single policy IS viable trên observed data, nhưng không đảm bảo tương lai
- x38 PLAN.md chưa address câu hỏi này explicitly

**Hai hướng đề xuất**:

1. **Giữ V8 position**: search space chỉ chấp nhận single stationary policy.
   Regime conditioning forbidden. Đơn giản, ít overfit risk, consistent với
   btc-spot-dev regime analysis [extra-archive].
2. **Mở rộng**: cho phép single frozen policy WITH regime-aware structure,
   nhưng policy phải qua ablation gates chặt (regime-aware version phải BEAT
   stationary version trên PAIRED comparison). Flexibility cao hơn, overfit
   risk cao hơn.

**Câu hỏi mở**:
- Nếu cho phép regime-aware structure, ablation gate cần strictness nào?
- Regime classifier là PHẦN CỦA policy (đóng băng cùng strategy) hay là
  EXTERNAL input (framework cung cấp)?
- Nếu regime-aware policy thắng stationary policy trên exhaustive scan nhưng
  THUA trên Clean OOS, đó là overfit evidence hay regime-shift evidence?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 001 (campaign-model) | X38-D-03 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be valid exit | 001 owns decision |
| 002 (contamination-firewall) | X38-D-04 | C-10: F-01 operationalization depends on firewall | 002 owns decision |
| 003 (protocol-engine) | X38-D-05 | F-25 regime prohibition constrains protocol stages | 003 owns decision |
| 004 (meta-knowledge) | MK-17 | MK-17 shadow-only prerequisite for F-01 interpretation. CLOSED | shared — see C-02 |
| 010 (clean-oos-certification) | X38-D-12, X38-D-21 | F-22 + F-20 define Phase 1 vs. Certification boundary | 010 owns decision |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-01 | Triết lý: kế thừa methodology, không đáp án | Judgment call | Converged (R2, 2026-03-23) |
| X38-D-20 | 3-tier claim separation: Mission / Campaign / Certification | Thiếu sót | Converged (R2, 2026-03-23) |
| X38-D-22 | Phase 1 value classification on exhausted archives | Judgment call | Converged (R3, 2026-03-23) |
| X38-D-25 | Regime-aware policy structure | Judgment call | Converged (R2, 2026-03-23) |
