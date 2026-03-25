# Historical Seed Audit Specification

`historical_seed_audit.csv` records the internal seed-discovery evidence extracted from the contaminated historical snapshot.

## Purpose

This file exists to preserve reproducibility and auditability of the seed freeze.

It does **not** create clean forward evidence.

## What it should contain

One row per candidate per seed segment per cost.

Recommended columns:
- `session_id`
- `snapshot_id`
- `candidate_id`
- `mechanism_type`
- `role_after_seed`
- `segment`
- `segment_start_utc`
- `segment_end_utc`
- `cost_rt_bps`
- `cagr`
- `sharpe`
- `max_drawdown`
- `entries`
- `exposure`
- `bootstrap_lb5_mean_daily_return`
- `selected_in_state_pack`

## Required segments

For the current seed constitution, include:
- `discovery`
- `holdout`
- `reserve_internal`

If discovery uses walk-forward folds, you may also include:
- `discovery_fold`
- `aggregate_discovery`

## What this file must not do

- It must not be merged into `forward_evaluation_ledger.csv`.
- It must not be used to claim `FORWARD_CONFIRMED`.
- It must not be treated as appended out-of-sample evidence.

## Packaging rule

The file is created in the seed discovery session and then carried forward unchanged inside all later state packs unless you intentionally add a more detailed audit appendix.

## Practical note

If you want fold-level detail, store it in `audit/` and keep `historical_seed_audit.csv` at the segment level for readability.
