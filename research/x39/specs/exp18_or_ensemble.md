# Exp 18: OR Ensemble (Any Signal Enters)

## Status: PENDING

## Hypothesis
Opposite of exp17. Instead of requiring agreement, enter when ANY signal fires.
Exit when ALL signals say exit. This MAXIMIZES exposure — captures every
opportunity that any system identifies.

If the three systems identify DIFFERENT good moments, OR ensemble captures
alpha that any single system would miss. Risk: more false entries.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Ensemble Logic
```python
# Three independent entry signals:
sig_e5   = ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
sig_gen4 = trade_surprise_168 > 0 AND rangepos_168 > 0.55
sig_gen1 = ret_168 > 0

# Entry: ANY signal fires (not already in position)
enter = sig_e5 OR sig_gen4 OR sig_gen1

# Exit: use E5 exit (trail + EMA cross) AND no other signal is active
# i.e., exit only when E5's exit triggers AND gen4/gen1 would also be flat
exit_e5 = close < trail_stop OR ema_fast < ema_slow
exit_gen4 = rangepos_168 < 0.35
exit_gen1 = ret_168 < 0
exit = exit_e5 AND exit_gen4 AND exit_gen1
```

## Parameter sweep (3 configs)
```
Config 1 (Version A): Entry=any, Exit=all-agree + trail stop
  exit = (exit_e5 AND exit_gen4 AND exit_gen1)
  trail_stop = peak - 3.0 * robust_atr (active)

Config 2 (Version A-notrail): Entry=any, Exit=all-agree, NO trail stop
  exit = (exit_e5_trend AND exit_gen4 AND exit_gen1)
  trail_stop = disabled (test if trail is redundant with multi-signal exit)

Config 3 (Version B): Entry=any, Exit=E5 only
  exit = close < trail_stop OR ema_fast < ema_slow
  (ignore gen4/gen1 for exit, simplest version)
```

## What to measure
Sharpe, CAGR, MDD, trades, win rate, exposure%. Delta vs E5 baseline.
Exposure will likely be MUCH higher than E5 alone.

## Implementation notes
- More trades = more cost drag (50 bps RT each)
- Position management: once in, don't re-enter. Only track entry/exit transitions.
- Compare exposure: E5 alone ≈ 44.5%. OR ensemble may be 60-80%.

## Output
- Script: x39/experiments/exp18_or_ensemble.py
- Results: x39/results/exp18_results.csv

## Result
_(to be filled by experiment session)_
