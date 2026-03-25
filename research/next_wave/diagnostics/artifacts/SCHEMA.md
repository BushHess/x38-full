# D1.2 Artifact Schema

Generated: 2026-03-07
Source: actual BacktestEngine (`v10/core/engine.py`), NOT vectorized surrogates.

## Trade Ledger: `trades_{STRATEGY}_{SCENARIO}.csv`

| Column | Type | Description |
|--------|------|-------------|
| strategy | str | Strategy label (X0, E0_EMA21, X0_LR) |
| scenario | str | Cost scenario (smart, base, harsh) |
| trade_id | int | Sequential trade number |
| entry_ts_ms | int | Entry fill timestamp (epoch ms) |
| exit_ts_ms | int | Exit fill timestamp (epoch ms) |
| entry_time | str | Entry time ISO-8601 UTC |
| exit_time | str | Exit time ISO-8601 UTC |
| entry_fill_price | float | Cost-adjusted entry fill price (ask + slippage) |
| exit_fill_price | float | Cost-adjusted exit fill price (bid - slippage) |
| entry_mid_price | float | Mid price at entry (fill_price / buy_multiplier) |
| exit_mid_price | float | Mid price at exit (fill_price / sell_multiplier) |
| qty | float | BTC quantity filled |
| gross_return_pct | float | Mid-to-mid return (no cost) |
| net_return_pct | float | Fill-to-fill return (includes spread+slippage, excludes fee) |
| pnl_usd | float | Realized PnL in USD (proceeds - cost_basis, includes fees) |
| holding_bars | int | Duration in H4 bars |
| holding_days | float | Duration in calendar days |
| entry_reason | str | Strategy entry signal reason |
| exit_reason | str | Strategy exit signal reason |

### Price semantics
- `entry_fill_price = mid * (1 + spread/20000) * (1 + slippage/10000)`
- `exit_fill_price = mid * (1 - spread/20000) * (1 - slippage/10000)`
- `net_return_pct = (exit_fill / entry_fill - 1) * 100` (includes spread+slippage)
- `gross_return_pct = (exit_mid / entry_mid - 1) * 100` (zero cost)
- `pnl_usd` additionally includes taker fee drag (deducted from cash)

## Bar-Level Feature Store: `bar_features.csv`

One row per H4 bar in the reporting window (2019-01-01 to 2026-02-20).

| Column | Type | Description | No-Lookahead |
|--------|------|-------------|--------------|
| bar_index | int | Index into full H4 bar array (incl. warmup) | N/A |
| open_time_ms | int | Bar open timestamp (epoch ms) | N/A |
| close_time_ms | int | Bar close timestamp (epoch ms) | N/A |
| close_time | str | Bar close time ISO-8601 UTC | N/A |
| close | float | Bar close price | at bar close |
| ema_fast_h4 | float | EMA(30) on H4 close | at bar close |
| ema_slow_h4 | float | EMA(120) on H4 close | at bar close |
| atr_14_h4 | float | Wilder ATR(14) on H4 | at bar close |
| ratr_h4 | float | Robust ATR (cap_q=0.90, lb=100, p=20) | at bar close |
| vdo | float | Volume Delta Oscillator (EMA(12)-EMA(28)) | at bar close |
| d1_regime | int | 1 if D1 close > D1 EMA(21), else 0 | last completed D1 bar |
| bars_since_last_exit | int | Bars since last X0 exit (base scenario) | at bar close |
| prior_exit_reason | str | Exit reason of most recent X0 trade | at bar close |
| breadth_ema21_share | float | Fraction of 13 alts with close > H4 EMA(126) | at bar close |

### No-lookahead rules
- All indicator values use data up to and including the current bar close
- D1 regime uses only completed D1 bars (close_time < H4 bar close_time)
- Breadth uses only completed H4 bars per symbol (close_time < BTC H4 close_time)
- bars_since_last_exit and prior_exit_reason use only exits that have already occurred

## Entry-Annotated Feature Store: `entry_features_{STRATEGY}_base.csv`

One row per executed entry (base cost scenario).

| Column | Type | Description |
|--------|------|-------------|
| trade_id | int | Sequential trade number |
| entry_ts_ms | int | Entry fill timestamp (fill happens at next bar open) |
| entry_time | str | Entry time ISO-8601 UTC |
| exit_ts_ms | int | Exit fill timestamp |
| exit_time | str | Exit time ISO-8601 UTC |
| entry_price | float | Entry fill price (cost-adjusted) |
| exit_price | float | Exit fill price (cost-adjusted) |
| net_return_pct | float | Fill-to-fill return |
| pnl_usd | float | Realized PnL in USD |
| holding_bars | int | Duration in H4 bars |
| exit_reason | str | Exit signal reason |
| decision_bar_idx | int | Bar index where entry signal fired |
| decision_close_time | str | Decision bar close time |
| decision_close | float | Decision bar close price |
| ema_fast_h4 | float | EMA(30) at decision bar |
| ema_slow_h4 | float | EMA(120) at decision bar |
| atr_14_h4 | float | ATR(14) at decision bar |
| ratr_h4 | float | Robust ATR at decision bar |
| vdo | float | VDO at decision bar |
| d1_regime | int | D1 regime at decision bar |
| bars_since_last_exit | int | Bars since prior exit at decision bar |
| prior_exit_reason | str | Reason of prior exit |
| breadth_ema21_share | float | Breadth share at decision bar |
| funding_raw | - | MISSING (blocked per D1.1) |
| funding_pct_rank | - | MISSING (blocked per D1.1) |
| oi_level | - | MISSING (blocked per D1.1) |
| oi_change_1d | - | MISSING (blocked per D1.1) |
| basis_raw | - | MISSING (blocked per D1.1) |
| reentry_within_1_bars | int | 1 if entry within 1 bar of prior exit |
| reentry_within_2_bars | int | 1 if entry within 2 bars of prior exit |
| reentry_within_3_bars | int | 1 if entry within 3 bars of prior exit |
| reentry_within_4_bars | int | 1 if entry within 4 bars of prior exit |
| reentry_within_6_bars | int | 1 if entry within 6 bars of prior exit |

### Decision bar semantics
- Strategy calls `on_bar(state)` at bar CLOSE and returns a Signal
- The Signal is executed as a fill at the NEXT bar's OPEN
- Therefore: `decision_bar_close_time < entry_ts_ms` (strictly before)
- All features are from the decision bar's close (no lookahead)

## Summary: `backtest_summary.csv`

| Column | Description |
|--------|-------------|
| strategy | Strategy label |
| scenario | Cost scenario |
| trades | Number of round-trip trades |
| sharpe | Annualized Sharpe (sqrt(6*365.25), ddof=0) |
| cagr_pct | CAGR in percent |
| max_dd_pct | Maximum drawdown (mid NAV) in percent |
| calmar | CAGR / MDD |
| win_rate | Win rate in percent |
| avg_exposure | Mean fractional exposure |
| time_in_market_pct | Fraction of bars with exposure > 0 |

## Equity Curves: `equity_{STRATEGY}_{SCENARIO}.csv`

| Column | Description |
|--------|-------------|
| close_time_ms | Bar close timestamp (epoch ms) |
| close_time | ISO-8601 UTC |
| nav_mid | Net asset value at mid price |
| cash | Cash balance |
| btc_qty | BTC holdings |
| exposure | Fractional exposure (BTC value / NAV) |

## Breadth approximation

D1 EMA(21) is approximated as H4 EMA(126) for breadth symbols because
only H4 bars are available in the breadth universe data.
This is a 6:1 mapping (6 H4 bars per D1 bar). The approximation is
close but not identical due to different bar-close alignments.

## Derivatives features

All 5 derivatives columns (funding_raw, funding_pct_rank, oi_level,
oi_change_1d, basis_raw) are present as empty placeholders.
Derivatives data does not exist in the project (hard blocker, see D1.1).
