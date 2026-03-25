# Step 2: Cascade KPIs — emergency_dd → Re-Enter → emergency_dd

**Script:** `out_v10_fix_loop/step2_cascade_analysis.py`
**Data:** `out_v10_fix_loop/v10_baseline_trades_harsh.csv` (103 trades), `v10_baseline_events_harsh.csv` (8,177 events)
**Scenario:** harsh (50 bps RT)
**Date:** 2026-02-24

---

## 1. Reentry Latency Distribution

After each of the 36 emergency_dd exits, how many H4 bars until the next entry?

| Metric | Value |
|--------|-------|
| N (emergency_dd exits) | 36 |
| With follow-up entry | 35 (97%) |
| **Minimum** | **4 bars** (16 hours) |
| P25 | 7 bars (28 hours) |
| **Median** | **12 bars** (2 days) |
| P75 | 16 bars (2.7 days) |
| P90 | 49 bars (8.2 days) |
| Max | 340 bars (56.7 days) |
| Mean | 34.5 bars (5.8 days) |

**Key finding:** The minimum re-entry latency is **4 bars** (not 1-3) because `exit_cooldown_bars=3`
blocks re-entry for 3 bars after any exit. The 4th bar is the first opportunity. Median re-entry
is 12 bars (2 days) — half of all emergency_dd exits are followed by a new position within 2 days.

### Latency histogram

| Bars | Trades | Mean PnL | ED again |
|------|--------|----------|----------|
| 4 | 2 | $-2,292 | 0/2 |
| 5 | 3 | $+4,410 | 2/3 |
| 6 | 2 | $+300 | 1/2 |
| 7 | 3 | $-1,695 | 2/3 |
| 8 | 2 | $-61 | 0/2 |
| 9 | 1 | $-742 | 1/1 |
| 10 | 2 | $-4,394 | 2/2 |
| 11 | 1 | $+17,000 | 0/1 |
| 12 | 5 | $-895 | 2/5 |
| 13-17 | 7 | $-33 | 1/7 |
| 25-51 | 3 | $-2,365 | 2/3 |
| 135-340 | 3 | $+399 | 0/3 |

The lat=5 and lat=11 outliers (one trade each: $+16,733 and $+17,000) dominate the positive mean
at certain K thresholds. Without them, the expectancy is consistently negative.

---

## 2. Cascade Rate

| K (bars) | N re-entries | Rate (% of 36) | Interpretation |
|----------|-------------|-----------------|----------------|
| ≤1 | 0 | 0.0% | Cooldown blocks |
| ≤2 | 0 | 0.0% | Cooldown blocks |
| ≤3 | 0 | 0.0% | Cooldown blocks (exit_cooldown_bars=3) |
| **≤4** | **2** | **5.6%** | First possible re-entry bar |
| ≤5 | 5 | 13.9% | |
| **≤6** | **7** | **19.4%** | ~1 in 5 emergency_dd → re-enter within 24h |
| ≤8 | 12 | 33.3% | |
| **≤10** | **15** | **41.7%** | |
| **≤12** | **21** | **58.3%** | Majority re-enter within 2 days |
| ≤18 | 28 | 77.8% | |
| ≤24 | 28 | 77.8% | Saturates at ~78% |

**Interpretation:** 58% of emergency_dd exits see re-entry within 12 bars (2 days). The cooldown
floor of 3 bars is the only brake — there is no additional "wait for conditions to improve" logic.

---

## 3. Expectancy of Quick Re-Entries

### 3.1 By K threshold

| K | N | Mean PnL | Median PnL | P10 PnL | P5 PnL | Total PnL | ED again % |
|---|---|----------|------------|---------|--------|-----------|------------|
| ≤4 | 2 | $-2,292 | $-2,292 | -$3,903 | -$3,903 | $-4,584 | 0% |
| ≤5 | 5 | $+1,729 | $-630 | -$3,732 | -$3,732 | $+8,647 | 40% |
| ≤6 | 7 | $+1,321 | **$-630** | -$3,446 | -$3,446 | $+9,246 | 43% |
| ≤8 | 12 | $+337 | **$-822** | -$4,190 | -$4,190 | $+4,038 | 42% |
| ≤10 | 15 | **$-366** | **$-1,015** | -$4,850 | -$4,850 | $-5,492 | **53%** |
| ≤12 | 21 | $+335 | **$-742** | -$5,212 | -$5,212 | $+7,030 | 48% |

### 3.2 Outlier sensitivity (K≤6)

| | N | Mean PnL | Median PnL | Total PnL |
|---|---|----------|------------|-----------|
| K≤6 all trades | 7 | $+1,321 | $-630 | $+9,246 |
| K≤6 **without outlier** | 6 | **$-1,248** | **$-1,127** | **$-7,487** |

The single outlier (trade #65, 2024-01-22, $+16,733, +27.67%) accounts for 181% of the K≤6 total PnL.
Removing it flips the mean from +$1,321 to **-$1,248**.

### 3.3 Verdict on expectancy

**Median is negative at every K threshold.** The positive mean at some K is driven by 1-2 outlier trades.
At K≤10 (the most populated threshold where outliers are diluted), both mean and median are negative
and 53% of re-entries end in another emergency_dd.

---

## 4. Fee Drag from Cascades

| K | Cascade Fees | % of Total Fees ($16,268) |
|---|-------------|--------------------------|
| ≤6 | $1,148 | 7.1% |
| ≤12 | $3,382 | **20.8%** |
| ≤18 | $4,437 | **27.3%** |

### Cascade chains (≥2 consecutive emergency_dd trades)

| Chain | Trades | Period | Total PnL | Fees | Regimes at entry |
|-------|--------|--------|-----------|------|-----------------|
| 1 | #8-9 | 2019-08 → 2019-08 | $-1,869 | $117 | BULL, CHOP |
| 2 | #11-12 | 2019-09 → 2019-09 | $-1,571 | $103 | CHOP, CHOP |
| 3 | #14-15 | 2019-11 → 2019-11 | $-2,449 | $76 | BULL, NEUTRAL |
| 4 | #25-26 | 2020-08 → 2020-09 | $-2,218 | $104 | BULL, BULL |
| 5 | #46-47 | 2021-11 → 2021-12 | $-9,490 | $344 | BULL, NEUTRAL |
| 6 | #55-56 | 2023-07 → 2023-08 | $-5,169 | $311 | BULL, TOPPING |
| **7** | **#69-74** | **2024-05 → 2024-08** | **$-26,686** | **$1,315** | BULL→TOPPING→BULL... |
| **8** | **#86-88** | **2025-01 → 2025-02** | **$-21,689** | **$820** | CHOP, CHOP, BULL |
| 9 | #97-98 | 2025-08 → 2025-09 | $-5,954 | $577 | TOPPING, BULL |

| Metric | Value |
|--------|-------|
| Trades in chains | 23 / 103 (22.3%) |
| **Chain total PnL** | **$-77,093** (82% of total net PnL destroyed) |
| Chain total fees | $3,767 (23.2% of all fees) |
| Chain mean PnL per trade | $-3,352 |

**Chain #7** (2024-05 → 2024-08, 6 consecutive emergency_dd) alone loses $26,686 — 28% of total strategy PnL.
**Chain #8** (2025-01 → 2025-02, 3 trades) loses $21,689. These two chains together destroy $48,375 (51% of total PnL).

---

## 5. Baseline Comparison: emergency_dd vs Other Exits

| | emergency_dd (N=36) | Other exits (N=67) |
|---|---|---|
| Mean PnL | **$-3,184** | $+3,114 |
| Median PnL | **$-2,780** | $+1,074 |
| Total PnL | **$-114,637** | $+208,663 |
| Total fees | $5,646 (34.7%) | $10,622 (65.3%) |
| PnL per $ fee | -$20.30 | +$19.64 |

emergency_dd trades as a class have -$20 of PnL per $1 of fees paid. They account for **35% of all trades
but 100%+ of all losses** (the strategy is profitable only because non-emergency_dd trades overcome the damage).

---

## 6. Conclusion

**Re-enter nhanh sau emergency_dd là negative expectancy.**

Evidence:
1. **Median PnL is negative at every K threshold** (K=4 through K=24). The positive mean at some K
   is entirely driven by 1-2 outlier trades that happened to catch bull reversals.

2. **43-53% of quick re-entries end in another emergency_dd** — the cascade is self-reinforcing.
   The strategy re-enters the same declining market that just stopped it out.

3. **9 cascade chains** (≥2 consecutive emergency_dd) contain 23 trades (22% of total) and destroy
   **$77,093** — equivalent to 82% of the strategy's total net PnL being given back.

4. **Fee drag is substantial:** cascade trades (K≤12) consume 20.8% of total fees while producing
   net-negative returns.

5. **The 3-bar cooldown is insufficient.** It prevents re-entry within 12 hours but 58% of
   emergency_dd exits still re-enter within 2 days (12 bars). The underlying cause — VDO momentum
   remaining positive during BULL-regime corrections — is not addressed by a time-based cooldown.

**Root cause:** After emergency_dd exit, the D1 regime is still RISK_ON (BULL) and H4 VDO is
often still positive (corrections don't immediately flip momentum). The strategy sees valid entry
conditions and re-enters, only to hit the same portfolio DD → emergency_dd again.

---

## 7. Data Files

| File | Description |
|------|-------------|
| `out_v10_fix_loop/step2_reentry_latency.csv` | 36 rows: each emergency_dd exit with latency to next entry |
| `out_v10_fix_loop/step2_cascade_expectancy.csv` | 11 rows: cascade metrics at K ∈ {1,2,3,4,5,6,8,10,12,18,24} |
| `out_v10_fix_loop/step2_cascade_analysis.py` | Analysis script |
