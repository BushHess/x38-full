# A3 Validation Report

Scenario: `harsh`  
Window: `2019-01-01` -> `2026-02-20`  
Warmup: `365` days

## Metrics

| Variant | Sharpe | CAGR % | MDD % | Trades |
|---|---:|---:|---:|---:|
| A3 ratio mode + adaptive theta | 1.2572 | 49.33 | 44.39 | 162 |
| Full Q-VDO-RH | 1.1507 | 42.79 | 45.00 | 154 |
| E0 baseline | 1.2653 | 52.04 | 41.61 | 192 |

## Deltas

- Delta Sharpe vs Full Q-VDO-RH: `+0.1065` (>>)
- Delta Sharpe vs E0: `-0.0081` (≈)

## Readout

- Verdict context: `CLOSE Q-VDO-RH family`
- Next action: Full Q-VDO-RH loses mainly from normalized input; A5 and A3 only recover back toward E0, so do not open d_ or e_.
