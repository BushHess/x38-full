# Phase 8: Final Research Memo

**Study**: X27
**Date**: 2026-03-11
**Data**: BTCUSDT H4+D1, 2017-08 to 2026-03 (8.56 years, 18,751 H4 bars)
**Benchmark**: VTREND E5+EMA21D1 (binary sizing)

---

## 1. EXECUTIVE CONCLUSION

**No improvement over benchmark. VTREND remains best known.**

Reason: The best data-derived candidate (Cand01: breakout + ATR trail, 3 DOF) passes all 8 validation gates but achieves Sharpe 0.907 vs benchmark 1.084, CAGR 38.6% vs 58.2%, Calmar 0.933 vs 1.107. Its only advantage — lower MDD (41.4% vs 52.6%) — is a tradeoff, not a strict improvement. Bootstrap P(candidate Sharpe > benchmark Sharpe) = 19.2%.

---

## 2. RESEARCH PATH

**Phase 1 (Data Audit)**: Audited 4 BTCUSDT files (15m/1h/4h/1d). Found perfect data quality: zero missing values, zero OHLC violations, single 32h gap (2018-02-08). 8 observations (Obs01–Obs08).

**Phase 2 (Price Behavior EDA)**: Characterized H4 return distribution and serial dependence structure. Key finding: NO statistically significant return persistence at ANY H4 scale (VR test, all p > 0.95). The dominant serial structure is volatility clustering (|return| ACF 100/100 lags significant), not directional persistence. 31 observations (Obs09–Obs39).

**Phase 3 (Signal Landscape EDA)**: Swept 4 entry types (54 combos) × 5 exit types (68 combos) × regime filter. Breakout (Type B) dominates the entry efficiency frontier (detection 0.839, 1 DOF). ATR trailing stop (Type Y) dominates exit Sharpe column. Best pair B+Y: Sharpe 1.064, MDD 44.6%. ALL exit types have churn >80% — churn is structural. 17 observations (Obs40–Obs56).

**Phase 4 (Formalization)**: Computed mutual information and Spearman rank correlations for 20 features × 6 horizons. All |ρ| < 0.05 — near-zero individual predictability. Formalized 2 entry classes, 2 exit classes, 1 filter class. 8/10 combinations POWERED. 8 propositions (Prop01–Prop08).

**Phase 5 (Go/No-Go)**: GO_TO_DESIGN. ΔSharpe vs buy-and-hold ≈ +0.46. ΔSharpe vs benchmark ≈ −0.13 (flagged as marginal). Value of design: independent validation of alpha surface + different risk profile.

**Phase 6 (Design)**: Specified 3 candidates — Cand01 (breakout + ATR trail, 3 DOF), Cand02 (+ D1 EMA21 filter, 4 DOF), Cand03 (ROC entry, 4 DOF). Pre-committed 6 rejection criteria. Full provenance chains from Obs → Prop → Cand.

**Phase 7 (Validation)**: Full-sample backtest, 4-fold anchored WFO, 2000-path circular block bootstrap, 6-fold jackknife, cost sensitivity, regime split, year-by-year analysis. Cand01: ALL 8 gates PASS (PROMOTE). Cand02: ALL gates PASS but redundant (+0.012 Sharpe for +1 DOF). Cand03: 2 gates FAIL (HOLD).

---

## 3. STRONGEST EVIDENCE

1. **Volatility clustering is the dominant serial structure in BTC H4** (Obs14, Obs23). |Return| ACF: 100/100 lags significant, lag1=0.261. Realized vol ACF lag1=0.986. This is orders of magnitude stronger than any return-level dependence and the foundation for ATR-based position management.

2. **No statistically significant return persistence at any H4 scale** (Obs16, Obs19, Tbl04). Variance ratio test with heteroskedasticity-robust inference: all VR ≤ 1.0, all p > 0.95. What prior research attributes to "trend persistence" is likely fat tails + drift + volatility clustering, not genuine directional serial dependence.

3. **Breakout entry eliminates churn entirely** (Test08, Tbl_churn_comparison). Cand01: 0/70 churn events. Benchmark: 107/219 = 49.1% churn rate. Breakout's natural re-entry barrier (new 120-bar high required) prevents the exit→re-enter→exit cycle. This is the single most important structural discovery.

4. **ALL entry types have >87% false positive rate; ALL exit types have >80% churn** (Obs41–44, Obs46–50, Prop04). These are structural properties of BTC price dynamics, not mechanism-specific deficiencies. No signal type tested escapes these constraints.

5. **Alpha converges across entry mechanisms** (Test01, Tbl_full_sample_comparison). Breakout (Sh 0.907) and EMA crossover (Sh 1.084) produce same-order Sharpe from the same underlying trend phenomenon. This confirms H_prior_2 extends to cross-mechanism redundancy — the alpha is generic.

6. **D1 regime filter is redundant for breakout entries** (Test01, Obs52). Cand02 filter blocked only 2/70 entries. New 120-bar highs inherently coincide with D1 close > EMA(21). The statistical significance of D1 conditioning (Obs37, p=0.0004) does NOT translate to strategy improvement for breakout-type entries.

7. **All individual features have |ρ| < 0.05 with forward returns** (Obs57, Tbl11). The information content of any single observable is near-zero. Strategy profit comes from asymmetric payoff structure (rare-event capture), not prediction accuracy (Prop01).

8. **At cost >105 bps RT, breakout dominates benchmark** (Test05, Tbl_cost_sensitivity). Zero churn means cost scaling 0.0025/bps (Cand01) vs 0.0065/bps (benchmark). Crossover at ~105 bps RT.

---

## 4. WHAT FAILED

### Hypotheses Refuted

- **"BTC H4 returns have positive autocorrelation at medium lags"** (H_prior_1): PARTIALLY REFUTED. Hurst 0.58 is nominal, but VR test — the more rigorous heteroskedasticity-robust test — shows NO significant persistence at any scale. The R/S estimator is upward-biased by volatility clustering.

- **"Speed advantage compensates for lower detection"** (Cand03 hypothesis): REFUTED. ROC(40) > 15% entry achieves faster detection (13.8 bars lag) but captures too few trends. Sharpe 0.45 fails R2 and WFO 0/4 fails R5.

### Signal Types Dominated

- **EMA crossover entry (Type A)**: Detection 10.5%, lag 53 bars. Occupied upper-right of efficiency frontier (high lag AND high FP). Dominated by breakout in all dimensions.

- **Volatility breakout entry (Type D)**: Intermediate on all metrics, least stable across time blocks (det_std=0.156). No frontier advantage.

- **Fixed % trailing stop (Type X)**: Highest churn (94%) of exit types. Fixed-percentage doesn't adapt to volatility regime.

- **Volatility-based exit (Type V)**: Longest hold (209 bars), highest MDD (24.2%), exposure 80–88%. Capital lock-in without risk-adjusted benefit.

### Candidates Rejected/Held

- **Cand03 (ROC + ATR Trail)**: HOLD. Gates R2 and R5 FAIL. Sharpe 0.45 < 0.867 threshold. WFO 0/4 wins. The "speed vs detection" tradeoff is decisively unfavorable.

- **Cand02 (Breakout + ATR Trail + D1 EMA21)**: PROMOTE but REDUNDANT. +0.012 Sharpe for +1 DOF. Filter blocked 2/70 entries. Rejected by DOF preference principle.

### Classes Eliminated at Formalization

- **Volume features**: EXCLUDED from state space. Category avg |ρ| = 0.012, definitively lowest (Obs58). TBR max |r| = 0.027, not economically meaningful (Obs30). Volume non-stationary across years (Obs27).

---

## 5. PRIOR HYPOTHESIS FINAL STATUS

| Hypothesis | Verdict | Evidence | Surprise? |
|-----------|---------|----------|-----------|
| H_prior_1: Trend persistence | **PARTIALLY CONFIRMED** | Hurst=0.58 nominal, VR test NO significance (Obs16, Obs19). Alpha exists (Sh 0.91) but may not be "persistence" per se. | YES — VR robustly shows no persistence, yet trend-following works. The mechanism is rare-event capture of fat-tailed moves, not exploitation of serial persistence. |
| H_prior_2: Cross-scale redundancy | **CONFIRMED** | Smooth monotonic VR profile (Obs16). Extended: cross-MECHANISM redundancy — breakout and EMA crossover converge on Sh ~0.9–1.1 (Test01). | No |
| H_prior_3: Entry lag vs FP tradeoff | **CONFIRMED** | 0/54 combos achieve lag<20 AND FP<50% (Obs53). Fundamental constraint. | No |
| H_prior_4: Exit churn structural | **CONFIRMED STRONGLY** | ALL 5 exit types churn >80% (Obs46–50). Breakout SOLVES churn via re-entry barrier (0/70, Test08). | YES — churn is 100% solvable at the ENTRY level, not exit level. Prior research focused on exit-level repair (X12–X19). |
| H_prior_5: Volume info ≈ 0 | **CONFIRMED** | TBR max |r|=0.027 (Obs30). Category last in information ranking (Obs58). | No |
| H_prior_6: D1 regime useful | **CONFIRMED WITH CAVEAT** | Statistically significant p=0.0004 (Obs37). But REDUNDANT for breakout entries (2/70 blocked). Filter is MDD/Sharpe tradeoff, not strict improvement (Obs52). | YES — "useful" at the population level does NOT mean useful for all entry types. |
| H_prior_7: Low exposure (~45%) | **PARTIALLY REFUTED** | 15/20 pairs >60% exposure (Obs55). Best pair B+Y has 30.1% — LOWER than 45%. Exposure is entry-type-dependent. | Mild |
| H_prior_8: Short-side negative EV | **NOT TESTED** | Long-only constraint accepted as input. | N/A |
| H_prior_9: Cost dominance | **NOT DIRECTLY TESTED** | Fixed 50 bps throughout. Cost sensitivity confirms: 50→15 bps raises Cand01 Sharpe 0.907→0.994 (+0.087). Benchmark: 1.084→1.317 (+0.233). Cost benefits benchmark MORE (more trades = more cost drag). | Mild — confirms prior but quantifies asymmetry |
| H_prior_10: Complexity ceiling | **CONFIRMED** | 3-DOF Cand01 matches 4-DOF Cand02 (+0.012 Sharpe). 1-DOF breakout entry outperforms 2-DOF ROC entry. Signal TYPE selection matters, not parameter count. | No |

---

## 6. MATHEMATICAL CONCLUSION

### Where is exploitable structure in BTC H4?

BTC H4 returns are approximately a random walk with:
1. **Fat tails** (excess kurtosis 20.4, 3σ events 6.5–7.8× Normal frequency)
2. **Positive drift** (mean +0.0148%/bar ≈ +45% annualized)
3. **Strong volatility clustering** (|return| ACF long-memory, realized vol ACF lag1=0.986)
4. **Rare large moves** concentrated in high-volatility regimes (12:1 ratio)

There is NO statistically significant directional persistence at any H4 scale (VR test). The exploitable structure is NOT "trends persist" but rather: **rare large upward moves exist, are detectable in real-time via price-level breakout, and produce sufficient magnitude to pay for the cost of frequent false entries.**

### Best function class

**Rare-event detector + volatility-adaptive stop**: f_entry = 𝟏{close > max(high, N bars)}, f_exit = {close < peak − m × ATR(p)}.

Why this class and not others:
- **Breakout over EMA crossover**: Breakout directly DETECTS the phenomenon (price at new highs) rather than attempting to INFER direction from smoothed price differences. Detection rate 0.839 vs 0.105. Zero churn vs 49%.
- **Breakout over ROC threshold**: Breakout requires 1 DOF vs 2, achieves higher detection (84% vs 54%), and dominates across ALL exit pairings.
- **ATR trail over fixed trail**: ATR adapts to volatility regime (leverages the strongest serial structure — Obs14). Fixed trail cannot adjust to BTC's extreme volatility clustering.
- **ATR trail over time-based exit**: ATR trail provides downside protection during adverse moves. Time-based exit holds through drawdowns with no protection.

### Information ceiling

Individual feature |ρ| < 0.05 with forward returns. Maximum MI (binned) = 0.053 bits (vol60 at k=20). The theoretical ceiling on any single-feature predictor is extremely low.

The practical ceiling is better estimated from the alpha itself: benchmark Sharpe 1.08 represents the best-known extraction from this data with 5+ DOF. The breakout approach (3 DOF) achieves 0.91 — 84% of benchmark. The remaining gap (~0.17 Sharpe) likely comes from the benchmark's higher trade frequency (219 vs 70 trades, √BR effect) rather than superior information.

**Estimated room to improve**: ~0.1–0.2 Sharpe at 50 bps cost. The dominant lever is cost reduction (50→15 bps adds ~0.23 Sharpe for benchmark, ~0.09 for Cand01).

### Complexity vs performance

**Optimal DOF ≈ 3–5.** Cand01 (3 DOF, Sh 0.907) ≈ Cand02 (4 DOF, Sh 0.920). Benchmark (5+ DOF, Sh 1.084) gains marginal improvement from extra filters (VDO, EMA cross-down exit) that add trade frequency. Beyond 5 DOF, prior research confirms zero improvement (V8/40+ params adds nothing — H_prior_10). The complexity ceiling is real and low.

---

## 7. PRACTICAL RECOMMENDATION

### STOP — No candidate warrants promotion over benchmark

The benchmark (VTREND E5+EMA21D1) achieves higher Sharpe (1.084 vs 0.907), higher CAGR (58.2% vs 38.6%), and higher Calmar (1.107 vs 0.933). Cand01 wins only on MDD (41.4% vs 52.6%). This is a tradeoff, not improvement.

### Why no improvement was found

1. **The alpha surface is singular**: BTC H4 long-only at 50 bps cost has approximately ONE exploitable phenomenon (rare upward moves captured by trend-following). All mechanism variants extract the SAME alpha — cross-mechanism Sharpe converges to ~0.9–1.1.

2. **The benchmark already sits near the frontier**: VTREND's EMA crossover + VDO filter + D1 regime + dual exit (ATR trail OR EMA cross-down) achieves higher trade frequency (219 vs 70) which, despite high churn cost, produces higher aggregate alpha per unit time.

3. **The breakout advantage (zero churn) is insufficient**: Breakout eliminates 107 churn trades (saving ~53.5% equity in cost) but this only narrows the gap — it doesn't close it. The benchmark's churn trades include enough profitable ones to offset their cost.

### Ranked directions for improvement

1. **Cost reduction** (biggest lever — engineering, not research)
   - 50→15 bps: benchmark Sh 1.08→1.32, Cand01 Sh 0.91→0.99
   - Binance VIP0+BNB: ~15–20 bps RT realistic
   - Estimated effort: LOW (exchange setup, fee tier)
   - Expected payoff: +0.1 to +0.3 Sharpe — larger than any algorithm change tested

2. **Instrument change** (futures/perps — new alpha surface)
   - Perps allow short-side exposure + lower cost (maker rebates)
   - Funding rate creates distinct alpha surface not present in spot
   - Estimated effort: MEDIUM (new data pipeline, different risk model)
   - Expected payoff: UNKNOWN — new research required

3. **More data** (longer history or higher frequency)
   - 8.5 years provides 70 trades for breakout, 219 for EMA crossover
   - Pre-2017 BTC data exists but market structure was fundamentally different
   - 15m data available but H4 is already optimal per prior research
   - Estimated effort: LOW–MEDIUM
   - Expected payoff: LOW (more data improves estimation precision, not alpha)

4. **Different market** (ETH, SOL, multi-asset)
   - Prior research (X20): BTC-only Sh 0.735 >> best portfolio 0.259
   - Altcoins dilute BTC alpha (median altcoin Sh 0.42)
   - Estimated effort: MEDIUM
   - Expected payoff: NEGATIVE per existing evidence

---

## 8. ANTI-SELF-DECEPTION

### What would make this conclusion wrong?

**Most fragile assumptions**:

1. **"Benchmark Sharpe 1.084 is the right comparison target."** The benchmark was re-implemented with binary sizing for fair comparison. If the original vol-target benchmark (published Sharpe 1.19) is the true target, the gap widens to 0.28. If the benchmark implementation has a bug (lookahead, incorrect VDO, etc.), the gap could narrow. The comparison is only as valid as the benchmark implementation.

2. **"Breakout N=120 is the right parameter."** N=120 was chosen from Tbl11 information ranking, not optimized. Phase 7 used fixed parameters (no parameter sweep in validation). A sweep across N ∈ [40, 160] might find N=80 or N=60 with higher Sharpe, but this risks overfitting with only 70 trades.

3. **"50 bps RT is the right cost model."** At 15 bps, Cand01 Sh=0.994 vs benchmark 1.317 — the gap WIDENS. At 100 bps, Cand01 Sh=0.784 vs benchmark 0.761 — breakout WINS. The conclusion is cost-dependent: breakout is only superior in very high-cost regimes (>105 bps).

**Data limitations**:

4. **Sample size**: 70 trades for Cand01, 219 for benchmark. Per-trade statistics have high variance. Bootstrap 90% CI for ΔSharpe: [−0.55, +0.16] — the interval includes zero and positive values. Cannot exclude that breakout is equivalent or slightly better than benchmark with more data.

5. **Regime coverage**: Block 3 (2021-11 to 2024-01) has ZERO target events. The signal landscape was measured predominantly on bull/recovery markets. Breakout underperforms in WFO folds 2 and 4 (bear/range periods). A permanently lower-volatility BTC regime would hurt all trend-following strategies but hurt breakout more (fewer signals per unit time).

6. **Survivorship**: BTC is the surviving cryptocurrency. The same analysis on a failed asset would show different results. The alpha includes a selection effect.

**Method limitations**:

7. **WFO 50% is borderline**: 2/4 folds positive is the minimum passing threshold. One more negative fold would flip the verdict. The chronological structure of WFO means bull periods (folds 1, 3) show positive delta while bear periods (folds 2, 4) show negative. With only 4 folds, the bull/bear split dominates the statistic.

8. **Bootstrap assumes stationarity within blocks**: Circular block bootstrap preserves local dependence but assumes the block-level process is stationary. BTC has undergone structural changes (ETF launch, institutional adoption, volume migration to CME) that may violate this.

**Conditions that could reverse the conclusion**:

9. If BTC transitions to a permanently higher-volatility regime with more frequent large moves, breakout's zero-churn advantage would compound and could overtake the benchmark.

10. If exchange costs structurally increase (regulatory, compliance), breakout's cost scaling advantage (0.0025/bps vs 0.0065/bps) becomes the dominant factor above ~105 bps.

11. If the benchmark's VDO filter truly carries zero information (prior research H_prior_5 + Obs30), removing it from the benchmark could reduce benchmark Sharpe closer to Cand01's level, making the comparison tighter.

**Known unknowns**:

12. Cand01's behavior in a multi-year sideways market (like 2022-era) with NO breakout signals: the strategy sits flat, earning zero while paying opportunity cost. The benchmark's EMA crossover generates trades in such periods (some profitable). Whether this is a feature or a bug depends on risk preference.

13. The interaction between breakout entry and vol-target position sizing (f=0.30) was NOT tested. The published benchmark uses vol-target; Cand01 was tested binary-only. Vol-target could differentially benefit one or the other.

---

## 9. FINAL STATUS

**FINALIZED_BENCHMARK_OPTIMAL**

The VTREND E5+EMA21D1 benchmark is near-optimal for BTC H4 spot long-only at 50 bps RT cost. The X27 research, starting from raw data with no incumbent assumption, independently converged on the same alpha surface (trend-following via rare-event capture) and confirmed:

- The alpha is real (Cand01 P(Sharpe > 0) = 99.2%)
- The alpha is generic (two different entry mechanisms produce Sharpe ~0.9–1.1)
- The information ceiling is low (all |ρ| < 0.05, optimal DOF ≈ 3–5)
- The dominant improvement lever is cost reduction, not algorithm change
- Breakout entry offers a valid ALTERNATIVE risk profile (lower MDD, lower Sharpe) but does NOT improve upon the benchmark

The breakout approach's structural advantage — zero churn — is real and valuable, but insufficient to overcome the benchmark's higher trade frequency advantage at standard cost levels. The crossover occurs only above ~105 bps RT, well above realistic exchange costs.

---

## Deliverables

- `08_final_report.md` (this document)
- `manifest.json` (updated to final)
