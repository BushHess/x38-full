# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 22.54340000 | return_term | 18.85000000 | mdd_penalty | 1.85400000 |
| full | harsh | 24.93800000 | return_term | 22.00000000 | profit_factor_term | 1.17800000 |
| full | smart | 19.04010000 | return_term | 15.57500000 | mdd_penalty | 1.82400000 |
| holdout | base | -22.47800000 | return_term | -16.50000000 | mdd_penalty | -3.46800000 |
| holdout | harsh | -18.45320000 | return_term | -13.82500000 | mdd_penalty | -2.38200000 |
| holdout | smart | -25.50250000 | return_term | -19.22500000 | mdd_penalty | -3.52200000 |
