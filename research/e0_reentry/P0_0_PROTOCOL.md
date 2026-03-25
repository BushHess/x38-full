# P0.0 Stretch-Recovery Protocol

## Objective

Test whether the `stretch gate` can be improved by a very small recovery
mechanism after a stretched chop entry is blocked.

The baseline from the prior branch is:

- reference family baseline: `X0_E5EXIT`
- current gated baseline: `X0E5_CHOP_STRETCH18`

## Key Design Constraint

Once `stretch gate` is the baseline, a "re-entry after compression" is not a
new mechanism. The stretch-only baseline already enters again as soon as the
entry is no longer stretched.

Therefore the only meaningful add-on mechanisms are:

1. `stretched override`
   - allow a blocked stretched entry immediately if flow is exceptionally strong
2. `delayed stretched confirmation`
   - after a block, allow entry a few bars later if the move stays stretched and
     confirms further

## Candidate Set

- `X0_E5EXIT`
- `X0E5_CHOP_STRETCH18`
- `X0E5_OVR_BROAD`
  - immediate override if:
    - chop stretch block would fire
    - `VDO >= 0.005`
    - `price_to_slow_atr < 3.0`
- `X0E5_OVR_NARROW`
  - immediate override if:
    - chop stretch block would fire
    - `VDO >= 0.005`
    - `2.5 <= price_to_slow_atr < 3.0`
- `X0E5_RE6_IMPULSE`
  - after a block, within `6` bars, allow entry if:
    - still stretched (`1.8 < price_to_slow_atr < 3.0`)
    - `close > blocked_close`
    - `VDO >= 0.008`
- `X0E5_OVR_NARROW_RE6`
  - combine `OVR_NARROW` and `RE6_IMPULSE`

## Locked Scope

- no parameter sweep
- no ML
- no new exit logic
- no new sizing logic

## Evaluation

Phase 1 benchmark:
- full period `2019-01-01` to `2026-02-20`
- scenarios: `smart`, `base`, `harsh`
- recent holdout `2024-01-01` to `2026-02-20` on `harsh`

Only if a candidate beats `X0E5_CHOP_STRETCH18` convincingly in Phase 1 does it
deserve a second validation phase.

## Branch Kill Rule

If none of the recovery candidates clearly beats `X0E5_CHOP_STRETCH18` on both:

- full-period harsh
- recent holdout harsh

then this branch is `KILL_RECOVERY_MECHANICS`.
