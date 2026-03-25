# PROMPT D1 - Seed Discovery Execution (GEN2 MONOLITHIC — not used since gen3)

> **Note**: This file is from gen2 and uses the old archetype-based search space.
> Gen3+ uses the split version (D1a-D1f) with open mathematical search.
> See `PROMPT_INDEX_EN.md` for the current prompt sequence.

Proceed with **seed discovery** under the active constitution and the admitted historical snapshot.

## Mission

Produce exactly:
- 1 champion seed
- up to 2 challenger seeds
- frozen candidate definitions
- a candidate registry
- a meta-knowledge registry
- a contamination map
- a portfolio state
- a historical seed audit
- an empty forward evaluation ledger
- an input hash manifest if it was supplied or can be derived from admitted files

## Hard instructions
- Use only the admitted raw historical snapshot and the constitution.
- Treat the historical snapshot as **candidate-mining-only**.
- Do not claim clean external OOS.
- Do not import prior winners or prior reports.
- Do not exceed the constitution hard caps.
- Do not change the constitution.
- Do not search beyond the three admitted archetypes.
- Do not output more than 3 live candidates total.

## Required procedure
1. Ingest and canonicalize the raw files to the 13-column schema.
2. Run data quality checks and log anomalies without inventing synthetic repairs.
3. Apply the historical seed protocol:
   - warmup
   - discovery walk-forward
   - holdout
   - reserve_internal
4. Search the admitted archetypes under the constitution hard caps.
5. Score candidates using the constitution hard constraints and ranking rules.
6. Freeze:
   - champion seed
   - up to two challenger seeds
7. Draft:
   - `candidate_registry.json`
   - `meta_knowledge_registry.json`
   - `portfolio_state.json`
   - `historical_seed_audit.csv`
   - `forward_evaluation_ledger.csv` with header only
   - `contamination_map.md`
   - `frozen_system_specs/`
   - `input_hash_manifest.txt`

## Required output sections
1. `Seed Discovery Summary`
2. `Champion Seed`
3. `Challenger Seeds`
4. `Rejected Candidate Summary`
5. `Evidence Labels At Seed Freeze`
6. `Files Prepared For Packaging`

## Important

Stop after preparing the outputs.
Do not start packaging yet. Packaging is the next prompt.
