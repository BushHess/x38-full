# WFO Window-Level Noise Explained by Trade-Level Analysis

**Script:** `out_trade_analysis/wfo_trade_level_bridge.py`
**Data:** `out_trade_analysis/matched_trades_{harsh,base}.csv`, individual trade CSVs
**WFO:** 10 windows, 24m train / 6m test / 6m slide (2021-01 → 2026-01)
**Report date:** 2026-02-24

---

## 1. The Problem

The V10 WFO round-by-round analysis (10 OOS windows, 6 months each) shows apparently
erratic results:

| Window | Period | Trades | V10 harsh Return |
|--------|--------|--------|-----------------|
| 0 | 2021-H1 | 8 | +41.3% |
| 1 | 2021-H2 | 10 | +0.1% |
| 2–3 | 2022 | 0 | 0.0% |
| 4 | 2023-H1 | 4 | -3.0% |
| 5 | 2023-H2 | 6 | +24.1% |
| 6 | 2024-H1 | 11 | +28.8% |
| 7 | 2024-H2 | 10 | +26.0% |
| 8 | 2025-H1 | 10 | -11.6% |
| 9 | 2025-H2 | 10 | -3.3% |

Returns swing from +41% to -12% between windows. Only 4/10 windows pass the ≥10 trade
scoring threshold (6/10 rejected). V10 vs V11 Δ score comparison: 8/10 windows show
Δ = 0 (identical), the 2 windows with differences go opposite directions (window 6:
V10 wins; window 5: V11 wins). This looks unstable and uninformative.

**Root cause:** too few trades per window, and 1–2 tail trades dominate each window's
result. This report quantifies exactly why, and shows what trade-level/regime-level
analysis reveals instead.

---

## 2. Per-Window Trade Counts

### 2.1 Full Inventory

| Win | Period | V10 | V11 | Matched | V10 Turnover | V11 Turnover | Days |
|-----|--------|-----|-----|---------|-------------|-------------|------|
| 0 | 2021-01 → 2021-07 | 7 | 7 | 7 | — | — | 181 |
| 1 | 2021-07 → 2022-01 | 11 | 11 | 10 | — | — | 184 |
| 2 | 2022-01 → 2022-07 | 0 | 0 | 0 | — | — | 181 |
| 3 | 2022-07 → 2023-01 | 0 | 0 | 0 | — | — | 184 |
| 4 | 2023-01 → 2023-07 | 5 | 4 | 4 | — | — | 181 |
| 5 | 2023-07 → 2024-01 | 7 | 7 | 7 | — | — | 184 |
| 6 | 2024-01 → 2024-07 | 11 | 11 | 11 | — | — | 182 |
| 7 | 2024-07 → 2025-01 | 12 | 11 | 10 | — | — | 184 |
| 8 | 2025-01 → 2025-07 | 10 | 10 | 9 | — | — | 181 |
| 9 | 2025-07 → 2026-01 | 9 | 9 | 9 | — | — | 184 |
| **Total WFO** | | **72** | **70** | **67** | | | |
| **Pre-WFO** | 2019-01 → 2020-12 | **31** | **32** | **29** | | | |
| **Grand total** | | **103** | **102** | **96** | | | |

### 2.2 Distribution (matched trades, active windows only)

| Statistic | Value |
|-----------|-------|
| Active windows (trades > 0) | 8 of 10 |
| Empty windows (2022 bear) | 2 |
| Min trades/window | **4** (Win 4) |
| Median trades/window | 9 |
| Max trades/window | **11** (Win 6) |
| Mean trades/window | 8.4 |
| Windows < 10 trades | **5 of 8** (63%) |

### 2.3 What WFO Misses

**29 matched trades (30% of total) fall before the first WFO window** (2019-01 to
2020-12). These are the earliest trades in the backtest — during the 2019 recovery
and 2020 bull — and are excluded from all WFO comparisons. Trade-level analysis
pools all 96 trades; WFO only sees 67.

---

## 3. "Few Trades ⟹ Large Variance": The Proof

### 3.1 Standard Error Formula

For a window with N matched trades, the standard error of the mean delta is:

```
SE = σ / √N
```

where σ is the pooled standard deviation of per-trade Δ PnL across all matched trades.

### 3.2 Pooled σ (from full sample)

| Scenario | σ(Δ PnL) | Full mean Δ |
|----------|----------|-------------|
| harsh | **$2,442** | +$418 |
| base | **$3,369** | -$263 |

### 3.3 SE by Window Size

| N trades | SE (harsh) | SE (base) | 95% CI half-width (harsh) |
|----------|-----------|-----------|--------------------------|
| 4 | **$1,221** | **$1,684** | ±$2,393 |
| 7 | $923 | $1,273 | ±$1,809 |
| 9 | $814 | $1,123 | ±$1,596 |
| 10 | $772 | $1,065 | ±$1,514 |
| 11 | $736 | $1,016 | ±$1,443 |
| **96 (all)** | **$249** | **$346** | **±$488** |

**The signal is $418/trade (harsh). At N=4, SE=$1,221 — the noise is 3× the signal.**
Even at N=11 (best window), SE=$736, still 1.8× the signal. Only by pooling all 96
trades does the SE ($249) become smaller than the signal ($418).

### 3.4 Signal-to-Noise Ratio (SNR) per Window

**Harsh:**

| Win | N | Sum Δ | Mean Δ | SE | **SNR** | 95% CI | Contains 0? |
|-----|---|-------|--------|----|---------|--------|-------------|
| 0 | 7 | +$1,815 | +$259 | $923 | 0.28 | [-$1,550, +$2,068] | **Yes** |
| 1 | 10 | -$1,051 | -$105 | $772 | 0.14 | [-$1,619, +$1,408] | **Yes** |
| 4 | 4 | +$11,873 | +$2,968 | $1,221 | **2.43** | [+$575, +$5,362] | No — tail trade |
| 5 | 7 | +$7,766 | +$1,109 | $923 | 1.20 | [-$700, +$2,918] | **Yes** |
| 6 | 11 | +$10,903 | +$991 | $736 | 1.35 | [-$452, +$2,434] | **Yes** |
| 7 | 10 | +$13,880 | +$1,388 | $772 | 1.80 | [-$126, +$2,902] | **Yes** |
| 8 | 9 | +$294 | +$33 | $814 | 0.04 | [-$1,563, +$1,628] | **Yes** |
| 9 | 9 | -$5,858 | -$651 | $814 | 0.80 | [-$2,246, +$945] | **Yes** |

**7 of 8 active windows have 95% CI containing zero.** Only window 4 (SNR=2.43) has a
CI excluding zero — and that's because a single tail trade (+$11.7k) dominates the
4-trade window.

**Base:**

| Win | N | Sum Δ | Mean Δ | SE | **SNR** | 95% CI | Contains 0? |
|-----|---|-------|--------|----|---------|--------|-------------|
| 0 | 7 | +$1,938 | +$277 | $1,273 | 0.22 | [-$2,219, +$2,773] | **Yes** |
| 1 | 10 | -$28,183 | -$2,818 | $1,065 | **2.65** | [-$4,906, -$730] | No — **outlier #43** |
| 4 | 4 | -$66 | -$16 | $1,684 | 0.01 | [-$3,318, +$3,285] | **Yes** |
| 5 | 7 | +$4,774 | +$682 | $1,273 | 0.54 | [-$1,814, +$3,178] | **Yes** |
| 6 | 11 | +$8,680 | +$789 | $1,016 | 0.78 | [-$1,202, +$2,780] | **Yes** |
| 7 | 10 | +$4,776 | +$478 | $1,065 | 0.45 | [-$1,611, +$2,566] | **Yes** |
| 8 | 9 | -$698 | -$78 | $1,123 | 0.07 | [-$2,279, +$2,124] | **Yes** |
| 9 | 8 | -$16,747 | -$2,093 | $1,191 | 1.76 | [-$4,428, +$241] | **Yes** |

Again, 7 of 8 active windows contain zero. The one exception (window 1, SNR=2.65) is
entirely due to the infamous outlier trade #43 (2021-09-22, -$28.4k).

---

## 4. Tail Trade Domination

### 4.1 Definition

A "tail trade" is a matched trade whose |Δ PnL| accounts for ≥50% of the window's
total Δ PnL. In a window with few trades, a single large trade easily reaches this
threshold.

### 4.2 How Many Windows Are Tail-Dominated?

| Scenario | Windows with ≥1 tail trade | Windows with 0 tail trades |
|----------|---------------------------|---------------------------|
| harsh | **7 of 8** active | 1 (Win 9) |
| base | **8 of 8** active | 0 |

**Every active window except one is dominated by 1–3 tail trades.**

### 4.3 The Worst Offenders

**Harsh — Window 4 (2023-H1, N=4):**
- Total Δ = +$11,873
- Tail trade: 2023-05-04, Δ = +$11,658 (98.2% of window total)
- This single trade where V11 converted emergency_dd → trailing_stop accounts for
  almost the entire window result

**Base — Window 1 (2021-H2, N=10):**
- Total Δ = -$28,183
- Tail trade: 2021-09-22 (trade #43), Δ = -$28,359 (100.6% of window total)
- The remaining 9 trades sum to +$176 (essentially zero)
- This one trade where V11's larger position hit emergency DD earlier = entire window

**Harsh — Window 8 (2025-H1, N=9):**
- 8 of 9 trades flagged as "tail" — because the total is near zero (+$294), and
  individual deltas of ±$1–3k each exceed 50% of the tiny total
- This window is pure noise: opposing trade deltas almost perfectly cancel out

### 4.4 Implication

When 1 trade controls >50% of a 6-month window result, that window's WFO metric
(score, return, etc.) is **not measuring strategy performance** — it's measuring
whether a single trade happened to exit a few hours earlier or later. This is sampling
noise, not signal.

---

## 5. Window-Level vs Trade-Level: Head-to-Head

### 5.1 Point Estimate Comparison

| Method | harsh mean Δ | harsh SE | base mean Δ | base SE |
|--------|-------------|----------|-------------|---------|
| **WFO** (mean of window means) | +$749 | ±$400 | -$348 | ±$477 |
| **Trade-level** (pooled mean) | +$418 | ±$249 | -$263 | ±$346 |

WFO gives different point estimates because **windows with few trades get equal
weight**. Window 4 (4 trades, +$2,968/trade) weighs the same as Window 6 (11 trades,
+$991/trade), inflating the WFO mean.

### 5.2 Standard Error

| Scenario | WFO SE | Trade SE | WFO SE / Trade SE |
|----------|--------|---------|-------------------|
| harsh | $400 | $249 | **1.61×** (61% wider) |
| base | $477 | $346 | **1.38×** (38% wider) |

Trade-level pooling is 38–61% more precise than WFO window-level aggregation.

### 5.3 Bootstrap P(V11 > V10)

| Method | harsh P(>0) | base P(>0) |
|--------|-------------|------------|
| WFO bootstrap (resample windows) | 0.987 | 0.228 |
| Trade-level bootstrap (resample trades) | 0.965 | 0.235 |

Both methods agree directionally (harsh: V11 wins; base: V10 wins), but WFO
appears more confident in harsh (98.7% vs 96.5%) due to the upward bias from
equal-weighting small windows.

### 5.4 Bootstrap 95% CI

| Method | harsh CI | base CI |
|--------|----------|---------|
| WFO bootstrap | [+$76, +$1,535] | [-$1,281, +$431] |
| Trade-level bootstrap | [-$37, +$939] | [-$1,002, +$293] |

WFO CI is wider in both scenarios, and its harsh lower bound (+$76) looks more
optimistic than trade-level (-$37). This is an artifact of unequal window weighting,
not a real signal.

---

## 6. What Trade-Level and Regime-Level Analysis Reveals Instead

### 6.1 Trade-Level Insights (from paired analysis + bootstrap)

| Finding | Window-level visible? | Trade-level visible? |
|---------|----------------------|---------------------|
| Median per-trade Δ = 0 | No (windows aggregate) | **Yes** |
| P(V11 wins individual trade) = 50% | No | **Yes** |
| 3 trades drive 78% of harsh advantage | Hidden in window totals | **Yes** (concentration analysis) |
| 1 trade drives 114% of base loss | Hidden in window 1 total | **Yes** (trade #43 identified) |
| Effect reverses between scenarios | Obscured by rejection | **Yes** (harsh +$40k, base -$25k) |
| Lag-1 autocorrelation = 0.18 | Cannot measure | **Yes** (justifies block bootstrap) |

### 6.2 Regime-Level Insights (from regime conditional comparison)

| Finding | Window-level visible? | Regime-level visible? |
|---------|----------------------|---------------------|
| BULL = 93.4% of harsh delta | Partially (BULL return per window) | **Yes** (precise attribution) |
| NEUTRAL = 114.2% of base delta | Hidden (trade #43 in window 1) | **Yes** (regime decomposition) |
| V11 TOPPING PnL worse than V10 | Cannot isolate (4 TOPPING trades across 3 windows) | **Yes** (deep dive: -$13k vs -$6k) |
| Cycle_late is sizing amplifier, not alpha | Cannot determine | **Yes** (size_ratio 1.21× in BULL) |
| V11 does not achieve "zero damage" | Cannot measure | **Yes** (TOPPING hit rate 20%) |

### 6.3 The Fundamental Advantage of Trade-Level Analysis

WFO compresses ~8 trades into one window metric. This destroys information:

```
96 matched trades → 8 active windows (12:1 compression)
```

Trade-level analysis preserves the full 96-trade resolution. Regime-level analysis
groups by economic context (BULL/NEUTRAL/CHOP/TOPPING) rather than arbitrary 6-month
boundaries, producing groups of 4–56 trades that are economically meaningful.

The key insight WFO cannot provide: **V11's advantage is entirely a BULL-regime sizing
play (+21% larger positions), not a strategy improvement. It amplifies both wins and
losses, and the net effect depends on which tail trades happen to dominate — not on
systematic strategy alpha.**

---

## 7. Why WFO Window-Level Results Are Unstable

### 7.1 Summary of Causes

| Cause | Evidence | Impact |
|-------|----------|--------|
| **Too few trades** | 63% of windows <10 trades, min=4 | SE > signal in every window |
| **Empty windows** | 2 of 10 (2022 bear) | 20% of WFO data lost |
| **Pre-WFO exclusion** | 29 trades (30%) before 2021 | WFO uses only 70% of available data |
| **Tail trade domination** | 7–8 of 8 windows dominated | Window metric = 1 trade's outcome |
| **Equal window weighting** | 4-trade windows = 11-trade windows | Inflates noise, biases mean |
| **SNR per window** | Median SNR = 0.48 (harsh), 0.44 (base) | Signal buried in noise |

### 7.2 The Arithmetic

Given:
- True mean effect ≈ $418/trade (harsh)
- Per-trade σ ≈ $2,442
- Typical window N = 8

```
SNR = 418 / (2442 / √8) = 418 / 863 = 0.48
```

A SNR of 0.48 means you need to observe the window **~4.3 times** (1/0.48²) to detect
the signal with standard confidence. With only 1 observation per window, each window
is dominated by noise.

To achieve SNR ≥ 2.0 (standard threshold for detection) per window, you'd need:

```
N ≥ (2.0 × σ / μ)² = (2.0 × 2442 / 418)² = 136 trades per window
```

That's 136 trades per 6-month window — about 17× what V10 actually produces. This is
structurally impossible for a trend-following strategy on H4 bars.

---

## 8. Conclusion

### 8.1 Answer: "WFO window-level noise đến từ đâu?"

**From the intersection of small N and fat tails.** With 4–11 trades/window and
σ = $2,442/trade, per-window SE exceeds the true signal ($418) in every single
window. One or two tail trades (out of 3–11 total) dominate each window's result,
making the WFO metric essentially random for V10 vs V11 comparison.

Specific evidence:
- **7/8 windows** have 95% CI containing zero (no detectable signal)
- **7–8/8 windows** are tail-trade dominated (≥50% from 1 trade)
- The 2 windows that appear to "detect" a signal (Win 4 harsh, Win 1 base) are
  actually detecting a single trade, not a window-level effect
- WFO SE is **38–61% larger** than trade-level SE due to equal-weighting small windows

### 8.2 Answer: "Trade-level/regime-level cho insight gì thay thế?"

| Dimension | WFO conclusion | Trade/regime conclusion |
|-----------|---------------|----------------------|
| V11 better? | "Can't tell — 6/10 windows rejected" | Harsh: yes (P=98%), Base: no (P=24%). **Scenario-dependent.** |
| Where V11 helps? | "Unclear — Δ score = 0 in 8/10 windows" | BULL regime only (+93% of delta), via 21% larger sizing |
| Where V11 hurts? | "Unclear" | NEUTRAL (outlier #43, -$28.5k base) and TOPPING (-$13k vs -$6k) |
| Stable effect? | "Only 2 windows differ" | **No** — sign flips between cost scenarios, 3 trades drive 78% |
| Mechanism? | Not identifiable | Size amplification (leverage), not alpha. Cycle_late = offensive overlay in defensive regime |

### 8.3 Recommendation

**Stop using WFO round-by-round for V10 vs V11 comparison.** The window-level
comparison is statistically powerless at 4–11 trades/window.

Instead use:
1. **Trade-level paired analysis** — 96 matched pairs with full decomposition
2. **Bootstrap inference** — cluster or block resampling with P values and CIs
3. **Regime-conditional comparison** — isolates BULL, NEUTRAL, TOPPING contributions
4. **Cross-scenario consistency** — the critical test WFO cannot perform

WFO windows remain useful for two things:
- **Detecting zero-trade periods** (2022 bear — confirms regime gate works)
- **Monitoring regime composition changes** (which regimes dominate each half-year)

But for V10 vs V11 comparison, trade-level is the correct unit of analysis.

---

## 9. Data Files

| File | Description |
|------|-------------|
| `out_trade_analysis/wfo_trade_level_bridge.py` | Analysis script |
| `out_trade_analysis/window_trade_counts.csv` | Per-window: trade counts, deltas, SE, SNR, CIs, tail trades |
| `out_trade_analysis/wfo_window_detail.json` | Full per-window detail with bootstrap comparisons |
