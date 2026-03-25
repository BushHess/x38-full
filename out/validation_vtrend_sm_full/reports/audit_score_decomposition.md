# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -86.47020000 | return_term | -108.10000000 | mdd_penalty | 15.48600000 |
| full | harsh | -67.62530000 | return_term | -90.10000000 | mdd_penalty | 15.91200000 |
| full | smart | -105.48060000 | return_term | -126.15000000 | mdd_penalty | 14.99400000 |
| holdout | base | -47.27620000 | return_term | -54.97500000 | mdd_penalty | 6.74400000 |
| holdout | harsh | -33.61120000 | return_term | -42.55000000 | mdd_penalty | 7.81800000 |
| holdout | smart | -60.74590000 | return_term | -67.37500000 | mdd_penalty | 5.82600000 |
