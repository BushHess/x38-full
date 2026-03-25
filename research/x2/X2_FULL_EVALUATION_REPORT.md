# X2 Full Evaluation Report — All Tiers

**Date**: 2026-03-08
**Strategy**: VTREND-X2 (adaptive trail + D1 EMA21 regime)
**Baseline**: X0 (E0+EMA21 D1, fixed trail=3.0)
**Verdict**: **REJECT** (WFO 4/8, holdout delta -22.19)

---

## TIER 1: Validation Framework (17 suites)

Run via `validate_strategy.py --suite all --bootstrap 2000 --sensitivity-grid`
Output: `results/eval_x2_vs_x0_full/`

| # | Suite | Status | Evidence |
|---|-------|--------|----------|
| 1 | Lookahead check | PASS | lookahead_check.txt |
| 2 | Data integrity | PASS | data_integrity.json |
| 3 | Backtest (3 scenarios) | PASS | Sharpe 1.4227 harsh (+0.098 vs X0) |
| 4 | Cost sweep (0-100 bps) | PASS | Wins X0 at ALL 6 cost levels |
| 5 | Invariants | PASS | invariant_violations.csv |
| 6 | Churn metrics | PASS | 138 trades, 8.9d avg hold |
| 7 | Regime decomposition | INFO | regime_decomposition.csv |
| 8 | **WFO** | **FAIL** | **4/8 (50%) — worst delta -105.78** |
| 9 | Bootstrap | INFO | P(X2>X0) = 87.5% harsh, CI includes zero |
| 10 | Subsampling | INFO | support_ratio 0.33 < 0.6 threshold |
| 11 | Sensitivity | INFO | trail_tight 2.7→1.34, 3.0→1.42, 3.3→1.37 |
| 12 | **Holdout** | **FAIL** | **delta -22.19 (X2: 0.82 vs X0: 1.05 Sharpe)** |
| 13 | Selection bias / DSR | PASS | DSR robust |
| 14 | Trade level | INFO | 133 matched, boot p_positive=0.944 |
| 15 | DD episodes | INFO | 36 episodes (X0: 28), worst 40.28% |
| 16 | Overlay | SKIP | overlay_test: true |
| 17 | Regression guard | SKIP | No golden snapshot |

### WFO Detail (8 windows, rolling 24m train / 6m test)

| Window | Period | X2 Sharpe | X0 Sharpe | Delta |
|--------|--------|:---------:|:---------:|:-----:|
| W0 | 2022-01 → 2022-07 | -0.4498 | -0.2364 | **-10.00** |
| W1 | 2022-07 → 2023-01 | -1.4348 | -1.4348 | 0.00 |
| W2 | 2023-01 → 2023-07 | 0.9324 | 0.8235 | +12.76 |
| W3 | 2023-07 → 2024-01 | 2.7406 | 2.1059 | +99.40 |
| W4 | 2024-01 → 2024-07 | 1.3668 | 0.9051 | +73.51 |
| W5 | 2024-07 → 2025-01 | 1.8450 | 2.5046 | **-105.78** |
| W6 | 2025-01 → 2025-07 | 0.6576 | 0.5072 | +13.38 |
| W7 | 2025-07 → 2026-01 | -0.3963 | -0.3254 | **-3.06** |

Window 5 (2024H2): X0 outperforms massively — fixed 3x trail allows more frequent entries during strong rally, catching multiple waves. X2's wider trail (4-5x) holds fewer, longer positions.

### Holdout Detail (last 20% of data)

| Metric | X2 | X0 | Delta |
|--------|:--:|:--:|:-----:|
| Sharpe | 0.8184 | 1.0499 | -0.2315 |
| CAGR% | 20.11 | 26.94 | -6.83 |
| MDD% | 22.20 | 18.23 | +3.97 |
| Trades | 27 | 31 | -4 |
| PF | 1.60 | 1.70 | -0.10 |

### Full Sample Backtest (harsh, 50 bps RT)

| Metric | X2 | X0 | Delta |
|--------|:--:|:--:|:-----:|
| Sharpe | 1.4227 | 1.3249 | +0.0978 |
| CAGR% | 62.87 | 54.70 | +8.17 |
| MDD% | 40.28 | 42.05 | -1.77 |
| Trades | 138 | 172 | -34 |
| PF | 1.90 | 1.72 | +0.18 |
| Avg hold | 8.9d | 6.9d | +2.0d |

### Cost Sweep (X2 vs X0, Sharpe)

| BPS | X2 | X0 | Delta |
|-----|:--:|:--:|:-----:|
| 0 | 46.67 CAGR | 44.71 CAGR | +1.96 |
| 10 | 43.57 | 41.04 | +2.53 |
| 25 | 39.05 | 35.71 | +3.34 |
| 50 | 31.82 | 27.27 | +4.55 |
| 75 | 24.97 | 19.35 | +5.62 |
| 100 | 18.47 | 11.93 | +6.54 |

### Bootstrap (2000 paths, 3 block sizes, harsh)

| Block | P(X2>X0) | CI lower | CI upper |
|-------|:--------:|:--------:|:--------:|
| 10 | 87.5% | -0.078 | +0.281 |
| 20 | 87.2% | -0.071 | +0.281 |
| 40 | 86.2% | -0.068 | +0.280 |

CI includes zero at all block sizes — NOT statistically significant.

### Sensitivity Grid (trail_tight sweep, harsh)

| trail_tight | Sharpe | CAGR% | MDD% | Trades |
|:-----------:|:------:|:-----:|:----:|:------:|
| 2.7 | 1.3411 | 57.70 | 42.72 | 153 |
| **3.0** | **1.4227** | **62.87** | **40.28** | **138** |
| 3.3 | 1.3655 | 59.35 | 43.80 | 130 |

---

## TIER 2: Research Studies (T1-T7)

Via `research/parity_eval_x.py` — 4 strategies (E0, X0, X2, X6).
Output: `research/results/parity_eval_x/parity_eval_x_results.json`

| # | Technique | Status | Result |
|---|-----------|--------|--------|
| T1 | Full backtest 3 scenarios | DONE | X2 Sharpe 1.43 harsh (vec), +0.10 vs X0 |
| T2 | Permutation test 1K | DONE | p=0.001 — alpha is REAL |
| T3 | Timescale robustness 16 TS | DONE | 16/16 positive Sharpe, wins E0 16/16 |
| T4 | Bootstrap VCBB 500 paths | DONE | Med Sharpe 0.5833, wins X0 Sharpe 14/16 |
| T5 | Postmortem / failure | DONE | 8 DD>20% episodes (X0: 5) at SP=120 |
| T6 | Param sensitivity | DONE | trail_tight=3.0 optimal, plateau broad |
| T7 | Cost study | DONE | Wins X0 at ALL 6 cost levels (0-100 bps) |

### T3: Timescale Robustness (Sharpe, harsh)

| SP | E0 | X0 | X2 | X2 vs X0 |
|---:|:--:|:--:|:--:|:--------:|
| 30 | 0.67 | 0.96 | 1.00 | +0.05 |
| 60 | 0.80 | 1.04 | 1.18 | +0.14 |
| 120 | 1.28 | 1.34 | 1.43 | +0.10 |
| 200 | 1.43 | 1.48 | 1.55 | +0.07 |
| 360 | 1.11 | 1.18 | 1.26 | +0.07 |
| 720 | 0.84 | 0.98 | 1.07 | +0.09 |

X2 wins X0 at **all 16 timescales** (vectorized sim).

### T4: Bootstrap VCBB (SP=120)

| Metric | E0 | X0 | X2 |
|--------|:--:|:--:|:--:|
| Sharpe median | 0.6968 | 0.5621 | 0.5833 |
| CAGR median | 21.95% | 14.28% | 15.36% |
| MDD median | 58.49% | 52.17% | 53.85% |
| P(CAGR>0) | 0.882 | 0.846 | 0.848 |

Paired vs X0 (16 TS): Sharpe **14/16**, CAGR **16/16**, MDD **1/16**
Paired vs E0 (16 TS): Sharpe **0/16**, CAGR **0/16**, MDD **16/16**

### T7: Cost Study (Sharpe, X2 vs X0 delta)

| BPS | X2 Sharpe | X0 Sharpe | Delta |
|----:|:---------:|:---------:|:-----:|
| 0 | 1.6710 | 1.6441 | +0.027 |
| 25 | 1.4326 | 1.3360 | +0.097 |
| 50 | 1.1934 | 1.0269 | +0.167 |
| 75 | 0.9546 | 0.7188 | +0.236 |
| 100 | 0.7171 | 0.4134 | +0.304 |

Delta grows with cost — X2's fewer trades (lower turnover) is a genuine advantage.

---

## TIER 3: Comparative Analysis (T8-T12)

| # | Technique | Status | Result |
|---|-----------|--------|--------|
| T8 | Calendar slice | DONE | Wins 6/8 years vs X0 — **LOSES 2024** |
| T9 | Rolling 24m window | DONE | Wins 8/11 windows vs X0 |
| T10 | Start-date sensitivity | DONE | Wins ALL 7 start dates vs X0 |
| T11 | Paired bootstrap + Holm | DONE | **Holm p=0.85 — NOT SIGNIFICANT** |
| T12 | Signal concordance | DONE | X2-X0 agree 98.0%, X2-E0 agree 96.8% |

### T8: Calendar Slice (Sharpe by year)

| Year | E0 | X0 | X2 | X2 wins? |
|------|:--:|:--:|:--:|:--------:|
| 2019 | 1.83 | 1.73 | 1.80 | YES |
| 2020 | 2.68 | 2.61 | 2.79 | YES |
| 2021 | 1.47 | 1.63 | 1.75 | YES |
| 2022 | -1.00 | -0.93 | -1.02 | NO |
| 2023 | 1.16 | 1.21 | 1.54 | YES |
| **2024** | **1.44** | **1.69** | **1.62** | **NO** |
| 2025 | 0.14 | 0.15 | 0.21 | YES |
| 2026 | -0.33 | -0.62 | -0.62 | TIE |

2024 is the critical year where X0 beats X2 — aligns with WFO window 5 failure.

### T11: Holm-Adjusted P-values

| Pair | P(A>B) | Raw p | Holm p | Sig |
|------|:------:|:-----:|:------:|:---:|
| X2 vs E0 | 0.942 | 0.116 | 0.578 | ns |
| X2 vs X0 | 0.849 | 0.302 | 0.851 | ns |
| X0 vs E0 | 0.853 | 0.293 | 0.851 | ns |

---

## TIER 4: Trade Anatomy (T13-T17)

### Engine-based (Tier 1 backtest, harsh)

| Metric | X2 | X0 |
|--------|:--:|:--:|
| Trades | 138 | 172 |
| Win rate | 42.8% | 42.4% |
| Profit factor | 1.90 | 1.72 |
| Avg hold | 8.9d | 6.9d |
| Matched trades | 133 (96.4% match rate) |
| Bootstrap P(X2>X0 pnl) | 0.944 |
| DD episodes | 36 | 28 |

### Vectorized sim (parity_eval_x, harsh)

| Metric | X2 |
|--------|:--:|
| Trades | 150 |
| Win rate | 44.0% |
| PF | 1.809 |
| Avg hold | 9.0d |
| Skew | 3.151 |
| Excess kurtosis | 11.643 |
| JB p-value | 0.0000 |
| Gini | 0.656 |
| HHI | 0.0258 |
| Jackknife drop-1 | -3.4% |

### Exit Reason Breakdown (vectorized)

| Reason | Count | % | Win Rate | Avg Return |
|--------|:-----:|:-:|:--------:|:----------:|
| Trail stop | 131 | 87.3% | 48.9% | +4.23% |
| Trend exit | 19 | 12.7% | 10.5% | -1.85% |

---

## Diagnosis

X2's adaptive trail (tight=3, mid=4, wide=5 at 5%/15% thresholds) produces excellent in-sample results:
- +0.098 Sharpe, +8.17% CAGR, -34 trades vs X0

But fails out-of-sample validation:
1. **WFO 4/8** — below 60% threshold, worst delta -105.78
2. **Holdout -22.19** — X0 dominates recent data (Sharpe 1.05 vs 0.82)
3. **Holm p=0.85** — improvement not statistically significant
4. **7 params vs 4** — 3 additional params create overfitting risk
5. **More DD episodes** (36 vs 28) — adaptive trail increases drawdown frequency

The critical failure window (2024H2): X0's fixed 3x trail allows frequent entries (12 trades) during strong rally, catching multiple waves. X2's wider trail (4-5x at high gains) holds fewer, longer positions (9 trades), resulting in lower total PnL.

## Final Verdict: **REJECT**

X2 is NOT a suitable replacement for X0. Use X0 (E0+EMA21 D1) for real money.
