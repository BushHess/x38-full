# Exp 15: E5-ema21D1 vs Gen1 V6 Head-to-Head

## Status: PENDING

## Hypothesis
Gen1 V6 (S3_H4_RET168_Z0) is gen1's frozen winner. Extremely simple:
ret_168 > 0 → long, else flat. One feature, one threshold.
Compare with E5-ema21D1 on same data, same cost.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Gen1 V6 Specification
From x37/resource/gen1/v6_ret168/spec:
```
Feature: ret168 = close_t / close_(t-168) - 1
Signal:  long if ret168 > 0, else flat
Entry:   signal changes 0→1 at close → buy at next open
Exit:    signal changes 1→0 at close → sell at next open
Position: 100% long or 100% flat
Cost: 20 bps RT (gen1 default) — BUT run at 50 bps for fair comparison
```
No trail stop. No VDO. No D1 regime. Just one momentum quantity.

## E5-ema21D1 (reference)
Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## What to compare
Run BOTH on same data (2019-01-01 to 2026-02-20, warmup=365).
Same cost (50 bps RT).

Metrics: Sharpe, CAGR, MDD, trades, win rate, exposure, Calmar.
Regime breakdown.

Gen1 V6 caveat: reserve CAGR was -5.75% in gen1's own test.
This experiment re-runs on full data to see current picture.

## Implementation notes
- Trivially simple to implement
- ret_168 needs 168 H4 bars warmup
- No trail stop = potentially much worse drawdowns
- Fewer parameters = less overfitting risk

## Output
- Script: x39/experiments/exp15_vs_gen1v6.py
- Results: x39/results/exp15_results.csv

## Result
_(to be filled by experiment session)_
