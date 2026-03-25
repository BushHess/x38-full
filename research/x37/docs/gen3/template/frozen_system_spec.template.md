# Frozen System Specification Template

## Identity
- candidate_id:
- mechanism_type:
- role: (champion or challenger)
- lineage_id:
- constitution_version:
- frozen_at_utc:

## Market Domain
- venue:
- symbol:
- timeframes used:
- data fields used:

## Signal Logic
Describe the exact feature formulas, lookbacks, thresholds, and tails.

## Execution Logic
Describe:
- decision timestamp,
- fill timestamp,
- entry condition,
- exit condition,
- hold condition,
- cost application.

## Position Sizing
Describe notional fraction rules.

## Tunable Quantities
List every tunable quantity and its frozen value.

## Logical Layers
List all layers in order and their roles.

## Warmup Requirement
State the minimum bars required on each timeframe.

## Evidence Summary
- holdout_hard_constraint_result: (PASS or FAIL)
- Summarize seed-stage discovery, holdout, reserve metrics and latest forward status.

## Known Risks
List known fragilities, such as low turnover or path-dependent exits.
