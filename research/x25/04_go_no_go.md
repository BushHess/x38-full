# Phase 4: Synthesis / Go-No-Go Decision

**Date**: 2026-03-10
**Inputs**: 01_raw_eda.md (Obs01–Obs14), 02_trade_eda.md (Obs15–Obs26), 03_formalization.md (Prop01–Prop06), Figures 01–14, Tables 01–06
**Protocol**: Synthesis only. No design. No candidate formulas.

---

## 1. What the data actually showed

**Finding 1**: Taker buy ratio has zero predictive power for forward returns at all horizons tested.
|ρ| ≤ 0.029 at t+1, t+6; non-significant at t+24. The statistical significance at short horizons is driven entirely by n=18,621, not by effect magnitude.
[Obs03, Tbl02]

**Finding 2**: The TBR→return relationship is non-stationary — the sign oscillates between negative and positive with half-cycles of 3–6 months.
A filter exploiting a relationship that flips sign cannot maintain stable positive ΔU over time.
[Obs07, Fig08]

**Finding 3**: Volume is symmetrically elevated during strong moves in both directions.
Up_strong vs down_strong volume: p=0.149, rank-biserial=0.036. Volume measures magnitude of participation, not directional conviction. For a long-only filter, this symmetry is fatal.
[Obs05, Obs11, Fig03, Tbl01]

**Finding 4**: Volume profiles around entry are indistinguishable between winners and losers.
Normalized volume median lines overlap from bar -20 through bar +10. IQR bands overlap completely. No separation at any offset.
[Obs15, Fig09]

**Finding 5**: TBR profiles around entry are indistinguishable between winners and losers.
Both groups show the same mechanical rise (0.49→0.52) in bars [-5, 0], then revert. The rise is driven by the entry condition (EMA cross-up requires recent price rises ↔ TBR > 0.5 contemporaneously). Zero differential information.
[Obs16, Obs21, Fig10]

**Finding 6**: At the entry bar, all five volume/microstructure features fail to separate winners from losers.
TBR (single bar, 5-bar mean, 10-bar mean), relative volume, ATR/price — all p > 0.39, all |rank-biserial| < 0.08. With n=78 winners and n=123 losers, these tests have adequate power for medium effects (d ≈ 0.35). The absence of signal is informative, not a power problem.
[Obs17, Tbl05]

**Finding 7**: VDO at entry is the sole feature approaching marginal significance (p=0.086, rank-biserial=0.144).
Winners have slightly higher median VDO (0.0054 vs 0.0035). However, VDO-to-return correlation is NOT significant (r=0.093, p=0.190). The effect size d ≈ 0.29 is below the minimum detectable effect of 0.41.
[Obs18, Obs25, Fig12, Tbl06]

**Finding 8**: VDO values at entry cluster just above zero (IQR 0.001–0.010).
The entry gate VDO > 0 creates a hard floor. Most entries have VDO barely above the threshold, compressing the dynamic range available for any residual filter.
[Obs24, Fig12, Fig13]

**Finding 9**: Regime conditioning (bull/bear) does not reveal hidden TBR predictive content.
Both regimes show similar weak negative correlations at short horizons. At t+24, both are non-significant with different signs. Splitting by regime adds noise, not signal.
[Obs08, Fig07, Tbl03]

**Finding 10**: The 5 worst losers show no common volume or TBR pattern at entry.
They span different years, price regimes, and volume contexts. At the point of entry, they visually resemble typical entries. The subsequent price drop is what makes them losers, not any identifiable entry-bar feature.
[Obs23, Fig14a–e]

---

## 2. What survived formalization

**Prop01** — Volume and TBR carry no incremental entry-bar information for ΔU_t. **Confidence: HIGH.**
Five independent tests across TBR (3 lookbacks), relative volume, and ATR/price yield consistent nulls (all p > 0.39). This is the central result.
[Prop01 ← Obs15, Obs16, Obs17]

**Prop02** — The marginal VDO signal (p=0.086) is likely a floor artifact, not genuine predictive content. **Confidence: MEDIUM.**
The VDO > 0 gate truncates the distribution. The residual range (IQR 0.001–0.010) is narrow. The VDO-return correlation is not significant (p=0.190). The effect is more consistent with sampling variability in a truncated distribution than with exploitable information. Cannot definitively rule out a small true effect.
[Prop02 ← Obs18, Obs24, Obs25]

**Prop03** — The pre-entry TBR rise is mechanical and information-free for filter purposes. **Confidence: HIGH.**
TBR increases to ~0.52 before entry for BOTH winners and losers identically. This is a consequence of the entry condition, not a predictive feature.
[Prop03 ← Obs21, Obs01, Obs16]

**Prop04** — TBR predictive content, if any, is non-stationary and economically negligible. **Confidence: HIGH.**
Rolling analysis shows oscillating sign with 3–6 month half-cycles. Even if a small effect exists in some sub-periods, a static filter cannot exploit it.
[Prop04 ← Obs03, Obs04, Obs07, Obs13]

**Prop05** — Volume level is symmetric across up/down moves and uninformative for long-only entry filtering. **Confidence: HIGH.**
Volume measures participation magnitude, not direction. The up/down symmetry (p=0.149) means high volume at entry is equally likely to precede winning or losing trades.
[Prop05 ← Obs05, Obs11, Obs15, Obs17]

**Prop06** — The winner/loser volatility gap is a regime property, not an exploitable entry feature. **Confidence: MEDIUM-HIGH.**
Winners enter at slightly higher ATR/price, but this difference persists across the entire [-20, +10] window and is not significant at the entry bar (p=0.715). It reflects regime-level context already captured by the ATR trail.
[Prop06 ← Obs19, Obs26, Tbl05]

---

## 3. SNR / Detectability Judgment

**Information strength: WEAK TO ABSENT.**
- The strongest entry-bar signal is VDO level: d ≈ 0.29, explaining ~2.1% of winner/loser variance. This is an upper bound because VDO is a price-volume hybrid — part of its marginal association is already in P_t.
- All other volume/TBR features: d < 0.08. Effectively zero.

**Stability: UNSTABLE.**
- The TBR→return relationship oscillates in sign with 3–6 month half-cycles [Obs07, Prop04]. Any relationship that exists is non-stationary.
- The VDO marginal signal has not been tested for temporal stability at trade-level, but its narrow dynamic range (IQR 0.001–0.010) makes any threshold highly sensitive to distributional shifts.

**Detectability: UNDERPOWERED.**
- MDE at n=201 (α=0.05, 80% power) requires d ≥ 0.41. The strongest signal is d ≈ 0.29. A design targeting VDO tightening (Class A) would achieve ~45% power — essentially a coin flip between detecting a real effect and missing it.
- Blocking trades reduces n further. WFO with 4 folds yields ~50 trades per fold — extreme small-sample territory.
- The asymmetric payoff structure (mean winner 3.2× mean loser) means any false positive suppression is expensive.

---

## 4. VDO Judgment

**VDO has captured the lion's share of extractable volume information at entry.**

Specific evidence:

1. **VDO > 0 already works.** The VDO filter is one of the 4 proven components of the pipeline (DOF-corrected p=0.031 Sharpe, p=0.004 MDD — from MEMORY.md). It passes all 16 timescales. This is not a weak filter; it is a statistically validated component.

2. **The residual VDO signal is small and truncated.** After conditioning on VDO > 0, the remaining VDO distribution has IQR 0.001–0.010 [Obs24]. The marginal separation between winners and losers within this range is p=0.086 (not significant) with d ≈ 0.29 [Obs18]. The headroom for a tighter VDO threshold is at most ~2% of variance explained — and even that is an optimistic upper bound.

3. **Non-VDO volume features add zero.** Raw volume (p=0.456), TBR at any lookback (p=0.398–0.806), all fail at entry [Obs17, Prop01]. VDO is not missing information that other volume features capture; there is no complementary volume signal waiting to be combined.

4. **The information ceiling is low.** I(ΔU_t ; V_t | P_t) appears to be ≤ 2% of variance. This is not a case where VDO captures 60% and 40% remains — it is a case where VDO captures most of a quantity that was already small, leaving a negligible residual.

5. **Context from prior research.** The broader research program (X12–X22) explored churn filters, conviction sizing, cross-asset expansion, and cost sensitivity — none found significant incremental entry-level volume information. X21 (Conviction Sizing) specifically found that entry features have zero IC for trade return prediction (CV IC = -0.039 < 0.05, MEMORY.md). This is convergent evidence from an independent study.

**Verdict: VDO > 0 is at or near the extractable optimum for volume/microstructure information at entry in this system. The ceiling is low, and VDO is already touching it.**

---

## 5. Conclusion: **(B) VDO has captured the bulk of volume information. Headroom is too small to justify design.**

### Justification

The evidence converges from three independent directions:

**(i) Comprehensive nulls on non-VDO volume features.** Five features × multiple lookbacks at the entry bar all fail (p > 0.39, |rank-biserial| < 0.08) [Prop01 ← Obs15, Obs16, Obs17]. This rules out the hypothesis that volume/TBR contains information that VDO misses.

**(ii) The residual VDO signal is marginal, likely artifactual, and underpowered.** VDO level at entry: p=0.086, d≈0.29 [Obs18, Obs25]. Below MDE of 0.41. VDO-return correlation not significant (p=0.190). Truncation at VDO=0 compresses dynamic range [Obs24, Prop02]. Even the best-case admissible design (Class A, 1 DOF) would have only ~45% power to detect this effect — likely producing an inconclusive validation.

**(iii) Convergent evidence from prior independent research.** X21 (Conviction Sizing) found zero predictive IC for entry features including VDO, ATR percentile, EMA spread, and D1 regime strength (CV IC = -0.039). This is an independent confirmation that entry-time information is exhausted by the binary gates already in the pipeline.

A design phase targeting Class A (VDO threshold tightening) is not unreasonable structurally (1 DOF, low overfit risk). But the expected outcome is overwhelmingly likely to be inconclusive or null. The expected ΔSharpe from a VDO threshold tightening is well below the MDE of 0.37. The asymmetric payoff structure (blocking 1 winner costs 3.2 losers) further reduces the probability of a positive outcome.

The honest conclusion is: **VDO > 0 is already near the extractable optimum. The improvement headroom from volume/microstructure entry filters is negligibly small.**

---

## 6. Gate

**STOP_VDO_NEAR_OPTIMAL**

Do not design a new filter.

Final direction for alpha search: **cost reduction** (X22 showed E5+EMA1D21 Sharpe increases from 1.19 to 1.67 at 15 bps; realistic Binance costs are 20-30 bps RT) **and execution quality** (the largest marginal Sharpe gain comes from reducing transaction costs, not from adding entry filters). Secondary directions: exit mechanism refinement (but X16–X19 mapped the ceiling there too) or longer-horizon regime research beyond D1 EMA(21).

---

## Phase 4 Checklist

1. **Files created**
   - `04_go_no_go.md` (this file)

2. **Key Obs / Prop IDs created**
   - No new Obs or Prop IDs. This phase synthesizes existing evidence.

3. **Blockers / uncertainties**
   - The VDO residual effect (p=0.086) cannot be definitively ruled out. It could be a real but small effect (d ≈ 0.29). However, it is below detection threshold and the structural argument (truncation artifact) is strong.
   - The STOP decision is based on expected value: the probability-weighted payoff of pursuing design is negative given power constraints and asymmetric payoff structure.

4. **Gate status**: **STOP_VDO_NEAR_OPTIMAL**
