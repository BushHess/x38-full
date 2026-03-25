# Phase 8 — Final Research Memo (X28)

**Study**: X28 — From-scratch algorithm discovery for BTC spot long-only
**Data**: BTCUSDT H4 (18,752 bars, 2017-08 → 2026-03) + D1 context (3,128 bars)
**Objective**: Maximize Sharpe ratio, MDD ≤ 60%, cost = 50 bps RT
**Date**: 2026-03-11

---

## 1. EXECUTIVE CONCLUSION

**Algorithm Cand01 [EMA Cross + Fixed Trail + D1 Regime] is the recommended system.**

| Metric | Cand01 | Best-Known Reference |
|--------|--------|---------------------|
| Sharpe | **1.251** | 1.08 |
| CAGR | 41.7% | 58% |
| MDD | **52.0%** | 53% |
| Trades | 39 | 219 |
| DOF | **4** | 5 |

ΔSharpe vs best-known reference = **+0.171**
ΔSharpe vs internal benchmark (no filter) = **+0.432**

**Caveat**: The best-known reference (Sharpe 1.08) is from a different codebase. When reimplemented in X28, that exact config yields Sharpe = −0.424 (Obs22). Cross-codebase comparison is unreliable. Within X28, the improvement over the internal benchmark (+0.432) is the reliable comparison.

---

## 2. RESEARCH PATH

**Phase 1** (Data Audit): Verified 4 timeframes (15m, 1h, 4h, 1d), 18,752 H4 bars covering 2017-08 → 2026-03. Zero missing values, zero duplicate timestamps, 1 gap in H4 (32h, 2018-02). Data is clean.

**Phase 2** (Price Behavior EDA): Established 17 observations. Raw returns are near-random-walk (VR test 0/9 significant). Volatility clustering is extreme (ACF(|ret|) 100/100 lags significant). D1 regime differential is the largest effect: EMA(21) = 661 pp/yr, H4|D1 Sharpe 1.25 vs −0.27. Volume has zero predictive power for returns.

**Phase 3** (Signal Landscape EDA): Swept 32 entry × 26 exit × 4 filter configurations (117 total backtests). **Impact analysis** revealed avg_loser is the dominant Sharpe predictor (|β·σ| = 0.709, partial R² = 0.306). Churn rate has zero predictive power (p = 0.76). **Decomposition** of best-known prior art showed Sharpe = −0.424 in this implementation — filters HURT (removing both yields Sharpe 0.424). Grid best: A_20_90 + X_trail8 + F2_d1ema50, Sharpe = 1.251.

**Phase 4** (Formalization): Derived 8 propositions from 30 observations. Ranked 23 features × 6 horizons: d1_ema_spread_50 is #1 feature (|r| = 0.088). Information concentrates at longer horizons (k=60 > k=1). Volume features definitively excluded (MI = 0.006 bits). 12 admissible combinations, all POWERED (Obs/MDE > 1.98×).

**Phase 5** (Go/No-Go): GO_TO_DESIGN. All 4 criteria met: ≥1 phenomenon powered, efficiency frontier populated, Sharpe > B&H + 0.10, actionable Sharpe driver identified.

**Phase 6** (Design): Selected 3 candidates from Phase 3 grid top-20. Cand01 (rank #1): EMA(20,90) cross + 8% trail + D1 EMA(50). Cand02 (rank #3): same + composite exit. Cand03 (rank #9): 60-bar breakout + ATR(3.0) trail + D1 EMA(50). Pre-committed 6 rejection criteria.

**Phase 7** (Validation): All 3 candidates pass ALL 9 gates. WFO 4-fold: Cand01/02 win 3/4 (75%), Cand03 2/4 (50%). Bootstrap P(Sharpe > 0) > 99% for all. Jackknife: 0 negative folds for all. Composite exit confirmed redundant with D1 filter (Phase 6 prediction validated). Cand01 recommended as PRIMARY.

---

## 3. STRONGEST EVIDENCE

**1. avg_loser is the dominant Sharpe predictor.** OLS regression (N=85, R²=0.557): avg_loser |β·σ| = 0.709, partial R² = 0.306, p < 1e-7. Configurations that cap per-trade losses have systematically higher Sharpe. *(Obs24, Tbl_sharpe_drivers, Fig_impact)*

**2. D1 EMA regime creates the largest return differential.** D1 EMA(21): 661 pp/yr (p < 0.0001). H4 conditioned on D1 EMA(21): Sharpe 1.25 vs −0.27 (Welch p = 0.036). D1 EMA(50) filter is the ONLY consistently positive filter: +0.045 mean ΔSharpe, 10/10 pairs positive. *(Obs16, Obs17, Obs23, Tbl09_d1, Tbl10)*

**3. Entry type A_20_90 dominates.** Present in ALL 5/5 top Sharpe configs. Mean Sharpe 0.700 across 9 exits (highest of 5 entries). EMA spread features carry |r| = 0.065–0.074, highest among price-based features. *(Obs21, Obs25, Obs30, Tbl_top20_sharpe, Fig13)*

**4. Information concentrates at longer horizons.** Mean |Spearman r| monotonically increases: k=1 (0.013) → k=60 (0.034). Consistent with trend-following alpha at multi-week timescales. avg_hold is the second Sharpe predictor (|β·σ| = 0.394, p = 1.1e-4). *(Obs24, Obs27, Tbl11)*

**5. Volume features carry zero exploitable information.** Confirmed in THREE independent analyses: (1) Phase 2 correlations |r| < 0.03 all horizons (Obs15), (2) Phase 3 VDO filter hurts ALL top-10 by −0.105 Sharpe (Obs23), (3) Phase 4 MI = 0.006 bits (Obs28). Triple confirmation. *(Obs15, Obs23, Obs28, Tbl08_volume, Tbl10_filter, Tbl11)*

**6. Cand01 passes ALL 9 validation gates.** Full-sample Sharpe 1.251. WFO 3/4 wins (75%). Bootstrap P(Sharpe > 0) = 99.6%, P(ΔSharpe > 0 vs benchmark) = 85.8%. Jackknife 0/6 negative. Breakeven cost > 300 bps. *(Tbl_full_sample, Tbl_wfo_results, Tbl_bootstrap_summary, Tbl_jackknife)*

**7. D1 filter is the dominant unmodeled driver.** Sharpe attribution residual = +0.424 (98% of ΔSharpe unexplained by linear model). The filter eliminates bad trades non-linearly — simultaneously improving win_rate, avg_hold, and reducing n_trades in a correlated manner. *(Tbl_sharpe_attribution)*

---

## 4. WHAT FAILED

### Signal Types Dominated
- **ROC threshold entry** (Type C): mean Sharpe 0.312 (worst of 5 entries). roc_20 |r| = 0.015 — near noise floor. Dominated by EMA cross on all metrics.
- **Volatility breakout entry** (Type D): D_20_1.5 mean Sharpe 0.458 (fourth of five). High detection rate (0.88) does NOT translate to high Sharpe after cost.
- **Time-based exits** (Type W): W_time20 Sharpe = −0.249. Forced exit destroys trend capture. Violates DC-2 (avg_hold requirement).
- **Reversal-only exit** (Type Z): Z_rev Sharpe = 0.515 but churn = 0.629. High churn from frequent re-entries.

### Candidates with Weaknesses
- **Cand02** (composite exit): PROMOTE but composite exit is **redundant** with D1 filter. Phase 6 predicted this (Cand01 Sharpe +0.152 higher, DOF 4 vs 5). In 2020, Cand02 earned +44.6% vs Cand01's +181.4% — reversal exit cuts too early during strong trends.
- **Cand03** (breakout entry): PROMOTE but marginal WFO (50%, exactly at threshold). Bootstrap P(ΔSharpe > 0) = 60.2% — barely better than coin flip vs benchmark. Cost-sensitive: crosses benchmark at ~100 bps.

### Rejected Classes at Formalization
- **Volume-based entry/filter**: Rejected on triple evidence (Obs15, Obs23, Obs28). MI = 0.006 bits.
- **Volatility regime filter** (F4): Inconsistent — 3/10 positive only (despite moderate nonlinear MI). Not included as admissible class.

### Failed Assumptions
- **Phase 3 decomposition assumption**: Expected prior art config to reproduce Sharpe ~1.08. Actual: −0.424. The strategy is implementation-sensitive — exact ATR variant, VDO definition, and entry/exit timing matter. Phase 3 grid had to find configurations from scratch.
- **Composite exit assumption**: Expected composites to uniformly outperform simple exits (Prop06, MEDIUM confidence). Actual: composites are redundant when D1 filter is present. The filter already removes the losing trades that the reversal exit was cutting.

### Design Constraints Not Fully Satisfied
- **Cand01 HC-3 margin**: 39 trades, only 9 above the 30-trade minimum. Per-fold WFO trade counts are 7–11. Statistical inference at the fold level is weak.
- **Cand02 SC-4**: Exposure 19.8%, marginally below the 20–50% recommended range.

---

## 5. KEY DISCOVERIES

| # | Discovery | Evidence | Surprise Level |
|---|-----------|----------|----------------|
| 1 | avg_loser is the #1 Sharpe predictor (β = +20.3, partial R² = 0.306) — more important than exposure, win_rate, or churn | Obs24, Tbl_sharpe_drivers | **HIGH** — prior research focused on exposure and churn; loss control is the actual lever |
| 2 | Churn rate has ZERO predictive power for Sharpe (p = 0.76, partial R² = 0.001) | Obs24, Tbl_sharpe_drivers | **HIGH** — prior studies X12–X19 spent 8 studies optimizing churn. This landscape shows it doesn't matter |
| 3 | D1 EMA(50) filter provides +0.432 ΔSharpe but 98% of this is through NON-LINEAR trade selection, not captured by linear attribution | Tbl_sharpe_attribution (residual +0.424) | **HIGH** — filter's value is in WHICH trades it removes, not in linear property changes |
| 4 | Volume features are genuinely information-free for BTC H4 returns — triple-confirmed across 3 independent analyses | Obs15, Obs23, Obs28 | **MED** — prior VDO filter was already marginal (DOF-corrected p = 0.031), but the STRENGTH of the null (MI = 0.006 bits) is surprising |
| 5 | Best-known prior art produces Sharpe = −0.424 when reimplemented independently — strategies are NOT portable across codebases | Obs22, Tbl_decomposition | **HIGH** — the "same" algorithm with minor implementation differences is a completely different strategy |
| 6 | Information concentrates monotonically at longer horizons (k=1: 0.013 → k=60: 0.034) | Obs27, Tbl11 | **LOW** — expected for trend-following, but the MONOTONICITY across all 6 horizons is clean confirmation |
| 7 | Entry choice explains more Sharpe variance than exit choice — the entry-exit interaction is ADDITIVE, not multiplicative | Obs21, Fig13 | **MED** — implies entry selection is the primary design decision; exit refinement is secondary |
| 8 | All 3 candidates have negative Sharpe in D1 EMA(21) bear regimes — this is structural for long-only and cannot be optimized away | §6c regime split | **LOW** — expected, but quantified: Cand01 Sharpe −0.937 in bear |

---

## 6. MATHEMATICAL CONCLUSION

### Where is exploitable structure in BTC H4 returns?

BTC H4 returns are near-random-walk in the linear sense (VR test 0/9 significant, ACF lag1 = −0.044). The exploitable structure resides in **two orthogonal phenomena**:

1. **Trend persistence at multi-week timescales**: Hurst = 0.583 (mild), but more precisely captured by EMA spread features (|r| = 0.065–0.088 at k = 40–60 bars). Returns 10–60 bars ahead are weakly predictable from current EMA spread.

2. **D1 regime conditioning**: The D1 close vs EMA(50) binary partitions H4 bars into Sharpe 1.25 (above) vs −0.27 (below). This is the single largest effect (661 pp/yr at D1 level).

### Best function class

The **EMA crossover + trail stop + D1 regime filter** class. Specifically:
- Entry: 𝟙{EMA(p_f, C) > EMA(p_s, C)}, p_f = 20, p_s = 90
- Exit: 𝟙{C < HWM × (1 − τ)}, τ = 0.08
- Filter: 𝟙{D1_close > EMA(p_d, D1_close)}, p_d = 50

### Why this class and not others?

- **EMA cross over breakout**: EMA spread carries |r| = 0.074 vs breakout_pos_60 |r| = 0.048 — 54% more information per feature. In grid: A_20_90 mean Sharpe 0.700 vs B_60 mean 0.709 (comparable), but with filter: 1.251 vs 0.888 (+41%).
- **Fixed trail over ATR trail**: ATR trail Sharpe improves monotonically with wider multiplier (Obs19). Fixed 8% trail captures this without ATR computation and maintains avg_hold = 124 bars vs ATR(3.0) = 47 bars — longer holds are the #2 Sharpe driver.
- **D1 EMA(50) over EMA(21)**: D1 EMA(21) filter produced Sharpe 0.937 with MDD 64.5% (FAILS HC-6). EMA(50) produces Sharpe 1.251 with MDD 52.0% (PASS). EMA(50) is the slower, more conservative filter — it captures the regime effect while avoiding whipsaw at the faster EMA(21) timescale.
- **No VDO/volume**: Volume features carry MI = 0.006 bits. Adding VDO hurts ALL top-10 by −0.105 Sharpe.

### Information ceiling

- **Linear lower bound**: IC ≈ 0.088, BR ≈ 50 → IR ≈ 0.62 (Grinold fundamental law)
- **Pragmatic ceiling**: Sharpe 1.2–1.5 (from grid evidence — top configs already at 1.05–1.25)
- **Cand01 at Sharpe 1.251**: Near the upper end of the pragmatic ceiling
- **Remaining room**: ~0.0–0.25 Sharpe. Diminishing returns. Most improvement would come from cost reduction, not algorithmic complexity.

### Complexity vs performance

| DOF | Best Sharpe in grid |
|-----|-------------------|
| 2 | 0.859 (B_60+Y_atr3) |
| 3 | 0.962 (A_20_90+X_trail8) |
| 4 | **1.251** (Cand01) |
| 5 | 1.099 (Cand02) |

**Optimal DOF = 4**. Adding the 5th DOF (composite exit) actually REDUCES Sharpe by 0.152. The 4th DOF (D1 filter) is the critical addition (+0.289 vs DOF=3).

### Sharpe attribution: Cand01 vs Benchmark

Cand01 beats benchmark (Sharpe +0.432) primarily because the D1 EMA(50) filter eliminates bad trades. Linear attribution explains only 2% of ΔSharpe — the filter's effect is non-linear (it simultaneously improves win_rate, extends avg_hold, and reduces n_trades in a correlated manner). The remaining 98% is in the residual.

---

## 7. PRACTICAL RECOMMENDATION

### Algorithm Specification (Cand01)

```
ENTRY:
  At each H4 bar close:
    Compute EMA(20, close) and EMA(90, close)
    If EMA(20) > EMA(90) AND position is flat AND filter allows:
      Enter LONG at next bar's open

EXIT (Fixed Percentage Trailing Stop):
  While in position:
    Track HWM = max(close prices since entry)
    At each bar close: if close < HWM × 0.92 → exit at next bar's open
    HWM resets on each new entry

FILTER (D1 EMA Regime):
  At each H4 bar:
    Look up PREVIOUS D1 close (1-day lag)
    Compute EMA(50) on D1 close
    allow_entry = (D1_close > EMA(50, D1_close))
    If filter OFF: no new entries; existing positions continue until exit fires

SIZING: Binary (fully invested or flat)
COST: 50 bps round-trip
PARAMETERS: p_f=20, p_s=90, τ=0.08, p_d=50 (Total DOF: 4)
```

### Key Metrics vs Benchmark

| Metric | Cand01 | Benchmark | ΔCand01 |
|--------|--------|-----------|---------|
| Sharpe | **1.251** | 0.819 | **+0.432** |
| CAGR | 41.7% | 31.7% | +10.0 pp |
| MDD | −52.0% | −39.9% | −12.1 pp |
| Calmar | 0.801 | 0.795 | +0.006 |
| Trades | 39 | 108 | −69 |
| Win Rate | 46.2% | 36.1% | +10.1 pp |
| Exposure | 25.8% | 25.7% | +0.1 pp |
| Profit Factor | 3.78 | 2.24 | +1.54 |
| Breakeven Cost | >300 bps | — | — |

### Sharpe Attribution: WHY It's Better

The D1 EMA(50) filter is the sole driver. It removes entries where D1 close < EMA(50) — periods that, on average, produce negative H4 Sharpe (−0.27). This has three downstream effects:
1. **Fewer, higher-quality trades**: 39 vs 108 (−64%), but win rate 46.2% vs 36.1% (+10 pp)
2. **Longer average hold**: 124 vs 45 bars — filter removes short-duration losing trades
3. **Better profit factor**: 3.78 vs 2.24 — the remaining trades have far more favorable payoff asymmetry

These effects are correlated (removing a bad trade simultaneously improves all three), which is why the linear attribution model fails (residual = 98%).

### Caveats

1. **Low trade count (39)**: Per-fold WFO trade counts are 7–11. Inference at the fold level is weak. This is the single biggest vulnerability.
2. **Bear regime exposure**: Sharpe −0.937 during D1 EMA(21) bear regimes. The D1 EMA(50) filter does NOT fully protect against bear markets (EMA(50) lags regime transitions).
3. **MDD = 52%**: Within the 60% constraint but not comfortable. A single bad regime could push past 60%.
4. **Cost assumption**: Results at 50 bps RT. At realistic exchange costs (15–30 bps RT), Sharpe improves to 1.29–1.31.
5. **Sample period**: 2017-08 → 2026-03 (8.5 years). BTC market structure has changed significantly (institutional adoption, ETF, derivatives market growth). Future regime may differ.
6. **2025 YTD negative**: Cand01 returned −14.6% in 2025 (partial year). Too early to determine if this signals a regime shift.
7. **Implementation sensitivity**: Obs22 demonstrates that minor implementation differences produce drastically different results (Sharpe −0.424 vs 1.08 for "same" config). Exact logic matching is critical.

### Monitoring for Live Deployment

- **Trade count**: If annual trade count drops below 3, the filter may be too restrictive for the current regime.
- **MDD**: If drawdown exceeds 55%, evaluate D1 EMA(50) regime status. If persistently below EMA(50) for >6 months, the filter is working correctly (blocking entries).
- **Win rate**: If rolling 20-trade win rate drops below 25% (vs 46.2% full-sample), investigate regime change.
- **D1 EMA(50) effectiveness**: Track conditional Sharpe above vs below EMA(50). If the differential narrows significantly, the regime signal may be degrading.

---

## 8. ANTI-SELF-DECEPTION

### What would make this conclusion wrong?

**Assumptions most likely to be wrong:**

1. **39 trades is sufficient for inference.** Bootstrap P(Sharpe > 0) = 99.6% with 2,000 paths, but all paths are resampled from the SAME 39 trades. If 2–3 of the large winners (contributing disproportionately to the right tail) are anomalous events, the true Sharpe could be significantly lower. The benchmark has 108 trades — 2.8× more statistical power.

2. **D1 regime differential persists.** The 661 pp/yr differential (Obs16) is measured over a specific BTC history that includes the 2017 bubble, 2020 COVID crash, 2021 bull run, and 2022 bear market. If BTC transitions to a more efficient, lower-volatility regime (which institutional adoption suggests), the D1 regime differential may shrink.

3. **Full-sample Sharpe represents future Sharpe.** The Phase 3 grid was used to both DISCOVER and EVALUATE Cand01. The grid Sharpe 1.251 was the selection criterion. This is an in-sample selection bias. The bootstrap and WFO mitigate but do not eliminate this bias.

**Data limitations:**

- **8.5 years of data**: Only ~2 complete bull/bear cycles. Different crypto cycles may have different characteristics.
- **Survivorship bias**: BTC is the surviving asset. An algorithm that works on BTC may not work on assets that failed.
- **Regime coverage**: The 2017 extreme early period (BTC < $5K) may not represent current market dynamics. Excluding pre-2020 data would leave only 6 years.
- **D1 EMA(50) filter specificity**: Only ONE D1 EMA period (50) was tested as the filter. Sweeping 15–60 would multiply DOF concern.

**Method limitations:**

- **WFO folds (4)**: With 39 trades total, each fold has ≤11 trades. Per-fold Sharpe estimates have enormous variance. WFO win rate of 75% (3/4) could easily be 50% or 100% with one fold's noise.
- **Bootstrap block size (136)**: Chosen as √N where N = 18,751 bars. This assumes a specific autocorrelation structure. If the true dependence structure is longer, the bootstrap understates uncertainty.
- **Single codebase**: All results are from one implementation (phase7_validation.py). No independent replication.

**Conditions that could reverse the conclusion:**

- **BTC volatility permanently drops below 30% annualized**: The D1 regime filter and trail stop are both calibrated to high-vol BTC. In a low-vol regime, the 8% trail would rarely trigger, and the EMA cross would generate fewer signals.
- **BTC becomes mean-reverting**: The Hurst exponent is only mildly above 0.5 (0.583). A regime shift to H < 0.5 would destroy trend-following alpha.
- **Exchange costs increase materially**: Unlikely given current trajectory, but regulatory changes could affect execution costs.

**Known unknowns:**

- Intraday execution: all fills assumed at bar open. Slippage is unmodeled.
- Black swan events: COVID (2020-03) is in-sample. The next black swan may behave differently.
- Correlation with traditional assets: not measured. If BTC becomes highly correlated with equities, the strategy may not add portfolio diversification.

**Protocol limitations:**

- Phase 3 grid swept only 45 entry×exit pairs + 40 filter variants = 85 total. The search space is much larger — configs outside the grid are unexplored.
- The protocol uses a single research agent — no adversarial review or independent replication.
- Phase 3's OLS regression (R² = 0.557) means 44% of Sharpe variance is unexplained. The identified drivers are necessary but not sufficient conditions.

---

## 9. RESEARCH PROTOCOL REVIEW

### Most Valuable Phase: Phase 3 (Signal Landscape EDA)

Phase 3's impact analysis was the single most valuable step. Without it, we would have:
- Optimized for churn reduction (prior research focus) — which has ZERO Sharpe predictive power
- Included VDO filter (prior art component) — which HURTS all top-10 by −0.105
- Missed that avg_loser is the #1 driver — and potentially chosen wider-trail exits without understanding why

The decomposition of the prior art config (Sharpe −0.424 in this implementation) was also critical — it forced the study to work from scratch rather than assume prior art portability.

### Least Valuable Phase: Phase 5 (Go/No-Go)

Phase 5's decision was obvious given Phase 3–4 results. All 12 combinations were POWERED, the grid had Sharpe > 1.0, and the regression clearly identified actionable drivers. The formal 4-criterion check added rigor but did not change the trajectory. In hindsight, Phases 4 and 5 could be merged.

### Protocol Blind Spots

1. **No parameter sensitivity sweep**: Phase 6 fixed parameters at Phase 3 grid defaults. The study did not test how sensitive Cand01 is to moving p_f from 20 to 15 or 25, p_s from 90 to 80 or 100, τ from 8% to 6% or 10%, p_d from 50 to 40 or 60. A parameter plateau analysis would strengthen confidence.

2. **No out-of-sample holdout**: The entire dataset was used for both discovery (Phases 2–3) and validation (Phase 7). A proper test would reserve the last 1–2 years as a true holdout — but with only 39 trades, this would leave insufficient trades for validation.

3. **Single implementation**: No cross-validation against the existing btc-spot-dev VTREND codebase. Obs22 shows this matters enormously. An independent implementation would be the strongest validation.

4. **No multi-asset test**: X20 (prior research) showed BTC-only dominates portfolio, but X28 did not test whether Cand01's specific parameters work on other assets — this would test whether the alpha is asset-specific or generic trend-following.

### Recommendations for Protocol X29

1. **Add parameter sensitivity phase** between Phase 6 and Phase 7: sweep each parameter ±50% from default, verify Sharpe remains within 80% of peak (plateau check).
2. **Reserve holdout period**: Use the most recent 20% of data as a true holdout, evaluated ONCE after all design decisions are made.
3. **Cross-implement**: Require at least one candidate to be implemented in the existing production codebase for direct comparison.
4. **Phase 3 grid expansion**: Increase grid from 45 to 100+ pairs to reduce risk of missing superior configs outside the grid.

---

## 10. FINAL STATUS

### **FINALIZED_PROMOTE_CAND01**

Algorithm Cand01 [EMA(20,90) Cross + 8% Trail + D1 EMA(50) Regime] passes all 9 validation gates, achieves Sharpe 1.251 (ΔSharpe +0.432 vs internal benchmark), and satisfies all constraints. It represents the same function class as prior art (EMA cross + trail + D1 regime) but with simplified structure: no volume filter, no composite exit, fewer DOF. The primary contribution is NEGATIVE — identifying what to REMOVE (VDO filter, composite exit, churn optimization) rather than what to add. This is consistent with the finding that BTC H4 trend-following alpha is captured by a simple 4-DOF system and additional complexity adds zero value.

**Qualification**: The improvement vs prior art reference (+0.171 Sharpe) is modest and may be within noise given cross-codebase unreliability. The LOW trade count (39) is the primary statistical weakness. Cand01 should be understood as confirming and refining the prior art's architecture, not as a breakthrough discovery.

---

## Deliverables

### Files Created
- `08_final_report.md` (this report)
- `manifest.json` (final update)

### Provenance Summary
- 30 Observations (Obs01–Obs30)
- 8 Propositions (Prop01–Prop08)
- 5 Design Constraints (DC-1 through DC-5)
- 3 Candidates (Cand01–Cand03), all PROMOTE
- 12 Admissible Combinations (C1–C12)
- 20 Figures (Fig01–Fig20)
- 25+ Tables (Tbl01–Tbl13, Tbl_*)
- 4 Code scripts (phase1–4 analysis, phase7 validation)
