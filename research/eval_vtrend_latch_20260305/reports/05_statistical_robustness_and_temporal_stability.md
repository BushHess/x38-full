# Report 05 — Statistical Robustness + Temporal Stability Audit

**Date:** 2026-03-05
**Step:** 5 of N
**Author:** Claude (audit-grade research)
**Script:** `src/run_robustness.py`
**Tests:** `tests/test_robustness.py` — 17/17 pass
**Runtime:** 130.7 s (5000 bootstrap reps × 3 block lengths × 4 hypotheses + temporal analyses)

---

## 1. Objective of This Step

Quantify the statistical uncertainty around every key pairwise conclusion from Steps 3-4. Determine which findings are robust vs tentative vs unsupported. Test temporal stability. Decide whether LATCH's added complexity over SM is justified.

This is NOT a score-redesign step. It is purely an evidence-quality audit.

---

## 2. Inputs Used

| Source | File | Purpose |
|--------|------|---------|
| Step 3 | `artifacts/factorial_equity_curves.npz` | 16 equity curves (4 signals × 3 sizings + 4 native) |
| Step 3 | `artifacts/step3_master_results.json` | Native metadata (exposure, turnover, fee drag, MDD) |
| Step 4 | `artifacts/frontier_grid.csv` | 101-point frontiers for cross-check |
| Step 4 | `artifacts/pairwise_diagnostics.json` | Matched-risk point estimates |
| Data | `data/bars_btcusdt_2016_now_h1_4h_1d.csv` | BTC close prices for calendar context |
| Frozen | `artifacts/step5_preanalysis_plan.json` | Pre-analysis plan (frozen before results) |

---

## 3. Reports Read Confirmation

- `reports/00_setup_and_scope.md` — read in full
- `reports/01_strategy_and_engine_inventory.md` — read in full
- `reports/02_parity_and_signal_extraction.md` — read in full
- `reports/03_factorial_sizing_and_scoring_bias.md` — read in full
- `reports/04_matched_risk_frontier.md` — read in full

---

## 4. Assumption Delta

### Assumptions from Step 4 that REMAIN VALID

1. **External cash-scaling preserves Sharpe** — confirmed by linearity check (Step 4) and bootstrap (Sharpe difference is stable across block lengths).
2. **Equity curves start at 1.0, same data period (2017-08 → 2026-02, 18662 H4 bars)** — confirmed.
3. **Cost is embedded in equity curves at 25 bps one-way** — carried forward.
4. **Engine/indicator/signal equivalence** (Step 2) — not re-tested, carried forward.

### Assumptions that NEED CORRECTION

5. **"E0 has a genuine signal-quality edge" (Step 3)** — Point estimate is real (+0.14 Sharpe at EntryVol_12), but **the bootstrap 95% CI includes zero** at all three block lengths. The edge is DIRECTIONALLY consistent (P(>0)≈73-75%) but NOT statistically distinguishable from noise. **CORRECTED: The signal-quality edge is TENTATIVE, not established.**

6. **"At matched MDD, LATCH dominates E0" (Step 4)** — Point estimate is real (+2.2 pp CAGR at 5% MDD, +4.6 pp at 10% MDD), but **the bootstrap 95% CI includes zero** at all block lengths. Direction is consistent (P(>0)≈75-77%) but not significant. **CORRECTED: The low-risk LATCH advantage is TENTATIVE, not established.**

7. **"Crossover at ~20% MDD" (Step 4)** — Rolling-window analysis shows the crossover varies from 3% to 26.5% across 24/36-month windows. The 20% figure is not stable. **CORRECTED: The crossover budget is highly variable, not a fixed threshold.**

### Assumptions STILL UNRESOLVED

8. **Whether 8.5 years of BTC data provides sufficient power to distinguish Sharpe differences of 0.1-0.3** — the bootstrap CIs suggest it does not. This is a fundamental limitation, not a methodological failure.

### Assumptions THIS STEP RESOLVES

9. **Statistical significance of all key pairwise differences** — RESOLVED (see Sections 7-9).
10. **Temporal stability of the two-regime model** — RESOLVED (see Section 11).
11. **Start-date sensitivity** — RESOLVED (see Section 10).
12. **LATCH complexity premium over SM** — RESOLVED (see Section 9).

### Working Conclusions from Steps 3-4 (Status After This Step)

| Conclusion | Step 3-4 Status | Step 5 Status |
|-----------|:--------------:|:-------------:|
| E0 signal-quality edge at identical sizing | Established | **TENTATIVE** — CI includes 0 |
| LATCH beats scaled E0 at low-risk budgets | Established | **TENTATIVE** — CI includes 0 |
| E0 is the only high-risk option | Established | **ROBUST** — structural property |
| SM ≈ LATCH in trade behavior and Sharpe | Established | **ROBUST** — confirmed |

---

## 5. Frozen Pre-Analysis Plan

Saved as `artifacts/step5_preanalysis_plan.json` **before** any results were computed.

### Primary hypotheses (frozen)

| ID | Claim | Effect size | Point est. |
|----|-------|-------------|:----------:|
| H1 | E0 has higher Sharpe than LATCH at EntryVol_12 | Sharpe(E0) - Sharpe(LATCH) | +0.137 |
| H2 | LATCH has higher CAGR than E0 at matched 5% MDD | CAGR(LATCH) - CAGR(E0) | +2.21 pp |
| H3 | LATCH has higher CAGR than E0 at matched 10% MDD | CAGR(LATCH) - CAGR(E0) | +4.59 pp |
| H4 | LATCH does NOT robustly beat SM (complexity test) | Sharpe(LATCH) - Sharpe(SM) | +0.003 |

### Method

- Circular block bootstrap, paired return streams
- Block lengths: 42, 126, 252 bars
- 5000 replications per test
- Seed: 20260305
- Holm adjustment for 4 primary hypotheses
- Evidence thresholds: ROBUST / TENTATIVE / UNSUPPORTED

---

## 6. Bootstrap Methodology

**Circular block bootstrap**: preserves serial dependence by sampling contiguous blocks. Paired — same bootstrap indices applied to both strategy return streams simultaneously, preserving their cross-sectional dependence.

**Three block lengths** test sensitivity to assumed serial dependence:
- 42 bars ≈ 1 week (short blocks, more resampling variation)
- 126 bars ≈ 3 weeks (medium)
- 252 bars ≈ 6 weeks (long blocks, preserves more structure)

**Matched-MDD recomputation**: For H2/H3, the k-scaling factor is recomputed inside each bootstrap sample via binary search. This correctly propagates uncertainty in the MDD estimate rather than freezing the original-sample scaling.

**Saturation handling**: If a bootstrap sample's native MDD is below the target budget, k is capped at 1.0 (no leverage). Saturation frequency is reported separately.

---

## 7. Bootstrap Results: Equal-Sizing E0 vs LATCH (H1)

**Test**: Sharpe(E0_EntryVol_12) - Sharpe(LATCH_EntryVol_12)

| Block | Mean | Median | 95% CI | P(>0) | CI excl 0 |
|:-----:|:----:|:------:|:------:|:-----:|:---------:|
| 42 | +0.132 | +0.131 | [-0.277, +0.545] | 73.2% | NO |
| 126 | +0.134 | +0.133 | [-0.264, +0.542] | 74.0% | NO |
| 252 | +0.137 | +0.138 | [-0.271, +0.544] | 75.0% | NO |

**Holm-adjusted p-value**: 1.000

### Interpretation

The E0 signal-quality edge is **directionally consistent** — 73-75% of bootstrap samples show E0 > LATCH. The mean effect size (+0.13 Sharpe) is practically meaningful. However, the 95% CI is wide [-0.27, +0.54] and comfortably includes zero.

**Verdict: TENTATIVE.** E0 most likely has a signal-quality edge, but 8.5 years of H4 data does not provide enough statistical power to confirm it. The CI width (0.82 Sharpe) reflects the fundamental challenge of distinguishing Sharpe ratios with limited data.

### Secondary diagnostics

The bootstrap is insensitive to block length — all three produce nearly identical CIs. This suggests the result is not an artifact of the serial dependence structure.

---

## 8. Bootstrap Results: Matched-Risk E0 vs LATCH (H2, H3)

### H2: LATCH CAGR advantage at 5% MDD budget

| Block | Mean | 95% CI | P(>0) | CI excl 0 | Sat E0 | Sat LATCH |
|:-----:|:----:|:------:|:-----:|:---------:|:------:|:---------:|
| 42 | +1.32 pp | [-2.26, +5.67] pp | 76.5% | NO | 0.0% | 0.0% |
| 126 | +1.22 pp | [-2.25, +5.55] pp | 76.6% | NO | 0.0% | 0.0% |
| 252 | +1.24 pp | [-2.17, +5.63] pp | 75.3% | NO | 0.0% | 0.0% |

### H3: LATCH CAGR advantage at 10% MDD budget

| Block | Mean | 95% CI | P(>0) | CI excl 0 | Sat E0 | Sat LATCH |
|:-----:|:----:|:------:|:-----:|:---------:|:------:|:---------:|
| 42 | +2.29 pp | [-4.89, +9.63] pp | 74.9% | NO | 0.0% | 21.6% |
| 126 | +2.25 pp | [-4.81, +9.73] pp | 76.0% | NO | 0.0% | 16.7% |
| 252 | +2.29 pp | [-4.58, +9.92] pp | 75.1% | NO | 0.0% | 16.2% |

**Holm-adjusted p-values**: H2: 1.000, H3: 1.000

### Interpretation

LATCH's low-risk advantage is **directionally consistent** (75-77% of samples favor LATCH), with practically meaningful mean effects (+1.2 pp at 5% MDD, +2.3 pp at 10% MDD). But the 95% CIs are wide and include zero.

**Saturation note**: At 10% MDD, 17-22% of bootstrap samples have LATCH saturating (native MDD < 10%), meaning LATCH cannot fully use the 10% budget. This reduces LATCH's effective advantage in those samples. E0 never saturates (its native MDD of 63% always exceeds 10%).

**Verdict: TENTATIVE.** The direction is consistent, but the difference is not statistically significant. The saturation asymmetry (only LATCH saturates) is a structural feature, not a noise artifact.

---

## 9. Bootstrap Results: LATCH vs SM Complexity Premium (H4)

### Native Sharpe difference

| Block | Mean | 95% CI | P(>0) | CI excl 0 |
|:-----:|:----:|:------:|:-----:|:---------:|
| 42 | +0.003 | [-0.051, +0.060] | 53.4% | NO |
| 126 | +0.003 | [-0.048, +0.055] | 54.7% | NO |
| 252 | +0.003 | [-0.043, +0.056] | 54.4% | NO |

### Matched-budget CAGR differences (secondary, block=126)

| Budget | Mean CAGR diff | 95% CI | P(>0) |
|:------:|:--------------:|:------:|:-----:|
| 5% | +0.10 pp | [-0.41, +0.71] pp | 67.9% |
| 10% | -0.11 pp | [-3.42, +1.15] pp | 59.6% |

**Holm-adjusted p-value**: 1.000

### Complexity-Premium Decision

LATCH's edge over SM is **effectively zero**:
- Sharpe difference: +0.003 (point estimate)
- 95% CI: [-0.048, +0.055] — centered on zero
- P(>0): 54% — essentially a coin flip
- Block-length sensitivity: none (all three identical)
- Trade behavior: 99.8% concordant (Step 2)
- Parameter difference: 15 vs 8 params

The pre-analysis plan required BOTH statistical support (CI excludes 0) AND practical materiality (Sharpe diff > 0.05). Neither criterion is met.

**Verdict: NOT_JUSTIFIED_BY_CURRENT_EVIDENCE.** SM achieves essentially the same performance as LATCH with roughly half the parameters. The additional complexity of LATCH (hysteretic regime, vol_floor, 3-state machine) provides no measurable benefit.

---

## 10. Start-Date Sensitivity

| Start | E0 Sharpe | SM Sharpe | LATCH Sharpe | Winner 5% MDD | Winner 10% MDD | EV12 Edge |
|:-----:|:---------:|:---------:|:-----------:|:-------------:|:--------------:|:---------:|
| 2017-08 | 1.077 | 1.312 | 1.315 | LATCH | LATCH | +0.137 |
| 2019-01 | 1.265 | 1.445 | 1.443 | LATCH | LATCH | +0.151 |
| 2020-01 | 1.158 | 1.237 | 1.226 | **E0** | **E0** | +0.092 |

### Key finding

Starting from 2020-01, the conclusions **reverse**: E0 wins at both 5% and 10% MDD budgets. This is because the 2020-01 start includes the 2020-2021 bull run where E0's high-exposure, trend-following approach was exceptionally profitable, and omits the 2018-2019 period where LATCH's lower exposure was advantageous.

The 2017-08 and 2019-01 starts agree with each other (LATCH wins at low-risk budgets). The 2020-01 start disagrees. This means the 2018 bear market is important for the LATCH advantage — it contributes materially to LATCH's risk-adjusted edge.

**Verdict: TENTATIVE start-date independence.** Conclusions are sensitive to whether the 2018 bear market is included.

---

## 11. Rolling-Window Stability

### 24-month windows (14 windows)

| Metric | Count | Fraction |
|--------|------:|:--------:|
| LATCH wins at 5% MDD | 9/14 | 64% |
| LATCH wins at 10% MDD | 8/14 | 57% |
| LATCH beats SM Sharpe | 8/14 | 57% |
| Crossover identifiable | 11/14 | 79% |

**Crossover MDD**: median=10.0%, range=[3.0%, 20.5%]

### 36-month windows (12 windows)

| Metric | Count | Fraction |
|--------|------:|:--------:|
| LATCH wins at 5% MDD | 8/12 | 67% |
| LATCH wins at 10% MDD | 8/12 | 67% |
| LATCH beats SM Sharpe | 6/12 | 50% |
| Crossover identifiable | 12/12 | 100% |

**Crossover MDD**: median=12.0%, range=[5.5%, 26.5%]

### Interpretation

The "two-regime model" (LATCH dominates at low risk, E0 dominates at high risk) holds in a **majority** of windows but not overwhelmingly:
- LATCH wins at 5% MDD in 64-67% of windows
- LATCH wins at 10% MDD in 57-67% of windows

The crossover budget is **highly variable** — ranging from 3% to 26.5%. The Step 4 estimate of "~20%" is not a stable threshold; it shifts with market regime.

LATCH vs SM: essentially a coin flip (50-57% of windows favor LATCH).

**Verdict: TENTATIVE temporal stability.** The two-regime model is more often right than wrong, but not overwhelmingly so. The crossover is unstable.

---

## 12. Calendar-Slice Diagnostics

| Year | BTC | E0 Sharpe | SM Sharpe | LATCH Sharpe | Winner 10% | EV12 Edge |
|:----:|:---:|:---------:|:---------:|:-----------:|:----------:|:---------:|
| 2017 | +215% | 1.97 | 2.13 | 2.12 | E0 | +0.79 |
| 2018 | -72% | -0.93 | -1.03 | -0.98 | LATCH | -0.41 |
| 2019 | +95% | 1.83 | 2.46 | 2.48 | LATCH | +0.43 |
| 2020 | +300% | 2.66 | 2.97 | 2.93 | E0 | -0.06 |
| 2021 | +58% | 1.47 | 0.18 | 0.27 | E0 | +1.07 |
| 2022 | -65% | -1.00 | -1.31 | -1.31 | LATCH | +0.05 |
| 2023 | +156% | 1.17 | 2.29 | 2.23 | LATCH | -0.36 |
| 2024 | +121% | 1.42 | 1.33 | 1.35 | E0 | +0.41 |
| 2025 | -7% | 0.17 | 0.42 | 0.34 | LATCH | +0.19 |
| 2026 | -23% | -1.12 | 0.89 | 1.00 | LATCH | -2.30 |

### Patterns

1. **E0's signal-quality edge (EV12 column) varies wildly**: from -2.30 (2026) to +1.07 (2021). It is NOT consistent across years — E0 wins in some years, LATCH wins in others.

2. **E0 wins at 10% MDD in strong bull markets**: 2017, 2020, 2021, 2024. These are years where high-exposure trend following produces outsized returns.

3. **LATCH wins at 10% MDD in bear/sideways markets**: 2018, 2019, 2022, 2023, 2025, 2026. LATCH's conservative sizing protects in drawdowns.

4. **SM and LATCH track each other closely** in every year — further confirming the complexity premium is zero.

5. **No single year dominates the full-sample result** — the LATCH advantage at low-risk budgets comes from accumulating a modest edge across multiple bear/sideways years.

---

## 13. Resolution Status for S1-S7

| ID | Question | Status | Evidence | Conclusion |
|----|----------|:------:|----------|------------|
| S1 | E0's equal-sizing Sharpe edge statistically supported? | **UNSUPPORTED** | CI=[-0.26, +0.54], P(>0)=74% | Edge is directional but CI includes 0 broadly |
| S2 | LATCH's 5% MDD CAGR advantage supported? | **UNSUPPORTED** | CI=[-2.3, +5.6] pp, P(>0)=77% | Direction consistent but not significant |
| S3 | LATCH's 10% MDD CAGR advantage supported? | **UNSUPPORTED** | CI=[-4.8, +9.7] pp, P(>0)=76% | Direction consistent but not significant |
| S4 | Two-regime model temporally stable? | **TENTATIVE** | LATCH wins 5% MDD in 64-67% of windows | More often right than wrong, but not dominant |
| S5 | Results depend on start date? | **TENTATIVE** | 2020-01 start reverses conclusions | 2018 bear market matters for LATCH edge |
| S6 | LATCH complexity premium over SM justified? | **UNSUPPORTED** | Sharpe diff +0.003, CI=[-0.05, +0.06], P(>0)=55% | **NOT_JUSTIFIED_BY_CURRENT_EVIDENCE** |
| S7 | Evidence base sufficient for final synthesis? | **TENTATIVE** | All point estimates directionally consistent | Proceed but with honest uncertainty bounds |

---

## 14. Remaining Uncertainties

1. **Statistical power**: 8.5 years of H4 data (18662 bars) is insufficient to distinguish Sharpe differences of 0.1-0.3 at 95% confidence. The CI widths (0.5-0.8 Sharpe) reflect this fundamental limitation. More data would not resolve this within a few years — it would require decades of additional BTC history.

2. **Regime dependence**: The E0 vs LATCH ranking reverses between bull and bear markets. Any full-sample conclusion is a weighted average of regime-specific effects, and the weighting depends on the sample composition.

3. **Crossover instability**: The MDD budget at which E0 overtakes LATCH varies from 3% to 26.5% across windows. There is no stable crossover point.

4. **Sample composition**: The 2018 bear market contributes disproportionately to LATCH's advantage. Whether future bear markets will reproduce this pattern is unknown.

5. **Model vs reality gap**: All analysis uses in-sample equity curves with fixed default parameters. Out-of-sample validation has not been performed.

---

## 15. Recommended Next Step

The evidence base is TENTATIVE but internally consistent. All point estimates are directionally sensible. The uncertainties are statistical power limitations, not methodological errors.

**Recommendation: Proceed to the final synthesis memo.**

The synthesis should:
1. Present the point estimates from Steps 3-4 as the best available evidence
2. Attach the Step 5 uncertainty bounds to every claim
3. Classify findings as ROBUST / TENTATIVE / UNSUPPORTED
4. Acknowledge that the E0 vs LATCH ranking is regime-dependent
5. State that SM is the preferred low-complexity alternative (no LATCH premium)
6. Not overstate any claim beyond what the bootstrap supports

---

## 16. Artifacts Produced

| File | Contents |
|------|----------|
| `step5_preanalysis_plan.json` | Frozen pre-analysis plan |
| `bootstrap_primary_tests.csv` | H1-H4 results × 3 block lengths |
| `bootstrap_method_sensitivity.csv` | Block-length sensitivity comparison |
| `bootstrap_matched_budget_diffs.csv` | H2/H3 matched-MDD CAGR diffs |
| `bootstrap_sm_latch_complexity.csv` | H4 complexity premium tests |
| `start_date_sensitivity.csv` | 3 start dates × key metrics |
| `rolling_window_summary.csv` | Window-level summary statistics |
| `rolling_window_details.csv` | Per-window detailed metrics |
| `calendar_slice_metrics.csv` | Annual calendar-year diagnostics |
| `crossover_stability.csv` | Crossover budget estimates per window |
| `step5_resolution_matrix.csv` | S1-S7 resolution status |
| `bootstrap_replications.npz` | Raw bootstrap diffs (5000 × 12 columns) |
| `holm_pvalues.json` | Holm-adjusted p-values for H1-H4 |

---

## 17. Tests

`tests/test_robustness.py` — 17 tests, 5 test classes:

| Class | Tests | Coverage |
|-------|------:|----------|
| TestBootstrapDeterminism | 3 | Same seed → same output, different seed → different |
| TestBlockLengthSensitivity | 3 | All block lengths run, correct index length/range |
| TestMatchedBudgetBootstrap | 4 | Matched-MDD runs, k accuracy, zero returns, saturation tracking |
| TestRollingWindowSegmentation | 5 | Sharpe/CAGR/MDD basics, Holm adjustment properties |
| TestNoProductionMutation | 2 | Input arrays not mutated |

---

*End of Report 05. No deployment recommendations. All conclusions carry explicit uncertainty bounds.*
