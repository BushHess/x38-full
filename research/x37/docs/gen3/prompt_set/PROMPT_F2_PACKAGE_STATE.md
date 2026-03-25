# PROMPT F2 - Package Forward State (Use this after F1 in the same chat)

Package the outputs already produced in this forward evaluation session into the next clean state pack.

## Instructions
- Do not perform new analysis.
- Do not redesign candidates.
- Do not change the constitution.
- Only package the outputs already produced in this chat.

## Step 0: Update hash manifests

Before packaging, update two hash manifest files:

**`input_hash_manifest.txt`** — sha256, file size, and line count for every file admitted as input in this session (constitution, session manifest, input state pack, and all appended delta CSV files). If the manifest was provided at session start, include it and add entries for any newly admitted files; otherwise generate it now from all admitted inputs.

**`artifact_hash_manifest.txt`** — sha256, file size, and line count for every frozen output artifact: all files in `frozen_system_specs/` and `frozen_implementations/`. If candidates are unchanged from the input state pack, carry the manifest forward unchanged. If any candidate was promoted or replaced, regenerate the affected entries.

**Important**: SHA-256 hashes and exact byte sizes require deterministic computation on raw file bytes. If you are running in an upload-only chat environment without filesystem access, you cannot reliably compute these values. In that case, populate the hash and size columns with `DEFERRED` and add a note at the top of each manifest: `# NOTE: hash and size columns are DEFERRED — operator must run sha256sum/stat to fill them before sealing.` The operator is responsible for completing both manifests before the state pack is sealed.

**State pack status**: If all hashes in both manifests are resolved, set `state_pack_status` to `"sealed"` in `portfolio_state.json`. If any hash in either manifest is `DEFERRED`, set `state_pack_status` to `"draft"`. A draft state pack must NOT be used as input to a new session until the operator resolves all DEFERRED entries and sets the status to `"sealed"`.

## Required deliverables

Create `state_pack_vN+1` containing:
- `research_constitution_version.txt`
- `lineage_id.txt`
- updated `session_summary.md`
- updated `candidate_registry.json`
- unchanged or updated `meta_knowledge_registry.json`
- updated `portfolio_state.json`
- unchanged `historical_seed_audit.csv`
- appended `forward_daily_returns.csv`
- appended `forward_evaluation_ledger.csv`
- updated `contamination_map.md`
- updated `input_hash_manifest.txt`
- updated `artifact_hash_manifest.txt`
- unchanged or superseded `frozen_system_specs/`
- unchanged or superseded `frozen_implementations/`
- optional `warmup_buffers/`

## Required output sections
1. `Packaged Files`
2. `Champion Status After Packaging`
3. `Allowed Next Action`
4. `Forbidden Next Action`

The final line must explicitly say:

`STOP THIS CHAT. OPEN A NEW CHAT FOR THE NEXT FORWARD REVIEW WINDOW OR FOR GOVERNANCE REVIEW.`
