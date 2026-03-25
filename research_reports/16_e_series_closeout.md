# Report 16 — E-Series Branch Close-Out Memo

**Date**: 2026-03-03
**Purpose**: Retire outdated E5 claims and close the E0/E5 family branch.
**Evidence base**: Reports 11, 11b, `e5_validation.json`, `exit_family_report.md`,
`COMPLETE_RESEARCH_REGISTRY.md`

---

## 1. Canonical A0 / A1 / A2 / A3 Definitions

2x2 factorial on the ATR feeding the trailing stop:

|  | period = 14 | period = 20 |
|---|---|---|
| **no cap** | **A0** = Wilder EMA(TR, 14) | **A1** = Wilder EMA(TR, 20) |
| **Q90 cap** | **A2** = Wilder EMA(min(TR, Q90(100)), 14) | **A3** = Wilder EMA(min(TR, Q90(100)), 20) |

- A0 is the production E0 baseline (= VTREND default, `_atr(14)`).
- A3 is the full E5 as implemented in `e5_validation.py` and `exit_family_study.py`.
- All variants share identical entry logic (EMA cross + VDO gate).
  Only the ATR series feeding `trail_stop = peak - trail_mult * ATR` differs.
- All prior E5 studies used trail_mult = 3.0 for both E0 and E5.

---

## 2. Claims to Retire

### 2.1 "E5 MDD 16/16 PROVEN (p = 1.5e-5)"

**Source**: `research/results/e5_validation/e5_validation.json`, line 259;
`COMPLETE_RESEARCH_REGISTRY.md`, entry 15.

**Status**: RETIRED — scale-mismatch artifact.

**Evidence chain**:

1. Robust ATR (A3) has median scale 0.955 relative to standard ATR (A0).
   At trail = 3.0, E5's stop is 4.5% tighter (Report 11, section 3).
2. The Q90 cap alone (A2) produces ATR that is below A0 at 100% of bars.
   This is definitional: `min(TR, Q90) <= TR` always (Report 11b, section 2.1).
3. Scale-matched (trail = 3.14 for A3): MDD wins drop from 15-16/16 to
   **6/16** — indistinguishable from chance (Report 11, section 5.1).
4. Factorial attribution (Report 11b, section 5.3):
   - Period effect on MDD: 6/16 (chance)
   - Cap effect on MDD: 8/16 (chance)
   - Cap + period interaction on MDD: **2/16** (actively harmful)
5. The 16/16 MDD result was produced entirely by the tighter stop, not
   by any quality property of the robust ATR mechanism.

### 2.2 "Real ΔNAV > 0: 16/16 PROVEN (p = 1.5e-5)"

**Source**: `e5_validation.json`, line 270.

**Status**: RETIRED — same confound.

At scale-matched, NAV wins drop to 14/16. Still directionally positive
on real data, but the original p-value is invalid because it was
computed under a scale-confounded comparison. The surviving 14/16 has
not been bootstrap-tested under fair conditions.

### 2.3 "E5 SUPPORTED" (exit family study)

**Source**: `exit_family_report.md`, line 593.

**Status**: RETIRED — the "SUPPORTED" verdict rested on NAV improvement
of +31.5% / +37.9% at sp = 120/144 with bootstrap P(CAGR+) of
84.6% / 89.3%. These numbers were computed at trail = 3.0 for both
variants, making the comparison scale-unfair. The exit family study
did not perform scale matching.

### 2.4 "Robust ATR mechanism is beneficial"

**Source**: implicit in multiple registry entries and MEMORY.md.

**Status**: RETIRED — not demonstrated. At scale-matched comparison, A3
is not better than A1 (period-only, no cap). The cap's specific
contribution beyond a period change is zero for Sharpe/CAGR, and
negative for MDD.

### 2.5 MEMORY.md Line

**Current**: "E5: MDD 16/16 PROVEN but Sharpe/CAGR 0/16 — MDD-only insufficient"

**Replace with**: "E5: RETIRED — scale-mismatch artifact (Report 16).
MDD 6/16 at scale-matched. No provable advantage over E0."

---

## 3. Claims That Survive

### 3.1 Scale-matched Sharpe: 12-13/16

All three non-baseline variants (A1, A2, A3) show Sharpe wins of
12-13/16 vs A0 under median-matched trail. Binomial p for 12/16
is 0.038; for 13/16 is 0.011.

**However**, this does not survive as evidence for robust ATR because:

- A1 (period-only, no cap, no scale correction needed) achieves the
  same 12/16. The cap contributes nothing beyond what a period change
  provides.
- Under family retuning, A0 at its own best trail beats all variants
  (median Sharpe: A0 = 1.217 > A1 = 1.211 > A2 = 1.197 > A3 = 1.188).
- The effect size is small (median ΔSharpe = +0.026 for A1) and has
  not been bootstrap-tested under scale-fair conditions.

**Verdict**: Weak directional signal for ATR period = 20 over 14 at
fixed trail = 3.0. Not evidence for the E5/robust-ATR mechanism.
Insufficient to warrant further investment.

### 3.2 E0 remains uncontested on all metrics simultaneously

No variant improved ALL of {Sharpe, CAGR, MDD} at any level of
analysis. This is consistent with the broader research finding that
VTREND E0 is on the Pareto frontier and added complexity degrades it.

### 3.3 Bootstrap Sharpe/CAGR: 0/16 for E5 (correctly directional)

The original e5_validation.json bootstrap result — E5 loses Sharpe and
CAGR on all 16 timescales — is directionally correct. On synthetic
paths, the tighter stop's extra churn degrades returns. That the
real-data result was opposite (16/16 wins) is consistent with sample-
specific overfitting to BTC's 2019-2026 trend structure. This
divergence (bootstrap negative, real positive) is itself a warning sign.

---

## 4. Final Branch Decision

### 4.1 Canonical Baseline

**A0 = ATR(14), no cap, trail = 3.0** remains the canonical baseline.

No variant produced a durable improvement under fair comparison. Under
family-level retuning across 16 timescales, A0 achieves the best
median Sharpe (1.217). The production VTREND spec is unchanged.

### 4.2 Near-Null Control

**A1 = ATR(20), no cap** is retained as a near-null control for
future audit if needed.

Rationale:
- A1 has negligible scale mismatch (median ratio 1.009), so
  trail = 3.0 is fair for both A0 and A1 without adjustment.
- A1 shows the only residual signal (Sharpe 12/16) that might be real
  rather than a scale artifact.
- It isolates a single variable change (period 14 vs 20).
- It is the closest competitor to A0 under family retuning.

**However**: this is a contingency designation, not a recommendation to
pursue. The effect is small, A0 wins under retuning, and bootstrap
testing would almost certainly fail to reach p < 0.025.

### 4.3 Retired Variants

| Variant | Status | Reason |
|---|---|---|
| **A2** (cap-only) | RETIRED | 100% of bars have lower scale; MDD 8/16 at matched; family retuning: worst-2 |
| **A3** (= E5) | RETIRED | Scale-confounded; cap adds nothing beyond period change; family retuning: worst |
| **E5R** (E5 + ratchet) | RETIRED | Built on top of A3; inherits all scale confounds |
| **COND-E5** | RETIRED | Conditional variant of A3; same confound |
| **E5 VCBB** | RETIRED | Same comparison, different bootstrap method; same confound |

All scripts in `research/e5_validation.py`, `research/e5r_test.py`,
`research/e5_vcbb_test.py` are frozen research artifacts. They remain
in the repo for provenance but their results carry no standing.

---

## 5. What This Branch Does NOT Settle About Bootstrap vs Subsampling

Reports 11 and 11b used real-data win counts across 16 timescales
with binomial testing. They did not re-run the paired block bootstrap
or subsampling under scale-matched conditions. Therefore:

1. **Bootstrap calibration under scale-matching is untested.** The
   original bootstrap found E5 loses Sharpe/CAGR 0/16 — but this was
   under the scale-confounded E5(3.0) vs E0(3.0). We do not know what
   the bootstrap would show for A3(3.14) vs A0(3.0). Given that
   real-data scale-matched shows 13/16 Sharpe, the bootstrap might
   flip. This is moot because the branch is being retired, but it
   means the bootstrap-vs-real divergence is not fully explained.

2. **Subsampling validity is untested for scale-matched.** The
   subsampling test (Report 07b) operates on differential log-returns.
   Under scale-matching, the trade entry/exit timing changes, altering
   the differential series. We do not know if the subsampling
   distribution properties (87.5% zeros, etc.) change materially.

3. **The general question of bootstrap vs subsampling power remains
   open.** Report 07b found p_a_better = 0.649, which the gate
   heuristic correctly rejected (threshold 0.80). But this was
   for the v12-vs-v10 pair, not for any E-series variant. Whether
   the bootstrap/subsampling framework has adequate power to detect
   small true effects (ΔSharpe ~0.03) in the presence of 87.5%
   identical returns remains an open methodological question.

4. **E-series scale-matching does not invalidate the bootstrap/
   subsampling methodology itself.** The issue was the comparison
   setup (same trail for unequal ATR scales), not the statistical
   method. The bootstrap and subsampling would produce valid inference
   if given a scale-fair input pair.

---

## 6. Recommended Next Experiment

**None for the E-series.** The branch is closed.

If the project were to revisit ATR variants in the future, the correct
protocol would be:

1. Choose a single-variable change (e.g., period 14 vs 20, no cap).
2. Verify scale parity (ratio should be within 1.0 +/- 0.01).
3. Run paired block bootstrap at 16 timescales under the existing
   `e5_validation.py` framework, substituting A1 for A3.
4. Require p < 0.025 on the binomial count of timescales where
   P(metric+) > 50%.

Estimated yield: negligible. A1's effect (median ΔSharpe = +0.026)
is small enough that bootstrap would likely produce ~50% probability
at each timescale, failing the binomial gate.

The project's effort is better directed at auditing the 4 PROVEN
components (EMA crossover, ATR trail + EMA exit, VDO filter, EMA(21d)
regime filter) or at the trail_mult retuning question exposed by the
family sweep (all families peak near trail = 4.5-5.0 vs current
default 3.0).

---

## Summary

The E-series branch began with a plausible hypothesis (robust ATR
improves exit quality by being less distorted by extreme bars) and
produced an impressive-looking result (MDD 16/16, p = 1.5e-5).

Reports 11 and 11b demonstrated that this result was entirely a
scale-mismatch artifact. The Q90 cap creates an ATR that is
definitionally smaller, producing a tighter stop at the same trail
multiplier. When corrected for scale, no metric improvement survives.
Under family-level retuning, A0 (baseline) is the best family.

**E5 is retired. A0 = ATR(14), no cap, trail = 3.0 remains the
canonical VTREND exit.**

---

*E-series branch closed. All E5-derived claims retired.*
