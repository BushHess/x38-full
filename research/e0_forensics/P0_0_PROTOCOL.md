# E0 Forensics Protocol

This branch performs the first mechanism-first diagnostic for the current
`VTrend E0` implementation.

Goal:

`Identify the concrete trade-level failure modes that create most of E0's pain under the current engine and default config.`

The branch is intentionally narrow:

- Strategy: `vtrend`
- Config: default from `configs/vtrend/vtrend_default.yaml`
- Engine: current `BacktestEngine`
- Scenario: `harsh`
- Reporting window: `2019-01-01` to `2026-02-20`
- Warmup: `365` days

## Questions

1. Where do losing trades come from?
2. Are losses dominated by false breakouts, late exits, or weak trend decay?
3. Are losses concentrated in specific market contexts?
4. Which drawdown episodes matter most, and what trade mix created them?
5. What is the next low-DOF mechanism branch we should test?

## Trade taxonomy

Only losing trades are classified into failure modes:

- `late_exit_giveback`
  Large MFE was available, but realized outcome captured too little and exit came late after the peak.

- `false_breakout`
  Early adverse excursion dominated before any meaningful favorable excursion developed.

- `slow_trend_reversal`
  Trade lingered, produced weak follow-through, and exited on trend reversal rather than a clean stop.

- `trail_stop_noise`
  Trade built only modest excursion, then got stopped out by the trailing logic with a loss.

- `other_loss`
  Residual bucket for losses not cleanly explained by the above rules.

## Output contract

- `p0_1_trade_table.csv`
- `p0_1_failure_summary.csv`
- `p0_1_regime_summary.csv`
- `p0_1_episode_table.csv`
- `p0_1_episode_trade_map.csv`
- `p0_1_top_losses.csv`
- `p0_1_results.json`
- `P0_1_INITIAL_REPORT.md`

## Decision use

This branch does not optimize anything. It only answers:

`What mechanism should be researched next, if any?`

Expected outcomes:

- If `late_exit_giveback` dominates:
  next branch should target exit geometry / peak give-back control.

- If `false_breakout` in chop dominates:
  next branch should target entry hygiene / regime gating.

- If no single failure mode dominates:
  next branch should stay conservative and avoid adding multiple mechanisms at once.
