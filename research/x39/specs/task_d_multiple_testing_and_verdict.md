# Task D: Multiple Testing Correction & Final Verdict

## Prerequisites
- Task B completed (strategy implemented, reproduction confirmed)
- Task C completed (formal validation results available for thr=0.6 and/or 0.7)

## Session prompt

```
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/formal_validation_spec.md
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/task_d_multiple_testing_and_verdict.md

Execute Phase 4 + Phase 5 of the formal validation spec.

Context from prior tasks:
- Read results/full_eval_e5_ema21d1_vc_06/reports/decision.json for thr=0.6 verdict
- Read results/full_eval_e5_ema21d1_vc_07/reports/decision.json for thr=0.7 verdict
- Read formal_validation_spec.md Phase 2 and Phase 3 sections for prior results
```

## What this task does

1. **Phase 4**: Compute multiple testing correction (52 x39 experiments)
2. **Phase 5**: MDD trade-off analysis (thr=0.6 vs 0.7)
3. **Final verdict**: Synthesize all evidence into CONCLUDE / REJECT / INCONCLUSIVE

---

## Phase 4: Multiple Testing Correction

### Step 4.1 — DSR with N=52

Write and run: `research/x39/experiments/formal_dsr_analysis.py`

```python
import sys
sys.path.insert(0, "/var/www/trading-bots/btc-spot-dev")

from research.lib.dsr import compute_dsr, deflated_sharpe
import numpy as np
import json

# Load candidate returns from validation output
# Check results/full_eval_e5_ema21d1_vc_06/results/ for the right file
# Usually in full_backtest_detail.json or trades_candidate.csv

# Method 1: From backtest summary
# If annualized Sharpe is available, use deflated_sharpe() directly:
#   sr_observed = annualized_sharpe_from_decision_json
#   n_trials = 52
#   t_samples = number_of_H4_bars_in_backtest_period
#   skew, kurt = computed from return series

# Method 2: From return series (preferred if available)
# result = compute_dsr(returns=bar_returns, num_trials=52, bars_per_year=6*365.25)
# print(f"DSR p-value: {result['dsr_pvalue']:.6f}")
# print(f"SR₀ (expected max under null): {result['sr0_annualized']:.4f}")
# print(f"Observed SR: {result['sr_annualized']:.4f}")

# For BOTH thresholds (0.6 and 0.7):
for thr in ["06", "07"]:
    # Load returns, compute DSR
    # ...
    pass
```

**Key question**: Is observed Sharpe > SR₀ (expected max from 52 random trials)?

**Expected**: SR₀ for N=52, T≈16000 is ~0.35-0.45. Observed ~1.49. Large margin.
But verify — DSR also accounts for skewness and kurtosis of BTC returns.

### Step 4.2 — Effective DOF (M_eff)

This is a secondary analysis. Only needed if DSR is borderline (p between 0.01-0.10).

If DSR p < 0.01 with N=52: skip M_eff (already conclusive).
If DSR p > 0.01: compute M_eff to see if correcting for correlated experiments helps.

```python
from research.lib.effective_dof import compute_meff

# Construct correlation matrix (simplified approach):
# Group experiments by shared mechanism:
#   Group A (exit variants): exp12,13,19-31 — 14 experiments, ~3 independent mechanisms
#   Group B (entry timing): exp32-39 — 8 experiments, ~4 independent mechanisms
#   Group C (combos): exp43-47 — 5 experiments, ~2 independent mechanisms
#   Group D (validation): exp40-42,49 — 4 experiments, ~2 independent mechanisms
#   Group E (other): exp01,14-18,48,50-52 — ~10 experiments, ~8 independent
#   Rough M_eff estimate: 3+4+2+2+8 = 19

# If formal M_eff needed:
# Build 52x52 binary outcome correlation matrix and call compute_meff()
```

### Step 4.3 — WFO Bonferroni correction

From formal validation spec Phase 4, Layer 3:

- 4 mechanisms submitted to WFO in x39 (AND-gate, velocity, accel, compression)
- Bonferroni-corrected α = 0.05 / 4 = 0.0125

From Task C results:
- Read the Wilcoxon p-value from v10's G4
- Is Wilcoxon p < 0.0125? (stricter than standard α=0.10)

If v10 WFO uses N=8 windows and all are positive:
- Binary: (0.5)^8 = 0.0039. Bonferroni: 4 × 0.0039 = 0.016 → borderline
- Wilcoxon: depends on effect sizes per window

### Step 4.4 — Record results

Write to `results/full_eval_e5_ema21d1_vc_06/x39_multiple_testing.json`:
```json
{
  "n_experiments_total": 52,
  "n_wfo_tests": 4,
  "dsr_pvalue_thr06": null,
  "dsr_pvalue_thr07": null,
  "dsr_sr0_annualized": null,
  "m_eff_estimate": null,
  "m_eff_method": "rough_grouping | nyholt | li_ji | galwey",
  "dsr_corrected_pvalue": null,
  "wfo_bonferroni_alpha": 0.0125,
  "v10_wilcoxon_p": null,
  "wfo_bonferroni_pass": null,
  "analyst_dof_notes": "..."
}
```

---

## Phase 5: MDD Trade-Off Analysis

### Step 5.1 — Extract metrics from Task C

From `decision.json` for both thresholds:

| Metric | thr=0.6 | thr=0.7 | Baseline |
|--------|---------|---------|----------|
| Sharpe | | | |
| CAGR% | | | |
| MDD% | | | |
| Calmar (CAGR/MDD) | | | |
| Trades | | | |

### Step 5.2 — MDD confidence interval

Check if the validation output includes bootstrap MDD distribution.
If available (from bootstrap suite):
- MDD 95% CI for baseline
- MDD 95% CI for compression
- If CIs overlap → MDD difference is within noise

If not available, assess from WFO windows:
- Per-window MDD for baseline and compression
- Does compression have worse MDD in ALL windows or just some?

### Step 5.3 — Recommendation

Apply decision criteria from formal_validation_spec.md Phase 5:

| Criterion | thr=0.6 preferred | thr=0.7 preferred |
|-----------|-------------------|-------------------|
| Max Sharpe | ? | ? |
| Min MDD | ? | ? |
| Best Calmar | ? | ? |
| Parameter safety margin | | thr=0.7 (less aggressive) |
| WFO consistency | ? | ? |

Default recommendation: **thr=0.7** unless thr=0.6 passes G4 and thr=0.7 doesn't.

---

## Final Verdict

### Collect all evidence

| Evidence Layer | thr=0.6 | thr=0.7 |
|---------------|---------|---------|
| v10 pipeline verdict | | |
| v10 G4 Wilcoxon p | | |
| DSR p (N=52) | | |
| WFO Bonferroni pass? | | |
| Calmar vs baseline | | |
| d_Sharpe (v10) | | |
| d_MDD (v10) | | |

### Apply decision matrix (from spec)

| Scenario | DSR | WFO (v10 G4) | → Verdict |
|----------|-----|--------------|-----------|
| A | PASS (p<0.05) | PASS (Wilcoxon p<0.10) | **CONCLUDE** |
| B | PASS | FAIL | **INCONCLUSIVE** (WFO underresolved) |
| C | FAIL | PASS | **INCONCLUSIVE** (selection bias concern) |
| D | FAIL | FAIL | **REJECT** |

### Write conclusion

Update `formal_validation_spec.md` with final verdict section:

```markdown
## Final Verdict: [CONCLUDE / REJECT / INCONCLUSIVE]

### Evidence summary
- Phase 2 reproduction: [PASS/FAIL] — d_Sharpe = X (x39: Y, ratio: Z%)
- Phase 3 pipeline: [PROMOTE/HOLD/REJECT] — G4 Wilcoxon p = X
- Phase 4 DSR: p = X (N=52), SR₀ = Y
- Phase 4 WFO Bonferroni: [PASS/FAIL] — corrected p = X
- Phase 5 threshold: [0.6/0.7] — Calmar [improves/degrades]

### Recommendation
[One paragraph: what to do next based on evidence]
```

---

## After completion

1. Update `formal_validation_spec.md` Status from PENDING → DONE
2. Write summary to `x39/PLAN.md` (add row for formal validation)
3. If CONCLUDE: update MEMORY.md with new algorithm status
4. If INCONCLUSIVE: document what additional evidence is needed
5. If REJECT: document why and close the vol compression line of research
