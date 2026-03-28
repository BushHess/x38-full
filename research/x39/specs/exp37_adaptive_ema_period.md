# Exp 37: Adaptive EMA Slow Period

## Status: PENDING

## Hypothesis
EMA slow_period=120 (20 days) is fixed. BTC exhibits distinctly different
regime characters: fast-trending (2020 Q4, 2024 Q4), slow-grinding (2023),
and choppy mean-reverting (2022).

In fast-trending regimes, a shorter EMA period is more responsive — captures
trend initiation sooner and detects reversals faster. In slow-grinding regimes,
a longer EMA period is more patient — avoids false crossovers in gentle trends.

This experiment tests whether adapting the EMA slow period to realized
volatility improves trend detection quality across regimes.

Mathematical motivation: the optimal smoothing parameter of a low-pass filter
depends on the signal-to-noise ratio. In high-vol (low SNR) environments,
more smoothing (longer period) reduces false signals. In low-vol (high SNR)
environments, less smoothing (shorter period) captures signals sooner.

Connection to slow_period plateau: x-series showed slow=60-144 is a plateau
(spread 0.017 Sharpe). This experiment tests whether SWITCHING within the
plateau based on regime beats any fixed value within it.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
realized_vol_84 = rolling_std(log_returns, 84) * sqrt(84)

# Volatility percentile over trailing window
rv_pctl[i] = percentile_rank(realized_vol_84[i], realized_vol_84[i-lb:i])

# Adaptive slow period (linear interpolation between min and max)
slow_period[i] = slow_min + rv_pctl[i] * (slow_max - slow_min)
#   low vol  (rv_pctl → 0): slow_period → slow_min (more responsive)
#   high vol (rv_pctl → 1): slow_period → slow_max (more patient)
```

## Modification to E5-ema21D1
REPLACE fixed EMA slow period with adaptive:
```python
# CRITICAL: adaptive EMA cannot use standard ema() since period varies.
# Implementation: at each bar, compute ema_slow with CURRENT slow_period
# using alpha = 2 / (slow_period + 1), applied recursively.
# This is mathematically equivalent to a time-varying smoothing filter.

# Original:
#   ema_slow = ema(close, 120)  # fixed period
#   ema_fast = ema(close, 30)   # fast = slow // 4

# Modified:
#   At bar i: slow_p = slow_min + rv_pctl[i] * (slow_max - slow_min)
#             alpha_s = 2.0 / (slow_p + 1)
#             ema_slow[i] = alpha_s * close[i] + (1 - alpha_s) * ema_slow[i-1]
#             fast_p = max(5, slow_p // 4)
#             alpha_f = 2.0 / (fast_p + 1)
#             ema_fast[i] = alpha_f * close[i] + (1 - alpha_f) * ema_fast[i-1]

# Entry/exit logic: same conditions as E5-ema21D1 (crossover, VDO, D1 regime)
```

## Parameter sweep
- slow_min: [60, 84]
  - Lower bound of plateau (from x-series slow sweep)
- slow_max: [120, 144, 168]
  - Upper bound of plateau
- rv_lookback (percentile window, H4 bars): [365]
  - Fixed at ~60 days to match ratr_pctl computation
- (2 × 3 = 6 configs)
- Plus: baseline (fixed slow=120) for comparison

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: distribution of effective slow_period over time. Mean slow_period
in bull vs bear regimes. Does the adaptation meaningfully change behavior?

## Implementation notes
- The time-varying EMA is NOT standard — it requires a custom recursive loop
- ema_fast period = max(5, slow_period // 4), also varies with slow_period
- rv_pctl requires 84 + 365 = 449 H4 bars warmup — within 365-day warmup
- The adaptive EMA is a DIFFERENT indicator than fixed EMA — comparison
  is against the fixed-EMA baseline, not against the same indicator
- This adds 0 tunable parameters at runtime (slow_min/slow_max are structural)
- Use explore.py's ema() for the fixed-period baseline comparison
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp37_adaptive_ema_period.py
- Results: x39/results/exp37_results.csv

## Result
_(to be filled by experiment session)_
