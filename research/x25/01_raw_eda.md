# Phase 1: Raw Exploratory Reconnaissance

**Date**: 2026-03-10
**Data**: bars_btcusdt_h1_4h_1d.csv, H4 interval (18,662 bars, 2017-08 → 2026-02)
**Protocol**: Observation before interpretation. No formalization, no suggestion, no design.

---

## 1. Data Audit Summary

See `00_data_audit.md` for full details.

- **Schema**: 13 columns, 96,423 rows total. H4=18,662, D1=3,110, H1=74,651.
- **Timestamps**: Both H4 and D1 are monotonic increasing, zero anomalous gaps.
- **Duplicates**: None.
- **H4/D1 alignment**: 3,109 of 3,111 calendar days have exactly 6 H4 bars. Two exceptions are boundary days (2017-08-17 start, 2026-02-21 end) — expected edge effects.
- **close_time**: 20 H4 bars have close_time != open_time + 14,400,000 - 1. D1: all 3,110 correct.
- **Volume**: No negative values. 17 H4 bars with zero volume (also zero taker_buy_base_vol). D1 has no zeros.
- **Taker buy ratio**: Range [0.085, 0.924] for H4, [0.175, 0.811] for D1. Mean ≈ 0.495, median ≈ 0.496. Never exceeds 1.0 or goes below 0.0.

---

## 2. Taker Buy Ratio — Full Period

[Fig01](figures/Fig01_h4_close_tbr.png): H4 close price (log scale) + taker buy ratio.

- TBR oscillates around 0.5 across the entire 8.5-year sample.
- Visually, variance of TBR appears to narrow in certain periods and widen in others.
- No obvious persistent departure from 0.5 lasting months.

[Fig02](figures/Fig02_tbr_yearly_hist.png): Yearly histograms.

- **2017**: Flat, dispersed. Widest distribution. n=820 (partial year).
- **2018**: Broad, slight left skew. Peak near 0.48.
- **2019**: Narrower than 2018, slight bimodal appearance with sub-peaks near 0.44 and 0.50.
- **2020**: Unimodal, moderate spread, centered ~0.49.
- **2021**: Narrow, sharply peaked at ~0.49.
- **2022**: Extremely concentrated. By far the narrowest distribution. Peak density >25.
- **2023**: Still concentrated but slightly wider than 2022. Clear single peak.
- **2024**: Returns to broader shape similar to 2020.
- **2025**: Dispersed, flatter. Partial year (n=2,190).
- **2026**: n=309 only. Broad, slight left tail.

The distribution shape changes across years. The concentration in 2022-2023 vs dispersion in 2017, 2025 is visible.

---

## 3. Volume by Bar Type

Bar classification: up_strong (return > +2%, n=1,078), down_strong (return < -2%, n=1,051), sideway (rest, n=16,532).

[Fig03](figures/Fig03_volume_by_bartype.png): Volume distribution (log scale).

- Both up_strong and down_strong have substantially higher volume than sideway.
- up_strong median = 12,504 BTC, down_strong median = 13,271 BTC, sideway median = 5,534 BTC.
- up_strong vs down_strong volume difference is NOT significant (p=0.149, rank-biserial=0.036).
- Strong-move vs sideway: highly significant (p < 1e-100, rank-biserial ≈ -0.43 to -0.47).

[Fig04](figures/Fig04_tbr_by_bartype.png): Taker buy ratio by bar type.

- Cleanest separation of all comparisons.
- up_strong median TBR = 0.523, down_strong median TBR = 0.467. Difference = 0.056.
- Mann-Whitney p = 4.1e-228, rank-biserial = -0.807.
- sideway median TBR = 0.496 — between the two, closer to 0.5.
- This is a **contemporaneous** relationship (same bar), not predictive.

[Tbl01](tables/Tbl01_bar_type_tests.csv): Full test results.

---

## 4. Autocorrelation

[Fig05](figures/Fig05_acf_comparison.png): ACF lag 1..20.

- **Volume**: Highest persistence. ACF(1) = 0.821, ACF(5) = 0.742, ACF(20) = 0.607. Very slow decay.
- **Taker buy ratio**: Moderate persistence. ACF(1) = 0.406, ACF(5) = 0.307, ACF(20) = 0.193. Decays roughly linearly.
- **H4 returns**: Near zero at all lags. ACF(1) = -0.046 (slight negative), all others within ±0.05. No meaningful persistence.

Volume is the most persistent series. TBR has non-trivial memory out to at least 20 bars (3.3 days). Returns show no usable autocorrelation.

---

## 5. Predictive Content (Raw)

[Fig06a](figures/Fig06a_tbr_vs_fwd_t1.png), [Fig06b](figures/Fig06b_tbr_vs_fwd_t6.png), [Fig06c](figures/Fig06c_tbr_vs_fwd_t24.png): Scatter plots (5,000-point subsample).

[Tbl02](tables/Tbl02_forward_corr.csv):

| Horizon | Spearman ρ | p-value | n |
|---------|-----------|---------|-------|
| t+1 | -0.0258 | 4.4e-04 | 18,621 |
| t+6 | -0.0289 | 7.9e-05 | 18,621 |
| t+24 | -0.0039 | 0.596 | 18,621 |

- All correlations are near zero.
- t+1 and t+6 are statistically significant (large n) but the magnitude is ≈ -0.03.
- t+24 is not significant. The already-weak signal vanishes at 4-day horizon.
- Sign is negative: higher TBR is associated with slightly lower future returns. Counter-intuitive if TBR were a pure "buying pressure" proxy.
- Scatter plots show amorphous clouds with no visible structure.

---

## 6. Regime Dependency

Regime: bull (close > EMA(126)), bear (close <= EMA(126)).
Bull n=9,783, Bear n=8,838.

[Fig07](figures/Fig07_regime_corr.png): Grouped bar chart.

[Tbl03](tables/Tbl03_regime_corr.csv):

| Regime | Horizon | Spearman ρ | p-value |
|--------|---------|-----------|---------|
| bull | t+1 | -0.0284 | 0.005 |
| bull | t+6 | -0.0274 | 0.007 |
| bull | t+24 | -0.0159 | 0.115 |
| bear | t+1 | -0.0241 | 0.023 |
| bear | t+6 | -0.0329 | 0.002 |
| bear | t+24 | +0.0076 | 0.473 |

- At t+1 and t+6: both regimes show similar weak negative correlations (ρ ≈ -0.024 to -0.033). No regime differentiation.
- At t+24: bull is slightly negative (-0.016, n.s.), bear flips slightly positive (+0.008, n.s.). Both non-significant.
- The regime split does not reveal a hidden predictive relationship.

---

## 7. Stationarity

[Fig08](figures/Fig08_rolling_spearman.png): Rolling Spearman ρ (window=500 bars ≈ 83 days) between TBR and forward 6-bar return.

- The rolling correlation oscillates between approximately -0.10 and +0.08.
- It crosses zero frequently — no stable sign.
- Periods of weakly positive correlation alternate with weakly negative. Typical half-cycle is 3-6 months.
- No visible trend (drift) in the mean level over 8+ years.
- The relationship between TBR and forward returns is non-stationary in sign.

---

## 8. Observation Log

### Observations

**Obs01** — TBR is contemporaneously linked to bar direction, not predictively.
Up bars have median TBR = 0.523, down bars = 0.467 (Δ = 0.056, p = 4.1e-228). This describes what happened in the bar, not what happens next.
Support: [Fig04], [Tbl01]

**Obs02** — TBR has moderate autocorrelation (ACF(1) = 0.41) with slow decay.
At lag 20 (3.3 days), ACF is still 0.19. This memory is much stronger than returns (≈ 0) but weaker than volume (0.82).
Support: [Fig05]

**Obs03** — Raw TBR-to-forward-return correlation is near zero at all tested horizons.
Magnitudes: |ρ| ≤ 0.029. Statistically significant at t+1 and t+6 due to large n, but economically negligible.
Support: [Fig06a], [Fig06b], [Fig06c], [Tbl02]

**Obs04** — The sign of TBR→forward return is weakly negative.
Higher TBR is associated with marginally lower future returns, not higher. This holds at t+1 (ρ=-0.026) and t+6 (ρ=-0.029).
Support: [Tbl02]

**Obs05** — Volume is substantially higher during strong-move bars (both directions) vs sideway bars.
Median strong-move volume ≈ 12,500-13,300 BTC vs sideway ≈ 5,500 BTC. But up_strong vs down_strong volumes are indistinguishable (p=0.149).
Support: [Fig03], [Tbl01]

**Obs06** — TBR distribution shape varies across years.
2022 is extremely concentrated (narrowest histogram). 2017 and 2025 are the most dispersed. The series is not identically distributed across years.
Support: [Fig02]

**Obs07** — Rolling TBR→forward return correlation is non-stationary and oscillates around zero.
Window=500 bars: range approximately [-0.10, +0.08], frequent zero crossings. No stable relationship.
Support: [Fig08]

**Obs08** — Regime conditioning (bull/bear via EMA(126)) does not improve TBR predictive content.
Both regimes show similar weak negative correlations at short horizons. At t+24, both are non-significant with different signs.
Support: [Fig07], [Tbl03]

**Obs09** — H4 returns show near-zero autocorrelation at all lags.
ACF(1) = -0.046, all other lags within ±0.05. Returns are effectively uncorrelated.
Support: [Fig05]

**Obs10** — Data quality is high: zero gaps, zero duplicates, monotonic timestamps.
17 zero-volume H4 bars exist but are a negligible fraction (0.09%). No negative values anywhere.
Support: [00_data_audit.md]

### Non-findings

**Obs11 (non-finding)** — Volume does NOT differentiate up_strong from down_strong bars.
Despite testing, up_strong and down_strong have statistically indistinguishable volume distributions (p=0.149, rank-biserial=0.036). Volume is elevated during large moves in either direction equally.
Support: [Fig03], [Tbl01]

**Obs12 (non-finding)** — TBR does NOT have meaningful predictive power at the 24-bar (4-day) horizon.
ρ = -0.004, p = 0.596. Whatever weak signal exists at t+1/t+6 does not survive to t+24.
Support: [Tbl02]

### Possible spurious patterns

**Obs13 (possibly spurious)** — The weak negative TBR→forward return correlation at t+1/t+6.
Magnitude |ρ| < 0.03. The statistical significance is driven entirely by n=18,621. The rolling analysis (Fig08) shows this sign is not stable over time — it oscillates. This could be an artifact of autocorrelation in TBR contaminating a contemporaneous relationship.
Support: [Fig08], [Tbl02]

**Obs14 (possibly spurious)** — The apparent regime difference at t+24 (bull: ρ=-0.016 vs bear: ρ=+0.008).
Both values are non-significant (p > 0.11). The sign flip could be pure noise. With only two subsamples (n≈9,000 each), a |ρ| of 0.01 is well within sampling variability.
Support: [Fig07], [Tbl03]

---

## Phase 1 Checklist

| Item | Status |
|------|--------|
| Data audit complete | DONE |
| Schema/dtypes/range/gaps verified | DONE |
| H4/D1 alignment checked | DONE |
| Volume/taker anomaly check | DONE |
| TBR full-period plot | DONE — Fig01 |
| TBR yearly histograms | DONE — Fig02 |
| Volume by bar type | DONE — Fig03, Tbl01 |
| TBR by bar type | DONE — Fig04, Tbl01 |
| ACF comparison | DONE — Fig05 |
| Predictive content scatter+corr | DONE — Fig06a/b/c, Tbl02 |
| Regime dependency | DONE — Fig07, Tbl03 |
| Rolling stationarity | DONE — Fig08 |
| Observation log (12 obs + 2 non-findings + 2 spurious) | DONE |
| No interpretation / no suggestion / no design | COMPLIANT |

---

## Deliverables

- `00_data_audit.md` — full data audit
- `01_raw_eda.md` — this file
- `figures/Fig01..Fig08` — 10 figures total
- `tables/data_audit_summary.csv, Tbl01..Tbl03` — 4 tables
- `code/phase1_raw_eda.py` — reproducible script
