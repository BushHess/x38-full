# Exp 41: Momentum Acceleration Gate Walk-Forward Validation

## Status: PENDING

## Hypothesis
Exp33 showed +0.1515 Sharpe and -10.31pp MDD (best: lb=12, min_accel=0.0).
The improvement comes from entry TIMING — blocked entries have nearly
identical win rate to the baseline (40-42% vs 41.2%). The gate delays entry
until ema_spread is accelerating, which gives shorter losers and better
entry prices, but doesn't selectively block losers.

Timing effects are potentially regime-dependent:
- In strong trends (bull), acceleration happens early and persistently →
  gate lets most entries through
- In choppy markets (bear/sideways), acceleration oscillates → gate blocks
  many entries, reducing exposure

This mirrors the bear/bull asymmetry in exp30. If accel gate only helps
by reducing exposure in bear markets, it will fail WFO like the AND gate.

Walk-forward validation tests whether the timing improvement persists
across temporal regimes.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~221 trades.

## WFO Design
Anchored walk-forward, 4 windows (identical to exp30/exp40):
```
Window 1: Train [2019-01 → 2021-06]  Test [2021-07 → 2023-06]
Window 2: Train [2019-01 → 2022-06]  Test [2022-07 → 2024-06]
Window 3: Train [2019-01 → 2023-06]  Test [2023-07 → 2025-06]
Window 4: Train [2019-01 → 2024-06]  Test [2024-07 → 2026-02]
```

## Parameter grid (train sweep)
Same as exp33:
- lookback: [3, 6, 12, 24]
- min_accel: [0.0, 0.001, 0.002]
- (12 configs)
- Select: best Sharpe on training period

## Fixed config (from exp33 global optimum)
lookback=12, min_accel=0.0

## Procedure per window
1. **Train**: sweep 12 configs → select best by Sharpe
2. **Test**: run train-selected + fixed + baseline on test period
3. Record: d_Sharpe, d_MDD, blocked count, blocked WR

## What to measure
Per window:
- Train-selected config
- Test d_Sharpe (selected), d_MDD (selected)
- Test d_Sharpe (fixed), d_MDD (fixed)
- Blocked entries and blocked WR per test window
- Exposure reduction in test window

Aggregate:
- WFO win rate ≥ 3/4 AND mean d_Sharpe > 0
- Parameter stability (is lb=12 consistently selected?)
- Bear vs bull analysis (does accel gate show regime asymmetry?)

## Critical question
Exp33 noted that improvement is timing, not selectivity (blocked WR ≈
baseline WR). If the WFO test shows the gate helps equally in bull AND
bear windows, then the timing mechanism is robust even though it's not
selective. If it only helps in bear → regime-dependent timing, not robust.

## Implementation notes
- Reuse exp33's run_backtest() and ema_spread_roc computation
- Reuse exp30's WFO infrastructure
- Warmup: SLOW_PERIOD=120 bars within each window (consistent with exp33)
  Note: exp33 used warmup_bar=SLOW_PERIOD, not 365 days. Keep consistent.
- Cost: 50 bps RT

## Output
- Script: x39/experiments/exp41_accel_gate_wfo.py
- Results: x39/results/exp41_results.csv

## Result
_(to be filled by experiment session)_
