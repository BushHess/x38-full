# OverlayA v2 Results: Baseline vs V1 vs V2

**Date:** 2026-02-24
**Scenario:** harsh (50 bps RT)

| Config | Description |
|--------|-------------|
| **baseline** | No cooldown (K=0) |
| **v1_K12** | Flat cooldown K=12 H4 bars (48h) — best holdout from C6 |
| **v2_escalating** | Escalating: short=3 (12h) / long=12 (48h) / lookback=24 (96h) / trigger=2 |

**Cascade episodes:** Full=4, Holdout=1

---

## 1. Full Period (2019-01 → 2026-02)

| Metric | baseline | v1 (K=12) | v2 (escalating) | v2 vs v1 Δ |
|--------|--------:|---------:|----------------:|-----------:|
| **G1 Benefit** | $0 | $17,368 | $0 | $-17,368 |
| **G2 Cost** | $0 | $14,717 | $0 | $-14,717 |
| **Net** | $0 | $-1,416 | $-11,728 | $-10,312 |
| **BCR** | — | 1.18 | 0.00 | — |
| **Top1 %** | — | 77% | 0% | — |
| **Top2 %** | — | 100% | 0% | — |
| **#Blocked Winners** | 0 | 2 | 0 | -2 |
| **Blocked Win PnL** | $0 | $+33,733 | $+0 | $-33,733 |
| **G1 Δ Total** | $0 | $+11,759 | $-11,728 | $-23,487 |
| **G2 Δ** | $0 | $-14,717 | $+0 | $+14,717 |
| **Trades** | 103 | 99 | 102 | +3 |
| **Final NAV** | $95,968.45 | $94,552.53 | $84,240.37 | — |

---

## 2. Holdout Period (2024-10 → 2026-02)

| Metric | baseline | v1 (K=12) | v2 (escalating) | v2 vs v1 Δ |
|--------|--------:|---------:|----------------:|-----------:|
| **G1 Benefit** | $0 | $13,449 | $0 | $-13,449 |
| **G2 Cost** | $0 | $5,765 | $0 | $-5,765 |
| **Net** | $0 | $+7,684 | $-11,728 | $-19,412 |
| **BCR** | — | 2.33 | 0.00 | — |
| **#Blocked Winners** | 0 | 1 | 0 | -1 |
| **Blocked Win PnL** | $0 | $+2,224 | $+0 | $-2,224 |
| **Trades** | 26 | 24 | 25 | +1 |

---

## 3. Analysis

### 3.1 Does v2 reduce Group2 cost?

**YES.** V2 reduces G2 cost by $14,717 (100%) on full period.

Holdout: V2 reduces cost by $5,765 (100%).

### 3.2 Does v2 retain Group1 benefit?

**NO — significant benefit loss.** V2 retains only 0% of V1 benefit.

Holdout: V2 retains 0% ($0 vs $13,449).

### 3.3 Blocked winners impact

| Period | V1 blocked | V2 blocked | Δ count | Δ PnL |
|--------|----------:|----------:|--------:|------:|
| Full | 2 ($+33,733) | 0 ($+0) | -2 | $-33,733 |
| Holdout | 1 ($+2,224) | 0 ($+0) | -1 | $-2,224 |

V2 unblocks 2 winner(s) worth $33,733 — the isolated-ED recovery trades that the escalating cooldown correctly allows through.

### 3.4 Net improvement

| Period | V1 Net | V2 Net | Δ Net |
|--------|-------:|-------:|------:|
| Full | $-1,416 | $-11,728 | $-10,312 |
| Holdout | $+7,684 | $-11,728 | $-19,412 |

V2 net is worse by $10,312 on full period.

---

## 4. Verdict

### FAIL

V2 lost too much benefit (0% retained). The escalating cooldown's short window is not long enough to protect in some cascade episodes.

### Summary

| Question | Answer |
|----------|--------|
| V2 reduces G2 cost? | YES (Δ=$-14,717) |
| V2 retains G1 benefit? | NO (0%) |
| V2 improves net? | NO (Δ=$-10,312) |
| V2 unblocks winners? | YES (-2) |
| Holdout confirms? | NO (Δ=$-19,412) |

---

## 5. Root Cause Analysis

### Why short_cooldown=3 provides zero cascade protection

The V8Apex strategy has `exit_cooldown_bars=3` (Gate 2), which already blocks re-entry for 3 bars after ANY exit. The escalating cooldown's `short_cooldown_bars=3` (Gate 0) overlaps with this existing gate:

```
After emergency_dd exit at bar N:
  Gate 0 (overlay):  blocks N, N+1       (short_cooldown=3, decremented immediately → effective 2 bars)
  Gate 2 (exit cd):  blocks N, N+1, N+2  (exit_cooldown_bars=3, checks idx - last_exit < 3)
  Net effect:        Gate 2 is the binding constraint → overlay adds nothing
```

Because `short_cooldown_bars ≤ exit_cooldown_bars`, the first ED exit triggers NO additional blocking. The strategy re-enters at the same time as baseline. Only after a 2nd ED exit does the long cooldown activate — but by then, the cascade damage is done.

### Evidence:

- V2 trades: 102 vs baseline: 103 (only 1 trade(s) blocked)
- V1 trades: 99 vs baseline: 103 (blocked 4 trades)
- V2 G1 Δ Total: $-11,728 (V2 is WORSE than baseline in cascade episodes)

### Cascade episode flow comparison

```
Typical 4-ED cascade:  ED₁ → ED₂ → ED₃ → ED₄

Baseline (K=0):        ✗     ✗     ✗     ✗    (takes all 4 losses)
V1 (K=12):             ✗     ○     ○     ○    (blocks 3, saves ~$17k)
V2 (short=3, long=12): ✗     ✗     ○     ○    (allows 2nd hit, then blocks)

✗ = loss taken   ○ = blocked by cooldown
```

V2 takes one extra loss per cascade compared to V1. With 4 cascade episodes, this adds up to a significant penalty that wipes out the benefit from unblocking isolated recovery winners.

### Fix options

1. **Increase short_cooldown to 6+** — ensures Gate 0 is the binding constraint after the first ED, providing partial protection even for isolated exits
2. **Use cascade_trigger_count=1** with conditional short/long logic — apply longer cooldown from the first ED if market context suggests cascade risk
3. **Stay with V1 (K=12)** — the flat cooldown is simpler and the opportunity cost ($33,733 blocked winners) is the known trade-off for $17,368 cascade protection

---

## 6. Deliverables

| Artifact | Path |
|----------|------|
| Script | `scripts/overlayA_compare_v1_v2.py` |
| Full CSV | `out_overlayA_conditional/compare_v1_v2_full.csv` |
| Holdout CSV | `out_overlayA_conditional/compare_v1_v2_holdout.csv` |
| This report | `reports/overlayA_v2_results.md` |

