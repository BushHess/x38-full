# Exp 47: Acceleration-Weighted Initial Trail

## Status: PENDING

## Hypothesis
Exp33 uses acceleration as a binary gate (enter if accel > 0, block if ≤ 0).
This discards information: the MAGNITUDE of acceleration carries signal.
High acceleration = strong trend initiation → wider initial trail to give
the trend room. Low acceleration = weak trend → tighter initial trail to
protect capital.

Instead of a binary gate, use acceleration magnitude to SET the initial
trail multiplier continuously. This preserves the timing information (no
late-cycle entries get tight trails) while keeping ALL entries (no blocking).

Combined with exp38's maturity decay: the trail starts at an accel-dependent
level and THEN decays with trend age. High-accel entries start wide and
decay slowly (strong trend gets room). Low-accel entries start tight and
decay faster (weak trend gets protection).

Mathematical motivation: optimal risk allocation depends on signal strength.
Strong signals (high acceleration) justify wider stops (higher risk tolerance)
because the expected reward is higher. Weak signals (low acceleration) justify
tighter stops because the expected reward is lower. This is a continuous
risk-reward optimization, not a discrete filter.

Connection to exp21 (conviction sizing): exp21 tested IC of entry features
for position sizing and found IC = -0.039 (no predictive power). BUT exp21
tested VDO/ema_spread/atr_pctl at entry, not ema_spread_roc. The acceleration
derivative may carry timing information even when level features don't.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades.

## Feature
```
ema_spread[i] = (ema_fast[i] - ema_slow[i]) / ema_slow[i]
ema_spread_roc[i] = ema_spread[i] - ema_spread[i - 12]

# Percentile rank of acceleration (trailing 365 bars)
accel_pctl[i] = percentile_rank(ema_spread_roc[i],
                                ema_spread_roc[i-365:i])

# Initial trail multiplier: linear interpolation
# Low accel (pctl → 0):  trail → trail_low  (tight)
# High accel (pctl → 1): trail → trail_high (wide)
initial_trail[i] = trail_low + accel_pctl[i] * (trail_high - trail_low)
```

## Modification to E5-ema21D1
```python
# Entry: UNCHANGED (no binary gate — ALL entries accepted)
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok

# Exit: accel-weighted initial trail + optional maturity decay
#   At entry: record initial_trail = trail_low + accel_pctl * (trail_high - trail_low)
#
#   Option A (accel-weighted only):
#     trail_stop = peak - initial_trail * robust_atr
#
#   Option B (accel-weighted + maturity decay):
#     effective_trail = decay(trend_age, initial_trail, trail_min, start, end)
#     trail_stop = peak - effective_trail * robust_atr
#
#   exit if close < trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
```
# Option A — accel-weighted trail only (no decay)
A1: trail_low=2.0, trail_high=3.0     # 2.0-3.0 range
A2: trail_low=2.0, trail_high=4.0     # wider range
A3: trail_low=2.5, trail_high=3.5     # narrow range, centered at 3.0
A4: trail_low=1.5, trail_high=3.0     # aggressive tightening for weak trends

# Option B — accel-weighted + maturity decay (trail_min=1.5, start=60, end=180)
B1: trail_low=2.0, trail_high=3.0, decay_min=1.5, decay_start=60, decay_end=180
B2: trail_low=2.0, trail_high=4.0, decay_min=1.5, decay_start=60, decay_end=180
B3: trail_low=2.5, trail_high=3.5, decay_min=1.5, decay_start=60, decay_end=180
B4: trail_low=1.5, trail_high=3.0, decay_min=1.5, decay_start=60, decay_end=180
```
Plus: baseline (fixed trail=3.0), exp38-only (decay from 3.0, min=1.5/60/180)
(10 total: 4A + 4B + 2 refs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%.
Delta vs baseline, delta vs exp38-only.

Key analysis:
1. **Option A vs baseline**: does continuous trail sizing beat fixed 3.0?
2. **Option B vs exp38**: does accel-weighting add value on top of decay?
3. **Distribution of initial_trail**: median, P10, P90. Is there meaningful
   variation or is accel_pctl too narrow to differentiate?
4. **Correlation check**: initial_trail vs trade net_ret. Positive = high
   trail entries do better (validates the hypothesis).
5. **B vs A**: does maturity decay matter MORE for accel-weighted trails?
   (Hypothesis: decay matters more when starting trail varies.)

## Implementation notes
- accel_pctl needs 365 + 12 bars history → within 365-day warmup
- initial_trail is FIXED at entry — doesn't change during the trade
  (unlike exp36 where trail adapts to current regime)
- In Option B, decay starts from initial_trail (not from 3.0) and decays
  toward trail_min. Each trade has its own starting trail.
- If accel_pctl is NaN (insufficient history), use trail=3.0 as fallback
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp47_accel_weighted_trail.py
- Results: x39/results/exp47_results.csv

## Result
_(to be filled by experiment session)_
