# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 22.53210000 | return_term | 19.87500000 | sharpe_term | 1.32160000 |
| full | harsh | 21.63910000 | return_term | 19.52500000 | sharpe_term | 1.31760000 |
| full | smart | 22.87350000 | return_term | 20.17500000 | sharpe_term | 1.32400000 |
| holdout | base | 9.70490000 | return_term | 5.80000000 | mdd_penalty | 2.10000000 |
| holdout | harsh | 9.54320000 | return_term | 5.55000000 | mdd_penalty | 2.37600000 |
| holdout | smart | 9.75320000 | return_term | 6.07500000 | mdd_penalty | 1.70400000 |
