# Exp 38: Trend Maturity Trail Decay

## Status: PENDING

## Hypothesis
VTREND's alpha is concentrated in the early/middle phase of trends. Fat-tail
analysis (x-series) shows top 5% of trades = 129.5% of profits. These are
typically early-trend entries that capture large moves.

As a trend matures (ema_fast > ema_slow for many bars), the probability of
continuation decreases and the probability of mean-reversion increases.
Tightening the trail stop as trend age increases captures accumulated profit
from long trends before the inevitable reversal.

This is NOT the same as exp29 (AND-gate trail tightener) which tightens based
on rangepos/trendq features. This experiment tightens based on TREND AGE —
a structural property of the trade, not a market feature.

Mathematical motivation: trend-following returns follow a heavy-tailed
distribution. Long-duration trends contribute disproportionately to total PnL
but also carry increasing reversal risk. An optimal exit policy should tighten
protection as the conditional probability of continued gains decreases with
duration (duration-based hazard rate).

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
# Trend age: bars since most recent EMA crossover (fast > slow)
trend_age[i] = bars since last ema_fast crossed above ema_slow

# Trail decay: trail_mult decreases linearly from base to minimum
# as trend_age increases from decay_start to decay_end
effective_trail[i] =
  if trend_age[i] < decay_start:
    trail_base                                    # no decay yet
  elif trend_age[i] >= decay_end:
    trail_min                                     # fully decayed
  else:
    trail_base - (trail_base - trail_min) * (trend_age - decay_start) / (decay_end - decay_start)
```

## Modification to E5-ema21D1
REPLACE fixed trail_mult with maturity-decaying trail:
```python
# Original exit:
#   trail_stop = peak - 3.0 * robust_atr
#   exit if close < trail_stop OR ema_fast < ema_slow

# Modified exit:
#   effective_trail = decay_function(trend_age, trail_base, trail_min,
#                                     decay_start, decay_end)
#   trail_stop = peak - effective_trail * robust_atr
#   exit if close < trail_stop OR ema_fast < ema_slow

# Entry logic UNCHANGED
```

## Parameter sweep
- trail_base: 3.0 (FIXED, same as baseline)
- trail_min: [1.5, 2.0, 2.5]
  - How tight does the trail get at full maturity
- decay_start (H4 bars): [30, 60]
  - When decay begins (~5 or ~10 days after crossover)
- decay_end (H4 bars): [120, 180, 240]
  - When trail reaches trail_min (~20, 30, or 40 days)
- Constraint: decay_start < decay_end
- (3 × 2 × 3 = 18 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: avg trend_age at exit. Distribution of effective_trail at exit.
Impact on longest trades (top 10% by duration) — does decay capture more
profit from these or cut them prematurely?

## Implementation notes
- trend_age resets to 0 when ema_fast drops below ema_slow
- In-trade: trend_age continues counting (doesn't reset on re-entry if
  the EMA crossover hasn't reversed)
- trail_min should never be < 1.0 (otherwise trail is tighter than 1 ATR)
- The decay is LINEAR — could test exponential in follow-up, but linear
  has fewer parameters
- decay_start provides a grace period for early trend development
- Use explore.py helpers for consistency
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp38_trend_maturity_decay.py
- Results: x39/results/exp38_results.csv

## Result
_(to be filled by experiment session)_
