# Report 21 — Final Inference-Stack Decision Memo

**Date**: 2026-03-03
**Status**: BINDING PROJECT DECISION
**Evidence base**: Reports 02, 03, 16, 17, 18, 19, 20
**Scope**: All statistical inference methods used for strategy promote/reject decisions

---

## 1. Executive Decision

### 1.1 Primary Paired Comparison Gate

**No tested statistical gate is suitable as the primary paired comparison
gate for strategy promote/reject decisions.**

Every available method was evaluated on a three-pair control testbed
(negative, mid-positive, strong-positive). No method achieved a perfect
3/3 scorecard:

| Method | Null (FAIL) | Mid+ (PASS) | Strong+ (PASS) | Score |
|--------|:-----------:|:-----------:|:---------------:|:-----:|
| Bootstrap CI (Sharpe) | OK | MISS | MISS | 1/3 |
| Subsampling CI (geo growth) | OK | MISS | MISS | 1/3 |
| Win-count V1 (real-data, Sharpe) | OK | MISS | OK | 2/3 |
| Win-count V1 (real-data, CAGR) | **MISS** | OK | OK | 2/3 |
| Win-count V2 (uncorrected) | **MISS** | MISS | MISS | **0/3** |
| Win-count V3 (DOF-corrected) | OK | MISS | MISS | 1/3 |
| DSR | N/A (not paired) | — | — | — |
| Permutation | N/A (component-level) | — | — | — |

**Root cause**: ~7 years of H4 BTC data yields ~15 effective independent
observations at single-timescale, or ~2.5–4.0 effective independent
observations at multi-timescale cross-strategy. No statistical method
can distinguish effects below ~0.75 Sharpe units at 95% confidence with
this data.

### 1.2 Least-Bad Operational Replacement

Since no automated gate is reliable, the project adopts a **human-in-the-
loop multi-evidence protocol**:

1. **Directional evidence** (not a gate): bootstrap p_a_better on
   geometric growth + CI width as a calibration diagnostic
2. **Cross-timescale pattern**: real-data win counts (V1) across 16
   timescales as directional signal, with explicit acknowledgment of
   false-positive risk on CAGR
3. **Component existence**: permutation tests confirm that individual
   components (EMA, VDO, ATR) contribute genuine alpha
4. **Selection-bias check**: DSR at the per-strategy level as advisory
5. **Human judgment**: final promote/reject decision by researcher,
   informed by all diagnostics above, with no single automated gate
   having veto power

**No strategy may be promoted or rejected based on a single statistical
gate.** All gates become diagnostics that inform the researcher's
judgment.

### 1.3 What Is Retired

- **Win-count V2** (uncorrected bootstrap-then-binomial): **BANNED** from
  cross-strategy comparison. Produces PROVEN*** false positives on null
  pairs (0/3 scorecard). Existing V2 results in the codebase that compare
  two different strategies are unreliable.
- **Bootstrap `p_a_better` as a p-value**: the name and threshold (0.80)
  must not be interpreted as controlling any Type I error rate.
- **Subsampling `p_a_better` on near-degenerate data**: produces p=0.97
  on null pairs with >80% exact zeros. Not calibrated for this data type.
- **E5 MDD 16/16 claim**: RETIRED (Report 16 — scale-mismatch artifact).

---

## 2. Evidence Summary

### 2.1 Report 02 — Inference Stack Audit

Audited all four inference methods. Key findings:

- **Bootstrap** `p_a_better = fraction(deltas > 0)` is NOT a p-value.
  It does not test H0: Sharpe(A) ≤ Sharpe(B). The distribution is
  centered at the observed delta, not zero. The gate threshold (p ≥ 0.80)
  has no connection to any significance level α.
- **Bootstrap alignment**: silent truncation to `min(len_a, len_b)`
  without timestamp validation. Subsampling raises `AlignmentError` on
  mismatch — bootstrap does not.
- **Bootstrap CI** `ci_lower > -0.01` allows CIs spanning zero to pass.
  Arbitrary tolerance with no statistical basis.
- **Subsampling** has a proper null hypothesis (H0: excess geometric
  growth ≤ 0) and a proper one-sided p-value via Politis-Romano-Wolf.
  Multi-block-size gate with stability check (support ≥ 0.60). However,
  the subsampling gate is NOT wired into `evaluate_decision()`.
- **DSR** answers "is this Sharpe genuine after multiple testing?" — a
  single-strategy test, not paired. Two different calling conventions in
  the codebase produce different results.
- **Permutation tests** are component-level (EMA, VDO, ATR), not
  pair-level. They test component existence, not candidate superiority.

### 2.2 Report 03 — Real Data vs Generator

The Monte Carlo generator used in Prompt 01's power simulation has 2
critical mismatches with real BTC data:

- **No volatility clustering**: ACF(|r|, lag=50) = 0.09 in real data
  vs ≈0 in generator. Real vol persistence is absent from the generator.
- **Insufficient vol-of-vol**: rolling 168-bar vol CV is 0.74 in real
  data vs 0.34 in generator.

**Implication**: coverage and power estimates from Monte Carlo simulations
are optimistic. The T_eff ≈ 15 finding in Report 18 (from bootstrap CI
width on real data) is more trustworthy than simulation-based power
curves.

### 2.3 Report 16 — E-Series Close-Out

- E5 MDD 16/16 was a scale-mismatch artifact. Robust ATR produces a
  tighter stop (0.955 scale factor), not a better stop. At scale-matched
  trail, MDD wins drop to 6/16 (chance).
- A0 = ATR(14) remains the canonical VTREND configuration.
- A1 = ATR(20) retained as near-null control (ΔSharpe = -0.006).

### 2.4 Report 17 — Testbed Selection

Six strategies profiled, 15 pairs diagnosed. Three control pairs selected
for Reports 18–20:

| Pair | Type | ΔSharpe | Zero-rate | Return corr |
|------|------|---------|-----------|-------------|
| A0 vs A1 | Negative control | -0.006 | 98.8% | 0.987 |
| A0 vs VBREAK | Mid positive | +0.098 | 73.2% | 0.735 |
| A0 vs VCUSUM | Strong positive | +0.343 | 62.7% | 0.525 |

### 2.5 Report 18 — Current Stack on Control Pairs

All methods fail on all pairs:

- **Bootstrap**: correct directional signal (p=0.82 on strong positive)
  but CI width ~1.5 Sharpe units. The `ci_lower > -0.01` condition
  requires ΔSharpe >> 0.75 — no pair in the repo achieves this.
- **Subsampling**: p_a_better = 0.97 on the NULL pair (suspicious).
  All CI gates fail. Support ratio = 0.00 on both positive controls.
- **DSR**: fails all strategies at all trial levels (high kurtosis of
  BTC H4 returns inflates the SR variance correction).
- **Root cause**: T_eff ≈ 15 independent macro cycles in 7 years.
  Bootstrap CI width implies SE(ΔSharpe) ≈ 0.38, not the naive 0.067.

### 2.6 Report 19 — Same-Statistic Audit

The apparent method disagreement from Report 18 was a **statistic-choice
artifact**, not a method-family difference:

- On **same statistic** (mean log-return diff), bootstrap and subsampling
  agree within 2pp on non-degenerate pairs (boot p=0.924 vs sub p=0.930
  on strong positive).
- **Statistic choice** drives 10–25pp difference: Sharpe reduces
  p_a_better by 10–25pp vs geometric growth on the same data. Sharpe
  CIs are 2.5× wider than geometric growth CIs.
- **Block-10 anomaly**: subsampling CI collapses on the A0-vs-A1
  differential (82.6% exact zeros → 300 unique block means out of
  15,638 blocks). This is a data-degeneracy artifact, not a software bug.
  Bootstrap is immune because resampling creates genuine variability.
- **Subsampling p is NOT calibrated on degenerate data** (>80% zeros).
  Bootstrap p IS correctly calibrated (p=0.52 on null pair).

### 2.7 Report 20 — Win-Count / Multi-Timescale Audit

Three win-count variants tested on the same control pairs:

- **V1 (real-data)**: best at 2/3, but false-positives on CAGR (14/16,
  p=0.002 on the null pair). Small, noise-level CAGR differences
  accumulate consistently across correlated timescales.
- **V2 (uncorrected bootstrap-then-binomial)**: catastrophic 0/3. Declares
  PROVEN*** on the null pair (16/16 Sharpe, p=1.5e-5). The mechanism:
  P(win) ≈ 53–57% per timescale × maximal cross-timescale correlation
  → 16/16 wins. Binomial test treats correlated outcomes as independent.
- **V3 (DOF-corrected)**: fixes the false positive (p=0.25) but kills all
  power. M_eff = 2.5–4.0 for cross-strategy comparison leaves only
  2.5–4 effective trials — insufficient for significance on any available
  positive control.
- **M_eff estimates**: 16 timescales provide only 2.5–4.0 effective
  independent observations for cross-strategy comparison. This is far
  lower than the 10–11 M_eff found for VDO on/off (within-strategy
  filter toggling), because VDO toggling creates genuinely independent
  variation.

---

## 3. Role Matrix

| Role | Method | Status | Justification |
|------|--------|--------|---------------|
| **Primary paired gate** | NONE | **VACANT** | No method achieves 3/3 on control scorecard. Fundamental power limitation. |
| **Paired directional diagnostic** | Bootstrap p_a_better (geo growth) | ACTIVE — advisory only | Correctly calibrated p (0.52 on null, 0.93 on strong+). NOT a p-value. Report the value, do not gate on it. |
| **Paired CI diagnostic** | Bootstrap CI (geo growth) | ACTIVE — advisory only | Provides magnitude and uncertainty estimate. CI width calibrates the power limit. Do not gate on `ci_lower`. |
| **Paired directional diagnostic** | Subsampling p_a_better | ACTIVE — advisory, non-degenerate data only | Agrees with bootstrap within 2pp on non-degenerate pairs. NOT calibrated when >80% of differential returns are exact zeros. |
| **Multi-timescale directional signal** | Win-count V1 (real-data) | ACTIVE — advisory, Sharpe only | Best scorecard (2/3) on Sharpe wins. CAGR version has demonstrated false-positive risk (14/16 on null). |
| **Multi-timescale directional signal** | Win-count V3 (DOF-corrected) | ACTIVE — advisory only | Eliminates false positives. Low power (1/3), but safe. Report M_eff alongside count. |
| **Within-strategy filter test** | Win-count V2/V3 (VDO on/off) | ACTIVE — proven valid | M_eff ≈ 10–11 for VDO toggle. Sufficient power. DOF-corrected p-values survive. Existing VDO claims SAFE. |
| **Component existence** | Permutation (EMA, VDO, ATR) | ACTIVE — proven valid | p < 0.001, survives Bonferroni at K=16. Tests component alpha, not strategy superiority. |
| **Selection-bias advisory** | DSR | ACTIVE — advisory only | Per-strategy, not paired. Warns if observed Sharpe could arise from data mining. Two calling conventions must be documented. |
| **BANNED** | Win-count V2 (uncorrected) for cross-strategy | **RETIRED** | 0/3 scorecard. PROVEN*** false positive on null pair. Must not be used without DOF correction for cross-strategy comparison. |

---

## 4. What Is Retired

### 4.1 Unsafe Claims — Must Be Retired

| # | Claim | Source | Why unsafe | Replacement |
|---|-------|--------|-----------|-------------|
| U1 | "Bootstrap `p_a_better` is a p-value" | Implicit in gate threshold = 0.80 | `fraction(deltas > 0)` is not centered at null. Not comparable to α-levels. (Report 02 §2.1.1) | Call it "directional probability under resampling." Do not compare to α. |
| U2 | "The 0.80 threshold controls false positives at some known rate" | `decision.py` gate logic | No calibration connecting 0.80 to any Type I error rate. (Report 02 §3.2) | Treat as heuristic signal, not a calibrated test. |
| U3 | "Bootstrap CI `ci_lower > -0.01` ensures candidate superiority" | `decision.py` gate logic | Allows CIs spanning zero. -0.01 tolerance is arbitrary. (Report 02 §3.3) | Report CI bounds without gating. |
| U4 | "Bootstrap alignment is safe" | `bootstrap.py:182` | Silent truncation to `min(len)` without timestamp check. (Report 02 §3.4) | Fix: add alignment validation matching subsampling. |
| U5 | "Subsampling p=0.97 means 97% probability A is better" | Report 18 subsampling output | p=0.97 on a null pair (ΔSharpe = -0.006) proves this is miscalibrated on degenerate data. (Reports 18 §6.2, 19 §4) | Subsampling p is NOT a posterior probability. Not reliable when >80% of differential returns are exact zeros. |
| U6 | "16/16 wins across timescales proves superiority (uncorrected)" | V2 win-count (e.g., `e5_validation.py`) | M_eff = 2.5–4.0 for cross-strategy. 16/16 with uncorrected binomial gives p=1.5e-5; DOF-corrected p=0.25. Catastrophic false positive PROVEN on null pair. (Report 20 §5.3, §9) | For cross-strategy comparison: always apply DOF correction. Uncorrected binomial is valid ONLY for VDO on/off (M_eff ≈ 10–11). |
| U7 | "E5 MDD 16/16 PROVEN (p=1.5e-5)" | `e5_validation.json` | Scale-mismatch artifact. At matched trail: MDD 6/16 (chance). (Report 16 §2.1) | RETIRED. E5 branch closed. |
| U8 | "Monte Carlo power estimates apply to real BTC data" | Prompt 01 simulation | Generator lacks volatility clustering and has 2× lower vol-of-vol. Power estimates are optimistic. (Report 03 §§3–4) | T_eff ≈ 15 from bootstrap CI width on real data is the binding constraint. |

### 4.2 Claims That Survive

| # | Claim | Source | Why safe |
|---|-------|--------|---------|
| S1 | "EMA crossover entry adds alpha (p=0.0003)" | `multiple_comparison.py` | Circular-shift permutation test. Survives Bonferroni at K=16. Component-level, genuinely distribution-free for this null. (Report 02 §4.5) |
| S2 | "VDO filter adds alpha (DOF-corrected p=0.031 Sharpe, p=0.004 MDD)" | `binomial_correction.py` | M_eff ≈ 10–11 for VDO toggle. Within-strategy test with sufficient effective DOF. (Report 20 §7.3) |
| S3 | "ATR trailing stop adds alpha (p=0.0003)" | `multiple_comparison.py` | Block-shuffle permutation. Survives Bonferroni at K=16. (Report 02 §4.5) |
| S4 | "Bootstrap and subsampling CIs have correct coverage (~95%)" | Prompt 01 simulation | Confirmed at 94–96.5% coverage under Student-t(3). Both methods are valid CI constructors. (Report 02 §4.1) |
| S5 | "Both methods control Type I error below 5%" | Prompt 01 simulation | Reproduced at 1.5–2.5% across block sizes. (Report 02 §4.2) |
| S6 | "On the same statistic, bootstrap and subsampling agree within 2pp" | Report 19 | Verified on two non-degenerate control pairs. Method choice barely matters; statistic choice drives divergence. (Report 19 §5.2) |
| S7 | "A0 is the canonical VTREND configuration" | Report 16 | A0 = ATR(14) optimal after E-series close-out. E5 branch retired. |

---

## 5. Minimal Process-Change Decision

### 5.1 What Changes

| # | Change | Scope | Rationale |
|---|--------|-------|-----------|
| P1 | **Reclassify bootstrap gate from SOFT GATE to DIAGNOSTIC** | `decision.py` | Gate cannot pass on any achievable pair. Retaining it as a gate is misleading — it implies a useful decision boundary exists. |
| P2 | **Reclassify subsampling gate from SOFT GATE to DIAGNOSTIC** | `decision.py` (currently not wired; formalize this) | Same power limitation. Gate structure is sound but cannot pass. |
| P3 | **Add WARNING comments to V2 win-count scripts** | `e5_validation.py`, `trail_sweep.py` | Mark uncorrected cross-strategy binomial results as unreliable. No code deletion — scripts are frozen research artifacts. |
| P4 | **Document DSR calling conventions** | `selection_bias.py`, `research/lib/dsr.py` | Two entry points produce different results. Document which is canonical and why. |
| P5 | **Add bootstrap alignment validation** | `v10/research/bootstrap.py` | Silent truncation is a correctness hazard. Match subsampling's `AlignmentError`. |

### 5.2 What Does NOT Change

| # | No-change | Why |
|---|-----------|-----|
| N1 | Gate thresholds (0.80, -0.01, etc.) | The thresholds are not the problem. The data resolution is. Changing thresholds would either (a) relax the gate and introduce false positives, or (b) keep it strict and change nothing. |
| N2 | Block bootstrap implementation | The bootstrap is honest and correctly reports uncertainty. Report 19 confirmed it agrees with subsampling on the same statistic. |
| N3 | Subsampling implementation | Produces correct inference on non-degenerate data. The block-10 anomaly is a data property, not a code bug. |
| N4 | Permutation test results | All component-level claims (EMA, VDO, ATR) are proven and survive multiple-testing correction. |
| N5 | V3 DOF-corrected win-count | Implementation is correct. M_eff estimates are validated against known properties. Low power is a data limitation, not a bug. |
| N6 | VDO on/off win-count claims | M_eff ≈ 10–11 provides sufficient effective DOF. Existing DOF-corrected VDO claims are safe. |
| N7 | Research scripts | All 53 scripts are frozen artifacts. No logic changes. Warning comments only (P3). |

### 5.3 Decision Authority

The following decisions may NOT be made by any single statistical gate:

- **Promote** a strategy variant over the A0 baseline
- **Reject** a strategy variant as inferior to A0
- **Retire** a previously accepted component

These decisions require the researcher to evaluate the full diagnostic
suite (§3 Role Matrix) and make an explicit, documented judgment call
that accounts for the known power limitations.

---

## 6. Recommended Patch Scope

### 6.1 Immediate (before next research study)

| Patch | File(s) | LOC estimate | Risk |
|-------|---------|-------------|------|
| Add alignment check to `paired_block_bootstrap` | `v10/research/bootstrap.py` | ~10 | Low — adds a safety check, no behavior change for aligned data |
| Add docstring to bootstrap `p_a_better` clarifying it is NOT a p-value | `v10/research/bootstrap.py` | ~5 | None |
| Add warning header to `e5_validation.py` and `trail_sweep.py` noting V2 cross-strategy results are unreliable without DOF correction | 2 files | ~6 each | None — comment only |

### 6.2 Short-term (next session)

| Patch | File(s) | LOC estimate | Risk |
|-------|---------|-------------|------|
| Reclassify bootstrap and subsampling from gate to diagnostic in decision engine | `validation/decision.py` | ~30 | Medium — changes gate semantics. Requires test updates. |
| Document DSR calling conventions (inline vs `lib/dsr.py`) | `validation/suites/selection_bias.py`, `research/lib/dsr.py` | ~20 | Low |
| Add `statistic='geo_growth'` option to bootstrap for consistent paired comparison with subsampling | `v10/research/bootstrap.py`, `validation/suites/bootstrap.py` | ~25 | Medium — new code path, needs tests |

### 6.3 Deferred (not urgent)

| Patch | File(s) | LOC estimate | Risk |
|-------|---------|-------------|------|
| Implement proper centered bootstrap p-value (`deltas - observed_delta`) | `v10/research/bootstrap.py` | ~15 | Medium — changes test semantics |
| Consolidate DSR to single entry point | `validation/suites/selection_bias.py` | ~40 | Medium — removes inline implementation |
| Add bootstrap geo-growth statistic to production validation pipeline | Multiple | ~50 | Higher — new diagnostic column |

---

## Appendix A: Evidence Chain Traceability

| Conclusion | Primary evidence | Cross-check |
|------------|-----------------|-------------|
| No gate achieves 3/3 | Report 20 §8.1 scorecard | Report 18 §5 decision matrix |
| T_eff ≈ 15 | Report 18 §9 (bootstrap CI width → SE ≈ 0.38) | Report 03 (generator mismatch confirms simulation power is optimistic) |
| Method ≈ method on same statistic | Report 19 §3.2–3.3 (boot p vs sub p differ by <2pp) | — |
| Statistic > method | Report 19 §5.3 (Sharpe CIs 2.5× wider than geo growth) | — |
| V2 false-positive mechanism | Report 20 §9 (correlated 53–57% bias → 16/16) | M_eff = 2.5 confirms (Report 20 §6.1) |
| VDO claims survive | Report 20 §7.3 (M_eff ≈ 10–11 for VDO toggle) | Different scenario from cross-strategy (M_eff 2.5–4.0) |
| E5 retired | Report 16 §2.1 (scale-mismatch: MDD 16/16 → 6/16 at matched scale) | — |
| Bootstrap alignment hazard | Report 02 §2.1.6 (silent truncation vs subsampling's AlignmentError) | — |

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **M_eff** | Effective number of independent tests, estimated from eigenvalues of the correlation matrix (Nyholt/Li-Ji/Galwey methods) |
| **V1** | Win-count variant 1: real-data wins, strict comparison, binomial test |
| **V2** | Win-count variant 2: bootstrap-then-binomial, P(win) > 0.50 threshold, UNCORRECTED for timescale correlation |
| **V3** | Win-count variant 3: same as V2 but with M_eff DOF correction on the binomial test |
| **T_eff** | Effective number of independent observations in the time series (≈15 macro cycles in 7 years of H4 BTC) |
| **DOF** | Degrees of freedom |
| **Scorecard** | 3-pair evaluation: null should FAIL, mid+ should PASS, strong+ should PASS |
| **Gate** | Automated pass/fail decision boundary in the validation pipeline |
| **Diagnostic** | Statistical output reported to the researcher without automated pass/fail |

---

*Inference-stack decision finalized. No statistical gate is suitable as a
primary paired comparison gate. All gates reclassified as diagnostics.
Win-count V2 (uncorrected) is BANNED for cross-strategy comparison.
Human-in-the-loop multi-evidence protocol adopted.*
