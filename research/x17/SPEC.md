# X17: Percentile-Ranked Selective Exit — Nested WFO & ΔU Diagnostic

## Context

X16 Design E (WATCH state machine) showed +0.088 Sharpe in-sample and 100% WFO
wins, but failed bootstrap (P(d>0)=49.8%). External review identified three
methodological weaknesses:

1. **τ-probability threshold is calibration-dependent**: P(churn)>0.85 means
   different things on different training windows and bootstrap paths.
2. **Full-sample screening leaks information**: T2 pre-selected params on full
   data before WFO, inflating apparent robustness.
3. **Large parameter grid (240 configs) + long G (4-20) overfits path structure**:
   WATCH mechanism exploited BTC-specific autocorrelation that bootstrap destroys.

External guidance (sample-size literature):
- With 168 episodes, continuous ΔU regression is too data-hungry (Riley: 20 params
  at R²=0.90 needs 254 samples; binary outcome is more forgiving).
- Penalized logistic (ridge) as ranker is appropriate at this sample size.
- Risk-coverage curve (sweep α) is the natural evaluation framework for selective
  prediction / abstention problems.

## Key Changes from X16

| Aspect | X16 | X17 |
|--------|-----|-----|
| Threshold | τ (probability, absolute) | α (percentile, rank-based) |
| Grid size | 240 configs | 60 configs |
| Grace window G | {4,6,8,12,16,20} | {1,2,3,4} |
| Deeper stop δ | {0.5,1.0,1.5,2.0} | {0.5,1.0,1.5} |
| Tuning method | Full-sample T2 + WFO T3 | Nested WFO only |
| Features | 10 (incl. trade context) | 7 (market-state only, per X14) |
| ΔU analysis | None | Diagnostic (validate ranker) |
| Regime check in WATCH | No | Yes (exit if D1 regime off) |

## Architecture

### Score → Percentile → WATCH Decision

```
1. Train L2-penalized logistic on training trail stops (7 features)
2. Compute P(churn) scores for all training trail-stop episodes
3. Set alpha_threshold = percentile(training_scores, 100 - α)
4. In sim, at each first trail breach:
   a. Compute score from 7 market-state features
   b. If score > alpha_threshold AND trend positive AND regime on:
      → Enter WATCH(G, δ)
   c. Else: exit immediately (trail stop)
```

### WATCH(G, δ) Policy

```
- Hold max G bars (1-4 H4 bars = 4-16 hours)
- Deeper fallback stop: peak - (trail_mult + δ) × ATR
- Exit immediately if:
  a. Price reclaims original trail level → back to LONG_NORMAL
  b. Price hits deeper stop → exit
  c. G bars elapsed without reclaim → timeout exit
  d. EMA fast < EMA slow (trend reversal) → exit
  e. D1 regime turns off → exit
```

### Feature Set (7 market-state features, same as X14)

| # | Feature | Source |
|---|---------|--------|
| 1 | ema_ratio (EMA_fast / EMA_slow) | Market state |
| 2 | atr_pctl (ATR percentile, 100-bar window) | Market state |
| 3 | bar_range_atr (bar range / ATR) | Market state |
| 4 | close_position ((close-low)/(high-low)) | Market state |
| 5 | vdo_at_exit | Market state |
| 6 | d1_regime_str ((D1 close - D1 EMA) / D1 close) | Market state |
| 7 | trail_tightness (trail_mult × ATR / close) | Market state |

EPV = 62 non-churn events / 7 features ≈ 8.9 (borderline but acceptable with L2 regularization).

## Parameter Grid

```
α ∈ {5, 10, 15, 20, 25%}  — suppression budget (5 values)
G ∈ {1, 2, 3, 4}          — grace window in H4 bars (4 values)
δ ∈ {0.5, 1.0, 1.5}       — deeper stop addon in ATR (3 values)

Total: 5 × 4 × 3 = 60 configurations
```

## Test Suite

### T0: ΔU Diagnostic

Compute per-episode ΔU to validate that the binary ranker correctly sorts
episodes by WATCH utility.

**Method:**
1. Train model on full data → get scores for all 168 trail-stop episodes
2. For each (G, δ) combination (12 total):
   a. For each trail-stop episode, simulate WATCH(G,δ):
      - EXIT NOW: close at trail-stop price
      - WATCH: hold for up to G bars with deeper stop
      - ΔU = log(watch_exit_price / exit_now_price)
   b. Sort episodes by model score → quintile groups (~34 each)
   c. Report: mean ΔU, median ΔU, p10 (10th percentile) per quintile

**Expected:** Top quintiles (high P(churn) score) should have positive ΔU.
Bottom quintiles (low score = likely genuine reversals) should have negative ΔU.

**Gate G0:** For the best (G,δ), top 2 quintiles have mean ΔU > 0 (monotonicity).

**Artefact:** `x17_delta_u.csv`

### T1: Nested Walk-Forward Validation (primary test)

4 expanding folds. Each fold independently trains model, computes scores,
and sweeps (α, G, δ) on training data.

**Method:** For each fold:
1. Train model on training portion (E0 sim → trail stops → fit)
2. Compute scores for all training trail-stop episodes
3. For each (α, G, δ):
   a. Compute alpha_threshold = percentile(train_scores, 100 - α)
   b. Run WATCH sim on full data with (G, δ, alpha_threshold)
   c. Measure training-window Sharpe
4. Select best (α, G, δ) by training Sharpe
5. Run with best params on full data → measure test-window Sharpe
6. d_sharpe = test_filter_sharpe - test_e0_sharpe

**Gate G1:** win_rate >= 3/4 AND mean d_sharpe > 0

**Artefact:** `x17_wfo.csv`

### T2: Bootstrap Validation (500 VCBB)

Use consensus params from T1 (mode across folds).

**Method:** For each of 500 bootstrap paths (seed=42, block=60):
1. Split: train on first 60%
2. Run E0 on training portion → trail stops → fit model → compute train scores
3. Compute alpha_threshold from training scores
4. Run WATCH sim on full path with trained model and consensus (G, δ)
5. Compare vs E0 on same path

**Gate G2:** P(d_sharpe > 0) > 0.60
**Gate G3:** median d_mdd ≤ +5.0 pp

**Artefact:** `x17_bootstrap.csv`

### T3: Jackknife (leave-year-out)

6 folds dropping each year 2020-2025.

**Gate G4:** d_sharpe < 0 in ≤ 2/6 years

**Artefact:** `x17_jackknife.csv`

### T4: PSR with DOF Correction

**Gate G5:** PSR > 0.95

DOF: E0_effective_DOF (4.35) + 3 (α, G, δ) = 7.35

### T5: Comparison Table

Side-by-side: E0, X17_WATCH, X14_D, X16_E.

**Artefact:** `x17_comparison.csv`

## Verdict Gates

| Gate | Test | Condition | Meaning |
|------|------|-----------|---------|
| G0 | T0 | Top 2 quintiles mean ΔU > 0 | Ranker sorts by utility |
| G1 | T1 | WFO ≥ 75%, mean d > 0 | Temporally robust |
| G2 | T2 | P(d_sharpe > 0) > 60% | Bootstrap robust |
| G3 | T2 | Median d_mdd ≤ +5pp | MDD acceptable |
| G4 | T3 | ≤ 2 negative jackknife | No single-year fragility |
| G5 | T4 | PSR > 0.95 | Statistically significant |

ALL gates pass → PROMOTE.

## Decision Matrix

| Outcome | Action |
|---------|--------|
| All gates pass | PROMOTE — α-ranked WATCH is production-ready |
| G0 fails | ABORT — ranker doesn't sort by utility |
| G1 fails | NOT_TEMPORAL — edge is in-sample only |
| G2 fails | NOT_ROBUST — same as X16, path-specific |
| G4 fails | FRAGILE — single-year dependency |
| G5 fails | UNDERPOWERED — DOF too high for sample |

## Consensus Params for Downstream Tests

After T1, extract per-fold best (α, G, δ). Take mode of each:
- If tie: use value from fold with highest d_sharpe
- These fixed params go to T2 (bootstrap), T3 (jackknife), T4 (PSR), T5 (comparison)

For bootstrap (T2): model is retrained per path, but (α, G, δ) are fixed.
The alpha_threshold is recomputed per path from that path's training scores.

## ΔU as Evaluation Target (Future Use)

If T1 shows stable lift AND T0 shows good score-ΔU monotonicity but
insufficient magnitude separation in top bucket, consider:
1. Ordinal regression: 3-bin target (harmful / neutral / helpful)
2. Ridge regression: 2-4 features, continuous ΔU target
3. Only after (G, δ) are fixed (ΔU is policy-specific)

This is NOT part of X17 — only considered if X17 succeeds and a clear
regression opportunity is identified.

## Dependencies

```python
import numpy as np
from scipy.signal import lfilter
from scipy.optimize import minimize
from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
```

## Estimated Runtime

- T0 (ΔU diagnostic): ~2s (168 episodes × 12 (G,δ) combinations)
- T1 (nested WFO): ~10s (4 folds × 60 configs)
- T2 (bootstrap): ~120s (500 paths × 2 sims × model training)
- T3 (jackknife): ~2s (6 folds × 2 sims)
- T4 (PSR): ~1s
- T5 (comparison): ~1s
- Total: ~2.5 min

## Output Files

```
x17/
  SPEC.md                # this file
  benchmark.py           # single script, all tests T0-T5
  x17_results.json       # master results
  x17_delta_u.csv        # T0: per-episode ΔU by score quintile
  x17_wfo.csv            # T1: WFO fold results
  x17_bootstrap.csv      # T2: bootstrap distributions
  x17_jackknife.csv      # T3: jackknife fold results
  x17_comparison.csv     # T5: strategy comparison
```
