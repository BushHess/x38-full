# PROMPT D0 - Seed Discovery Precheck (Use this in a brand-new chat)

You are starting a **seed discovery session** under a frozen constitution.

Your job in this turn is **only** to perform the session precheck.
Do **not** run research yet.
Do **not** propose, score, or compare strategies yet.
Do **not** redesign the constitution.

## Inputs you may use in this turn
- `research_constitution_v3.0.yaml`
- `FILE_AND_SCHEMA_CONVENTIONS_EN.md`
- raw historical snapshot files
- `session_manifest.json`
- optional `input_hash_manifest.txt`
- optional `snapshot_notes.md`

## Inputs you must ignore if present
- prior reports
- prior winners
- prior shortlist tables
- prior system specs
- prior evaluation ledgers
- prior benchmark definitions
- prior state packs
- prior contamination logs

## Required output sections
1. `Mode Confirmation`
   - confirm this is a seed discovery session
   - confirm the constitution file is readable
   - confirm the snapshot id, timeframes, and date range
2. `Admissible Input Audit`
   - list the files actually used
   - list any files present but inadmissible for blind discovery
3. `Contamination Status`
   - state that the historical snapshot is candidate-mining-only
   - state clearly that no clean external OOS claim may be made from this snapshot
4. `Execution Boundaries`
   - state the search space philosophy (open mathematical, measurement-first)
   - state the hard caps (layers, tunables, configs)
   - state the hard constraints
   - state the required outputs
5. `Go / No-Go`
   - if inputs are admissible and sufficient, say `GO FOR D1`
   - otherwise say `NO-GO` and list the missing or invalid items

## Required style
- concise
- technical
- no strategy results
- no redesign suggestions
