# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -51.74930000 | return_term | -52.82500000 | mdd_penalty | 2.04600000 |
| full | harsh | -44.09090000 | return_term | -44.35000000 | sharpe_term | -1.44240000 |
| full | smart | -59.56510000 | return_term | -61.47500000 | mdd_penalty | 3.01800000 |
| holdout | base | -6.27320000 | return_term | -8.77500000 | mdd_penalty | 1.62600000 |
| holdout | harsh | -2.21260000 | return_term | -4.70000000 | mdd_penalty | 1.63800000 |
| holdout | smart | -10.53420000 | return_term | -12.90000000 | profit_factor_term | 1.63100000 |
