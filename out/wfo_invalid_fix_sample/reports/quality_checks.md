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
- Mode used: `full_fallback`
- Estimated report span: `0.67` years
- Quick mode note: requested quick but runner fell back to full-history slice.
- score_primary note: score_primary = compute_objective(summary), cost-dependent; returns -1_000_000 when trades < 10.
- Breakeven rule: first bps where `CAGR <= 0` or `score_primary <= 0`.

| strategy_id | breakeven_bps | slope_0_to_50 | slope_50_to_100 |
|---|---:|---:|---:|
| baseline | 75.00 | -0.667114 | -0.856612 |
| candidate | 75.00 | -0.667114 | -0.856612 |

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
| candidate | smart | 17 | 1.249 | 0.4706 | 15.00 | 0.00 | 0.00 | 4.824 |
| baseline | smart | 17 | 1.249 | 0.4706 | 15.00 | 0.00 | 0.00 | 4.824 |
| candidate | base | 17 | 3.549 | 0.4706 | 15.00 | 0.00 | 0.00 | 4.824 |
| baseline | base | 17 | 3.549 | 0.4706 | 15.00 | 0.00 | 0.00 | 4.824 |
| candidate | harsh | 17 | 5.290 | 0.4706 | 15.00 | 0.00 | 0.00 | 4.824 |
| baseline | harsh | 17 | 5.290 | 0.4706 | 15.00 | 0.00 | 0.00 | 4.824 |
- WARNING count: `0`