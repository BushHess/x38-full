# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | 35.93500000 | return_term | 29.82500000 | mdd_penalty | 3.37800000 |
| full | harsh | 31.55660000 | return_term | 26.07500000 | mdd_penalty | 2.98800000 |
| full | smart | 40.02370000 | return_term | 33.70000000 | mdd_penalty | 3.39000000 |
| holdout | base | -7.42100000 | return_term | -5.42500000 | mdd_penalty | -1.93800000 |
| holdout | harsh | -11.78320000 | return_term | -9.62500000 | mdd_penalty | -1.62000000 |
| holdout | smart | -2.69720000 | mdd_penalty | -2.12400000 | trade_count_term | 1.10000000 |
