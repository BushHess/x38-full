# PROMPT D1e2 - Holdout & Reserve Evaluation (Use this after D1e1 in the same chat)

You have completed D1e1. Surviving candidates and their representative configs are in `d1e_surviving_candidates.csv`.

Your job in this turn is **only** to run holdout and reserve_internal evaluation for surviving candidates.
Do **not** run bootstrap — that is D1e3.
Do **not** freeze any candidate — that is D1f's job.

**Guard**: If D1e1 reported zero surviving candidates, save empty `d1e_holdout_results.csv` and `d1e_reserve_results.csv` (header only), then state: "No candidates to evaluate. Proceed to D1e3."

## Step 1: Run holdout evaluation

**Holdout period: 2023-07-01 → 2024-09-30**

For each surviving candidate (using its representative config from D1e1 and the implementation from `d1d_impl_{candidate_id}.py`):
1. Initialize strategy with all data up to 2023-06-30 (warmup + discovery) for indicator warmup.
2. Run on holdout period.
3. Record at both 20 bps and 50 bps RT:
   - CAGR, Sharpe, max drawdown, entries, exit_count, final_position_state, exposure, mean daily return

4. Check hard constraints on holdout at 50 bps:
   - CAGR_50bps > 0
   - MDD_50bps ≤ 0.45
   - Entries per year ∈ [6, 80] (holdout_entries / holdout_years)
   - Exposure ∈ [0.15, 0.90]
   - If a candidate fails any holdout hard constraint, flag it but do not eliminate yet — record the failure per constraint.

## Step 2: Run reserve_internal evaluation

**Reserve internal period: 2024-10-01 → snapshot end**

For each surviving candidate:
1. Initialize with all data up to 2024-09-30.
2. Run on reserve_internal period.
3. Record same metrics as holdout (including exit_count and final_position_state).
4. This is additional internal evidence, not clean forward evidence.

## Step 3: Save results

Save to files:
- `d1e_holdout_results.csv` — holdout metrics per surviving candidate (both cost levels, holdout constraint pass/fail), including exit_count and final_position_state columns
- `d1e_reserve_results.csv` — reserve metrics per surviving candidate (both cost levels), including exit_count and final_position_state columns
- `d1e_holdout_daily_returns.csv` — daily return series for holdout segment, columns: candidate_id, cost_bps_rt, date, daily_return. Required for D1f3 to compute daily_returns_hash without re-running.
- `d1e_reserve_daily_returns.csv` — daily return series for reserve_internal segment, same columns as above.
- `d1e_terminal_states.json` — per-candidate terminal state at the end of reserve_internal:
  - `candidate_id`
  - `position_state`: `"flat"` or `"long"`
  - `position_fraction`: 0.0 or 1.0
  - `entry_time_utc`: null or ISO 8601 timestamp (if long)
  - `entry_price`: null or float (if long)
  - `trail_state`: null or `{"trail_price": <value>}` (if mechanism uses path-dependent exit)
  - `custom_state`: null or an opaque JSON object for any additional mechanism-specific state that cannot be reconstructed from warmup-only replay
  - `last_signal_time_utc`: ISO 8601 timestamp of last signal generated
  - `reconstructable_from_warmup_only`: true or false
  If `reconstructable_from_warmup_only` is false, the serialized state fields above are load-bearing and must be copied verbatim into `portfolio_state.json`.
  This file ensures D1f2 can populate `portfolio_state.json` without relying on chat context memory, making the handoff robust against chat interruptions.

## Required output sections
1. `Holdout Results` — table of holdout metrics per candidate, with constraint pass/fail flags
2. `Reserve Results` — table of reserve metrics per candidate
3. `Files Saved` — list of output files

## What not to do
- Do not re-run the walk-forward.
- Do not change candidate designs or representative configs.
- Do not run bootstrap — that is D1e3.
- Do not eliminate candidates based on holdout failures — flag only. D1f decides.
- Do not freeze or select champion/challengers — that is D1f.
- Do not modify the constitution.
