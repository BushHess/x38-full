# Quality Checks

| Group | Enabled | Status | Key Artifacts |
|---|---|---|---|
| Data Integrity | off | `disabled` | - |
| Cost Sweep | off | `disabled` | - |
| Invariants | off | `disabled` | - |
| Regression Guard | off | `disabled` | - |
| Churn Metrics | on | `pass` | `results/churn_metrics.csv` |

## Churn & Fee Drag

- Status: `pass`
- Rows: `2`
- Event source: `fills`
- Definition: `fee_drag_pct = 100 * total_fees / abs_gross_pnl`
- Warning thresholds: `fee_drag_pct>=20.000`, `cascade_leq3>=30.000`, `cascade_leq6>=50.000`

| strategy_id | scenario | trades | fee_drag_pct | share_emergency_dd | reentry_median_bars | cascade_leq3 | cascade_leq6 | buy_sell_ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| candidate | base | 3 | 1.922 | 0.3333 | 12.00 | 0.00 | 0.00 | 6.333 |
| baseline | base | 3 | 1.922 | 0.3333 | 12.00 | 0.00 | 0.00 | 6.333 |
- WARNING count: `0`