# Frozen System Specification Template

## Version Identity
- system_version_id:
- parent_system_version_id:
- freeze_cutoff_utc:
- design_inputs_end_utc:
- reason_for_freeze:

## Candidate Identity
- candidate_id:
- mechanism_type:
- role: (champion or challenger)
- program_lineage_id:
- constitution_version:
- frozen_at_utc:

## Market Domain
- venue:
- symbol:
- timeframes used:
- data fields used:

## Signal Logic

Write the exact signal logic as **unambiguous pseudocode** (not prose). Every formula, comparison, and branching condition must be explicit enough that an independent implementer produces bit-identical output on the same data. Use variable names matching the canonical input schema.

Example level of precision required:
```
ema_slow = EMA(close_h4, period=slow_period)
ema_fast = EMA(close_h4, period=slow_period // 2)
entry_long = (ema_fast > ema_slow) AND (NOT in_position)
```

If a formula is complex, define intermediate variables. Do NOT use vague phrases like "when trend is up" or "volatility is high".

## Execution Logic

Write the exact execution semantics as **unambiguous pseudocode**:
- decision timestamp: which bar's close generates the signal,
- fill timestamp: which bar's open executes the fill,
- entry condition: exact pseudocode,
- exit condition: exact pseudocode (including trail stop update rule if applicable),
- hold condition: exact pseudocode,
- cost application: exact formula (e.g., `nav *= (1 - cost_per_side)` at each entry and exit).

## Position Sizing

Write the exact sizing rule as pseudocode (e.g., `fraction = 1.0 if signal_long else 0.0`).

## Tunable Quantities
List every tunable quantity and its frozen value.

## Logical Layers
List all layers in order and their roles.

## Warmup Requirement
State the minimum bars required on each timeframe.

## Evidence Summary
- holdout_hard_constraint_result: (PASS or FAIL)
- Summarize seed-stage discovery, holdout, reserve metrics and latest forward status.
- forward_evidence_days: (for this system_version_id)
- forward_evidence_entries: (for this system_version_id)

## Redesign Lineage (if parent exists)
- parent_system_version_id:
- what_changed_from_parent:
- redesign_trigger:
- redesign_dossier_ref:

## Known Risks
List known fragilities, such as low turnover or path-dependent exits.
