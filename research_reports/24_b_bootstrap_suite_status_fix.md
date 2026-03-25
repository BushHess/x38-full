# Report 24B — Bootstrap Suite Status Semantic Leak Fix

**Date**: 2026-03-03
**Canonical plan**: `research_reports/22_b_inference_patch_plan.md`
**Scope**: Fix remaining semantic leak in `BootstrapSuite.run()` status field + tighten role-semantic tests

---

## 1. Problem Statement

After Phase 3A (Report 24) retired the bootstrap gate's veto power in `validation/decision.py`, a semantic leak remained: the `BootstrapSuite.run()` method in `validation/suites/bootstrap.py` still computed a `pass`/`fail` status at lines 100–105:

```python
if not gate:
    status = "info"
else:
    p = float(gate.get("p_candidate_better") or 0.0)
    ci_low = float(gate.get("ci_lower") or 0.0)
    status = "pass" if p >= 0.80 and ci_low > -0.01 else "fail"
```

While no downstream consumer used this status for decision-making (the decision engine only checks `!= "skip"`), the presence of pass/fail:
1. Contradicts the diagnostic-only role established in Reports 21, 22B, 24
2. Could mislead future consumers into treating bootstrap as a gate
3. Is inconsistent with the subsampling suite (already changed to `status = "info"` in Phase 3B)

---

## 2. Touched Files

| File | Change type |
|------|------------|
| `validation/suites/bootstrap.py` | Suite status → always "info" |
| `validation/tests/test_inference_role_semantics.py` | +4 new tests, 2 strengthened assertions, helper updated |

---

## 3. Behavior Changed

### 3A: Bootstrap suite status → info in `validation/suites/bootstrap.py`

**Before** (lines 100–105):
```python
if not gate:
    status = "info"
else:
    p = float(gate.get("p_candidate_better") or 0.0)
    ci_low = float(gate.get("ci_lower") or 0.0)
    status = "pass" if p >= 0.80 and ci_low > -0.01 else "fail"
```

**After**:
```python
# Bootstrap is a DIAGNOSTIC, not a gate (Report 21, §1.1; Report 22B, Phase 3).
# Gate dict is still populated for diagnostic consumption, but status is always "info".
status = "info"
```

### 3B: Downstream consumer audit

Two downstream consumers check bootstrap status — neither relies on pass/fail:

| Consumer | File | Check | Impact |
|----------|------|-------|--------|
| Decision engine | `validation/decision.py:303` | `status not in {"skip"}` | None — "info" is not "skip" |
| Artifact validator | `validation/runner.py:418` | `status != "skip"` | None — "info" is not "skip" |

### 3C: Test helper updated

`_make_bootstrap_suite_result()` in `test_inference_role_semantics.py`:
- `status="pass"` → `status="info"` (line 60)

### 3D: T5/T6 assertions strengthened

| Test | Before | After |
|------|--------|-------|
| `test_negative_control_not_blocked` (T5) | `assert verdict.tag != "REJECT"` | `assert verdict.tag == "PROMOTE"` + `assert verdict.exit_code == 0` |
| `test_strong_positive_not_blocked` (T6) | `assert verdict.tag != "REJECT"` | `assert verdict.tag == "PROMOTE"` + `assert verdict.exit_code == 0` |

Rationale: Both tests use only diagnostic suites (bootstrap + subsampling). With no hard/soft gates, the verdict must be PROMOTE. Asserting the exact expected outcome is stronger than asserting the absence of one bad outcome.

---

## 4. Diagnostic Fields Preserved

All diagnostic fields remain unchanged from Report 24:

| Field | Status |
|-------|--------|
| `gate` dict (p_candidate_better, ci_lower, ci_upper, observed_delta) | **PRESERVED** |
| `rows` (per-scenario/block-size detail) | **PRESERVED** |
| `summary` (n_rows, bootstrap, seed, gate) | **PRESERVED** |
| Bootstrap artifacts (CSV, JSON) | **PRESERVED** |

---

## 5. Tests Added/Updated

### New tests in `TestBootstrapSuiteStatus` class:

| Test method | What it verifies |
|-------------|-----------------|
| `test_bootstrap_suite_status_is_info_with_gate` | Status is "info" when gate dict is populated |
| `test_bootstrap_suite_status_is_info_without_gate` | Status is "info" when gate dict is empty |
| `test_bootstrap_suite_status_never_pass_or_fail` | Status is "info" for both would-be-pass and would-be-fail gate values |
| `test_bootstrap_suite_gate_data_preserved` | Gate dict retains all diagnostic values after status change |

### Updated tests:

| Test method | Change |
|-------------|--------|
| `test_negative_control_not_blocked` (T5) | `!= "REJECT"` → `== "PROMOTE"` + exit_code check |
| `test_strong_positive_not_blocked` (T6) | `!= "REJECT"` → `== "PROMOTE"` + exit_code check |
| `_make_bootstrap_suite_result` helper | `status="pass"` → `status="info"` |

---

## 6. Exact Test Count

| File | New tests | Updated tests |
|------|-----------|--------------|
| `validation/tests/test_inference_role_semantics.py` | **4** | **2** (T5, T6 strengthened) |

Total test count in file: **20** (was 16 from Report 24, +4 new).

---

## 7. Regression Results

```
436 passed, 0 failed, 34 warnings in 83.58s
```

All warnings are pre-existing (numpy divide-by-zero in v8_apex/v11_hybrid strategies).

---

## 8. Consistency Audit — All Three Layers Now Aligned

| Layer | File | Status value | Gate role |
|-------|------|-------------|-----------|
| Suite (bootstrap) | `validation/suites/bootstrap.py` | `"info"` always | Diagnostic |
| Suite (subsampling) | `validation/suites/subsampling.py` | `"info"` always | Diagnostic |
| Decision engine | `validation/decision.py` | `severity="info"`, `passed=True` | Diagnostic |

The semantic leak is fully closed. Bootstrap and subsampling are diagnostic-only at every layer.

---

## 9. Known Limitations Intentionally Unchanged

| Item | Status | Reason |
|------|--------|--------|
| `DecisionPolicy.bootstrap_p_threshold` / `bootstrap_ci_lower_min` | UNCHANGED | Fields still exist on policy dataclass but are unreferenced. Removing = broader API cleanup. |
| `summarize_block_grid().decision_pass` | UNCHANGED | Subsampling grid still computes `decision_pass` for diagnostic consumption. |
| Phase 5 wording cleanup | NOT IMPLEMENTED | Per task scope |
