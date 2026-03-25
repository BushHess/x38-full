# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -91.21230000 | return_term | -83.05000000 | sharpe_term | -3.84080000 |
| full | harsh | -83.40210000 | return_term | -73.82500000 | mdd_penalty | -5.11800000 |
| full | smart | -99.06220000 | return_term | -92.42500000 | sharpe_term | -3.99920000 |
| holdout | base | -71.88220000 | return_term | -61.95000000 | sharpe_term | -5.83520000 |
| holdout | harsh | -64.67020000 | return_term | -55.40000000 | sharpe_term | -5.75520000 |
| holdout | smart | -79.01710000 | return_term | -68.55000000 | sharpe_term | -5.90960000 |
