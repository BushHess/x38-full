# Exp 48: Selectivity Batch Screen — Pending Entry Filters

## Status: PENDING

## Hypothesis
Exp42 (vol compression WFO) established the critical criterion for robust
entry filters: **SELECTIVITY** — blocked entries must have lower win rate
than baseline entries IN ALL temporal regimes.

- exp34 (vol compression): blocked WR 27-41% < baseline 41% → WFO PASS 4/4
- exp33 (accel gate): blocked WR ≈ baseline WR → WFO FAIL 1/4
- exp01 (D1 anti-vol): "win rate unchanged" → NOT selective

Five Category A features (exp02-06) are PENDING with 2-3/5 significant
residual horizons. Instead of running 5 separate experiments, this batch
screen tests ALL of them for selectivity in one run. Only features that
pass the selectivity test are candidates for WFO validation.

This is an EFFICIENCY experiment: screen 5 features + 2 new candidates
in one run, then promote only the selective ones.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades, WR ~40.6%.

## Features to screen

| Feature | Source | Residual sig | Pending exp | Gate logic |
|---------|--------|-------------|-------------|------------|
| trendq_84 | Gen1 V3 | 3/5 | exp02 | trendq_84 > threshold |
| vol_per_range | x39 | 3/5 | exp03 | vol_per_range > threshold |
| trade_surprise_168 | Gen4 C3 | 2/5 | exp04 | trade_surprise_168 > threshold |
| d1_taker_imbal_12 | Gen4 C2 | 2/5 | exp05 | d1_taker_imbal_12 < threshold (negative=reversal) |
| body_consist_6 | x39 | 3/5 | exp06 | body_consist_6 > threshold |
| relvol_168 | Gen4 | 2/5 | NEW | relvol_168 > threshold |
| range_vol_84 | Gen4 | — | NEW | range_vol_84 < threshold (low range-vol) |

## Procedure (NOT a full backtest sweep)

For each feature, run a **selectivity diagnostic** only:

```python
# Step 1: Identify all baseline entry bars (EMA cross + VDO > 0 + D1 regime)
# Step 2: For each entry bar, simulate the trade → record win/loss
# Step 3: For threshold in [P25, P33, P50, P67, P75] of feature at entry bars:
#           - Split entries into PASS (feature passes gate) and BLOCKED
#           - Compute: pass_WR, blocked_WR, N_pass, N_blocked
# Step 4: Selectivity score = baseline_WR - blocked_WR
#           - Positive = gate blocks worse entries (GOOD)
#           - Negative = gate blocks better entries (BAD)
#           - Near zero = gate blocks randomly (USELESS)

# ALSO: compute per-window selectivity (same 4 WFO windows) to check
# if selectivity is regime-dependent or universal.
```

## What to measure

Per feature × threshold:
- N_pass, N_blocked, pass_WR, blocked_WR, selectivity_score
- Sharpe of PASS-only entries vs baseline (rough, from replay)

Per feature (aggregate):
- Is selectivity_score > 0 at ≥ 3/5 thresholds? → **SELECTIVE**
- Is selectivity_score > 0 in ALL 4 WFO windows? → **REGIME-ROBUST**
- Both SELECTIVE + REGIME-ROBUST → **PROMOTE to WFO test**

## Pass criteria
- Feature is PROMOTED if:
  1. selectivity_score > 0 at majority of thresholds (≥3/5)
  2. selectivity_score > 0 in ≥3/4 WFO windows
  3. N_blocked ≥ 15 in each window (sufficient sample)
- Features that fail selectivity → CLOSE (no WFO needed)

## Implementation notes
- Use explore.py's compute_features() + replay_trades() for entry identification
- Replay trades to get win/loss for each entry bar
- Feature values at entry bars from the feature DataFrame
- Use percentile thresholds (P25-P75) to avoid arbitrary threshold selection
- WFO windows: same as exp30/40/41/42
- Cost: 50 bps RT
- Warmup: 365 days

## Output
- Script: x39/experiments/exp48_selectivity_batch_screen.py
- Results: x39/results/exp48_results.csv

## Result
_(to be filled by experiment session)_
