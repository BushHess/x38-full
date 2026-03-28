# Exp 18: OR Ensemble (Any Signal Enters)

## Status: DONE

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

**FAIL**: All 3 OR-ensemble configs degrade Sharpe vs E5 baseline. OR entry floods the system with low-quality Gen1/Gen4 entries that E5's exit mechanism cannot rescue.

### Signal analysis
- E5: 23.5% of bars active, Gen4: 28.2%, Gen1: 54.0%
- ANY signal (OR): 58.6% of bars — massive expansion vs E5 alone
- Avg pairwise correlation r=0.378 (moderate)
- Exclusive non-E5 bars: 21.3% (Gen1-only 19.1%, Gen4-only 2.2%)

### Entry source quality (OR entries, E5 exit)
- E5 active at entry: 73 trades, WR 42.5%, avg ret +1.82%
- E5 NOT active: 1094 trades, WR 24.8%, avg ret **-0.19%**
- Gen1-only entries: 859 trades, WR 24.7%, avg ret -0.27% — catastrophic noise
- All-3-agree: 9 trades, WR 77.8%, avg ret +4.44% (but too few to matter)

### Full-period results (50 bps RT, warmup=168)

| Config           | Sharpe | CAGR %  | MDD %  | Trades | WR %  | Avg Held | Exp % | d_Sharpe |
|------------------|--------|---------|--------|--------|-------|----------|-------|----------|
| E5_baseline      | 1.332  | 60.0    | 51.3   | 219    | 41.6  | 36.3     | 43.0  | —        |
| A_all_agree_exit | 0.922  | 41.1    | 67.8   | 143    | 21.7  | 82.6     | 63.8  | -0.410   |
| A_notrail        | 0.924  | 41.5    | 68.4   | 133    | 22.6  | 89.7     | 64.5  | -0.408   |
| B_e5_exit        | -0.311 | -23.6   | 97.2   | 1167   | 25.9  | 8.7      | 55.2  | -1.643   |

### Key observations
1. **Config B (E5 exit) is catastrophic** — 1167 trades at -23.6% CAGR, MDD 97.2%. Gen1-only entries churn through the trail stop at massive cost.
2. **Configs A/A-notrail survive** (Sh ~0.92) only because all-agree exit DELAYS exits — avg 83-90 bars held vs E5's 36. This raises exposure to 64% but at worse risk-adjusted return.
3. **Trail stop is irrelevant in A-mode**: A vs A-notrail nearly identical (Sh 0.922 vs 0.924). When exit requires gen4+gen1 agreement, the trail rarely binds.
4. **Root cause**: 94% of OR-exclusive entries (1094/1167) come without E5 confirmation. These have WR 24.8% and avg ret -0.19% — pure noise at 50 bps cost.
5. **OR ensemble fails for the INVERSE reason exp17 failed**: exp17's AND filter removed good E5 trades. exp18's OR adds bad non-E5 trades. E5's entry signal IS the alpha — Gen4/Gen1 contribute noise, not independent alpha.
6. **Combined conclusion from exp17+exp18**: E5 entry signal is strictly dominant. Neither filtering (AND) nor expanding (OR) improves it. Gen4/Gen1 signals are not independent sources of alpha on this dataset.
