# Findings Under Review — Convergence Analysis

**Topic ID**: X38-T-13
**Opened**: 2026-03-22
**Author**: claude_code (architect)

2 findings về framework đo lường convergence và stop conditions.

**Issue ID prefix**: `X38-CA-` (Convergence Analysis).

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-04: x38 hiện KHÔNG có bounded recalibration path

---

## F-30: Convergence measurement framework

- **issue_id**: X38-CA-01
- **classification**: Thiếu sót
- **opened_at**: 2026-03-22
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

F-03 (Campaign Model) nói "convergence analysis chéo giữa sessions" nhưng **không
định nghĩa thuật toán** để đo convergence. V4→V8 cho thấy 5 sessions, 5 winners
khác family — research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md [extra-archive] kết luận "hội tụ ở family level, phân kỳ ở
exact winner". Nhưng kết luận này dựa trên human judgment, không phải metric.

Framework cần **convergence algorithm** cụ thể, bao gồm:

**1. Cấp độ so sánh (granularity)**:
- Family-level: sessions đồng ý trên cùng strategy family? (e.g., 4/5 chọn
  momentum-based → converged at family)
- Architecture-level: cùng family nhưng khác cấu trúc? (e.g., layered vs single)
- Parameter-level: cùng architecture, khác params? (e.g., slow=A vs slow=B)
- Performance-level: khác winner nhưng Sharpe distribution overlap? (winners khác
  nhau nhưng equivalent về performance)

V4→V8 evidence: family-level divergence (D1 efficiency, H4 momentum, D1 volatility
clustering, D1 momentum). Chỉ converge ở "D1 slow" — rất thô. Framework cần
metric chặt hơn.

**2. Distance metric**:
- Winner identity agreement (voting: K/N sessions chọn cùng winner)
- Sharpe distribution overlap (bootstrap: P(winner_A > winner_B) across sessions)
- Top-K overlap (Jaccard index giữa top-K candidates của mỗi session)
- Rank correlation (Spearman ρ giữa candidate rankings across sessions)

**3. Statistical test**:
- Bootstrap comparison: sessions produce Sharpe distributions → test overlap
- Permutation test: null = sessions interchangeable → p-value cho divergence
- Majority voting: K/N threshold → binary converged/not-converged

**4. Multi-level convergence**:
V4→V8 cho thấy convergence có thể xảy ra ở levels khác nhau:
- Converge family (D1 slow) nhưng diverge exact winner → PARTIALLY_CONVERGED
- Converge cả family + params → FULLY_CONVERGED
- Diverge family → NOT_CONVERGED

Framework cần hỗ trợ partial convergence — không chỉ binary.

**Evidence**:
- research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md [extra-archive]: 5 sessions diverge ở exact winner,
  partial convergence ở "D1 slow" family
- x38 F-03: "convergence analysis" mentioned nhưng không defined
- x38 F-15: metric scoping (session vs campaign vs cross-campaign) ảnh hưởng
  cách đo convergence

**Câu hỏi mở**:
- Nên đo convergence ở granularity nào? Tất cả levels hay chỉ family-level?
- Distance metric nào phù hợp cho offline pipeline (reproducible, deterministic)?
- PARTIALLY_CONVERGED đủ để chuyển sang Clean OOS? Hay phải FULLY_CONVERGED?
- Convergence metric có cần asset-agnostic không? (BTC có ít families; equities
  có thể có hàng trăm)

---

## F-31: Stop conditions & diminishing returns detection

- **issue_id**: X38-CA-02
- **classification**: Thiếu sót
- **opened_at**: 2026-03-22
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

F-03 đặt câu hỏi mở "stop conditions: bao nhiêu NO_ROBUST trước khi dừng?"
nhưng chưa có framework. Hai vấn đề cần giải quyết:

**1. Khi nào dừng thêm sessions (within-campaign)?**

Mỗi session mới tiêu tốn compute và thời gian. Cần cơ chế detect khi session
thứ N+1 không thêm thông tin mới:

- **Information gain**: session mới thay đổi convergence metric bao nhiêu?
  Nếu Δ(convergence) < ε → diminishing returns
- **Novel candidate rate**: session mới có tìm ra candidates ngoài top-K
  của sessions trước? Nếu top-K stable qua 3 sessions liên tiếp → stop
- **Winner stability**: winner thay đổi hay giữ nguyên? Nếu giữ nguyên
  qua M sessions → converged

**2. Khi nào dừng campaigns (cross-campaign)?**

Same-file campaigns chạy trên cùng data → diminishing returns tự nhiên.
V4→V8 evidence: 5 sessions chạy, 4 sessions cuối có governance improvements
nhưng winner vẫn khác. Cần tiêu chí rõ ràng:

- **Same-data ceiling**: trên cùng dataset, bao nhiêu campaigns đủ?
  V4→V8 cho thấy 5 sessions → PROMPT_FOR_V8_HANDOFF [extra-archive] dừng lại.
  Trần mặc định là bao nhiêu? Vượt trần cần human override.
- **Methodology exhaustion**: campaigns mới chỉ thay đổi methodology (MK-17).
  Nếu methodology changes giảm → space đã exhausted
- **NO_ROBUST_IMPROVEMENT policy**: output hợp lệ (F-03), nhưng khi nào
  thì framework nên chấp nhận nó thay vì thêm campaign?

**3. Interaction với MK-17 (shadow-only)**:

MK-17 quy định: trên cùng dataset, empirical priors là shadow-only. Nghĩa là:
- Campaign C2 trên cùng data ≈ thêm batch sessions (không có real meta-learning)
- Diminishing returns đến NHANH hơn vì sessions gần như independent
- Stop condition cần account cho điều này: same-data campaigns có trần thấp
  hơn new-data campaigns

**Evidence**:
- V4→V8: 5 sessions, cuối cùng dừng bằng human judgment (research/x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md:62
  [extra-archive]: same-file iteration có giới hạn)
- x38 F-03: stop conditions là câu hỏi mở
- x38 F-16: gen4 cooldown 180d — không áp dụng offline nhưng concept tương tự
- MK-17 (topic 004, RESOLVED): shadow-only trên same dataset

**Câu hỏi mở**:
- Trần mặc định sessions per campaign? (3? 5? adaptive?)
- Trần mặc định same-data campaigns? (2? 3?)
- ε threshold cho diminishing returns: fixed hay relative?
- Ai quyết định vượt trần: human only hay framework có thể suggest?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01, ESP-04 | Coverage metrics in ESP overlap convergence measurement (CA-01). Budget governor coverage obligation interacts with campaign stop conditions (CA-02): coverage floor chưa đạt → extend campaign? | 013 owns convergence metrics and stop conditions; 017 defines coverage obligations for budget governor. |
| 018 | SSE-09, SSE-04-THR | Scan-phase correction law + equivalence/anomaly thresholds routed from Topic 018 (REOPENED). Provisional until 018 re-closes under standard 2-agent debate. | 013 owns implementation; 018 provides architectural context (provisional). |
| 008 | SSE-04-IDV | 013's equivalence thresholds (SSE-04-THR) must be compatible with 008's identity vocabulary (SSE-04-IDV) — both are components of SSE-D-04 7-field contract field 3+4. | 008 owns identity vocabulary interface; 013 owns semantic equivalence rules. |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-CA-01 | Convergence measurement framework | Thiếu sót | Open |
| X38-CA-02 | Stop conditions & diminishing returns | Thiếu sót | Open |
| X38-SSE-09 | Scan-phase correction law default (từ Topic 018) | Thiếu sót | Open |
| X38-SSE-04-THR | Equivalence + anomaly thresholds (từ Topic 018) | Thiếu sót | Open |

---

## Issues routed from Topic 018 — Search-Space Expansion (2026-03-26)

Architecture-level decisions proposed in Topic 018 (**REOPENED** 2026-03-26 —
prior 4-agent closure revoked; standard 2-agent debate required). These issues
represent implementation obligations contingent on Topic 018's re-closure.
Source: `debate/018-search-space-expansion/final-resolution.md` (provisional).

---

## SSE-D-09: Scan-phase correction law default

- **issue_id**: X38-SSE-09
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 0 (deferred from Topic 018, NEW-01 ChatGPT Pro)
- **current_status**: Open

**Nội dung**:

Topic 018 proposed (provisional): breadth-activation contract requires `scan_phase_correction_method`
declaration (SSE-D-04 field 5). Coupling between multiplicity control and breadth
expansion is locked.

Topic 013 owns:
1. Default correction formula (Holm/FDR/cascade/other)
2. Recommendation for v1 default
3. Threshold calibration methodology

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md` SSE-D-09
- `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` CL-13
- `docs/search-space-expansion/debate/claude/claude_debate_lan_5.md` CL-19 point 1

**Câu hỏi mở**:
- Holm (step-down) vs BH (FDR) vs cascade — which suits Alpha-Lab's false discovery risk profile?
- Should the default be conservative (Holm) or balanced (BH)?
- How does correction interact with cell-elite's diversity preservation?

---

## SSE-D-04/05: Equivalence + anomaly thresholds

- **issue_id**: X38-SSE-04-THR
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 0 (deferred from Topic 018, SSE-D-04/05)
- **current_status**: Open

**Nội dung**:

Topic 018 proposed (provisional): hybrid equivalence (structural pre-bucket + behavioral
nearest-rival) and 5 anomaly axes for surprise queue admission.

Topic 013 owns:
1. Behavioral equivalence distance threshold (paired-return ρ cutoff)
2. Structural hash granularity for pre-bucketing
3. Robustness bundle minimum requirements (what "minimum" means numerically)
4. Shared with 017: anomaly axis thresholds (what counts as "outlier" on each axis)

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md` SSE-D-04 field 4, SSE-D-06
- `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` CL-19 fields 4/6

**Câu hỏi mở**:
- ρ > 0.95 or ρ > 0.99 for behavioral equivalence?
- How does the structural pre-bucket interact with 006's feature family taxonomy?
- Are anomaly thresholds absolute or relative to cell population?
