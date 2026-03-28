# Exp 32: Pullback-in-Trend Entry

## Status: DONE

## Hypothesis
Current EMA crossover fires at trend initiation — price has already moved
significantly by the time ema_fast crosses above ema_slow. After a trail/trend
exit, re-entry requires ANOTHER crossover which may occur much later (or never)
in the same macro trend.

A pullback entry enters when price retraces to ema_fast WITHIN an established
uptrend (ema_fast > ema_slow sustained for N bars). This captures re-entries
at better prices without waiting for a new crossover.

Mathematical motivation: buying at a lower price within the same trend improves
the risk/reward ratio of each trade. The trail stop distance (3.0 * RATR) is
the same, but entry is closer to support (ema_fast), so the reward-to-risk
per unit of trail risk is higher.

Key question: does pullback timing add value, or does VTREND's original
crossover timing already capture the relevant alpha?

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
# Trend establishment: ema_fast > ema_slow for at least N consecutive bars
trend_age[i] = consecutive bars where ema_fast > ema_slow up to bar i
established[i] = trend_age[i] >= N

# Pullback condition: close touches or dips below ema_fast
pullback[i] = close[i] <= ema_fast[i] * (1 + pullback_margin)
```

## Modification to E5-ema21D1
REPLACE entry condition with pullback logic:
```python
# Original entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   (fires once at crossover)

# Modified entry (two modes):
# MODE 1 — Standard crossover (unchanged):
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   (first entry into a new trend)
#
# MODE 2 — Pullback re-entry (NEW):
#   IF NOT in_position AND trend_age >= N AND pullback AND vdo > 0 AND d1_regime_ok:
#     → enter at pullback price
#
# Exit logic UNCHANGED: trail_stop OR ema_fast < ema_slow
# When ema_fast < ema_slow: trend_age resets to 0, MODE 2 disabled
```

## Parameter sweep
- N (trend establishment bars): [12, 24, 36, 48]
- pullback_margin: [0.0, 0.005, 0.01]
  - 0.0 = close <= ema_fast exactly
  - 0.005 = close <= ema_fast * 1.005 (0.5% above ema_fast still counts)
  - 0.01 = close <= ema_fast * 1.01 (1% above ema_fast)
- trail_mult: 3.0 (FIXED)
- (4 × 3 = 12 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: how many entries are MODE 1 (crossover) vs MODE 2 (pullback)?
Average entry price improvement (MODE 2 entry price vs what MODE 1 would have been).

## Implementation notes
- trend_age must reset to 0 when ema_fast drops below ema_slow
- After a MODE 2 entry + exit (trail/trend), the strategy can MODE 2 again
  if trend_age still >= N (trend hasn't reversed)
- pullback_margin prevents requiring exact touch — EMA is smooth so price
  often bounces slightly above
- Use explore.py's ema() for consistency with baseline
- Warmup: 365 days (same as baseline)
- Cost: 50 bps RT (harsh)

## Output
- Script: x39/experiments/exp32_pullback_entry.py
- Results: x39/results/exp32_results.csv

## Result

**Verdict: FAIL** (marginal, not actionable)

### Baseline (standard E5-ema21D1 replay)
Sharpe 1.2965, CAGR 57.77%, MDD 51.32%, 221 trades, exposure 43.0%

### Sweep results (12 configs: 4 N × 3 margin)

| N  | margin | Sharpe | d_Sharpe | CAGR%  | d_CAGR  | MDD%  | d_MDD  | Trades | M1 | M2  |
|----|--------|--------|----------|--------|---------|-------|--------|--------|----|-----|
| 12 | 0.000  | 1.2320 | -0.0645  | 45.36  | -12.41  | 47.38 | -3.94  | 155    | 46 | 109 |
| 12 | 0.005  | 1.2018 | -0.0947  | 44.66  | -13.11  | 47.65 | -3.67  | 166    | 46 | 120 |
| 12 | 0.010  | 1.2314 | -0.0651  | 47.68  | -10.09  | 47.26 | -4.06  | 174    | 46 | 128 |
| 24 | 0.000  | 1.2552 | -0.0413  | 46.30  | -11.47  | 46.21 | -5.11  | 151    | 46 | 105 |
| 24 | 0.005  | 1.2728 | -0.0237  | 48.16  | -9.61   | 44.48 | -6.84  | 160    | 46 | 114 |
| 24 | 0.010  | 1.2996 | +0.0031  | 51.08  | -6.69   | 43.55 | -7.77  | 167    | 46 | 121 |
| 36 | 0.000  | 1.2533 | -0.0432  | 45.97  | -11.80  | 43.77 | -7.55  | 148    | 46 | 102 |
| 36 | 0.005  | 1.2084 | -0.0881  | 44.37  | -13.40  | 45.85 | -5.47  | 156    | 46 | 110 |
| 36 | 0.010  | 1.2356 | -0.0609  | 47.18  | -10.59  | 46.82 | -4.50  | 162    | 46 | 116 |
| 48 | 0.000  | 1.2067 | -0.0898  | 43.09  | -14.68  | 43.46 | -7.86  | 145    | 46 | 99  |
| 48 | 0.005  | 1.1326 | -0.1639  | 40.10  | -17.67  | 45.55 | -5.77  | 153    | 46 | 107 |
| 48 | 0.010  | 1.2229 | -0.0736  | 46.31  | -11.46  | 46.53 | -4.79  | 159    | 46 | 113 |

### Key findings

1. **Best config (N=24, margin=0.01)**: Sharpe +0.003, MDD -7.77 pp — technically both improve
   but Sharpe gain is negligible (+0.2%) and CAGR drops -6.69 pp. Not actionable.

2. **11/12 configs DEGRADE Sharpe**. The only "improvement" is +0.003 — noise-level.

3. **CAGR drops in ALL 12 configs** (6.69 to 17.67 pp). Pullback timing loses absolute returns.

4. **MDD improves in ALL 12 configs** (3.67 to 7.86 pp). The mechanism IS a risk reducer,
   but at unacceptable CAGR cost.

5. **MODE 1 drops from 221 → 46 entries**. The core issue: restricting standard entry to
   only crossover transitions (first bar of new uptrend) eliminates the re-entry-within-trend
   capability that the baseline has by default. MODE 2 adds 99-128 pullback entries but
   with latency and selectivity that reduce total capture.

6. **Average MODE 2 entry is ~1.4% below ema_fast** — pullbacks do enter at better prices,
   but the timing constraint means many profitable re-entries are missed entirely.

### Conclusion
Pullback re-entry is a **risk reduction mechanism** (MDD consistently better) but
**NOT an alpha improvement**. The baseline's unrestricted re-entry within trends is
more valuable than waiting for a pullback. VTREND's original entry timing already
captures the relevant alpha — the answer to the key question is: pullback timing
does NOT add value over the standard approach.
