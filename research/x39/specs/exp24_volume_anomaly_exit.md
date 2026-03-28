# Exp 24: Volume Anomaly Exit

## Status: PENDING

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
_(to be filled by experiment session)_
