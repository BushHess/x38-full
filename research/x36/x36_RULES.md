# X36 — Branch Isolation Rules

**Kế thừa**: [`../../CLAUDE.md`](../../CLAUDE.md) → [`../../docs/research/RESEARCH_RULES.md`](../../docs/research/RESEARCH_RULES.md) → file này.

---

## 1. Write Zone

`x36` current write zone is:

```
research/x36/README.md
research/x36/PLAN.md
research/x36/manifest.json
research/x36/x36_RULES.md
research/x36/program/**/*
research/x36/shared/**/*
research/x36/branches/**/*
research/x36/code/**/*
research/x36/results/**/*
```

No exceptions outside `research/x36/`.

## 2. Read-Only Legacy Subtrees

The following `x36` paths are frozen inputs and must not be modified by current work:

```
research/x36/resource/**/*
research/x36/branches/a_vcbb_bias_study/**/*
```

## 3. External Read-Only Inputs

The active branch may read:

- `results/full_eval_e5_ema21d1/**/*`
- `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml`
- `configs/vtrend/vtrend_default.yaml`
- `data/bars_btcusdt_2016_now_h1_4h_1d.csv`

These are frozen upstream inputs. They must never be edited by `x36`.

## 4. Architecture

`x36` uses the following structure:

```
x36/
├── README.md
├── PLAN.md
├── manifest.json
├── x36_RULES.md
├── program/                 ← program-level notes
├── resource/                ← frozen source material
├── shared/                  ← shared helpers for current branches
├── branches/                ← branch-local code/results
│   ├── a_vcbb_bias_study/   ← frozen legacy branch
│   └── b_e5_wfo_robustness_diagnostic/
├── code/                    ← root wrappers only
└── results/                 ← root index only
```

Rules:

1. `shared/` contains reusable helpers for current `x36` branches.
2. `branches/<branch>/code/` contains branch-local runners.
3. `branches/<branch>/results/` is the canonical output location.
4. Root `code/` contains wrappers only.
5. Root `results/` contains index-only docs, not canonical branch outputs.

## 5. Branch Structure

Every new non-legacy branch under current `x36` must follow:

```
branches/<branch_name>/
├── PLAN.md
├── code/
│   ├── __init__.py
│   └── run_<branch_name>.py
└── results/
```

Optional helper modules stay inside that branch or in `shared/`.

`branches/a_vcbb_bias_study/` is a grandfathered frozen branch. It is exempt from the
normalized branch layout, but it is still read-only.

## 6. Scope Freeze for Current Branch

Frozen legacy branch: `a_vcbb_bias_study`

Current active branch: `b_e5_wfo_robustness_diagnostic`

Frozen question:

> Diagnose the current `2026-03-16` WFO soft-fail of `E5+EMA21D1` without changing
> strategy logic, validation logic, dataset, or canonical result directories.

Frozen branch tasks:

1. Capture provenance of the canonical rerun.
2. Recompute and autopsy the canonical WFO windows locally.
3. Run a **small preregistered split menu** locally.
4. Emit a branch-local verdict.

## 7. Frozen Split Menu

The current branch is only allowed to test these WFO designs:

| Tag | Train | Test | Slide | Window cap |
|---|---:|---:|---:|---:|
| `canonical_24_6_last8` | 24m | 6m | 6m | 8 |
| `short_horizon_24_3_last12` | 24m | 3m | 3m | 12 |
| `long_horizon_24_9_last6` | 24m | 9m | 9m | 6 |
| `canonical_24_6_all` | 24m | 6m | 6m | none |

Freeze note:

- The current repo WFO suite does not retrain per window.
- Therefore `train_months` by itself is not a reliable perturbation axis for branch
  diagnostics once `lastN` truncation is applied.
- Allowed alternatives must change the OOS segmentation itself, not only the nominal
  training span.

No extra WFO grid may be added without explicitly editing this file and the branch
`PLAN.md` before running.

## 8. Branch Verdict Freeze

The current branch uses the following frozen interpretation:

- `LIKELY_TRUE_INSTABILITY`:
  canonical config fails and at least 2 of 3 alternative split specs also fail.
- `LIKELY_DESIGN_SENSITIVE_FAIL`:
  canonical config fails and at least 2 of 3 alternative split specs pass.
- `MIXED_EVIDENCE`:
  any other outcome.

This verdict is branch-local only. It is not allowed to overwrite repo-wide strategy
status documents.

## 9. Execution Hygiene

Every runnable file in current `x36` must:

1. insert repo root into `sys.path` locally;
2. write only inside its own branch `results/`;
3. preserve upstream artifact paths as read-only;
4. record provenance of any external inputs it consumes.

## 10. No Contamination Clauses

The current branch must not:

- modify `validation/`
- modify `strategies/`
- modify `v10/`
- modify `results/full_eval_e5_ema21d1/`
- modify `research/x36/branches/a_vcbb_bias_study/`
- modify `research/x36/resource/`

Any future experiment that requires those changes is **out of scope** for current `x36`.
