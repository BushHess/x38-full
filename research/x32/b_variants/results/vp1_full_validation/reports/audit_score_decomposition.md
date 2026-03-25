# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 29.73410000 | return_term | 25.70000000 | sharpe_term | 1.57360000 |
| full | harsh | 27.75350000 | return_term | 24.97500000 | sharpe_term | 1.56800000 |
| full | smart | 30.69030000 | return_term | 26.40000000 | mdd_penalty | 1.67400000 |
| holdout | base | 5.88820000 | return_term | 2.97500000 | mdd_penalty | 1.74600000 |
| holdout | harsh | 5.52280000 | return_term | 2.42500000 | mdd_penalty | 2.10600000 |
| holdout | smart | 6.32350000 | return_term | 3.55000000 | mdd_penalty | 1.44600000 |
