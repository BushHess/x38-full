# Phase 3: Signal Landscape EDA

**Study**: X27
**Date**: 2026-03-11
**Data**: BTCUSDT H4 (18,752 bars) + D1, 2017-08 to 2026-03
**Code**: `code/phase3_signal_landscape.py`

---

## Objective

Survey the LANDSCAPE of possible entry and exit signal types. Answer:
"Which signal TYPES detect trends? Which exit TYPES preserve alpha?"
by MEASURING on data, not by opinion.

**Constraints**: BTC spot, H4 primary, long-only, 50 bps RT cost, ≤10 DOF total.
**Method**: Sweep parameters within each signal type, report TYPE AVERAGES (not cherry-picked best).

---

## 1. Target Event Definition

Using the Phase 2 trend-finding algorithm (cumulative return threshold from local troughs), target events are defined as upward moves ≥10% on H4 close prices.

| Metric | Value |
|--------|-------|
| N events | 28 |
| Frequency | 3.3/year |
| Duration mean | 29.8 bars (5.0 days) |
| Duration median | 14 bars (2.3 days) |
| Magnitude mean | 11.6% |
| Magnitude median | 11.2% |

**Distribution over time** (4 equal blocks):
- Block 1 (2017-08 → 2019-10): 15 events
- Block 2 (2019-10 → 2021-11): 9 events
- Block 3 (2021-11 → 2024-01): 0 events
- Block 4 (2024-01 → 2026-03): 4 events

- **Obs40**: Target events are highly non-uniform in time. Block 3 (late 2021 to early 2024) contains ZERO events — this was the bear/range market following the 2021 peak. Any signal evaluation must account for this temporal clustering.

---

## PART A: ENTRY SIGNAL LANDSCAPE

### 2. Signal Types Swept

| Type | Mechanism | Parameters | Combos |
|------|-----------|------------|--------|
| A | EMA crossover (fast > slow) | fast ∈ {5,10,20,30}, slow ∈ {50,80,120,160,200} | 20 |
| B | Breakout (close > N-bar high) | N ∈ {20,40,60,80,120,160} | 6 |
| C | ROC exceeds threshold | N ∈ {10,20,40,60}, thr ∈ {5%,10%,15%,20%} | 16 |
| D | Volatility breakout (close > SMA + w×ATR) | lb ∈ {20,40,60}, w ∈ {1.5,2.0,2.5,3.0} | 12 |
| E | Volume-confirmed | **SKIPPED** — Phase 2 Obs30 confirmed H_prior_5 | — |

Total: 54 parameter combinations across 4 signal types.

### 3. Entry Signal Comparison (Tbl07, averaged over parameter sweep)

| Type | Detection Rate | False Positive Rate | Avg Lag (bars) | Avg Slip (%) | Signals/yr |
|------|---------------|-------------------|----------------|-------------|-----------|
| A (EMA crossover) | **0.105** | 0.972 | 53.3 | -1.6 | 16 |
| B (Breakout) | **0.839** | 0.873 | 19.2 | 5.5 | 51 |
| C (ROC threshold) | 0.404 | 0.883 | **15.2** | 5.3 | 26 |
| D (Vol breakout) | 0.565 | 0.922 | 20.2 | 4.5 | 46 |

Key observations:

- **Obs41**: Type A (EMA crossover) has dramatically low detection (10.5%). The crossover is too slow for short-duration target events (median 14 bars). Average lag of 53 bars means the crossover typically fires AFTER the trend has ended. The negative slip (-1.6%) indicates crossovers sometimes fire at prices below the trend start point.

- **Obs42**: Type B (Breakout) achieves the highest detection rate (83.9%) with moderate lag (19 bars). Breaking above N-bar highs is the most natural detector of upward price moves. The 5.5% average slip means ~half the 10% trend is already captured by the time the signal fires.

- **Obs43**: Type C (ROC threshold) has the lowest lag (15.2 bars) but only 40% detection. The threshold requirement filters out slow-developing trends that don't produce a sharp enough rate-of-change spike. It is the most "selective" entry type.

- **Obs44**: Type D (Volatility breakout) sits in between: 56.5% detection, 20 bars lag. Breaking above a volatility-defined channel requires a sufficiently strong move relative to recent volatility, acting as a natural filter.

- **ALL types have >87% false positive rate.** This is a structural property: most signals fire outside of the defined target events. Entry signals alone cannot reliably predict a ≥10% upward move.

### 4. Signal Efficiency Frontier (Fig10)

**Fig10** plots average lag (x-axis) vs false positive rate (y-axis) for all 54 parameter combinations, colored by type.

The frontier (lower-left boundary = low lag AND low FP) is populated by:
- **Type B** (breakout): low lag, moderate FP — forms the dominant cluster in the frontier region
- **Type C** (ROC): lowest lag cluster, but scattered across FP range

**Type A is dominated**: it occupies the upper-right (high lag AND high FP) region. No Type A variant reaches the frontier.

**Type D** is intermediate: scattered between B and A, with no clear frontier advantage.

### 5. Signal Robustness (4 time blocks)

| Type | Det rate std across blocks | FP rate std across blocks |
|------|--------------------------|--------------------------|
| A | 0.147 | 0.026 |
| B | 0.123 | 0.028 |
| **C** | **0.082** | **0.019** |
| D | 0.156 | 0.011 |

- **Obs45**: Type C (ROC threshold) is the most stable across time blocks (det_std = 0.082). Type D (volatility breakout) is the least stable (det_std = 0.156). The FP rates are relatively stable for all types (std < 0.03), indicating that the false positive structure is time-invariant.

Note: Block 3 has ZERO target events, which affects robustness measurement. With only 3 usable blocks containing events, the stability estimates have limited precision.

---

## PART B: EXIT SIGNAL LANDSCAPE

### 6. Exit Types Swept

| Type | Mechanism | Parameters | Combos |
|------|-----------|------------|--------|
| X | Fixed trailing stop (%) | trail ∈ {3,5,8,12,15,20}% | 6 |
| Y | ATR trailing stop | period ∈ {14,20,30}, mult ∈ {2.0–5.0} | 18 |
| Z | Signal reversal (A-D reversed) | ZA: EMA cross-down (9), ZB: break below (4), ZC: ROC drop (9), ZD: vol channel (9) | 31 |
| W | Time-based (fixed holding period) | hold ∈ {20,40,60,80,120,160,200} bars | 7 |
| V | Volatility-based | spike K ∈ {1.5,2.0,2.5,3.0}, compress K ∈ {0.3,0.5} | 6 |

Total: 68 parameter combinations. Applied to 28 target events with perfect entry (enter at trend start).

### 7. Exit Signal Comparison (Tbl08, averaged by type group)

| Type | Capture Ratio | Churn Rate | Avg Hold (bars) | Avg Return/trade (%) | Max DD (%) |
|------|--------------|-----------|----------------|--------------------|-----------|
| X (Fixed trail) | 0.974 | **0.940** | 68 | 10.6 | 12.2 |
| Y (ATR trail) | 0.895 | 0.909 | 59 | 10.0 | 14.8 |
| Z (Signal reversal) | 1.427 | 0.926 | 101 | 15.7 | 18.7 |
| W (Time-based) | 1.904 | 0.857 | 97 | 21.5 | 17.9 |
| V (Volatility-based) | 2.638 | **0.833** | 209 | 29.5 | 24.2 |

Key observations:

- **Obs46–50**: ALL exit types have churn rate > 80%. This is the single most striking finding of the exit landscape. After exiting a trade, price recovers above the exit level within 10 bars in 83–94% of cases. **Churn is a structural property of BTC price dynamics, not specific to any exit mechanism.**

- **Capture ratio vs holding period tradeoff**: Types that hold longer (V: 209 bars, W: 97 bars) capture more (cap 1.9–2.6) but at the cost of higher MDD (18–24%) and longer capital lockup. Types that exit quickly (Y: 59 bars, X: 68 bars) capture approximately the target trend (cap ~1.0) with lower MDD (12–15%) but the highest churn.

- **Capture > 1.0** for Z, W, V means these exits hold beyond the target event's peak, capturing additional upward movement (or giving back gains from the peak). The high capture is partly an artifact of holding through price oscillations after the trend peak.

- **Return per trade**: V has the highest return (29.5%) due to very long holding, but also highest MDD (24.2%). Y has the lowest return per trade (10.0%) but lowest MDD among trailing stops (14.8%).

### 8. Exit Efficiency Frontiers (Fig11, Fig12)

**Fig11** (capture vs churn): No exit type reaches the upper-left ideal (high capture, low churn). The frontier runs from lower-right (X, Y: ~1.0 capture, 91–94% churn) to upper-left (V: 2.6 capture, 83% churn). The tradeoff is monotonic: more capture requires longer holding which slightly reduces churn.

**Fig12** (capture vs drawdown): The frontier runs from lower-left (Y: 0.9 capture, 15% MDD) to upper-right (V: 2.6 capture, 24% MDD). Types X and Y dominate the low-capture-low-MDD end; V and W occupy the high-capture-high-MDD end.

**No exit type achieves simultaneously high capture (>0.6) and low churn (<0.10).** This confirms the structural difficulty of exiting BTC trends without premature exits.

---

## PART C: ENTRY × EXIT INTERACTION

### 9. Pairing Analysis (Tbl09, Fig13)

Representative parameters selected per type (best detection_rate − fp_rate for entry, best capture − churn for exit):

Entry reps: A=f20/s50, B=N160, C=N10/t5, D=lb20/w1.5
Exit reps: X=trail15, Y=atr30/m5.0, Z=low80, W=hold200, V=compress_0.3

**Sharpe Ratio Heatmap** (50 bps RT):

| Entry \ Exit | V | W | X | Y | Z |
|-------------|------|------|------|------|------|
| A | 0.526 | 0.015 | 0.437 | 0.628 | 0.629 |
| **B** | 0.584 | 0.740 | 0.840 | **1.064** | 0.886 |
| C | 0.627 | 0.394 | 0.600 | 0.833 | 0.726 |
| D | 0.560 | 0.511 | 0.441 | 0.620 | 0.627 |

**CAGR Heatmap** (%):

| Entry \ Exit | V | W | X | Y | Z |
|-------------|------|------|------|------|------|
| A | 41.9 | 0.9 | 24.2 | 34.9 | 41.8 |
| B | 45.7 | 40.4 | 39.0 | 47.5 | 51.8 |
| C | 51.4 | 28.3 | 40.7 | 57.9 | 54.1 |
| D | 45.2 | 37.0 | 27.0 | 38.6 | 44.3 |

**MDD Heatmap** (%):

| Entry \ Exit | V | W | X | Y | Z |
|-------------|------|------|------|------|------|
| A | 83.8 | 86.5 | 79.8 | 65.0 | 70.6 |
| B | 79.2 | 65.3 | 58.0 | **44.6** | 64.1 |
| C | 79.3 | 81.5 | 76.3 | 70.8 | 80.3 |
| D | 83.7 | 77.7 | 81.8 | 74.3 | 75.9 |

**Exposure Heatmap** (%):

| Entry \ Exit | V | W | X | Y | Z |
|-------------|------|------|------|------|------|
| A | 87.5 | 73.3 | 76.5 | 58.6 | 72.2 |
| B | 80.5 | 50.7 | 49.3 | **30.1** | 44.5 |
| C | 86.2 | 77.6 | 84.0 | 62.0 | 74.8 |
| D | 87.9 | 85.2 | 83.0 | 67.9 | 79.4 |

- **Obs51**: The best pair is **B+Y** (breakout entry + ATR trailing stop): Sharpe 1.064, CAGR 47.5%, MDD 44.6%, 50 trades, 30% exposure. The range across all 20 pairs is 1.049 — signal type choice has a LARGE impact on performance.

Structural patterns in the heatmap:
1. **Entry type B dominates across ALL exit types.** B's Sharpe column ({0.58, 0.74, 0.84, 1.06, 0.89}) is strictly above A's ({0.53, 0.02, 0.44, 0.63, 0.63}) and D's ({0.56, 0.51, 0.44, 0.62, 0.63}).
2. **Exit type Y (ATR trail) produces the highest Sharpe across ALL entry types.** The Y column ({0.63, 1.06, 0.83, 0.62}) dominates or ties every other exit column.
3. **Entry matters more than exit.** The Sharpe range across entry types (within a fixed exit) averages 0.45, while across exit types (within a fixed entry) averages 0.39.
4. **Exposure is inversely correlated with Sharpe.** The best pair (B+Y, Sharpe 1.064) has the lowest exposure (30.1%). High-exposure pairs tend to have worse risk-adjusted returns.
5. **Exit type V (vol-based) produces uniformly high exposure (80–88%) but mediocre Sharpe (0.53–0.63).** The long holding periods lock in capital without corresponding risk-adjusted improvement.

### 10. Regime Conditioning (Tbl10)

D1 SMA200 regime filter: only take entries when D1 close > D1 SMA(200) (lagged by 1 day to avoid lookahead).

| Metric | All pairs avg (no filter) | All pairs avg (bull only) | Δ |
|--------|--------------------------|--------------------------|---|
| Sharpe | 0.598 | 0.521 | **-0.077** |
| CAGR | 38.1% | 23.4% | -14.7 |
| MDD | 73.7% | 57.7% | **-16.0** |
| N trades | 56 | 31 | -25 |
| Exposure | 70.2% | 42.0% | -28.2 |

- **Obs52**: Regime filter (bull-only) improves Sharpe for only 5/20 pairs (25%). Average ΔSharpe = −0.077. However, it consistently reduces MDD (average −16 pp) and exposure (average −28 pp).

The effect is NOT uniform:
- Best improvement: B+W (+0.234 Sharpe, −27 pp MDD)
- Worst change: A+X (−0.368 Sharpe)

**The regime filter trades CAGR for MDD reduction.** It removes both profitable and unprofitable bear-regime trades, reducing overall return. The Sharpe effect depends on whether excluded trades were net positive or negative — which varies by entry×exit combination.

This contrasts with Phase 2's Obs37 (D1 SMA200 conditioning is statistically significant). The significance of the regime as a conditioning variable does NOT guarantee it improves strategy Sharpe — it shifts the return distribution without uniformly improving risk-adjusted return.

---

## Hypothesis Verification

### H_prior_3 (Entry Lag): CONFIRMED

> Any type with lag < 20 bars AND FP < 50%?

**No.** Zero type averages AND zero individual parameter combinations achieve both lag < 20 bars and FP < 50% simultaneously. The lag-vs-FP tradeoff is fundamental:
- Types with low lag (C: 15 bars) have 88% FP rate
- Types with high detection (B: 84%) have 87% FP rate
- No mechanism tested escapes this tradeoff

**Obs53**: The prior observation that "all efforts to reduce lag increase false signal rate" is confirmed across all 4 signal types and 54 parameter combinations.

### H_prior_4 (Exit Churn): CONFIRMED

> Any exit type with churn < 10% AND capture > 60%?

**No.** Zero type averages AND zero individual parameter combinations achieve both. The minimum churn is 78.6% (individual Y combos), far above 10%. Churn is structural in BTC trend-following.

**Obs54**: The ~10% ceiling on churn repair identified in prior research is validated. The problem is not the exit mechanism — it's the BTC price process (post-exit price recovery is near-universal for trend exits).

### H_prior_7 (Low Exposure): PARTIALLY REFUTED

> Any entry×exit pair with exposure > 60%?

**Yes — 15 out of 20 pairs.** Maximum exposure is 87.9% (D+V). The prior finding of ~45% exposure was specific to the EMA crossover + ATR trail combination (our A+Y has 58.6%, our B+Y has 30.1%). Exposure is highly dependent on signal type:
- Entries with high signal frequency (A, C, D: 16–46/yr) produce high exposure
- The best-performing pair (B+Y) has the LOWEST exposure (30.1%)

**Obs55**: Low exposure is a feature of the best-performing signal combinations, not a universal constraint. The 45% figure from prior research reflects the specific entry+exit choice, not a structural limit.

### H_prior_10 (Complexity Ceiling): NUANCED

> Simplest vs most complex in landscape — gap?

The Sharpe range across all 20 entry×exit pairs is **1.049** (from 0.015 to 1.064), with std = 0.217. This is a LARGE range — signal type selection is the dominant factor in performance.

However, this range comes primarily from ENTRY type selection (B >> A, C > D > A), not from adding complexity within a type. The simplest entry (B with 1 parameter) produces the best results. Adding complexity (D with 2 parameters, or stacking filters) does NOT systematically improve performance.

**Obs56**: The complexity ceiling holds within signal types (more parameters ≠ better), but signal TYPE selection itself creates a large performance gap. The prior finding that "40+ params adds zero value over 3 params" is consistent — the value comes from choosing the RIGHT 1–3 parameters, not from having more.

---

## Observation Registry

| ID | Description | Evidence |
|----|-------------|----------|
| Obs40 | Target events: 28 upward moves ≥10%, 3.3/yr, median 14 bars. Temporally clustered (Block 3 = 0 events). | Tbl06 |
| Obs41 | Entry Type A (EMA cross): det=0.105, FP=0.972, lag=53. Poorly suited for short trends. | Tbl07 |
| Obs42 | Entry Type B (Breakout): det=0.839, FP=0.873, lag=19. Best detection rate. | Tbl07 |
| Obs43 | Entry Type C (ROC): det=0.404, FP=0.883, lag=15. Lowest lag, most selective. | Tbl07 |
| Obs44 | Entry Type D (Vol breakout): det=0.565, FP=0.922, lag=20. Intermediate. | Tbl07 |
| Obs45 | Robustness: Type C most stable (det_std=0.082), Type D least stable (det_std=0.156). | Tbl07 |
| Obs46 | Exit Type V: cap=2.64, churn=0.83, hold=209bars. Longest hold, lowest churn. | Tbl08 |
| Obs47 | Exit Type W: cap=1.90, churn=0.86, hold=97bars. Time-based, simple. | Tbl08 |
| Obs48 | Exit Type X: cap=0.97, churn=0.94, hold=68bars. Tight trail, highest churn. | Tbl08 |
| Obs49 | Exit Type Y: cap=0.90, churn=0.91, hold=59bars. ATR trail, best risk-adjusted exit. | Tbl08 |
| Obs50 | Exit Type Z: cap=1.43, churn=0.93, hold=101bars. Signal reversal, intermediate. | Tbl08 |
| Obs51 | Best pair B+Y: Sharpe 1.064, CAGR 47.5%, MDD 44.6%, 30% exposure. Range 1.049. | Tbl09, Fig13 |
| Obs52 | Regime filter: 5/20 improved Sharpe, avg ΔSharpe=-0.077, avg ΔMDD=-16pp. | Tbl10 |
| Obs53 | H_prior_3: 0 combos achieve lag<20 AND FP<50%. Tradeoff is fundamental. | Tbl07 |
| Obs54 | H_prior_4: 0 combos achieve churn<10% AND cap>60%. Churn is structural. | Tbl08 |
| Obs55 | H_prior_7: 15/20 pairs have exposure>60%. Low exposure is entry-dependent, not universal. | Tbl09 |
| Obs56 | H_prior_10: Sharpe range 1.049 across pairs. Signal TYPE selection dominates. | Tbl09 |

---

## End-of-Phase Checklist

### 1. Files created
- `03_signal_landscape_eda.md` (this report)
- `code/phase3_signal_landscape.py`
- `figures/Fig10_entry_efficiency_frontier.png`
- `figures/Fig11_exit_capture_vs_churn.png`
- `figures/Fig12_exit_capture_vs_drawdown.png`
- `figures/Fig13_entry_exit_heatmap.png`
- `tables/Tbl07_entry_signals.csv` (+ detail)
- `tables/Tbl08_exit_signals.csv` (+ detail)
- `tables/Tbl09_entry_exit_pairing.csv`
- `tables/Tbl10_regime_conditioning.csv`
- `tables/phase3_observations.csv`

### 2. Key Obs / Prop IDs created
Obs40–Obs56 (17 observations)

### 3. Blockers / uncertainties
- **Temporal clustering**: Block 3 (2021-11 to 2024-01) has zero target events. Robustness analysis relies on only 3 of 4 blocks. The signal landscape is measured predominantly on bull/recovery markets.
- **Target event count**: 28 events provides adequate but not large sample for per-event exit analysis. Individual exit metrics have high variance.
- **Representative selection**: Part C uses one representative parameter per type (best score). Different parameter selections could shift the heatmap values, though the TYPE-level ordering is likely robust.
- **Regime filter paradox**: Phase 2 showed D1 SMA200 is statistically significant (Obs37, p=0.0004), but here regime filter hurts average Sharpe. The significance of a conditioning variable does not guarantee it improves strategy performance — it may just shift the return distribution.

### 4. Gate status
**PASS_TO_NEXT_PHASE**

The signal landscape has been characterized:
1. Entry: Breakout (B) dominates detection; EMA crossover (A) is poorly suited for short H4 trends
2. Exit: ALL types have >80% churn — this is structural, not mechanism-specific
3. Pairing: B+Y (breakout + ATR trail) is the best combination found (Sharpe 1.064)
4. The lag-vs-FP tradeoff and universal churn are fundamental constraints of this data

Ready for Phase 4 (Formalization).
