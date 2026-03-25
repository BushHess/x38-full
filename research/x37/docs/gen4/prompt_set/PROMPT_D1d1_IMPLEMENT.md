# PROMPT D1d1 - Implement Candidates & Smoke Test (Use this after D1c in the same chat)

You have completed D1c. Candidate designs and the config matrix are ready.

Your job in this turn is **only** to implement each candidate strategy as executable code and verify correctness with a smoke test.
Do **not** run the full walk-forward evaluation.
Do **not** use holdout or reserve_internal data.
Do **not** select a champion or challenger.

## Constitution walk-forward specification (reference)

Type: quarterly expanding (anchored start, expanding training window).

**14 test folds on discovery period (2020-01-01 → 2023-06-30):**

| Fold | Train end (exclusive) | Test start | Test end |
|------|----------------------|------------|----------|
| 1 | 2020-01-01 | 2020-01-01 | 2020-03-31 |
| 2 | 2020-04-01 | 2020-04-01 | 2020-06-30 |
| ... | ... | ... | ... |
| 14 | 2023-04-01 | 2023-04-01 | 2023-06-30 |

Training data for each fold: warmup start → train_end_exclusive.
Test data for each fold: test_start → test_end.

## Execution semantics
- Signal generated at bar close → fill at next bar open (next-open execution).
- UTC alignment for all timestamps.
- No lookahead: the strategy at bar t may only use data up to and including bar t.
- Position sizing: 0% or 100% notional (binary).
- Warmup period data (→ 2019-12-31) is available for indicator initialization but no trades allowed.

## Cost model
Two cost levels will be used in D1d2:
- 20 bps round-trip (10 bps per side)
- 50 bps round-trip (25 bps per side)

Apply cost at each entry and exit event.

## What to do

### 1. Implement each candidate strategy

Using the exact signal logic from `d1c_candidate_designs.md` and configs from `d1c_config_matrix.csv`, implement each candidate as executable code.

**Save implementations to files**: Write each candidate's implementation to `d1d_impl_{candidate_id}.py`. Each file must be self-contained and expose a minimal runner contract:
- `run_candidate(data_by_timeframe, config, cost_rt_bps, start_utc=None, end_utc=None, initial_state=None)`
  or an equivalent class method with the same arguments,
- **Cost invariant**: `cost_rt_bps` must only affect net daily return and metric computation. Signal generation, entry/exit decisions, and all path-dependent state must not depend on `cost_rt_bps`.
- return at minimum `daily_returns`, `trade_log`, and `terminal_state`.

`terminal_state` must be compatible with `portfolio_state.json` and include:
- `position_state`
- `position_fraction`
- `entry_time_utc`
- `entry_price`
- `trail_state`
- `custom_state`
- `last_signal_time_utc`
- `reconstructable_from_warmup_only`

This file is the **named artifact** that D1d2, D1e2, and D1e3 will reload if runtime state is lost. These files will also be copied into the state pack as `impl/{candidate_id}.py` during D2 packaging, to enable forward evaluation sessions to use the exact same code without re-implementation.

**Performance note**: Prefer vectorized signal generation (e.g., pandas boolean columns and rolling computations) over bar-by-bar loops for speed. If the 15m CSV is too large, consider that many swing-horizon mechanisms primarily use D1 or H4 — but this is not a constraint. Use whatever timeframes D1b measurement supports.

### 1b. Ablation variants (multi-layer candidates only) — governance patch v4.0.1

For each candidate with **more than one logical layer**, implement ablated variants:
one variant per layer, where that layer's decision function is disabled (bypassed,
so the remaining layers operate as if the removed layer always permits).

- Name files `d1d_impl_{candidate_id}_no_{layer_name}.py`.
- Each ablated variant uses the candidate's **first config** in the matrix (same config
  used for the smoke test). The ablation test checks whether a layer *contributes*,
  not whether it survives all parameter combinations.
- Single-layer candidates do not require ablation variants.

Example: a 2-layer candidate `trendvol` with layers `trend` and `vol_filter` produces
two files: `d1d_impl_trendvol_no_trend.py` and `d1d_impl_trendvol_no_vol_filter.py`.

### 2. Smoke test

For **one config per candidate** (the first config in the matrix), run on **fold 1 only** at 50 bps RT:
- Verify the implementation produces trades (or correctly produces zero trades if the signal never fires).
- Verify entry/exit timestamps are consistent with next-open execution.
- Verify cost is applied at each entry and exit.
- Verify no lookahead (no use of future data).
- Print a brief summary: number of entries, exposure, gross vs net return.

If the smoke test reveals implementation bugs, fix them before proceeding.

### 3. Report readiness

Confirm that all candidates are implemented, smoke-tested, and ready for the full WFO batch in D1d2.

## Required output sections
1. `Implementation Notes` — any implementation decisions made (vectorization, timeframe handling, etc.)
2. `Implementation Files` — list of `d1d_impl_{candidate_id}.py` files saved (including ablation variants)
3. `Smoke Test Results` — per-candidate: config tested, fold 1 entries, exposure, gross/net return
4. `Ablation Variants` — list of ablation files per multi-layer candidate, or "N/A — all candidates single-layer"
5. `Readiness Confirmation` — "All N candidates implemented, saved, and smoke-tested. Ready for D1d2."

## What not to do
- Do not run the full walk-forward (all folds × all configs). That is D1d2.
- Do not use holdout data (2023-07-01 → 2024-09-30).
- Do not use reserve_internal data (2024-10-01 → snapshot end).
- Do not rank, filter, or select candidates.
- Do not freeze any candidate.
- Do not modify the constitution.
