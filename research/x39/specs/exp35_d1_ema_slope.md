# Exp 35: D1 EMA Slope Confirmation

## Status: DONE

## Hypothesis
Current D1 regime filter is binary: close > D1 EMA(21) → regime OK.
This allows entries when price is above the EMA but the EMA itself is
DECLINING (late bear → early recovery, or false breakout above declining EMA).

Adding a slope requirement — D1 EMA must be RISING — filters entries where
the daily trend structure is still bearish even though price has temporarily
crossed above. A rising EMA confirms that the underlying trend has shifted,
not just that price spiked.

Mathematical motivation: the EMA is a low-pass filter. Its slope represents
the filtered trend direction. Requiring positive slope means the trend has
genuinely turned, not just that price crossed a declining moving average.
This is a second-order confirmation (direction of the direction indicator).

Connection to D1 EMA proven component: D1 EMA(21) regime is one of the
4 PROVEN components (p=1.5e-5, 16/16 ALL metrics). Adding slope to the
proven filter tests whether the binary version leaves value on the table.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
d1_ema21[i]       = ema(d1_close, 21)[i]
d1_ema_slope[i]   = (d1_ema21[i] - d1_ema21[i - slope_lookback]) / d1_ema21[i - slope_lookback]
d1_slope_ok[i]    = d1_ema_slope[i] > min_slope
```
slope_lookback controls how many D1 bars to look back for slope computation.
min_slope controls how steep the rise must be.

## Modification to E5-ema21D1
ADD slope requirement to D1 regime filter:
```python
# Original entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   where d1_regime_ok = d1_close > d1_ema21

# Modified entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok AND d1_slope_ok
#   where d1_regime_ok = d1_close > d1_ema21   (unchanged)
#         d1_slope_ok  = d1_ema_slope > min_slope  (NEW)

# Exit logic UNCHANGED: trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
- slope_lookback (D1 bars): [3, 5, 10, 15]
  - 3 = 3-day slope (responsive, noisy)
  - 15 = 15-day slope (smooth, laggy)
- min_slope: [0.0, 0.001, 0.005, 0.01]
  - 0.0 = just require non-declining EMA
  - 0.001 = ~0.1% rise over lookback period
  - 0.01 = ~1% rise over lookback period (aggressive)
- trail_mult: 3.0 (FIXED)
- (4 × 4 = 16 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: how many entries are blocked by slope requirement? D1 EMA slope
distribution at baseline entry bars. Entry delay (bars between d1_regime_ok
and d1_slope_ok becoming true simultaneously).

## Implementation notes
- D1 EMA slope must be computed on D1 bars then mapped to H4 grid
  using map_d1_to_h4() — same causal alignment as d1_regime_ok
- slope_lookback refers to D1 bars, NOT H4 bars
- d1_ema_slope[i] requires slope_lookback prior D1 bars — additional warmup
- Very high min_slope (0.01) with long lookback (15) is very restrictive:
  requires 1% EMA rise over 15 days, which only happens in strong trends
- Use explore.py helpers for consistency
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp35_d1_ema_slope.py
- Results: x39/results/exp35_results.csv

## Result

**Baseline** (365-day warmup): Sharpe 1.3098, CAGR 52.70%, MDD 41.01%, 197 trades.

### Best config: lb=3, ms=0.0

Only config improving BOTH Sharpe AND MDD:

| Metric | Baseline | lb=3, ms=0.0 | Delta |
|--------|----------|---------------|-------|
| Sharpe | 1.3098 | 1.3457 | +0.0359 |
| CAGR% | 52.70 | 54.41 | +1.71 |
| MDD% | 41.01 | 40.28 | -0.73 pp |
| Trades | 197 | 189 | -8 |
| Win rate | 40.6% | 41.3% | +0.7 pp |
| Blocked | — | 67 | — |
| Blocked WR | — | 34.3% | GOOD (< 40.6%) |

### Sweep summary (16 configs)

- **1/16 PASS** (lb=3, ms=0.0): Sharpe +0.036, MDD -0.73pp. Marginal.
- **0/16 PASS at ms>0**: every non-zero min_slope degrades Sharpe.
- **MDD-only improvements** (lb=10-15): MDD -1.2 to -4.9pp but Sharpe -0.02 to -0.12.
  Best MDD: lb=15, ms=0.005 → MDD 36.16% (-4.85pp) but Sharpe 1.2422 (-0.068).
- **Aggressive filtering kills returns**: lb=3, ms=0.01 → Sharpe 0.992 (-0.318), 128 trades.

### Slope distribution at baseline entries

Most baseline entries already have rising D1 EMA:
- lb=3: only 12.2% would be blocked at ms=0.0 (declining EMA at entry).
- lb=5: 25.4% blocked at ms=0.0. lb=10: 32.0%. lb=15: 30.5%.
- Median slope at entries: lb=3: 0.72%, lb=5: 1.21%, lb=10: 2.39%, lb=15: 3.54%.

### Entry delay (regime onset → slope onset)

Short lookback (lb=3) at ms=0.0: median 6 H4 bars (24h), 36/162 onsets missed entirely.
Longer lookbacks have higher missed rates (53-65/162) but lower median delay (0-6 bars)
because longer lookbacks smooth slope toward zero crossing.

### Selectivity

lb=3, ms=0.0 is the only config with clearly GOOD selectivity (blocked WR 34.3% < baseline 40.6%).
Most other configs block entries with WR ≈ 40-52% (similar to or worse than baseline).

### Conclusion

**MARGINAL PASS — not actionable.** The best config (lb=3, ms=0.0 = "require non-declining
D1 EMA") provides +0.036 Sharpe and -0.73pp MDD, blocking ~8 of 197 entries. The improvement
is real but too small to justify adding a parameter. The binary regime filter (price > EMA)
already captures nearly all the value.

The slope requirement generally HURTS because it introduces lag: by the time the EMA turns
upward, the best entries are already past. The D1 EMA is a lagging indicator; requiring its
DERIVATIVE to be positive adds a second layer of lag that filters out more good entries
than bad ones.

**Key insight**: D1 EMA regime filter's value comes from level (price > EMA), not slope.
Second-order confirmation (direction of direction) is too laggy for 4h-resolution entries.
