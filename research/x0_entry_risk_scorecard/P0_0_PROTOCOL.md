# P0.0 Protocol -- X0 Entry Risk Scorecard

## Question

Can the project identify, before entry, whether an `X0` / `X0_E5EXIT` order is
part of a weak cohort that is more likely to become a bad trade?

## Scope

- Source data: `research/e0_entry_hygiene/p0_1_trade_table.csv`
- Strategies under study:
  - `X0`
  - `X0_E5EXIT`
- Train period: `2019-01-01` to `2023-12-31`
- Holdout period: `2024-01-01` to `2026-02-20`

## Labels

Primary label:

- `core_bad = failure_mode in {false_breakout, trail_stop_noise}`

Rationale:

- These are the two dominant loss modes that are still plausibly attributable to
  entry quality rather than pure exit give-back.
- `late_exit_giveback` is excluded from the primary label because it is mostly
  an exit-quality problem, not an entry-quality problem.

Secondary label:

- `any_bad = not is_winner`

## Candidate Inputs

Only pre-entry fields are allowed:

- `entry_context`
- `entry_price_to_slow_atr`
- `entry_er30`
- `entry_vdo`
- `entry_ema_spread_atr`

## Candidate Rules

Evaluate only tiny, interpretable rules:

- `chop`
- `chop + stretch`
- `chop + stretch + weak ER`
- `chop + stretch + weak VDO`
- `chop + stretch + wide spread`

No ML, no fitted score, no parameter sweep beyond a tiny locked threshold set.

## Selection Standard

A rule is considered stable only if, on both `X0` and `X0_E5EXIT`:

1. flagged `core_bad` rate is higher than kept `core_bad` rate in both train and holdout
2. flagged average PnL is lower than kept average PnL in both train and holdout
3. flagged support is not tiny

If a lower-DOF rule and a higher-DOF rule are both stable, prefer the lower-DOF
rule unless the higher-DOF rule delivers clearly better holdout separation.

## Deliverables

- atomic rule table
- chosen scorecard spec
- train/holdout risk-bin table
- holdout bootstrap table
- yearly risk-bin table
- trade-level risk flags
- final memo with production interpretation
