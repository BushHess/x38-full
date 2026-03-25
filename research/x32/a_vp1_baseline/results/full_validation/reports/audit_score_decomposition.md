# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 29.06760000 | return_term | 25.72500000 | sharpe_term | 1.53360000 |
| full | harsh | 27.45880000 | return_term | 24.22500000 | sharpe_term | 1.49680000 |
| full | smart | 30.65710000 | return_term | 27.22500000 | sharpe_term | 1.56560000 |
| holdout | base | -4.63240000 | return_term | -4.22500000 | trade_count_term | 0.60000000 |
| holdout | harsh | -8.01980000 | return_term | -6.47500000 | mdd_penalty | -1.17600000 |
| holdout | smart | -1.00090000 | return_term | -1.85000000 | mdd_penalty | 0.66000000 |
