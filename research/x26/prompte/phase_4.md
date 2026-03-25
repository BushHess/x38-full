PREPEND PROMPT 0 tại: /var/www/trading-bots/btc-spot-dev/research/prompte/phase_0.md
======================================================================

Bạn đang ở PHASE 4: FORMALIZATION.

Đầu vào:
- Tất cả artifacts từ Phase 1–3
- Top phenomena từ scoring matrix

Mục tiêu:
Formalize decision problem cho phenomenon(a) đã chọn.
Derive admissible function classes từ evidence — KHÔNG từ ký ức.

Cấu trúc bắt buộc:

1. Decision problem
- Định nghĩa chính xác:
  - Signal event: khi nào opportunity phát sinh?
  - Action space: a_t ∈ {0, 1} (take / skip)? Hay continuous sizing?
  - Utility function: ΔU_t phụ thuộc gì?
- Utility PHẢI account for VTREND interaction:
  - Additive: U_combined = U_vtrend + U_new (nếu non-overlapping)
  - Conditional: U_new chỉ active khi VTREND flat
- Cost model: 50 bps RT per trade cho strategy mới
- Cash opportunity cost: nếu new strategy occupies capital,
  VTREND có thể miss entry → phải model conflict

2. Information set
- V_new: information available tại signal time từ phenomenon
- P_t: price information đã available
- VT_t: VTREND state (FLAT / IN_TRADE) — đây LÀ observable
- Central question: I(ΔU_new ; V_new | P_t, VT_t) > 0?
- Estimate bằng evidence từ Phase 2–3 (effect sizes, correlations)

3. Propositions
- Derive từ observations
- Mỗi proposition phải trỏ về ≥ 1 Observation
- Viết rõ confidence level: HIGH / MEDIUM / LOW
- Ghi rõ nếu proposition dựa trên phenomenon gần threshold

4. Admissible function classes
- Derive từ evidence + constraints
- Mỗi class phải có:
  - Mathematical form
  - DOF count (tối đa 3)
  - Why admissible (evidence reference)
  - Known caveats
- Tối đa 3 classes

5. Rejected function classes
- Mỗi rejection phải có evidence reference
- Bao gồm: classes đã biết fail từ prior research
  (reference specific study: X11, X20, X21, entry_filter_lab, etc.)

6. Power analysis
- MDE cho mỗi admissible class
- N of opportunities per year
- Total N over full sample
- WFO fold sizes
- Effect size vs MDE comparison
- Explicit statement: POWERED / BORDERLINE / UNDERPOWERED

7. Complementarity proof
- Show analytically hoặc empirically:
  new strategy does not degrade VTREND
- Compute: % of new-strategy signals during VTREND FLAT
- Compute: expected timing overlap (simultaneous positions)
- If overlap > 10%: address capital allocation and conflict resolution

Deliverables bắt buộc:
- research/beyond_trend_lab/04_formalization.md
- Code nếu cần cho power analysis, complementarity computation
- Tables nếu cần

Cấm:
- Không propose candidates (chỉ CLASSES)
- Không nhớ ra strategy quen thuộc rồi justify
- Derive từ data, không từ literature
- Không skip power analysis — nó quyết định feasibility
