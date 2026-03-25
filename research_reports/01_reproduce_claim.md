# Audit Report 01: Reproduce "Bootstrap Không Bị Vỡ" Claim

**Date**: 2026-03-03
**Auditor**: Claude Opus 4.6
**Status**: COMPLETED — claim PARTIALLY SUPPORTED with material caveats

---

## 1. Claim Under Audit

The following claim was made during the previous conversation session:

> "With BTC-realistic heavy tails (Student-t df=3, kurtosis~24, Hill α≈2.88):
> - Both Bootstrap and Subsampling have ~95% coverage
> - Both have ~3-4% Type I error
> - Both have ~30% power for 5.6% annual edge
>
> Bootstrap is NOT broken. Both methods are valid."

## 2. Source Files Used

### 2.1 Inference Method Implementations (Production Code)

| File | Role | SHA256 |
|------|------|--------|
| `v10/research/bootstrap.py` (250 lines) | Circular block bootstrap: `paired_block_bootstrap()`, `calc_sharpe()` | Production code, reviewed |
| `v10/research/subsampling.py` (285 lines) | Overlapping block subsampling: `paired_block_subsampling()`, `summarize_block_grid()` | Production code, reviewed |
| `research/lib/bootstrap.py` (493 lines) | VCBB — Volatility-Conditioned Block Bootstrap (price path resampling) | NOT used in claims |
| `research/lib/dsr.py` (167 lines) | Deflated Sharpe Ratio (Bailey & López de Prado, 2014) | NOT used in claims |

### 2.2 Validation Suite Code

| File | Role |
|------|------|
| `validation/suites/subsampling.py` (148 lines) | SubsamplingSuite — validation gate |
| `v10/validation/suites/subsampling.py` (167 lines) | V10 SubsamplingSuite — validation gate |
| `validation/suites/bootstrap.py` | BootstrapSuite — validation gate |
| `v10/validation/suites/bootstrap.py` (142 lines) | V10 BootstrapSuite — validation gate |

### 2.3 Tests

| File | Tests |
|------|-------|
| `v10/tests/test_subsampling.py` (149 lines) | 9 tests, all pass |

### 2.4 Scripts That Produced the Claimed Tables

**CRITICAL FINDING: NO PERSISTED SCRIPTS EXIST.**

The claimed tables (coverage, Type I error, power, kurtosis/tail-index) were produced
by **inline Python heredoc code** executed via Bash tool calls during the conversation.
These scripts were never saved to disk. They existed only in the conversation transcript.

Evidence:
- `grep -r "coverage.*simulation" btc-spot-dev/**/*.py` → 0 results
- `grep -r "Student.*t|student_t|heavy.tail.*simul" btc-spot-dev/**/*.py` → 0 results
- `find btc-spot-dev/ -name "*vtrend_significance*"` → 0 results
- No Jupyter notebooks in the repo
- No simulation scripts in `research/`, `research/lib/`, or `v10/research/`

**Implication**: The original results cannot be bit-for-bit reproduced because the exact
inline code was consumed by the conversation and is only preserved in the conversation
transcript (JSONL). The reproduction script in this report reimplements the same logic
from first principles, matching the described parameters.

## 3. Exact Commands and Reproduction

### 3.1 Reproduction Script

```
research_reports/artifacts/01_reproduce_heavy_tail_sim.py
```

**Execution command:**
```bash
cd /var/www/trading-bots/btc-spot-dev
python -u research_reports/artifacts/01_reproduce_heavy_tail_sim.py
```

**Runtime**: ~290 seconds (Steps 1-2: 2s, Coverage+Power: 143s, Type I: 142s)

### 3.2 Parameters (Exact Match to Claimed)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Generator | Student-t(df=3.0) | Heavy tails, finite variance, infinite kurtosis |
| n_bars | 15,000 | ~6.8 years of H4 bars |
| n_reps | 200 | Monte Carlo repetitions |
| vol | 0.0065 | Per-bar volatility scale |
| phi (AR1) | 0.15 | Return autocorrelation coefficient |
| edge | 0.000025 per bar | Annualizes to ~5.6% |
| block_sizes | [10, 20, 40] | H4 bars |
| n_bootstrap | 1,000 | Resamples per bootstrap test |
| ci_level | 0.95 | For subsampling CI |
| bootstrap_seed | 42 | Fixed seed per rep |
| Seeds (candidate) | 1000+rep | For coverage/power reps |
| Seeds (baseline) | 5000+rep | For coverage/power reps |
| Seeds (H0 test A) | 8000+rep | For Type I error reps |
| Seeds (H0 test B) | 9000+rep | For Type I error reps |
| Pop truth | 30 runs × 80,000 bars | Seeds: 100000+i / 200000+i |

## 4. Data/Generator Specification

### 4.1 Return Generator

```python
# Student-t innovations scaled for target volatility
t_scale = vol * sqrt((df - 2) / df)  # = 0.0065 * sqrt(1/3) ≈ 0.00375
innovations = rng.standard_t(df=3.0, size=n_bars) * t_scale

# AR(1) process with drift
returns[0] = mean_excess + innovations[0]
returns[i] = mean_excess + phi * (returns[i-1] - mean_excess) + innovations[i]

# Equity from returns
equity[0] = 10000.0
equity[1:] = 10000.0 * cumprod(1 + returns)
```

### 4.2 Why Student-t(df=3)?

- BTC H4 returns show excess kurtosis ≈ 23.55 and Hill tail index α ≈ 2.7
- Student-t(df=3): theoretical kurtosis = ∞ (population), sample kurtosis ≈ 20-40
- Student-t(df=3): tail index α = df = 3, close to empirical BTC α ≈ 2.7
- This is a conservative choice (slightly heavier tails than needed)

## 5. Statistic Definitions

### 5.1 Bootstrap Statistic: Sharpe Difference

```python
def calc_sharpe(returns):
    mu = returns.mean()
    sigma = returns.std(ddof=0)  # population std
    return mu / sigma * sqrt(2190)  # annualize for H4

# Test: H0: Sharpe(A) - Sharpe(B) ≤ 0
# CI: percentile method on bootstrap distribution of deltas
```

### 5.2 Subsampling Statistic: Excess Geometric Growth

```python
# log-return difference
diff = log(equity_a[1:]/equity_a[:-1]) - log(equity_b[1:]/equity_b[:-1])
theta_n = mean(diff)  # full-sample mean log-return difference

# Overlapping block means
theta_b = block_means(diff, block_size)  # via cumsum

# Root-n scaling
root = sqrt(block_size) * (theta_b - theta_n)

# CI construction
ci_lower = theta_n - quantile(root, 1-alpha/2) / sqrt(n)
ci_upper = theta_n - quantile(root, alpha/2) / sqrt(n)

# Annualize
annualized_delta = expm1(2190 * theta_n)
```

**KEY DIFFERENCE**: Bootstrap tests **risk-adjusted** edge (Sharpe), subsampling tests
**absolute growth** edge. These are different hypotheses on the same data.

## 6. Reproduced Tables

### 6.1 Tail Properties

| Property | Original Claim | Reproduced | Match? |
|----------|---------------|------------|--------|
| Kurtosis (Fisher=False) | ~24 | 30.36 | PARTIAL — same order, different seed |
| Skewness | not specified | -0.5598 | N/A |
| Hill α | ~2.88 | 2.67 | PARTIAL — same order, different seed |

**Note**: Kurtosis and Hill α are highly variable for Student-t(df=3) with finite samples.
The population kurtosis is infinite. Sample values from 15000 draws typically range 15-50.
Both the claimed (~24) and reproduced (30.36) values are consistent with the same generator.

### 6.2 Coverage (Nominal 95%)

| Block | Bootstrap (claimed) | Bootstrap (reproduced) | Sub (claimed) | Sub (reproduced) |
|-------|--------------------|-----------------------|--------------|-------------------|
| 10 | ~95% | **94.0%** | ~95-96% | **96.0%** |
| 20 | ~95% | **95.0%** | ~95-96% | **96.0%** |
| 40 | ~95% | **94.5%** | ~95-96% | **96.5%** |

**Verdict: CONFIRMED.** Both methods achieve nominal 95% coverage under heavy tails.
Bootstrap: 94.0-95.0%, Subsampling: 96.0-96.5%. All within Monte Carlo error (±2.1% for n=200).

### 6.3 Type I Error (Nominal ≤ 5%)

| Block | Bootstrap (claimed) | Bootstrap (reproduced) | Sub (claimed) | Sub (reproduced) |
|-------|--------------------|-----------------------|--------------|-------------------|
| 10 | ~3-4% | **2.5%** | ~3-4% | **2.0%** |
| 20 | ~3-4% | **2.0%** | ~3-4% | **1.5%** |
| 40 | ~3-4% | **1.5%** | ~3-4% | **2.0%** |

**Verdict: CONFIRMED.** Both methods control Type I error well below 5%.
Reproduced values (1.5-2.5%) are slightly lower than the claimed (~3-4%) but still
consistent. The difference is likely due to different random seeds and the conservative
nature of block-based CIs with heavy tails.

### 6.4 Power (Ability to Detect 5.6% Annual Edge)

| Block | Bootstrap (claimed) | Bootstrap (reproduced) | Sub (claimed) | Sub (reproduced) |
|-------|--------------------|-----------------------|--------------|-------------------|
| 10 | ~30% | **6.5%** | ~30% | **6.5%** |
| 20 | ~30% | **7.0%** | ~30% | **6.0%** |
| 40 | ~30% | **6.5%** | ~30% | **6.5%** |

**Verdict: MISMATCH.** The claimed ~30% power is NOT reproduced. Actual power is **6-7%**,
barely above the Type I error rate. This means the test has essentially NO ability to
detect a 5.6% annual edge with 15,000 bars and these heavy tails.

## 7. Mismatch Analysis

### 7.1 Power Discrepancy (Critical)

The most significant mismatch is in power: claimed ~30% vs reproduced ~6.5%.

**Possible explanations:**

1. **Different edge magnitude in the original inline code**: The original code may have
   used a larger edge (e.g., 0.0001 per bar ≈ 24% annual instead of 0.000025 ≈ 5.6%).
   Since the original script was not persisted, this cannot be verified.

2. **Different generator**: The original may have used a different return process
   (e.g., pure i.i.d. Student-t without AR(1), or Gaussian innovations with different
   vol). AR(1) with phi=0.15 introduces autocorrelation that reduces effective sample
   size and thus power.

3. **Different power definition**: "Power" in the original might have been defined as
   `p_a_better > 0.80` (bootstrap probability) rather than `ci_lower > 0` (strict
   confidence interval excludes zero). The former is a weaker criterion.

4. **Conversation context compression**: The original results may have been from a
   different simulation variant that was summarized/rounded during the conversation.

**This mismatch is material**: A method with 6.5% power for a 5.6% edge is functionally
unable to distinguish signal from noise. This does NOT mean bootstrap is "broken" (the
coverage and Type I error are correct), but it means **neither method can reliably detect
the edge we care about** with 15,000 bars of heavy-tailed data.

### 7.2 Kurtosis/Hill Variance (Minor)

The tail property values (kurtosis 30.36 vs ~24, Hill α 2.67 vs ~2.88) differ because:
- Student-t(df=3) has infinite population kurtosis
- Sample kurtosis varies enormously between draws (CV > 50%)
- Different seeds produce different sample kurtosis values
- Both values are consistent with the same DGP

**This mismatch is immaterial** — it confirms the generator matches.

### 7.3 Type I Error (Minor)

Reproduced (1.5-2.5%) vs claimed (~3-4%). Both are well below 5%.
The difference is within expected Monte Carlo variance for n=200 reps.

**This mismatch is immaterial** — the qualitative conclusion (conservative Type I control) holds.

## 8. What Is Unverifiable

1. **Exact original inline code**: The Python heredoc scripts that produced the original
   tables were never saved to disk. Only the conversation transcript (JSONL) preserves them.
   Bit-for-bit reproduction is impossible without extracting the exact code from the transcript.

2. **Original RNG state**: Even if we had the exact code, the claimed tables used specific
   seed sequences. Without knowing if the AR(1) generator loop was identical, the exact
   numeric values cannot be matched.

3. **Whether multiple simulation variants were run**: The conversation may have run several
   variants with different parameters, and the "final" claimed values may be from a different
   variant than what was described in the summary.

4. **The ~30% power claim specifically**: This is the most suspicious number. Given the
   reproduced 6.5% power, either:
   - The original used a larger edge (plausible)
   - The original used a weaker power criterion (plausible)
   - The number was misremembered/misquoted (plausible)
   - All of the above

## 9. Conclusions

### 9.1 Supported Claims

| Claim | Status | Evidence |
|-------|--------|----------|
| Bootstrap coverage ~95% under heavy tails | **CONFIRMED** | 94.0-95.0% reproduced |
| Subsampling coverage ~95% under heavy tails | **CONFIRMED** | 96.0-96.5% reproduced |
| Type I error ≤ 5% for both methods | **CONFIRMED** | 1.5-2.5% reproduced |
| Both methods are "valid" (correct coverage) | **CONFIRMED** | Coverage and Type I error nominal |
| Bootstrap is "not broken" | **CONFIRMED** | Coverage correct, Type I controlled |
| The two methods test different statistics | **CONFIRMED** | Sharpe vs geometric growth |

### 9.2 Unsupported Claims

| Claim | Status | Evidence |
|-------|--------|----------|
| Power ~30% for 5.6% edge | **NOT REPRODUCED** | 6.5% reproduced |

### 9.3 Practical Implications

1. **Both methods are statistically valid** — they produce correct confidence intervals
   and control false positive rates, even under heavy tails.

2. **Neither method has useful power** for detecting a 5.6% annual edge with ~7 years
   of H4 data under BTC-like heavy tails. Power ≈ 6.5% means you'd need to see
   the edge ~15x to detect it once.

3. **This is not a defect of the methods** — it's a fundamental sample-size limitation.
   With Student-t(df=3) innovations and 15,000 bars, the noise drowns the signal.

4. **The bootstrap is NOT "distorting" research results** — it's simply unable to
   detect small edges. This is honest behavior: when power is low, CIs are wide,
   and the method correctly says "I can't tell."

5. **DSR (`research/lib/dsr.py`) provides complementary analytical inference** for Sharpe,
   and is already integrated in the project but was not tested in this simulation.

## 10. Artifacts

| File | Description |
|------|-------------|
| `artifacts/01_reproduce_heavy_tail_sim.py` | Standalone reproduction script |
| `artifacts/01_heavy_tail_sim_results.json` | Machine-readable results |
| `artifacts/01_console_output.txt` | Full console output from reproduction run |

---

*Report generated 2026-03-03 by Claude Opus 4.6. No runtime code was modified.*
