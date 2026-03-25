# Quality Checks

| Group | Enabled | Status | Key Artifacts |
|---|---|---|---|
| Data Integrity | on | `fail` | `results/data_integrity.json`, `results/data_integrity_issues.csv` |
| Cost Sweep | on | `skip` | - |
| Invariants | on | `skip` | - |
| Regression Guard | off | `disabled` | - |
| Churn Metrics | on | `skip` | - |

## Data Integrity

- Status: `fail`
- Hard fail: `True`
- Hard-fail reasons: `duplicate_timestamps, ohlc_invalid_rows, missing_bars_pct_exceeds_threshold, warmup_missing_severe`
- Duplicate timestamps: `1`
- Non-monotonic timestamps: `0`
- OHLC invalid rows: `1`
- Max missing bars (estimated): `40.000000%`
- Missing-bars fail threshold: `0.500000%`
- Warmup severe fail if coverage < `50.00%`

| Timeframe | Bar Seconds | Source | Gaps | Missing % (est) | OHLC Invalid | Warmup |
|---|---:|---|---:|---:|---:|---|
| 4h | 14400 | config | 1 | 40.000000 | 1 | fail (33.33%) |
| 1d | 86400 | config | 0 | 0.000000 | 0 | fail (33.33%) |