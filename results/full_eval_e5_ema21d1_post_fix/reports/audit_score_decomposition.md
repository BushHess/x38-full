# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 28.60930000 | return_term | 24.70000000 | sharpe_term | 1.52480000 |
| full | harsh | 26.52860000 | return_term | 23.90000000 | sharpe_term | 1.51360000 |
| full | smart | 29.69060000 | return_term | 25.47500000 | mdd_penalty | 1.67400000 |
| holdout | base | 6.01270000 | return_term | 3.12500000 | mdd_penalty | 1.74600000 |
| holdout | harsh | 5.58270000 | return_term | 2.55000000 | mdd_penalty | 2.10600000 |
| holdout | smart | 6.53520000 | return_term | 3.72500000 | mdd_penalty | 1.44600000 |
