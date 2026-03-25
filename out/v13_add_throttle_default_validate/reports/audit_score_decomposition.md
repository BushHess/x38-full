# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -70.46550000 | return_term | -64.32500000 | sharpe_term | -3.88000000 |
| full | harsh | -69.06920000 | return_term | -60.50000000 | sharpe_term | -3.96720000 |
| full | smart | -82.05090000 | return_term | -72.57500000 | sharpe_term | -4.53840000 |
| holdout | base | -50.67320000 | return_term | -45.57500000 | sharpe_term | -3.18720000 |
| holdout | harsh | -57.11020000 | return_term | -49.92500000 | sharpe_term | -3.67920000 |
| holdout | smart | -65.77650000 | return_term | -57.72500000 | sharpe_term | -4.37600000 |
