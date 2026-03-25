# Report 29 — Runner Orchestration E2E Audit

**Date**: 2026-03-04
**Scope**: `ValidationRunner.run()` end-to-end, exercised via stubbed harness
**Predecessors**: Report 27 (gate-level), Report 28 (runner-level isolation)

---

## 1. Objectives

Reports 27-28 proved gate and runner authority in isolation. This report proves
the same behaviors on the **real `run()` code path** — exercising the actual
orchestration loop with controlled fake suites and minimal stubs.

Specific goals:
1. WFO low-power auto-enable actually happens in `run()`
2. Early-abort / short-circuit behavior correct on real path
3. Final verdict precedence correct on real path
4. Output-contract double-write behavior proven end-to-end
5. Zero-authority suites still cannot veto on real path


## 2. Harness Design

### 2.1 What Was Stubbed

| Dependency | Stub | Reason |
|-----------|------|--------|
| `DataFeed` | `_Stub()` | Requires real CSV market data |
| `load_config` | `_Stub()` | Requires YAML with strategy schema |
| `_build_config_obj` | `_Stub()` | Requires strategy registry |
| `tracker_for_config_obj` | `_Stub()` | Requires real config objects |
| `make_factory` | `lambda: None` | Requires full strategy machinery |
| `load_raw_yaml` | `→ {}` | File I/O |
| `build_effective_config_payload` | `→ {}` | Requires live config objects |
| `build_usage_payloads` | Controllable via `set_usage()` | Requires real trackers |
| `build_effective_config_report` | `→ ""` | Requires real payloads |
| `build_score_decomposition_report` | `→ ""` | Requires backtest rows |
| `generate_validation_report` | Writes empty file | Heavy report generator |
| `generate_quality_checks_report` | Writes empty file | Heavy report generator |
| `discover_checks` | `→ {}` | File system scan |
| `get_git_hash` | `→ "test-hash"` | Git dependency |
| `stamp_run_meta` | No-op | Writes metadata |
| `_import_suite` | Returns `FakeSuite` classes | Avoids real suite imports |

### 2.2 What Remained Real

| Component | Lines | Why |
|-----------|-------|-----|
| Suite execution loop | 206-265 | **Core target** — queue iteration, error handling, break logic |
| WFO auto-enable check | 268-294 | Tests queue mutation, `cfg.auto_trade_level` |
| `evaluate_decision()` | 330 | Gate evaluation logic |
| `_apply_quality_policy()` | 331 | Quality override authority |
| `_apply_config_usage_policy()` | 332-336 | Config override authority |
| `_collect_decision_warnings()` | 337 | Warning aggregation |
| `_collect_decision_errors()` | 338 | Error aggregation |
| `write_decision_json()` | 345, 362 | Final JSON output |
| `write_index()` | 346, 365 | Index file output |
| `_verify_output_contract()` | 348-366 | Contract check + override |
| `copy_configs()` | 129 | Uses real (empty) YAML files in tmp_path |
| `write_json()`, `write_text()` | various | File I/O for configs, audit reports |

### 2.3 FakeSuite Mechanism

Each fake suite:
1. Records its name to `_suite_run_order` (execution order tracking)
2. Returns preset `SuiteResult` from `_suite_payloads` dict
3. Raises preset `Exception` if payload is an exception (crash simulation)
4. Writes placeholder output files so `_verify_output_contract` passes
5. Can be opted out of file writing via `_skip_output_write` set

Suite queue controlled by monkeypatching `resolve_suites`.


## 3. Execution-Order Proof

### 3.1 Observed Order (SC3: clean run)

```
Suite execution:  wfo → (done)
evaluate_decision() → PROMOTE(0)
_apply_quality_policy() → no issues → PROMOTE preserved
_apply_config_usage_policy() → no unused → PROMOTE preserved
_collect_decision_warnings() → warnings populated
_collect_decision_errors() → errors populated
write_decision_json() → reports/decision.json (first write)
_verify_output_contract() → all files present → no override
Final: PROMOTE(0) — decision.json matches in-memory verdict (PD3)
```

### 3.2 Observed Order (OC1: contract failure)

```
Suite execution:  backtest → (done, but output files NOT written)
evaluate_decision() → PROMOTE(0) with gates=[full_harsh_delta(passed=True)]
_apply_quality_policy() → no issues → PROMOTE preserved
_apply_config_usage_policy() → no unused → PROMOTE preserved
write_decision_json() → reports/decision.json (first write: PROMOTE with gates)
_verify_output_contract() → missing files detected
  → new DecisionVerdict(tag="ERROR", gates=[]) created
  → write_decision_json() OVERWRITES reports/decision.json (second write)
Final: ERROR(3) with gates=[] — proves overwrite occurred
```


## 4. WFO Auto-Enable Proof

### 4.1 Auto-Enable Fires (WFO1)

| Step | Observation |
|------|------------|
| Queue before WFO | `["wfo"]` |
| WFO result | `power_windows=1, low_trade_ratio=1.0` → `low_power=True` |
| Condition check | `low_power=True AND "trade_level" not in queue AND "trade_level" not in results` |
| Side effects | `cfg.auto_trade_level = True`, `suite_queue.append("trade_level")` |
| Queue after WFO | `["wfo", "trade_level"]` |
| Execution order | `["wfo", "trade_level"]` — trade_level actually ran |
| Final verdict | PROMOTE(0) — trade_level bootstrap healthy |

### 4.2 No Auto-Enable (WFO2)

| Step | Observation |
|------|------------|
| WFO result | `power_windows=10, low_trade_ratio=0.0` → `low_power=False` |
| Condition check | `low_power=False` → branch skipped entirely |
| `cfg.auto_trade_level` | `False` (unchanged) |
| Execution order | `["wfo"]` — no trade_level |

### 4.3 No Duplicate (WFO3)

| Step | Observation |
|------|------------|
| Queue before WFO | `["wfo", "trade_level"]` |
| WFO result | `low_power=True` |
| Condition check | `"trade_level" not in suite_queue` → **False** (already queued) |
| `cfg.auto_trade_level` | `False` (auto-enable branch skipped) |
| Execution order | `["wfo", "trade_level"]` — trade_level runs once |

**Note on `"trade_level" not in results` defense-in-depth**: In current code,
this check is always redundant with the queue check because items are never
removed from `suite_queue`. The results check guards against hypothetical
future code that might remove completed items from the queue.


## 5. Short-Circuit Proof

### 5.1 Data Integrity Hard Fail (SC1)

```
Queue: ["data_integrity", "wfo"]
data_integrity runs → status="fail", hard_fail=True
Runner: result.status == "fail" AND hard_fail → break
WFO: NEVER runs (not in _suite_run_order)
evaluate_decision: data_integrity hard_fail → ERROR(3) immediately
Final: ERROR(3)
```

**Proven**: Later suites are completely skipped. `"wfo" not in results`.

### 5.2 Suite Exception (SC2)

```
Queue: ["cost_sweep"]
cost_sweep.run() raises RuntimeError("engine crash")
Runner: catches Exception → results["cost_sweep"] = SuiteResult(status="error")
evaluate_decision: any status="error" → ERROR(3)
Final: ERROR(3), error_message preserved
```

**Proven**: Exception → status="error" → ERROR(3). No crash propagation.


## 6. Output-Contract E2E Proof

### 6.1 Double-Write Behavior (OC1)

**Setup**: backtest runs with status="pass" and `score_delta=0.5`, but output
files intentionally NOT written (`_skip_output_write={"backtest"}`).

| Event | decision.json content |
|-------|----------------------|
| Line 345 (first write) | `verdict="PROMOTE", gates=[{full_harsh_delta, passed=True}]` |
| Line 348 (_verify_output_contract) | Detects missing `full_backtest_summary.csv` etc. |
| Line 351-361 | **New** DecisionVerdict created: `tag="ERROR", gates=[]` |
| Line 362 (second write) | Overwrites: `verdict="ERROR", gates=[]` |
| Final on disk | `verdict="ERROR", exit_code=3, gates=[], failures=["missing: ..."]` |

### 6.2 Gates Lost — Intentional

The output contract creates a **new** `DecisionVerdict` that does not carry
forward the original `gates` list. This is intentional: when the pipeline is
incomplete (missing output files), gate-level analysis is moot.

**Preserved**: `warnings`, `errors` (merged), `key_links`, `deltas`
**Lost**: `gates`, `reasons` (replaced with contract failure reason)

### 6.3 Final JSON Shape (from OC1 assertion)

```json
{
  "verdict": "ERROR",
  "exit_code": 3,
  "gates": [],
  "failures": ["missing: results/full_backtest_summary.csv", ...],
  "reasons": ["Output contract verification failed"],
  "warnings": [...],
  "errors": ["missing: results/full_backtest_summary.csv", ...],
  "metadata": {"missing_count": 3}
}
```

### 6.4 When Write Happens Once vs Twice

| Condition | Writes |
|-----------|--------|
| Contract passes (all files present) | **Once** at line 345 |
| Contract fails (missing files) | **Twice**: line 345 (initial) + line 362 (overwrite) |


## 7. Zero-Authority Proof on Real Path

### 7.1 cost_sweep (ZA1)

```
cost_sweep.status = "fail"
evaluate_decision: no gate for cost_sweep → PROMOTE
_apply_quality_policy: only checks data_integrity, invariants, regression_guard → skip
_apply_config_usage_policy: no unused → skip
_collect_decision_warnings: "Cost sweep reported 1 issue(s)" added to warnings
Final: PROMOTE(0) with warnings only
```

**Proven**: `status="fail"` for zero-authority suite → no veto at any layer.

### 7.2 churn_metrics (ZA2)

Same behavior as ZA1. `status="fail"` → warnings only, PROMOTE(0).

### 7.3 Crash vs Fail Distinction

- `status="fail"`: No veto for zero-authority suites (ZA1, ZA2)
- `status="error"` (crash): ERROR(3) for ALL suites including zero-authority (SC2)

This is correct: a crash indicates infrastructure failure, not a policy decision.


## 8. Precedence on Real Path

| Test | Starting | Policy Trigger | Final | Downgrade? |
|------|----------|---------------|-------|------------|
| PD1 | PROMOTE(0) | quality: data_integrity soft-fail | ERROR(3) | No (elevated) |
| PD2 | PROMOTE(0) | config: unused fields | ERROR(3) | No (elevated) |
| PD4 | PROMOTE(0) | quality + config both | ERROR(3) | No (elevated) |
| PD5 | REJECT(2) | none (clean policies) | REJECT(2) | No (preserved) |
| SC2 | ERROR(3) | none (from evaluate_decision) | ERROR(3) | No (preserved) |
| SC3 | PROMOTE(0) | none (clean) | PROMOTE(0) | N/A (no change) |

**Proven on real path**: No runner policy can downgrade the verdict.


## 9. Files Changed

### Code Changes
None. No bugs or fail-open paths found.

### Test Changes
| File | Tests | New? |
|------|-------|------|
| `validation/tests/test_runner_run_loop_e2e.py` | 14 | Yes |

### Doc Changes
| File | New? |
|------|------|
| `research_reports/29_runner_orchestration_e2e_audit.md` | Yes |

## 10. Behavior Changes

**No.** No production code was modified. All 14 tests pass against unmodified code.


## 11. Test Coverage Summary

| ID | Test | Category | Assert |
|----|------|----------|--------|
| WFO1 | `test_wfo_low_power_auto_enables_trade_level` | WFO auto-enable | trade_level appended, runs, cfg set |
| WFO2 | `test_wfo_normal_power_no_auto_enable` | WFO auto-enable | trade_level NOT appended |
| WFO3 | `test_no_duplicate_when_trade_level_already_queued` | WFO auto-enable | no duplicate, count==1 |
| SC1 | `test_data_integrity_hard_fail_aborts_remaining_suites` | Short-circuit | wfo NOT in results |
| SC2 | `test_suite_exception_becomes_error_result` | Short-circuit | status="error", ERROR(3) |
| SC3 | `test_clean_run_all_suites_complete` | Baseline | all ran, PROMOTE(0) |
| OC1 | `test_output_contract_failure_produces_error_and_overwrites` | Output contract | ERROR(3), gates=[], overwrite |
| ZA1 | `test_advisory_suite_fail_does_not_veto` | Zero-authority | PROMOTE(0), warnings only |
| ZA2 | `test_churn_fail_does_not_veto` | Zero-authority | PROMOTE(0), no veto |
| PD1 | `test_quality_policy_elevates_on_real_run_path` | Precedence | PROMOTE→ERROR via quality |
| PD2 | `test_config_usage_policy_elevates_on_real_run_path` | Precedence | PROMOTE→ERROR via config |
| PD3 | `test_decision_json_matches_returned_verdict` | Consistency | JSON == in-memory verdict |
| PD4 | `test_both_policies_cumulate_on_real_path` | Precedence | both sources in failures |
| PD5 | `test_reject_not_downgraded_on_real_path` | Precedence | REJECT stays REJECT |


## 12. Remaining Unresolved Risks

1. **WFO auto-enable `"trade_level" not in results` check**: This defense-in-depth
   condition is unreachable in current code because `suite_queue` items are never
   removed. If future code removes completed items from the queue, this check becomes
   the sole guard. Low risk — the check exists and is correct.

2. **Output contract gate loss**: When the contract fails, the final `decision.json`
   loses the `gates` list. This is documented and intentional (§6.2). Any downstream
   consumer that expects gates in an ERROR verdict should handle the empty case.

3. **Full end-to-end with real data**: The stubbed harness cannot test suite-to-suite
   data flow (e.g., backtest results feeding into WFO). This requires the full pipeline
   with real market data and is covered by the existing acceptance tests
   (`test_acceptance.py`).


## Appendix A: Harness Architecture

```
┌─────────────────────────────────────────────────┐
│  ValidationRunner.run()  (REAL)                  │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │FakeSuite │  │FakeSuite │  │FakeSuite │ ...   │
│  │(wfo)     │  │(trade_   │  │(backtest)│       │
│  │→preset   │  │ level)   │  │→preset   │       │
│  │ result   │  │→preset   │  │ result   │       │
│  └──────────┘  └──────────┘  └──────────┘       │
│         ↓                                        │
│  evaluate_decision()          (REAL)             │
│         ↓                                        │
│  _apply_quality_policy()      (REAL)             │
│  _apply_config_usage_policy() (REAL)             │
│         ↓                                        │
│  write_decision_json()        (REAL)             │
│  _verify_output_contract()    (REAL)             │
│         ↓                                        │
│  Final decision.json on disk                     │
└─────────────────────────────────────────────────┘
```

## Appendix B: Test Files (Cumulative from Reports 27-29)

| File | Tests | Scope |
|------|-------|-------|
| `validation/tests/test_decision_authority.py` | 12 | Gate-level authority (Report 27) |
| `validation/tests/test_runner_authority.py` | 33 | Runner-level isolation (Report 28) |
| `validation/tests/test_runner_run_loop_e2e.py` | 14 | E2E orchestration (Report 29) |
| `validation/tests/test_decision_payload.py` | 2 | Warning/error payload |
| `validation/tests/test_inference_role_semantics.py` | 20 | Bootstrap/subsampling info-only |
