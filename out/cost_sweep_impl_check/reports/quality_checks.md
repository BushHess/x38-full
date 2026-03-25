# Quality Checks

| Group | Enabled | Status | Key Artifacts |
|---|---|---|---|
| Data Integrity | on | `pass` | `results/data_integrity.json`, `results/data_integrity_issues.csv` |
| Cost Sweep | on | `pass` | `results/cost_sweep.csv` |
| Invariants | on | `pass` | `results/invariant_violations.csv` |
| Regression Guard | off | `disabled` | - |
| Churn Metrics | on | `info` | `results/churn_metrics.csv` |

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
- Estimated report span: `2.50` years
- Quick mode note: backtest ran on recent subset for faster runtime.
- score_primary note: score_primary = compute_objective(summary), cost-dependent; returns -1_000_000 when trades < 10.
- Breakeven rule: first bps where `CAGR <= 0` or `score_primary <= 0`.

| strategy_id | breakeven_bps | slope_0_to_50 | slope_50_to_100 |
|---|---:|---:|---:|
| baseline | - | -0.666960 | -0.885208 |
| candidate | - | -0.666960 | -0.885208 |