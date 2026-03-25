# X36 Program Note 01 — Segmentation Verdict Interpretation

**Date**: 2026-03-17  
**Applies to**: `branches/b_e5_wfo_robustness_diagnostic/`

## Scope

This note records how the current x36 branch verdict should be interpreted.

It is a program-level interpretation note only. It does not overwrite:

- repo-wide strategy status,
- validation policy,
- or canonical validation artifacts under `results/full_eval_e5_ema21d1/`.

## Frozen Facts

The branch locally reproduces the canonical WFO rerun exactly:

- `5/8` positive windows
- mean delta score `12.4563`
- Wilcoxon `p=0.125`
- bootstrap CI `[-3.4378, 29.279]`

The branch then evaluates the preregistered split menu:

- `canonical_24_6_last8` -> `FAIL`
- `short_horizon_24_3_last12` -> `FAIL`
- `long_horizon_24_9_last6` -> `PASS`
- `canonical_24_6_all` -> `PASS`

Branch verdict: `LIKELY_DESIGN_SENSITIVE_FAIL`.

## Interpretation

Current evidence is more consistent with **sensitivity to OOS segmentation design**
than with a strong claim of **true temporal instability**.

This conclusion is justified by three observations:

1. The branch reproduces the canonical fail exactly, so the issue is not a local
   calculation mismatch.
2. The fail does not persist across the majority of preregistered alternative
   segmentations.
3. A shorter-horizon segmentation still fails, so the evidence is not clean enough to
   claim the canonical fail is spurious.

Therefore the correct reading is:

- not `bug`,
- not `proof of true instability`,
- but `diagnostic evidence that the current fail is segmentation-sensitive`.

## Program Consequence

This note supports using the x36 result as a **research diagnostic** for future
evaluation-design review.

This note does **not** support:

- promoting `E5+EMA21D1`,
- downgrading the strategy on x36 evidence alone,
- or editing validation thresholds post hoc.

## Next Acceptable Use

If x36 is extended later, the next valid target is evaluation-design analysis:

- why `24m/6m last8` is harsher than `24m/6m all`,
- why `24m/3m last12` remains unstable,
- and whether future diagnostics should reason in terms of segmentation coverage rather
  than nominal `train_months`.
