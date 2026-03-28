# Exp 30: AND-Gate Walk-Forward Validation

## Status: PENDING

## Hypothesis
Exp22's AND gate (rp=0.20, tq=-0.10) was optimized on FULL SAMPLE data
(2019-01 to 2026-02). All x39 experiments share this problem: parameter
selection and performance measurement use the same data. This creates
selection bias — we picked the best of 16 configs (exp22) on full data.

Walk-forward validation (WFO) tests whether the AND gate parameters
discovered in one period STILL WORK in the next unseen period. If the
AND gate passes WFO, the +0.057 Sharpe improvement has temporal stability.
If it fails, the improvement is period-specific.

This is CRITICAL before any further building on the AND gate. Exp25/26/27
test parameter robustness (space dimension). Exp30 tests temporal robustness
(time dimension). Both must pass for the mechanism to be credible.

Note: this uses x39's simplified replay (explore.py), not the full v10
validation pipeline. The result is DIAGNOSTIC, not authoritative — but a
WFO failure here would kill the AND gate line regardless.

## Baseline
E5-ema21D1 (simplified replay): full-sample ~1.2965 Sharpe, ~221 trades.

## WFO Design
**Anchored walk-forward**: training window grows, test window fixed at ~2 years.

```
Window 1:  Train [2019-01 → 2021-06]  Test [2021-07 → 2023-06]
Window 2:  Train [2019-01 → 2022-06]  Test [2022-07 → 2024-06]
Window 3:  Train [2019-01 → 2023-06]  Test [2023-07 → 2025-06]
Window 4:  Train [2019-01 → 2024-06]  Test [2024-07 → 2026-02]
```

4 windows. Train expands (anchored at 2019-01). Test is 2 years (except
window 4: ~20 months due to data end).

## Features
```
rangepos_84[i] = (close[i] - rolling_low_84[i]) / (rolling_high_84[i] - rolling_low_84[i])
trendq_84[i]   = ret_84[i] / realized_vol_84[i]
```

## Procedure per window

**Step 1: Train** — Run the exp22 parameter grid on the TRAINING period:
- rp_threshold in [0.15, 0.20, 0.25, 0.30]
- tq_threshold in [-0.30, -0.10, 0.10, 0.30]
- (16 configs, same as exp22)
- Select best config by highest Sharpe on training period.

**Step 2: Test** — Apply the train-selected config on the TEST period:
- Run E5-ema21D1 + AND gate with train-selected thresholds
- Run E5-ema21D1 baseline (no AND gate) on same test period
- Record: d_Sharpe = AND_test_sharpe - baseline_test_sharpe

**Step 3: Also test the fixed (rp=0.20, tq=-0.10)** on the TEST period
(no training selection — uses exp22's global optimum directly).

## What to measure
Per window:
- Train-selected config: which (rp, tq) was chosen?
- Test period: AND gate Sharpe, baseline Sharpe, d_Sharpe
- Test period: AND gate MDD, baseline MDD, d_MDD
- Trade count and AND gate exits in test period
- Fixed (0.20, -0.10) test performance (for comparison)

Aggregate:
- **WFO win rate**: # windows where AND gate beats baseline / 4
  - Target: >= 3/4 (75%)
- **WFO mean d_Sharpe**: average d_Sharpe across 4 test windows
  - Target: > 0 (positive on average)
- **Parameter stability**: are train-selected configs consistent across
  windows, or does optimal (rp, tq) jump around?
  - Stable = robust mechanism. Jumping = overfit to training period.
- **Fixed vs selected**: does fixed (0.20, -0.10) match or beat
  train-selected on test periods? If yes → parameter is stable.
  If no → optimal config is period-dependent.

## Implementation notes
- Use exp22 code as base. Add outer loop for WFO windows.
- Warmup of 365 days applies WITHIN each window. Bars before warmup
  boundary are used for indicator computation but not for trading.
- For Window 1 (train 2019-01→2021-06): only ~2.5 years of trading
  data after warmup. May have few trades (~50-80). Accept low power.
- For Window 4 (test 2024-07→2026-02): ~20 months. May have fewer
  trades than typical 2-year window.
- Split by DATE, not by bar index. Use datetime column from H4 data.
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Feature warmup (84 bars, 365 days) means effective trading start is
  later than nominal window start. Track actual trade count per window.

## Output
- Script: x39/experiments/exp30_and_gate_walk_forward.py
- Results: x39/results/exp30_results.csv

## Result
_(to be filled by experiment session)_
