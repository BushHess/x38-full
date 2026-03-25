# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 12.08300000 | return_term | 10.10000000 | mdd_penalty | 0.84600000 |
| full | harsh | 13.60490000 | return_term | 11.45000000 | mdd_penalty | 0.96000000 |
| full | smart | 10.43460000 | return_term | 8.62500000 | mdd_penalty | 0.73200000 |
| holdout | base | 1.16710000 | mdd_penalty | 0.70800000 | return_term | 0.57500000 |
| holdout | harsh | 2.17250000 | return_term | 1.85000000 | trade_count_term | -0.30000000 |
| holdout | smart | -0.60770000 | return_term | -0.77500000 | mdd_penalty | 0.45600000 |
