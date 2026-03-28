# Exp 38: Trend Maturity Trail Decay

## Status: DONE

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

**Verdict: PASS** — best config improves BOTH Sharpe and MDD vs baseline.

### Baseline
Sharpe 1.3098, CAGR 52.70%, MDD 41.01%, 197 trades, exposure 43.5%.

### Best config: trail_min=1.5, decay_start=60, decay_end=180
| Metric       | Baseline | Best     | Delta     |
|--------------|----------|----------|-----------|
| Sharpe       | 1.3098   | 1.4596   | **+0.150**|
| CAGR%        | 52.70    | 58.11    | +5.41     |
| MDD%         | 41.01    | 31.19    | **-9.82** |
| Trades       | 197      | 263      | +66       |
| Win rate%    | 40.6     | 39.5     | -1.1      |
| Exposure%    | 43.5     | 40.3     | -3.2      |
| Avg bars held| 36.4     | 25.2     | -11.2     |
| Avg trend age at exit | 130.8 | 169.4 | +38.6  |
| Avg eff trail at exit | 3.000 | 2.193 | -0.807  |

### Runner-up: trail_min=1.5, decay_start=60, decay_end=240
Sharpe 1.4568 (+0.147), CAGR 58.21% (+5.51), MDD 32.70% (-8.31 pp).
Very close to best — longer decay window, similar performance.

### Key findings

1. **Decay works**: 11 of 18 configs improve Sharpe; 18 of 18 improve MDD.
   The trail_min=1.5, decay_start=60 family dominates (all 3 pass).

2. **MDD improvement is universal**: Every single decay config reduces MDD
   (range -2.89 to -9.82 pp). Tighter mature trails protect accumulated profits.

3. **Sharpe-MDD tradeoff by aggressiveness**:
   - trail_min=1.5: largest MDD gains but cuts some long-trade profit
   - trail_min=2.0: balanced — still +0.14 Sharpe, -8.23 MDD at best
   - trail_min=2.5: minimal effect, most configs degrade Sharpe

4. **Grace period matters**: decay_start=60 (10 days) consistently beats
   decay_start=30 (5 days). Early trends need full trail protection.

5. **Long-trade impact**: Decay cuts avg net return on top-10% duration
   trades by -6 to -11 pp (from +24.15% to +15-18%). More trades compensate
   — total P&L still higher because mid-duration trends captured better.

6. **Trade count increases**: Tighter trails create more exits → more
   re-entries on same trend. 197 → 263 trades at best config.

### Trend age statistics (eval window)
- Mean: 144.0 bars, Median: 93, P90: 359, Max: 711
- Decay window [60, 180] captures the bulk of trend maturation.
