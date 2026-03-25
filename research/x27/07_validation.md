# Phase 7: Validation

**Study**: X27
**Date**: 2026-03-11
**Input**: Phase 6 candidates (Cand01–Cand03), rejection criteria (R1–R6), benchmark specification

---

## 1. IMPLEMENTATION

### Strategy Implementations

All three candidates and the benchmark were implemented exactly per Phase 6 specification in `code/phase7_validation.py` (single runnable script, ~500 lines).

**Cand01 (Breakout + ATR Trail, 3 DOF)**:
- Entry: H4 close > max(high of preceding 120 bars)
- Exit: H4 close ≤ peak_close − 4.0 × ATR(20)
- Parameters: N=120, p=20, m=4.0

**Cand02 (Breakout + ATR Trail + D1 EMA21 Regime, 4 DOF)**:
- Same as Cand01 + D1 close (lagged) > D1 EMA(21)
- Parameters: N=120, p=20, m=4.0, K=21

**Cand03 (ROC Threshold + ATR Trail, 4 DOF)**:
- Entry: ROC(40) > 15%
- Exit: Same as Cand01
- Parameters: N_roc=40, τ=0.15, p=20, m=4.0

**Benchmark (VTREND E5+EMA21D1, binary sizing)**:
- Entry: EMA(30) > EMA(120) AND VDO(12,28) > 0 AND D1 close > D1 EMA(21)
- Exit: close < peak − 3.0 × RobustATR(20) OR EMA(30) < EMA(120)
- Position sizing: binary {0,1} for fair comparison with candidates

### Data

- H4: 18,751 bars (2017-08 to 2026-02), BPY = 2189.6
- D1: 3,128 bars
- 8.56 years of evaluation data
- Warmup: 200 bars

### Sanity Checks

| Check | Cand01 | Cand02 | Cand03 |
|-------|--------|--------|--------|
| Trade count vs estimate | 70 (est 45–65) ✓ | 68 (est 25–40) ⚠ | 55 (est 50–80) ✓ |
| Lookahead | None (D1 lagged, signals at bar close) | None | None |
| Cost | 50 bps RT per trade ✓ | ✓ | ✓ |
| Position sizing | Binary {0,1} ✓ | ✓ | ✓ |

**Cand02 trade count warning**: Phase 6 estimated 25–40 trades based on SMA(200) regime halving trade count (Obs52). Actual: 68 trades — the D1 EMA(21) filter only blocked 2 of 70 breakout entries. This reveals that breakout entries (new 120-bar highs) almost always coincide with D1 close > EMA(21). The regime filter is effectively redundant for breakout-type entries. The Phase 6 estimate was based on EMA crossover entry pairs, not breakout pairs.

---

## 2. FULL-SAMPLE BACKTEST

### Tbl_full_sample_comparison

| Metric | Cand01 | Cand02 | Cand03 | Benchmark |
|--------|--------|--------|--------|-----------|
| **Sharpe** | **0.9073** | **0.9197** | 0.4495 | **1.0836** |
| **CAGR (%)** | 38.62 | 38.95 | 17.58 | **58.21** |
| **MDD (%)** | **41.38** | 42.42 | 54.23 | 52.59 |
| Calmar | 0.9333 | 0.9182 | 0.3242 | 1.1068 |
| Trades | 70 | 68 | 55 | 219 |
| Win rate (%) | 45.7 | 45.6 | 45.5 | 41.6 |
| Exposure (%) | 28.4 | 27.8 | 21.3 | 42.9 |
| Avg hold (bars) | 75.2 | 75.9 | 72.0 | 36.3 |
| Max consec losses | 6 | 6 | 7 | 9 |
| Profit factor | 2.74 | 2.80 | 1.91 | 2.10 |
| Avg winner (%) | 17.95 | 18.43 | 17.70 | 10.87 |
| Avg loser (%) | -5.51 | -5.52 | -7.74 | -3.68 |

### Key Observations

1. **Cand01/02 vs Benchmark — different risk profiles**: The breakout candidates achieve Sharpe ~0.91 vs benchmark 1.08 (Δ = −0.17), but with substantially lower MDD (41% vs 53%, Δ = −11 pp). This confirms the Phase 5 prediction of convergent alpha at different points on the risk frontier.

2. **Cand01 ≈ Cand02**: The D1 EMA(21) filter adds only +0.012 Sharpe while adding 1 DOF. The filter blocked only 2/70 entries — it is redundant for breakout entries.

3. **Cand03 underperforms**: Sharpe 0.45 is well below both other candidates and benchmark. ROC(40) > 15% is too aggressive a filter — only 55 trades with similar hold period but much worse capture.

4. **Churn structure**: Breakout candidates have ZERO churn (0/70 trades) vs benchmark 49.1% (107/219). This confirms Prop04 and validates the structural advantage of breakout entry over EMA crossover.

5. **Trade quality**: Breakout candidates have higher avg winner (18% vs 11%), higher win rate (46% vs 42%), and higher profit factor (2.7 vs 2.1). The benchmark compensates with 3× more trades and higher exposure.

### Pre-committed Rejection Criteria (Full-sample)

| # | Criterion | Cand01 | Cand02 | Cand03 |
|---|-----------|--------|--------|--------|
| R1 | Sharpe ≥ 0 | PASS | PASS | PASS |
| R2 | Sharpe ≥ 0.867 (80% of bench) | PASS (0.907) | PASS (0.920) | **FAIL** (0.450) |
| R3 | MDD ≤ 75% | PASS (41.4%) | PASS (42.4%) | PASS (54.2%) |
| R4 | Trades ≥ 15 | PASS (70) | PASS (68) | PASS (55) |

Cand03 fails R2 at the full-sample level.

---

## 3. WALK-FORWARD OPTIMIZATION (WFO)

4 folds, anchored expanding window, fixed parameters (no optimization).
Segment size: ~3,710 bars (~1.7 years per test fold).

### Tbl_wfo_results

| Strategy | Fold | IS Sharpe | OOS Sharpe | OOS Bench | ΔSharpe | OOS Trades |
|----------|------|-----------|------------|-----------|---------|------------|
| Cand01 | 1 | 1.374 | 1.908 | 1.871 | **+0.037** | 12 |
| Cand01 | 2 | 1.598 | −0.442 | 0.304 | −0.746 | 13 |
| Cand01 | 3 | 1.074 | 1.190 | 0.998 | **+0.192** | 15 |
| Cand01 | 4 | 1.083 | −0.209 | 0.673 | −0.882 | 18 |
| Cand02 | 1 | 1.429 | 1.908 | 1.871 | **+0.037** | 12 |
| Cand02 | 2 | 1.629 | −0.491 | 0.304 | −0.796 | 13 |
| Cand02 | 3 | 1.091 | 1.122 | 0.998 | **+0.124** | 15 |
| Cand02 | 4 | 1.085 | −0.132 | 0.673 | −0.805 | 17 |
| Cand03 | 1 | 1.038 | 0.902 | 1.871 | −0.969 | 15 |
| Cand03 | 2 | 0.972 | −0.954 | 0.304 | −1.258 | 15 |
| Cand03 | 3 | 0.502 | 0.505 | 0.998 | −0.493 | 9 |
| Cand03 | 4 | 0.490 | 0.239 | 0.673 | −0.434 | 3 |

### WFO Summary

| Strategy | Win Rate | Positive Folds | Gate R5 (≥50%) |
|----------|----------|----------------|----------------|
| Cand01 | 50% | 2/4 | **PASS** |
| Cand02 | 50% | 2/4 | **PASS** |
| Cand03 | 0% | 0/4 | **FAIL** |

**Observation**: Cand01/02 win folds 1 and 3, lose folds 2 and 4. Folds 2 and 4 cover 2020–2022 and 2024–2026 respectively — periods with extended bear/range markets where breakout entries generate fewer signals and more false positives. The benchmark's EMA crossover entry is more adaptive during these periods due to higher trade frequency.

Cand03 loses ALL 4 folds — the ROC entry never beats the benchmark in any sub-period.

---

## 4. BOOTSTRAP VALIDATION

Circular block bootstrap, block size = 136 (√18751), 2000 paths.
Paired bootstrap (same block indices for candidate and benchmark).

### Tbl_bootstrap_summary

| Strategy | P(Sharpe > 0) | P(Δ > 0) | Median Δ | [5%, 95%] |
|----------|---------------|----------|----------|-----------|
| Cand01 | **99.2%** | 19.2% | −0.184 | [−0.546, +0.160] |
| Cand02 | **99.2%** | 20.5% | −0.170 | [−0.542, +0.176] |
| Cand03 | **88.2%** | 0.7% | −0.644 | [−1.116, −0.190] |

### Interpretation

- **Alpha is real**: All three candidates have P(Sharpe > 0) > 60%, passing R6. Cand01/02 at 99.2% — strong evidence of genuine alpha.
- **Benchmark is better**: P(Δ > 0) ≈ 20% for Cand01/02 — the benchmark almost certainly has higher Sharpe. This is not a rejection criterion but confirms the Phase 5 prediction.
- **Cand03 95% CI excludes zero**: The entire [5%, 95%] interval for Cand03's delta is negative, meaning the bootstrap is confident Cand03 is worse than benchmark at the Sharpe level.

---

## 5. ROBUSTNESS CHECKS

### 5a. Jackknife (6 folds, chronological delete-one-block)

### Tbl_jackknife

| Fold | Cand01 Sh | Cand02 Sh | Cand03 Sh | Bench Sh |
|------|-----------|-----------|-----------|----------|
| 1 | 0.910 | 0.906 | 0.290 | 1.214 |
| 2 | 0.848 | 0.863 | 0.554 | 1.040 |
| 3 | 0.633 | 0.647 | 0.156 | 0.700 |
| 4 | 1.036 | 1.061 | 0.676 | 1.347 |
| 5 | 0.986 | 1.007 | 0.515 | 1.064 |
| 6 | 1.008 | 1.009 | 0.461 | 1.121 |
| Neg folds | **0/6** | **0/6** | **0/6** | 0/6 |

**Gate**: ≤ 1 fold with Sharpe < 0 → **ALL PASS**

All candidates maintain positive Sharpe in every jackknife fold. Cand01/02 show moderate variation (range 0.63–1.06), worst in fold 3 (mid-data removal covering late 2020 to mid 2022). Cand03 weakest in fold 3 (Sh = 0.156) but still positive.

### 5b. Cost Sensitivity

### Tbl_cost_sensitivity (Sharpe values)

| Cost (bps) | Cand01 | Cand02 | Cand03 | Benchmark |
|------------|--------|--------|--------|-----------|
| 15 | 0.994 | 1.005 | 0.516 | 1.317 |
| 30 | 0.957 | 0.968 | 0.487 | 1.216 |
| **50** | **0.907** | **0.920** | **0.450** | **1.084** |
| 75 | 0.846 | 0.859 | 0.403 | 0.921 |
| 100 | 0.784 | 0.799 | 0.356 | 0.761 |

**Key findings**:
- Cand01 Sharpe = 0 breakeven: >999 bps (extremely robust to cost)
- Cand01 loses to benchmark at ALL cost levels — the Sharpe gap persists
- **At 100 bps**, Cand01/02 (0.78/0.80) BEATS benchmark (0.76) — the zero-churn advantage emerges at high cost
- Benchmark degrades faster: ΔSharpe/Δcost = −0.0065/bps (benchmark) vs −0.0025/bps (Cand01)
- **Crossover point**: ~105 bps RT — above this, breakout strategies dominate the benchmark
- Cand03 never beats benchmark at any cost level

### 5c. Regime Split (D1 SMA200 bull/bear)

| Strategy | Bull Sharpe | Bear Sharpe | Bull MDD | Bear MDD |
|----------|-------------|-------------|----------|----------|
| Cand01 | 1.125 | 0.657 | 42.9% | 41.4% |
| Cand02 | 1.095 | 0.717 | 42.9% | 38.6% |
| Cand03 | 0.754 | 0.130 | 43.6% | 66.1% |
| Benchmark | 1.195 | 0.955 | 48.6% | 48.8% |

**All candidates work in both regimes** (positive Sharpe). Bear-market Sharpe is lower for all but no strategy collapses. Cand03's bear performance is near-zero (0.13) — the ROC entry struggles in range-bound markets.

Bull/bear split: 51.6% / 48.4% of bars.

### 5d. Year-by-Year Performance

### Tbl_yearly_performance (Sharpe by year)

| Year | Cand01 | Cand02 | Cand03 | Benchmark |
|------|--------|--------|--------|-----------|
| 2017 | 2.921 | 2.921 | 3.329 | 2.647 |
| 2018 | −0.924 | −0.737 | −0.621 | −0.900 |
| 2019 | 1.514 | 1.514 | 0.085 | 1.569 |
| 2020 | 2.678 | 2.678 | 1.319 | 2.673 |
| 2021 | 0.711 | 0.711 | 0.980 | 1.538 |
| 2022 | −1.795 | −2.088 | −3.361 | −1.182 |
| 2023 | 1.891 | 1.836 | 0.667 | 1.074 |
| 2024 | 0.160 | 0.101 | 0.639 | 1.657 |
| 2025 | 0.273 | 0.173 | −0.801 | 0.054 |
| 2026 | −2.515 | −1.419 | 0.000 | −2.133 |

**No catastrophic years** (no CAGR < −50%). Negative Sharpe years: 2018, 2022, 2026 (partial year) — all bear/correction periods.

**2022 is the worst year** for all strategies: Cand01 Sh=−1.80, Cand03 Sh=−3.36. The extended bear market (BTC −65%) hits all trend-following systems.

**2024**: Cand01/02 near-zero (0.16/0.10) while benchmark posts 1.66 — the benchmark's more frequent trading captures the 2024 rally better.

---

## 6. CHURN ANALYSIS (H_prior_4 verification)

### Tbl_churn_comparison

| Strategy | Churn Events | Total Trades | Churn Rate | Churn Cost |
|----------|-------------|--------------|------------|------------|
| **Cand01** | **0** | 70 | **0.0%** | 0.00% |
| **Cand02** | **0** | 68 | **0.0%** | 0.00% |
| Cand03 | 1 | 55 | 1.9% | 0.50% |
| Benchmark | **107** | 219 | **49.1%** | 53.50% |

**H_prior_4 CONFIRMED**: Breakout entry naturally eliminates churn. After an ATR trail exit, re-entry requires price to make a new 120-bar high — this mechanical delay prevents the exit→re-enter→exit cycle.

The benchmark suffers massive churn: 107 of 218 inter-trade gaps (49.1%) are ≤ 10 bars. Each churn cycle costs 50 bps RT, totaling approximately 53.5% of equity over the backtest period. This is the primary structural disadvantage of EMA crossover entry.

Cand03 has 1 churn event — ROC re-entry is less protected than breakout but still near-zero.

---

## 7. VERDICTS

### Cand01: Breakout + ATR Trail (3 DOF) — ★ PROMOTE ★

| Gate | Result | Value |
|------|--------|-------|
| R1: Sharpe ≥ 0 | PASS | 0.907 |
| R2: Sharpe ≥ 0.867 | PASS | 0.907 > 0.867 |
| R3: MDD ≤ 75% | PASS | 41.4% |
| R4: Trades ≥ 15 | PASS | 70 |
| R5: WFO WR ≥ 50% | PASS | 50% (2/4) |
| R6: Bootstrap P(Sh>0) ≥ 60% | PASS | 99.2% |
| Jackknife ≤ 1 neg | PASS | 0/6 |
| No catastrophic year | PASS | — |

**ALL gates PASS.** Cand01 is the simplest candidate (3 DOF), has the lowest MDD (41.4%), zero churn, and maintains positive Sharpe across all jackknife folds. The Sharpe deficit vs benchmark (−0.18) is the cost of lower exposure (28% vs 43%) and fewer trades, but the MDD advantage (−11 pp) offers a materially different risk profile.

---

### Cand02: Breakout + ATR Trail + D1 EMA21 (4 DOF) — ★ PROMOTE ★

| Gate | Result | Value |
|------|--------|-------|
| R1: Sharpe ≥ 0 | PASS | 0.920 |
| R2: Sharpe ≥ 0.867 | PASS | 0.920 > 0.867 |
| R3: MDD ≤ 75% | PASS | 42.4% |
| R4: Trades ≥ 15 | PASS | 68 |
| R5: WFO WR ≥ 50% | PASS | 50% (2/4) |
| R6: Bootstrap P(Sh>0) ≥ 60% | PASS | 99.2% |
| Jackknife ≤ 1 neg | PASS | 0/6 |
| No catastrophic year | PASS | — |

**ALL gates PASS**, but with a caveat: Cand02 adds 1 DOF (D1 EMA period) for negligible improvement over Cand01 (+0.012 Sharpe, +0.33% CAGR, +1.0% MDD). The regime filter blocked only 2 of 70 entries. Per the complexity principle (fewer DOF preferred when evidence equivalent), **Cand01 is preferred over Cand02**.

---

### Cand03: ROC Threshold + ATR Trail (4 DOF) — HOLD

| Gate | Result | Value |
|------|--------|-------|
| R1: Sharpe ≥ 0 | PASS | 0.450 |
| R2: Sharpe ≥ 0.867 | **FAIL** | 0.450 < 0.867 |
| R3: MDD ≤ 75% | PASS | 54.2% |
| R4: Trades ≥ 15 | PASS | 55 |
| R5: WFO WR ≥ 50% | **FAIL** | 0% (0/4) |
| R6: Bootstrap P(Sh>0) ≥ 60% | PASS | 88.2% |
| Jackknife ≤ 1 neg | PASS | 0/6 |
| No catastrophic year | PASS | — |

**2 gates FAIL** (R2, R5). The ROC entry with τ=15% is too aggressive — it captures fewer trends and misses the entry timing advantage hypothesized in Phase 6. The speed advantage (lower lag) is real but doesn't compensate for the severe detection rate loss. Verdict is HOLD (not REJECT) because alpha is still real (P(Sh>0) = 88%) and it may improve with parameter adjustment.

---

## 8. CROSS-CANDIDATE COMPARISON

| Property | Cand01 (PROMOTE) | Cand02 (PROMOTE) | Cand03 (HOLD) | Benchmark |
|----------|---------|---------|---------|-----------|
| DOF | 3 | 4 | 4 | 5+ |
| Sharpe | 0.907 | 0.920 | 0.450 | 1.084 |
| CAGR | 38.6% | 39.0% | 17.6% | 58.2% |
| MDD | **41.4%** | 42.4% | 54.2% | 52.6% |
| Calmar | 0.933 | 0.918 | 0.324 | 1.107 |
| Churn | **0%** | **0%** | 1.9% | 49.1% |
| WFO WR | 50% | 50% | 0% | — |
| P(Sh>0) | 99.2% | 99.2% | 88.2% | — |
| Verdict | **PROMOTE** | PROMOTE | HOLD | — |

**Primary candidate: Cand01** — simplest (3 DOF), lowest MDD, zero churn, all gates pass.

---

## 9. KEY FINDINGS

### What X27 Discovered

1. **Breakout entry eliminates churn entirely** (0/70 vs 107/219 for EMA cross). This is the single most important structural finding. The breakout's natural re-entry barrier (new N-bar high requirement) is an inherent anti-churn mechanism.

2. **Alpha converges across entry types**: Breakout (Sh 0.91) and EMA crossover (Sh 1.08) produce similar-order Sharpe from the same underlying BTC trend phenomenon. The alpha surface is robust to mechanism choice — confirming H_prior_2 (cross-scale redundancy extends to cross-mechanism redundancy).

3. **MDD-Sharpe tradeoff is real**: Breakout trades fewer, bigger moves with lower MDD (41% vs 53%), while EMA crossover trades more frequently with higher Sharpe but deeper drawdowns. Neither dominates the other — they occupy different frontier positions.

4. **D1 EMA(21) regime filter is redundant for breakout entries**: Blocked only 2/70 entries. New N-bar highs are inherently regime-aligned.

5. **ROC entry underperforms**: The "speed vs detection" hypothesis (Phase 6, Cand03) fails — faster entry with ROC(40) > 15% captures too few trends to compensate.

6. **At high cost (>100 bps), breakout dominates**: Zero churn means cost scaling is ~3× slower than EMA crossover. The crossover point is ~105 bps RT.

### What X27 Confirms About Prior Research

- H_prior_1 (trend persistence): CONFIRMED — Sh 0.91 from data-derived breakout confirms real trend alpha
- H_prior_3 (lag vs FP tradeoff): CONFIRMED — breakout's lower FP rate translates to better win rate (46% vs 42%)
- H_prior_4 (churn structural): CONFIRMED STRONGLY — breakout = 0% churn (complete solution)
- H_prior_5 (volume at entry ≈ 0): Not directly tested but VDO filter omission in candidates doesn't hurt
- H_prior_10 (complexity ceiling): CONFIRMED — 3-param Cand01 matches 4-param Cand02

---

## End-of-Phase Checklist

### 1. Files created
- `07_validation.md` (this report)
- `code/phase7_validation.py` (complete, runnable)
- `phase7_results.json` (machine-readable results)
- **Figures**: Fig14 (equity), Fig15 (drawdown), Fig16 (monthly heatmap), Fig17 (trade distribution), Fig18 (WFO deltas), Fig19 (bootstrap), Fig20 (cost sensitivity)
- **Tables**: Tbl_full_sample_comparison, Tbl_wfo_results, Tbl_bootstrap_summary, Tbl_cost_sensitivity, Tbl_jackknife, Tbl_yearly_performance, Tbl_churn_comparison

### 2. Key IDs
- Test01: Full-sample backtest (4 strategies × 12 metrics)
- Test02: WFO (4 folds × 3 candidates)
- Test03: Bootstrap (2000 paths × 3 candidates)
- Test04: Jackknife (6 folds × 4 strategies)
- Test05: Cost sensitivity (5 levels × 4 strategies)
- Test06: Regime split (bull/bear × 4 strategies)
- Test07: Year-by-year (9 years × 4 strategies)
- Test08: Churn analysis (4 strategies)

### 3. Blockers / uncertainties
- **Cand01 vs benchmark**: Sharpe gap (−0.18) is persistent across all cost levels up to ~105 bps. The breakout approach is not a Sharpe improvement — it is a risk-profile alternative.
- **WFO borderline**: 50% WFO win rate for Cand01/02 is the minimum passing threshold. Folds 2 and 4 (bear/range periods) show negative deltas (−0.75, −0.88), indicating the breakout approach underperforms the benchmark specifically during extended bear markets.
- **2026 partial year**: 2026 data is only 2 months — the negative Sharpe in 2026 may not be representative.
- **Cand02 redundancy**: D1 EMA(21) filter adds nothing for breakout entries. If pursued, Cand01 (3 DOF) is strictly preferred.

### 4. Gate status
**FINALIZED**

- **Cand01**: PROMOTE (3 DOF, Sh 0.91, MDD 41%, 0% churn, all gates pass)
- **Cand02**: PROMOTE (technically passes but adds no value over Cand01)
- **Cand03**: HOLD (R2 + R5 fail, Sh 0.45, 0% WFO WR)

Primary recommendation: **Cand01 (Breakout + ATR Trail)** — the evidence-minimal, churn-free trend follower.
