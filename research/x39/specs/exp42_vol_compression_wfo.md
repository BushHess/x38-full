# Exp 42: Volatility Compression Entry Walk-Forward Validation

## Status: DONE

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

**VERDICT: PASS** — Vol compression gate has temporal stability across all 4 WFO windows.

### WFO Results (all 3 configs PASS: 4/4 win rate AND mean d_Sharpe > 0)

| Config | WFO Win Rate | Mean d_Sharpe | Mean d_MDD |
|--------|-------------|---------------|------------|
| Train-selected | 4/4 (100%) | +0.1703 | -2.05 pp |
| Fixed A (0.6) | 4/4 (100%) | +0.2625 | -4.65 pp |
| Fixed B (0.7) | 4/4 (100%) | +0.2532 | -4.75 pp |

### Per-window detail (Fixed A = 0.6)

| Window | Test Period | d_Sharpe | d_MDD | Blocked | Blocked WR | Baseline WR |
|--------|------------|----------|-------|---------|------------|-------------|
| W1 (bear-ish) | 2021-07→2023-06 | +0.3973 | -10.00 pp | 69 | 23.2% | 34.7% |
| W2 (bear) | 2022-07→2024-06 | +0.3037 | -3.55 pp | 86 | 32.6% | 34.4% |
| W3 (bull) | 2023-07→2025-06 | +0.1634 | -4.30 pp | 68 | 33.8% | 45.6% |
| W4 (bull) | 2024-07→2026-02 | +0.1857 | -0.76 pp | 43 | 32.6% | 43.9% |

### Key findings

1. **Parameter stability: STABLE** — threshold=0.6 selected 3/4 windows (W1 picked 0.9, others 0.6).
2. **Selectivity: ALL SELECTIVE** — blocked entry WR < baseline WR in ALL 4 windows.
   Blocked entries are genuinely worse trades, not random filtering.
3. **Regime-robust**: Helps in both bear (+0.35 mean d_Sh) and bull (+0.17 mean d_Sh).
   Bear windows benefit more (larger losers to block), but bull windows still positive.
4. **vol_ratio distribution is stable**: median ~0.47, <0.6 fraction ~61%, <0.7 fraction ~68-70%
   across all windows. No regime-dependent skew in the feature distribution itself.
5. **Fixed A (0.6) > Fixed B (0.7)** on Sharpe (+0.2625 vs +0.2532) but B wins slightly on MDD
   (-4.75 vs -4.65 pp). Both are excellent.

### Methodological finding
Unconditional residual scan (explore.py) showed zero predictive power for vol_ratio_5_20.
Yet within E5-ema21D1, it has strong CONDITIONAL timing value — preferentially blocking
entries that would have been losers. Features with zero marginal correlation can still
have conditional value within a strategy context.
