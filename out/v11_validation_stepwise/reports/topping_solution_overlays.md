# Nhiệm vụ F: Risk Overlay Testing — TOPPING Drawdown Reduction

**Script:** `out_v11_validation_stepwise/scripts/overlay_test.py`
**Backtests:** 208 total (48 full-period + 160 WFO)
**Period:** 2019-01-01 → 2026-02-20

---

## 1. Overlay Definitions

| Overlay | Mechanism | Grid |
|---------|-----------|------|
| **OV1: Pyramid Ban** | Block adds in LATE_BULL + tighten trail | trail_mult: [1.8, 2.0, 2.2] |
| **OV2: Peak-DD Stop** | Exit if position drawdown > threshold | pct: [5%, 8%, 12%]; ATR: [2, 3, 4] |
| **OV3: Deceleration** | Tighten trail + reduce sizing when accel<0 + price<HMA | bars×trail: [3×1.5, 3×2.5, 5×2.0, 8×1.5, 8×2.5] |

All overlays are layered ON TOP of V11 cycle_late_only (WFO-opt: 0.95/2.8/0.90).

---

## 2. Full-Period Results (harsh scenario)

| Variant | Score | Δ V10 | Δ V11 | BULL% | TOPPING% | MDD% | Trades | Turnover/yr |
|---------|-------|-------|-------|-------|----------|------|--------|------------|
| **v10_baseline** | **88.9** | — | -1.9 | **1109** | **-21.0** | **36.3** | 103 | 26.3 |
| **v11_cycle_late** | **90.8** | +1.9 | — | **1143** | **-21.0** | **36.3** | 103 | 26.3 |
| | | | | | | | | |
| ov1_trail_1.8 | 72.8 | -16.2 | -18.0 | 786 | -21.0 | 36.3 | 106 | 25.8 |
| ov1_trail_2.0 | 81.0 | -8.0 | -9.8 | 949 | -21.0 | 36.3 | 105 | 25.6 |
| ov1_trail_2.2 | 82.8 | -6.2 | -8.0 | 973 | -21.0 | 36.3 | 106 | 25.7 |
| | | | | | | | | |
| ov2_pct_5 | 83.7 | -5.3 | -7.1 | 1037 | **-12.3** | 36.3 | 119 | 29.4 |
| ov2_pct_8 | 65.7 | -23.3 | -25.1 | 899 | -22.7 | **42.0** | 110 | 27.6 |
| ov2_pct_12 | 76.2 | -12.8 | -14.6 | 1207 | -21.0 | **46.6** | 103 | 26.3 |
| ov2_atr_2 | 45.4 | -43.5 | -45.4 | 539 | **-8.6** | **31.0** | 222 | 40.0 |
| ov2_atr_3 | 79.1 | -9.8 | -11.7 | 1170 | **-9.1** | 38.7 | 166 | 36.5 |
| ov2_atr_4 | 77.6 | -11.3 | -13.2 | 1117 | **-10.5** | 38.7 | 140 | 31.9 |
| | | | | | | | | |
| ov3_b3_t1.5 | 61.8 | -27.1 | -29.0 | 602 | -18.9 | 37.6 | 121 | 27.9 |
| ov3_b3_t2.5 | 80.4 | -8.6 | -10.4 | 874 | -17.6 | 37.5 | 109 | 27.0 |
| ov3_b5_t2.0 | 70.5 | -18.4 | -20.3 | 758 | -17.6 | 34.8 | 112 | 27.5 |
| ov3_b8_t1.5 | 76.5 | -12.4 | -14.3 | 864 | -17.9 | **34.1** | 111 | 27.7 |
| **ov3_b8_t2.5** | **97.0** | **+8.1** | **+6.2** | **1240** | -18.7 | **34.4** | 104 | 26.7 |

---

## 3. Overlay 1 Analysis: Pyramid Ban — **REJECT**

### Result: All 3 variants FAIL badly

| Variant | Score | BULL capture | TOPPING impact |
|---------|-------|-------------|----------------|
| ov1_trail_1.8 | 72.8 (-18.0) | 786 (69% of V10) | **-21.0 (unchanged)** |
| ov1_trail_2.0 | 81.0 (-9.8) | 949 (86% of V10) | -21.0 (unchanged) |
| ov1_trail_2.2 | 82.8 (-8.0) | 973 (88% of V10) | -21.0 (unchanged) |

### Why it fails:

1. **TOPPING return is completely unchanged** (-21.0% for all variants). The pyramid ban + tighter trail only affect LATE_BULL phase, but TOPPING is structurally orthogonal to LATE_BULL (as proven in Nhiệm vụ E: 0% overlap). The overlay fires in the wrong market condition.

2. **BULL capture destroyed**: 69-88% of V10's BULL return. The tighter trail (1.8-2.2 vs 3.5 base) in LATE_BULL exits profitable positions too early during normal pullbacks.

3. **Zero benefit, large cost**: This overlay addresses a non-problem (LATE_BULL pyramiding) while ignoring the actual issue (TOPPING consolidation losses).

### Verdict: **REJECT — structurally misguided**

---

## 4. Overlay 2 Analysis: Peak-DD Stop — **MIXED, best at ov2_pct_5 and ov2_atr_3**

### Percentage-based variants:

| Variant | Score | TOPPING% | BULL% | MDD% | Extra trades |
|---------|-------|----------|-------|------|-------------|
| ov2_pct_5 | 83.7 (-7.1) | **-12.3** (+8.7) | 1037 (93% V10) | 36.3 | +16 |
| ov2_pct_8 | 65.7 (-25.1) | -22.7 (-1.7) | 899 (81% V10) | 42.0 (+5.7) | +7 |
| ov2_pct_12 | 76.2 (-14.6) | -21.0 (0.0) | 1207 (109% V10) | 46.6 (+10.3) | 0 |

### ATR-based variants:

| Variant | Score | TOPPING% | BULL% | MDD% | Extra trades |
|---------|-------|----------|-------|------|-------------|
| ov2_atr_2 | 45.4 (-45.4) | **-8.6** (+12.4) | 539 (49% V10) | 31.0 (-5.3) | +119 |
| ov2_atr_3 | 79.1 (-11.7) | **-9.1** (+11.9) | 1170 (105% V10) | 38.7 (+2.4) | +63 |
| ov2_atr_4 | 77.6 (-13.2) | **-10.5** (+10.5) | 1117 (101% V10) | 38.7 (+2.4) | +37 |

### Key findings:

1. **OV2 actually reduces TOPPING damage** — the only overlay that does. Best case: `ov2_atr_3` cuts TOPPING loss from -21.0% to -9.1% (57% reduction).

2. **But at a cost**: All variants lose 5-45 pts on score due to more frequent exits → more round-trip costs → lower net returns. Trades increase 7-119 above baseline.

3. **Paradox of ov2_pct_8 and ov2_pct_12**: Tighter % stops can INCREASE MDD because they exit during dips and re-enter at worse prices. The 5% variant works because it's tight enough to catch TOPPING quickly; 8%/12% variants are in a "worst of both worlds" zone.

4. **ov2_atr_3 is the most interesting**: It preserves BULL capture (105% of V10!) while cutting TOPPING by 57%. The extra 63 trades and 38.7% MDD are the cost.

### Why it still fails promotion:

All variants fail C1 (score >= V11). The TOPPING improvement doesn't compensate for the round-trip cost of more frequent exits. OV2 would need lower transaction costs to be net-positive.

### Verdict: **REJECT for production, but ov2_atr_3 is the most promising direction**

---

## 5. Overlay 3 Analysis: Deceleration — **ov3_b8_t2.5 is exceptional**

### Results:

| Variant | Score | Δ V11 | BULL% | TOPPING% | MDD% | Trades |
|---------|-------|-------|-------|----------|------|--------|
| ov3_b3_t1.5 | 61.8 | -29.0 | 602 (54%) | -18.9 (+2.1) | 37.6 | 121 |
| ov3_b3_t2.5 | 80.4 | -10.4 | 874 (79%) | -17.6 (+3.4) | 37.5 | 109 |
| ov3_b5_t2.0 | 70.5 | -20.3 | 758 (68%) | -17.6 (+3.4) | 34.8 | 112 |
| ov3_b8_t1.5 | 76.5 | -14.3 | 864 (78%) | -17.9 (+3.1) | **34.1** | 111 |
| **ov3_b8_t2.5** | **97.0** | **+6.2** | **1240 (112%)** | **-18.7 (+2.3)** | **34.4** | 104 |

### ov3_b8_t2.5 deep-dive:

This variant is remarkable:

| Metric | V10 | V11 | ov3_b8_t2.5 | vs V10 | vs V11 |
|--------|-----|-----|-------------|--------|--------|
| **Score (harsh)** | 88.9 | 90.8 | **97.0** | **+8.1** | **+6.2** |
| **Score (base)** | 112.7 | 114.7 | **111.7** | -1.0 | -2.9 |
| **Score (smart)** | 121.4 | 123.3 | **117.5** | -3.9 | -5.9 |
| CAGR (harsh) | 37.3% | 37.9% | **39.7%** | +2.4% | +1.8% |
| BULL return | 1109% | 1143% | **1240%** | +131% | +97% |
| TOPPING return | -21.0% | -21.0% | **-18.7%** | +2.3% | +2.3% |
| MDD | 36.3% | 36.3% | **34.4%** | **-1.9%** | **-1.9%** |
| Sharpe (harsh) | 1.151 | 1.170 | **1.218** | +0.067 | +0.048 |
| Trades | 103 | 103 | 104 | +1 | +1 |
| Turnover/yr | 26.3 | 26.3 | 26.7 | +0.4 | +0.4 |

**Why it works**: `bars=8, trail=2.5` is a *gentle* deceleration filter. It only tightens trail when momentum has been negative for 8 consecutive H4 bars (= 32 hours) AND price is below HMA. This is a high-conviction signal that catches genuine trend exhaustion, not noise. The trail_mult=2.5 matches the existing `trail_tighten_mult` (profit > 25%), so it's a natural extension.

**The pattern**: This overlay is essentially "if momentum is dying, switch to defensive trailing mode early." It doesn't change entry behavior (only 1 extra trade). It mainly protects against the gradual grind-down that characterizes TOPPING consolidation.

### Why ov3_b8_t2.5 fails promotion criteria:

| Criterion | Value | Required | **PASS/FAIL** |
|-----------|-------|----------|---------------|
| C1: score ≥ V11 | 97.0 > 90.8 | YES | **PASS** |
| C2: TOPPING ≥ V10 | -18.7 > -21.0 | YES | **PASS** |
| C3: BULL ≥ 90% V10 | 1240 > 998 | YES | **PASS** |
| C4: MDD ≤ V10 | 34.4 < 36.3 | YES | **PASS** |
| C5: WFO ≥ 60% | **40%** < 60% | NO | **FAIL** |
| C6: cliff_safe ≥ 2/5 | 0/5 pass | NO | **FAIL** |

**C5 failure analysis**: ov3_b8_t2.5 wins 4/10 WFO windows (40%), loses 4/10, ties 2/10. The windows it loses are W1 (2021-H2) and W4 (2023-H1) where deceleration filter exits too early in choppy recovery. But it wins the **highest-magnitude windows** — W0 (2021-H1: +50 pts), W7 (2024-H2: +37 pts).

**C6 failure**: No other OV3 variant passes even C1 — they all regress vs V11. `bars=8, trail=2.5` is on the edge of the parameter space, and tighter settings destroy value.

### Verdict: **HOLD — ov3_b8_t2.5 is the most promising candidate but fails robustness tests**

---

## 6. Cross-Scenario Consistency

| Variant | harsh | base | smart | Consistent? |
|---------|-------|------|-------|-------------|
| **ov3_b8_t2.5 Δ vs V10** | **+8.1** | -1.0 | -3.9 | **NO** — only harsh improves |
| **ov3_b8_t2.5 Δ vs V11** | **+6.2** | -2.9 | -5.9 | **NO** — only harsh improves |

The harsh-only improvement is concerning. Under base/smart scenarios (lower costs), the deceleration overlay slightly hurts because the avoided losses are smaller (fewer exits) but the missed gains are the same.

---

## 7. MDD Comparison

| Variant | harsh MDD | vs V10 |
|---------|-----------|--------|
| v10_baseline | 36.3% | — |
| v11_cycle_late | 36.3% | 0.0% |
| ov2_atr_2 | **31.0%** | **-5.3%** |
| ov3_b8_t1.5 | **34.1%** | **-2.2%** |
| ov3_b8_t2.5 | **34.4%** | **-1.9%** |
| ov3_b5_t2.0 | **34.8%** | **-1.5%** |
| ov2_pct_8 | 42.0% | +5.7% |
| ov2_pct_12 | 46.6% | +10.3% |

The deceleration overlays (OV3) consistently reduce MDD by 1.5-2.2%. This is a genuine risk improvement.

---

## 8. TOPPING Impact Summary

| Variant | TOPPING% | Δ vs V10 | Mechanism |
|---------|----------|----------|-----------|
| ov2_atr_2 | -8.6% | **+12.4%** | Aggressive position-level stop |
| ov2_atr_3 | -9.1% | **+11.9%** | Position-level stop |
| ov2_atr_4 | -10.5% | **+10.5%** | Position-level stop |
| ov2_pct_5 | -12.3% | **+8.7%** | Tight % stop |
| ov3_b3_t2.5 | -17.6% | +3.4% | Trail tightening on decel |
| ov3_b5_t2.0 | -17.6% | +3.4% | Trail tightening on decel |
| ov3_b8_t1.5 | -17.9% | +3.1% | Trail tightening on decel |
| ov3_b8_t2.5 | -18.7% | +2.3% | Trail tightening on decel |
| ov3_b3_t1.5 | -18.9% | +2.1% | Trail tightening on decel |
| **OV1 (all)** | **-21.0%** | **0.0%** | **Zero impact** |

**Key insight**: Only OV2 (position-level DD stop) makes a meaningful dent in TOPPING losses. OV3 provides ~2-3% improvement. OV1 has zero effect because LATE_BULL and TOPPING are structurally disjoint (Nhiệm vụ E confirmed 0% overlap).

---

## 9. Promotion Criteria Matrix

| Criterion | ov1_* | ov2_pct5 | ov2_atr3 | ov3_b8t2.5 |
|-----------|-------|----------|----------|------------|
| C1: score ≥ V11 | FAIL | FAIL | FAIL | **PASS** |
| C2: TOPPING ≥ V10 | FAIL | **PASS** | **PASS** | **PASS** |
| C3: BULL ≥ 90% V10 | varies | **PASS** | **PASS** | **PASS** |
| C4: MDD ≤ V10 | PASS | PASS | FAIL | **PASS** |
| C5: WFO ≥ 60% | FAIL | FAIL | FAIL | FAIL |
| C6: cliff_safe | FAIL | FAIL | FAIL | FAIL |
| **Overall** | **REJECT** | **REJECT** | **REJECT** | **HOLD** |

No overlay passes all 6 criteria. The closest is **ov3_b8_t2.5** which passes 4/6 but fails robustness (WFO consistency and cliff safety).

---

## 10. Conclusions

### 10.1 What we learned

1. **TOPPING drawdown is hard to reduce without large score sacrifice.** The regime-level TOPPING definition (price near EMA50, low ADX) describes consolidation that can resolve in either direction. Any overlay that exits during TOPPING also exits during consolidation that leads to continuation.

2. **Position-level stops (OV2) are the most direct solution** but create a turnover penalty. Every stop → re-entry costs 50 bps round-trip (harsh). At 63 extra trades, that's ~31.5% of NAV over 7 years.

3. **Deceleration (OV3) is the best risk/return trade-off.** It reduces MDD by 1.9%, improves TOPPING by 2.3%, and actually INCREASES harsh score by 8.1 pts — but only in the harsh scenario and only at one specific parameter setting (bars=8, trail=2.5).

4. **Cycle phase overlays (OV1) are ineffective for TOPPING** because LATE_BULL and TOPPING are structurally disjoint. Any LATE_BULL-specific modification has zero impact on TOPPING days.

### 10.2 Recommendations

| Action | Rationale |
|--------|-----------|
| **Reject OV1** | Zero TOPPING impact, large BULL sacrifice |
| **Reject OV2 for now** | TOPPING improvement real but score sacrifice too large |
| **HOLD ov3_b8_t2.5** | Best single variant (+8.1 harsh score, -1.9% MDD) but fails robustness |
| **Consider ov3_b8_t2.5 + ov2_atr_3 combo** | Decel for score + peak-DD for TOPPING — untested |

### 10.3 If forced to pick ONE overlay for production

**ov3_b8_t2.5** is the only variant that improves harsh score (+8.1), reduces MDD (-1.9%), and doesn't increase TOPPING losses. Its WFO consistency (40%) is below the 60% threshold, but it wins the highest-magnitude windows. The risk is parameter sensitivity — bars=8 is the only working setting.

### 10.4 What would make an overlay promotable

1. **Lower cost environment**: OV2_atr_3 becomes viable under base/smart scenarios (where 63 extra trades cost less)
2. **Wider decel sweet spot**: If bars=6 or bars=10 also worked for OV3, cliff risk disappears
3. **Combination testing**: OV3 (score/MDD) + OV2 (TOPPING specifically) might be complementary

---

## 11. Cumulative Validation Status

| Test | Verdict | Notes |
|------|---------|-------|
| A. Reproducibility | PASS | SHA256 match |
| B1. WFO Round-by-Round (score) | INCONCLUSIVE → negative | 0/2 non-zero rounds positive |
| B1b. WFO Round-by-Round (return) | INCONCLUSIVE → positive (weak) | 2/4 positive, 5.6× asymmetry |
| B2. Sensitivity Grid | **FAIL** | 6/27 = 22% beat baseline |
| B3. Final Holdout | **HOLD** | V11 thua -1.23 on 3/3 scenarios |
| C. Selection Bias | **PASS** | PBO = 13.9%, DSR = 1.0 |
| D. Lookahead | **PASS** | 16/16 tests passed |
| E. TOPPING vs LATE_BULL | **PASS** | 0% overlap, structurally orthogonal |
| **F. Risk Overlays** | **HOLD** | ov3_b8_t2.5 promising but fails robustness |

---

## 12. Data Files

| File | Description |
|------|-------------|
| `out_v11_validation_stepwise/overlay_results.csv` | 48 rows: 16 variants × 3 scenarios (full-period) |
| `out_v11_validation_stepwise/overlay_wfo.csv` | 160 rows: 16 variants × 10 WFO windows (harsh) |
| `out_v11_validation_stepwise/overlay_results.json` | Summary + promotion verdicts |
| `out_v11_validation_stepwise/scripts/overlay_test.py` | Reproducible test script (208 backtests) |
| `candidates_v11_overlay_1.yaml` | OV1 configs (3 variants) |
| `candidates_v11_overlay_2.yaml` | OV2 configs (6 variants) |
| `candidates_v11_overlay_3.yaml` | OV3 configs (5 variants) |
| `out_v11_validation_stepwise/reports/topping_solution_overlays.md` | This report |
