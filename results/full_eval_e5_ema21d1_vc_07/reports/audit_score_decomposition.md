# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 15.52990000 | return_term | 12.87500000 | profit_factor_term | 1.46250000 |
| full | harsh | 17.48140000 | return_term | 13.80000000 | mdd_penalty | 1.47600000 |
| full | smart | 14.50110000 | return_term | 11.87500000 | profit_factor_term | 1.66050000 |
| holdout | base | 17.97570000 | return_term | 14.25000000 | sharpe_term | 1.86720000 |
| holdout | harsh | 18.41510000 | return_term | 15.40000000 | sharpe_term | 1.92960000 |
| holdout | smart | 17.01820000 | return_term | 13.05000000 | profit_factor_term | 1.99100000 |
