# Redesign Dossier

This dossier is a required gate for any redesign_freeze session.
If you cannot fill it concisely, you probably do not have sufficient reason to redesign.

## Version Identity
- parent_system_version_id:
- proposed_new_system_version_id:
- program_lineage_id:
- constitution_version:

## Redesign Trigger
Which allowed trigger fired? (check exactly one)
- [ ] consecutive_hard_constraint_failure: champion failed hard constraints in 2 consecutive standard reviews
- [ ] emergency_breach: emergency review trigger fired
- [ ] proven_bug: logic/data bug proven to affect trade/PnL
- [ ] structural_deficiency: challenger shows meaningful paired advantage across multiple reviews

## Evidence Window
- Forward data observed: (date range)
- Forward days accumulated: (must be >= 180)
- Forward entries accumulated: (must be >= 6)
- Last freeze date: (must be >= 180 days ago, unless emergency/bug)

## Failure Claim
What went wrong? Be specific. Reference cumulative metrics, not single-window noise.

## Hypothesis
Why did it happen? What structural deficiency or bug caused the failure?

## Proposed Fix
Describe exactly ONE principal change:
-

### Change Scope
- Logic blocks changed: (max 1)
- Tunables added/changed: (max 3)
- Execution semantics changed: (max 1)
- Is this within the minor redesign budget? (yes/no)
- If no: escalate to governance as major redesign.

### Complexity Impact
- Current logical layers:
- After redesign logical layers:
- Current tunable quantities:
- After redesign tunable quantities:
- Net DOF change: (+N or 0)
- If DOF increases: justify why the complexity tax is warranted.

## Expected Effect
What should improve? By how much (order of magnitude)?

## Do-Not-Touch List
What must NOT change in this redesign? List explicitly.
-
-
-

## Evidence Clock Reset Justification
Why is the cost of resetting the evidence clock (losing all accumulated forward evidence for the parent version) justified by this change?

## Search Accounting
- Total variants explored in sandbox:
- Total configurations tried:
- Variants rejected and why (list each):
  -
- This proposal was selected because:
- Total search DOF across all sandbox iterations:

## Minor vs Major Classification
- Net DOF change from parent: (+N)
- Cumulative DOF across all versions in lineage:
- Initial version (V1) DOF:
- Ratio (cumulative / initial): (must be < 2.0, or governance required)
- Classification: (minor / major)
- If major: governance approval reference:
