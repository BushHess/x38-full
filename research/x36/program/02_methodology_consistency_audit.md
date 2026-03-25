# X36 Program Note 02 — Methodology Consistency Audit

**Date**: 2026-03-17  
**Scope**: `research/x36/` excluding `resource/`

## Outcome

`x36` now splits cleanly into two methodological roles:

1. `branches/b_e5_wfo_robustness_diagnostic/`:
   active diagnostic branch, intended to mirror the current validation WFO logic as
   closely as possible for the frozen `2026-03-16` rerun.
2. `branches/a_vcbb_bias_study/`:
   historical comparison branch, useful as legacy research context but **not** an
   authority source for current validation semantics.

## Verified Active-Branch Facts

- The active branch reproduces the canonical `results/full_eval_e5_ema21d1`
  `wfo_summary.json` exactly on the frozen canonical split.
- The canonical source run has:
  - `n_windows_valid = 8`
  - `n_windows_power_only = 8`
  - `low_trade_windows_count = 0`
  - `invalid_windows_count = 0`
- Therefore the current branch verdict is based on a genuinely high-power WFO case,
  not on a delegated `trade_level_bootstrap` case.

## Active-Branch Guardrail

The active runner must not silently score low-power splits as ordinary WFO PASS/FAIL.
Current branch code therefore treats `valid_window`, `low_trade_window`,
`stats_power_only`, and `wfo_low_power` as first-class state. If a preregistered
split becomes low-power, the result must be interpreted as unresolved unless a new
branch explicitly adds trade-level evidence.

## Legacy-Branch Caveats

The legacy VCBB branch contains several items that should be read as branch-local
historical analysis, not current validation policy:

- `README.md` and `results/CONCLUSIONS.md` were written as narrative summaries and
  can lag the raw CSV/JSON artifacts.
- Section 4 WFO in `METHODOLOGY.md` is descriptive branch-local segmentation, not the
  current validation gate. It does not implement candidate-vs-baseline delta scoring,
  Wilcoxon/CI authority, invalid-window filtering, or low-power delegation.
- The final branch-local WFO window is `2025-01-01 -> 2026-02-20` (416 days), so the
  branch-local claim "`12 × 6-month windows`" is not literally true.
- Branch-local holdout `2024-01-01 -> 2026-02-20` overlaps later WFO windows, so
  holdout and WFO evidence are not independent there.
- Current repo validation treats PSR as diagnostic/info-only; it is not a binding
  gate for PROMOTE/HOLD in the current decision policy.
- Wilcoxon significance over synthetic bootstrap paths in the legacy test battery
  should be read as branch-local paired-resample evidence, not as an independent
  real-market p-value.

## Authority Order

For current validation semantics, use this order:

1. `validation/suites/*.py`
2. `validation/decision.py`
3. `docs/validation/decision_policy.md`
4. active branch artifacts under `branches/b_e5_wfo_robustness_diagnostic/results/`

For the legacy branch, quantitative authority is:

1. `results/*.csv`
2. `results/*.json`
3. `results/comparison_report.md`

`results/CONCLUSIONS.md` remains a historical interpretation note, not the numeric
source of truth.
