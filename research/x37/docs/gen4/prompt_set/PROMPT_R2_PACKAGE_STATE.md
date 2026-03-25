# PROMPT R2 - Package Redesign State (Use this after R1 in the same chat)

Package the outputs already produced in this redesign freeze session into the next clean state pack.

## Instructions
- Do not perform new research.
- Do not change any frozen candidate.
- Do not modify the constitution.
- Only package the outputs already produced in this chat.

## Step 0: Generate input_hash_manifest.txt

Before packaging, create `input_hash_manifest.txt` recording sha256, file size, and line count for every file admitted in this session (constitution, session manifest, input state pack, redesign dossier, and all data files).

**Important**: SHA-256 hashes and exact byte sizes require deterministic computation on raw file bytes. If you are running in an upload-only chat environment without filesystem access, you cannot reliably compute these values. In that case, populate the hash and size columns with `DEFERRED` and add a note at the top of the manifest: `# NOTE: hash and size columns are DEFERRED — operator must run sha256sum/stat to fill them before packaging.` The operator is responsible for completing the manifest before the state pack is sealed.

## Required deliverables

Create `state_pack_vN+1` containing:
- `research_constitution_version.txt`
- `program_lineage_id.txt`
- `system_version_id.txt`
- `system_version_manifest.json`
- `session_summary.md`
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv` (parent rows carried forward + new rows appended for redesigned candidates from R1 step 3)
- `forward_daily_returns.csv` (header-only for new version; parent version rows **must be** archived into the parent state pack before sealing)
- `forward_evaluation_ledger.csv` (header-only for new version; parent version rows **must be** archived into the parent state pack before sealing)
- `contamination_map.md`
- `input_hash_manifest.txt`
- `frozen_system_specs/`
- `impl/` — regenerated implementation files matching the new frozen specs
- `warmup_buffers/` — **required** if any candidate in `portfolio_state.json` has `reconstructable_from_warmup_only: true`, OR if `warmup_requirements` has any nonzero bar count. Omit only if all candidates have `reconstructable_from_warmup_only: false` AND all `warmup_requirements` values are zero.
- `redesign_dossier.md` — the dossier that was validated in R0. Include unchanged so that future sessions can audit the redesign trigger, scope, search accounting, and DOF justification without relying on the original chat.

If any required file is missing, generate it now only from information already established in this chat.

## Required output sections
1. `Packaged Files`
2. `Version Lineage After Packaging` — show parent → new version chain
3. `Champion Status After Packaging`
4. `Evidence Clock Status` — confirm zero for new version
5. `Allowed Next Action`
6. `Forbidden Next Action`

The final line must explicitly say:

`STOP THIS CHAT. OPEN A NEW CHAT FOR FORWARD EVALUATION OF THE NEW VERSION WHEN THE NEXT REVIEW WINDOW IS READY.`
