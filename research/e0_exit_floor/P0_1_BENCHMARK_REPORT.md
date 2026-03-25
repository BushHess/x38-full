# P0.1 Exit-Floor Benchmark Report

## Verdict

- `KILL_EXIT_FLOOR`

## Full Period (harsh) vs Reference

- `X0_E5EXIT`: Sharpe=1.4545, CAGR=61.60%, MDD=40.97%, Calmar=1.5037, Trades=188
- `X0E5_LL30`: Sharpe=1.4531, CAGR=61.13%, MDD=36.15%, Calmar=1.6908, Trades=195
- `X0E5_FLOOR_SM`: Sharpe=1.4531, CAGR=61.13%, MDD=36.15%, Calmar=1.6908, Trades=195
- `X0E5_FLOOR_LATCH`: Sharpe=1.4560, CAGR=61.28%, MDD=35.46%, Calmar=1.7282, Trades=195

## Candidate Deltas vs Reference (harsh)

- `X0E5_LL30`: full dSharpe=-0.0014, dCAGR=-0.47pp, dMDD=-4.82pp, dCalmar=+0.1871; holdout dSharpe=-0.0631, dCAGR=-2.50pp, dMDD=+0.06pp, dCalmar=-0.1000
- `X0E5_FLOOR_SM`: full dSharpe=-0.0014, dCAGR=-0.47pp, dMDD=-4.82pp, dCalmar=+0.1871; holdout dSharpe=-0.0631, dCAGR=-2.50pp, dMDD=+0.06pp, dCalmar=-0.1000
- `X0E5_FLOOR_LATCH`: full dSharpe=+0.0015, dCAGR=-0.32pp, dMDD=-5.51pp, dCalmar=+0.2245; holdout dSharpe=-0.0631, dCAGR=-2.50pp, dMDD=+0.06pp, dCalmar=-0.1000

## Interpretation

- None of the support-floor variants cleared the benchmark gate cleanly.
- Current evidence does not justify continuing this exit family.
