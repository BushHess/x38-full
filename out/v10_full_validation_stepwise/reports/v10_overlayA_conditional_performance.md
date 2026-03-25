# V10 OverlayA Conditional Performance Report

**Date:** 2026-02-24
**Feature:** OverlayA — post-emergency-DD cooldown (cooldown_after_emergency_dd_bars = 12)
**Baseline:** cooldown_after_emergency_dd_bars = 0 (no cooldown)
**Scenario:** harsh (50 bps round-trip)
**Period:** 2019-01-01 → 2026-02-20 (7.1 years, 15,648 H4 bars)
**Holdout:** 2024-10-01 → 2026-02-20

---

## VERDICT: **HOLD**

> Full-period approximately neutral ($-1,416, -1.6% of baseline), BCR 1.07 > 1.0. Holdout net positive ($+7,684) but small sample (1 cascade episodes < 3).

> **Concentration warning:** Benefit is highly concentrated: 85% from episode 16. Top 2 episodes account for 97% of total benefit.

> **Small-sample warning:** holdout has only 1 cascade episode(s) (< 3 recommended).

> **Consistency:** DIVERGENT_FAVORABLE — Full-period slightly negative, holdout positive. Holdout does NOT confirm full-period loss — suggests the full-period result is borderline/noisy.

---

## 1. Benefit / Cost Summary

| Metric | Full Period | Holdout |
|--------|------------|---------|
| **Benefit $** | $15,789.48 | $13,448.75 |
| **Cost $** | $14,717.05 | $5,765.09 |
| **Net $** | $-1,415.92 | $+7,683.66 |
| **BCR** | 1.073 | 2.333 |

### Definitions

- **Benefit** = Σ max(0, overlay_pnl − baseline_pnl) across cascade episodes (Group 1). Counts only episodes where overlay outperforms.
- **Cost** = max(0, baseline_pnl_Group2 − overlay_pnl_Group2). The performance given up in non-cascade time.
- **Net** = overlay_total − baseline_total (end-to-end backtest).
- **BCR** = Benefit / Cost. BCR > 1 means the protective benefit from winning cascade episodes exceeds Group 2 opportunity cost.

---

## 2. Group 1 — Cascade Episode Detail

4 cascade episodes identified (episodes with ≥ 2 consecutive emergency_dd exits).

| EP | Peak | Δ PnL | Benefit | Overlay Better? |
|---:|------|------:|--------:|:---------------:|
| 4 | 2019-06-26 | $-1,700 | $0 | **No** |
| 11 | 2021-11-10 | $+465 | $465 | Yes |
| 14 | 2024-03-04 | $+1,876 | $1,876 | Yes |
| 16 | 2025-01-20 | $+13,449 | $13,449 | Yes |
| | **Total** | **$+14,089** | **$15,789** | 3/4 |

- **3/4** cascade episodes show positive overlay delta.
- **1/4** show negative delta (overlay worse): $-1,700.
- Aggregate G1 delta: $+14,089.

---

## 3. Group 2 — Non-Cascade Time Cost

| Metric | Full | Holdout |
|--------|-----:|--------:|
| Baseline G2 PnL | $107,666 | $40,779 |
| Overlay G2 PnL | $92,949 | $35,014 |
| G2 Delta | $-14,717 | $-5,765 |
| Cost $ | $14,717 | $5,765 |

### Blocked trades (opportunity cost)

Full period: **2 blocked trades** (total PnL: $+33,733)

| Trade | Entry | Exit | PnL | Return% |
|------:|-------|------|----:|--------:|
| 44 | 2021-09-30 | 2021-10-22 | $+17,000 | +32.7% |
| 63 | 2024-01-23 | 2024-02-24 | $+16,733 | +27.7% |

Holdout: **1 blocked trade(s)** (total PnL: $+2,224)

| Trade | Entry | Exit | PnL | Return% |
|------:|-------|------|----:|--------:|
| 79 | 2024-10-11 | 2024-10-23 | $+2,224 | +3.8% |

All blocked trades are profitable winners blocked by cooldown spillover from isolated emergency_dd exits. This is the core opportunity cost mechanism.

---

## 4. Accounting Reconciliation

### Full period

| Component | Baseline | Overlay | Delta |
|-----------|--------:|--------:|------:|
| G1 (cascade) | — | — | $+14,089 |
| G2 (rest) | $107,666 | $92,949 | $-14,717 |
| **G1+G2 sum** | — | — | **$-628** |
| **Global (actual)** | $85,968 | $84,553 | **$-1,416** |
| Decomposition residual | — | — | $+788 |

The $788 residual arises from NAV path-dependency: G1 and G2 PnLs are measured on sub-windows and do not account for inter-period compounding effects.

### Holdout

| Component | Baseline | Overlay | Delta |
|-----------|--------:|--------:|------:|
| G1 (cascade) | $-22,878 | $-9,429 | $+13,449 |
| G2 (rest) | $40,779 | $35,014 | $-5,765 |
| **Global** | $17,901 | $25,585 | **$+7,684** |
| Decomposition residual | — | — | $+0 |

---

## 5. Diagnostics

### 5.1 Concentration

| Metric | Value |
|--------|-------|
| Top-1 episode share of benefit | **85.2%** (EP 16) |
| Top-2 episodes share of benefit | **97.1%** (EP [16, 14]) |
| # episodes contributing benefit | 3 / 4 |

Benefit is **highly concentrated** in episode 16 (Jan-2025 crash), which alone provides 85% of total benefit. Removing EP 16 would make the overlay net negative.

### 5.2 Consistency

| Period | Net $ | Sign |
|--------|------:|:----:|
| Full | $-1,416 | − |
| Holdout | $+7,684 | + |

**DIVERGENT_FAVORABLE**: Full-period slightly negative, holdout positive. Holdout does NOT confirm full-period loss — suggests the full-period result is borderline/noisy.

### 5.3 Small-sample warning

**WARNING**: Holdout contains only **1** cascade episode(s). The recommended minimum is 3. The holdout BCR (2.33) and net ($+7,684) are based on a single episode and should be treated as indicative, not conclusive.

---

## 6. Interpretation

### What the overlay does well

1. **Cascade protection works**: In 3 of 4 cascade episodes, the cooldown reduces bleed by blocking re-entries into ongoing drawdowns. The largest benefit (+$13,449) comes from episode 16, where the cooldown avoids 2 additional emergency_dd exits and reduces MDD by 5.8pp.
2. **Emergency_dd exit count reduced**: Across cascade episodes, overlay reduces total emergency_dd exits from 34 to 31.
3. **Holdout validates the mechanism**: The one holdout cascade episode shows clear benefit with BCR 2.33.

### What the overlay costs

1. **Blocked winners**: The cooldown cannot distinguish cascade re-entries (bad) from genuine recovery entries (good). 2 blocked trades in full period had combined PnL of $+33,733.
2. **NAV propagation**: Lower NAV entering non-cascade periods (due to position-size differences during cascades) compounds into smaller absolute returns on the same winning trades.
3. **One bad episode**: Episode 4 (2019-2020) shows -$1,700 overlay degradation, where the cooldown blocked entries that would have captured the recovery rally.

### Net assessment

Over the full 7.1-year period, the overlay is approximately **break-even** (net $-1,416, or -1.6% of baseline PnL). The cascade protection benefit ($15,789) slightly exceeds the non-cascade cost ($14,717) at the episode level (BCR 1.07), but G1 loss episodes and compounding effects bring the true net slightly negative.

The holdout period is more favorable (net $+7,684, BCR 2.33), but this relies on a single cascade episode and should not be over-weighted.

---

## 7. Conditions for Promotion to PROMOTE

The overlay should be promoted if ANY of these conditions are met:

1. **More holdout cascade data**: If 2+ additional cascade episodes occur in future holdout data and the overlay remains net positive, the small-sample concern is resolved.
2. **Selective cooldown**: Implementing a shorter cooldown (e.g., 6 bars instead of 12) or a cooldown that only activates after maxrun ≥ 2 (not after isolated emergency_dd events) would reduce blocked-winner opportunity cost while preserving cascade protection.
3. **Regime-conditional activation**: Activating the cooldown only when a cascade is detected in real-time (e.g., after the 2nd consecutive emergency_dd exit) would eliminate cost during non-cascade periods entirely.

---

## 8. Deliverables

| Artifact | Path |
|----------|------|
| Script | `scripts/benefit_cost_final.py` |
| Full summary JSON | `out_overlayA_conditional/benefit_cost_summary_full.json` |
| Holdout summary JSON | `out_overlayA_conditional/benefit_cost_summary_holdout.json` |
| This report | `reports/v10_overlayA_conditional_performance.md` |

