# Audit Report 03: Real BTC 4H Data vs Monte Carlo Generator

**Date**: 2026-03-03
**Auditor**: Claude Opus 4.6
**Verdict**: Generator has **2 critical mismatches** that limit Monte Carlo conclusions

---

## 1. Real Data Source

| Property | Value |
|----------|-------|
| **File** | `data/bars_btcusdt_2016_now_h1_4h_1d.csv` |
| **Symbol** | BTCUSDT spot |
| **Interval** | 4H |
| **Period** | 2019-01-01 to 2026-02-20 |
| **Bars loaded** | 15,642 (→ 15,641 returns) |
| **Source** | Binance Vision (pre-downloaded via data-pipeline) |
| **Return type** | Simple percentage returns: `r_t = (P_t - P_{t-1}) / P_{t-1}` |

---

## 2. Diagnostics on Real BTC 4H

### 2.1 Distribution Shape

| Metric | Value |
|--------|-------|
| Mean return (per bar) | 0.000271 |
| Std return (per bar) | 0.013099 |
| Skewness | **-0.2878** |
| Excess kurtosis (Fisher) | **15.28** |
| Kurtosis (raw) | 18.28 |
| 1st percentile | -0.042277 |
| 99th percentile | 0.038903 |
| Min return | -0.162254 |
| Max return | 0.175143 |
| Jarque-Bera stat | 152,461.8 (p ≈ 0.0) |

### 2.2 Tail Index

| Metric | Value |
|--------|-------|
| Hill α (both tails, k=5%) | **2.79** |
| Hill α (upper tail) | **2.84** |
| Hill α (lower tail) | **2.73** |

Interpretation: α ≈ 2.8 means finite variance (α > 2) but infinite kurtosis population (α < 4). Consistent with a power-law tail heavier than Gaussian but lighter than Cauchy.

### 2.3 Autocorrelation Structure

| Lag | ACF(returns) | ACF(returns²) | ACF(\|returns\|) |
|-----|:-----------:|:-------------:|:----------------:|
| 1 | -0.0207 | **0.1073** | **0.2191** |
| 2 | -0.0133 | 0.0752 | 0.1774 |
| 5 | -0.0091 | **0.0921** | **0.2008** |
| 10 | 0.0097 | **0.0555** | **0.1440** |
| 20 | 0.0007 | 0.0614 | 0.1330 |
| 50 | 0.0063 | **0.0432** | **0.0902** |

**Key observation**: Returns themselves are nearly uncorrelated (ACF ≈ 0), but squared/absolute returns show **strong, persistent positive autocorrelation** that does not decay to zero even at lag 50. This is the **volatility clustering** signature — large moves tend to follow large moves.

### 2.4 Volatility Dynamics

| Metric | Value |
|--------|-------|
| Rolling vol mean (120-bar window) | 0.01277 |
| Rolling vol std | 0.00542 |
| Rolling vol CV (std/mean) | **0.4246** |
| Rolling vol max/min ratio | **12.44** |

BTC's volatility varies by a factor of 12.4× between its calmest and most volatile periods. The coefficient of variation (0.42) indicates extreme heteroscedasticity.

### 2.5 Regime Durations

| Metric | Value |
|--------|-------|
| Total regimes (EMA-120 based) | 645 |
| Bull regime mean duration | 26.3 bars |
| Bull regime median duration | 4.0 bars |
| Bull regime max duration | 2,126 bars |
| Bear regime mean duration | 22.2 bars |
| Bear regime median duration | 5.0 bars |
| Bear regime max duration | 2,082 bars |

The heavy-tailed duration distribution (mean >> median) indicates a few very long regimes dominating the statistics.

### 2.6 Drawdown Durations

| Metric | Value |
|--------|-------|
| DD episodes | 125 |
| DD mean duration | 122.8 bars |
| DD median duration | 4.0 bars |
| DD max duration | **5,103 bars** (~3.5 years) |
| DD P90 duration | 229.4 bars |
| DD max depth | **77.04%** |
| DD mean depth | 8.90% |

---

## 3. Diagnostics on Simulation Generator

### 3.1 Generator Specification (Prompt 01)

```python
# Student-t(df=3) AR(1) process
t_scale = vol * sqrt((df - 2) / df)           # scale for target vol
innovations = rng.standard_t(df=3.0) * t_scale
returns[i] = mean + phi * (returns[i-1] - mean) + innovations[i]

# Parameters used in Prompt 01:
vol = 0.0065, phi = 0.15, df = 3.0, n_bars = 15000
```

For this audit, the generator was run with **matched parameters** (vol = real std, mean = real mean, n = real n) to isolate structural differences.

### 3.2 Distribution Shape (Generator, vol-matched, seed=42)

| Metric | Value |
|--------|-------|
| Mean return | 0.000370 |
| Std return | 0.012835 |
| Skewness | **+1.2770** |
| Excess kurtosis (Fisher) | **27.54** |
| Kurtosis (raw) | 30.54 |

### 3.3 Tail Index (Generator)

| Metric | Value |
|--------|-------|
| Hill α (both tails) | **2.78** |
| Hill α (upper tail) | **2.76** |
| Hill α (lower tail) | **2.86** |

### 3.4 Autocorrelation Structure (Generator)

| Lag | ACF(returns) | ACF(returns²) | ACF(\|returns\|) |
|-----|:-----------:|:-------------:|:----------------:|
| 1 | **+0.1497** | 0.0812 | 0.0616 |
| 5 | 0.0004 | **-0.0026** | **-0.0008** |
| 10 | -0.0161 | **-0.0065** | **-0.0164** |
| 20 | 0.0119 | 0.0043 | 0.0025 |
| 50 | -0.0006 | 0.0022 | 0.0127 |

### 3.5 Volatility Dynamics (Generator)

| Metric | Value |
|--------|-------|
| Rolling vol CV | **0.2102** |
| Rolling vol max/min ratio | **3.89** |

### 3.6 Generator Variability (10 seeds)

| Metric | Range [min, max] | Median |
|--------|:----------------:|:------:|
| Skewness | [-1.61, +4.24] | -0.27 |
| Excess kurtosis | [10.25, 158.81] | 27.90 |
| Hill α | [2.54, 2.83] | 2.69 |
| ACF(r², lag=1) | [0.014, 0.036] | 0.023 |
| ACF(\|r\|, lag=1) | [0.046, 0.076] | 0.058 |
| Rolling vol CV | [0.158, 0.320] | 0.214 |

---

## 4. Mismatch Table

| Diagnostic | Real BTC 4H | Generator | Status | Severity |
|-----------|:-----------:|:---------:|:------:|:--------:|
| **Skewness** | -0.29 | +1.28 (varies -1.6 to +4.2) | Sign flip, seed-unstable | Minor |
| **Excess kurtosis** | 15.28 | 27.54 (varies 10-159) | ~2× too high, huge variance | Moderate |
| **Hill α (both)** | 2.79 | 2.78 | **MATCH** | -- |
| **Hill α (upper)** | 2.84 | 2.76 | **MATCH** | -- |
| **Hill α (lower)** | 2.73 | 2.86 | **MATCH** | -- |
| **ACF(r, lag=1)** | -0.021 | **+0.150** | **CRITICAL MISMATCH** | **CRITICAL** |
| **ACF(r, lag=5)** | -0.009 | 0.000 | OK | -- |
| **ACF(r², lag=1)** | 0.107 | 0.081 | Close | Minor |
| **ACF(r², lag=5)** | **0.092** | **-0.003** | **CRITICAL MISMATCH** | **CRITICAL** |
| **ACF(r², lag=10)** | **0.056** | **-0.007** | **CRITICAL MISMATCH** | **CRITICAL** |
| **ACF(r², lag=50)** | **0.043** | **0.002** | **CRITICAL MISMATCH** | **CRITICAL** |
| **ACF(\|r\|, lag=1)** | **0.219** | **0.062** | **3.5× too low** | **CRITICAL** |
| **ACF(\|r\|, lag=5)** | **0.201** | **-0.001** | **CRITICAL MISMATCH** | **CRITICAL** |
| **ACF(\|r\|, lag=10)** | **0.144** | **-0.016** | **CRITICAL MISMATCH** | **CRITICAL** |
| **ACF(\|r\|, lag=50)** | **0.090** | **0.013** | **CRITICAL MISMATCH** | **CRITICAL** |
| **Rolling vol CV** | **0.425** | **0.210** | **2× too low** | **HIGH** |
| **Rolling vol max/min** | **12.44** | **3.89** | **3.2× too low** | **HIGH** |
| Regime count | 645 | 654 | MATCH | -- |
| Regime bull mean | 26.3 | 27.8 | MATCH | -- |
| Regime bear mean | 22.2 | 20.1 | MATCH | -- |
| DD episodes | 125 | 204 | OK | Minor |
| DD max duration | 5,103 | 2,610 | ~2× too short | Moderate |
| DD max depth | 77.0% | 66.7% | Close | Minor |

### Summary of Match/Mismatch

**What the generator gets RIGHT:**
- Tail index (Hill α ≈ 2.8) — correct power-law decay rate
- Marginal volatility level (when matched)
- Regime count and mean regime durations (EMA-based)
- Number of drawdown episodes (right order of magnitude)
- Basic return level (mean, std)

**What the generator gets WRONG — 2 critical failures:**

#### CRITICAL FAILURE 1: No Volatility Clustering

Real BTC has ACF(|r|) that remains above 0.09 even at lag 50 (200 hours). The generator's ACF(|r|) drops to essentially zero by lag 2. This is the most fundamental statistical property of financial returns — **volatility clustering** — and the AR(1) Student-t generator completely fails to reproduce it.

The AR(1) coefficient (phi=0.15) creates short-range return autocorrelation at lag 1, but this is an autocorrelation of **returns**, not of **volatility**. Real BTC has:
- Near-zero return ACF (efficient market)
- Strong, persistent volatility ACF (GARCH-like clustering)

The generator has the opposite:
- Positive return ACF at lag 1 (phi=0.15)
- Near-zero volatility ACF beyond lag 1

#### CRITICAL FAILURE 2: Rolling Volatility Dynamics

Real BTC volatility (120-bar rolling window) has:
- CV = 0.42 (vol of vol is 42% of mean vol)
- Max/min ratio = 12.4× (volatility range from calm to crisis)

Generator volatility has:
- CV = 0.21 (2× too stable)
- Max/min ratio = 3.9× (3.2× too compressed)

This means the generator produces data where volatility is roughly constant, while real BTC goes through extended periods of both extreme calm and extreme crisis.

---

## 5. Impact on Inference Conclusions

### 5.1 Impact on Coverage Results (Prompt 01)

The coverage test asked: "Does the 95% CI contain the true parameter 95% of the time?"

**Under the generator**: Both methods achieved ~95% coverage. This result is **still valid in principle** because coverage depends primarily on:
- The marginal distribution of the statistic (tails match)
- Block-size adequacy for the dependence structure

**However**: the generator's lack of volatility clustering means the effective sample size under the generator is LARGER than under real BTC data. Volatility clustering creates long-range dependence in squared returns, which reduces effective degrees of freedom. Therefore:

> **Coverage in reality may be LOWER than 95%** because the real data has more dependence than the generator captures. The simulation was **optimistic** about coverage.

### 5.2 Impact on Type I Error Results

Type I error was 1.5-2.5% (well below 5%). Under real data with stronger dependence:

> Type I error may be **HIGHER** (closer to 5% or possibly above), because stronger volatility clustering inflates the variance of block means, making CIs less reliable if the block size doesn't capture the full dependence range.

The block sizes tested [10, 20, 40] correspond to 1.7-6.7 days. But BTC's volatility clustering persists for lag 50+ (200+ hours = 8+ days). Block sizes of 10-40 may be **too short** to capture the full dependence structure of real BTC.

### 5.3 Impact on Power Results

Power was 6.5% for a 5.6% annual edge. Under real data with volatility clustering:

> Power may be **EVEN LOWER** because volatility clustering increases the variance of the test statistic, making it harder to detect a signal. The already-low 6.5% power estimate may be optimistic.

### 5.4 Which Conclusions Survive?

| Conclusion | Status Under Real Data |
|-----------|:---------------------:|
| "Both methods have correct coverage" | **WEAKENED** — generator underestimates dependence, real coverage may be lower |
| "Type I error is ≤ 5%" | **UNCERTAIN** — may hold but wasn't tested with realistic dependence |
| "Power is low (~6.5%) for 5.6% edge" | **STILL VALID** — power is likely even lower under real data |
| "Bootstrap is not broken" | **STILL VALID** — the method is mathematically sound; the issue is calibration, not correctness |
| "Both methods test different statistics" | **UNCHANGED** — structural fact, independent of generator |
| "Neither method has useful power for small edges" | **STRENGTHENED** — real data makes power even worse |

### 5.5 What Would a Realistic Generator Need?

To properly simulate BTC 4H returns, the generator needs:

1. **GARCH or stochastic-vol dynamics**: ACF(|r|) must persist to lag 50+. A GARCH(1,1) with α+β ≈ 0.97 would approximate this.
2. **No return autocorrelation**: ACF(r, lag=1) should be ≈ 0 (not +0.15). Remove the AR(1) component.
3. **Proper vol-of-vol**: Rolling vol CV should be ≈ 0.42, max/min ratio ≈ 12×.
4. **Mild negative skewness**: skewness ≈ -0.29 (not seed-dependent swings of -1.6 to +4.2).

A minimal fix:
```python
# Replace AR(1) Student-t with GARCH(1,1) Student-t:
sigma2[t] = omega + alpha * r[t-1]^2 + beta * sigma2[t-1]
r[t] = sqrt(sigma2[t]) * innovations[t]
innovations ~ Student-t(df=5) / sqrt(df/(df-2))
```

With parameters calibrated to match ACF(|r|) and rolling-vol CV of real BTC.

---

## 6. Artifacts

| File | Description |
|------|-------------|
| `artifacts/03_real_vs_generator_diagnostics.py` | Standalone diagnostic script |
| `artifacts/03_real_vs_generator.json` | Full diagnostic data (real + generator + comparison) |

---

*Report generated 2026-03-03 by Claude Opus 4.6. No production code was modified.*
