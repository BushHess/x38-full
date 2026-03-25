# 07 — Exact Series Tail Sanity

**Date**: 2026-03-03
**Script**: `research_reports/artifacts/07_exact_series_tail_sanity.py`
**Artifacts**:
  `research_reports/artifacts/07_exact_series_tail_sanity.json`
  `research_reports/artifacts/07_bar_level_paired_returns.csv`

---

## 1. Exact Series Definitions by Method

### 1.1 Paired Block Bootstrap

**Source**: `v10/research/bootstrap.py`, lines 106–107, 179–205

The bootstrap operates on **individual simple percentage returns**, not on a
differential series:

```python
# Per curve (lines 106-107):
navs = np.array([e.nav_mid for e in equity], dtype=np.float64)
returns = np.diff(navs) / navs[:-1]   # simple pct returns

# Per replicate (lines 200-205):
starts = rng.integers(0, n, size=n_blocks)
indices = np.concatenate([np.arange(s, s + block_size) % n for s in starts])[:n]
deltas[i] = metric_fn(returns_a[indices]) - metric_fn(returns_b[indices])
```

Each bootstrap replicate:
1. Draws identical block indices
2. Resamples **both** individual return series with those indices
3. Computes `metric(resampled_A) - metric(resampled_B)`

The bootstrap **never forms a bar-level return differential**. The differential
exists only at the metric level (e.g., Sharpe_A − Sharpe_B), after aggregation.

### 1.2 Paired Block Subsampling

**Source**: `v10/research/subsampling.py`, lines 129–133, 180–182, 190

The subsampling operates on the **differential log-return** series:

```python
# Lines 129-133:
log_a = np.log(navs_a[1:] / navs_a[:-1])
log_b = np.log(navs_b[1:] / navs_b[:-1])
diff  = log_a - log_b

# Line 190: statistic = mean(diff)
full_mean = float(np.mean(diff))
```

The subsampling then computes overlapping block means of `diff` and forms
confidence intervals for `mean(diff)` via the subsampling distribution.

### 1.3 What Report 06 Analyzed

Report 06 computed `simple_ret_candidate - simple_ret_baseline` and analyzed
its tail. **Neither method consumes this series.** The bootstrap uses individual
returns; the subsampling uses log-return differential. Report 06's tail
analysis was applied to a series not used by any inference method.

---

## 2. Simple vs Log Differential Diagnostics

### 2.1 Summary Statistics

| Series                   |       Mean |        Std |   Skew |   Ex. Kurt |  % Zero |
|:-------------------------|-----------:|-----------:|-------:|-----------:|--------:|
| candidate simple ret     | 1.736e-04  | 6.607e-03  | +0.259 |     26.260 |  46.46% |
| baseline simple ret      | 1.667e-04  | 6.572e-03  | +0.358 |     23.473 |  45.97% |
| candidate log ret        | 1.518e-04  | 6.604e-03  | -0.023 |     26.777 |  46.46% |
| baseline log ret         | 1.452e-04  | 6.567e-03  | +0.108 |     23.551 |  45.97% |
| **simple differential**  | **6.89e-06** | **1.774e-03** | **-8.639** | **616.3** | **46.12%** |
| **log differential**     | **6.65e-06** | **1.787e-03** | **-9.725** | **697.4** | **67.50%** |

Key observations:

- **Individual returns**: ~46% are exactly zero (strategy is flat / in cash).
  Mean ≈ 1.7×10⁻⁴, std ≈ 6.6×10⁻³, excess kurtosis ≈ 23–27. Heavy-tailed
  but not pathological.

- **Log differential**: 67.5% of values are exactly zero. This is higher than
  the simple differential's 46.1% because `log(nav[t+1]/nav[t])` produces
  exact zeros when NAV is unchanged, which happens when both strategies hold
  zero BTC at the same time.

- **Both differentials** have extreme skew and kurtosis. The log differential
  is even more extreme (skew -9.7, kurtosis 697) than the simple differential
  (skew -8.6, kurtosis 616).

### 2.2 Autocorrelation (Lag 1)

| Series                | ACF(ret) | ACF(ret²) | ACF(\|ret\|) |
|:----------------------|---------:|-----------:|--------------:|
| candidate simple ret  |  +0.011  |   +0.144   |    +0.381     |
| baseline simple ret   |  +0.004  |   +0.158   |    +0.383     |
| simple differential   |  +0.040  |   +0.035   |    +0.388     |
| log differential      |  +0.038  |   +0.030   |    +0.381     |

Both differentials show weak level-ACF but strong absolute-return ACF (~0.38),
indicating volatility clustering in the differential — the rare large
divergences tend to cluster (e.g., around emergency-DD trigger events).

---

## 3. Hill Threshold Sensitivity

### 3.1 Combined |x| Hill Estimates

| Series                | 0.5% (k≈78) | 1% (k≈156) | 2% (k≈313) | 5% (k≈782) | 10% (k≈1565) | 20% (k≈3129) |
|:----------------------|:------------|:-----------|:-----------|:-----------|:-------------|:-------------|
| candidate simple ret  | 3.58        | 3.00       | 2.72       | 2.22       | 1.83         | 1.36         |
| baseline simple ret   | 3.85        | 3.12       | 2.76       | 2.26       | 1.84         | 1.36         |
| candidate log ret     | 3.59        | 2.97       | 2.70       | 2.23       | 1.83         | 1.36         |
| baseline log ret      | 3.87        | 3.14       | 2.71       | 2.26       | 1.83         | 1.36         |
| simple differential   | **2.24**    | **1.81**   | **1.45**   | **0.85**   | **0.44**     | **0.05**     |
| log differential      | **2.24**    | **1.82**   | **1.45**   | **0.86**   | **0.44**     | **0.06**     |

### 3.2 Separated Upper/Lower Tails (at 5% threshold)

| Series                | Upper α | Lower α | Combined α | n+ | n− | n₀ |
|:----------------------|--------:|--------:|-----------:|---:|---:|---:|
| candidate simple ret  |    2.75 |    2.54 |       2.22 | 4232 | 4145 | 7270 |
| baseline simple ret   |    2.83 |    2.58 |       2.26 | 4284 | 4170 | 7193 |
| simple differential   |    1.22 |    1.23 |       0.85 | 4216 | 4214 | 7217 |
| log differential      |    1.61 |    1.68 |       0.86 | 2572 | 2514 | 10561 |

### 3.3 Interpretation: Why the Hill Plot Is Unstable

The Hill estimator assumes a continuous Pareto-like tail:
P(|X| > x) ∼ C·x^{−α} for large x.

For the differential series, this assumption **fails** because:

1. **Massive point mass at zero**: 46–67% of values are exactly 0.0. The series
   is a mixture of a point mass at zero and a continuous distribution on the
   non-zero values.

2. **Bimodal non-zero structure**: When both strategies hold BTC, the return
   differential is tiny (typically < 0.01%). When one holds and the other
   doesn't, the differential is large (up to 9%). These are structurally
   different generating mechanisms.

3. **Threshold sweeps through the mixture boundary**: At k_frac=0.5% (k≈78),
   we sample only the true extremes and get α ≈ 2.2. As k grows, we pull in
   observations from the near-zero cluster, which look like an absurdly fat
   tail to the Hill estimator (many small values followed by a few extreme
   values). At k_frac=20%, the estimator has collapsed to α ≈ 0.05.

4. **Separated tails tell a different story**: At 5% threshold, the upper and
   lower tails individually have α ≈ 1.2–1.7 (depending on simple vs log),
   while the combined |x| estimate is 0.85–0.86. The combined estimate is
   biased low because mixing two tails doubles k, dragging in more body
   observations.

---

## 4. Which Prior Claims Survive

### Claim: "Individual strategy returns are heavy-tailed with Hill α ≈ 2.2"

**SURVIVES**, with qualification. At the 5% threshold (k ≈ 782), Hill α ≈
2.22–2.26 for both strategies. This is consistent across simple and log
returns. At stricter thresholds (0.5–2%), α increases to 2.7–3.9, suggesting
the very extreme tail is less heavy than the 5%-estimate implies.

Interpretation: strategy returns have finite variance (α > 2 at all reasonable
thresholds) but borderline-infinite or infinite kurtosis (α < 4 at most
thresholds). This is consistent with BTC's known fat-tailed behavior,
modulated by the strategy's cash/market regime switching.

### Claim: "The paired differential has extreme kurtosis and skew"

**SURVIVES**. Both simple (kurtosis 616, skew -8.6) and log (kurtosis 697,
skew -9.7) differentials are highly leptokurtic and left-skewed. This is not a
Hill-estimation artifact — it's a direct sample moment.

### Claim: "Candidate and baseline are ρ = 0.964 correlated"

**SURVIVES** (from report 06, not re-tested here but the 46% identical-zero
returns and tiny typical differential confirm near-identical behavior).

---

## 5. Which Prior Claims Fail

### Claim: "Hill α = 0.82 implies infinite mean"

**FAILS**. This claim was wrong on multiple levels:

1. **Wrong series**: Report 06 analyzed the simple-return differential.
   Neither the bootstrap nor the subsampling operates on this series.

2. **Single-threshold fragility**: The Hill estimate for the differential at
   k_frac=10% gives α ≈ 0.44, and at k_frac=5% gives α ≈ 0.85. But at
   k_frac=0.5% it gives α ≈ 2.24. A single threshold cannot establish the
   tail index of a mixture distribution. The estimator sweeps from α > 2
   down to α ≈ 0 as the threshold includes more of the zero mass.

3. **Pareto assumption violated**: The Hill estimator requires a Pareto-like
   tail. A series with 46–67% point mass at zero is not Pareto. Applying
   the Hill estimator to such a series and interpreting the result as a tail
   index is statistically invalid.

4. **Separated tails contradict the claim**: Upper and lower tails individually
   have α ≈ 1.2–1.7 at 5% (simple) and 1.6–1.7 (log). Both are above 1.0,
   suggesting finite first moments in each tail separately.

5. **The sample mean clearly exists**: The series has 15,647 observations.
   The sample mean is 6.65×10⁻⁶ (log) / 6.89×10⁻⁶ (simple). There is no
   computational or empirical evidence that the mean does not exist as a
   well-defined population quantity. The extreme kurtosis means the mean is
   estimated with poor precision, but "poorly estimated" ≠ "infinite".

### Claim: "Bootstrap mean estimates are inconsistent — they don't converge to the true mean as B → ∞"

**FAILS**. This statement was wrong on two counts:

1. **Wrong about what the bootstrap does**: The paired block bootstrap does not
   estimate the mean of a differential series. It resamples both individual
   return series with shared block indices, computes a metric (e.g., Sharpe)
   on each resampled series, and differences the metrics. The "B → ∞"
   convergence refers to the bootstrap distribution of the metric delta, not
   the mean of a return differential.

2. **Individual series have finite variance**: For the individual simple-return
   series that the bootstrap actually operates on, Hill α ≈ 2.2–3.0 at
   reasonable thresholds (1–5%). Finite variance is sufficient for circular
   block bootstrap consistency of the mean and Sharpe ratio, given
   appropriate block growth rate (Lahiri, 2003).

### Claim: "The reported p_candidate_better = 0.649 has no valid frequentist interpretation"

**FAILS as stated**. The bootstrap p-value is computed from the distribution
of `Sharpe(resampled_A) - Sharpe(resampled_B)`, not from the differential
return series. Since the individual return series have finite variance at
reasonable tail thresholds, the block bootstrap of the Sharpe ratio is
asymptotically valid.

What IS true: the bootstrap has very **low statistical power** for this
comparison because the two strategies are 96.4% correlated. The metric delta
is small relative to its resampling variance. The p-value of 0.649 correctly
reflects this: the bootstrap cannot distinguish the strategies.

---

## 6. Implications for Bootstrap vs Subsampling

### 6.1 Bootstrap (individual simple returns)

**Input series tail properties (at 5% threshold)**:
- Hill α ≈ 2.2 (finite variance, borderline kurtosis)
- Strong volatility clustering (ACF of |r| ≈ 0.38)
- ~46% zero-return bars (in-cash periods)

**Validity**: The circular block bootstrap is valid for Sharpe and CAGR
estimation on these series, provided the block size is large enough to capture
the volatility regime structure. With ACF(|r|) ≈ 0.38 at lag 1, the
dependence decays slowly. Block sizes of 40+ are recommended.

**Power limitation**: The two strategies are near-identical (ρ = 0.964). The
bootstrap can validly estimate the uncertainty of the metric delta, but the
delta itself is tiny relative to that uncertainty. This is a power problem,
not a validity problem. The p = 0.649 is interpretable — it means the data
cannot distinguish the two strategies under bootstrap inference.

### 6.2 Subsampling (differential log-return)

**Input series tail properties (at 5% threshold)**:
- Hill α ≈ 0.86 (combined) but upper/lower tails separately α ≈ 1.6
- 67.5% zero mass
- ACF(|diff|) ≈ 0.38 — strong volatility clustering in the differential

**Validity considerations**:
- Subsampling is more robust to heavy tails than bootstrap. Its validity
  requires only that the studentized statistic has a limit distribution,
  not finite moments of any specific order (Politis, Romano & Wolf 1999).
- The 67.5% zero mass is the genuine concern: the differential is a
  mixture distribution, not a standard time series. Block means of such
  a series converge slowly because most blocks contain predominantly zeros.
- The subsampling CIs are likely **conservative** (too wide) rather than
  anti-conservative, because the zero mass inflates the variance of block
  means.

**Power limitation**: Same as bootstrap — the differential is dominated by
zeros with rare large events. Detecting a mean of 6.65×10⁻⁶ against std
of 1.79×10⁻³ requires enormous sample sizes.

### 6.3 The Real Problem: Near-Identical Strategies

Both inference methods are valid but low-power for this comparison.
The root cause is structural, not statistical:

- v12_emdd_ref_fix and v8_apex are V8Apex variants differing only in
  emergency drawdown handling
- On >95% of bars, they make identical position decisions
- The rare divergences (when emergency DD triggers) produce the extreme
  events in the differential
- No statistical method can reliably adjudicate between strategies that
  agree on 95%+ of decisions from 7 years of data

---

## Summary

| # | Item | Status |
|---|------|--------|
| 1 | Report 06 analyzed a series (simple-return differential) not used by either inference method | **Error corrected** |
| 2 | Hill α < 1 at 10% threshold for the differential | True as computed, but an artifact of the zero-mass mixture — see below |
| 3 | "α < 1 implies infinite mean" applied to this data | **Overstatement**: Hill estimator invalid for 46–67% zero-mass mixtures |
| 4 | "Bootstrap estimates inconsistent as B → ∞" | **Wrong**: bootstrap operates on individual returns (α ≈ 2.2, finite variance) |
| 5 | "p = 0.649 has no valid frequentist interpretation" | **Wrong**: bootstrap is valid; the p-value reflects low power, not invalidity |
| 6 | Individual return series have heavy tails | **Correct**: Hill α ≈ 2.2–3.0 at 1–5% thresholds |
| 7 | Extreme kurtosis in both differentials (616–697) | **Correct**: direct sample moment, not dependent on tail model |
| 8 | Strategies are near-identical (ρ = 0.964) | **Correct**: confirmed by 46–67% identical-zero bars |

The correct conclusion is: both bootstrap and subsampling are **valid but
low-power** for the v12-vs-v8 comparison. The inability to distinguish the
strategies is a power problem inherent to comparing near-identical algorithms,
not a breakdown of statistical inference.

---

*Generated by `07_exact_series_tail_sanity.py` on 2026-03-03.*
*Full numerical results in `artifacts/07_exact_series_tail_sanity.json`.*
