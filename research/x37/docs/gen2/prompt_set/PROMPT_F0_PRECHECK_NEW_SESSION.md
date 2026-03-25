# PROMPT F0 - Forward Evaluation Precheck (Use this in a brand-new chat)

You are starting a **forward evaluation session**.

Your job in this turn is **only** to perform the session precheck.
Do not redesign candidates.
Do not change the constitution.
Do not score the new data yet.

## Inputs you may use in this turn
- `research_constitution_v2.0.yaml`
- latest `state_pack_vN`
- appended data delta files
- optional warmup buffer files
- `session_manifest.json`
- optional `input_hash_manifest.txt`

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
   - confirm that the evaluation window begins after the last frozen timestamp
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
