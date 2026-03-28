# Exp 14: E5-ema21D1 vs Gen4 C3 Head-to-Head

## Status: PENDING

## Hypothesis
Gen4 C3 (btcsd_20260318_c3_trade4h15m) is gen4's champion strategy.
It uses completely different features: D1 trade surprise + H4 rangepos + 15m relvol.
Never compared head-to-head with E5-ema21D1 using SAME data and cost model.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Gen4 C3 Specification
From x37/resource/gen4/state_pack_v1:
```
Entry (ALL must be true):
  1. d1_trade_surprise168 > 0  (D1 participation permission)
  2. h4_rangepos168 > entry_thresh  (H4 trend context)
  3. m15_relvol168 > relvol_thresh  (15m activity timing)

Exit:
  h4_rangepos168 < hold_thresh  (H4 range position drops)

Position: 100% long or 100% flat
Cost: 50 bps RT (for comparison)
```

Champion config (cfg_025):
- entry_thresh: 0.55, hold_thresh: 0.35, relvol_thresh: 1.10

## E5-ema21D1 (reference)
Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## What to compare
Run BOTH strategies on same data (2019-01-01 to 2026-02-20, warmup=365).
Same cost (50 bps RT harsh).

Metrics: Sharpe, CAGR, MDD, trades, win rate, exposure, Calmar.
Regime breakdown: bull (2020-2021), bear (2022), recovery (2023-2024), recent (2025-2026).

## Implementation notes
- Gen4 C3 needs 15m data for m15_relvol168. Check if 15m bars are available in dataset.
  If not, this experiment uses H4-only variant (drop 15m timing, use only D1+H4).
- Gen4 C3 trade_surprise needs fitted model. Use same approach as exp04.
- Gen4 C3 has NO trail stop. Exit is purely rangepos < hold_thresh.
  This is a fundamental architectural difference from E5.

## Output
- Script: x39/experiments/exp14_vs_gen4c3.py
- Results: x39/results/exp14_results.csv

## Result
_(to be filled by experiment session)_
