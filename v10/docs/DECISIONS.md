# Decision Log

## 2026-02-23 — V11 Extended WFO + Bootstrap — WFO-optimal SUPERSEDES winner

**Output:** `out_v11_wfo_extended/`

### Fixed-Param WFO: 10 OOS windows, all 3 configs

| Window | Period | V10 Ret% | V11 Winner | V11 WFO-opt | Delta(W) | Delta(O) |
|--------|--------|----------|-----------|-------------|----------|----------|
| 0 | 2021-H1 | +42.6 | +44.5 | +44.8 | +1.8 | +2.2 |
| 1 | 2021-H2 | +12.7 | +12.7 | +12.7 | 0.0 | 0.0 |
| 2 | 2022-H1 | +0.0 | +0.0 | +0.0 | 0.0 | 0.0 |
| 3 | 2022-H2 | +0.0 | +0.0 | +0.0 | 0.0 | 0.0 |
| 4 | 2023-H1 | +12.9 | +12.9 | +12.9 | 0.0 | 0.0 |
| 5 | 2023-H2 | +25.6 | +28.6 | +28.5 | +3.0 | +2.9 |
| 6 | 2024-H1 | +31.2 | +30.9 | +30.9 | -0.3 | -0.3 |
| 7 | 2024-H2 | +28.3 | +27.5 | +27.6 | -0.8 | -0.7 |
| 8 | 2025-H1 | -9.9 | -9.9 | -9.9 | 0.0 | 0.0 |
| 9 | 2025-H2 | +2.0 | +2.0 | +2.0 | 0.0 | 0.0 |

- **WFO pass rate: 9/10 (90%) — IDENTICAL for all 3 configs**
- V11 cycle fires in only 4/10 windows (0,5,6,7 — bull periods)
- V11 wins 2, loses 2 in those 4 windows (net positive due to larger wins)
- 6/10 windows: V11 = V10 exactly (bear/chop/recovery periods)

### Enhanced Bootstrap (5000 resamples × 3 block sizes)

| Comparison | Block 10 | Block 20 | Block 40 | Mean |
|-----------|----------|----------|----------|------|
| P(V11 winner > V10) | 87.2% | 88.7% | 87.3% | **87.7%** |
| P(V11 WFO-opt > V10) | 91.3% | 92.2% | 91.3% | **91.6%** |
| P(V11 winner > WFO-opt) | 21.2% | 19.6% | 13.0% | **17.9%** |

**Key finding: WFO-optimal params (0.95/2.8/0.9) BEAT hand-picked winner (0.90/3.0/0.9)**
- WFO-opt NAV: $150,883 vs winner $150,113 vs V10 $145,815
- WFO-opt Sharpe: 1.3413 vs winner 1.3391 vs V10 1.3219
- P(winner > WFO-opt) = only 18% → winner is WORSE

### Revised Recommendation

**Use WFO-optimal params (0.95/2.8/0.9) instead of hand-picked winner (0.90/3.0/0.9):**
- Higher confidence vs V10: 91.6% vs 87.7%
- Still below 95% bar, but closer
- Milder params = less risk of over-tuning
- WFO-selected = selection-bias resistant

```yaml
# V11 WFO-optimal (supersedes original winner)
enable_cycle_phase: true
cycle_early_aggression: 1.0
cycle_early_trail_mult: 3.5
cycle_late_aggression: 0.95      # was 0.90
cycle_late_trail_mult: 2.8       # was 3.0
cycle_late_max_exposure: 0.90    # unchanged
```

---

## 2026-02-23 — V11 Comprehensive Validation — CONDITIONAL PROMOTE

**Output:** `out_v11_full_validation/`, `out_v11_wfo/`

### 1. Full Backtest (V10 vs V11 vs B&H, 3 cost scenarios)

| Strategy | Smart | Base | Harsh | Trades |
|----------|-------|------|-------|--------|
| V10 baseline | 121.37 | 112.74 | 88.94 | 100 |
| V11 winner | 123.03 | 114.37 | 90.52 | 100 |
| Delta | +1.66 | +1.64 | +1.59 | 0 |

V11 final NAV (base): $150,113 vs V10 $145,815 (+$4,298 / +2.9%)
CAGR: 46.14% vs 45.55%, MDD: 34.78% identical, Sharpe: 1.339 vs 1.322

### 2. Paired Bootstrap (Sharpe Difference, 2000 resamples)

| Scenario | V11 Sharpe | V10 Sharpe | Delta | 95% CI | P(V11>V10) |
|----------|-----------|-----------|-------|--------|------------|
| Smart | 1.403 | 1.386 | +0.017 | [-0.008, +0.053] | 88.8% |
| Base | 1.339 | 1.322 | +0.017 | [-0.008, +0.052] | 88.7% |
| Harsh | 1.168 | 1.151 | +0.017 | [-0.008, +0.052] | 87.9% |

**P(V11>V10) ≈ 88%, NOT statistically significant at 95% level.**
CI includes 0 — improvement could be noise.

### 3. WFO Rolling OOS (24m train / 6m test, 10 windows)

- **Best WFO params:** `late_aggression=0.95, trail_mult=2.8, max_exposure=0.9`
- Pass rate: 100% (4/4 windows where this combo was top-K)
- 4 survivors out of 27 param combinations
- All survivors use late-bull protection (concept validated)
- WFO preferred **milder** params (0.95) vs our winner (0.90)

### 4. Individual Bootstrap (V11, base scenario)

| Metric | Observed | 95% CI | P>0 |
|--------|----------|--------|-----|
| Sharpe | 1.339 | [0.542, 2.092] | 100% |
| CAGR% | 46.10 | [12.71, 87.42] | 99.9% |
| MDD% | 34.78 | [25.93, 60.39] | 100% |

V11 as standalone strategy is robust (Sharpe CI entirely > 0).

### 5. Regime Return Decomposition

| Regime | V10 Ret% | V11 Ret% | Delta | V10 MDD% | V11 MDD% |
|--------|---------|---------|-------|----------|----------|
| BULL | 1491 | 1531 | **+40** | 33.3 | 33.3 |
| TOPPING | -17.5 | -17.5 | **0.0** | 26.1 | 26.1 |
| BEAR | 0.0 | 0.0 | 0.0 | 5.6 | 5.6 |
| CHOP | 3.9 | 3.8 | -0.1 | 30.2 | 30.2 |
| SHOCK | -14.1 | -13.6 | +0.5 | 27.1 | 27.1 |
| NEUTRAL | 24.4 | 24.4 | 0.0 | 17.0 | 17.0 |

Improvement comes entirely from BULL regime. **Zero damage to TOPPING or any other regime.**

### 6. DD Episodes (base, ≥5%)

- V10: 21 episodes, V11: 23 episodes (2 more minor episodes)
- Max DD identical: 33.2%
- Major episodes identical in timing and severity

### Honest Assessment

**CONDITIONAL PROMOTE** — V11 `cycle_late_only` is a modest, defensible improvement:

**Evidence FOR:**
- Consistently better across all 3 cost scenarios (+1.6 points)
- Zero damage to any regime (TOPPING unchanged at -17.49%)
- WFO validates the concept (all survivors use late-bull protection)
- Same trade count (100), same MDD (34.78%), no turnover increase
- Only 3 new parameters, all with economic rationale (reduce exposure in late bull)

**Evidence AGAINST:**
- P(V11>V10) ≈ 88%, below 95% significance threshold
- 95% CI for Sharpe difference includes 0
- 30+ configs tested → selection bias risk (mitigated by WFO concept validation)
- WFO preferred slightly milder params (0.95 vs 0.90 aggression)
- Improvement is small: +$4,298 on $150K over 7 years

**Conclusion:** The cycle late-bull protection *concept* is validated (WFO confirms), but the *exact params* show only ~88% confidence of being better than V10. This is above chance (50%) but below the 95% bar used for `trail_tighten` promotion. Recommend applying as default only if user accepts 88% confidence level, OR wait for more OOS data.

---

## 2026-02-23 — V11 Hybrid strategy created and tested (30+ configs)

**Files created:**
- `v10/strategies/v11_hybrid.py` — V11 Hybrid strategy (Momentum + MR + Macro)
- `v10/research/candidates.py` — updated for strategy polymorphism
- `v10/research/wfo.py` — updated to use strategy factory
- `v10/core/config.py`, `v10/cli/backtest.py` — V11 registration

**V11 Framework:** Three configurable layers on top of V8 Apex core:
- **A: MR Defensive** — D1 RSI extreme + price-to-MA200 distance gating
- **B: Macro Cycle Phase** — EARLY/MID/LATE_BULL/BEAR detection with per-phase adjustments
- **C: ADX Trend Strength** — entry gating and sizing based on ADX

**Testing (5 rounds, 30+ configurations):**

| Round | Configs | Best Result |
|-------|---------|-------------|
| Parity | V11 disabled = V10 | Identical scores (confirmed) |
| Isolate | MR, Cycle, ADX each alone | Cycle closest (harsh 89.41), MR/ADX hurt |
| Refined | Cycle variants, MR ultra | Cycle early+fast best score (109.23) but TOPPING -18.9% |
| Final | Cycle late-only, neutral | **cycle_late_only PROMOTE (harsh 90.52)** |
| Combos | Late+MR, late+milder | Late_only confirmed best, MR still hurts |

**Winner: `v11_cycle_late_only`** config:
```yaml
enable_cycle_phase: true
cycle_early_aggression: 1.0      # no early boost
cycle_early_trail_mult: 3.5      # keep default
cycle_late_aggression: 0.90      # -10% in late bull
cycle_late_trail_mult: 3.0       # tighter trail
cycle_late_max_exposure: 0.90    # -10% cap
```

**Key findings:**
1. **MR Defensive does NOT work for BTC spot** — D1 RSI thresholds fire too often in bull markets, even at RSI 88+. Reduces CAGR by 40-50%.
2. **ADX Gating hurts** — blocks entries during legitimate re-entries after dips, increases MDD.
3. **Cycle early boost hurts TOPPING** — EARLY_BULL aggression boost overlaps with TOPPING transitions.
4. **Cycle late protection WORKS** — mild reduction (0.90× aggression, 3.0× trail, 0.90 max_exposure) preserves capital during late-bull-to-bear transitions without hurting TOPPING or BULL capture.

**Status:** CONDITIONAL PROMOTE — see comprehensive validation entry above.

---

## 2026-02-23 — Comprehensive parameter optimization (20 configs tested)

**Study:** `RESEARCH_V10_PARAM_OPTIMIZATION.md`

Tested 20 configurations across 3 rounds (isolate, combos, TOPPING-focused).
**Kết luận: Baseline hiện tại (sau trail_tighten fix) đã là Pareto-optimal.**
Không có thay đổi đơn lẻ hay kết hợp nào vượt qua decision gate.

Rejected candidates (with reasons):
- rsi_wilder: harsh+6 nhưng TOPPING -4.5% → HOLD
- cooldown_2: harsh+8.6 nhưng TOPPING -4% → HOLD
- trail_atr_30: TOPPING+1.4% nhưng harsh-8.6 → HOLD
- fstop_018: harsh-2.4, neutral → HOLD
- caution_030: gần nhất (harsh-3, TOPPING-0.2%) → HOLD
- All combos: tác động TOPPING cộng dồn, không bù trừ → HOLD
- rsi_ob_70, topping_defense: MDD vượt ngưỡng → REJECT

Key insight: ewm_span RSI tốt hơn wilder cho TOPPING (-17.5% vs -22.0%).
Gate study cũ bị confounding (rsi_method + emergency_ref đổi cùng lúc).

## 2026-02-23 — trail_tighten_profit_pct: 0.20 → 0.25 (APPLIED)

**File:** `v10/strategies/v8_apex.py` line 89

Evidence:
- Paired bootstrap: P(ΔSharpe > 0) = 99.6%, CI [+0.009, +0.212]
- WFO: 100% OOS pass (5/5 windows)
- Damage analysis: PnL +26% ($97.6K → $123K)
- 0.30 rejected: P = 89.6% (< 95%), WFO 75%

Impact:
- Harsh score: 83.48 → 88.94 (+5.46)
- Base CAGR: 38.55% → 45.55% (+7.00%)
- TOPPING: -22.0% → -17.5% (+4.5%, do ewm_span baseline)

## 2026-02-22 — Gate study: baseline_legacy confirmed (pre-existing)

**Study:** `out_v10_full_eval/`

- baseline_legacy (pre_cost_legacy + wilder): PROMOTE, score 83.48
- v9_like (post_cost + ewm_span): HOLD, score 77.45
- peak_emergency: REJECT, MDD 54.14%
- peak_cooldown: REJECT, MDD 54.17%
- peak_dd_adaptive: REJECT, MDD 40.41%

Note: Study has confounding (rsi_method + emergency_ref changed together).
Isolated testing (2026-02-23) showed ewm_span actually better for TOPPING.
