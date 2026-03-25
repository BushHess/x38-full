# Phase 6: Final Research Memo

**Date**: 2026-03-10
**Study**: entry_filter_lab
**Question**: Can a volume/microstructure entry filter improve upon or replace VDO > 0 in the BTC H4 trend-following pipeline?

---

## 1. Executive Conclusion

**Keep VDO: volume information ceiling too low.**

The existing VDO > 0 gate is at or near the extractable optimum for volume/microstructure information at entry. The residual information in volume and taker buy ratio, conditional on VDO > 0 already being applied, is indistinguishable from zero across every formulation tested. The single marginal signal (VDO level above zero, p=0.086) is below the minimum detectable effect size and is more consistent with a truncation artifact than with exploitable predictive content. No replacement or tightening is warranted.

---

## 2. Research Path

**Phase 0 — Data Audit.** Verified schema, timestamps, gaps, duplicates, and value ranges for 18,662 H4 bars and 3,110 D1 bars. Data quality is high: zero anomalous gaps, zero duplicates, 17 zero-volume bars (0.09%). TBR range [0.085, 0.924], mean 0.495.

**Phase 1 — Raw EDA.** Examined TBR and volume across the full H4 bar population (n=18,662). TBR is contemporaneously linked to bar direction (p=4.1e-228) but has near-zero predictive correlation with forward returns (|rho| <= 0.029 at all horizons). The TBR-return relationship is non-stationary, oscillating in sign with 3-6 month half-cycles. Volume is symmetrically elevated during strong moves in both directions. Regime conditioning does not improve predictive content. Produced 10 observations, 2 non-findings, 2 flagged-as-spurious.

**Phase 2 — Trade-Level Conditional EDA.** Reproduced 201 trades (78 winners, 123 losers) under the E0+D1 EMA(21) strategy at 50 bps RT. Computed volume, TBR, volatility, and VDO profiles around entry for winners vs losers. All five entry-bar features failed separation tests (p > 0.39, |rank-biserial| < 0.08). VDO at entry was the sole marginal signal (p=0.086, d~0.29). The 5 worst losers showed no common volume or TBR pattern at entry. Produced 12 observations.

**Phase 3 — Formalization.** Defined the decision problem (binary entry filter maximizing cumulative trade utility), information sets (P_t vs V_t), and assessed conditional mutual information I(delta_U; V_t | P_t). Formalized 6 propositions from the evidence. Identified 3 admissible function classes (A: VDO threshold, B: volume percentile, C: regime-conditional VDO) and rejected 6 inadmissible classes. Power analysis showed MDE=0.406 vs strongest signal d=0.29 — any design would be underpowered.

**Phase 4 — Go/No-Go.** Synthesized all evidence into 10 key findings. Assessed SNR (weak to absent), stability (unstable), and detectability (underpowered). Concluded VDO > 0 has captured the bulk of extractable volume information. Gate: **STOP_VDO_NEAR_OPTIMAL**. Phases 5 (design) and 6 (validation) were skipped per protocol.

---

## 3. Strongest Evidence

**E1.** All five volume/TBR features at entry fail to separate winners from losers (all p > 0.39, all |rank-biserial| < 0.08) with adequate power for medium effects. [Obs17, Tbl05, Prop01]

**E2.** Volume profiles around entry are indistinguishable between winners and losers — median lines overlap from bar -20 through bar +10, IQR bands overlap completely. [Obs15, Fig09]

**E3.** TBR profiles around entry are indistinguishable between winners and losers. The pre-entry TBR rise to ~0.52 is mechanical (driven by EMA cross-up requiring recent price rises) and identical for both groups. [Obs16, Obs21, Fig10, Prop03]

**E4.** Raw TBR-to-forward-return correlation is |rho| <= 0.029 at all horizons, and the sign is non-stationary — oscillating between negative and positive with 3-6 month half-cycles. A filter cannot exploit a relationship that flips sign. [Obs03, Obs07, Fig08, Tbl02, Prop04]

**E5.** Volume is symmetrically elevated during strong up and down moves (p=0.149, rank-biserial=0.036). Volume measures participation magnitude, not directional conviction. For a long-only filter, this symmetry is fatal. [Obs05, Obs11, Fig03, Tbl01, Prop05]

**E6.** VDO at entry is the sole marginal signal (p=0.086, rank-biserial=0.144, d~0.29), but: (a) below MDE of 0.406, (b) VDO-return correlation not significant (r=0.093, p=0.190), (c) VDO values cluster just above zero (IQR 0.001-0.010) due to the existing VDO > 0 gate truncating the distribution. [Obs18, Obs24, Obs25, Fig12, Fig13, Tbl06, Prop02]

**E7.** The 5 worst losers (returns -10% to -26%) show no common volume, TBR, or VDO pattern at entry. They span different years, regimes, and volume contexts, and visually resemble typical entries at the point of entry. [Obs23, Fig14a-e]

**E8.** Independent convergent evidence from X21 (Conviction Sizing): entry features including VDO, ATR percentile, EMA spread, and D1 regime strength have zero cross-validated IC for trade return prediction (CV IC = -0.039 < 0.05). The binary gates already in the pipeline exhaust entry-time information.

---

## 4. What Failed

| Hypothesis / Class | Verdict | Reason |
|---------------------|---------|--------|
| TBR as entry predictor (any lookback: 1, 5, 10 bars) | REJECTED | Comprehensive nulls (p=0.398-0.806 at entry), non-stationary sign, |rho| <= 0.029 unconditionally [Obs03, Obs07, Obs17, Prop04] |
| Raw volume level as entry filter | REJECTED | Symmetric across up/down moves, no W/L separation (p=0.456) [Obs11, Obs15, Obs17, Prop05] |
| Volume directional asymmetry | REJECTED | Volume amplifies magnitude, not direction. p=0.149 for up_strong vs down_strong [Obs05, Obs11, Prop05] |
| Regime-conditioned TBR | REJECTED | Both bull and bear regimes show same weak negative correlation. No hidden predictive content revealed [Obs08, Tbl03, Prop04] |
| ATR/price volatility gate at entry | REJECTED | Gap is persistent across 30-bar window (regime property), not localized to entry. p=0.715 at entry bar [Obs19, Obs26, Prop06] |
| VDO threshold tightening (Class A) | NOT TESTED — underpowered | d=0.29 vs MDE=0.406. Design would achieve ~45% power. Expected outcome: inconclusive [Prop02, Phase 3 power analysis] |
| Volume temporal pattern / ramp-up shape | REJECTED | Volume profiles identical for W and L across full -20 to +10 window [Obs15, Fig09] |
| Multi-feature logistic model | REJECTED a priori | >= 3 DOF on features that individually show p > 0.39. Confirmed by X15 (dynamic multi-feature filter catastrophically over-suppresses) |

---

## 5. Mathematical Conclusion

**What information do volume and taker_buy carry?**

1. **Contemporaneous direction** (TBR): TBR strongly separates up from down bars within the same bar (rho = -0.807, p = 4.1e-228) [Obs01, Fig04]. This is a same-bar identity, not a predictive signal.

2. **Participation magnitude** (volume): Volume measures the intensity of activity during a bar, equally for up and down moves. It is a magnitude proxy, not a directional signal [Obs05, Obs11, Prop05].

3. **Forward predictive content** (TBR -> future returns): Near zero (|rho| <= 0.029) and non-stationary in sign [Obs03, Obs07, Prop04]. The information, if it exists at all, is economically negligible and temporally unreliable.

4. **Conditional on entry** (V_t | E_t): All volume/TBR features at the entry bar fail to separate winners from losers (p > 0.39) [Obs17, Prop01]. Conditioning on the entry signal does not reveal hidden structure.

**Is this information usable?**

No, not for entry filtering in this system.

- The conditional mutual information I(delta_U; V_t | P_t) is estimated at <= 2% of win/lose variance (upper bound from VDO residual r^2 = 0.021) [Phase 3, Section 2].
- This upper bound is itself inflated because VDO is a price-volume hybrid — part of its marginal association is already in P_t.
- The existing VDO > 0 gate extracts the one usable piece: volume-confirmed direction as a binary entry qualifier (DOF-corrected p=0.031 Sharpe, p=0.004 MDD from prior validated research).
- The residual after VDO > 0 is a narrow distribution (IQR 0.001-0.010) with no significant predictive gradient [Obs24, Prop02].

**Usable at what class of functions?**

- Class A (VDO threshold tightening): Structurally admissible (1 DOF) but the target signal (d=0.29) is below MDE (0.406). Expected validation outcome: inconclusive.
- Class B (volume percentile): No signal to target (p=0.456).
- Class C (regime-conditional VDO): 2 DOF with no evidence for regime dependency. Dominated by Class A.
- All other classes: Rejected on evidence grounds.

**Bottom line**: Volume/taker_buy information for BTC H4 entry filtering is almost entirely exhausted by two things: (1) the price-derived trend signal itself (EMA crossover), and (2) the binary VDO > 0 confirmation. There is no residual volume/microstructure information surface deep enough to support a new filter at n=201 trades.

---

## 6. Practical Recommendation

VDO is not being replaced. The next marginal alpha is not in entry filtering.

**Where to look next, ranked by expected return on research effort:**

1. **Cost reduction / execution quality.** X22 showed that E5+EMA1D21 Sharpe increases from 1.19 (50 bps) to 1.67 (15 bps). Realistic Binance costs are 20-30 bps RT. The largest accessible Sharpe improvement (~0.3-0.5) comes from minimizing transaction costs via execution optimization (limit orders, timing, fee tier), not from adding filters. This is engineering, not research.

2. **Longer-horizon regime research.** The D1 EMA(21) regime filter is proven but was chosen from a narrow range (15-40d). Investigating regime signals at weekly/monthly timeframes, or structural regime indicators (e.g., on-chain metrics, funding rates), could find complementary information orthogonal to the current H4 trend-following alpha.

3. **Different instrument structure.** BTC perpetual futures offer short-side exposure and funding rate alpha that spot cannot access. The long-only constraint caps the opportunity set at ~50% of market states. A different instrument could expand the alpha surface — but this is a new research program, not an incremental filter.

4. **Exit mechanism refinement.** X16-X19 mapped the ceiling for churn filters and alternative actuators. The ~10% oracle ceiling on churn repair is a hard cap. However, the ATR trail multiplier (trail=3.0) represents a return/risk tradeoff (trail sweep shows monotonic relationship). A different exit paradigm (e.g., time-based exits, volatility regime-adaptive exits) could be explored, though X16's adaptive trail already failed.

5. **More data.** The current sample is n=201 trades over 8.5 years. Extending the data window (if more BTC history becomes available) or reducing the timeframe to H1 (more trades but noisier) could improve detection power. However, BTC's structural regime changes (2017 retail mania vs 2024 ETF era) mean more data does not guarantee more signal.

---

## 7. What Would Make This Conclusion Wrong?

**Assumption 1: The marginal VDO signal (p=0.086) is non-significant.**
If d=0.29 is a real effect, a larger sample (n >= 400 trades, achievable with ~17 years of data or lower timeframe) could detect it. A VDO threshold of ~0.003-0.005 might then show a small but real ΔSharpe of ~0.05-0.10. This would not change the practical conclusion (the improvement would be tiny), but it would technically mean the information ceiling is slightly above zero rather than at zero.

**Assumption 2: Static TBR-return relationship does not exist.**
If the TBR-return sign oscillation (Obs07) has a slowly drifting mean that becomes persistently negative or positive in the future, a regime-adaptive TBR filter could have value. The 8.5-year sample shows no drift trend, but BTC market structure continues to evolve (ETF inflows, institutional participation). A structural shift that stabilizes the TBR-return relationship is conceivable but not currently evidenced.

**Assumption 3: Volume information is fully captured by bar-level aggregates.**
This study analyzed bar-level aggregates (OHLCV per 4h bar). Sub-bar (tick-level or order-book) microstructure data was not examined because it is not available in the dataset. If bid-ask spread, order flow imbalance, or trade-by-trade clustering at the moment of entry contains predictive content, this study cannot detect it. This is a data limitation, not an analytical failure.

**Assumption 4: The 50 bps RT cost model is appropriate.**
All trade-level analysis used 50 bps RT. At lower costs (15-20 bps, realistic for Binance), some marginal trades that appear as losers at 50 bps become winners. The winner/loser partition shifts, and the entry-bar feature distributions could change. This was not re-tested at low cost. However, the fundamental observation — that volume/TBR features show zero separation — is unlikely to depend on the cost model since it is measured in rank-order (Mann-Whitney), not in dollar P&L.

**What is underpowered:**
- The VDO residual test (d=0.29 vs MDE=0.406) is explicitly underpowered. We cannot definitively rule out a small true effect.
- Sub-group analyses (e.g., VDO behavior in bull-only or bear-only regimes at trade level) were not performed due to small n per sub-group.

**What could reverse the conclusion:**
- A structural break in BTC microstructure that creates persistent TBR→return predictability. This would require a regime change in market structure (e.g., a dominant informed trader class consistently visible in taker flow).
- Access to order-book or tick data revealing sub-bar predictive content invisible at the 4h aggregate level.
- A sample 3-5x larger that elevates the VDO residual from suggestive to significant — but even then, the practical ΔSharpe would likely be < 0.10.

---

## 8. Final Status

**FINALIZED_KEEP_VDO**

---

## Provenance Summary

This conclusion rests on:
- 26 observations (Obs01-Obs26), of which 2 are non-findings and 2 are flagged as possibly spurious
- 6 propositions (Prop01-Prop06), 4 at HIGH confidence, 1 at MEDIUM, 1 at MEDIUM-HIGH
- 20 figures (Fig01-Fig14e) and 9 tables (Tbl01-Tbl06 + 3 audit/reference tables)
- 3 reproducible code scripts
- Convergent evidence from independent prior study X21 (Conviction Sizing)
- No candidates were designed. No validation was performed. This is a STOP conclusion, not a failure to validate.

---

## Phase 6 Checklist

1. **Files created**
   - `07_final_report.md` (this file)
   - `manifest.json` (updated)

2. **Key Obs / Prop IDs created**
   - None. This phase synthesizes existing evidence.

3. **Blockers / uncertainties**
   - VDO residual (p=0.086) remains ambiguous — small true effect cannot be definitively excluded
   - Sub-bar microstructure data not available for analysis
   - Trade-level analysis at lower cost model (15-20 bps) not performed

4. **Gate status**: **FINALIZED**
