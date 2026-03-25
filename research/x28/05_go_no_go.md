# Phase 5 — GO / NO-GO Decision

**Data**: BTCUSDT H4 (18,752 bars, 2017-08 → 2026-03) + D1 context (3,128 bars)
**Input**: Phase 2 (02_price_behavior_eda.md), Phase 3 (03_signal_landscape_eda.md), Phase 4 (04_formalization.md)
**Protocol**: Quantitative evidence-based decision only.

---

## 1. EVIDENCE FOR DESIGN

| # | Finding | Obs/Prop | Effect Size | Significance |
|---|---------|----------|-------------|--------------|
| 1 | avg_loser is dominant Sharpe predictor (partial R²=0.306) | Obs24, Prop01 | \|β·σ\|=0.709 | p < 1e-7 |
| 2 | Grid best Sharpe = 1.251 (A_20_90+X_trail8+F2_d1ema50) | Obs21, Tbl_top20 | Sharpe 1.251 | In-sample, 39 trades |
| 3 | All 12 admissible combinations POWERED (Obs/MDE = 1.98–4.02) | Tbl13 | Weakest ratio 1.98× | α=0.05, 80% power |
| 4 | D1 EMA regime: H4 Sharpe 1.25 vs -0.27 conditional on D1 | Obs16/17, Prop04 | 661 pp/yr (D1), ΔSharpe=1.52 (H4\|D1) | Welch p=0.036 |
| 5 | D1 EMA(50) filter: only consistently positive filter (+0.045 mean, 10/10) | Obs23 | +0.045 Sharpe | 10/10 consistency |
| 6 | Dual-EMA cross entry in ALL 5/5 top Sharpe configs | Obs25, Prop02 | Mean Sharpe 1.098 (top-5) | 5/5 presence |
| 7 | ATR trail exits monotonically improve with wider multiplier (3→5) | Obs19, Prop01 | Y_atr14_5.0 Sharpe 0.681 (best single exit) | Monotonic pattern |
| 8 | avg_hold second Sharpe predictor; info concentrates at longer horizons | Obs24/27, Prop03 | \|β·σ\|=0.394, mean \|r\| increases k=1→60 | p=1.1e-4 |
| 9 | OLS regression explains 56% of Sharpe variance with 6 trade properties | Obs24 | R²=0.557 | F-stat p < 1e-12 |
| 10 | d1_ema_spread_50 is #1 information feature (\|r\|=0.088) | Obs26 | \|r\|=0.088 at k=60 | p=3.6e-33 |

---

## 2. EVIDENCE AGAINST DESIGN

| # | Finding | Obs/Prop | Effect Size | Implication |
|---|---------|----------|-------------|-------------|
| 1 | VR test: 0/9 horizons reject random walk (heteroskedasticity-robust) | Obs07 | All \|z*\| < 0.03 | Raw returns near-random; predictability is subtle |
| 2 | ACF(returns) lag 1 = -0.044, weak serial dependence | Obs04 | Max \|ACF\| = 0.074 | Return predictability not in linear autocorrelation |
| 3 | Best-known prior art config yields Sharpe = -0.424 in this implementation | Obs22 | ΔSharpe = -1.50 vs prior codebase | Strategies are implementation-sensitive; cross-codebase portability is poor |
| 4 | Volume features carry zero predictive info (VDO, TBR, log_volume) | Obs15/28, Prop05 | MI=0.006 bits, \|r\|<0.03 | One entire feature category eliminated |
| 5 | Composite exits modestly better but NOT uniformly (mean Sh 0.351 vs 0.276) | Obs20, Prop06 | +0.075 mean Sharpe | Extra DOF may not be justified |
| 6 | Information \|r\| values are small in absolute terms (max 0.088) | Obs26/Tbl11 | \|r\| range 0.015–0.088 | Predictive signal exists but is weak per-bar |
| 7 | Hurst 0.583 NOT robust to heteroskedasticity correction | Obs08 | VR test null | Mild persistence may be volatility artifact |

**Required checks**:

- **TOP-N vs prior art Sharpe 1.08**: Phase 3 grid best = 1.251, unfiltered best = 1.053. **Both EXCEED** prior art reference of 1.08. However, direct comparison is imperfect (different codebases — Obs22). Within THIS implementation, the signal landscape produces Sharpe > 1.0 in multiple independent configs.

- **Regression predicts Sharpe?**: YES. R² = 0.557 (Obs24). avg_loser and avg_hold are actionable predictors. This is NOT an R²≈0 situation.

- **Decomposition shows prior art near-optimal?**: NO. The decomposition (Obs22) shows the prior art config is NON-FUNCTIONAL in this codebase (Sharpe = -0.424). The no-filter variant (Sharpe = 0.424) is the starting point. Phase 3 grid found configs reaching 1.251 — substantial headroom above the decomposition baseline.

---

## 3. DETECTABILITY ASSESSMENT

**Strongest phenomenon**: D1 EMA regime differential.
- Effect size: 661 pp/yr at D1 level (Obs16), H4|D1 Sharpe differential 1.52 (Obs17)
- Power: Welch p = 0.036, MW p = 0.098 at H4|D1 level; p < 0.0001 at D1 level
- Stability: all three D1 MAs (EMA21, EMA50, SMA200) significant at D1 level; EMA21 and EMA50 significant at H4|D1 level

**Second phenomenon**: Trail-stop loss control → Sharpe.
- Effect size: avg_loser partial R² = 0.306 (Obs24)
- Power: p < 1e-7 in regression
- Stability: monotonic pattern across 5 ATR multipliers (Obs19), consistent across all 5 entry types

**Third phenomenon**: EMA spread information at longer horizons.
- Effect size: |r| = 0.074–0.088 at k=60 (Obs26/30)
- Power: p < 1e-22
- Stability: monotonic horizon effect (Obs27), consistent across EMA periods 50–120

**Conclusion**: **CÓ ĐỦ signal — YES.**

Three independent phenomena are statistically significant, stable, and have clear exploitation mechanisms. The per-bar predictability is weak (|r| < 0.10) — this is expected for a financial time series. But the cumulative effect over multi-week holding periods (avg_hold ~100 bars = 17 days) is substantial, as evidenced by grid Sharpe up to 1.251.

---

## 4. IMPROVEMENT POTENTIAL

### a. Best combination from Phase 3 grid

| Config | Sharpe | CAGR | MDD | Trades |
|--------|--------|------|-----|--------|
| A_20_90 + X_trail8 + F2_d1ema50 | **1.251** | 41.7% | 52.0% | 39 |
| A_20_90 + XZ_trail8_rev + F4_vol_low | **1.128** | 31.2% | 34.5% | 57 |
| A_20_90 + XZ_trail8_rev + F2_d1ema50 | **1.099** | 32.1% | 40.3% | 49 |
| A_20_90 + XZ_trail8_rev (no filter) | **1.053** | 45.4% | 48.9% | 114 |

Best Phase 3 Sharpe = **1.251**.

### b. Prior art best known

Sharpe = **1.08** (EMA cross + dual exit + VDO + D1 EMA21, 50 bps RT, different codebase).

### c. Theoretical ceiling (from information analysis)

Upper bound on Sharpe from information content: the best single-feature linear |r| = 0.088 (d1_ema_spread_50 at k=60). For a trend-following strategy with ~50 trades/year and multi-week holding:

IC ≈ 0.088, BR ≈ 50 trades/year → IR ≈ IC × √BR ≈ 0.088 × 7.07 ≈ **0.62** (Grinold fundamental law, linear-only).

This is a LOWER BOUND — the actual ceiling is higher because:
1. Nonlinear information (rvol_60 MI = 0.116 bits) is not captured by Spearman r
2. Composite features (entry + exit interaction) can combine information
3. The grid already achieves Sharpe 1.251, exceeding this linear-only estimate

Pragmatic ceiling estimate: **Sharpe ≈ 1.2–1.5** based on grid evidence (top configs already at 1.05–1.25 with limited optimization).

### Assessment

**(a) > (b)**: Phase 3 đã tìm được config tốt hơn prior art reference.

The best Phase 3 config (Sharpe 1.251) exceeds the prior art reference (1.08) by +0.171. Even the best UNFILTERED config (1.053) is within 0.03 of prior art. Multiple independent configs exceed 1.0.

**Caveat**: The +0.171 excess is in-sample on the same dataset. It does NOT prove out-of-sample superiority. But it confirms that exploitable structure exists in this implementation that matches or exceeds prior art levels.

**ΔSharpe vs buy-and-hold**:
- Best Phase 3: 1.251 − 0.60 = **+0.651** >> 0.10 threshold. **PASS.**
- Best unfiltered: 1.053 − 0.60 = **+0.453** >> 0.10 threshold. **PASS.**

---

## 5. DECISION

### **GO_TO_DESIGN**

All four criteria met:

| Criterion | Status | Evidence |
|-----------|--------|----------|
| ≥ 1 phenomenon POWERED (effect > MDE) | **PASS** | All 12/12 combinations powered; weakest Obs/MDE = 1.98× (Tbl13) |
| ≥ 1 combination on efficiency frontier | **PASS** | C4 (Sh 1.251, MDD 52%), C5 (Sh 1.053, MDD 49%), C2 (Sh 0.828, MDD est. <50%) span the frontier |
| Expected Sharpe > buy-and-hold + 0.10 | **PASS** | 1.251 >> 0.70 (ΔSharpe = +0.651) |
| Phase 3 impact analysis ≥ 1 actionable Sharpe driver | **PASS** | avg_loser (Obs24: |β·σ|=0.709, p<1e-7) — directly actionable via trail-stop exit design |

---

## 6. CONSTRAINTS FOR PHASE 6

Derived from Phase 3 impact analysis and Phase 4 information ranking. These are evidence-based constraints, NOT prescriptive designs. Phase 6 agent is free to design any algorithm WITHIN these constraints.

### Hard Constraints (MUST)

| ID | Constraint | Source | Rationale |
|----|-----------|--------|-----------|
| HC-1 | avg_loser ≥ −0.08 | Obs24, DC-1 | Top Sharpe predictor; 75th percentile of top-10 configs |
| HC-2 | avg_hold ≥ 40 bars | Obs24, DC-2 | Second Sharpe predictor; info concentrates at k≥20 (Obs27) |
| HC-3 | 30–200 trades over sample | Tbl13, DC-3 | Power requirement (MDE at N=30 is 0.51; below N=30 underpowered) + negative β on n_trades |
| HC-4 | Total DOF ≤ 10 | Protocol constraint | Budget from Phase 0; all C1–C12 already ≤ 5 |
| HC-5 | MUST NOT use volume features (VDO, TBR, log_volume) as entry, exit, or filter | Obs15/23/28, Prop05 | Zero predictive info; VDO filter hurts ALL top-10 (ΔSharpe = −0.105) |
| HC-6 | MDD ≤ 60% | Protocol constraint | From research question |

### Soft Constraints (SHOULD)

| ID | Constraint | Source | Rationale |
|----|-----------|--------|-----------|
| SC-1 | Candidate SHOULD use trail-stop exit class (ATR or fixed %) | Obs19, Prop01 | Trail stops directly control avg_loser — the #1 Sharpe lever. Monotonic improvement with wider multiplier |
| SC-2 | Candidate SHOULD include D1 EMA regime filter (period 15–60) | Obs23/26, Prop04 | Only consistently positive filter (10/10, +0.045 mean). #1 information feature (|r|=0.088) |
| SC-3 | Entry SHOULD use EMA spread or dual-EMA crossover mechanism | Obs25/30, Prop02 | EMA spread carries |r|=0.065–0.074 (highest price-based info). A_20_90 in ALL 5/5 top configs |
| SC-4 | Exposure SHOULD be moderate (0.20–0.50) | Obs25, DC-4 | Top-5 mean exposure = 0.291; positive but weak Sharpe predictor |

### Anti-Constraints (MUST NOT optimize for)

| ID | Constraint | Source | Rationale |
|----|-----------|--------|-----------|
| AC-1 | MUST NOT add complexity to reduce churn | Obs24, DC-5, Prop07 | Churn p=0.76, partial R²=0.001 — zero Sharpe predictive power |
| AC-2 | MUST NOT target high trade count as a goal | Obs24, Tbl_sharpe_drivers | n_trades has negative β: more trades → LOWER Sharpe |

---

## Deliverables

### Files Created
- `05_go_no_go.md` (this report)

### Key IDs Referenced
- Obs04, Obs07, Obs08, Obs15, Obs16, Obs17, Obs19, Obs20, Obs21, Obs22, Obs23, Obs24, Obs25, Obs26, Obs27, Obs28, Obs29, Obs30
- Prop01–Prop08
- DC-1 through DC-5
- Tbl07–Tbl13, Tbl_sharpe_drivers, Tbl_top20_sharpe, Tbl_decomposition

### Blockers / Uncertainties
- Phase 3 best (Sharpe 1.251) has only 39 trades — barely above the HC-3 lower bound. Validation in Phase 7 must confirm power.
- Cross-codebase portability is poor (Obs22). Phase 6 design will be validated WITHIN this codebase only.
- D1 regime filter reduces trade count by 30–50% (Prop04). Combined with trail-stop exits, final trade count may approach the HC-3 lower bound.

### Gate Status
**GO_TO_DESIGN**

Three phenomena are powered, stable, and have clear exploitation mechanisms. Phase 3 grid achieves Sharpe 1.05–1.25, exceeding buy-and-hold by 0.45–0.65. Regression identifies actionable Sharpe drivers. All 12 admissible combinations pass power analysis. Proceed to Phase 6 with constraints HC-1 through HC-6, SC-1 through SC-4, and AC-1 through AC-2.
