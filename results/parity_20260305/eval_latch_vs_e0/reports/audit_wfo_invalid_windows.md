# WFO invalid-window audit

- Generated: 2026-03-05 18:16:15 UTC

## Spec

- `valid_window=False` when either side has zero trades or any core metric is NaN/Inf.
- `low_trade_window=True` only when `valid_window=True` and trade count is in `(0, min_trades_for_power)`.
- Aggregate stats use valid windows only; power stats exclude low-trade windows.
- Invalid windows must carry explicit `invalid_reason`; their `delta_harsh_score` is `NaN`.

## What changed

- Removed sentinel-driven window deltas from WFO reporting by using non-reject objective scoring in this suite.
- Added explicit per-window validity fields:
  - `trade_count_baseline`, `trade_count_candidate`
  - `valid_window`, `invalid_reason`
  - `low_trade_window`, `low_trade_reason`
- Added dual aggregation blocks in `wfo_summary.json`: `stats_all_valid` and `stats_power_only`.
- Default `min_trades_for_power` for WFO is now `5`.

## Before/after example

- Before (legacy sentinel path): windows with very low/zero trades could emit extreme deltas like `-1000056.8469`.
- After: invalid windows are explicitly marked and excluded from aggregation.

| low-trade window_id | valid_window | low_trade_window | low_trade_reason | delta_harsh_score |
|---:|---|---|---|---:|
| 0 | True | True | candidate_below_min_trades_for_power | 37.0090 |

## Summary snapshot

- invalid_windows_count: `0`
- low_trade_windows_count: `2`
- stats_all_valid.median_delta: `23.2477`
- stats_all_valid.worst_delta: `-251.1670`
- stats_power_only.median_delta: `2.9329`
- stats_power_only.worst_delta: `-251.1670`
