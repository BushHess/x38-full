# PROMPT D1f2 - Registry & State Files (Use this after D1f1 in the same chat)

You have completed D1f1. Champion/challengers are selected, and frozen system specs are drafted.

Your job in this turn is to draft `candidate_registry.json`, `meta_knowledge_registry.json`, and `portfolio_state.json`.
Do **not** draft audit, ledger, or contamination files — that is D1f3.
Do **not** perform new research.
Do **not** re-run backtests.
Do **not** modify the constitution.

## Step 1: Draft candidate_registry.json

Using the exact schema from `candidate_registry.template.json`, create `candidate_registry.json` with:
- program_lineage_id
- constitution_version
- system_version_id
- parent_system_version_id (`null` for V1)
- freeze_cutoff_utc
- design_inputs_end_utc
- evidence_clean_since_utc
- registry_created_in_session
- active_champion_id (the champion's candidate_id, or `"NO_ROBUST_CANDIDATE"`)
- live_candidates array — for each live candidate:
  - candidate_id, role, status, mechanism_type, frozen_spec_file, origin_snapshot_id, frozen_at_utc
  - logical_layers, tunable_quantities, current_evidence_label (`"INTERNAL_SEED_CANDIDATE"`), holdout_flag (`"PASS"` or `"FAIL"`)
  - cumulative_anchor_utc (set to the date component of `evidence_clean_since_utc`, i.e. the calendar date of the first bar after `freeze_cutoff_utc`, in date-only format `YYYY-MM-DD` to match `date_utc` granularity in `forward_daily_returns.csv`), cumulative_anchor_event (`"freeze"`)
  - decision_eligibility: cumulative_forward_days_required, cumulative_forward_entries_required
  - cumulative_forward_metrics: `days: 0`, `entries: 0`, all metric fields (`cagr_*`, `sharpe_*`, `max_drawdown_*`, `exposure`) set to `null`
  - For champion: `retention_rule_ref` (points to `champion_retention_rule`)
  - For challengers: `promotion_rule_ref` and `kill_rule_ref` (point to `challenger_promotion_rule` and `challenger_kill_rule`)
- retired_candidates array — empty if no candidates were eliminated, or one entry per eliminated candidate
- version_lineage_summary array — one entry for V1 with `system_version_id`, `parent_system_version_id` (null), `freeze_cutoff_utc`, `evidence_days_accumulated` (0), `status` ("active")

If `NO_ROBUST_CANDIDATE`: set `active_champion_id` to `"NO_ROBUST_CANDIDATE"`, `live_candidates` to `[]`, and in Step 3 set `candidate_states` to `{}`, `active_challenger_ids` to `[]`, and `current_forward_status` to `"governance_required"`.

## Step 2: Draft meta_knowledge_registry.json

Record structural knowledge discovered during this session:
- Tier 1 axioms (from constitution — no lookahead, UTC, next-open, no synthetic repair)
- Tier 2 structural priors (from constitution design choices only — e.g. microstructure excluded for swing horizon, layering is hypothesis not default)
- Tier 3 session notes (from D1b/D1d/D1e — which channels had signal, which did not, WFO stability, regime sensitivity, etc. These are snapshot-specific empirical findings and must not be elevated to Tier 2.)

Each entry must have: rule_id, statement, tier, basis, scope, authority, provenance, overlap_guard, challenge_rule, expiry, status.

## Step 3: Draft portfolio_state.json

Using the exact schema from `portfolio_state.template.json`, create `portfolio_state.json`.

**Source for per-candidate state**: Use `d1e_terminal_states.json` (created in D1e2) as the primary source for each candidate's terminal state, including any load-bearing serialized state. If `d1e_terminal_states.json` is not available (e.g., older session), derive from execution context.

Top-level fields:
- program_lineage_id, constitution_version, system_version_id, state_pack_version
- active_champion_id (match candidate_registry)
- active_challenger_ids (match candidate_registry)
- current_forward_status: `"not_started"` if live candidates exist, `"governance_required"` if `NO_ROBUST_CANDIDATE`
- forward_boundary_utc: the last bar timestamp of the reserve_internal segment (snapshot end), as ISO 8601 UTC. This anchors the first forward evaluation boundary.
- last_evaluated_timestamp_by_timeframe_utc: all `null` (no forward evaluation yet)
- warmup_requirements: bars required per timeframe for deterministic state reconstruction

For each live candidate in `candidate_states` (populate from `d1e_terminal_states.json`):
- position_state: `"flat"` or `"long"` (from terminal states)
- position_fraction: 0.0 or 1.0
- entry_time_utc: null or timestamp if long
- entry_price: null or price if long
- trail_state: null or `{"trail_price": <value>}` if the mechanism uses a path-dependent exit
- custom_state: null or an opaque JSON object for mechanism-specific state not covered by trail_state (e.g., latch flags, cooldown counters). If non-null, the frozen spec must document its schema.
- last_signal_time_utc: timestamp of last signal
- reconstructable_from_warmup_only: true or false

If `reconstructable_from_warmup_only` is `false`, treat the serialized fields in `d1e_terminal_states.json`
as load-bearing and copy them verbatim into `portfolio_state.json`.

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
