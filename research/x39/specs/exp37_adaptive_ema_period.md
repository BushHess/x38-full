# Exp 37: Adaptive EMA Slow Period

## Status: DONE

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

**FAIL**: No adaptive EMA config improves Sharpe over fixed slow=120 baseline.

### Baseline
| Sharpe | CAGR% | MDD% | Trades | Win% | Exposure% |
|--------|-------|------|--------|------|-----------|
| 1.3098 | 52.70 | 41.01 | 197 | 40.6 | 43.5 |

### Sweep Results (delta vs baseline)

| Config | Sharpe | d_Sharpe | CAGR% | d_CAGR | MDD% | d_MDD | Trades | Mean Slow |
|--------|--------|----------|-------|--------|------|-------|--------|-----------|
| min=60/max=120 | 1.1095 | -0.2003 | 41.52 | -11.18 | 38.76 | -2.25 | 211 | 88.6 |
| min=60/max=144 | 1.2659 | -0.0439 | 49.74 | -2.96 | 38.83 | -2.18 | 202 | 100.1 |
| min=60/max=168 | 1.1666 | -0.1432 | 44.15 | -8.55 | 38.73 | -2.28 | 204 | 111.6 |
| min=84/max=120 | 1.2150 | -0.0948 | 47.25 | -5.45 | 40.27 | -0.74 | 199 | 101.2 |
| min=84/max=144 | 1.3071 | -0.0027 | 52.09 | -0.61 | 40.50 | -0.51 | 193 | 112.6 |
| min=84/max=168 | 1.3087 | -0.0011 | 51.90 | -3.38 | 37.63 | -3.38 | 189 | 124.1 |

### Key Findings

1. **All 6 adaptive configs lose Sharpe** vs fixed slow=120. Best: min=84/max=168 at -0.0011 (negligible).
2. **MDD improves for all configs** (−0.5 to −3.4 pp), but Sharpe cost eliminates the benefit.
3. **Adaptation direction is correct** — bull regimes get shorter periods (diff -1 to -3 bars),
   but the effect size is tiny (~2% of the period range).
4. **Best configs cluster near baseline**: min=84/max=144 and min=84/max=168 have mean slow
   ~113-124 (close to fixed 120), explaining near-zero delta.
5. **Wider adaptation hurts more**: min=60 configs lose 0.04-0.20 Sharpe. Shorter periods
   in low-vol regimes generate more false crossovers, not faster trend detection.

### Interpretation

The slow_period plateau (60-144, spread 0.017 Sharpe from x-series) means ALL fixed values
in this range perform similarly. Switching between them adds noise from the time-varying EMA
but captures no new information. The mathematical premise (SNR-dependent optimal smoothing)
is correct in theory but the regime signal (rv_pctl) doesn't separate trend-quality regimes
with enough precision — bull and bear mean slow periods differ by only 1-3 bars.

**Conclusion**: Fixed slow_period=120 remains optimal. Adaptive EMA is a tradeoff
(MDD improvement at Sharpe cost), not an improvement.
