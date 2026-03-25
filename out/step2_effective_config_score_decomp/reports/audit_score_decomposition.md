# Score decomposition audit

## Residual check

- Full period residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**
- Holdout residual max abs: `0.000000000000` (tol `1.0e-06`) -> **PASS**

## Top delta terms (candidate - baseline)

| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
|---|---|---:|---|---:|---|---:|
| full | base | -6.91440000 | mdd_penalty | -3.67800000 | return_term | -2.47500000 |
| full | harsh | 0.31200000 | return_term | 5.05000000 | mdd_penalty | -4.94400000 |
| full | smart | -7.81210000 | mdd_penalty | -3.96000000 | return_term | -3.05000000 |
| holdout | base | -32.22780000 | return_term | -27.25000000 | sharpe_term | -2.24480000 |
| holdout | harsh | -24.62440000 | return_term | -21.67500000 | sharpe_term | -1.80240000 |
| holdout | smart | -31.87490000 | return_term | -27.00000000 | profit_factor_term | -2.25850000 |
