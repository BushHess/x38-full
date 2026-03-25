# 47-Technique Coverage Index

**Date**: 2026-03-08
**Purpose**: Quick lookup for which strategies have been validated through which techniques.
**Master technique list**: 47 techniques across 4 tiers + 3 audit/infrastructure.

---

## Strategy Coverage Summary

| Strategy | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Total | Coverage | Report |
|----------|:------:|:------:|:------:|:------:|:-----:|:--------:|--------|
| **E0 (baseline)** | 17/17 | 7/7 | 20/20 | 8/8 | 52/52 | 100% | (baseline — all scripts written for E0) |
| **E0+EMA1D21 (X0)** | 16/17 | 7/7 | 13/20 | 8/8 | 44/52 | 85% | `research/x0/TECHNIQUE_COVERAGE_47.md` |
| **E5+EMA1D21** | 15/17 | 7/7 | 14/20 | 8/8 | 44/52 | 85% | `research/eval_e5_ema1d21/TECHNIQUE_COVERAGE_47.md` |
| **X2 (adaptive trail)** | 15/17* | 4/7* | 0/20 | 4/8* | 23/52 | 44% | `research/X2_X6_VALIDATION_REPORT.md` |
| **X6 (trail + BE)** | 15/17* | 4/7* | 0/20 | 4/8* | 23/52 | 44% | `research/X2_X6_VALIDATION_REPORT.md` |

*X2/X6 have partial Tier 2 (T1+T2+T3+T4 via benchmark.py) and partial Tier 4 (exit reasons, tier distribution). No Tier 3 comparative analysis.

---

## Gap Matrix (techniques NOT done per strategy)

| # | Technique | E0 | E0+EMA1D21 | E5+EMA1D21 | X2 | X6 |
|---|-----------|:--:|:----------:|:----------:|:--:|:--:|
| 11 | Sensitivity grid | Y | Y | **SKIP** | — | — |
| 17 | Regression guard | Y | **SKIP** | **SKIP** | — | — |
| 37 | Effective DOF / Binomial | Y | **NO** | **NO** | NO | NO |
| 38 | True WFO + Permutation | Y | **NO** | **NO** | NO | NO |
| 39 | Cross-check vs VTrend | Y | **NO** | **NO** | NO | NO |
| 42 | Multi-coin validation | Y | **NO** | **NO** | NO | NO |
| 43 | Exit family study | Y | **NO** | PARTIAL | NO | NO |
| 44 | Resolution sweep | Y | **NO** | **NO** | NO | NO |

SKIP = intentionally skipped (valid reason). NO = not yet run. PARTIAL = partially covered.

---

## Per-Technique Status (all strategies)

### TIER 1: Validation Framework (17 suites)

| # | Technique | E0 | E0+EMA1D21 | E5+EMA1D21 | X2 | X6 |
|---|-----------|:--:|:----------:|:----------:|:--:|:--:|
| 1 | Lookahead | Y | Y | Y | Y | Y |
| 2 | Data integrity | Y | Y | Y | Y | Y |
| 3 | Backtest (3 cost) | Y | Y | Y | Y | Y |
| 4 | Cost sweep | Y | Y | Y | — | — |
| 5 | Invariants | Y | Y | Y | Y | Y |
| 6 | Churn metrics | Y | Y | Y | — | — |
| 7 | Regime decomposition | Y | Y | Y | — | — |
| 8 | WFO | Y | Y (6/8) | Y (5/8) | — | — |
| 9 | Bootstrap | Y | Y | Y | Y | Y |
| 10 | Subsampling | Y | Y | Y | — | — |
| 11 | Sensitivity | Y | Y | SKIP | — | — |
| 12 | Holdout | Y | Y | Y | — | — |
| 13 | Selection bias / DSR | Y | Y | Y | — | — |
| 14 | Trade level | Y | Y | Y | — | — |
| 15 | DD episodes | Y | Y | Y | — | — |
| 16 | Overlay | Y | Y | Y | — | — |
| 17 | Regression guard | Y | SKIP | SKIP | — | — |

### TIER 2: Research Studies (T1-T7)

| # | Technique | E0 | E0+EMA1D21 | E5+EMA1D21 | X2 | X6 |
|---|-----------|:--:|:----------:|:----------:|:--:|:--:|
| 18 | Full backtest 3 scenarios | Y | Y | Y | Y | Y |
| 19 | Permutation test 10K | Y | Y | Y | — | — |
| 20 | Timescale robustness 16 TS | Y | Y | Y | — | — |
| 21 | Bootstrap VCBB 500 paths | Y | Y | Y | Y | Y |
| 22 | Postmortem DD episodes | Y | Y | Y | — | — |
| 23 | Param sensitivity sweep | Y | Y | Y | — | — |
| 24 | Cost study | Y | Y | Y | — | — |

### TIER 3: Comparative / Structural Analysis

| # | Technique | E0 | E0+EMA1D21 | E5+EMA1D21 | X2 | X6 |
|---|-----------|:--:|:----------:|:----------:|:--:|:--:|
| 25 | Factorial sizing | Y | Y | Y | — | — |
| 26 | Matched-risk frontier | Y | Y | Y | — | — |
| 27 | Robustness + Holm | Y | Y | Y | — | — |
| 28 | Calendar slice | Y | Y | Y | — | — |
| 29 | Rolling window | Y | Y | Y | — | — |
| 30 | Start-date sensitivity | Y | Y | Y | — | — |
| 31 | Concordance | Y | Y | Y | — | — |
| 32 | Risk budget | Y | Y | Y | — | — |
| 33 | Signal comparison | Y | Y | Y | — | — |
| 34 | Matched MDD | Y | Y | Y | — | — |
| 35 | Linearity check | Y | Y | Y | — | — |
| 36 | Multiple comparison | Y | P | P | — | — |
| 37 | Effective DOF / Binomial | Y | — | — | — | — |
| 38 | True WFO + Permutation | Y | — | — | — | — |
| 39 | Cross-check vs VTrend | Y | — | — | — | — |
| 40 | Mathematical invariants | Y | P | P | — | — |
| 41 | VCBB vs Uniform | Y | N/A | N/A | N/A | N/A |
| 42 | Multi-coin validation | Y | — | — | — | — |
| 43 | Exit family study | Y | — | P | — | — |
| 44 | Resolution sweep | Y | — | — | — | — |

Legend: Y = done, P = partial, — = not done, SKIP = intentionally skipped, N/A = not applicable

### TIER 4: Trade Anatomy (8 techniques)

| # | Technique | E0 | E0+EMA1D21 | E5+EMA1D21 | X2 | X6 |
|---|-----------|:--:|:----------:|:----------:|:--:|:--:|
| 45a | Win rate / PF | Y | Y | Y | P | P |
| 45b | Streaks | Y | Y | Y | — | — |
| 45c | Holding time | Y | Y | Y | P | P |
| 45d | MFE / MAE | Y | Y | Y | — | — |
| 45e | Exit reason profitability | Y | Y | Y | Y | Y |
| 45f | Payoff concentration | Y | Y | Y | P | P |
| 45g | Top-N jackknife | Y | Y | Y | — | — |
| 45h | Fat-tail statistics | Y | Y | Y | — | — |

---

## Report Locations

| Strategy | Coverage Report | Evaluation Report | Validation Results |
|----------|----------------|-------------------|--------------------|
| E0 (baseline) | (all research scripts) | `research/results/COMPLETE_RESEARCH_REGISTRY.md` | `results/parity_20260305/eval_e0_vs_e0/` |
| E0+EMA1D21 (X0) | `research/x0/TECHNIQUE_COVERAGE_47.md` | `results/parity_20260305/PARITY_REPORT.md` | `results/parity_20260305/eval_ema21d1_vs_e0/` |
| E5+EMA1D21 | `research/eval_e5_ema1d21/TECHNIQUE_COVERAGE_47.md` | `results/parity_20260306/E5_PLUS_EMA1D21_EVALUATION_REPORT.md` | `results/parity_20260306/eval_e5_ema21d1_vs_e0/` |
| X2 | `research/X2_X6_VALIDATION_REPORT.md` | `research/x2/X2_EVALUATION_REPORT.md` | `research/x2/x2_results.json` |
| X6 | `research/X2_X6_VALIDATION_REPORT.md` | `research/x6/X6_EVALUATION_REPORT.md` | `research/x6/x6_results.json` |

## Fragility Audit (separate from 47 techniques)

All 3 promoted strategies covered in `research/fragility_audit_20260306/`:

| Strategy | Step 2 | Step 3 | Step 5 | Sign-off |
|----------|:------:|:------:|:------:|:--------:|
| E0+EMA1D21 | Y (11 files) | Y (8 files) | Y — GO_WITH_GUARDS (LT1) | Y |
| E5+EMA1D21 | Y (11 files) | Y (8 files) | Y — HOLD (all) | Y |
| SM | Y (11 files) | Y (8 files) | Y — GO (LT1/2) | Y |

---

## How to Use This Index

1. **Check coverage for a strategy**: Look at the Summary table for high-level numbers, then Per-Technique tables for details.
2. **Find gaps**: Gap Matrix shows all missing techniques per strategy.
3. **Locate artifacts**: Report Locations table links to detailed reports.
4. **Prioritize next work**: Focus on filling "—" entries in the Per-Technique tables. Highest-value gaps are #42 (multi-coin) and #37 (DOF correction) for promoted strategies.
