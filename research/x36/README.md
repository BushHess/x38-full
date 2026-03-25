# X36 — Path Robustness Research Family

**Status**: ACTIVE  
**Frozen legacy branch**: `branches/a_vcbb_bias_study/`  
**Current active branch**: `branches/b_e5_wfo_robustness_diagnostic/`  

---

## Scope

`x36` now has two branch layers:

- `branches/a_vcbb_bias_study/` — frozen comparison study for V3/V4 vs `E5+EMA21D1`
- `branches/b_e5_wfo_robustness_diagnostic/` — tightly scoped follow-on diagnostic

The current branch does **not** reopen the original VCBB comparison. It diagnoses the
current `2026-03-16` WFO soft-fail of `E5+EMA21D1` using branch-local runners and
branch-local outputs only.

## Why this exists

The repo now contains a newer validation rerun where `E5+EMA21D1` remains strong on
full-sample and holdout, but fails `wfo_robustness`. The current branch asks:

> Is that fail more consistent with true temporal instability, or with sensitivity to
> the current WFO split design?

This question belongs in `x36` because the family already treats path-robustness,
window stability, and bootstrap evidence as the core research object.

## Active Branch Index

| Branch | Path | Role | Status |
|---|---|---|---|
| Legacy VCBB study | [`branches/a_vcbb_bias_study/`](branches/a_vcbb_bias_study/PLAN.md) | Frozen historical comparison branch | FROZEN |
| WFO diagnostic | [`branches/b_e5_wfo_robustness_diagnostic/`](branches/b_e5_wfo_robustness_diagnostic/PLAN.md) | Current-run autopsy + frozen split sensitivity | ACTIVE |

## Root Layout

```
x36/
├── README.md
├── PLAN.md
├── manifest.json
├── x36_RULES.md
├── program/                 ← program-level notes
├── resource/                ← frozen source material (read-only)
├── shared/                  ← helpers for active x36 branches
├── branches/                ← branch-local code + results
│   ├── a_vcbb_bias_study/   ← frozen legacy branch
│   └── b_e5_wfo_robustness_diagnostic/
├── code/                    ← root convenience wrappers only
└── results/                 ← root index only
```

## Authority

| Topic | Source of truth |
|---|---|
| Branch isolation rules | [x36_RULES.md](x36_RULES.md) |
| Current branch prereg | [branches/b_e5_wfo_robustness_diagnostic/PLAN.md](branches/b_e5_wfo_robustness_diagnostic/PLAN.md) |
| Program interpretation note | [program/01_segmentation_verdict_note.md](program/01_segmentation_verdict_note.md) |
| Program consistency audit | [program/02_methodology_consistency_audit.md](program/02_methodology_consistency_audit.md) |
| Repo-wide WFO sanity check | [program/03_repo_wfo_sanity_check.md](program/03_repo_wfo_sanity_check.md) |
| WFO power reform spec | [program/04_wfo_power_authority_reform.md](program/04_wfo_power_authority_reform.md) |
| Future root patch blueprint | [program/05_root_patch_blueprint.md](program/05_root_patch_blueprint.md) |
| Branch outputs | `branches/b_e5_wfo_robustness_diagnostic/results/` |
| Legacy x36 narrative snapshot | [branches/a_vcbb_bias_study/results/CONCLUSIONS.md](branches/a_vcbb_bias_study/results/CONCLUSIONS.md) |
