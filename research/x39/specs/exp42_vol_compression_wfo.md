# Exp 42: Volatility Compression Entry Walk-Forward Validation

## Status: PENDING

## Hypothesis
Exp34 showed ALL 6 thresholds improve Sharpe (best threshold=0.6: +0.1901).
MDD slightly worse (+2.3pp at 0.6; +0.4pp at 0.7). Blocked entries have
LOWER win rate than baseline (27-41% vs 41.2%) → selectivity is GOOD.

Unlike exp33 (timing effect, not selective), exp34 IS genuinely selective —
it preferentially blocks entries that would have been losers. This is a
stronger signal. Single-parameter sweep (1 DOF) also reduces overfitting risk.

However, vol_ratio_5_20 is derived from short-term price volatility. In
prolonged low-vol regimes (2023), most entries pass; in high-vol (2022),
most entries are blocked. This regime dependence could cause WFO failure.

This WFO test determines: is the selectivity real and stable across time?

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~221 trades.

## WFO Design
Anchored walk-forward, 4 windows:
```
Window 1: Train [2019-01 → 2021-06]  Test [2021-07 → 2023-06]
Window 2: Train [2019-01 → 2022-06]  Test [2022-07 → 2024-06]
Window 3: Train [2019-01 → 2023-06]  Test [2023-07 → 2025-06]
Window 4: Train [2019-01 → 2024-06]  Test [2024-07 → 2026-02]
```

## Parameter grid (train sweep)
Same as exp34:
- compression_threshold: [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
- (6 configs — 1.0 = baseline equivalent)
- Select: best Sharpe on training period

## Fixed configs (from exp34 global optima)
- Fixed A: threshold=0.6 (best Sharpe)
- Fixed B: threshold=0.7 (best Sharpe/MDD balance)

## Procedure per window
1. **Train**: sweep 6 thresholds → select best by Sharpe
2. **Test**: run train-selected + fixed A + fixed B + baseline
3. Record: d_Sharpe, d_MDD, blocked count, blocked WR

## What to measure
Per window:
- Train-selected threshold
- Test d_Sharpe and d_MDD for selected, fixed A (0.6), fixed B (0.7)
- Blocked entries and blocked WR per test window
- vol_ratio_5_20 distribution at entry bars per window (is it regime-dependent?)

Aggregate:
- WFO win rate ≥ 3/4 AND mean d_Sharpe > 0
- Parameter stability (is threshold=0.6 or 0.7 consistently selected?)
- Blocked WR selectivity: is blocked WR < baseline WR in ALL windows?
  (If selectivity is robust, compression is genuinely informative)

## Critical question
Exp34 overturned the negative residual-scan prior: vol compression HAS
conditional entry timing value. If WFO confirms this, it means the
unconditional scan (residual_scan in explore.py) MISSES conditional signals.
This would be a methodological finding: features with zero unconditional
predictive power can still have conditional timing value within a strategy.

## Implementation notes
- Reuse exp34's run_backtest() with vol_ratio_5_20 gate
- Reuse exp30's WFO infrastructure
- Warmup: SLOW_PERIOD=120 bars (consistent with exp34's warmup)
  Note: vol_ratio_5_20 needs 20 bars warmup (trivially within 120)
- Cost: 50 bps RT

## Output
- Script: x39/experiments/exp42_vol_compression_wfo.py
- Results: x39/results/exp42_results.csv

## Result
_(to be filled by experiment session)_
