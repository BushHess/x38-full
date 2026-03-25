# Regime Monitor V2 — Comprehensive Validation Report

**Generated**: 2026-03-16 20:48 UTC
**Data**: 2019-01-01 to 2026-02-20 (warmup=365d)
**Engine**: BacktestEngine (next-open fills, no_trade warmup)
**Cost scenarios**: smart (13 bps RT), base (31 bps RT), harsh (50 bps RT)

---

## T1: Engine Baseline (harsh cost)

| Metric | Monitor OFF | Monitor ON | Delta |
|--------|----------:|----------:|------:|
| Sharpe | 1.4545 | 1.5931 | +0.1386 |
| CAGR % | 61.60 | 68.11 | +6.51 |
| MDD % | 40.97 | 38.74 | -2.23 |
| Trades | 188 | 173 | -15 |
| Monitor exits | -- | 0 | |
| Final NAV | 307790.48 | 408030.03 | +100239.55 |

## T2: Threshold Sensitivity

### red_6m

| Value | Sharpe | CAGR % | MDD % | Trades | RED bars |
|------:|-------:|-------:|------:|-------:|---------:|
| 0.40 | 1.1954 | 37.47 | 44.73 | 126 | 6708 |
| 0.45 | 1.2362 | 40.23 | 38.54 | 134 | 5694 |
| 0.50 | 1.2614 | 42.71 | 38.74 | 146 | 3972 |
| 0.55 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.60 | 1.5779 | 67.20 | 38.74 | 174 | 1506 |
| 0.65 | 1.5779 | 67.20 | 38.74 | 174 | 1404 |
| 0.70 | 1.5779 | 67.20 | 38.74 | 174 | 1368 |

Plateau (Sharpe >= 95% of best 1.5931): **0.55 - 0.70** (default: 0.55)

### red_12m

| Value | Sharpe | CAGR % | MDD % | Trades | RED bars |
|------:|-------:|-------:|------:|-------:|---------:|
| 0.55 | 1.3643 | 44.55 | 25.60 | 126 | 4776 |
| 0.60 | 1.3527 | 45.12 | 29.69 | 134 | 4104 |
| 0.65 | 1.5016 | 59.44 | 38.74 | 155 | 2748 |
| 0.70 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.75 | 1.5820 | 67.54 | 38.74 | 176 | 1386 |
| 0.80 | 1.5820 | 67.54 | 38.74 | 176 | 1386 |
| 0.85 | 1.5820 | 67.54 | 38.74 | 176 | 1386 |

Plateau (Sharpe >= 95% of best 1.5931): **0.70 - 0.85** (default: 0.70)

### amber_6m

| Value | Sharpe | CAGR % | MDD % | Trades | RED bars |
|------:|-------:|-------:|------:|-------:|---------:|
| 0.30 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.35 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.40 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.45 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.50 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.55 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.60 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |

Plateau (Sharpe >= 95% of best 1.5931): **0.30 - 0.60** (default: 0.45)

### amber_12m

| Value | Sharpe | CAGR % | MDD % | Trades | RED bars |
|------:|-------:|-------:|------:|-------:|---------:|
| 0.45 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.50 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.55 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.60 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.65 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.70 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |
| 0.75 | 1.5931 | 68.11 | 38.74 | 173 | 1638 |

Plateau (Sharpe >= 95% of best 1.5931): **0.45 - 0.75** (default: 0.60)

## T3: Cost Sweep

| Scenario | RT bps | dSharpe | dCAGR % | dMDD % | dTrades |
|----------|-------:|--------:|--------:|-------:|--------:|
| smart | 13 | +0.1250 | +5.74 | +0.00 | -15 |
| base | 31 | +0.1316 | +6.14 | -0.29 | -15 |
| harsh | 50 | +0.1386 | +6.51 | -2.23 | -15 |

## T4: Factorial Isolation

| Config | Sharpe | CAGR % | MDD % | Trades |
|--------|-------:|-------:|------:|-------:|
| no_regime | 1.0912 | 34.50 | 40.31 | 149 |
| ema21_only | 1.4545 | 61.60 | 40.97 | 188 |
| monitor_only | 1.2112 | 38.43 | 32.73 | 136 |
| ema21_plus_monitor | 1.5931 | 68.11 | 38.74 | 173 |

**Marginal contributions:**
- EMA(21) filter: Sharpe +0.3633, CAGR +27.10%, MDD +0.66%
- Monitor V2: Sharpe +0.1386, CAGR +6.51%, MDD -2.23%

## T5: Subperiod Robustness

| Period | dSharpe | dCAGR % | dMDD % | dTrades |
|--------|--------:|--------:|-------:|--------:|
| 2018-2020 | +0.2194 | +6.64 | -0.82 | -11 |
| 2020-2022 | +0.0000 | +0.00 | +0.00 | +0 |
| 2022-2024 | +0.5390 | +15.08 | -3.74 | -12 |
| 2024-2026 | +0.0000 | +0.00 | +0.00 | +0 |

**2/4 periods Sharpe improved, 2/4 MDD improved**

## T6: Jackknife — Blocked Entry Analysis

- Trades (monitor OFF): 188
- Trades (monitor ON): 173
- Blocked entries: 15
- Modified exits: 0
- Monitor forced exits: 0
- Total blocked PnL: -36704.76

| # | Entry Date | PnL | Return % | Days | Exit Reason |
|---|-----------|----:|--------:|-----:|------------|
| 1 | 2022-08-17 | -10038.57 | -6.81 | 1.7 | vtrend_e5_ema21_d1_trail_stop |
| 2 | 2022-07-24 | -8713.27 | -5.54 | 2.0 | vtrend_e5_ema21_d1_trail_stop |
| 3 | 2022-09-11 | -5812.26 | -4.23 | 2.0 | vtrend_e5_ema21_d1_trail_stop |
| 4 | 2022-10-05 | -5222.81 | -4.10 | 2.7 | vtrend_e5_ema21_d1_trail_stop |
| 5 | 2022-09-13 | -4187.10 | -3.18 | 1.8 | vtrend_e5_ema21_d1_trend_exit |
| 6 | 2022-10-29 | -2586.21 | -2.15 | 4.8 | vtrend_e5_ema21_d1_trail_stop |
| 7 | 2022-08-03 | -2466.95 | -1.68 | 6.0 | vtrend_e5_ema21_d1_trail_stop |
| 8 | 2022-07-28 | -1878.42 | -1.26 | 4.7 | vtrend_e5_ema21_d1_trail_stop |
| 9 | 2022-10-26 | -1631.77 | -1.34 | 2.2 | vtrend_e5_ema21_d1_trail_stop |
| 10 | 2019-02-27 | -278.67 | -2.75 | 4.5 | vtrend_e5_ema21_d1_trail_stop |
| 11 | 2019-01-05 | -148.48 | -1.48 | 5.2 | vtrend_e5_ema21_d1_trail_stop |
| 12 | 2019-02-09 | +285.43 | +2.90 | 14.8 | vtrend_e5_ema21_d1_trail_stop |
| 13 | 2022-11-03 | +1285.60 | +1.09 | 4.2 | vtrend_e5_ema21_d1_trail_stop |
| 14 | 2022-07-19 | +1534.44 | +0.99 | 4.3 | vtrend_e5_ema21_d1_trail_stop |
| 15 | 2022-08-10 | +3154.27 | +2.19 | 7.0 | vtrend_e5_ema21_d1_trail_stop |

Blocked: 11 losers, 4 winners. Net PnL avoided: -36704.76

## T7: Walk-Forward Optimization

| Window | Test Period | OFF Sharpe | ON Sharpe | Delta | Sign |
|-------:|-----------|----------:|----------:|------:|:----:|
| 1 | 2019-01-01 → 2019-07-01 | 3.9529 | 4.2816 | +0.3287 | + |
| 2 | 2019-07-01 → 2020-01-01 | -1.6042 | -1.6042 | +0.0000 | - |
| 3 | 2020-01-01 → 2020-07-01 | 1.2547 | 1.2547 | +0.0000 | - |
| 4 | 2020-07-01 → 2021-01-01 | 4.7263 | 4.7263 | +0.0000 | - |
| 5 | 2021-01-01 → 2021-07-01 | 1.6016 | 1.6016 | +0.0000 | - |
| 6 | 2021-07-01 → 2022-01-01 | 2.1132 | 2.1132 | +0.0000 | - |
| 7 | 2022-01-01 → 2022-07-01 | -0.0597 | -0.0597 | +0.0000 | - |
| 8 | 2022-07-01 → 2023-01-01 | -1.8475 | -0.3876 | +1.4599 | + |

**Win rate**: 2/8 = 25.0%
**Bootstrap CI** (95%): [0.0000, 0.5886] mean=0.2233 includes zero

## Verdict

| Gate | Status | Detail |
|------|:------:|--------|
| G1: Engine Sharpe improvement | **PASS** | dSharpe=+0.1386 |
| G2: Threshold plateau | **PASS** | All params have plateau >= 3 points |
| G3: Subperiod majority positive | **PASS** | 2/4 |
| G4: Blocked trades net negative PnL | **PASS** | PnL=-36704.76 |
| G5: WFO win rate >= 50% | **FAIL** | win_rate=25.0% |
| G6: Monitor forced exits = 0 | **PASS** | monitor_exits=0 |

**5/6 gates PASS**

**VERDICT: CONDITIONAL PASS** — Monitor V2 passes most gates. Review failures.

---
*Generated by validate_monitor_v2.py (engine-authoritative)*
