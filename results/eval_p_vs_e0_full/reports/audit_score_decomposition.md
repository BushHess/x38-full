# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -95.24280000 | return_term | -116.92500000 | mdd_penalty | 16.84800000 |
| full | harsh | -75.97260000 | return_term | -98.65000000 | mdd_penalty | 17.35800000 |
| full | smart | -114.44580000 | return_term | -135.17500000 | mdd_penalty | 16.33800000 |
| holdout | base | -54.73550000 | return_term | -60.37500000 | mdd_penalty | 7.41600000 |
| holdout | harsh | -40.58070000 | return_term | -47.60000000 | mdd_penalty | 8.39400000 |
| holdout | smart | -68.91520000 | return_term | -73.20000000 | mdd_penalty | 6.49200000 |
