# Exp 46: Regime-Adaptive Maturity Decay

## Status: DONE

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

**FAIL**: No adaptive config beats fixed decay (60/180) on Sharpe. 0/9 configs improve.

### Key numbers

| Config | Sharpe | CAGR% | MDD% | Trades | d_Sh vs fixed |
|--------|--------|-------|------|--------|---------------|
| no_decay (baseline) | 1.3098 | 52.70 | 41.01 | 197 | -0.1498 |
| **fixed(60,180)** | **1.4596** | **58.11** | **31.19** | **263** | **0.0000** |
| LV(60,240)/HV(30,120) | 1.2902 | 49.11 | 32.86 | 274 | -0.1694 |
| LV(60,240)/HV(30,180) | 1.3503 | 52.41 | 34.73 | 262 | -0.1093 |
| LV(60,240)/HV(60,120) | 1.3935 | 54.54 | 32.86 | 267 | -0.0661 |
| LV(90,240)/HV(30,120) | 1.2685 | 48.00 | 34.39 | 272 | -0.1911 |
| LV(90,240)/HV(30,180) | 1.3329 | 51.51 | 36.21 | 260 | -0.1267 |
| LV(90,240)/HV(60,120) | 1.3716 | 53.39 | 34.39 | 265 | -0.0880 |
| LV(90,300)/HV(30,120) | 1.2311 | 46.11 | 34.39 | 271 | -0.2285 |
| LV(90,300)/HV(30,180) | 1.2899 | 49.28 | 36.21 | 260 | -0.1697 |
| LV(90,300)/HV(60,120) | 1.3338 | 51.43 | 34.39 | 264 | -0.1258 |

### Why it failed

1. **Faster HV decay HURTS**: All 9 configs show HV Sharpe worse than fixed
   (best HV Sharpe 2.18 vs fixed 2.33). In high-vol regimes, BTC trends are
   actually STRONG (HV Sharpe ~2x LV Sharpe) — tightening the trail sooner
   cuts the best alpha.

2. **Slower LV decay also HURTS**: 7/9 configs show LV Sharpe worse than fixed.
   Only LV(60,240)/HV(30,180) and LV(90,240)/HV(30,180) slightly improve LV
   Sharpe (+0.02, +0.06), but the HV degradation dominates.

3. **The hazard-rate hypothesis is wrong for BTC**: The assumption was that
   high-vol → higher trend termination hazard → faster decay optimal. But BTC
   trends in high-vol regimes are actually the MOST profitable (HV Sharpe 2.33
   vs LV Sharpe 1.10). Fixed decay (60/180) is already near-optimal because
   it gives ALL regimes uniform room, and the high-vol regime — where alpha
   concentrates — benefits from NOT being tightened prematurely.

4. **Regime split increases DOF without benefit**: 2 extra params (split the
   schedule) + 0 Sharpe gain = pure overfitting risk.

### Conclusion
Fixed decay (start=60, end=180) captures the optimal average across regimes.
Volatility-conditioned decay is a complexity increase with negative return.
The decay schedule does not need regime adaptation.
