# PROMPT D2 - Package Seed State (Use this after D1f in the same chat)

Package the outputs already produced in this seed discovery session into a clean `state_pack_v1`.

## Instructions
- Do not perform new research.
- Do not change any frozen candidate.
- Do not rescore anything.
- Do not redesign the constitution.
- Only package the outputs already produced in this chat.

## Required deliverables

Create `state_pack_v1` containing:
- `research_constitution_version.txt`
- `lineage_id.txt`
- `session_summary.md`
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_evaluation_ledger.csv`
- `contamination_map.md`
- `input_hash_manifest.txt` if available
- `frozen_system_specs/`

If any required file is missing, generate it now only from information already established in this chat.

## Required output sections
1. `Packaged Files`
2. `Champion Status After Packaging`
3. `Allowed Next Action`
4. `Forbidden Next Action`

The final line must explicitly say:

`STOP THIS CHAT. OPEN A NEW CHAT FOR FORWARD EVALUATION WHEN THE NEXT REVIEW WINDOW IS READY.`
