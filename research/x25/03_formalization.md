# Phase 3: Formalization From Evidence

**Date**: 2026-03-10
**Inputs**: 01_raw_eda.md (Obs01–Obs14), 02_trade_eda.md (Obs15–Obs26), Figures 01–14, Tables 01–06
**Protocol**: Derive from evidence. No candidate formulas. No indicator names. No design.

---

## 1. Decision Problem

### Definitions

Let t index H4 bars.

- **E_t**: the event that the base system generates an entry signal at bar t.
  Operationally: EMA(30) crosses above EMA(120) on H4 close, AND D1 close > D1 EMA(21), AND VDO(12,28) > 0.
  In the sample, E_t fires 201 times (the filtered trade set).

- **a_t ∈ {0, 1}**: the filter decision.
  a_t = 1: allow entry (take the trade).
  a_t = 0: block entry (stay flat, no trade opened).

- **R_t**: the net return of trade t (including 50 bps RT cost), observed only if a_t = 1.

### Utility

Define the per-signal utility gain:

    ΔU_t = R_t · a_t

When a_t = 0 (blocked), the alternative is cash (return = 0), so ΔU_t = 0.
When a_t = 1 (allowed), ΔU_t = R_t.

The filter's objective is to maximize the expected cumulative utility:

    max_{a} E[ Σ_t ΔU_t | E_t ]

subject to the constraint that the filter only observes information available at bar t (causality).

### Why this definition fits BTC H4 long-only trend-following

1. **Cash alternative is zero-return**: The system is fully invested or fully flat. There is no short side, no carry, no yield on idle capital in this model. Blocking an entry means 0 return for that episode.

2. **Asymmetric payoff structure**: Winners average +12.19%, losers average -3.78% [Tbl04]. The strategy profits from fat right tails. A filter that blocks a fraction of losers ALSO risks blocking the rare large winners that dominate cumulative performance. ΔU_t = R_t captures this asymmetry directly.

3. **Trade-level, not bar-level**: The decision is binary (take trade / skip trade) at signal time, not a continuous allocation. This is a classification problem on the signal set {t : E_t = 1}, not a continuous portfolio optimization.

4. **Risk-adjustment**: The raw ΔU_t = R_t formulation implicitly assumes risk-neutral utility over individual trades. This is appropriate because risk management is handled by the trail stop and position sizing (f = 0.30), both of which are fixed and not subject to filter modification. The filter's job is purely to improve the quality of the entry set.

---

## 2. Information Sets

### Definitions

At bar t (when E_t fires):

- **P_t**: price-derived information available at bar t.
  Includes: close, open, high, low, all EMA values, ATR, returns, VDO (which is derived from volume BUT is already conditioned on by the entry gate VDO > 0), and D1 regime state.

- **V_t**: volume/microstructure information available at bar t.
  Includes: raw volume, taker_buy_base_vol, taker buy ratio (TBR = taker_buy_base_vol / volume), and any lookback transformations of these quantities.

Note: VDO is a mixed price-volume quantity (it measures volume-confirmed direction). Since the base system already conditions on VDO > 0, the *level* of VDO above zero is the residual information in V_t not yet consumed by P_t.

### The central question

Does V_t carry incremental information about ΔU_t beyond P_t?

Formally, we ask whether:

    I(ΔU_t ; V_t | P_t) > 0

where I(·;·|·) denotes conditional mutual information.

We cannot compute I(ΔU_t ; V_t | P_t) directly — it requires estimating a joint density in high dimensions with n = 201 samples. Instead, we assess it through the marginal evidence from Phases 1–2.

### Evidence assessment

**V_t components examined in Phase 1–2:**

| Component | Evidence | Obs refs |
|-----------|----------|----------|
| TBR (single bar at entry) | p = 0.570, r_rb = 0.048 | Obs16, Obs17 |
| TBR (5-bar lookback mean) | p = 0.398, r_rb = 0.071 | Obs17 |
| TBR (10-bar lookback mean) | p = 0.806, r_rb = 0.021 | Obs17 |
| Volume / median_vol(20) | p = 0.456, r_rb = 0.063 | Obs15, Obs17 |
| VDO level at entry | p = 0.086, r_rb = 0.144 | Obs18, Obs24 |

**Interpretation:**

- Four of five V_t components show zero separation between winners and losers (all p > 0.39, all |r_rb| < 0.08). These are informative nulls at adequate power for medium effects [Tbl05].

- VDO level is the sole marginal signal (p = 0.086, r_rb = 0.144). However, VDO is a price-volume hybrid that is ALREADY conditioned on (VDO > 0). The residual information in VDO level above zero is constrained to a narrow range (IQR ≈ 0.001 to 0.010) [Obs24]. This compression limits the information capacity of the residual.

- TBR at unconditional (bar-level) analysis also shows negligible predictive content: |ρ| ≤ 0.029 [Obs03], non-stationary sign [Obs07], no regime differentiation [Obs08].

**Assessment of I(ΔU_t ; V_t | P_t):**

The evidence is consistent with I(ΔU_t ; V_t | P_t) ≈ 0, or at most a quantity too small to reliably exploit at n = 201.

The strongest bound comes from the VDO residual: r² ≈ 0.021 (2.1% of win/lose variance explained). Even this is an upper bound on the *conditional* information, because part of VDO's marginal association may be captured by P_t (VDO is a function of volume AND price-derived direction).

---

## 3. Propositions

### Prop01 — Volume and TBR carry no incremental entry-bar information for ΔU_t

**Statement**: Conditional on the base entry signal E_t having fired, raw volume (normalized) and taker buy ratio at or before the entry bar do not separate winners from losers.

**Support**: [Obs15] (volume profile indistinguishable), [Obs16] (TBR profile indistinguishable), [Obs17] (all five features fail, p > 0.39).

**Confidence**: HIGH. Five independent tests, consistent nulls, adequate power for medium effects.

### Prop02 — The marginal VDO signal is likely a floor artifact, not genuine predictive content

**Statement**: The VDO effect (p = 0.086, r_rb = 0.144) arises from a constrained distribution truncated at VDO = 0 by the entry gate. The dynamic range above zero is narrow (IQR 0.001–0.010). The VDO-to-return correlation is not significant (r = 0.093, p = 0.190). The signal is more consistent with sampling variability in a truncated distribution than with exploitable information.

**Support**: [Obs18] (marginal p), [Obs24] (clustering near zero), [Obs25] (visually tempting but statistically weak).

**Confidence**: MEDIUM. The signal is not zero (p = 0.086 is suggestive), but the structural argument (truncation + compression) plus the VDO-return non-significance (p = 0.190) both argue against a real effect. Cannot definitively rule out a small true effect.

### Prop03 — The pre-entry TBR rise is mechanical and information-free for filter purposes

**Statement**: The synchronized TBR increase from ~0.49 to ~0.52 in bars [-5, 0] before entry is a consequence of the entry condition (EMA cross-up requires recent price rises, which mechanically coincide with TBR > 0.5). This rise occurs identically for winners and losers and carries zero differential information.

**Support**: [Obs21] (mechanical nature), [Obs01] (contemporaneous TBR-direction link, not predictive), [Obs16] (identical profile).

**Confidence**: HIGH. The mechanism is well-understood (entry condition → price up → TBR up), and the empirical evidence confirms zero separation.

### Prop04 — TBR predictive content, if any, is non-stationary and economically negligible

**Statement**: The weak negative TBR→forward return correlation (|ρ| ≤ 0.029) is non-stationary: rolling analysis shows the sign oscillates with half-cycles of 3–6 months. A filter based on a relationship that flips sign every few months cannot maintain a stable positive ΔU.

**Support**: [Obs03] (magnitude near zero), [Obs04] (negative sign), [Obs07] (non-stationary rolling), [Obs13] (possibly spurious).

**Confidence**: HIGH. The non-stationarity finding (Obs07) is particularly damaging — even if a small effect exists, its sign is unreliable.

### Prop05 — Volume level is symmetric across up/down moves and uninformative for long-only entry filtering

**Statement**: Volume is elevated during strong moves in BOTH directions equally (up_strong vs down_strong not significant, p = 0.149). Volume level at entry does not differentiate winners from losers (p = 0.456). High volume at entry could mean strong conviction in either direction. For a long-only filter, volume level alone is uninformative.

**Support**: [Obs05] (volume by bar type), [Obs11] (non-finding: no up/down asymmetry), [Obs15] (no separation at entry), [Obs17] (p = 0.456).

**Confidence**: HIGH. The symmetry finding (Obs11) is the key insight — volume amplifies magnitude, not direction.

### Prop06 — The winner/loser volatility gap is a regime property, not an exploitable entry feature

**Statement**: Winners enter at slightly higher ATR/price (0.0171 vs 0.0160, ~4–7% relative), but this difference persists across the entire [-20, +10] window and is not significant at the entry bar (p = 0.715). It reflects that trades initiated during higher-volatility regimes have larger potential returns (and the system's trail stop captures these). This is a regime-level property already partially captured by the ATR-based trail stop width, not an additional entry filter signal.

**Support**: [Obs19] (gap exists but persistent), [Obs26] (visually tempting, statistically weak), [Tbl05] (p = 0.715 at entry).

**Confidence**: MEDIUM-HIGH. The persistence of the gap across 30 bars is strong evidence against it being an entry-bar feature. The non-significance at entry confirms it is not exploitable by a bar-level filter.

---

## 4. Admissible Function Classes

Given the constraints:
- Causality (only information at bar t)
- Scale invariance or appropriate normalization
- Regime robustness
- ≤ 2 DOF
- Detectable at n ≈ 201
- Resistant to overfit in WFO / bootstrap / jackknife

### Class A: Scalar threshold on residual VDO level

**Form**: a_t = 1 if VDO_t > τ, where τ ≥ 0 is a single free parameter.

- **Why admissible**: 1 DOF. Causal (VDO_t computed from bars ≤ t). Scale-normalized by construction (VDO is a ratio). Already part of the system (this would tighten the existing VDO > 0 gate). Directly targets the only marginal signal (Obs18).
- **Compactness**: Maximum compression — a single scalar threshold.
- **Information loss**: Discards all non-VDO volume information. Given Prop01, this loss is negligible.
- **DOF cost**: 1.

### Class B: Percentile gate on recent volume relative to own history

**Form**: a_t = 1 if vol_t / rolling_median(vol, w) > τ, or equivalently percentile_rank(vol_t, w) > τ.

- **Why admissible**: 1–2 DOF (threshold, optionally window). Causal. Scale-invariant via normalization. Respects volume's high autocorrelation (Obs02).
- **Compactness**: Scalar threshold on normalized quantity.
- **Information loss**: Discards TBR, directional content. Given Prop01/Prop05, acceptable.
- **DOF cost**: 1–2.
- **Caveat**: Evidence strongly against this class (Obs15, Obs17 — volume relative shows no separation, p = 0.456). Admissible structurally but likely ineffective.

### Class C: Conditional threshold on VDO level interacted with one binary state

**Form**: a_t = 1 if VDO_t > τ_s, where s ∈ {0, 1} indexes a binary state (e.g., high/low volume regime).

- **Why admissible**: 2 DOF (two thresholds). Causal. Scale-invariant. Allows the filter strength to vary with a context variable.
- **Compactness**: Two scalars indexed by a binary regime.
- **Information loss**: Captures regime dependency, but evidence says regime conditioning doesn't help (Obs08). Marginal benefit over Class A is questionable.
- **DOF cost**: 2.
- **Caveat**: 2 DOF doubles the overfit risk at n = 201. The evidence does NOT support regime-dependent behavior of volume features (Obs08).

---

## 5. Rejected (Inadmissible) Function Classes

### Rejected 1: Multi-feature linear or logistic model

**Why rejected**: Requires ≥ 3 DOF (intercept + 2 feature weights minimum). With n = 201 trades, a 3+ parameter model on features that individually show p > 0.39 (Obs17) will overfit. No evidence supports any feature combination having power that individual features lack. The X14/X15 churn research confirms: adding features beyond a static mask causes catastrophic over-suppression [memory: X15 ABORT].

### Rejected 2: TBR-based threshold or anomaly detector at any lookback

**Why rejected**: Comprehensive null evidence. Single-bar TBR p = 0.570, 5-bar mean p = 0.398, 10-bar mean p = 0.806 (Obs17). Raw TBR→return |ρ| ≤ 0.029 (Obs03). Non-stationary sign (Obs07). Mechanical pre-entry rise (Obs21/Prop03). No evidence basis at any lookback or transformation tested.

### Rejected 3: Volume directional asymmetry filter

**Why rejected**: Volume is symmetric across up and down strong-move bars (p = 0.149, Obs11/Prop05). A filter based on "high volume = bullish confirmation" has no empirical support in this data. Volume amplifies magnitude, not direction.

### Rejected 4: Lookback-dependent TBR anomaly (z-score, percentile deviation from recent mean)

**Why rejected**: Requires stationarity of the TBR-return relationship. Obs07 shows this relationship is non-stationary with oscillating sign (Prop04). A z-score or percentile deviation would need the relationship to be stable in sign and magnitude. It is neither.

### Rejected 5: Volatility-level gate (ATR/price threshold at entry)

**Why rejected**: The winner/loser volatility gap is persistent across the entire 30-bar window, not localized to entry (Obs19/Prop06). Entry-bar ATR/price has p = 0.715 (Obs17). This is a regime property already captured by the ATR trail width. A threshold on ATR/price at entry adds 1 DOF to detect a non-existent entry-bar effect.

### Rejected 6: Temporal pattern on volume sequence (e.g., volume ramp-up pattern)

**Why rejected**: Volume profiles before entry are identical for winners and losers (Obs15). Both groups show the same normalized volume trajectory from bar -20 to bar +10. No temporal pattern in volume sequence differentiates trade quality. Extracting a "shape" feature from the volume sequence would require ≥ 2 DOF and targets a non-existent signal.

---

## 6. Detectability and Power

### Sample constraints

- n = 201 trades (78 winners, 123 losers) after D1 EMA(21) filter
- Any filter that blocks k trades reduces the evaluation sample to 201 − k
- WFO with 4 folds → ~50 trades per fold. Jackknife removes 1/6 → ~168 per fold.

### Minimum detectable effects (80% power, α = 0.05)

| Metric | MDE | Interpretation |
|--------|-----|----------------|
| Cohen's d (W vs L separation) | 0.406 | Medium-to-large effect needed |
| Win rate change | 38.8% → ~50% | +11.2 pp for 80% power |
| ΔSharpe (no blocking) | 0.365 | Substantial improvement needed |
| ΔSharpe (block 20%) | 0.409 | Even harder after sample reduction |

### Evidence vs detection threshold

The strongest observed signal is VDO at entry:
- Rank-biserial = 0.144, equivalent to Cohen's d ≈ 0.291
- **This is BELOW the MDE of 0.406**
- VDO explains ~2.1% of winner/loser variance (r² ≈ 0.021)

All other volume/TBR features have d < 0.08 — far below detection threshold.

### What a filter would need to achieve

If a filter blocks 30 trades (~15%) with perfect loser precision (100% of blocked trades are actual losers):
- Win rate increases from 38.8% to 45.6%
- This is still below the 50% threshold needed for 80% detection power

With realistic precision (70% of blocked trades are losers, 30% are winners):
- Win rate increases from 38.8% to 40.4% — a trivial improvement
- Mean return may actually decrease if the blocked winners include even one large outlier

### Asymmetric risk of filtering

Mean winner return (+12.19%) is 3.2× mean loser magnitude (-3.78%). Blocking 1 winner costs as much as correctly blocking 3.2 losers. With 78 winners and 123 losers, a filter with precision < 78% (losers among blocked) could DECREASE cumulative performance even while improving win rate. The base rate of losers is 61.2% — a random filter already has 61.2% "precision." A useful filter must substantially exceed the base rate.

### Order-of-magnitude conclusions

| Design type | Expected effect | Power | Verdict |
|-------------|----------------|-------|---------|
| VDO threshold tightening (Class A) | d ≈ 0.29 | ~45% | Underpowered, likely inconclusive |
| Volume percentile gate (Class B) | d < 0.08 | <10% | Almost certainly undetectable |
| Regime-conditional VDO (Class C) | d ≈ 0.29 / 2 DOF | ~30% | Worse power, more overfit risk |
| Any TBR-based design | d < 0.08 | <10% | No signal to detect |

---

## 7. Conclusion

### Allowed function classes

1. **Class A** (scalar VDO threshold tightening): Structurally admissible, targets the only marginal signal, 1 DOF. But the effect size (d ≈ 0.29) is below the MDE (0.406), making detection unreliable.

2. **Class B** (volume percentile gate): Structurally admissible, but evidence strongly suggests zero effect (p = 0.456 at entry). Included only for completeness.

3. **Class C** (regime-conditional VDO): Structurally admissible, but 2 DOF with no evidence for regime dependency. Dominated by Class A on parsimony grounds.

### Rejected function classes

1. Multi-feature linear/logistic model (DOF ≥ 3, no multi-feature evidence)
2. TBR threshold at any lookback (comprehensive nulls across 5 formulations)
3. Volume directional asymmetry (volume is directionally symmetric)
4. Lookback-dependent TBR anomaly (non-stationary relationship)
5. ATR/price volatility gate (regime property, not entry-bar feature)
6. Volume temporal pattern (identical profiles for winners and losers)

### Design gate recommendation

**GO_TO_SYNTHESIS_BUT_EXPECT_SMALL_HEADROOM**

Rationale:

- The evidence strongly indicates that volume/microstructure information provides near-zero incremental predictive power for trade quality beyond what the base system already extracts via VDO > 0.

- The only marginal signal (VDO level, p = 0.086) is below the detection threshold for reliable validation (d = 0.29 vs MDE = 0.41). Any design targeting this signal will likely produce inconclusive test results — neither clearly significant nor clearly null.

- The information ceiling I(ΔU_t ; V_t | P_t) appears to be ≤ 2% of win/lose variance, which translates to an expected ΔSharpe well below the MDE of 0.37.

- Proceeding to design is not unreasonable (Class A has 1 DOF and low overfit risk), but the analyst should expect small headroom and be prepared for a STOP_VDO_NEAR_OPTIMAL conclusion after validation.

- The honest-stopping outcome "VDO > 0 is already near the extractable optimum for volume information at entry" is a plausible and legitimate final conclusion.

---

## Phase 3 Checklist

1. **Files created**
   - `03_formalization.md` (this file)
   - `code/phase3_formalization_notes.py` (power analysis computations)

2. **Key Obs / Prop IDs created**
   - Prop01 (volume/TBR carry no incremental info) — HIGH confidence
   - Prop02 (VDO marginal signal is likely floor artifact) — MEDIUM confidence
   - Prop03 (pre-entry TBR rise is mechanical) — HIGH confidence
   - Prop04 (TBR predictive content non-stationary, negligible) — HIGH confidence
   - Prop05 (volume symmetric across up/down, uninformative for long-only) — HIGH confidence
   - Prop06 (volatility gap is regime property, not entry feature) — MEDIUM-HIGH confidence

3. **Blockers / uncertainties**
   - VDO residual effect cannot be definitively ruled out (p = 0.086). Could be real but small, or artifact.
   - Power constraints are severe: MDE = 0.406 vs strongest signal d = 0.291. Phase 4/5 validation may be inconclusive rather than decisive.
   - The 2.1% variance explained by VDO level may partly overlap with P_t (VDO is price-volume hybrid), making the true conditional information even smaller.

4. **Gate status**: **GO_TO_SYNTHESIS_BUT_EXPECT_SMALL_HEADROOM**
