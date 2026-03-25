# Historical Seed Audit Specification

`historical_seed_audit.csv` records internal evidence for all frozen candidates on the constitution's standard segments. Rows originate from seed discovery (initial freeze) and from redesign freeze sessions (appended rows for redesigned candidates).

## Purpose

This file exists to preserve reproducibility and auditability of each candidate's baseline metrics at freeze time. It serves as the benchmark for the F1 reproduction check.

It does **not** create clean forward evidence.

## What it should contain

One row per candidate per segment per cost.

Required columns:
- `session_id`
- `snapshot_id`
- `candidate_id`
- `mechanism_type`
- `role_at_freeze`
- `segment`
- `segment_start_utc`
- `segment_end_utc`
- `cost_rt_bps`
- `cagr`
- `sharpe`
- `max_drawdown`
- `entries`
- `exit_count` — number of position exits in this segment (used by F1 reproduction check)
- `final_position_state` — `flat` or `long` at segment end (used by F1 reproduction check)
- `daily_returns_hash` — SHA-256 hex digest of the candidate's daily return series on this segment, each return rounded to 8 decimal places, one per line, newline-separated (used by F1 reproduction check for path-level verification)
- `exposure`
- `bootstrap_lb5_mean_daily_return`
- `selected_in_state_pack`

These columns are mandatory because F1 reproduction checks depend on them. Values that are not
applicable for a specific segment may be left blank or null-equivalent, but the columns themselves
must be present.

## Required segments

For the current seed constitution, include:
- `discovery`
- `holdout`
- `reserve_internal`

If discovery uses walk-forward folds, you may also include:
- `discovery_fold`
- `aggregate_discovery`

## Key invariant

The F1 reproduction check looks up audit rows by `candidate_id + segment + cost_rt_bps`. This lookup is unambiguous because:
- Carry-forward candidates retain their original `candidate_id` and algorithm — their existing audit rows remain valid.
- Redesigned candidates **must** receive a new `candidate_id` distinct from all IDs in the parent version (enforced in R1 step 4).

This invariant must hold across all versions in a lineage. If violated, audit rows become ambiguous and the F1 reproduction check cannot determine the correct benchmark.

## What this file must not do

- It must not be merged into `forward_evaluation_ledger.csv`.
- It must not be used to claim `FORWARD_CONFIRMED`.
- It must not be treated as appended out-of-sample evidence.

## Packaging rule

The file is created in the seed discovery session. In forward evaluation state packs, it is carried forward unchanged. In redesign freeze state packs, new rows are **appended** for redesigned candidates (produced in R1 step 3 on the same standard segments at both cost levels). Carry-forward candidates retain their existing rows unchanged — their algorithm and parameters have not changed, so the original benchmarks remain valid for the F1 reproduction check.

## Practical note

If you want fold-level detail, store it in `audit/` and keep `historical_seed_audit.csv` at the segment level for readability.
