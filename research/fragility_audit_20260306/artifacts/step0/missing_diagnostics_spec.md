# Missing Diagnostics Specification — Step 0

## Overview

17 diagnostics are needed. 6 are partially covered (E5_plus gap). 11 are fully missing.
Grouped by implementation complexity and replay dependency.

---

## Group 1: Ledger-Only Diagnostics (no replay needed)

### 1.1 Winning Streaks (E5_plus_EMA1D21 gap fill)

- **Diagnostic name**: winning_streaks
- **Objective**: Complete T2 streak analysis for E5_plus_EMA1D21
- **Target ledger view**: Fill Ledger
- **Scope**: Full backtest
- **Required input fields**: `trade_id`, `return_pct` (or `pnl_usd` for win/loss classification)
- **Formula**: Sequential scan of trades ordered by entry_ts; win = return_pct > 0; count consecutive wins; record max, mean, median streak lengths and number of streak runs
- **Convention**: win = return_pct > 0 (strict); loss = return_pct <= 0 (includes zero)
- **Ledger-only**: Yes
- **Reusable code**: `research/trade_profile_8x5.py` function `t2_streaks()`
- **Missing pieces**: Add E5_plus_EMA1D21 to STRATEGIES dict and rerun
- **Candidate applicability**: E5_plus_EMA1D21 (other 5 already READY)
- **Output artifacts**: Updated `summary_8x5.csv` row, `profile.json`
- **Acceptance**: E5_plus streak values present; cross-check max_win_streak <= n_trades

### 1.2 E5_plus_EMA1D21 Full Trade Profile (T1-T8)

- **Diagnostic name**: e5_plus_trade_profile
- **Objective**: Compute all 8 trade-level techniques for the 6th candidate
- **Target ledger view**: Fill Ledger
- **Scope**: Full backtest
- **Required input fields**: All 22 columns from trades_candidate.csv + H4 bar data for MFE/MAE
- **Formula**: Same as trade_profile_8x5.py T1-T8
- **Ledger-only**: Yes (MFE/MAE uses bar data but not signal replay)
- **Reusable code**: Entire `research/trade_profile_8x5.py`
- **Missing pieces**: Add E5_plus_EMA1D21 trade path to STRATEGIES dict; optionally add `results/parity_20260306/eval_e5_ema21d1_vs_e0/results/trades_candidate.csv`
- **Candidate applicability**: E5_plus_EMA1D21
- **Output artifacts**: `results/trade_profile_8x5/E5_plus_EMA1D21/profile.json`, `mfe_mae_per_trade.csv`, `exit_reason_detail.json`, updated `summary_8x5.csv`
- **Acceptance**: All T1-T8 metrics present; trade count = 186; values in plausible ranges

### 1.3 Giveback Ratio

- **Diagnostic name**: giveback_ratio
- **Objective**: For each trade, measure how much of the maximum favorable excursion was surrendered before exit. Answers: "How much profit do we leave on the table?"
- **Target ledger view**: Fill Ledger + H4 bar data
- **Scope**: Full backtest
- **Required input fields**: `entry_ts_ms`, `exit_ts_ms`, `entry_price`, `exit_price`, `return_pct`, H4 OHLC bars
- **Formula**:
  ```
  peak_price = max(H4 highs during [entry_ts, exit_ts])
  MFE_pct = (peak_price - entry_price) / entry_price * 100
  realized_pct = return_pct  (already in CSV)
  giveback_pct = MFE_pct - realized_pct
  giveback_ratio = giveback_pct / MFE_pct  if MFE_pct > 0, else 0.0
  ```
- **Convention**: giveback_ratio in [0, 1+]. Ratio > 1 means exit below entry despite positive MFE. For losing trades where MFE > 0, giveback > realized.
- **Ledger-only**: Yes (uses H4 bars for peak, same as MFE computation)
- **Reusable code**: MFE computation from `trade_profile_8x5.py::compute_mfe_mae()`; extend to also compute giveback
- **Missing pieces**: Giveback column computation and aggregation (mean, median, P90 per strategy)
- **Candidate applicability**: All 6
- **Output artifacts**: Per-trade giveback column in mfe_mae CSV; summary stats per strategy
- **Acceptance**: giveback_ratio mean in [0.3, 0.9] range for trend-following; perfectly correlated with 1 - (realized/MFE) when MFE > 0

### 1.4 Top-N Absolute Contribution (formalization)

Already computed in trade_profile_8x5 as `t6_top_N_pnl_pct_of_total`. Formalize:

- **Diagnostic name**: top_n_absolute_contribution
- **Denominator convention (FROZEN)**: `contribution_pct = sum(pnl_usd for top-N trades) / sum(pnl_usd for all trades) * 100`. Denominator = total net PnL. Can exceed 100% when tail trades have negative aggregate PnL.
- **Alternative considered**: Using absolute PnL as denominator (sum(|pnl_usd|)). Rejected because the standard "% of total profit" convention is more interpretable for the home-run question.
- **Status**: READY for 5/6, MISSING for E5_plus_EMA1D21

### 1.5 Gini / HHI (formalization)

Already computed. Formalize:

- **Gini convention (FROZEN)**: Computed on `|pnl_usd|` per trade. Standard Lorenz curve formula. Range [0, 1].
- **HHI convention (FROZEN)**: `HHI = sum((|pnl_i| / sum(|pnl|))^2)`. Effective N = 1/HHI.
- **Status**: READY for 5/6, MISSING for E5_plus_EMA1D21

### 1.6 Skewness / Kurtosis / Jarque-Bera (formalization)

Already computed. Formalize:

- **Input**: `return_pct` per trade (unit-size view)
- **Skewness**: scipy.stats.skew (Fisher's definition, bias=True)
- **Kurtosis**: scipy.stats.kurtosis (excess, Fisher's definition, bias=True)
- **Jarque-Bera**: scipy.stats.jarque_bera
- **Status**: READY for 5/6, MISSING for E5_plus_EMA1D21

### 1.7 Skip-After-N-Consecutive-Losses

- **Diagnostic name**: skip_after_n_losses
- **Objective**: If a trader skips the next entry after seeing N consecutive losses, what happens to terminal wealth / Sharpe? Tests behavioral fragility.
- **Target ledger view**: Native Episode Ledger (ordered trades)
- **Scope**: Full backtest
- **Required input fields**: `trade_id`, `entry_ts`, `return_pct` (or `pnl_usd`), ordered by entry_ts
- **Formula/Protocol**:
  ```
  For N in {1, 2, 3, 4, 5}:
    Walk trades in order. Track consecutive loss count.
    When consecutive_losses >= N, skip the NEXT trade (mark it removed).
    Reset loss counter after a win or after a skip.
    Recompute Sharpe and sum(pnl_usd) from remaining trades.
  Report: {N, n_skipped, remaining_trades, remaining_pnl, remaining_sharpe, delta_sharpe_pct, delta_pnl_pct}
  ```
- **Convention**: Loss = return_pct <= 0. The skipped trade is NOT counted toward streak continuation.
- **Normalization**: Delta expressed as % change from baseline (skip-0).
- **Ledger-only**: Yes
- **Reusable code**: None directly; simple to implement from trade DataFrame
- **Missing pieces**: Full implementation
- **Candidate applicability**: All 6
- **Output artifacts**: CSV with rows per (candidate, N); summary table
- **Acceptance**: For N=1 (skip after every loss), number skipped should be significant fraction; Sharpe change should be documented; verify n_remaining + n_skipped = n_total

---

## Group 2: New Analytical Diagnostics (ledger-only, new implementation)

### 2.1 Sensitivity Curve (Top-Trade Removal)

- **Diagnostic name**: sensitivity_curve_top_removal
- **Objective**: Plot and tabulate how strategy performance degrades as the top K% of trades by absolute PnL are progressively removed. Identifies cliff-edges where a small number of trades disproportionately determine viability.
- **Target ledger view**: Fill Ledger (unit-size return_pct for fair comparison)
- **Scope**: Full backtest
- **Required input fields**: `trade_id`, `pnl_usd`, `return_pct`
- **Formula/Protocol**:
  ```
  Sort trades by pnl_usd descending.
  For removal_pct in np.arange(0, 21, 1):  # 0% to 20% in 1% steps
    K = ceil(n_trades * removal_pct / 100)
    Remove top-K trades.
    remaining_pnl = sum(pnl_usd for remaining trades)
    remaining_wealth = initial_cash + sum(pnl_usd for remaining)  # additive approx
    remaining_sharpe = annualized Sharpe from remaining return_pct series
    Record: {removal_pct, K, remaining_wealth, remaining_sharpe, remaining_cagr}
  ```
- **Denominator/normalization**: remaining_wealth relative to baseline (removal_pct=0). Express as fraction: `remaining_wealth / baseline_wealth`.
- **CAGR note**: CAGR from additive PnL approximation: `((initial + remaining_pnl) / initial)^(1/years) - 1`. This is an approximation since compounding is ignored, but acceptable for the sensitivity curve shape.
- **Cliff-edge**: A cliff-edge exists if the discrete second derivative of the remaining_wealth curve exceeds a threshold at some K. Formally: `|delta(remaining_wealth, K) - delta(remaining_wealth, K-1)| / delta(remaining_wealth, 1)` > 2.0 for some K in [1, ceil(0.2*n_trades)].
- **Ledger-only**: Yes
- **Reusable code**: Jackknife from trade_profile_8x5.py (t7) provides drop-top-K at discrete points; extend to continuous curve
- **Missing pieces**: Continuous curve generation; cliff-edge detection algorithm; plotting
- **Candidate applicability**: All 6
- **Output artifacts**: `sensitivity_curve.csv` (per candidate, 21 rows), `sensitivity_curve.png` (6 overlaid curves), `cliff_edge_summary.json`
- **Acceptance**: Curve is monotonically decreasing from removal_pct=0; values at removal_pct=0 match baseline; curve at K=top-5 matches trade_profile_8x5 t7_drop_top5 approximately (additive vs compounding will differ slightly)

### 2.2 Cliff-Edge Detection

- **Diagnostic name**: cliff_edge_detection
- **Objective**: Automatically identify whether the sensitivity curve has a sharp "cliff" — a small number of trades whose removal causes disproportionate damage.
- **Target ledger view**: Fill Ledger
- **Scope**: Full backtest
- **Required input fields**: Output of sensitivity_curve diagnostic
- **Formula**:
  ```
  deltas[k] = remaining_wealth[k] - remaining_wealth[k-1]  for k = 1..K_max
  avg_delta = mean(|deltas|)
  cliff_score[k] = |deltas[k]| / avg_delta
  cliff_detected = any(cliff_score[k] > 3.0)
  cliff_trade_id = trade at position k in the sorted-by-PnL list where cliff_score is max
  ```
- **Convention**: cliff_score > 3.0 means that removing trade k causes 3x the average per-trade damage. Threshold of 3.0 is a working default.
- **Ledger-only**: Yes (derived from sensitivity curve)
- **Reusable code**: Sensitivity curve output
- **Missing pieces**: Cliff detection algorithm
- **Candidate applicability**: All 6
- **Output artifacts**: `cliff_edge_summary.json` per candidate with {cliff_detected, max_cliff_score, cliff_trade_id, cliff_removal_pct}
- **Acceptance**: If max single-trade PnL > 20% of total, cliff_detected should be True

---

## Group 3: Signal-Replay Diagnostics (require backtest re-execution)

### 3.1 Missed-Entry Sensitivity (1, 2, 3 random misses)

- **Diagnostic name**: missed_entry_N (N=1,2,3)
- **Objective**: If the trader misses N random entries (e.g., sleeping, exchange down), what is the distribution of resulting Sharpe/CAGR/terminal wealth? Measures operational fragility to random unavailability.
- **Target ledger view**: Native Episode Ledger (for identifying which entries to skip)
- **Scope**: Full backtest
- **Required input fields**: Full trade list with entry_ts, return_pct, pnl_usd
- **Protocol**:
  ```
  For each trial in range(n_trials):  # n_trials = 1000
    Randomly sample N trades to skip (without replacement)
    Compute remaining Sharpe and remaining total PnL from non-skipped trades
  Report: distribution of remaining_sharpe across trials
    - mean, median, P5, P95 of remaining_sharpe
    - probability that remaining_sharpe < 0
    - probability that remaining_sharpe < 0.5 * baseline_sharpe
  ```
- **Alternative approach**: If trades are independent (no path-dependency), this can be done from the ledger alone by combinatorial resampling. If sizing is NAV-dependent (compounding), this requires full replay. **For the existing trade CSV where pnl_usd is recorded at the time-of-trade NAV, the ledger-only approach is an approximation.** The approximation is acceptable for N=1,2,3 because the removed trades are a tiny fraction.
- **Recommendation**: Use ledger-only approach first (combinatorial removal); flag if replay is needed later.
- **Ledger-only**: Yes (approximate, acceptable for small N)
- **Reusable code**: Jackknife from trade_profile_8x5 (for N=1 this is exactly drop-random-1)
- **Missing pieces**: Monte Carlo random removal loop; distribution summary
- **Candidate applicability**: All 6
- **Output artifacts**: `missed_entry_summary.csv` with rows per (candidate, N, statistic)
- **Acceptance**: P(Sharpe<0) should be very small for N=1; distribution should be tighter than jackknife-top-N (random miss is less damaging than worst-case miss)

### 3.2 Outage-Window Miss Sensitivity

- **Diagnostic name**: outage_window_miss
- **Objective**: If the exchange is down for a contiguous window of W hours, and all entries during that window are missed, how much damage? Tests vulnerability to scheduled maintenance or extended outages.
- **Target ledger view**: Native Episode Ledger
- **Scope**: Full backtest
- **Required input fields**: `entry_ts_ms`, `return_pct`, `pnl_usd`
- **Protocol**:
  ```
  For W in {4, 8, 24, 48, 168} hours:
    For each possible window start (slide by 4h = 1 bar):
      Identify trades whose entry_ts_ms falls within [start, start + W*3600*1000)
      Remove those trades
      Compute remaining_sharpe and remaining_pnl
    Report: distribution over all window placements
      - worst_case_sharpe, worst_case_pnl_loss
      - mean_sharpe, P5_sharpe
      - worst_window_start_ts
  ```
- **Convention**: Only entries are checked (not exits). An entry missed means the entire trade is skipped.
- **Ledger-only**: Yes (approximate, same caveat as missed-entry)
- **Reusable code**: Entry timestamp filtering
- **Missing pieces**: Sliding window loop; worst-case identification
- **Candidate applicability**: All 6
- **Output artifacts**: `outage_sensitivity.csv` per (candidate, W); `outage_worst_case.json`
- **Acceptance**: Worst-case 168h outage should produce meaningful Sharpe degradation; worst-case windows should cluster around major trend reversal periods

### 3.3 Delayed-Entry Sensitivity

- **Diagnostic name**: delayed_entry
- **Objective**: If every entry is delayed by D bars (1, 2, 3 H4 bars = 4, 8, 12 hours), how much does performance degrade? Tests sensitivity to execution latency.
- **Target ledger view**: Requires signal/bar replay
- **Scope**: Full backtest
- **Required input fields**: Full bar data + strategy signal logic
- **Protocol**: Re-run backtest with entry delayed by D bars. Entry price becomes the close of entry_bar + D. Exit logic unchanged.
- **Ledger-only**: **No** — requires actual backtest re-execution because delayed entry changes the entire subsequent trade trajectory (different entry price, different trail levels, potentially different exit bar).
- **Reusable code**: `validate_strategy.py` framework can rerun backtests; would need a delay parameter injected
- **Missing pieces**: Entry-delay injection into backtest engine; multi-delay sweep
- **Candidate applicability**: All 6
- **Output artifacts**: `delayed_entry_sweep.csv` per (candidate, D bars)
- **Acceptance**: Performance should degrade monotonically with D; 1-bar delay should cause < 10% Sharpe degradation for a robust strategy

---

## Implementation Priority

| Priority | Diagnostic | Complexity | Dependencies |
|----------|-----------|------------|--------------|
| P0 | E5_plus trade profile (1.2) | Low | Rerun existing script |
| P1 | Giveback ratio (1.3) | Low | Extend MFE computation |
| P1 | Sensitivity curve (2.1) | Medium | New code, ledger-only |
| P1 | Cliff-edge detection (2.2) | Low | Derives from 2.1 |
| P1 | Skip-after-N-losses (1.7) | Low | New code, ledger-only |
| P2 | Missed-entry (3.1) | Medium | Monte Carlo, ledger-only approx |
| P2 | Outage-window (3.2) | Medium | Sliding window, ledger-only approx |
| P3 | Delayed-entry (3.3) | High | Requires backtest engine modification |
