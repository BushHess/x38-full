# Exp 39: Dual-Clock EMA Entry

## Status: DONE

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

**Verdict: FAIL** — No dual-clock config meaningfully improves on single-clock baseline.

Note: warmup bar = 530 (to cover EMA(480) in config E), so baseline numbers differ
slightly from the canonical E5-ema21D1 stats (warmup 365d ≈ bar 2190 from 2017).
All configs evaluated under identical conditions.

### Baseline (single clock 30/120, same warmup)
Sharpe 1.2952, CAGR 57.03%, MDD 51.32%, 214 trades, exposure 42.7%

### Results summary
```
Config  fast    slow    exit       Sharpe  CAGR%  MDD%   trades  d_Sh     d_MDD
─────────────────────────────────────────────────────────────────────────────────
A1      15/60   30/120  fast_exit  1.2824  52.94  37.87  213     -0.0128  -13.45
A2      15/60   30/120  any_exit   1.2727  52.35  38.97  214     -0.0225  -12.35
B1      15/60   60/240  fast_exit  1.2306  46.75  38.39  175     -0.0646  -12.93
B2      15/60   60/240  any_exit   1.2392  47.19  38.39  175     -0.0560  -12.93
C1      20/84   60/240  fast_exit  1.2909  51.41  44.92  169     -0.0043   -6.40
C2      20/84   60/240  any_exit   1.2992  51.86  44.92  169     +0.0040   -6.40
D1      30/120  60/240  fast_exit  1.2958  53.44  52.54  173     +0.0006   +1.22
D2      30/120  60/240  any_exit   1.3041  53.92  52.49  173     +0.0089   +1.17
E1      15/60  120/480  fast_exit  1.0758  37.26  40.44  164     -0.2194  -10.88
E2      15/60  120/480  any_exit   1.0758  37.26  40.44  164     -0.2194  -10.88
```

### Key findings

1. **C2 technically PASS** (Sharpe +0.004, MDD -6.40 pp) but the Sharpe delta is
   negligible (+0.3%) while CAGR drops -5.17 pp. This is a MDD-only improvement
   achieved by filtering 169→169 trades (from 214 baseline) — the "improvement"
   is from reduced exposure (34.7% vs 42.7%), not better entry selection.

2. **MDD improves dramatically in configs A/B** (-12 to -13 pp) but at the cost of
   Sharpe degradation. Faster entry clocks (15/60) generate many signals that get
   blocked by the slow clock — reducing exposure and thus both returns AND drawdown.

3. **D1/D2 configs (30/120 + 60/240)** are closest to baseline because the fast clock
   IS the baseline. Adding slow 60/240 barely changes Sharpe (+0.001 to +0.009)
   but doesn't improve MDD either (+1.2 pp worse).

4. **E configs (slow=120/480)** destroy performance: Sharpe -0.22, CAGR -20 pp.
   The ultra-slow clock blocks too many valid entries (1424 blocked, agreement 11.4%).

5. **Blocked-trade analysis (D1 config)**: Blocked trades avg_ret=2.19% vs allowed
   avg_ret=2.38%. The slow clock filters out SLIGHTLY worse trades but the
   difference is marginal (0.19 pp). Win rates are actually HIGHER for blocked
   trades (44.8% vs 39.5%) — the blocked trades are frequent small winners that
   get replaced by nothing.

6. **Agreement rates**: 11-32% depending on config. The two clocks disagree most of
   the time, confirming the hypothesis that different timescales see different trends.
   But the DISAGREEMENT entries are not systematically bad — they're a mix.

7. **Exit mode matters little**: fast_exit vs any_exit produces nearly identical results
   in most configs (B1≈B2, D1≈D2, E1=E2). This suggests the trail stop dominates
   exit timing, not the EMA clock reversal.

### Conclusion
Dual-clock confirmation is a MDD-vs-return tradeoff, not a strict improvement.
The MDD reduction comes from reduced exposure (fewer entries pass dual filter),
not from genuinely better entry selection. Consistent with ρ=0.92 cross-timescale
finding: timescales are too correlated for the second clock to provide independent
information. The slow clock is largely redundant as a filter — it blocks entries
semi-randomly rather than selectively removing bad ones.
