# 06 — Actual Paired OOS Series Diagnostics

**Date**: 2026-03-03
**Script**: `research_reports/artifacts/04_oos_paired_diagnostics.py`
**Artifacts**: `research_reports/artifacts/04_actual_paired_oos_diagnostics.json`,
              `research_reports/artifacts/04_paired_equity_curves.csv`

---

## 1. Objective

Audit the **actual out-of-sample (OOS) paired series** used by the project's
decision process. Reproduce the exact equity curves from the canonical
validation pipeline, compute distributional diagnostics, and assess whether
the paired differential series meets the assumptions required for valid
bootstrap inference.

## 2. Canonical Configuration

Reproduced from `out/validate/v12_vs_v10/2026-02-24/run_meta.json`:

| Parameter       | Value                                  |
|:----------------|:---------------------------------------|
| Candidate       | v12_emdd_ref_fix (V8Apex + fixed EMDD) |
| Baseline        | v8_apex (frozen production config)     |
| Date range      | 2019-01-01 to 2026-02-20              |
| Warmup          | 365 calendar days                      |
| Initial cash    | $10,000                                |
| Cost scenario   | harsh (50 bps round-trip)              |
| Bootstrap       | 2,000 reps, block sizes [10, 20, 40]  |
| Seed            | 1337                                   |

Additionally reproduced: **VTREND** (3-param proven algorithm, not in formal
validation pipeline) for informational comparison.

## 3. Reproduction Validation

Engine-computed metrics match existing validation output **exactly**:

| Series           | Sharpe | CAGR   | MDD    | Trades |
|:-----------------|-------:|-------:|-------:|-------:|
| v12 candidate    | 1.2297 | 39.47% | 44.14% |    102 |
| v8 baseline      | 1.1872 | 37.45% | 35.90% |     98 |
| VTREND (bonus)   | 1.2653 | 52.04% | 41.61% |    192 |

Timestamp alignment: **perfect** — all 3 curves have 15,648 H4 bars with
identical `close_time` values. Zero gaps, zero misalignments.

## 4. Distributional Diagnostics

### 4.1 Summary Statistics (per H4 bar)

| Series              | Mean       | Std       | Skew   | Ex. Kurt | Hill α |
|:--------------------|:-----------|:----------|:-------|:---------|:-------|
| v12 candidate       | 1.736e-4   | 6.607e-3  | +0.259 | 26.3     | 2.17   |
| v8 baseline         | 1.667e-4   | 6.572e-3  | +0.358 | 23.5     | 2.22   |
| VTREND              | 2.261e-4   | 8.363e-3  | +0.450 | 22.0     | 2.40   |
| **diff (v12−v8)**   | **6.9e-6** | **1.774e-3** | **−8.64** | **616** | **0.82** |
| diff (VT−v8)        | 5.94e-5    | 6.475e-3  | +0.256 | 32.9     | 1.94   |
| Raw BTC             | 2.723e-4   | 1.310e-2  | −0.288 | 15.3     | 2.37   |

### 4.2 Tail Quantiles

| Series            | p1        | p5        | p95      | p99      | Min       | Max       |
|:------------------|:----------|:----------|:---------|:---------|:----------|:----------|
| v12 candidate     | −1.97%    | −0.80%    | +0.92%   | +2.22%   | −9.39%    | +8.12%    |
| v8 baseline       | −1.98%    | −0.81%    | +0.92%   | +2.20%   | −8.04%    | +8.12%    |
| VTREND            | −2.57%    | −1.04%    | +1.22%   | +2.86%   | −9.61%    | +11.17%   |
| **diff (v12−v8)** | **−0.36%** | **−0.01%** | **+0.01%** | **+0.43%** | **−9.26%** | **+4.80%** |
| Raw BTC           | −3.99%    | −1.90%    | +1.98%   | +3.91%   | −20.50%   | +14.75%   |

### 4.3 Interpretation of Hill Tail Index

The Hill estimator α characterizes the tail heaviness. Rules of thumb:
- α > 4: thin tails (kurtosis finite) — standard inference safe
- 2 < α < 4: heavy tails (variance finite, kurtosis infinite)
- **α < 2: very heavy tails (variance infinite)** — CLT convergence extremely slow
- **α < 1: catastrophically heavy tails (mean infinite)**

**Findings**:
- Individual strategy returns: α ≈ 2.17–2.40. Heavy-tailed but variance exists.
  Bootstrap is valid but may converge slowly.
- Raw BTC: α ≈ 2.37. Similar regime.
- **Paired differential (v12−v8): α = 0.82**. This is below 1.0 — the mean
  itself is not guaranteed to exist as a distributional property. The kurtosis
  of 616 and skew of −8.6 confirm pathological behavior.

## 5. Autocorrelation Structure

### 5.1 ACF at Lag 1

| Series         | ACF(returns) | ACF(squared) | ACF(|returns|) |
|:---------------|:-------------|:-------------|:---------------|
| v12 candidate  | +0.011       | +0.144       | +0.381         |
| v8 baseline    | +0.004       | +0.158       | +0.383         |
| VTREND         | −0.004       | +0.110       | +0.369         |
| Raw BTC        | −0.021       | +0.107       | +0.219         |

**Interpretation**: Returns themselves are approximately uncorrelated (ACF ≈ 0),
but **squared and absolute returns show strong persistence**. This is the
signature of GARCH-type volatility clustering. Strategy returns inherit this
from BTC but amplify it (strategy ACF(|r|) ≈ 0.37–0.38 vs BTC 0.22) because
flat-cash periods create artificial zero-return stretches followed by volatile
in-market periods.

### 5.2 Rolling Volatility Persistence

| Series         | σ₂₀ ACF(1) | σ₆₀ ACF(1) |
|:---------------|:-----------|:-----------|
| v12 candidate  | 0.988      | 0.998      |
| v8 baseline    | 0.989      | 0.998      |
| VTREND         | 0.989      | 0.998      |
| Raw BTC        | 0.983      | 0.997      |

Rolling volatility is extremely persistent (ACF1 > 0.98). This means volatility
regimes persist for hundreds of bars, and block bootstrap must use blocks large
enough to capture regime transitions.

## 6. Drawdown Analysis

| Series         | Max DD | Episodes | Mean dur | Median dur | Max dur | p95 dur |
|:---------------|-------:|---------:|---------:|-----------:|--------:|--------:|
| v12 candidate  | 44.1%  |       99 |      150 |          3 |   4,539 |     363 |
| v8 baseline    | 35.9%  |       92 |      161 |          4 |   4,943 |     912 |
| VTREND         | 41.6%  |      123 |      125 |          4 |   5,037 |     312 |
| Raw BTC        | 77.0%  |      121 |      127 |          4 |   5,103 |     311 |

Drawdown durations are extremely right-skewed (mean >> median). The max DD
episodes last 4,500–5,100 bars (750–850 days) — the 2021-2023 crypto winter.
The median DD is only 3–4 bars, reflecting the many small retracements.

Baseline (v8_apex) has the lowest max DD (35.9%) but the worst p95 duration (912
bars), suggesting it survives drawdowns better in depth but takes longer to
recover.

## 7. Cross-Correlations

| Pair                       | ρ      |
|:---------------------------|-------:|
| v12 candidate vs BTC       | 0.617  |
| v8 baseline vs BTC         | 0.611  |
| VTREND vs BTC              | 0.638  |
| **v12 vs v8 baseline**     | **0.964** |
| VTREND vs v8 baseline      | 0.648  |

**Key finding**: The candidate and baseline are **96.4% correlated**. They are
nearly identical strategies (both V8Apex variants). The differential captures
only the remaining 3.6% of independent variation, which is dominated by a
handful of extreme events (hence α = 0.82).

VTREND, by contrast, has ρ = 0.648 with baseline — substantially more
independent. This is consistent with it being a genuinely different 3-parameter
algorithm.

## 8. Critical Finding: Pathological Differential Series

The paired differential **d(t) = r_candidate(t) − r_baseline(t)** has:

| Property        | Value     | Implication                                |
|:----------------|:----------|:-------------------------------------------|
| Hill α          | 0.82      | Infinite mean — CLT does not apply         |
| Skewness        | −8.64     | Extreme left skew (rare large losses)      |
| Excess kurtosis | 616       | Extreme leptokurtic                        |
| p5 / p95        | −0.01% / +0.01% | Median difference is near zero       |
| p1 / p99        | −0.36% / +0.43% | Occasional moderate divergence       |
| Min / Max       | −9.26% / +4.80% | Rare catastrophic events dominate    |

**Root cause**: v12 and v8 are nearly identical (ρ = 0.964). On >95% of bars,
their returns differ by <0.01%. But on rare bars where the emergency DD
mechanism triggers differently, the difference can be 5–9%. These rare events
dominate the distribution and produce infinite-variance tails.

**Consequence for bootstrap inference**: The validation pipeline's paired block
bootstrap operates on this differential. With α < 1:
- Bootstrap mean estimates are **inconsistent** — they don't converge to the
  true mean as B → ∞
- Confidence intervals are unreliable
- The reported p_candidate_better = 0.649 (harsh, block=10) has **no valid
  frequentist interpretation**
- This does NOT mean the comparison is wrong, only that the bootstrap
  cannot adjudicate between these two near-identical strategies

**This pathology does NOT affect VTREND research**: The VTREND differential
(VT−v8) has Hill α = 1.94 (heavy-tailed but finite variance), making bootstrap
inference on VTREND vs baseline meaningfully more reliable.

## 9. Comparison: Strategy vs Raw BTC

| Property              | Strategies     | Raw BTC       | Ratio         |
|:----------------------|:---------------|:--------------|:--------------|
| Per-bar volatility    | 6.6–8.4 ×10⁻³ | 13.1 ×10⁻³    | 0.50–0.64×    |
| Hill α                | 2.17–2.40      | 2.37          | similar       |
| Skewness              | +0.26 to +0.45 | −0.29         | opposite sign |
| ACF(|r|) lag 1        | 0.37–0.38      | 0.22          | 1.7× higher   |
| Max drawdown          | 36–44%         | 77%           | 0.47–0.57×    |
| Correlation with BTC  | 0.61–0.64      | 1.00          | —             |

Strategy returns are approximately half as volatile as BTC, have **positive**
skew (BTC has negative), and similar tail heaviness. The volatility clustering
is stronger in strategy returns due to the on/off exposure pattern.

## 10. Summary of Findings

1. **Reproduction**: Equity curves reproduced exactly (metrics match to last decimal).
2. **Alignment**: All series perfectly aligned (15,648 bars, zero gaps).
3. **Individual series**: Heavy-tailed (α ≈ 2.2) with strong vol clustering.
   Manageable for bootstrap but convergence is slow.
4. **CRITICAL**: The v12-vs-v8 differential has **α = 0.82 (infinite variance
   and infinite mean)**, rendering the paired bootstrap p-values unreliable
   for this specific comparison.
5. **VTREND differential is better-behaved**: α = 1.94 (heavy but finite
   variance). Bootstrap is more meaningful for VTREND comparisons.
6. **The v12-vs-v8 comparison was correctly rejected** by the validation
   pipeline — but the rejection should be interpreted as "cannot distinguish"
   rather than "baseline is better", because the bootstrap lacks statistical
   power on this pathological differential.
7. **Strategy returns show positive skew** while BTC shows negative skew —
   the trend-following exit mechanism successfully truncates left-tail events.

## 11. Recommendations

1. **For near-identical strategy comparisons** (ρ > 0.95): Do not rely on
   paired block bootstrap. Use permutation tests or direct trade-level
   comparison instead, as the differential is dominated by rare events.
2. **For VTREND comparisons**: Paired bootstrap is marginally acceptable
   (α ≈ 1.9) but should use large block sizes (≥40) to capture vol regimes.
3. **Block size validation**: With rolling-vol ACF1 > 0.98, volatility regimes
   persist for hundreds of bars. Block sizes of 10 may be too small to capture
   regime transitions. Block size 40 is the minimum recommended.
4. **Hill α monitoring**: Any future paired comparison should report Hill α of
   the differential as a diagnostic. If α < 2, flag the bootstrap as unreliable.

---

*Generated by `04_oos_paired_diagnostics.py` on 2026-03-03.*
*Full numerical results in `artifacts/04_actual_paired_oos_diagnostics.json`.*
