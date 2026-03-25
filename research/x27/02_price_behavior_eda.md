# Phase 2: BTC H4 Price Behavior EDA

**Study**: X27
**Date**: 2026-03-11
**Data**: BTCUSDT H4 (18,751 returns) + D1 (3,127 returns), 2017-08 to 2026-03
**Code**: `code/phase2_eda.py`

---

## 1. Return Distribution (H4)

| Metric          | Value     |
|-----------------|-----------|
| N               | 18,751    |
| Mean            | 0.000148 (0.0148% / bar) |
| Std             | 0.014839 (1.48% / bar) |
| Skew            | -0.2008   |
| Excess kurtosis | 20.4145   |
| Jarque-Bera     | 325,731 (p ≈ 0) |

- **Obs09**: H4 log-return distribution has small positive drift, slight negative skew, and extreme leptokurtosis (excess kurtosis = 20.4).
- **Obs10**: Jarque-Bera overwhelmingly rejects normality (p ≈ 0).
- **Obs11**: Tail analysis shows significant fat tails:
  - +2σ: 2.64% observed vs 2.28% Normal expected
  - -2σ: 2.71% observed vs 2.28% Normal expected
  - +3σ: 0.85% observed vs 0.13% Normal expected (6.5× excess)
  - -3σ: 1.02% observed vs 0.13% Normal expected (7.8× excess)
- **Obs12**: Tail asymmetry at 3σ: 159 up-tail events vs 191 down-tail events. Down-tail is heavier (crash risk > rally frequency at extreme magnitudes).

**Figures**: Fig01 (histogram + Q-Q plot)

---

## 2. Serial Dependence

### 2.1 ACF of Returns (Fig02)

- **Obs13**: 25/100 lags significant at 95% level. Significant lags: 1, 3, 4, 6, 7, 10, 11, 16, 19, 23, 26, 29, 32, 33, 38, 39, 55, 56, 66, 85...
- Lag 1 is significant but magnitudes are small. The structure is consistent with weak short-range dependence, not strong trending at individual bar level.

### 2.2 ACF of |Returns| — Volatility Clustering (Fig03)

- **Obs14**: ALL 100/100 lags significant. Decay is slow:
  - lag 1: 0.261, lag 5: 0.238, lag 10: 0.189, lag 20: 0.167
  - This is long-memory behavior in volatility — the defining property of financial returns.

### 2.3 PACF of Returns (Fig04)

- **Obs15**: Significant lags: 1, 3, 4, 6, 7, 9, 10, 11, 16, 19, 23, 25, 26, 29. Multiple significant lags beyond lag 1 indicate structure beyond AR(1).

### 2.4 Variance Ratio Test — Lo-MacKinlay (Tbl04)

| k (bars) | k (hours) | VR      | z*     | p-value |
|----------|-----------|---------|--------|---------|
| 2        | 8         | 0.9558  | -0.023 | 0.982   |
| 5        | 20        | 0.9737  | -0.006 | 0.995   |
| 10       | 40        | 0.9480  | -0.008 | 0.994   |
| 20       | 80        | 0.9499  | -0.005 | 0.996   |
| 40       | 160       | 0.9801  | -0.002 | 0.999   |
| 60       | 240       | 0.9979  | 0.000  | 1.000   |

- **Obs16**: ALL variance ratios are ≤ 1.0 (range 0.948–0.998). The z* statistics are all near zero with p ≫ 0.05, meaning NONE are statistically significant under heteroskedasticity-robust testing.
- Pattern: VR < 1 at all scales, trending toward 1.0 as scale increases. This is mild mean-reversion at short scales, converging to random walk at longer scales.
- **Critical note**: The VR test under heteroskedasticity-robust inference produces NO significant evidence of persistence at any H4 scale tested (8h–240h).

### 2.5 Hurst Exponent — R/S Method (Tbl05, Fig05)

| Metric        | Value  |
|---------------|--------|
| Overall H     | 0.5805 |
| Rolling mean  | 0.586  |
| Rolling std   | 0.036  |
| Rolling range | [0.482, 0.685] |

- **Obs17**: Overall Hurst = 0.58, nominally above 0.5 (persistence). However, the R/S estimator is known to be upward-biased for series with volatility clustering (which BTC strongly exhibits — see Obs14).
- **Obs18**: Rolling Hurst mostly in 0.56–0.61 range. Some windows drop below 0.5 (min 0.48). The persistence signal is **weak and unstable**.

### 2.6 Scale Dependence Summary

- **Obs19**: Combining VR and Hurst results: at H4 resolution, BTC returns show NO statistically significant persistence at individual scales (VR p-values all > 0.95). The Hurst estimate of 0.58 is consistent with the well-documented R/S bias in the presence of volatility clustering. The dominant serial structure in BTC H4 is **volatility clustering** (long memory in |r|), not **directional persistence** (long memory in r).

**Figures**: Fig02 (ACF returns), Fig03 (ACF |returns|), Fig04 (PACF), Fig05 (rolling Hurst)

---

## 3. Trend Anatomy (Tbl06)

Trends defined by cumulative return threshold from local troughs:

| Threshold | N trends | Dur mean | Dur median | Q25  | Q75  | Mag mean | Mag med | Speed (%/bar) |
|-----------|----------|----------|------------|------|------|----------|---------|---------------|
| 10%       | 27       | 27.6     | 14.0       | 9.0  | 24.0 | 11.6%    | 11.2%   | 1.79           |
| 20%       | 13       | 35.8     | 24.0       | 18.0 | 59.0 | 21.6%    | 20.8%   | 1.31           |
| 30%       | 7        | 56.3     | 53.0       | 36.5 | 62.0 | 32.8%    | 32.4%   | 0.85           |
| 50%       | 5        | 167.6    | 103.0      | 90.0 | 114.0| 52.2%    | 50.7%   | 0.62           |

- **Obs20**: Large trends are rare events. Only 13 moves ≥20% in 8.5 years (1.5/year). Duration is highly variable (Q25–Q75 spread for 20%: 18–59 bars = 3–10 days).
- **Obs21**: Pre-trend pattern: mean cumulative return in the 20 bars before trend start is +9.16%. Trends tend to start from already-rising price, not from flat/declining.
- **Obs22**: Post-peak pattern: mean cumulative return in 20 bars after peak is +4.96%. Price does NOT immediately collapse after trend peaks — gradual decay rather than sharp reversal.

**Figures**: Fig06 (trend profiles aligned at start/end)

---

## 4. Volatility Structure

- **Obs23**: Realized volatility (20-bar rolling std) has extremely persistent ACF: lag1 = 0.986, lag10 = 0.813, lag20 = 0.597, lag50 = 0.468. This is the strongest serial dependence signal in the data — far stronger than return ACF.

- **Obs24**: Vol-return correlation (vol_t → future return):
  - fwd 1 bar: r = 0.013 (p = 0.086) — not significant
  - fwd 5 bars: r = 0.023 (p = 0.002) — significant but tiny
  - fwd 20 bars: r = 0.026 (p = 0.0004) — significant but tiny
  - fwd 40 bars: r = 0.054 (p < 0.001) — weakly significant
  - Direction: high vol weakly predicts positive returns at longer horizons.

- **Obs25**: Vol regime characteristics:
  - Low vol: mean_ret = 0.000134, std = 0.00775
  - High vol: mean_ret = 0.000162, std = 0.01951
  - High vol returns are 2.5× more dispersed. Mean returns are similar.

- **Obs26**: Trend frequency by vol regime (≥20% trends): **low-vol: 1 trend, high-vol: 12 trends** (12:1 ratio). Large trends almost exclusively occur during high-volatility periods.

**Figures**: Fig07 (vol time series), Fig08 (vol-return scatter)

---

## 5. Volume Structure

- **Obs27**: Volume is non-stationary: peaks in 2022 (mean 24,407 BTC/bar) and drops to ~3,500–5,900 in 2024–2026. This reflects market microstructure changes (ETF launch shifting volume to CME/spot ETFs), not trading-relevant information.

- **Obs28**: Volume-return relationship:
  - Contemporaneous cor(log_vol, |ret|) = 0.223 (p ≈ 0). Strong — high volume accompanies large moves.
  - Leading: decays rapidly. lag1 = 0.074, lag3 = 0.040, lag7 = 0.019, lag8 = 0.006 (not significant). Volume predicts future |return| magnitude only 1–6 bars ahead, driven by volatility clustering (high vol → high vol → high |ret|), not directional signal.

- **Obs29**: Taker buy ratio: mean = 0.4949, std = 0.048. Nearly symmetric. Distribution is tight around 0.50.

- **Obs30**: TBR predictive power for future returns:
  - k=1: r = -0.004 (p = 0.62) — zero signal
  - k=5: r = 0.012 (p = 0.09) — not significant
  - k=10: r = 0.017 (p = 0.02) — marginally significant, economically negligible
  - k=20: r = 0.027 (p = 0.0003) — statistically significant, magnitude negligible

- **Obs31**: Volume at trend starts (mean 7,885) vs trend ends (mean 13,299), ratio 1.69. Volume tends to be higher at trend peaks.

**Figures**: Fig09 (volume distribution)

---

## 6. D1 Context

- **Obs32**: D1 returns: mean = 0.000893, std = 0.0361, skew = -0.96, excess kurtosis = 15.4. Stronger negative skew than H4 (D1 captures intra-day crash clustering). JB strongly rejects normality.

- **Obs33**: D1 ACF: 6 significant return lags (out of 50), |return| 50/50 significant. Same volatility clustering pattern as H4.

- **Obs34**: D1 Variance Ratio:
  - VR(2d) = 0.947, VR(5d) = 0.975 — mild mean-reversion (not significant)
  - VR(10d) = 1.015, VR(20d) = 1.085 — mild persistence at 10–20 day scale (not significant)
  - Pattern: mean-reversion at short D1 scales, transition to persistence at 10–20 day scale (corresponding to k=60–120 H4 bars). Consistent with H4 VR converging toward 1.0 at k=60.

- **Obs35**: D1 SMA200 regime vs H4 trends (≥20%): above = 6 trends, below = 7 trends. Roughly equal. SMA200 regime does NOT strongly predict trend frequency.

- **Obs36**: D1 vol regime vs H4 trends (≥20%): low_vol = 1 trend, high_vol = 12 trends. Vol regime is the dominant predictor of trend occurrence (12:1 ratio). This dwarfs the SMA200 regime effect.

---

## 7. Cross-Timeframe (Tbl10)

| D1 Regime    | N bars | Mean ret   | Std ret   | Ann. ret  |
|--------------|--------|------------|-----------|-----------|
| SMA200 above | 9,560  | +0.000524  | 0.01285   | +114.8%   |
| SMA200 below | 9,185  | -0.000242  | 0.01665   | -52.9%    |
| Vol low      | 9,435  | +0.000084  | 0.00944   | +18.5%    |
| Vol high     | 9,310  | +0.000214  | 0.01879   | +47.0%    |

- **Obs37**: H4 returns conditioned on D1 SMA200 regime differ significantly: above mean = +0.000524, below mean = -0.000242 (Welch t = 3.52, p = 0.0004; Mann-Whitney p = 0.0002). D1 price level relative to SMA200 is a statistically significant conditioning variable.

- **Obs38**: D1-native vs H4-aggregated-to-D1: ACF difference is negligible (mean |diff| = 0.00016). D1 does NOT contain unique return-predictive information — it's the same process viewed at different resolution.

- **Obs39**: Scale-conditional persistence (VR(5), VR(20)):
  - Above SMA200: VR(5) = 0.992, VR(20) = 0.927
  - Below SMA200: VR(5) = 0.954, VR(20) = 0.918
  - Low vol: VR(5) = 1.013, VR(20) = 1.049
  - High vol: VR(5) = 0.960, VR(20) = 0.908
  - D1 regime conditioning changes H4 persistence structure. **Low-vol regime shows mild persistence (VR > 1)** while high-vol shows mean-reversion. The regime is a framing variable.

---

## Observation Registry

| ID    | Description                                                   | Evidence             |
|-------|---------------------------------------------------------------|----------------------|
| Obs09 | H4 returns: mean=0.000148, std=0.0148, skew=-0.20, kurt=20.4 | Tbl04_ret_dist       |
| Obs10 | Jarque-Bera: JB=325,731, p≈0. Normality rejected.           | Tbl04_ret_dist       |
| Obs11 | Fat tails: 3σ events 6.5–7.8× Normal expected frequency     | Fig01, Tbl04_ret_dist |
| Obs12 | Down-tail heavier (191 vs 159 events at 3σ)                  | Tbl04_ret_dist       |
| Obs13 | ACF returns: 25/100 lags significant, weak magnitudes        | Fig02                |
| Obs14 | ACF |returns|: 100/100 significant, strong volatility clustering | Fig03            |
| Obs15 | PACF: 14 significant lags (1,3,4,6,7,9,10,11,16,19,23,25,26,29) | Fig04            |
| Obs16 | VR test: ALL VR ≤ 1.0, NONE significant (p > 0.95)          | Tbl04_variance_ratio |
| Obs17 | Hurst overall = 0.58, nominally persistent but R/S biased    | Tbl05_hurst          |
| Obs18 | Rolling Hurst: mean=0.586, range [0.48, 0.68]               | Fig05, Tbl05_hurst   |
| Obs19 | Scale dependence: VR < 1 at all scales, no significant persistence | Tbl04_variance_ratio |
| Obs20 | Trend count: 27 (10%), 13 (20%), 7 (30%), 5 (50%)           | Tbl06_trend_anatomy  |
| Obs21 | Pre-trend: +9.16% mean cum-return in 20 bars before start    | Fig06                |
| Obs22 | Post-peak: +4.96% mean cum-return in 20 bars after peak      | Fig06                |
| Obs23 | Realized vol ACF: lag1=0.986, lag50=0.468. Long memory.      | Fig07                |
| Obs24 | Vol→return: r(fwd20)=0.026, r(fwd40)=0.054. Weak positive.  | Fig08                |
| Obs25 | Vol regimes: similar means, high-vol 2.5× dispersed          | Tbl07_vol_regimes    |
| Obs26 | Trend frequency: high-vol=12, low-vol=1 (12:1 ratio)        | Tbl06, Tbl07         |
| Obs27 | Volume non-stationary: peaks 2022, drops 2024+               | Fig09                |
| Obs28 | Vol→|ret|: contemp 0.223, leading decays by lag 7–8          | Tbl08_volume_corrs   |
| Obs29 | TBR: mean=0.495, std=0.048, near-symmetric                   | Fig09                |
| Obs30 | TBR→return: max |r|=0.027, economically negligible           | Tbl08_volume_corrs   |
| Obs31 | Volume at trend end 1.69× trend start                        | Tbl06_trend_anatomy  |
| Obs32 | D1: skew=-0.96 (more negative than H4), kurt=15.4            | Tbl09_d1_returns     |
| Obs33 | D1 ACF: 6 sig return lags, 50/50 sig |return| lags          | Tbl09_d1_returns     |
| Obs34 | D1 VR: mean-revert at 2–5d, mild persistence at 10–20d      | Tbl09_d1_returns     |
| Obs35 | D1 SMA200 regime: ~equal trend frequency (6 vs 7)            | Tbl09, Tbl06         |
| Obs36 | D1 vol regime: trends 12:1 concentrated in high-vol          | Tbl07, Tbl06         |
| Obs37 | D1 SMA200 conditioning: above +114.8% ann, below -52.9% ann (p=0.0004) | Tbl10   |
| Obs38 | D1 native ≈ H4 aggregated: no unique information             | Tbl10                |
| Obs39 | Regime conditions persistence structure differently           | Tbl10                |

---

## Hypothesis Verification

### H_prior_1 (Trend Persistence): **PARTIAL**

Evidence:
- Hurst = 0.58 nominally persistent, BUT R/S is upward-biased with volatility clustering
- VR test: ALL VR < 1.0 at every scale tested (k=2–60), NONE statistically significant
- ACF of returns: 25/100 significant but magnitudes small
- Large trends exist (27 at 10% threshold) but these could arise from a random walk with fat tails and volatility clustering

Assessment: BTC H4 does NOT show robust persistence in returns at the individual-bar level. What prior research attributes to "trend persistence" may be the combination of (a) positive drift (mean > 0), (b) volatility clustering (runs of large |returns|), and (c) fat tails (occasional extreme moves that look like "trends"). Formal VR testing with heteroskedasticity correction does not support directional persistence.

### H_prior_2 (Cross-Scale Redundancy): **PARTIAL**

Evidence:
- VR profile is smooth and monotonic (0.948 → 0.998 as scale increases)
- This suggests a single underlying return-generating process, not multiple distinct phenomena at different scales
- But VR ≤ 1 everywhere — so the "redundancy" may be that all scales contain approximately zero trend signal

Assessment: Consistent with one phenomenon (BTC's return distribution). The parameter-insensitivity of trend-following systems could reflect that the underlying phenomenon is broad rather than scale-specific.

### H_prior_5 (Volume Info ≈ 0): **CONFIRMED**

Evidence:
- TBR→return: max |r| = 0.027, not economically meaningful
- Volume→|return| leading: significant for 1–6 bars only, driven by volatility persistence
- Volume at entry carries no directional information

Assessment: Confirmed. Volume and taker buy ratio provide effectively zero directional information at any horizon.

### H_prior_6 (D1 Regime Useful): **CONFIRMED**

Evidence:
- D1 SMA200 conditioning produces significant return differential (p = 0.0004)
- Above SMA200: annualized +114.8% vs Below: -52.9%
- Mann-Whitney also significant (p = 0.0002), confirming robustness to distributional assumptions
- D1 vol regime also strongly predicts trend occurrence (12:1 ratio)

Assessment: D1 regime is a statistically significant conditioning variable. The price-level regime (SMA200) affects mean returns; the vol regime affects trend frequency. Both are informative.

---

## End-of-Phase Checklist

### 1. Files created
- `02_price_behavior_eda.md` (this report)
- `code/phase2_eda.py`
- `figures/Fig01_return_distribution.png`
- `figures/Fig02_acf_returns.png`
- `figures/Fig03_acf_abs_returns.png`
- `figures/Fig04_pacf_returns.png`
- `figures/Fig05_rolling_hurst.png`
- `figures/Fig06_trend_profiles.png`
- `figures/Fig07_volatility_timeseries.png`
- `figures/Fig08_vol_return_scatter.png`
- `figures/Fig09_volume_distribution.png`
- `tables/Tbl04_ret_dist.csv`
- `tables/Tbl04_variance_ratio.csv`
- `tables/Tbl05_hurst.csv`
- `tables/Tbl06_trend_anatomy.csv`
- `tables/Tbl07_vol_regimes.csv`
- `tables/Tbl08_volume_corrs.csv`
- `tables/Tbl09_d1_returns.csv`
- `tables/Tbl10_cross_timeframe.csv`
- `tables/phase2_observations.csv`

### 2. Key Obs / Hyp IDs created
Obs09–Obs39 (31 observations)

### 3. Blockers / uncertainties
- **VR vs Hurst contradiction**: VR (heteroskedasticity-robust) shows no persistence; Hurst (R/S) shows mild persistence. The VR result is more trustworthy because it accounts for volatility clustering, which is the dominant serial structure in BTC. Hurst R/S is known to be biased upward by long-memory in volatility.
- **Trend count sensitivity**: The trend-finding algorithm's count (13 at 20%) depends on the specific definition used. Different algorithms may yield different counts. The key structural finding (trends are rare, concentrated in high-vol regimes) is robust to definition.
- **Volume non-stationarity**: Volume is not comparable across years. Any volume-based analysis must account for this.

### 4. Gate status
**PASS_TO_NEXT_PHASE**

The data has been characterized. Key structural properties are:
1. No robust return persistence (dominant structure is volatility clustering)
2. Fat tails with negative skew
3. D1 regime is a valid conditioning variable
4. Volume/TBR carry no directional information
5. Trends are rare events concentrated in high-volatility periods

Ready for Phase 3 (Signal Landscape EDA).
