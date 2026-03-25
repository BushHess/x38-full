======================================================================
PHASE 7: VALIDATION
======================================================================

Điều kiện: Phase 6 hoàn thành, ≥ 1 candidate specification.
Nếu Phase 5 ≠ GO hoặc Phase 6 bị SKIP → SKIP phase này.

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x27/prompte/phase_0.md
  Đọc deliverables Phase 6 (candidate specs, rejection criteria, expected behavior):
  - /var/www/trading-bots/btc-spot-dev/research/x27/06_design.md
  Đọc deliverables Phase 5 (go/no-go decision):
  - /var/www/trading-bots/btc-spot-dev/research/x27/05_go_no_go.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/
- Candidate specifications và rejection criteria từ Phase 6

Mục tiêu:
Implement, backtest, validate MỖI candidate NGHIÊM NGẶT.
KHÔNG thay đổi candidate specification. Report TẤT CẢ kể cả failures.

======================================================================
Protocol cho MỖI candidate:
======================================================================

1. IMPLEMENTATION
- Code strategy CHÍNH XÁC theo Phase 6 specification
- Code benchmark (VTREND) cho comparison
- Sanity checks:
  - Trade count phù hợp Phase 6 estimate (±30%)
  - Không lookahead (signal tại bar t chỉ dùng data đến t-1 hoặc t)
  - Cost applied correctly (50 bps RT mỗi trade)
  - Position sizing correct
  - No overlapping contradictory positions

2. FULL-SAMPLE BACKTEST
- Run candidate trên full data range
- Run benchmark trên cùng data range
- Metrics (CẢ candidate VÀ benchmark):
  Sharpe, CAGR, MDD, Calmar, trade count, win rate,
  exposure, avg holding period, max consecutive losses,
  profit factor, avg winner / avg loser
- Plots:
  - Equity curve: candidate vs benchmark overlay (Fig14)
  - Drawdown: candidate vs benchmark (Fig15)
  - Monthly return heatmap (Fig16)
  - Trade distribution: return per trade histogram (Fig17)
- Apply pre-committed rejection criteria từ Phase 6
- Nếu BẤT KỲ criterion nào FAIL → ghi REJECT, vẫn report nhưng mark

3. WALK-FORWARD OPTIMIZATION (WFO)
- 4 folds minimum, anchored expanding window
- Nếu candidate có tunable parameters:
  - Train: optimize trên in-sample
  - Test: apply to out-of-sample
- Nếu fixed parameters (no tuning):
  - Each fold: compute metrics on test segment
- Report per fold:
  - In-sample Sharpe, OOS Sharpe
  - Delta vs benchmark (OOS)
  - Trade count in OOS
- WFO win rate = folds with positive delta / total folds
- Bar chart: per-fold delta (Fig18)
- Gate: WFO win rate ≥ 50%

4. BOOTSTRAP VALIDATION
- Method: circular block bootstrap (block size ~ sqrt(N))
  hoặc stationary bootstrap (Politis & Romano)
- n_paths = 2000
- Mỗi path: compute candidate Sharpe VÀ benchmark Sharpe
- d_sharpe = candidate - benchmark
- Report:
  - P(candidate_sharpe > 0): probability alpha is real
  - P(d_sharpe > 0): probability candidate beats benchmark
  - Median d_sharpe, 5th/95th percentile
  - Distribution histogram (Fig19)
- Gate: P(candidate_sharpe > 0) ≥ 70%

5. ROBUSTNESS CHECKS
(a) Jackknife: remove 1/6 of data chronologically × 6 folds
    - Re-compute all metrics
    - Gate: ≤ 1 fold with Sharpe < 0

(b) Cost sensitivity: run at 15, 30, 50, 75, 100 bps RT
    - At what cost does candidate Sharpe drop below 0?
    - At what cost does candidate lose to benchmark?
    - Table: cost × metrics (Tbl_cost_sensitivity)
    - Curve: Sharpe vs cost (Fig20)

(c) Regime split: identify bull/bear from D1 data
    - Run candidate separately in each regime
    - Does it work in both? Or only one? (note but don't auto-reject)

(d) Year-by-year performance
    - Annual Sharpe, CAGR for each calendar year
    - Any years with catastrophic loss?

6. CHURN ANALYSIS (verify H_prior_4)
- Count churn events: exit → re-entry within 10 bars
- Churn rate: as % of total trades
- Cost of churn: total cost attributable to churn cycles
- Compare with benchmark churn rate

7. VERDICT (mỗi candidate, chọn MỘT):

PROMOTE — All gates pass:
  - Full-sample metrics beat rejection criteria
  - WFO win rate ≥ 50%
  - Bootstrap P(sharpe > 0) ≥ 70%
  - Jackknife ≤ 1 negative fold
  - No catastrophic annual loss

HOLD — Most gates pass, 1-2 borderline:
  - Note which gates borderline
  - May promote with more data

REJECT — Multiple gates fail:
  - Note which gates fail and by how much

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x27/):
======================================================================
- 07_validation.md
- code/phase7_validation.py (complete, runnable)
- figures/Fig14–Fig20+ (equity, drawdown, heatmap, bootstrap, WFO, cost)
- tables/:
  - Tbl_full_sample_comparison (candidate vs benchmark)
  - Tbl_wfo_results (per-fold)
  - Tbl_bootstrap_summary
  - Tbl_cost_sensitivity
  - Tbl_jackknife
  - Tbl_yearly_performance
  - Tbl_churn_comparison
- manifest.json cập nhật

======================================================================
Cấm:
======================================================================
- KHÔNG thay đổi candidate spec sau khi bắt đầu
  (muốn thay → quay Phase 6, Cand## mới)
- KHÔNG cherry-pick metrics
- KHÔNG hide failures
- KHÔNG re-optimize parameters trên full sample rồi claim "default"
- KHÔNG chạy thêm candidates ngoài Phase 6 spec
- Report EVERYTHING — kể cả khi candidate tệ hơn benchmark
