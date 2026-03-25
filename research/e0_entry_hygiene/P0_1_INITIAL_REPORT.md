# P0.1 Entry Hygiene Report

## Scope

- Baselines: `E0`, `X0`, `X0_E5EXIT`
- Candidates: `X0_CHOP_VDO2`, `X0_CHOP_STRETCH18`, `X0_CHOP_COMBO`,
  `X0E5_CHOP_VDO2`, `X0E5_CHOP_STRETCH18`, `X0E5_CHOP_COMBO`
- Period: `2019-01-01` to `2026-02-20`

## Verdict

- `PROMOTE_TO_PHASE_2`
- Elapsed: `34.00s`

## Harsh Backtest Snapshot

- `E0`: Sharpe=1.2653, CAGR=52.04%, MDD=41.61%, Calmar=1.2507, Trades=192
- `X0`: Sharpe=1.3536, CAGR=56.62%, MDD=40.01%, Calmar=1.4151, Trades=174
- `X0_E5EXIT`: Sharpe=1.4545, CAGR=61.60%, MDD=40.97%, Calmar=1.5037, Trades=188
- `X0_CHOP_VDO2`: Sharpe=1.3383, CAGR=55.16%, MDD=41.15%, Calmar=1.3405, Trades=166
- `X0_CHOP_STRETCH18`: Sharpe=1.5334, CAGR=66.39%, MDD=37.39%, Calmar=1.7757, Trades=153
- `X0_CHOP_COMBO`: Sharpe=1.3550, CAGR=56.24%, MDD=41.15%, Calmar=1.3668, Trades=170
- `X0E5_CHOP_VDO2`: Sharpe=1.4568, CAGR=60.93%, MDD=39.08%, Calmar=1.5592, Trades=180
- `X0E5_CHOP_STRETCH18`: Sharpe=1.5448, CAGR=64.96%, MDD=39.13%, Calmar=1.6601, Trades=168
- `X0E5_CHOP_COMBO`: Sharpe=1.4265, CAGR=59.20%, MDD=41.21%, Calmar=1.4367, Trades=184

## Candidate Deltas vs Family Reference

- `X0_CHOP_VDO2` vs `X0`: dSharpe=-0.0153, dCAGR=-1.46pp, dMDD=+1.14pp, dCalmar=-0.0746
  false_breakout loss delta: +35559.93 USD; trail_stop_noise loss delta: +8990.65 USD
  blocked entries in harsh: 91
- `X0_CHOP_STRETCH18` vs `X0`: dSharpe=+0.1798, dCAGR=+9.77pp, dMDD=-2.62pp, dCalmar=+0.3606
  false_breakout loss delta: +19423.71 USD; trail_stop_noise loss delta: -63263.42 USD
  blocked entries in harsh: 426
- `X0_CHOP_COMBO` vs `X0`: dSharpe=+0.0014, dCAGR=-0.38pp, dMDD=+1.14pp, dCalmar=-0.0483
  false_breakout loss delta: +14570.96 USD; trail_stop_noise loss delta: +8740.57 USD
  blocked entries in harsh: 75
- `X0E5_CHOP_VDO2` vs `X0_E5EXIT`: dSharpe=+0.0023, dCAGR=-0.67pp, dMDD=-1.89pp, dCalmar=+0.0555
  false_breakout loss delta: +18400.35 USD; trail_stop_noise loss delta: +31545.24 USD
  blocked entries in harsh: 104
- `X0E5_CHOP_STRETCH18` vs `X0_E5EXIT`: dSharpe=+0.0903, dCAGR=+3.36pp, dMDD=-1.84pp, dCalmar=+0.1564
  false_breakout loss delta: +18571.64 USD; trail_stop_noise loss delta: -22370.42 USD
  blocked entries in harsh: 481
- `X0E5_CHOP_COMBO` vs `X0_E5EXIT`: dSharpe=-0.0280, dCAGR=-2.40pp, dMDD=+0.24pp, dCalmar=-0.0670
  false_breakout loss delta: +5217.12 USD; trail_stop_noise loss delta: +4943.09 USD
  blocked entries in harsh: 90

## Interpretation

- Candidates clearing the branch gate: `X0_CHOP_STRETCH18`, `X0E5_CHOP_STRETCH18`
- Next step should test the surviving gate with matched-trade attribution against the family reference.
