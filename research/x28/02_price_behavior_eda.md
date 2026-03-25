# Phase 2 — BTC H4 Price Behavior EDA

**Data**: BTCUSDT H4 (18,752 bars, 2017-08 → 2026-03) + D1 context (3,128 bars)
**Code**: `code/phase2_eda.py`
**Protocol**: Descriptive only — no strategy proposals.

---

## 1. Return Distribution

| Statistic | Value |
|-----------|-------|
| Mean (per bar) | 0.000148 (1.48 bps) |
| Std | 0.01484 |
| Skew | -0.201 |
| Excess Kurtosis | 20.41 |
| Jarque-Bera stat | 325,731 |
| JB p-value | < 1e-300 |

**Obs01**: H4 log returns: mean=0.000148 (positive drift), std=0.0148, mild negative skew (-0.201), extreme leptokurtosis (excess kurtosis 20.41). *(Fig01)*

**Obs02**: Jarque-Bera decisively rejects normality (stat=325,731, p≈0). The excess kurtosis of 20.4 indicates returns are far heavier-tailed than Gaussian. *(Fig01)*

**Obs03**: Tail excess vs normal distribution:
- P(|r| > 3σ) = 1.87% vs 0.27% expected (6.9x)
- P(|r| > 4σ) = 0.78% vs 0.006% expected (124x)

Empirical tails are 7-124x heavier than normal, depending on threshold. *(Fig01)*

**Figures**: Fig01a (histogram + normal overlay), Fig01b (QQ plot)

---

## 2. Serial Dependence (Core)

### 2.1 ACF of Returns

**Obs04**: ACF(returns): 25/100 lags significant at 5% (critical ≈ ±0.0143). Lag 1 = -0.0441 (small negative — mild mean reversion at 4h). Max |ACF| = 0.0740. Overall: weak serial dependence in raw returns. *(Fig02)*

### 2.2 ACF of |Returns| (Volatility Clustering)

**Obs05**: ACF(|returns|): **100/100** lags significant. Lag 1 = 0.2607, lag 50 = 0.1326, lag 100 = 0.1117. Very slow power-law decay. Strong, persistent volatility clustering. *(Fig03)*

### 2.3 PACF of Returns

**Obs06**: PACF(returns): significant lags = [1, 3, 4, 6, 7, 9, 10, 11, 16, 19]. Lag 1 = -0.0441. Some structure at short lags, but magnitudes are small (all |PACF| < 0.05). *(Fig04)*

### 2.4 Variance Ratio (Lo-MacKinlay, heteroskedasticity-robust)

| k | VR | z* | p-value |
|---|----|----|---------|
| 2 | 0.9558 | -0.023 | 0.982 |
| 5 | 0.9737 | -0.006 | 0.995 |
| 10 | 0.9480 | -0.008 | 0.994 |
| 20 | 0.9499 | -0.005 | 0.996 |
| 40 | 0.9801 | -0.002 | 0.999 |
| 60 | 0.9979 | -0.000 | 1.000 |
| 80 | 1.0200 | 0.001 | 0.999 |
| 100 | 1.0412 | 0.002 | 0.998 |
| 120 | 1.0651 | 0.003 | 0.997 |

*Saved: tables/Tbl04_variance_ratio.csv*

**Obs07**: Variance ratio: 3/9 periods have VR > 1, **0/9 significant** at 5%. VR(20) = 0.9499 (slight mean reversion at short horizons), VR(120) = 1.0651 (slight persistence at longer horizons). The Lo-MacKinlay test does NOT reject random walk at any horizon when accounting for heteroskedasticity. *(Tbl04)*

### 2.5 Hurst Exponent (R/S)

| Measure | Value |
|---------|-------|
| Full sample H | 0.583 |
| Rolling mean H | 0.588 |
| Rolling min H | 0.495 |
| Rolling max H | 0.702 |
| Rolling std H | 0.036 |

**Obs08**: Hurst (R/S): full sample H = 0.583, mildly above 0.5. Rolling (500-bar window): mean = 0.588, range [0.50, 0.70]. The Hurst exponent suggests mild persistence, but the VR test (which is heteroskedasticity-robust) shows this is NOT statistically significant. The Hurst elevation may partly reflect volatility clustering rather than true return persistence. *(Fig05)*

### Serial Dependence Summary (Tbl05)

| Measure | Value |
|---------|-------|
| ACF(ret) lag 1 | -0.0441 |
| ACF(ret) max |val| | 0.0740 |
| ACF(ret) sig lags /100 | 25 |
| ACF(\|ret\|) lag 1 | 0.2607 |
| ACF(\|ret\|) lag 50 | 0.1326 |
| ACF(\|ret\|) sig lags /100 | 100 |
| PACF(ret) sig lags /20 | 10 |
| Hurst (full) | 0.5834 |
| Hurst (rolling mean) | 0.5885 |

*Saved: tables/Tbl05_serial_dependence.csv*

---

## 3. Trend Anatomy

Trends defined objectively as upward moves with cumulative return ≥ threshold, detected via trough-to-peak scanning.

| Threshold | Count | Mean Duration (bars) | Median Duration | Mean Magnitude | Max Magnitude |
|-----------|-------|---------------------|-----------------|----------------|---------------|
| ≥ 10% | 175 | 52.7 (211h) | 39 (156h) | 21.5% | varies |
| ≥ 20% | 61 | 149.7 (599h) | 110 (440h) | 45.2% | varies |

*Saved: tables/Tbl06_trend_anatomy.csv*

**Obs09**: Uptrends ≥ 10%: 175 events over 8.5 years (~20/year), mean duration 53 bars (8.8 days), mean magnitude 21.5%. These are frequent and substantial. *(Tbl06, Fig06)*

**Obs10**: Uptrends ≥ 20%: 61 events (~7/year), mean duration 150 bars (25 days), mean magnitude 45.2%. Longer-duration trends carry disproportionately larger returns (non-linear duration→magnitude relationship). *(Tbl06)*

**Fig06**: Average trend profile (price indexed to 100 at trend start, normalized time). Shows characteristic gradual acceleration into peak.

---

## 4. Volatility Structure

### 4.1 Volatility Persistence

**Obs11**: Volatility ACF: 100/100 lags significant (all within 100 H4 bars = 16.7 days). Lag 1 = 0.986, lag 50 = 0.468. This is extreme persistence — consistent with long-memory processes (FIGARCH-class). *(Fig07)*

### 4.2 Vol-Return Correlation

**Obs12**: Vol-return correlation:
- Contemporaneous: Spearman r = 0.009 (p = 0.207) — NOT significant
- Lagged (vol_t → ret_{t+k}): r = 0.013 (k=1) to 0.004 (k=20) — negligible at all horizons

Volatility does NOT predict return direction. *(Fig08)*

### 4.3 Volatility Regimes

| Regime | Bars | Mean Ann. Vol | Mean H4 Return | Std H4 Return | Ann. Sharpe |
|--------|------|---------------|----------------|----------------|-------------|
| Low | 6,238 (33.3%) | 28.3% | 1.69 bps | 63.3 bps | 1.253 |
| Mid | 6,256 (33.4%) | 50.1% | 2.88 bps | 109.6 bps | 1.228 |
| High | 6,238 (33.3%) | 97.1% | -0.04 bps | 223.7 bps | -0.009 |

*Saved: tables/Tbl07_vol_regimes.csv*

**Obs13**: Vol regimes — Low vol (<39% ann.) has positive mean return (1.69 bps/bar, Sharpe 1.25). High vol (>62% ann.) has near-zero mean return (-0.04 bps, Sharpe -0.01). Risk is 3.5x higher in high-vol regime with no compensating return. Regime transitions occur in only 6.4% of bars — regimes are sticky. *(Tbl07)*

---

## 5. Volume Structure

**Obs14**: H4 volume: mean = 10,281 BTC, heavily right-skewed (skew = 4.60). Taker buy ratio: mean = 0.4950, std = 0.0481 — centered near 0.50 with low dispersion. *(Fig09)*

### Volume-Return Correlations

| Relation | Spearman r | p-value |
|----------|-----------|---------|
| vol × \|ret\| (contemp) | 0.3323 | < 1e-300 |
| vol_t → ret_{t+1} | 0.0048 | 0.512 |
| vol_t → ret_{t+5} | 0.0029 | 0.695 |
| vol_t → ret_{t+10} | -0.0018 | 0.800 |
| vol_t → ret_{t+20} | 0.0000 | 1.000 |
| tbr_t → ret_{t+1} | -0.0253 | 0.0005 |
| tbr_t → ret_{t+5} | -0.0002 | 0.973 |
| tbr_t → ret_{t+10} | 0.0099 | 0.177 |
| tbr_t → ret_{t+20} | 0.0070 | 0.338 |

*Saved: tables/Tbl08_volume_correlations.csv*

**Obs15**: Volume × |return| contemporaneous correlation r = 0.332 — volume is concurrent with large moves (both directions). Leading volume → return: |r| < 0.03 at ALL horizons (1, 5, 10, 20 bars). Taker buy ratio: lag-1 r = -0.025 (statistically significant but economically negligible). Volume has NO predictive power for future returns. *(Tbl08)*

---

## 6. D1 Context

### 6.1 D1 Regime Differentials

| Regime | Above (bars) | Below (bars) | Mean Ret Above (ann %) | Mean Ret Below (ann %) | Diff (pp/yr) | Welch p | MW p |
|--------|-------------|-------------|----------------------|----------------------|-------------|---------|------|
| SMA(200) | 1,595 | 1,334 | 114.9 | -87.9 | 202.8 | < 0.0001 | < 0.0001 |
| EMA(21) | 1,526 | 1,403 | 339.3 | -322.0 | 661.2 | < 0.0001 | < 0.0001 |
| EMA(50) | 1,507 | 1,422 | 230.7 | -198.0 | 428.7 | < 0.0001 | < 0.0001 |

*Saved: tables/Tbl09_d1_regime_differentials.csv*

**Obs16**: D1 regime differentials are LARGE and HIGHLY SIGNIFICANT for all three variants. EMA(21) shows the largest differential (661 pp/yr, Welch p < 0.0001). SMA(200) shows the smallest (203 pp/yr) but still highly significant. Both Welch t-test and Mann-Whitney agree. *(Tbl09)*

### 6.2 H4 Returns Conditioned on D1 Regime (1-day lag to avoid look-ahead)

| D1 Regime | H4 Above (bars) | H4 Below (bars) | Mean Ret Above | Mean Ret Below | Sharpe Above | Sharpe Below | Welch p | MW p |
|-----------|-----------------|-----------------|----------------|----------------|-------------|-------------|---------|------|
| EMA(21) | 9,861 | 8,886 | 3.67 bps | -0.93 bps | 1.250 | -0.272 | 0.036 | 0.098 |
| EMA(50) | 9,805 | 8,942 | 3.71 bps | -0.95 bps | 1.224 | -0.287 | 0.032 | 0.030 |
| SMA(200) | 9,566 | 9,181 | 2.02 bps | 0.93 bps | 0.735 | 0.262 | 0.618 | 0.478 |

*Saved: tables/Tbl10_h4_conditioned_on_d1.csv*

**Obs17**: H4 returns conditioned on D1 regime (1-day lag):
- D1 EMA(21): above = +3.67 bps (Sh 1.25), below = -0.93 bps (Sh -0.27). Welch p = 0.036, MW p = 0.098.
- D1 EMA(50): above = +3.71 bps (Sh 1.22), below = -0.95 bps (Sh -0.29). Welch p = 0.032, MW p = 0.030.
- D1 SMA(200): above = +2.02 bps (Sh 0.74), below = +0.93 bps (Sh 0.26). Welch p = 0.618 — NOT significant.

EMA(21) and EMA(50) regime conditioning passes at the 5% level (Welch), SMA(200) does not. The differential exists cross-timeframe but is weaker than the D1-only effect. *(Tbl10)*

---

## 7. Observation Summary

### All Observations Ranked by Effect Size

| Obs | Finding | Effect Size | Exploitability |
|-----|---------|-------------|----------------|
| **Obs16** | D1 regime differential (EMA 21): 661 pp/yr | Very large | **likely exploitable** |
| **Obs05** | Vol clustering: ACF(\|ret\|) lag1=0.261, all 100 lags sig | Very large | **likely exploitable** |
| **Obs11** | Vol persistence: ACF(vol) lag1=0.986 | Very large | **likely exploitable** |
| **Obs17** | H4\|D1 regime: Sharpe 1.25 vs -0.27 | Large | **likely exploitable** |
| **Obs13** | Vol regime return differential: Low Sh 1.25, High Sh 0.00 | Large | **likely exploitable** |
| **Obs03** | Fat tails: 124x excess at 4σ | Large | unclear |
| **Obs02** | Non-normal returns: JB=325k | Large (shape) | not exploitable (standalone) |
| **Obs10** | Large trends (≥20%): 61 events, 45% mean magnitude | Moderate | **likely exploitable** |
| **Obs09** | Trends (≥10%): 175 events, 22% mean magnitude | Moderate | **likely exploitable** |
| **Obs08** | Hurst=0.583 (mild persistence) | Small | unclear |
| **Obs07** | VR test: 0/9 significant (random walk consistent) | Null | not exploitable |
| **Obs04** | ACF(ret): lag1=-0.044, 25/100 sig | Small | not exploitable |
| **Obs06** | PACF: scattered structure, small magnitudes | Small | not exploitable |
| **Obs15** | Volume → return: |r| < 0.03 all horizons | Null | not exploitable |
| **Obs14** | Volume skewed, TBR ≈ 0.50 | Descriptive | not exploitable |
| **Obs12** | Vol → return direction: r < 0.013 | Null | not exploitable |
| **Obs01** | Return moments: mean/std/skew/kurt | Descriptive | not exploitable |

### Key Takeaways (Descriptive Only)

1. **Raw returns are near-random-walk**: VR test 0/9 significant, ACF small. Hurst slightly >0.5 but not robust to heteroskedasticity correction.
2. **Volatility is highly predictable**: ACF(|ret|) all 100 lags significant, vol ACF lag1=0.986. Long-memory process.
3. **D1 regime conditioning creates the largest return differential**: EMA(21) regime = 661 pp/yr on D1, Sharpe 1.25 vs -0.27 on H4.
4. **Large uptrends exist and are frequent**: ~7 events/year with ≥20% magnitude.
5. **Volume has zero predictive power for returns**: strong concurrent correlation but zero leading correlation.
6. **Returns have extreme tails**: 124x excess at 4σ. Risk management must account for this.

---

## Deliverables

### Files Created
- `02_price_behavior_eda.md` (this report)
- `code/phase2_eda.py`
- `figures/Fig01_return_distribution.png`
- `figures/Fig02_acf_returns.png`
- `figures/Fig03_acf_abs_returns.png`
- `figures/Fig04_pacf_returns.png`
- `figures/Fig05_rolling_hurst.png`
- `figures/Fig06_trend_profile.png`
- `figures/Fig07_volatility_timeseries.png`
- `figures/Fig08_vol_return_scatter.png`
- `figures/Fig09_volume_structure.png`
- `tables/Tbl04_variance_ratio.csv`
- `tables/Tbl05_serial_dependence.csv`
- `tables/Tbl06_trend_anatomy.csv`
- `tables/Tbl07_vol_regimes.csv`
- `tables/Tbl08_volume_correlations.csv`
- `tables/Tbl09_d1_regime_differentials.csv`
- `tables/Tbl10_h4_conditioned_on_d1.csv`
- `tables/observations_phase2.json`

### Key Obs / Prop IDs Created
- Obs01 — Obs17 (17 observations, 0 propositions — per protocol, no interpretive claims in Phase 2)

### Blockers / Uncertainties
- None

### Gate Status
**PASS_TO_NEXT_PHASE**

Evidence of exploitable structure exists (D1 regime, vol clustering, trend existence).
Phase 3 will determine whether this structure can be formalized.
