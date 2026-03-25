# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 20.93330000 | return_term | 17.57500000 | mdd_penalty | 1.85400000 |
| full | harsh | 23.19990000 | return_term | 20.42500000 | mdd_penalty | 1.06200000 |
| full | smart | 17.69620000 | return_term | 14.57500000 | mdd_penalty | 1.82400000 |
| holdout | base | -25.90410000 | return_term | -19.47500000 | mdd_penalty | -3.46800000 |
| holdout | harsh | -22.18600000 | return_term | -17.07500000 | mdd_penalty | -2.38200000 |
| holdout | smart | -28.57230000 | return_term | -21.87500000 | mdd_penalty | -3.52200000 |
