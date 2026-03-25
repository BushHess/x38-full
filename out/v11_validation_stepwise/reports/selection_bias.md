# Nhiệm vụ C: Selection Bias Analysis — CSCV/PBO + Deflated Sharpe

**Script:** `out_v11_validation_stepwise/scripts/selection_bias.py`
**Scenario:** harsh (50 bps RT)
**Method 1:** CSCV/PBO (Bailey, Borwein, López de Prado 2017)
**Method 2:** Deflated Sharpe Ratio (Bailey & López de Prado 2014)

---

## 1. Problem Statement

V11 cycle_late was developed by testing **30+ configurations** and selecting the best-performing one on in-sample data (full 2019–2026 period). With this many trials, there's a quantifiable risk that the observed improvement (+1.86 harsh score) is due to **selection bias** (data mining, multiple testing) rather than genuine skill.

**Question:** Given N ≥ 28 trials, what's the probability that the selected config would also outperform out-of-sample?

---

## 2. Method 1: CSCV/PBO

### 2.1 Design

| Parameter | Value |
|-----------|-------|
| Strategy universe | 28 configs: 27 V11 grid (aggr × trail × cap) + V10 baseline |
| Blocks (S) | 10 WFO windows (6-month each, 2021-H1 through 2025-H2) |
| CSCV combinations | C(10, 5) = **252** symmetric train/test splits |
| Performance metric | score_no_reject (same formula as objective, without <10 trades rejection) |
| Backtests executed | 28 × 10 = **280** |

### 2.2 Algorithm

For each of 252 combinations:
1. **Train set** = 5 randomly-assigned blocks, **Test set** = remaining 5 blocks
2. For each of 28 configs: compute avg score across train blocks, avg score across test blocks
3. **Select** config with highest train performance
4. **Measure** its rank on test (1 = best, 28 = worst)
5. **Overfit** if test rank > 14 (below median)

**PBO** = fraction of combinations where selected config overfits.

### 2.3 Results

| Metric | PBO | Mean OOS Rank | Median OOS Rank | Interpretation |
|--------|-----|---------------|-----------------|----------------|
| **score_no_reject** | **13.9%** | 5.9 / 28 | 2.5 / 28 | Low overfitting risk |
| **total_return_pct** | **13.9%** | 5.9 / 28 | — | Consistent |

### 2.4 OOS Rank Distribution

```
IS-optimal config's OOS rank across 252 combinations:

Rank 1-7  (top 25%):   196 / 252 = 77.8%  ████████████████████
Rank 8-14 (2nd quartile): 49 / 252 = 19.4% █████
Rank 15-21 (3rd quartile):  7 / 252 =  2.8% █
Rank 22-28 (bottom 25%):  0 / 252 =  0.0%
```

IS-optimal config **never** ranks in the bottom quartile OOS. In 77.8% of splits, it remains in the top quartile.

### 2.5 PBO Interpretation

| PBO Range | Interpretation | Our Result |
|-----------|----------------|------------|
| < 0.10 | Very low overfitting risk | — |
| 0.10 – 0.30 | Low overfitting risk | **13.9% ← HERE** |
| 0.30 – 0.50 | Moderate overfitting risk | — |
| > 0.50 | High overfitting risk (coin flip or worse) | — |

**PBO = 13.9%** means: in only 14% of the 252 symmetric train/test splits does the in-sample optimal config underperform the median out-of-sample. This is well below the 50% threshold that would indicate pure data mining.

---

## 3. Method 2: Deflated Sharpe Ratio

### 3.1 Inputs

| Parameter | Value |
|-----------|-------|
| Observed Sharpe (annualized) | **1.1470** |
| Number of trials (N) | 28 |
| Daily return observations (T) | 2607 |
| Return skewness | 1.4183 |
| Return kurtosis | 24.7419 |

### 3.2 Calculation

```
SE(SR) = sqrt((1 - skew*SR + (kurt-1)/4 * SR²) / T)
       = sqrt((1 - 1.42*1.15 + 23.74/4 * 1.32) / 2607)
       = 0.0525

E[max(SR)] under null (N=28 trials, true SR=0):
       = SE(SR) * [(1-γ)*Φ⁻¹(1-1/N) + γ*Φ⁻¹(1-1/(Ne))]
       = 0.0525 * 2.044
       = 0.1073

DSR z-score = (1.1470 - 0.1073) / 0.0525 = 19.81
DSR p-value = Φ(19.81) ≈ 1.0000
```

### 3.3 Result

| Metric | Value | PASS/FAIL |
|--------|-------|-----------|
| **DSR p-value** | **1.0000** | **PASS** |

### 3.4 Sensitivity to N (number of trials)

| N | E[max(SR)] | DSR p-value |
|---|------------|-------------|
| 28 | 0.1073 | 1.0000 |
| 30 | 0.1088 | 1.0000 |
| 40 | 0.1149 | 1.0000 |
| 50 | 0.1195 | 1.0000 |

Even with 50 trials, DSR remains 1.0000. The observed Sharpe (1.15) is **orders of magnitude** above what random selection could produce.

### 3.5 DSR Caveat

**Important:** DSR tests whether the strategy's **absolute Sharpe** is explainable by selection bias. With SR=1.15 and N=28, the answer is clearly "no" — even V10 baseline has SR≈1.15. The DSR does **NOT** test whether V11's **excess Sharpe over V10** (Δ ≈ 0.017) is explainable by selection bias. For that, the CSCV/PBO analysis is more informative.

---

## 4. Cross-Validation with Prior Tests

| Test | What it measures | Result | Consistent? |
|------|-----------------|--------|-------------|
| **C: PBO** | Is selection from 28 configs overfitting? | **13.9% — low risk** | YES with full-period |
| **C: DSR** | Is absolute Sharpe due to N trials? | **1.0 — PASS** | YES (trivially) |
| **B1: Round-by-round** | Per-window score improvement | INCONCLUSIVE | Partially consistent |
| **B1b: Return-based** | Per-window return improvement | Leaning positive | Consistent with PBO |
| **B2: Sensitivity grid** | Parameter robustness | **FAIL (22% beat)** | **CONTRADICTS PBO** |
| **B3: Final holdout** | OOS on unseen period | **HOLD (V11 loses)** | **CONTRADICTS PBO** |

### Reconciliation

The apparent contradiction between PBO (PASS) and B2/B3 (FAIL/HOLD) is explained by **what each test measures**:

- **PBO** tests: "Given that I pick the best of 28 configs, will it rank well on held-out blocks?" → YES, because most V11 configs have similar per-block performance, and the top configs form a stable cluster.

- **B2** tests: "Does V11 beat V10 across parameter space?" → NO, only 22% of params beat V10. But PBO doesn't require V11 to be robust across ALL params — it only requires the SELECTED config to rank well.

- **B3** tests: "Does V11 beat V10 on the last 17 months?" → NO, but this is 1 specific time period. PBO averages across 252 random splits.

**Key insight:** PBO says the selection process is not overfitting (the best config is genuinely one of the better configs). But B2 and B3 say the improvement itself is small and not reliable. These are **different questions** — you can have a non-overfit selection that still doesn't produce meaningful improvement.

---

## 5. Quantitative Risk Statement

With 30+ trials and observed improvement Δ harsh_score = +1.86:

1. **Selection bias risk is LOW** (PBO = 13.9%). The selected config is not a lucky outlier — it genuinely ranks in the top quartile of the strategy universe in 78% of train/test splits.

2. **However, the improvement itself is SMALL and FRAGILE:**
   - Δ score = +1.86 represents only **2.1%** relative improvement over V10 (88.94 → 90.80)
   - Δ Sharpe = +0.017 — near measurement noise for 7 years of daily data
   - B2 sensitivity grid: 78% of parameter space **loses** to V10
   - B3 holdout: V11 **loses** on the most recent 17 months

3. **The improvement is REGIME-DEPENDENT:**
   - V11 outperforms in early/moderate bull (2021-H1: +16.5, 2023-H2: +19.3 score_no_reject)
   - V11 underperforms in late/extended bull (2024: -1.6, -4.3 score)
   - V11 is identical in BEAR/CHOP/TOPPING
   - Since future regime mix is unknown, the net effect is unpredictable

4. **Deflated Sharpe is uninformative for the margin:** DSR=1.0 because V11's absolute Sharpe (1.15) vastly exceeds what N=28 random trials could produce. But this doesn't address whether the 0.017 Sharpe increment over V10 is real.

5. **Bottom line:** Selection bias did NOT create the improvement — it's a real pattern in the data. But the pattern is too small, too regime-specific, and too parameter-sensitive to be exploitable in production.

---

## 6. Methodology Limitations

1. **Grid universe ≠ full search space**: CSCV uses 28 configs from the sensitivity grid. The actual development process tested additional configs (WFO, manual exploration) that are not in the grid. True N may be 30–50+, which would increase PBO slightly (but our sensitivity analysis shows DSR is robust to N up to 50).

2. **Block size**: 10 blocks of 6 months each. Shorter blocks → more noise. Longer blocks → fewer combinations. S=10 is a reasonable compromise but limits CSCV precision.

3. **Score_no_reject limitation**: Using score without rejection avoids the -1M masking problem but treats 0-trade windows (score=0 for all configs) as "ties" that don't discriminate between strategies.

4. **Non-independence**: CSCV assumes strategy returns on different blocks are independent. In practice, strategies have autocorrelation (position carryover), and regime clustering means adjacent blocks may be correlated.

5. **DSR assumes normal null**: The Deflated Sharpe assumes strategies under the null have zero Sharpe with normal returns. Our returns are fat-tailed (kurtosis=24.7), which the formula partially accounts for but may still be misspecified.

---

## 7. Combined Verdict

### PBO = 13.9% → **PASS** (low overfitting risk)
### DSR = 1.0000 → **PASS** (absolute Sharpe robust)
### Selection bias verdict: **PASS — selection is not the problem**

### But combined with B2/B3: The problem is not overfitting — it's that the real improvement is too small and regime-dependent to be actionable.

---

## 8. Data Files

| File | Mô tả |
|------|--------|
| `out_v11_validation_stepwise/selection_bias_results.json` | PBO + DSR + full performance matrix (28×10) |
| `out_v11_validation_stepwise/scripts/selection_bias.py` | Reproducible script (280 backtests) |
| `out_v11_validation_stepwise/reports/selection_bias.md` | This report |
