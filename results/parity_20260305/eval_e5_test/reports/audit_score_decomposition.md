# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 15.72410000 | return_term | 13.70000000 | sharpe_term | 0.83760000 |
| full | harsh | 13.19600000 | return_term | 11.45000000 | mdd_penalty | 0.74400000 |
| full | smart | 18.32600000 | return_term | 16.02500000 | sharpe_term | 0.93200000 |
