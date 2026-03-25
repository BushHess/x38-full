# Report 33 — Heuristic Governance Cleanup, Single-Source-of-Truth Thresholds, and JSON Compatibility Patch

**Date**: 2026-03-04
**Scope**: Duplicated authority-bearing thresholds, provenance labeling, JSON standards compliance
**Predecessor**: Report 32 (threshold provenance and heuristic governance audit)
**Status**: Complete — governance debt cleaned, no threshold values changed

---

## 1. Executive Summary

Report 32 identified three authority-bearing thresholds duplicated between producer
suites and the decision consumer, several thresholds lacking provenance documentation,
and one holdout.py serialization path bypassing the JSON sanitizer. This report
implements the governance cleanup:

- **Created `validation/thresholds.py`** — single source of truth for 3 shared constants
  (HARSH_SCORE_TOLERANCE, WFO_WIN_RATE_THRESHOLD, WFO_SMALL_SAMPLE_CUTOFF)
- **Unified 6 code locations** — 3 producer suites and 1 consumer now import from
  the same module instead of hardcoding values
- **Added provenance labels** — explicit classification (proven / documented but weak /
  inferred / unproven) in thresholds.py and config.py
- **Fixed holdout.py JSON serialization** — replaced raw `json.dump()` with `write_json()`
  for standards-compliant output
- **26 new tests** lock the single-source-of-truth contract and JSON compliance

**No threshold values changed. No gate authority changed. No decision behavior changed.**

The only observable output change: `holdout_lock.json` is now written via the centralized
`write_json()` path (sanitized, `allow_nan=False`) instead of raw `json.dump()`.
This has zero practical impact since the lock payload contains only date strings.

---

## 2. Duplicated Threshold Audit

### 2.1 Backtest Harsh Delta Tolerance (-0.2)

| Location | Before | After |
|----------|--------|-------|
| `validation/suites/backtest.py:193` | `tolerance = -0.2` (hardcoded) | `tolerance = -HARSH_SCORE_TOLERANCE` |
| `validation/decision.py:23` | `harsh_score_tolerance: float = 0.2` (literal) | `harsh_score_tolerance: float = HARSH_SCORE_TOLERANCE` |

**Action**: Unified. Both now import from `validation/thresholds.py`.

### 2.2 Holdout Harsh Delta Tolerance (-0.2)

| Location | Before | After |
|----------|--------|-------|
| `validation/suites/holdout.py:167` | `delta >= -0.2` (hardcoded) | `delta >= -HARSH_SCORE_TOLERANCE` |
| `validation/decision.py:24` | `holdout_score_tolerance: float = 0.2` (literal) | `holdout_score_tolerance: float = HARSH_SCORE_TOLERANCE` |

**Action**: Unified. Both share the same constant. DecisionPolicy retains separate
`holdout_score_tolerance` field for future divergence if needed.

### 2.3 WFO Win-Rate Threshold (0.60) and Small-Sample Cutoff (5)

| Location | Before | After |
|----------|--------|-------|
| `validation/suites/wfo.py:527` | `0.6 * n_windows` (hardcoded) | `WFO_WIN_RATE_THRESHOLD * n_windows` |
| `validation/suites/wfo.py:526` | `n_windows <= 5` (hardcoded) | `n_windows <= WFO_SMALL_SAMPLE_CUTOFF` |
| `validation/decision.py:25` | `wfo_win_rate_threshold: float = 0.60` (literal) | `wfo_win_rate_threshold: float = WFO_WIN_RATE_THRESHOLD` |
| `validation/decision.py:366` | `n_windows <= 5` (hardcoded) | `n_windows <= WFO_SMALL_SAMPLE_CUTOFF` |

**Action**: Unified. All four locations now import from `validation/thresholds.py`.

---

## 3. Single-Source-of-Truth Design

### 3.1 Where the Shared Constants Live

`validation/thresholds.py` — a new, minimal module with zero dependencies beyond
`__future__`. Contains three constants:

```
HARSH_SCORE_TOLERANCE = 0.2      # backtest + holdout delta tolerance
WFO_WIN_RATE_THRESHOLD = 0.60    # WFO win-rate gate
WFO_SMALL_SAMPLE_CUTOFF = 5      # WFO small-sample branching point
```

### 3.2 Why This Location

- **No import coupling**: The module imports nothing from the validation package,
  so it cannot create circular dependencies.
- **Single concern**: Only authority-bearing thresholds that need producer/consumer
  unification. Config-only thresholds (data_integrity params) stay in config.py
  since they are already parameterized through ValidationConfig.
- **Discoverable**: The filename `thresholds.py` is self-documenting. The module
  docstring references Report 32 for full provenance details.

### 3.3 Import Graph

```
thresholds.py  (no dependencies)
  ← decision.py      (consumer)
  ← backtest.py       (producer)
  ← holdout.py        (producer)
  ← wfo.py            (producer)
```

---

## 4. Provenance Labeling Changes

### 4.1 `validation/thresholds.py` (new file)

| Constant | Provenance Label | Report 32 ID |
|----------|-----------------|--------------|
| HARSH_SCORE_TOLERANCE | documented but weak | H01/H02 |
| WFO_WIN_RATE_THRESHOLD | unproven | H04 |
| WFO_SMALL_SAMPLE_CUTOFF | unproven | H05 |

Each constant has an inline comment block documenting:
- Provenance classification
- Brief rationale (or lack thereof)
- Reference to Report 32 section for full details
- Future calibration recommendation where applicable

### 4.2 `validation/config.py` (existing file, comments added)

| Field | Provenance Label | Report 32 ID |
|-------|-----------------|--------------|
| data_integrity_missing_bars_fail_pct | unproven | H35 |
| data_integrity_gap_multiplier | unproven | H37 |
| data_integrity_warmup_fail_coverage_pct | unproven | H36 |

These thresholds feed into ERROR(3) elevation via the runner quality policy but had
zero documentation. Each now has a `# Provenance:` comment with Report 32 reference.

---

## 5. JSON Compatibility Patch

### 5.1 Files Affected

`validation/suites/holdout.py` — the only serialization path that bypassed the
centralized `write_json()` sanitizer.

### 5.2 Previous Behavior

```python
with open(lock_path, "w") as file_obj:
    json.dump(lock_payload, file_obj, indent=2)
```

This used Python's default `allow_nan=True`, meaning any NaN/Infinity value in the
payload would serialize as the non-standard JSON tokens `NaN` or `Infinity`. Strict
JSON parsers (Go `encoding/json`, JavaScript `JSON.parse`, most non-Python languages)
would reject these files.

### 5.3 New Behavior

```python
write_json(lock_payload, lock_path)
```

This uses the centralized `_sanitize_for_json()` + `allow_nan=False` path from
`validation/output.py`, which:
- Recursively converts NaN → `null`, Infinity → `null`, -Infinity → `null`
- Handles numpy types, dataclasses, Paths
- Enforces strict JSON via `allow_nan=False` (raises ValueError if sanitization misses anything)

### 5.4 Decision-Bearing Impact

**None.** The holdout lock payload contains only string values (ISO dates and UTC
timestamp). No numeric values are serialized through this path. The change is purely
a correctness improvement for defense-in-depth.

### 5.5 Serialization Strategy

**NaN/Inf → `null`** (JSON `null`). This is the strategy already used by all other
serialization paths in the pipeline via `_sanitize_for_json()`. The holdout.py patch
simply brings the last holdout into consistency.

The `import json` statement was also removed from holdout.py since it is no longer
used directly.

---

## 6. Regression Tests Added

### `test_threshold_single_source.py` — 19 tests

| Group | Count | What It Proves |
|-------|-------|----------------|
| TestDecisionPolicyDefaults (TS1-3) | 3 | DecisionPolicy defaults == shared constants |
| TestProducerImports (TS4-7) | 4 | Producer source code references shared constants, not hardcoded values |
| TestDecisionBoundaries (TS8-10) | 6 | Gate pass/fail at exact threshold boundaries; WFO branching at cutoff |
| TestThresholdValues (TS11) | 3 | Constants are exactly 0.2, 0.60, 5 (regression guard against accidental changes) |
| TestZeroAuthority (TS12) | 3 | cost_sweep, churn, bootstrap cannot veto decisions |

### `test_json_serialization_compliance.py` — 7 tests

| Group | Count | What It Proves |
|-------|-------|----------------|
| TestJsonStrictCompliance (JS1-6) | 6 | write_json produces RFC 8259-compliant JSON for NaN, Inf, -Inf, nested, holdout lock, numpy |
| TestHoldoutLockNoRawJsonDump (JS7) | 1 | holdout.py source no longer contains json.dump or import json |

**Total new tests: 26**

---

## 7. Files Changed

| File | Change |
|------|--------|
| `validation/thresholds.py` | **NEW** — 3 shared constants with provenance comments |
| `validation/decision.py` | Import from thresholds; DecisionPolicy defaults; WFO branching constant |
| `validation/suites/backtest.py` | Import + use HARSH_SCORE_TOLERANCE |
| `validation/suites/holdout.py` | Import + use HARSH_SCORE_TOLERANCE; write_json for lock; remove import json |
| `validation/suites/wfo.py` | Import + use WFO_WIN_RATE_THRESHOLD and WFO_SMALL_SAMPLE_CUTOFF |
| `validation/config.py` | Provenance comments on 3 data_integrity defaults |
| `validation/tests/test_threshold_single_source.py` | **NEW** — 19 tests |
| `validation/tests/test_json_serialization_compliance.py` | **NEW** — 7 tests |

---

## 8. Behavior Changes

### Decision-behavior changes: No

All threshold values are identical before and after. The refactor changes where
constants are defined (from inline literals to a shared module), not what values
they hold. All 211 pre-existing tests pass unchanged.

### Diagnostic-output-only changes: Yes (minimal)

`holdout_lock.json` is now written via `write_json()` instead of raw `json.dump()`.
This means:
- Non-finite values would be sanitized to `null` (was: would serialize as `NaN`/`Infinity`)
- The file is now guaranteed RFC 8259-compliant
- Practical impact: zero, since the lock payload contains only date strings

---

## 9. Remaining Open Governance/Science Debt After Prompt 7

### 9.1 Heuristics That Need Future Calibration

| ID | Threshold | Current Status | Recommended Action |
|----|-----------|---------------|-------------------|
| H04 | WFO_WIN_RATE_THRESHOLD = 0.60 | Unproven; now labeled and shared | Simulation study with known-null/positive pairs |
| H05 | WFO_SMALL_SAMPLE_CUTOFF = 5 | Unproven; now labeled and shared | Power analysis for optimal branching point |
| H35 | missing_bars_fail_pct = 0.5% | Unproven; now labeled in config.py | Validate against real data quality profiles |
| H36 | warmup_fail_coverage_pct = 50% | Unproven; now labeled in config.py | Same |
| H27 | low_trade_threshold = 5 | Unproven; config default only | Document rationale or calibrate |
| H44 | WFO scenario priority (harsh > base > smart) | Unproven; hardcoded | Document rationale |

### 9.2 Governance Items Closed by This Report

| Item | Status |
|------|--------|
| Producer/consumer threshold duplication | Closed — unified via thresholds.py |
| Missing provenance labels | Closed — all authority-bearing thresholds labeled |
| Non-standard JSON in holdout.py | Closed — uses write_json() now |
| No test coverage for single-source-of-truth | Closed — 19 tests |
| No test coverage for JSON strict compliance | Closed — 7 tests |

### 9.3 Items Explicitly Out of Scope

- Threshold retuning (deferred to future calibration studies)
- Gate authority redesign (no changes since Report 27)
- Selection-bias string-matching heuristic (H11) — untested in production but
  correct by unit tests; needs stress-testing with weak strategies
- Trade-level low-power resolution rate — needs more diverse archived runs
