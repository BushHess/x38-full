# Exp 21: ret_168 Momentum Exit

## Status: DONE

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

### Summary table

| Config     | Sharpe | CAGR%  | MDD%   | Trades | WR%  | AvgHeld | ret168 exits | d_Sharpe | d_CAGR | d_MDD |
|------------|--------|--------|--------|--------|------|---------|--------------|----------|--------|-------|
| baseline   | 1.3098 | 52.70  | 41.01  | 197    | 40.6 | 36.4    | 0            | —        | —      | —     |
| thr=-0.15  | 1.3276 | 53.64  | 39.71  | 202    | 41.6 | 35.4    | 7            | +0.0178  | +0.94  | -1.30 |
| thr=-0.10  | 1.2974 | 51.81  | 42.69  | 212    | 40.1 | 33.5    | 22           | -0.0124  | -0.89  | +1.68 |
| thr=-0.05  | 1.2086 | 46.33  | 40.57  | 269    | 37.2 | 25.8    | 92           | -0.1012  | -6.37  | -0.44 |
| thr=0.00   | 0.9086 | 30.36  | 47.58  | 399    | 29.8 | 16.4    | 242          | -0.4012  | -22.34 | +6.57 |
| thr=+0.05  | 0.3320 | 5.65   | 74.71  | 656    | 23.5 | 9.1     | 526          | -0.9778  | -47.05 | +33.7 |
| thr=+0.10  | -0.3201| -15.42 | 90.95  | 946    | 21.0 | 5.5     | 858          | -1.6299  | -68.12 | +49.9 |

### Exit attribution
- baseline:  trail 179 (91%), trend 18 (9%), ret168 0 (0%)
- thr=-0.15: trail 179 (89%), trend 16 (8%), ret168 7 (3%)
- thr=-0.10: trail 175 (83%), trend 15 (7%), ret168 22 (10%)
- thr=-0.05: trail 164 (61%), trend 13 (5%), ret168 92 (34%)
- thr=0.00+: ret168 dominates (61-91%), destroys performance

### Timing analysis (all thresholds)
ret_168 ALWAYS exits earlier than trail/trend would have (100% of cases).
- thr=-0.15: median 33 bars earlier, mean avoided PnL -0.42 pp (hurts slightly)
- thr=-0.10: median 10 bars earlier, mean avoided PnL +2.25 pp (helps)
- thr=-0.05: median 16 bars earlier, mean avoided PnL -2.40 pp (hurts on average)
- thr=0.00: median 23 bars earlier, mean avoided PnL -4.44 pp (cuts winners hard)

### Selectivity
- thr=-0.15: ret168 WR 57% vs trail/trend 41% (7 exits — too few to conclude)
- thr=-0.10: ret168 WR 32% vs trail/trend 41% (exits more losers — good)
- thr=-0.05 to +0.10: ret168 WR 18-25% vs trail/trend 43-46% — cuts losers
  AND winners indiscriminately. Lower win rate because ret168 exits small
  trades before they have time to develop.

### Verdict: FAIL (marginal)
thr=-0.15 is the only config that improves BOTH Sharpe (+0.018) and MDD (-1.3 pp),
but the improvement is tiny (1.4% relative Sharpe) and based on only 7 ret168 exits.
This is noise, not a robust edge.

All other thresholds degrade performance. The pattern is clear and monotonic:
higher threshold → more ret168 exits → more premature exits of developing
trends → catastrophic destruction of CAGR and Sharpe.

**Root cause**: ret_168 is a LAGGING indicator (28-day lookback). By the time
it signals momentum reversal, the trail stop has ALREADY done its job for
sharp reversals. For gradual topping patterns, ret_168 exits BEFORE the
trail stop — but in doing so, it also exits profitable consolidation-then-
continuation patterns. The avoided_PnL analysis confirms: mean avoided PnL
is NEGATIVE for most thresholds, meaning ret_168 exits trades that would have
been MORE profitable if held to trail/trend exit.

The selectivity is anti-selective at conservative thresholds (thr=-0.15 exits
MORE winners than losers) and becomes loser-selective at aggressive thresholds
but at catastrophic cost to overall returns.

**Conclusion**: ret_168 as supplementary exit adds NO robust value to E5-ema21D1.
The trail stop + EMA cross-down exit system is already sufficient. ret_168's
28-day lookback is too slow to add useful information that the trail stop
(reactive to recent price) doesn't already capture.
