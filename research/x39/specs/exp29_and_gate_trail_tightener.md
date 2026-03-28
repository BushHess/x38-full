# Exp 29: AND-Gate Trail Tightener

## Status: PENDING

## Hypothesis
Exp22's AND gate exits immediately when rp < 0.20 AND tq < -0.10. This is
BINARY: the trade dies regardless of what happens next. But 2/12 AND exits
(17%) were on winners — trades that would have recovered and profited.

Exp20 tested CONTINUOUS trail adaptation using rangepos → FAIL (all configs
degrade). The failure mode: continuous modulation changes the trail at EVERY
bar, adding noise. Fixed trail=3.0 is a local optimum under continuous
variation.

But exp20's failure doesn't rule out EVENT-TRIGGERED trail adjustment.
The mechanism is structurally different:
- Exp20 (continuous): trail_mult = f(rangepos) at every bar. Always on.
- Exp29 (event-triggered): trail_mult stays at 3.0 until AND gate fires.
  THEN drops to tight_mult. Only fires ~12 times across entire backtest.

When the AND gate fires:
- If the trade is a LOSER: tighter trail exits sooner → reduces loss (good)
- If the trade is a WINNER in temporary distress: tighter trail gives the
  trade a chance to recover (unlike binary exit), but with a shorter leash.
  If recovery happens → trade continues at normal trail. If not → exits.

This is a SOFTER version of exp22: same signal, graduated response instead
of immediate exit. It should reduce the 17% false positive rate by giving
borderline trades a chance to recover.

## Baseline
E5-ema21D1 (simplified replay): ~1.2965 Sharpe, ~51.32% MDD, 221 trades.

## Feature
```
rangepos_84[i] = (close[i] - rolling_low_84[i]) / (rolling_high_84[i] - rolling_low_84[i])
trendq_84[i]   = ret_84[i] / realized_vol_84[i]
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — AND gate triggers trail tightening, not immediate exit:
```python
# State: each trade starts with trail_mult = 3.0 and tightened = False

# On each bar during a trade:
if not tightened and rangepos_84[i] < rp_threshold and trendq_84[i] < tq_threshold:
    trail_mult = tight_mult    # e.g., 1.5
    tightened = True           # one-way latch: once tightened, stays tight

# Trail stop uses current trail_mult (3.0 or tight_mult):
trail_stop = peak_price - trail_mult * ratr[i]
exit_signal = close < trail_stop OR ema_fast < ema_slow
```

Key properties:
- Tightening is a ONE-WAY LATCH: once AND fires, trail stays tight for the
  remainder of the trade. No recovery to 3.0 (prevents oscillation).
- Only the trail multiplier changes. Peak tracking, ATR, and EMA exit are
  unchanged.
- If AND never fires during a trade → identical to baseline.
- After tightening, the trade may survive (price stays above tighter trail)
  or exit (price hits tighter trail). Both are acceptable outcomes.

## Parameter sweep
Fix rp_threshold = 0.20, tq_threshold = -0.10 (exp22 optimum).
Vary tight_mult:

- tight_mult in [1.0, 1.5, 2.0, 2.5]
- (4 configs)

Also vary tq_threshold with fixed tight_mult = 1.5:
- tq_threshold in [-0.20, -0.10, 0.00, 0.10]
- (4 configs, tq=-0.10 overlaps)

Also include controls:
- baseline (no AND gate)
- exp22 reproduction (AND gate → immediate exit)

Total: 7 unique configs + 2 controls = 9 runs.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, exposure%
- Delta vs baseline for Sharpe, MDD
- Tightening events: how many trades had trail tightened?
- Post-tightening outcomes:
  - Survived (trade continued and exited later by normal trail/trend)
  - Triggered (trade hit tighter trail stop)
  - For each: was the trade ultimately a winner or loser?

Key analysis:
1. **Trail tighten vs binary exit**: compare best tight_mult config vs
   exp22 (binary exit). Does graduated response beat immediate exit?
   - If tight_mult=1.0 ≈ exp22 (trail at 1.0×ATR is almost immediate exit)
   - If tight_mult=2.5 ≈ minor adjustment (barely different from baseline)
   - Sweet spot should be somewhere in between

2. **Recovery rate**: of trades where AND fires + trail tightens, how many
   survive (price recovers above tighter trail)? This directly measures
   whether the "softer response" hypothesis holds. If 0% survive → binary
   exit is equivalent. If >30% survive → graduated response has value.

3. **Winner preservation**: of exp22's 2/12 false positive exits (winners
   killed by binary exit), do any survive under trail tightening?
   Requires matching trades by entry bar between configs.

4. **Optimal tight_mult**: plot d_Sharpe vs tight_mult. Monotonic (tighter
   always better → binary exit is optimal)? Or inverted-U (intermediate
   tight_mult wins → graduated response is genuinely different)?

## Implementation notes
- Use exp22 code as base. Instead of exiting when AND fires, set a flag
  and change trail_mult for that trade.
- tightened flag is per-TRADE, not global. Reset on each new trade entry.
- Peak price tracking continues normally. Tighter trail just means the
  stop is closer to peak.
- tight_mult=1.0 should approximate exp22's binary exit (1×ATR distance
  from peak is very tight, likely triggers within 1-3 bars). Use as
  sanity check: result should be close to exp22.
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days

## Output
- Script: x39/experiments/exp29_and_gate_trail_tightener.py
- Results: x39/results/exp29_results.csv

## Result
_(to be filled by experiment session)_
