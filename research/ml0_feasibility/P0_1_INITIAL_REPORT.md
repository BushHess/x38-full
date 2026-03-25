# P0.1 Initial Report

## Scope

- Reporting window: `2019-01-01` to `2026-02-20`
- Horizon `H`: `24` bars
- Sample mode for model benchmark: `thin3`

## Sample Summary

- Raw near-peak origins: `3439`
- Thin3 origins: `1327`
- Near-peak clusters: `441`
- Soft non-censored / positive: `3081` / `1164`
- Hard non-censored / positive: `2547` / `463`

## Best Compact Baselines

- Soft target: `CORE4` with median OOS logloss gain `2.36%` and AUC `0.6598`
- Hard target: `DD_ONLY` with median OOS logloss gain `2.20%` and AUC `0.5634`

## Verdict

- Decision: `KILL_STACK`

## Kill Matrix

- `SOFT_LL_GAIN`: value=2.364828 threshold=3.0 pass=False
- `SOFT_AUC`: value=0.65976 threshold=0.57 pass=True
- `SOFT_POS_CLUSTERS`: value=123.0 threshold=60.0 pass=True
- `SOFT_ESS_PC1`: value=54.151884 threshold=200.0 pass=False
- `HARD_LL_GAIN`: value=2.204338 threshold=3.0 pass=False
- `HARD_AUC`: value=0.563443 threshold=0.56 pass=True
- `HARD_POS_CLUSTERS`: value=49.5 threshold=45.0 pass=True
- `HARD_ESS_PC1`: value=44.309478 threshold=180.0 pass=False

## Top Univariate Features

- soft: dd_now_atr (AUC 0.6068), ret_3 (AUC 0.5623), d1_regime (AUC 0.5596)
- hard: dd_now_atr (AUC 0.5932), vdo (AUC 0.5875), ret_3 (AUC 0.5811)
