# Research Q1: Window 5 Deep Dive (X6 vs X0)

**Date**: 2026-03-08
**Question**: Window 5 (2024-07 → 2025-01) has delta -100.14, pulling WFO from 5/8 to 4/8 and flipping verdict from PASS to FAIL. Analyze trades, PnL, regime, and counterfactual scenarios.

---

## 1. Window 5 Summary Metrics

| Metric | X6 (candidate) | X0 (baseline) | Delta |
|--------|:--------------:|:-------------:|:-----:|
| Sharpe | 1.8786 | 2.5046 | -0.6260 |
| CAGR% | 83.22 | 120.77 | -37.55 |
| MDD% | 14.72 | 13.30 | +1.42 |
| Trades | 8 | 12 | -4 |
| Score | 225.05 | 325.18 | **-100.14** |

Both strategies are profitable — X6 earns 83% annualized. But X0 earns 121%. The delta is massive because the score formula amplifies the CAGR gap.

---

## 2. Trade-by-Trade Breakdown

### X6 (8 trades, sum of returns: +38.66%)

| # | Entry | Exit | Return | PnL | Days | Exit Reason | Regime |
|---|-------|------|-------:|----:|-----:|-------------|--------|
| T106 | Jul 16 | Jul 25 | +0.76% | +$1,494 | 8.8 | trail_stop | BULL |
| T107 | Jul 26 | Jul 30 | -0.90% | -$2,570 | 4.3 | trail_stop | BULL |
| T108 | Aug 23 | Aug 27 | +0.09% | -$156 | 4.0 | trail_stop | BULL |
| T109 | Sep 15 | Oct 1 | +4.75% | +$11,133 | 15.3 | trail_stop | CHOP |
| T110 | Oct 1 | Oct 2 | -5.25% | -$13,652 | 0.7 | trail_stop | TOPPING |
| T111 | Oct 7 | Oct 9 | -4.12% | -$10,209 | 2.7 | trail_stop | BULL |
| **T112** | **Oct 13** | **Nov 3** | **+8.59%** | **+$19,271** | **20.8** | **BE STOP** | **BULL** |
| **T113** | **Nov 3** | **Dec 20** | **+34.74%** | **+$85,488** | **46.7** | **BE STOP** | **BULL** |

### X0 (12 trades, sum of returns: +50.06%)

| # | Entry | Exit | Return | PnL | Days | Exit Reason | Regime |
|---|-------|------|-------:|----:|-----:|-------------|--------|
| T137 | Jul 16 | Jul 25 | +0.76% | +$943 | 8.8 | trail_stop | BULL |
| T138 | Jul 26 | Jul 30 | -0.90% | -$1,622 | 4.3 | trail_stop | BULL |
| T139 | Aug 23 | Aug 27 | +0.09% | -$99 | 4.0 | trail_stop | BULL |
| T140 | Sep 15 | Sep 16 | -4.26% | -$6,734 | 1.0 | trail_stop | CHOP |
| T141 | Sep 16 | Sep 30 | +9.92% | +$14,245 | 13.7 | trail_stop | CHOP |
| T142 | Sep 30 | Oct 2 | -4.42% | -$7,299 | 1.2 | trail_stop | BULL |
| T143 | Oct 7 | Oct 9 | -4.12% | -$6,510 | 2.7 | trail_stop | BULL |
| T144 | Oct 13 | Oct 23 | +6.17% | +$8,757 | 10.0 | trail_stop | BULL |
| T145 | Oct 24 | Oct 31 | +2.40% | +$3,473 | 7.0 | trail_stop | BULL |
| T146 | Nov 2 | Nov 25 | +35.92% | +$56,271 | 23.0 | trail_stop | BULL |
| T147 | Nov 26 | Dec 9 | +5.47% | +$11,346 | 12.8 | trail_stop | BULL |
| T148 | Dec 9 | Dec 19 | +3.02% | +$6,437 | 9.2 | trail_stop | BULL |

---

## 3. Mechanistic Divergence (4 Phases)

### Phase 1: Jul–Aug (IDENTICAL)
Trades T106-T108 / T137-T139 are identical entries and exits. Both use 3×ATR trail in this gain range (<5%). Net: -0.05% both sides.

### Phase 2: Sep 15 (FIRST DIVERGENCE)
- **X6 T109**: Entered Sep 15 in CHOP regime. Adaptive trail held through Sep 16 dip → exited Oct 1 at +4.75%
- **X0 T140**: Same entry. Fixed 3×ATR trail tighter → stopped out Sep 16 at -4.26%, then **re-entered T141** on Sep 16 at better price → exited Sep 30 at +9.92%
- **X0 net: +5.66% vs X6 +4.75%** (gap: +0.9% for X0)

**Mechanism**: X0's tighter stop generated a whipsaw loss but immediately re-entered at a reset trailing stop, capturing +9.92% on the recovery. X6 held through the dip but missed the re-entry reset.

### Phase 3: Oct 1–9 (SIMILAR LOSSES)
- X6: -5.25% + -4.12% = -9.38%
- X0: -4.42% + -4.12% = -8.54%
- Gap: +0.84% for X0

### Phase 4: Oct 13 → Dec 20 (THE MAIN EVENT — 85% of total gap)

**X6 (2 trades, +43.33%)**:
- T112: Oct 13 → Nov 3 at +8.59% (**BE stop** — breakeven floor triggered on pullback)
- T113: Nov 3 → Dec 20 at +34.74% (**BE stop** — held through the entire BTC rally)

**X0 (5 trades, +52.99%)**:
- T144: Oct 13 → Oct 23 at +6.17% (trail stop on pullback)
- T145: Oct 24 → Oct 31 at +2.40% (re-entry, short swing)
- T146: Nov 2 → Nov 25 at +35.92% (main rally leg)
- T147: Nov 26 → Dec 9 at +5.47% (re-entry after Nov 25 pullback)
- T148: Dec 9 → Dec 19 at +3.02% (re-entry, last swing)

**Gap: +9.66% for X0**

**Root cause**: X0's fixed 3×ATR trail exit-and-re-enters during intra-rally pullbacks. Each re-entry resets the trailing stop from a new peak price. This creates a "ratchet" effect that compounds gains across 5 trades instead of X6's 2 trades. X6's adaptive trail (wider at high gains) holds positions open through pullbacks but misses the re-entry compounding.

---

## 4. Regime Breakdown in W5

| Strategy | Regime | Trades | Total Return | Avg Return |
|----------|--------|:------:|:------------:|:----------:|
| X6 | BULL | 6 | +39.16% | +6.53% |
| X6 | CHOP | 1 | +4.75% | +4.75% |
| X6 | TOPPING | 1 | -5.25% | -5.25% |
| X0 | BULL | 10 | +44.40% | +4.44% |
| X0 | CHOP | 2 | +5.66% | +2.83% |

D1 EMA(21) regime was active (BULL) for most of the window. This was a strong trending environment where X0's exit-and-re-enter mechanism excelled.

---

## 5. Matched vs Unmatched Trades

Of 12 X0 trades, only **6 are matched** (same entry bar as an X6 trade). The other 6 are **X0-only re-entries** that X6 never generates:

| X0 Trade | Entry | Return | Note |
|----------|-------|-------:|------|
| T141 | Sep 16 | +9.92% | Re-entry after T140 stop-out |
| T142 | Sep 30 | -4.42% | Re-entry (whipsaw loss) |
| T145 | Oct 24 | +2.40% | Re-entry after T144 stop-out |
| T146 | Nov 2 | +35.92% | Re-entry — captured main rally |
| T147 | Nov 26 | +5.47% | Re-entry after pullback |
| T148 | Dec 9 | +3.02% | Re-entry — last swing |

Net of unmatched: +52.31% — these re-entries are overwhelmingly profitable because the macro trend (BULL) remained intact.

---

## 6. Counterfactual Scenarios

### Scenario A: Exclude W5 (7 windows)

| Metric | Value |
|--------|-------|
| Positive delta windows | 4/7 = **57.1%** |
| WFO gate (≥60%) | **STILL FAIL** |
| Mean delta | +25.67 |
| Median delta | +9.27 |
| Worst delta | -10.00 (W0) |

Excluding W5 is not enough — W0 and W7 are still negative. 4/7 = 57.1% < 60%.

### Scenario B: Only 2023+ windows (W2–W7)

| Window | Period | Delta | Verdict |
|--------|--------|------:|---------|
| W2 | 2023H1 | +9.27 | WIN |
| W3 | 2023H2 | +99.40 | WIN |
| W4 | 2024H1 | +73.51 | WIN |
| W5 | 2024H2 | -100.14 | LOSE |
| W6 | 2025H1 | +13.38 | WIN |
| W7 | 2025H2 | -5.90 | LOSE |

| Metric | Value |
|--------|-------|
| Positive delta windows | 4/6 = **66.7%** |
| WFO gate (≥60%) | **PASS** |
| Mean delta | +14.92 |
| Median delta | +11.32 |

### Scenario C: 2023+ excluding W5 (W2,W3,W4,W6,W7)

| Metric | Value |
|--------|-------|
| Positive delta windows | 4/5 = **80.0%** |
| WFO gate (≥60%) | **PASS** |
| Mean delta | +37.93 |
| Median delta | +13.38 |
| Worst delta | -5.90 (W7) |

---

## 7. Key Findings

1. **W5 is not an outlier in isolation** — it exposes a genuine structural weakness. X6's adaptive trail (wider at high gains) sacrifices re-entry compounding during sustained rallies. This is not a fluke; it's the design operating as intended, just in a regime where X0's simpler mechanism wins.

2. **Excluding W5 alone doesn't save X6** — WFO would still be 4/7 = 57.1% (FAIL). W0 (-10.0) and W7 (-5.9) are also negative. X6 needs at least 5/8 positive windows.

3. **2023+ subset favors X6** — 4/6 = 66.7% PASS. The 2022 bear market (W0, W1) hurts X6 because fewer trades trigger the adaptive trail, but both strategies lose similarly.

4. **The gap is concentrated in Phase 4 (Oct–Dec 2024)** — 85% of the return gap comes from X0's 5-trade ratchet vs X6's 2-trade hold. This is the BTC ETF rally period where strong trends with intra-trend pullbacks create the ideal environment for X0's exit-and-re-enter pattern.

5. **X6's BE stops fired correctly** — T112 and T113 exited at breakeven floor, which protected capital. But the protection came at the cost of missing re-entry opportunities that X0 captured.

6. **Absolute PnL favors X6** ($90.8k vs $79.2k) because X6 had higher NAV from earlier windows. But **percentage returns favor X0** (50.06% vs 38.66%), which is what the WFO score uses.
