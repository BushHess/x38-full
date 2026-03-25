# PROMPT F2 - Package Forward State (Use this after F1 in the same chat)

Package the outputs already produced in this forward evaluation session into the next clean state pack.

## Instructions
- Do not perform new analysis.
- Do not redesign candidates.
- Do not change the constitution.
- Only package the outputs already produced in this chat.

## Required deliverables

Create `state_pack_vN+1` containing:
- `research_constitution_version.txt`
- `lineage_id.txt`
- updated `session_summary.md`
- updated `candidate_registry.json`
- unchanged or updated `meta_knowledge_registry.json`
- updated `portfolio_state.json`
- unchanged `historical_seed_audit.csv`
- appended `forward_evaluation_ledger.csv`
- updated `contamination_map.md`
- updated `input_hash_manifest.txt` if available
- unchanged or superseded `frozen_system_specs/`
- optional `warmup_buffers/`

## Required output sections
1. `Packaged Files`
2. `Champion Status After Packaging`
3. `Allowed Next Action`
4. `Forbidden Next Action`

The final line must explicitly say:

`STOP THIS CHAT. OPEN A NEW CHAT FOR THE NEXT FORWARD REVIEW WINDOW OR FOR GOVERNANCE REVIEW.`
