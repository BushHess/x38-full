PREPEND PROMPT 0 tại: /var/www/trading-bots/btc-spot-dev/research/prompte/phase_0.md
======================================================================

Bạn đang ở PHASE 6: DESIGN.

Điều kiện tiên quyết: Phase 5 gate = GO_TO_DESIGN
Nếu Phase 5 gate ≠ GO, phase này bị SKIP.

Đầu vào:
- Tất cả artifacts từ Phase 1–5
- Phenomenon, function class, và power analysis từ Phase 4–5

Mục tiêu:
Thiết kế candidate strategy cụ thể, minimal, testable.

Cấu trúc bắt buộc:

1. Candidate specification
- Mỗi candidate phải có:
  - Cand## ID
  - Exact mathematical formula / decision rule
  - All parameters with DEFAULT values (chưa optimize)
  - DOF count
  - Provenance chain: Cand## ← Prop## ← Obs## ← Fig##
- Tối đa 3 candidates (tránh multiple-testing penalty lớn)
- Mỗi candidate ≤ 3 free parameters

2. Parameter selection rationale
- Mỗi parameter: TẠI SAO giá trị default này?
- Phải dựa trên evidence:
  e.g., "lookback = 20 vì ACF decays to insignificant ở lag ~20 (Obs##)"
- KHÔNG dùng "common in literature" hay "industry standard" làm lý do
- Nếu không có evidence cho default → chọn trung điểm của admissible range

3. Integration with VTREND
- Rule set cụ thể:
  - Khi VTREND IN_TRADE: new strategy off? reduced? independent?
  - Khi VTREND FLAT: new strategy eligible
  - Capital: f_vtrend + f_new ≤ 1.0
  - Conflict resolution: nếu new strategy đang active VÀ VTREND triggers entry → ?
    (Recommend: VTREND priority — close new position, take VTREND)

4. Expected behavior (pre-backtest estimates)
- Estimated trade count (from phenomenon frequency in data)
- Estimated exposure (% of total time, % of FLAT time)
- Estimated mean return per trade (from effect size)
- Estimated ΔSharpe (from power analysis)
- What kind of trades: duration, frequency, win rate range

5. Backtest specification (cho Phase 7)
- Data range: full sample (2017-08 → 2026-02)
- Cost model: 50 bps RT per trade
- Metrics: Sharpe, CAGR, MDD, Calmar, trade count, win rate,
  exposure, avg trade duration
- Combined system: VTREND + new strategy running simultaneously
- WFO setup:
  - Minimum 4 folds, anchored expanding window
  - Train: optimize adjustable parameters (if any)
  - Test: out-of-sample performance
  - Win criterion: combined Sharpe > VTREND-only Sharpe in fold
- Bootstrap setup: VCBB, n_paths=2000
- PSR gate: ≥ 0.95, DOF-corrected

6. Pre-committed rejection criteria
- Define TRƯỚC KHI backtest những gì sẽ REJECT candidate:
  - Combined Sharpe < VTREND-only Sharpe (new strategy HURTS)
  - WFO win rate < 50%
  - Bootstrap P(d_sharpe > 0) < 55%
  - PSR < 0.90
  - Trade count < 20 (insufficient sample)
  - New strategy standalone Sharpe < 0 (negative EV)
- Ghi rõ: "nếu bất kỳ criterion nào fail → REJECT"

Deliverables bắt buộc:
- research/beyond_trend_lab/06_design.md
- Candidate specification sheets (mỗi candidate: exact rules, parameters, provenance)

Cấm:
- Không backtest trong phase này — chỉ design
- Không tune parameters — chỉ set defaults từ evidence
- Không thêm "just in case" features
- Mỗi candidate phải justify MỌI parameter từ evidence
