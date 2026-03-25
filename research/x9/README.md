# X9 — Break-Even Stop for E5+EMA21D1

**Date**: 2026-03-09
**Registry**: Study #46
**Verdict**: **REJECTED**

---

## Hypothesis

When unrealized profit reaches X×R (R = trail_mult × robust_ATR at entry),
moving the stop to entry price (breakeven) eliminates winning-to-losing trades.

**Counter-hypothesis**: ATR trail at mult=3.0 already provides organic breakeven
protection. Hard BE stop may whipsaw out of profitable trends prematurely.

## Variants

| Variant | Description |
|---------|-------------|
| E5 | E5+EMA21D1 baseline (no BE stop) |
| BE_0.8 | BE stop activates at 0.8R profit |
| BE_1.0 | BE stop activates at 1.0R profit |

## Tests

- T1: Full backtest (3 variants × 3 cost scenarios)
- T2: Timescale robustness (16 slow_periods)
- T3: Bootstrap VCBB (500 paths, head-to-head)
- T4: BE threshold sweep (0.4R to 2.5R, step 0.2)
- T5: Trade anatomy (per-trade MFE in R units)
- T6: Organic BE analysis (does ATR trail already protect at 1R?)

## Results (harsh cost, 50 bps RT)

| Variant | Sharpe | CAGR | MDD | Trades |
|---------|--------|------|-----|--------|
| E5 (baseline) | 1.430 | 59.85% | 41.64% | 186 |
| BE_0.8 | 1.409 (-0.021) | 58.48% | 41.64% | 189 |
| BE_1.0 | 1.428 (-0.002) | 59.73% | 41.64% | 187 |

## Conclusion

Marginal differences — BE adds nothing. Counter-hypothesis confirmed:
ATR trail at mult=3.0 already provides organic breakeven protection.
The BE stop is redundant with the trailing stop mechanism.

## Artifacts

- `benchmark.py` — study code
- `x9_results.json` — full results
- `x9_backtest_table.csv`, `x9_be_sweep.csv`, `x9_bootstrap_table.csv`, `x9_timescale_table.csv`
