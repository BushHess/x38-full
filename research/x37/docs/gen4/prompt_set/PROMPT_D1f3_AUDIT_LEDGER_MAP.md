# PROMPT D1f3 - Audit, Ledger & Contamination Map (Use this after D1f2 in the same chat)

You have completed D1f2. Registry and state files are drafted.

Your job in this turn is to draft `historical_seed_audit.csv`, `forward_evaluation_ledger.csv`, and `contamination_map.md`, then provide a complete file inventory for D2.
Do **not** perform new research.
Do **not** re-run backtests.
Do **not** modify the constitution.

## Step 1: Draft historical_seed_audit.csv

One row per candidate per segment per cost:
- session_id, snapshot_id, candidate_id, mechanism_type, role_at_freeze
- segment (discovery, holdout, reserve_internal)
- segment_start_utc, segment_end_utc
- cost_rt_bps (20 and 50)
- cagr, sharpe, max_drawdown, entries, exit_count, final_position_state, daily_returns_hash, exposure
- bootstrap_lb5_mean_daily_return (discovery only)
- selected_in_state_pack (true/false)

**Reproduction check columns** (required for F1 verification):
- `exit_count`: number of position exits in the segment. Source: `d1d_wfo_results.csv` (sum across folds for representative config, discovery segment), `d1e_holdout_results.csv` (holdout), `d1e_reserve_results.csv` (reserve_internal).
- `final_position_state`: `flat` or `long` at segment end. Source: `d1d_wfo_results.csv` final fold (discovery), `d1e_holdout_results.csv` (holdout), `d1e_terminal_states.json` (reserve_internal).
- `daily_returns_hash`: SHA-256 hex digest of the candidate's daily return series on this segment. Compute by rounding each daily return to 8 decimal places, writing one per line (newline-separated), and hashing the resulting string. Source: `d1d_wfo_daily_returns.csv` (discovery, filter by representative config), `d1e_holdout_daily_returns.csv` (holdout), `d1e_reserve_daily_returns.csv` (reserve_internal).

## Step 2: Draft forward_evaluation_ledger.csv

Header only, no data rows. Use the exact header from the template `forward_evaluation_ledger.template.csv`:
```
system_version_id,session_id,review_type,window_start_utc,window_end_utc,candidate_id,candidate_role_before_window,evidence_clean_for_version,cost_rt_bps,incremental_days,incremental_entries,incremental_cagr,incremental_sharpe,incremental_max_drawdown,incremental_exposure,cumulative_forward_days,cumulative_forward_entries,cumulative_cagr,cumulative_sharpe,cumulative_max_drawdown,cumulative_exposure,bootstrap_lb5_mean_daily_return_cumulative,evidence_label_after_window,decision_after_window,paired_advantage_vs_champion
```

## Step 3: Draft contamination_map.md

Record:
- snapshot_id and date range
- which data was used for seed discovery (warmup + discovery period)
- which data was used for holdout (internal, not forward)
- which data was used for reserve_internal (internal, not forward)
- explicit statement: no clean forward evidence exists yet
- latest state pack version: v1

## Step 4: Provide file inventory for D2 packaging

List **all** files created across D1f1, D1f2, and D1f3:
- `frozen_system_specs/{candidate_id}.md` (one per live candidate; omit if NO_ROBUST_CANDIDATE)
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_evaluation_ledger.csv`
- `contamination_map.md`

Also list files from earlier D1 steps that D2 will package:
- `d1d_impl_{candidate_id}.py` (one per live candidate, from D1d1 — packaged as `impl/{candidate_id}.py`)

Also list files that D2 will generate during packaging (not created in D1f):
- `research_constitution_version.txt`
- `program_lineage_id.txt`
- `system_version_id.txt`
- `system_version_manifest.json`
- `session_summary.md`
- `forward_daily_returns.csv` (header-only)
- `input_hash_manifest.txt`
- `warmup_buffers/` (if needed per portfolio_state.json warmup_requirements)

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
