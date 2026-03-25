# Executive summary — exit research from scratch

## Locked scope
- Entry fixed: research-version `weakvdo_q0.5_activity_and_fresh_imb`
- No ML in exit
- Exit only
- Baseline A: Sharpe 1.374, MDD -0.273, trades 104
- Baseline B: Sharpe 1.131, MDD -0.371, trades 118

## What mattered
- Trail is essential.
- Trend exit is not.
- Cooldown after exit matters a lot.
- Explicit time stop is the dominant new edge.
- Volume exits/guards are weaker than price-only lifecycle control.

## Winner
`trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`

### OOS result
- Sharpe: **1.804352**
- CAGR: **0.568013**
- MDD: **-0.260183**
- Trades: **124**
- Positive folds vs Baseline A: **4/4**

## Validation
- Bootstrap vs A: **~94.5%–96.2%** positive delta Sharpe across block lengths
- Cost sweep: wins A on Sharpe at **9/9** cost points; fold pass **>=3/4 at 9/9**
- Exposure trap: generic lower-exposure random horizon controls do **not** reproduce winner
- Sensitivity: robust across trail multiplier and cooldown band; horizon has a real ridge around **29–32 bars**, with **30** best
- Regime diagnostic: clearly **post-2021 favorable** under fixed-threshold entry proxy

## Read
This is not an argument for “better volume exit”.  
It is an argument for:

1. keep a real trail,
2. remove redundant trend exit,
3. stop overstaying around the 30-bar horizon,
4. add cooldown to kill the large quick re-entry cluster.

## Runner-up
Simpler fallback:
`trail3.0_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop36`

- Sharpe: **1.758763**
- Also 4/4 vs Baseline A
- Winner’s edge over it exists, but is not overwhelming under bootstrap
