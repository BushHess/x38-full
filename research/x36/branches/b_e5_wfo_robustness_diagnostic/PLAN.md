# b_e5_wfo_robustness_diagnostic — Current WFO Failure Diagnostic

**Status**: ACTIVE  
**Runner**: `code/run_b_e5_wfo_robustness_diagnostic.py`

---

## Objective

Diagnose the current `2026-03-16` `wfo_robustness` soft-fail of `E5+EMA21D1`
without modifying:

- strategy logic,
- validation logic,
- canonical result directories,
- or any file outside `research/x36/`.

## Frozen Inputs

- Canonical rerun: `results/full_eval_e5_ema21d1/`
- Candidate config: `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml`
- Baseline config: `configs/vtrend/vtrend_default.yaml`
- Data: `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- Cost: `harsh` = 50 bps RT

## Phase Menu

### Phase 0 — Artifact Freeze

Capture provenance from the canonical rerun:

- timestamp
- start/end dates
- current verdict
- canonical WFO summary

Deliverables:

- `results/phase0_artifact_freeze.json`
- `results/phase0_artifact_freeze.md`

### Phase 1 — Canonical Window Autopsy

Recompute the canonical `24m / 6m / slide 6m / last 8 windows` locally and:

- verify window deltas reproduce the stored WFO summary;
- isolate the failing windows;
- summarize candidate vs baseline per failed window;
- summarize trade profile per failed window.

Deliverables:

- `results/phase1_canonical_window_autopsy.json`
- `results/phase1_canonical_window_autopsy.md`

### Phase 2 — Frozen Split Sensitivity

Run this exact frozen menu only:

| Tag | Train | Test | Slide | Window cap |
|---|---:|---:|---:|---:|
| `canonical_24_6_last8` | 24m | 6m | 6m | 8 |
| `short_horizon_24_3_last12` | 24m | 3m | 3m | 12 |
| `long_horizon_24_9_last6` | 24m | 9m | 9m | 6 |
| `canonical_24_6_all` | 24m | 6m | 6m | none |

Rationale freeze:

- The repo WFO suite does not retrain per window; it evaluates fixed configs over
  test slices.
- Changing `train_months` alone can therefore collapse to the same terminal
  `test_start/test_end` sequence when `lastN` windows are selected.
- This menu varies the actual OOS segmentation axis instead: shorter horizon,
  longer horizon, and full-sample window count.
- Any split that becomes `wfo_low_power` is **not** allowed to be labeled pass/fail
  from WFO alone; branch-local runner must mark it unresolved unless paired
  trade-level evidence is explicitly added in a new prereg.

No adaptive split search is allowed beyond this menu.

Deliverables:

- `results/phase2_split_sensitivity.json`
- `results/phase2_split_sensitivity.md`

### Phase 3 — Branch Verdict

Frozen branch verdict rule:

- `LIKELY_TRUE_INSTABILITY`:
  canonical fails and at least 2 of 3 alternative split specs also fail.
- `LIKELY_DESIGN_SENSITIVE_FAIL`:
  canonical fails and at least 2 of 3 alternative split specs pass.
- `MIXED_EVIDENCE`:
  all other cases.

Deliverables:

- `results/final_verdict.json`
- `results/final_verdict.md`

## Non-Goals

- No new bootstrap family here.
- No new regime-conditioned resampling here.
- No edits to `branches/a_vcbb_bias_study/`.
- No edits to `validation/`.
- No new strategy variant.
