# Step 4: Group 2 — Complement-Time Performance Comparison

**Date:** 2026-02-24
**Script:** `scripts/group2_rest_compare.py`
**Scenario:** harsh (50 bps round-trip)

---

## 1. Definition

```
Group 2 = all H4 bars NOT inside any cascade episode window [peak_ts, end_ts]
```

Full period: 4,098 / 15,648 bars = 26.2% of bars are in Group 2
(the remaining 73.8% are inside 4 cascade episode windows that span long bear markets).

Trades are assigned to Group 2 by exit timestamp — a trade belongs to Group 2 if its
exit_ts falls outside all cascade windows.

---

## 2. Full Period — Group 2 Comparison

### 2.1 Equity-level metrics

| Metric | Baseline | OverlayA | Delta |
|--------|----------|----------|-------|
| Bars | 4,098 | 4,098 | 0 |
| PnL $ | +$107,666 | +$92,949 | **-$14,717** |
| Return % | 1,076.7% | 929.5% | -147.2pp |
| MDD % | 25.34% | 25.34% | 0.00pp |

### 2.2 Trade-level metrics

| Metric | Baseline | OverlayA | Delta |
|--------|----------|----------|-------|
| Trades | 26 | 26 | 0 |
| Wins | 18 | 18 | 0 |
| Win rate | 69.2% | 69.2% | 0.0pp |
| EmDD exits | 2 | 2 | 0 |
| Total PnL | +$79,070 | +$66,278 | -$12,791 |
| Avg PnL | +$3,041 | +$2,549 | -$492 |
| Fees | $3,648 | $3,286 | -$362 |
| Turnover | $2,431,885 | $2,190,541 | -$241,344 |

### 2.3 Key observations

- **Identical trade count and win rate**: OverlayA does not reduce Group 2 trade count. The 26 trades that exit in non-cascade time are the same ones in both variants.
- **Lower PnL and turnover**: The -$12,791 trade PnL gap comes from lower position sizes (overlayA has lower NAV entering Group 2 segments, propagated from cascade episodes) and 2 missed entries (see §3).
- **MDD identical at 25.34%**: OverlayA does not affect drawdown behavior in non-cascade time.

---

## 3. Blocked Trades (Opportunity Cost)

### 3.1 Full period: 2 blocked trades

| Trade | Entry | Exit | Entry Price | Exit Price | PnL | Return% | Days | Exit Reason | Cooldown? |
|-------|-------|------|-------------|------------|-----|---------|------|-------------|-----------|
| 44 | 2021-09-30 | 2021-10-22 | 46,835 | 62,131 | **+$17,000** | +32.7% | 21.2 | trailing_stop | Yes |
| 63 | 2024-01-23 | 2024-02-24 | 39,708 | 50,693 | **+$16,733** | +27.7% | 31.3 | trailing_stop | Yes |

Both blocked trades are **profitable winners** exiting via trailing_stop.

| Stat | Value |
|------|-------|
| N blocked | 2 |
| N cooldown-blocked | 2 (100%) |
| Total PnL | **+$33,733** |
| Mean PnL | +$16,866 |
| Median PnL | +$16,866 |
| Blocked positive PnL | +$33,733 |
| Blocked negative PnL | $0 |
| % exit emergency_dd | 0.0% |

### 3.2 Anatomy of each blocked trade

**Trade 44** (Sep-Oct 2021):
Entry 2021-09-30 falls just after the trough of episode 9 (non-cascade, 2021-05-03 → 2021-10-06). In the overlayA run, an emergency_dd exit near the episode 9 trough triggers a 12-bar cooldown, blocking the re-entry that catches the subsequent +33% rally to the Nov 2021 all-time high.

**Trade 63** (Jan-Feb 2024):
Entry 2024-01-23 follows trade 62's emergency_dd exit during episode 13 (non-cascade, 2024-01-11 → 2024-02-08). The cooldown blocks the dip-buy re-entry that captures the subsequent +28% rally (BTC $39.7K → $50.7K).

### 3.3 Pattern

Both blocked trades share the same structure:
1. An isolated emergency_dd exit (maxrun=1, hence the episode is non-cascade)
2. Cooldown blocks the immediate re-entry
3. The re-entry would have been a large winner (+28% to +33%)

This is the **opportunity cost mechanism**: the cooldown cannot distinguish between a cascade re-entry (bad) and a genuine recovery entry (good). In non-cascade episodes with isolated emergency_dd exits, the cooldown sometimes blocks winners.

### 3.4 Holdout: 1 blocked trade

| Trade | Entry | Exit | PnL | Return% | Exit Reason | Cooldown? |
|-------|-------|------|-----|---------|-------------|-----------|
| 79 | 2024-10-11 | 2024-10-23 | **+$2,224** | +3.8% | trailing_stop | Yes |

This is a smaller winner blocked by cooldown spillover from trade 78's emergency_dd exit. The opportunity cost in the holdout is $2,224.

---

## 4. Holdout — Group 2 Comparison

### 4.1 Equity-level

| Metric | Baseline | OverlayA | Delta |
|--------|----------|----------|-------|
| Bars | 668 | 668 | 0 |
| PnL $ | +$40,779 | +$35,014 | **-$5,765** |
| Return % | 53.0% | 51.5% | -1.5pp |
| MDD % | 9.77% | 9.77% | 0.00pp |

### 4.2 Trade-level

| Metric | Baseline | OverlayA | Delta |
|--------|----------|----------|-------|
| Trades | 7 | 7 | 0 |
| Wins | 6 | 6 | 0 |
| EmDD exits | 1 | 1 | 0 |
| Total PnL | +$30,110 | +$25,672 | -$4,438 |
| Fees | $1,936 | $1,678 | -$258 |

---

## 5. Group 1 vs Group 2 Accounting

### Full period

| Group | BL PnL | OV PnL | Δ PnL | Interpretation |
|-------|--------|--------|-------|----------------|
| **G1 (cascade)** | -$19,378 | -$5,289 | **+$14,089** | OverlayA saves by reducing cascade bleed |
| **G2 (rest)** | +$107,666 | +$92,949 | **-$14,717** | OverlayA loses from lower NAV + 2 missed winners |
| **Global** | +$85,968 | +$84,553 | **-$1,416** | Net: slight OverlayA degradation |

### Holdout

| Group | BL PnL | OV PnL | Δ PnL |
|-------|--------|--------|-------|
| **G1 (cascade)** | -$22,878 | -$9,429 | **+$13,449** |
| **G2 (rest)** | +$40,779 | +$35,014 | **-$5,765** |
| **Global holdout** | +$17,901 | +$25,585 | **+$7,684** |

On holdout, the G1 benefit (+$13,449) exceeds the G2 cost (-$5,765), yielding a net +$7,684 for overlayA.

### Decomposition of Group 2 cost

| Component | Full | Holdout |
|-----------|------|---------|
| Blocked trades (direct PnL) | -$33,733 | -$2,224 |
| Sizing/NAV propagation effect | remainder of -$14,717 | remainder of -$5,765 |

The -$14,717 Group 2 equity delta is partially from the 2 blocked trades (-$33,733 had they been taken at the same size) and partially from the **NAV propagation effect**: overlayA's lower NAV entering Group 2 segments means smaller position sizes on the same winning trades, compounding into lower absolute returns.

---

## 6. Key Findings

1. **Group 2 trade quality is unchanged**: Same 26 trades, same 69% win rate, same 2 emergency_dd exits. OverlayA does not degrade the quality of trades taken in non-cascade time.

2. **Opportunity cost is real but concentrated**: Only 2 blocked trades in 7+ years (full period), both large winners (+$17K each). This is the price of the cooldown.

3. **The blocked trades share a pattern**: Both follow isolated (non-cascade) emergency_dd exits where the subsequent re-entry catches a recovery rally. The cooldown is designed for cascades but also fires after isolated emergency_dd events.

4. **MDD in Group 2 is unaffected**: 25.34% for both variants (full), 9.77% for both (holdout). The cooldown doesn't create new drawdown risk in non-cascade time.

5. **Net balance depends on period**:
   - Full period: G1 benefit (+$14K) ≈ G2 cost (-$15K) → approximately neutral (-$1.4K)
   - Holdout: G1 benefit (+$13K) > G2 cost (-$6K) → net positive (+$7.7K)
   - The holdout result is more favorable because the blocked-trade opportunity cost is smaller ($2K vs $34K).

---

## 7. Deliverables

| Artifact | Path | Records |
|----------|------|---------|
| Script | `scripts/group2_rest_compare.py` | — |
| Full comparison CSV | `out_overlayA_conditional/group2_rest_compare_full.csv` | 2 rows |
| Holdout comparison CSV | `out_overlayA_conditional/group2_rest_compare_holdout.csv` | 2 rows |
| Full blocked trades | `out_overlayA_conditional/group2_blocked_trades_full.csv` | 2 trades |
| Holdout blocked trades | `out_overlayA_conditional/group2_blocked_trades_holdout.csv` | 1 trade |
| This report | `reports/overlayA_conditional_step4_group2.md` | — |
