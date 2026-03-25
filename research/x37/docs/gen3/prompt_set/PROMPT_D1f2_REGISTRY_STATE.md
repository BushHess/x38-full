# PROMPT D1f2 - Registry & State Files (Use this after D1f1 in the same chat)

You have completed D1f1. Champion/challengers are selected, and frozen system specs are drafted.

Your job in this turn is to draft `candidate_registry.json`, `meta_knowledge_registry.json`, and `portfolio_state.json`.
Do **not** draft audit, ledger, or contamination files — that is D1f3.
Do **not** perform new research.
Do **not** re-run backtests.
Do **not** modify the constitution.

## Step 1: Draft candidate_registry.json

Using the exact schema from `candidate_registry.template.json`, create `candidate_registry.json` with:
- lineage_id
- constitution_version
- registry_created_in_session
- active_champion_id (the champion's candidate_id, or `"NO_ROBUST_CANDIDATE"`)
- live_candidates array — for each live candidate:
  - candidate_id, role, status, mechanism_type, frozen_spec_file, seed_snapshot_id, frozen_at_utc
  - logical_layers, tunable_quantities, current_evidence_label (`"INTERNAL_SEED_CANDIDATE"`), holdout_flag (`"PASS"` or `"FAIL"`)
  - cumulative_anchor_utc (set to `reserve_internal_end_utc` from `portfolio_state.json` — the last market data timestamp of the seed snapshot, NOT the packaging wall-clock time), cumulative_anchor_event (`"freeze"`)
  - decision_eligibility: cumulative_forward_days_required, cumulative_forward_entries_required
  - cumulative_forward_metrics: `days: 0`, `entries: 0`, all metric fields (`cagr_*`, `sharpe_*`, `max_drawdown_*`, `exposure`) set to `null`
  - For champion: `retention_rule_ref` (points to `champion_retention_rule`)
  - For challengers: `promotion_rule_ref` and `kill_rule_ref` (point to `challenger_promotion_rule` and `challenger_kill_rule`)
- retired_candidates array — empty if no candidates were eliminated, or one entry per eliminated candidate

If `NO_ROBUST_CANDIDATE`: set `active_champion_id` to `"NO_ROBUST_CANDIDATE"`, `live_candidates` to `[]`, and in Step 3 set `candidate_states` to `{}`.

## Step 2: Draft meta_knowledge_registry.json

Record structural knowledge discovered during this session:
- Tier 1 axioms (from constitution — no lookahead, UTC, next-open, no synthetic repair)
- Tier 2 structural priors (from constitution design choices only — e.g. microstructure excluded for swing horizon, layering is hypothesis not default)
- Tier 3 session notes (from D1b/D1d/D1e — which channels had signal, which did not, WFO stability, regime sensitivity, etc. These are snapshot-specific empirical findings and must not be elevated to Tier 2.)

Each entry must have: rule_id, statement, tier, basis, scope, authority, provenance, overlap_guard, challenge_rule, expiry, status.

## Step 3: Draft portfolio_state.json

Using the exact schema from `portfolio_state.template.json`, create `portfolio_state.json`.

Top-level fields:
- lineage_id, constitution_version, state_pack_version, state_pack_status (always `"draft"` at this stage — D2 will set to `"sealed"` after hash manifest is finalized)
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
- additional_state: null or an object containing mechanism-specific internal state not covered by the standard fields above (e.g., pending signal, hysteresis state, cooldown counter, adaptive threshold state)

## Required output sections
1. `Candidate Registry` — summary of registry contents
2. `Meta-Knowledge Registry` — count of entries per tier
3. `Portfolio State` — position state per candidate, warmup requirements
4. `Evidence Labels` — INTERNAL_SEED_CANDIDATE for all live candidates
5. `Files Created` — list of JSON files

## What not to do
- Do not run new backtests.
- Do not change any metric or ranking from D1e.
- Do not draft audit, ledger, or contamination files — that is D1f3.
- Do not start packaging into state_pack_v1 — that is D2's job.
- Do not modify the constitution.
