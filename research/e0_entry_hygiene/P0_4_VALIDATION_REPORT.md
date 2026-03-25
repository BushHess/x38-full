# P0.4 Stretch Validation Report

## Candidate

- Reference: `X0_E5EXIT`
- Candidate: `X0E5_CHOP_STRETCH18`

## Verdict

- `HOLD_RESEARCH_ONLY`

## Full Period (harsh)

- reference: Sharpe=1.4545, CAGR=61.60%, MDD=40.97%, Calmar=1.5037
- candidate: Sharpe=1.5448, CAGR=64.96%, MDD=39.13%, Calmar=1.6601

## Recent Holdout (2024-01-01 to 2026-02-20, harsh)

- pre-holdout delta: dSharpe=+0.1208, dCAGR=+6.02pp, dMDD=-1.84pp
- holdout delta: dSharpe=-0.0125, dCAGR=-1.34pp, dMDD=+1.43pp

## Rolling OOS Windows (harsh)

- windows=21
- Sharpe wins=15/21
- CAGR wins=15/21
- MDD wins=10/21
- Calmar wins=15/21

## Paired Bootstrap (full harsh actual engine equity)

- Sharpe: delta=+0.0903, CI=[-0.0848, +0.2739], P(candidate better)=0.832
- CAGR: delta=+3.3607, CI=[-7.2236, +14.4648], P(candidate better)=0.712
- -MDD: delta=+1.8332, CI=[-4.9349, +11.1082], P(candidate better)=0.742

## Pair Diagnostic

- class=borderline
- boot_sharpe_p=0.821
- boot_geo_p=0.701
- sub_p=0.951
- consensus_gap_pp=25.09
- route=escalate_full_manual_review

## Interpretation

- Validation is mixed. The candidate is interesting, but not yet strong enough for unconditional promotion.
- Because this is post-selection validation, even a good result should be treated as `integration-candidate`, not as final champion proof.
