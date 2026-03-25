# PROMPT D2 - Package Seed State (Use this after D1f3 in the same chat)

Package the outputs already produced in this seed discovery session into a clean `state_pack_v1`.

## Instructions
- Do not perform new research.
- Do not change any frozen candidate.
- Do not rescore anything.
- Do not redesign the constitution.
- Only package the outputs already produced in this chat.

## Step 0: Generate input_hash_manifest.txt

Before packaging, create `input_hash_manifest.txt` recording sha256, file size, and line count for every file admitted in this session (constitution, session manifest, schema conventions doc, and all raw CSV files). If the manifest was provided at session start, include it unchanged; otherwise generate it now.

**Important**: SHA-256 hashes and exact byte sizes require deterministic computation on raw file bytes. If you are running in an upload-only chat environment without filesystem access, you cannot reliably compute these values. In that case, populate the hash and size columns with `DEFERRED` and add a note at the top of the manifest: `# NOTE: hash and size columns are DEFERRED — operator must run sha256sum/stat to fill them before packaging.` The operator is responsible for completing the manifest before the state pack is sealed.

## Required deliverables

Create `state_pack_v1` containing:
- `research_constitution_version.txt`
- `program_lineage_id.txt`
- `system_version_id.txt`
- `system_version_manifest.json`
- `session_summary.md`
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_daily_returns.csv` (header-only; no forward data exists yet)
- `forward_evaluation_ledger.csv`
- `contamination_map.md`
- `input_hash_manifest.txt`
- `frozen_system_specs/`
- `impl/` — copy each `d1d_impl_{candidate_id}.py` into `impl/{candidate_id}.py`. These are convenience artifacts that allow forward evaluation sessions to skip re-implementation. The frozen spec pseudocode remains authoritative.
- `warmup_buffers/` — **required** if any candidate in `portfolio_state.json` has `reconstructable_from_warmup_only: true`, OR if `warmup_requirements` has any nonzero bar count (needed for indicator rolling computation even when serialized state is load-bearing). Include sufficient bars per `warmup_requirements`. Omit only if all candidates have `reconstructable_from_warmup_only: false` AND all `warmup_requirements` values are zero.

If any required file is missing, generate it now only from information already established in this chat.

## Required output sections
1. `Packaged Files`
2. `Champion Status After Packaging`
3. `Allowed Next Action`
4. `Forbidden Next Action`

The final line must explicitly say one of:

- If live candidates exist: `STOP THIS CHAT. OPEN A NEW CHAT FOR FORWARD EVALUATION WHEN THE NEXT REVIEW WINDOW IS READY.`
- If NO_ROBUST_CANDIDATE: `STOP THIS CHAT. NO CANDIDATES TO FORWARD-EVALUATE. PREPARE governance_failure_dossier.md BEFORE STARTING GOVERNANCE REVIEW, OR START NEW SEED DISCOVERY ON A DIFFERENT SNAPSHOT.`
