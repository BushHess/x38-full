# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -5.34590000 | return_term | -4.85000000 | mdd_penalty | -0.43800000 |
| full | harsh | -2.82450000 | return_term | -2.60000000 | mdd_penalty | -0.29400000 |
| full | smart | -7.93930000 | return_term | -7.17500000 | mdd_penalty | -0.57600000 |
| holdout | base | 24.82300000 | return_term | 21.62500000 | sharpe_term | 2.00800000 |
| holdout | harsh | 24.87870000 | return_term | 21.97500000 | sharpe_term | 2.10720000 |
| holdout | smart | 23.94150000 | return_term | 21.22500000 | sharpe_term | 1.91200000 |
