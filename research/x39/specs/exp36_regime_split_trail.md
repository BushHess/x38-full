# Exp 36: Regime-Split Trail Multiplier

## Status: PENDING

## Hypothesis
Exp30 showed the AND gate works in bear (W1/W2) but hurts in bull (W3/W4).
This is the fundamental WFO failure: mechanisms that help in one regime
destroy alpha in the other.

The root cause may be simpler: trail_mult=3.0 is a COMPROMISE between regimes.
In low-volatility trending markets (bull), a tighter trail captures more
profit before reversal. In high-volatility markets (bear/chop), a wider
trail prevents whipsaw exits.

Rather than adding filters or exit signals, this experiment tests whether
ADAPTING the core trail parameter to volatility regime improves robustness.
The adaptation is deterministic (no model fitting) — just reading current
volatility and adjusting trail width proportionally.

Mathematical motivation: trail_mult defines the noise bandwidth the strategy
tolerates. Volatility IS the noise. A fixed bandwidth in varying noise is
suboptimal by definition — the optimal bandwidth scales with noise level.
This is analogous to a Kalman filter's measurement noise parameter.

Connection to trail sweep (x-series): trail_mult 2.0-5.0 showed monotonic
return/risk tradeoff. This experiment tests whether SWITCHING trail_mult
based on volatility beats any fixed value.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
ratr_pct[i] = robust_atr[i] / close[i]

# Volatility percentile over trailing 365 bars (~60 days)
ratr_pctl[i] = percentile_rank(ratr_pct[i], ratr_pct[i-365:i])

# Regime classification
low_vol[i]  = ratr_pctl[i] < vol_split   # below median → tighter trail
high_vol[i] = ratr_pctl[i] >= vol_split   # above median → wider trail
```

## Modification to E5-ema21D1
REPLACE fixed trail_mult with regime-adaptive trail:
```python
# Original exit:
#   trail_stop = peak - 3.0 * robust_atr
#   exit if close < trail_stop OR ema_fast < ema_slow

# Modified exit:
#   IF low_vol:  trail_stop = peak - trail_low * robust_atr
#   IF high_vol: trail_stop = peak - trail_high * robust_atr
#   exit if close < trail_stop OR ema_fast < ema_slow

# Entry logic UNCHANGED
```

## Parameter sweep
- vol_split (percentile threshold): [0.50]
  - Fixed at median — symmetric split, no optimization of split point
- trail_low (low-vol trail mult): [2.0, 2.5, 3.0]
- trail_high (high-vol trail mult): [3.0, 3.5, 4.0, 4.5]
- Constraint: trail_low <= trail_high (tighter in low-vol, wider in high-vol)
- Valid combos: (2.0, 3.0), (2.0, 3.5), (2.0, 4.0), (2.0, 4.5),
                (2.5, 3.0), (2.5, 3.5), (2.5, 4.0), (2.5, 4.5),
                (3.0, 3.0), (3.0, 3.5), (3.0, 4.0), (3.0, 4.5)
- (12 configs)
- Note: (3.0, 3.0) = baseline equivalent (sanity check)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: exits per regime (low-vol vs high-vol). Average trail width in each
regime. Does the adaptation reduce the bull/bear asymmetry seen in exp30?

## Implementation notes
- ratr_pctl requires 365 H4 bars of history — within warmup period
- Trail multiplier can CHANGE during a trade if vol regime shifts. This is
  intentional: the trail adapts to current conditions, not entry conditions
- vol_split=0.50 is fixed to avoid overfitting the split point. If results
  are positive, a follow-up can test sensitivity to split point.
- Use explore.py's robust_atr() for consistency
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp36_regime_split_trail.py
- Results: x39/results/exp36_results.csv

## Result
_(to be filled by experiment session)_
