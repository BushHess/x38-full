# V10 Final Holdout — Baseline Profile

**Timestamp:** 2026-02-23 23:58:52 UTC

## 1. Holdout Definition

| Parameter | Value |
|-----------|-------|
| **Holdout start** | **2024-10-01** |
| **Holdout end** | **2026-02-20** |
| Holdout duration | ~17 months (507 days, 19.4% of full period) |
| Full evaluation | 2019-01-01 → 2026-02-20 (2607 days) |
| Warmup | 365 days |
| Strategy | V10 = `V8ApexStrategy(V8ApexConfig())` |
| Scenarios | harsh (50 bps), base (31 bps), smart (13 bps) |

Identical holdout window as V11 validation (`out_v11_validation_stepwise/scripts/final_holdout.py:41-42`).

## 2. Holdout Metrics

| Scenario | Score | CAGR% | Return% | MDD% | Sharpe | Sortino | PF | Trades | Fees |
|----------|-------|-------|---------|------|--------|---------|-----|--------|------|
| harsh | 34.66 | 17.29 | +24.82 | 31.56 | 0.6961 | 0.7270 | 1.4397 | 26 | 902 |
| base | 55.06 | 24.35 | +35.40 | 30.86 | 0.8954 | 0.9370 | 1.6068 | 25 | 595 |
| smart | 64.64 | 27.65 | +40.42 | 30.19 | 0.9856 | 1.0284 | 1.6484 | 25 | 213 |

## 3. Holdout vs Full-Period

| Scenario | Full Score | Holdout Score | Full CAGR% | Holdout CAGR% | Full Trades | Holdout Trades |
|----------|-----------|---------------|-----------|---------------|-------------|----------------|
| harsh | 88.94 | 34.66 | 37.26 | 17.29 | 103 | 26 |
| base | 112.74 | 55.06 | 45.55 | 24.35 | 100 | 25 |
| smart | 121.37 | 64.64 | 48.56 | 27.65 | 100 | 25 |

## 4a. Regime Breakdown — HARSH holdout

| Regime | Days | Ret% | MDD% | Sharpe | Trades | WR% | PF | Avg PnL | Fees |
|--------|------|------|------|--------|--------|-----|-----|---------|------|
| BULL | 300 | +43.89 | 27.41 | 1.5700 | 16 | 62 | 2.65 | 315.76 | 660 |
| TOPPING | 18 | -0.70 | 7.26 | -0.3081 | 2 | 50 | 0.24 | -151.69 | 24 |
| BEAR | 93 | +0.00 | 0.00 | N/A | 0 | 0 | 0.00 | 0.00 | 0 |
| SHOCK | 7 | -10.55 | 14.80 | -11.7856 | 0 | 0 | 0.00 | 0.00 | 19 |
| CHOP | 50 | +2.59 | 30.95 | 0.7161 | 4 | 50 | 0.61 | -211.18 | 116 |
| NEUTRAL | 40 | -4.82 | 14.57 | -1.3533 | 4 | 50 | 0.08 | -243.51 | 83 |

## 4b. Regime Breakdown — BASE holdout

| Regime | Days | Ret% | MDD% | Sharpe | Trades | WR% | PF | Avg PnL | Fees |
|--------|------|------|------|--------|--------|-----|-----|---------|------|
| BULL | 300 | +54.25 | 26.45 | 1.8290 | 15 | 67 | 3.16 | 390.37 | 429 |
| TOPPING | 18 | -0.62 | 6.08 | -0.2506 | 2 | 50 | 0.30 | -138.59 | 16 |
| BEAR | 93 | +0.00 | 0.00 | N/A | 0 | 0 | 0.00 | 0.00 | 0 |
| SHOCK | 7 | -10.45 | 13.20 | -11.6746 | 0 | 0 | 0.00 | 0.00 | 13 |
| CHOP | 50 | +3.17 | 30.23 | 0.8352 | 4 | 50 | 0.63 | -196.19 | 78 |
| NEUTRAL | 40 | -4.40 | 14.15 | -1.2197 | 4 | 50 | 0.11 | -239.56 | 58 |

## 4c. Regime Breakdown — SMART holdout

| Regime | Days | Ret% | MDD% | Sharpe | Trades | WR% | PF | Avg PnL | Fees |
|--------|------|------|------|--------|--------|-----|-----|---------|------|
| BULL | 300 | +58.13 | 25.53 | 1.9246 | 15 | 67 | 3.27 | 409.49 | 153 |
| TOPPING | 18 | -0.51 | 6.05 | -0.1768 | 2 | 50 | 0.30 | -164.67 | 6 |
| BEAR | 93 | +0.00 | 0.00 | N/A | 0 | 0 | 0.00 | 0.00 | 0 |
| SHOCK | 7 | -10.36 | 11.75 | -11.5677 | 0 | 0 | 0.00 | 0.00 | 5 |
| CHOP | 50 | +3.71 | 29.54 | 0.9480 | 4 | 50 | 0.66 | -183.75 | 28 |
| NEUTRAL | 40 | -4.00 | 13.75 | -1.0929 | 4 | 50 | 0.14 | -232.63 | 21 |

## 5. Cross-Reference: V11 Holdout (from V11 validation)

V11 holdout results (from `out_v11_validation_stepwise/reports/final_holdout.md`):

| Scenario | V10 Score (this run) | V10 Score (V11 report) | V11 Score | V11 Δ Score |
|----------|---------------------|----------------------|-----------|-------------|
| harsh | 34.66 | 34.66 | 33.43 | -1.23 |
| base | 55.06 | 55.06 | 53.78 | -1.28 |
| smart | 64.64 | 64.64 | 63.31 | -1.32 |

V11 underperformed V10 by -1.23 to -1.32 score points across all 3 scenarios on this holdout.

## 6. Key Findings

- **Holdout return (harsh):** +24.82% over ~17 months (+17.29% CAGR)
- **MDD (harsh):** 31.56% — consistent with full-period MDD (36.28%)
- **BULL regime** drives all gains: +43.9% return
- **TOPPING/BEAR** damage: TOPPING=-0.7%, BEAR=+0.0%
- **Trade count (harsh):** 26 in 17 months (vs 103 in 7 years)
