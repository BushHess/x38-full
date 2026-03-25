# Phase 1 data decomposition report

## Bucket scan summary

| bucket               |   configs_scanned |   configs_pass_gate |   best_cagr |   best_sharpe | best_config_id                          |
|:---------------------|------------------:|--------------------:|------------:|--------------:|:----------------------------------------|
| native_d1            |               343 |                 178 |    1.01344  |      1.69417  | native_d1|ret_40|high|zero|0            |
| native_h4            |               349 |                  55 |    0.469656 |      1.11658  | native_h4|rangepct_48|high|q|0.60       |
| cross_tf             |                68 |                   6 |    0.43495  |      0.872497 | cross_tf|x_h4atr6_vs_d1atr|low|fixed|1  |
| transported_d1_on_h4 |               343 |                 179 |    1.01326  |      1.69401  | transported_d1_on_h4|ret_40|high|zero|0 |

## Key conclusions

- The strongest slower-timeframe structure came from **volatility-state** D1 systems, with both ATR-level and volatility-clustering families showing strong discovery evidence.
- The strongest genuine native H4 structure came from **trend / breakout** systems, especially `rangepct_48` and `ret_48`.
- Cross-timeframe relation features did not survive cost stress well enough to become frontier candidates.
- Transported D1-on-H4 clones were almost exact reproductions of native D1 systems and therefore served as redundancy controls, not independent fast-information candidates.
