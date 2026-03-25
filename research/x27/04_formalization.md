# Phase 4: Formalization

**Study**: X27
**Date**: 2026-03-11
**Data**: BTCUSDT H4 (18,752 bars) + D1, 2017-08 to 2026-03
**Code**: `code/phase4_information.py`

---

## 1. PHENOMENON SUMMARY

The strongest phenomena from Phase 2–3, ranked by exploitability:

### CHẮC CHẮN EXPLOITABLE

| ID | Phenomenon | Effect Size | Significance | Stability |
|----|-----------|------------|-------------|-----------|
| Obs14 | Volatility clustering: |return| ACF 100/100 lags significant, lag1=0.261, lag50=0.468 | Large | p ≈ 0 | Rolling stable |
| Obs42 | Breakout entry (Type B) dominates detection: det=0.839, lag=19 bars | 0.839 detection rate | N/A (descriptive) | det_std=0.123 across blocks |
| Obs49+51 | ATR trail exit (Type Y) produces best risk-adjusted pairing: B+Y Sharpe 1.064 | 0.45 Sharpe above worst | N/A (descriptive) | Consistent across entry types |
| Obs37 | D1 SMA200 regime: above +114.8% ann, below -52.9% ann | Δ = 167.7 pp | p = 0.0004 (Welch), p = 0.0002 (MW) | Directionally stable |

### CÓ THỂ EXPLOITABLE

| ID | Phenomenon | Effect Size | Significance | Stability |
|----|-----------|------------|-------------|-----------|
| Obs26+36 | Trends 12:1 concentrated in high-vol periods | 12:1 ratio | Qualitative (N=13 trends) | Small sample |
| Obs21 | Pre-trend momentum: +9.16% mean cum-return 20 bars before trend start | 9.16% | Qualitative (N=13) | Not tested per-block |
| Obs22 | Post-peak gradual decay: +4.96% after peak (not sharp reversal) | 4.96% | Qualitative (N=13) | Not tested per-block |
| Obs43 | ROC entry (Type C) has lowest lag (15.2 bars) and best stability (std=0.082) | 15.2 bars lag | N/A (descriptive) | Most stable of 4 types |
| Obs39 | Low-vol regime shows mild VR persistence (VR>1), high-vol shows mean-reversion | VR range 0.91–1.05 | Not significant | Regime-dependent |

### KHÔNG EXPLOITABLE

| ID | Phenomenon | Reason |
|----|-----------|--------|
| Obs16+19 | No significant return persistence at any H4 scale (VR test all p > 0.95) | Zero signal |
| Obs30 | TBR→return: max |r| = 0.027, economically negligible | Zero signal |
| Obs28 | Volume→|return| leading: significant only 1–6 bars, driven by vol clustering | Not directional |
| Obs27 | Volume non-stationary (structural shift 2022→2024) | Non-stationary = unreliable |

---

## 2. DECISION PROBLEM

### Formal Definition

**State space** S_t = (P_t, V_t, R_t) where:
- P_t: price-derived observables at bar t — close, high, low, N-bar max, ROC, EMA spread
- V_t: volatility observables — realized vol, ATR, vol regime indicator
- R_t: D1 regime observable — close vs D1 MA (lagged 1 day)
- Volume-based information is EXCLUDED from S_t (Obs30: zero directional signal)

**Action space** A = {ENTER_LONG, EXIT, HOLD_FLAT, HOLD_POSITION}

**Transition** P(S_{t+1} | S_t, A_t):
- Returns are approximately uncorrelated (VR ≈ 1, no significant persistence — Obs16)
- |Returns| are strongly autocorrelated (volatility clustering — Obs14)
- Regime transitions (D1 SMA200) are slow (trend in price level)
- Action does not affect transition (price-taker assumption)

**Reward** R(S_t, A_t):
- R_t = position_t × r_{t+1} - cost × |Δposition_t|
- cost = 25 bps per side = 50 bps round-trip
- position ∈ {0, 1} (binary: flat or fully invested)

**Objective**: Maximize Sharpe ratio of Σ R_t (risk-adjusted cumulative reward)

**Key structural constraints from data**:
1. Trade frequency is low (28 target events in 8.5 years = 3.3/yr at 10% threshold)
2. ALL entry mechanisms have >87% false positive rate (Obs41–44)
3. ALL exit mechanisms have >80% churn rate (Obs46–50)
4. The strategy profit comes from capturing rare, large moves — not from frequent accurate prediction

This is a **rare-event capture** problem, not a **frequent-prediction** problem. The decision framework must emphasize:
- Participating in large moves (high detection rate)
- Controlling cost from false entries and churn exits
- NOT precision of individual trade prediction

---

## 3. INFORMATION SETS — WHAT IS OBSERVABLE AND USEFUL?

Mutual information and Spearman rank correlation between features and forward H4 returns at multiple horizons, computed on full sample (N ≈ 18,700). See Tbl11 for complete results.

### Information Ranking at k=20 (Tbl11)

| Rank | Feature | Category | ρ (Spearman) | p-value | MI (binned) |
|------|---------|----------|-------------|---------|------------|
| 1 | ema_spread_120 | price | +0.0479 | <0.001 | 0.02649 |
| 2 | roc_120 | price | +0.0476 | <0.001 | 0.02226 |
| 3 | d1_above_ema21 | d1_regime | +0.0462 | <0.001 | — (binary) |
| 4 | ema_spread_80 | price | +0.0411 | <0.001 | 0.02434 |
| 5 | roc_60 | price | +0.0352 | <0.001 | 0.02375 |
| 6 | breakout_120 | price | +0.0346 | <0.001 | — (binary) |
| 7 | breakout_40 | price | +0.0338 | <0.001 | — (binary) |
| 8 | atr_pctl | volatility | +0.0330 | <0.001 | 0.00758 |
| 9 | ema_spread_50 | price | +0.0326 | <0.001 | 0.02431 |
| 10 | vol60 | volatility | +0.0307 | <0.001 | 0.05255 |
| ... | ... | ... | ... | ... | ... |
| 18 | log_vol | volume | +0.0109 | 0.138 | 0.00854 |
| 19 | roc_20 | price | +0.0108 | 0.139 | 0.02470 |
| 20 | d1_above_sma200 | d1_regime | +0.0084 | 0.250 | — (binary) |

### Category Summary (average |ρ| across all horizons)

| Category | Avg |ρ| | Max |ρ| | N significant | N total |
|----------|---------|---------|---------------|---------|
| price | 0.0268 | 0.0709 | 53/72 | 72 |
| d1_regime | 0.0268 | 0.0560 | 7/12 | 12 |
| volatility | 0.0261 | 0.0569 | 21/24 | 24 |
| volume | 0.0122 | 0.0253 | 4/12 | 12 |

### Key Findings

**Obs57**: ALL individual features have |ρ| < 0.05 with 20-bar forward returns. The information content of ANY single observable is extremely low. This is consistent with the near-random-walk finding from Phase 2 (Obs16, Obs19). No single feature provides economically meaningful prediction of future returns.

**Obs58**: Price-based features (momentum, breakout) and D1 regime carry equal aggregate information (avg |ρ| ≈ 0.027). Volatility features are nearly tied (0.026). Volume is definitively the least informative category (0.012), confirming Obs30.

**Obs59**: D1 EMA(21) has much higher information content than D1 SMA(200) at k=20 horizon (ρ = 0.046 vs 0.008). The shorter-period regime indicator captures more relevant conditioning than the longer one. This is consistent with the EMA(21) being a more responsive regime detector.

**Obs60**: Longer-lookback momentum features dominate shorter ones: roc_120 (ρ=0.048) > roc_60 (ρ=0.035) > roc_40 (ρ=0.019) > roc_20 (ρ=0.011) > roc_10 (ρ=0.015). The information in price momentum is concentrated at 60–120 bar horizons.

**Implication for strategy design**: Since no single feature has meaningful predictive power (max |ρ| < 0.05), the strategy must NOT rely on prediction accuracy. Instead, it must rely on **asymmetric payoff structure**: participate in large moves (right tail) while limiting losses from false signals. This confirms the rare-event capture framing from Section 2.

---

## 4. ADMISSIBLE FUNCTION CLASSES — ENTRY

Derived from the Phase 3 signal efficiency frontier (Fig10, Tbl07).

### Class E1: Breakout

**Formula**: signal_t = 𝟏{close_t > max(high_{t-1}, ..., high_{t-N})}

**DOF**: 1 (N = lookback period)

**Evidence**:
- Obs42: Detection rate 0.839 (highest of all types)
- Obs51: Produces best Sharpe across ALL exit types (B column dominates in heatmap)
- Obs56: Simplest entry (1 DOF) yet best performance
- Fig10: Forms dominant cluster on signal efficiency frontier
- Tbl07_entry_detail: Stable across N ∈ {20, 40, 60, 80, 120, 160} — detection 0.82–0.89

**Mechanism**: Detects price making new highs — the most direct observation of an upward move in progress. Does not attempt to PREDICT; instead DETECTS and PARTICIPATES.

**Parameter range**: N ∈ [20, 160] (evidence-supported from sweep)

### Class E2: Rate-of-Change Threshold

**Formula**: signal_t = 𝟏{(close_t / close_{t-N} - 1) > τ}

**DOF**: 2 (N = lookback, τ = threshold)

**Evidence**:
- Obs43: Lowest average lag (15.2 bars) — fastest detection
- Obs45: Most stable across time blocks (det_std = 0.082)
- Obs60: roc_120 has highest rank-correlation with future returns (ρ = 0.048)
- Tbl07_entry_detail: Best individual combos achieve 75% detection (N10_t5)

**Mechanism**: Detects abnormally fast price acceleration. More selective than breakout — filters slow trends but catches fast-developing ones earlier.

**Parameter range**: N ∈ [10, 60], τ ∈ [5%, 20%]

### REJECTED Entry Classes

| Class | Reason | Evidence |
|-------|--------|----------|
| A (EMA crossover) | Detection rate 10.5%, lag 53 bars — too slow for H4 trend durations (median 14 bars). DOMINATED on frontier. | Obs41, Fig10 |
| D (Vol breakout) | Intermediate on all metrics: det 0.565, lag 20, FP 0.922. No frontier advantage over B or C. Least stable (det_std=0.156). | Obs44, Obs45, Fig10 |

---

## 5. ADMISSIBLE FUNCTION CLASSES — EXIT

Derived from Phase 3 exit efficiency frontiers (Fig11, Fig12, Tbl08).

### Class X1: ATR Trailing Stop

**Formula**: trail_t = max(close_{t-H:t}) - m × ATR(p)_t; exit when close_t < trail_t

**DOF**: 2 (p = ATR period, m = multiplier)

**Evidence**:
- Obs49: cap=0.90, churn=0.91, hold=59 bars — best balance of capture and holding period
- Obs51: Produces highest Sharpe across ALL entry types (Y column dominates)
- Tbl08_exit_detail: Wide multiplier range (2.0–5.0) all produce positive results; stable
- Fig12: Occupies low-capture-low-MDD frontier endpoint (best risk-adjusted)

**Mechanism**: Adaptive stop that widens in high volatility, tightens in low volatility. Allows trends to "breathe" while protecting against large reversals.

**Parameter range**: p ∈ [14, 30], m ∈ [2.0, 5.0]

### Class X2: Time-Based Exit

**Formula**: exit at bar t + H after entry

**DOF**: 1 (H = holding period)

**Evidence**:
- Obs47: cap=1.90, churn=0.857 — **lowest churn** of all exit types
- Tbl08_exit_detail: Monotonic capture increase with H (hold20: 0.82 → hold200: 2.83)
- Tbl09: B+W Sharpe 0.740, 47 trades — viable but lower than B+Y

**Mechanism**: Pure time-based exit eliminates noise-induced exits entirely. Trade-off: cannot adapt to adverse price moves — holds through drawdowns.

**Parameter range**: H ∈ [20, 200] bars

### REJECTED Exit Classes

| Class | Reason | Evidence |
|-------|--------|----------|
| X (Fixed % trail) | Highest churn (0.940) of all types. The fixed-percentage approach doesn't adapt to volatility regime. | Obs48, Fig11 |
| V (Volatility-based) | Highest MDD (24.2%), longest hold (209 bars), exposure 80–88%. Capital lock-in without risk-adjusted benefit. | Obs46, Fig12 |
| Z (Signal reversal) | Intermediate on all metrics. No frontier advantage. Introduces coupling between entry and exit mechanisms. | Obs50, Tbl09 |

---

## 6. ADMISSIBLE FUNCTION CLASSES — FILTER / REGIME

### Class F1: D1 Price-Level Regime

**Formula**: filter_t = 𝟏{D1_close_{t-1} > MA_D1(K)_{t-1}} (lagged 1 day)

**DOF**: 1 (K = MA period)

**Evidence**:
- Obs37: D1 SMA200 regime produces significant return differential (p = 0.0004). Above: +114.8% ann, Below: -52.9% ann.
- Obs59: D1 EMA(21) has higher information content than SMA(200) (ρ = 0.046 vs 0.008)
- Obs52: Regime filter reduces MDD by 16 pp on average across all pairs. BUT hurts average Sharpe by -0.077.

**Regime filter is a TRADEOFF, not a strict improvement:**
- It improves Sharpe for 5/20 pairs (25%) — notably B+W: +0.234 Sharpe
- It reduces MDD for most pairs (avg -16 pp)
- It halves trade count and exposure

**Decision**: Include F1 as an admissible class because:
1. The return differential is statistically significant (p = 0.0004)
2. MDD reduction is consistent and large
3. Whether to use it depends on the risk preference of the final design — this is a design choice, not a formalization rejection

**Parameter range**: K ∈ [21, 200] (evidence: EMA21 has most information, SMA200 has strongest return differential)

### "No Filter" is Also Admissible

The regime filter is NOT universally beneficial (Obs52). For return-maximizing objectives, no filter may be optimal. Both {F1} and {no filter} are admissible.

---

## 7. TOTAL DOF BUDGET

### Component DOF (Tbl12)

| Component | Formula | DOF | Parameters |
|-----------|---------|-----|------------|
| Entry E1 (Breakout) | close > max(high, N bars) | 1 | N |
| Entry E2 (ROC) | ROC(N) > τ | 2 | N, τ |
| Exit X1 (ATR trail) | trail = max - m×ATR(p) | 2 | p, m |
| Exit X2 (Time-based) | exit after H bars | 1 | H |
| Filter F1 (Regime) | D1 close > MA(K) | 1 | K |
| Filter F0 (None) | — | 0 | — |

### Combination DOF (Tbl12)

| Combination | DOF | Budget Check |
|-------------|-----|-------------|
| E1 + X1 (B+Y) | 1+2 = **3** | ✓ ≤ 10 |
| E1 + X1 + F1 (B+Y+regime) | 1+2+1 = **4** | ✓ ≤ 10 |
| E1 + X2 (B+W) | 1+1 = **2** | ✓ ≤ 10 |
| E1 + X2 + F1 (B+W+regime) | 1+1+1 = **3** | ✓ ≤ 10 |
| E2 + X1 (C+Y) | 2+2 = **4** | ✓ ≤ 10 |
| E2 + X1 + F1 (C+Y+regime) | 2+2+1 = **5** | ✓ ≤ 10 |
| E2 + X2 (C+W) | 2+1 = **3** | ✓ ≤ 10 |
| E2 + X2 + F1 (C+W+regime) | 2+1+1 = **4** | ✓ ≤ 10 |

All 8 combinations are within the ≤ 10 DOF budget. Maximum DOF = 5 (C+Y+regime).

---

## 8. POWER ANALYSIS (Tbl13)

Minimum Detectable Effect (MDE) for Sharpe ratio at 80% power, α = 0.05:
MDE = (z_{0.975} + z_{0.80}) / √N = 2.80 / √N

| Entry | Exit | Filter | DOF | N trades | MDE (Sharpe) | Observed Sharpe | Obs/MDE | Verdict |
|-------|------|--------|-----|----------|-------------|----------------|---------|---------|
| B (Breakout) | Y (ATR trail) | none | 3 | 50 | 0.396 | 1.064 | 2.69 | **POWERED** |
| B (Breakout) | W (Time) | none | 2 | 47 | 0.409 | 0.740 | 1.81 | **POWERED** |
| B (Breakout) | Z (Sig rev) | none | 3 | 35 | 0.474 | 0.886 | 1.87 | **POWERED** |
| C (ROC) | Y (ATR trail) | none | 4 | 105 | 0.273 | 0.833 | 3.05 | **POWERED** |
| C (ROC) | W (Time) | none | 3 | 72 | 0.330 | 0.394 | 1.19 | BORDERLINE |
| C (ROC) | Z (Sig rev) | none | 4 | 69 | 0.337 | 0.726 | 2.15 | **POWERED** |
| B (Breakout) | Y (ATR trail) | SMA200 | 4 | 32 | 0.495 | 0.873 | 1.76 | **POWERED** |
| B (Breakout) | W (Time) | SMA200 | 3 | 31 | 0.503 | 0.975 | 1.94 | **POWERED** |
| C (ROC) | Y (ATR trail) | SMA200 | 5 | 55 | 0.378 | 0.571 | 1.51 | **POWERED** |
| C (ROC) | W (Time) | SMA200 | 4 | 40 | 0.443 | 0.574 | 1.30 | BORDERLINE |

**Summary**: 8/10 combinations are POWERED, 2/10 are BORDERLINE. Zero are UNDERPOWERED. The C+W combinations are borderline because ROC's selectivity (lower detection rate) combined with time-based exit produces moderate Sharpe that barely exceeds MDE.

**No blockers from power analysis.** The strongest combination (B+Y, Sharpe 1.064, Obs/MDE = 2.69) has substantial margin above MDE.

---

## 9. PROPOSITIONS

Each proposition is derived from the evidence chain: Obs## → analysis → Prop##.

### Prop01: THE PROFITABLE MECHANISM IS RARE-EVENT CAPTURE, NOT PREDICTION

**Confidence**: HIGH

**Evidence chain**:
- Obs16, Obs19: No significant return persistence at any H4 scale (VR test)
- Obs57: All features have |ρ| < 0.05 with future returns — near-zero predictability
- Obs20: Only 13 moves ≥20% in 8.5 years (1.5/yr)
- Obs42: Best entry detection rate is 84% for ≥10% moves, but with 87% false positive rate

**Statement**: BTC H4 returns are approximately unpredictable at the individual-bar level. The profitable mechanism is NOT predicting direction, but PARTICIPATING in rare large moves while controlling costs from inevitable false signals. The decision framework must optimize the participation/cost ratio, not prediction accuracy.

### Prop02: BREAKOUT IS THE DOMINANT ENTRY CLASS

**Confidence**: HIGH

**Evidence chain**:
- Obs42: Detection rate 0.839 — 2× higher than next-best (D: 0.565)
- Obs51: B row dominates all other entry types across ALL exit pairings
- Obs56: 1-DOF entry outperforms 2-DOF entries — complexity adds no value
- Fig10: B forms dominant frontier cluster

**Statement**: The breakout function class f(t) = 𝟏{close_t > max(high, N bars)} is the admissible entry class with strongest evidence. It directly detects the phenomenon being exploited (price making new highs during upward moves) without attempting prediction.

### Prop03: ATR TRAILING STOP IS THE DOMINANT EXIT CLASS

**Confidence**: HIGH

**Evidence chain**:
- Obs49: Best exit capture/risk tradeoff (cap=0.90, MDD=14.8%)
- Obs51: Y column dominates all other exit types in Sharpe heatmap
- Obs14: Volatility clustering → adaptive trailing (ATR) naturally matches regime
- Fig12: Y occupies optimal frontier endpoint for risk-adjusted exit

**Statement**: The ATR trailing stop class trail_t = max_price - m × ATR(p) is the admissible exit class with strongest evidence. Its volatility-adaptive nature is uniquely suited to BTC's extreme volatility clustering (Obs14).

### Prop04: CHURN IS STRUCTURAL AND UNRESOLVABLE AT THE EXIT LEVEL

**Confidence**: HIGH

**Evidence chain**:
- Obs46–50: ALL 5 exit types have churn > 80% (range 83–94%)
- Obs54: 0/68 parameter combinations achieve churn < 10% with capture > 60%
- Obs22: Post-peak gradual decay (+4.96% after peak) — price recovers after most exits

**Statement**: Exit churn is a structural property of BTC price dynamics, not a mechanism deficiency. No exit function class can simultaneously achieve high capture and low churn. Strategies must BUDGET for churn cost rather than attempt to eliminate it.

### Prop05: D1 REGIME FILTER IS A MDD/SHARPE TRADEOFF, NOT A STRICT IMPROVEMENT

**Confidence**: HIGH

**Evidence chain**:
- Obs37: D1 SMA200 conditioning is statistically significant (p = 0.0004)
- Obs52: Regime filter HURTS average Sharpe (-0.077) but improves MDD (-16 pp)
- Obs59: D1 EMA(21) has higher information content than SMA(200) at k=20

**Statement**: The D1 price-level regime is a statistically significant conditioning variable that trades return for drawdown reduction. Its use is a design-level risk preference choice, not an evidence-driven mandate. Both {with filter} and {without filter} are admissible. If used, EMA(21) is preferred over SMA(200) based on information content.

### Prop06: VOLUME INFORMATION IS ZERO — EXCLUDE FROM STATE SPACE

**Confidence**: HIGH

**Evidence chain**:
- Obs30: TBR→return max |r| = 0.027, not significant at short horizons
- Obs58: Volume category avg |ρ| = 0.012, definitively lowest
- Obs27: Volume non-stationary (structural shift 2022→2024)

**Statement**: Volume and taker-buy-ratio carry no exploitable directional information at any horizon. They must be excluded from the decision state space.

### Prop07: LONG-LOOKBACK MOMENTUM DOMINATES SHORT-LOOKBACK

**Confidence**: MEDIUM

**Evidence chain**:
- Obs60: roc_120 (ρ=0.048) > roc_60 (0.035) > roc_40 (0.019) > roc_20 (0.011)
- Tbl07_entry_detail: Breakout N=120–160 achieves 82% detection with lower FP than N=20
- Obs20: Trend durations are highly variable (Q25=9, Q75=59 bars for ≥10%)

**Statement**: Information for trend participation is concentrated at 60–120 bar lookback horizons. Short lookbacks (<20 bars) add noise without improving detection.

### Prop08: THE BEST STRATEGY WILL HAVE LOW EXPOSURE (≤40%)

**Confidence**: MEDIUM

**Evidence chain**:
- Obs51: Best pair B+Y has 30.1% exposure — lowest of all 20 pairs
- Obs55: Low exposure correlates with high Sharpe across the pairing landscape
- Obs20: Only 3.3 target events per year — natural ceiling on useful exposure

**Statement**: The optimal strategy will spend most time flat. High exposure (>60%) indicates over-trading or holding through non-trend periods, which dilutes risk-adjusted returns without capturing additional alpha.

---

## Observation Registry (Phase 4)

| ID | Description | Evidence |
|----|-------------|----------|
| Obs57 | All features |ρ| < 0.05 with fwd returns. Near-zero individual predictability. | Tbl11 |
| Obs58 | Category ranking: price ≈ d1_regime > volatility >> volume | Tbl11 |
| Obs59 | D1 EMA(21) ρ=0.046 >> D1 SMA(200) ρ=0.008. Shorter regime more informative. | Tbl11 |
| Obs60 | Momentum info concentrated at 60–120 bar lookback (roc_120 ρ=0.048 best) | Tbl11 |

---

## End-of-Phase Checklist

### 1. Files created
- `04_formalization.md` (this report)
- `code/phase4_information.py`
- `tables/Tbl11_information_ranking.csv`
- `tables/Tbl12_dof_budget.csv`
- `tables/Tbl12_dof_combinations.csv`
- `tables/Tbl13_power_analysis.csv`

### 2. Key Obs / Prop IDs created
- Obs57–Obs60 (4 observations)
- Prop01–Prop08 (8 propositions)

### 3. Blockers / uncertainties
- **Low individual feature information**: All |ρ| < 0.05. Strategy cannot rely on prediction. This is not a blocker — it confirms the rare-event capture framing (Prop01) — but it means any strategy's edge is inherently thin and depends on cost control.
- **Regime filter ambiguity**: D1 regime is statistically significant but hurts average Sharpe. The decision to include it is a risk-preference choice that cannot be resolved at the formalization level — it must be tested at design/validation level.
- **Borderline power for C+W combinations**: 2/10 combinations are borderline. C+W (ROC entry + time exit) may not have sufficient statistical power to distinguish from noise. If selected, validation must account for this.
- **Temporal clustering**: Block 3 (2021-11 to 2024-01) has zero target events. All signal landscape measurements are dominated by bull/recovery markets. Bear-market behavior is unmeasured.

### 4. Gate status
**PASS_TO_NEXT_PHASE**

Formalization is complete:
1. **2 admissible entry classes** (Breakout, ROC) with clear evidence ranking (Breakout dominant)
2. **2 admissible exit classes** (ATR trail, Time-based) with clear evidence ranking (ATR trail dominant)
3. **1 admissible filter class** (D1 price-level regime) + "no filter" both admissible
4. **All 8 combinations within DOF budget** (max 5 DOF)
5. **8/10 combinations POWERED**, 0 UNDERPOWERED
6. **8 propositions** with full provenance chains

Ready for Phase 5 (Go/No-Go Decision).
