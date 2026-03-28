# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 18.31030000 | return_term | 15.40000000 | profit_factor_term | 1.55550000 |
| full | harsh | 20.75670000 | return_term | 16.77500000 | mdd_penalty | 1.47600000 |
| full | smart | 16.78040000 | return_term | 13.95000000 | profit_factor_term | 1.72800000 |
| holdout | base | 18.94230000 | return_term | 15.00000000 | sharpe_term | 2.00080000 |
| holdout | harsh | 20.39370000 | return_term | 16.57500000 | sharpe_term | 2.09920000 |
| holdout | smart | 17.50040000 | return_term | 13.32500000 | profit_factor_term | 2.19900000 |
