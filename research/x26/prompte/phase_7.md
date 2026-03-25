PREPEND PROMPT 0 tại: /var/www/trading-bots/btc-spot-dev/research/prompte/phase_0.md
======================================================================

Bạn đang ở PHASE 7: VALIDATION.

Điều kiện tiên quyết: Phase 6 hoàn thành, ít nhất 1 candidate specification
Nếu Phase 5 gate ≠ GO hoặc Phase 6 bị SKIP, phase này cũng SKIP.

Đầu vào:
- Tất cả artifacts từ Phase 1–6
- Candidate specifications từ Phase 6

Mục tiêu:
Validate MỖI candidate nghiêm ngặt. Code, run, evaluate.

Protocol cho MỖI candidate:

1. Implementation
- Code strategy CHÍNH XÁC theo specification từ Phase 6
- Không sửa đổi rules hay parameters
- Verify:
  - Trade count phù hợp với Phase 6 estimate
  - Signal timing correct (no lookahead)
  - VTREND integration rules correct (priority, capital, conflicts)
  - Cost model applied correctly (50 bps RT)
- Sanity checks:
  - Trades only during FLAT periods (nếu design specifies)
  - No overlapping positions beyond specification
  - Cash balance never negative

2. Full-sample standalone backtest (new strategy only)
- Metrics: Sharpe, CAGR, MDD, Calmar, trade count, win rate,
  exposure, avg trade duration, max consecutive losses
- Equity curve plot
- Drawdown plot
- Monthly return heatmap
- Gate: standalone Sharpe > 0 (new strategy has positive EV)

3. Combined system backtest (VTREND + new)
- Run VTREND E5+EMA21D1 + new strategy simultaneously
- Apply integration rules từ Phase 6 (priority, capital allocation)
- Metrics: same as above cho combined system
- Comparison table: VTREND-only vs Combined
- Gate: combined Sharpe > VTREND-only Sharpe

4. Walk-Forward Optimization (WFO)
- 4 folds minimum, anchored expanding window
- If new strategy has tunable parameters:
  - Train: optimize on in-sample
  - Test: apply best params to out-of-sample
- If no tunable parameters (fixed defaults):
  - Each fold: compute combined delta vs VTREND-only
- Report:
  - Per-fold: in-sample Sharpe, OOS Sharpe, delta vs VTREND-only
  - WFO win rate = fraction of folds with positive delta
- Gate: WFO win rate ≥ 50% (at least half the folds improve)

5. Bootstrap validation (VCBB)
- Import from research/lib/vcbb.py: gen_path_vcbb
- n_paths = 2000
- Compute for each path:
  - VTREND-only Sharpe
  - Combined Sharpe
  - d_sharpe = combined - VTREND-only
- Report:
  - Distribution of d_sharpe (histogram)
  - P(d_sharpe > 0)
  - Median d_sharpe
  - 5th and 95th percentile of d_sharpe
- Gate: P(d_sharpe > 0) ≥ 60%

6. PSR gate
- Compute PSR cho combined system
- DOF correction: Nyholt M_eff (from research/lib/effective_dof.py) nếu applicable
- Gate: PSR ≥ 0.95

7. Robustness checks
- Jackknife: remove each 1/6 of data chronologically, re-compute.
  Gate: ≤ 1 fold with negative delta
- Cost sensitivity: run combined system at 15, 30, 50, 75, 100 bps RT
  - Report: at which cost does new strategy stop adding value?
- Regime split: bull (D1 close > D1 EMA(200)) vs bear
  - Does new strategy help in both regimes?
  - Or only in one? (acceptable but note it)

8. Verdict cho MỖI candidate:

PROMOTE: ALL gates pass
- Standalone Sharpe > 0
- Combined > VTREND-only
- WFO ≥ 50%
- Bootstrap P(d > 0) ≥ 60%
- PSR ≥ 0.95
- Jackknife ≤ 1 negative

HOLD: Most gates pass, 1-2 borderline
- Note which gates are borderline
- May promote with more data

REJECT: Multiple gates fail
- Note which gates fail
- Explain why

Deliverables bắt buộc:
- research/beyond_trend_lab/07_validation.md
- research/beyond_trend_lab/code/phase7_validation.py
- Figures:
  - Equity curves (standalone + combined + VTREND-only overlay)
  - Drawdown plots
  - Monthly return heatmaps
  - Bootstrap d_sharpe histogram
  - WFO per-fold bar chart
  - Cost sensitivity curve
- Tables:
  - Full metrics comparison (VTREND-only vs Combined vs Standalone)
  - WFO fold-by-fold results
  - Bootstrap summary statistics
  - Cost sensitivity table
  - Jackknife results
- manifest.json cập nhật

Cấm:
- KHÔNG thay đổi candidate specification sau khi bắt đầu validation
  (nếu muốn thay đổi → quay lại Phase 6, new Cand## ID)
- KHÔNG cherry-pick metrics
- KHÔNG chỉ report favorable results — report TẤT CẢ bao gồm failures
- KHÔNG re-optimize parameters on full sample rồi claim đó là "default"
