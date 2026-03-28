# Exp 46: Regime-Adaptive Maturity Decay

## Status: PENDING

## Hypothesis
Exp38's maturity decay uses FIXED decay parameters (start=60, end=180).
But trend duration is regime-dependent:
- High-vol regimes (2022 bear): trends are shorter, choppier → faster decay
- Low-vol regimes (2023 grind): trends persist longer → slower decay

Exp36 showed regime-split trail is marginal (+0.026 Sharpe). But exp36
split the trail MULTIPLIER, not the DECAY SCHEDULE. This experiment
splits the DECAY RATE instead — a fundamentally different adaptation.

In high-vol: shorter decay window (e.g., start=30, end=120) → protect
profits sooner because trends reverse faster.
In low-vol: longer decay window (e.g., start=90, end=240) → give
persistent trends more room because reversals are gradual.

This tests whether volatility-conditioned decay schedule improves on
fixed decay. If yes → the mechanism is regime-aware AND robust.
If no → fixed decay already captures the optimal average.

Mathematical motivation: the hazard rate of trend termination depends on
volatility. Higher volatility → higher hazard rate → faster optimal decay.
A fixed decay averages over regimes, which is suboptimal when the hazard
rates differ significantly. Regime-adaptive decay matches the decay
schedule to the current conditional hazard rate.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades.
E5-ema21D1 + fixed decay (exp38 best): ~1.46 Sharpe.

## Feature
```
ratr_pct[i] = robust_atr[i] / close[i]
ratr_pctl[i] = percentile_rank(ratr_pct[i], ratr_pct[i-365:i])
high_vol[i] = ratr_pctl[i] >= 0.50  # above-median volatility
```

## Modification to E5-ema21D1 + exp38
```python
# Entry: UNCHANGED (standard E5-ema21D1)

# Exit: regime-adaptive decay
if high_vol:
    eff_trail = decay(trend_age, 3.0, trail_min, start_hv, end_hv)
else:
    eff_trail = decay(trend_age, 3.0, trail_min, start_lv, end_lv)

trail_stop = peak - eff_trail * robust_atr
exit if close < trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
- trail_min: 1.5 (FIXED at exp38 optimum)
- vol_split: 0.50 (FIXED at median, same as exp36)
- Low-vol schedule (start_lv, end_lv):
  [(60, 240), (90, 240), (90, 300)]  # slower decay
- High-vol schedule (start_hv, end_hv):
  [(30, 120), (30, 180), (60, 120)]  # faster decay
- (3 × 3 = 9 regime-adaptive configs)
- Plus: fixed decay baseline (start=60, end=180 for BOTH regimes)
- Plus: no-decay baseline
- (11 total)

## What to measure
Sharpe, CAGR%, MDD%, trades, exposure%.
Delta vs no-decay baseline, delta vs fixed-decay baseline.

Key analysis:
1. Does ANY adaptive config beat fixed (60/180)? By how much?
2. Per-regime breakdown: low-vol Sharpe vs high-vol Sharpe for each config
3. Trade count and holding period per regime
4. Does faster high-vol decay prevent the losses that fixed decay misses?
5. Does slower low-vol decay capture more of the persistent trend alpha?

## Implementation notes
- Combine exp38's trend_age + effective_trail with exp36's ratr_pctl
- ratr_pctl needs 365 H4 bars history → within 365-day warmup
- vol regime can CHANGE during a trade: if vol regime shifts from low to
  high mid-trade, the decay schedule switches. This is intentional.
- Use median split (0.50) to avoid overfitting the split point
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp46_regime_adaptive_decay.py
- Results: x39/results/exp46_results.csv

## Result
_(to be filled by experiment session)_
