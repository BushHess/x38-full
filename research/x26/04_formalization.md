# Phase 4: Formalization

**Date**: 2026-03-11
**Inputs**: 01_audit_state_map.md, 02_flat_period_eda.md, 03_phenomenon_survey.md (Obs01–Obs29, P1–P4)
**Selected phenomena**: P1 (Mean-Reversion within FLAT), P2 (24h Autocorrelation)
**Method**: Decision-theoretic formalization + empirical power analysis

---

## 1. Decision Problem

### 1.1 Signal Event

An opportunity arises at each H4 bar close during a VTREND FLAT period. The mean-reversion property (Obs17: VR(2)=0.762 per-period) implies that the next bar's return is negatively correlated with the current bar's return. In a long-only BTC spot context, the actionable component is: **buy after a down bar** (expecting positive reversion).

### 1.2 Action Space

Binary: a_t ∈ {0, 1}

- a_t = 1: buy BTC at bar t close, hold for fixed horizon (1 bar for Class A, k bars for Class B)
- a_t = 0: remain flat (cash)

Continuous sizing is excluded: X21 proved entry-feature IC = -0.039 (no sizing information at entry).

### 1.3 Utility Function

**Standalone** (Classes A, B):

    ΔU_t = a_t × (r_{t+1:t+h} - c)

where r is the forward return over holding period h, and c is the round-trip cost (50 bps baseline).

**Filter** (Class C):

    ΔU_t = U_VTREND(modified entries) - U_VTREND(original entries)

Class C does not deploy capital — it modifies VTREND's entry decisions. Its utility is the improvement (or degradation) of VTREND's performance.

### 1.4 VTREND Interaction

- **Classes A, B (standalone)**: Additive. U_combined = U_VTREND + U_new. They operate during non-overlapping time windows (FLAT only), so VTREND equity is unaffected. Capital conflict rate is low: 1.3% for Class A (1-bar hold), 6.8% for Class B (k=5). At conflict, Class A/B must exit to free capital for VTREND — this is a hard constraint, not a tunable parameter.

- **Class C (filter)**: Conditional. U_new is defined ONLY through its effect on VTREND. It either improves VTREND by suppressing bad entries (positive ΔU) or degrades it by suppressing good entries (negative ΔU).

### 1.5 Cost Model

- Standalone: 50 bps RT (conservative), with sensitivity at 30, 20, 15 bps
- Filter: 0 bps (no additional trades; cost is already in VTREND's trades)
- Cash opportunity cost: during Class A/B positions, capital cannot enter VTREND. Quantified: 1.3%–12.1% of signals overlap with a VTREND entry window (Section 5).

---

## 2. Information Set

### 2.1 Observable Variables at Decision Time

| Variable | Symbol | Source |
|----------|--------|--------|
| Current bar return | r_t | H4 OHLCV |
| Cumulative k-bar return | R_{t-k:t} | H4 OHLCV |
| VTREND state | VT_t ∈ {FLAT, IN_TRADE} | Engine state |
| Bar-level volatility (rolling) | σ_t | H4 close |
| Preceding flat-period VR | VR(2)_{flat} | Computed from flat-period returns |
| Bar index within flat period | pos_t | State classification |

### 2.2 Central Question

**I(ΔU_new ; V_new | P_t, VT_t) > 0?**

Conditioning on VT_t = FLAT and P_t (price history):

| Information channel | MI proxy (nats) | MI (millibits) | p-value |
|---------------------|----------------:|---------------:|--------:|
| r_t → r_{t+1} (lag-1 autocorrelation) | 0.00148 | 2.14 | 0.216 |
| VR(2)_preceding → trade_ret (filter) | 0.00141 | 2.03 | 0.515 |

**Both information channels carry ≈ 2 millibits** — essentially zero mutual information. For context, perfect prediction of the next bar's return would carry ~11,500 millibits (for Gaussian with σ=157 bps). The mean-reversion signal contains 0.02% of the information needed for profitable trading.

### 2.3 Critical Discrepancy: Phase 3 vs Phase 4

Phase 3 scored P1 with Cohen's d = -0.866 (STRONG). This measures the **existence** of mean-reversion: "is VR(2) ≠ 1.0?" — answer: yes, overwhelmingly (p < 1e-23).

Phase 4 measures the **exploitation** of mean-reversion: "does knowing r_t predict r_{t+1} with enough precision to profit?" The bar-level ρ(1) = -0.054 — an order of magnitude smaller than the per-period VR-based estimate of ρ ≈ -0.238.

The discrepancy arises because the per-period VR(2) = 0.762 is the **mean of within-period VRs**, each computed on very short windows (median 11 bars). Small-sample VR estimators are downward-biased and noisy (VR std = 0.274). The bar-level correlation across the full FLAT sample is the correct measure for trading:

**ρ(1)_bar-level = -0.054, not -0.238**

This 4.4× reduction is the gap between "the phenomenon exists" and "the phenomenon is tradeable."

---

## 3. Propositions

### Prop01 [HIGH confidence] — Mean-reversion exists but is economically negligible
**Source**: Obs17 (VR per-period), Phase 4 Section 1
**Statement**: BTC H4 returns during VTREND FLAT periods exhibit negative lag-1 autocorrelation (ρ = -0.054), confirming per-period VR < 1 (Obs17). However, the bar-level effect translates to only +2.9 bps expected return per contrarian trade (buy after down bar), which is NOT statistically significant (t=1.24, p=0.216).

### Prop02 [HIGH confidence] — No function class can overcome the cost barrier
**Source**: Phase 4 Sections 1, 2, 6
**Statement**: At the observed bar-level ρ(1) = -0.054, the maximum gross return per trade is 2.9 bps (Class A) to 9.1 bps (Class B, k=5). The breakeven cost is approximately 3–9 bps RT. Even the most optimistic realistic cost (Binance VIP0+BNB: ~15 bps RT) exceeds the gross by 2–5×. No standalone mean-reversion strategy can be profitable.

### Prop03 [HIGH confidence] — Preceding flat-period VR has zero predictive power for trade quality
**Source**: Phase 4 Section 3
**Statement**: The VR(2) of the flat period preceding a VTREND trade has no correlation with the trade's return (Spearman ρ = 0.053, p = 0.515; KW across terciles p = 0.687). Class C (VR-conditional filter) has no information to act on.

### Prop04 [MEDIUM confidence] — The mean-reversion signal weakens at longer horizons
**Source**: Phase 4 Section 2
**Statement**: Multi-bar forward returns after flat-period drawdowns are near zero (k=2: -2.2 bps, k=5: +9.1 bps) or negative (k=10: -10.8 bps, k=20: -27.9 bps). The positive k=5 value is borderline (p=0.088). At k=20, forward returns are significantly negative (p=0.010), suggesting that flat-period drawdowns are not mean-reverting but rather precursors to further decline. This is consistent with the D1 EMA(21) regime filter: extended flat periods during bear markets are followed by more downside.

### Prop05 [HIGH confidence] — All three classes are UNDERPOWERED
**Source**: Phase 4 Section 4
**Statement**: Despite large N (4,000–5,000+ signals), all observed effect sizes are smaller than their MDE. The ratio |d|/MDE ranges from 0.23 to 0.92. The largest (Class B k=20 at 0.92) has a significant p-value but with NEGATIVE direction (losses, not gains). The power analysis confirms that no class has a detectable positive signal.

---

## 4. Admissible Function Classes

### Class A: Single-Bar Contrarian Long

**Mathematical form**:

    a_t = 1{VT_t = FLAT ∧ r_t < -θ × σ_t}

Buy at bar t close if VTREND is FLAT and the bar's return falls below -θ standard deviations. Exit at bar t+1 close (fixed 1-bar hold).

| Property | Value |
|----------|-------|
| DOF | 1 (θ, threshold) |
| Evidence | Obs17 (VR<1), ρ(1)=-0.054 bar-level |
| N total | 5,188 (θ=0); 1,009 (θ=1.0) |
| N/year | 610 (θ=0); 119 (θ=1.0) |
| Gross return | +2.9 bps (θ=0); +11.9 bps (θ=1.0) |
| Significance | p=0.216 (θ=0); p=0.169 (θ=1.0) |
| Effect size d | 0.017 |
| MDE | 0.039 |
| Power status | **UNDERPOWERED** (|d|/MDE = 0.44) |

**Known caveats**:
- Gross return is below ANY realistic transaction cost
- Increasing θ raises gross per trade but reduces N without improving significance
- At θ=1.5 (largest testable), gross reaches 25.2 bps (p=0.061) — still below 30 bps cost
- Long-only constraint halves the theoretical edge (cannot profit from up→down reversals)

### Class B: Multi-Bar Range-Reversion Long

**Mathematical form**:

    a_t = 1{VT_t = FLAT ∧ R_{t-k:t} < -θ × σ_k}

Buy at bar t close if VTREND is FLAT and the cumulative return over past k bars is negative (or below -θ × k-bar volatility). Exit at bar t+k close or when FLAT ends (whichever first).

| Property | Value |
|----------|-------|
| DOF | 2 (k: lookback, θ: threshold) |
| Evidence | Obs17 (VR declining with horizon) |
| Best case (k=5) | N=4,708, gross +9.1 bps, p=0.088 |
| Other horizons | k=2: -2.2 bps; k=10: -10.8 bps; k=20: -27.9 bps |
| Effect size d (k=5) | 0.025 |
| MDE (k=5) | 0.041 |
| Power status | **UNDERPOWERED** (|d|/MDE = 0.61) |

**Known caveats**:
- Only k=5 shows positive gross; all others are zero or negative
- k=20 is significantly NEGATIVE (p=0.010) — longer-horizon mean-reversion does NOT hold
- Capital conflict with VTREND: 6.8% (k=5) to 12.1% (k=10) of signals overlap
- 2 DOF invites overfitting to the one positive k value

### Class C: VR-Conditional VTREND Entry Filter

**Mathematical form**:

    suppress VTREND entry if VR(k)_{preceding_flat} < τ

Compute VR(k) from the flat period preceding a VTREND entry signal. If VR is below threshold τ (strongly mean-reverting), suppress the entry (hypothesis: the EMA crossover is a mean-reverting blip, not a true trend).

| Property | Value |
|----------|-------|
| DOF | 2 (k: VR window, τ: threshold) |
| Evidence | Obs17 (VR varies, std=0.274) |
| N (trade pairs) | 153 |
| N/year | 18 |
| Effect size d | 0.082 |
| MDE | 0.227 |
| Power status | **UNDERPOWERED** (|d|/MDE = 0.36) |
| Spearman ρ(VR, trade_ret) | 0.053, p=0.515 |
| KW across terciles | p=0.687 |

**Known caveats**:
- VR of preceding flat has ZERO predictive power for trade return
- Tercile analysis shows non-monotonic pattern (T1: 154, T2: 431, T3: 251 bps)
- Only 153 testable pairs (flat periods with ≥5 bars followed by a trade)
- Even if an effect existed, N=18/year → WFO folds of ~4.5 trades each (unusable)

---

## 5. Rejected Function Classes

### R1: Short-Side Mean-Reversion
**Rejection**: X11 proved BTC shorts are negative-EV at ALL timescales (Short Sharpe -0.640, MDD 92%). Mean-reversion requires both long and short legs for symmetric exploitation; the short leg is fatal.

### R2: Cross-Asset Mean-Reversion Portfolio
**Rejection**: X20 proved altcoins dilute BTC alpha (best portfolio Sharpe 0.259 vs BTC-only 0.735). Cross-asset mean-reversion spreads would face the same problem: BTC alpha is unique, not replicated by altcoin pair dynamics.

### R3: Entry-Feature Enhanced Mean-Reversion
**Rejection**: X21 proved CV IC = -0.039 for entry features (VDO, EMA spread, ATR percentile, regime strength). entry_filter_lab proved volume/microstructure information ceiling ≈ 0. Adding features to the mean-reversion signal cannot improve it because the features themselves carry no information.

### R4: Calendar-Timed Mean-Reversion
**Rejection**: P4 (Obs28) showed hourly return effects exist but have η² = 0.0008 and the best/worst hours shift across time blocks. Conditioning mean-reversion trades on hour-of-day would add 1 DOF (hour selection) for ≈ 5 bps additional expected return — insufficient even with perfect hour identification.

### R5: Post-Exit Conditional Strategy
**Rejection**: P3 (Obs23) showed post-exit winner/loser asymmetry is not significant (d=0.057, p=0.386), unstable across time blocks (sign flips in blocks 3-4), and requires knowing trade outcome at exit time (look-ahead). No function class can be built on an insignificant, unstable signal that requires future information.

### R6: Churn Filter via Mean-Reversion State
**Rejection**: X12–X19 exhaustively studied churn filtering. The best promoted filters (X14_D, X18) use static suppress based on logistic models and α-percentile ranking — both of which already incorporate price dynamics information. X22 showed churn filters HURT at <30 bps cost. Any Class C variant is either (a) a rediscovery of X14/X18 or (b) an inferior version using less information (VR alone vs multi-feature model).

---

## 6. Power Analysis

### 6.1 Summary Table

| Class | N_total | N/year | Observed |d| | MDE (α=0.05, β=0.80) | Ratio |d|/MDE | Status |
|-------|--------:|-------:|-----------:|------:|---------------:|--------|
| A (θ=0) | 5,188 | 610 | 0.017 | 0.039 | 0.44 | UNDERPOWERED |
| A (θ=1.0) | 1,009 | 119 | 0.043 | 0.088 | 0.49 | UNDERPOWERED |
| B (k=5) | 4,708 | 554 | 0.025 | 0.041 | 0.61 | UNDERPOWERED |
| B (k=20) | 4,180 | 492 | 0.040 | 0.043 | 0.92 | UNDERPOWERED* |
| C | 153 | 18 | 0.082 | 0.227 | 0.36 | UNDERPOWERED |

*Class B (k=20) is close to MDE but the effect is in the WRONG direction (negative returns, not positive).

### 6.2 WFO Fold Sizes

Total FLAT bars: 10,721

| Folds | Bars/fold | Years/fold | Trades (Class A, θ=0) |
|------:|----------:|-----------:|----------------------:|
| 4 | 2,680 | 1.2 | ~153 |
| 5 | 2,144 | 1.0 | ~122 |

WFO is feasible for Classes A and B (sufficient N per fold). Class C has only ~18 trades/year → ~4-5 trades per fold → WFO is not meaningful.

### 6.3 Effect Size vs MDE

For any class to be POWERED, it would need |d| > 1.5 × MDE:
- Class A: needs |d| > 0.058, observed 0.017 → 3.4× shortfall
- Class B (k=5): needs |d| > 0.061, observed 0.025 → 2.4× shortfall
- Class C: needs |d| > 0.340, observed 0.082 → 4.1× shortfall

**No class is within reach of the POWERED threshold.**

### 6.4 Verdict

All three admissible classes are **UNDERPOWERED**. The mean-reversion phenomenon is statistically real (Phase 3: d=-0.87 for VR ≠ 1) but the bar-level exploitable signal is an order of magnitude smaller (d ≈ 0.02). The gap between "phenomenon exists" and "phenomenon is profitable" is the central finding of this formalization.

---

## 7. Complementarity Proof

### 7.1 Time Overlap

All three classes operate during VTREND FLAT periods by construction.

| Class | Operates during | Time overlap with VTREND IN_TRADE |
|-------|----------------|----------------------------------|
| A | FLAT only | 0% |
| B | FLAT only | 0% |
| C | FLAT→entry transition | 0% (modifies entry decision, no capital) |

Correlation with VTREND returns: ρ = 0.00 for Classes A and B (non-overlapping time windows).

### 7.2 Capital Conflict

| Class | Hold period | Conflicts/signals | Conflict rate |
|-------|-------------|------------------:|-------------:|
| A | 1 bar | 68/5,256 | 1.3% |
| B (k=5) | 5 bars | 356/5,255 | 6.8% |
| B (k=10) | 10 bars | 635/5,253 | 12.1% |

Class A conflict is negligible (1.3%). Class B (k=10) exceeds the 10% threshold — capital allocation and conflict resolution would be required.

**Conflict resolution** (if Class B were viable): priority to VTREND. If VTREND entry fires while Class B is in position, close Class B immediately and enter VTREND. Cost: one additional RT on the Class B position.

### 7.3 VTREND Degradation Assessment

- **Classes A, B**: Cannot degrade VTREND because they do not modify VTREND's signals. Capital conflict (1.3%–12.1%) could cause missed VTREND entries in edge cases, but with VTREND priority rule, the conflict cost is one additional RT on the mean-reversion position, not a missed VTREND trade.

- **Class C**: By design modifies VTREND entries. VR-conditional suppression could degrade VTREND if it suppresses good trades. Empirical evidence (Section 3): suppressing low-VR entries removes trades with mean return 5–289 bps (depending on threshold), while kept trades have 278–351 bps. The difference is not statistically significant at any threshold (MW p=0.82). **Class C cannot demonstrably improve VTREND, but it also cannot demonstrably harm it — the signal is pure noise.**

### 7.4 Complementarity Verdict

All three classes are complementary to VTREND in the trivial sense: they operate during non-overlapping time windows and have zero correlation with VTREND returns. However, this complementarity is vacuous because none of the classes has a positive expected utility. A strategy with ΔU ≤ 0 is complementary to anything — it simply adds nothing.

---

## Summary

### Central Finding

BTC H4 returns during VTREND FLAT periods exhibit statistically real mean-reversion (VR(2)=0.762 per-period, p < 1e-23, Phase 3). However, the bar-level autocorrelation is only ρ(1) = -0.054 — translating to a gross expected return of +2.9 bps per contrarian trade. This is:

- **17× smaller** than the 50 bps RT cost
- **5× smaller** than the most optimistic realistic cost (15 bps RT)
- **Not statistically significant** (p=0.216)

No function class — bar-level contrarian (Class A), multi-bar mean-reversion (Class B), or VR-conditional VTREND filter (Class C) — can overcome this fundamental constraint. All three are UNDERPOWERED with observed effect sizes 2–4× below their MDEs.

The mean-reversion property is a genuine statistical fact about BTC flat-period microstructure. It is not an artifact of small samples, biased estimators, or look-ahead. It is simply **too small to trade**.

### Implications for Phase 5 Gate Decision

This formalization provides strong evidence for:

**STOP** (economically underpowered for trading purposes)

The P1/P2 phenomena are real but economically negligible. No admissible function class achieves POWERED status. The information content is ~2 millibits. Phase 5 should confirm this conclusion or identify a specific flaw in this analysis before proceeding to design.

> **Supersession note (2026-03-13)**: Original verdict label "STOP_FLAT_PERIODS_ARE_NOISE" corrected.
> The phenomena are real (VR=0.762, p<1e-23) but too small to trade (2.9 bps vs 15-50 bps cost).
> Correct characterization: **underpowered and economically dominated**, not "noise".
> See methodology.md §8c for terminology discipline.

---

## Verification Artifacts

### Code
- `code/phase4_formalization.py` — conditional returns, multi-bar analysis, VR-trade correlation, power analysis, complementarity, information content

### Tables
- `tables/Tbl07_conditional_returns.csv` — bar-level conditional returns by threshold
- `tables/Tbl09_power_analysis.csv` — summary power analysis for all classes
- `tables/Tbl10_complementarity.csv` — complementarity metrics

---

## END-OF-PHASE CHECKLIST

### 1. Files created
- `04_formalization.md` (this file)
- `code/phase4_formalization.py`
- `tables/Tbl07_conditional_returns.csv`
- `tables/Tbl09_power_analysis.csv`
- `tables/Tbl10_complementarity.csv`

### 2. Key Prop IDs created
- **Prop01**: Mean-reversion exists but is economically negligible (bar-level ρ=-0.054, p=0.216)
- **Prop02**: No function class can overcome the cost barrier (gross 3–9 bps vs 15–50 bps cost)
- **Prop03**: Preceding flat-period VR has zero predictive power for trade quality (ρ=0.053, p=0.515)
- **Prop04** [MEDIUM]: Mean-reversion weakens/reverses at longer horizons (k=20: -27.9 bps, p=0.010)
- **Prop05**: All three classes are UNDERPOWERED (|d|/MDE = 0.23 to 0.92)

### 3. Blockers / uncertainties
- The per-period VR (d=-0.87) vs bar-level ρ (d=0.017) discrepancy deserves methodological discussion: per-period VR is biased downward in small samples. Phase 3's "STRONG" S1 score was for phenomenon existence, not economic magnitude.
- Class B (k=5) is the closest to significance (p=0.088) but with gross of only 9.1 bps — still below any cost scenario.
- Class B (k=20) is significantly negative — suggesting that flat-period drawdowns may be trend-continuation signals in bear markets, not mean-reversion opportunities. This is consistent with D1 EMA(21) regime dynamics (Obs08).

### 4. Gate status
**STOP_FLAT_PERIODS_ARE_NOISE**

Rationale: All three admissible function classes are UNDERPOWERED. The bar-level mean-reversion signal contains ~2 millibits of mutual information — 0.02% of what would be needed for profitable trading. No exploitation mechanism can bridge the 5–17× gap between gross return and transaction cost. BTC spot flat-period microstructure is a statistically real phenomenon that is economically untradeable.
