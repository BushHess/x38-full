# X0E5_LL30 Validation Report

## Candidate

- Reference: `X0_E5EXIT`
- Candidate: `X0E5_LL30`

## Verdict

- `HOLD_RESEARCH_ONLY`

## Full Period (harsh)

- reference: Sharpe=1.4545, CAGR=61.60%, MDD=40.97%, Calmar=1.5037
- candidate: Sharpe=1.4531, CAGR=61.13%, MDD=36.15%, Calmar=1.6908

## Recent Holdout (2024-01-01 to 2026-02-20, harsh)

- pre-holdout delta: dSharpe=+0.0168, dCAGR=+0.75pp, dMDD=-4.82pp
- holdout delta: dSharpe=-0.0631, dCAGR=-2.50pp, dMDD=+0.06pp

## Rolling OOS Windows (harsh)

- windows=21
- Sharpe wins=7/21
- CAGR wins=7/21
- MDD wins=7/21
- Calmar wins=7/21

## Paired Bootstrap (full harsh actual engine equity)

- Sharpe: delta=-0.0014, CI=[-0.0991, +0.0969], P(candidate better)=0.476
- CAGR: delta=-0.4734, CI=[-6.7353, +5.5105], P(candidate better)=0.435
- -MDD: delta=+4.8133, CI=[-4.7128, +4.8637], P(candidate better)=0.522

## Pair Diagnostic

- class=near_identical
- boot_sharpe_p=0.477
- boot_geo_p=0.433
- sub_p=0.018
- consensus_gap_pp=41.50
- route=no_action_default

## Interpretation

- Validation is mixed. This candidate should remain research-only.
