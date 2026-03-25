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
- Estimated report span: `1.43` years
- Quick mode note: requested quick but runner fell back to full-history slice.
- score_primary note: score_primary = compute_objective(summary), cost-dependent; returns -1_000_000 when trades < 10.
- Breakeven rule: first bps where `CAGR <= 0` or `score_primary <= 0`.

| strategy_id | breakeven_bps | slope_0_to_50 | slope_50_to_100 |
|---|---:|---:|---:|
| baseline | - | -0.609354 | -0.470462 |
| candidate | - | -0.270684 | -0.202876 |

## Invariants

- Status: `pass`
- Violation count: `0`
- Collection limit: `200`

## Churn & Fee Drag

- Status: `pass`
- Rows: `2`
- Event source: `fills`
- Definition: `fee_drag_pct = 100 * total_fees / abs_gross_pnl`
- Warning thresholds: `fee_drag_pct>=20.000`, `cascade_leq3>=30.000`, `cascade_leq6>=50.000`

| strategy_id | scenario | trades | fee_drag_pct | share_emergency_dd | reentry_median_bars | cascade_leq3 | cascade_leq6 | buy_sell_ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| candidate | harsh | 20 | 4.562 | 0.2500 | 12.00 | 0.00 | 0.00 | 4.400 |
| baseline | harsh | 24 | 5.511 | 0.2917 | 13.50 | 0.00 | 0.00 | 5.542 |
- WARNING count: `0`