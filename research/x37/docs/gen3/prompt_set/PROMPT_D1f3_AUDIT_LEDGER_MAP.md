# PROMPT D1f3 - Audit, Ledger & Contamination Map (Use this after D1f2 in the same chat)

You have completed D1f2. Registry and state files are drafted.

Your job in this turn is to draft `historical_seed_audit.csv`, `forward_evaluation_ledger.csv`, and `contamination_map.md`, then provide a complete file inventory for D2.
Do **not** perform new research.
Do **not** re-run backtests.
Do **not** modify the constitution.

## Step 1: Draft historical_seed_audit.csv

One row per candidate per segment per cost:
- session_id, snapshot_id, candidate_id, mechanism_type, role_after_seed
- segment (discovery, holdout, reserve_internal)
- segment_start_utc, segment_end_utc
- cost_rt_bps (20 and 50)
- cagr, sharpe, max_drawdown, entries, exposure
- bootstrap_lb5_mean_daily_return (discovery only)
- selected_in_state_pack (true/false)

## Step 2: Draft forward_evaluation_ledger.csv and forward_daily_returns.csv

Header only, no data rows.

**forward_evaluation_ledger.csv** — use the exact header from `forward_evaluation_ledger.template.csv`:
```
session_id,review_type,window_start_utc,window_end_utc,candidate_id,candidate_role_before_window,cost_rt_bps,incremental_days,incremental_entries,incremental_cagr,incremental_sharpe,incremental_max_drawdown,incremental_exposure,cumulative_forward_days,cumulative_forward_entries,cumulative_cagr,cumulative_sharpe,cumulative_max_drawdown,cumulative_exposure,bootstrap_lb5_mean_daily_return_cumulative,evidence_label_after_window,decision_after_window,paired_advantage_vs_champion
```

**forward_daily_returns.csv** — use the exact header from `forward_daily_returns.template.csv`:
```
candidate_id,date_utc,daily_return,cost_rt_bps,session_id
```

Both files contain header only at this stage — no forward data exists yet.

## Step 3: Draft contamination_map.md

Record:
- snapshot_id and date range
- which data was used for seed discovery (warmup + discovery period)
- which data was used for holdout (internal, not forward)
- which data was used for reserve_internal (internal, not forward)
- explicit statement: no clean forward evidence exists yet
- latest state pack version: v1

## Step 4: Provide complete file inventory

List **all** files created across D1f1, D1f2, and D1f3 that are ready for D2 packaging:
- `frozen_system_specs/{candidate_id}.md` (one per live candidate; omit if NO_ROBUST_CANDIDATE)
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_evaluation_ledger.csv`
- `forward_daily_returns.csv`
- `contamination_map.md`
- `input_hash_manifest.txt` — generated in D2, not in this turn

## Required output sections
1. `Seed Discovery Summary` — brief overview of the full D1a–D1f process and key outcomes
2. `Historical Seed Audit` — row count, segments covered
3. `Contamination Map` — summary of data usage boundaries
4. `Complete File Inventory` — all files ready for D2 packaging
5. `Files Created` — list of files created in this turn

## What not to do
- Do not run new backtests.
- Do not change any metric or ranking from D1e.
- Do not generate input_hash_manifest.txt — that is D2's job.
- Do not start packaging into state_pack_v1 — that is D2's job.
- Do not modify the constitution.
