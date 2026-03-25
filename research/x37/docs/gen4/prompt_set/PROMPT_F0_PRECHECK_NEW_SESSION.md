# PROMPT F0 - Forward Evaluation Precheck (Use this in a brand-new chat)

You are starting a **forward evaluation session**.

Your job in this turn is **only** to perform the session precheck.
Do not redesign candidates.
Do not change the constitution.
Do not score the new data yet.

## Inputs you may use in this turn
- `research_constitution_v4.0.yaml`
- latest `state_pack_vN`
- appended data delta files
- optional warmup buffer files
- `session_manifest.json`
- optional `input_hash_manifest.txt`
- optional historical snapshot raw files (for F1 reproduction check)

## Required output sections
1. `Mode Confirmation`
   - confirm this is a forward evaluation session
   - confirm constitution version
   - confirm the incoming state pack version
2. `Loaded Frozen Candidates`
   - list champion
   - list challengers
   - list their frozen spec files
3. `Data Window Audit`
   - identify the appended evaluation window
   - identify any warmup-only window
   - confirm that the evaluation window begins strictly after the last evaluated timestamp per timeframe (from `portfolio_state.json` field `last_evaluated_timestamp_by_timeframe_utc`), or after `forward_boundary_utc` (from `portfolio_state.json`) if `current_forward_status` is `"not_started"`
   - if `current_forward_status` is `"governance_required"`, report `NO-GO` with reason: "Lineage is in governance_required state (all candidates eliminated during prior forward evaluation). Run governance review before starting a new forward session."
   - if `input_hash_manifest.txt` from the incoming state pack contains any `DEFERRED` entries, report `NO-GO` with reason: "Input state pack has unresolved DEFERRED hashes. Operator must complete the manifest before this state pack can be used as input."
4. `Review Eligibility`
   - state whether this is a standard review or an emergency review
   - state whether the minimum decision threshold could be met after this window
5. `Boundary Confirmation`
   - state that redesign is forbidden
   - state that only keep / promote / kill / downgrade / governance-escalate decisions are allowed
6. `Go / No-Go`
   - if inputs are valid, say `GO FOR F1`
   - otherwise say `NO-GO`

## Important
No performance claims in this turn.
No champion changes in this turn.
