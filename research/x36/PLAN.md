# X36 — Master Plan

`x36` is now a **research family** with one frozen historical branch and one active
diagnostic branch.

## Frozen Inputs

The active branch is allowed to read, but not modify:

- `results/full_eval_e5_ema21d1/`
- `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml`
- `configs/vtrend/vtrend_default.yaml`
- `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- `resource/**/*`
- `branches/a_vcbb_bias_study/**/*`

## Active Question

Determine whether the current `wfo_robustness` fail of `E5+EMA21D1` is better explained
by:

1. true temporal instability of the strategy, or
2. sensitivity to the currently-frozen WFO split design.

## Active Branch

| Branch | Path | Purpose | Status |
|---|---|---|---|
| `a_vcbb_bias_study` | [branches/a_vcbb_bias_study/PLAN.md](branches/a_vcbb_bias_study/PLAN.md) | Frozen legacy comparison branch | FROZEN |
| `b_e5_wfo_robustness_diagnostic` | [branches/b_e5_wfo_robustness_diagnostic/PLAN.md](branches/b_e5_wfo_robustness_diagnostic/PLAN.md) | Current-run autopsy + frozen split sensitivity | ACTIVE |

## Program Note

- [program/01_segmentation_verdict_note.md](program/01_segmentation_verdict_note.md)
- [program/02_methodology_consistency_audit.md](program/02_methodology_consistency_audit.md)
- [program/03_repo_wfo_sanity_check.md](program/03_repo_wfo_sanity_check.md)
- [program/04_wfo_power_authority_reform.md](program/04_wfo_power_authority_reform.md)
- [program/05_root_patch_blueprint.md](program/05_root_patch_blueprint.md)

## Branch Dependency Graph

```
canonical rerun artifacts
        │
        ▼
phase 0 freeze + provenance capture
        │
        ▼
phase 1 canonical-window autopsy
        │
        ▼
phase 2 frozen split-sensitivity menu
        │
        ▼
phase 3 branch verdict
```

## Root Hygiene

- No new output may be written into `branches/a_vcbb_bias_study/`.
- No new output may be written into `resource/`.
- Root `results/` is index-only.
- Canonical output for the active branch lives only in its own `results/`.
