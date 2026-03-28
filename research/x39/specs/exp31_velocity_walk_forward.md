# Exp 31: Velocity Walk-Forward Validation

## Status: PENDING

## Hypothesis
Exp28 found that rangepos VELOCITY (rate of change) provides marginal but real
improvement as supplementary exit:
- Part A best: vel_N=6, v=-0.3 → Sharpe +0.0364, MDD -7.40 pp, 47 exits
- Part C best: vel_N=6, v=-0.2, tq=0.0 → Sharpe +0.0699, MDD -5.21 pp, 42 exits

However, exp30 proved that the LEVEL-based AND gate (exp22: rp<0.20, tq<-0.10)
fails WFO: helps in bear markets, hurts in bull markets, mean d_Sharpe < 0.
The mechanism is regime-dependent, not alpha.

**The question**: does velocity share the same regime-dependency?

Arguments FOR velocity surviving WFO:
- Velocity captures RATE of decline, not absolute position. Fast drops
  (delta_rp < -0.3 in 6 bars) may be regime-invariant — they signal
  sudden disruptions in both bull corrections and bear waterfalls.
- exp30's failure was specific to LEVEL thresholds: low rangepos in a
  bull market = healthy consolidation (false positive). But fast velocity
  drops in a bull market = genuine disruption (potentially fewer FPs).

Arguments AGAINST:
- Velocity delta (+0.07) is same magnitude as level delta (+0.057) that
  failed WFO. Similar size → similar vulnerability.
- N=6 is fragile (N=12/24 fail). Single-window dependency.
- exp30 showed: ALL supplementary exits conflict with trend-following in
  trending periods. Velocity may not be exempt from this structural issue.

This is the FINAL experiment for x39. If velocity fails WFO, the entire
supplementary exit research line is closed. If it passes, velocity becomes
a candidate for formal validation via the v10 pipeline.

## Baseline
E5-ema21D1 (simplified replay): full-sample ~1.2965 Sharpe, ~221 trades.

## WFO Design
**Same anchored walk-forward as exp30** (for direct comparison):

```
Window 1:  Train [2019-01 → 2021-06]  Test [2021-07 → 2023-06]
Window 2:  Train [2019-01 → 2022-06]  Test [2022-07 → 2024-06]
Window 3:  Train [2019-01 → 2023-06]  Test [2023-07 → 2025-06]
Window 4:  Train [2019-01 → 2024-06]  Test [2024-07 → 2026-02]
```

4 windows. Identical to exp30 for apples-to-apples regime comparison.

## Configs to WFO-test

**Config A — Velocity-only (exp28 Part A):**
```python
# Exit: close < trail_stop OR ema_fast < ema_slow
#       OR delta_rp_6 < velocity_threshold
# where delta_rp_6[i] = rangepos_84[i] - rangepos_84[i - 6]
```
Training grid:
- velocity_threshold in [-0.40, -0.30, -0.20, -0.10]
- (4 configs per window)

**Config C — Velocity + trendq AND (exp28 Part C):**
```python
# Exit: close < trail_stop OR ema_fast < ema_slow
#       OR (delta_rp_6 < velocity_threshold AND trendq_84 < tq_threshold)
```
Training grid:
- velocity_threshold in [-0.30, -0.20, -0.10]
- tq_threshold in [-0.20, 0.00, 0.20]
- (9 configs per window)

## Procedure per window

**Step 1: Train** — Run all configs on TRAINING period.
Select best by highest Sharpe.

**Step 2: Test** — Apply train-selected config on TEST period.
Also run baseline (no supplementary exit) on same test period.
Record: d_Sharpe, d_MDD, velocity exit count.

**Step 3: Also test fixed configs** on TEST period (no training selection):
- Fixed A: vel=-0.30 (exp28 Part A best)
- Fixed C: vel=-0.20, tq=0.00 (exp28 Part C best)

## What to measure

Per window:
- Train-selected config (which parameters?)
- Test: velocity Sharpe, baseline Sharpe, d_Sharpe, d_MDD
- Test: velocity exit count
- Fixed config test performance (for comparison)

Aggregate:
- **WFO win rate**: # windows where velocity beats baseline / 4
  - Target: >= 3/4 (75%)
- **WFO mean d_Sharpe**: average across 4 test windows
  - Target: > 0
- **Parameter stability**: do selected params jump across windows?
- **Regime comparison with exp30**: same bear/bull pattern?
  - W1/W2 (bear-inclusive): velocity d_Sharpe vs exp30 AND gate d_Sharpe
  - W3/W4 (bull): velocity d_Sharpe vs exp30 AND gate d_Sharpe
  - If velocity shows SAME pattern (bear+, bull−) → structural, not fixable

## Decision criteria

| Outcome | Action |
|---------|--------|
| WFO win rate >= 3/4 AND mean d_Sharpe > 0 | **PASS** — velocity is temporally stable. Candidate for v10 formal validation. |
| WFO win rate 2/4 AND mean d_Sharpe ≈ 0 | **INCONCLUSIVE** — same as exp30. Close x39. |
| WFO win rate <= 2/4 OR mean d_Sharpe < 0 | **FAIL** — velocity is regime-dependent. Close x39. |

If FAIL or INCONCLUSIVE: **x39 is CLOSED.** Conclusion: E5-ema21D1 exit
mechanism (trail + EMA cross-down) cannot be improved by supplementary exits
derived from x39 feature space. Full-sample improvements are selection bias.

## Implementation notes
- Use exp28 code as base. Add outer WFO loop (same structure as exp30).
- N=6 FIXED (not in training grid — exp28 showed N=6 is only viable window,
  and including N in training would overfit on a fragile dimension).
- Split by DATE using datetime column. Warmup of 365 days within each window.
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Print per-window results AND exp30 comparison side by side.

## Output
- Script: x39/experiments/exp31_velocity_walk_forward.py
- Results: x39/results/exp31_results.csv

## Result
_(to be filled by experiment session)_
