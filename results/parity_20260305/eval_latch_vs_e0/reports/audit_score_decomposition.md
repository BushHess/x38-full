# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -92.53650000 | return_term | -116.57500000 | mdd_penalty | 17.65200000 |
| full | harsh | -72.91350000 | return_term | -98.05000000 | mdd_penalty | 18.22200000 |
| full | smart | -112.01620000 | return_term | -135.02500000 | mdd_penalty | 17.08800000 |
| holdout | base | -52.06980000 | return_term | -59.82500000 | mdd_penalty | 7.48200000 |
| holdout | harsh | -37.65100000 | return_term | -46.80000000 | mdd_penalty | 8.58600000 |
| holdout | smart | -66.23480000 | return_term | -72.77500000 | mdd_penalty | 6.54000000 |
