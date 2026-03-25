# P0.0 Entry Hygiene Protocol

## Objective

Test whether a very small, mechanism-driven entry gate can reduce the two
dominant E0/X0 failure modes identified in
[e0_forensics](../e0_forensics/P0_1_INITIAL_REPORT.md):

- `false_breakout`
- `trail_stop_noise`

The goal is not to search for a new strategy family. The goal is to test a
single hypothesis:

`When X0-style entries are taken inside chop, weak-flow and over-stretched entries are overrepresented among losing trades.`

## Scope

- Canonical data: `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- Reporting window: `2019-01-01` to `2026-02-20`
- Warmup: `365` days
- Cost scenarios: `smart`, `base`, `harsh`
- Engine: current `BacktestEngine` with next-open fills

## Locked Context

These values are locked from the forensics branch and are not tuned here:

- `ER_LOOKBACK = 30`
- `ER_CHOP = 0.25`
- `slow_period = 120`
- `trail_mult = 3.0`
- `vdo_threshold = 0.0`
- `d1_ema_period = 21`

## Candidate Set

Reference baselines:

- `E0`
- `X0`
- `X0_E5EXIT`

Standard-exit entry gates:

- `X0_CHOP_VDO2`
  - In chop (`ER30 < 0.25`), require `VDO >= 0.002`
- `X0_CHOP_STRETCH18`
  - In chop, reject entry when `(close - ema_slow) / ATR > 1.8`
- `X0_CHOP_COMBO`
  - In chop, reject entry when both:
    - `(close - ema_slow) / ATR > 1.6`
    - `VDO < 0.003`

Robust-exit mirrors:

- `X0E5_CHOP_VDO2`
- `X0E5_CHOP_STRETCH18`
- `X0E5_CHOP_COMBO`

## Why These Gates

The thresholds are not from a broad sweep. They are fixed from the harsh-scenario
trade table in `e0_forensics`:

- `vdo < 0.002` in `chop + D1 on` was a negative-PnL cohort
- `price_to_slow_atr > 1.8` in `chop + D1 on` was a negative-PnL cohort
- `price_to_slow_atr > 1.6 and vdo < 0.003` isolated a smaller, weaker cohort

## Acceptance Criteria

A candidate is interesting only if it satisfies both:

1. It improves its family baseline on `harsh` in a meaningful way:
   - higher `Sharpe` or `Calmar`
   - and no material `MDD` deterioration
2. It reduces `false_breakout` loss in the harsh trade-level forensics

`trail_stop_noise` is tracked, but it is treated as a secondary diagnostic here.
It is partly an exit-geometry problem, so it should not be used as a hard kill
criterion for an entry-hygiene branch.

If no candidate clears those conditions, this branch is marked
`KILL_ENTRY_HYGIENE` and the next mechanism should shift away from entry gating.
