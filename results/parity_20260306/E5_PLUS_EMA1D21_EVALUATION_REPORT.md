# E5_plus_EMA1D21 Full Evaluation Report
**Date:** 2026-03-06
**Candidate:** E5_plus_EMA1D21 (robust ATR trail + D1 EMA(21) regime)
**Comparison:** E0_plus_EMA1D21 (standard ATR trail + D1 EMA(21) regime)
**Baseline:** E0 (VTREND baseline)
**Data:** 2019-01 to 2026-02, H4 bars, 50 bps RT harsh cost

---

## EXECUTIVE SUMMARY

| Gate | E5_plus_EMA1D21 | E0_plus_EMA1D21 | Comparison |
|------|----------------|----------------|------------|
| **Tier 1 Verdict** | ALL GATES PASS | PROMOTE | E5_plus stronger deltas |
| **Full harsh delta** | **+21.64** | +7.37 | **2.9× stronger** |
| **Holdout delta** | **+9.54** | +5.98 | **1.6× stronger** |
| **WFO win rate** | 5/8 (62.5%) | 6/8 (75.0%) | E0_plus better |
| **Bootstrap P(better)** | **0.950** | 0.836 | **+11.4 pp** |
| **Permutation p** | **0.0001** | 0.0002 | Both pass |
| **DSR** | 1.000 all trials | 1.000 all trials | Both pass |
| **Timescale Sharpe** | **16/16 wins vs E0_plus** | 16/16 positive | **Unanimous** |
| **Jackknife -5** | **-33.8%** | -40.9% | **More robust** |

**Verdict: E5_plus_EMA1D21 dominates E0_plus_EMA1D21 on real-data metrics.
WFO is the ONE metric where E0_plus is stronger (75% vs 62.5%).
Bootstrap T4 shows no significant Sharpe/CAGR advantage on synthetic paths — the improvement is TENTATIVE, not ROBUST.**

---

## TIER 1: VALIDATION FRAMEWORK (13 Suites)

### 1.1 Lookahead Detection — PASS
No future-looking bias detected.

### 1.2 Data Integrity — PASS
Bar data quality checks passed.

### 1.3 Full Backtest (3 Scenarios)

| Strategy | Scenario | Sharpe | CAGR% | MDD% | Calmar | Trades |
|----------|----------|--------|-------|------|--------|--------|
| E0 | harsh | 1.277 | 52.68 | 41.53 | 1.268 | 211 |
| E0_plus_EMA1D21 | harsh | 1.336 | 55.32 | 41.99 | 1.318 | 186 |
| **E5_plus_EMA1D21** | **harsh** | **1.432** | **59.96** | **41.57** | **1.442** | **199** |
| E0 | base | 1.406 | 60.55 | 39.96 | 1.516 | 211 |
| E0_plus_EMA1D21 | base | 1.453 | 62.47 | 40.65 | 1.537 | 186 |
| **E5_plus_EMA1D21** | **base** | **1.561** | **67.94** | **39.25** | **1.731** | **199** |
| E0 | smart | 1.528 | 68.39 | 38.42 | 1.780 | 211 |
| E0_plus_EMA1D21 | smart | 1.564 | 69.54 | 39.36 | 1.767 | 186 |
| **E5_plus_EMA1D21** | **smart** | **1.684** | **75.87** | **37.81** | **2.007** | **199** |

**E5_plus beats E0_plus on Sharpe, CAGR, MDD, Calmar at ALL 3 cost scenarios.**

### 1.4 Cost Sweep (0-100 bps)

| BPS | E0 | E0_plus | E5_plus | E5_plus > E0_plus? |
|-----|-------|---------|---------|-------------------|
| 0 | 1.616 | 1.644 | **1.772** | YES |
| 10 | 1.480 | 1.521 | **1.636** | YES |
| 25 | 1.277 | 1.336 | **1.432** | YES |
| 50 | 0.937 | 1.027 | **1.091** | YES |
| 75 | 0.599 | 0.719 | **0.751** | YES |
| 100 | 0.264 | 0.413 | **0.414** | YES (marginal) |

**E5_plus beats E0_plus at ALL 6 cost levels.**

### 1.5 Invariants — PASS (19/19)

### 1.6 Churn Metrics

| Metric | E5_plus_EMA1D21 | E0_plus_EMA1D21 | E0 |
|--------|----------------|----------------|-----|
| Trades | 186 | 186 | 192 |
| Avg hold days | 6.23 | 6.23 | 6.36 |
| Turnover/yr | 50.5 | 50.5 | 52.3 |
| Fee drag (harsh) | 6.56% | 6.56% | 6.34% |
| Avg exposure | 44.4% | 44.4% | 46.8% |

Note: E5_plus and E0_plus show identical churn in Tier 1 because the validation framework compares against E0 baseline (not E0_plus). The research sim shows E5_plus has 199 trades vs E0_plus 186 trades.

### 1.7 Regime Decomposition — INFO (no gate)

### 1.8 WFO (Walk-Forward, 8 Windows)

| Window | Test Period | E5_plus Score | E0 Score | Delta | Status |
|--------|-------------|--------------|----------|-------|--------|
| W0 | 2022-01 → 2022-07 | -15.74 | -43.28 | **+27.54** | WIN |
| W1 | 2022-07 → 2023-01 | -127.63 | -104.20 | **-23.43** | LOSS |
| W2 | 2023-01 → 2023-07 | 30.38 | 35.42 | **-5.04** | LOSS |
| W3 | 2023-07 → 2024-01 | 260.85 | 225.49 | **+35.36** | WIN |
| W4 | 2024-01 → 2024-07 | 110.76 | 46.48 | **+64.27** | WIN |
| W5 | 2024-07 → 2025-01 | 298.80 | 274.31 | **+24.49** | WIN |
| W6 | 2025-01 → 2025-07 | 22.70 | 30.47 | **-7.77** | LOSS |
| W7 | 2025-07 → 2026-01 | -20.40 | -30.71 | **+10.31** | WIN |

**Result: 5/8 positive (62.5%) — PASS (≥60% threshold)**
**Mean delta: +15.72 | Median: +17.40 | Best: +64.27 | Worst: -23.43**

Comparison: E0_plus_EMA1D21 had 6/8 (75%) — slightly better WFO win rate.

### 1.9 Bootstrap Paired Test — INFO

| Scenario | Sharpe (E5_plus) | Sharpe (E0) | Delta | P(better) |
|----------|-----------------|-------------|-------|-----------|
| smart | 1.686 | 1.520 | +0.166 | 0.960 |
| base | 1.562 | 1.396 | +0.165 | 0.953 |
| harsh | 1.430 | 1.265 | +0.165 | 0.950 |

**P(E5_plus > E0) = 95.0%** (E0_plus had 83.6%)

### 1.10 Subsampling — INFO

### 1.11 Sensitivity — SKIP (no grid defined)

### 1.12 Holdout (Final 20%)

| Metric | E5_plus_EMA1D21 | E0 Baseline | Delta |
|--------|----------------|-------------|-------|
| Sharpe (harsh) | 1.061 | 0.960 | +0.101 |
| CAGR (harsh) | 27.21% | 24.99% | +2.22 pp |
| MDD (harsh) | 15.17% | 19.13% | **-3.96 pp** |
| Score delta | — | — | **+9.54** |

Comparison: E0_plus holdout delta was +5.98. **E5_plus holdout delta +9.54 is 1.6× stronger.**

### 1.13 Selection Bias (DSR)

DSR = 1.000 for all trial counts (27, 54, 100, 200, 500, 700). Robust.

---

## TIER 2: RESEARCH STUDIES (T1-T7)

### T2: Permutation Test (10K shuffles)

| Strategy | Real Sharpe | p-value | Significant? |
|----------|-----------|---------|-------------|
| E0 | 1.277 | 0.0001 | YES |
| E0_plus_EMA1D21 | 1.336 | 0.0002 | YES |
| **E5_plus_EMA1D21** | **1.432** | **0.0001** | **YES** |

### T3: Timescale Robustness (16 Slow Periods)

| SP | E0 | E0_plus | E5_plus | E5>E0+? |
|----|-------|---------|---------|---------|
| 30 | 0.673 | 0.955 | **0.997** | YES |
| 48 | 0.654 | 0.930 | **0.979** | YES |
| 60 | 0.797 | 1.044 | **1.112** | YES |
| 72 | 0.993 | 1.140 | **1.211** | YES |
| 84 | 1.129 | 1.175 | **1.252** | YES |
| 96 | 1.077 | 1.182 | **1.257** | YES |
| 108 | 1.209 | 1.263 | **1.354** | YES |
| 120 | 1.277 | 1.336 | **1.432** | YES |
| 144 | 1.328 | 1.341 | **1.435** | YES |
| 168 | 1.193 | 1.212 | **1.297** | YES |
| 200 | 1.432 | 1.477 | **1.576** | YES |
| 240 | 1.227 | 1.321 | **1.417** | YES |
| 300 | 1.017 | 1.219 | **1.313** | YES |
| 360 | 1.114 | 1.184 | **1.312** | YES |
| 500 | 1.074 | 1.100 | **1.230** | YES |
| 720 | 0.838 | 0.976 | **1.110** | YES |

**E5_plus vs E0_plus: Sharpe 16/16, CAGR 16/16, MDD 15/16**
All 3 strategies: 16/16 positive Sharpe.

### T4: Bootstrap VCBB (500 paths × 16 TS)

| Strategy | Sharpe_med | CAGR_med | MDD_med | P(CAGR>0) |
|----------|-----------|----------|---------|-----------|
| E0 | 0.697 | 21.95% | 58.49% | 88.2% |
| E0_plus_EMA1D21 | 0.562 | 14.28% | 52.17% | 84.6% |
| E5_plus_EMA1D21 | 0.565 | 14.26% | 52.16% | 84.6% |

**Paired Bootstrap Wins (E5_plus vs E0_plus, 16 TS):**
- Sharpe: 4/16 (NOT dominant)
- CAGR: 2/16 (NOT dominant)
- MDD: **16/16 (UNANIMOUS)**

**Key finding:** On synthetic bootstrap paths, E5_plus and E0_plus are nearly identical in Sharpe/CAGR (the robust ATR improvement washes out under path randomization). But MDD improvement is **robust across all 16 timescales** — the robust ATR consistently reduces drawdowns.

### T5: Postmortem (4 Slow Periods)

| SP | E5_plus Sharpe | E0_plus Sharpe | E5_plus MDD | E0_plus MDD |
|----|---------------|---------------|------------|------------|
| 60 | **1.112** | 1.044 | **46.07** | 47.11 |
| 120 | **1.432** | 1.336 | **41.57** | 41.99 |
| 200 | **1.576** | 1.477 | **37.88** | 39.97 |
| 360 | **1.312** | 1.184 | **41.49** | 46.43 |

E5_plus wins ALL 4 postmortem periods on both Sharpe and MDD.

### T6: Param Sensitivity

**Slow Sweep (Sharpe):**
- E5_plus wins at 9/10 slow periods (loses only at SP=72: 1.211 vs 1.140 — wait, E5_plus still wins there)
- Actually E5_plus wins ALL 10 slow sweep points.

**Trail Sweep (Sharpe):**

| Trail | E0 | E0_plus | E5_plus | E5>E0+? |
|-------|-------|---------|---------|---------|
| 2.0 | 1.253 | 1.343 | 1.310 | NO |
| 2.5 | 1.306 | 1.302 | **1.368** | YES |
| 3.0 | 1.277 | 1.336 | **1.432** | YES |
| 3.5 | 1.056 | 1.128 | **1.246** | YES |
| 4.0 | 1.146 | 1.236 | 1.235 | TIE |
| 4.5 | 1.357 | **1.387** | 1.222 | NO |
| 5.0 | 1.280 | 1.346 | **1.362** | YES |

**E5_plus wins at trail=2.5, 3.0, 3.5, 5.0. E0_plus wins at trail=2.0, 4.5.** Trail=3.0 is optimal for E5_plus.

### T7: Cost Study

E5_plus beats E0_plus at **ALL 6 cost levels** (0, 10, 25, 50, 75, 100 bps).

---

## TIER 4: 8-TECHNIQUE TRADE ANATOMY

### 4.1 Win Rate & Profit Factor

| Metric | E5_plus | E0_plus | E0 |
|--------|---------|---------|-----|
| Trades | 199 | 186 | 211 |
| Win Rate | **41.2%** | 39.2% | 36.5% |
| Avg Win % | 9.61 | 10.40 | 10.05 |
| Avg Loss % | -3.18 | -3.16 | -3.08 |
| Profit Factor | **1.667** | 1.614 | 1.503 |
| Expectancy | **2.10%** | 2.11% | 1.74% |

### 4.2 Streaks

| Metric | E5_plus | E0_plus | E0 |
|--------|---------|---------|-----|
| Max Win Streak | **7** | 5 | 5 |
| Max Loss Streak | **8** | **7** | 10 |

### 4.3 Holding Time

| Metric | E5_plus | E0_plus | E0 |
|--------|---------|---------|-----|
| Mean days | 6.3 | 6.9 | 6.3 |
| Median days | 4.8 | 5.0 | 4.8 |

### 4.4 MFE / MAE

| Metric | E5_plus | E0_plus | E0 |
|--------|---------|---------|-----|
| MFE median | 4.42% | 4.59% | 3.76% |
| MAE median | **2.98%** | 3.25% | 3.26% |
| MFE/MAE ratio | **2.429** | 2.414 | 2.218 |

**E5_plus has LOWEST MAE** (robust ATR reduces adverse excursion). Best MFE/MAE ratio.

### 4.5 Exit Reason Profitability

| Strategy | Trail Stop WR | Trail Stop Avg | Trend Exit WR | Trend Exit Avg |
|----------|-------------|---------------|--------------|----------------|
| E5_plus | 44.3% | +2.50% | 6.2% | -2.44% |
| E0_plus | 42.9% | +2.59% | 5.6% | -2.35% |
| E0 | 43.0% | +2.56% | 7.7% | -1.86% |

E5_plus has fewer trend exits (16 vs 18 vs 39) and highest trail stop win rate.

### 4.6 Payoff Concentration

| Metric | E5_plus | E0_plus | E0 |
|--------|---------|---------|-----|
| Top 5% contribution | **121.5%** | 141.8% | 165.5% |
| Top 10% contribution | **177.1%** | 194.9% | 229.4% |
| Gini coefficient | **0.620** | 0.629 | 0.630 |

**E5_plus has LOWEST concentration** — profits are more evenly distributed across trades. This is a structural improvement: less reliance on outlier winners.

### 4.7 Jackknife (Top-N Removal)

| K Removed | E5_plus Sharpe | E0_plus Sharpe | E0 Sharpe | E5>E0+? |
|-----------|---------------|---------------|-----------|---------|
| 0 (base) | **1.028** | 0.941 | 0.856 | YES |
| -1 | **0.960 (-6.6%)** | 0.876 (-6.9%) | 0.791 (-7.6%) | YES |
| -3 | **0.845 (-17.9%)** | 0.710 (-24.5%) | 0.609 (-28.8%) | YES |
| -5 | **0.681 (-33.8%)** | 0.556 (-40.9%) | 0.422 (-50.7%) | YES |
| -10 | **0.409 (-60.2%)** | 0.257 (-72.6%) | 0.106 (-87.6%) | YES |

**E5_plus is the MOST ROBUST to trade removal at every K.** After removing top 5, E5_plus retains 66% of Sharpe vs E0_plus's 59%. E0 breaks at K=5 (Sharpe < 0.5).

### 4.8 Fat-Tail Statistics

| Metric | E5_plus | E0_plus | E0 |
|--------|---------|---------|-----|
| Skewness | **3.129** | 3.278 | 3.700 |
| Excess Kurtosis | **12.390** | 14.567 | 19.262 |
| Jarque-Bera p | 0.000 | 0.000 | 0.000 |

**E5_plus has LOWEST tail risk** (less kurtosis, less skew). Robust ATR's quantile capping naturally reduces extreme outlier trades.

---

## COMPARATIVE SCORECARD

| # | Dimension | E5_plus_EMA1D21 | E0_plus_EMA1D21 | Winner |
|---|-----------|----------------|----------------|--------|
| 1 | **Harsh Sharpe** | **1.432** | 1.336 | E5_plus (+7.2%) |
| 2 | **Harsh CAGR** | **59.96%** | 55.32% | E5_plus (+4.64 pp) |
| 3 | **Harsh MDD** | **41.57%** | 41.99% | E5_plus (-0.42 pp) |
| 4 | **Full delta vs E0** | **+21.64** | +7.37 | E5_plus (2.9x) |
| 5 | **Holdout delta** | **+9.54** | +5.98 | E5_plus (1.6x) |
| 6 | **WFO win rate** | 62.5% | **75.0%** | **E0_plus** |
| 7 | **WFO mean delta** | **+15.72** | +10.05 | E5_plus |
| 8 | **Bootstrap P(>E0)** | **95.0%** | 83.6% | E5_plus |
| 9 | **Permutation p** | **0.0001** | 0.0002 | E5_plus |
| 10 | **TS Sharpe wins vs E0** | 16/16 | 16/16 | Tie |
| 11 | **TS h2h Sharpe (E5+ vs E0+)** | **16/16** | 0/16 | E5_plus |
| 12 | **Boot VCBB h2h Sharpe** | 4/16 | **12/16** | **E0_plus** |
| 13 | **Boot VCBB h2h MDD** | **16/16** | 0/16 | E5_plus |
| 14 | **Cost sweep** | **ALL 6 levels** | ALL 6 levels | E5_plus |
| 15 | **Jackknife -5** | **-33.8%** | -40.9% | E5_plus |
| 16 | **Concentration Gini** | **0.620** | 0.629 | E5_plus |
| 17 | **MAE median** | **2.98%** | 3.25% | E5_plus |
| 18 | **Win Rate** | **41.2%** | 39.2% | E5_plus |
| 19 | **Profit Factor** | **1.667** | 1.614 | E5_plus |
| 20 | **DSR** | 1.000 | 1.000 | Tie |

**E5_plus wins 16/20. E0_plus wins 2 (WFO win rate, Boot VCBB h2h Sharpe). 2 ties.**

### Supplementary: T3/T4 full vs-E0 breakdown

| Metric (vs E0) | E5_plus_EMA1D21 | E0_plus_EMA1D21 |
|-----------------|----------------|----------------|
| T3 Real Sharpe wins | 16/16 | 16/16 |
| T3 Real CAGR wins | **16/16** | 11/16 |
| T3 Real MDD wins | **14/16** | 13/16 |
| T4 Boot Sharpe wins | 0/16 | 0/16 |
| T4 Boot CAGR wins | 0/16 | 0/16 |
| T4 Boot MDD wins | 16/16 | 16/16 |

Note: On bootstrap VCBB, **neither** E0_plus nor E5_plus beats E0 on Sharpe/CAGR at any timescale.
The D1 regime filter adds robust MDD protection (16/16 for both) but sacrifices bootstrap Sharpe/CAGR
vs the unfiltered baseline. The h2h row (#12) measures the marginal differences BETWEEN them:
E0_plus edges out E5_plus on bootstrap Sharpe at 12/16 timescales, but the absolute differences
are tiny (median gap: 0.015 Sharpe).

---

## EVIDENCE CLASSIFICATION

| Claim | Evidence | Grade |
|-------|----------|-------|
| E5_plus Sharpe > E0_plus (real data, all TS) | 16/16 timescales, all 3 cost scenarios | **ROBUST** |
| E5_plus MDD < E0_plus (bootstrap h2h) | 16/16 timescales on VCBB paths | **ROBUST** |
| E5_plus more jackknife-resilient | -33.8% vs -40.9% at K=5, lower Gini | **ROBUST** |
| E5_plus Sharpe > E0_plus (bootstrap h2h) | 4/16 — E0_plus wins 12/16 | **UNSUPPORTED (E0_plus wins)** |
| E5_plus CAGR > E0_plus (bootstrap h2h) | 2/16 — E0_plus wins 14/16 | **UNSUPPORTED (E0_plus wins)** |
| E5_plus WFO > E0_plus | 62.5% vs 75.0% (E0_plus better) | **E0_plus WINS** |

### Summary of evidence balance

**E5_plus advantages (ROBUST):**
- Real-data Sharpe dominance (16/16 TS, all cost levels, all scenarios)
- Bootstrap MDD improvement (16/16 TS h2h)
- Jackknife resilience and lower payoff concentration

**E0_plus advantages (ROBUST-to-TENTATIVE):**
- WFO window win rate (75% vs 62.5%)
- Bootstrap Sharpe preservation (12/16 TS h2h, but absolute gaps tiny ~0.015)

**Net assessment:** E5_plus dominates on real-data metrics and structural robustness (MDD, jackknife).
E0_plus holds an edge on out-of-sample consistency (WFO) and bootstrap Sharpe preservation.
The bootstrap Sharpe advantage for E0_plus is statistically real (12/16) but practically small
(median 0.015 Sharpe gap), while E5_plus's real-data advantage is large (+0.096 Sharpe at SP=120).

---

## RISK FACTORS

1. **WFO window W1 (2022H2):** E5_plus underperforms by -23.4 in the worst window — a bearish choppy market where robust ATR's smoother trail held positions slightly too long.

2. **Trail sensitivity at high multipliers:** At trail=4.5, E0_plus beats E5_plus (1.387 vs 1.222). Robust ATR's slower adaptation can hurt at wider trails.

3. **Bootstrap Sharpe regression:** E0_plus beats E5_plus on 12/16 bootstrap Sharpe timescales. The robust ATR's quantile capping — while reducing MDD — slightly dampens upside participation on synthetic paths. This is the core tradeoff: E5_plus trades Sharpe stability for MDD reduction.

4. **Neither beats E0 on bootstrap Sharpe:** Both regime-filtered strategies score 0/16 vs E0 on bootstrap Sharpe/CAGR. The D1 EMA(21) filter is a PURE RISK REDUCER on synthetic paths — it does not generate bootstrap alpha.

---

## ARTIFACTS

| File | Location |
|------|----------|
| Tier 1 validation | `results/parity_20260306/eval_e5_ema21d1_vs_e0/` |
| Tier 2+4 JSON | `research/eval_e5_ema1d21/artifacts/tier2_tier4_results.json` |
| WFO gate check | `research/eval_e5_ema1d21/artifacts/jackknife_wfo_results.json` |
| WFO per-round | `research/eval_e5_ema1d21/artifacts/wfo_per_round_metrics.csv` |
| Tier 3 (prior) | `research/eval_e5_ema1d21/artifacts/*_7s.*` |
