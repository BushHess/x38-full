# Exp 16: Hybrid — Gen4 C3 Entry + E5 Exit

## Status: PENDING

## Hypothesis
Gen4 C3 has potentially better entry logic (trade surprise + rangepos).
E5 has proven exit logic (robust ATR trail + EMA cross-down).
Gen4 C3's weakness: no trail stop, exits only on rangepos drop.
Combine: use Gen4's entry conditions but E5's exit mechanism.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Hybrid Specification
```python
# Entry (Gen4 C3 style):
#   trade_surprise_168 > 0
#   AND rangepos_168 > entry_thresh
#   AND d1_regime_ok  (keep E5's D1 EMA(21) for regime)

# Exit (E5 style):
#   close < peak - 3.0 * robust_atr
#   OR ema_fast < ema_slow
```

## Parameter sweep
- entry_thresh in [0.50, 0.55, 0.65]
- (3 configs. Trail + EMA exit are fixed from E5.)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs E5 baseline.
Also compare vs pure Gen4 C3 (exp14) and pure E5.

## Implementation notes
- Combines compute from both systems
- trade_surprise_168 needs linear regression fit (causal, first 2000 bars)
- rangepos_168 needs rolling 168-bar high/low
- EMA fast/slow and robust ATR computed as usual for exit
- D1 EMA(21) regime kept from E5 (Gen4 C3 uses D1 trade surprise instead,
  but keeping E5's D1 filter for cleaner comparison)

## Output
- Script: x39/experiments/exp16_hybrid_gen4_e5.py
- Results: x39/results/exp16_results.csv

## Result
_(to be filled by experiment session)_
