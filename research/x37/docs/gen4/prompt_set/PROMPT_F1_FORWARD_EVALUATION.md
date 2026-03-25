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

1. Load the frozen candidate specs from the incoming state pack.
2. Implement each candidate from its frozen spec pseudocode. If the state pack includes `impl/` source files, use their exported runner contract directly; otherwise re-implement from the spec. If `impl/` is absent, treat the pack as legacy or non-compliant and note that in the report before continuing.
3. **Reproduction check** (conditional on data availability): If the operator has provided the discovery segment raw data (or the execution environment has filesystem access to it), run each candidate on the **discovery segment** at **both 20 bps and 50 bps RT** and compare against the corresponding rows in `historical_seed_audit.csv` (segment=`discovery`, cost_rt_bps=`20` and cost_rt_bps=`50`). Required checks per cost level:
   - `entries` must match exactly.
   - `exit_count` must match exactly.
   - `cagr` must match within ±0.5 pp.
   - `final_position_state` must match (`flat` or `long`).
   - `daily_returns_hash` (SHA-256 of the candidate's daily return series on the discovery segment, rounded to 8 decimal places) must match. If the audit row does not contain a `daily_returns_hash` (legacy state packs), skip this check and note it in the report.

   If any candidate diverges beyond tolerance on any check, stop and report the mismatch before proceeding — do not continue to forward evaluation with a potentially unfaithful re-implementation.

   If discovery segment data is not available (upload-only environment without historical snapshot), skip the reproduction check and report: "Reproduction check SKIPPED — discovery segment data not provided. Proceeding with impl/ runner (or re-implementation from spec) without path-level verification." This is acceptable for routine forward evaluation; the operator may provide discovery data for higher-assurance sessions.
4. Reconstruct candidate state from `portfolio_state.json` and any admitted warmup buffers.
5. Evaluate all live candidates on the appended window at both 20 bps and 50 bps round-trip costs.
6. Update cumulative forward metrics since the `cumulative_anchor_utc` recorded in `candidate_registry.json` for each candidate. Recompute cumulative Sharpe, MDD, and bootstrap from the retained version-scoped daily return series in `forward_daily_returns.csv` combined with the current window's daily returns, filtering by `date_utc >= cumulative_anchor_utc` for candidate-scoped reporting — do not derive these from prior summary statistics.
7. Append each candidate's daily returns for this window to `forward_daily_returns.csv` (one row per candidate per trading day per cost scenario). Do **not** truncate pre-promotion rows for live candidates; promotion resets reporting scope, not file retention scope.
8. Apply the constitution hard constraints on the cumulative forward basis if the minimum decision threshold is met.
9. Rank surviving candidates under the constitution objective.
10. Run the paired daily-return bootstrap where required for promotion decisions.
11. Decide:
   - champion stays or changes,
   - challengers remain alive or are killed,
   - evidence labels are updated,
   - governance concern is raised or not.
   - **If a challenger is promoted**:
     - Promoted challenger: set `role` to `"champion"`, reset `cumulative_forward_metrics` to zero, set `cumulative_anchor_utc` to the calendar date after the current window's last date (date-only format `YYYY-MM-DD`, matching `date_utc` granularity in `forward_daily_returns.csv`), set `cumulative_anchor_event` to `"promotion"`. Update `active_champion_id` in both `candidate_registry.json` and `portfolio_state.json`.
     - Old champion: if it still satisfies cumulative hard constraints, set `role` to `"challenger"` and keep its cumulative basis unchanged (no reset). Set `retention_rule_ref` → `promotion_rule_ref` + `kill_rule_ref`. Update `active_challenger_ids` in `portfolio_state.json`. If the old champion fails cumulative hard constraints, move it to `retired_candidates` with `eliminated_at_stage: "forward_retention_fail_on_promotion"`.
   - **If a candidate is killed** (challenger fails kill rule, or champion fails retention rule): move the candidate from `live_candidates` to `retired_candidates` in `candidate_registry.json`. Each retired entry must include `candidate_id`, `mechanism_type`, `system_version_id`, `status: "eliminated"`, `elimination_reason` (the specific rule or constraint that triggered elimination), `eliminated_at_stage` (e.g. `"forward_kill"`, `"forward_retention_fail"`), and `origin_snapshot_id` — matching the `retired_candidate_schema` in `candidate_registry.template.json`. In `portfolio_state.json`: remove the candidate from `candidate_states`, remove its ID from `active_challenger_ids` (if challenger) or set `active_champion_id` to `"NO_ROBUST_CANDIDATE"` (if champion). Both fields must remain consistent with `candidate_registry.json` per STATE_PACK_SPEC invariant.
   - **If no candidate survives** (champion fails cumulative hard constraints and all challengers are killed or also fail): move all candidates to `retired_candidates` as above, then set `active_champion_id` to `"NO_ROBUST_CANDIDATE"`, set `live_candidates` to `[]`, label `NO_ROBUST_CANDIDATE`, and escalate governance review. In `portfolio_state.json`, set `active_champion_id` to `"NO_ROBUST_CANDIDATE"`, `active_challenger_ids` to `[]`, `candidate_states` to `{}`, and `current_forward_status` to `"governance_required"`. The session summary must state that governance review is required before any further forward evaluation.
12. Draft updates for:
   - `system_version_manifest.json` — update `evidence_days_accumulated` in the active version's `version_history` entry to reflect total forward calendar days accumulated so far (including this window)
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
1. `Reproduction Check` — per candidate per cost level: segment tested, cost_rt_bps, expected vs actual for entries, exit_count, cagr, final_position_state, daily_returns_hash — PASS/FAIL per check. If discovery data was not provided, report SKIPPED with reason.
2. `Forward Window Summary`
3. `Incremental Candidate Results`
4. `Cumulative Forward Candidate Results`
5. `Champion-Challenger Decision`
6. `Evidence Labels After Window`
7. `Governance Escalation`
8. `Files Prepared For Packaging`

## Important

Stop after preparing the outputs.
Do not package yet. Packaging is the next prompt.
