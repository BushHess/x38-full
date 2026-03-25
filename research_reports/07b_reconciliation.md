# 07b — Reconciliation

**Date**: 2026-03-03
**Script**: `research_reports/artifacts/07b_reconciliation.py`
**Artifact**: `research_reports/artifacts/07b_reconciliation.json`
**Inputs**: report 07 (md + json + csv), validation output, bootstrap/subsampling source

---

## 1. CSV-vs-JSON Consistency Table

The reconciliation script reloads `07_bar_level_paired_returns.csv` (15,647
rows, 12-digit precision) and recomputes all statistics independently.

| Series                | Metric   | JSON (07)   | CSV reload  | Match? |
|:----------------------|:---------|:------------|:------------|:-------|
| candidate_simple_ret  | n_zero   | 7,270       | 7,270       | YES    |
| baseline_simple_ret   | n_zero   | 7,193       | 7,193       | YES    |
| candidate_log_ret     | n_zero   | 7,270       | 7,270       | YES    |
| baseline_log_ret      | n_zero   | 7,193       | 7,193       | YES    |
| **simple_differential** | **n_zero** | **7,217** | **13,695** | **NO** |
| **log_differential**  | **n_zero** | **10,561**  | **13,695** | **NO** |
| candidate_simple_ret  | mean     | 1.736e-4    | 1.736e-4    | YES    |
| baseline_simple_ret   | mean     | 1.667e-4    | 1.667e-4    | YES    |
| simple_differential   | mean     | 6.89e-6     | 6.89e-6     | YES    |
| log_differential      | mean     | 6.65e-6     | 6.65e-6     | YES    |
| All series            | std      | —           | —           | YES    |

All means, stds, and individual-series zero counts agree. The **only
discrepancy** is in the differential zero counts.

### Root Cause of the Discrepancy

The JSON computed `n_zero = int(np.sum(x == 0.0))` on raw float64 NumPy
arrays. The CSV was written with `:.12f` formatting (12 decimal places).

When both strategies hold identical positions (same BTC qty, same cash), their
NAV ratios are mathematically identical. But computing the differential via
separate floating-point operations leaves tiny residuals:

- `simple_diff = diff(navs_c)/navs_c[:-1] - diff(navs_b)/navs_b[:-1]`
  → residuals at ~10⁻¹⁶ scale (not exactly 0.0 in float64)
- `log_diff = log(ratio_c) - log(ratio_b)` → different cancellation behavior,
  more values happen to land on exact 0.0

After CSV serialization at 12 digits, all residuals below 5×10⁻¹³ become
"0.000000000000" and reload as 0.0. This is why the CSV shows 13,695 zeros
for **both** differentials, while the JSON shows different counts (7,217 vs
10,561) for what are semantically the same zeros.

**The true zero rate for both differentials is 13,695 / 15,647 = 87.52%.**

The JSON's "67.5% vs 46.1%" distinction was a float64 artifact, not a
structural property of the data.

### Verification

From the CSV:

| Venn region              | Count  |
|:-------------------------|-------:|
| Both differentials zero  | 13,695 |
| Simple zero only         | 0      |
| Log zero only            | 0      |
| Neither zero             | 1,952  |

The two differentials have **identical** zero/nonzero structure after
eliminating float64 noise.

---

## 2. Meaning of 0.649

### What It Is

The value 0.6485 (rounded to 0.649 in report 06) comes from:

```
File:  out/validate/v12_vs_v10/2026-02-24/results/bootstrap_summary.json
Field: gate.p_candidate_better
```

It is computed at `v10/research/bootstrap.py` line 216:

```python
p_a_better = float((deltas > 0).mean())
```

where `deltas[i] = Sharpe(resampled_A[i]) - Sharpe(resampled_B[i])` for
i = 0..1999, with `metric_fn = calc_sharpe`, scenario = harsh, block_size = 10,
seed = 1337.

### What It Is Not

It is **not** a p-value in the hypothesis-testing sense. Specifically:

- A bootstrap p-value for H₀: δ ≤ 0 would use a centered or studentized test
  statistic, e.g. `p = P*(T* ≥ T_obs)` where T is pivoted around the null.
- This implementation simply counts the fraction of replicates where the
  raw metric delta is positive. No centering, no studentization, no null
  imposition.
- It is a **heuristic probability estimate**: "what fraction of bootstrap
  worlds show candidate Sharpe > baseline Sharpe?"

### Gate Rule

The validation gate (`validation/suites/bootstrap.py` line 104):

```python
status = "pass" if p >= 0.80 and ci_lower > -0.01 else "fail"
```

The 0.80 threshold was not derived from formal Type-I error control, power
analysis, or any calibration procedure. It is a project-specific heuristic.

---

## 3. Method-Family Validity vs Implementation Validity

### Method-family: circular block bootstrap

The circular block bootstrap (Politis & Romano, 1994) is asymptotically
valid for the sample mean and smooth functionals (including the Sharpe ratio)
under:

- Stationarity (at least wide-sense)
- Mixing conditions (α-mixing with polynomial decay)
- Finite second moment (for mean); finite fourth moment (for Sharpe)
- Block size growing as b = O(n^{1/3}) with n → ∞

For the individual strategy return series: Hill α ≈ 2.2–3.0 at 1–5%
thresholds suggests finite variance, so the method-family regularity
conditions are plausibly met. Whether the series are stationary is
questionable (BTC regime changes), but this is inherent to all financial
time-series bootstrap applications.

### Implementation: this project

The project's implementation has specific deviations from textbook usage:

| Aspect                   | Textbook                          | This project                        |
|:-------------------------|:----------------------------------|:------------------------------------|
| Test statistic           | Studentized or centered           | Raw fraction `(deltas > 0).mean()`  |
| Null hypothesis          | Imposed (center at 0)             | Not imposed                         |
| p-value interpretation   | Type-I error probability          | Heuristic probability estimate      |
| Decision threshold       | Calibrated (e.g., α = 0.05)      | Heuristic (p ≥ 0.80)               |
| Block size selection      | Data-driven (e.g., Politis-White) | Fixed grid [10, 20, 40]            |
| CI type                  | Studentized / BCa                 | Percentile                          |

The percentile CI is first-order valid but has slower convergence than
studentized or BCa intervals. The `(deltas > 0).mean()` statistic is a
legitimate quantity (posterior-like probability under the bootstrap measure)
but should not be called a "p-value" without qualification.

**Conclusion**: The method family is sound. The implementation produces
a meaningful quantity (bootstrap probability of candidate superiority) with
a heuristic decision rule. It is not formally calibrated for Type-I error.

---

## 4. Corrected Zero-Mass and Equality Metrics

All values recomputed from the CSV:

### Individual Return Zeros (bars where strategy is flat / in cash)

| Series                | n_zero | Fraction |
|:----------------------|-------:|---------:|
| candidate_simple_ret  |  7,270 |   46.46% |
| baseline_simple_ret   |  7,193 |   45.97% |
| candidate_log_ret     |  7,270 |   46.46% |
| baseline_log_ret      |  7,193 |   45.97% |

These are correct in both JSON and CSV. Individual returns are exactly zero
when the strategy holds zero BTC (NAV is unchanged).

### Differential Zeros (bars where both strategies have identical returns)

| Series               | JSON (float64) | CSV (12 digits) | True semantic value |
|:---------------------|---------------:|----------------:|--------------------:|
| simple_differential  |          7,217 |          13,695 | **13,695 (87.52%)** |
| log_differential     |         10,561 |          13,695 | **13,695 (87.52%)** |

The CSV value is correct. The JSON values are float64 artifacts.

### Exposure States

| State                          | Count  | Fraction |
|:-------------------------------|-------:|---------:|
| Both flat (exp = 0)            |  7,044 |   45.02% |
| Both in market (exp > 0)       |  8,036 |   51.36% |
| Candidate only in market       |    243 |    1.55% |
| Baseline only in market        |    324 |    2.07% |
| Exposure exactly equal         | 13,727 |   87.73% |

### Correlations

| Pair                               | ρ        |
|:-----------------------------------|:---------|
| Simple returns (full series)       | 0.96377  |
| Log returns (full series)          | 0.96320  |
| Simple returns (nonzero bars only) | 0.96375  |
| Log returns (nonzero bars only)    | 0.96319  |

The ρ = 0.964 claim from reports 06/07 is **confirmed**. Filtering to
nonzero-only bars does not change the correlation meaningfully.

---

## 5. Which Claims from Report 07 Survive

### "Individual return series have Hill α ≈ 2.2–3.0 at 1–5% thresholds"

**SURVIVES.** Recomputed from CSV:

| Threshold | Candidate α | Baseline α |
|:---------:|:-----------:|:----------:|
| 0.5%      | 3.58        | 3.85       |
| 1%        | 3.00        | 3.12       |
| 2%        | 2.72        | 2.76       |
| 5%        | 2.22        | 2.26       |
| 10%       | 1.83        | 1.84       |
| 20%       | 1.36        | 1.36       |

Identical to report 07's values.

### "Both differentials have extreme kurtosis and skew"

**SURVIVES.** Skew ≈ −8.6 (simple) / −9.7 (log), kurtosis ≈ 616 / 697.
These are computed from the full arrays (not affected by zero-count issue).

### "Strategies are near-identical (ρ = 0.964)"

**SURVIVES.** Confirmed at 0.96377 (simple) / 0.96320 (log).

### "Bootstrap operates on individual simple returns, not a differential"

**SURVIVES.** Confirmed by source code reading.

### "Subsampling operates on differential log-return"

**SURVIVES.** Confirmed by source code reading.

### "Hill estimator is unstable across threshold fractions for the differential"

**SURVIVES.** Recomputed from CSV: α ranges from 2.24 (0.5%) to NaN (20%)
for both differentials (identical values). The instability is real.

### "Report 06 analyzed a series not consumed by either method"

**SURVIVES.** Report 06's simple-return differential is not consumed by
bootstrap (which uses individual returns) or subsampling (which uses log
differential). Correct.

---

## 6. Which Claims from Report 07 Fail

### "Log differential has 67.5% zeros; simple differential has 46.1% zeros"

**FAILS.** Both differentials have **87.52% zeros** (13,695 / 15,647).
The reported distinction was entirely a float64 exact-comparison artifact.
The log function and the division-based formula leave different-magnitude
residuals (~10⁻¹⁶) when the true value is zero. The CSV (12-digit precision)
correctly resolves both to zero.

### "67.5% zero mass — higher than simple's 46.1% — because log(nav/nav) produces exact zeros when NAV is unchanged"

**FAILS.** The stated mechanism is wrong. Both simple and log returns produce
exact float64 zeros when NAV is unchanged (in-cash bars). The difference
in JSON zero counts came from bars where both strategies hold **identical
positions** and both returns are nonzero but equal: the subtraction
`log(r_a) - log(r_b)` happens to cancel to exact 0.0 more often than
`(r_a - 1) - (r_b - 1)` due to floating-point cancellation patterns.
Neither count reflects the true zero rate.

### "The bootstrap has very low statistical power for this comparison"

**PARTIALLY FAILS as stated in report 07.** Report 07 attributed low power
solely to the ρ = 0.964 correlation. This framing is incomplete:

1. The bootstrap resamples individual return series, not the differential.
   High correlation between input series does NOT directly reduce bootstrap
   power — the paired design (same block indices) already accounts for
   correlation.

2. The actual reason for low discrimination is that the **metric delta is
   small**: observed Sharpe delta = +0.043 against bootstrap std of ~0.11.
   This is a signal-to-noise problem at the metric level, not a return-
   correlation problem.

3. Additionally, 87.52% of bars contribute zero information to the metric
   delta (identical returns). The effective sample size for distinguishing
   the strategies is not 15,647 but closer to 1,952 (the nonzero-differential
   bars).

### "p = 0.649 correctly reflects low power"

**PARTIALLY FAILS.** The quantity 0.6485 is not a p-value at all (see
Section 2). It is a heuristic bootstrap probability. It reflects the
bootstrap distribution of Sharpe deltas, which may or may not correspond
to "power" in the statistical sense. Saying it "correctly reflects" anything
requires specifying what the correct answer should be, which requires a
formal null hypothesis and test procedure — neither of which the current
implementation provides.

---

## 7. Recommended Next Step

The core issue is not tail heaviness or zero mass. The core issue is that the
project's bootstrap gate is a **heuristic decision rule applied to an
uncalibrated quantity**.

Concretely:

1. `p_a_better = (deltas > 0).mean()` is a legitimate bootstrap quantity but
   is not a p-value. Calling the gate threshold "p ≥ 0.80" conflates it with
   formal hypothesis testing. The project should either:

   **(a)** Acknowledge the gate as heuristic and document its operating
   characteristics empirically (e.g., via simulation under known null), OR

   **(b)** Replace it with a proper bootstrap hypothesis test: impose the null
   (center the bootstrap distribution), use a studentized test statistic,
   and report a calibrated p-value.

2. The 87.52% identical-return rate means any comparison between v12 and v8 is
   fundamentally limited: only 1,952 bars (12.5%) carry distinguishing
   information. No statistical method — however well-calibrated — can extract
   a confident answer from 1,952 informative bars out of 15,647 when the
   signal is as small as Sharpe delta = 0.043.

3. For comparing **genuinely different** algorithms (e.g., VTREND vs v8_apex,
   where ρ ≈ 0.648 and a much larger fraction of bars are informative), the
   existing bootstrap and subsampling infrastructure is adequate. The
   calibration concern applies mainly to near-identical strategy pairs.

---

*Generated by `07b_reconciliation.py` on 2026-03-03.*
*Full numerical results in `artifacts/07b_reconciliation.json`.*
