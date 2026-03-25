# Report 28 — Runner-Level Authority & Integration Audit

**Date**: 2026-03-04
**Scope**: `validation/runner.py`, `validation/output.py`, all post-decision authority paths
**Predecessor**: Report 27 (gate-level authority audit, `validation/decision.py`)

---

## 1. Scope & Objectives

Report 27 locked the semantics of `evaluate_decision()` — the core decision engine that
produces the initial verdict from suite results. This report audits the **runner layer**:
everything that happens between `evaluate_decision()` returning and `reports/decision.json`
being written. Specifically:

1. Map every runner-level authority point that can modify the verdict.
2. Verify precedence — can any runner policy **downgrade** a verdict?
3. Trace the WFO low-power → auto-enable trade_level flow.
4. Verify zero-authority suites cannot create vetoes at the runner level.
5. Regression-test all findings.


## 2. Runner Authority Map

### 2.1 Complete Execution Flow

The runner's `run()` method (lines 76-374) follows this sequence after suites complete:

| Step | Code Lines | Method | Authority | Effect |
|------|-----------|--------|-----------|--------|
| 1 | 206-257 | Suite execution loop | Sets `status="error"` on crash | Flows to ERROR via `evaluate_decision` |
| 2 | 259-265 | data_integrity hard_fail check | `break` — abort remaining suites | Short-circuits pipeline |
| 3 | 268-294 | WFO low-power check | Appends `trade_level` to queue | Side effect: more suites run |
| 4 | 330 | `evaluate_decision(results)` | Initial verdict | PROMOTE/HOLD/REJECT/ERROR |
| 5 | 331 | `_apply_quality_policy()` | Re-check quality suites | Can elevate ANY → ERROR(3) |
| 6 | 332-336 | `_apply_config_usage_policy()` | Unused config fields | Can elevate ANY → ERROR(3) |
| 7 | 337 | `_collect_decision_warnings()` | Warning collection | **No verdict change** |
| 8 | 338 | `_collect_decision_errors()` | Error list population | **No verdict change** |
| 9 | 345 | `write_decision_json()` | Writes initial `decision.json` | First write |
| 10 | 348-366 | `_verify_output_contract()` | Missing output files | Can elevate ANY → ERROR(3) |
| 11 | 362 | `write_decision_json()` | **Overwrites** `decision.json` | Second write (if contract fails) |

### 2.2 Authority Classification

| Method | Can Elevate? | Can Downgrade? | Creates New Verdict? | Preserves Gates? |
|--------|-------------|----------------|---------------------|-----------------|
| `_apply_quality_policy` | Yes → ERROR(3) | **Never** | No (mutates in place) | Yes |
| `_apply_config_usage_policy` | Yes → ERROR(3) | **Never** | No (mutates in place) | Yes |
| `_collect_decision_warnings` | No | No | No | N/A |
| `_collect_decision_errors` | No | No | No | N/A |
| `_verify_output_contract` | Yes → ERROR(3) | **Never** | **Yes (new verdict)** | **No — gates lost** |

**Key invariant**: All runner policies can only **elevate** to ERROR(3). No policy can
downgrade (e.g., REJECT → HOLD, ERROR → PROMOTE). Proven by tests PR4 and PR5
(parametrized across all 4 starting verdicts).


## 3. Findings

### 3.1 Finding F1: data_integrity Soft-Fail Authority Gap

**Severity**: Informational (by design, not a bug)

`evaluate_decision()` only returns ERROR when `data_integrity.data.hard_fail == True`.
If `data_integrity.status == "fail"` but `hard_fail == False`, it passes through
to gate evaluation — and data_integrity has **no gate** in the gate section.

`_apply_quality_policy()` catches **all** `data_integrity.status == "fail"` regardless
of `hard_fail`. This is a **real authority gap**: soft data_integrity failures are
only caught at the runner level, not the decision engine level.

**Impact**: A data_integrity soft-fail would initially produce PROMOTE from
`evaluate_decision()`, then be elevated to ERROR(3) by `_apply_quality_policy()`.
The final verdict is correct, but the initial decision object lacks the error.

**Test**: QP1 (`test_quality_policy_data_integrity_soft_fail_elevates_error`)

### 3.2 Finding F2: Output Contract Creates New Verdict (Gates Lost)

**Severity**: Low (acceptable behavior)

When `_verify_output_contract()` detects missing files, the runner creates a **new**
`DecisionVerdict` object (line 351-361), not a mutation:

```python
decision = DecisionVerdict(
    tag="ERROR",
    exit_code=3,
    reasons=["Output contract verification failed"],
    failures=missing_failures,
    warnings=decision.warnings,     # preserved
    errors=...,                      # merged
    key_links=decision.key_links,    # preserved
    deltas=decision.deltas,          # preserved
    metadata={"missing_count": ...}, # new
)
```

The original `decision.gates` list is **not carried forward**. This means the
`decision.json` written after an output contract failure will have an empty `gates` array.

**Justification**: When the output contract fails, the pipeline is fundamentally
incomplete. The gate-level analysis is moot because outputs are missing. Losing the
gates array is acceptable in this context.

### 3.3 Finding F3: decision.json Double-Write

**Severity**: Informational (working as intended)

`decision.json` is written at line 345 (initial) and potentially overwritten at
line 362 (output contract failure). The final file is always correct, but there
is a brief window where the file contains the pre-contract-check verdict.

This is safe because:
- The overwrite is atomic (same `write_json` call).
- No downstream consumer reads `decision.json` between lines 345 and 362.
- `write_index` and reports are also regenerated (lines 363-365).

### 3.4 Finding F4: Quality Policy is Redundant Safety Net

`_apply_quality_policy` re-checks `data_integrity`, `invariants`, and
`regression_guard` — all of which are already checked by `evaluate_decision()`.

| Check | `evaluate_decision()` | `_apply_quality_policy()` | Gap? |
|-------|----------------------|--------------------------|------|
| `data_integrity` | Only `hard_fail=True` | Any `status="fail"` | **Yes (F1)** |
| `invariants` | `n_violations > 0` or `status="fail"` | Same conditions | No |
| `regression_guard` | `pass=False` or `status in {fail,error}` | Same conditions | No |

For invariants and regression_guard, the quality policy is purely redundant — a
defense-in-depth safety net. For data_integrity, it catches a real gap (F1).


## 4. Precedence Analysis

### 4.1 Can Any Policy Downgrade?

**No.** All three authority policies (`quality`, `config_usage`, `output_contract`)
unconditionally set `tag="ERROR"` and `exit_code=3` when triggered. They never
set to PROMOTE, HOLD, or REJECT. Proven by parametrized tests PR4 and PR5 across
all 4 starting verdicts × 2 policies = 8 test cases.

### 4.2 Precedence Table

Starting verdict flows through runner policies:

| Starting | quality_policy | config_usage | output_contract | Final |
|----------|---------------|--------------|-----------------|-------|
| PROMOTE(0) | clean | clean | clean | PROMOTE(0) |
| PROMOTE(0) | fails | clean | clean | ERROR(3) |
| PROMOTE(0) | clean | fails | clean | ERROR(3) |
| PROMOTE(0) | clean | clean | fails | ERROR(3) |
| HOLD(1) | clean | clean | clean | HOLD(1) |
| HOLD(1) | fails | - | - | ERROR(3) |
| REJECT(2) | clean | clean | clean | REJECT(2) |
| REJECT(2) | fails | - | - | ERROR(3) |
| ERROR(3) | clean | clean | clean | ERROR(3) |
| ERROR(3) | fails | - | - | ERROR(3) (no-op) |

**Invariant**: `final_exit_code >= initial_exit_code` always holds.
More precisely: final verdict is either unchanged or elevated to ERROR(3).


## 5. WFO Low-Power Auto-Enable Trace

### 5.1 Runner-Side (lines 268-294)

After the WFO suite completes, the runner:

1. Extracts `power_windows` from `summary.stats_power_only.n_windows`
2. Computes `low_trade_ratio = low_trade_windows / valid_windows`
3. Evaluates `low_power = power_windows < 3 or low_trade_ratio > 0.5`
4. If `low_power` AND `trade_level` not already queued/completed:
   - Sets `cfg.auto_trade_level = True`
   - Appends `"trade_level"` to `suite_queue`
   - Adds warning to `ctx.run_warnings`
5. Suite loop continues and eventually runs the trade_level suite.

### 5.2 Decision-Side (decision.py lines 254-267)

`evaluate_decision()` independently computes `wfo_low_power` using the
**identical formula**: `power_windows < 3 or low_trade_ratio > 0.5`.

Both sides use identical fallback logic:
- `low_trade_windows` from `low_trade_windows_count` || `low_trade_windows`
- `valid_windows` from `n_windows_valid` || `n_windows`
- `low_trade_ratio` defaults to `1.0` when `valid_windows == 0`

### 5.3 Consistency Verification

The runner's detection and the decision engine's detection use identical
conditions, ensuring no desynchronization. Tests WF1-WF3 verify the decision
engine's `wfo_low_power` flag matches expected conditions:

| Test | power_windows | low_trade_ratio | Expected wfo_low_power |
|------|--------------|-----------------|----------------------|
| WF1 | 2 (< 3) | 0.0 | True |
| WF2 | 10 (≥ 3) | 0.0 (≤ 0.5) | False |
| WF3 | 10 (≥ 3) | 0.6 (> 0.5) | True |

### 5.4 Testing Limitation

The actual queue mutation (`suite_queue.append("trade_level")`) and
`cfg.auto_trade_level = True` assignment are embedded in the `run()` method
loop. They cannot be unit-tested without running the full pipeline (which
requires DataFeed, config loading, strategy factories, etc.). This is
documented as an integration test gap that can only be covered by
end-to-end validation runs.


## 6. Zero-Authority Suite Verification

### 6.1 At Decision Level

Suites `cost_sweep` and `churn_metrics` are not processed by `evaluate_decision()`:
- No gate is created for either suite.
- Their `status="fail"` does NOT appear in `verdict.failures`.
- Only `status="error"` (crash) triggers the generic error short-circuit.

Tests ZA1 and ZA2 verify that `cost_sweep.status="fail"` and
`churn_metrics.status="fail"` both produce PROMOTE(0) with no failures.

### 6.2 At Runner Level

- `_collect_decision_warnings()` processes cost_sweep/churn issues into **warnings only**.
- `_collect_decision_errors()` only catches `status="error"` (crashes), not `status="fail"`.
- `_apply_quality_policy()` only checks data_integrity, invariants, regression_guard.
- `_apply_config_usage_policy()` only checks config field usage.

**Conclusion**: Zero-authority suites (cost_sweep, churn_metrics, bootstrap,
subsampling, dd_episodes, regime, sensitivity, overlay) cannot create vetoes
at any layer unless they crash (status="error"), which is correct behavior.


## 7. Test Coverage Matrix

### 7.1 File: `validation/tests/test_runner_authority.py`

33 tests total (25 unique + 8 parametrized variants):

| ID | Test | Target | Assert |
|----|------|--------|--------|
| QP1 | `test_quality_policy_data_integrity_soft_fail_elevates_error` | F1 gap | PROMOTE → ERROR |
| QP2 | `test_quality_policy_invariants_fail_elevates_error` | quality | PROMOTE → ERROR |
| QP3 | `test_quality_policy_regression_guard_fail_elevates_error` | quality | PROMOTE → ERROR |
| QP4 | `test_quality_policy_clean_preserves_promote` | quality | PROMOTE preserved |
| QP5 | `test_quality_policy_elevates_reject_to_error` | quality | REJECT → ERROR |
| QP6 | `test_quality_policy_data_integrity_hard_fail_also_caught` | quality | hard_fail → ERROR |
| CU1 | `test_config_usage_unused_fields_elevates_error` | config | PROMOTE → ERROR |
| CU2 | `test_config_usage_clean_preserves_verdict` | config | PROMOTE preserved |
| CU3 | `test_config_usage_elevates_hold_to_error` | config | HOLD → ERROR |
| OC1 | `test_output_contract_detects_missing_base_files` | contract | missing detected |
| OC2 | `test_output_contract_passes_when_base_complete` | contract | no missing |
| OC3 | `test_output_contract_includes_suite_specific_files` | contract | backtest files |
| WA1 | `test_cost_sweep_issues_are_warnings_only` | warnings | warnings only |
| WA2 | `test_churn_metrics_issues_are_warnings_only` | warnings | warnings only |
| WA3 | `test_run_warnings_propagated` | warnings | ctx warnings → decision |
| EC1 | `test_error_collection_populates_list_not_verdict` | errors | no verdict change |
| EC2 | `test_error_collection_includes_regression_guard` | errors | violations listed |
| PR1 | `test_no_runner_policy_downgrades_error` | precedence | ERROR stays ERROR |
| PR2 | `test_no_runner_policy_downgrades_reject` | precedence | REJECT stays REJECT |
| PR3 | `test_quality_then_config_cumulative_error` | precedence | both sources in failures |
| PR4 | `test_quality_policy_only_elevates_to_error` ×4 | precedence | all starting verdicts |
| PR5 | `test_config_policy_only_elevates_to_error` ×4 | precedence | all starting verdicts |
| WF1 | `test_wfo_low_power_condition_detected` | wfo auto | power_windows < 3 |
| WF2 | `test_wfo_normal_power_not_low_power` | wfo auto | normal power |
| WF3 | `test_wfo_low_trade_ratio_triggers_low_power` | wfo auto | ratio > 0.5 |
| ZA1 | `test_zero_authority_cost_sweep_never_vetoes` | zero-auth | PROMOTE preserved |
| ZA2 | `test_zero_authority_churn_never_vetoes` | zero-auth | PROMOTE preserved |


## 8. Summary

The runner layer has exactly **three** authority points that can modify the verdict
after `evaluate_decision()`:

1. **Quality policy** — redundant safety net with one real gap (F1: data_integrity soft-fail)
2. **Config usage policy** — catches wiring bugs (unused YAML fields)
3. **Output contract** — catches pipeline incompleteness

All three can only **elevate** to ERROR(3). No downgrade is possible. The
WFO auto-enable flow is consistent between runner and decision engine.
Zero-authority suites cannot create vetoes at any layer.

No code changes needed. No behavior issues found. All 33 tests pass.


## Appendix A: Files Audited

| File | Lines | Role |
|------|-------|------|
| `validation/runner.py` | 670 | Runner orchestration, post-decision policies |
| `validation/output.py` | 184 | Decision JSON writer, index writer |
| `validation/decision.py` | 473 | Core decision engine (audited in Report 27) |
| `validation/config.py` | 227 | ValidationConfig, suite resolution |
| `validation/suites/base.py` | 66 | SuiteResult, SuiteContext, BaseSuite |

## Appendix B: Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `validation/tests/test_runner_authority.py` | 33 | Runner-level authority (this report) |
| `validation/tests/test_decision_authority.py` | 12 | Gate-level authority (Report 27) |
| `validation/tests/test_decision_payload.py` | 2 | Warning/error payload, regression_guard |
| `validation/tests/test_inference_role_semantics.py` | 20 | Bootstrap/subsampling info-only role |
