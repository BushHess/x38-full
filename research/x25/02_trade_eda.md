# Phase 2: Conditional Analysis Around Actual Trades

**Date**: 2026-03-10
**Data**: bars_btcusdt_h1_4h_1d.csv, H4 interval (18,662 bars, 2017-08 to 2026-02)
**Strategy**: vtrend_ema21_d1 (E0 + D1 EMA(21) regime filter)
**Protocol**: Observation before interpretation. No formalization, no suggestion, no design.

---

## 0. Trade Reproduction

Strategy parameters:
- EMA fast=30, slow=120 (H4 close)
- ATR period=14, trail multiplier=3.0
- VDO fast=12, slow=28, threshold=0.0
- D1 EMA period=21
- Cost: 50 bps round-trip

**Result: 201 trades reproduced.**

The reference "~226 trades" is the E0 base without D1 filter. Verified: E0 alone produces exactly 226 trades on this data. The D1 EMA(21) regime filter blocks 25 entries (where D1 close <= D1 EMA(21) at entry time), yielding 201.

| Metric | Value |
|--------|-------|
| Total trades | 201 |
| Trail stop exits | 183 (91.0%) |
| Trend exits | 18 (9.0%) |
| Win rate (net) | 38.8% |
| Median hold | 29 bars (116h) |
| Mean gross return | 2.51% |
| First entry | 2017-08-25 |
| Last entry | 2026-02-09 |

Saved: [trade_list.csv](tables/trade_list.csv), [trade_repro_check.csv](tables/trade_repro_check.csv)

---

## 1. Winner / Loser Split

Winners: net trade return > 0 after 50 bps RT cost.
Losers: net trade return <= 0.

[Tbl04](tables/Tbl04_trade_groups.csv):

| Group | Count | Median net return | Mean net return | Median hold (bars) | Median hold (hours) | Trail stop % | Trend exit % |
|-------|-------|-------------------|-----------------|--------------------|--------------------|-------------|-------------|
| Winner | 78 | +4.63% | +12.19% | 59 | 236 | 98.7% | 1.3% |
| Loser | 123 | -3.40% | -3.78% | 17 | 68 | 86.2% | 13.8% |

- 61.2% of trades are losers.
- Mean winner (+12.19%) is ~3.2x the magnitude of mean loser (-3.78%), which is how the strategy profits despite low win rate.
- Winners hold 3.5x longer than losers (59 vs 17 bars median).
- Nearly all winners (98.7%) exit via trail stop. Losers exit via trail stop 86.2% of the time; 13.8% by trend reversal.

---

## 2. Volume Profile Around Entry

For each trade, volume is normalized by the median volume of bars [-20, -1] (the 20-bar pre-entry baseline). Profiles show the cross-trade median at each relative bar position, with IQR shaded.

[Fig09](figures/Fig09_volume_profile.png): Normalized volume profile, bars -20 to +10.

- Both winner and loser median lines are nearly overlapping across the entire window.
- Both groups fluctuate around 1.0 (the pre-entry baseline) from bar -20 through bar 0.
- After entry, both groups show a slight upward drift in normalized volume (median ~1.0 to ~1.2 by bar +10), but the IQR bands overlap completely.
- There is no visible separation between winners and losers at any offset.

[Fig10](figures/Fig10_tbr_profile.png): Taker buy ratio profile, bars -20 to +10.

- Both groups show a synchronized rise in TBR starting around bar -5, from ~0.49 up to ~0.52 at bar 0 (entry).
- This rise is mechanical: the entry condition (EMA fast > EMA slow) fires when price has been rising, which correlates with TBR > 0.5 on contemporaneous bars.
- After entry, both groups revert toward 0.50 by bar +5.
- The two median lines are nearly indistinguishable throughout. IQR bands overlap completely.
- No separation between winners and losers before entry, at entry, or after entry.

---

## 3. Volatility Profile Around Entry

[Fig11](figures/Fig11_volatility_profile.png): ATR(20)/price profile, bars -20 to +10.

- Winner median ATR(20)/price is consistently slightly above loser median across the full window (-20 to +10).
- The difference in medians is approximately 0.001 (winners ~0.0165, losers ~0.0158), which is ~4-7% relative.
- This difference is not localized to entry — it persists across the entire 30-bar window.
- IQR bands overlap heavily. The loser IQR extends higher than the winner IQR.
- The persistent nature of this gap suggests it reflects a difference in which volatility regimes produce winning vs losing trades, not an actionable signal at the entry bar.

---

## 4. Statistical Separation at Entry Bar

Five features computed at the entry bar. Mann-Whitney U test (two-sided), winners vs losers.

[Tbl05](tables/Tbl05_entry_separation.csv):

| Feature | Median W | Median L | p-value | Rank-biserial | Direction |
|---------|----------|----------|---------|---------------|-----------|
| TBR (single bar) | 0.5178 | 0.5203 | 0.570 | 0.048 | losers_higher |
| Mean TBR 5 bars before | 0.4956 | 0.4945 | 0.398 | -0.071 | winners_higher |
| Mean TBR 10 bars before | 0.4923 | 0.4921 | 0.806 | 0.021 | winners_higher |
| Volume / median_vol(20) | 1.017 | 1.058 | 0.456 | 0.063 | losers_higher |
| ATR(20) / price | 0.01709 | 0.01600 | 0.715 | 0.031 | winners_higher |

- **No feature achieves statistical significance.** All p-values are > 0.39.
- All rank-biserial effect sizes are < 0.08 in absolute value. These are negligible effects.
- The directions are inconsistent: TBR single-bar favors losers, TBR-mean-5 favors winners, volume-relative favors losers.
- With n=78 winners and n=123 losers, the test has adequate power to detect medium effects (d ≈ 0.35). The absence of any signal is informative.

---

## 5. VDO at Entry

[Fig12](figures/Fig12_vdo_histogram.png): VDO histogram, winners vs losers.

- Both distributions are concentrated in a narrow range just above VDO=0 (the entry threshold).
- Most trades have VDO between 0.000 and 0.010.
- The distributions overlap almost completely. Winners have a slightly taller peak in the [0.000, 0.010] bin.
- There is a subtle rightward shift for winners: the winner distribution has slightly more mass in [0.01, 0.05].

[Fig13](figures/Fig13_vdo_scatter.png): VDO at entry vs net trade return.

- The cloud is dense at low VDO (0-0.01) with both winners and losers intermingled.
- No visible trend. Large winners (return > 30%) occur at VDO in [0.001, 0.035] — the same range as losers.
- A few high-VDO outliers (VDO > 0.05) are losers.
- Spearman r = 0.093, p = 0.190. Not significant.

[Tbl06](tables/Tbl06_vdo_entry_stats.csv):

| Metric | Value |
|--------|-------|
| Median VDO — winners | 0.0054 |
| Median VDO — losers | 0.0035 |
| Mann-Whitney U | 5,487 |
| MW p-value | 0.086 |
| Rank-biserial | -0.144 |
| Spearman r (VDO vs return) | 0.093 |
| Spearman p | 0.190 |

- VDO at entry is the **only** feature approaching marginal significance (p=0.086), but does not pass the 0.05 threshold.
- Effect size is small (rank-biserial = 0.144).
- Winners have slightly higher median VDO (0.0054 vs 0.0035).
- The VDO-return correlation is not significant (r=0.093, p=0.190).

---

## 6. False Entries — 5 Worst Losers

| Rank | Trade # | Entry Date | Net Return | Hold (bars) | Exit Reason |
|------|---------|------------|------------|-------------|-------------|
| 1 | 10 | 2017-12-21 | -25.81% | 6 | trail_stop |
| 2 | 41 | 2019-06-29 | -12.94% | 14 | trail_stop |
| 3 | 7 | 2017-11-08 | -11.14% | 11 | trail_stop |
| 4 | 3 | 2017-09-06 | -10.80% | 19 | trail_stop |
| 5 | 82 | 2021-01-17 | -10.11% | 22 | trail_stop |

Individual trade plots: [Fig14a](figures/Fig14a_worst_loser_1.png), [Fig14b](figures/Fig14b_worst_loser_2.png), [Fig14c](figures/Fig14c_worst_loser_3.png), [Fig14d](figures/Fig14d_worst_loser_4.png), [Fig14e](figures/Fig14e_worst_loser_5.png).

**Visual descriptions:**

**Fig14a** (#10, 2017-12-21, -25.81%): Entry at the BTC blow-off top. Price was already declining pre-entry. Volume spikes after entry as the crash accelerates. TBR rises at entry (~0.60) but is chaotic. This is the December 2017 crash — a macro-structural event.

**Fig14b** (#41, 2019-06-29, -12.94%): Price had peaked ~15 bars before entry and was in a declining channel. Volume was elevated pre-entry (bars -15 to -10) then decreased to entry. TBR oscillated around 0.50 without clear signal. Entry came at a local recovery that failed.

**Fig14c** (#7, 2017-11-08, -11.14%): Price in a choppy range. Volume spiked at entry bar. TBR was predominantly below 0.50 in the pre-entry window (bars -20 to -5), suggesting persistent sell-side pressure. Price dropped sharply post-entry.

**Fig14d** (#3, 2017-09-06, -10.80%): Price rose slightly into entry, then reversed. Volume and TBR unremarkable at entry — no distinguishing features. A standard false breakout.

**Fig14e** (#82, 2021-01-17, -10.11%): Price declining into entry. Volume decreasing. TBR near 0.50 throughout. Exit bar is at bar +22 (beyond the plot's +20 window). No distinguishing features at entry.

**Common patterns across worst losers:**
- All 5 exit via trail stop.
- 3 of 5 are from 2017 (early, volatile period).
- No consistent volume or TBR pattern distinguishes these entries from typical entries.
- #14c has persistently below-0.50 TBR before entry, but this is one case out of five.
- The worst losers generally look similar to other entries at the point of entry — the subsequent price drop is what makes them losers, not any visible entry-bar feature.

---

## 7. Observation Log

### Where winners and losers look the same

**Obs15** — Volume profile around entry is indistinguishable between winners and losers.
Normalized volume median lines for both groups overlap from bar -20 through bar +10. IQR bands overlap completely. No separation before, at, or after entry.
Support: [Fig09]

**Obs16** — Taker buy ratio profile around entry is indistinguishable between winners and losers.
Both groups show the same mechanical TBR rise (0.49 to 0.52) in bars -5 to 0, then revert to 0.50 post-entry. The two median lines are essentially the same curve. IQR bands overlap.
Support: [Fig10]

**Obs17** — At the entry bar, all five tested features fail to separate winners from losers.
TBR (single bar, 5-bar mean, 10-bar mean), relative volume, and normalized ATR all have p > 0.39 and rank-biserial < 0.08. With n=201 trades, these are informative null results.
Support: [Tbl05]

### Where separation exists (if any)

**Obs18** — VDO at entry is the only feature approaching marginal significance (p=0.086).
Winners have slightly higher median VDO (0.0054 vs 0.0035), rank-biserial = 0.144. The effect is small and does not pass the 0.05 threshold. VDO is already an entry condition (VDO > 0), constraining the range.
Support: [Fig12], [Tbl06]

**Obs19** — Winners enter at slightly higher volatility than losers (median ATR(20)/price: 0.0171 vs 0.0160).
However, this difference is persistent across the full -20 to +10 window (not localized to entry) and is not statistically significant at the entry bar (p=0.715). It reflects regime-level context, not an entry-bar signal.
Support: [Fig11], [Tbl05]

### Structural observations

**Obs20** — Winners hold 3.5x longer than losers (median 59 vs 17 bars).
This is the dominant structural difference but it is an outcome (post-entry), not a predictor at entry time.
Support: [Tbl04]

**Obs21** — The pre-entry TBR rise (bars -5 to 0) is mechanical, not predictive.
TBR increases toward 0.52 before entry for both groups equally. This reflects the entry condition requiring upward price momentum (EMA cross-up), which coincides with contemporaneous buy-side dominance. The rise cannot distinguish trade quality.
Support: [Fig10], [Obs01 from Phase 1]

**Obs22** — 91% of exits are trail stops; trend exits are rare (9%).
Among losers, 86% exit via trail stop and 14% via trend reversal. Among winners, 99% exit via trail stop.
Support: [Tbl04]

**Obs23** — The 5 worst losers show no common volume/TBR pattern at entry.
They span different years (2017x3, 2019, 2021), different price regimes, and different volume contexts. At the point of entry, they visually resemble typical entries.
Support: [Fig14a], [Fig14b], [Fig14c], [Fig14d], [Fig14e]

**Obs24** — VDO values at entry cluster just above zero (IQR approximately 0.001 to 0.010).
The entry condition VDO > 0 creates a hard floor. Most entries occur with VDO barely above the threshold. The distribution has a long right tail but most mass is compressed near 0.
Support: [Fig12], [Fig13]

### What is visually tempting but statistically weak

**Obs25 (VISUALLY TEMPTING, STATISTICALLY WEAK)** — VDO at entry appears to slightly favor winners.
The histogram (Fig12) shows winners shifted slightly right of losers, and the median difference exists (0.0054 vs 0.0035). However: (a) p=0.086 does not reach significance, (b) rank-biserial = 0.144 is a small effect, (c) VDO-vs-return correlation is not significant (r=0.093, p=0.190), (d) the VDO range is already constrained by the VDO > 0 entry condition, limiting the dynamic range available for discrimination. This signal is tempting because VDO is already part of the system and "should" matter, but the evidence is insufficient.
Support: [Fig12], [Fig13], [Tbl06]

**Obs26 (VISUALLY TEMPTING, STATISTICALLY WEAK)** — The volatility gap between winners and losers in Fig11.
Winners appear to have consistently higher ATR/price across the profile. However: (a) the difference is ~0.001, which is ~4-7% relative, (b) it persists across the entire 30-bar window, suggesting it's a regime property not an entry-bar feature, (c) it's not significant at entry (p=0.715), (d) the IQR bands overlap substantially. The persistence of the gap actually argues against it being exploitable as an entry filter — it's not a localized pre-entry signal.
Support: [Fig11], [Tbl05]

---

## Phase 2 Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Files created | trade_list.csv, trade_repro_check.csv, Tbl04, Tbl05, Tbl06, Fig09..Fig14e, 02_trade_eda.md, phase2_trade_eda.py |
| 2 | Key Obs/Prop IDs created | Obs15..Obs26 (12 observations, 0 propositions) |
| 3 | Blockers / uncertainties | VDO marginal signal (p=0.086) — ambiguous. Could be real weak effect or noise at n=201. |
| 4 | Gate status | **PASS_TO_NEXT_PHASE** |

**Rationale for PASS_TO_NEXT_PHASE:**
Phase 2 found one marginal signal (VDO, p=0.086) and otherwise comprehensive nulls across volume, TBR, and volatility features at entry. The data supports proceeding to formalization (Phase 3) to rigorously assess whether the VDO marginal signal or any remaining structural property warrants filter design, or whether the evidence points to STOP_VDO_NEAR_OPTIMAL / STOP_NO_SIGNAL.

---

## Deliverables

- `02_trade_eda.md` — this file
- `code/phase2_trade_eda.py` — reproducible script
- `figures/Fig09_volume_profile.png`
- `figures/Fig10_tbr_profile.png`
- `figures/Fig11_volatility_profile.png`
- `figures/Fig12_vdo_histogram.png`
- `figures/Fig13_vdo_scatter.png`
- `figures/Fig14a_worst_loser_1.png`
- `figures/Fig14b_worst_loser_2.png`
- `figures/Fig14c_worst_loser_3.png`
- `figures/Fig14d_worst_loser_4.png`
- `figures/Fig14e_worst_loser_5.png`
- `tables/trade_list.csv`
- `tables/trade_repro_check.csv`
- `tables/Tbl04_trade_groups.csv`
- `tables/Tbl05_entry_separation.csv`
- `tables/Tbl06_vdo_entry_stats.csv`
