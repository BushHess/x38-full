# Phase 2: Flat-Period Raw EDA

**Date**: 2026-03-11
**Inputs**: 01_audit_state_map.md, state_classification.csv (Phase 1)
**Method**: H4/H1/D1 OHLCV analysis conditioned on VTREND FLAT/IN_TRADE state

---

## 2.1 FLAT-Period Return Distribution (H4)

**Tbl03**: Return distribution statistics (FLAT vs IN_TRADE vs FULL)

| Statistic | FLAT (n=10,720) | IN_TRADE (n=7,941) | FULL (n=18,661) |
|-----------|----------------:|-------------------:|----------------:|
| Mean (bps) | -2.05 | +6.23 | +1.47 |
| Median (bps) | +1.25 | +3.50 | +2.10 |
| Std (bps) | 157.37 | 135.28 | 148.43 |
| Skew | -0.126 | -0.322 | -0.202 |
| Kurtosis (excess) | 22.49 | 13.97 | 20.49 |
| JB stat | 225,928 | 64,725 | 326,411 |
| JB p-value | 0 | 0 | 0 |
| IQR (bps) | [-51, +52] | [-45, +54] | [-48, +53] |
| Range (bps) | [-2294, +2716] | [-1474, +1272] | [-2294, +2716] |

**Obs11** [Fig04, Tbl03]: FLAT H4 returns have mean -2.05 bps vs IN_TRADE +6.23 bps. The median difference is smaller (1.25 vs 3.50 bps). The mean-median gap in FLAT (-2.05 vs +1.25) indicates the mean is pulled by left-tail events. FLAT bars contain the most extreme observations in both tails (min -2294 bps, max +2716 bps), which are absent from IN_TRADE returns.

**Obs12** [Fig04c, Tbl03]: FLAT returns have excess kurtosis 22.49, substantially higher than IN_TRADE (13.97). Both are strongly leptokurtic and reject normality (JB p≈0). The Q-Q plot (Fig04c, R²=0.9958) shows heavy-tail departure at ±3σ. FLAT returns have wider std (157 vs 135 bps) and wider IQR.

**Obs13** [Fig04, Tbl03]: FLAT returns have mild negative skew (-0.126), less than IN_TRADE (-0.322). IN_TRADE skew is more negative because the trailing stop truncates the left tail less aggressively than the upper tail — winning trades run, losing trades are cut.

---

## 2.2 Autocorrelation Structure

**Fig05**: ACF comparison (FLAT vs FULL, returns and |returns|)
**Significance bound**: FLAT ±0.0189, FULL ±0.0143 (95% CI, white noise null)

### Return ACF (FLAT bars only)

Significant lags: 1, 3, 6, 7, 11, 14, 19, 20, 22, 25, 30, 32, 36, 38, 50 (15 of 50 lags)

| Lag | FLAT ACF | FULL ACF | Significant? |
|----:|---------:|---------:|:-------------|
| 1 | -0.0524 | -0.0354 | Yes (FLAT & FULL) |
| 3 | +0.0423 | +0.0135 | Yes (FLAT only) |
| 6 | -0.0762 | -0.0403 | Yes (FLAT & FULL) |
| 7 | -0.0445 | -0.0204 | Yes (FLAT only) |
| 10 | +0.0133 | +0.0058 | No |

**Obs14** [Fig05a]: FLAT return ACF shows a significant negative lag-1 autocorrelation of -0.052. This is larger in magnitude than the full-sample lag-1 ACF (-0.035). The strongest effect is at lag 6 (ACF = -0.076), corresponding to 24 hours (6 H4 bars). Of 50 lags tested, 15 are significant at 5% — more than the 2.5 expected by chance. The pattern alternates between negative (lags 1, 6, 7) and positive (lag 3) at short lags.

### |Return| ACF (volatility clustering)

**Obs15** [Fig05b]: FLAT-period absolute return ACF is large and persistent: lag 1 = 0.278, lag 10 = 0.181, lag 20 = 0.180, lag 50 = 0.116. All 50 lags are statistically significant. This indicates strong volatility clustering during FLAT periods. The magnitude is comparable to (or slightly larger than) the full-sample |return| ACF. FLAT periods are not low-volatility quiet zones — they exhibit the same GARCH-like vol persistence as the full market.

### PACF

**Obs16** [Fig05c]: FLAT PACF is significant at lag 1 (-0.052), lag 3 (+0.030), and lag 6 (-0.071). The lag-6 PACF is nearly as large as the lag-1, confirming that the 24-hour periodicity is a distinct effect, not an artifact of lower-lag dependence.

### Variance Ratio Tests

**Tbl04**: Variance ratio results (three methods)

| Method | VR(2) | VR(5) | VR(10) | VR(20) |
|--------|------:|------:|-------:|-------:|
| FULL sample | 0.955 | 0.974 | 0.948 | 0.952 |
| FLAT per-period (mean) | 0.824*** | 0.782*** | 0.751*** | 0.720*** |
| FLAT concatenated | 0.952*** | 0.946** | 0.872*** | 0.824*** |

Per-period test: n=154/111/80/58 periods, t-test vs VR=1, all p < 0.0001.
Homoscedastic z-test significant for concatenated. Heteroscedastic z-test non-significant (heavy tails absorb the signal under het-robust normalization).

**Obs17** [Tbl04, Fig06a]: Flat-period returns are mean-reverting. The per-period variance ratio test (the most reliable method, free of concatenation artifacts) shows VR consistently below 1 and declining with holding period: VR(2)=0.82, VR(5)=0.78, VR(10)=0.75, VR(20)=0.72, all highly significant (p<0.0001). This means that within individual flat periods, multi-bar returns have LESS variance than expected under a random walk — price tends to partially reverse. The full-sample VR is closer to 1 (0.95) because it mixes FLAT and IN_TRADE bars, and trends during IN_TRADE periods push VR upward.

### Hurst Exponent (R/S method)

| Sample | Hurst H |
|--------|--------:|
| FULL | 0.576 |
| FLAT concatenated | 0.514 |
| Longest flat period (620 bars) | 0.621 |

**Obs18** [Fig06b]: The Hurst exponent tells a mixed story. FLAT concatenated H=0.514 (near random walk), but the longest single flat period gives H=0.621 (persistent). The Hurst estimator aggregates across all timescales; the per-period VR test (Obs17) is more informative for the specific question of within-flat-period dynamics. The full-sample H=0.576 reflects the trending character of the overall BTC series.

---

## 2.3 Volatility Structure

### Realized Volatility Comparison

| State | Mean Ann. Vol | Median Ann. Vol |
|-------|-------------:|-----------:|
| FLAT | 62.5% | 53.1% |
| IN_TRADE | 53.0% | 45.8% |
| FULL | 58.5% | 49.9% |

**Obs19** [Fig07b]: FLAT-period realized volatility is HIGHER than IN_TRADE (62.5% vs 53.0% annualized, mean of 20-bar rolling std). This is counterintuitive: VTREND enters when a trend begins (EMA crossover), and one might expect trending periods to be more volatile. The observation is that FLAT bars — which include choppy ranges, failed setups, and consolidation — have wider dispersion per bar. The median difference is similar (53.1% vs 45.8%).

### Vol-of-Vol

| State | Mean Ann. Vol-of-Vol |
|-------|----:|
| FLAT | 10.21% |
| IN_TRADE | 8.96% |

FLAT periods have higher vol-of-vol, indicating more heterogeneous volatility regimes during out-of-market periods.

### Volatility by Position within Flat Period

**Fig07a**: Volatility binned by normalized position (0=start, 1=end) across flat periods of ≥5 bars:

| Position | Mean Vol (%) | Median Vol (%) |
|---------:|------:|-------:|
| 0.0–0.1 | 60.8 | 50.6 |
| 0.1–0.2 | 63.4 | 50.8 |
| 0.2–0.3 | 65.5 | 53.5 |
| 0.3–0.4 | 68.7 | 61.3 |
| 0.4–0.5 | 65.1 | 53.4 |
| 0.5–0.6 | 63.5 | 53.2 |
| 0.6–0.7 | 65.6 | 59.2 |
| 0.7–0.8 | 64.3 | 56.7 |
| 0.8–0.9 | 53.9 | 47.1 |
| 0.9–1.0 | 55.6 | 49.3 |

**Obs20** [Fig07a]: There is a mild systematic volatility pattern within flat periods. Volatility is elevated in the middle portion (peak at 0.3–0.4 position, mean 68.7%) and declines toward both ends, with the sharpest decline at the end (0.8–1.0: 54–56%). The pattern is present in both mean and median. The drop at the end of flat periods (before the next trade entry) is consistent with the volatility compression that precedes EMA crossover signals.

---

## 2.4 Flat-Period Internal Structure

### Per-Period Summary Statistics (n=218 flat periods)

| Metric | Mean | Median |
|--------|-----:|-------:|
| Duration (bars) | 49.2 | 11 |
| Total return (%) | -0.88 | +0.60 |
| Max drawdown (%) | -6.17 | -1.81 |
| Max runup (%) | +6.76 | +3.89 |
| Volatility (bps/bar) | 97.33 | 82.54 |

### Predictive Relationships

**Tbl05**: Spearman correlations between flat-period characteristics and next trade return

| Relationship | Spearman ρ | p-value | Significant? |
|-------------|----------:|--------:|:------------|
| flat_duration vs flat_total_return | -0.046 | 0.502 | No |
| flat_duration vs next_trade_return | -0.021 | 0.758 | No |
| flat_total_return vs next_trade_return | -0.061 | 0.368 | No |
| flat_volatility vs next_trade_return | -0.057 | 0.401 | No |

**Obs21** [Tbl05, Fig08]: None of the four tested flat-period characteristics predict the next trade's return. All Spearman correlations are small (|ρ| < 0.07) and non-significant (all p > 0.35). The scatter plots (Fig08) show no visible structure. Flat-period duration, total return, and volatility carry no cross-sectional information about the quality of the subsequent trade entry.

---

## 2.5 Transition Dynamics

Profiles computed from 217 trades, 20-bar window on each side.

### Pre-Entry (20 bars before trade entry)

| Subset | Cumulative Return (bar -20 to -1) |
|--------|----------------------------------:|
| All trades (n=217) | +1.033% |
| Before winners (n=95) | +0.976% |
| Before losers (n=122) | +1.077% |

**Obs22** [Fig09a]: The average cumulative return in the 20 bars preceding a trade entry is +1.03%. This is expected: VTREND enters on an EMA(30/120) crossover, which requires price to have been rising. The pre-entry drift is nearly identical for winners (+0.98%) and losers (+1.08%). This confirms that the entry signal fires after a price run-up, but the magnitude of the pre-entry drift does not distinguish winning from losing trades.

### Post-Exit (20 bars after trade exit)

| Subset | Cumulative Return (bar 0 to +19) |
|--------|----------------------------------:|
| All trades (n=217) | +0.344% |
| After winners (n=95) | +0.810% |
| After losers (n=122) | -0.019% |

**Obs23** [Fig09b]: Post-exit behavior differs by trade outcome. After winning trades, price continues to rise (+0.81% over 20 bars) — consistent with the exit being triggered by a trail stop or brief pullback within a continuing trend. After losing trades, price is essentially flat (-0.02%) — the failed trend has reverted, and the market enters a neutral drift. The all-trade average (+0.34%) is modest and dominated by the winner sub-group.

### Volatility and Volume Profiles

**Obs24** [Fig09c-f]: Pre-entry volatility is approximately flat across the 20-bar window (no systematic ramp). Pre-entry volume shows a gradual increase approaching entry (consistent with rising activity during trend initiation). Post-exit volatility is elevated at the exit bar and decays over the following bars. Post-exit volume is also elevated at exit and normalizes within ~5 bars.

---

## 2.6 Cross-Timeframe Check

### H1 Resolution (FLAT periods mapped from H4 states)

42,883 H1 FLAT bars (57.4%), 3 bars with unknown H4 mapping.

| Metric | H1 FLAT | H4 FLAT | D1 FLAT |
|--------|--------:|--------:|--------:|
| Mean (bps) | -0.51 | -2.05 | -18.43 |
| Std (bps) | 84.43 | 157.37 | 385.98 |
| Skew | -0.309 | -0.126 | -1.586 |
| Kurtosis | 38.19 | 22.49 | 19.53 |
| Hurst | 0.511 | 0.514 | 0.467 |

**Obs25** [Fig11]: H1 FLAT ACF reproduces the H4 patterns with finer resolution:
- Return ACF: lag-1 negative (-0.050), lag-24 significant (-0.041, corresponding to H4 lag-6). The 24-hour periodicity appears explicitly at H1 as lag 24.
- |Return| ACF: all 50 lags significant, lag-1 = 0.321 (stronger than H4's 0.278).
- H1 VR tests confirm mean-reversion: VR(2)=0.949, VR(20)=0.830.

**Obs26**: D1 FLAT returns (days with ≥75% FLAT H4 bars, n=1,697) show stronger negative mean (-18.43 bps) and stronger negative skew (-1.586). D1 Hurst = 0.467, the only sub-0.5 estimate, suggesting daily-scale mean-reversion during flat periods. D1 VR(2)=0.847, VR(5)=0.783 — mean-reversion is more pronounced at daily resolution.

**Obs27**: The mean-reversion signal (VR < 1) strengthens at longer aggregation: H1 VR(2)=0.949, H4 per-period VR(2)=0.824, D1 VR(2)=0.847. Vol clustering is present at all three timeframes. The core patterns (negative return autocorrelation, strong vol clustering, mean-reversion) are consistent across H1, H4, and D1 — they are not timeframe-specific artifacts.

---

## 2.7 Calendar Effects (H1, FLAT only)

42,883 FLAT H1 bars analyzed.

### Return by Hour

Most positive: 21:00 UTC (+5.26 bps), 22:00 UTC (+3.61 bps), 11:00 UTC (+3.27 bps)
Most negative: 01:00 UTC (-5.55 bps), 03:00 UTC (-5.43 bps), 14:00 UTC (-4.02 bps)

### |Return| by Hour (intraday volatility)

Lowest: 03:00–05:00 UTC (39.1–40.2 bps) — Asia late session
Highest: 13:00–16:00 UTC (54.1–62.1 bps) — US/EU overlap

### Return by Day of Week

No significant variation (KW p=0.627). The largest deviation is Thursday (-2.57 bps), but this is not statistically reliable.

### |Return| by Day of Week

Weekend volatility is markedly lower: Saturday 36.1 bps, Sunday 41.7 bps vs weekday 49.8–52.7 bps.

### Statistical Tests

**Tbl06**: Kruskal-Wallis test results

| Test | KW Statistic | p-value | Significant? | Half-Sample |
|------|------------:|--------:|:------------|:-----------|
| Return by hour | 57.09 | 0.0001 | Yes | STABLE |
| |Return| by hour | 589.46 | < 1e-10 | Yes | STABLE |
| Return by DoW | 4.37 | 0.627 | No | — |
| |Return| by DoW | 769.65 | < 1e-10 | Yes | STABLE |

**Obs28** [Fig10, Tbl06]: Three calendar effects are statistically significant and STABLE across half-sample splits:
1. Return by hour (p=0.0001): approximately ±5 bps hourly deviation. Largest at 01:00/03:00 (negative) and 21:00/22:00 (positive).
2. Intraday volatility pattern (p≈0): 60% higher vol during US/EU hours (13–16 UTC) vs Asia session (03–05 UTC).
3. Day-of-week volatility (p≈0): weekend vol is 30% lower than weekday vol.

Return by day of week is NOT significant (p=0.63). There is no exploitable weekday directional effect during FLAT periods.

**Obs29** [Tbl06]: All three significant effects are STABLE — they reproduce in both the first and second half of the sample (half1 and half2 both pass at p<0.05). The intraday volatility pattern is the strongest and most stable (KW=589, both halves p<0.0001).

---

## 2.8 Verification Artifacts

### Code
- `code/phase2_flat_eda.py` — all 7 sections, 700+ lines

### Figures
- `figures/Fig04_flat_return_distribution.png` — Return histograms + Q-Q plot
- `figures/Fig05_acf_comparison.png` — ACF/PACF: FLAT vs FULL
- `figures/Fig06_variance_ratio_hurst.png` — VR test + R/S Hurst
- `figures/Fig07_vol_structure.png` — Vol by position, FLAT vs IN_TRADE
- `figures/Fig08_scatter_matrix.png` — Flat characteristics vs next trade
- `figures/Fig09_transition_dynamics.png` — Pre-entry/post-exit profiles
- `figures/Fig10_calendar_effects.png` — Hour × DoW heatmaps
- `figures/Fig11_cross_timeframe_acf.png` — H1 vs H4 ACF comparison

### Tables
- `tables/Tbl03_return_distribution.csv` — Distribution statistics
- `tables/Tbl04_variance_ratio.csv` — VR tests (3 methods) + Hurst
- `tables/Tbl05_predictive_relationships.csv` — Spearman correlations
- `tables/Tbl06_calendar_effects.csv` — Calendar KW tests + stability
- `tables/flat_period_characteristics.csv` — Per-period metrics (218 rows)

---

## END-OF-PHASE CHECKLIST

### 1. Files created
- `02_flat_period_eda.md` (this file)
- `code/phase2_flat_eda.py`
- 8 figures (Fig04–Fig11)
- 5 tables (Tbl03–Tbl06 + flat_period_characteristics)

### 2. Key Obs / Prop IDs created
- **Obs11**: FLAT mean -2.05 bps, IN_TRADE +6.23 bps; extreme tails in FLAT
- **Obs12**: FLAT kurtosis 22.49 >> IN_TRADE 13.97; strongly non-normal
- **Obs13**: FLAT skew -0.126, less negative than IN_TRADE -0.322
- **Obs14**: FLAT return ACF: lag 1 = -0.052, lag 6 = -0.076 (24h cycle); 15/50 lags significant
- **Obs15**: FLAT |return| ACF: lag 1 = 0.278, all 50 lags significant (strong vol clustering)
- **Obs16**: FLAT PACF: lag 6 = -0.071 (distinct 24h periodicity)
- **Obs17**: Per-period VR strongly < 1 (VR(2)=0.82, VR(20)=0.72, all p<0.0001) — mean-reversion
- **Obs18**: Hurst mixed (0.51 concat, 0.62 longest); VR test more informative
- **Obs19**: FLAT vol HIGHER than IN_TRADE (62.5% vs 53.0%)
- **Obs20**: Vol within flat period: elevated mid-period, lower at boundaries
- **Obs21**: No predictive power: flat characteristics → next trade return (all |ρ|<0.07, p>0.35)
- **Obs22**: Pre-entry drift +1.03% (expected for trend entry); no win/loss distinction
- **Obs23**: Post-exit: +0.81% after winners (trend continues), -0.02% after losers (reversal done)
- **Obs24**: Post-exit vol elevated at exit, decays over ~5 bars
- **Obs25**: H1 reproduces H4: lag-24 ACF = -0.041, |ret| ACF 0.321, VR confirms mean-reversion
- **Obs26**: D1 FLAT: Hurst 0.467 (mean-reverting), negative mean -18.43 bps, strong left skew
- **Obs27**: Mean-reversion consistent across H1/H4/D1 — not timeframe-specific
- **Obs28**: 3 calendar effects significant + STABLE: hourly return, intraday vol, weekend vol
- **Obs29**: All stable across half-sample splits; intraday vol pattern is strongest

### 3. Blockers / uncertainties
- Heteroscedastic z-tests for VR are non-significant (heavy tails absorb signal). Per-period t-test is more reliable and shows clear mean-reversion.
- Hurst exponent is ambiguous due to mixing of timescales; VR per-period is the preferred measure.
- H4→H1 state mapping has 3 unmapped bars (negligible).
- Calendar return effects (~5 bps hourly deviation) are small relative to per-bar std (84 bps); economic significance is unclear.

### 4. Gate status
**PASS_TO_NEXT_PHASE**

Rationale: Multiple non-trivial statistical properties identified in FLAT periods:
1. **Mean-reversion** (Obs17): VR << 1, highly significant, consistent across timeframes.
2. **Vol clustering** (Obs15): ACF(|r|) lag-1 = 0.28, persistent through lag 50.
3. **24-hour periodicity** (Obs14, Obs16): Distinct cycle visible in both ACF and PACF.
4. **Calendar effects** (Obs28): Intraday vol pattern and hourly return bias, both STABLE.
5. **Post-exit asymmetry** (Obs23): Divergent behavior after winners vs losers.
6. **No flat→trade predictability** (Obs21): Flat characteristics do not predict next trade.

Whether these properties contain exploitable alpha beyond VTREND is for Phase 3 (phenomenon survey) to assess. Phase 2 describes; it does not judge exploitability.
