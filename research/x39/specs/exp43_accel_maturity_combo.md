# Exp 43: Acceleration Gate + Maturity Decay Combination

## Status: DONE

## Hypothesis
Exp33 (accel gate) and exp38 (maturity decay) both PASS full-sample with
+0.15 Sharpe. They modify INDEPENDENT parts of the strategy:
- Exp33 modifies ENTRY (blocks entries during momentum deceleration)
- Exp38 modifies EXIT (tightens trail as trend ages)

Independent mechanisms can be additive: entry timing reduces bad entries,
maturity decay protects accumulated profit. If additive, the combination
should yield +0.20 to +0.30 Sharpe over baseline. If redundant (both
capture the same improvement via different routes), the combination will
plateau near the better single mechanism.

The key test: does entry + exit jointly beat either alone?

Mathematical motivation: if entry quality and exit timing are independent
signals, the joint improvement is approximately the sum of individual
improvements. If they're correlated (both benefit the same trades),
the joint improvement is less than the sum.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades.

## Components
```
# Exp33 best: entry gate
lookback = 12
min_accel = 0.0
ema_spread_roc = ema_spread[i] - ema_spread[i - 12]
entry: base_conditions AND ema_spread_roc > 0.0

# Exp38 best: exit modification
trail_min = 1.5, decay_start = 60, decay_end = 180
effective_trail decays linearly from 3.0 → 1.5 over bars 60-180 of trend age
```

## Modification to E5-ema21D1
```python
# Entry (exp33):
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   AND ema_spread_roc > 0  (accel gate)

# Exit (exp38):
#   effective_trail = decay(trend_age, 3.0, trail_min, decay_start, decay_end)
#   trail_stop = peak - effective_trail * robust_atr
#   exit if close < trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
Fixed combination of best configs:
```
# Group 1: fixed at exp33 + exp38 optima
combo_A: lb=12, ma=0.0, min=1.5, start=60, end=180

# Group 2: exp33 optimal + exp38 variants (vary exit)
combo_B: lb=12, ma=0.0, min=1.5, start=60, end=240
combo_C: lb=12, ma=0.0, min=2.0, start=60, end=180
combo_D: lb=12, ma=0.0, min=2.0, start=60, end=240

# Group 3: exp33 variant + exp38 optimal (vary entry)
combo_E: lb=6,  ma=0.0, min=1.5, start=60, end=180
combo_F: lb=24, ma=0.0, min=1.5, start=60, end=180
```
Plus: baseline, exp33-only (lb=12, ma=0.0), exp38-only (min=1.5, start=60, end=180)
(9 total: 6 combos + 3 references)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%, avg holding period.
Delta vs baseline, delta vs exp33-only, delta vs exp38-only.

Key metric: **additivity ratio** = combo_delta / (exp33_delta + exp38_delta).
- Ratio ≈ 1.0: fully additive (independent mechanisms)
- Ratio < 0.5: redundant (same improvement, different routes)
- Ratio > 1.0: synergistic (mechanisms interact positively)

Also: how many entries pass BOTH gates? How many pass exp33 but not exp38
(or vice versa)?

## Implementation notes
- Combine exp33's entry logic with exp38's exit logic in one backtest loop
- Reuse compute_trend_age() from exp38 and ema_spread_roc from exp33
- Warmup: 365 days (use max of exp33/exp38 warmup requirements)
- Cost: 50 bps RT, INITIAL_CASH = 10_000
- exp33's warmup was only SLOW_PERIOD=120 bars; exp38 used 365 days.
  Use 365 days here for consistency with exp38's baseline numbers.

## Output
- Script: x39/experiments/exp43_accel_maturity_combo.py
- Results: x39/results/exp43_results.csv

## Result

### Baseline
| Metric | Value |
|--------|-------|
| Sharpe | 1.3098 |
| CAGR | 52.70% |
| MDD | 41.01% |
| Trades | 197 |

### Reference singles
| Config | Sharpe | d_Sharpe | CAGR% | d_CAGR | MDD% | d_MDD | Trades |
|--------|--------|----------|-------|--------|------|-------|--------|
| exp33_only (lb=12, ma=0.0) | 1.3419 | +0.0321 | 48.08 | -4.62 | 41.01 | 0.00 | 149 |
| exp38_only (min=1.5, s=60, e=180) | 1.4596 | +0.1498 | 58.11 | +5.41 | 31.19 | -9.82 | 263 |

### Combination configs
| Config | Sharpe | d_Sharpe | CAGR% | MDD% | d_MDD | Trades | Additivity Ratio |
|--------|--------|----------|-------|------|-------|--------|------------------|
| combo_A (lb=12, min=1.5, s=60, e=180) | 1.4501 | +0.1403 | 49.75 | 37.41 | -3.60 | 177 | 0.771 [ADDITIVE] |
| combo_B (lb=12, min=1.5, s=60, e=240) | 1.4199 | +0.1101 | 48.40 | 37.82 | -3.19 | 172 | 0.605 [PARTIAL] |
| combo_C (lb=12, min=2.0, s=60, e=180) | 1.4047 | +0.0949 | 48.53 | 39.98 | -1.03 | 167 | 0.522 [PARTIAL] |
| combo_D (lb=12, min=2.0, s=60, e=240) | 1.3576 | +0.0478 | 46.44 | 39.69 | -1.32 | 165 | 0.263 [REDUNDANT] |
| combo_E (lb=6, min=1.5, s=60, e=180) | 1.3525 | +0.0427 | 45.76 | 35.83 | -5.18 | 185 | 0.235 [REDUNDANT] |
| combo_F (lb=24, min=1.5, s=60, e=180) | 1.2325 | -0.0773 | 39.25 | 39.98 | -1.03 | 176 | -0.425 [REDUNDANT] |

### Gate overlap
- Base entry signals: 3,910
- Pass accel gate (lb=12): 2,221
- Blocked by accel gate: 1,689 (43.2%)
- Maturity decay modifies EXIT, not entry — structurally independent

### Additivity analysis
- Sum of individual deltas: +0.1819 Sharpe
- Best combo (A): +0.1403 → ratio 0.771 (near-additive for Sharpe)
- CAGR: combo HURTS (all combos lose CAGR vs baseline; exp33 costs -4.62pp CAGR via trade suppression)
- MDD: combo captures only 37% of exp38's MDD improvement (exp33 adds 0 MDD benefit, combo dilutes exp38)

### Verdict: MARGINAL

**Best combo (A) does NOT beat exp38-only.** Sharpe 1.4501 vs 1.4596 (-0.0095).
exp38 alone dominates on ALL metrics: higher Sharpe, higher CAGR (+58.11% vs +49.75%),
lower MDD (31.19% vs 37.41%).

The accel gate (exp33) is **net-harmful** in combination:
1. Blocks 43% of entries → kills CAGR (all combos lose 3-13pp CAGR vs baseline)
2. Blocked entries include good trades → dilutes exp38's exit improvement
3. Exposure drops from 40.3% (exp38) to 29.6% (combo_A) — severe under-investment

**Conclusion**: exp38 (maturity decay) is the strictly better single mechanism.
Adding exp33 (accel gate) is NOT additive in practice — the entry suppression
destroys CAGR and dilutes MDD gains. Use exp38 alone.
