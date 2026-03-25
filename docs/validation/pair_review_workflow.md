# Pair Review Workflow — Operator Guide

**Effective**: 2026-03-04 (updated 2026-03-17: 3-tier authority model)
**Authority**: Report 21 (binding decision), Report 22B (patch plan), Reports 23–25 (implementation)
**Role in 3-tier model**: This is the **Tier 3 (Deployment Decision)** process.

---

## 1. Purpose

This workflow is the **final decision authority** (Tier 3) in the 3-tier model:

| Tier | Question | Authority | Output |
|------|----------|-----------|--------|
| 1. Research Screening | Worth productionizing? | `benchmark.py` | SCREEN_PASS / SCREEN_FAIL |
| 2. Machine Validation | OOS evidence sufficient? | `decision.json` | AUTO_PROMOTE / AUTO_HOLD / AUTO_REJECT |
| **3. Deployment Decision** | **Deploy live now?** | **Human researcher (this workflow)** | **DEPLOY / SHADOW / DEFER / REJECT** |

No single statistical test can reliably distinguish VTREND variants with ~7 years
of H4 BTC data (T_eff ≈ 15 independent macro cycles). The machine pipeline
(Tier 2) provides automated evidence; this workflow requires a **human researcher**
to make the final deployment decision using all available evidence.

**Key principle**: Tier 2 AUTO_HOLD means "automated evidence insufficient to
confirm", NOT "do not deploy". A strategy can be the best available option
despite AUTO_HOLD (e.g., E5_ema21D1 with WFO underresolved but bootstrap
P(>E0)=97.2%). Only hard gate failures (lookahead, data integrity) are
absolute blockers that Tier 3 cannot override.

The deployment decision artifact is `reports/deployment_decision.md`.

---

## 2. What Changed from the Old System

| Before | After |
|--------|-------|
| Bootstrap `p_a_better >= 0.80` was a soft gate that could HOLD a candidate | Bootstrap is a diagnostic. Status is always `"info"`. No veto power. |
| Subsampling suite computed pass/fail status | Subsampling is a diagnostic. Status is always `"info"`. Never wired to decision engine. |
| A single gate could block a candidate | No single diagnostic can block. Only hard gates (data integrity, regression guard) have veto power. |
| Researcher could defer to automated verdict | Researcher **must** fill in the Human Review Note with explicit reasoning. |

**What did NOT change**: bootstrap and subsampling code still runs, still produces the same numbers. The numbers are now labeled correctly and presented as diagnostics.

---

## 3. What Bootstrap Now Means

Bootstrap `p_a_better` is a **directional resampling score** — the fraction of bootstrap resamples where candidate's metric exceeds baseline's. It is centered at the observed delta, not at zero.

**It is NOT**:
- A p-value (does not test H0: metric(A) <= metric(B))
- Comparable to significance levels (alpha = 0.05, 0.10, etc.)
- A basis for automated promote/reject

**How to use it**: A value near 0.50 means no directional signal. Higher means the candidate tends to outperform in resampled paths. The CI width tells you how uncertain the estimate is — on real BTC data, Sharpe CI width is typically ~1.5 units, meaning you cannot distinguish effects below ~0.75 Sharpe.

**Example reading**: `p=0.818, CI=[-0.40, +1.07], width=1.47` — directional signal favors candidate (82% of resamples), but CI spans zero and is very wide. Not conclusive.

---

## 4. What Subsampling Now Means

Subsampling `p_a_better` is a **directional score** from Politis-Romano-Wolf block subsampling on geometric growth.

**It is NOT**:
- A posterior probability
- Calibrated when >80% of the differential return series are near-zero (degenerate data)
- A basis for automated promote/reject

**Reliability rule**: If `near_equal_1bp_rate > 80%`, subsampling results are unreliable. The harness flags this automatically.

**How to use it**: On non-degenerate pairs, subsampling agrees with bootstrap within ~2 percentage points on the same statistic. Use it as a **cross-check**, not an independent signal.

---

## 5. What DSR Now Means

DSR (Deflated Sharpe Ratio) is a **single-strategy advisory** — it answers "could this Sharpe arise from testing N strategies by chance?" (Bailey & Lopez de Prado, 2014).

**It is NOT**: a paired comparison tool. It says nothing about whether strategy A beats strategy B.

**How to use it**: Check both strategies' DSR. If both fail (high p-value), the entire comparison is suspect. If both pass, proceed with the paired diagnostics. DSR does not contribute to the pair decision directly.

---

## 6. What the Pair Diagnostic Harness Outputs

Run the harness:

```python
from research.lib.pair_diagnostic import run_pair_diagnostic, render_review_template

result = run_pair_diagnostic(equity_a, equity_b, "VTREND_A0", "VCUSUM")
template = render_review_template(result)
```

The output has two layers:

**Layer A — Machine diagnostic** (`PairDiagnosticResult`):
- Pair profile: tolerance-based equality rates, correlation, exposure overlap
- Classification: `near_identical`, `borderline`, or `materially_different`
- Bootstrap diagnostics (Sharpe + geo-growth statistics)
- Subsampling diagnostics (geo-growth)
- Cross-method consensus (bootstrap geo vs subsampling gap)
- DSR per strategy (advisory)
- Auto-generated caveats
- Suggested review route (non-binding)

**Layer B — Human review note** (blank section in the markdown template):
- Decision: `NO_ACTION` / `INCONCLUSIVE` / `PROMOTE` / `REJECT`
- Reasoning (must cite Section 1 values)
- Tradeoff summary
- Unresolved concerns

The harness has **zero decision authority**. The `PairDiagnosticResult` dataclass contains no decision/promote/reject field by design.

---

## 7. How to Fill the Human Review Note

1. Read Section 1 of the generated template
2. Check the classification — this determines the default review depth:
   - `near_identical`: usually NO_ACTION unless anomalous signal
   - `borderline`: always requires full manual review
   - `materially_different`: review diagnostics, assess power limitations
3. Check caveats — if subsampling is flagged unreliable, weight bootstrap more
4. Check consensus — if bootstrap and subsampling disagree (>5pp gap), investigate
5. Fill in Section 2:

```markdown
**Decision**: INCONCLUSIVE

**Reasoning**:
  Bootstrap directional score p=0.818 favors A0 over VCUSUM, but Sharpe CI
  spans zero ([-0.40, +1.07], width=1.47). Subsampling p=0.930 is consistent
  (consensus gap=0.6pp). Power is insufficient to distinguish at this effect
  size given T_eff ≈ 15.

**Tradeoff summary**:
  A0 shows +0.34 Sharpe advantage but cannot be confirmed statistically.

**Unresolved concerns**:
  CI width requires ΔSharpe >> 0.75 for significance. Observed Δ=0.34
  is well below this threshold.
```

**Decision options**:
- `NO_ACTION` — pair is near-identical or no meaningful difference found
- `INCONCLUSIVE` — diagnostics suggest a difference but power is insufficient to confirm
- `PROMOTE` — diagnostics consistently favor the candidate with supporting evidence
- `REJECT` — diagnostics consistently disfavor the candidate

---

## 8. What Researchers Must Never Claim

| Retired claim | Why |
|---------------|-----|
| "Bootstrap p=0.82 means 82% probability A is better" | `p_a_better` is a resampling score, not a probability. Not centered at null. |
| "Subsampling p=0.97 means 97% confidence" | Miscalibrated on degenerate data (produced p=0.97 on a known null pair). |
| "16/16 wins across timescales proves superiority" | V2 uncorrected binomial is BANNED for cross-strategy. Produces false positives (PROVEN\*\*\* on null pair). Use DOF correction (M_eff ≈ 2.5–4.0). |
| "Bootstrap/subsampling gate passed, so the candidate is validated" | These are diagnostics, not gates. They cannot pass or fail. |
| "Monte Carlo simulation shows 95% coverage, so real-data results are reliable" | Simulations used a toy generator (Student-t(3), no vol clustering). Real-data CI width is the binding constraint. |

---

## 9. Worked Examples

### Example A: Near-Identical Pair (A0 vs A1)

**Context**: A0 = ATR(14), A1 = ATR(20). Known near-null control (ΔSharpe = -0.006).

**Section 1 (machine output)**:
```
Classification: near_identical
  near_equal_1bp=98.9%, corr=0.987
  subsampling_reliable=False

Bootstrap (Sharpe): p=0.474, CI=[-0.124, +0.456], width=0.580
Bootstrap (geo growth): p=0.489, CI=[-0.0004, +0.0003]
Subsampling: p=0.965, CI=[-0.020, +0.015], support=0.33

Caveats:
  - Subsampling unreliable: near_equal_1bp_rate=98.9% > 80% threshold
  - Very high return correlation (0.987) — strategies may be near-equivalent

Suggested route: no_action_default
  Reason: near_identical pair, no anomalous signal
```

**Section 2 (researcher fills in)**:
```
Decision: NO_ACTION

Reasoning:
  Pair is near-identical (98.9% returns within 1bp, corr=0.987).
  Bootstrap p=0.474 shows no directional signal — consistent with null.
  Subsampling p=0.965 is flagged unreliable due to data degeneracy
  (98.9% near-zero differentials) and should be ignored.
  This is a known null control pair confirming the harness works correctly.

Tradeoff summary: None — strategies are functionally equivalent.

Unresolved concerns: None.
```

### Example B: Materially-Different Pair (A0 vs VCUSUM)

**Context**: A0 = VTREND canonical, VCUSUM = alternative entry. Observed ΔSharpe = +0.343.

**Section 1 (machine output)**:
```
Classification: materially_different
  near_equal_1bp=63.2%, corr=0.525
  subsampling_reliable=True

Bootstrap (Sharpe): p=0.818, CI=[-0.401, +1.072], width=1.473
Bootstrap (geo growth): p=0.924, CI=[-0.069, +0.601]
Subsampling: p=0.930, CI=[-0.139, +0.625], support=0.00

Consensus: gap=0.6pp — OK

Caveats:
  - Bootstrap Sharpe CI width=1.473 (wide — low discriminative power)
  - Subsampling support=0.00 (expected for available effect sizes)

Suggested route: inconclusive_default
  Reason: materially_different pair, diagnostics consistent, power limitation applies
```

**Section 2 (researcher fills in)**:
```
Decision: INCONCLUSIVE

Reasoning:
  Directional signal consistently favors A0 (boot_sharpe p=0.818,
  boot_geo p=0.924, sub p=0.930, consensus gap=0.6pp — methods agree).
  However, bootstrap Sharpe CI spans zero ([-0.40, +1.07]) with
  width=1.47, meaning the test cannot distinguish ΔSharpe=0.34 from
  noise. Subsampling support=0.00 confirms no block-size configuration
  achieves the CI gate at this effect size.

Tradeoff summary:
  A0 shows Sharpe +0.34 over VCUSUM. Advantage direction is consistent
  across methods but magnitude is below the detectable threshold
  (need ΔSharpe >> 0.75 given CI width).

Unresolved concerns:
  Power insufficient at T_eff ≈ 15. Would need ~4× more data
  (or a much larger effect) for conclusive result.
```
