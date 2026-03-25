# P0.1 E0 Initial Forensics Report

## Scope

- Strategy: `vtrend` default
- Scenario: `harsh`
- Period: `2019-01-01` to `2026-02-20`

## Executive Summary

- Trades: `192`
- Winners / losers: `73` / `119`
- Win rate: `38.0%`
- Sharpe: `1.2653`
- CAGR: `52.04%`
- Max drawdown: `41.61%`
- Primary losing mode: `false_breakout` with `40.8%` of total loss
- Worst entry context: `chop + D1 on` with `62.5%` of total loss
- Largest drawdown episode: `41.61%` starting `2019-06-26T19:59:59Z`

## Next Mechanism Hypotheses

- Next branch should target entry hygiene, especially against early adverse excursion.
- Chop-sensitive entry gating deserves explicit testing.

## Failure Mode Table

- `late_exit_giveback`: trades=36, loss_share=14.2%, median_MFE_R=2.803179088025866
- `false_breakout`: trades=32, loss_share=40.8%, median_MFE_R=0.21187633688621715
- `slow_trend_reversal`: trades=3, loss_share=0.8%, median_MFE_R=0.23235956135976482
- `trail_stop_noise`: trades=34, loss_share=38.8%, median_MFE_R=1.3423135459388484
- `other_loss`: trades=14, loss_share=5.4%, median_MFE_R=0.5037716732928671

## Regime Table

- `chop + D1 on`: trades=112, win_rate=39.3%, loss_share=62.5%
- `transition + D1 on`: trades=28, win_rate=39.3%, loss_share=12.5%
- `chop + D1 off`: trades=24, win_rate=20.8%, loss_share=10.6%
- `transition + D1 off`: trades=13, win_rate=23.1%, loss_share=7.3%

## Drawdown Episodes

- Episode `10`: dd=41.61%, overlap_trades=44, top_failure_mode=trail_stop_noise
- Episode `22`: dd=40.61%, overlap_trades=61, top_failure_mode=late_exit_giveback
- Episode `23`: dd=33.01%, overlap_trades=26, top_failure_mode=false_breakout
- Episode `15`: dd=28.73%, overlap_trades=5, top_failure_mode=late_exit_giveback
- Episode `17`: dd=26.65%, overlap_trades=11, top_failure_mode=trail_stop_noise
