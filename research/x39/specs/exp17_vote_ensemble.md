# Exp 17: Vote Ensemble (2/3 Agreement)

## Status: PENDING

## Hypothesis
Three independent signal systems exist:
- E5: EMA crossover + VDO + D1 EMA(21)
- Gen4: trade_surprise + rangepos_168
- Gen1: ret_168 > 0

If they tap partially independent alpha, requiring 2/3 agreement should
produce higher-quality entries with fewer false signals.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Ensemble Logic
```python
# Compute three independent entry signals (boolean):
sig_e5   = ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
sig_gen4 = trade_surprise_168 > 0 AND rangepos_168 > 0.55
sig_gen1 = ret_168 > 0

# Entry: at least 2 of 3 agree
vote = int(sig_e5) + int(sig_gen4) + int(sig_gen1)
enter = vote >= 2

# Exit: E5's exit (trail stop + EMA cross-down)
# Exit is NOT by vote — once in, use proven exit mechanism
```

## Parameter sweep
- vote_threshold in [2, 3]  (majority vs unanimous)
- (2 configs)
- Also run each signal system standalone as reference

## What to measure
- Ensemble metrics: Sharpe, CAGR, MDD, trades, win rate, exposure
- Per-signal overlap: how often do signals agree? Correlation matrix.
- Quality: what is the win rate of trades where all 3 agree vs only 2?
- Delta vs E5 baseline

## Implementation notes
- Three signals computed independently
- Exit uses E5's mechanism regardless of which signals triggered entry
- If signals are highly correlated, ensemble adds nothing.
  Measure signal correlation FIRST before interpreting results.

## Output
- Script: x39/experiments/exp17_vote_ensemble.py
- Results: x39/results/exp17_results.csv

## Result
_(to be filled by experiment session)_
