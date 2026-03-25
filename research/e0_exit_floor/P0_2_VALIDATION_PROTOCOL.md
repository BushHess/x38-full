# P0.2 Exit-Floor Validation Protocol

## Scope

Validate only the survivors from `P0.1`:

- `X0E5_LL30`
- `X0E5_FLOOR_LATCH`

`X0E5_FLOOR_SM` is excluded from Phase 2 because it produced identical
benchmark metrics and identical floor-hit counts to `X0E5_LL30` in `P0.1`.

## Reference

- `X0_E5EXIT`

## Validation Stack

For each candidate vs reference:

1. full-period backtest
2. pre-holdout / holdout split
3. rolling OOS windows
4. paired block bootstrap on actual engine equity
5. pair diagnostic review

## Pass Conditions

A candidate is promotable only if all of the following hold:

1. holdout is not worse on `Calmar`
2. rolling OOS wins at least half the windows on `Calmar`
3. paired bootstrap gives:
   - `P(Sharpe candidate > reference) > 0.55`
   - `P(-MDD candidate > reference) > 0.55`
4. pair diagnostic does not require `escalate_full_manual_review`

If no candidate passes, the branch verdict is:

- `HOLD_RESEARCH_ONLY`

If one candidate passes, it becomes:

- `INTEGRATION_CANDIDATE`
