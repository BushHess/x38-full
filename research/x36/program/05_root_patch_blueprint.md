# X36 Program Note 05 — Root Patch Blueprint for WFO Reform

**Date**: 2026-03-17  
**Scope**: implementation guide for a future root-code session; no root edits here

## Goal

Translate Program Note 04 into concrete root patches without changing frozen `x36`
artifacts or re-litigating branch conclusions.

## Patch Objective

Future root implementation should:

1. preserve existing `wfo_low_power` delegation behavior,
2. add a distinct `underresolved` evidence state,
3. add a distinct `negative_confirmed` evidence state,
4. stop conflating "no positive confirmation" with "evidence of instability".

## File-by-File Patch Map

### 1. `validation/suites/wfo.py`

Required changes:

- Keep current greater-side Wilcoxon and bootstrap-lower logic.
- Add negative-side evidence:
  - `wilcoxon_less`
  - existing `bootstrap_ci.ci_upper` already exists and can support
    `bootstrap_ci_upper < 0`
- Emit a new summary field:
  - `evidence_state`
  - allowed values:
    - `positive_confirmed`
    - `negative_confirmed`
    - `underresolved`
    - `delegated_low_power`
- Emit explicit booleans for clarity:
  - `wfo_low_power`
  - `positive_confirmed`
  - `negative_confirmed`
  - `underresolved`
- Preserve backward compatibility:
  - keep existing `wilcoxon` payload as alias to the current greater-side test
  - keep existing `bootstrap_ci` payload

Important:

- suite `status` should no longer be the only carrier of semantics
- `status=fail` is too coarse for underresolved vs negative-confirmed

Recommended direction:

- keep suite `status` conservative for backward compatibility if needed
- move authority-bearing interpretation to `summary.evidence_state`

### 2. `validation/decision.py`

Required changes:

- Continue computing `wfo_low_power` exactly as today.
- If `wfo_low_power=True`:
  - keep unconditional WFO pass
  - keep delegation to `trade_level_bootstrap`
- Otherwise consume `summary.evidence_state`.

Recommended decision mapping:

- `positive_confirmed`
  - `wfo_robustness` gate PASS
- `negative_confirmed`
  - `wfo_robustness` gate FAIL
  - failure code: `wfo_negative_confirmed`
  - reason text should say candidate underperforms baseline on paired OOS evidence
- `underresolved`
  - `wfo_robustness` gate FAIL
  - failure code: `wfo_underresolved`
  - reason text should say positive OOS delta not confirmed and inferiority not confirmed

Important:

- keep HOLD as the conservative exit for both `negative_confirmed` and `underresolved`
- do not upgrade `underresolved` into PROMOTE
- the reform is semantic/authority cleanup, not a permissive shortcut

### 3. `validation/report.py`

Required changes:

- Render `evidence_state` explicitly in the WFO section and gate summary.
- Distinguish report wording:
  - `negative_confirmed`: "candidate worse than baseline on paired OOS evidence"
  - `underresolved`: "WFO did not confirm positive OOS delta; inferiority also not confirmed"
  - `delegated_low_power`: "WFO low-power; authority delegated to trade-level bootstrap"
- Preserve existing numeric diagnostics:
  - greater-side `wilcoxon_p`
  - `bootstrap_ci_lower`
  - optionally also show:
    - `wilcoxon_less_p`
    - `bootstrap_ci_upper`

### 4. `docs/validation/decision_policy.md`

Required changes:

- Rewrite `wfo_robustness` section around evidence states, not binary fail wording.
- Clarify:
  - `low_power` is a trade-coverage delegation rule
  - `underresolved` is an inference-state classification
  - these are different concepts
- Document that current paired WFO authority has three non-error outcomes:
  - positive-confirmed
  - underresolved
  - delegated-low-power
  plus negative-confirmed for adverse evidence

### 5. `validation/thresholds.py`

Required changes:

- Keep `WFO_WILCOXON_ALPHA = 0.10` unless future independent calibration disproves it.
- Fix stale explanatory comment claiming `N=8` requires `W+ >= 30/36`; actual exact
  passing cutoff at current alpha is `W+ >= 28/36`.
- If desired, add a comment explicitly stating:
  - alpha tuning is not the intended remedy for underresolved small-`N` cases

### 6. Tests

Add or update tests in:

- `validation/tests/test_decision_authority.py`
- `validation/tests/test_runner_payload_contract_e2e.py`
- `validation/tests/test_wfo_power_only_and_seed.py`
- `validation/tests/test_wfo_summary_json_valid.py`
- `validation/tests/test_decision_payload.py`

Recommended new coverage:

1. non-low-power + positive-confirmed -> WFO PASS
2. non-low-power + negative-confirmed via `bootstrap_ci_upper < 0` -> WFO FAIL
3. non-low-power + underresolved -> WFO FAIL with `wfo_underresolved`
4. low-power + missing trade-level payload -> existing failsafe still holds
5. backward compatibility for legacy summaries lacking new fields

## Acceptance Criteria

A future root patch should satisfy all of the following:

1. canonical `E5+EMA21D1` no longer reads as implied instability
2. canonical `E5+EMA21D1` still does **not** become a WFO PASS
3. low-power delegation behavior remains unchanged
4. a clearly negative synthetic case still emits real WFO failure
5. current frozen `x36` conclusions remain consistent with root semantics

## Rollout Order

Recommended order for the future implementation session:

1. update `docs/validation/decision_policy.md`
2. patch `validation/suites/wfo.py`
3. patch `validation/decision.py`
4. patch `validation/report.py`
5. update tests
6. rerun targeted validation suite
7. rerun one canonical sample (`E5`) and one clearly weak strategy

## Explicit Non-Goals

- No rewrite of `research/x36/branches/a_vcbb_bias_study/`
- No modification of frozen `results/full_eval_e5_ema21d1/`
- No adaptive search over new WFO split menus inside root validation
- No use of full-sample bootstrap or PSR to bypass paired OOS WFO semantics

## Bottom Line

The future root patch should be a terminology-and-authority correction, not a hidden
threshold relaxation.

`E5+EMA21D1` is the motivating example, but the patch should be generic:

- positive evidence -> PASS
- negative evidence -> FAIL
- no positive and no negative confirmation -> UNDERRESOLVED HOLD
- low trade power -> delegate to trade-level evidence
