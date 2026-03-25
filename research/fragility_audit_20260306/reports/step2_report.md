# Step 2 Report — Cross-Strategy Trade Structure & Fragility Audit

**Date**: 2026-03-06
**Scope**: Track B — comparative episode-ledger build, home-run dependence, behavioral fragility for 6 VTREND candidates
**Status**: COMPLETE — all artifacts written, all checks PASS

---

## 1. Executive Summary

Step 2 builds the cross-strategy view that Step 1's E0-only audit could not provide. All 6 VTREND candidates (E0, E5, SM, LATCH, E0_plus_EMA1D21, E5_plus_EMA1D21) are audited using the same frozen diagnostic methods, producing 12 canonical episode ledgers, 4 cross-strategy comparison tables, 3 pairwise structure-delta analyses, and style/fragility classifications for every candidate.

**Key findings:**

1. **All 6 candidates are home-run dependent in unit-size view.** CAGR goes negative within 6-14 trades removed (6-10% of trades). No candidate is a "grinder."

2. **Native view separates two groups.** E0 and E0_plus_EMA1D21 are the most concentrated (top-5 = 83-90% of PnL, cliff-like decay). SM/LATCH are the most resilient natively (zero-cross at 10.8%, smooth decay) because vol-targeted sizing compresses dollar-denominated dispersion. E5 and E5_plus are intermediate.

3. **SM and LATCH are near-duplicates** at the trade-structure level. Same trade count, same hold time, same zero-cross points, same giveback, same style labels. The hysteresis mechanism produces no measurable structural differentiation.

4. **The EMA(21d) overlay preserves structure but improves selectivity.** It removes ~10% of trades (mostly small losers), improving win rate (+1-2 pp), profit factor (+0.10), and reducing top-5 concentration (5-7 pp). It does not transform a home-run strategy into a grinder.

5. **Behavioral fragility is universal and high.** All 6 candidates are harmed by skipping after 2 consecutive losses (delta Sharpe ranging -0.159 to -0.263). Every signal must be taken.

6. **E0 Step 1 regression: 13/13 PASS.** Step 2 reproduces Step 1 E0 outputs exactly.

7. **E5_plus_EMA1D21 profile gap: CLOSED.** Full T1-T8 profile computed from trade CSV + H4 bars.

---

## 2. Inputs and Provenance

### 2.1 Candidate Registry

| Candidate | Trade CSV Source | Expected N | Profile Mode |
|-----------|----------------|-----------|--------------|
| E0 | `results/parity_20260305/eval_e0_vs_e0/results/trades_candidate.csv` | 192 | imported |
| E5 | `results/parity_20260305/eval_e5_vs_e0/results/trades_candidate.csv` | 207 | imported |
| SM | `results/parity_20260305/eval_sm_vs_e0/results/trades_candidate.csv` | 65 | imported |
| LATCH | `results/parity_20260305/eval_latch_vs_e0/results/trades_candidate.csv` | 65 | imported |
| E0_plus_EMA1D21 | `results/parity_20260305/eval_ema21d1_vs_e0/results/trades_candidate.csv` | 172 | imported |
| E5_plus_EMA1D21 | `results/parity_20260306/eval_e5_ema21d1_vs_e0/results/trades_candidate.csv` | 186 | computed_step2 |

### 2.2 Canonical Parameters

- Period: 2019-01-01 to 2026-02-20 (6.5 years)
- Fee: 50 bps round-trip (harsh)
- NAV0: $10,000
- Resolution: H4
- MFE/MAE: computed from H4 OHLC bars

### 2.3 Profile Sources

5 candidates import canonical profiles from `results/trade_profile_8x5/{label}/profile.json`. E5_plus_EMA1D21 had no existing profile (the gap identified in Step 0). Step 2 computed the full T1-T8 profile from the trade CSV + H4 bars using the same algorithms, closing the gap.

---

## 3. RECON_ASSERT and Regression Results

### 3.1 Candidate RECON

| Candidate | Expected N | Observed N | Period | Fee | Status |
|-----------|-----------|-----------|--------|-----|--------|
| E0 | 192 | 192 | 2019-01-04 to 2026-01-21 | 50 bps RT | **PASS** |
| E5 | 207 | 207 | 2019-01-04 to 2026-01-21 | 50 bps RT | **PASS** |
| SM | 65 | 65 | 2019-01-06 to 2026-01-19 | 50 bps RT | **PASS** |
| LATCH | 65 | 65 | 2019-01-06 to 2026-01-19 | 50 bps RT | **PASS** |
| E0_plus_EMA1D21 | 172 | 172 | 2019-01-05 to 2026-01-20 | 50 bps RT | **PASS** |
| E5_plus_EMA1D21 | 186 | 186 | 2019-01-05 to 2026-01-20 | 50 bps RT | **PASS** |

All 6 candidates: **RECON PASS**

### 3.2 E0 Step 1 Regression

13/13 checks PASS against Step 1 artifacts:

| Check | Step 1 Value | Step 2 Value | Match |
|-------|-------------|-------------|-------|
| trade_count | 192 | 192 | PASS |
| giveback_valid_count | 188 | 188 | PASS |
| giveback_median | 1.206 | 1.206 | PASS |
| native_zero_cross_index | 6 | 6 | PASS |
| unit_size_zero_cross_index | 11 | 11 | PASS |
| native_cliff_terminal | True | True | PASS |
| native_cliff_cagr | True | True | PASS |
| unit_cliff_terminal | True | True | PASS |
| unit_cliff_cagr | True | True | PASS |
| skip_n2_delta_sharpe | -0.263 | -0.263 | PASS |
| skip_n3_delta_sharpe | -0.109 | -0.109 | PASS |
| skip_n4_delta_sharpe | +0.001 | +0.001 | PASS |
| skip_n5_delta_sharpe | +0.004 | +0.004 | PASS |

### 3.3 Episode Ledger Validation

All 12 ledgers (6 candidates x 2 views) pass structural checks:

| Check | All 12 | Details |
|-------|--------|---------|
| Row count matches expected | PASS | E0=192, E5=207, SM=65, LATCH=65, E0_plus=172, E5_plus=186 |
| Episode IDs unique | PASS | No duplicates |
| Hold metrics present | PASS | hold_days, hold_bars populated |
| Exit reason present | PASS | Non-null for all rows |
| MFE/MAE present | PASS | mfe_pct, mae_pct populated |
| Giveback computed | PASS | Where MFE > 0 |
| Rank columns populated | PASS | positive_contribution_rank assigned |

### 3.4 E5_plus_EMA1D21 Gap Closure

| Metric | Status |
|--------|--------|
| Profile computed | YES |
| Trade count verified | 186 |
| MFE/MAE from H4 bars | YES |
| Gini, HHI, effective_n | Computed |
| Saved to trade_profile_8x5 | NO (Step 2 artifacts only) |

**Gap: CLOSED**

---

## 4. Cross-Strategy Trade Structure Comparison

| Candidate | N | Win% | Avg Win | Avg Loss | PF | Med Hold | Skew | Gini | HHI | Eff N |
|-----------|---|------|---------|----------|-----|----------|------|------|-----|-------|
| E0 | 192 | 41.7 | 10.0% | -3.0% | 1.61 | 4.8d | 3.66 | 0.609 | 0.017 | 57.4 |
| E5 | 207 | 43.5 | 9.2% | -3.0% | 1.67 | 4.3d | 3.39 | 0.600 | 0.015 | 64.7 |
| SM | 65 | 40.0 | 19.4% | -5.1% | 2.64 | 9.8d | 2.46 | 0.539 | 0.040 | 24.8 |
| LATCH | 65 | 41.5 | 18.8% | -5.2% | 2.71 | 9.8d | 2.51 | 0.542 | 0.041 | 24.4 |
| E0_plus | 172 | 43.6 | 10.4% | -3.2% | 1.72 | 5.0d | 3.26 | 0.609 | 0.019 | 51.9 |
| E5_plus | 186 | 44.6 | 9.8% | -3.1% | 1.78 | 4.8d | 3.08 | 0.607 | 0.017 | 59.1 |

Key observations:
- SM/LATCH have 3x fewer trades, 2x longer holds, 2x larger avg win/loss, 1.6x higher profit factor
- E5_plus_EMA1D21 has the highest win rate (44.6%) and profit factor (1.78) among E0-class variants
- Gini is similar across all candidates (0.539-0.609), indicating moderate-high concentration everywhere
- SM/LATCH have higher HHI (0.040-0.041) due to small N, but lower Gini (0.539-0.542)

---

## 5. Cross-Strategy Home-Run Comparison

### 5.1 Top-Trade Concentration (Native View)

| Candidate | Top-1 | Top-3 | Top-5 | Top-10 | Remainder |
|-----------|-------|-------|-------|--------|-----------|
| E0 | 22.9% | 61.7% | **90.2%** | 143.2% | -$94K |
| E5 | 22.0% | 53.0% | 79.0% | 122.6% | -$62K |
| SM | 19.3% | 53.9% | 81.9% | 124.3% | -$5K |
| LATCH | 18.3% | 54.1% | 81.5% | 122.5% | -$3K |
| E0_plus | 23.1% | 58.0% | 83.4% | 134.3% | -$83K |
| E5_plus | 21.2% | 50.0% | **73.8%** | 114.8% | -$46K |

E0 is the most concentrated (top-5 = 90.2%). E5_plus is the least concentrated (73.8%). All have top-10 > 100%, meaning the bottom 90%+ of trades are net negative in aggregate.

SM/LATCH have negative remainders of only -$3K to -$5K (vs -$46K to -$94K for E0-class) because vol-targeted sizing produces smaller dollar dispersion.

### 5.2 Sensitivity Zero-Cross Points

| Candidate | Native ZC Index | Native ZC % | Unit ZC Index | Unit ZC % |
|-----------|----------------|-------------|--------------|----------|
| E0 | 6 | 3.1% | 11 | 5.7% |
| E5 | 8 | 3.9% | 13 | 6.3% |
| SM | 7 | 10.8% | 6 | 9.2% |
| LATCH | 7 | 10.8% | 6 | 9.2% |
| E0_plus | 7 | 4.1% | 12 | 7.0% |
| E5_plus | 8 | 4.3% | 14 | 7.5% |

In native view, E0 is the most fragile (zero-cross at 3.1%), SM/LATCH the most resilient (10.8%). In unit-size view, the ordering partially reverses: SM/LATCH zero-cross at 9.2% while E5_plus holds to 7.5%.

---

## 6. Cross-Strategy Giveback Comparison

| Candidate | Valid | Mean | Median | P90 | >50% MFE | >75% MFE | Hold <1d | Hold 14d+ |
|-----------|-------|------|--------|-----|----------|----------|----------|-----------|
| E0 | 188 | 4.08 | 1.21 | 6.89 | 81.9% | 69.1% | 17.0 | 0.33 |
| E5 | 203 | 3.71 | 1.12 | 7.95 | 82.3% | 67.0% | 13.6 | 0.31 |
| SM | 65 | 3.87 | 1.31 | 10.39 | 78.5% | 66.2% | n/a | 0.50 |
| LATCH | 65 | 4.58 | 1.31 | 13.47 | 78.5% | 67.7% | n/a | 0.50 |
| E0_plus | 168 | 3.79 | 1.09 | 6.10 | 81.5% | 69.0% | 27.2 | 0.34 |
| E5_plus | 182 | 3.39 | **1.05** | 7.65 | 81.3% | 66.5% | 18.4 | 0.31 |

E5_plus_EMA1D21 has the lowest median giveback (1.05x) — the EMA filter most effectively removes whipsawed entries. SM/LATCH have higher giveback on long holds (0.50 vs 0.31-0.34) because their vol-targeted exits allow more retracement.

The pattern is consistent: EMA-overlaid variants have lower giveback than their base versions, and all candidates show the same hold-duration gradient (short holds give back massively, long holds capture most of the move).

---

## 7. Cross-Strategy Cliff-Edge Comparison

### 7.1 Cliff Scores

| Candidate | Native CAGR Cliff | Native Shape | Unit CAGR Cliff | Unit Shape |
|-----------|-------------------|-------------|-----------------|-----------|
| E5 | **25.29** | cliff-like | 4.97 | cliff-like |
| E0_plus | 23.06 | cliff-like | 4.94 | cliff-like |
| E5_plus | 21.61 | cliff-like | 4.34 | cliff-like |
| E0 | 17.36 | cliff-like | 5.64 | cliff-like |
| LATCH | 1.23 | **smooth** | 2.81 | cliff-like |
| SM | 1.19 | **smooth** | 2.76 | cliff-like |

SM and LATCH are the only candidates with smooth native decay — no cliff detected (score < 3.0). Their vol-targeted sizing compresses the dollar-denominated dispersion enough that no single trade removal causes disproportionate damage.

In unit-size view, all 6 candidates are cliff-like. The cliff occurs at trade #1 (the single largest return-pct trade) with terminal cliff scores of 6.2-17.8. This is a universal property: the best return-pct trade is always disproportionately important.

### 7.2 Interpretation

| Candidate | Interpretation |
|-----------|---------------|
| E0-class (E0, E5, E0_plus, E5_plus) | Single-point collapse in both views. One trade removal can shift CAGR from positive to negative. |
| SM/LATCH | Smooth native decay, single-point collapse in unit-size. Vol-targeting provides native resilience but cannot protect against the removal of the best return-pct trade. |

---

## 8. Cross-Strategy Skip-After-N Comparison

### 8.1 Worst Delta Sharpe (N=2)

| Candidate | Trades Skipped | Winners Hit | Top-10 Hit | Delta Sharpe | Delta Sharpe % |
|-----------|---------------|-------------|-----------|-------------|---------------|
| E0 | 37 | 18 | 3 | **-0.263** | -23.1% |
| E5_plus | 33 | 19 | 3 | -0.252 | -19.8% |
| E5 | 36 | 17 | 3 | -0.213 | -17.3% |
| E0_plus | 30 | 15 | 3 | -0.195 | -16.6% |
| SM | 13 | 7 | 3 | -0.175 | -21.4% |
| LATCH | 13 | 7 | 3 | -0.159 | -19.2% |

All 6: **HARMFUL at N=2** (delta Sharpe < -0.15)

### 8.2 Transition to Neutral

| Candidate | Harmful at N=2 | Harmful at N=3 | Neutral at N=4 |
|-----------|---------------|---------------|----------------|
| E0 | YES (-0.263) | YES (-0.109) | YES (+0.001) |
| E5 | YES (-0.213) | YES (-0.150) | YES (+0.022) |
| SM | YES (-0.175) | NO (-0.025) | NO (-0.036) |
| LATCH | YES (-0.159) | YES (-0.138) | YES (+0.026) |
| E0_plus | YES (-0.195) | NO (-0.027) | NO (-0.038) |
| E5_plus | YES (-0.252) | NO (+0.008) | NO (-0.035) |

E0 and E5 remain harmful at N=3. SM, E0_plus, and E5_plus transition to neutral at N=3. LATCH remains harmful at N=3 (delta Sharpe -0.138) despite being the least fragile at N=2.

The universal message: **never skip after 2 consecutive losses**. At N>=4, all candidates are neutral — but by N=4, only 1-8 trades are skipped (too few to matter).

---

## 9. Pairwise Delta Analysis

### 9.1 SM vs LATCH — **NEAR-DUPLICATE**

Every metric is within noise. Same trade count (65), same median hold (9.83d), same zero-cross indices, identical giveback medians. Win rate differs by 1.5 pp, profit factor by 0.07. Style labels, dependence shapes, and cliff scores are identical. The LATCH hysteresis produces no measurable structural differentiation from SM's state machine at the trade-population level.

### 9.2 E0 vs E0_plus_EMA1D21 — **MODESTLY DIFFERENTIATED**

The EMA overlay removes ~20 trades (10.4%), improving:
- Win rate: +1.9 pp
- Profit factor: +0.10
- Top-5 share: -6.8 pp (less concentrated)
- Skip-after-N fragility: -25.9% (less fragile)
- Giveback median: -9.3% (lower)

Style labels remain identical (home-run/home-run/home-run, cliff-like). The native cliff score increases (17.4 → 23.1) because fewer trades make the survivors relatively more important. The improvement is structural but does not change the strategy's character.

### 9.3 E5 vs E5_plus_EMA1D21 — **MODESTLY DIFFERENTIATED**

Same EMA overlay pattern as E0 pair:
- Win rate: +1.1 pp
- Profit factor: +0.11
- Top-5 share: -5.2 pp (E5_plus is the *least concentrated* of all 6)
- Giveback median: -6.5%

**Anomaly**: Skip-after-N fragility *increases* for E5_plus (-0.252 vs -0.213). The filter removes trades that break loss streaks, making surviving loss clusters more damaging. This is the only case where the EMA overlay worsens behavioral fragility.

---

## 10. Answers to the 9 Required Cross-Strategy Questions

### Q1. Are all 6 candidates home-run dependent?

**YES** in unit-size (exposure-neutral) view. All 6 cross zero CAGR within 6-14 trades removed (6-10% of trades). In native view, SM/LATCH are classified as hybrid rather than home-run because their vol-targeted sizing shifts the zero-cross to 10.8% of trades.

### Q2. Which candidate is the most home-run dependent?

**E0** in native view (zero-cross at 3.1%, top-5 = 90.2%, cliff score 17.4). In unit-size view, the ordering is tighter but SM/LATCH zero-cross earliest (9.2%) because they have only 65 trades.

### Q3. Which candidate is the least home-run dependent?

**SM/LATCH** in native view (zero-cross at 10.8%, smooth decay, no cliff detected). In unit-size view, **E5_plus_EMA1D21** (zero-cross at 7.5%, lowest top-5 share at 73.8%).

### Q4. Does the EMA overlay change the home-run classification?

**NO.** The EMA overlay preserves the style label for both E0 and E5. It modestly reduces concentration (5-7 pp lower top-5 share) and improves zero-cross resilience by ~1 trade, but does not transform a home-run strategy into a grinder.

### Q5. Are SM and LATCH structurally distinct at the trade level?

**NO.** They are near-duplicates. Every metric is within noise. The hysteresis mechanism produces no measurable structural differentiation.

### Q6. Which candidate is the most behaviorally fragile?

**E0** (worst skip-after-2 delta Sharpe = -0.263, destroying 23.1% of Sharpe). E5_plus_EMA1D21 is a close second (-0.252). LATCH is the least fragile (-0.159).

### Q7. Is behavioral fragility correlated with home-run dependence?

**Partially.** E0 is both the most home-run dependent and the most behaviorally fragile. But E5_plus is the least concentrated (73.8% top-5 share) yet has the second-worst skip-after-N fragility (-0.252). The correlation is not perfect because skip-after-N is driven by loss-streak clustering patterns, not just PnL concentration.

### Q8. Does any candidate show smooth dependence (no cliff) in both views?

**NO.** SM/LATCH show smooth decay in native view only. All 6 candidates show cliff-like behavior in unit-size view. No candidate has smooth dependence in both views simultaneously.

### Q9. What is the practical implication for live trading?

All 6 candidates require:
1. **Full automation** — missing 3-8 trades (3-4% of total) can destroy all profitability
2. **No behavioral overrides** — skipping after 2 losses destroys 16-23% of Sharpe
3. **Zero-tolerance uptime** — the worst week to miss eliminates 19-23% of total PnL
4. **Acceptance of losing streaks** — max loss streaks of 7-10 trades are structural, not anomalous

The EMA-overlaid variants are marginally more forgiving but do not escape these constraints. Vol-targeted variants (SM/LATCH) are more forgiving natively but have identical unit-size fragility. **No VTREND variant is operationally robust enough to trade manually.**

---

## 11. Limitations and What Remains for Step 3

### 11.1 Limitations of Step 2

1. **Post-hoc trade removal**: The sensitivity analysis removes completed trades from the ledger. It cannot capture the cascading effects of missing a trade on subsequent entry signals (which may depend on equity, position state, or regime indicators).

2. **No replay**: Random-miss, outage-window, and delayed-entry simulations require replaying the backtest engine. Step 2 operates entirely on completed-trade populations.

3. **E5_plus profile not persisted**: The computed profile exists only in Step 2 artifacts, not in the canonical trade_profile_8x5 directory.

4. **Trail stop exit taxonomy**: E5_plus_EMA1D21 shows a display artifact in exit-reason percentages (93% for both trail and trend columns). The per-trade exit reasons are correct in the episode ledgers.

### 11.2 What Step 3 Would Address

If a Step 3 is undertaken, it should focus on replay-dependent operational fragility:
- Random-miss simulations (K random trades removed, 1000+ bootstrap draws)
- Outage-window miss simulations (contiguous calendar windows)
- Delayed-entry simulations (1-4 bars late)

These require engine modifications and are outside Step 2's scope.

---

## 12. Artifact Index

### 12.1 Root Artifacts (`artifacts/step2/`)

| File | Type | Description |
|------|------|-------------|
| `candidate_input_manifest.csv` | CSV | All 6 candidates with paths, expected counts, profile modes |
| `candidate_recon_assertions.csv` | CSV | RECON PASS/FAIL for all 6 |
| `profile_coverage_regression.csv` | CSV | Profile source mode and gap closure status |
| `e0_step1_regression_check.json` | JSON | 13/13 regression checks |
| `cross_strategy_episode_ledger_status.csv` | CSV | 12 ledger validation statuses |
| `cross_strategy_trade_structure_summary.csv` | CSV | T1-T8 metrics for all 6 |
| `cross_strategy_home_run_summary.csv` | CSV | Top-N shares, drop-top-N CAGR/Sharpe |
| `cross_strategy_sensitivity_zero_cross.csv` | CSV | Zero-cross indices and values |
| `cross_strategy_cliff_edge_summary.csv` | CSV | Cliff scores, flags, interpretations |
| `cross_strategy_giveback_summary.csv` | CSV | Giveback stats by candidate and hold bucket |
| `cross_strategy_skip_after_n_summary.csv` | CSV | Skip-after-N deltas for N={2,3,4,5} x 2 views |
| `cross_strategy_style_labels.csv` | CSV | Style/shape/fragility labels per candidate |
| `pairwise_structure_deltas.csv` | CSV | 3 mandatory pairs, 20 metrics each |
| `step2_summary.json` | JSON | Machine-readable summary |
| `method_regression_notes.md` | MD | Profile sources, regression details, conventions |
| `cross_strategy_findings.md` | MD | 7 cross-strategy findings with evidence |
| `pairwise_delta_notes.md` | MD | Written judgments for 3 mandatory pairs |
| `remaining_open_items.md` | MD | What Step 2 did not address |

### 12.2 Figures (`artifacts/step2/`)

| File | Description |
|------|-------------|
| `cross_strategy_native_sensitivity_overlay.png` | Native sensitivity curves (6 candidates overlaid) |
| `cross_strategy_unit_size_sensitivity_overlay.png` | Unit-size sensitivity curves (6 candidates overlaid) |
| `cross_strategy_top5_top10_concentration.png` | Top-5/Top-10 share bar chart |
| `cross_strategy_skip_after_n_sharpe_delta.png` | Skip-after-N delta Sharpe heatmap |

### 12.3 Per-Candidate Subdirectories (`artifacts/step2/candidates/{label}/`)

Each of the 6 candidates has 11 files:

| File | Description |
|------|-------------|
| `native_episode_ledger.csv` | Full Native episode ledger |
| `unit_size_episode_ledger.csv` | Full Unit-Size episode ledger |
| `giveback_summary.json` | Giveback statistics |
| `native_sensitivity_curve.csv` | Native sensitivity curve (0-20% removal) |
| `unit_size_sensitivity_curve.csv` | Unit-size sensitivity curve (0-20% removal) |
| `native_cliff_edge.csv` | Native cliff scores per removal index |
| `unit_size_cliff_edge.csv` | Unit-size cliff scores per removal index |
| `skip_after_n_native.csv` | Skip-after-N results (native view) |
| `skip_after_n_unit_size.csv` | Skip-after-N results (unit-size view) |
| `style_label.json` | Style/shape/fragility classification |
| `candidate_profile.json` | T1-T8 metrics (imported or computed) |

**Total per-candidate files: 66** (6 candidates x 11 files)

### 12.4 Code

| File | Description |
|------|-------------|
| `code/step2/run_step2_track_b.py` | Main Step 2 script (~900 lines, 7 phases) |

---

## Style Label Summary

| Candidate | Native Style | Unit Style | Overall | Native Shape | Unit Shape | Behavioral Fragility |
|-----------|-------------|-----------|---------|-------------|-----------|---------------------|
| E0 | home-run | home-run | **home-run** | cliff-like | cliff-like | HIGH (-0.263) |
| E5 | hybrid | home-run | **hybrid** | cliff-like | cliff-like | HIGH (-0.213) |
| SM | hybrid | home-run | **hybrid** | smooth | cliff-like | HIGH (-0.175) |
| LATCH | hybrid | home-run | **hybrid** | smooth | cliff-like | HIGH (-0.159) |
| E0_plus | home-run | home-run | **home-run** | cliff-like | cliff-like | HIGH (-0.195) |
| E5_plus | hybrid | home-run | **hybrid** | cliff-like | cliff-like | HIGH (-0.252) |

---

*End of Step 2 Report*
