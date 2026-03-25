# PROMPT R0 - Redesign Freeze Precheck (Use this in a brand-new chat)

You are starting a **redesign freeze session**.

Your job in this turn is **only** to perform the session precheck and validate the redesign dossier.
Do **not** execute the redesign yet.
Do **not** freeze a new version yet.
Do **not** change the constitution.

## Inputs you may use in this turn
- `research_constitution_v4.0.yaml`
- latest `state_pack_vN` (including forward evidence from parent version)
- full data set (historical + all appended data)
- `redesign_dossier.md` (required gate)
- `session_manifest.json` with `mode: "redesign_freeze"`
- optional `input_hash_manifest.txt`

## Required output sections
1. `Mode Confirmation`
   - confirm this is a redesign_freeze session
   - confirm constitution version
   - confirm the incoming state pack version
   - confirm the parent `system_version_id` being redesigned
2. `Redesign Dossier Audit`
   - confirm `redesign_dossier.md` is present and complete
   - confirm exactly one redesign trigger is checked and valid
   - confirm the failure claim references cumulative metrics, not single-window noise
   - confirm exactly one principal change is proposed
   - confirm change scope is within budget (max 1 logic block, max 3 tunables, max 1 execution change)
   - confirm minor vs major classification
   - if major: confirm governance approval reference is present
3. `Guardrail Verification`
   - cooldown: >= 180 days since last freeze (unless emergency/bug exception)
   - evidence threshold: >= 180 forward days AND >= 6 entries accumulated for parent version
   - redesign budget: no more than 1 major redesign per 180 calendar days
   - DOF circuit breaker: cumulative DOF < 2x initial version DOF (or governance override)
4. `Complexity Impact Assessment`
   - current logical layers → after redesign
   - current tunable quantities → after redesign
   - net DOF change
   - complexity tax impact on ranking
5. `Data Audit`
   - confirm all data (historical + appended) is available
   - confirm the proposed `freeze_cutoff_utc` (latest data timestamp)
   - confirm all data up to `freeze_cutoff_utc` will be seen data for the new version
   - confirm the evidence clock will reset to zero
6. `Go / No-Go`
   - if all guardrails pass and dossier is valid, say `GO FOR R1`
   - otherwise say `NO-GO` and list the failing conditions

## Important
No redesign execution in this turn.
No new candidate freezing in this turn.
No performance claims in this turn.
