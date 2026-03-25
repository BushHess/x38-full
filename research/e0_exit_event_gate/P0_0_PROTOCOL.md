# P0.0 Exit-Event Gate Protocol

## Objective

Test whether the `research-only` exit-floor mechanism can be rescued by a very
small event gate.

Reference family state:

- operational anchor: `X0_E5EXIT`
- research-only floor variant: `X0E5_FLOOR_LATCH`

Source evidence:

- `research/e0_exit_floor/P0_2_VALIDATION_REPORT.md`
- `research/e0_exit_floor/P0_3_EVENT_REVIEW_REPORT.md`

## Core Question

The floor-exit family showed a real mechanism, but not a promotable one.

The next question is not:

- "what other exit family should we try?"

The next question is:

- "among floor-exit events, when is the early exit helpful and when does it cut
  off later winners?"

## Event Definition

This branch studies only `actionable floor events`:

- `floor_hit == True`
- `trail_hit_same_bar == False`
- `trend_down_same_bar == False`

Reason:

- if floor, trail, or trend exit all trigger on the same bar, then the floor is
  redundant and cannot explain the economic difference

## Locked Scope

- no ML
- no re-entry
- no entry changes
- no new exit family
- only event-conditioned gating on top of `X0E5_FLOOR_LATCH`

## Phase 1: Event Scan

Build an event table for all floor-hit bars with:

- entry age
- peak age
- MFE-to-date
- giveback-from-peak
- ER30
- VDO
- EMA spread
- price vs EMA slow
- price vs floor
- current D1 regime

Label each actionable matched event:

- `good_exit` if candidate PnL > reference PnL
- `bad_exit` if candidate PnL < reference PnL
- `neutral` otherwise

Then evaluate a tiny library of monotonic rules only.

## Phase 2: Benchmark

Only if Phase 1 finds a separator that is both:

- economically positive on event delta
- and structurally simple

then benchmark at most `1-2` gated candidates on:

- full period
- recent holdout

## Phase 3: Validation

Only if a gated candidate beats `X0_E5EXIT` and beats raw `X0E5_FLOOR_LATCH`
cleanly on benchmark, run:

- rolling OOS
- paired bootstrap
- pair diagnostic

## Kill Rule

If event scan cannot produce a simple gate with convincing economic separation,
or if the gated candidate still relies mainly on sequencing spillover, mark:

- `KILL_EVENT_GATE`

If it helps but still fails validation, mark:

- `HOLD_RESEARCH_ONLY`
