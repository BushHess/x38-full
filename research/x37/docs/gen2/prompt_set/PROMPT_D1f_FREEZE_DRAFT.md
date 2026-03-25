# PROMPT D1f - Freeze & Draft Outputs (Use this after D1e in the same chat)

You have completed D1e. Results are available in the D1e output files:
- `d1e_final_ranking.csv` — ranked candidates with all metrics
- `d1e_holdout_results.csv` — holdout metrics per candidate
- `d1e_reserve_results.csv` — reserve metrics per candidate
- `d1e_hard_constraint_filter.csv` — pass/fail per constraint per config

Your job in this turn is to select the champion and challengers, then draft all required output files.
Do **not** perform new research.
Do **not** re-run backtests.
Do **not** modify the constitution.

## Step 1: Select champion and challengers

From the final ranking in D1e:

**Champion (exactly 1):**
- The rank-1 candidate by adjusted preference.
- Must pass all hard constraints on discovery AND holdout.
- If rank-1 fails holdout hard constraints, take the highest-ranked candidate that passes both.
- If no candidate passes both, the champion is `NO_ROBUST_CANDIDATE`.

**Challengers (0 to 2):**
- The next highest-ranked candidates that pass discovery hard constraints.
- Challengers that fail holdout are allowed but must be flagged with `holdout_flag: FAIL`.
- Max 2 challengers.
- If only 1 or 0 viable challengers exist, that is acceptable.

**Total live candidates: max 3.**

## Step 2: Draft frozen system specs

For each live candidate, create a frozen system spec file in `frozen_system_specs/`:
- Filename: `{candidate_id}.md`

Each spec must include:
- candidate_id
- archetype (A, B, or C)
- role: champion or challenger
- exact signal logic (entry condition, exit condition)
- exact execution logic (next-open fill, UTC, binary sizing)
- exact cost model (20 bps and 50 bps RT)
- tunable quantities with frozen values
- fixed quantities with values
- layer count
- evidence summary:
  - discovery WFO metrics (Calmar, CAGR, Sharpe, MDD, entries, exposure)
  - holdout metrics
  - reserve metrics
  - bootstrap LB5
- provenance: session_id, snapshot_id, constitution_version

## Step 3: Draft candidate_registry.json

Using the template schema, create `candidate_registry.json` with:
- lineage_id
- constitution_version
- created_by_session
- snapshot_id
- candidates array:
  - For each live candidate: id, archetype, role, status (active), config, evidence_summary
  - For each eliminated candidate: id, archetype, status (eliminated), elimination_reason

## Step 4: Draft meta_knowledge_registry.json

Record structural knowledge discovered during this session:
- Tier 1 axioms (from constitution — no lookahead, UTC, next-open, no synthetic repair)
- Tier 2 structural priors (from D1b measurements — which primitives had signal, which did not)
- Tier 3 session notes (from D1d/D1e — observations about WFO stability, regime sensitivity, etc.)

Each entry must have: statement, tier, basis, scope, authority, provenance, overlap_guard, challenge_rule, expiry, status.

## Step 5: Draft portfolio_state.json

For each live candidate:
- position_state: "flat" (at end of reserve_internal period, or "long" if position is open)
- position_fraction: 0.0 or 1.0
- entry_time_utc: null or timestamp if long
- entry_price: null or price if long
- trail_state: null or current trail value if applicable
- last_signal_time_utc: timestamp of last signal
- reconstructable_from_warmup_only: true or false

## Step 6: Draft historical_seed_audit.csv

One row per candidate per segment per cost:
- session_id, snapshot_id, candidate_id, archetype, role_after_seed
- segment (discovery, holdout, reserve_internal)
- segment_start_utc, segment_end_utc
- cost_rt_bps (20 and 50)
- cagr, sharpe, max_drawdown, entries, exposure
- bootstrap_lb5_mean_daily_return (discovery only)
- selected_in_state_pack (true/false)

## Step 7: Draft forward_evaluation_ledger.csv

Header only, no data rows. Use the exact header from the template `forward_evaluation_ledger.template.csv`:
```
session_id,review_type,window_start_utc,window_end_utc,candidate_id,candidate_role_before_window,cost_rt_bps,incremental_days,incremental_entries,incremental_cagr,incremental_sharpe,incremental_max_drawdown,incremental_exposure,cumulative_forward_days,cumulative_forward_entries,cumulative_cagr,cumulative_sharpe,cumulative_max_drawdown,cumulative_exposure,bootstrap_lb5_mean_daily_return_cumulative,evidence_label_after_window,decision_after_window,paired_advantage_vs_champion
```

## Step 8: Draft contamination_map.md

Record:
- snapshot_id and date range
- which data was used for seed discovery (warmup + discovery period)
- which data was used for holdout (internal, not forward)
- which data was used for reserve_internal (internal, not forward)
- explicit statement: no clean forward evidence exists yet
- latest state pack version: v1

## Step 9: Pass through input_hash_manifest.txt

If `input_hash_manifest.txt` was provided at session start or can be derived from admitted files,
include it in the output file set unchanged.

## Step 10: Provide all files for download

List all files created and make them available:
- `frozen_system_specs/{candidate_id}.md` (one per live candidate)
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_evaluation_ledger.csv`
- `contamination_map.md`
- `input_hash_manifest.txt` (if available)

## Required output sections
1. `Seed Discovery Summary` — brief overview of the full D1a–D1f process and key outcomes
2. `Champion Selection` — who and why
3. `Challenger Selection` — who and why (or "none")
4. `Rejected Candidate Summary` — candidates eliminated and reasons
5. `Frozen System Specs` — summary per candidate
6. `Evidence Labels` — INTERNAL_SEED_CANDIDATE for all live candidates
7. `Files Prepared` — list of all files ready for D2 packaging

## What not to do
- Do not run new backtests.
- Do not change any metric or ranking from D1e.
- Do not start packaging into state_pack_v1 — that is D2's job.
- Do not modify the constitution.
