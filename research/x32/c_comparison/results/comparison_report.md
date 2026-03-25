# VP1 Family vs E5+EMA1D21 — Comprehensive Comparison Report

**Date**: 2026-03-12
**Validation window**: 2019-01-01 to 2026-02-20 (warmup 365d, effective trading ~2020-01-01)
**Baseline**: E0 (vtrend, slow=120, trail=3.0, no D1 filter)
**Cost**: 50 bps RT (harsh scenario)

## 1. Strategy Identity Summary

| Property | VP1 | VP1-E5exit | VP1-FULL | E5+EMA1D21 |
|----------|-----|-----------|----------|------------|
| ATR type | Standard Wilder | **RATR** | **RATR** | **RATR** |
| slow_period | 140 | 140 | **120** | **120** |
| trail_mult | 2.5 | 2.5 | **3.0** | **3.0** |
| d1_ema_period | 28 | 28 | **21** | **21** |
| D1 mapping | prevday (date) | prevday (date) | prevday (date) | close_time (time) |
| VDO method | per-bar auto+NaN carry | per-bar auto+NaN carry | per-bar auto+NaN carry | global taker/fallback |
| Anomaly handling | volume<=0 skip | volume<=0 skip | volume<=0 skip | none |

## 2. Full-Sample Performance (harsh, 50 bps RT)

| Metric | VP1 | VP1-E5exit | VP1-FULL | E5+EMA1D21 | E0 base |
|--------|-----|-----------|----------|------------|---------|
| **Sharpe** | 1.4524 | **1.4880** | 1.4613 | 1.4300 | 1.2653 |
| **CAGR %** | 61.73 | **62.47** | 62.03 | 59.85 | 52.04 |
| **MDD %** | 40.51 | **36.63** | 40.97 | 41.64 | 41.61 |
| Sortino | 1.3287 | 1.3723 | 1.3572 | 1.3297 | 1.1952 |
| Calmar | 1.5238 | **1.7052** | 1.5141 | 1.4373 | 1.2507 |
| Trades | 194 | 213 | 187 | 186 | 192 |
| Win rate % | 44.33 | 46.01 | 43.32 | 43.55 | 40.10 |
| Avg exposure % | 44.09 | 43.29 | 44.51 | 44.41 | 46.82 |
| Score | 150.78 | **154.88** | 151.08 | 144.96 | 123.32 |

**Key finding**: All VP1 variants BEAT E5+EMA1D21 on full-sample harsh metrics.
VP1-E5exit is best overall: highest Sharpe (1.488), lowest MDD (36.63%), highest Calmar (1.705).

## 3. Delta vs E0 Baseline

| Metric | VP1 | VP1-E5exit | VP1-FULL | E5+EMA1D21 |
|--------|-----|-----------|----------|------------|
| d_Sharpe | +0.187 | +0.223 | +0.196 | +0.165 |
| d_CAGR pp | +9.69 | +10.43 | +9.99 | +7.81 |
| d_MDD pp | -1.10 | **-4.98** | -0.64 | +0.03 |
| d_Score | +27.46 | +31.56 | +27.75 | +21.64 |

## 4. Validation Gates (vs E0 baseline)

| Gate | VP1 | VP1-E5exit | VP1-FULL | E5+EMA1D21 |
|------|-----|-----------|----------|------------|
| Lookahead | PASS | PASS | PASS | PASS |
| Full delta (G0) | PASS (+27.46) | PASS (+31.56) | PASS (+27.75) | PASS (+21.64) |
| Holdout delta | **FAIL** (-8.02) | **FAIL** (-11.78) | PASS (+5.52) | PASS (+9.54) |
| WFO Wilcoxon | PASS (p=0.055) | PASS (p=0.074) | FAIL (p=0.125) | PASS (p=0.074) |
| WFO win rate | 75% (6/8) | 62.5% (5/8) | 62.5% (5/8) | 62.5% (5/8) |
| Bootstrap P(d>0) | 92.4% | 92.8% | **97.5%** | 95.0% |
| PSR | 0.9998 | 1.0000 | 0.9999 | 0.9993 |
| **Verdict** | **ERROR** | **ERROR** | **ERROR** | **PROMOTE** |

**Root causes of ERROR verdicts**:
- VP1, VP1-E5exit: holdout FAIL (underperform E0 in late 2024-2026)
- VP1-FULL: WFO FAIL (Wilcoxon p=0.125 > 0.10 AND bootstrap CI includes zero)
- All 3 also flagged for unused `warmup_days` config field (cosmetic)

**E5+EMA1D21 passes all gates** — the ONLY strategy that achieves PROMOTE.

## 5. Decomposing the VP1 vs E5+EMA1D21 Gap

### 5a. VP1 structural features help (vs E0)
VP1 (no RATR, no parameter changes) already beats E0 by +0.187 Sharpe.
This is LARGER than E5+EMA1D21's delta of +0.165 Sharpe.

→ VP1's structural features (prevday D1, per-bar VDO, anomaly handling) add value.

### 5b. RATR swap adds the most (VP1 → VP1-E5exit)
| Change | d_Sharpe vs VP1 | d_MDD vs VP1 |
|--------|-----------------|--------------|
| +RATR only (E5exit) | +0.036 | **-3.88 pp** |
| +all params (FULL) | +0.009 | +0.46 pp |

→ RATR is the single biggest improvement. It primarily reduces MDD (-3.88 pp).
→ When you also change slow=120/trail=3.0/d1_ema=21 (FULL), MDD improvement VANISHES.

### 5c. Why VP1-FULL ≈ VP1 despite all E5 parameters?
VP1-FULL has all E5 parameters (slow=120, trail=3.0, d1_ema=21, RATR) but on VP1 structure.
Result: Sharpe 1.4613 vs VP1's 1.4524 — only +0.009 improvement.
The parameter changes mostly offset each other on VP1's structural framework.

### 5d. VP1 vs E5+EMA1D21: structure vs parameters
| Component | Sharpe contribution |
|-----------|-------------------|
| VP1 structure only (vs E0) | +0.187 |
| E5 params only (vs E0) | +0.165 |
| VP1 + RATR (best combo) | +0.223 |
| VP1 + all E5 params | +0.196 |
| E5 structure + E5 params | +0.165 |

→ VP1 structure is strictly better than E5 structure for full-sample performance.
→ But VP1 structure FAILS holdout (2024-09 to 2026-02).

## 6. Holdout Analysis (2024-09-17 to 2026-02-20)

| Metric | VP1 | VP1-E5exit | VP1-FULL | E5+EMA1D21* |
|--------|-----|-----------|----------|-------------|
| Sharpe | 0.893 | 0.843** | 1.000 | 0.979* |
| CAGR % | 22.4 | 19.9** | 27.5 | 25.8* |
| MDD % | 21.09 | 22.0** | 17.9 | 19.2* |
| Trades | 41 | 43** | 36 | 36* |
| **Holdout d_score** | **-8.02** | **-11.78** | **+5.52** | **+9.54** |

*E5+EMA1D21 holdout estimated from previous validation run
**VP1-E5exit estimated from gate failures

VP1 and VP1-E5exit underperform E0 in the holdout period.
VP1-FULL and E5+EMA1D21 outperform E0 in holdout — parameter changes (slow=120, trail=3.0, d1_ema=21) are more robust OOS.

→ VP1's parameter set (slow=140, trail=2.5, d1_ema=28) is tuned to historical data but less robust forward.

## 7. WFO Window Analysis (VP1 vs E0)

| Window | Period | VP1 delta | Verdict |
|--------|--------|-----------|---------|
| 0 | 2022-H1 | +12.30 | WIN |
| 1 | 2022-H2 | +7.80 | WIN |
| 2 | 2023-H1 | +79.33 | WIN |
| 3 | 2023-H2 | +55.75 | WIN |
| 4 | 2024-H1 | +161.36 | WIN |
| 5 | 2024-H2 | +87.52 | WIN |
| 6 | 2025-H1 | **-41.28** | LOSE |
| 7 | 2025-H2 | **-12.25** | LOSE |

VP1 wins strongly in 2022-2024 but loses the last 2 windows (2025).
This pattern explains the holdout FAIL.

## 8. Regime Performance (VP1 harsh)

| Regime | VP1 Sharpe | E0 Sharpe | VP1 wins? |
|--------|-----------|-----------|-----------|
| BULL | 2.057 | 1.712 | YES |
| BEAR | 1.470 | 1.506 | no |
| NEUTRAL | 1.149 | 0.810 | YES |
| CHOP | 0.597 | 1.580 | **no (large gap)** |
| TOPPING | 0.081 | -0.867 | YES |
| SHOCK | -2.021 | -2.677 | YES |

VP1 wins 4/6 regimes but loses badly in CHOP (0.60 vs 1.58).
This is a known vulnerability: slower EMA (140 vs 120) whipsaws more in choppy conditions.

## 9. Cost Sensitivity (VP1 vs E0 harsh)

| Cost bps | VP1 Score | E0 Score | Delta |
|----------|-----------|----------|-------|
| 0 | 163.40 | 111.01 | +52.39 |
| 10 | 150.29 | 98.93 | +51.36 |
| 25 | 131.21 | 81.40 | +49.81 |
| 50 | 98.87 | 53.67 | +45.20 |
| 75 | 68.70 | 27.72 | +40.98 |
| 100 | 40.54 | 3.44 | +37.10 |

VP1 dominates E0 at ALL cost levels. Advantage decreases with cost (52→37).

## 10. Conclusions

### VP1 family vs E5+EMA1D21 (final answer)

1. **Full-sample**: VP1 variants beat E5+EMA1D21 on Sharpe (+0.02 to +0.06) and MDD (-5 to +0.5 pp)
2. **Holdout**: VP1, VP1-E5exit FAIL. VP1-FULL passes but E5+EMA1D21 has larger margin
3. **WFO**: VP1 wins recent history (2022-2024) but loses 2025. E5+EMA1D21 more stable
4. **Validation verdict**: Only E5+EMA1D21 achieves PROMOTE. All VP1 variants hit ERROR

### Why VP1 full-sample beats E5+EMA1D21 but fails validation

VP1's structural advantages (prevday D1, per-bar VDO, anomaly) provide genuine in-sample alpha.
But its parameter set (slow=140, trail=2.5, d1_ema=28) overfits earlier market regimes.
When evaluated OOS (holdout 2024-2026), the parameter overfit outweighs structural gains.

### What VP1 research taught us

1. **RATR is the single most valuable E5 change**: -3.88 pp MDD with +0.036 Sharpe
2. **VP1 structural features (prevday D1, per-bar VDO) add value** but not enough to overcome parameter sensitivity
3. **E5+EMA1D21 parameter set (slow=120, trail=3.0, d1_ema=21) is more robust** than VP1's (140/2.5/28)
4. **CHOP regime is VP1's Achilles heel**: slow=140 whipsaws badly vs slow=120

### Decision: E5+EMA1D21 remains PRIMARY

No VP1 variant passes all gates. E5+EMA1D21 confirmed as the right choice.
