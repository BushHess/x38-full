# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -30.07890000 | return_term | -28.12500000 | sharpe_term | -1.07040000 |
| full | harsh | -25.96580000 | return_term | -23.12500000 | mdd_penalty | -2.03400000 |
| full | smart | -34.27100000 | return_term | -33.25000000 | sharpe_term | -1.21600000 |
| holdout | base | 16.10970000 | return_term | 12.70000000 | profit_factor_term | 1.86650000 |
| holdout | harsh | 19.11800000 | return_term | 15.17500000 | sharpe_term | 1.84000000 |
| holdout | smart | 13.15990000 | return_term | 10.17500000 | profit_factor_term | 1.96050000 |
