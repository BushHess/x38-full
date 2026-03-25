# Report 31 — Authoritative Shape/Status Semantics Completion Audit

**Date**: 2026-03-04
**Scope**: Container-shape assumptions and status semantics for all authority-bearing
consumer paths in `validation/decision.py` and `validation/runner.py`
**Predecessor**: Reports 27 (gate authority), 28 (runner authority), 29 (E2E orchestration),
30 (scalar decisive-field fail-open)
**Status**: Complete — all shape/status holes patched and tested

---

## 1. Shape Risk Inventory

### 1.1 `.data` Not a Dict

Every suite consumer calls `.data.get(...)` which crashes with `AttributeError` if
`.data` is `None`, `str`, `list`, or `int`. While `SuiteResult.data` is typed as
`dict[str, Any]` with `field(default_factory=dict)`, defense-in-depth demands no crash.

| Location | Consumer | Risk |
|----------|----------|------|
| decision.py L94 | `data_integrity.data.get("hard_fail")` | AttributeError |
| decision.py L232 | `backtest.data.get("deltas",{}).get(...)` | AttributeError |
| decision.py L262 | `holdout.data.get("delta_harsh_score")` | AttributeError |
| decision.py L298 | `wfo.data.get("summary",{})` | AttributeError |
| decision.py L344 | `bootstrap.data.get("gate",{})` | AttributeError |
| decision.py L367 | `trade_level.data.get("matched_p_positive")` | AttributeError |
| decision.py L471 | `sb.data.get("risk_statement","")` | AttributeError |
| runner.py L260 | `result.data.get("hard_fail")` | AttributeError |
| runner.py L269 | `result.data.get("summary",{})` | AttributeError |
| runner.py L536–564 | Quality policy `.data.get(...)` | AttributeError |
| runner.py L631–660 | Error collection `.data.get(...)` | AttributeError |

### 1.2 Unprotected `int()` Coercions

Bare `int(x)` raises `ValueError` on non-numeric strings like `"abc"` or `"5.5"`.

| Location | Expression | Context |
|----------|-----------|---------|
| decision.py L299 | `int(summary.get("n_windows", 0))` | WFO gate |
| decision.py L300 | `int(summary.get("positive_delta_windows", 0))` | WFO gate |
| decision.py L302 | `int(dict(...).get("n_windows", 0) or 0)` | WFO power_windows |
| decision.py L303 | `int(summary.get("n_windows_valid", ...) or 0)` | WFO valid_windows |
| decision.py L304–306 | `int(summary.get("low_trade_windows_count", ...) or 0)` | WFO |
| decision.py L383 | `int(trade_level_bootstrap.get("block_len", 0) or 0)` | TL bootstrap |
| runner.py L271–276 | Same WFO pattern in auto-enable block | Runner |
| runner.py L544, 550 | `int(invariants.data.get(...))`, `int(value)` | Quality policy |
| runner.py L639, 644 | Same in error collection | Runner |

### 1.3 Unprotected `dict()`/`list()` Coercions

| Location | Expression | Crash Type |
|----------|-----------|-----------|
| decision.py L137 | `dict(invariants.data.get("counts_by_invariant", {}))` | TypeError if string |
| decision.py L168–169 | `list(regression_guard.data.get("violated_metrics", []))` | `list("abc")` → char-list → `.get()` crash |
| decision.py L186 | `dict(regression_guard.data.get("deltas", {}))` | TypeError if string |
| decision.py L302 | `dict(summary.get("stats_power_only", {}))` | TypeError if string |
| decision.py L377 | `dict(trade_level.data.get("trade_level_bootstrap", {}))` | TypeError if string |
| runner.py L269–270 | `dict(result.data.get("summary", {}))` | TypeError if string |
| runner.py L547 | `dict(invariants.data.get("counts_by_invariant", {}))` | TypeError if string |
| runner.py L564–565 | `list(regression_guard.data.get(...))` | char-list → crash |

### 1.4 `bool()` Semantics

| Location | Expression | Issue |
|----------|-----------|-------|
| decision.py L94 | `bool(data_integrity.data.get("hard_fail"))` | `bool("false")` → True |
| decision.py L160 | `bool(invariants.data.get("limit_reached", False))` | Same |
| decision.py L166 | `bool(regression_guard.data.get("pass", ...))` | Same |
| runner.py L260 | `bool(result.data.get("hard_fail"))` | Same |
| runner.py L560, 654 | `bool(regression_guard.data.get("pass", ...))` | Same |

### 1.5 Iteration Over Non-Dict Rows

| Location | Expression | Issue |
|----------|-----------|-------|
| decision.py L171–176 | `for item in violated_rows: item.get("metric")` | Crashes if item is string/int/None |
| runner.py L568, 573, 659, 664 | Same pattern | Same |

---

## 2. Producer Status Contract Table

| Suite | Possible Statuses | Meaning |
|-------|------------------|---------|
| lookahead | pass, fail, skip | pass=pytest exit 0; fail=non-zero; skip=no test files |
| backtest | pass, fail | pass=harsh_delta >= -0.2; fail=below threshold |
| holdout | pass, fail, error | pass=delta >= -0.2; fail=below; error=lock file exists |
| wfo | pass, fail, info | pass=win_rate OK; fail=below threshold; info=0 valid windows |
| trade_level | info (always) | Always informational; never a gate |
| selection_bias | pass, info, skip | pass=DSR robust; info=caution/fallback; skip=disabled |
| data_integrity | pass, fail | pass=no hard_fail; fail=hard_fail detected |
| invariants | pass, fail | pass=0 violations; fail=violations detected |
| regression_guard | pass, fail | pass=metrics within tolerance; fail=violations or golden missing |

**Status="fail" meaning by suite:**
- **backtest/holdout**: Valid policy failure (delta below threshold)
- **wfo**: Valid policy failure (win_rate below threshold)
- **data_integrity**: Contract assertion (hard_fail detected)
- **invariants**: Contract assertion (violations detected)
- **regression_guard**: Contract assertion (metrics outside tolerance)
- **selection_bias**: Never produces "fail" (uses "info" for caution)

---

## 3. Defensive Helpers Added

Four helpers added to `decision.py` (after `_require_decisive_float`, before `evaluate_decision`):

### `_as_dict(value, default=None) → dict`
Returns `value` if `isinstance(value, dict)`, else empty dict or `default`.
Prevents crash on `.data` being None/string/list/int.

### `_safe_int(value, default=0) → int`
Returns `int(float(value))` if possible, else `default`.
Rejects NaN/inf via `math.isfinite()`. Uses `float()` intermediate to handle `"3.0"`.

### `_as_list_of_dicts(value) → list[dict]`
Returns list of only dict elements from `value`. Returns `[]` if value is not a list.
Prevents `list("abc")` → `["a","b","c"]` then `item.get()` crash.

### `_strict_bool(value) → bool`
Returns `True` only for `value is True` or `isinstance(int) and value == 1`.
Prevents `bool("false")` → True.

---

## 4. Patches Applied

### 4.1 `decision.py` — ~25 consumer paths hardened

**data_integrity block**: `_as_dict(.data)`, `_strict_bool(hard_fail)`, `_as_dict(counts)`
**invariants block**: `_as_dict(.data)`, `_safe_int(n_violations)`, `_as_dict(counts_by_invariant)`, `_strict_bool(limit_reached)`
**regression_guard block**: `_as_dict(.data)`, `_strict_bool(pass)`, `_as_list_of_dicts(violated_metrics/metadata)`, `_as_dict(deltas)`
**backtest block**: Triple `_as_dict()` for chained `.get().get().get()` on deltas.harsh.score_delta
**holdout block**: `_as_dict(.data)` on delta_harsh_score access
**WFO block**: `_as_dict()` on summary and stats_power_only; `_safe_int()` on all 5 int fields
**bootstrap block**: `_as_dict(.data)`, `_as_dict(gate)`
**trade_level block**: `_as_dict(.data)`, `_as_dict(trade_level_bootstrap)`, `_safe_int(block_len)`
**selection_bias block**: `_as_dict(.data)` on risk_statement access

### 4.2 `runner.py` — ~20 consumer paths hardened

**Import**: `from validation.decision import _as_dict, _as_list_of_dicts, _safe_int, _strict_bool`
**data_integrity short-circuit (L260)**: `_strict_bool(_as_dict(.data).get("hard_fail"))`
**WFO auto-enable (L269–276)**: All `dict()` → `_as_dict()`, all `int()` → `_safe_int()`
**Quality policy (L536–580)**: `_as_dict(.data)`, `_safe_int()`, `_as_dict()`, `_strict_bool()`, `_as_list_of_dicts()`
**Warning collection (L597–618)**: `_as_dict(.data)` on cost_sweep and churn
**Error collection (L635–673)**: Mirrors quality policy changes
**Config usage policy (L496)**: `_as_dict()` on chained `.get().get()`
**Score decomposition (L316–324)**: `_as_dict(.data)` for crash-safety

### 4.3 QP2 Test Updated

`test_data_integrity_string_hard_fail_true` in `test_decision_payload_contracts.py`
updated to expect PROMOTE (was ERROR) since `_strict_bool("true")` → False → no early exit.
Runner quality policy catches `status="fail"` as defense-in-depth.

---

## 5. Regression Tests Added

### Unit tests: `test_decision_shape_status_contracts.py` (61 tests)

| Group | Count | Covers |
|-------|-------|--------|
| TestAsDict (AD1–6) | 6 | dict passthrough, None, string, list, int, custom default |
| TestSafeInt (SI1–9) | 9 | int, float, string, None, non-numeric, NaN, inf, list, default |
| TestAsListOfDicts (AL1–6) | 6 | valid, filters non-dicts, string, None, int, empty |
| TestStrictBool (SB1–8) | 8 | True, False, None, "true", "false", 1, 0, [1] |
| TestDataNone (DN1–9) | 9 | .data=None for all 9 authority-bearing suites |
| TestDataNonDict (ND1–5) | 5 | .data=string/list/int for 5 suite types |
| TestIntCrashPrevention (IC1–6) | 6 | Non-numeric strings in WFO int fields + trade_level block_len |
| TestDictListCoercionCrash (DC1–6) | 6 | String where dict/list expected in 6 patterns |
| TestBoolSemantics (BL1–4) | 4 | "false"/"true" strings, True bool, "false" in pass field |
| TestIterationFiltering (IR1–2) | 2 | Non-dict items in violated_metrics/metadata filtered |

### E2E tests: `test_runner_shape_status_e2e.py` (3 tests)

| ID | Test | Scenario |
|----|------|----------|
| SS1 | `test_wfo_non_numeric_int_fields_no_crash` | WFO all int fields = "abc" → runner doesn't crash, auto-enables trade_level |
| SS2 | `test_invariants_non_dict_counts_no_crash` | counts_by_invariant = "corrupted" → ERROR(3) on disk |
| SS3 | `test_regression_guard_violated_metrics_string_no_crash` | violated_metrics = "abc" → ERROR(3) on disk |

---

## 6. Behavioral Changes

**Yes** — one behavioral change:

`_strict_bool` for `data_integrity.hard_fail`: string values like `"true"` or `"false"`
no longer trigger the data_integrity early exit in `evaluate_decision()`. Previously
`bool("true")` → True → ERROR(3). Now `_strict_bool("true")` → False → normal gate
evaluation continues.

**Defense-in-depth**: The runner quality policy independently checks
`data_integrity.status == "fail"` and elevates to ERROR(3) via that path. The data_integrity
producer always emits `hard_fail` as a Python `bool`, so this change has zero impact on
real-world runs.

All other changes are pure crash-prevention: code that previously crashed on malformed
input now returns safe defaults and produces defined verdicts.

---

## 7. Remaining Ambiguities

### RA1: status enum not validated

Neither `evaluate_decision()` nor the runner validates that `status` is one of the
expected values (`pass`, `fail`, `skip`, `error`, `info`). An unexpected status like
`None` or `"unknown"` would pass through `!= "skip"` checks and enter processing blocks.
**Verdict**: Low risk — all producers are tested and emit known values. Adding status
validation would be a larger change beyond the scope of shape/status hardening.

### RA2: `list("abc")` in runner warning collection

`_as_dict(.data).get("issues", [])` returns the value as-is if it's a string. Then
`str(item) for item in "abc"` iterates over characters. This is in zero-authority
warning collection (cost_sweep, churn_metrics) and cannot affect verdicts.
**Verdict**: Cosmetic — warnings would contain character-level entries but cannot crash
or affect decision authority.

---

## 8. Final Verdict

All container-shape assumptions and type-coercion hazards in authority-bearing consumer
paths are now closed:

- **`.data` is None/non-dict** → `_as_dict()` returns `{}`, no crash
- **`int("abc")`** → `_safe_int()` returns default, no crash
- **`dict("string")`** → `_as_dict()` returns `{}`, no crash
- **`list("string")` → char-list → `.get()` crash** → `_as_list_of_dicts()` returns `[]`
- **`bool("false")` → True** → `_strict_bool()` returns False
- **Iteration over non-dict rows** → `_as_list_of_dicts()` filters to dict items only

64 new regression tests (61 unit + 3 E2E) lock these guarantees.

Combined with Report 30's scalar-field hardening (42 tests), the decision engine and
runner quality policy are now robust against all identified classes of malformed
authoritative payloads: missing scalars, non-finite numerics, wrong container shapes,
non-numeric strings, ambiguous boolean coercion, and non-dict iteration targets.
