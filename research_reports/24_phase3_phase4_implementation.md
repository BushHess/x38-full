# Report 24 — Phase 3 + Phase 4 Implementation Report

**Date**: 2026-03-03
**Canonical plan**: `research_reports/22_b_inference_patch_plan.md`
**Scope**: Phase 3 (retire unsafe gate semantics) + Phase 4 (regression tests)

---

## 1. Canonical Plan Path

`research_reports/22_b_inference_patch_plan.md` — no mapping needed, exact match.

---

## 2. Touched Files

| File | Phase | Change type |
|------|-------|------------|
| `validation/decision.py` | 3A | Bootstrap gate → diagnostic (severity, passed, failures) |
| `validation/suites/subsampling.py` | 3B | Suite status → always "info" |
| `validation/tests/test_inference_role_semantics.py` | 4 | **NEW** — regression tests |

---

## 3. Behavior Changed

### Phase 3A: Bootstrap gate → diagnostic in `validation/decision.py`

**Before** (lines 298–321):
```python
passed = p >= policy.bootstrap_p_threshold and ci_low > policy.bootstrap_ci_lower_min
gates.append(GateCheck(gate_name="bootstrap", passed=passed, severity="soft", ...))
if not passed:
    failures.append("bootstrap_gate_failed")
    reasons.append("Bootstrap evidence not strong enough for promote")
```

**After**:
```python
gates.append(GateCheck(gate_name="bootstrap", passed=True, severity="info", ...))
# No failures.append — bootstrap has no veto power.
```

Changes made:
1. `passed=True` unconditionally — bootstrap cannot fail
2. `severity="soft"` → `severity="info"` — excluded from soft_failures filter at line 446
3. Removed `if not passed` block — no `failures.append("bootstrap_gate_failed")`
4. Updated `GateCheck.severity` type comment: `# hard | soft` → `# hard | soft | info`
5. Detail string updated to state "diagnostic only — no veto power"

**Consequence**: The decision engine's verdict logic at lines 445–453 filters on `severity == "hard"` and `severity == "soft"`. Since bootstrap is now `severity="info"`, it is excluded from both `hard_failures` and `soft_failures`, meaning it can never cause REJECT or HOLD.

### Phase 3B: Subsampling suite status → info in `validation/suites/subsampling.py`

**Before** (line 139/142):
```python
status = "info" if not gate else ("pass" if bool(gate.get("decision_pass")) else "fail")
```

**After**:
```python
# Subsampling is a DIAGNOSTIC, not a gate (Report 21, §1.1; Report 22B, Phase 3B).
# Gate dict is still populated for diagnostic consumption, but status is always "info".
status = "info"
```

Note: Subsampling was never wired into `validation/decision.py`'s gate logic (no `results.get("subsampling")` call exists). This change prevents any future consumer from interpreting the suite status as pass/fail.

---

## 4. Diagnostic Fields Preserved

| Field | Location | Status |
|-------|----------|--------|
| `deltas["bootstrap_p_candidate_better"]` | `validation/decision.py` | **PRESERVED** — still populated with `round(p, 4)` |
| `deltas["bootstrap_ci_lower"]` | `validation/decision.py` | **PRESERVED** — still populated with `round(ci_low, 6)` |
| Bootstrap `GateCheck` in `gates` list | `validation/decision.py` | **PRESERVED** — gate entry still exists with detail string |
| `gate` dict in bootstrap suite data | `validation/suites/bootstrap.py` | **UNCHANGED** — `p_candidate_better`, `ci_lower`, `ci_upper`, `observed_delta` |
| `gate` dict in subsampling suite data | `validation/suites/subsampling.py` | **UNCHANGED** — `p_candidate_better`, `ci_lower`, `support_ratio`, `decision_pass` |
| `rows` in both suite results | Both suites | **UNCHANGED** — per-scenario/block-size detail rows |

---

## 5. Tests Added/Updated

### New file: `validation/tests/test_inference_role_semantics.py`

| Test method | Plan ID | Parametrized | What it verifies |
|-------------|---------|-------------|------------------|
| `test_bootstrap_gate_is_info_not_soft` | T1 | ×3 pairs | `severity="info"`, `passed=True` for all control pairs |
| `test_bootstrap_never_in_failures` | T2 | ×3 pairs | `"bootstrap_gate_failed"` never in `failures` |
| `test_bootstrap_still_reports_values` | T3 | ×3 pairs | `deltas` contains bootstrap_p and ci_lower with correct values |
| `test_subsampling_status_always_info` | T4 | — | Status is "info" regardless of `decision_pass` |
| `test_subsampling_gate_data_preserved` | — | — | Gate dict still contains diagnostic values |
| `test_negative_control_not_blocked` | T5 | — | A0 vs A1 not blocked by diagnostics |
| `test_strong_positive_not_blocked` | T6 | — | A0 vs VCUSUM not blocked by diagnostics |
| `test_bootstrap_only_results_promote` | — | — | Bootstrap-only → PROMOTE (no gates can veto) |
| `test_no_hidden_promote_reject_path` | — | — | Extreme bootstrap values (p=0, ci=-10) still pass |
| `test_bootstrap_alignment_rejects_mismatch` | T7 | — | Length-mismatched curves raise ValueError |

### Existing tests updated: 0

No existing test relied on bootstrap gate veto behavior or subsampling pass/fail status. Analysis:
- `v10/tests/test_decision.py` tests `v10.research.decision` (a separate module, not `validation.decision`)
- `validation/tests/test_decision_payload.py` tests cost_sweep/churn/regression_guard, not bootstrap gate
- `validation/tests/test_invariants.py` tests invariant violations, not bootstrap
- `validation/tests/test_data_integrity.py` tests data integrity, not bootstrap
- No test anywhere references `"bootstrap_gate_failed"` or checks subsampling suite status

---

## 6. Exact New/Updated Test Count

| File | New tests | Updated tests |
|------|-----------|--------------|
| `validation/tests/test_inference_role_semantics.py` | **16** | 0 |

The 16 count comes from:
- T1–T3 are parametrized ×3 control pairs = 9 test cases
- T4–T7 = 4 tests
- 3 additional tests (subsampling data preserved, bootstrap-only promote, no hidden path)
- Total: 9 + 4 + 3 = **16 new tests**

---

## 7. Test-Count Discrepancy Explanation (17 vs 18 from Prompt 23)

The Prompt 23 implementation report stated **18 new tests**. Here is the exact breakdown:

**Prompt 23 (Phase 1 + Phase 2):**
- `v10/tests/test_bootstrap.py`: +1 test (alignment mismatch)
- `research/tests/test_pair_diagnostic.py`: +17 tests (T8–T18 = 11 plan tests + 6 additional)
- Total: **18 new tests**

The plan (§7.3) states "Total new tests: 19" and lists:
- Phase 1: +1 (alignment)
- Phase 2: +11 (T8–T18) → actually 17 implemented (6 additional for coverage)
- Phase 4: +7 (T1–T7) → actually 16 implemented (T1–T3 parametrized ×3, +3 additional)

The plan's "19" counted the enumerated tests (T1–T18 = 18) plus the Phase 1 alignment test (1) = 19 IDs. But T1–T3 are each verified across 3 control pairs (parametrized), and additional tests were added for completeness.

**Actual totals across Prompts 23 + 24: 18 + 16 = 34 new tests.**

---

## 8. Path Deviations from Patch Plan

| Plan path | Actual path | Reason |
|-----------|-------------|--------|
| All files | Exact match | No deviations |

---

## 9. Known Limitations Intentionally Unchanged

| Item | Status | Reason |
|------|--------|--------|
| `BootstrapSuite` status logic (line 104) | UNCHANGED | The suite still computes pass/fail in its own status field (`status = "pass" if p >= 0.80 and ci_low > -0.01 else "fail"`). This is harmless because `evaluate_decision()` no longer uses it for gating — the bootstrap `GateCheck` is always `passed=True, severity="info"`. Changing the suite status was out of scope (would require touching bootstrap suite tests). |
| `summarize_block_grid().decision_pass` | UNCHANGED | The subsampling grid summary still computes `decision_pass`. The value is preserved in the gate dict for diagnostic consumption but the suite status is always "info". |
| `DecisionPolicy.bootstrap_p_threshold` / `bootstrap_ci_lower_min` | UNCHANGED | These fields still exist on the policy dataclass but are no longer referenced in the gate logic. Removing them would be a broader API cleanup. |
| Phase 5 wording cleanup | NOT IMPLEMENTED | Per task scope |
| `validation/suites/bootstrap.py` status logic | NOT MODIFIED | The suite's own status field was not in the Phase 3 plan scope. The critical change (removing veto from decision engine) is complete. |
