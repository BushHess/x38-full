# Exp 47: Acceleration-Weighted Initial Trail

## Status: DONE

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

**Verdict: FAIL** — Acceleration magnitude as continuous trail sizing HURTS.

### Summary Table (vs baseline: Sharpe 1.310, CAGR 52.7%, MDD 41.01%)
```
Config       | Sharpe | CAGR%  | MDD%  | Trades | d_Sh    | d_MDD
-------------|--------|--------|-------|--------|---------|------
baseline     | 1.310  | 52.70  | 41.01 |  197   |   —     |   —
exp38_only   | 1.460  | 58.11  | 31.19 |  263   | +0.150  | -9.82
A1 [2.0-3.0] | 1.135  | 42.00  | 40.49 |  243   | -0.175  | -0.52
A2 [2.0-4.0] | 1.038  | 37.84  | 42.70 |  201   | -0.272  | +1.69
A3 [2.5-3.5] | 1.187  | 45.86  | 38.70 |  196   | -0.122  | -2.31
A4 [1.5-3.0] | 1.158  | 42.84  | 36.82 |  271   | -0.152  | -4.19
B1 [2.0-3.0] | 1.253  | 46.79  | 34.22 |  286   | -0.057  | -6.79
B2 [2.0-4.0] | 1.265  | 47.88  | 34.01 |  256   | -0.045  | -7.00
B3 [2.5-3.5] | 1.313  | 50.42  | 33.39 |  261   | +0.004  | -7.62
B4 [1.5-3.0] | 1.203  | 44.06  | 34.18 |  305   | -0.107  | -6.83
```

### Key Findings

1. **Option A vs baseline**: ALL 4 configs WORSE on Sharpe (-0.12 to -0.27).
   Continuous trail sizing actively destroys alpha vs fixed trail=3.0.

2. **Option B vs exp38-only**: ALL 4 configs WORSE on BOTH Sharpe (-0.15 to -0.26)
   AND MDD (+2.2 to +3.0 pp). Accel-weighting is pure drag on top of decay.

3. **Correlation check**: ALL negative, ALL non-significant (p > 0.29).
   rho ranges from -0.011 to -0.061. Hypothesis REJECTED: high-acceleration
   entries do NOT produce better returns than low-acceleration entries.

4. **Distribution**: Good range utilization (85-88%), P10-P90 spread meaningful.
   The problem is NOT narrow percentiles — accel_pctl differentiates entries
   effectively, but the differentiation carries NO useful signal for trail sizing.

5. **B vs A (decay on top of accel-weighted)**: Decay helps all 4 pairs
   (+0.04 to +0.23 Sharpe), confirming exp38's value. But this is exp38
   doing its usual work — accel-weighting is a drag that decay partially offsets.

6. **B3 "PASS" is misleading**: d_Sharpe=+0.004 vs baseline is noise-level.
   B3 loses to exp38-only by -0.146 Sharpe. The MDD improvement (-7.62 pp)
   is entirely from the decay component.

### Conclusion

Acceleration magnitude contains NO information for optimal trail width.
The connection to exp21 (conviction sizing) is confirmed: entry features
(including derivatives like ema_spread_roc) have zero predictive power
over trade outcomes. This is consistent with alpha being GENERIC trend-following
(plateau slow=60-144) — individual entry timing doesn't predict trade quality.

**exp38 (pure maturity decay from fixed 3.0) remains strictly superior.**
