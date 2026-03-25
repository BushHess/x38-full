# X23 Report: State-Conditioned Exit Geometry Redesign

Generated: 2026-03-16T22:22:09.411074Z


## T0: Full-Sample Comparison

| Strategy | Sharpe | CAGR% | MDD% | Trades | Exposure% |
|----------|--------|-------|------|--------|-----------|
| e0 | 1.3718 | 57.72 | 39.96 | 189 | 49.3 |
| e5 | 1.4690 | 62.48 | 40.90 | 202 | 48.0 |
| x23_fixed | 1.2523 | 50.57 | 44.66 | 197 | 48.9 |
| x23_cal | 1.2778 | 50.03 | 39.45 | 249 | 46.0 |

d_sharpe(X23-fixed vs E5) = -0.2168
G0: **FAIL**

Calibrated multipliers: weak=1.608, normal=2.024, strong=2.389


## T1: Exit Anatomy & Churn Diagnostic

| Strategy | Total | Trail | Hard | Trend | Ch/Trail% | Ch/Total% |
|----------|-------|-------|------|-------|----------|-----------|
| E0 | 189 | 168 | 0 | 21 | 66.1 | 66.1 |
| E5 | 202 | 183 | 0 | 19 | 67.2 | 67.2 |
| X23-fixed | 197 | 124 | 55 | 18 | 77.4 | 67.0 |
| X23-cal | 249 | 160 | 72 | 17 | 84.4 | 73.7 |

## T2: Pullback Calibration Report

| State | N | Mean | Q50 | Q75 | Q90 | Cal.Mult | Preset |
|-------|---|------|-----|-----|-----|----------|--------|
| weak | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 1.608 | 2.250 |
| normal | 3185 | 0.942 | 0.724 | 1.534 | 2.264 | 2.024 | 3.000 |
| strong | 1864 | 1.077 | 0.956 | 1.730 | 2.389 | 2.389 | 4.250 |

## T3: Walk-Forward Optimization

| Fold | E5 Sharpe | X23f Sharpe | d_fixed | X23c Sharpe | d_cal |
|------|-----------|-------------|---------|------------|-------|
| 1 | -1.1070 | -1.1833 | -0.0763 | -1.1780 | -0.0710 |
| 2 | 1.2602 | 1.2986 | +0.0384 | 1.2885 | +0.0283 |
| 3 | 1.8919 | 1.5835 | -0.3083 | 1.7293 | -0.1626 |
| 4 | 0.0998 | 0.2081 | +0.1084 | -0.3986 | -0.4984 |

X23-fixed: win_rate=50%, mean_d=-0.0595
G1: **FAIL**


## T4: Bootstrap

- P(d_sharpe > 0): 45.0%
- Median d_sharpe: -0.0110
- Median d_mdd: +0.31pp
- G2: **FAIL**, G3: **PASS**


## T5: Jackknife

| Year | E5 Sharpe | X23 Sharpe | d_sharpe |
|------|-----------|------------|----------|
| 2020 | 0.7696 | 0.7267 | -0.0429 |
| 2021 | 1.1075 | 1.1885 | +0.0810 |
| 2022 | 1.5824 | 1.3442 | -0.2383 |
| 2023 | 1.5292 | 1.2568 | -0.2724 |
| 2024 | 1.3169 | 1.2532 | -0.0637 |
| 2025 | 1.6118 | 1.3717 | -0.2401 |

Negative: 5/6
G4: **FAIL**


## T6: PSR

- X23-fixed Sharpe: 1.2523
- SR0: 0.3938
- PSR: 1.0000
- G5: **PASS**


## T7: Summary

| Gate | Test | Criterion | Value | Pass? |
|------|------|-----------|-------|-------|
| G0 | T0 | d_sharpe > 0 vs E5 | -0.2168 | FAIL |
| G1 | T3 | WFO >= 3/4, mean d > 0 | wr=50%, d=-0.0595 | FAIL |
| G2 | T4 | P(d_sh > 0) > 0.55 | 0.4500 | FAIL |
| G3 | T4 | med d_mdd <= +5pp | 0.3145 | PASS |
| G4 | T5 | JK neg <= 2/6 | 5.0000 | FAIL |
| G5 | T6 | PSR > 0.95 | 1.0000 | PASS |

**VERDICT: REJECT**
