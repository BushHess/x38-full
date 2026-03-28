# Exp 41: Momentum Acceleration Gate Walk-Forward Validation

## Status: DONE

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

**Verdict: FAIL** — Accel gate lacks temporal stability. exp33's +0.1515 Sharpe is period-specific.

### Parameter stability
lb=12, min_accel=0.0 selected in **4/4 windows** (perfectly STABLE). Fixed = selected in every window.

### WFO results (fixed = selected = lb=12, min_accel=0.0)
| Window | Test period | Baseline Sh | Gated Sh | d_Sharpe | d_MDD (pp) | Blocked | Blocked WR |
|--------|-------------|-------------|----------|----------|------------|---------|------------|
| W1 | 2021-07→2023-06 (bear-ish) | 0.4788 | 0.2101 | **-0.2687** | +0.00 | 237 | 18.1% |
| W2 | 2022-07→2024-06 (bear) | 0.6722 | 0.7368 | **+0.0646** | +3.57 | 288 | 26.0% |
| W3 | 2023-07→2025-06 (bull) | 1.7250 | 1.4461 | **-0.2789** | -1.15 | 271 | 46.9% |
| W4 | 2024-07→2026-02 (bull) | 0.9068 | 0.4403 | **-0.4665** | +8.83 | 168 | 53.6% |

- **WFO win rate**: 1/4 = 25% (FAIL, need ≥75%)
- **Mean d_Sharpe**: -0.2374 (FAIL, need >0)
- **Mean d_MDD**: +2.81 pp (worse)
- **Mean d_exposure**: -10.4 pp (gate blocks ~25% of exposure uniformly)

### Regime analysis
- Bear mean d_Sh: -0.1021
- Bull mean d_Sh: -0.3727
- **ASYMMETRIC**: gate hurts MORE in bull markets. Not bear-only benefit — it hurts everywhere.

### Critical insight
Blocked WR increases from 18.1% (W1, bear) to 53.6% (W4, bull). In bull markets the gate
blocks entries that would have been winners (blocked WR > baseline WR ~41%). The timing
mechanism from exp33 is an artifact of the training period composition, not a robust signal.

The gate reduces exposure by ~10pp uniformly but the entries it blocks are NOT selectively
bad — in bull regimes they're selectively GOOD. This is the opposite of useful timing.
