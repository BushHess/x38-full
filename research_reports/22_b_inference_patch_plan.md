# Report 22 — Inference Stack Patch Plan (Revised)

**Date**: 2026-03-03
**Revision**: B (replaces original 22)
**Source**: Reports 21, 18, 19, 20
**Scope**: Maximal automation of mechanical pair-review work.
Zero automated promote/reject authority.
**Constraint**: No broad refactors. No changes to statistical core logic.

---

## Overview

Five phases, strictly ordered by risk. Each phase is independently
deployable and independently revertible.

| Phase | Goal | Files touched | Risk |
|-------|------|---------------|------|
| 1 | Safety fixes + documentation | 7 production + 2 research | Low (alignment check, docstrings, comments) |
| 2 | Machine-only Pair Diagnostic Harness | 1 new module + 1 new test | Low (new code, no existing code modified) |
| 3 | Retire unsafe gate semantics | 2 production | Medium (gate behavior changes) |
| 4 | Regression tests | 1 new test file | None |
| 5 | Wording cleanup in reports/docs | 0 production, 2–4 docs | None |

---

## Phase 1: Safety Fixes + Documentation

**Goal**: Fix the one known correctness hazard (bootstrap alignment),
relabel misleading names, add caveats, document conventions. No
behavioral changes. All existing callers continue to work identically.

### 1A. Bootstrap: alignment validation

**File**: `v10/research/bootstrap.py`
**Lines**: 182–184

**Current behavior**:
```python
n = min(len(returns_a), len(returns_b))
returns_a = returns_a[:n]
returns_b = returns_b[:n]
```
Silent truncation. No timestamp check. (Report 02, U4.)

**New behavior**:
```python
if len(returns_a) != len(returns_b):
    raise ValueError(
        f"paired_block_bootstrap: equity curves have different lengths "
        f"({len(returns_a)} vs {len(returns_b)}). "
        f"Ensure both curves cover the same time range."
    )
n = len(returns_a)
```

Replace `min(len_a, len_b)` + truncation with a length-equality check
that raises `ValueError`. Matches subsampling's `AlignmentError` pattern
(subsampling.py lines 118–120).

**Tests to add**: 1 test in `v10/tests/test_bootstrap.py`:
`test_paired_bootstrap_raises_on_length_mismatch` — pass equity curves
of different lengths, assert `ValueError`.

**Rollback risk**: LOW. Only affects misaligned input. All existing
callers pass aligned curves.

### 1B. Bootstrap: relabel `p_a_better`

**File**: `v10/research/bootstrap.py`
**Lines**: ~170–176 (docstring of `paired_block_bootstrap`)

Append to existing docstring:
```
NOTE: The returned `p_a_better` is the fraction of bootstrap resamples
where the candidate's metric exceeds the baseline's. It is a
*directional resampling score*, NOT a calibrated p-value. It does not
test H0: metric(A) ≤ metric(B) and should not be compared to
significance levels (α = 0.05, etc.). See Report 21, U1–U2.
```

**File**: `validation/suites/bootstrap.py` — add inline comment on
`p_candidate_better` (line ~82):
```python
# Directional resampling score, NOT a p-value (Report 21, U1).
```

**Rollback risk**: NONE. Docstring/comment only.

### 1C. Subsampling: degeneracy caveat

**File**: `v10/research/subsampling.py`
**Lines**: ~164–170 (docstring of `paired_block_subsampling`)

Add to docstring:
```
CAVEAT: When the near-equality rate (|diff| < 1bp) of the differential
return series exceeds ~80%, block means become degenerate and the
subsampling CI may collapse. In this regime, p_a_better is NOT
calibrated and should not be interpreted as a probability.
See Report 19, §4 and Report 21, U5.
```

**File**: `validation/suites/subsampling.py` — add inline comment on
`p_candidate_better` (line ~108):
```python
# Subsampling directional score. NOT a posterior probability.
# Miscalibrated when differential series has high near-equality rate
# (Report 19, §4; Report 21, U5).
```

**Rollback risk**: NONE.

### 1D. Win-count V2: ban warning for cross-strategy

**Files**: `research/e5_validation.py` (after line 21),
`research/trail_sweep.py` (after line 11)

Add warning comment block:
```python
# ──────────────────────────────────────────────────────────────
# WARNING (Report 21, U6): The uncorrected binomial test in this script
# treats 16 timescale outcomes as independent. For CROSS-STRATEGY
# comparison, adjacent-timescale correlation yields M_eff ≈ 2.5–4.0,
# making the uncorrected p-values unreliable (demonstrated false
# positive: PROVEN*** on null pair, Report 20 §5.3).
#
# Cross-strategy results from this script MUST be verified with DOF
# correction (research/lib/effective_dof.py) before citation.
#
# WITHIN-STRATEGY results (e.g., VDO on/off, M_eff ≈ 10–11) are
# not affected by this limitation.
# ──────────────────────────────────────────────────────────────
```

**Rollback risk**: NONE. Comment only.

### 1E. DSR: document calling conventions

**File**: `validation/suites/selection_bias.py` — add documentation
block before DSR loop (~line 95):
```python
# ── DSR calling convention (canonical) ──
# This suite calls deflated_sharpe() with:
#   sr_observed = annualized Sharpe (from daily log-returns)
#   t_samples   = number of DAILY observations
#   skew, kurt  = from daily log-returns
#
# This differs from research/lib/dsr.py:compute_dsr() which takes
# per-bar (H4) Sharpe and per-bar sample count. The daily convention
# is more lenient because n_daily < n_h4 and annualized Sharpe is
# larger than per-bar Sharpe.
#
# The suite convention is CANONICAL for the validation pipeline.
# See Report 21, §3 (Role Matrix) — DSR is advisory only.
```

**File**: `research/lib/dsr.py` — add note to `deflated_sharpe`
docstring (~line 91):
```
Note: The validation suite (selection_bias.py) calls this function with
annualized Sharpe and daily sample count, which is the CANONICAL calling
convention for the pipeline. Direct calls with per-bar (H4) Sharpe and
H4 sample count produce stricter (less lenient) results.
See Report 21, §3 — DSR is a single-strategy advisory, not a paired gate.
```

**Rollback risk**: NONE.

### Phase 1 summary

| Item | File | LOC changed | Tests affected |
|------|------|-------------|----------------|
| 1A. Alignment check | `v10/research/bootstrap.py` | ~6 | +1 new test |
| 1B. Relabel p_a_better | `v10/research/bootstrap.py`, `validation/suites/bootstrap.py` | ~8 | 0 |
| 1C. Degeneracy caveat | `v10/research/subsampling.py`, `validation/suites/subsampling.py` | ~10 | 0 |
| 1D. V2 ban warning | `research/e5_validation.py`, `research/trail_sweep.py` | ~12 each | 0 |
| 1E. DSR conventions | `validation/suites/selection_bias.py`, `research/lib/dsr.py` | ~15 | 0 |

---

## Phase 2: Machine-Only Pair Diagnostic Harness

**Goal**: Automate all mechanical pair-review computation into a single
entry point that produces machine-readable JSON and an auto-filled
markdown review template. The harness has ZERO decision authority.

**New file**: `research/lib/pair_diagnostic.py`

### 2.1 Tolerance Policy

**MANDATORY**: Raw float equality (`diff == 0`) is BANNED for pair
classification. All near-equality checks use explicit tolerance
thresholds.

**Defined metrics** (computed from paired return series `r_a`, `r_b`):

```python
TOLERANCE_EXACT = 1e-10     # machine epsilon (for "exact" match audit)
TOLERANCE_1BP   = 1e-4      # 1 basis point per bar
TOLERANCE_10BP  = 1e-3      # 10 basis points per bar

@dataclass(frozen=True)
class PairProfile:
    """Tolerance-based pair properties. No raw float equality."""

    n_bars: int
    # ── Tolerance-based equality rates ──
    equal_rate_tol: float           # |r_a - r_b| < TOLERANCE_EXACT
    near_equal_1bp_rate: float      # |r_a - r_b| < TOLERANCE_1BP
    near_equal_10bp_rate: float     # |r_a - r_b| < TOLERANCE_10BP
    # ── Directional agreement ──
    same_direction_rate: float      # sgn(r_a) == sgn(r_b) (both zero counts as same)
    # ── Linear dependence ──
    return_correlation: float       # Pearson ρ of bar returns
    # ── Exposure overlap ──
    exposure_agreement_rate: float  # both in or both out (requires exposure arrays)
```

**Implementation**:
```python
def compute_pair_profile(
    returns_a: np.ndarray,
    returns_b: np.ndarray,
    *,
    exposure_a: np.ndarray | None = None,
    exposure_b: np.ndarray | None = None,
    tol_exact: float = 1e-10,
    tol_1bp: float = 1e-4,
    tol_10bp: float = 1e-3,
) -> PairProfile:
    """Compute tolerance-based pair profile. No raw float ==."""
    diff = np.abs(returns_a - returns_b)
    ...
```

**Verification against Report 17 data**:

| Pair | equal_tol (R17 Exact-Eq) | 1bp (R17 <1bp) | corr | Classification |
|------|--------------------------|----------------|------|----------------|
| A0 vs A1 | 98.8% | 98.9% | 0.987 | near_identical |
| VBREAK vs VTWIN | 99.6% | 99.6% | 0.993 | near_identical |
| VBREAK vs VCUSUM | 83.0% | 83.2% | 0.639 | borderline |
| A0 vs VBREAK | 73.2% | 73.5% | 0.735 | materially_different |
| A0 vs VCUSUM | 62.7% | 63.2% | 0.525 | materially_different |
| A0 vs BUY_HOLD | 45.7% | 46.3% | 0.638 | materially_different |

### 2.2 Pair Classification (3-Tier)

```python
@dataclass(frozen=True)
class PairClassification:
    pair_class: str                 # "near_identical" | "borderline" | "materially_different"
    subsampling_reliable: bool      # False if near_equal_1bp_rate > 0.80
    primary_reason: str             # human-readable explanation

def classify_pair(profile: PairProfile) -> PairClassification:
    """Three-tier classification from tolerance-based metrics.

    Rules (order matters — first match wins):
      near_identical:       1bp_rate > 0.95 AND corr > 0.97
      borderline:           1bp_rate > 0.80 OR  corr > 0.90
      materially_different: everything else

    Subsampling reliability threshold: 1bp_rate <= 0.80.
    Above this, block means become degenerate (Report 19, §4).
    """
    sub_reliable = profile.near_equal_1bp_rate <= 0.80

    if profile.near_equal_1bp_rate > 0.95 and profile.return_correlation > 0.97:
        return PairClassification(
            pair_class="near_identical",
            subsampling_reliable=False,
            primary_reason=(
                f"near_equal_1bp={profile.near_equal_1bp_rate:.1%}, "
                f"corr={profile.return_correlation:.3f}"
            ),
        )
    if profile.near_equal_1bp_rate > 0.80 or profile.return_correlation > 0.90:
        return PairClassification(
            pair_class="borderline",
            subsampling_reliable=sub_reliable,
            primary_reason=(
                f"near_equal_1bp={profile.near_equal_1bp_rate:.1%}, "
                f"corr={profile.return_correlation:.3f}"
            ),
        )
    return PairClassification(
        pair_class="materially_different",
        subsampling_reliable=True,
        primary_reason=(
            f"near_equal_1bp={profile.near_equal_1bp_rate:.1%}, "
            f"corr={profile.return_correlation:.3f}"
        ),
    )
```

### 2.3 Machine-Only Diagnostic Output (Layer A)

**STRICT RULE**: This dataclass has NO `decision` field, NO
`decision_reasoning` field, NO promote/reject/inconclusive authority.
It contains only computed diagnostics, caveats, and a non-binding
suggested review route.

```python
@dataclass(frozen=True)
class PairDiagnosticResult:
    """Machine-only pair diagnostic. NO decision authority.

    This object contains ONLY computed values and caveats.
    It does NOT and MUST NOT contain any promote/reject field.
    The human review note (Layer B) is a separate artifact.
    """

    # ── Pair identification ──
    label_a: str
    label_b: str

    # ── Tolerance-based profile (§2.1) ──
    profile: PairProfile

    # ── Classification (§2.2) ──
    classification: PairClassification

    # ── Bootstrap diagnostic (Sharpe statistic) ──
    boot_sharpe_p: float            # directional resampling score (NOT a p-value)
    boot_sharpe_ci_lower: float
    boot_sharpe_ci_upper: float
    boot_sharpe_ci_width: float
    boot_sharpe_observed_delta: float

    # ── Bootstrap diagnostic (geo-growth statistic, for consensus) ──
    boot_geo_p: float
    boot_geo_ci_lower: float
    boot_geo_ci_upper: float

    # ── Subsampling diagnostic (geo-growth statistic) ──
    sub_p: float                    # directional score (NOT a posterior probability)
    sub_ci_lower: float
    sub_ci_upper: float
    sub_support: float              # support ratio across block sizes

    # ── Cross-method consensus ──
    consensus_gap_pp: float         # |boot_geo_p - sub_p| in percentage points
    consensus_ok: bool              # gap < 5pp

    # ── DSR per-strategy (advisory) ──
    dsr_a: dict[int, float]         # {27: pvalue, 54: pvalue, ...}
    dsr_b: dict[int, float]

    # ── Caveats (auto-generated list of warnings) ──
    caveats: list[str]

    # ── Suggested review route (non-binding, §2.4) ──
    suggested_route: str
    route_reason: str

    # ── Metadata ──
    bootstrap_config: dict          # {n_bootstrap, block_sizes, seed}
    timestamp_utc: str              # ISO 8601
```

**What this dataclass DOES NOT contain**:
- `decision` (no field exists)
- `decision_reasoning` (no field exists)
- `promote` / `reject` / `inconclusive` (no such concepts)
- `t_eff_approx` or `min_detectable_delta_sharpe` (project constants
  belong in report metadata, not library logic)

### 2.4 Suggested Review Route (Non-Binding)

The harness suggests a review route based on pair class and diagnostic
patterns. This is a ROUTING SUGGESTION, not a decision. The researcher
may override it.

```python
ROUTE_NO_ACTION = "no_action_default"
ROUTE_INCONCLUSIVE = "inconclusive_default"
ROUTE_ESCALATE_EVENT = "escalate_event_review"
ROUTE_ESCALATE_FULL = "escalate_full_manual_review"

def suggest_review_route(
    classification: PairClassification,
    boot_sharpe_p: float,
    consensus_ok: bool,
    caveats: list[str],
) -> tuple[str, str]:
    """Non-binding review route suggestion.

    Returns (route, reason). The route is a label, not a decision.
    """
    if classification.pair_class == "near_identical":
        # Near-identical pairs default to no action.
        # Escalate if bootstrap shows anomalous directional signal.
        if abs(boot_sharpe_p - 0.5) > 0.15:
            return (
                ROUTE_ESCALATE_EVENT,
                f"near_identical pair with unexpected directional "
                f"signal (boot_p={boot_sharpe_p:.3f}, "
                f"expected ~0.50)"
            )
        return (
            ROUTE_NO_ACTION,
            "near_identical pair, no anomalous signal"
        )

    if classification.pair_class == "borderline":
        # Borderline pairs always need full manual review.
        return (
            ROUTE_ESCALATE_FULL,
            "borderline classification — manual review required "
            "to determine if differential series is informative"
        )

    # materially_different
    if not consensus_ok:
        return (
            ROUTE_ESCALATE_EVENT,
            f"method consensus failed — investigate "
            f"statistic mismatch or data issue"
        )
    if len(caveats) > 2:
        return (
            ROUTE_ESCALATE_FULL,
            f"{len(caveats)} caveats flagged — manual review recommended"
        )
    return (
        ROUTE_INCONCLUSIVE,
        "materially_different pair, diagnostics consistent, "
        "power limitation applies"
    )
```

### 2.5 Orchestration: `run_pair_diagnostic()`

```python
def run_pair_diagnostic(
    equity_a: list,                 # list[EquitySnap]
    equity_b: list,
    label_a: str,
    label_b: str,
    *,
    block_sizes: tuple[int, ...] = (10, 20, 40),
    n_bootstrap: int = 2000,
    seed: int = 1337,
    tol_exact: float = 1e-10,
    tol_1bp: float = 1e-4,
    tol_10bp: float = 1e-3,
    dsr_trial_levels: tuple[int, ...] = (27, 54, 100, 200, 500, 700),
) -> PairDiagnosticResult:
    """Run ALL single-timescale diagnostics on a strategy pair.

    Returns a machine-only PairDiagnosticResult (Layer A).
    NO decision, NO decision_reasoning, NO promote/reject.
    The human writes their review note separately (Layer B).
    """
    # 1. Extract returns from equity curves
    # 2. compute_pair_profile() → PairProfile (tolerance-based)
    # 3. classify_pair() → PairClassification (3-tier)
    # 4. Build caveats list based on profile + classification
    # 5. paired_block_bootstrap(metric=sharpe) → boot_sharpe_*
    # 6. paired_block_bootstrap(metric=mean_log_return) → boot_geo_*
    # 7. paired_block_subsampling(all block_sizes) → sub_*
    # 8. Consensus check: |boot_geo_p - sub_p|
    # 9. compute_dsr() per strategy → dsr_a, dsr_b
    # 10. suggest_review_route() → route, reason
    # 11. Assemble PairDiagnosticResult
    ...
```

**What it calls** (all existing, no new statistics):

| Step | Function | Module |
|------|----------|--------|
| Profile | `np.corrcoef`, tolerance-based counts | numpy |
| Bootstrap (Sharpe) | `paired_block_bootstrap()` | `v10/research/bootstrap.py` |
| Bootstrap (geo) | `paired_block_bootstrap(metric_fn=...)` | same, custom metric |
| Subsampling | `paired_block_subsampling()`, `summarize_block_grid()` | `v10/research/subsampling.py` |
| DSR | `compute_dsr()` | `research/lib/dsr.py` |

**What it does NOT call**:
- No multi-timescale loop (V1/V3 — see §2.8)
- No promote/reject logic
- No uncorrected binomial (V2 is not exposed)

### 2.6 JSON Output

`PairDiagnosticResult` serializes to JSON via `dataclasses.asdict()`.
The output schema is machine-readable and can be validated.

**Schema invariant**: the JSON NEVER contains keys named `decision`,
`promote`, `reject`, `verdict`, or `recommendation`. This is
enforced by the dataclass definition (no such fields exist) and
verified by regression test (Phase 4, T8).

### 2.7 Markdown Template Generation

```python
def render_review_template(diag: PairDiagnosticResult) -> str:
    """Generate markdown review template from machine diagnostic.

    The template has two sections:
      Section 1 (auto-filled): all diagnostic values, caveats, route
      Section 2 (blank): human review note
    """
```

Example output for A0 vs VCUSUM:

```markdown
# Pair Diagnostic: VTREND_A0 vs VCUSUM

## Section 1: Machine Diagnostic (auto-filled)

**Classification**: materially_different
  near_equal_1bp=63.2%, corr=0.525
  subsampling_reliable=True

**Bootstrap (Sharpe)**: p=0.818, CI=[-0.401, +1.072], width=1.473
**Bootstrap (geo growth)**: p=0.924, CI=[-0.069, +0.601]
**Subsampling**: p=0.930, CI=[-0.139, +0.625], support=0.00
**Consensus**: gap=0.6pp — OK

**DSR (A)**: {27: 0.91, 54: 0.88, ...}  (advisory only)
**DSR (B)**: {27: 0.85, 54: 0.82, ...}  (advisory only)

**Caveats**:
  - Subsampling support=0.00 (expected for available effect sizes)

**Suggested route**: inconclusive_default
  Reason: materially_different pair, diagnostics consistent,
  power limitation applies

---

## Section 2: Human Review Note (researcher fills in)

**Decision**: _______________
  Options: NO_ACTION | INCONCLUSIVE | PROMOTE | REJECT

**Reasoning**:
  [Explain which diagnostics support this decision and which are
  inconclusive. Cite specific values from Section 1.]

**Tradeoff summary**:
  [If the pair involves a Sharpe/MDD tradeoff, describe it here.]

**Unresolved concerns**:
  [List anything that cannot be resolved with current data.]
```

### 2.8 Multi-Timescale Extension (Optional, Researcher-Invoked)

Multi-timescale V1 (real-data wins) and V3 (DOF-corrected) are NOT
part of the core `run_pair_diagnostic()` workflow. They are available
as an explicitly researcher-invoked extension:

```python
def run_multiscale_extension(
    build_signals_a: Callable,
    build_signals_b: Callable,
    data_feed: Any,
    *,
    slow_periods: tuple[int, ...] = (30, 48, 60, 72, 84, 96, 108,
                                      120, 144, 168, 200, 240,
                                      300, 360, 500, 720),
    n_bootstrap: int = 500,
    seed: int = 42,
) -> dict:
    """OPTIONAL: Run V1 real-data wins + V3 DOF-corrected.

    This is NOT part of the standard pair diagnostic.
    Invoke explicitly when multi-timescale evidence is needed.
    Runtime: ~10 min (500 paths × 16 timescales × 2 strategies).
    """
    ...
```

This function:
- Is never called by `run_pair_diagnostic()`
- Is never mentioned in the suggested review route
- Does not appear in the markdown template by default
- Can be appended to the review template as a supplementary section
  if the researcher chooses to run it

### 2.9 Phase 2 summary

| Item | File | LOC | Tests |
|------|------|-----|-------|
| Full harness | `research/lib/pair_diagnostic.py` (NEW) | ~300 | — |
| Unit tests | `research/tests/test_pair_diagnostic.py` (NEW) | ~150 | +10 (see §2.10) |

### 2.10 Phase 2 unit tests

| Test | What it verifies |
|------|-----------------|
| `test_pair_profile_uses_tolerance_not_exact_eq` | `compute_pair_profile()` uses `|diff| < tol`, never `diff == 0` |
| `test_classify_near_identical` | 1bp_rate=0.989, corr=0.987 → `"near_identical"` |
| `test_classify_borderline` | 1bp_rate=0.832, corr=0.639 → `"borderline"` |
| `test_classify_materially_different` | 1bp_rate=0.632, corr=0.525 → `"materially_different"` |
| `test_subsampling_unreliable_when_1bp_above_80` | 1bp_rate=0.95 → `subsampling_reliable=False` |
| `test_subsampling_reliable_when_1bp_below_80` | 1bp_rate=0.73 → `subsampling_reliable=True` |
| `test_diagnostic_result_has_no_decision_field` | `PairDiagnosticResult` has no attr named `decision`, `promote`, `reject`, `verdict` |
| `test_json_output_has_no_decision_key` | `asdict(result)` JSON has no key matching `/decision\|promote\|reject\|verdict/` |
| `test_route_near_identical_default` | near_identical + boot_p≈0.5 → `"no_action_default"` |
| `test_route_materially_different_no_consensus` | consensus_ok=False → `"escalate_event_review"` |

---

## Phase 3: Retire Unsafe Gate Semantics

**Goal**: Remove pass/fail authority from bootstrap and subsampling gates
in the validation pipeline. These become diagnostics.

### 3A. Bootstrap gate → diagnostic in decision engine

**File**: `validation/decision.py`
**Lines**: 298–321

**Current behavior**:
```python
passed = p >= policy.bootstrap_p_threshold and ci_low > policy.bootstrap_ci_lower_min
gates.append(GateCheck(gate_name="bootstrap", passed=passed, severity="soft", ...))
if not passed:
    failures.append("bootstrap_gate_failed")
    reasons.append("Bootstrap evidence not strong enough for promote")
```

**New behavior**:
```python
# Bootstrap is a DIAGNOSTIC, not a gate (Report 21, §1.1).
# p_a_better is a directional resampling score, NOT a p-value.
gates.append(GateCheck(gate_name="bootstrap", passed=True, severity="info", ...))
# Never append to failures — bootstrap has no veto power.
```

**Exact change**: (a) `passed=True` unconditionally. (b) `severity`
→ `"info"`. (c) Remove the `if not passed` block. (d) Keep
`deltas["bootstrap_p_candidate_better"]` and
`deltas["bootstrap_ci_lower"]` — values still reported, not gated on.

**Tests to update**:
- `v10/tests/test_decision.py`: update any test asserting HOLD/REJECT
  from bootstrap gate failure. `test_hold_when_not_promoted` — if it
  relies on bootstrap, switch trigger to a different gate.

**Rollback risk**: LOW. Bootstrap gate cannot pass on any achievable
pair anyway (Report 18).

### 3B. Subsampling suite status → info

**File**: `validation/suites/subsampling.py`
**Lines**: 137–139

**Current behavior**:
```python
status = "info" if not gate else ("pass" if bool(gate.get("decision_pass")) else "fail")
```

**New behavior**:
```python
# Subsampling is a DIAGNOSTIC, not a gate (Report 21, §1.1).
status = "info"
```

Gate dict still populated for diagnostic consumption.

**Tests to update**: verify no test checks `SuiteResult.status == "pass"`
for subsampling.

**Rollback risk**: NONE. Subsampling was never wired to decision engine.

### Phase 3 summary

| Item | File | LOC changed | Tests affected |
|------|------|-------------|----------------|
| Bootstrap gate → diagnostic | `validation/decision.py` | ~8 | 1–2 in `test_decision.py` |
| Subsampling status → info | `validation/suites/subsampling.py` | ~3 | 0 (verify) |

---

## Phase 4: Regression Tests

**New file**: `validation/tests/test_inference_role_semantics.py`

### 4.1 Control pair fixtures

```python
CONTROL_PAIRS = {
    "A0_vs_A1": {       # near_identical (Report 17)
        "bootstrap_p": 0.474,
        "bootstrap_ci_lower": -0.124,
        "subsampling_p": 0.965,
        "subsampling_ci_lower": -0.020,
        "subsampling_support": 0.33,
        "delta_sharpe": -0.006,
        "near_equal_1bp_rate": 0.989,
        "return_correlation": 0.987,
    },
    "A0_vs_VBREAK": {   # materially_different
        "bootstrap_p": 0.644,
        "bootstrap_ci_lower": -0.454,
        "subsampling_p": 0.905,
        "subsampling_ci_lower": -0.127,
        "subsampling_support": 0.00,
        "delta_sharpe": 0.098,
        "near_equal_1bp_rate": 0.735,
        "return_correlation": 0.735,
    },
    "A0_vs_VCUSUM": {   # materially_different
        "bootstrap_p": 0.818,
        "bootstrap_ci_lower": -0.401,
        "subsampling_p": 0.930,
        "subsampling_ci_lower": -0.139,
        "subsampling_support": 0.00,
        "delta_sharpe": 0.343,
        "near_equal_1bp_rate": 0.632,
        "return_correlation": 0.525,
    },
}
```

### 4.2 Gate-retirement tests (T1–T6)

| Test | Assertion |
|------|-----------|
| T1: `test_bootstrap_gate_is_info_not_soft` | `GateCheck` for bootstrap has `severity="info"`, `passed=True` for all 3 pairs |
| T2: `test_bootstrap_never_in_failures` | `"bootstrap_gate_failed"` never in `failures` list for any control pair |
| T3: `test_bootstrap_still_reports_values` | `deltas["bootstrap_p_candidate_better"]` and `deltas["bootstrap_ci_lower"]` are populated |
| T4: `test_subsampling_status_always_info` | SubsamplingSuite status is `"info"` regardless of gate dict values |
| T5: `test_negative_control_not_blocked` | A0 vs A1 flows through without HOLD from any diagnostic |
| T6: `test_strong_positive_not_blocked` | A0 vs VCUSUM flows through without HOLD from any diagnostic |

### 4.3 Alignment test (T7)

| Test | Assertion |
|------|-----------|
| T7: `test_bootstrap_alignment_rejects_mismatch` | `paired_block_bootstrap` with different-length curves raises `ValueError` |

### 4.4 Pair diagnostic harness tests (T8–T17)

| Test | Assertion |
|------|-----------|
| T8: `test_diagnostic_result_schema_no_decision` | `PairDiagnosticResult` has no attribute named `decision`, `promote`, `reject`, `verdict`, `recommendation` |
| T9: `test_json_output_schema_no_decision_key` | JSON serialization has no key matching `decision\|promote\|reject\|verdict\|recommendation` |
| T10: `test_pair_profile_tolerance_not_exact` | `compute_pair_profile` called with custom tolerances produces different `near_equal_*` rates than raw float `==` count |
| T11: `test_classify_a0_vs_a1_near_identical` | 1bp=0.989, corr=0.987 → `"near_identical"` |
| T12: `test_classify_a0_vs_vbreak_materially_different` | 1bp=0.735, corr=0.735 → `"materially_different"` |
| T13: `test_classify_borderline_case` | 1bp=0.83, corr=0.60 → `"borderline"` (1bp > 0.80 triggers borderline) |
| T14: `test_route_near_identical_no_action` | near_identical + boot_p=0.47 → `"no_action_default"` |
| T15: `test_route_near_identical_escalate` | near_identical + boot_p=0.72 → `"escalate_event_review"` (anomalous) |
| T16: `test_route_borderline_always_escalate` | borderline → `"escalate_full_manual_review"` regardless of diagnostics |
| T17: `test_route_materially_different_consensus_fail` | materially_different + consensus_ok=False → `"escalate_event_review"` |

### 4.5 Markdown template test (T18)

| Test | Assertion |
|------|-----------|
| T18: `test_markdown_template_has_blank_human_section` | `render_review_template()` output contains "Decision: ___" and "Reasoning:" with blank fields, and does NOT contain any pre-filled decision value |

### 4.6 Phase 4 summary

| File | Tests | Purpose |
|------|-------|---------|
| `validation/tests/test_inference_role_semantics.py` | T1–T7 (7) | Gate retirement, alignment |
| `research/tests/test_pair_diagnostic.py` | T8–T18 (11) | Harness schema, classification, routing, template |

Total: **18 new tests**.

---

## Phase 5: Wording Cleanup in Reports/Docs

### 5A. Qualify simulation-only coverage claims

**File**: `research_reports/02_inference_stack_audit.md`, §4.1 and §4.2

Add to each:
```
*Caveat*: Coverage and Type I error were validated under a Student-t(3)
generator that lacks volatility clustering and has ~2× lower vol-of-vol
than real BTC 4H data (Report 03). These results confirm the methods'
mathematical correctness but should not be extrapolated as blanket
real-BTC guarantees. On real data, the bootstrap CI width on control
pairs (Report 18) is the binding constraint on power.
```

### 5B. Check p-value wording

Reports 02, 18 already state `p_a_better` is not a p-value. No changes
needed.

### 5C. Permutation test scope

Report 02 §1.4 and MEMORY.md already scope permutation to
component-level. No changes needed.

### Phase 5 summary

| Item | File | LOC changed | Risk |
|------|------|-------------|------|
| 5A. Qualify sim claims | `research_reports/02_inference_stack_audit.md` | ~8 | None |
| 5B–5C | None needed | 0 | None |

---

## 4. Machine-Only Pair Diagnostic Design (Summary)

### Layer A: `PairDiagnosticResult` (machine output)

| Property | Description |
|----------|-------------|
| Computed by | `run_pair_diagnostic()` |
| Contains | profile, classification, bootstrap, subsampling, DSR, consensus, caveats, suggested route |
| Does NOT contain | `decision`, `decision_reasoning`, `promote`, `reject`, any judgment |
| Output formats | frozen dataclass → JSON, markdown template (Section 1) |
| Authority | ZERO. Cannot promote, reject, or make any binding decision. |

### Layer B: Human Review Note (separate artifact)

| Property | Description |
|----------|-------------|
| Written by | Researcher, after reading Layer A output |
| Contains | `decision`, `reasoning`, `tradeoff_summary`, `unresolved_concerns` |
| Format | Markdown (Section 2 of the review template) |
| Storage | Saved alongside the Layer A JSON as the audit trail |
| Authority | SOLE decision authority. Only the researcher can promote/reject. |

### Separation enforcement

- `PairDiagnosticResult` is a frozen dataclass — fields cannot be added
  at runtime
- No field in the dataclass accepts decision-like values
- JSON schema test (T9) verifies no decision keys exist
- Markdown template test (T18) verifies Section 2 is blank
- The harness function signature returns `PairDiagnosticResult`, not a
  tuple or dict that could smuggle a decision

---

## 5. Human Review Note Design

The researcher fills in Section 2 of the markdown template. The
structure is:

```python
# This is NOT in pair_diagnostic.py — it is documentation only.
# The researcher writes this manually in the markdown file.

class HumanReviewNote:   # conceptual, not implemented as code
    decision: str        # "NO_ACTION" | "INCONCLUSIVE" | "PROMOTE" | "REJECT"
    reasoning: str       # free-text, must cite Section 1 values
    tradeoff_summary: str  # e.g., "Sharpe +0.34 but MDD +13pp"
    unresolved_concerns: str  # e.g., "power insufficient for this effect size"
```

This is a markdown template, not a Python dataclass. The researcher
edits the markdown file directly. No code enforces the structure —
it is a convention.

---

## 6. Suggested Review Route Logic (Summary)

| Pair class | Condition | Route | Meaning |
|------------|-----------|-------|---------|
| near_identical | boot_p ≈ 0.50 (normal) | `no_action_default` | Nothing to investigate |
| near_identical | boot_p deviates > 15pp from 0.50 | `escalate_event_review` | Anomalous signal on null pair |
| borderline | any | `escalate_full_manual_review` | Researcher must determine if data is informative |
| materially_different | consensus fails | `escalate_event_review` | Method disagreement needs investigation |
| materially_different | >2 caveats | `escalate_full_manual_review` | Multiple warnings |
| materially_different | consensus OK, ≤2 caveats | `inconclusive_default` | Standard power-limited result |

**Non-binding**: the route is a label printed in the report. The
researcher may override it. No code path checks the route for
promote/reject logic.

---

## 7. Test Plan

### 7.1 Existing tests to verify (no change expected)

| Test file | Count | Expected |
|-----------|-------|----------|
| `v10/tests/test_bootstrap.py` | 16 | All pass |
| `v10/tests/test_subsampling.py` | 9 | All pass |
| `validation/tests/test_acceptance.py` | 7 | All pass |
| `validation/tests/test_decision_payload.py` | 2 | All pass |

### 7.2 Existing tests to update (Phase 3)

| Test file | Test | Change |
|-----------|------|--------|
| `v10/tests/test_decision.py` | `test_hold_when_not_promoted` | If relies on bootstrap failure → switch trigger |
| `v10/tests/test_decision.py` | any asserting `"bootstrap_gate_failed"` | Remove/update assertion |

### 7.3 New tests

| File | Count | Phase |
|------|-------|-------|
| `v10/tests/test_bootstrap.py` | +1 (alignment) | 1 |
| `research/tests/test_pair_diagnostic.py` | +11 (T8–T18) | 2 |
| `validation/tests/test_inference_role_semantics.py` | +7 (T1–T7) | 4 |

**Total new tests**: 19.

### 7.4 Regression run

```bash
pytest v10/tests/test_bootstrap.py v10/tests/test_subsampling.py \
       v10/tests/test_decision.py \
       research/tests/test_pair_diagnostic.py \
       validation/tests/ \
       -v --tb=short
```

---

## 8. Rollback Risks

| Phase | Rollback method | Risk if reverted | Side effects |
|-------|----------------|-----------------|-------------|
| 1 | `git revert` safety/doc commits | Silent truncation returns (pre-existing hazard). Warning comments removed. | None beyond restoring pre-existing state |
| 2 | Delete `research/lib/pair_diagnostic.py` + test file | Researcher returns to manual workflow. No existing code affected. | None — new files only |
| 3 | `git revert` decision.py + subsampling.py | Bootstrap gate regains veto (but cannot pass on any pair anyway) | Test updates must also be reverted |
| 4 | Delete `test_inference_role_semantics.py` | Lose regression coverage | No code impact |
| 5 | `git revert` report edits | Unqualified simulation claims return | No code impact |

**Overall**: each phase independently revertible. No irreversible state.

---

## 9. Recommended Implementation Order

```
Phase 1A  (bootstrap alignment)     ← Safety fix, zero risk
Phase 1B  (relabel p_a_better)      ← Docstring only
Phase 1C  (subsampling caveat)      ← Docstring only
Phase 1D  (V2 ban warning)          ← Comment only
Phase 1E  (DSR conventions)         ← Docstring only
  ↓
Phase 2   (pair diagnostic harness) ← New module, zero existing-code risk
          + Phase 2 unit tests
  ↓
Phase 3A  (bootstrap gate → diag)   ← Gate behavior change
Phase 3B  (subsampling → info)      ← Suite status change
  ↓
Phase 4   (regression tests)        ← Lock in all new semantics
  ↓
Phase 5   (report wording)          ← Lowest priority
```

**Rationale**:
1. Safety/doc fixes first — zero risk, immediate value.
2. Harness second — new module with its own tests, no existing code
   touched. Provides the automation layer before gate semantics change.
3. Gate retirement third — behavioral changes with test updates.
   Harness is already in place to verify.
4. Regression tests fourth — lock in all behavioral invariants.
5. Wording last — zero code risk, lowest priority.

**Estimated LOC**: ~65 changed (existing files) + ~450 new (harness +
tests).

---

## Appendix: File Index

| File | Phase | Change type |
|------|-------|------------|
| `v10/research/bootstrap.py` | 1A, 1B | Alignment check, docstring |
| `v10/research/subsampling.py` | 1C | Docstring |
| `validation/suites/bootstrap.py` | 1B | Inline comment |
| `validation/suites/subsampling.py` | 1C, 3B | Docstring, status logic |
| `validation/suites/selection_bias.py` | 1E | Documentation block |
| `research/lib/dsr.py` | 1E | Docstring |
| `research/e5_validation.py` | 1D | Warning comment |
| `research/trail_sweep.py` | 1D | Warning comment |
| `validation/decision.py` | 3A | Gate logic (severity, failures) |
| `research/lib/pair_diagnostic.py` | 2 | **NEW** — pair diagnostic harness |
| `research_reports/02_inference_stack_audit.md` | 5A | Qualification text |
| `v10/tests/test_bootstrap.py` | 1A | +1 alignment test |
| `v10/tests/test_decision.py` | 3A | Update gate expectations |
| `research/tests/test_pair_diagnostic.py` | 2 | **NEW** (+11 unit tests) |
| `validation/tests/test_inference_role_semantics.py` | 4 | **NEW** (+7 tests) |

---

*Revised patch plan complete. Five phases, 15 files, ~515 LOC total.
Maximal automation of mechanical pair-review work.
Zero automated promote/reject authority.
Tolerance-based pair classification (3-tier).
19 new regression tests.*
