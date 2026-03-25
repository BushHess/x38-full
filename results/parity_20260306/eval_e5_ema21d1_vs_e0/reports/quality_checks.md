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
| baseline | - | -1.146888 | -1.004628 |
| candidate | - | -1.158348 | -1.032618 |

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
| candidate | smart | 186 | 1.618 | 0.0000 | 0.00 | 0.00 | 0.00 | 1.000 |
| baseline | smart | 192 | 1.567 | 0.0000 | 0.00 | 0.00 | 0.00 | 1.000 |
| candidate | base | 186 | 4.504 | 0.0000 | 0.00 | 0.00 | 0.00 | 1.000 |
| baseline | base | 192 | 4.358 | 0.0000 | 0.00 | 0.00 | 0.00 | 1.000 |
| candidate | harsh | 186 | 6.556 | 0.0000 | 0.00 | 0.00 | 0.00 | 1.000 |
| baseline | harsh | 192 | 6.339 | 0.0000 | 0.00 | 0.00 | 0.00 | 1.000 |
- WARNING count: `0`