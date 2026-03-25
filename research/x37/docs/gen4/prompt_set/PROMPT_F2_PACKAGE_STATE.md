# PROMPT F2 - Package Forward State (Use this after F1 in the same chat)

Package the outputs already produced in this forward evaluation session into the next clean state pack.

## Instructions
- Do not perform new analysis.
- Do not redesign candidates.
- Do not change the constitution.
- Only package the outputs already produced in this chat.

## Step 0: Update input_hash_manifest.txt

Before packaging, update `input_hash_manifest.txt` to record sha256, file size, and line count for every file admitted in this session (constitution, session manifest, input state pack, and all appended delta CSV files). If the manifest was provided at session start, include it and add entries for any newly admitted files; otherwise generate it now from all admitted inputs.

**Important**: SHA-256 hashes and exact byte sizes require deterministic computation on raw file bytes. If you are running in an upload-only chat environment without filesystem access, you cannot reliably compute these values. In that case, populate the hash and size columns with `DEFERRED` and add a note at the top of the manifest: `# NOTE: hash and size columns are DEFERRED — operator must run sha256sum/stat to fill them before packaging.` The operator is responsible for completing the manifest before the state pack is sealed.

## Required deliverables

Create `state_pack_vN+1` containing:
- `research_constitution_version.txt`
- `program_lineage_id.txt`
- `system_version_id.txt`
- `system_version_manifest.json`
- updated `session_summary.md`
- updated `candidate_registry.json`
- unchanged or updated `meta_knowledge_registry.json`
- updated `portfolio_state.json`
- unchanged `historical_seed_audit.csv`
- appended `forward_daily_returns.csv`
- appended `forward_evaluation_ledger.csv`
- updated `contamination_map.md`
- updated `input_hash_manifest.txt`
- unchanged or superseded `frozen_system_specs/`
- unchanged `impl/` (carry forward from input state pack if present)
- `warmup_buffers/` — **required** if any candidate in `portfolio_state.json` has `reconstructable_from_warmup_only: true`, OR if `warmup_requirements` has any nonzero bar count. Omit only if all candidates have `reconstructable_from_warmup_only: false` AND all `warmup_requirements` values are zero.

## Required output sections
1. `Packaged Files`
2. `Champion Status After Packaging`
3. `Allowed Next Action`
4. `Forbidden Next Action`

The final line must explicitly say:

`STOP THIS CHAT. OPEN A NEW CHAT FOR THE NEXT FORWARD REVIEW WINDOW, SANDBOX EXPLORATION (IF REDESIGN IS MOTIVATED — SEE FORWARD_DECISION_POLICY), OR GOVERNANCE REVIEW.`
