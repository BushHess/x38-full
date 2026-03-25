# P0.3 Validation Protocol

## Goal

Validate the `X0` / `X0_E5EXIT` entry-risk scorecard on the live engine path and
decide the only action that is justified:

- `warning_only`
- `hard_gate_x0_only`
- `kill`

## Scope

This phase validates the scorecard as instrumentation and cohort diagnostic. It
does **not** promote a new production strategy by itself.

## Questions

1. Does `emit_entry_risk_tag=true` preserve parity vs `tag off`?
2. Are the three cohorts economically ordered on actual engine trades?
3. Does the ordering survive holdout and a practical WFO lens?
4. Does the evidence justify action on `X0_E5EXIT`, or only a warning path?

## Data / Engine

- Dataset: `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- Engine: `BacktestEngine`
- Scenario: `harsh`
- Full period: `2019-01-01 -> 2026-02-20`
- Holdout: `2024-01-01 -> 2026-02-20`
- WFO lens: last 8 windows from `24m train / 6m test / 6m slide`
- Warmup: `365 days`

## Validation Steps

### 1. Parity

Run:

- `X0(tag off)` vs `X0(tag on)`
- `X0_E5EXIT(tag off)` vs `X0_E5EXIT(tag on)`

Required:

- identical fills
- identical trades ignoring `entry_reason`
- identical summary metrics

If parity fails, the scorecard path is rejected immediately.

### 2. Cohort Stability

For each strategy and period, aggregate trades by:

- `low_non_chop`
- `medium_chop`
- `high_chop_stretch`

Track:

- `trades`
- `avg_pnl_usd`
- `total_pnl_usd`
- `win_rate`

### 3. Bootstrap

For each strategy and period, bootstrap the mean-PnL gap:

- `low_non_chop - high_chop_stretch`
- `medium_chop - high_chop_stretch`

Bootstrap is simple trade-resampling by cohort. It is used only as a practical
stability check, not as a production promotion gate.

### 4. WFO Lens

On each eligible test window, check whether:

- `avg_pnl(high) < avg_pnl(low)`
- `win_rate(high) < win_rate(low)`

A window is eligible only if both buckets have at least `3` trades.

## Decision Rules

### `warning_only`

Use when:

- parity passes
- `high_chop_stretch` remains weaker than `low_non_chop`
- but evidence is not broad/clean enough to justify a default hard gate on the
  production anchor

### `hard_gate_x0_only`

Use only if:

- parity passes
- `X0` shows stable degradation in `high_chop_stretch`
- holdout remains clearly adverse
- and prior gate research on `X0` is already positive

This does not imply promotion for `X0_E5EXIT`.

### `kill`

Use if:

- parity fails, or
- cohort ordering collapses on holdout/WFO

## Why not run the full 47-technique stack?

Not at this stage.

Reason:

- `emit_entry_risk_tag` is instrumentation, not a new trading policy
- parity is the relevant engineering standard for instrumentation
- economic stability is the relevant research standard for the scorecard itself

If a new gated strategy is promoted from this scorecard, *that gated strategy*
must then go through the full validation stack.
