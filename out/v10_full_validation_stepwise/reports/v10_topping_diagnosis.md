# V10 Drawdown Episode Diagnosis

**Script:** `out_v10_full_validation_stepwise/scripts/v10_dd_episodes.py`
**Data:** `out_v10_full_validation_stepwise/v10_dd_episodes.csv`, `v10_dd_episodes.json`
**Scenario:** harsh (50 bps RT)
**Period:** 2019-01-01 → 2026-02-20 (warmup 365 d)

---

## 1. Question

> V10 không có late-bull trigger. Vậy cơ chế nào gây đau nhất khi thị trường topping/correction?

**Short answer:** TOPPING regime itself is nearly irrelevant (3.8% of DD time). The pain
comes from **BULL-regime corrections** where V10 is fully invested, keeps pyramiding
into the decline, and relies on emergency_dd as the primary exit — not the trailing stop.

---

## 2. Top 10 DD Episodes

| # | Peak | Trough | Depth | Days | BTC DD | Dominant Regime | Buys | Sells | Exposure@Peak |
|---|------|--------|-------|------|--------|-----------------|------|-------|---------------|
| 1 | 2021-11-09 | 2023-10-12 | 36.3% | 703 | -61.1% | BEAR (50%) | 62 | 13 | 95.8% |
| 2 | 2019-06-26 | 2020-07-05 | 35.2% | 375 | -35.3% | BULL (31%) | 98 | 20 | 98.2% |
| 3 | 2024-05-20 | 2024-08-07 | 33.5% | 79 | -23.4% | BULL (77%) | 32 | 7 | 97.2% |
| 4 | 2025-01-20 | 2025-03-31 | 31.6% | 70 | -24.7% | BULL (47%) | 29 | 6 | 96.1% |
| 5 | 2025-01-20 | 2025-04-21 | 30.9% | 91 | -19.2% | CHOP (24%) | 32 | 7 | 96.1% |
| 6 | 2025-01-20 | 2025-05-08 | 25.4% | 108 | -8.2% | BULL (47%) | 40 | 8 | 96.1% |
| 7 | 2021-05-03 | 2021-10-01 | 25.3% | 151 | -25.8% | BULL (51%) | 32 | 8 | 87.3% |
| 8 | 2025-01-20 | 2025-06-22 | 24.9% | 153 | -8.6% | BULL (47%) | 47 | 9 | 96.1% |
| 9 | 2025-01-20 | 2025-09-06 | 21.3% | 229 | -1.7% | BULL (47%) | 70 | 14 | 96.1% |
| 10 | 2021-01-08 | 2021-01-27 | 20.9% | 19 | -26.6% | BULL (100%) | 9 | 2 | 97.8% |

**Note:** Episodes 4-9 share the same peak (2025-01-20) at different trough depths — they represent
the ongoing 2025 correction measured at progressively later points.

---

## 3. Aggregate Statistics

### 3.1 Regime Distribution During DDs

| Regime | Mean % | Median % | Interpretation |
|--------|--------|----------|----------------|
| **BULL** | 51.3% | 47.3% | Most DD time occurs while D1 regime is still bullish |
| BEAR | 7.4% | 0.0% | Only Episode 1 (2021-2023 crypto winter) has significant BEAR |
| NEUTRAL | 12.8% | 15.0% | Transitional — regime hasn't flipped yet |
| CHOP | 8.3% | 1.4% | |
| **TOPPING** | 3.8% | 3.1% | Barely present — NOT the pain driver |
| SHOCK | 1.3% | 0.0% | |

**Key insight:** V10's D1 EMA50/200 regime is a lagging indicator. By the time it signals
TOPPING or BEAR, the price correction is already deep. 7 of 10 DD episodes have their
dominant regime as BULL.

### 3.2 Exposure & Pyramiding

| Metric | Mean | Min | Max |
|--------|------|-----|-----|
| Exposure at peak | 96.0% | 87.3% | 98.2% |
| Max exposure during DD | 98.3% | 96.3% | 100% |
| Buy fills per episode | 45.1 | 9 | 98 |
| Sell fills per episode | 9.4 | 2 | 20 |
| Buy/Sell ratio | **4.8:1** | — | — |

V10 enters corrections near-fully invested and keeps buying throughout.

### 3.3 Entry Reasons During DDs

| Reason | Total | % | Character |
|--------|-------|---|-----------|
| vdo_trend_accel | 293 | 65% | Momentum entries — the workhorse |
| vdo_trend | 113 | 25% | Trend-following entries |
| vdo_dip_buy | 43 | 10% | Counter-trend "buy the dip" |
| vdo_compression | 2 | 0% | Volatility squeeze |

**Problem:** vdo_trend_accel fires 293 times during DDs. This signal uses
`accel > entry_threshold` (default 0.004), which can remain positive even as price
declines — lagging momentum and HMA smoothing create delayed signal reversal.

### 3.4 Exit Reasons During DDs

| Reason | Count | % |
|--------|-------|---|
| **emergency_dd** | 46 | 49% |
| trailing_stop | 45 | 48% |
| fixed_stop | 3 | 3% |

**Critical finding:** emergency_dd (the -5% per-trade hard stop) triggers as often
as the trailing stop. This means trades are entering and immediately moving against
the position before the trail can engage. The trailing stop (ATR*3.5) is too wide
to protect in fast corrections.

### 3.5 Trailing Stop Distance

| Metric | Value |
|--------|-------|
| ATR multiplier | 3.5× |
| Mean trail distance (at trailing_stop exits) | 8.5% |
| Max trail distance observed | 28.1% |
| Min trail distance observed | 3.1% |

ATR*3.5 = 8.5% average — meaning a winning trade must give back 8.5% of price before
the trail triggers. In a fast correction, this allows massive profit erosion.

---

## 4. Episode Deep-Dives

### 4.1 Episode 3 — 2024 Summer Correction (depth 33.5%)

- **BTC:** $71,447 → $54,759 (-23.4%), May-Aug 2024
- **NAV:** $105,593 → $70,217 (-33.5%)
- **Regime:** 77.4% BULL, 6.3% TOPPING — regime never flipped
- **RSI at peak:** 89.2 (extremely overbought)
- **Pattern:** 6 consecutive emergency_dd exits in sequence

| Trade | Entry | Exit | Return | Exit Reason |
|-------|-------|------|--------|-------------|
| #68 | Apr 30 @ 62,476 | May 23 @ 67,133 | +7.5% | trailing_stop |
| #69 | May 27 @ 69,616 | Jun 11 @ 66,823 | -4.0% | emergency_dd |
| #70 | Jun 12 @ 68,589 | Jun 17 @ 65,303 | -4.8% | emergency_dd |
| #71 | Jun 20 @ 64,964 | Jun 24 @ 61,231 | -5.8% | emergency_dd |
| #72 | Jun 26 @ 61,425 | Jul 5 @ 56,993 | -7.2% | emergency_dd |
| #73 | Jul 6 @ 57,483 | Jul 8 @ 55,105 | -4.1% | emergency_dd |
| #74 | Jul 16 @ 66,440 | Aug 3 @ 60,818 | -8.5% | emergency_dd |
| #75 | Aug 6 @ 57,037 | Aug 19 @ 58,369 | +2.3% | trailing_stop |

**Diagnosis:** V10 re-enters within days of each emergency_dd exit because the VDO/HMA
momentum indicators haven't reversed yet (regime = BULL). Each re-entry catches
another leg down. The strategy loses $20k in 6 sequential failed trades.

### 4.2 Episode 4 — 2025 Q1 Correction (depth 31.6%)

- **BTC:** $108,239 → $81,530 (-24.7%), Jan-Mar 2025
- **NAV:** $118,846 → $81,340 (-31.6%)
- **Regime:** 47.3% BULL, 23.9% CHOP, 26.0% NEUTRAL
- **RSI at peak:** 67.3 (not extreme — correction started from a "normal" level)
- **ATR_f at peak:** 2,960 — trailing distance = 3.5 × 2,960 / 108,239 = **9.6%**

| Trade | Entry | Exit | Return | Exit Reason |
|-------|-------|------|--------|-------------|
| #85 | Jan 10 @ 96,043 | Jan 23 @ 101,843 | +6.0% | trailing_stop |
| #86 | Jan 24 @ 105,225 | Feb 2 @ 98,175 | -6.7% | emergency_dd |
| #87 | Feb 4 @ 97,948 | Feb 25 @ 89,231 | -8.9% | emergency_dd |
| #88 | Feb 26 @ 86,187 | Feb 28 @ 80,372 | -6.8% | emergency_dd (vdo_dip_buy entry!) |
| #89 | Feb 28 @ 87,780 | Mar 4 @ 83,103 | -5.3% | trailing_stop |
| #90 | Mar 5 @ 90,493 | Mar 7 @ 86,904 | -4.0% | emergency_dd |

**Diagnosis:** Trade #88 is a vdo_dip_buy entry at $86,187 — the dip-buying logic fired
during a crash and lost 6.8% in 2 days. The high ATR (2,960) meant trailing stops were
~10% wide, so they never engaged — emergency_dd fired at -5% first.

### 4.3 Episode 7 — 2021 May Crash (depth 25.3%)

- **BTC:** $58,788 → $43,636 (-25.8%), May-Oct 2021
- **NAV:** $73,647 → $54,984 (-25.3%)
- **Regime:** 51.0% BULL — regime stayed bullish through the crash
- **Exit mix:** 5 trailing_stop, 2 fixed_stop, 1 emergency_dd
- Relatively better exit profile — the trailing stop worked here because the decline
  was slower (150 days vs 79 days for Episode 3)

### 4.4 Episode 10 — 2021 January Flash Correction (depth 20.9%)

- **BTC:** $41,287 → $30,323 (-26.6%), Jan 8-27 2021
- **NAV:** $57,740 → $45,686 (-20.9%)
- **Duration:** 19 days — fastest DD episode
- **Regime:** 100% BULL
- **Exposure:** 97.8% at peak
- Only 3 trades, 2 exited via trailing_stop — clean, fast, unavoidable

---

## 5. Root Cause Analysis

### Primary Cause: Pyramiding Into BULL-Regime Corrections

V10's pain is NOT caused by the TOPPING regime label. It's caused by a feedback loop:

```
BULL regime active → VDO momentum signals still firing → V10 enters/re-enters
→ Price drops → emergency_dd triggers at -5% → V10 re-enters (VDO still positive)
→ Price drops more → emergency_dd again → cycle repeats
```

**Quantified impact:**
- 293 vdo_trend_accel entries during DDs — the signal doesn't know the trend has reversed
- 46 emergency_dd exits — half of all DD exits are hard stops, not trailing stops
- Mean 45 buy fills per episode — massive over-trading during corrections

### Contributing Factors (ranked by severity)

| Rank | Factor | Evidence | Severity |
|------|--------|----------|----------|
| 1 | **No regime-based position reduction** | Exposure = 96% at peak of every DD | HIGH |
| 2 | **VDO signal lag during reversals** | 293 trend_accel entries during DDs | HIGH |
| 3 | **Wide trailing stop** (ATR×3.5 = 8.5%) | Trail never engages in fast corrections; emergency_dd fires instead | MEDIUM |
| 4 | **Dip-buying in crashes** | 43 vdo_dip_buy entries during DDs, incl. Episode 4 trade #88 (-6.8%) | MEDIUM |
| 5 | **No cooldown after emergency_dd** | Re-entry within days of hard stop | LOW-MEDIUM |

### What TOPPING Actually Looks Like

The TOPPING regime (D1 EMA50 < EMA200 with price still above EMA200) accounts for only
3.8% of DD time. By the time the D1 EMAs cross, the fast correction is already over or
deep into BEAR territory. The regime label is too slow to be useful as a defensive signal.

---

## 6. Risk Overlay Proposals

### Overlay A: Emergency-DD Cooldown (Minimal)

**Concept:** After an emergency_dd exit, suppress all new entries for N bars.

**Rationale:** The deadliest pattern is re-entering 1-3 bars after an emergency_dd exit.
46 emergency_dd exits in the top 10 DDs means ~46 unnecessary re-entries.

**Parameters:**
- `cooldown_bars_after_emergency_dd`: 6 (= 1 day of H4 bars)
- Effect: After emergency_dd, no new positions for 24 hours

**Implementation:**
```python
# In on_bar(), before _check_entry():
if state.bars_since_emergency_dd < self.cfg.cooldown_bars:
    state.bars_since_emergency_dd += 1
    return  # skip entry check
```

**Expected impact:**
- Reduces re-entry cascades (Episode 3: 6→3 emergency_dd trades)
- Minimal drag on trend-following (cooldown is short)
- Zero change to entry alpha (no new signals added)

**Test plan:**
1. Sensitivity grid: `cooldown_bars` ∈ {0, 3, 6, 12, 18}
2. Run full backtest (harsh, 2019-2026) for each
3. Compare: DD depth, # emergency_dd exits, score, CAGR
4. WFO validation: run cooldown grid across 10 OOS windows
5. Acceptance: MDD reduction ≥ 3 pts with score loss ≤ 5%

### Overlay B: Exposure Cap by Recent Drawdown (Moderate)

**Concept:** Scale maximum allowed exposure inversely with rolling portfolio drawdown.

**Rationale:** At correction onset, V10 is 96% invested. If we cap exposure when
the portfolio is already in drawdown, we reduce damage from subsequent legs down.

**Parameters:**
- `dd_threshold_1`: -10% → cap exposure to 60%
- `dd_threshold_2`: -20% → cap exposure to 30%
- `dd_recovery`: re-enable full exposure when DD recovers to -5%

**Implementation:**
```python
# In on_bar(), after regime check:
rolling_dd = (state.nav / state.peak_nav) - 1.0
if rolling_dd < -0.20:
    max_exposure = 0.30
elif rolling_dd < -0.10:
    max_exposure = 0.60
else:
    max_exposure = 1.00
# Apply cap to position sizing
```

**Expected impact:**
- Episode 1 (36.3% DD): after -10% DD, exposure caps at 60% → subsequent trades
  are half-sized → estimated DD reduction to ~28%
- Episode 3 (33.5% DD): similar mechanics → estimated DD reduction to ~25%
- Trade-off: slower recovery from legitimate dips (2021 Jan dip was 20.9% DD
  but recovered in 18 days — this overlay would slow the recovery)

**Test plan:**
1. Sensitivity grid: `dd_threshold_1` ∈ {-8%, -10%, -12%}, `dd_threshold_2` ∈ {-15%, -20%, -25%}
2. Full backtest + WFO validation for each combination
3. Compare: MDD, recovery days, score, CAGR
4. Backtest Episode 3 and Episode 4 in isolation to verify DD reduction
5. Acceptance: MDD reduction ≥ 5 pts with CAGR loss ≤ 15% and score loss ≤ 8%

---

## 7. Overlay Comparison

| Dimension | A: Cooldown | B: Exposure Cap |
|-----------|-------------|-----------------|
| Complexity | 1 parameter | 3 parameters |
| Mechanism | Suppresses re-entry | Reduces position size |
| Targets | Emergency_dd cascades | All DD amplification |
| Expected MDD reduction | 3-5 pts | 5-10 pts |
| Risk of CAGR drag | Low | Moderate |
| Overfitting risk | Low (1 param) | Moderate (3 params) |
| Recommendation | **Test first** | Test second |

### Recommended Sequence

1. **Implement and test Overlay A** (cooldown) — simplest, lowest overfitting risk
2. If MDD improvement is insufficient (<3 pts), **add Overlay B** (exposure cap)
3. Never combine both without isolated testing of each

---

## 8. Conclusion

### Diagnosis

V10's drawdown pain is NOT caused by the TOPPING regime. It's caused by a
**structural feedback loop**: BULL-regime corrections where VDO momentum signals
lag the reversal, causing repeated entries that get stopped out by emergency_dd.
The wide trailing stop (ATR×3.5) rarely engages in fast corrections.

### Key Numbers

| Metric | Value |
|--------|-------|
| Mean regime during DDs | 51% BULL, 3.8% TOPPING |
| Mean exposure at DD peak | 96% |
| Buy fills per DD episode | 45.1 (mean), 98 (max) |
| emergency_dd as exit | 49% of all DD exits |
| Trailing stop distance | 8.5% mean |

### Overlay Priority

1. **Overlay A (cooldown)**: low-risk, targets the exact pathology (emergency_dd cascades)
2. **Overlay B (exposure cap)**: moderate complexity, broader protection, higher overfitting risk

---

## 9. Data Files

| File | Description |
|------|-------------|
| `out_v10_full_validation_stepwise/v10_dd_episodes.csv` | Top 10 DD episodes (summary) |
| `out_v10_full_validation_stepwise/v10_dd_episodes.json` | Full episode detail (trades, indicators, trail analysis) |
| `out_v10_full_validation_stepwise/scripts/v10_dd_episodes.py` | Reproducible analysis script |
| `out_v10_full_validation_stepwise/reports/v10_topping_diagnosis.md` | This report |
