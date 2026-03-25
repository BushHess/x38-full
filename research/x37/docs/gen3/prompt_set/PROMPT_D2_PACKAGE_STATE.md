# PROMPT D2 - Package Seed State (Use this after D1f3 in the same chat)

Package the outputs already produced in this seed discovery session into a clean `state_pack_v1`.

## Instructions
- Do not perform new research.
- Do not change any frozen candidate.
- Do not rescore anything.
- Do not redesign the constitution.
- Only package the outputs already produced in this chat.

## Step 0: Generate hash manifests

Before packaging, create two hash manifest files:

**`input_hash_manifest.txt`** — sha256, file size, and line count for every file admitted as input in this session (constitution, session manifest, schema conventions doc, and all raw CSV files). If the manifest was provided at session start, include it unchanged; otherwise generate it now.

**`artifact_hash_manifest.txt`** — sha256, file size, and line count for every frozen output artifact: all files in `frozen_system_specs/` and `frozen_implementations/`. This manifest must always be generated fresh from the actual output files.

**Important**: SHA-256 hashes and exact byte sizes require deterministic computation on raw file bytes. If you are running in an upload-only chat environment without filesystem access, you cannot reliably compute these values. In that case, populate the hash and size columns with `DEFERRED` and add a note at the top of each manifest: `# NOTE: hash and size columns are DEFERRED — operator must run sha256sum/stat to fill them before sealing.` The operator is responsible for completing both manifests before the state pack is sealed.

**State pack status**: If all hashes in both manifests are resolved, set `state_pack_status` to `"sealed"` in `portfolio_state.json`. If any hash in either manifest is `DEFERRED`, set `state_pack_status` to `"draft"`. A draft state pack must NOT be used as input to a new session until the operator resolves all DEFERRED entries and sets the status to `"sealed"`.

## Required deliverables

Create `state_pack_v1` containing:
- `research_constitution_version.txt`
- `lineage_id.txt`
- `session_summary.md`
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_daily_returns.csv` (header-only; no forward data exists yet)
- `forward_evaluation_ledger.csv`
- `contamination_map.md`
- `input_hash_manifest.txt`
- `artifact_hash_manifest.txt`
- `frozen_system_specs/`
- `frozen_implementations/` — one `d1d_impl_{candidate_id}.py` per live candidate (the exact implementation files created in D1d1). These are the machine-executable counterparts to the frozen system specs.
- `warmup_buffers/` — **required** if any candidate in `portfolio_state.json` has `reconstructable_from_warmup_only: true`; include sufficient bars per `warmup_requirements`. Omit if all candidates have `reconstructable_from_warmup_only: false`.

If any required file is missing, generate it now only from information already established in this chat.

## Required output sections
1. `Packaged Files`
2. `Champion Status After Packaging`
3. `Allowed Next Action`
4. `Forbidden Next Action`

The final line must explicitly say one of:

- If live candidates exist: `STOP THIS CHAT. OPEN A NEW CHAT FOR FORWARD EVALUATION WHEN THE NEXT REVIEW WINDOW IS READY.`
- If NO_ROBUST_CANDIDATE: `STOP THIS CHAT. NO CANDIDATES TO FORWARD-EVALUATE. START GOVERNANCE REVIEW OR NEW SEED DISCOVERY ON A DIFFERENT SNAPSHOT.`
