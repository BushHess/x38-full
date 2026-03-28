# Exp 39: Dual-Clock EMA Entry

## Status: PENDING

## Hypothesis
Current E5-ema21D1 uses a single EMA pair (30/120). This is a single "clock"
for trend detection. Different trend timescales coexist: a 30/120 crossover
may fire while a faster 15/60 pair is ALREADY crossing back down (exhaustion),
or while a slower 60/240 pair hasn't confirmed yet (premature).

A dual-clock entry requires agreement between two EMA timescales:
- FAST clock (e.g., 15/60): timing — when to enter within a trend
- SLOW clock (e.g., 60/240): direction — confirms the macro trend

Entry fires only when BOTH clocks agree (both fast > slow). This is different
from exp17 (vote ensemble) which uses 3 DIFFERENT strategies. Dual-clock uses
the SAME strategy logic with two period sets — it's multi-timescale confirmation,
not multi-strategy voting.

Mathematical motivation: multi-timescale trend confirmation reduces false
signals from any single timescale. If ema_fast_15 > ema_slow_60 AND
ema_fast_60 > ema_slow_240, the trend is confirmed at both weekly and monthly
scales. False crossovers at one scale are filtered by the other.

Connection to cross-timescale research: x-series ρ=0.92 across timescales.
High correlation means single-timescale captures most signal. But the
DISAGREEMENT bars (where timescales diverge) may be exactly the entries to
filter out. Dual-clock tests this directly.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
# FAST clock
ema_fast_f = ema(close, fast_fast)   # e.g., 15
ema_slow_f = ema(close, fast_slow)   # e.g., 60
fast_up[i] = ema_fast_f[i] > ema_slow_f[i]

# SLOW clock
ema_fast_s = ema(close, slow_fast)   # e.g., 60
ema_slow_s = ema(close, slow_slow)   # e.g., 240
slow_up[i] = ema_fast_s[i] > ema_slow_s[i]

# Dual-clock agreement
dual_up[i] = fast_up[i] AND slow_up[i]
```

## Modification to E5-ema21D1
REPLACE single-clock EMA with dual-clock:
```python
# Original entry:
#   ema_fast(30) > ema_slow(120) AND vdo > 0 AND d1_regime_ok

# Modified entry:
#   fast_up AND slow_up AND vdo > 0 AND d1_regime_ok

# Exit — TWO OPTIONS to test:
# Option A: exit when FAST clock reverses (fast_fast < fast_slow)
#           → faster exit, SLOW clock provides entry filter only
# Option B: exit when EITHER clock reverses
#           → most conservative, but may exit too early

# Trail stop UNCHANGED: peak - 3.0 * robust_atr
# Final exit: trail_stop OR clock_reversal (per option)
```

## Parameter sweep
Preset combinations (avoid full grid — would be 4D):
```
# Config  fast_f  fast_s  slow_f  slow_s  exit_mode
# A1      15      60      30      120     fast_exit
# A2      15      60      30      120     any_exit
# B1      15      60      60      240     fast_exit
# B2      15      60      60      240     any_exit
# C1      20      84      60      240     fast_exit
# C2      20      84      60      240     any_exit
# D1      30      120     60      240     fast_exit
# D2      30      120     60      240     any_exit
# E1      15      60      120     480     fast_exit
# E2      15      60      120     480     any_exit
```
- (10 configs)
- Note: D1/D2 uses 30/120 as fast clock and 60/240 as slow — the current
  single clock becomes the FAST one with a slower confirming clock added.

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: how many entries blocked by slow clock? Agreement rate between clocks.
Entries where fast_up but NOT slow_up — were these winning or losing trades
in the baseline?

## Implementation notes
- All EMA computations use explore.py's ema() for consistency
- Slow clock with period 480 (80 days) requires more warmup — should be
  within 365-day warmup period
- Exit mode matters: fast_exit uses the faster clock for exit (more trades,
  tighter), any_exit uses the most conservative signal (fewer trades, wider)
- D1 regime filter is KEPT in all configs (dual-clock replaces H4 trend
  detection, not D1 regime)
- VDO filter is KEPT in all configs
- Trail stop (3.0 * RATR) is KEPT in all configs
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp39_dual_clock_entry.py
- Results: x39/results/exp39_results.csv

## Result
_(to be filled by experiment session)_
