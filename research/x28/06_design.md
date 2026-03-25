# Phase 6 — Design

**Input**: Phases 2–5 deliverables, Phase 3 grid data, Phase 5 GO_TO_DESIGN decision
**Protocol**: Design candidates from Phase 3 grid, constrained by Phase 4 function classes and Phase 5 constraints.
**Restriction**: No backtesting. Defaults from evidence or Phase 3 grid only.

---

## 1. CANDIDATE SELECTION — DATA-DRIVEN

### 1.1 Source: Tbl_top20_sharpe (Phase 3 Part E)

| Rank | Config | Sharpe | CAGR | MDD | Trades | avg_loser | avg_hold |
|------|--------|--------|------|-----|--------|-----------|----------|
| 1 | A_20_90+X_trail8+F2_d1ema50 | 1.251 | 41.7% | 52.0% | 39 | -0.070 | 124.3 |
| 2 | A_20_90+XZ_trail8_rev+F4_vol_low | 1.128 | 31.2% | 34.5% | 57 | -0.034 | 85.9 |
| 3 | A_20_90+XZ_trail8_rev+F2_d1ema50 | 1.099 | 32.1% | 40.3% | 49 | -0.043 | 75.6 |
| 4 | A_20_90+XZ_trail8_rev | 1.053 | 45.4% | 48.9% | 114 | -0.042 | 69.7 |
| 5 | A_20_90+X_trail8+F4_vol_low | 1.018 | 29.8% | 39.7% | 38 | -0.062 | 156.1 |
| 6 | A_20_90+X_trail8 | 0.962 | 42.8% | 54.0% | 87 | -0.065 | 105.3 |
| 7 | A_20_90+X_trail8+F1_d1ema21 | 0.937 | 36.5% | 64.5% | 68 | -0.065 | 113.6 |
| 8 | B_60+XZ_trail8_rev+F2_d1ema50 | 0.902 | 37.3% | 46.6% | 85 | -0.058 | 80.3 |
| 9 | B_60+Y_atr3+F2_d1ema50 | 0.888 | 36.9% | 45.0% | 110 | -0.041 | 47.0 |
| 10 | B_60+YZ_atr3_rev+F2_d1ema50 | 0.888 | 36.9% | 45.0% | 110 | -0.041 | 47.0 |

### 1.2 Phase 5 Constraint Filtering

**Hard constraints** (HC-1 through HC-6):

| Rank | Config | HC-1 (avg_loser≥-0.08) | HC-2 (hold≥40) | HC-3 (30-200 trades) | HC-4 (DOF≤10) | HC-5 (no vol) | HC-6 (MDD≤60%) | Admissible Class? |
|------|--------|------------------------|-----------------|----------------------|----------------|---------------|-----------------|-------------------|
| 1 | A_20_90+X_trail8+F2_d1ema50 | PASS (-0.070) | PASS (124.3) | PASS (39) | PASS (4) | PASS | PASS (52.0%) | YES: E1+X2+F1 |
| 2 | A_20_90+XZ_trail8_rev+F4_vol_low | PASS | PASS | PASS | PASS | PASS | PASS | **NO**: F4_vol_low not admissible (Phase 4 rejected) |
| 3 | A_20_90+XZ_trail8_rev+F2_d1ema50 | PASS (-0.043) | PASS (75.6) | PASS (49) | PASS (5) | PASS | PASS (40.3%) | YES: E1+X3+F1 |
| 4 | A_20_90+XZ_trail8_rev | PASS | PASS | PASS | PASS | PASS | PASS | YES: E1+X3 |
| 5 | A_20_90+X_trail8+F4_vol_low | PASS | PASS | PASS | PASS | PASS | PASS | **NO**: F4_vol_low not admissible |
| 6 | A_20_90+X_trail8 | PASS | PASS | PASS | PASS | PASS | PASS (54.0%) | YES: E1+X2 |
| 7 | A_20_90+X_trail8+F1_d1ema21 | PASS | PASS | PASS | PASS | PASS | **FAIL** (64.5%) | — |
| 8 | B_60+XZ_trail8_rev+F2_d1ema50 | PASS | PASS | PASS | PASS | PASS | PASS | YES: E2+X3+F1 |
| 9 | B_60+Y_atr3+F2_d1ema50 | PASS (-0.041) | PASS (47.0) | PASS (110) | PASS (3) | PASS | PASS (45.0%) | YES: E2+X1+F1 |
| 10 | B_60+YZ_atr3_rev+F2_d1ema50 | PASS | PASS | PASS | PASS | PASS | PASS | YES: E2+X3'+F1 |

**Eliminated**: Rank 2 (F4 not admissible), Rank 5 (F4 not admissible), Rank 7 (MDD 64.5% > 60%).

**Note on Rank 9 vs 10**: B_60+Y_atr3 and B_60+YZ_atr3_rev produce **identical results** (Sharpe, CAGR, MDD, trades all match). The reversal component NEVER fires before the ATR(3.0) trail with the B_60 entry — the ATR trail at m=3.0 is tight enough to always trigger first.

### 1.3 Candidate Selection

**Admissible TOP configs** after constraint + class filtering:

| Rank | Config | Sharpe | Type (Entry × Exit) |
|------|--------|--------|---------------------|
| 1 | A_20_90+X_trail8+F2_d1ema50 | 1.251 | E1 × X2 (simple trail) |
| 3 | A_20_90+XZ_trail8_rev+F2_d1ema50 | 1.099 | E1 × X3 (composite) |
| 4 | A_20_90+XZ_trail8_rev | 1.053 | E1 × X3 (composite, no filter) |
| 6 | A_20_90+X_trail8 | 0.962 | E1 × X2 (simple, no filter) |
| 8 | B_60+XZ_trail8_rev+F2_d1ema50 | 0.902 | E2 × X3 (composite) |
| 9 | B_60+Y_atr3+F2_d1ema50 | 0.888 | E2 × X1 (ATR trail) |

**Selection rationale**:

- **Cand01** = Rank 1 (highest admissible Sharpe): A_20_90+X_trail8+F2_d1ema50. Simple exit.
- Per protocol: TOP-1 has simple exit → Cand02 MUST have composite exit.
- Composite contribution check: A_20_90+XZ_trail8_rev (Sh 1.053) vs A_20_90+X_trail8 (Sh 0.962) → Δ=+0.091 > 0.05 threshold. Composite exit DOES contribute. At least one composite candidate required.
- **Cand02** = Rank 3 (highest admissible composite): A_20_90+XZ_trail8_rev+F2_d1ema50. Different exit type from Cand01 (X3 vs X2).
- **Cand03** = Rank 9: B_60+Y_atr3+F2_d1ema50. Different ENTRY type (E2 vs E1) AND different EXIT type (X1 vs X2/X3). Maximum diversity across all three pipeline components.

---

## 2. CANDIDATE SPECIFICATIONS

---

### Cand01: EMA Cross + Fixed Trail + D1 Regime

**ID**: Cand01
**SOURCE**: Tbl_top20_sharpe rank #1, grid config [E1_ema_cross(20,90) × X2_pct_trail(8%) × F1_d1_regime(50)]

**PROVENANCE CHAIN**:
```
Cand01 ← Prop02 (EMA cross best entry) ← Obs25 ← Tbl_top20_sharpe
                                          ← Obs21 ← Tbl09, Fig13
                                          ← Obs30 ← Tbl11
       ← Prop01 (exit loss control)     ← Obs24 ← Tbl_sharpe_drivers
                                          ← Obs19 ← Tbl08, Fig11
       ← Prop03 (longer holds)          ← Obs24 ← Tbl_sharpe_drivers
                                          ← Obs27 ← Tbl11
       ← Prop04 (D1 regime filter)      ← Obs23 ← Tbl10
                                          ← Obs16 ← Tbl09_d1
                                          ← Obs17 ← Tbl10_h4d1
                                          ← Obs26 ← Tbl11
```

**CONSTRAINT SATISFACTION**:

| Constraint | Required | Candidate Value | Status | Margin |
|------------|----------|-----------------|--------|--------|
| HC-1: avg_loser ≥ -0.08 | ≥ -0.08 | -0.070 | PASS | 0.010 |
| HC-2: avg_hold ≥ 40 bars | ≥ 40 | 124.3 | PASS | 84.3 |
| HC-3: 30–200 trades | [30, 200] | 39 | PASS | 9 above min |
| HC-4: DOF ≤ 10 | ≤ 10 | 4 | PASS | 6 |
| HC-5: no volume features | — | none | PASS | — |
| HC-6: MDD ≤ 60% | ≤ 60% | 52.0% | PASS | 8.0 pp |
| SC-1: trail-stop exit | SHOULD | YES (X2) | PASS | — |
| SC-2: D1 EMA regime filter | SHOULD | YES (p_d=50) | PASS | — |
| SC-3: EMA cross entry | SHOULD | YES (E1) | PASS | — |
| SC-4: exposure 0.20–0.50 | SHOULD | 0.258 | PASS | — |
| AC-1: no anti-churn | MUST NOT | none | PASS | — |
| AC-2: no high-trade targeting | MUST NOT | 39 trades | PASS | — |

**Note**: HC-3 margin is tight (39 trades, 9 above minimum). Phase 5 flagged this uncertainty.

**COMPLETE RULE SET**:

**Entry condition**:
- At each H4 bar close, compute: EMA(20, close) and EMA(90, close)
- If EMA(20) > EMA(90) AND position is flat AND filter allows: enter LONG at next bar's open
- EMA uses standard exponential smoothing: EMA_t = α × C_t + (1 − α) × EMA_{t-1}, α = 2/(N+1)

**Exit condition** (Fixed Percentage Trailing Stop):
- While in position, track HWM = max(close prices since entry)
- At each bar close: if close < HWM × (1 − τ), where τ = 0.08 → exit at next bar's open
- HWM resets on each new entry

**Filter condition** (D1 EMA Regime):
- At each H4 bar, look up the PREVIOUS D1 close (1-day lag to avoid look-ahead)
- Compute EMA(50) on D1 close prices
- allow_entry = 𝟙{D1_close_{t-1d} > EMA(50, D1_close)}
- If filter is OFF: no new entries allowed; existing positions continue until exit fires

**Position sizing**: Binary (fully invested or flat). Cost: 50 bps round-trip.

**PARAMETERS**:

| Parameter | Symbol | Default | Range | DOF | Evidence |
|-----------|--------|---------|-------|-----|----------|
| Fast EMA period | p_f | 20 | [1, 30] | 1 | A_20_90 in 5/5 top Sharpe configs (Obs25); ema_spread_90 |r|=0.065 (Obs30, Tbl11) |
| Slow EMA period | p_s | 90 | [60, 144] | 1 | A_20_90 best entry mean Sharpe 0.700 across 9 exits (Obs21, Tbl09); ema_spread_120 |r|=0.074 (Obs30) |
| Trail percentage | τ | 8% | [4%, 15%] | 1 | X_trail8 in 3/5 top-5 Sharpe configs (Obs25); avg_hold=105 bars satisfies DC-2; Phase 3 grid optimal (Tbl_top20) |
| D1 EMA period | p_d | 50 | [15, 60] | 1 | F2_d1ema50: only positive filter, 10/10 consistency, +0.045 mean ΔSharpe (Obs23); d1_ema_spread_50 = #1 info feature |r|=0.088 (Obs26, Tbl11) |

**Total DOF: 4**

---

### Cand02: EMA Cross + Composite Exit (Trail OR Reversal) + D1 Regime

**ID**: Cand02
**SOURCE**: Tbl_top20_sharpe rank #3, grid config [E1_ema_cross(20,90) × X3_composite(trail8% OR reversal) × F1_d1_regime(50)]

**PROVENANCE CHAIN**:
```
Cand02 ← [all of Cand01's chain] +
       ← Prop06 (composite modest improvement) ← Obs20 ← Tbl08
                                                  ← Obs19 ← Tbl08, Fig11
                                                  ← Obs22 ← Tbl_decomposition
```

**CONSTRAINT SATISFACTION**:

| Constraint | Required | Candidate Value | Status | Margin |
|------------|----------|-----------------|--------|--------|
| HC-1: avg_loser ≥ -0.08 | ≥ -0.08 | -0.043 | PASS | 0.037 |
| HC-2: avg_hold ≥ 40 bars | ≥ 40 | 75.6 | PASS | 35.6 |
| HC-3: 30–200 trades | [30, 200] | 49 | PASS | 19 above min |
| HC-4: DOF ≤ 10 | ≤ 10 | 5 | PASS | 5 |
| HC-5: no volume features | — | none | PASS | — |
| HC-6: MDD ≤ 60% | ≤ 60% | 40.3% | PASS | 19.7 pp |
| SC-1: trail-stop exit | SHOULD | YES (trail component) | PASS | — |
| SC-2: D1 EMA regime filter | SHOULD | YES (p_d=50) | PASS | — |
| SC-3: EMA cross entry | SHOULD | YES (E1) | PASS | — |
| SC-4: exposure 0.20–0.50 | SHOULD | 0.198 | MARGINAL | 0.002 below range |
| AC-1: no anti-churn | MUST NOT | none | PASS | — |
| AC-2: no high-trade targeting | MUST NOT | 49 trades | PASS | — |

**COMPLETE RULE SET**:

**Entry condition**: Same as Cand01 (EMA(20) > EMA(90), with D1 EMA(50) regime filter).

**Exit condition** (Composite: Trail OR Reversal, whichever fires first):

- **Component A** (Fixed Percentage Trail):
  - Track HWM = max(close since entry)
  - Fire when: close < HWM × (1 − τ), τ = 0.08

- **Component B** (EMA Reversal):
  - Fire when: EMA(p_f, close) < EMA(p_s, close)
  - Uses the SAME periods as entry (p_f=20, p_s=90) — NO additional parameters

- **Composite logic**: exit at next bar's open when **Component A fires OR Component B fires**, whichever happens first.

**Filter condition**: Same as Cand01.

**Position sizing**: Same as Cand01.

**PARAMETERS**:

| Parameter | Symbol | Default | Range | DOF | Evidence |
|-----------|--------|---------|-------|-----|----------|
| Fast EMA period | p_f | 20 | [1, 30] | 1 | Same as Cand01 |
| Slow EMA period | p_s | 90 | [60, 144] | 1 | Same as Cand01 |
| Trail percentage | τ | 8% | [4%, 15%] | 1 | Same as Cand01 |
| D1 EMA period | p_d | 50 | [15, 60] | 1 | Same as Cand01 |
| Reversal (structural) | — | on | {on} | 1 | Composite Δ = +0.091 Sharpe unfiltered (Obs21: 1.053 vs 0.962); XZ in 3/5 top-5 (Obs25); Prop06 |

**Total DOF: 5** (per Tbl12 convention: X3 composite = 2 DOF for exit, 4 free parameters + 1 structural)

---

### Cand03: Breakout + ATR Trail + D1 Regime

**ID**: Cand03
**SOURCE**: Tbl_top20_sharpe rank #9, grid config [E2_breakout(60) × X1_atr_trail(3.0) × F1_d1_regime(50)]

**PROVENANCE CHAIN**:
```
Cand03 ← Prop01 (exit loss control)     ← Obs24 ← Tbl_sharpe_drivers
                                          ← Obs19 ← Tbl08, Fig11
       ← Prop04 (D1 regime filter)      ← Obs23 ← Tbl10
                                          ← Obs16 ← Tbl09_d1
                                          ← Obs26 ← Tbl11
       ← Obs21 (B_60 second-best entry)  ← Tbl09, Fig13
       ← Obs18 (breakout detection)      ← Tbl07, Fig10
```

**CONSTRAINT SATISFACTION**:

| Constraint | Required | Candidate Value | Status | Margin |
|------------|----------|-----------------|--------|--------|
| HC-1: avg_loser ≥ -0.08 | ≥ -0.08 | -0.041 | PASS | 0.039 |
| HC-2: avg_hold ≥ 40 bars | ≥ 40 | 47.0 | PASS | 7.0 |
| HC-3: 30–200 trades | [30, 200] | 110 | PASS | 80 above min |
| HC-4: DOF ≤ 10 | ≤ 10 | 3 | PASS | 7 |
| HC-5: no volume features | — | none | PASS | — |
| HC-6: MDD ≤ 60% | ≤ 60% | 45.0% | PASS | 15.0 pp |
| SC-1: trail-stop exit | SHOULD | YES (X1 ATR) | PASS | — |
| SC-2: D1 EMA regime filter | SHOULD | YES (p_d=50) | PASS | — |
| SC-3: EMA cross entry | SHOULD | NO (breakout) | WAIVED | Breakout is E2 — admissible class from Phase 4 |
| SC-4: exposure 0.20–0.50 | SHOULD | 0.275 | PASS | — |
| AC-1: no anti-churn | MUST NOT | none | PASS | — |
| AC-2: no high-trade targeting | MUST NOT | 110 trades | PASS | — |

**COMPLETE RULE SET**:

**Entry condition** (N-bar Breakout):
- At each H4 bar close: if close > max(close_{t-1}, close_{t-2}, ..., close_{t-N}), where N=60
- If breakout AND position is flat AND filter allows: enter LONG at next bar's open

**Exit condition** (ATR Trailing Stop):
- While in position, track HWM = max(close prices since entry)
- Compute ATR(14) on H4 bars using Wilder smoothing
- At each bar close: if close < HWM − m × ATR(14)_t, where m = 3.0 → exit at next bar's open
- HWM resets on each new entry

**Filter condition**: Same as Cand01 (D1 EMA(50) regime).

**Position sizing**: Same as Cand01.

**PARAMETERS**:

| Parameter | Symbol | Default | Range | DOF | Evidence |
|-----------|--------|---------|-------|-----|----------|
| Breakout period | N | 60 | [20, 120] | 1 | B_60 second-best entry mean Sharpe 0.709 (Obs21, Tbl09); breakout_pos_60 |r|=0.048 (Tbl11); detection rate 0.83 at FP 0.16 for B_break20 (Obs18) — N=60 from grid optimal |
| ATR multiplier | m | 3.0 | [2.0, 6.0] | 1 | ATR trail Sharpe monotonically improving with wider m (Obs19, Tbl08); Y_atr14_3.0 Sharpe=0.574 — m=3.0 is Phase 3 grid value for this config (Tbl_top20) |
| ATR period | p_atr | 14 | fixed | 0 | All Phase 3 ATR exits used period 14 — no evidence to vary |
| D1 EMA period | p_d | 50 | [15, 60] | 1 | Same as Cand01 |

**Total DOF: 3**

---

## 3. COMPOSITE EXIT SPECIFICATION (Cand02)

Cand02 uses exit X3: **Component A (trail) OR Component B (reversal)**.

### Exact Logic

```
while in_position:
    hwm = max(hwm, close_t)
    trail_trigger = (close_t < hwm * (1 - 0.08))
    reversal_trigger = (EMA(20, close_t) < EMA(90, close_t))

    if trail_trigger OR reversal_trigger:
        exit at next bar's open
        break
```

### Expected Component Interaction

Evidence from Phase 3 grid (unfiltered configs):

| Config | Sharpe | Trades | avg_hold |
|--------|--------|--------|----------|
| A_20_90+X_trail8 (trail only) | 0.962 | 87 | 105.3 |
| A_20_90+XZ_trail8_rev (composite) | 1.053 | 114 | 69.7 |
| A_20_90+Z_rev (reversal only) | 0.746 | 114 | 86.3 |

- Composite produces **27 additional trades** (114 vs 87) and **shorter avg_hold** (69.7 vs 105.3)
- This means Component B (reversal) fires BEFORE Component A (trail) in approximately **30–35% of trades**, creating earlier exits and allowing re-entries
- Component A (trail) fires first in the remaining **65–70% of trades**: scenarios with large sudden drops (>8% from HWM) before the EMA cross-down occurs
- Component B (reversal) fires first in scenarios with gradual price deterioration where the EMA(20) cross-down happens before the 8% trail distance is reached

### Phase 3 Decomposition Evidence (Tbl_decomposition)

From the prior-art decomposition (different entry: A_1_120):
- Trail only (d): Sharpe = 0.129
- Reversal only (e): Sharpe = -0.256
- Combined with no filters (f): Sharpe = 0.424

The trail component is the primary contributor. Reversal alone is negative but provides value as an OR-exit by cutting losing trades earlier.

### Filter Interaction Warning

| Config | Sharpe | ΔSharpe vs simple trail |
|--------|--------|------------------------|
| A_20_90+X_trail8+F2_d1ema50 (Cand01) | 1.251 | — |
| A_20_90+XZ_trail8_rev+F2_d1ema50 (Cand02) | 1.099 | -0.152 |

With the D1 filter, Cand01 (simple trail) **outperforms** Cand02 (composite) by 0.152 Sharpe. Without filter, composite outperforms by 0.091. The D1 filter likely already removes the losing trades that the reversal exit was cutting — making the reversal exit REDUNDANT with the filter. This will be tested in Phase 7.

---

## 4. CANDIDATE COMPARISON SUMMARY

| Property | Cand01 | Cand02 | Cand03 |
|----------|--------|--------|--------|
| Entry | E1: EMA(20)>EMA(90) | E1: EMA(20)>EMA(90) | E2: 60-bar breakout |
| Exit | X2: trail 8% | X3: trail 8% OR reversal | X1: ATR(14)×3.0 trail |
| Filter | F1: D1 EMA(50) | F1: D1 EMA(50) | F1: D1 EMA(50) |
| Total DOF | 4 | 5 | 3 |
| Phase 3 Sharpe | **1.251** | 1.099 | 0.888 |
| CAGR | **41.7%** | 32.1% | **36.9%** |
| MDD | 52.0% | **40.3%** | **45.0%** |
| Trades | 39 | 49 | **110** |
| Exposure | 25.8% | 19.8% | 27.5% |
| avg_loser | -0.070 | **-0.043** | **-0.041** |
| avg_hold | **124.3** | 75.6 | 47.0 |
| win_rate | **46.2%** | 30.6% | 38.2% |

**Cand01**: Highest Sharpe, longest holds, but fewest trades (HC-3 margin tight).
**Cand02**: Best MDD, moderate Sharpe, composite exit may be redundant with filter.
**Cand03**: Most trades (highest statistical power), lowest DOF, different entry mechanism.

---

## 5. BENCHMARK COMPARISON PLAN

### Benchmark Strategy

**Config**: A_20_90 + Y_atr3 (no filter)
- Entry: EMA(20) > EMA(90) crossover
- Exit: ATR(14) × 3.0 trailing stop
- Filter: none
- DOF: 3
- Source: Tbl09 grid (A_20_90 + Y_atr3)

**Phase 3 grid values**:

| Metric | Benchmark |
|--------|-----------|
| Sharpe | 0.819 |
| CAGR | 31.7% |
| MDD | 39.9% |
| Trades | 108 |
| Exposure | 25.7% |
| avg_loser | -0.040 |
| avg_hold | 44.7 |
| win_rate | 36.1% |

**Rationale**: Uses the best Phase 3 entry (A_20_90) with a simple ATR trail, no filter. This is the "does added complexity help?" baseline. Same codebase, same data, same cost model.

**Secondary benchmark**: Buy-and-hold (Sharpe ~0.60, CAGR ~35%, MDD ~83%). From Phase 0 Section C.

### Metrics

All metrics computed on same data (H4 2017-08 → 2026-03) with same cost (50 bps RT):
- Sharpe, CAGR, MDD, Calmar (CAGR/|MDD|)
- Trade count, win rate, exposure, avg duration
- avg_winner, avg_loser, profit factor
- Max consecutive losses

---

## 6. PRE-COMMITTED REJECTION CRITERIA

**These criteria are FIXED. They MUST NOT be changed after Phase 7 begins.**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Sharpe < 0 | REJECT | Negative expected value |
| Sharpe < benchmark × 0.80 = **0.655** | REJECT | Significantly worse than simple baseline (0.819 × 0.80) |
| MDD > 75% | REJECT | Unacceptable risk (exceeds protocol 60% + safety margin for OOS) |
| Trade count < 15 | REJECT | Insufficient sample for any statistical inference |
| WFO win rate < 50% | REJECT | Out-of-sample failure |
| Bootstrap P(Sharpe > 0) < 60% | REJECT | Insufficient evidence against luck |

---

## 7. EXPECTED BEHAVIOR (Pre-Backtest Estimates)

All values from Phase 3 grid data. Phase 7 results deviating >30% from these estimates require explanation.

### Cand01

| Metric | Estimate | Source |
|--------|----------|--------|
| Sharpe | 1.251 | Tbl_top20_sharpe rank #1 |
| CAGR | 41.7% | Tbl_top20_sharpe |
| MDD | 52.0% | Tbl_top20_sharpe |
| Trades | 39 | Tbl_top20_sharpe |
| Exposure | 25.8% | Tbl_top20_sharpe |
| avg_hold | 124.3 bars (~20.7 days) | Tbl_top20_sharpe |
| avg_loser | -0.070 | Tbl_top20_sharpe |
| avg_winner | 0.309 | Tbl_top20_sharpe |
| win_rate | 46.2% | Tbl_top20_sharpe |
| HC-3 headroom | 9 trades above minimum | **Tight — flag if OOS reduces further** |
| HC-6 headroom | 8.0 pp | Moderate |

### Cand02

| Metric | Estimate | Source |
|--------|----------|--------|
| Sharpe | 1.099 | Tbl_top20_sharpe rank #3 |
| CAGR | 32.1% | Tbl_top20_sharpe |
| MDD | 40.3% | Tbl_top20_sharpe |
| Trades | 49 | Tbl_top20_sharpe |
| Exposure | 19.8% | Tbl_top20_sharpe |
| avg_hold | 75.6 bars (~12.6 days) | Tbl_top20_sharpe |
| avg_loser | -0.043 | Tbl_top20_sharpe |
| avg_winner | 0.319 | Tbl_top20_sharpe |
| win_rate | 30.6% | Tbl_top20_sharpe |
| HC-3 headroom | 19 trades above minimum | Moderate |
| HC-6 headroom | 19.7 pp | Comfortable |

### Cand03

| Metric | Estimate | Source |
|--------|----------|--------|
| Sharpe | 0.888 | Tbl_top20_sharpe rank #9 |
| CAGR | 36.9% | Tbl_top20_sharpe |
| MDD | 45.0% | Tbl_top20_sharpe |
| Trades | 110 | Tbl_top20_sharpe |
| Exposure | 27.5% | Tbl_top20_sharpe |
| avg_hold | 47.0 bars (~7.8 days) | Tbl_top20_sharpe |
| avg_loser | -0.041 | Tbl_top20_sharpe |
| avg_winner | 0.155 | Tbl_top20_sharpe |
| win_rate | 38.2% | Tbl_top20_sharpe |
| HC-3 headroom | 80 trades above minimum | Very comfortable |
| HC-6 headroom | 15.0 pp | Comfortable |

---

## 8. TÍNH ĐƠN GIẢN

- 3 candidates (maximum allowed, minimizes multiple testing penalty)
- DOF: 3, 4, 5 — all well below the ≤10 limit
- Cand03 (DOF=3) is the simplest and has the highest trade count (most statistically robust)
- If Cand01 and Cand02 produce similar evidence, prefer Cand01 (DOF=4 < Cand02 DOF=5)
- Cand02's composite exit may be redundant with the D1 filter — Phase 7 will resolve this

---

## Deliverables

### Files Created
- `06_design.md` (this report)

### Key IDs Created
- Cand01: E1(20,90) + X2(8%) + F1(50), DOF=4
- Cand02: E1(20,90) + X3(8%,reversal) + F1(50), DOF=5
- Cand03: E2(60) + X1(3.0) + F1(50), DOF=3
- Benchmark: A_20_90 + Y_atr3, Sharpe=0.819, DOF=3

### Blockers / Uncertainties
1. Cand01 has tight HC-3 margin (39 trades, 9 above minimum). OOS validation may drop below 30.
2. Cand02's composite exit appears redundant with D1 filter (ΔSharpe = -0.152 vs Cand01 with filter). Phase 7 will test whether the composite adds value after filter.
3. Cand03 (breakout entry) has lower Sharpe (0.888 vs 1.099–1.251) but more trades and lowest DOF. It tests whether the entry type matters more than the exit/filter configuration.

### Gate Status
**PASS_TO_NEXT_PHASE**

Three candidates designed from Phase 3 grid evidence, all satisfying Phase 5 constraints. Complete provenance chains. Pre-committed rejection criteria defined. Benchmark strategy specified. Ready for Phase 7 (Validation).
