# X-Series Concept Audit: X1-X6 vs E5+EMA1D21

**Date**: 2026-03-09
**Baseline**: X0 = E0+EMA1D21 (EMA crossover + VDO gate + ATR(14) trail@3.0 + EMA cross-down exit + D1 EMA(21) regime)
**Reference**: E5+EMA1D21 (robust ATR trail Q90-capped, period=20 + D1 EMA(21) regime)

---

## E5+EMA1D21 Mechanism Summary

E5 replaces E0's standard ATR(14) with a **robust ATR**: True Range capped at rolling Q90
over 100 bars, then smoothed with Wilder EMA(20). Net effect: ATR is ~4.5% smaller
(median), making the trail ~8.1% tighter on average. This produces:
- More frequent exits (225 trades vs 211 for E0)
- Shorter average holding periods
- Better MDD control through earlier loss-cutting
- Same entry logic as E0 (EMA cross + VDO + D1 regime)

**Key insight**: E5's advantage is primarily from the *tighter mechanical stop*, not from
robustness per se. At scale-matched trail (3.14-3.22×), MDD advantage collapses to 6/16
(chance level). Despite this, E5+EMA1D21 was PROMOTED on real-data metrics (wins 16/20
dimensions vs E0+EMA1D21), though downgraded to HOLD in fragility audit (compound
fragility too high).

---

## X1 — Re-entry Separation

### (a) Core concept
After a trailing-stop exit while trend is still up (EMA fast > slow), re-enter with
**relaxed conditions**: only VDO > 0 OR price > last_trail_stop. Skips the D1 regime
check for re-entries.

### (b) X0 weakness targeted
**Re-entry delay**: X0 requires all 3 entry conditions (EMA cross + VDO + D1 regime)
even when re-entering an ongoing trend after a temporary pullback. This causes missed
continuation moves — the D1 regime can lag behind H4 price recovery.

### (c) Does E5+EMA1D21 address this?
**NO**. E5+EMA1D21 uses identical entry logic to E0+EMA1D21. Same 3 conditions,
same re-entry delay. However, E5's tighter trail means it exits more often (more
trades), so the re-entry problem is actually **worse** in E5 — more frequent exits
with the same re-entry friction.

### (d) Recommendation: **REDUNDANT**

Despite E5 not addressing this weakness directly, X1 was empirically **REJECTED**:
all metrics worse at all cost levels (delta: -0.11 Sharpe, -4.28% CAGR, +4.37% MDD).
The D1 regime filter is **protective, not obstructive** — removing it for re-entries
introduces noise. The weakness X1 targets is not a real weakness; it's a feature.
Testing on E5+EMA1D21 base would not change this conclusion.

**Verdict: REDUNDANT** — the "weakness" is actually protective. No further testing.

---

## X2 — Adaptive Trailing Stop (Gain-tiered)

### (a) Core concept
Trail multiplier widens as unrealized gains grow:
- Gain < 5%: trail = 3.0×ATR (protect capital early)
- 5% ≤ gain < 15%: trail = 4.0×ATR (loosen as buffer grows)
- Gain ≥ 15%: trail = 5.0×ATR (wide trail in strong trends)

Adds 3 trail multipliers + 2 gain thresholds (7 params total vs 4 in X0).

### (b) X0 weakness targeted
**Fixed trail width**: 3×ATR is a single compromise — too tight for large winners
(whipsawed out of big moves during normal pullbacks), too loose for small gains
(gives back too much before exiting).

### (c) Does E5+EMA1D21 address this?
**PARTIALLY, via a different mechanism**. E5's robust ATR reduces spike sensitivity,
making the effective trail width more stable across volatility regimes. However:
- E5 still uses a **fixed** multiplier (3.0 × robust_ATR)
- E5 does NOT adapt to the trade's unrealized P&L
- E5's tighter trail actually makes the "too tight for big winners" problem **worse**

X2's concept is orthogonal: E5 stabilizes ATR estimation, X2 adapts trail width
to trade profitability. These are independent dimensions.

### (d) Recommendation: **CONFLICTING**

X2 widens the trail for large gains (up to 5.0×ATR). E5 tightens the trail via
smaller ATR estimates. Combining them creates an incoherent signal: E5 says "exit
earlier" while X2 says "hold longer on winners." The tighter E5 trail would partially
offset X2's wider multipliers, making the adaptive tiers less meaningful.

Moreover, X2 **failed OOS validation** even on X0 base (WFO 4/8, holdout delta near
zero). The 3 extra parameters (gain thresholds + tier multipliers) add overfitting
surface without robust improvement. Adding E5's mechanism on top would only add
more parameters to a concept that already fails out-of-sample.

**Verdict: CONFLICTING** — E5 tightens exits, X2 loosens them for winners. Incoherent
combination. Both failed OOS independently. Do not combine.

---

## X3 — Graduated Exposure (VDO-based sizing)

### (a) Core concept
VDO determines position size instead of acting as binary gate:
- VDO ≤ 0: enter at 40% exposure (core position)
- VDO > 0: scale to 70% exposure
- VDO > 0.02: scale to 100% exposure (rarely achieved)

Also changes exit: trail stop reduces to 40% core (not full exit); only EMA
cross-down fully exits.

### (b) X0 weakness targeted
**Binary sizing**: X0 is 0% or 100% regardless of signal strength. This ignores
the information content of VDO magnitude — a VDO of 0.001 and 0.05 get identical
treatment.

### (c) Does E5+EMA1D21 address this?
**NO**. E5+EMA1D21 uses the same binary VDO gate (VDO > 0 → enter 100%, else don't).
No graduated sizing in any E-series variant. The vol-target sizing (f=0.30) is
portfolio-level, not signal-strength-based.

### (d) Recommendation: **REDUNDANT**

Although E5 doesn't cover this concept, X3 was **catastrophically REJECTED**:
-0.361 Sharpe, -33.77% CAGR. The failure is not implementation-specific — it's
**structural**:

1. VDO > 0.02 occurs in only 1.1% of bars → effectively a permanent 40% strategy
2. Graduated sizing asymmetrically caps winners (enter small) while full-sizing
   losers (40% core always deployed)
3. Trend-following alpha is fat-tailed — you MUST be fully sized for the few
   big winners that drive 80% of returns

This structural argument applies regardless of base strategy. On E5+EMA1D21,
VDO distribution is identical (same VDO calculation), so VDO > 0.02 would
still be ~1.1% of bars. The graduated concept is mathematically incompatible
with trend-following's fat-tailed return profile.

**Verdict: REDUNDANT** — structural failure, not base-strategy-dependent. No further testing.

---

## X4B — Parallel Breakout Entry

### (a) Core concept
Two-stage entry system:
- **Path 1 (Breakout)**: close > highest_high(20) + volume > SMA(20) + D1 regime → 40% early entry
- **Path 2 (EMA)**: standard EMA cross + VDO → scale to 100%

Captures trend starts earlier via momentum breakout, preserves EMA defensiveness
for full sizing.

### (b) X0 weakness targeted
**Late trend entry**: EMA crossover is inherently lagging — by the time fast EMA
crosses slow EMA, the trend is already established and some initial move is missed.
Breakout detection can catch the inflection point earlier.

### (c) Does E5+EMA1D21 address this?
**NO**. E5+EMA1D21 uses the same EMA crossover entry. E5 only changes the exit
mechanism (trail computation). Entry timing is identical to E0+EMA1D21.

### (d) Recommendation: **REDUNDANT**

Despite E5 not addressing entry timing, X4B was **REJECTED** across all cost levels
(delta: -0.11 to -0.20 Sharpe, -11 to -20% CAGR). The failure mechanism:

1. Breakout entries are **lower quality** — many false breakouts in crypto
2. 40% partial entry on breakout → suboptimal when breakout IS real
3. Added complexity (breakout_lookback, vol_lookback, breakout_exposure) with
   no robust improvement

The problem isn't that EMA entries are late — it's that **being late is the filter**.
EMA's lag is a feature: it filters out short-lived spikes that breakout detection
catches. The "missed" initial move is the cost of entry quality. This structural
insight applies regardless of base strategy.

**Verdict: REDUNDANT** — EMA lag is a feature, not a bug. Breakout entries degrade
signal quality. No further testing.

---

## X5 — Partial Profit-Taking (Multi-level TP)

### (a) Core concept
Lock in gains at fixed profit thresholds via partial exits:
- +10% unrealized → sell 25% (TP1), activate breakeven floor
- +20% unrealized → sell another 25% (TP2), widen trail to 5×ATR
- State machine: FLAT → LONG_FULL(100%) → LONG_T1(75%) → LONG_T2(50%)

### (b) X0 weakness targeted
**No profit protection**: X0 rides trends fully, then gives back unrealized gains
when trail stop or trend reversal triggers. A trade can go +40% unrealized then
exit at +15% after a pullback. X5 locks partial gains at milestones.

### (c) Does E5+EMA1D21 address this?
**PARTIALLY, via a different mechanism**. E5's tighter trail (mechanically 8.1%
closer) means it exits earlier on pullbacks, reducing the magnitude of give-back.
However:
- E5 still exits **100% at once** — no partial profit locking
- E5's earlier exit also cuts winners shorter (both good and bad)
- E5 does NOT have a breakeven floor mechanism

E5 reduces give-back through tighter trailing, while X5 reduces give-back through
partial realization. Different approaches to the same underlying problem.

### (d) Recommendation: **CONFLICTING**

X5 was classified as a **TRADEOFF** on X0 base: -0.042 Sharpe, -13.26% CAGR, but
-2.91% MDD with 83.6% bootstrap MDD win rate. The failure is fundamental to
trend-following:

**Trend-following alpha is fat-tailed.** Selling 25-50% of position at +10%/+20%
systematically amputates the few trades that go +100% or +200%. These rare large
winners drive the majority of total returns. X5's TP1/TP2 converts a right-skewed
return distribution into a more normal one — which is exactly what you do NOT want
in a trend-following system.

On E5+EMA1D21 base, this problem is **amplified**: E5's tighter trail already exits
earlier, meaning fewer trades reach the +10%/+20% thresholds. The combination would
be double-conservative: tighter trail (E5) + partial exits (X5) = severely capped
upside with negligible MDD benefit over E5 alone.

**Verdict: CONFLICTING** — E5 already exits earlier (tighter trail). Adding partial
profit-taking on top would double-penalize the fat tail. The mechanisms compound
in the wrong direction.

---

## X6 — Adaptive Trail + Breakeven Floor (X2+X5 Hybrid)

### (a) Core concept
Combines X2's gain-tiered trail with a breakeven floor:
- Gain < 5%: trail = 3.0×ATR (no breakeven — needs room)
- 5% ≤ gain < 15%: trail = 4.0×ATR + breakeven floor (max(entry, trail))
- Gain ≥ 15%: trail = 5.0×ATR + breakeven floor
Binary exposure (stays 0 or 100%) — preserves CAGR upside that X5 sacrificed.

### (b) X0 weakness targeted
**Two weaknesses**: (1) fixed trail width (same as X2) and (2) no breakeven
protection — winning trades can become losers before trail catches up.

### (c) Does E5+EMA1D21 address this?
**PARTIALLY for (1), NO for (2)**.
- Trail stability: E5's robust ATR reduces spike-driven trail instability, but
  doesn't adapt to trade P&L
- Breakeven protection: E5 has NO breakeven floor. A trade at +8% can still
  exit at -2% if ATR spikes

The breakeven floor concept is genuinely **not covered** by E5+EMA1D21.

### (d) Recommendation: **CONFLICTING**

Despite the breakeven floor being a novel concept, X6 was **REJECTED** on X0 base:
- WFO 4/8 (worst window: delta -100.14 in 2024H2)
- Holdout: Sharpe -0.19 vs X0, CAGR -5.53%
- Bootstrap CI includes zero

The failure modes:
1. **Adaptive trail + E5 are conflicting** (same argument as X2)
2. **Breakeven floor harms trend-following**: During strong rallies with normal
   5-8% pullbacks, the breakeven floor converts healthy dips into flat exits.
   The 2024H2 BTC rally shows this catastrophically (delta -100.14)
3. The breakeven concept assumes trades should never give back gains below entry.
   But trend-following REQUIRES tolerance for drawdown within trades — that's
   how you stay in the big moves

The breakeven floor concept, while intuitively appealing, is structurally hostile
to trend-following. On E5+EMA1D21 (already tighter trail), adding a breakeven
floor would create even more premature exits during healthy pullbacks.

**Verdict: CONFLICTING** — breakeven floor + trend-following = structural incompatibility.
E5's tighter trail would amplify the problem. Do not combine.

---

## Summary Matrix

| Variant | Concept | X0 Weakness | E5 Covers? | Classification | Reason |
|---------|---------|-------------|------------|----------------|--------|
| **X1** | Relaxed re-entry | Re-entry delay | No | **REDUNDANT** | "Weakness" is actually protective (D1 filter). Empirically rejected. |
| **X2** | Adaptive trail | Fixed trail width | Partially | **CONFLICTING** | E5 tightens, X2 loosens → incoherent. Both fail OOS independently. |
| **X3** | Graduated sizing | Binary sizing | No | **REDUNDANT** | Structural failure (fat-tail incompatible). Base-independent. |
| **X4B** | Breakout entry | Late entry | No | **REDUNDANT** | EMA lag is the filter. Breakout degrades quality. Base-independent. |
| **X5** | Partial TP | No profit lock | Partially | **CONFLICTING** | E5 already exits earlier. Double-conservative = amputated fat tail. |
| **X6** | Adaptive + BE | Fixed trail + no BE | Partially | **CONFLICTING** | Breakeven floor hostile to trend-following. E5 amplifies problem. |

---

## COMPLEMENTARY Concepts: None

**No X variant produced a concept that is both (a) not covered by E5+EMA1D21 and
(b) structurally compatible with trend-following.**

The 6 concepts fall into two categories:
1. **REDUNDANT (X1, X3, X4B)**: The targeted "weakness" is either protective (X1),
   structurally incompatible with the strategy class (X3), or a feature not a bug (X4B).
   These fail regardless of base strategy.
2. **CONFLICTING (X2, X5, X6)**: The concept's mechanism opposes E5's tighter-trail
   philosophy, or opposes trend-following's fundamental requirement to preserve fat-tailed
   winners.

---

## Research Plan for COMPLEMENTARY Concepts

**None required.** All 6 concepts are either REDUNDANT or CONFLICTING with E5+EMA1D21.

### What this means for the research agenda

The X-series exhaustively explored the 5 most natural modifications to a trend-following
exit/entry/sizing system:
1. Entry relaxation (X1) — harmful
2. Adaptive exits (X2, X6) — overfit
3. Signal-based sizing (X3) — structurally broken
4. Alternative entry (X4B) — degrades quality
5. Partial realization (X5) — amputates fat tail

All 5 directions are dead ends for E5+EMA1D21. Future research should focus on
**orthogonal** dimensions not explored by X1-X6:
- Multi-asset diversification (cross-coin, documented ceiling: +3.5% CAGR max)
- Regime-conditioned vol-targeting (already partially explored via EMA regime)
- Alternative data sources (funding rates, on-chain metrics — different information axis)
- Execution optimization (entry timing within bar, limit vs market — reduces cost drag)

These are outside the scope of this audit but represent the remaining unexplored
dimensions after X1-X6 closure.
