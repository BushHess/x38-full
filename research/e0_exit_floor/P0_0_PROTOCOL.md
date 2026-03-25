# P0.0 Exit-Floor Protocol

## Objective

Test whether a very small `support-floor` exit overlay can improve the current
anchor `X0_E5EXIT` by reducing the two remaining dominant failure modes:

- `late_exit_giveback`
- `trail_stop_noise`

The family under test is intentionally narrow. This is not a broad redesign of
the strategy. It is a controlled test of one exit geometry idea.

## Context

Locked prior evidence:

- `ML / XGBoost` was killed in `research/ml0_feasibility`
- `entry stretch gate` was interesting but not promotable in
  `research/e0_entry_hygiene`
- `re-entry / recovery` was killed in `research/e0_reentry`
- current anchor is `X0_E5EXIT`

Forensics source:

- `research/e0_forensics/P0_1_INITIAL_REPORT.md`

## Hypothesis

`X0_E5EXIT` already reduced some raw trail noise through robust ATR, but it
still exits only on:

- robust ATR trailing stop
- EMA cross-down

That leaves room for a small structural floor exit:

- rolling support break
- or rolling support break combined with EMA-slow floor

The hope is to catch giveback earlier without reopening the rejected staleness
family.

## Locked Scope

- no entry changes
- no re-entry logic
- no sizing changes
- no D1 regime changes
- no parameter sweep
- no ML

## Candidate Set

Reference:

- `X0_E5EXIT`

Candidates:

- `X0E5_LL30`
  - add early exit when `close < rolling_low(low.shift(1), 30)`
- `X0E5_FLOOR_SM`
  - add early exit when `close < max(ll30, ema_slow - 3.0 * robust_ATR)`
  - parameters borrowed from the `SM` family defaults
- `X0E5_FLOOR_LATCH`
  - add early exit when `close < max(ll30, ema_slow - 2.0 * robust_ATR)`
  - ATR multiplier borrowed from the `LATCH` family default

Notes:

- `30` bars is not tuned here; it is the structural `slow // 4` value for
  `slow = 120`
- `2.0` and `3.0` are inherited from existing exit families, not optimized in
  this branch

## Benchmark

Phase 1 benchmark:

- period: `2019-01-01` to `2026-02-20`
- scenarios: `smart`, `base`, `harsh`
- recent holdout slice: `2024-01-01` to `2026-02-20` on `harsh`
- trade-level attribution on `harsh`

## Acceptance Criteria

A candidate is interesting only if all of the following hold:

1. It improves the `X0_E5EXIT` family baseline on full-period `harsh`
   - higher `Sharpe` or `Calmar`
   - and no material `MDD` deterioration
2. It improves recent holdout `harsh` enough to avoid immediate kill
3. It reduces loss concentration in at least one of:
   - `late_exit_giveback`
   - `trail_stop_noise`

If no candidate satisfies those conditions, mark the branch:

- `KILL_EXIT_FLOOR`

If one candidate survives, move to validation:

- rolling OOS
- paired bootstrap
- final promote / hold / kill verdict
