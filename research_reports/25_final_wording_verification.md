# Report 25 — Final Wording Cleanup & Verification

**Date**: 2026-03-04
**Canonical plan**: `research_reports/22_b_inference_patch_plan.md`, Phase 5
**Scope**: Wording cleanup in reports/docs + final regression verification for all 5 phases

---

## 1. What Changed (This Prompt)

### 5A: Toy-generator caveat added to Report 02

**File**: `research_reports/02_inference_stack_audit.md`

- **§4.1** (after coverage claim): Added 5-line caveat noting Student-t(3) generator lacks volatility clustering, has ~2× lower vol-of-vol than real BTC 4H, and that real-data CI width (Report 18) is the binding power constraint.
- **§4.2** (after Type I error claim): Added back-reference to §4.1 caveat.

### 5B: p-value wording — No changes needed

Reports 02 and 18 already correctly characterize `p_a_better`. Confirmed by audit.

### 5C: Permutation test scope — No changes needed

Report 02 §1.4 and MEMORY.md already scope permutation to component-level. Confirmed by audit.

---

## 2. What Did NOT Change

| Item | Reason |
|------|--------|
| Statistical logic | Out of scope — no computation changes |
| Gate behavior | Already correct from Prompts 24/24B |
| Bootstrap/subsampling code | Already correct from Prompts 23/24/24B |
| Pair diagnostic harness | Already correct from Prompt 23 |
| Decision engine | Already correct from Prompt 24 |
| Any production code | Phase 5 is docs/reports only |

---

## 3. Final Touched Files List (All Phases, Prompts 23–25)

### Production code modified

| File | Phase | Change |
|------|-------|--------|
| `v10/research/bootstrap.py` | 1A, 1B | Alignment ValueError + p_a_better docstring |
| `v10/research/subsampling.py` | 1C | Degeneracy caveat docstring |
| `validation/suites/bootstrap.py` | 1B, 24B | Inline comment + status always "info" |
| `validation/suites/subsampling.py` | 1C, 3B | Inline comment + status always "info" |
| `validation/suites/selection_bias.py` | 1E | DSR calling convention docs |
| `validation/decision.py` | 3A | Bootstrap gate → diagnostic (severity="info", passed=True) |
| `research/lib/dsr.py` | 1E | Calling convention docstring |

### Research scripts (comments only)

| File | Phase | Change |
|------|-------|--------|
| `research/e5_validation.py` | 1D | V2 ban warning comment |
| `research/trail_sweep.py` | 1D | V2 ban warning comment |

### New files

| File | Phase | Content |
|------|-------|---------|
| `research/lib/pair_diagnostic.py` | 2 | Machine-only pair diagnostic harness (~350 LOC) |
| `research/tests/__init__.py` | 2 | Package init |
| `research/tests/test_pair_diagnostic.py` | 2 | 17 tests for harness |
| `validation/tests/test_inference_role_semantics.py` | 4, 24B | 20 role-semantic tests |

### Reports/docs modified

| File | Phase | Change |
|------|-------|---------|
| `research_reports/02_inference_stack_audit.md` | 5A | Toy-generator caveat on §4.1 and §4.2 |
| `research_reports/23_phase1_phase2_implementation.md` | — | Implementation report (Prompt 23) |
| `research_reports/24_phase3_phase4_implementation.md` | — | Implementation report (Prompt 24) |
| `research_reports/24_b_bootstrap_suite_status_fix.md` | — | Implementation report (Prompt 24B) |
| `research_reports/25_final_wording_verification.md` | — | This report |

---

## 4. Final Test Run Summary

### Focused regression (canonical §7.4 set)

```
99 passed, 0 failed in 56.51s
```

Files included:
- `v10/tests/test_bootstrap.py` (17 tests, incl. 1 new alignment test)
- `v10/tests/test_subsampling.py` (9 tests)
- `v10/tests/test_decision.py` (10 tests)
- `research/tests/test_pair_diagnostic.py` (17 tests, all new)
- `validation/tests/` (46 tests, incl. 20 new role-semantic tests)

### Full regression

```
436 passed, 0 failed, 34 warnings in 82.50s
```

All 34 warnings are pre-existing (numpy divide-by-zero in v8_apex.py / v11_hybrid.py).

### Test count reconciliation

| Source | New tests | Total in file |
|--------|-----------|---------------|
| `v10/tests/test_bootstrap.py` | +1 (alignment) | 17 |
| `research/tests/test_pair_diagnostic.py` | +17 (all new) | 17 |
| `validation/tests/test_inference_role_semantics.py` | +20 (16 from P24 + 4 from P24B) | 20 |
| **Total new** | **38** | — |

The canonical plan (Report 22B §7.3) estimated 19 new tests. Actual: 38. Difference explained by:
- Plan estimated 11 harness tests → actual 17 (6 additional classification/routing tests)
- Plan estimated 7 role-semantic tests → actual 20 (9 parametrized T1-T3 + 4 bootstrap suite status tests from P24B + T5/T6/T7 + 4 flow-through tests)

No `.md.md` path oddities encountered during implementation.

---

## 5. What Researchers Must Stop Claiming

These claims are now explicitly documented as incorrect across the codebase:

| Retired claim | Correct statement | Where documented |
|---------------|-------------------|-----------------|
| Bootstrap `p_a_better` is a p-value | Directional resampling score, not calibrated | `bootstrap.py` docstring, `suites/bootstrap.py` comment, `decision.py` comment |
| Subsampling `p_a_better` is a posterior probability | Directional score, miscalibrated when near-equality >80% | `subsampling.py` docstring, `suites/subsampling.py` comment |
| Bootstrap/subsampling can promote or reject | Diagnostic/info only — human review required | `decision.py` (severity="info"), both suites (status="info"), 20 regression tests |
| V2 uncorrected win-count is valid for cross-strategy | Must use DOF correction (M_eff ≈ 2.5–4.0); demonstrated false positive on null pair | `e5_validation.py` + `trail_sweep.py` warning blocks |
| Simulation coverage/Type I guarantees apply to real BTC | Toy-generator findings only; CI width on real pairs is the binding constraint | `02_inference_stack_audit.md` §4.1–4.2 caveats |

---

## 6. What Remains Intentionally Manual

| Item | Why |
|------|-----|
| Final promote/reject decision | By design — `PairDiagnosticResult` has NO decision field. Human fills in Section 2 of review template. |
| Multi-timescale V1/V3 analysis | Researcher-invoked extension only. Not part of standard pair diagnostic. |
| DOF correction for cross-strategy claims | Researcher must invoke `research/lib/effective_dof.py` explicitly. Scripts have warning comments. |

---

## 7. Intentionally Deferred Cleanup

| Item | Reason deferred |
|------|----------------|
| `BootstrapSuite.run()` direct smoke test (invoking actual `run()` with a `SuiteContext`) | Requires full backtest fixture with equity curves. Current coverage is via synthetic `SuiteResult` construction + decision engine flow-through. Adding a full integration test is a separate ticket. |
| `DecisionPolicy.bootstrap_p_threshold` / `bootstrap_ci_lower_min` field removal | These fields still exist on the policy dataclass but are unreferenced after P24. Removing them is an API cleanup, not a semantic fix. |
| `summarize_block_grid().decision_pass` in subsampling | Grid still computes `decision_pass` for diagnostic display. Not a gate. Renaming is cosmetic. |
| Broader documentation sweep (untouched reports, MEMORY.md entries) | Out of scope per task constraints — only files directly adjacent to already-touched files were checked. |
| `v10/tests/test_decision.py` alignment with `validation/decision.py` | These test different modules (`v10.research.decision` vs `validation.decision`). No cross-contamination found. Unification is a separate concern. |

---

## 8. Implementation Timeline

| Prompt | Phase | Tests added | Key change |
|--------|-------|-------------|------------|
| 23 | 1 (safety/docs) + 2 (harness) | +18 | Alignment check, caveats, pair diagnostic harness |
| 24 | 3 (gate retirement) + 4 (regression) | +16 | Bootstrap/subsampling → diagnostic in decision engine |
| 24B | 3 supplement | +4 | Bootstrap suite status → always "info" |
| 25 | 5 (wording) | 0 | Toy-generator caveat in Report 02, final verification |
| **Total** | **All 5 phases** | **+38** | — |

---

*All 5 phases of Report 22B are now complete. 436 tests pass. Zero automated promote/reject authority. Human review remains the sole decision authority.*
