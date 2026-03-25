# PROMPT G2 - Package Governance Outcome (Use this after G1 in the same chat)

Package the governance outcome already established in this chat.

## Instructions
- Do not run strategy search.
- Do not invent new evidence.
- Only package the decision already reached.

## If the decision is KEEP CURRENT VERSION

Create:
- `governance_decision.md`
- `constitution_status.txt`

## If the decision is PREPARE NEXT MAJOR VERSION

Create:
- `research_constitution_vNEXT_MAJOR.0.yaml`
- `migration_note_current_to_next_major.md`
- `governance_decision.md`
- `constitution_status.txt`

Replace `NEXT_MAJOR` with the next integer major version.

## Required output sections
1. `Packaged Governance Files`
2. `Effective Constitution Version`
3. `Allowed Next Action`
4. `Forbidden Next Action`

The final line must explicitly say:

`STOP THIS CHAT. IF A NEW CONSTITUTION WAS RELEASED, START A NEW LINEAGE UNDER THAT VERSION.`
