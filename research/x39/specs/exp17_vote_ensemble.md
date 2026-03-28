# Exp 17: Vote Ensemble (2/3 Agreement)

## Status: DONE

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

**FAIL**: No ensemble config improves Sharpe over E5 baseline. Voting filters OUT profitable E5 trades.

### Signal analysis
- E5: 23.5% of bars active, Gen4: 28.2%, Gen1: 54.0%
- Avg pairwise correlation r=0.378 (moderate — not truly independent)
- All 3 agree on only 11.3% of bars

### Full-period results (50 bps RT, warmup=168)

| Config          | Sharpe | CAGR %  | MDD %  | Trades | WR %  | Exp % | d_Sharpe |
|-----------------|--------|---------|--------|--------|-------|-------|----------|
| E5_baseline     | 1.332  | 60.0    | 51.3   | 219    | 41.6  | 43.0  | —        |
| Gen4_standalone | 0.596  | 17.7    | 70.3   | 400    | 30.0  | 44.3  | -0.736   |
| Gen1_standalone | -0.171 | -17.6   | 94.4   | 1056   | 26.1  | 51.9  | -1.503   |
| vote>=2         | 0.902  | 34.8    | 64.7   | 318    | 32.7  | 45.7  | -0.430   |
| vote>=3         | 1.173  | 45.4    | 55.3   | 168    | 42.3  | 35.8  | -0.160   |

### Trade quality by vote count (E5 trades only)

| Vote | Trades | Win Rate | Avg Ret |
|------|--------|----------|---------|
| 1    | 43     | 41.9%    | +2.10%  |
| 2    | 93     | 36.6%    | +2.13%  |
| 3    | 83     | 47.0%    | +2.86%  |

### Key observations
1. **Gen4 and Gen1 standalone are catastrophic with E5 exit** — their entry signals are not suited
   to trail stop + EMA cross-down exit. Gen1 produces 1056 trades at -17.6% CAGR.
2. **vote>=3 closest** (Sh 1.173, -0.16 vs E5) but loses on BOTH Sharpe AND MDD (55.3% vs 51.3%).
3. **vote>=2 much worse** (Sh 0.902) — adds Gen4/Gen1 noise entries that E5 exit cannot rescue.
4. Vote=3 trades ARE slightly higher quality (WR 47%, avg +2.86%) vs vote=1 (WR 41.9%, +2.10%),
   but the filter discards 43 profitable E5-only trades, and the 168 surviving trades don't compensate.
5. Signals are moderately correlated (r=0.38) — not independent enough for true diversification.
6. **Root cause**: Gen4/Gen1 signals are LESS informative than E5 on this data (proven in exp14/exp15).
   Requiring their agreement adds a noise gate that mostly blocks valid E5 entries.
