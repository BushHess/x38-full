# Exp 48: Selectivity Batch Screen — Pending Entry Filters

## Status: DONE

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

**Date**: 2026-03-28
**Baseline**: 221 trades, WR=41.2%, span=8.37 years

### Full-sample selectivity + per-window regime robustness

| Feature | Sel (full) | Rgm (P50) | Best sel | Verdict |
|---------|-----------|-----------|----------|---------|
| trendq_84 | **5/5** | **3/4** | +4.2pp (P50) | **PROMOTE** |
| vol_per_range | 0/5 | 0/4 | -1.3pp | CLOSE (anti-selective) |
| trade_surprise_168 | 4/5 | 2/4 | +3.4pp (P25) | CLOSE (regime-dependent) |
| d1_taker_imbal_12 | 4/5 | 2/4 | +2.7pp (P33) | CLOSE (regime-dependent) |
| body_consist_6 | 0/5 | 3/4 | -0.2pp | CLOSE (not selective) |
| relvol_168 | 3/5 | 2/4 | +1.9pp (P75) | CLOSE (regime-dependent) |
| range_vol_84 | 1/5 | 0/4 | -3.5pp | CLOSE (anti-selective) |

### trendq_84 detail (the only PROMOTE)

**Full-sample** (gate: trendq_84 > threshold):
- P25 (0.108): pass WR 42.4%, blocked WR 37.5%, sel +3.7pp
- P33 (0.245): pass WR 42.6%, blocked WR 38.4%, sel +2.8pp
- P50 (0.465): pass WR 45.5%, blocked WR 36.9%, sel +4.2pp
- P67 (0.739): pass WR 46.6%, blocked WR 38.5%, sel +2.7pp
- P75 (0.946): pass WR 52.7%, blocked WR 37.3%, sel +3.8pp

**Per-window at P50** (threshold=0.465):
- W1 (2021-07 → 2023-06): N=49, blocked WR 30.0%, sel +4.7pp [SEL]
- W2 (2022-07 → 2024-06): N=62, blocked WR 35.5%, sel +0.0pp [---]
- W3 (2023-07 → 2025-06): N=59, blocked WR 40.5%, sel +3.5pp [SEL]
- W4 (2024-07 → 2026-02): N=41, blocked WR 40.0%, sel +6.3pp [SEL]

### Interpretation

1. **trendq_84 is the only selective + regime-robust feature.** It blocks
   entries where momentum-quality is low (ret_84 / realized_vol_84 < threshold).
   Blocked entries have 3-5pp lower win rate across most temporal regimes.
   W2 is the lone zero-selectivity window but not anti-selective.

2. **6/7 features CLOSE.** Consistent with exp01/exp33/exp51 precedent:
   most features lack selectivity. Vol compression (exp34/42) remains the
   only prior selective feature. trendq_84 is the second discovery.

3. **trade_surprise_168 and d1_taker_imbal_12** showed full-sample selectivity
   (4/5) but failed regime-robustness (2/4). Their selectivity is temporal —
   strong in recent windows, absent in earlier ones.

4. **Anti-selective features**: vol_per_range and range_vol_84 block BETTER
   entries (negative selectivity). These should never be used as entry gates.

5. **trendq_84 PROMOTE does NOT mean deploy.** It means: proceed to full
   WFO validation (separate task, outside x39). The selectivity screen is
   necessary but not sufficient — WFO must confirm that the threshold
   selected in-sample generalizes out-of-sample.
