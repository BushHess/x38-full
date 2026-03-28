# Exp 19: Stacked Supplementary Exits

## Status: PENDING

## Hypothesis
Exp12 proved that rangepos_84 < 0.25 as supplementary exit improves E5-ema21D1
(+0.046 Sharpe, −6.37 pp MDD). That exit fires on only 35/240 trades (15%) —
highly selective, which avoids the X31-A trap (top 5% trades = 129.5% of profits).

If a SECOND selective exit captures a different failure mode than rangepos, the
two exits should compound: rangepos catches "price falling within range" while
a momentum or trend-quality exit catches "underlying trend deteriorating".

Key constraint: each additional exit must remain selective (low intervention count).
If exits overlap heavily, the second exit adds churn without new information.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.
(Internal replay baseline ~1.2965 Sharpe due to simplified logic — deltas are
internally consistent.)

## Features
```
# Feature A (proven in exp12):
rangepos_84[i] = (close[i] - rolling_low_84[i]) / (rolling_high_84[i] - rolling_low_84[i])

# Feature B candidates:
ret_168[i]  = close[i] / close[i-168] - 1         # 28-day momentum (4/5 residual horizons)
trendq_84[i] = ret_84[i] / realized_vol_84[i]     # trend quality (3/5 residual horizons)
d1_rangevol84_rank365[i]                            # D1 vol regime rank (4/5 residual horizons)
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — ADD two supplementary conditions (OR with existing):
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR ema_fast < ema_slow
#           OR rangepos_84 < rp_threshold
#           OR feature_B < fb_threshold
```
Each supplementary exit fires independently. A trade exits on whichever
condition triggers first.

## Parameter sweep
Fixed: rangepos_84 threshold = 0.25 (exp12 optimum).

Three stacking variants, each with its own feature B threshold sweep:

**Variant A — ret_168 momentum exit:**
- fb_threshold in [−0.10, −0.05, 0.00, 0.05, 0.10]
- (5 configs)

**Variant B — trendq_84 trend quality exit:**
- fb_threshold in [−0.40, −0.20, 0.00, 0.20, 0.40]
- (5 configs)

**Variant C — d1_rangevol84_rank365 vol regime exit:**
- fb_threshold_high in [0.70, 0.75, 0.80, 0.85, 0.90]
- Exit when rank RISES above threshold (high vol = chaotic regime)
- (5 configs)

Total: 15 configs + 1 baseline + 1 rangepos-only (exp12 reproduction) = 17 runs.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, exposure%
- Delta vs baseline AND delta vs rangepos-only
- Per-exit breakdown: how many exits triggered by trail / trend / rangepos / feature_B?
- Overlap rate: how often do rangepos and feature_B fire on the SAME trade?
  (High overlap = redundant, low overlap = complementary)

## Implementation notes
- Use x39/explore.py's compute_features() to get all feature arrays
- Start from exp12's code as base, add second exit channel
- Map D1 features to H4 using map_d1_to_h4() for variant C
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 D1 bars (for d1_rangevol84_rank365)
- IMPORTANT: track exit attribution per trade (which exit triggered)
  to measure overlap vs complementarity
- Variant C exits when d1_rangevol84_rank365 > threshold (ABOVE, not below —
  high rank = high vol = bad regime). This is the opposite direction from exp01.

## Output
- Script: x39/experiments/exp19_stacked_exits.py
- Results: x39/results/exp19_results.csv

## Result
_(to be filled by experiment session)_
