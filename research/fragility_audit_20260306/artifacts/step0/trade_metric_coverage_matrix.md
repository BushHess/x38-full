# Trade Metric Coverage Matrix — Step 0 Audit

## Status Legend
- **READY**: Canonical artifact exists, reconciled, directly usable
- **PARTIAL**: Reusable pieces exist but blockers remain
- **MISSING**: No usable artifact/tooling found
- **E0_ONLY**: Exists only for E0
- **NON_CANONICAL**: Exists but period/fees/mapping don't match

## Summary

| Status | Count | % |
|--------|-------|---|
| READY | 115 | 59.9% |
| MISSING | 77 | 40.1% |

## A) Trade Structure

| Metric | E0 | E5 | SM | LATCH | E0+EMA1D21 | E5+EMA1D21 |
|--------|----|----|----| ------|------------|------------|
| win_rate | READY | READY | READY | READY | READY | MISSING |
| wins_losses | READY | READY | READY | READY | READY | MISSING |
| avg_win_avg_loss | READY | READY | READY | READY | READY | MISSING |
| profit_factor | READY | READY | READY | READY | READY | MISSING |
| losing_streaks | READY | READY | READY | READY | READY | MISSING |
| winning_streaks | READY | READY | READY | READY | READY | MISSING |
| holding_time | READY | READY | READY | READY | READY | MISSING |
| exit_reason_taxonomy | READY | READY | READY | READY | READY | MISSING |
| MFE | READY | READY | READY | READY | READY | MISSING |
| MAE | READY | READY | READY | READY | READY | MISSING |
| giveback_ratio | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING |

**Source**: `results/trade_profile_8x5/` via `research/trade_profile_8x5.py`
**Blocker for E5_plus_EMA1D21**: Not included in the 8x5 profile run. Rerun needed.
**Blocker for giveback_ratio**: Not computed by trade_profile_8x5. Old postmortem has it for E0 only (NON_CANONICAL, 189 vs 192 trades).

## B) Home-Run Dependence

| Metric | E0 | E5 | SM | LATCH | E0+EMA1D21 | E5+EMA1D21 |
|--------|----|----|----| ------|------------|------------|
| top_1_contribution | READY | READY | READY | READY | READY | MISSING |
| top_3_contribution | READY | READY | READY | READY | READY | MISSING |
| top_5_contribution | READY | READY | READY | READY | READY | MISSING |
| top_10_contribution | READY | READY | READY | READY | READY | MISSING |
| jackknife_top_1 | READY | READY | READY | READY | READY | MISSING |
| jackknife_top_3 | READY | READY | READY | READY | READY | MISSING |
| jackknife_top_5 | READY | READY | READY | READY | READY | MISSING |
| jackknife_top_10 | READY | READY | READY | READY | READY | MISSING |
| skewness | READY | READY | READY | READY | READY | MISSING |
| kurtosis | READY | READY | READY | READY | READY | MISSING |
| jarque_bera | READY | READY | READY | READY | READY | MISSING |
| gini_concentration | READY | READY | READY | READY | READY | MISSING |
| hhi_concentration | READY | READY | READY | READY | READY | MISSING |
| sensitivity_curve | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING |
| cliff_edge_detection | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING |

**Source for 5/6**: `results/trade_profile_8x5/` T6/T7/T8 columns
**Missing**: E5_plus (needs profile rerun), sensitivity curve, cliff-edge detection (new diagnostics needed)

### Denominator/Convention Notes (T6/T7)
- **Top-N contribution**: `t6_top_N_pnl_pct_of_total` = sum of top-N PnL / total net PnL * 100. Denominator = total net PnL across all trades. Can exceed 100% when remaining trades have net negative PnL.
- **Gini**: Computed on **absolute** PnL values (|pnl_usd| per trade).
- **HHI**: Herfindahl-Hirschman index on absolute PnL shares: sum((|pnl_i| / sum(|pnl|))^2).
- **Jackknife**: Remove top-K trades by PnL rank, recompute Sharpe from remaining per-trade returns using annualization sqrt(trades_per_year), ddof=0.

## C) Operational Fragility

| Metric | All 6 Candidates | Feasibility |
|--------|------------------|-------------|
| missed_entry_1 | MISSING | requires signal/bar replay |
| missed_entry_2 | MISSING | requires signal/bar replay |
| missed_entry_3 | MISSING | requires signal/bar replay |
| outage_window_miss | MISSING | requires signal/bar replay |
| skip_after_N_losses | MISSING | feasible from episode ledger only |
| delayed_entry | MISSING | requires signal/bar replay |

**Key insight**: Only `skip_after_N_losses` is feasible from the existing trade ledger alone. All other fragility metrics require re-running the backtest engine with modified entry logic (signal replay).

## Coverage by Candidate

| Candidate | READY | MISSING | % READY |
|-----------|-------|---------|---------|
| E0 | 23 | 9 | 71.9% |
| E5 | 23 | 9 | 71.9% |
| SM | 23 | 9 | 71.9% |
| LATCH | 23 | 9 | 71.9% |
| E0_plus_EMA1D21 | 23 | 9 | 71.9% |
| E5_plus_EMA1D21 | 0 | 32 | 0.0% |
