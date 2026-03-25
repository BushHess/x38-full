# Comprehensive Report: 5 Candidate Strategies — Re-validation 2026-03-17

> **Date**: 2026-03-17 (vocabulary reform applied 2026-03-17)
> **Scope**: Full re-run of all 5 strategies that passed their respective validation gates.
> **Baseline**: E0 (vtrend, slow=120, trail=3.0, VDO=0.0, harsh 50 bps RT)
> **Data**: `bars_btcusdt_2016_now_h1_4h_1d.csv` (2017-08 → 2026-02, H4+D1)
>
> **Vocabulary note**: Production strategies use PROMOTE/HOLD/REJECT (from `decision.json`).
> Research strategies use SCREEN_PASS/SCREEN_FAIL (from standalone benchmarks).
> These verdicts are NOT comparable — different gate systems, WFO designs, and statistical tests.
> See `STRATEGY_STATUS_MATRIX.md § Verdict Vocabulary Policy` for details.

---

## Executive Summary

| # | Strategy | Authority | Type | Verdict | Sharpe | CAGR% | MDD% | Trades | WFO | Key Gate |
|---|----------|-----------|------|---------|--------|-------|------|--------|-----|----------|
| 1 | **E0_ema21D1** | Production | standalone | **HOLD** | 1.3536 | 56.62% | 40.01% | 174 | 5/8, Wilcoxon p=0.191 | WFO FAIL |
| 2 | **E5_ema21D1** | Production | standalone | **HOLD** | 1.4545 | 61.60% | 40.97% | 188 | 5/8, Wilcoxon p=0.125 | WFO FAIL |
| 3 | **X14 Design D** | Research | overlay (E0) | **SCREEN_PASS_D** | 1.5300 | 70.67% | 35.87% | 148 | 3/4 (75%), 6/6 gates | All PASS |
| 4 | **X18 α=50%** | Research | overlay (E0) | **SCREEN_PASS** | 1.5479 | 71.89% | 36.92% | 145 | 3/4 (75%), 6/6 gates | All PASS |
| 5 | **X28 Cand01** | Research | from-scratch | **SCREEN_PASS** | 1.251 | 41.7% | 52.0% | 39 | 3/4 (75%), 9/9 gates | All PASS |

**All verdicts CONFIRMED — no changes from prior runs.**

---

## 1. E0_ema21D1 (vtrend_ema21_d1) — HOLD

**Pipeline**: Full validation (19 suites, 7 gates, 2000 bootstrap paths)
**Output**: `results/full_eval_e0_ema21d1_20260317/`

### Gate Results
| Gate | Status | Detail |
|------|--------|--------|
| lookahead | PASS | Zero violations |
| data_integrity | PASS | |
| backtest | PASS | harsh ΔScore = +13.60 |
| cost_sweep | PASS | |
| invariants | PASS | |
| churn_metrics | PASS | |
| regime | INFO | |
| **wfo** | **FAIL** | Wilcoxon p=0.191 > α=0.10, CI crosses zero |
| bootstrap | INFO | P(candidate better)=94.1% |
| holdout | PASS | harsh ΔScore = +2.17 |
| selection_bias | INFO | PSR=1.000, DSR robust |
| trade_level | INFO | |
| dd_episodes | INFO | |

### Full-Sample Metrics (harsh, 50 bps RT)
- Sharpe: 1.3536 (baseline E0: 1.2653)
- CAGR: 56.62% (E0: 52.04%)
- MDD: 40.01% (E0: 41.61%)
- Trades: 174, Win rate: 40.23%
- Avg exposure: 45.51%

### Holdout (harsh)
- Candidate Sharpe: 1.1514, Baseline: 1.1189, Δ=+0.0325
- Candidate MDD: 18.67%, Baseline: 19.13%

### WFO Detail
- Win rate: 5/8 (62.5%), median ΔScore=+6.01
- Wilcoxon p=0.191 → **underresolved** (insufficient OOS power)

---

## 2. E5_ema21D1 (vtrend_e5_ema21_d1) — HOLD [PRIMARY]

**Pipeline**: Full validation (19 suites, 7 gates, 2000 bootstrap paths)
**Output**: `results/full_eval_e5_ema21d1_20260317/`

### Gate Results
| Gate | Status | Detail |
|------|--------|--------|
| lookahead | PASS | Zero violations |
| data_integrity | PASS | |
| backtest | PASS | harsh ΔScore = +26.53 |
| cost_sweep | PASS | |
| invariants | PASS | |
| churn_metrics | PASS | |
| regime | INFO | |
| **wfo** | **FAIL** | Wilcoxon p=0.125 > α=0.10, CI crosses zero |
| bootstrap | INFO | P(candidate better)=97.2% |
| holdout | PASS | harsh ΔScore = +5.58 |
| selection_bias | INFO | PSR=1.000, DSR robust |
| trade_level | INFO | |
| dd_episodes | INFO | |

### Full-Sample Metrics (harsh, 50 bps RT)
- Sharpe: 1.4545 (baseline E0: 1.2653), **Δ=+0.1892**
- CAGR: 61.60% (E0: 52.04%), **Δ=+9.56pp**
- MDD: 40.97% (E0: 41.61%), **Δ=-0.64pp**
- Trades: 188, Win rate: 42.02%
- Avg exposure: 44.48%

### Holdout (harsh)
- Candidate Sharpe: 1.1618, Baseline: 1.1189, Δ=+0.0429
- Candidate MDD: 15.62%, Baseline: 19.13%, **Δ=-3.51pp**

### WFO Detail
- Win rate: 5/8 (62.5%), median ΔScore=+12.98
- Wilcoxon p=0.125 → **underresolved** (insufficient OOS power, not negative-confirmed)

### Bootstrap (trade-level, 2000 paths)
- P(E5 > E0 Sharpe) = 97.2%
- CI: [-0.006, +0.398], observed Δ=+0.189

---

## 3. X14 Design D — SCREEN_PASS_D (Churn Filter, Research Authority)

**Pipeline**: Research benchmark (6 gates, 500 VCBB bootstrap paths) — NOT production pipeline
**Output**: `research/x14/x14_results.json`, `x14_*.csv`
**Runtime**: 206s

### Gate Results
| Gate | Threshold | Result | Status |
|------|-----------|--------|--------|
| G0: T0 d_sharpe > 0 | >0 | +0.158 | **PASS** |
| G1: T1 WFO ≥ 3/4 | ≥75% | 75% (3/4) | **PASS** |
| G2: T2 P(d_sharpe>0) > 60% | >60% | 66.2% | **PASS** |
| G3: T2 median d_mdd ≤ +5pp | ≤+5pp | +2.45pp | **PASS** |
| G4: T3 ≤ 2/6 neg jackknife | ≤2 | 0/6 neg | **PASS** |
| G5: T4 PSR > 0.95 | >0.95 | 1.000 | **PASS** |

### Metrics (E0 + Design D filter, harsh)
- Sharpe: 1.5300 (+0.158 vs E0), CAGR: 70.67%, MDD: 35.87%
- Trades: 148, Avg hold: 53.9 bars
- Trail suppressions: 594 (model-based logistic filter)

### Key Numbers
- Bootstrap d_sharpe: median +0.068, CI [-0.209, +0.432]
- Jackknife: all 6 years positive (mean d=+0.123)
- Captures 11% of oracle ceiling (+0.845 Sharpe)

---

## 4. X18 α-Percentile Static Mask — SCREEN_PASS (α=50%, Research Authority)

**Pipeline**: Research benchmark (6 gates, 500 VCBB bootstrap paths) — NOT production pipeline
**Output**: `research/x18/x18_results.json`, `x18_*.csv`
**Runtime**: 32s

### Gate Results
| Gate | Threshold | Result | Status |
|------|-----------|--------|--------|
| G0: T0 Q5 median ΔU > 0 | >0 | +0.00126 | **PASS** |
| G1: T1 WFO ≥ 3/4 | ≥75% | 75% (3/4) | **PASS** |
| G2: T2 P(d_sharpe>0) > 60% | >60% | 63.4% | **PASS** |
| G3: T2 median d_mdd ≤ +5pp | ≤+5pp | -0.23pp | **PASS** |
| G4: T3 ≤ 2/6 neg jackknife | ≤2 | 0/6 neg | **PASS** |
| G5: T4 PSR > 0.95 | >0.95 | 1.000 | **PASS** |

### Metrics (E0 + X18 α=50% mask, harsh)
- Sharpe: 1.5479 (+0.176 vs E0), CAGR: 71.89%, MDD: 36.92%
- Trades: 145, Avg hold: 55.2 bars
- Trail suppressions: 673

### WFO Detail
- Fold 1: d=+0.191 WIN, Fold 2: d=+0.142 WIN, Fold 3: d=-0.113 LOSE, Fold 4: d=+0.311 WIN
- Consensus α=50% (selected by nested WFO)

### Comparison Table
| Strategy | Sharpe | CAGR% | MDD% | Trades |
|----------|--------|-------|------|--------|
| E0 | 1.372 | 57.7% | 40.0% | 189 |
| **X18 (α=50%)** | **1.548** | **71.9%** | **36.9%** | 145 |
| X14_D | 1.428 | 64.0% | 36.7% | 133 |

**Note**: X18 consensus α changed from 40% to 50% in this run (nested WFO selects α per fold).

---

## 5. X28 Cand01 — SCREEN_PASS (From-Scratch Discovery, Research Authority)

**Pipeline**: Phase 7 validation (9 gates, 2000 bootstrap paths, 4-fold WFO) — NOT production pipeline
**Output**: `research/x28/tables/`, `research/x28/figures/`
**Runtime**: 7s

### Gate Results (Cand01)
| Gate | Result | Status |
|------|--------|--------|
| G1: Sharpe > 0 | 1.251 | **PASS** |
| G2: Sharpe ≥ 0.80×bench | 1.251 ≥ 0.655 | **PASS** |
| G3: MDD ≤ 75% | 52.0% | **PASS** |
| G4: Trades ≥ 15 | 39 | **PASS** |
| G5: WFO ≥ 50% | 75% (3/4) | **PASS** |
| G6: Bootstrap ≥ 70% | 85.8% | **PASS** |
| G7: JK ≤ 1 neg | 0 neg | **PASS** |
| G8: No catastrophe | 0 years < -30% | **PASS** |
| G9: Phase 5 HC | all PASS | **PASS** |

### Cand01 Metrics (EMA(20,90) cross + 8% fixed trail + D1 EMA(50), harsh)
- Sharpe: 1.251, CAGR: 41.7%, MDD: 52.0%
- Trades: 39, Win rate: 46.2%, PF: 3.78
- Avg hold: 124.3 bars, Exposure: 25.8%

### All Candidates
| Candidate | Sharpe | CAGR% | MDD% | Trades | WFO | Bootstrap P(Δ>0) | Verdict |
|-----------|--------|-------|------|--------|-----|-------------------|---------|
| **Cand01** | **1.251** | 41.7% | 52.0% | 39 | 75% | 85.8% | **PROMOTE** |
| Cand02 | 1.099 | 32.1% | 40.3% | 49 | 75% | 77.2% | PROMOTE |
| Cand03 | 0.888 | 36.9% | 45.0% | 110 | 50% | 60.2% | PROMOTE |
| Benchmark | 0.819 | 31.7% | 39.9% | 108 | — | — | baseline |

**Note**: All Cand01-03 < E5_ema21D1 (Sharpe 1.455) on ALL major metrics. Confirms E5_ema21D1 superiority.

---

## Cross-Strategy Comparison (harsh, 50 bps RT)

| Strategy | Authority | Type | Sharpe | CAGR% | MDD% | Trades | WFO win% | Wilcoxon p | Boot P(>E0) | Verdict |
|----------|-----------|------|--------|-------|------|--------|----------|------------|-------------|---------|
| E0 (baseline) | Production | baseline | 1.265 | 52.0% | 41.6% | 192 | — | — | — | baseline |
| E0_ema21D1 | Production | standalone | 1.354 | 56.6% | 40.0% | 174 | 62.5% | 0.191 | 94.1% | **HOLD** |
| **E5_ema21D1** | **Production** | **standalone** | **1.455** | **61.6%** | **41.0%** | **188** | **62.5%** | **0.125** | **97.2%** | **HOLD** |
| X14_D (+E0) | Research | overlay | 1.530 | 70.7% | 35.9% | 148 | 75% | — | 66.2% | **SCREEN_PASS_D** |
| X18 α=50% (+E0) | Research | overlay | 1.548 | 71.9% | 36.9% | 145 | 75% | — | 63.4% | **SCREEN_PASS** |
| X28 Cand01 | Research | from-scratch | 1.251 | 41.7% | 52.0% | 39 | 75% | — | 85.8% | **SCREEN_PASS** |

**⚠ Verdicts are NOT directly comparable across authority levels.** Production HOLD (Wilcoxon 8-window, hard gates) ≠ Research SCREEN_PASS (win-rate 4-fold, lenient gates).

---

## Key Observations

1. **E5_ema21D1 remains PRIMARY** — highest absolute Sharpe among production strategies (1.455), bootstrap P(>E0)=97.2%, but WFO underresolved (p=0.125)
2. **E0_ema21D1 weaker** — Wilcoxon p=0.191 (worse than E5's 0.125), lower Sharpe (+0.089 vs E0)
3. **X14_D and X18 are churn filters ON TOP OF E0** — overlays, not standalone strategies. They improve E0 when cost >35 bps. SCREEN_PASS under research gates only.
4. **At measured cost (17 bps RT)**: churn filters HURT (X22 crossover analysis). Deploy E5_ema21D1 without overlays
5. **X28 Cand01 confirms VTREND superiority** — from-scratch discovery peaks at Sharpe 1.251, well below E5_ema21D1's 1.455
6. **Verdicts not comparable across authority levels** — Production HOLD (Wilcoxon 8-window p<0.10) is stricter than Research SCREEN_PASS (win-rate ≥75% on 4 folds). A SCREEN_PASS does NOT imply the strategy would pass production validation.

---

## Production Recommendation (unchanged from X33)

- **Deploy**: E5_ema21D1 without overlays at measured 17 bps RT cost
- **Arm in code**: X18 (α=50%), activate if live cost exceeds 35 bps RT
- **Monitor**: WFO underresolved status — more OOS data may resolve in future

---

*Generated: 2026-03-17 | Vocabulary reform: 2026-03-17 | Pipeline: validation v10 + research benchmarks | Bootstrap: 2000 (validation) / 500 (research)*
