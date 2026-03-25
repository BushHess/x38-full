# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | harsh | -64.57960000 | return_term | -59.87500000 | sharpe_term | -3.16560000 |
| holdout | harsh | -77.18000000 | return_term | -70.25000000 | sharpe_term | -5.88000000 |
