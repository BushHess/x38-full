# X16: Stateful Exit — WATCH State & Adaptive Trail

## Central Question

X14 Design D captures only 10.9% of the oracle ceiling (+0.092 / +0.845 Sharpe).
X15 proved that simply adding trade-context features causes catastrophic
over-suppression (15,020 suppressions, 7 trades, MDD 77%).

**Root cause diagnosis** (from X15 post-mortem + external analysis):

1. **Feedback loop at inference**: X14/X15 query the model at EVERY bar where
   `close < trail_stop`. When suppressed, the trade continues, next bar the model
   is queried again with even stronger trade-context features (bars_held +1,
   dd_from_peak still small) → P(churn) stays high → suppress again → indefinitely.

2. **Binary churn label is asymmetric**: "recover peak within 20 bars" treats
   a 0.2% reclaim and a 20% trend extension identically, while downside of
   a false suppress (holding through a real reversal) is much larger.

3. **Model predicts correctly but uselessly**: 63% of trail stops ARE churn.
   A model that learns this base rate + trade-context reinforcement will
   predict "churn" for almost everything → suppress everything → hold forever.

**X16 tests a fundamentally different approach**: instead of binary
suppress/allow evaluated every bar, use a **stateful exit architecture**
with bounded actions, evaluated once per breach episode.

## Prior: Key Numbers from X12-X15

### X12 (mechanism forensics)
- E0+EMA1D21: Sharpe=1.336, CAGR=55.3%, MDD=42.0%, 186 trades
- 63% trail stop exits are churn (re-entry within 20 bars)
- Churn PnL is NET POSITIVE (+$329,680)
- E5-E0 gap is noise (P=46.4%)

### X13 (predictability)
- Oracle ceiling: Sharpe 2.18 (+0.845), CAGR 121.6%, MDD 29.3%, 82 trades
- LOOCV AUC=0.805, permutation p=0.002
- Bootstrap median AUC=0.68, P(AUC>0.60)=86.8%
- Top features: ema_ratio (d=0.567), bars_held (d=0.520), d1_regime_str (d=0.458)

### X14 (static filter)
- Design D: Sharpe 1.428 (+0.092), MDD 36.7% (-5.3pp), 133 trades
- 7 effective features (3 trade-context zeroed by static mask)
- All 6 gates pass. Oracle capture: 10.9%

### X15 (dynamic filter — ABORT)
- 10-feature dynamic: Sharpe 1.030, 7 trades, 15,020 suppressions, MDD 77%
- Feedback loop: model queried every bar → suppress indefinitely
- 7-feature subset reproduces X14 (Sharpe 1.39, 133 trades)
- Adding ANY trade-context feature causes collapse

### Critical Insight from X15
The "feature mismatch bug" in X14 was **implicit regularisation**. Zeroing
trade-context features prevented over-suppression. The fix is not to restore
these features to a binary classifier, but to change the decision architecture
so trade-context information is used safely.

## Oracle Ceiling: Diagnostic Bound, Not Target

The oracle +0.845 Sharpe suppresses with PERFECT foreknowledge of which exits
are followed by recovery. Once exit policy changes, the path changes, re-entry
timing changes, and the definition of "churn" itself changes. The oracle
ceiling is a diagnostic upper bound indicating room for improvement, not a
target to approach asymptotically.

## Anti-Overfitting Protocol

### The Core Risk

X16 introduces a state machine with 2-3 new parameters (G, δ, possibly α).
With ~168 trail-stop episodes and ~106 churn events, overfitting risk is
moderate. Mitigations:

1. **Pre-registration**: This spec defines all designs, parameter grids,
   test order, and verdict gates BEFORE any X16 code runs.

2. **GO/NO-GO gate (T0)**: Empirical MFE/MAE analysis determines whether
   WATCH state has positive expected value BEFORE testing any design. If T0
   fails, no designs are tested.

3. **Economic motivation**: WATCH state is grounded in market structure —
   trail stops fire during pullbacks within trends; giving the trend time to
   resume (bounded) is a natural modification.

4. **Small parameter space**: Design E has 2 new params (G, δ), Design F
   has 1 new param (δ). Much smaller than X14's 10-feature logistic model.

5. **Fixed-sequence testing**: Designs tested simplest-first (F→E→G→H).
   First passing design accepted. FWER controlled.

6. **Same validation stack**: WFO 4-fold + bootstrap 500 VCBB + jackknife
   + PSR with DOF correction. All must pass.

### What Would Invalidate Results

If ANY of the following occur, the design is REJECTED:
- WFO win rate < 3/4 → doesn't generalise temporally
- Bootstrap P(improvement) < 60% → sample-specific
- MDD increase > 5 pp vs E0 → trades return for risk
- Jackknife drops Sharpe in > 2/6 years → unstable
- T0 GO/NO-GO fails → WATCH state has no empirical basis

## Test Suite

### T0: Post-Trigger MFE/MAE Analysis (GO/NO-GO)

**Purpose**: Before testing any design, measure what ACTUALLY happens to price
after trail stop fires. This is the empirical foundation for WATCH state.

**Method**: For each of the 168 trail-stop exits in E0:

```
For G in {2, 4, 6, 8, 12, 16, 20} bars after exit:
  MFE_G = max(close[exit_bar : exit_bar+G]) - close[exit_bar]
  MAE_G = close[exit_bar] - min(close[exit_bar : exit_bar+G])
  net_G = close[exit_bar+G] - close[exit_bar]
```

Split by churn (106) vs non-churn (62):
- Churn episodes: expected MFE, MAE, net move
- Non-churn episodes: expected MFE, MAE, net move
- Combined: E[MFE] - E[MAE] weighted by base rate (63% churn)

Also compute for each episode:
```
deeper_stop_hit(G, δ) = any(close[exit_bar : exit_bar+G] < peak - (3+δ)×ATR)
reclaim(G) = any(close[exit_bar : exit_bar+G] > trail_stop_level)
```

**Outputs**:
- MFE/MAE/net table by G and by churn/non-churn
- Fraction of churn episodes that reclaim within G bars
- Fraction of non-churn episodes that hit deeper stop within G bars
- Risk-reward ratio: E[gain|suppress correct] / E[loss|suppress wrong]

**Artefact**: `x16_mfe_mae.csv`

**GO/NO-GO Gate**:
- PASS if: for at least one G ∈ {2..20}, churn MFE > churn MAE AND
  non-churn deeper-stop hit rate > 60% (deeper stop catches real reversals)
- FAIL → ABORT entire X16. WATCH state has no empirical basis.

### T1: Risk-Coverage Curve (Exploratory)

**Purpose**: Understand the relationship between suppression aggressiveness
and risk/return before committing to any design.

**Method**: Using X14 Design D model as scorer (already trained, validated):

For each trail-stop first-breach episode, compute model score s_i.
Then sweep suppression configurations:

```
For threshold τ in {0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95}:
  For G in {2, 4, 6, 8} bars:
    For δ in {0.5, 1.0, 1.5, 2.0} ATR:
      Run WATCH-state sim:
        At first breach: if score > τ AND trend_up AND d1_regime → WATCH(G, δ)
        Otherwise → EXIT
      Record: Sharpe, MDD, trades, avg_hold, % stops_suppressed
```

10 × 4 × 4 = 160 configurations.

**Outputs**:
- Risk-coverage curve: x = % trail stops suppressed, y = Sharpe
- Risk-coverage curve: x = % trail stops suppressed, y = MDD
- Pareto front identification
- Sensitivity heatmaps (G × δ at best τ)

**Artefact**: `x16_risk_coverage.csv`, `x16_pareto.csv`

**No gate**: T1 is exploratory. Results inform Design E parameter grid.

## Designs (Fixed-Sequence, Simplest First)

Designs tested F→E→G→H. First design to pass ALL gates wins.

### Design F: Regime-Gated Adaptive Trail (0 model params, 1 new param)

**Logic**: Widen trail when market conditions are favourable, standard
trail otherwise. No model, no state machine, minimal complexity.

```python
if regime_ok and trend_up:
    effective_trail = trail_mult + delta    # wider leash
else:
    effective_trail = trail_mult            # standard 3×ATR

trail_stop = peak - effective_trail * rATR[i]
if close[i] < trail_stop:
    EXIT
```

**Parameter**: δ ∈ {0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0} (7 values)

**Rationale**: Simplest possible use of "context" — when D1 regime is healthy
and H4 trend is up, the pullback is more likely noise. Wider trail gives room.
When either condition fails, standard trail applies.

**1 new parameter** → minimal DOF penalty. No model dependency.

**Key property**: Trail width changes EVERY bar based on current conditions
(not just at breach). This naturally handles the case where regime deteriorates
DURING a pullback — trail automatically tightens.

### Design E: WATCH State Machine (model-assisted, 2 new params)

**Logic**: At first trail-stop breach, query X14 model ONCE to decide whether
to enter a bounded grace period.

**State machine**:

```
States: FLAT, LONG_NORMAL, LONG_WATCH

FLAT → LONG_NORMAL:
  entry signal (trend_up AND vdo>0 AND d1_regime)

LONG_NORMAL → FLAT:
  trail stop fires AND (model_score <= τ OR NOT trend_up OR NOT d1_regime)
  OR trend reversal (ema_fast < ema_slow)

LONG_NORMAL → LONG_WATCH:
  trail stop fires at bar b (FIRST BREACH ONLY)
  AND model_score > τ
  AND trend_up
  AND d1_regime
  Record: watch_start = b, original_trail = trail_level

LONG_WATCH → LONG_NORMAL:
  close[i] > original_trail (reclaim — price recovered past breach level)
  Reset: peak updates, new trail computed from new peak

LONG_WATCH → FLAT:
  close[i] < peak - (trail_mult + δ) × rATR[i]   (deeper stop hit)
  OR i - watch_start >= G                          (timeout)
  OR ema_fast[i] < ema_slow[i]                     (trend reversal)
```

**Parameters**:
- G ∈ {2, 4, 6, 8} bars (grace window, informed by T0/T1)
- δ ∈ {0.5, 1.0, 1.5, 2.0} ATR (deeper stop addon, informed by T0/T1)
- τ: fixed at best threshold from T1 risk-coverage curve (not a free param)

**Grid**: 4 × 4 = 16 combinations (much smaller than X14's 36).

**WFO**: In each fold, select (G*, δ*) on training data by Sharpe.
Use model weights from X14 WFO fold (already trained).

**Critical differences from X14/X15**:
1. Model queried ONCE at first breach, not every bar → no feedback loop
2. Suppress action is BOUNDED (max G bars) → no "hold forever"
3. Deeper fallback stop ensures tail risk is capped
4. Trade-context features used safely (single query, not repeated)

**2 new parameters** (G, δ) → DOF penalty. Model reuses X14 → no extra model DOF.

### Design G: Score-Ranked Suppression with Budget (if E shows lift)

**Only tested if Design E passes G0 (in-sample improvement).**

**Logic**: Same WATCH state machine as E, but instead of fixed threshold τ,
use suppression budget α%: only the top α% highest-scoring breach episodes
get WATCH treatment.

**Method**:
1. Run E0 sim → collect all first-breach episodes with model scores
2. Sort by score descending
3. Only suppress top α% episodes
4. Sweep α ∈ {5%, 10%, 15%, 20%, 30%, 40%, 50%}

**Rationale**: Budget constraint directly controls how aggressive the filter
is. Risk-coverage curve from T1 identifies the Pareto-optimal α.

**Parameters**: α (budget), G and δ from Design E best values.

### Design H: ΔU Training Target via Branch Replay (if E or G shows lift)

**Only tested if Design E or G passes G1 (WFO validation).**

**Central idea**: Replace binary churn label with utility differential —
the actual PnL difference between WATCH and EXIT NOW.

**Method**:
1. For each trail-stop exit episode in E0 (168 episodes):
   - Branch A: EXIT NOW → record subsequent path until re-entry, compute PnL_A
   - Branch B: WATCH(G*, δ*) → apply WATCH state, record outcome, compute PnL_B
   - ΔU_i = PnL_B - PnL_A (net cost including 50 bps RT friction)
2. Train regression model (L2-regularised linear) on ΔU_i using 10 features
3. Decision rule: suppress iff E[ΔU|x] > 0 AND Q_10(ΔU|x) > −L
   (mean positive AND 10th percentile above loss threshold)

**Why branch replay works here**: With WATCH(G*, δ*) as the alternative policy,
both branches re-synchronise within G bars (either WATCH exits or reclaims).
No path divergence beyond G bars.

**Risk**: n=168 for regression is small. Expected high variance in ΔU
estimates. Only worth attempting if simpler designs show directional lift.

**Proxy alternative** (if branch replay too noisy): Use post-trigger MFE/MAE
from T0 as pseudo-targets. Model predicts E[MFE − MAE | features] instead
of full ΔU. Cheaper, less accurate, but may suffice for ranking.

## Simulation Architecture

### State Machine Implementation

```python
# States
FLAT, LONG_NORMAL, LONG_WATCH = 0, 1, 2

state = FLAT
watch_start = 0
original_trail = 0.0

for i in range(n):
    p = cl[i]
    # ... entry/exit execution on previous bar's signals ...

    if state == FLAT:
        if entry_signal(i):
            pending_entry = True

    elif state == LONG_NORMAL:
        pk = max(pk, p)
        pk_bar = i if p >= pk else pk_bar
        ts = pk - trail_mult * atr[i]

        if p < ts:
            # FIRST BREACH: evaluate once
            if should_watch(i, entry_bar, pk, pk_bar):
                state = LONG_WATCH
                watch_start = i
                original_trail = ts
                deeper_stop = pk - (trail_mult + delta) * atr[i]
            else:
                pending_exit = True  # EXIT
                state = FLAT

        elif ema_f[i] < ema_s[i]:
            pending_exit = True  # trend reversal
            state = FLAT

    elif state == LONG_WATCH:
        pk = max(pk, p)
        pk_bar = i if p >= pk else pk_bar
        deeper_stop = pk - (trail_mult + delta) * atr[i]

        if p > original_trail:
            # RECLAIM: return to normal
            state = LONG_NORMAL

        elif p < deeper_stop:
            pending_exit = True  # deeper stop hit
            state = FLAT

        elif (i - watch_start) >= G:
            pending_exit = True  # timeout
            state = FLAT

        elif ema_f[i] < ema_s[i]:
            pending_exit = True  # trend reversal
            state = FLAT
```

### Design F Implementation (no state machine)

```python
for i in range(n):
    # ... entry logic unchanged ...
    if in_position:
        pk = max(pk, p)
        regime_ok = d1_regime[i]
        trend_ok = ema_f[i] > ema_s[i]

        if regime_ok and trend_ok:
            eff_trail = trail_mult + delta
        else:
            eff_trail = trail_mult

        ts = pk - eff_trail * atr[i]
        if p < ts:
            pending_exit = True
        elif ema_f[i] < ema_s[i]:
            pending_exit = True
```

### Key Difference: First-Breach vs Every-Bar

| Aspect | X14/X15 | X16 Design E |
|--------|---------|-------------|
| Query frequency | Every bar where close < trail | ONCE at first breach |
| Action duration | Single bar (re-evaluated next bar) | G bars (bounded) |
| Fallback | None (suppress or exit, binary) | Deeper stop at (3+δ)×ATR |
| Feedback loop | Yes (suppress → bars_held++ → suppress) | No (single query) |
| Trade-context features | X14: zeroed. X15: causes collapse | Safe (single query) |

## Walk-Forward Optimisation (WFO) Framework

Same expanding-window structure as X14:

| Fold | Train | Test |
|------|-------|------|
| 1 | 2020-01 → 2021-12 | 2022-01 → 2022-12 |
| 2 | 2020-01 → 2022-12 | 2023-01 → 2023-12 |
| 3 | 2020-01 → 2023-12 | 2024-01 → 2024-12 |
| 4 | 2020-01 → 2024-12 | 2025-01 → 2026-02 |

### WFO for Design F (1 param)

Per fold: sweep δ on training data, select δ* = argmax(Sharpe_train).
Run with δ* on test data.

### WFO for Design E (2 params)

Per fold: sweep (G, δ) grid on training data. Model weights reused from
X14 WFO (same fold boundaries). Select (G*, δ*) by Sharpe_train.
Run with (G*, δ*) on test data.

### WFO for Design G (budget)

Per fold: use E's best (G*, δ*). Sweep α on training data.
Select α* = argmax(Sharpe_train). Run with α* on test data.

### WFO for Design H (ΔU target)

Per fold: branch replay on training trail stops → compute ΔU → fit regression.
Run WATCH state on test data using regression predictions.

## Validation Tests (for winning design)

### T2: In-Sample Screening

Run winning design on full data. Compare to E0.

**Gate G0**: d_sharpe > 0

**Artefact**: `x16_screening.csv`

### T3: Walk-Forward Validation (4 folds)

**Gate G1**: win_rate >= 3/4 AND mean_d_sharpe > 0

**Artefact**: `x16_wfo_results.csv`

### T4: Bootstrap Validation (500 VCBB)

500 VCBB paths (block=60, seed=42). For each path: run E0 and filtered sim.

**Gate G2**: P(d_sharpe > 0) > 0.60
**Gate G3**: median d_mdd <= +5.0 pp

**Artefact**: `x16_bootstrap.csv`

### T5: Jackknife Leave-Year-Out (6 folds)

Drop each year (2020-2025), re-evaluate.

**Gate G4**: d_sharpe < 0 in <= 2/6 years

**Artefact**: `x16_jackknife.csv`

### T6: DOF Correction / PSR

DOF for each design:
- E0 baseline: 4.35 effective (Nyholt)
- Design F: +1 param (δ) → 5.35 effective
- Design E: +2 params (G, δ) → 6.35 effective
- Design G: +3 params (G, δ, α) → 7.35 effective
- Design H: +2 params + regression DOF → TBD

**Gate G5**: filtered_PSR > 0.95

**Artefact**: included in `x16_results.json`

### T7: Comprehensive Comparison

| Metric | E0 | E0+X14D | Design F | Design E | Oracle |
|--------|----|---------|---------:|----------|--------|
| Sharpe | | | | | |
| CAGR (%) | | | | | |
| MDD (%) | | | | | |
| Trades | | | | | |
| Avg hold (bars) | | | | | |
| % stops suppressed | | | | | |
| Oracle capture (%) | | | | | |
| WFO win rate | | | | | |
| Bootstrap P(Sh>0) | | | | | |
| PSR | | | | | |

**Artefact**: `x16_comparison.csv`

## Verdict Gates (for winning design)

| Gate | Condition | Meaning |
|------|-----------|---------|
| **G_pre** | T0 MFE/MAE GO | Empirical basis for WATCH exists |
| **G0** | T2 d_sharpe > 0 | In-sample improvement |
| **G1** | T3 win_rate >= 3/4 | Temporally robust (WFO) |
| **G2** | T4 P(d_sharpe > 0) > 0.60 | Bootstrap robust |
| **G3** | T4 median d_mdd <= +5.0 pp | MDD not materially worse |
| **G4** | T5 d_sharpe < 0 in <= 2/6 years | Jackknife stable |
| **G5** | T6 PSR > 0.95 | Survives DOF correction |

G_pre must pass BEFORE any design is tested.
G0-G5 must ALL pass for PROMOTE.

## Decision Matrix

| Outcome | Verdict |
|---------|---------|
| T0 fails (MFE <= MAE, deeper stop miss rate > 40%) | **ABORT** — no empirical basis |
| Design F passes G0-G5 | **PROMOTE_F** — simplest, no model dependency |
| F fails, E passes G0-G5 | **PROMOTE_E** — model-assisted, bounded state |
| F+E fail, G passes G0-G5 | **PROMOTE_G** — budget-constrained, most controlled |
| F+E+G fail, H passes G0-G5 | **PROMOTE_H** — utility-aligned, highest complexity |
| All fail G0 | **CEILING_UNREACHABLE** — WATCH architecture doesn't help |
| All pass G0, fail G1 | **NOT_TEMPORAL** — in-sample only |
| All pass G0+G1, fail G2-G3 | **NOT_ROBUST** or **MDD_TRADEOFF** |
| All pass G0-G4, fail G5 | **DOF_KILLED** — noise given parameter count |

### What Each Verdict Means

**PROMOTE_X**: The design strictly improves E0+EMA1D21 with proper OOS
validation. Runs PARALLEL to E5+EMA1D21 and X14 Design D. Future data
validates which modification adds most value.

**ABORT**: Post-trigger price dynamics don't support a grace period.
Trail stops should not be delayed. E0 exit architecture is correct as-is.

### What This Does NOT Do

- Does not integrate into production code
- Does not change E5+EMA1D21 or X14 Design D status
- Does not propose deployment
- Does not test interaction with regime monitor (separate study if PROMOTE)
- Does not test on other assets
- Only answers: does stateful exit capture more of the oracle ceiling?

## Relationship to Prior Work

| Study | What it proved | X16 builds on |
|-------|---------------|---------------|
| X12 | 63% churn, E5-E0 = noise | Churn rate, baseline metrics |
| X13 | AUC=0.805, oracle +0.845 | Feature importance, oracle ceiling |
| X14 | Static 7-feature model passes 6 gates | Model weights for Design E scorer |
| X15 | Dynamic 10-feature causes collapse | Feedback loop diagnosis, inference architecture |
| External | Episode-level + bounded suppress + ΔU target | WATCH state design, testing order |

## Known Risks & Limitations

1. **Small episode count**: 168 trail-stop episodes (~106 churn, 62 non-churn).
   Each WFO fold has ~30-50 trail stops. Parameter selection is noisy.

2. **WATCH state changes subsequent trades**: After a WATCH episode that
   reclaims, the trade continues → different exit timing → different re-entry
   → cascade effects. Metrics on full sim capture this; per-episode metrics don't.

3. **Deeper stop selection is itself a tradeoff**: δ too small → deeper stop
   fires immediately (WATCH is useless). δ too large → holding through real
   reversals (MDD increases). T0 MFE/MAE analysis sizes δ empirically.

4. **Model score dependency (Design E/G)**: Uses X14 logistic model as
   scorer. If the model is poorly calibrated, score ranking may be wrong.
   Design F avoids this entirely (no model).

5. **ΔU estimation noise (Design H)**: With 168 episodes, regression on
   continuous ΔU will have high variance. May need to bin into terciles
   (positive/neutral/negative) instead of continuous regression.

6. **Regime-gated adaptive trail (Design F) is always-on**: Unlike WATCH
   (triggered at breach), Design F widens trail every bar when conditions
   are good. This fundamentally changes the strategy's risk profile —
   wider trail means larger drawdowns during regime transitions.

## Output Files

```
x16/
  SPEC.md                    # this file
  benchmark.py               # single script, all tests T0-T7
  x16_results.json           # master results (nested dict)
  x16_mfe_mae.csv            # T0: post-trigger price dynamics
  x16_risk_coverage.csv      # T1: 160-point sweep results
  x16_pareto.csv             # T1: Pareto front points
  x16_screening.csv          # T2: in-sample results per design
  x16_wfo_results.csv        # T3: WFO fold results
  x16_bootstrap.csv          # T4: bootstrap distribution
  x16_jackknife.csv          # T5: leave-year-out results
  x16_comparison.csv         # T7: comprehensive comparison
```

## Dependencies

```python
import numpy as np
import math
from scipy.signal import lfilter
from scipy.optimize import minimize       # L2-logistic (reuse X14 model)
from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
```

## Estimated Runtime

- T0 (MFE/MAE): ~5s (post-processing on E0 trades)
- T1 (risk-coverage): ~60s (160 WATCH-state sims)
- T2 (screening): ~10s (4 designs × full-data sims)
- T3 (WFO): ~60s (4 folds × 16-grid per design)
- T4 (bootstrap): ~300s (500 paths × 2 sims)
- T5 (jackknife): ~10s (6 folds × 2 sims)
- T6 (DOF/PSR): ~1s
- T7 (comparison): ~2s
- Total: ~8 min
