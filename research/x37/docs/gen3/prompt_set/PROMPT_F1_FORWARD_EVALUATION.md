# PROMPT F1 - Forward Evaluation Execution (Use this after F0 in the same chat)

Proceed with forward evaluation on the appended data window only.

## Mission

Evaluate the frozen champion and all frozen challengers on the newly appended evaluation window.

Then make only the allowed decisions:
- keep champion
- promote challenger
- kill challenger
- downgrade evidence label
- escalate a governance concern

## Hard instructions
- Do not redesign any candidate.
- Do not add new feature families.
- Do not search for new candidates.
- Do not rewrite the constitution.
- Use warmup buffers only for rolling-context computation or deterministic state reconstruction.
- Count only the appended evaluation window as new evidence.
- Report both incremental window metrics and cumulative forward metrics.
- Use cumulative forward basis for promote / keep / kill unless an emergency trigger applies.

## Required procedure

**Guard**: If the incoming state pack has `active_champion_id` set to `NO_ROBUST_CANDIDATE` and zero live candidates, stop here and report: "No live candidates in state pack. Forward evaluation is not possible. Run governance review or start a new seed discovery on a different snapshot."

1. Load the frozen candidate specs and implementation artifacts from the incoming state pack (`frozen_system_specs/` and `frozen_implementations/`). Use the implementation files (`d1d_impl_{candidate_id}.py`) as the executable code — do not re-implement from prose specs.
2. Reconstruct candidate state from `portfolio_state.json` (including `additional_state` if present) and any admitted warmup buffers.
3. Evaluate all live candidates on the appended window at both 20 bps and 50 bps round-trip costs.
4. Update cumulative forward metrics since the `cumulative_anchor_utc` recorded in `candidate_registry.json` for each candidate. Recompute cumulative Sharpe, MDD, and bootstrap from the full daily return series in `forward_daily_returns.csv` combined with the current window's daily returns — do not derive these from prior summary statistics.
5. Append each candidate's daily returns for this window to `forward_daily_returns.csv` (one row per candidate per trading day per cost scenario).
6. Apply the constitution hard constraints on the cumulative forward basis if the minimum decision threshold is met.
7. Rank surviving candidates under the constitution objective.
8. Run the paired daily-return bootstrap where required for promotion decisions.
9. Decide:
   - champion stays or changes,
   - challengers remain alive or are killed,
   - evidence labels are updated,
   - governance concern is raised or not.
   - **If a challenger is promoted**:
     - Promoted challenger: set `role` to `"champion"`, reset `cumulative_forward_metrics` to zero, set `cumulative_anchor_utc` to the current window's end timestamp, set `cumulative_anchor_event` to `"promotion"`. Update `active_champion_id` in both `candidate_registry.json` and `portfolio_state.json`.
     - Old champion: if it still satisfies cumulative hard constraints, set `role` to `"challenger"` and keep its cumulative basis unchanged (no reset). Set `retention_rule_ref` → `promotion_rule_ref` + `kill_rule_ref`. Update `active_challenger_ids` in `portfolio_state.json`. If the old champion fails cumulative hard constraints, move it to `retired_candidates` with `eliminated_at_stage: "forward_retention_fail_on_promotion"`.
   - **If a candidate is killed** (challenger fails kill rule, or champion fails retention rule): move the candidate from `live_candidates` to `retired_candidates` in `candidate_registry.json`. Each retired entry must include `candidate_id`, `mechanism_type`, `status: "eliminated"`, `elimination_reason` (the specific rule or constraint that triggered elimination), `eliminated_at_stage` (e.g. `"forward_kill"`, `"forward_retention_fail"`), and `seed_snapshot_id`. Remove the candidate from `candidate_states` in `portfolio_state.json`.
   - **If no candidate survives** (champion fails cumulative hard constraints and all challengers are killed or also fail): move all candidates to `retired_candidates` as above, then set `active_champion_id` to `"NO_ROBUST_CANDIDATE"`, set `live_candidates` to `[]`, label `NO_ROBUST_CANDIDATE`, and escalate governance review. In `portfolio_state.json`, set `active_champion_id` to `"NO_ROBUST_CANDIDATE"`, `active_challenger_ids` to `[]`, `candidate_states` to `{}`, and `current_forward_status` to `"governance_required"`. The session summary must state that governance review is required before any further forward evaluation.
10. Draft updates for:
   - `candidate_registry.json`
   - `portfolio_state.json` — you **must** update these navigation fields:
     - set `state_pack_version` to `"vN+1"` matching the output state pack name
     - set `current_forward_status` to `"in_progress"` (if it was `"not_started"`)
     - set `last_evaluated_timestamp_by_timeframe_utc` per timeframe to the last bar timestamp of the evaluation window (ISO 8601 UTC)
     - update `candidate_states` for each live candidate (position, trail, last signal)
   - `forward_daily_returns.csv` (append this window's daily returns)
   - `forward_evaluation_ledger.csv`
   - `contamination_map.md`
   - `session_summary.md`
   - `meta_knowledge_registry.json` only if a new Tier 3 note or governance-relevant rule status change is justified; otherwise carry it forward unchanged

## Required output sections
1. `Forward Window Summary`
2. `Incremental Candidate Results`
3. `Cumulative Forward Candidate Results`
4. `Champion-Challenger Decision`
5. `Evidence Labels After Window`
6. `Governance Escalation`
7. `Files Prepared For Packaging`

## Important

Stop after preparing the outputs.
Do not package yet. Packaging is the next prompt.
