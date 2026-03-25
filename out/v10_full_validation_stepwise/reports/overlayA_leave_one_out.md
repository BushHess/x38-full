# OverlayA Leave-One-Episode-Out Robustness Test

**Date:** 2026-02-24
**Scenario:** harsh (50 bps RT)
**Overlay:** V1 (cooldown_after_emergency_dd_bars = 12)
**Cascade episodes:** 4 (full period), 1 (holdout)

---

## 1. Per-Episode G1 Benefit Breakdown

| EP | Peak Date | Depth% | #ED | BL PnL | OV PnL | Δ PnL | Benefit | Share% |
|---:|:----------|-------:|----:|-------:|-------:|------:|--------:|-------:|
| 4 | 2019-06-26 | 35.2 | 12 | $+383 | $-1,428 | $-1,810 | $0 | 0% |
| 12 | 2021-11-10 | 36.2 | 7 | $+1,845 | $-1,954 | $-3,799 | $0 | 0% |
| 15 | 2024-05-21 | 33.4 | 7 | $+528 | $+4,447 | $+3,920 | $3,920 | 23% |
| 17 | 2025-01-20 | 31.6 | 9 | $-22,878 | $-9,429 | $+13,449 | $13,449 | 77% |
| **Total** | | | | | | | **$17,368** | **100%** |

**G2 Cost:** $14,717
**BCR (all episodes):** 1.18
**Net conditional:** $+2,651
**Global net:** $-1,416

---

## 2. Leave-One-Out Results (Full Period)

| Excluded EP | Date | Benefit Lost | Remaining Benefit | Cost | LOO Net | LOO BCR | Still ≥ 0? |
|:------------|:-----|------------:|-----------------:|-----:|--------:|--------:|:----------:|
| EP4 | 2019-06-26 | $0 (0%) | $17,368 | $14,717 | $+2,651 | 1.18 | YES |
| EP12 | 2021-11-10 | $0 (0%) | $17,368 | $14,717 | $+2,651 | 1.18 | YES |
| EP15 | 2024-05-21 | $3,920 (23%) | $13,449 | $14,717 | $-1,268 | 0.91 | **NO** |
| EP17 | 2025-01-20 | $13,449 (77%) | $3,920 | $14,717 | $-10,797 | 0.27 | **NO** |

**LOO net ≥ 0 in 2/4 scenarios** (removing each cascade episode one at a time).

---

## 3. Leave-One-Out Results (Holdout)

| Excluded EP | Date | Benefit Lost | Remaining | Cost | LOO Net | LOO BCR | Still ≥ 0? |
|:------------|:-----|------------:|----------:|-----:|--------:|--------:|:----------:|
| EP2 | 2025-01-20 | $13,449 (100%) | $0 | $5,765 | $-5,765 | 0.00 | **NO** |

**Holdout baseline:** benefit=$13,449, cost=$5,765, BCR=2.33

---

## 4. Concentration Risk Assessment

**Largest single-episode contribution:** EP17 (2025-01-20) — $13,449 (77% of total benefit)

**MODERATE concentration risk.** The top episode provides 77% of benefit — still the majority contributor, but some benefit comes from other episodes.

**Episodes where overlay performed WORSE than baseline:** 2/4
  - EP4 (2019-06-26): Δ=$-1,810
  - EP12 (2021-11-10): Δ=$-3,799

These episodes represent time periods where the cooldown's opportunity cost (blocking profitable re-entries) exceeded its benefit. The overlay is net-positive only because other cascade episodes provide enough benefit to offset.

---

## 5. Verdict

### FAIL — NOT ROBUST

> LOO net goes negative in 2/4 scenarios. The overlay's benefit is too concentrated.

### Summary

| Metric | Value |
|--------|-------|
| Cascade episodes | 4 |
| Total benefit | $17,368 |
| G2 cost | $14,717 |
| Full BCR | 1.18 |
| LOO net ≥ 0 | 2/4 |
| Worst LOO net | $-10,797 |
| Top1 concentration | 77% |

---

## 6. Deliverables

| Artifact | Path |
|----------|------|
| Script | `scripts/overlayA_leave_one_out.py` |
| LOO CSV | `out_overlayA_conditional/leave_one_episode_out.csv` |
| This report | `reports/overlayA_leave_one_out.md` |

