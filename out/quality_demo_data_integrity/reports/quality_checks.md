# Quality Checks

| Group | Enabled | Status | Key Artifacts |
|---|---|---|---|
| Data Integrity | on | `pass` | `results/data_integrity.json`, `results/data_integrity_issues.csv` |
| Cost Sweep | on | `info` | `results/cost_sweep.csv` |
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