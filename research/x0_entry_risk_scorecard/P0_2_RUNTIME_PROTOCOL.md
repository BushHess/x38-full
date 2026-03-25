# P0.2 Protocol -- Runtime Risk Tag Probe

## Question

Can the `x0_entry_risk_v1` scorecard be attached to strategy runtime without
changing trading behavior?

## Objective

Test a research-only implementation that:

- leaves entry/exit decisions unchanged
- adds the risk bin only to `entry_reason`
- verifies that backtest outputs remain parity-clean except for the tagged
  `entry_reason`

## Why this matters

The engine already persists `Signal.reason -> Fill.reason -> Trade.entry_reason`.
If that path is stable enough, the project can surface entry risk warnings
without changing signal logic or adding ML / new engine metadata.

## Probe Design

Create two research-only wrapper strategies:

- `X0RiskTaggedStrategy`
- `X0E5RiskTaggedStrategy`

Both wrappers:

- reuse the original strategy logic
- compute the scorecard at entry time
- replace `x0_entry` with `x0_entry|risk=<risk_level>`
- leave exits unchanged

## Validation Criteria

Probe passes only if all of the following hold:

1. fills are identical to baseline, ignoring `reason`
2. trades are identical to baseline, ignoring `entry_reason`
3. summary metrics are identical
4. runtime risk tags match the offline scorecard flags from
   `p0_1_trade_flags.csv`

## Deliverables

- parity table
- runtime risk table
- tagged trade table
- final memo
