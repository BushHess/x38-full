# VDO Decomposition — Gap Analysis vs Closed Studies

**Date**: 2026-03-14
**Context**: Analyst's VDO decomposition analysis proposed 5 research branches (B3, F3, C1/C2, B2).
This document maps each proposed branch against existing closed studies to identify genuinely novel gaps.

---

## Branch-by-Branch Overlap Map

### B3: Conditional Incremental Utility of VDO After Trend State

**Proposal**: Build candidate-signal dataset, measure incremental utility of VDO sign, VDO continuous,
volume surprise, normalized net flow — all in same WFO protocol, conditioned on trend state.

**Overlap with closed studies**:

| Closed Study | What It Already Tested | Coverage |
|---|---|---|
| **X25** (Phase 2) | TBR (1/5/10-bar), volume/median, VDO residual — all **conditioned on entry signal already fired** (trend_up & regime_ok & VDO>0). All p>0.39 except VDO (p=0.086, underpowered). | ~90% |
| **X25** (Phase 3) | Formalized I(ΔU; V_t \| P_t) ≤ 2% of win/lose variance. 3 admissible function classes (A: threshold, B: percentile, C: regime-conditional) all rejected or underpowered. | ~95% |
| **X21** | VDO continuous at entry + ema_spread + atr_pctl + d1_regime_str → CV IC = -0.039. Entry features have ZERO cross-validated predictive power. | ~80% |

**What is genuinely novel?**

1. **Competitive comparison framework**: X25 tested features individually (univariate separation tests).
   The user wants head-to-head comparison of VDO sign vs VDO continuous vs alternatives in the SAME
   model/framework. However: since ALL individual features are null (p>0.39), a competitive comparison
   is structurally unable to find a winner. Multiple null signals combined remain null.

2. **"Volume surprise" and "normalized net flow"**: These are derived features within the OHLCV+taker
   family. "Volume surprise" ≈ volume/rolling_median (tested in X25, p=0.456). "Normalized net flow"
   ≈ (taker_buy - taker_sell) / f(volume) — this is VDO's input (vdr), tested implicitly.

**Assessment**: ~95% overlap with X25+X21. The framing "incremental utility after trend state" is
X25's exact conditioning (entry signal fired = trend_up & regime_ok). No genuinely untested
sub-hypothesis survives.

**Recommendation**: **DO NOT RUN.** Would reproduce X25 with different methodology but same answer.

---

### C1: Architecture Ceiling (Binary Entry Gate Oracle)

**Proposal**: The analyst's oracle (Sharpe 3.05 from perfect binary entry gate, same exits)
establishes the ceiling of the current architecture.

**Overlap**: No study has done this exact computation. This IS genuinely new.

**Assessment**: **ALREADY DONE** by the analyst. The number (3.05) is a useful diagnostic reference.
No further research needed — the oracle number is a single computation, not a research program.

**Key interpretation caveat**: 3.05 includes information from ALL sources (macro, sentiment, luck,
not just volume). The volume-accessible portion is bounded at ≤2% variance (X25). So the gap
(3.05 - 1.49 = 1.56 Sharpe) is overwhelmingly from non-volume information.

---

### C2: Volume-Only Information Ceiling

**Proposal**: Separate the ceiling of volume information from the architecture ceiling.

**Overlap**: X25 already answered this. Conditional mutual information I(ΔU; V_t | P_t) ≤ 2%
of win/lose variance. VDO > 0 extracts the one usable piece: volume-confirmed direction as binary
qualifier.

**Assessment**: **FULLY ANSWERED by X25.** The ceiling is ~0 residual after VDO > 0.

---

### F3: Role/Use Changes

**Proposal** (in order): context/confidence → hold management → exit hysteresis → hard veto.

#### F3.1: Context/Confidence

"VDO continuous value at entry → confidence signal → variable sizing or conditional behavior."

| Closed Study | Coverage |
|---|---|
| **X21** | Tested EXACTLY this: VDO continuous + 3 other features → trade return prediction → sizing. CV IC = -0.039 (NEGATIVE). Fixed sizing f=0.30 optimal. |
| **X25** (Prop02) | VDO residual above threshold: r=0.093, p=0.190 (not significant). IQR 0.001-0.010 (truncated). |

**Assessment**: **100% COVERED by X21.** VDO continuous at entry has zero predictive power for trade quality.

#### F3.2: Hold Management

"VDO state during trade → mid-trade exit/hold decision."

| Closed Study | What It Tested | Relevance |
|---|---|---|
| **X31-A** | D1 EMA(21) flip during trade → early exit. Selectivity 0.21 << 1.5. Cuts winners 5× per loser saved. | Structural constraint applies to ANY mid-trade signal |
| **X16 Design E** | 7-feature model (including vdo_at_exit) at trail stop → WATCH grace period. Bootstrap FAIL (path-specific). | VDO already included as feature; mechanism failed |
| **X17** | Same 7 features, α-percentile, nested WFO. G dilemma: too short = no-op, too long = path-specific. | Fundamental: viable G window may not exist |

**What is specifically untested**: "VDO sign flip during trade" as a standalone exit trigger (not part
of a multivariate model or WATCH mechanism). X31-A tested D1 regime flip (not VDO), X16 tested VDO
as one feature among seven.

**However**: The structural constraint from X31-A applies identically to VDO flip:
- Fat-tail alpha concentration: top 5% trades = 129.5% of profits
- ANY mid-trade exit faces selectivity ratio problem (loser benefit / winner cost)
- VDO is a NOISIER signal than D1 EMA(21) (p=0.031 vs p=1.5e-5)
- If D1 flip has selectivity 0.21, VDO flip would likely be WORSE

**Assessment**: ~80% covered. The specific "VDO flip during trade" test is novel but the structural
constraint predicts failure. Expected selectivity ratio < 0.21 (D1's value). Running this would
confirm the constraint at high cost with near-certain negative result.

**Recommendation**: If run at all, do as a CHEAP diagnostic (Phase 0 only, < 1 hour), not a full
8-phase study. Count VDO flips during trades, compute selectivity ratio. If selectivity < 1.5 → STOP.

#### F3.3: Exit Hysteresis

"VDO crosses zero → delay exit / add hysteresis."

| Closed Study | Coverage |
|---|---|
| **X16 Design F** | Adaptive trail (widen trail when conditions positive). d_sharpe = -0.006. Zero lift. Trail width is NOT the bottleneck. |
| **X16 Design E** | WATCH with 7-feature model (VDO included). +0.088 but bootstrap FAIL (path-specific). |
| **X17** | Conservative WATCH (G=1-4). Mechanism is no-op at short grace windows. |

**Assessment**: **100% COVERED by X16+X17.** The entire exit-delay/hysteresis family has been explored.
VDO was already a feature in the exit model. The bottleneck is NOT the trigger signal — it's the
fundamental G dilemma (too short = no effect, too long = path-specific).

#### F3.4: Hard Veto

"VDO as binary gate" — this IS the current architecture (VDO > 0). X25 confirmed near-optimal.

**Assessment**: **STATUS QUO.** Nothing to test.

#### F3 Summary

| Sub-branch | Coverage | Novel? | Expected Value |
|---|---|---|---|
| F3.1 context/confidence | 100% (X21) | No | Zero |
| F3.2 hold management | 80% (X31-A constraint) | VDO flip specifically | Very low |
| F3.3 exit hysteresis | 100% (X16, X17) | No | Zero |
| F3.4 hard veto | 100% (status quo) | No | Zero |

---

### B2: Input vs Operator

**Proposal**: "Operator + selection logic quan trọng hơn input normalization."
Is the VDO formula (EMA(12)-EMA(28) of vdr) optimal, or could a different operator extract more?

**Overlap with closed studies**:

| Study | What It Tested | Coverage |
|---|---|---|
| **X34** (Q-VDO-RH) | Alternative VDO formula: quote-volume normalized, regime-heavy. Full Q-VDO-RH Sharpe 1.151 vs E0 1.265 = -0.115. **REJECT.** | ~50% |
| **X34 c_ablation** | Decomposed Q-VDO-RH: normalized input was the damage source. Stripping normalization (A3, A5) recovered to ≈E0 (Δ -0.008 to -0.010). | Key finding |
| **X25** | Alternative inputs (TBR, raw volume, volume percentile) — all null at entry. | Input alternatives |
| **X25** bound | I(ΔU; V_t \| P_t) ≤ 2% of variance. ANY operator on same information bounded. | Ceiling |

**What is genuinely novel?**

1. **EMA period alternatives**: VDO uses fast=12, slow=28 (structural, never optimized). No study has
   swept these periods. However: VDO is a MACD of ratio. Period sensitivity for MACD-type oscillators
   is typically low around reasonable values (12/26 vs 12/28 etc.).

2. **Non-MACD operators**: No study tested e.g. ROC(vdr), Bollinger-band(vdr), or other operator
   families on the same vdr input. However: X25 bounds the INFORMATION at ≤2%, so a better operator
   can at most extract marginally more from the same ≤2% signal.

3. **Absolute flow vs ratio**: VDO uses ratio (vdr = (buy-sell)/volume). Nobody tested
   momentum(taker_buy) or momentum(taker_buy - taker_sell) without volume normalization as an entry
   gate. X34 tested QUOTE-normalized flow (worse), but not absolute flow.

**Assessment**: ~50% covered by X34+X25. The genuinely untested space is:
- (a) Period sweep for current MACD-of-ratio operator
- (b) Alternative operator families (ROC, z-score, etc.) on same vdr input
- (c) Absolute flow momentum (un-normalized)

All three are bounded by X25's ≤2% information ceiling. Expected maximum improvement even with
perfect operator: ΔSharpe < 0.10 (from the 2% residual variance).

**Recommendation**: Only worth pursuing as CHEAP diagnostic.
- Phase 0: period sweep (fast × slow grid) — single script, < 30 min
- If any period beats 0.0 threshold with Δ > 0.05 Sharpe → continue
- Otherwise STOP (information ceiling binds)

---

## Summary Matrix

| Branch | Overlap % | Genuinely Novel | Structural Bound | Recommendation |
|---|---|---|---|---|
| **B3** | 95% | Competitive framework (but all features null) | ≤2% info ceiling (X25) | **SKIP** |
| **C1** | 0% (new) | Oracle number | Already computed | **DONE** |
| **C2** | 100% | None | ≤2% (X25) | **ANSWERED** |
| **F3.1** | 100% | None | CV IC = -0.039 (X21) | **SKIP** |
| **F3.2** | 80% | VDO flip mid-trade | Selectivity constraint (X31-A) | **CHEAP DIAGNOSTIC ONLY** |
| **F3.3** | 100% | None | G dilemma (X16/X17) | **SKIP** |
| **F3.4** | 100% | None | Status quo | **SKIP** |
| **B2** | 50% | Period sweep, alt operators, absolute flow | ≤2% info ceiling (X25) | **CHEAP DIAGNOSTIC ONLY** |

---

## Actionable Next Steps (if any)

Only TWO items survive the gap analysis as genuinely untested AND theoretically non-zero:

### 1. F3.2 Diagnostic: VDO Flip During Trade — Selectivity Check

**Hypothesis**: VDO sign flip (positive → negative) during an open trade predicts trade failure
with selectivity ratio > 1.5.

**Protocol**: Phase 0 only (no WFO, no bootstrap, no full study).
- Count trades where VDO flips sign during position
- For those trades: compute loser benefit (saved by early exit) and winner cost (cut by early exit)
- Selectivity ratio = mean(loser_benefit) / mean(winner_cost)
- **STOP if ratio < 1.5** (same threshold as X31-A)
- **GO if ratio > 1.5** → design proper study

**Expected outcome**: Ratio < 1.5 (same structural constraint as X31-A).
**Expected cost**: < 1 hour, single script, ~50 lines.

### 2. B2 Diagnostic: VDO Period Sweep

**Hypothesis**: VDO MACD periods (fast=12, slow=28) are not locally optimal; a different
period pair extracts more from the vdr signal.

**Protocol**: Phase 0 only.
- Grid: fast ∈ {6, 8, 10, 12, 14, 16}, slow ∈ {20, 24, 28, 32, 36, 40} (36 combos)
- For each: run E5+EMA21D1 with modified VDO periods, harsh cost
- Report: Sharpe surface, identify if 12/28 is local optimum
- **STOP if plateau** (Sharpe varies < 0.05 across grid) → confirms structural, not optimizable
- **GO if clear gradient** (Sharpe varies > 0.10) → design proper study with WFO

**Expected outcome**: Plateau (MACD periods are typically insensitive in this range).
**Expected cost**: < 1 hour, single script, reuses existing backtest engine.

### 3. NOT recommended but theoretically open: Absolute Flow Momentum

Testing momentum(taker_buy - taker_sell) without ratio normalization as entry gate. This is
the one B2 sub-question X34 did not directly test (X34 tested quote-normalized, not un-normalized).
However: the information ceiling (≤2%) strongly suggests this would yield nothing material.
Park unless diagnostic #1 or #2 shows unexpected signal.

---

## What This Analysis Changes About the Strategic Conclusion

The analyst's decomposition work (B1/B4, A1-A3, F2) is **validated** — it produced genuinely new
understanding of HOW VDO works (selection, not timing; follow-through filter, not random gate).

But the proposed NEXT STEPS (B3, F3, C2) are **largely pre-empted** by 68 closed studies.
The research program that the analyst envisions (candidate-signal dataset → WFO → iterate) would
be a costly re-derivation of X25's null result under a different framing.

The only genuinely productive work is the two cheap diagnostics above, which can be completed
in 1-2 hours total. If both confirm expected nulls, the VDO research space is definitively closed —
not just at the formula/threshold level (X25, X34), but also at the role/use level.

---

## Provenance

This gap analysis was produced by cross-referencing:
- X14 (REPORT.md: Design D features, static mask mechanism)
- X16 (SPEC.md, REPORT.md: WATCH state machine, adaptive trail, bootstrap failure)
- X17 (SPEC.md, REPORT.md: α-percentile, G dilemma, nested WFO)
- X21 (REPORT.md: CV IC = -0.039, feature-level IC breakdown)
- X25 (07_final_report.md: STOP_VDO_NEAR_OPTIMAL, ≤2% information ceiling)
- X31-A (README.md: selectivity ratio 0.21, D1 regime exit)
- X34 (README.md, c_ablation/attribution_matrix.md: Q-VDO-RH REJECT, input vs operator)
- research_phase_conclusion.md (closure scope and future directions)
- methodology.md (error corrections, underpowered ≠ noise)
