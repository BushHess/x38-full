# OverlayA Final Decision

**Date:** 2026-02-24
**Scenario:** harsh (50 bps RT)
**Candidates evaluated:** V1 (K=12), V2 (escalating short=3/long=12)

---

## 1. Decision Criteria (from C11 prompt)

| # | Criterion | Threshold |
|--:|:----------|:----------|
| 1 | Full period net | ≥ $0 (ε = -$500) |
| 2 | Holdout net | ≥ $0 (no flip negative) |
| 3 | BCR | > 1.0 |
| 4 | Concentration top1 | ≤ 70% (else LOO must not flip strongly negative) |
| 5 | Blocked winners PnL | ≤ 20% of total benefit |

---

## 2. V2 (Escalating) — Pre-Eliminated

V2 was eliminated in C9. Short cooldown (3 bars) is redundant with the strategy's existing `exit_cooldown_bars=3` (Gate 2). Result: benefit=$0, net=-$11,728. **All criteria fail.**

No further evaluation needed.

---

## 3. V1 (K=12) — Full Evaluation

### 3.1 Criterion-by-criterion

| # | Criterion | Threshold | Full Period | Holdout | Result |
|--:|:----------|:----------|:------------|:--------|:------:|
| 1 | Net ≥ 0 (ε=-500) | ≥ -$500 | **-$1,416** | +$7,684 | **FAIL** |
| 2 | Holdout net ≥ 0 | ≥ $0 | — | +$7,684 | PASS |
| 3 | BCR > 1.0 | > 1.0 | 1.18 | 2.33 | PASS |
| 4 | Top1 ≤ 70% | ≤ 70% | **77%** → LOO check | 100% (1 ep) | **FAIL** |
| 5 | Blocked win ≤ 20% benefit | ≤ 20% | **194%** | 17% | **FAIL** |

### 3.2 Criterion 1: Full period net

- Full net = -$1,416 (below -$500 epsilon)
- Benefit = $17,368, Cost = $14,717 → net negative because G2 cost exceeds G1 benefit
- Global net (including indirect effects) = -$1,416

**FAIL.** The overlay destroys more value in non-cascade periods than it saves in cascade periods.

### 3.3 Criterion 4: Concentration + LOO

- Top1 concentration = 77% (EP17, 2025-01-20)
- Since >70%, LOO test required:

| Excluded EP | LOO Net | BCR | Verdict |
|:------------|--------:|----:|:-------:|
| EP4 | +$2,651 | 1.18 | OK |
| EP12 | +$2,651 | 1.18 | OK |
| EP15 | **-$1,268** | 0.91 | NEGATIVE |
| EP17 | **-$10,797** | 0.27 | STRONGLY NEGATIVE |

Removing EP17 (the dominant episode) makes net = -$10,797. Removing EP15 also flips negative.

**LOO net ≥ 0 in only 2/4 scenarios.** The overlay is not robust.

Additionally, 2/4 cascade episodes show overlay performing **worse** than baseline:
- EP4: overlay Δ = -$1,810 (overlay lost more)
- EP12: overlay Δ = -$3,799 (overlay lost more)

The overlay only helps in episodes where the cascade is deep enough that blocking multiple re-entries saves more than the opportunity cost. In shallower cascades, the blocked trades would have recovered.

### 3.4 Criterion 5: Blocked winners

- Blocked winners: 5 trades, PnL = $+38,709 (from C7 diagnosis)
- Grid-counted blocked winners: 2 trades, PnL = $+33,733 (within cascade episodes)
- Total benefit: $17,368

Ratio (grid): $33,733 / $17,368 = **194%**
Ratio (all): $38,709 / $17,368 = **223%**

**FAIL.** The blocked winners PnL is nearly **2x the total benefit**. The cooldown blocks more profitable trades than it saves in cascade protection.

From C7 diagnosis:
- All 5 blocked winners exit via trailing_stop (legitimate recovery trades)
- 8/10 blocked losers exit via emergency_dd (cascade re-entries, correctly blocked)
- The cooldown correctly blocks cascade re-entries but the collateral damage to recovery trades is too high

---

## 4. Alternative K Values

For completeness, checking if any other K from C6 grid passes all criteria:

| K | Full Net | Holdout Net | BCR | Top1% | Blocked Win PnL | BW/Benefit |
|--:|--------:|-----------:|----:|------:|----------------:|-----------:|
| 0 | $0 | $0 | — | — | $0 | — |
| 3 | $0 | $0 | — | — | $0 | — |
| 6 | +$956 | +$541 | ∞ | 50% | $0 | 0% |
| 9 | -$9,575 | +$2,275 | 0.50 | 100% | $16,733 | 177% |
| 12 | -$1,416 | +$7,684 | 1.18 | 77% | $33,733 | 194% |
| 18 | -$16,829 | -$3,864 | 0.94 | 80% | $51,735 | 270% |

**K=6** is the only value that passes all five criteria:

| # | Criterion | K=6 Value | Result |
|--:|:----------|:----------|:------:|
| 1 | Full net ≥ -$500 | +$956 | PASS |
| 2 | Holdout net ≥ 0 | +$541 | PASS |
| 3 | BCR > 1.0 | ∞ (cost=0) | PASS |
| 4 | Top1 ≤ 70% | 50% (full) | PASS |
| 5 | BW ≤ 20% benefit | 0% | PASS |

However, K=6 has **negligible benefit**: $699 (full), $324 (holdout). The overlay barely does anything — it blocks zero losers and zero winners. The net improvement ($956 full) is within noise range for a 7-year backtest. This is effectively equivalent to no overlay.

---

## 5. Verdict

### REJECT

> **OverlayA (post-emergency-dd cooldown) does not meet promotion criteria at any K value.**

### Reasoning

| Factor | Evidence |
|:-------|:---------|
| **Net negative (full)** | V1 K=12 net = -$1,416; V2 net = -$11,728 |
| **Concentration risk** | 77% of benefit from one episode (EP17, Jan 2025) |
| **Not robust (LOO)** | Removing EP17 → net = -$10,797; 2/4 LOO negative |
| **Excessive collateral** | Blocked winners PnL ($33,733) = 194% of benefit ($17,368) |
| **2/4 episodes hurt** | EP4 and EP12: overlay worse than baseline by $1,810 and $3,799 |
| **V2 fundamentally flawed** | Short cooldown redundant with exit_cooldown_bars; 0% benefit |
| **K=6 is noise** | Benefit $699 on 7-year backtest ≈ statistical noise |

### Core problem

The emergency_dd cooldown faces an unavoidable trade-off:
- **Too short (K≤6):** Provides negligible cascade protection
- **Too long (K≥9):** Blocks legitimate recovery trades whose PnL exceeds the cascade savings
- **Escalating (V2):** Short window is redundant with existing exit cooldown

There is no K value in the tested grid that provides meaningful cascade protection without excessive opportunity cost. The overlay is **structurally unviable** for this strategy.

---

## 6. Recommendation

| Action | Detail |
|:-------|:-------|
| **Do not deploy OverlayA** | Set `cooldown_after_emergency_dd_bars = 0` in production config |
| **Keep code in codebase** | The escalating cooldown machinery (V2) is clean and tested; keep for future use |
| **Explore alternatives** | If cascade protection is still desired, consider position-sizing overlays (reduce size after ED) rather than entry-blocking overlays |

---

## 7. Evidence Trail

| Step | Report | Key Finding |
|:-----|:-------|:------------|
| C6 | Grid search | K=12 best holdout (BCR 2.33) but full net negative |
| C7 | Blocked winners | 5 winners ($38,709) all trailing_stop; 8/10 losers emergency_dd |
| C8 | V2 implementation | Escalating cooldown state machine + 14 unit tests |
| C9 | V1 vs V2 | V2 FAIL — short_cooldown redundant with exit_cooldown_bars |
| C10 | Leave-one-out | V1 FAIL — 77% concentration, 2/4 LOO negative |
| **C11** | **This report** | **REJECT — no viable K value** |

---

## 8. Deliverables

| Artifact | Path |
|----------|------|
| This report | `reports/overlayA_final_decision.md` |
| Decision JSON | `out_overlayA_conditional/decision.json` |
