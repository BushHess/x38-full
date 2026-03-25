# Research Q13: Step 5 Threshold Provenance — Is -0.35 Arbitrary?

**Date**: 2026-03-08
**Script**: `research/x6/threshold_sensitivity_q13.py`
**Sources**: `run_step5_live_signoff.py`, `recompute_signoff.py`, Report 32
**Question**: Where does the -0.35 combined disruption threshold come from? If it's also convention like WFO 60%, we're rejecting the best strategy based on 2 arbitrary thresholds in series.

---

## 1. Tracing the -0.35 Threshold

### Where it lives

```python
# run_step5_live_signoff.py, lines 78-91
SIGNOFF_GATES = {
    "GO": {
        "p95_delta_sharpe": -0.15,
        "p_cagr_le_0": 0.10,
        "p95_delta_mdd_frac": 0.25,
        "worst_combo_delta_sharpe": -0.20,
    },
    "GO_WITH_GUARDS": {
        "p95_delta_sharpe": -0.30,
        "p_cagr_le_0": 0.20,
        "p95_delta_mdd_frac": 0.50,
        "worst_combo_delta_sharpe": -0.35,
    },
}
```

Identically duplicated in `recompute_signoff.py` lines 22-35. No shared constants module.

### Provenance search results

| Source searched | Found -0.35 derivation? |
|----------------|:-----------------------:|
| Step 5 report | NO — states threshold, doesn't derive it |
| Step 4 report | NO — Step 4 predated Step 5 thresholds |
| Step 3 report | NO — Step 3 has no sign-off gates |
| Report 32 (threshold audit) | **NOT INCLUDED** — Report 32 audits validation pipeline only |
| All research_reports/ (1-37) | NO |
| All code comments | NO — bare constant with no inline justification |
| VTREND_BLUEPRINT.md | NO |
| Any .md or .py file | NO reference to simulation, derivation, or literature for -0.35 |

**Result: ZERO PROVENANCE.** The -0.35 threshold has no documented statistical basis, no simulation calibration, no literature reference, and was not included in Report 32's comprehensive threshold audit (which covered 47 heuristics in the validation pipeline but not Step 5's research script).

---

## 2. The Complete Threshold Inventory for Step 5

| Threshold | Value | Provenance | Binding? |
|-----------|:-----:|:----------:|:--------:|
| GO: p95_delta_sharpe | -0.15 | NONE | SM blocked at LT3 |
| GO: p_cagr_le_0 | 0.10 | NONE | Never binding |
| GO: p95_delta_mdd_frac | 0.25 | NONE | Never binding |
| GO: worst_combo | -0.20 | NONE | E0/E0_plus blocked from GO |
| **GWG: worst_combo** | **-0.35** | **NONE** | **E5/E5_plus blocked from GWG** |
| GWG: p95_delta_sharpe | -0.30 | NONE | Never binding |
| GWG: p_cagr_le_0 | 0.20 | NONE | Never binding |
| GWG: p95_delta_mdd_frac | 0.50 | NONE | Never binding |

**ALL 8 Step 5 thresholds have zero provenance.** But only one matters: `worst_combo_delta_sharpe = -0.35` is the SOLE binding constraint that separates E0_plus (PASS) from E5_plus (FAIL).

---

## 3. Threshold Sensitivity: Who Passes at Each Level?

| Threshold | SM | E0_plus | E0 | E5_plus | E5 |
|:---------:|:--:|:-------:|:--:|:-------:|:--:|
| -0.20 | GO | HOLD | HOLD | HOLD | HOLD |
| -0.25 | GO | HOLD | HOLD | HOLD | HOLD |
| -0.30 | GO | HOLD | HOLD | HOLD | HOLD |
| -0.32 | GO | **GWG** | HOLD | HOLD | HOLD |
| **-0.35** | **GO** | **GWG** | **GWG** | **HOLD** | **HOLD** |
| -0.40 | GO | GWG | GWG | **GWG** | HOLD |
| -0.45 | GO | GWG | GWG | GWG | **GWG** |

### Critical flip points

| Threshold | What changes | Recommendation becomes |
|:---------:|:-------------|:----------------------|
| > -0.318 | E0_plus also fails | **SM is the only deployable candidate** |
| **-0.35 (current)** | **E0_plus passes, E5_plus fails** | **X0 (E0_plus)** |
| < -0.396 | E5_plus also passes | **E5+EMA1D21 (reinstated as best)** |

The entire decision rests on the threshold falling between -0.318 and -0.396 — a window of 0.078 Sharpe units.

---

## 4. The Two Arbitrary Thresholds in Series

### Threshold 1: WFO win_rate >= 0.60

| Attribute | Value |
|-----------|-------|
| Source | `validation/thresholds.py` (hardcoded default) |
| Provenance | **Report 32 H04: "UNPROVEN"** |
| Statistical basis | For N=8: P(≥5/8 \| H₀) = 0.363 — NOT a standard significance level |
| Report 32 assessment | "60% ≠ any standard significance level" |
| Impact | X2/X6 fail (4/8), E5+ passes (5/8), X0 passes (6/8) |

**Binomial test (H₀: fair coin):**

| Strategy | WFO | P(≥k/8 \| H₀) | α=0.05? |
|----------|:---:|:---:|:---:|
| X0 | 6/8 | 0.145 | FAIL |
| E5+EMA21 | 5/8 | 0.363 | FAIL |
| X2/X6 | 4/8 | 0.637 | FAIL |

**NONE are significant at α=0.05.** Even X0's 6/8 corresponds to p=0.145. The 60% threshold creates an arbitrary line between X0 (passes) and E5+EMA21 (passes) and X2/X6 (fails), but none of these results would survive a formal hypothesis test.

### Threshold 2: worst_combo_delta_sharpe > -0.35

| Attribute | Value |
|-----------|-------|
| Source | `run_step5_live_signoff.py` line 89 (hardcoded constant) |
| Provenance | **NONE — not even in Report 32's 47-heuristic inventory** |
| Statistical basis | NONE |
| Simulation basis | NONE |
| Literature reference | NONE |
| Impact | E0_plus passes (-0.318, margin 0.032), E5_plus fails (-0.396, over by 0.046) |

### Combined effect

```
Strategy  → Threshold 1 (WFO 60%)  → Threshold 2 (-0.35)  → Final
────────    ─────────────────────     ───────────────────    ──────
X2/X6     → FAIL (4/8)              → (not reached)        → REJECT
E5+EMA21  → PASS (5/8)              → FAIL (-0.396)        → HOLD
X0        → PASS (6/8)              → PASS (-0.318)        → GO_WITH_GUARDS
E0        → N/A (is baseline)       → PASS (-0.322)        → GO_WITH_GUARDS
```

X0 is the sole binary survivor of two serial filters, both with zero statistical provenance.

---

## 5. Report 32 Already Flagged This Problem (for WFO)

Report 32 §3.4 on H04 (WFO win_rate=0.60):

> "Bare default on DecisionPolicy. For N=8 windows, 60% requires 5/8 positive. Under H₀ (fair coin), P(≥5/8) = 0.363 — this does NOT correspond to any standard significance level."

Report 32 §5.1 counterfactual analysis found zero verdict flips because all failures were gross (deltas of -33 to -76 vs tolerance of -0.2). But it warned:

> "This stability may reflect the homogeneity of archived runs... not inherent threshold robustness. A diverse corpus of 'almost-passing' runs would provide a more informative sensitivity test."

The E0_plus vs E5_plus decision IS the "almost-passing" case Report 32 warned about. And it flips on 0.078 Sharpe units.

---

## 6. Report 32 Did NOT Audit Step 5

Report 32's scope (§1):

> "Every threshold, routing heuristic, and string-matching rule that can influence the final decision verdict"

It audited `decision.py`, `runner.py`, and 11 suite producers — the **validation pipeline**. Step 5 is a separate research script (`run_step5_live_signoff.py`) that was written AFTER Report 32 (Step 5 date: 2026-03-06; Report 32 date: 2026-03-04).

**Step 5's 8 thresholds were never subjected to provenance audit.** They escaped the governance framework entirely because they live in a research script, not in the validation pipeline.

---

## 7. What a Proper Threshold Would Look Like

### Option A: Statistical calibration via simulation

Generate N synthetic strategy pairs with known performance gap. For each pair, compute combined disruption delta. Find the threshold that minimizes false positive rate (rejecting a genuinely superior strategy) while controlling false negative rate (approving a fragile strategy).

**Not done.** Would require defining "genuinely superior" and "fragile" distributions.

### Option B: Empirical quantile from observed data

Set threshold as p-th percentile of the observed combined disruption distribution across all candidates. E.g., threshold = median (p50) of all 5 deltas:

```
Sorted deltas: -0.402, -0.396, -0.322, -0.318, -0.000
Median: -0.322
```

At median threshold (-0.322), E0_plus barely passes (-0.318) and E5_plus fails (-0.396). Similar to current but data-driven.

### Option C: Relative to baseline Sharpe

"No more than X% of baseline Sharpe lost under worst-case disruption."

| Candidate | Baseline | Worst delta | % loss |
|-----------|:--------:|:----------:|:------:|
| E0_plus | 1.325 | -0.318 | 24.0% |
| E5_plus | 1.430 | -0.396 | 27.7% |

If threshold = "max 25% loss": E0_plus passes (24.0%), E5_plus fails (27.7%). This at least has a meaningful interpretation — but 25% is still arbitrary.

### Option D: Accept that thresholds are necessarily arbitrary

Acknowledge that any threshold for "acceptable operational fragility" is a risk appetite decision, not a statistical one. Document it as such, provide sensitivity analysis, and let the decision-maker choose.

---

## 8. The Core Finding

### The recommendation chain has 3 links, ALL with zero statistical provenance

| Link | Threshold | Provenance | Effect |
|------|:---------:|:----------:|--------|
| 1. Validation WFO | 60% win rate | UNPROVEN (Report 32 H04) | Filters X2/X6 |
| 2. Validation holdout | delta > -0.20 | Documented but weak (Report 32 H01/H02) | Confirms X0 > E0 |
| 3. **Step 5 combined** | **> -0.35** | **ZERO PROVENANCE** | **Filters E5+EMA1D21** |

E5+EMA1D21 dominates X0 on 16/20 scorecard dimensions (Q9). The ONLY reason X0 is recommended is link 3 — an undocumented threshold in a research script that was never audited.

### The margin is razor-thin

```
E0_plus (X0):  -0.318  →  passes by 0.032
E5_plus:       -0.396  →  fails by  0.046
                                     ─────
Total gap:                           0.078 Sharpe units
```

A threshold shift of 0.078 (from -0.35 to -0.43) reverses the entire recommendation. For context, the Sharpe standard error with 2607 daily observations is ~0.048 — the gap is only 1.6 standard errors.

---

## 9. Counterarguments

### "The threshold is conservative, which is good for live capital"

True. Conservative thresholds protect capital. But:
- If the goal is "protect capital at all costs," then the threshold should be -0.20 (GO level), which rejects ALL binary candidates including X0
- SM would be the only recommendation at any threshold tighter than -0.318
- The -0.35 level specifically advantages X0 over E5+EMA1D21 without justification

### "E5+EMA1D21 is genuinely more fragile"

True — E5+EMA1D21 loses 40.7% of Sharpe at D4 vs X0's 31.7%. The fragility difference is real. But:
- The QUESTION is not "is there a difference?" but "where do you draw the line?"
- At -0.35, you draw it between them. At -0.40, both fail. At -0.32, both pass.
- Without provenance, the -0.35 cutoff is as arbitrary as any other

### "Step 5 knew it was a convention"

The signoff_findings.md states:
> "Key margin: worst combined delta = -0.318 vs threshold -0.35 (headroom = 0.032). This is tight."

Step 5 acknowledged the margin was tight but did not question whether -0.35 was the right number.

---

## 10. Summary

| Question | Answer |
|----------|--------|
| Where does -0.35 come from? | `run_step5_live_signoff.py` line 89 — **hardcoded constant, zero derivation** |
| Is there documentation? | **NO** — no report, no comment, no literature reference |
| Is there simulation basis? | **NO** — no calibration study |
| Is there statistical basis? | **NO** — not derived from any distribution or test |
| Was it included in Report 32's threshold audit? | **NO** — Step 5 was written after Report 32 and escaped the governance framework |
| Is this the same as WFO 60%? | **WORSE** — WFO 60% was at least flagged as "unproven" by Report 32. The -0.35 has never been audited at all. |
| Are we rejecting the best strategy on 2 arbitrary thresholds? | **YES** — WFO 60% (unproven) filters X2/X6, combined -0.35 (zero provenance) filters E5+EMA1D21. Neither has statistical calibration. |
| How tight is the margin? | **0.078 Sharpe** total gap. Threshold shift of 0.05 in either direction reverses the verdict. |
| What would change the conclusion? | Threshold < -0.396: E5+EMA1D21 reinstated. Threshold > -0.318: X0 also rejected, SM only survivor. |
