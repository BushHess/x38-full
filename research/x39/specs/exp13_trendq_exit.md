# Exp 13: Trend Quality Exit

## Status: PENDING

## Hypothesis
trendq_84 = ret_84 / realized_vol_84. When trendq drops to zero or negative,
momentum has stalled relative to volatility — trend is degrading.
Use as EXIT signal instead of (or in addition to) EMA cross-down.

Advantage over EMA cross-down: trendq responds to volatility expansion
(denominator), not just price direction. A trend can still be "up" on EMA
but "degraded" on trendq if volatility spikes.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
log_ret[i] = log(close[i] / close[i-1])
realized_vol_84[i] = std(log_ret[i-83:i+1]) * sqrt(84)
ret_84[i] = close[i] / close[i-84] - 1
trendq_84[i] = ret_84[i] / realized_vol_84[i]
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — REPLACE EMA cross-down with trendq. Trail stop KEPT:
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR trendq_84 < threshold
# trail_stop = peak - 3.0 * robust_atr  (KEPT, unchanged from E5)
# EMA cross-down is REMOVED, replaced by trendq_84 < threshold
```

## Parameter sweep
- threshold in [-0.2, -0.1, 0.0, 0.1, 0.2]
- (5 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period. Delta vs baseline.

## Implementation notes
- This REPLACES EMA cross-down exit, not adds to it
- trendq can be negative even when EMA fast > slow (if recent vol spike)
- Trail stop is KEPT regardless

## Output
- Script: x39/experiments/exp13_trendq_exit.py
- Results: x39/results/exp13_results.csv

## Result

**FAIL** — All thresholds degrade Sharpe vs EMA cross-down baseline.

| threshold | Sharpe | CAGR% | MDD% | trades | avg_held | d_sharpe | d_mdd |
|-----------|--------|-------|------|--------|----------|----------|-------|
| baseline  | 1.2965 | 57.77 | 51.32 | 221   | 36.0     | —        | —     |
| -0.2      | 1.2480 | 53.69 | 47.39 | 294   | 26.6     | -0.049   | -3.93 |
| -0.1      | 1.1777 | 48.72 | 53.14 | 342   | 22.2     | -0.119   | +1.82 |
| 0.0       | 1.1199 | 44.81 | 54.86 | 410   | 17.9     | -0.177   | +3.54 |
| 0.1       | 1.0519 | 40.62 | 53.23 | 477   | 14.9     | -0.245   | +1.91 |
| 0.2       | 0.8679 | 30.46 | 55.84 | 570   | 12.1     | -0.429   | +4.52 |

threshold=-0.2 improves MDD (-3.93 pp) but still degrades Sharpe.
Higher thresholds cause excessive exits (trades 221→570, avg hold 36→12 bars),
cutting trends short and destroying trend-following alpha.
trendq responds too eagerly to vol spikes — not a viable EMA cross-down replacement.
