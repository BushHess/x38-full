# Step 1 Report: E0 Home-Run Dependence & Behavioral Fragility Audit (Track A)

**Date**: 2026-03-06
**Namespace**: `research/fragility_audit_20260306/`
**Repo root**: `/var/www/trading-bots/btc-spot-dev`
**Candidate**: E0 (vtrend, `configs/vtrend/vtrend_default.yaml`)
**Period**: 2019-01-01 to 2026-02-20
**Fee**: 50 bps RT (harsh scenario)
**Initial Cash**: $10,000

---

## 1. Executive Summary

**E0 is a home-run dependent strategy.** Six trades out of 192 (3.1%) determine whether the strategy is profitable at all. Removing the top 5 trades leaves CAGR at 19.3%; removing one more collapses it to -26.1%. This is a structural feature of trend-following with extreme positive skew (3.66) and high PnL concentration (Gini 0.609). The cliff is real and detectable: cliff scores of 3.60 (terminal) and 17.36 (CAGR) both exceed the 3.0 threshold.

Behavioral fragility is confirmed: skipping trades after 2-3 consecutive losses destroys 9-23% of Sharpe by catching top-10 winners that follow loss clusters. At N>=4 the effect disappears. Every signal must be taken.

Giveback analysis shows the trail stop works well for sustained moves (14d+ trades give back only 0.33x MFE) but hemorrhages on short, choppy entries (<1d: 17x giveback). The median trade gives back 1.21x its MFE, typical of an ATR-trail trend follower.

**All reconciliation checks PASS**: 192 trades confirmed, 15/15 T7 anchor points reproduced exactly (tolerance 1e-6), MFE/MAE join 192/192.

---

## 2. RECON_ASSERT

| Check | Asserted | Observed | Status |
|-------|----------|----------|--------|
| Trade count | 192 | 192 | PASS |
| Period | 2019-01-01 to 2026-02-20 | First entry 2019-01-04, last exit 2026-01-21 | PASS |
| Fee | 50 bps RT | Confirmed via run_meta.json | PASS |
| **Overall** | | | **PASS** |

---

## 3. T7 Anchor Check

All 15 T7 anchor points reproduced from the canonical `profile.json`:

| Metric | Computed | Expected | Match |
|--------|----------|----------|-------|
| base_sharpe | 1.137892 | 1.137892 | Exact |
| base_cagr_pct | 61.827940 | 61.827940 | Exact |
| base_total_pnl | 218479.79 | 218479.79 | Exact |
| drop_top1_sharpe | 1.073418 | 1.073418 | Exact |
| drop_top1_cagr_pct | 55.802794 | 55.802794 | Exact |
| drop_top1_pnl | 168541.45 | 168541.45 | Exact |
| drop_top3_sharpe | 0.942888 | 0.942888 | Exact |
| drop_top3_cagr_pct | 41.105439 | 41.105439 | Exact |
| drop_top3_pnl | 83763.63 | 83763.63 | Exact |
| drop_top5_sharpe | 0.774896 | 0.774896 | Exact |
| drop_top5_cagr_pct | 19.268321 | 19.268321 | Exact |
| drop_top5_pnl | 21434.98 | 21434.98 | Exact |
| drop_top10_sharpe | 0.461625 | 0.461625 | Exact |
| drop_top10_cagr_pct | -100.000000 | -100.000000 | Exact |
| drop_top10_pnl | -94371.81 | -94371.81 | Exact |

**T7 Anchor Check: PASS (15/15)**

---

## 4. Trade Structure Overview (from T1-T8 profile)

| Metric | Value |
|--------|-------|
| Total trades | 192 |
| Wins / Losses | 80 / 112 |
| Win rate | 41.67% |
| Profit factor | 1.614 |
| Average win | +9.98% |
| Average loss | -3.02% |
| W/L ratio | 3.30 |
| Expectancy | +2.40% per trade |
| Max win streak | 5 |
| Max loss streak | 9 |
| Median hold time | 4.83 days |
| Trail stop exits | 83.9% (161 trades) |
| Trend-exit exits | 16.1% (31 trades) |
| Skewness | +3.66 (extreme positive) |
| Excess kurtosis | 18.73 (leptokurtic) |
| Jarque-Bera | 3075.9 (p=0.0, non-normal) |

---

## 5. Concentration Metrics

| Metric | Value |
|--------|-------|
| Top 1 trade: % of total PnL | 22.9% ($49,938) |
| Top 3 trades: % of total PnL | 61.7% ($134,716) |
| Top 5 trades: % of total PnL | 90.2% ($197,045) |
| Top 10 trades: % of total PnL | 143.2% ($312,852) |
| Remaining 182 trades: net PnL | -$94,372 |
| Gini coefficient | 0.609 |
| HHI | 0.0174 |
| Effective N | 57.4 |

The top 10 trades exceed 100% of total PnL, meaning the other 182 trades are collectively unprofitable. This is the hallmark of a home-run-dependent payoff structure.

---

## 6. Sensitivity Curves

### 6.1 Native View (pnl_usd ranked)

Progressive removal of the highest-PnL trades:

| # Removed | % Removed | Terminal Value | CAGR | Sharpe | Note |
|-----------|-----------|---------------|------|--------|------|
| 0 | 0.0% | $228,480 | 61.83% | 1.138 | Baseline |
| 1 | 0.5% | $178,541 | 55.80% | 1.073 | -$49,938 |
| 3 | 1.6% | $93,764 | 41.11% | 0.943 | |
| 5 | 2.6% | $31,435 | 19.27% | 0.775 | Marginal profitability |
| 6 | 3.1% | $1,403 | -26.07% | 0.687 | **CAGR collapses below zero** |
| 7 | 3.6% | -$24,983 | -100.00% | 0.643 | Terminal below initial cash |
| 10 | 5.2% | -$84,372 | -100.00% | 0.462 | |
| 20 | 10.4% | -$185,879 | -100.00% | -0.086 | |
| 38 | 19.8% | -$232,116 | -100.00% | -0.853 | |

The **critical cliff** is at trade #6: removing it (episode 103, 2023-01-09, a +32.8% / +$30K trade from a January trend) flips the strategy from marginally profitable (CAGR 19.3%) to deeply unprofitable (CAGR -26.1%).

### 6.2 Unit-Size View (return_pct ranked)

| # Removed | % Removed | Terminal Value | CAGR | Sharpe | Note |
|-----------|-----------|---------------|------|--------|------|
| 0 | 0.0% | $354,311 | 73.13% | 1.138 | Baseline |
| 1 | 0.5% | $188,548 | 57.12% | 1.094 | -$165,763 |
| 5 | 2.6% | $45,031 | 26.05% | 0.753 | |
| 10 | 5.2% | $11,559 | 2.25% | 0.217 | Near break-even |
| 12 | 6.3% | $7,634 | -4.07% | -0.017 | **CAGR/Sharpe below zero** |
| 20 | 10.4% | $2,989 | -16.50% | -0.539 | |

Unit-size view shows more resilience (zero-cross at 12 vs 6 trades) because compounding amplifies large percentage returns. But the pattern is the same: a small fraction of trades carries the entire strategy.

---

## 7. Cliff-Edge Detection

| View | Metric | Cliff? | Max Score | At Index | Interpretation |
|------|--------|--------|-----------|----------|----------------|
| Native | Terminal | Yes | 3.60 | 1 | Top trade ($49.9K) is 3.6x the average marginal damage |
| Native | CAGR | Yes | 17.36 | 5 | Removing trade #6 causes 17.4x average CAGR damage |
| Native | Sharpe | Yes | 4.21 | 28 | |
| Unit-size | Terminal | Yes | 17.81 | 1 | The 87.9% return trade is 17.8x average damage |
| Unit-size | CAGR | Yes | 5.64 | 1 | |
| Unit-size | Sharpe | No | 1.32 | - | Sharpe degrades smoothly in unit-size view |

**Cliff-edge judgment: CLIFF-LIKE.** Both views detect cliffs exceeding the 3.0 threshold in terminal and CAGR metrics. The native CAGR cliff (score 17.36) is the most severe, corresponding to the CAGR zero-crossing at trade #6.

---

## 8. Giveback Ratio

### 8.1 Summary Statistics

| Statistic | Value |
|-----------|-------|
| Valid trades | 188 (4 have MFE=0 or negative, giveback=NA) |
| Mean | 4.08x |
| Median | 1.21x |
| P25 | 0.67x |
| P75 | 2.89x |
| P90 | 6.89x |
| P95 | 17.94x |
| % giving back >50% of MFE | 81.9% |
| % giving back >75% of MFE | 69.1% |

### 8.2 By Exit Reason

| Exit Reason | N | Mean Giveback | Median Giveback | Mean Return |
|-------------|---|--------------|-----------------|-------------|
| trail_stop | 161 | 3.15x | 1.05x | +3.09% |
| trend_exit | 31 | 8.96x | 3.10x | -1.24% |

Trail stop exits are more efficient at capturing MFE. Trend-exit trades (EMA cross-down) give back nearly 9x MFE on average, as these often fire during choppy reversals.

### 8.3 By Holding Time

| Bucket | N | Mean Giveback | Mean Return | Mean MFE |
|--------|---|--------------|-------------|----------|
| <1 day | 19 | 17.04x | -2.0% | 0.5% |
| 1-3 days | 51 | 5.40x | -3.5% | 2.0% |
| 3-7 days | 60 | 2.69x | -1.0% | 5.3% |
| 7-14 days | 43 | 0.77x | +4.5% | 11.7% |
| 14+ days | 19 | 0.33x | +28.6% | 42.0% |

Clear pattern: **longer holds = lower giveback**. The 14d+ trades (the home-run winners) give back only 0.33x of their MFE, meaning the trail stop captures 67% of the peak gain. These 19 trades average +28.6% return with mean MFE of 42.0%.

### 8.4 Worst Giveback Trades

The 10 worst giveback trades are all short-duration losers (2-22 bars) that barely moved before reversing. Top: episode 45 (2020-07-11, hold 3 bars, giveback 65.5x). These are not meaningful in dollar terms but show that the entry filter lets through noisy signals that the trail stop quickly stops out.

---

## 9. Skip-After-N-Losses

### 9.1 Results

| N | Skipped | Winners Hit | Top-10 Hit | Delta Sharpe | Delta Sharpe % | Verdict |
|---|---------|-------------|-----------|-------------|---------------|---------|
| 2 | 37 | 18 | 3 | -0.263 | -23.1% | **HARMFUL** |
| 3 | 16 | 7 | 2 | -0.109 | -9.6% | **HARMFUL** |
| 4 | 8 | 3 | 0 | +0.001 | +0.1% | NEUTRAL |
| 5 | 5 | 1 | 0 | +0.004 | +0.3% | NEUTRAL |

### 9.2 Interpretation

At N=2, the strategy skips 37 trades (19.3% of all trades). Of these, 18 are winners, including 3 that rank in the top 10 by PnL. This destroys 23% of Sharpe. The mechanism: after 2 consecutive losses, the next trade has roughly a coin-flip chance of being a winner — and some of those winners are the massive trend-following payoffs.

At N=4-5, the skip count drops to 5-8 trades, none of which are top-10 winners, and the Sharpe impact is negligible.

**Skip-after-N-losses judgment: HARMFUL for N<=3, NEUTRAL for N>=4.**

This confirms the home-run hypothesis: the big winning trades are preceded by unpredictable sequences. Behavioral loss aversion (sitting out after a bad streak) is the primary operational risk.

---

## 10. Style Classification

### 10.1 Classification

| Dimension | Label |
|-----------|-------|
| Native view (pnl_usd) | **home-run** |
| Unit-size view (return_pct) | **home-run** |
| Overall | **home-run** |
| Dependence shape | **cliff-like** |

### 10.2 Evidence Summary

| Criterion | Value | Implication |
|-----------|-------|-------------|
| Top 5 = 90% of PnL | 90.19% | Extreme top-heavy |
| Top 10 > 100% of PnL | 143.19% | Remaining trades net negative |
| CAGR zero-cross | At 6 trades removed (3.1%) | Small sample drives profitability |
| Gini | 0.609 | Moderate-high concentration |
| Skewness | 3.66 | Extreme positive tail |
| Effective N | 57.4 of 192 | Only ~30% of trades "matter" |
| Cliff score | 17.36 (CAGR, native) | Single trade = 17x average damage |
| Win rate | 41.67% | Majority of trades lose |
| W/L ratio | 3.30 | But wins are 3.3x bigger |

### 10.3 Why Not "Hybrid" or "Grind"?

- **Not grind**: A grinder would have many small wins adding up gradually. E0 has 112 losses and only 80 wins, with the top 5 wins accounting for nearly all profit. Without them, it loses money.
- **Not hybrid**: A hybrid would show partial degradation (e.g., dropping from 60% to 30% CAGR after removing top trades). E0 collapses to negative CAGR after removing just 3.1% of trades — this is not partial degradation, it is a cliff.

---

## 11. Answers to Specification Questions

**Q1: Would E0 be profitable without its top 5 trades?**
Barely. Terminal value drops from $228,480 to $31,435 (CAGR 19.3%, Sharpe 0.77). Remove one more trade and CAGR goes negative. The strategy is viable without the top 5, but only marginally. Without the top 10, it loses $94K.

**Q2: Is the dependence cliff-like or smooth?**
Cliff-like. CAGR cliff score 17.36 at trade #6 (native view). Terminal cliff score 3.60 at trade #1. The degradation is discontinuous: trade #6 alone is responsible for a 45-percentage-point CAGR swing.

**Q3: Does skipping after N consecutive losses hurt?**
Yes for N<=3 (destroys 9-23% of Sharpe, hits top-10 trades). No for N>=4 (negligible impact, no top-10 trades hit). Big winners follow loss clusters unpredictably.

**Q4: How much MFE is given back?**
Median 1.21x (typical trade gives back slightly more than it keeps). Short trades (<1d) give back 17x (noise entries, quickly stopped). Long trades (14d+) give back 0.33x (trail captures 67% of peak). The trail stop is well-calibrated for sustained moves.

**Q5: Overall home-run dependence grade?**
**HIGH.** E0 is unambiguously home-run dependent. 3.1% of trades determine profitability. Extreme positive skew (3.66), high Gini (0.609), cliff detection in both views. This is the structural signature of trend-following and means every signal must be taken without exception.

---

## 12. Artifact Index

### Reconciliation & Anchoring
- `artifacts/step1/e0_recon_assertion.json` — RECON_ASSERT result
- `artifacts/step1/e0_anchor_checks.json` — T7 anchor check details (15 points)
- `artifacts/step1/e0_input_manifest.json` — Input file paths and parameters

### Ledgers
- `artifacts/step1/e0_native_episode_ledger.csv` — Native Episode Ledger (192 trades, sorted by pnl_usd)
- `artifacts/step1/e0_unit_size_episode_ledger.csv` — Unit-Size Episode Ledger (192 trades, sorted by return_pct)

### Giveback
- `artifacts/step1/e0_giveback_per_trade.csv` — Per-trade giveback ratio (192 rows)
- `artifacts/step1/e0_giveback_summary.json` — Aggregate giveback statistics
- `artifacts/step1/e0_giveback_by_exit_reason.csv` — Giveback by exit type
- `artifacts/step1/e0_giveback_by_hold_bucket.csv` — Giveback by holding period
- `artifacts/step1/e0_giveback_worst10.csv` — Top 10 worst giveback trades
- `artifacts/step1/e0_giveback_distribution.png` — Giveback histogram

### Sensitivity Curves
- `artifacts/step1/e0_native_sensitivity_curve.csv` — Native sensitivity curve (39 points)
- `artifacts/step1/e0_native_sensitivity_curve.png` — Native sensitivity plot
- `artifacts/step1/e0_unit_size_sensitivity_curve.csv` — Unit-size sensitivity curve (39 points)
- `artifacts/step1/e0_unit_size_sensitivity_curve.png` — Unit-size sensitivity plot

### Cliff-Edge
- `artifacts/step1/e0_cliff_edge_summary.csv` — Cliff detection results (both views)

### Skip-After-N-Losses
- `artifacts/step1/e0_skip_after_n_summary.csv` — Summary table (N=2,3,4,5 x 2 views)
- `artifacts/step1/e0_skip_after_n_event_log.csv` — Per-event detail log
- `artifacts/step1/e0_skip_after_n_impact.png` — Skip impact visualization

### Synthesis
- `artifacts/step1/e0_track_a_summary.json` — Machine-readable synthesis with all classifications
- `artifacts/step1/e0_home_run_fragility_summary.md` — Human-readable synthesis
- `artifacts/step1/e0_method_notes.md` — Methodology documentation
- `artifacts/step1/e0_column_dictionary.csv` — Column definitions for all CSVs

### Code
- `code/step1/run_step1_e0.py` — Reproducible analysis script (6 phases)

### Report
- `reports/step1_report.md` — This file

**Total artifacts**: 24 (21 from script + 3 synthesis documents)

---

## 13. Stop Condition

This report completes Step 1 (Track A). All required artifacts are written.

- RECON_ASSERT: **PASS**
- T7 anchor check: **PASS** (15/15)
- Style classification: Native = **home-run**, Unit-size = **home-run**, Overall = **home-run**
- Dependence shape: **cliff-like** (CAGR cliff score 17.36)
- Skip-after-N harmful: **Yes** (N<=3)
- Giveback: median 1.21x, long-hold trades give back 0.33x

**STOPPED AFTER STEP 1.** Track B (cross-strategy comparison) and all deferred diagnostics (missed-entry, outage, delayed-entry) are out of scope.
