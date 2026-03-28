# Exp 24: Volume Anomaly Exit

## Status: DONE

## Hypothesis
All exp01-18 supplementary exits used PRICE-BASED features (rangepos, trendq,
ret_168, EMA). Volume-based features have been tested only as entry gates
(exp03: liquidity, exp04: trade_surprise, exp10: VDO replacement) — all failed.

But volume features have NOT been tested as supplementary exits. The residual
scan shows two volume-domain features with independent predictive power:
- vol_per_range: 3/5 horizons (rho +0.036 to +0.142), positive at all horizons
- trade_surprise_168: 2/5 horizons (rho dual-signed: −0.022 at fwd_6, +0.033 at fwd_168)

vol_per_range measures LIQUIDITY: how much volume is needed to move price one
unit. High vol_per_range = deep market, orderly. Low vol_per_range = thin market,
fragile. When liquidity DROPS during a long trade, the market is becoming fragile
— potential for fast, illiquid selloffs.

trade_surprise_168 measures PARTICIPATION ANOMALY: whether trade count is
unusually high/low relative to volume. Negative surprise = fewer participants
than volume suggests = large players dominating = potential for regime shift.

These provide a DIFFERENT information domain than price-based exits. Price exits
react to what HAS happened. Volume exits detect structural changes in market
microstructure that PRECEDE price moves.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Features
```
# Feature A: Liquidity (vol per unit price range)
vol_per_range[i] = volume[i] / (high[i] - low[i])
# Raw per-bar, then z-score vs 100-bar rolling window for stationarity:
vpr_z[i] = (vol_per_range[i] - rolling_mean_100[i]) / rolling_std_100[i]
# Negative z-score = liquidity below recent average

# Feature B: Participation anomaly (trade count residual)
# From explore.py: fit log(num_trades) ~ log(volume) on first 2000 bars,
# then compute residual for all bars. Subtract 168-bar rolling mean.
trade_surprise_168[i]  # Already in compute_features()
# Negative = fewer participants than expected = concentrated flow
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — ADD volume condition (OR with existing):

**Variant A — Liquidity dropout:**
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR ema_fast < ema_slow OR vpr_z < threshold
# Exit when liquidity drops significantly below recent average
```

**Variant B — Participation anomaly:**
```python
# Modified: close < trail_stop OR ema_fast < ema_slow OR trade_surprise_168 < threshold
# Exit when participation is anomalously low (concentrated flow)
```

## Parameter sweep

**Variant A (liquidity z-score):**
- threshold in [−2.0, −1.5, −1.0, −0.5, 0.0]
- (5 configs)
- Rationale: z = −2 is very conservative (2σ below mean), z = 0 is aggressive
  (any below-average liquidity triggers exit)

**Variant B (trade surprise):**
- threshold in [−0.15, −0.10, −0.05, 0.00, 0.05]
- (5 configs)
- Range centered around 0 (neutral participation)

Total: 10 configs + 1 baseline = 11 runs.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, exposure%
- Delta vs baseline for Sharpe, CAGR, MDD
- Exit attribution: how many exits triggered by volume feature?
- Information overlap with exp12: of trades exited by volume signal, how many
  ALSO had rangepos_84 < 0.25? (Low overlap = independent information domain →
  good stacking candidate for exp19)
- Timing: when volume exit fires, does a price-based exit fire within the
  next 1-5 bars anyway? (If yes → volume is just slightly earlier. If no →
  volume catches events that price never catches.)

## Implementation notes
- vol_per_range z-score: compute per-bar vol_per_range, then rolling mean/std
  with window=100. This is NOT directly in compute_features() — compute_features()
  has raw vol_per_range and volume_z/range_z, but NOT vol_per_range z-score.
  Compute it manually: vpr = volume / range, then z-score with 100-bar rolling.
- trade_surprise_168 IS in compute_features() — use directly
- Handle div-by-zero: when range = 0 (doji), vol_per_range = inf → set vpr_z = NaN
  → treat as "not triggered" for exit purposes
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days
- The volume features may have different characteristics across bull/bear regimes.
  Report per-regime exit counts if feasible (pre-2022, 2022 bear, post-2022).

## Output
- Script: x39/experiments/exp24_volume_anomaly_exit.py
- Results: x39/results/exp24_results.csv

## Result

**FAIL — both variants. Volume anomaly exits do NOT help E5-ema21D1.**

### Baseline
Sharpe 1.3098, CAGR 52.70%, MDD 41.01%, 197 trades, 43.5% exposure.
Exits: trail=179 (91%), trend=18 (9%).

### Variant A: Liquidity Dropout (vpr_z)

| threshold | Sharpe | CAGR% | MDD% | trades | d_Sharpe | d_MDD | vol exits |
|-----------|--------|-------|------|--------|----------|-------|-----------|
| -2.0      | 1.2452 | 48.87 | 41.01 | 211  | -0.0646  |  0.00 |  17       |
| -1.5      | 0.9799 | 33.52 | 46.31 | 352  | -0.3299  | +5.30 | 187       |
| -1.0      | 0.0854 | -2.20 | 76.58 | 787  | -1.2244  | +35.57| 701       |
| -0.5      | -1.3063| -33.31| 96.35 | 1277 | -2.6161  | +55.34| 1241      |
|  0.0      | -2.7214| -52.15| 99.62 | 1644 | -4.0312  | +58.61| 1624      |

Every threshold hurts. Even the most conservative (z=-2.0, only 17 exits) loses
0.065 Sharpe. More aggressive thresholds are catastrophic — vpr_z=0.0 generates
1624 exits (8x baseline trades), MDD 99.6%.

### Variant B: Participation Anomaly (trade_surprise_168)

| threshold | Sharpe | CAGR% | MDD% | trades | d_Sharpe | d_MDD | vol exits |
|-----------|--------|-------|------|--------|----------|-------|-----------|
| -0.15     | -0.2277| -12.17| 89.80| 774    | -1.5375  | +48.79| 674       |
| -0.10     | -0.6348| -22.24| 92.19| 947    | -1.9446  | +51.18| 874       |
| -0.05     | -1.1771| -32.81| 95.27| 1139   | -2.4869  | +54.26| 1086      |
|  0.00     | -1.6171| -39.74| 97.84| 1320   | -2.9269  | +56.83| 1281      |
|  0.05     | -2.3078| -48.75| 99.36| 1517   | -3.6176  | +58.35| 1489      |

Even worse than Variant A. The most conservative threshold (-0.15) still generates
674 exits and destroys the strategy (Sharpe -0.23, MDD 90%).

### Information Overlap with rangepos_84

Volume exits are nearly 100% independent from rangepos_84 exits:
- Variant A (vpr_z=-2.0): 0/17 overlap (0%) with rangepos_84 < 0.25
- Variant A (vpr_z=-1.5): 2/187 overlap (1%)
- Variant B (all thresholds): 1-2% overlap

Volume features occupy a genuinely different information domain. But this
independence doesn't help — the domain has no predictive power for exits.

### Timing Analysis

Variant A (vpr_z=-2.0): all 17 exits fire EARLIER than trail/trend (100%).
Median 18 bars earlier (3 days). But mean avoided PnL = -3.48 pp — volume
exits are **early but wrong**, cutting winning trades short.

The key trade: bar 7270→7326 exits +28.94% but counterfactual holds to +67.91%.
Volume dropout during a strong rally triggers premature exit.

### Selectivity Analysis

Variant A (vpr_z=-2.0): 76% of volume exits are WINNERS (avg +13.23%).
This is the opposite of useful selectivity — the signal preferentially exits
profitable trades. Liquidity drops during strong moves are structural (price
moves fast → fewer volume per range unit), not fragility signals.

Variant B: 45% winners at ts168=-0.15, declining to 33% at ts168=0.05.
Better selectivity but still cuts too many trades indiscriminately.

### Regime Analysis

Variant A (vpr_z=-2.0): 13/17 exits in pre-2022, 0 in 2022 bear, 4 post-2022.
Liquidity dropout is regime-dependent — more common in high-volatility bull runs.

Variant B: more evenly distributed but heavier post-2022 (92% vs 82% pre-2022
at ts168=-0.15). Trade surprise is noisier in the more liquid post-2022 market.

### Diagnosis

Both features trigger exits FAR too frequently when used as exit signals.
The fundamental problem: **volume anomalies are common during trend-following
trades**. Strong trends inherently create volume/liquidity anomalies (fast moves
thin the book, large directional flow concentrates participation). Using these
as exit signals is self-defeating — they fire precisely when the strategy is
working as designed.

This is the mirror of the entry gate findings (exp03: liquidity, exp04:
trade_surprise — both failed as entry gates). Volume features have no
predictive power for E5-ema21D1 in either direction (entry or exit).

### Conclusion

Volume-domain features are informationally independent from price-domain features
(0-2% overlap with rangepos_84) but carry zero useful signal for supplementary
exits. The hypothesis that volume features "detect structural changes that PRECEDE
price moves" is rejected — in practice, volume anomalies are CONSEQUENCES of
price moves, not predictors.
