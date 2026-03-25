# Contamination Map

## Program Identity
- `program_lineage_id`:
- `constitution_version`:
- `latest_state_pack_version`:

## System Version Lineage

| Version | Parent | freeze_cutoff_utc | design_inputs_end_utc | Reason | Evidence days | Status |
|---|---|---|---|---|---|---|
| V1 | — | | | Initial seed discovery | 0 | active |

## Historical Seed Snapshot
- `snapshot_id`:
- used for seed discovery only: yes / no
- clean external OOS claim allowed from this snapshot: no

## Blind Seed Discovery Withheld Inputs
List any prior artifacts that were intentionally not uploaded:
-
-
-

## Forward Evaluation Windows

| Session | Version | Window start UTC | Window end UTC | Clean for version? | Role |
|---|---|---|---|---|---|
| | | | | yes/no | forward_evaluation |

**Clean for version** = true only if `window_start_utc > version.freeze_cutoff_utc`.
A window used to inform a redesign is NOT clean for the redesigned version.

## Overlap Caveats
- Historical seed snapshot remains contaminated for same-file OOS claims.
- Forward-confirmed status requires appended data after the version's freeze_cutoff_utc.
- Forward data used to inform a redesign is seen data for the new version.

## Redesign History
| From version | To version | Redesign trigger | Dossier ref | Date |
|---|---|---|---|---|

## Governance Notes
- last governance review session:
- active known governance concern:
