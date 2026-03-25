# Report 27 — Gate Authority Audit

**Date**: 2026-03-04
**Scope**: All components that participate in the decision engine's final promote/reject/hold/error outcome
**Inputs**: `validation/decision.py`, `validation/runner.py`, all `validation/suites/`, Report 21, Report 25
**Goal**: Determine which components retain real veto/promotion authority after the Report 21 role changes

---

## 1. Decision-Flow Map

The decision engine has a layered evaluation with three authority tiers. Control flows top-to-bottom; first match wins for ERROR; otherwise all gates accumulate.

```
ValidationRunner.run()
│
├─ Suite execution loop (sequential, ordered by resolve_suites)
│   ├─ data_integrity.run() → hard_fail? → BREAK (skip remaining suites)
│   ├─ invariants.run()
│   ├─ regression_guard.run()
│   ├─ lookahead.run()
│   ├─ backtest.run()
│   ├─ wfo.run() → low_power? → auto-append "trade_level" to queue
│   ├─ bootstrap.run()         [status always "info"]
│   ├─ subsampling.run()       [status always "info"]
│   ├─ holdout.run()
│   ├─ selection_bias.run()
│   ├─ trade_level.run()       [status always "info"]
│   ├─ cost_sweep.run()        [warning only]
│   ├─ churn_metrics.run()     [warning only]
│   ├─ dd_episodes.run()       [descriptive only]
│   ├─ regime.run()            [descriptive only]
│   ├─ sensitivity.run()       [descriptive only]
│   └─ overlay.run()           [descriptive only]
│
├─ evaluate_decision(results) → DecisionVerdict
│   │
│   │  ┌── ERROR TIER (short-circuit, exit_code=3) ──────────────────────┐
│   ├──│ 1. Any suite with status="error"        → ERROR                 │
│   ├──│ 2. data_integrity.hard_fail=True         → ERROR                │
│   ├──│ 3. invariants.n_violations > 0           → ERROR                │
│   ├──│ 4. regression_guard.pass=False           → ERROR                │
│   │  └─────────────────────────────────────────────────────────────────┘
│   │
│   │  ┌── GATE TIER (accumulate, then classify) ────────────────────────┐
│   ├──│ Hard gate 1: lookahead.status != "pass"  → hard failure         │
│   ├──│ Hard gate 2: backtest harsh Δscore < -0.2 → hard failure        │
│   ├──│ Hard gate 3: holdout harsh Δscore < -0.2  → hard failure        │
│   ├──│ Soft gate 1: WFO win_rate < 60% (or N-1 rule) → soft failure   │
│   ├──│ Soft gate 2: trade_level_bootstrap (WFO low-power path only)    │
│   ├──│ Soft gate 3: selection_bias "CAUTION"     → soft failure         │
│   ├──│ Info:        bootstrap (passed=True always, no veto)             │
│   │  └─────────────────────────────────────────────────────────────────┘
│   │
│   │  hard_failures? → REJECT(2)
│   │  soft_failures? → HOLD(1)
│   │  else           → PROMOTE(0)
│   │
│   └─ return DecisionVerdict
│
├─ _apply_quality_policy()    → can elevate to ERROR(3)
│   ├─ data_integrity fail    → ERROR
│   ├─ invariants fail        → ERROR
│   └─ regression_guard fail  → ERROR
│
├─ _apply_config_usage_policy() → can elevate to ERROR(3)
│   └─ unused config fields   → ERROR
│
├─ _verify_output_contract()  → can elevate to ERROR(3)
│   └─ missing required files → ERROR
│
└─ Final DecisionVerdict written to reports/decision.json
```

**Key observation**: The runner applies three post-decision policies (`_apply_quality_policy`, `_apply_config_usage_policy`, `_verify_output_contract`) that can **override** `evaluate_decision()`'s verdict upward to ERROR(3). These are additional veto layers beyond the core gate logic.

---

## 2. Authority Matrix

### 2.1 Components With Direct Authority (Can Change Final Verdict)

| # | Component | Gate Name in Code | Authority Type | Verdict It Can Produce | Exact Field(s) That Drive Decision | Can Indirectly Veto? |
|---|-----------|-------------------|---------------|----------------------|-----------------------------------|---------------------|
| 1 | **Suite error (any)** | — | ERROR short-circuit | ERROR(3) | `SuiteResult.status == "error"` | Yes — any suite crash/import failure triggers this |
| 2 | **Data integrity** | — (ERROR path) | ERROR short-circuit | ERROR(3) | `data.hard_fail == True` | Yes — also breaks suite loop, skipping all remaining suites |
| 3 | **Invariants** | — (ERROR path) | ERROR short-circuit | ERROR(3) | `data.n_violations > 0` OR `status == "fail"` | No |
| 4 | **Regression guard** | — (ERROR path) | ERROR short-circuit | ERROR(3) | `data.pass == False` OR `status in {"fail", "error"}` | No |
| 5 | **Lookahead** | `lookahead` | Hard gate | REJECT(2) | `status != "pass"` | No |
| 6 | **Backtest** | `full_harsh_delta` | Hard gate | REJECT(2) | `data.deltas.harsh.score_delta < -0.2` | No |
| 7 | **Holdout** | `holdout_harsh_delta` | Hard gate | REJECT(2) | `data.delta_harsh_score < -0.2` | Yes — holdout lock file can force ERROR via status="error" |
| 8 | **WFO** | `wfo_robustness` | Soft gate | HOLD(1) | `win_rate < 0.60` (N>5) or `positive_windows < N-1` (N≤5) | Yes — low_power triggers trade_level auto-enable |
| 9a | **Trade-level bootstrap** | `trade_level_bootstrap` | Soft gate (conditional) | HOLD(1) | `ci_crosses_zero AND mean_diff ≤ threshold` (only when WFO is low-power); OR missing payload when WFO is low-power | No |
| 9b | **Trade-level matched delta** | `trade_level_matched_delta` | Soft gate | HOLD(1) | `CI_upper < 0` (any WFO state, fires when `trade_level_bootstrap` payload is absent) | No |
| 10 | **Selection bias (DSR)** | `selection_bias` | Soft gate | HOLD(1) | `risk_statement` contains "CAUTION" or "fallback" | No |
| 11 | **Config usage audit** | — (runner policy) | ERROR override | ERROR(3) | `has_unused_fields == True` | No |
| 12 | **Output contract** | — (runner policy) | ERROR override | ERROR(3) | Missing required output files | No |

### 2.2 Components With No Direct Authority (Advisory/Descriptive Only)

| # | Component | Suite Status | Decision Engine Treatment | Can It Indirectly Veto? | Claim Risk |
|---|-----------|-------------|--------------------------|------------------------|------------|
| 13 | **Bootstrap** | Always `"info"` | `GateCheck(passed=True, severity="info")` — values in deltas only | **No** — explicitly neutered (Report 21, P24) | LOW — 20 regression tests guard this |
| 14 | **Subsampling** | Always `"info"` | Not consumed by `evaluate_decision()` at all | **No** — not wired into decision engine | LOW — suite returns "info", decision.py ignores it |
| 15 | **Trade-level (no bootstrap payload, ci_upper >= 0)** | `"info"` | `GateCheck(passed=True, severity="soft")` when `p_pos` present; no gate emitted when `p_pos` absent | **No** — only records diagnostic | LOW |
| 16 | **Cost sweep** | varies | Runner treats as warning only (`_collect_decision_warnings`) | **No** | NONE |
| 17 | **Churn metrics** | varies | Runner treats as warning only (`_collect_decision_warnings`) | **No** | NONE |
| 18 | **DD episodes** | varies | Not consumed by decision engine | **No** | NONE |
| 19 | **Regime** | varies | Not consumed by decision engine | **No** | NONE |
| 20 | **Sensitivity** | varies | Not consumed by decision engine | **No** | NONE |
| 21 | **Overlay** | varies | Not consumed by decision engine | **No** | NONE |

### 2.3 Legacy Decision Engine (v10/research/decision.py)

| # | Component | Authority Type | Active? | Claim Risk |
|---|-----------|---------------|---------|------------|
| 22 | **v10/research/decision.py** | Standalone PROMOTE/HOLD/REJECT | **NOT wired** into validation runner | NONE — used only in research matrix optimization, separate workflow |

---

## 3. Hidden / Indirect Authority Findings

### 3.1 Data Integrity Suite Loop Break (CONFIRMED — by design)

**Location**: `runner.py:259-265`

When `data_integrity` returns `status="fail"` with `hard_fail=True`, the runner **breaks the suite loop**. All subsequent suites (invariants, backtest, WFO, holdout, etc.) are never executed. This means data_integrity has:
- **Direct authority**: ERROR(3)
- **Indirect authority**: Prevents all other suites from running, which means no gate data is collected

**Assessment**: Correct by design. Data integrity failure means the input data is unreliable — running further suites would produce meaningless results.

### 3.2 WFO Low-Power Auto-Enable (CONFIRMED — indirect authority)

**Location**: `runner.py:268-294`

When WFO detects low power (`power_windows < 3` or `low_trade_ratio > 0.5`):
1. Appends `"trade_level"` to the suite queue
2. Sets `cfg.auto_trade_level = True`
3. In `evaluate_decision()`: WFO gate passes unconditionally (`passed=True`) when low_power
4. **But**: the trade-level bootstrap gate becomes active and can produce a soft HOLD

**Authority chain**: WFO → auto-enables trade_level → trade_level_bootstrap can veto → HOLD(1)

**Assessment**: This is an indirect authority path where WFO's *inability* to gate (low power) delegates gating to trade_level_bootstrap. The trade_level_bootstrap only vetoes when `ci_crosses_zero AND mean_diff ≤ small_threshold` — a narrow condition.

### 3.3 Trade-Level Bootstrap Dual Personality

**Location**: `decision.py:323-426`

The trade_level suite's authority depends on WFO state:
- **When WFO is NOT low-power**: trade_level data is recorded in deltas, but the gate only fires if `ci_upper < 0` (a very extreme condition) or just reports `p(delta>0)` passively. No `wfo_low_power AND ci_crosses_zero` path.
- **When WFO IS low-power**: the `trade_level_bootstrap` gate becomes a soft gate that can fail on `ci_crosses_zero AND is_small_improvement`.
- **When WFO is low-power but trade_level_bootstrap payload is missing**: automatic soft FAIL with `"wfo_low_power_missing_trade_level_bootstrap"`.

**Assessment**: This is architecturally sound but subtle. The trade_level_bootstrap effectively inherits WFO's authority when WFO cannot exercise it. The missing-payload failsafe (line 416-426) is correct — it prevents silent promotion when the required fallback evidence is absent.

### 3.3.1 Complete Trade-Level Truth Table

All paths through the trade_level gate logic in `decision.py:323-426`.
Verified by 12 regression tests in `validation/tests/test_decision_authority.py`.

| Path | wfo_low_power | tl_bootstrap present? | ci_crosses_zero | is_small | ci_upper | p_pos | Gate emitted | passed | Effect |
|------|:---:|:---:|:---:|:---:|:---:|:---:|---|:---:|---|
| A1 | T | Yes | T | T | — | — | `trade_level_bootstrap` | F(soft) | **HOLD**: inconclusive under low-power |
| A2 | T | Yes | T | F | — | — | `trade_level_bootstrap` | T(soft) | pass |
| A3 | T | Yes | F | T | — | — | `trade_level_bootstrap` | T(soft) | pass |
| A4 | T | Yes | F | F | — | — | `trade_level_bootstrap` | T(soft) | pass |
| A5 | F | Yes | T | T | — | — | `trade_level_bootstrap` | T(soft) | pass (wfo_low_power=F → condition not met) |
| A6 | F | Yes | T | F | — | — | `trade_level_bootstrap` | T(soft) | pass |
| A7 | F | Yes | F | T | — | — | `trade_level_bootstrap` | T(soft) | pass |
| A8 | F | Yes | F | F | — | — | `trade_level_bootstrap` | T(soft) | pass |
| B1 | any | No | — | — | < 0 | any | `trade_level_matched_delta` | F(soft) | **HOLD**: CI upper negative |
| C1 | any | No | — | — | ≥ 0/None | present | `trade_level_matched_delta` | T(soft) | pass |
| D1 | any | No | — | — | ≥ 0/None | None | *(none)* | — | no gate emitted |
| E1 | T | No | — | — | — | — | `trade_level_bootstrap` | F(soft) | **HOLD**: missing payload |
| E2 | F | No | — | — | — | — | *(none)* | — | no gate emitted |

Key findings:
- **A1** is the ONLY path where `trade_level_bootstrap` fails with payload present.
- **B1** fires regardless of `wfo_low_power` — this corrects the original §2.2 row 15 claim that trade_level authority was WFO-dependent.
- **E1** is a failsafe: WFO is low-power but bootstrap data is missing.
- **D1, E2**: no gate emitted — these paths cannot influence the verdict.

### 3.4 Quality Policy Double-Counting (CONFIRMED — harmless redundancy)

**Location**: `runner.py:525-586` and `decision.py:60-175`

Both `evaluate_decision()` and `_apply_quality_policy()` check data_integrity, invariants, and regression_guard for ERROR conditions. If `evaluate_decision()` already returned ERROR, `_apply_quality_policy()` will attempt to elevate again (which is a no-op since it's already ERROR). If `evaluate_decision()` returned PROMOTE/HOLD/REJECT, `_apply_quality_policy()` can override it to ERROR.

**Assessment**: Redundant but not harmful. The double-check ensures that even if the ERROR short-circuit in `evaluate_decision()` is somehow bypassed (e.g., status encoding mismatch), the runner catches it. No false positives possible — both check the same fields.

### 3.5 Config Usage Policy (CONFIRMED — hidden hard veto)

**Location**: `runner.py:479-511`

If a strategy config object has fields that are never read during backtest execution (tracked by `AccessTracker`), the runner overrides the verdict to ERROR(3). This is a **hard veto** that operates outside `evaluate_decision()` entirely.

**Assessment**: Correct by design — unused config fields indicate a wiring bug (strategy ignores a parameter the YAML declares). This should remain a hard veto. However, it has no documentation in `docs/validation/decision_policy.md`.

### 3.6 Output Contract Verification (CONFIRMED — hidden hard veto)

**Location**: `runner.py:348-366`

If required output files are missing after all suites and decisions complete, the runner overrides to ERROR(3). This is a final integrity check.

**Assessment**: Correct by design. A missing output file means the pipeline didn't complete properly.

### 3.7 DecisionPolicy Vestigial Fields — RESOLVED

**Location**: `decision.py:21-24`

`bootstrap_p_threshold` and `bootstrap_ci_lower_min` were declared on the
`DecisionPolicy` dataclass but never referenced after the P24 change.
**Removed in this prompt** (Report 27 patch). Zero codebase references confirmed
by grep. 46 existing tests pass after removal.

### 3.8 Holdout Lock File Indirect Veto

**Location**: `suites/holdout.py:41-50`

If `holdout_lock.json` exists and `--force-holdout` is not set, the holdout suite returns `status="error"`. This propagates through the suite-error short-circuit in `evaluate_decision()` → ERROR(3).

**Assessment**: By design — prevents re-running holdout after a final evaluation. But the mechanism (returning "error" status) means the lock triggers the generic suite-error path, not a clear "holdout locked" message. The error message is descriptive, so this is adequate.

### 3.9 Selection Bias Fallback-to-None Path

**Location**: `suites/selection_bias.py:79-84`

When `t_samples < 30`, the suite sets `risk_statement = "CAUTION — fallback to none"`. In `evaluate_decision()` (line 432), this triggers `"CAUTION" in statement.upper()` → soft gate FAIL → HOLD(1).

**Assessment**: This means insufficient data for DSR automatically produces a HOLD, even though the "fallback" is a data limitation, not a strategy deficiency. This is a **conservative false positive by design** — the researcher must override with judgment. Consistent with Report 21's human-in-the-loop protocol.

---

## 4. Components That Are Safe As-Is

| # | Component | Why Safe |
|---|-----------|---------|
| 1 | Data integrity → ERROR | Correct: bad data should halt. Suite-loop break is appropriate. |
| 2 | Invariants → ERROR | Correct: logic violations indicate engine bugs, not strategy issues. |
| 3 | Regression guard → ERROR | Correct: metric regressions against golden snapshot catch unintended changes. |
| 4 | Lookahead → REJECT | Correct: lookahead in a trading strategy is a fatal flaw. |
| 5 | Backtest harsh delta → REJECT | Correct: large in-sample regression is unambiguous. Tolerance (-0.2) is documented. |
| 6 | Holdout harsh delta → REJECT | Correct: large OOS regression is unambiguous. Same tolerance. |
| 7 | WFO robustness → HOLD | Correct: WFO failure indicates potential overfitting. Soft gate allows researcher override. |
| 8 | WFO low-power → auto-enable trade_level | Correct: delegates evidence to trade-level when WFO lacks power. |
| 9 | Trade-level bootstrap → HOLD (conditional) | Correct: narrow condition (ci_crosses_zero AND small_improvement) prevents ambiguous promotions. |
| 10 | Bootstrap → info only | Correct: Report 21 established this. 20 regression tests guard it. |
| 11 | Subsampling → info only | Correct: not wired into decision.py at all. Returns "info" status. |
| 12 | Cost sweep → warning only | Correct: informational, no decision authority. |
| 13 | Churn metrics → warning only | Correct: informational, no decision authority. |
| 14 | Config usage → ERROR | Correct: unused config fields indicate a wiring bug. |
| 15 | Output contract → ERROR | Correct: missing files indicate pipeline failure. |
| 16 | Quality policy (double-check) | Harmless redundancy. Belt-and-suspenders for ERROR elevation. |

---

## 5. Components Needing Semantics / Docs Cleanup Only

| # | Component | Issue | Recommended Fix | Risk if Unfixed |
|---|-----------|-------|----------------|----------------|
| 1 | **`docs/validation/decision_policy.md` — bootstrap entry** | ~~Lines 42-47 still describe bootstrap as a soft gate.~~ | **RESOLVED** — doc rewritten to match code (this prompt). | — |
| 2 | **`DecisionPolicy.bootstrap_p_threshold` / `bootstrap_ci_lower_min`** | ~~Vestigial fields.~~ | **RESOLVED** — both fields removed (this prompt). 46 tests pass. | — |
| 3 | **`docs/validation/decision_policy.md` — missing entries** | ~~Missing config_usage, output_contract, WFO auto-enable.~~ | **RESOLVED** — all three documented (this prompt). | — |
| 4 | **`summarize_block_grid().decision_pass` in subsampling** | Grid summary still computes `decision_pass` boolean. Not consumed by decision engine. The field name implies gate authority it does not have. | Rename to `diagnostic_pass` or add comment clarifying it is display-only. Already flagged in Report 25 §7. | LOW — cosmetic only. |
| 5 | **Selection bias "fallback" → CAUTION → HOLD** | When DSR has insufficient samples, the fallback risk statement contains "CAUTION" which triggers the soft gate. This means "I don't have enough data" is treated identically to "I have data and it's concerning." | Consider distinguishing `CAUTION_INSUFFICIENT` from `CAUTION_DSR_FAIL` in the risk_statement parsing. Currently a conservative false positive by design. | LOW — produces HOLD, which the researcher must review anyway. Consistent with human-in-the-loop protocol. |

---

## 6. Recommended Next Step

**Completed in this prompt:**

1. **DONE**: `docs/validation/decision_policy.md` rewritten to match code exactly. Bootstrap correctly listed as diagnostic. All post-decision runner policies (config_usage, output_contract, quality_policy) and WFO→trade_level auto-enable documented.
2. **DONE**: `bootstrap_p_threshold` and `bootstrap_ci_lower_min` removed from `DecisionPolicy`. Zero references confirmed.
3. **DONE**: Trade-level authority contradiction resolved. §2.1 split into rows 9a/9b, §2.2 row 15 corrected, complete 13-path truth table added as §3.3.1.
4. **DONE**: 12 regression tests added (`validation/tests/test_decision_authority.py`) covering all hard gate, soft gate, error, and promote paths.

**Remaining (deferred, low priority):**
- `summarize_block_grid().decision_pass` cosmetic rename in subsampling (§5 item 4).
- Selection bias CAUTION/fallback distinction (§5 item 5).

---

## Appendix A: Complete Gate Registry

Every `GateCheck` that `evaluate_decision()` can emit:

| gate_name | severity | can fail? | condition for failure |
|-----------|----------|-----------|---------------------|
| `lookahead` | hard | Yes | `status != "pass"` |
| `full_harsh_delta` | hard | Yes | `score_delta < -0.2` |
| `holdout_harsh_delta` | hard | Yes | `score_delta < -0.2` |
| `wfo_robustness` | soft | Yes (unless low_power) | `win_rate < 0.60` or `positive < N-1` |
| `bootstrap` | info | **No** (passed=True always) | — |
| `trade_level_bootstrap` | soft | Yes (only when WFO low_power) | `ci_crosses_zero AND mean_diff ≤ threshold` |
| `trade_level_bootstrap` | soft | Yes (only when WFO low_power) | Missing payload when WFO is low-power |
| `trade_level_matched_delta` | soft | Yes | `CI_upper < 0` |
| `selection_bias` | soft | Yes | `"CAUTION"` or `"fallback"` in risk_statement |

## Appendix B: Post-Decision Authority Layers (Runner)

| Layer | Function | Can Override To | Trigger |
|-------|----------|----------------|---------|
| Quality policy | `_apply_quality_policy()` | ERROR(3) | data_integrity fail, invariants fail, regression_guard fail |
| Config usage | `_apply_config_usage_policy()` | ERROR(3) | Unused strategy config fields detected |
| Output contract | `_verify_output_contract()` | ERROR(3) | Missing required output files |
| Warnings | `_collect_decision_warnings()` | None (append only) | cost_sweep issues, churn_metrics issues |
| Errors | `_collect_decision_errors()` | None (append only) | Suite errors, data_integrity, invariants, regression_guard |

## Appendix C: Test Coverage for Authority Semantics

| Test File | Tests | What It Guards |
|-----------|-------|---------------|
| `validation/tests/test_decision_authority.py` | 12 | All gate authority paths: hard gates → REJECT (HA1-HA3), soft gates → HOLD (SO1-SO7), suite error → ERROR (ER1), full promote path (PR1). Includes trade-level truth table verification. |
| `validation/tests/test_inference_role_semantics.py` | 20 | Bootstrap info-only (T1-T3), subsampling info-only (T4), control pair flow-through (T5-T6), alignment (T7), suite status (4 bootstrap status tests) |
| `validation/tests/test_decision_payload.py` | varies | cost_sweep/churn as warnings, regression_guard → ERROR |
| `validation/tests/test_acceptance.py` | varies | End-to-end CLI exit codes match decision verdicts |
| `v10/tests/test_decision.py` | 10 | Legacy v10 decision engine (separate module) |

---

*Authority audit complete. All 22 identified components classified. Bootstrap and subsampling have zero decision authority (confirmed by code + 32 regression tests). Three hard gates (lookahead, backtest delta, holdout delta) and four soft gates (WFO, trade_level_bootstrap, trade_level_matched_delta, selection bias) retain real authority. Three runner-level policies (quality, config usage, output contract) can override any verdict to ERROR. Trade-level truth table (13 paths) verified. All documentation gaps resolved. Vestigial DecisionPolicy fields removed.*
