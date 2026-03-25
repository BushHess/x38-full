# Report 23 — Phase 1 + Phase 2 Implementation Report

**Date**: 2026-03-03
**Canonical plan**: `research_reports/22_b_inference_patch_plan.md`
**Scope**: Phase 1 (safety/docs) + Phase 2 (pair diagnostic harness)

---

## Touched Files

### Phase 1: Modified (existing files)

| File | Change type | LOC changed |
|------|------------|-------------|
| `v10/research/bootstrap.py` | 1A: alignment validation, 1B: docstring | ~12 |
| `v10/research/subsampling.py` | 1C: degeneracy caveat docstring | ~8 |
| `validation/suites/bootstrap.py` | 1B: inline comment on p_candidate_better | ~1 |
| `validation/suites/subsampling.py` | 1C: inline comment on p_candidate_better | ~3 |
| `validation/suites/selection_bias.py` | 1E: DSR calling-convention block | ~12 |
| `research/lib/dsr.py` | 1E: docstring note on calling convention | ~5 |
| `research/e5_validation.py` | 1D: V2 ban warning comment block | ~12 |
| `research/trail_sweep.py` | 1D: V2 ban warning comment block | ~12 |
| `v10/tests/test_bootstrap.py` | 1A: +1 alignment mismatch test | ~8 |

### Phase 2: New files

| File | Purpose | LOC |
|------|---------|-----|
| `research/lib/pair_diagnostic.py` | Machine-only pair diagnostic harness | ~350 |
| `research/tests/__init__.py` | Package marker (empty) | 0 |
| `research/tests/test_pair_diagnostic.py` | Phase 2 unit tests | ~330 |

---

## Behavior Added

### Phase 1

- **1A**: `paired_block_bootstrap()` now raises `ValueError` on length-mismatched equity curves instead of silently truncating
- **1B**: Docstring on `paired_block_bootstrap()` clarifies `p_a_better` is a directional resampling score, NOT a calibrated p-value (Report 21, U1-U2)
- **1C**: Docstring on `paired_block_subsampling()` warns about CI collapse when near-equality rate > 80% (Report 19, §4; Report 21, U5)
- **1D**: Warning comment blocks in `e5_validation.py` and `trail_sweep.py` about uncorrected binomial cross-strategy false positives (Report 21, U6)
- **1E**: DSR calling-convention documentation in `selection_bias.py` (canonical pipeline convention) and `dsr.py` (notes daily vs H4)

### Phase 2

- `PairProfile`: Tolerance-based pair properties (no raw float `==`)
- `PairClassification`: 3-tier classification (near_identical / borderline / materially_different)
- `PairDiagnosticResult`: Frozen dataclass with NO decision/promote/reject fields
- `compute_pair_profile()`: Tolerance-based equality rates, correlation, exposure overlap
- `classify_pair()`: Rule-based 3-tier classification with configurable thresholds
- `suggest_review_route()`: Non-binding routing labels (4 types)
- `run_pair_diagnostic()`: Full orchestration — profile, classification, bootstrap (Sharpe + geo), subsampling, DSR, consensus, caveats, route
- `render_review_template()`: Auto-filled Section 1 + blank Section 2

---

## Thresholds/Tolerances Exposed as Defaults

All thresholds are module-level constants AND function parameter defaults — configurable at call site:

| Constant | Default | Used in |
|----------|---------|---------|
| `DEFAULT_TOL_EXACT` | `1e-10` | `compute_pair_profile()` |
| `DEFAULT_TOL_1BP` | `1e-4` | `compute_pair_profile()` |
| `DEFAULT_TOL_10BP` | `1e-3` | `compute_pair_profile()` |
| `CLASSIFY_1BP_NEAR_IDENTICAL` | `0.95` | `classify_pair()` |
| `CLASSIFY_CORR_NEAR_IDENTICAL` | `0.97` | `classify_pair()` |
| `CLASSIFY_1BP_BORDERLINE` | `0.80` | `classify_pair()` |
| `CLASSIFY_CORR_BORDERLINE` | `0.90` | `classify_pair()` |
| `SUBSAMPLING_RELIABILITY_1BP_MAX` | `0.80` | `classify_pair()` |
| `CONSENSUS_GAP_MAX_PP` | `5.0` | `run_pair_diagnostic()` |
| `ROUTE_BOOT_P_ANOMALY_THRESHOLD` | `0.15` | `suggest_review_route()` |

No hardcoded project constants (t_eff, min_detectable_delta) in library logic.

---

## Tests Added/Updated

### New tests: 18

| File | Test count | Tests |
|------|-----------|-------|
| `v10/tests/test_bootstrap.py` | +1 | `test_paired_bootstrap_raises_on_length_mismatch` |
| `research/tests/test_pair_diagnostic.py` | +17 | T8–T18 + 4 additional (see below) |

### Test mapping to plan (Report 22B §2.10 and §4.4–4.5)

| Plan ID | Test name | Status |
|---------|-----------|--------|
| T8 | `test_diagnostic_result_schema_no_decision` | PASS |
| T9 | `test_json_output_schema_no_decision_key` | PASS |
| T10 | `test_pair_profile_tolerance_not_exact` | PASS |
| T11 | `test_classify_a0_vs_a1_near_identical` | PASS |
| T12 | `test_classify_a0_vs_vbreak_materially_different` | PASS |
| T13 | `test_classify_borderline_case` | PASS |
| T14 | `test_route_near_identical_no_action` | PASS |
| T15 | `test_route_near_identical_escalate` | PASS |
| T16 | `test_route_borderline_always_escalate` | PASS |
| T17 | `test_route_materially_different_consensus_fail` | PASS |
| T18 | `test_markdown_template_has_blank_human_section` | PASS |
| — | `test_subsampling_unreliable_when_1bp_above_80` | PASS |
| — | `test_subsampling_reliable_when_1bp_below_80` | PASS |
| — | `test_classify_borderline_by_corr` | PASS |
| — | `test_route_materially_different_many_caveats` | PASS |
| — | `test_route_materially_different_inconclusive` | PASS |
| — | `test_markdown_template_has_section1_filled` | PASS |
| (1A) | `test_paired_bootstrap_raises_on_length_mismatch` | PASS |

### Exact new test count: 18

The plan's discrepancy (19 vs T18) is reconciled as follows:
- The plan lists T1–T7 as Phase 4 tests (gate retirement, NOT implemented yet)
- The plan lists T8–T18 as Phase 2 + Phase 4 harness tests (11 tests)
- I implemented all 11 plan tests (T8–T18) + 6 additional tests for better coverage + 1 Phase 1A alignment test = **18 new tests total**
- T1–T7 will be added in Phase 3/4 when gate retirement is implemented

### Existing tests: 0 modified, 0 broken

Full regression run: **79/79 PASS** (17 bootstrap + 9 subsampling + 10 decision + 17 pair_diagnostic + 26 validation)

---

## Path Deviations from Patch Plan

| Plan path | Actual path | Reason |
|-----------|-------------|--------|
| `research/tests/test_pair_diagnostic.py` | `research/tests/test_pair_diagnostic.py` | Exact match (created `research/tests/` directory with `__init__.py`) |
| All other files | Exact match | No deviations |

---

## Phases Intentionally NOT Implemented

| Phase | Status | Reason |
|-------|--------|--------|
| Phase 3: Retire unsafe gate semantics | NOT IMPLEMENTED | Per task scope — do NOT touch `validation/decision.py` |
| Phase 4: Regression tests (T1–T7) | NOT IMPLEMENTED | Depends on Phase 3 gate changes |
| Phase 5: Wording cleanup | NOT IMPLEMENTED | Per task scope |
| §2.8: Multi-timescale extension | NOT IMPLEMENTED | Per task scope |
