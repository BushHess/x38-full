# PROMPT D1f - Freeze & Draft Outputs (DEPRECATED — use D1f1–D1f3)

> **Note**: This monolithic prompt has been split into 3 sub-prompts for better per-turn execution:
> - `PROMPT_D1f1_FREEZE_SPECS.md` — champion/challenger selection + frozen system specs
> - `PROMPT_D1f2_REGISTRY_STATE.md` — candidate_registry + meta_knowledge_registry + portfolio_state
> - `PROMPT_D1f3_AUDIT_LEDGER_MAP.md` — historical_seed_audit + forward ledger + contamination map
>
> `input_hash_manifest.txt` has been moved to `PROMPT_D2_PACKAGE_STATE.md` (packaging concern).
>
> Use the split version. This file is retained for reference only.

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

**If the result is `NO_ROBUST_CANDIDATE`**: skip Step 2 (no frozen specs to draft). In Step 3, set `active_champion_id` to `"NO_ROBUST_CANDIDATE"` and `live_candidates` to `[]`. In Step 5, generate a minimal `portfolio_state.json` with `active_champion_id` set to `"NO_ROBUST_CANDIDATE"`, empty `active_challenger_ids`, and empty `candidate_states`. All other steps still apply.

## Step 2: Draft frozen system specs

For each live candidate, create a frozen system spec file in `frozen_system_specs/`:
- Filename: `{candidate_id}.md`

Each spec must include:
- candidate_id
- mechanism_type (brief description of what the mechanism exploits)
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

Using the exact schema from `candidate_registry.template.json`, create `candidate_registry.json` with:
- lineage_id
- constitution_version
- registry_created_in_session
- active_champion_id (the champion's candidate_id, or `"NO_ROBUST_CANDIDATE"`)
- live_candidates array — for each live candidate:
  - candidate_id, role, status, mechanism_type, frozen_spec_file, seed_snapshot_id, frozen_at_utc
  - logical_layers, tunable_quantities, current_evidence_label (`"INTERNAL_SEED_CANDIDATE"`), holdout_flag (`"PASS"` or `"FAIL"`)
  - cumulative_anchor_utc (set to frozen_at_utc), cumulative_anchor_event (`"freeze"`)
  - decision_eligibility: cumulative_forward_days_required, cumulative_forward_entries_required
  - cumulative_forward_metrics: `days: 0`, `entries: 0`, all metric fields (`cagr_*`, `sharpe_*`, `max_drawdown_*`, `exposure`) set to `null`
  - For champion: `retention_rule_ref` (points to `champion_retention_rule`)
  - For challengers: `promotion_rule_ref` and `kill_rule_ref` (point to `challenger_promotion_rule` and `challenger_kill_rule`)
- retired_candidates array — empty if no candidates were eliminated, or one entry per eliminated candidate

If `NO_ROBUST_CANDIDATE`: set `active_champion_id` to `"NO_ROBUST_CANDIDATE"` and `live_candidates` to `[]`.

## Step 4: Draft meta_knowledge_registry.json

Record structural knowledge discovered during this session:
- Tier 1 axioms (from constitution — no lookahead, UTC, next-open, no synthetic repair)
- Tier 2 structural priors (from constitution design choices only — e.g. microstructure excluded for swing horizon, layering is hypothesis not default)
- Tier 3 session notes (from D1b/D1d/D1e — which channels had signal, which did not, WFO stability, regime sensitivity, etc. These are snapshot-specific empirical findings and must not be elevated to Tier 2.)

Each entry must have: statement, tier, basis, scope, authority, provenance, overlap_guard, challenge_rule, expiry, status.

## Step 5: Draft portfolio_state.json

Using the exact schema from `portfolio_state.template.json`, create `portfolio_state.json`.

Top-level fields:
- lineage_id, constitution_version, state_pack_version
- active_champion_id (match candidate_registry)
- active_challenger_ids (match candidate_registry)
- current_forward_status: `"not_started"` (seed discovery produces no forward evidence)
- reserve_internal_end_utc: the last bar timestamp of the reserve_internal segment (snapshot end), as ISO 8601 UTC. This anchors the first forward evaluation boundary.
- last_evaluated_timestamp_by_timeframe_utc: all `null` (no forward evaluation yet)
- warmup_requirements: bars required per timeframe for deterministic state reconstruction

For each live candidate in `candidate_states`:
- position_state: `"flat"` (at end of reserve_internal period, or `"long"` if position is open)
- position_fraction: 0.0 or 1.0
- entry_time_utc: null or timestamp if long
- entry_price: null or price if long
- trail_state: null or `{"trail_price": <value>}` if the mechanism uses a path-dependent exit
- last_signal_time_utc: timestamp of last signal
- reconstructable_from_warmup_only: true or false

## Step 6: Draft historical_seed_audit.csv

One row per candidate per segment per cost:
- session_id, snapshot_id, candidate_id, mechanism_type, role_after_seed
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

## Step 9: Generate input_hash_manifest.txt

Create `input_hash_manifest.txt` recording sha256, file size, and line count for every file admitted in this session (constitution, session manifest, schema conventions doc, and all raw CSV files). If the manifest was provided at session start, include it unchanged; otherwise generate it now.

**Important**: SHA-256 hashes and exact byte sizes require deterministic computation on raw file bytes. If you are running in an upload-only chat environment without filesystem access, you cannot reliably compute these values. In that case, populate the hash and size columns with `DEFERRED` and add a note at the top of the manifest: `# NOTE: hash and size columns are DEFERRED — operator must run sha256sum/stat to fill them before packaging.` The operator is responsible for completing the manifest before the state pack is sealed in D2.

## Step 10: Provide all files for download

List all files created and make them available:
- `frozen_system_specs/{candidate_id}.md` (one per live candidate)
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_evaluation_ledger.csv`
- `contamination_map.md`
- `input_hash_manifest.txt`

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
