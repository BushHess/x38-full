# Exp 40: Trend Maturity Decay Walk-Forward Validation

## Status: PENDING

## Hypothesis
Exp38 showed +0.150 Sharpe and -9.82pp MDD (best config: trail_min=1.5,
decay_start=60, decay_end=180). 11/18 configs improved Sharpe, 18/18
improved MDD — the most universal finding in x39.

However, exp30 demonstrated that full-sample improvements can be
selection bias: the AND gate (+0.057 Sharpe full-sample) had 50% WFO win
rate and NEGATIVE mean d_Sharpe. The AND gate worked in bear but hurt in bull.

Maturity decay is DIFFERENT from the AND gate — it's a structural mechanism
(time-based trail tightening) rather than a feature-based exit signal.
The hypothesis is that maturity decay is MORE temporally stable because:
1. It doesn't rely on a specific feature (rangepos/trendq) that may have
   regime-dependent predictive power
2. The underlying mechanism (trends age and mean-revert) is universal
3. 11/18 configs passed full-sample, suggesting broad robustness

This experiment tests temporal stability via anchored walk-forward validation.
**If exp38 fails WFO, the +0.150 Sharpe is period-specific.**
**If it passes, maturity decay is the first robust x39 mechanism.**

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades.

## WFO Design
Anchored walk-forward, 4 windows (identical to exp30):
```
Window 1: Train [2019-01 → 2021-06]  Test [2021-07 → 2023-06]
Window 2: Train [2019-01 → 2022-06]  Test [2022-07 → 2024-06]
Window 3: Train [2019-01 → 2023-06]  Test [2023-07 → 2025-06]
Window 4: Train [2019-01 → 2024-06]  Test [2024-07 → 2026-02]
```

## Parameter grid (train sweep)
Same as exp38:
- trail_min: [1.5, 2.0, 2.5]
- decay_start: [30, 60] (H4 bars)
- decay_end: [120, 180, 240] (H4 bars)
- constraint: decay_start < decay_end
- (18 configs)
- Select: best Sharpe on training period

## Fixed config (from exp38 global optimum)
trail_min=1.5, decay_start=60, decay_end=180

## Procedure per window
1. **Train**: sweep 18 configs on training period → select best by Sharpe
2. **Test**: run train-selected config + fixed config + baseline on test period
3. Record: d_Sharpe, d_MDD vs baseline for both selected and fixed

## What to measure
Per window:
- Train-selected config: which (min, start, end) was chosen?
- Test d_Sharpe (selected vs baseline), d_MDD
- Test d_Sharpe (fixed vs baseline), d_MDD
- Trade count, effective trail at exit in test period

Aggregate:
- **WFO win rate**: windows where d_Sharpe > 0 / 4 (target ≥ 3/4)
- **Mean d_Sharpe**: average across 4 test windows (target > 0)
- **Parameter stability**: are train-selected configs consistent?
- **Fixed vs selected**: does the fixed config match or beat selected?
- **Bear vs bull**: does maturity decay show the same regime asymmetry as exp30?

## Pass criteria
- WFO win rate ≥ 75% (3/4) AND mean d_Sharpe > 0
- OR: fixed config passes both criteria independently
- ALSO note: if maturity decay helps in BOTH bear (W1/W2) and bull (W3/W4),
  this breaks the pattern seen in exp30 (AND gate = bear-only)

## Implementation notes
- Reuse exp38's compute_trend_age() and effective_trail() functions
- Reuse exp30's WFO infrastructure (find_bar_idx, window splitting)
- Warmup: 365 days within each window (consistent with exp30/exp38)
- Cost: 50 bps RT, INITIAL_CASH = 10_000
- Force-close open positions at window end (consistent with exp30)

## Output
- Script: x39/experiments/exp40_maturity_decay_wfo.py
- Results: x39/results/exp40_results.csv

## Result
_(to be filled by experiment session)_
