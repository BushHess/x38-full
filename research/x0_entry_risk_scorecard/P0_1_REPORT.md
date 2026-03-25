# P0.1 Entry Risk Scorecard Report

## Scope

- Strategies: `X0`, `X0_E5EXIT`
- Target label: `core_bad = false_breakout or trail_stop_noise`
- Train: `2019-01-01` to `2023-12-31`
- Holdout: `2024-01-01` to `2026-02-20`

## Verdict

- `PROMOTE_SCORECARD_AS_DIAGNOSTIC`
- Elapsed: `0.26s`

## Stable Shared Rules

- `stretch18`: dof=2, holdout core-bad gap avg=`0.1541`, min holdout support=`17`

## Chosen Scorecard

- `low_non_chop`: `entry_context != chop`
- `medium_chop`: `entry_context == chop and entry_price_to_slow_atr <= 1.8`
- `high_chop_stretch`: `entry_context == chop and entry_price_to_slow_atr > 1.8`

Rationale:

- `chop` is a stable first-pass risk separator.
- `stretch > 1.8 ATR-from-slow` is the only higher-risk refinement that stayed stable across both families.
- Extra ER / VDO / spread conditions did not survive cleanly enough to justify more complexity.

## Holdout Snapshot

- `X0`
  low_non_chop: trades=12, core_bad_rate=0.083, any_bad_rate=0.333, avg_pnl=4793.32 USD
  medium_chop: trades=23, core_bad_rate=0.217, any_bad_rate=0.565, avg_pnl=2737.29 USD
  high_chop_stretch: trades=17, core_bad_rate=0.353, any_bad_rate=0.706, avg_pnl=-1200.17 USD
- `X0_E5EXIT`
  low_non_chop: trades=13, core_bad_rate=0.077, any_bad_rate=0.308, avg_pnl=6703.96 USD
  medium_chop: trades=24, core_bad_rate=0.250, any_bad_rate=0.583, avg_pnl=2331.88 USD
  high_chop_stretch: trades=19, core_bad_rate=0.316, any_bad_rate=0.579, avg_pnl=-446.32 USD

## Holdout Bootstrap

- `X0`: high-vs-rest core_bad gap median=`0.180` (p05=`-0.024`, p95=`0.388`), avg_pnl gap median=`-4436.68` USD
- `X0_E5EXIT`: high-vs-rest core_bad gap median=`0.127` (p05=`-0.064`, p95=`0.339`), avg_pnl gap median=`-4299.76` USD

## Interpretation

- The project can identify `bad-trade-prone` cohorts in a coarse but usable way before entry.
- It cannot identify winners precisely enough for a rich score or ML overlay.
- The right operational use is:
  - `X0`: optional hard gate or manual veto on `high_chop_stretch`
  - `X0_E5EXIT`: warning / review flag, not a default hard block

## Recommendation

- Keep the scorecard as a deterministic diagnostic layer.
- Do not expand it into an ML classifier on the current dataset.
- If implemented live, start with `warning-only` on `X0_E5EXIT` and only then test a hard gate.

