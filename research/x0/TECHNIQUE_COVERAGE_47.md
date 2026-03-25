# E0+EMA1D21 (X0) — 47-Technique Coverage Report

**Date**: 2026-03-08
**Strategy**: E0+EMA1D21 (vtrend_ema21_d1) — EMA crossover + ATR trail + VDO + D1 EMA(21) regime
**Baseline**: E0 (vtrend)
**Verdict**: PROMOTE (decision.json, 0 failures, 0 warnings)

---

## TIER 1: Validation Framework (17 suites)

Run via `validate_strategy.py --suite all` on 2026-03-05.
Config: `results/parity_20260305/eval_ema21d1_vs_e0/run_meta.json`

| # | Technique | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Lookahead check | DONE | `lookahead_check.txt` — PASS |
| 2 | Data integrity | DONE | `data_integrity.json` — PASS |
| 3 | Backtest (3 scenarios) | DONE | `full_backtest_summary.csv` — Sharpe 1.336 harsh |
| 4 | Cost sweep (0-100 bps) | DONE | `cost_sweep.csv` — wins ALL 6 levels vs E0 |
| 5 | Invariants | DONE | `invariant_violations.csv` — PASS |
| 6 | Churn metrics | DONE | `churn_metrics.csv` |
| 7 | Regime decomposition | DONE | `regime_decomposition.csv` + `.json` |
| 8 | WFO | DONE | `wfo_summary.json` — 6/8 (75%) PASS |
| 9 | Bootstrap | DONE | `bootstrap_paired_test.csv` — P=0.836 |
| 10 | Subsampling | DONE | `subsampling_summary.json` |
| 11 | Sensitivity | DONE | `sensitivity_grid.csv` + `sensitivity_detail.json` |
| 12 | Holdout | DONE | `final_holdout_metrics.csv` — delta +5.98 |
| 13 | Selection bias / DSR | DONE | `selection_bias.json` — DSR robust |
| 14 | Trade level | DONE | `matched_trades.csv` + `bootstrap_return_diff.json` |
| 15 | DD episodes | DONE | `dd_episodes_summary.json` |
| 16 | Overlay | DONE | `overlay_test: true` in config |
| 17 | Regression guard | SKIP | No golden snapshot for new candidate |

**Tier 1: 16/17 done, 1 skipped (by design)**

All result files: `results/parity_20260305/eval_ema21d1_vs_e0/results/`

---

## TIER 2: Research Studies (T1-T7)

Via `research/parity_eval.py` — EMA21_D1 included as 1 of 6 strategies.
Results: `research/results/parity_eval/parity_eval_results.json`

| # | Technique | Status | Evidence |
|---|-----------|--------|----------|
| 18 | Full backtest 3 scenarios | DONE | parity_eval T1 |
| 19 | Permutation test 10K | DONE | p=0.0002 |
| 20 | Timescale robustness 16 TS | DONE | 16/16 positive Sharpe |
| 21 | Bootstrap VCBB 500 paths | DONE | 500 paths x 16 TS |
| 22 | Postmortem DD episodes | DONE | T5 |
| 23 | Parameter sensitivity sweep | DONE | T6 |
| 24 | Cost study | DONE | T7 |

**Tier 2: 7/7 done**

---

## TIER 3: Comparative / Structural Analysis

E0+EMA1D21 included in 6s scripts (`research/eval_vtrend_latch_20260305/`) AND 7s scripts (`research/eval_e5_ema1d21/`).

| # | Technique | Status | Evidence |
|---|-----------|--------|----------|
| 25 | Factorial sizing decomposition | DONE | `factorial_7s_summary.csv` |
| 26 | Matched-risk frontier | DONE | `frontier_7s_grid.csv` |
| 27 | Statistical robustness + Holm | DONE | `holm_7s_pvalues.json` |
| 28 | Calendar slice | DONE | `calendar_slice_7s.csv` |
| 29 | Rolling window | DONE | `rolling_window_7s.csv` |
| 30 | Start-date sensitivity | DONE | `start_date_7s.csv` |
| 31 | Concordance | DONE | `concordance_7s.csv` |
| 32 | Risk budget | DONE | `risk_budget_7s.csv` |
| 33 | Signal comparison binary | DONE | `signal_comparison_7s_binary100.csv` |
| 34 | Matched MDD | DONE | `matched_mdd_7s.csv` |
| 35 | Linearity check | DONE | `linearity_7s_check.json` |
| 36 | Multiple comparison / Bonferroni | PARTIAL | Holm in `holm_7s_pvalues.json`; standalone `multiple_comparison.py` only covers E0 |
| 37 | Effective DOF / Binomial | NOT DONE | `binomial_correction.py` only covers E0 |
| 38 | True WFO + Permutation | NOT DONE | `true_wfo_compare.py` only covers VTREND vs V8 |
| 39 | Cross-check vs VTrend engine | NOT DONE | `cross_check_vs_vtrend.py` only covers E0 |
| 40 | Mathematical invariant tests | PARTIAL | Tier 1 invariants PASS; standalone `invariant_tests.py` (17 tests) only covers E0 |
| 41 | VCBB vs Uniform bootstrap | N/A | Infrastructure validation, strategy-agnostic |
| 42 | Multi-coin validation | NOT DONE | 4 multicoin scripts only cover E0/E5 base |
| 43 | Exit family study | NOT DONE | `exit_family_study.py` only covers E0-E5 exit variants |
| 44 | Resolution sweep | NOT DONE | `resolution_sweep.py` only covers E0 |

**Tier 3: 11/20 done, 2 partial, 5 not done, 1 N/A (infrastructure), 1 skip**

Artifact locations:
- 6s: `research/eval_vtrend_latch_20260305/artifacts/*_6s.*`
- 7s: `research/eval_e5_ema1d21/artifacts/*_7s.*`

---

## TIER 4: Trade Anatomy (8 techniques)

Covered via TWO independent sources:
1. Standalone `research/trade_profile_8x5.py` → `results/trade_profile_8x5/E0_plus_EMA1D21/`
2. Embedded in `research/eval_e5_ema1d21/src/run_tier2_tier4.py`

| # | Technique | Status | Evidence |
|---|-----------|--------|----------|
| 45a | Win rate / avg W/L / PF | DONE | `profile.json` + Report section 4.1 |
| 45b | Streaks | DONE | `profile.json` + Report section 4.2 |
| 45c | Holding time distribution | DONE | `profile.json` + Report section 4.3 |
| 45d | MFE / MAE | DONE | `mfe_mae_per_trade.csv` + Report section 4.4 |
| 45e | Exit reason profitability | DONE | `exit_reason_detail.json` + Report section 4.5 |
| 45f | Payoff concentration | DONE | Report section 4.6 |
| 45g | Top-N jackknife | DONE | Report section 4.7 |
| 45h | Fat-tail statistics | DONE | Report section 4.8 |

**Tier 4: 8/8 done**

---

## Audit & Infrastructure (46-48)

| # | Technique | Status | Notes |
|---|-----------|--------|-------|
| 46 | Full system audit | N/A | Infrastructure-level, strategy-agnostic |
| 47 | DSR module unit tests | N/A | Infrastructure-level, 19/19 pass |
| 48 | Bug audit & fix | N/A | Infrastructure-level, already completed |

---

## Summary

| Tier | Done | Partial | Not Done | Skip/N/A | Total |
|------|:----:|:-------:|:--------:|:--------:|:-----:|
| Tier 1 (Validation) | 16 | 0 | 0 | 1 | 17 |
| Tier 2 (Research T1-T7) | 7 | 0 | 0 | 0 | 7 |
| Tier 3 (Comparative) | 11 | 2 | 5 | 2 | 20 |
| Tier 4 (Trade Anatomy) | 8 | 0 | 0 | 0 | 8 |
| Audit | 0 | 0 | 0 | 3 | 3 |
| **Total** | **42** | **2** | **5** | **6** | **55** |

**Coverage: 42/47 applicable techniques done (89%)**

## Gaps

| # | Technique | Risk |
|---|-----------|------|
| 37 | Effective DOF / Binomial | May overstate significance due to timescale correlation |
| 38 | True WFO + Permutation | WFO already done (6/8), but no permutation-on-WFO |
| 39 | Cross-check vs VTrend engine | No bit-identical indicator verification |
| 42 | Multi-coin validation | Unknown if E0+EMA1D21 generalizes beyond BTC |
| 44 | Resolution sweep | H4 assumed optimal (inherited from E0 proof) |

Note: gaps #37-39, #42, #44 are identical to E5+EMA1D21 gaps — all standalone research scripts were written for E0 baseline only.

## Key Result Files

| Source | Path |
|--------|------|
| Tier 1 validation | `results/parity_20260305/eval_ema21d1_vs_e0/` |
| Tier 2 parity eval | `research/results/parity_eval/` |
| Tier 3 (6s) | `research/eval_vtrend_latch_20260305/artifacts/*_6s.*` |
| Tier 3 (7s) | `research/eval_e5_ema1d21/artifacts/*_7s.*` |
| Tier 4 trade profile | `results/trade_profile_8x5/E0_plus_EMA1D21/` |
| Tier 4 research eval | `research/eval_e5_ema1d21/artifacts/tier2_tier4_results.json` |
| Fragility audit | `research/fragility_audit_20260306/artifacts/step*/candidates/E0_plus_EMA1D21/` |
| Decision | `results/parity_20260305/eval_ema21d1_vs_e0/reports/decision.json` |
