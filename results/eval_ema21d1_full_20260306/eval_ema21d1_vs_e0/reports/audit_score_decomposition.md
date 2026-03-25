# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 5.32320000 | return_term | 4.82500000 | profit_factor_term | 0.51700000 |
| full | harsh | 7.36980000 | return_term | 6.65000000 | profit_factor_term | 0.50700000 |
| full | smart | 3.18860000 | return_term | 2.92500000 | mdd_penalty | -0.54600000 |
| holdout | base | 4.70170000 | return_term | 3.35000000 | mdd_penalty | 0.94200000 |
| holdout | harsh | 5.98040000 | return_term | 4.87500000 | sharpe_term | 0.71840000 |
| holdout | smart | 2.48830000 | return_term | 1.77500000 | sharpe_term | 0.51680000 |
