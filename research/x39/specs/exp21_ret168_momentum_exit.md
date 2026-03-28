# Exp 21: ret_168 Momentum Exit

## Status: PENDING

## Hypothesis
ret_168 (28-day momentum) is the STRONGEST residual predictor in the x39 scan:
4/5 forward horizons significant, rho up to +0.119 at fwd_168. All correlations
positive — high momentum predicts continuation.

Exp07 tested ret_168 as entry REPLACEMENT for EMA crossover → FAIL (best
d_Sharpe = −0.060). This is expected: E5's EMA crossover captures the same
directional information more precisely at H4 resolution.

UNTESTED: ret_168 as supplementary EXIT. The mechanism is different from
trail stop and EMA cross-down:
- Trail stop: absolute decline from peak price (reactive to recent move)
- EMA cross-down: local trend reversal at H4 scale (fast responds to slow)
- ret_168 < 0: STRUCTURAL momentum reversal at multi-week scale

When 28-day return goes negative during a long trade, the macro trend has
shifted. This is a regime change that trail stop (local) and EMA cross
(medium-term) may not catch until significant damage is done. ret_168
provides early warning at a different timescale.

Key risk: ret_168 changes slowly (168-bar lookback = 28 days on H4). It may
exit too late (after drawdown already severe) or too early (during a healthy
consolidation within a larger uptrend). The threshold sweep tests this.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
ret_168[i] = close[i] / close[i - 168] - 1
# Positive = price higher than 28 days ago (momentum intact)
# Negative = price lower than 28 days ago (momentum broken)
# Zero-crossing is the key signal: long-term momentum flipped
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — ADD ret_168 condition (OR with existing):
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR ema_fast < ema_slow OR ret_168 < threshold

# threshold < 0: only exit when momentum is solidly negative (conservative)
# threshold = 0: exit at zero-crossing (neutral)
# threshold > 0: exit when momentum weakens even if still positive (aggressive)
```

## Parameter sweep
- threshold in [−0.15, −0.10, −0.05, 0.00, 0.05, 0.10]
- (6 configs + 1 baseline = 7 runs)

Rationale for range:
- −0.15: very conservative, only exits after 15% decline from 28d ago
- 0.00: exit at momentum zero-crossing (natural boundary)
- +0.10: aggressive, exits when momentum is still positive but weakening

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, avg holding period, exposure%
- Delta vs baseline for Sharpe, CAGR, MDD
- Exit attribution: how many exits triggered by trail / trend / ret_168?
- Timing analysis: for trades where ret_168 fires, how many bars BEFORE or AFTER
  the trail/trend exit would have fired? (positive = ret_168 exits earlier)
- Per-trade analysis: of trades exited by ret_168, what fraction were losers vs
  winners? (selectivity check — does it selectively cut losers?)

## Implementation notes
- Use x39/explore.py's compute_features() which already computes ret_168
- ret_168 is NaN for first 168 bars — during warmup period, use only
  trail + trend exits (no ret_168 supplementary exit)
- ret_168 is a LAGGING indicator (28-day lookback). In sharp reversals it may
  react slower than trail stop. The value is in catching STRUCTURAL reversals
  that develop gradually — where trail stop keeps resetting upward during a
  topping pattern and then finally gets hit during the crash.
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days

## Output
- Script: x39/experiments/exp21_ret168_momentum_exit.py
- Results: x39/results/exp21_results.csv

## Result
_(to be filled by experiment session)_
