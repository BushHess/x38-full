# V10 Baseline Profile — Regime Decomposition

## Executive Summary

V10 baseline = `V8ApexStrategy(V8ApexConfig())` — long-only H4 VDO-momentum
strategy with D1 EMA50/200 regime gating, trailing + fixed stops.

Evaluation period: 2019-01-01 → 2026-02-20 (warmup=365d, ~7.14 years)

## Overall Performance

| Scenario | Score | CAGR% | MDD% | Sharpe | Sortino | PF | Trades |
|----------|-------|-------|------|--------|---------|-----|--------|
| smart | 121.37 | 48.56 | 34.07 | 1.3856 | 1.3857 | 1.8656 | 100 |
| base | 112.74 | 45.55 | 34.78 | 1.3219 | 1.3252 | 1.8309 | 100 |
| harsh | 88.94 | 37.26 | 36.28 | 1.1510 | 1.1421 | 1.6693 | 103 |

## Market Regime Distribution

| Regime | D1 Days | % of Period | Definition |
|--------|---------|-------------|------------|
| BULL | 1211 | 46.4% | close > EMA200 AND EMA50 > EMA200 |
| TOPPING | 102 | 3.9% | |close - EMA50|/EMA50 < 1% AND ADX < 25 |
| BEAR | 661 | 25.3% | close < EMA200 AND EMA50 < EMA200 |
| SHOCK | 89 | 3.4% | |daily return| > 8% |
| CHOP | 215 | 8.2% | ATR% > 3.5% AND ADX < 20 |
| NEUTRAL | 330 | 12.7% | everything else |

## Regime Breakdown — SMART (score=121.37)

| Regime | Return% | MDD% | Sharpe | Trades | WR% | PF | Avg PnL | Fees | Turnover |
|--------|---------|------|--------|--------|-----|-----|---------|------|----------|
| BULL | 1657.75 | 32.60 | 2.3666 | 60 | 53.3 | 2.04 | 1956.64 | 3827.46 | 10935606 |
| TOPPING | -17.02 | 25.03 | -2.2366 | 4 | 25.0 | 0.12 | -3121.86 | 234.28 | 669369 |
| BEAR | 0.03 | 4.97 | 0.0185 | 0 | 0.0 | 0.00 | 0.00 | 8.09 | 23127 |
| SHOCK | -13.75 | 24.96 | -0.9368 | 2 | 50.0 | 1.44 | 508.91 | 121.64 | 347549 |
| CHOP | 6.10 | 29.54 | 0.4650 | 14 | 57.1 | 1.87 | 1948.19 | 658.03 | 1880075 |
| NEUTRAL | 26.41 | 16.36 | 1.1143 | 20 | 50.0 | 2.07 | 1412.60 | 559.08 | 1597378 |

## Regime Breakdown — BASE (score=112.74)

| Regime | Return% | MDD% | Sharpe | Trades | WR% | PF | Avg PnL | Fees | Turnover |
|--------|---------|------|--------|--------|-----|-----|---------|------|----------|
| BULL | 1491.43 | 33.27 | 2.2910 | 60 | 53.3 | 1.98 | 1703.89 | 9894.14 | 9894141 |
| TOPPING | -17.49 | 26.08 | -2.3082 | 4 | 25.0 | 0.10 | -2744.56 | 604.84 | 604844 |
| BEAR | 0.00 | 5.55 | 0.0102 | 0 | 0.0 | 0.00 | 0.00 | 21.67 | 21666 |
| SHOCK | -14.10 | 27.11 | -0.9689 | 2 | 50.0 | 1.41 | 449.28 | 318.25 | 318248 |
| CHOP | 3.91 | 30.23 | 0.3612 | 14 | 57.1 | 1.86 | 1742.20 | 1704.58 | 1704582 |
| NEUTRAL | 24.41 | 16.99 | 1.0469 | 20 | 50.0 | 2.07 | 1309.23 | 1435.35 | 1435352 |

## Regime Breakdown — HARSH (score=88.94)

| Regime | Return% | MDD% | Sharpe | Trades | WR% | PF | Avg PnL | Fees | Turnover |
|--------|---------|------|--------|--------|-----|-----|---------|------|----------|
| BULL | 1109.11 | 36.01 | 2.1019 | 61 | 50.8 | 1.78 | 1099.15 | 11488.53 | 7659021 |
| TOPPING | -21.04 | 29.53 | -2.9593 | 5 | 40.0 | 0.32 | -1211.98 | 673.50 | 448997 |
| BEAR | 0.78 | 17.74 | 0.8486 | 0 | 0.0 | 0.00 | 0.00 | 4.29 | 2862 |
| SHOCK | -14.25 | 29.32 | -0.9848 | 2 | 50.0 | 1.37 | 385.16 | 392.84 | 261891 |
| CHOP | 1.64 | 31.81 | 0.2517 | 14 | 57.1 | 1.86 | 1297.34 | 1920.04 | 1280026 |
| NEUTRAL | 14.44 | 24.83 | 0.7149 | 21 | 47.6 | 1.63 | 671.65 | 1788.95 | 1192637 |

## Key Findings

**Where V10 makes money** (base scenario):

- **BULL**: +1491.4% return, 60 trades, WR=53%
- **NEUTRAL**: +24.4% return, 20 trades, WR=50%
- **CHOP**: +3.9% return, 14 trades, WR=57%

**Where V10 loses money** (base scenario):

- **SHOCK**: -14.1% return, 2 trades, WR=50%
- **TOPPING**: -17.5% return, 4 trades, WR=25%

**Cost sensitivity across regimes:**

| Regime | Smart Ret% | Base Ret% | Harsh Ret% | Harsh-Smart delta |
|--------|-----------|----------|-----------|-------------------|
| BULL | 1657.75 | 1491.43 | 1109.11 | -548.64 |
| TOPPING | -17.02 | -17.49 | -21.04 | -4.02 |
| BEAR | 0.03 | 0.00 | 0.78 | +0.75 |
| SHOCK | -13.75 | -14.10 | -14.25 | -0.50 |
| CHOP | 6.10 | 3.91 | 1.64 | -4.46 |
| NEUTRAL | 26.41 | 24.41 | 14.44 | -11.97 |
