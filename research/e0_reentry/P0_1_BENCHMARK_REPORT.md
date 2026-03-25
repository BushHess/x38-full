# P0.1 Stretch-Recovery Benchmark Report

## Verdict

- `KILL_RECOVERY_MECHANICS`

## Full Period (harsh) vs Stretch Baseline

- `X0_E5EXIT`: Sharpe=1.4545, CAGR=61.60%, MDD=40.97%, Calmar=1.5037, Trades=188
- `X0E5_CHOP_STRETCH18`: Sharpe=1.5448, CAGR=64.96%, MDD=39.13%, Calmar=1.6601, Trades=168
- `X0E5_OVR_BROAD`: Sharpe=1.4421, CAGR=59.48%, MDD=40.33%, Calmar=1.4748, Trades=176
- `X0E5_OVR_NARROW`: Sharpe=1.4975, CAGR=62.61%, MDD=40.47%, Calmar=1.5469, Trades=173
- `X0E5_RE6_IMPULSE`: Sharpe=1.5000, CAGR=62.53%, MDD=39.13%, Calmar=1.5978, Trades=171
- `X0E5_OVR_NARROW_RE6`: Sharpe=1.4677, CAGR=60.87%, MDD=40.47%, Calmar=1.5040, Trades=174

## Candidate Deltas vs Stretch Baseline (harsh)

- `X0E5_OVR_BROAD`: full dSharpe=-0.1027, dCAGR=-5.48pp, dMDD=+1.20pp, dCalmar=-0.1853; holdout dSharpe=-0.0972, dCAGR=-3.07pp, dMDD=+3.69pp, dCalmar=-0.2194
- `X0E5_OVR_NARROW`: full dSharpe=-0.0473, dCAGR=-2.35pp, dMDD=+1.34pp, dCalmar=-0.1132; holdout dSharpe=+0.0217, dCAGR=+1.01pp, dMDD=+0.00pp, dCalmar=+0.0374
- `X0E5_RE6_IMPULSE`: full dSharpe=-0.0448, dCAGR=-2.43pp, dMDD=+0.00pp, dCalmar=-0.0623; holdout dSharpe=+0.1094, dCAGR=+4.05pp, dMDD=+0.00pp, dCalmar=+0.1500
- `X0E5_OVR_NARROW_RE6`: full dSharpe=-0.0771, dCAGR=-4.09pp, dMDD=+1.34pp, dCalmar=-0.1561; holdout dSharpe=+0.0217, dCAGR=+1.01pp, dMDD=+0.00pp, dCalmar=+0.0374

## Interpretation

- None of the recovery mechanisms improved the stretch baseline cleanly on both full-period and recent holdout.
- Current evidence favors keeping the stretch gate simple, or abandoning this family refinement entirely.
