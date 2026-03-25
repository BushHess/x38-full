# v12_emdd_ref_fix

Intent:
- Keep a dedicated V12 strategy line for EMDD reference-fix work.
- Step 2 focuses on parity: V12 in `emdd_ref_mode=legacy` must reproduce V10 baseline.

Invariants:
- `strategy_id` is fixed to `v12_emdd_ref_fix`.
- Class names stay V12-specific (`V12EMDDRefFixConfig`, `V12EMDDRefFixStrategy`).
- `emdd_ref_mode` supports `legacy|fixed`, default `legacy` for parity stage.
- Core entry/exit/sizing logic is copied from V10 baseline to preserve behavior.
