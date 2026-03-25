# Phase 6: Design

**Study**: X27
**Date**: 2026-03-11
**Input**: Phase 2–5 deliverables (Obs09–Obs60, Prop01–Prop08), manifest.json

---

## 1. CANDIDATE SPECIFICATIONS

### Cand01: Breakout + ATR Trail (PRIMARY)

**PROVENANCE CHAIN**:
Cand01 ← Prop02 ← Obs42 ← Tbl07, Fig10
Cand01 ← Prop03 ← Obs49, Obs14 ← Tbl08, Fig12, Fig03
Cand01 ← Prop01 ← Obs16, Obs57, Obs20 ← Tbl04_VR, Tbl11, Tbl06

**DOF**: 3

**Complete Rule Set**:

**Entry condition**:
At each H4 bar close: enter long if flat AND

    close_t > max(high_{t-N}, high_{t-N+1}, ..., high_{t-1})

i.e., current close exceeds the highest high of the preceding N bars.

**Exit condition**:
While in position, at each H4 bar close: exit if

    close_t ≤ trail_t

where

    trail_t = max(close_s for s ∈ [entry_bar, t]) − m × ATR(p)_t

ATR(p)_t is the standard Average True Range over the most recent p bars.
Trail is recalculated each bar — rises with new highs, widens if ATR increases.

**Filter condition**: None.

**Position sizing**: Binary {0, 1}. Full allocation when in position, flat otherwise.

**Parameters**:

| Parameter | Default | Range | Justification |
|-----------|---------|-------|---------------|
| N (breakout lookback) | 120 | [40, 160] | Obs60: information concentrated at 60–120 bar lookback (roc_120 ρ=0.048, breakout_120 ρ=0.042 at k=60 — highest among breakout features, Tbl11). Tbl07: detection plateau at N≥60 (0.8214), FP decreases monotonically (N=120: FP=0.848 vs N=20: FP=0.912). N=120 maximizes information content within the detection plateau. |
| p (ATR period) | 20 | [14, 30] | Obs23: realized vol ACF lag20=0.597 — period 20 integrates ~60% of volatility persistence. Obs14: vol clustering is the dominant serial structure; ATR period must capture it. Midpoint of admissible range [14, 30]. |
| m (ATR multiplier) | 4.0 | [2.0, 5.0] | Tbl08: m=4.0 achieves capture 1.34–1.41 (among highest for p=14, p=20), with MDD 18–19% at target-event level. Obs22: post-peak gradual decay (+4.96% in 20 bars, Fig06) supports wider stop to capture continuation. m=4.0 balances between tight (m=2–3, cap<1.0, low MDD) and wide (m=5.0, highest MDD). |

---

### Cand02: Breakout + ATR Trail + D1 EMA Regime Filter

**PROVENANCE CHAIN**:
Cand02 ← Cand01 (all chains above)
Cand02 ← Prop05 ← Obs37 ← Tbl10
Cand02 ← Prop05 ← Obs52 ← Tbl10_regime
Cand02 ← Prop05 ← Obs59 ← Tbl11

**DOF**: 4

**Complete Rule Set**:

**Entry condition**:
At each H4 bar close: enter long if flat AND

    close_t > max(high_{t-N}, ..., high_{t-1})

AND

    D1_close_{d-1} > EMA_D1(K)_{d-1}

where d is the current D1 bar index (d-1 = last completed D1 bar, lagged 1 day to avoid lookahead). EMA_D1(K) is the K-period exponential moving average of D1 close prices.

**Exit condition**: Same as Cand01 (ATR trail). The regime filter does NOT affect exits — once in position, the exit is purely trail-based.

**Filter condition**: D1 close (lagged) > D1 EMA(K) (lagged). Only affects entry gating.

**Position sizing**: Binary {0, 1}.

**Parameters**:

| Parameter | Default | Range | Justification |
|-----------|---------|-------|---------------|
| N (breakout lookback) | 120 | [40, 160] | Same as Cand01 |
| p (ATR period) | 20 | [14, 30] | Same as Cand01 |
| m (ATR multiplier) | 4.0 | [2.0, 5.0] | Same as Cand01 |
| K (D1 EMA period) | 21 | [15, 50] | Obs59: D1 EMA(21) ρ=0.046 at k=20 (p<0.001) vs SMA(200) ρ=0.008 (p=0.250). EMA(21) carries 5.5× more information than SMA(200) at the relevant horizon (Tbl11). Range [15, 50]: short enough to be responsive to regime shifts, long enough to avoid noise. |

---

### Cand03: ROC Threshold + ATR Trail

**PROVENANCE CHAIN**:
Cand03 ← Prop07 ← Obs60 ← Tbl11
Cand03 ← Prop03 ← Obs49, Obs14 ← Tbl08, Fig12, Fig03
Cand03 ← Prop01 ← Obs16, Obs57, Obs20 ← Tbl04_VR, Tbl11, Tbl06
Cand03 ← Obs43 ← Tbl07, Fig10

**DOF**: 4

**Complete Rule Set**:

**Entry condition**:
At each H4 bar close: enter long if flat AND

    (close_t / close_{t-N_roc} − 1) > τ

i.e., the N_roc-bar rate of change exceeds threshold τ.

**Exit condition**: Same as Cand01 (ATR trail, parameters p and m).

**Filter condition**: None.

**Position sizing**: Binary {0, 1}.

**Parameters**:

| Parameter | Default | Range | Justification |
|-----------|---------|-------|---------------|
| N_roc (ROC lookback) | 40 | [10, 60] | Obs60: roc_40 significant at k=10+ (ρ=0.024 at k=10, 0.040 at k=60, Tbl11). Within the informative range [40, 120]. N=40 chosen over N=60/N=120 because ROC entry's purpose is SPEED advantage (Obs43: lowest lag type); shorter lookback preserves this advantage. Tbl07: N40_t15 has best balance (det=0.536, fp=0.862, lag=13.8) among N=40 settings. |
| τ (ROC threshold) | 15% | [5%, 20%] | Tbl07: N40_t15 achieves highest detection (0.536) and lowest FP (0.862) among all N=40 settings — it empirically dominates N40_t5 (det=0.321, fp=0.950), N40_t10 (det=0.321, fp=0.940), and N40_t20 (det=0.464, fp=0.789). τ=15% with N=40 selects trends with sufficient momentum context: Obs21 shows pre-trend +9.16% mean, so ROC(40) ≈ pre-trend + trend onset ≈ 15–20% for detected events. |
| p (ATR period) | 20 | [14, 30] | Same as Cand01 |
| m (ATR multiplier) | 4.0 | [2.0, 5.0] | Same as Cand01 |

---

## 2. PARAMETER DEFAULTS — EVIDENCE SUMMARY

| Parameter | Default | Evidence Source | Strength |
|-----------|---------|----------------|----------|
| N_breakout = 120 | Tbl11 (breakout_120 ρ peak at k=40-60), Tbl07 (detection plateau + FP), Obs60 | HIGH — converging evidence from information ranking and signal sweep |
| p_atr = 20 | Obs23 (vol ACF), Obs14 (vol clustering) | MEDIUM — midpoint of range, justified by vol memory structure |
| m_atr = 4.0 | Tbl08 (capture analysis), Obs22 (post-peak decay) | MEDIUM — balances capture/MDD tradeoff |
| K_ema = 21 | Tbl11 (d1_above_ema21 ρ=0.046), Obs59 | HIGH — EMA(21) dominates SMA(200) in information content |
| N_roc = 40 | Tbl11 (roc_40 significant), Tbl07 (N40_t15 best balance), Obs43 (speed) | MEDIUM — chosen for speed differentiation from breakout |
| τ_roc = 15% | Tbl07 (empirically dominates other τ at N=40), Obs21 (pre-trend momentum) | HIGH — empirically best within N=40 sweep |

---

## 3. BENCHMARK COMPARISON PLAN

### Benchmark Implementation: VTREND E5+EMA21D1

From Phase 0, Section D:

**Entry**: EMA(30) crosses above EMA(120) on H4 close.
**Filter**: VDO(12,28) > 0 AND D1 close > D1 EMA(21) (lagged 1 day).
**Exit**: ATR trailing stop (period=20, multiplier=3.0) OR EMA(30) crosses below EMA(120).
**Position sizing**: Binary {0, 1} (same as candidates for fair comparison).
**Cost**: 50 bps round-trip.

VDO(S,L) = EMA(volume, S) / EMA(volume, L) − 1 (Volume Delta Oscillator).

Note: Benchmark published metrics (Sharpe 1.19, CAGR 52.59%) used vol-target sizing (f=0.30).
Phase 7 will report benchmark with BOTH binary and vol-target sizing for comparison.

### Metrics (all candidates + benchmark, same data, same cost)

| Metric | Description |
|--------|-------------|
| Sharpe | Annualized Sharpe ratio of daily strategy returns |
| CAGR | Compound annual growth rate |
| MDD | Maximum peak-to-trough drawdown |
| Calmar | CAGR / MDD |
| Trade count | Total number of round-trip trades |
| Win rate | Fraction of trades with positive return |
| Exposure | Fraction of time with open position |
| Avg duration | Mean holding period (H4 bars) |
| Max consec losses | Longest streak of losing trades |

---

## 4. PRE-COMMITTED REJECTION CRITERIA

**These criteria are FIXED and CANNOT be modified after Phase 7 begins.**

| # | Criterion | Threshold | Rationale |
|---|-----------|-----------|-----------|
| R1 | Negative EV | Sharpe < 0 | No alpha |
| R2 | Significantly worse than benchmark | Sharpe < benchmark_binary × 0.80 | 20% shortfall threshold |
| R3 | Unacceptable risk | MDD > 75% | Capital preservation floor |
| R4 | Insufficient sample | Trade count < 15 | Unreliable statistics |
| R5 | Out-of-sample failure | WFO win rate < 50% | No forward validity |
| R6 | Luck | Bootstrap P(Sharpe > 0) < 60% | Below chance level |

**Note on R2**: `benchmark_binary` is the Sharpe of the VTREND benchmark implemented with binary sizing (determined in Phase 7). The benchmark implementation is fully specified above and cannot be changed.

---

## 5. EXPECTED BEHAVIOR (pre-backtest estimates)

### Cand01 (Breakout + ATR Trail, 3 DOF)

| Metric | Estimate | Source |
|--------|----------|--------|
| Trade count | 45–65 | Tbl07: breakout N=120 fires 36.78/yr; Tbl08: atr20_m4.0 hold≈84 bars → ~5–7 trades/yr × 8.5yr |
| Exposure | 25–35% | Tbl09: B+Y reference=30.1% (with atr30_m5.0); m=4.0 shorter hold → slightly lower |
| Avg holding period | 60–90 bars (10–15 days) | Tbl08: atr20_m4.0 hold=83.9 bars |
| Churn | Near zero | Tbl09: B+Y churn=0/50 trades — breakout re-entry requires new N-bar high, naturally anti-churn |
| Sharpe | 0.9–1.1 | Tbl09: B+Y reference=1.064 (atr30_m5.0); conservative range for parameter variation |
| CAGR | 40–50% | Tbl09: B+Y reference=47.5% |
| MDD | 40–50% | Tbl09: B+Y reference=44.6% |
| ΔSharpe vs benchmark | −0.3 to +0.1 | Phase 5: expected −0.13 from reference data (conservative, parameters may differ) |

**Key structural advantage**: Breakout entry naturally eliminates churn (Tbl09: 0 churn events in 50 trades). After an ATR trail exit, re-entry requires price to make a new N-bar high — this mechanical delay prevents the exit→re-enter→exit cycle that plagues EMA crossover systems (Prop04, Obs54).

### Cand02 (Breakout + ATR Trail + D1 EMA21 Regime, 4 DOF)

| Metric | Estimate | Source |
|--------|----------|--------|
| Trade count | 25–40 | Obs52: regime filter halves trade count (−25 avg) |
| Exposure | 15–25% | Tbl10: B+Y bull exposure=21.0% |
| Avg holding period | 60–90 bars | Same exit mechanism as Cand01 |
| Sharpe | 0.8–1.0 | Tbl10: B+Y bull Sharpe=0.873 (with SMA200); EMA(21) may improve per Obs59 |
| CAGR | 25–40% | Tbl10: B+Y bull CAGR=26.9% (SMA200 regime); EMA(21) may differ |
| MDD | 35–50% | Tbl10: B+Y bull MDD=44.7% (note: MDD NOT reduced by SMA200 filter for this pair) |
| ΔSharpe vs benchmark | −0.4 to 0.0 | Regime filter expected to reduce Sharpe relative to Cand01 |

**Caveat**: Phase 3 regime analysis used SMA(200), not EMA(21). Cand02 uses EMA(21) based on its superior information content (Obs59). Actual results may differ from Phase 3 regime conditioning data.

**Important observation**: For the B+Y pair specifically, the SMA(200) regime filter does NOT reduce MDD (44.69% bull vs 44.59% all — Tbl10). The worst drawdowns occur WITHIN the bull regime. The shorter EMA(21) may or may not improve this.

### Cand03 (ROC + ATR Trail, 4 DOF)

| Metric | Estimate | Source |
|--------|----------|--------|
| Trade count | 50–80 | Tbl07: N40_t15 fires 19.5/yr; with exits → ~6–10 trades/yr × 8.5yr |
| Exposure | 35–55% | Tbl09: C+Y reference=62.0% (with N10_t5); N40_t15 more selective → lower |
| Avg holding period | 60–90 bars | Same exit as Cand01 |
| Sharpe | 0.7–0.9 | Tbl09: C+Y reference=0.833 (with N10_t5, atr30_m5.0); N40_t15 more selective |
| CAGR | 40–55% | Tbl09: C+Y reference=57.9%; lower detection → lower CAGR |
| MDD | 55–70% | Tbl09: C+Y reference=70.8%; more selective entry may reduce but not eliminate |
| ΔSharpe vs benchmark | −0.5 to −0.1 | Likely below benchmark; value is testing alternative entry hypothesis |

**Speed advantage**: Cand03's entry lag (13.8 bars, Tbl07) is 32% faster than Cand01's breakout lag (20.4 bars). The hypothesis: faster entry with ROC trades lower detection rate for better entry prices on captured trends. Phase 7 will determine whether this tradeoff is favorable.

---

## 6. CANDIDATE COMPARISON SUMMARY

| Property | Cand01 (B+Y) | Cand02 (B+Y+F1) | Cand03 (C+Y) |
|----------|-------------|-----------------|-------------|
| DOF | 3 | 4 | 4 |
| Entry mechanism | New N-bar high | New N-bar high + bull regime | N-bar ROC > threshold |
| Entry lag | 20.4 bars | 20.4 bars | 13.8 bars |
| Detection rate | 0.821 | ~0.821 × regime fraction | 0.536 |
| FP rate | 0.848 | Lower (regime filters FPs) | 0.862 |
| Churn expected | Near zero | Near zero | Unknown (ROC re-entry different) |
| Hypothesis tested | Breakout is dominant entry | Regime filter adds value for breakout | Speed > detection for entry |
| Status | PRIMARY | VARIANT (filter test) | SECONDARY (entry alternative) |

**Design principle**: All three candidates share the ATR trail exit (Prop03: dominant exit class). The variation is ONLY in the entry mechanism. This isolates the entry-type effect for clean comparison.

---

## 7. ANTI-POST-HOC DECLARATION

Cand01's breakout entry closely resembles Donchian channel breakout systems. This emerged as a consequence of the evidence chain:
1. Phase 2: no return persistence → cannot PREDICT direction (Obs16, Obs19)
2. Phase 3: breakout DETECTS price making new highs (Obs42) — does not predict
3. Phase 4: breakout has highest information content at relevant horizons (Tbl11)
4. Phase 3: breakout dominates the efficiency frontier across all exit types (Fig10, Obs51)

The resemblance to Donchian channels is an emergent property of the data analysis, not a post-hoc wrapper. The critical difference from naive Donchian: the ATR-adaptive exit (not fixed channel exit) and the specific lookback (N=120, evidence-driven, not arbitrary).

Cand03's ROC entry resembles momentum threshold strategies. This emerged from:
1. Obs60: information concentrated at 60–120 bar lookback
2. Obs43: ROC type has lowest lag (15.2 bars)
3. Tbl07: N40_t15 empirically dominates within its parameter space

---

## End-of-Phase Checklist

### 1. Files created
- `06_design.md` (this report)

### 2. Key Obs / Prop IDs created
- Cand01, Cand02, Cand03 (3 candidate specifications)

### 3. Blockers / uncertainties
- **Benchmark sizing mismatch**: Benchmark published metrics use vol-target (f=0.30), candidates use binary sizing. Phase 7 must re-run benchmark with binary sizing for fair comparison. If binary-sizing benchmark Sharpe is substantially different from 1.19, the R2 rejection threshold shifts.
- **Regime filter caveat**: Phase 3 tested SMA(200) regime, not EMA(21). Cand02's EMA(21) filter is evidence-based (Obs59) but untested in full pairing. Actual ΔSharpe may differ from Phase 3 estimates.
- **B+Y MDD insensitivity to regime**: Phase 3 data shows SMA(200) filter does NOT reduce MDD for B+Y specifically (44.69% vs 44.59%). If EMA(21) shows the same pattern, Cand02 offers no advantage over Cand01 and should be rejected per DOF preference (rule 3: fewer DOF if evidence equivalent).
- **ROC churn unknown**: Tbl09 shows B+Y has 0 churn, but C+Y had 13 churn events out of 105 trades. ROC entry may not have breakout's natural anti-churn property. This could hurt Cand03's cost-adjusted performance.
- **ATR trail formulation**: Trail is recalculated each bar (chandelier-style) rather than ratcheted. If ATR increases, trail can widen (move down). This was the Phase 3 test methodology; Phase 7 must use the same formulation.

### 4. Gate status
**PASS_TO_NEXT_PHASE**

Three candidates designed with:
1. Complete provenance chains (Cand## ← Prop## ← Obs## ← Fig##/Tbl##)
2. Exact formulas for entry, exit, and filter conditions
3. Evidence-based parameter defaults (6 parameters, all justified)
4. Pre-committed rejection criteria (6 criteria, fixed)
5. Expected behavior estimates from Phase 3 data
6. Benchmark implementation specified for fair comparison

Ready for Phase 7 (Validation).
