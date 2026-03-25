# X0E5_FLOOR_LATCH Validation Report

## Candidate

- Reference: `X0_E5EXIT`
- Candidate: `X0E5_FLOOR_LATCH`

## Verdict

- `HOLD_RESEARCH_ONLY`

## Full Period (harsh)

- reference: Sharpe=1.4545, CAGR=61.60%, MDD=40.97%, Calmar=1.5037
- candidate: Sharpe=1.4560, CAGR=61.28%, MDD=35.46%, Calmar=1.7282

## Recent Holdout (2024-01-01 to 2026-02-20, harsh)

- pre-holdout delta: dSharpe=+0.0207, dCAGR=+0.99pp, dMDD=-5.51pp
- holdout delta: dSharpe=-0.0631, dCAGR=-2.50pp, dMDD=+0.06pp

## Rolling OOS Windows (harsh)

- windows=21
- Sharpe wins=7/21
- CAGR wins=7/21
- MDD wins=7/21
- Calmar wins=7/21

## Paired Bootstrap (full harsh actual engine equity)

- Sharpe: delta=+0.0015, CI=[-0.0963, +0.1005], P(candidate better)=0.509
- CAGR: delta=-0.3197, CI=[-6.5258, +5.6841], P(candidate better)=0.464
- -MDD: delta=+5.5071, CI=[-4.6696, +4.9037], P(candidate better)=0.543

## Pair Diagnostic

- class=near_identical
- boot_sharpe_p=0.498
- boot_geo_p=0.455
- sub_p=0.020
- consensus_gap_pp=43.49
- route=no_action_default

## Interpretation

- Validation is mixed. This candidate should remain research-only.
