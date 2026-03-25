# c_ablation Attribution Matrix

Scenario: `harsh`
Window: `2019-01-01` -> `2026-02-20`
Warmup: `365` days

## Strategy Metrics

| Key | Variant | Sharpe | CAGR % | MDD % | Trades | Win Rate % | Avg Exposure |
|---|---|---:|---:|---:|---:|---:|---:|
| e0 | E0 VTREND baseline | 1.2653 | 52.04 | 41.61 | 192 | 40.10 | 0.4682 |
| full | Full Q-VDO-RH | 1.1507 | 42.79 | 45.00 | 154 | 42.21 | 0.4013 |
| a5 | A5 VDO + adaptive theta | 1.2552 | 49.22 | 44.67 | 162 | 41.98 | 0.4229 |
| a3 | A3 ratio mode + adaptive theta | 1.2572 | 49.33 | 44.39 | 162 | 41.98 | 0.4227 |

## Delta Sharpe Matrix

| Comparison | Delta Sharpe | Relation |
|---|---:|---|
| A5 vs Full | +0.1045 | >> |
| A3 vs Full | +0.1065 | >> |
| A5 vs E0 | -0.0101 | ≈ |
| A3 vs E0 | -0.0081 | ≈ |
| Full vs E0 | -0.1146 | << |

## Verdict

- Verdict: `CLOSE Q-VDO-RH family`
- Next action: Full Q-VDO-RH loses mainly from normalized input; A5 and A3 only recover back toward E0, so do not open d_ or e_.
