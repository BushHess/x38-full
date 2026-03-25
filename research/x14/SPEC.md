# X14: Trail-Stop Churn Filter — Design & Validation

## Central Question

X13 proved that predictive information EXISTS at the trail stop trigger
(AUC=0.805, permutation p=0.002, bootstrap median AUC=0.68). The oracle
ceiling is massive (+0.845 Sharpe).

**Can we capture this signal with a simple filter that strictly improves
E0+EMA1D21 — and survives proper OOS validation?**

This is the hardest part: X13 answered an existence question. X14 must
build a filter, which means adding parameters, which means overfitting risk.

## Prior: Key Numbers from X12 + X13

### X12 (mechanism forensics)
- E0+EMA1D21: Sharpe=1.336, CAGR=55.3%, MDD=42.0%, 186 trades
- 63% trail stop exits are churn (re-entry within 20 bars)
- Churn PnL is NET POSITIVE (+$329,680) — churn exits capture profits
- E5 doesn't fix churn; E5-E0 gap is noise (P=46.4% bootstrap)

### X13 (predictability)
- Oracle ceiling: Sharpe 2.18 (+0.845), CAGR 121.6%, MDD 29.3%, 82 trades
- Oracle suppresses 104 trade-level exits (186→82), 1627 bar-level triggers
- Top features by Cliff's delta:
  - **ema_ratio** = +0.567 (large) — churn when trend strong
  - **bars_held** = +0.520 (large) — churn when trade mature
  - **d1_regime_str** = +0.458 (medium) — churn when D1 regime healthy
  - **bar_range_atr** = -0.291 (small) — true reversal when bar wide
- Logistic model: ema_ratio coef=+0.49, bars_held=+0.46, d1_regime=+0.32
- LOOCV AUC=0.805, permutation p=0.002
- Bootstrap median AUC=0.68, P(AUC>0.60)=86.8%
- Stable across all 5 churn windows (10-40 bars)

### Critical Context
- 17+ alternatives previously rejected — none strict-dominate E0
- Trail sweep: monotonic return/risk tradeoff (Pareto frontier)
- X13 says the frontier is breakable. X14 tests whether we CAN break it.

## Anti-Overfitting Protocol

### The Core Risk

X13 discovered features on the SAME data (2019-2026) that X14 will use
for validation. Even with walk-forward, the feature SELECTION is informed
by the full dataset. This is "implicit look-ahead."

### Mitigations (layered)

1. **Pre-registration:** This spec defines all filter designs, test order,
   and verdict gates BEFORE any X14 code runs. No post-hoc modifications.

2. **Economic motivation:** Features are grounded in market logic, not
   data-mined from a large candidate pool:
   - ema_ratio: trend-following alpha comes from trends; exiting during
     a strong trend is mechanically costly
   - d1_regime_str: higher timeframe confirms lower timeframe
   - bar_range_atr: wide bars indicate real selling, not noise

3. **X13 bootstrap confirmed OOS predictability:** AUC=0.68 median across
   500 VCBB paths. Features predict churn on synthetic price paths too.

4. **Fixed-sequence testing:** Designs tested simplest-first. Only the
   first passing design is accepted. FWER controlled at α=0.05.

5. **WFO + bootstrap + jackknife:** Three independent OOS validations.
   All three must pass.

6. **DOF correction:** Each new parameter penalised via Nyholt effective
   DOF in the PSR calculation.

### What Would Invalidate Results

If ANY of the following occur, the filter is REJECTED regardless of metrics:
- WFO win rate < threshold → filter doesn't generalise temporally
- Bootstrap P(improvement) < 60% → edge is sample-specific
- MDD increases > 5 pp vs E0 → filter trades return for risk
- Jackknife drops Sharpe below E0 in > 2/6 years → unstable

## Filter Designs (pre-specified order)

Designs are tested in order of complexity. Fixed-sequence procedure:
test Design A at α=0.05. If PASS → accept, stop. If FAIL → test B at
α=0.05. Continue until one passes or all fail.

### Design A: Entry-Signal Gate (0 new parameters)

**Logic:** At each bar where trail stop would trigger (`close < peak -
3×ATR`), check if the ENTRY signal is currently active:

```
if ema_fast[i] > ema_slow[i] AND vdo[i] > 0 AND regime_h4[i]:
    SUPPRESS trail stop (stay in position)
else:
    ALLOW trail stop (exit normally)
```

**Rationale:** If the system would immediately re-enter after exiting,
the exit is wasteful. Suppress exits during active entry signals.

**Zero new parameters** — reuses existing entry conditions. No DOF penalty.
No optimisation needed. No overfitting risk in the filter itself.

**Risk:** May be too aggressive. At most trail stop bars, EMA fast > EMA
slow (mean ema_ratio = 1.038 at trail stops). But VDO < 0 at many exits
(mean = -0.011), so the VDO gate provides meaningful filtering. D1 regime
provides additional selectivity.

**Expected behaviour:** Suppress ~50-70% of trail stops (where entry signal
active). Allow ~30-50% (where VDO < 0 or regime off). Trade count drops
from ~186 to ~100-130. Holding period increases.

### Design B: EMA-Ratio Threshold (1 new parameter)

**Logic:** At trail stop trigger, suppress if trend is "strong enough":

```
if ema_fast[i] / ema_slow[i] > τ:
    SUPPRESS trail stop
else:
    ALLOW trail stop
```

**Parameter:** τ ∈ {1.000, 1.005, 1.010, 1.015, 1.020, 1.025, 1.030,
1.035, 1.040, 1.050, 1.060, 1.080} (12 grid values)

**Rationale:** ema_ratio is the strongest feature (Cliff's d = 0.567).
Churn exits have mean ema_ratio = 1.048, true exits = 1.021. A threshold
around 1.02-1.04 should separate the groups.

**Optimisation:** τ selected by walk-forward (train on past, test on future).
See WFO Framework section.

**1 new parameter** → DOF penalty via Nyholt correction.

### Design C: EMA-Ratio + D1-Regime Dual Threshold (2 new parameters)

**Logic:** Suppress only if BOTH conditions met:

```
if ema_fast[i] / ema_slow[i] > τ_ema AND d1_regime_str[i] > τ_d1:
    SUPPRESS trail stop
else:
    ALLOW trail stop
```

**Parameters:**
- τ_ema ∈ {1.00, 1.01, 1.02, 1.03, 1.04, 1.05} (6 values)
- τ_d1 ∈ {0.00, 0.01, 0.02, 0.03, 0.04, 0.05} (6 values)
- Grid: 36 combinations

**Rationale:** Dual gate reduces false suppressions. Requires BOTH trend
strength AND regime health to suppress → more conservative than B.

**2 new parameters** → larger DOF penalty.

### Design D: Walk-Forward Logistic Model (model-based)

**Logic:** In each WFO fold, fit L2-logistic model on training trail stops.
At trail stop trigger, suppress if P(churn | features) > 0.5.

**Parameters:** 10 feature weights + bias + regularisation C = 12 effective.
But WFO means parameters are always trained on past data only.

**Rationale:** Captures all feature interactions. Walk-forward training
means no in-sample contamination.

**Risk:** Most complex. Highest DOF. Only tested if A/B/C all fail.
The logistic model from X13 is NOT reused (that was trained on full data).
Each WFO fold trains its own model.

## Simulation Details

### Modified sim_e0_d1 with filter

The filter modifies only the trail stop exit logic. Entry logic and
EMA cross-down exit are UNCHANGED.

```python
# At each bar where trail stop triggers:
if close[i] < peak - trail_mult * atr[i]:
    if filter_suppresses(i):    # <-- new: filter check
        pass                    # stay in position, trail continues
    else:
        exit_reason = "trail_stop"
        pending_exit = True
# EMA cross-down exit: unchanged
elif ema_fast[i] < ema_slow[i]:
    exit_reason = "trend_exit"
    pending_exit = True
```

### Bar-level vs trade-level suppression

When the filter suppresses at bar i, the position stays open. At bar i+1,
if close is still below the trail, the trail stop tries again. The filter
re-evaluates at EACH bar. This means:
- Multiple bar-level suppressions per trade
- The trail level keeps evolving (ratchet: only moves up with new peaks)
- After price recovers past the trail, the stop deactivates naturally

### Effect on trail dynamics

After suppression, the trail level = `peak - 3×ATR`. If price recovers
and makes a new high, peak updates → trail ratchets up. ATR may change
during the pullback period. The trail stop is NOT reset or weakened by
suppression — it's the same mechanism, just held through a pullback.

## Walk-Forward Optimisation (WFO) Framework

### Window structure

Post-warmup data: 2020-01 to 2026-02 (~6 years H4).
Expanding-window WFO with 1-year test periods:

| Fold | Train        | Test         |
|------|-------------|--------------|
| 1    | 2020-01 → 2021-12 | 2022-01 → 2022-12 |
| 2    | 2020-01 → 2022-12 | 2023-01 → 2023-12 |
| 3    | 2020-01 → 2023-12 | 2024-01 → 2024-12 |
| 4    | 2020-01 → 2024-12 | 2025-01 → 2026-02 |

4 folds. Win rate = folds where filtered Sharpe > E0 Sharpe on test data.

### WFO for Design A (0 params)

No optimisation needed. Run filtered sim on each test fold, compare to E0.
This is pure OOS evaluation.

### WFO for Design B (1 param)

In each fold's training period:
1. Run E0 sim on training data → get trail stop exits
2. For each τ in grid: run filtered sim on training data → compute Sharpe
3. Select τ* = argmax(Sharpe_train)
4. Run filtered sim on test data with τ* → record test Sharpe

### WFO for Design C (2 params)

Same as B but sweep the 36-value (τ_ema × τ_d1) grid.

### WFO for Design D (logistic model)

In each fold's training period:
1. Run E0 sim → get trail stop exits with features + churn labels
2. Fit L2-logistic on training trail stops (standardise, select C by CV)
3. Run filtered sim on test data using the trained model for suppression

### Metric: WFO win rate

- Win: filtered_sharpe_test > e0_sharpe_test (same fold)
- Pass threshold: ≥ 3/4 folds (75%)

### Secondary: Wilcoxon signed-rank

If ≥ 6 folds available, compute Wilcoxon p-value on paired Sharpe deltas.
With 4 folds, Wilcoxon is underpowered — win rate is the primary metric.

## Test Suite

### T0: Full-Sample Screening (all 4 designs)

**Purpose:** Quick in-sample check. Which designs improve on E0?

For each design: run filtered sim on full data (no WFO), compare to E0.

**Outputs per design:**
- Sharpe, CAGR, MDD, trade count, avg holding period
- Churn rate: fraction of trail stops suppressed
- Trail stop exits: allowed vs suppressed (trade-level)
- Delta vs E0: d_sharpe, d_cagr, d_mdd
- Screen: d_sharpe > 0 (minimal bar — just checks direction)

**For Design B:** sweep all 12 τ values, find τ* (in-sample optimal).
**For Design C:** sweep all 36 grid points, find (τ_ema*, τ_d1*).

**Artefact:** `x14_screening.csv`

**Gate:** Design must show d_sharpe > 0 in full sample to proceed to WFO.
(If it can't even beat E0 in-sample, WFO is pointless.)

### T1: Walk-Forward Validation

**Purpose:** OOS validation for each design that passes T0 screen.

Run the WFO framework described above. 4 folds.

**Outputs per design:**
- Per-fold: train Sharpe, test Sharpe (E0 and filtered), d_sharpe
- Win rate (folds where filtered > E0)
- Mean test d_sharpe
- For Design B/C: τ* selected in each fold (check stability)
- For Design D: model coefficients in each fold (check stability)

**Artefact:** `x14_wfo_results.csv`

**Gate:** win_rate ≥ 3/4 AND mean_test_d_sharpe > 0

### T2: Bootstrap Validation (500 VCBB)

**Purpose:** Test whether the winning design's improvement survives on
synthetic price paths.

**Method:** 500 VCBB paths (block=60, seed=42).
For each path:
1. Run E0 sim → baseline metrics
2. Run filtered sim (same design, fixed parameters from T1) → filtered metrics
3. Record: d_sharpe, d_cagr, d_mdd

**Parameter choice for bootstrap:**
- Design A: no parameters, same filter for all paths
- Design B: use τ = WFO consensus (most common τ* across folds). If no
  consensus, use the full-sample τ* from T0.
- Design C/D: same logic

**Outputs:**
- d_sharpe: median, [p5, p95]
- P(d_sharpe > 0): fraction where filter beats E0
- P(d_mdd < 0): fraction where filter reduces MDD
- d_cagr: median, [p5, p95]

**Artefact:** `x14_bootstrap.csv`

**Gate:** P(d_sharpe > 0) > 0.60 AND median_d_mdd ≤ +5.0 pp

### T3: Jackknife Leave-Year-Out

**Purpose:** Test stability by dropping each year and re-evaluating.

**Method:** 6 folds (drop 2020, 2021, 2022, 2023, 2024, 2025).
For each fold:
1. Run E0 sim on remaining data → baseline Sharpe
2. Run filtered sim on remaining data → filtered Sharpe
3. Record d_sharpe

**Outputs:**
- Per-year: d_sharpe, filtered Sharpe, E0 Sharpe
- Count of folds where d_sharpe < 0 (filter WORSE)
- Jackknife mean d_sharpe ± SE

**Artefact:** `x14_jackknife.csv`

**Gate:** d_sharpe < 0 in ≤ 2/6 folds (filter is worse in at most 2 years)

### T4: DOF Correction / PSR

**Purpose:** Penalise for additional parameters.

**Method:**
- E0 baseline: 4 effective params (slow, trail, vdo_threshold, d1_ema_period)
  Nyholt M_eff ≈ 4.35 (from prod_readiness study)
- Design A: +0 params → 4.35 effective
- Design B: +1 param → 5.35 effective
- Design C: +2 params → 6.35 effective
- Design D: +10 effective (model weights) → 14.35 effective

Compute PSR (Probabilistic Sharpe Ratio) with appropriate DOF.
Compare filtered PSR to E0 PSR.

**Outputs:**
- E0 PSR, filtered PSR
- Delta PSR
- Effective DOF used
- Nyholt-corrected p-value for Sharpe improvement

**Artefact:** included in `x14_results.json`

**Gate:** filtered_PSR > 0.95

### T5: Comprehensive Comparison Table

**Purpose:** Side-by-side comparison of E0, winning filter, E5, and oracle.

**Outputs (per strategy):**

| Metric                | E0   | E0+Filter | E5   | Oracle |
|-----------------------|------|-----------|------|--------|
| Sharpe                |      |           |      |        |
| CAGR (%)              |      |           |      |        |
| MDD (%)               |      |           |      |        |
| Trades                |      |           |      |        |
| Avg holding (bars)    |      |           |      |        |
| Trail stop exits      |      |           |      |        |
| Churn rate             |      |           |      |        |
| Trail stops suppressed|      |           |      |        |
| WFO win rate          |      |           |  —   |   —    |
| Bootstrap P(Sharpe>0) |      |           |      |   —    |
| PSR                   |      |           |      |   —    |

**Artefact:** `x14_comparison.csv`

## Verdict Gates (for winning design)

| Gate | Condition | Meaning |
|------|-----------|---------|
| **G0** | T0 d_sharpe > 0 | In-sample improvement exists |
| **G1** | T1 win rate ≥ 3/4 | Temporally robust (WFO) |
| **G2** | T2 P(d_sharpe > 0) > 0.60 | Bootstrap robust |
| **G3** | T2 median d_mdd ≤ +5.0 pp | MDD not materially worse |
| **G4** | T3 d_sharpe < 0 in ≤ 2/6 years | Jackknife stable |
| **G5** | T4 PSR > 0.95 | Survives DOF correction |

ALL 6 gates must pass for PROMOTE. Any gate failure → REJECT that design
and try the next in sequence.

## Decision Matrix

| Outcome | Verdict |
|---------|---------|
| Design A passes G0-G5 | **PROMOTE_A** — zero-param filter, strongest result |
| Design A fails, B passes G0-G5 | **PROMOTE_B** — one-param filter, WFO-validated |
| A+B fail, C passes G0-G5 | **PROMOTE_C** — two-param filter, more DOF risk |
| A+B+C fail, D passes G0-G5 | **PROMOTE_D** — model-based, highest complexity |
| All fail G0 | **CEILING_UNREACHABLE** — information exists but no simple filter captures it |
| All pass G0, fail G1 | **NOT_TEMPORAL** — works in-sample only, not across time |
| All pass G0+G1, fail G2 | **NOT_ROBUST** — works on historical path, not on bootstrap |
| All pass G0-G2, fail G3 | **MDD_TRADEOFF** — improves return but costs risk |
| All pass G0-G4, fail G5 | **DOF_KILLED** — improvement is noise given parameter count |

### What Each Verdict Means

**PROMOTE_X:** The filter strictly improves E0+EMA1D21 with proper OOS
validation. The identified design becomes a candidate for integration into
the primary strategy. Integration design is a SEPARATE study (X15+).

**CEILING_UNREACHABLE:** X13's information is real but can't be captured
with a static threshold filter. Possible reasons: the predictive signal
is non-linear, time-varying, or requires more features than the cost of
additional parameters justifies. E0 remains primary.

**NOT_TEMPORAL / NOT_ROBUST:** Filter works on some data but not generally.
The churn prediction signal may be regime-specific (e.g., works only in
2021-2022 bull market). E0 remains primary.

**MDD_TRADEOFF:** Filter improves Sharpe/CAGR by suppressing trail stops,
but holding through pullbacks increases drawdown. This is a risk profile
change, not a strict improvement. Same conclusion as LATCH/SM alternatives.

**DOF_KILLED:** The filter "improves" metrics, but the improvement is
within the noise band after accounting for the additional parameters.
E0 remains primary.

### What This Does NOT Do

- Does not integrate the filter into production code
- Does not change E0+EMA1D21 or E5+EMA1D21 status
- Does not propose deployment
- Does not test filter interaction with regime monitor
- Does not sweep core strategy parameters (slow, trail, etc.)
- Only answers: can a simple filter capture X13's signal and survive OOS?

## Known Risks & Limitations

1. **Implicit look-ahead:** Feature selection (X13) used the same data
   window. Mitigated by pre-registration, economic motivation, bootstrap
   OOS in X13, and WFO in X14. Not fully eliminated.

2. **Small OOS sample:** 4 WFO folds, each with ~1 year of test data
   (~1500 H4 bars, ~20-40 trades). Individual fold results are noisy.
   Bootstrap (T2) provides the stronger OOS test.

3. **Oracle ceiling includes compounding:** Oracle Sharpe 2.18 benefits
   from compounding (higher NAV → larger positions → more profit). A
   partial filter will capture much less than the oracle ceiling.

4. **Churn PnL is positive:** X12 showed churn exits are net profitable.
   Suppressing them means giving up profit-taking at local peaks. The
   filter must recover MORE from continued holding than it loses from
   not taking profits. The oracle (P0 from X13) shows this is possible
   (+0.845 Sharpe) but a partial filter may not achieve it.

5. **Trade count reduction:** The oracle reduces trades from 186 to 82.
   Fewer trades → noisier Sharpe/CAGR estimates. Need sufficient trades
   in each WFO fold and bootstrap path for meaningful comparison.

6. **Design A may effectively remove the trail stop:** If the entry signal
   is active at most trail stop triggers, Design A lets very few trail
   stops through. The remaining exits are mostly EMA cross-down. This is
   essentially a different strategy (EMA-only exit) rather than a "filter."
   T0 will quantify how many trail stops Design A allows vs suppresses.

7. **Threshold stability for Design B:** If WFO selects different τ*
   values across folds (e.g., 1.01 in fold 1, 1.05 in fold 3), the
   threshold is unstable → less trustworthy. T1 reports τ* per fold.

## Output Files

```
x14/
  SPEC.md                    # this file
  benchmark.py               # single script, all tests T0-T5
  x14_results.json           # nested dict of all results
  x14_screening.csv          # T0: full-sample screening
  x14_wfo_results.csv        # T1: walk-forward results
  x14_bootstrap.csv          # T2: bootstrap distribution
  x14_jackknife.csv          # T3: leave-year-out results
  x14_comparison.csv         # T5: comprehensive comparison
```

## Dependencies

```python
import numpy as np
from scipy.signal import lfilter
from scipy.optimize import minimize       # L2-logistic for Design D
from scipy.stats import wilcoxon          # WFO signed-rank (if ≥6 folds)
from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
```

## Estimated Runtime

- T0 (screening): ~10s (4 designs × multiple sims)
- T1 (WFO): ~30s (4 folds × 12-36 sims per fold per design)
- T2 (bootstrap): ~300s (500 paths × 2 sims)
- T3 (jackknife): ~10s (6 folds × 2 sims)
- T4 (DOF/PSR): ~1s (computation only)
- T5 (comparison): ~2s
- Total: ~6 min (faster than X13 — no permutation test)
