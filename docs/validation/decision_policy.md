# Decision Policy

How `validation/decision.py` and `validation/runner.py` produce the **machine
validation verdict** (Tier 2 of the 3-tier authority model).

## Scope and Limits

This document defines **automated machine gates only** (Tier 2). The machine
verdict is evidence, not the final deployment decision.

| Tier | Authority | Document |
|------|-----------|----------|
| 1. Research Screening | `research/xNN/benchmark.py` → SCREEN_PASS/FAIL | Study-specific REPORT.md |
| **2. Machine Validation** | **`validation/decision.py` → PROMOTE/HOLD/REJECT** | **This document** |
| 3. Deployment Decision | Human researcher → DEPLOY/SHADOW/REJECT | `reports/deployment_decision.md` |

Hard gates (lookahead, data integrity, regression) are absolute blockers —
no Tier 3 override. Soft gate HOLD means "automated evidence insufficient",
not "do not deploy". See `pair_review_workflow.md` for Tier 3 process.

## Strategy Nomenclature (updated 2026-03-09)

| Name | strategy_id | ATR type | Status |
|------|-------------|----------|--------|
| E5_ema21D1 (PRIMARY candidate) | `vtrend_e5_ema21_d1` | Robust ATR (Q90-capped) | HOLD (WFO underresolved) |
| E0_ema21D1 | `vtrend_ema21_d1` | Standard ATR(14) | HOLD (WFO FAIL) |
| E0 (baseline) | `vtrend` | Standard ATR(14) | Baseline |

## Exit Codes

- `0`: `PROMOTE`
- `1`: `HOLD`
- `2`: `REJECT`
- `3`: `ERROR`

## Evaluation Order

`evaluate_decision()` runs first, then the runner applies post-decision policies:

1. Any suite with `status="error"` → `ERROR(3)`.
2. `data_integrity` has `hard_fail=True` → `ERROR(3)`.
3. `invariants` has `n_violations > 0` or `status="fail"` → `ERROR(3)`.
4. `regression_guard` has `pass=False` or `status in {"fail","error"}` → `ERROR(3)`.
5. Accumulate all hard and soft gates.
6. Any hard gate fails → `REJECT(2)`.
7. Any soft gate fails (no hard failures) → `HOLD(1)`.
8. All gates pass → `PROMOTE(0)`.

Post-decision runner policies (applied after `evaluate_decision()`):

9. `_apply_quality_policy()` → can elevate to `ERROR(3)` on data_integrity,
   invariants, or regression_guard failure (redundant safety net).
10. `_apply_config_usage_policy()` → can elevate to `ERROR(3)` if strategy
    config contains unused fields (wiring bug detection via `AccessTracker`).
11. `_verify_output_contract()` → can elevate to `ERROR(3)` if required output
    files are missing (pipeline completeness check).

## Hard Gates

### 1. `lookahead`
- Condition: `lookahead` suite `status != "pass"` (when enabled).
- Effect: hard failure → REJECT(2).

### 2. `full_harsh_delta`
- Condition: `backtest.data.deltas.harsh.score_delta < -0.2`.
- Source: `results/full_backtest_summary.csv`.
- Effect: hard failure → REJECT(2).

### 3. `holdout_harsh_delta`
- Condition: `holdout.data.delta_harsh_score < -0.2` (when holdout runs).
- Source: `results/final_holdout_metrics.csv`.
- Effect: hard failure → REJECT(2).

## Soft Gates

### 1. `wfo_robustness`
- When `wfo_low_power` (`power_windows < 3` or `low_trade_ratio > 0.5`):
  gate passes unconditionally; authority delegates to `trade_level_bootstrap`.
- **Primary (since 2026-03-09)**: PASS if EITHER Wilcoxon signed-rank
  `p ≤ 0.10` (with sufficient non-zero pairs) OR Bootstrap CI lower > 0
  (excludes zero). Both `wilcoxon_sufficient` and `bootstrap_excludes_zero`
  use `_strict_bool` to prevent string coercion (added 2026-03-16).
  Binary win-rate demoted to advisory.
- **Legacy fallback** (when `wilcoxon` key absent in WFO summary):
  - When `N ≤ 5`: requires `positive_delta_windows >= N-1`.
  - When `N > 5`: requires `win_rate >= 0.60`.
- Source: `results/wfo_per_round_metrics.csv`, `results/wfo_summary.json`.
- Effect: soft failure → HOLD(1).

### 2. `trade_level_bootstrap` / `trade_level_matched_delta`

Three distinct gate paths (see Report 27 §3.3.1 for the complete 13-path truth table):

a) **`trade_level_bootstrap`** (payload present in `trade_level.data.trade_level_bootstrap`):
   - FAIL when `wfo_low_power=True AND ci_crosses_zero AND is_small_improvement`.
   - PASS in all other cases.

b) **`trade_level_matched_delta`** (payload absent):
   - FAIL when `CI_upper < 0` (any WFO state — not WFO-dependent).
   - PASS when `CI_upper >= 0` and `p_pos` is present.
   - No gate emitted when `CI_upper` is None/>=0 and `p_pos` is None.

c) **`trade_level_bootstrap` missing-payload failsafe**:
   - FAIL when `wfo_low_power=True` and no `trade_level_bootstrap` data.
   - No gate emitted when `wfo_low_power=False` and no bootstrap data.

- Source: `results/matched_trades.csv`, `results/bootstrap_return_diff.json`.
- Effect: soft failure → HOLD(1).

### 3. `selection_bias`

Three sub-checks with distinct roles:

a) **Method fallback check (soft, added 2026-03-16)**: If `requested_method != method`
   or `fallback_reason` is present in the suite payload, the gate unconditionally
   FAILs (soft) regardless of other values. This prevents PROMOTE when the user
   requested PBO but the suite fell back to `none` (e.g. no valid WFO windows,
   insufficient samples). Evaluated FIRST.

b) **PBO overfitting gate (soft, when `method=pbo`)**: Window-level
   candidate-vs-baseline score deltas. Windows where either strategy scores
   ≤ −999,999 (reject sentinel from `compute_objective`, triggered by
   n_trades < 10) are excluded from the `negative_delta_ratio`. Rejected
   window count reported as `n_windows_rejected`.
   PBO pass requires `negative_delta_ratio ≤ 0.5`.
   PBO is an independent overfitting check, decoupled from PSR.
   Only binding when user explicitly requests `method=pbo`; the `deflated`
   method computes PBO as informational side-product but does not gate on it.

c) **PSR diagnostic (info, demoted 2026-03-16)**: PSR (Probabilistic Sharpe
   Ratio, Bailey & López de Prado 2012) treats `sr_benchmark` as a known
   constant, ignoring the baseline's estimation error. For 2-strategy
   comparison this is anti-conservative (underestimates total uncertainty).
   Paired evidence for "candidate beats baseline" is provided by WFO
   Wilcoxon + Bootstrap CI (wfo_robustness gate), not PSR.
   PSR is reported with advisory levels:
   - `>= 0.95`: strong support
   - `0.90–0.95`: moderate support
   - `< 0.90`: warning
   PSR alone does NOT gate PROMOTE, and does NOT block PROMOTE when paired
   OOS evidence is strong.

- Source: `results/selection_bias.json`.
- Effect: method_fallback or PBO fail → soft failure → HOLD(1).
  PSR → info only (diagnostic, no veto power).

## Diagnostic (No Veto Power)

### `bootstrap` (info-only, since Report 21 / Prompt 24)
- `GateCheck(passed=True, severity="info")` unconditionally.
- Values (`p_candidate_better`, `ci_lower`) reported in `deltas` for human review.
- Has NO veto power. See Report 21 §1.1, Report 24B.

### `subsampling` (info-only)
- Not consumed by `evaluate_decision()` at all.
- Suite returns `status="info"`.

## Non-Blocking Suites (Warning Only)

- `cost_sweep`: issues appended to `warnings` by runner.
- `churn_metrics`: issues appended to `warnings` by runner.

## Descriptive Suites (No Decision Participation)

`dd_episodes`, `regime`, `sensitivity`, `overlay` — not consumed by decision engine.

## Post-Decision Runner Policies

### Quality Policy (`_apply_quality_policy`)
Redundant safety net that re-checks `data_integrity`, `invariants`, and
`regression_guard`. Can elevate any verdict to ERROR(3).

### Config Usage Policy (`_apply_config_usage_policy`)
If strategy config has unused fields (tracked by `AccessTracker`), overrides to
ERROR(3). Catches wiring bugs where YAML declares parameters the strategy never
reads.

### Output Contract (`_verify_output_contract`)
If required output files are missing after all suites complete, overrides to
ERROR(3). Final integrity check for pipeline completeness.

## WFO Low-Power Auto-Enable

When WFO detects low power (`power_windows < 3` or `low_trade_ratio > 0.5`):
1. Runner appends `"trade_level"` to suite queue.
2. Sets `cfg.auto_trade_level = True`.
3. WFO gate passes unconditionally.
4. Authority delegates to `trade_level_bootstrap` gate.

## Decision Payload

Runner writes verdict to `reports/decision.json`:
`verdict`, `exit_code`, `deltas`, `failures`, `warnings`, `errors`, `reasons`,
`key_links`, `gates[]`, `trade_level_bootstrap`, `metadata`.
