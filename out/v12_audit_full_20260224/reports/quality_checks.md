# Quality Checks

| Group | Enabled | Status | Key Artifacts |
|---|---|---|---|
| Data Integrity | on | `pass` | `results/data_integrity.json`, `results/data_integrity_issues.csv` |
| Cost Sweep | on | `pass` | `results/cost_sweep.csv` |
| Invariants | on | `pass` | `results/invariant_violations.csv` |
| Regression Guard | off | `disabled` | - |
| Churn Metrics | on | `pass` | `results/churn_metrics.csv` |

## Data Integrity

- Status: `pass`
- Hard fail: `False`
- Duplicate timestamps: `0`
- Non-monotonic timestamps: `0`
- OHLC invalid rows: `0`
- Max missing bars (estimated): `0.000000%`
- Missing-bars fail threshold: `0.500000%`
- Warmup severe fail if coverage < `50.00%`

| Timeframe | Bar Seconds | Source | Gaps | Missing % (est) | OHLC Invalid | Warmup |
|---|---:|---|---:|---:|---:|---|
| 4h | 14400 | config | 0 | 0.000000 | 0 | ok (100.00%) |
| 1d | 86400 | config | 0 | 0.000000 | 0 | ok (100.00%) |

## Cost Sweep

- Status: `pass`
- Rows: `12/12`
- Mode requested: `quick`
- Mode used: `quick`
- Estimated report span: `3.00` years
- Quick mode note: backtest ran on recent subset for faster runtime.
- score_primary note: score_primary = compute_objective(summary), cost-dependent; returns -1_000_000 when trades < 10.
- Breakeven rule: first bps where `CAGR <= 0` or `score_primary <= 0`.

| strategy_id | breakeven_bps | slope_0_to_50 | slope_50_to_100 |
|---|---:|---:|---:|
| baseline | - | -0.567386 | -0.921862 |
| candidate | 75.00 | -0.361912 | -0.345302 |

## Invariants

- Status: `pass`
- Violation count: `0`
- Collection limit: `200`

## Churn & Fee Drag

- Status: `pass`
- Rows: `6`
- Event source: `fills`
- Definition: `fee_drag_pct = 100 * total_fees / abs_gross_pnl`
- Warning thresholds: `fee_drag_pct>=20.000`, `cascade_leq3>=30.000`, `cascade_leq6>=50.000`

| strategy_id | scenario | trades | fee_drag_pct | share_emergency_dd | reentry_median_bars | cascade_leq3 | cascade_leq6 | buy_sell_ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| candidate | smart | 73 | 0.679 | 0.0000 | 0.00 | 0.00 | 0.00 | 5.973 |
| baseline | smart | 97 | 1.032 | 0.3299 | 15.00 | 0.00 | 0.00 | 5.392 |
| candidate | base | 73 | 1.936 | 0.0000 | 0.00 | 0.00 | 0.00 | 5.973 |
| baseline | base | 97 | 2.935 | 0.3299 | 15.00 | 0.00 | 0.00 | 5.402 |
| candidate | harsh | 73 | 2.897 | 0.0000 | 0.00 | 0.00 | 0.00 | 5.973 |
| baseline | harsh | 98 | 4.412 | 0.3367 | 15.00 | 0.00 | 0.00 | 5.418 |
- WARNING count: `0`