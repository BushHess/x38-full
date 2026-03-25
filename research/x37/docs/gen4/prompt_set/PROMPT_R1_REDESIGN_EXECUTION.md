# PROMPT R1 - Redesign Execution (Use this after R0 GO in the same chat)

You have completed R0 and received GO FOR R1.

Proceed with the redesign as described in the validated `redesign_dossier.md`.

## Mission

Apply exactly one principal change to the parent version's algorithm, freeze the result as a new `system_version_id`, and produce all required state artifacts.

## Hard instructions
- Apply **only** the change described in the dossier. Do not sneak in additional modifications.
- Do not exceed the change budget (max 1 logic block, max 3 tunables, max 1 execution change).
- Do not touch the constitution.
- All data up to `freeze_cutoff_utc` is now seen data for the new version.
- The evidence clock for the new version starts at zero.
- Forward evidence from the parent version does NOT transfer to the new version.
- Use the full data set (historical + appended) for internal validation of the redesigned algorithm.

## Required procedure

1. **Assign new version identity**
   - `system_version_id`: next in sequence (e.g. V2, V3)
   - `parent_system_version_id`: the parent version from the dossier
   - `freeze_cutoff_utc`: latest data timestamp
   - `design_inputs_end_utc`: latest data timestamp
   - `reason_for_freeze`: from dossier

2. **Implement the redesign**
   - Apply the single principal change from the dossier
   - Verify the change does not violate complexity caps (max 3 layers, max 4 tunables, max 4 feature families)
   - Smoke-test on seen data to confirm implementation correctness

3. **Internal validation on seen data**
   - Run the redesigned algorithm on the full seen data (all data up to `freeze_cutoff_utc`)
   - Compare against the parent version on the same data
   - This is contaminated internal validation — do NOT claim OOS
   - Verify the redesign achieves the expected effect described in the dossier
   - **Produce audit rows**: Record the redesigned candidate's metrics on the constitution's standard segments (discovery, holdout, reserve_internal) at both 20 and 50 bps RT, using the same column schema as `historical_seed_audit.csv`. These rows will be appended to the audit file in R2, giving the F1 reproduction check a version-scoped benchmark for the new candidate.

4. **Select champion and challengers**
   - The redesigned algorithm is the primary candidate. It **must** receive a new `candidate_id` distinct from all candidate_ids in the parent version — even if the mechanism_type is similar. This ensures that `historical_seed_audit.csv` rows are unambiguously keyed by `candidate_id` across versions.
   - The parent version's champion may be carried forward as a challenger if still within the max 2 challenger limit. Carry-forward candidates **retain** their original `candidate_id`.
   - Total live candidates: max 1 champion + 2 challengers

5. **Freeze candidates**
   - Produce `frozen_system_specs/` for each live candidate under the new `system_version_id`
   - Each spec must follow `frozen_system_spec.template.md` format and include all fields required by `STATE_PACK_SPEC_v4.0_EN.md`
   - Signal logic, execution logic, and position sizing must be written as **unambiguous pseudocode** (not prose)

6. **Draft state artifacts**
   - `candidate_registry.json` — new `system_version_id`, reset evidence to zero, label `INTERNAL_SEED_CANDIDATE`. Include all top-level fields required by `candidate_registry.template.json`: `system_version_id`, `parent_system_version_id`, `freeze_cutoff_utc`, `design_inputs_end_utc`, `evidence_clean_since_utc`, `version_lineage_summary`.
   - `meta_knowledge_registry.json` — carry forward from parent, add any new Tier 3 notes from redesign
   - `portfolio_state.json` — new version, `current_forward_status: "not_started"`, reset last-evaluated timestamps, set `forward_boundary_utc` to `freeze_cutoff_utc` (anchors the first forward evaluation boundary for the new version).
     **Source for per-candidate state**: For each live candidate in `candidate_states`:
     - **Redesigned candidate**: use the terminal state from step 3's internal validation run (at the end of seen data). Save `position_state`, `position_fraction`, `entry_time_utc`, `entry_price`, `trail_state`, `custom_state`, `last_signal_time_utc`, `reconstructable_from_warmup_only` — matching the schema in `portfolio_state.template.json`.
     - **Carry-forward candidate**: copy verbatim from the parent version's `portfolio_state.json` `candidate_states` entry.
     - `warmup_requirements`: derive from each candidate's indicator parameters (e.g., longest lookback period per timeframe). Must match `portfolio_state.template.json` schema.
   - `system_version_manifest.json` — append new version entry, update top-level fields
   - `contamination_map.md` — updated to reflect all data is now seen for the new version
   - `session_summary.md`

## Required output sections
1. `New Version Identity` — system_version_id, parent, freeze_cutoff_utc
2. `Redesign Implementation` — what was changed, complexity impact
3. `Internal Validation` — seen-data comparison (NOT OOS), including audit rows for new candidates
4. `Candidate Lineup` — champion, challengers, frozen spec files (pseudocode format)
5. `State Artifacts Drafted` — list of files prepared (including appended historical_seed_audit.csv rows and impl/)
6. `Evidence Clock Status` — confirm reset to zero, no parent evidence carried

## What not to do
- Do not claim OOS evidence from any data used in this session.
- Do not change more than the dossier specifies.
- Do not package yet — that is R2's job.
