# Spec Request Prompt

Write two separate spec documents, each self-contained enough for an engineer to rebuild everything from scratch without access to chat history, original code, or any other documentation beyond these specs and the two input data files (raw H4 CSV and raw D1 CSV — specify the expected schema, column names, and format of each file within the spec).

---

## Spec 1 — Research Reproduction Spec (Full research process)

Describe every step taken to go from raw data to the frozen winner. No step may be omitted. Each step must specify: **input → logic → output → decision rule**.

### Mandatory requirements

- **Data pipeline & anomaly handling:** Specify how each logged anomaly type was handled — all retained exactly as supplied, with no synthetic repair or row removal. The anomaly classes and their dispositions are:
  - 19 H4 bars with nonstandard duration (close_time not exactly 4h after open_time) — retained, close_time governs feature visibility
  - 8 H4 bars preceding gaps > 4h (missing bars not invented) — retained, next available open used for execution
  - 1 duplicated H4 close_time pair (2017-09-06) — both rows retained because no duplicate open_time; warmup-only impact
  - 1 H4 zero-activity row (2017-09-06 16:00 UTC) — retained, warmup-only
  - No missing values, no impossible OHLC, no duplicate open_time, no duplicate rows in either file
  - Native D1 vs aggregated H4 reconciliation: complete overlapping days match within floating-point tolerance
  Specify the exact order of processing steps (parse UTC → sort → check → reconcile → log).

- **Data splits:** Specify the exact date ranges for each partition:
  - Context/warmup: 2017-08-17 to 2019-12-31
  - Discovery: 2020-01-01 to 2023-06-30
  - Candidate-selection holdout: 2023-07-01 to 2024-09-30
  - Reserve/internal: 2024-10-01 to 2026-03-17
  Specify that the warmup/discovery/holdout/reserve ordering is strict temporal, that holdout stays sealed until the comparison set is frozen from discovery only, and that reserve stays sealed until the exact frozen leader and comparison set are recorded.

- **Discovery walk-forward structure:** 14 quarterly, non-overlapping unseen test folds within the discovery window (2020-Q1 through 2023-Q2), each with expanding training/calibration on all data preceding the test fold. All train-window calibrations (quantile thresholds) recomputed fold by fold.

- **Feature engineering:** List every feature computed across all four buckets, the exact formula, all lookback periods, all threshold modes (zero, fixed_one, train_quantile, absolute, category), and all admissible tails. The full Stage 1 library is:
  - **Native D1** (343 configs scanned, 178 pass gate): 10 families — directional_persistence (posfrac 5/10/20/40), directional_continuation (ret 5/10/20/40/80), trend_quality (retvol 5/10/20/40/80), range_location (rangepct 10/20/40/80), drawdown_pullback (drawdown 20/40/80), volatility_level (atrpct 10/20/40), volatility_clustering (volcluster 5_20/10_40/20_80), participation_volume (volratio 5/10/20), participation_flow (takeratio 1/5/10), candle (bodyfrac/closeloc 1/3), calendar_dow
  - **Native H4** (349 configs scanned, 55 pass gate): same family structure scaled to H4 lookbacks (3/6/12/24/48), plus calendar_hour
  - **Cross-timeframe** (68 configs scanned, 6 pass gate): 8 relation features (x_rel_d1close_atr, x_rel_d1high_atr, x_rel_d1low_atr, x_in_d1range, x_h4atr6_vs_d1atr, x_h4volshare_d1, x_h4ret6_vs_d1ret20, x_h4rangepct_vs_d1trend)
  - **Transported D1 on H4** (343 configs scanned, 179 pass gate): D1 features evaluated on H4 bars as redundancy controls

- **Stage 1 screening gate:** Specify all criteria: positive edge after 20 bps RT cost on aggregate discovery walk-forward, ≥ 20 trades across discovery folds, ≥ 50% of folds nonnegative after cost, no dependence on one isolated quarter, no leakage.

- **Stage 2 shortlist formation:** Specify the keep/drop ledger. 7 candidates kept (4 native D1, 2 native H4, 1 H4 participation), 4 dropped (1 near-duplicate H4 retvol_48 ≈ ret_48, 2 cross-TF cost-fragile, 1 transported clone ρ ≈ 0.9996 with native). Explain why cross-TF relation features and transported clones did not survive.

- **Stage 3 layered architectures:** 3 two-layer candidates constructed (L2_VOLCL_RANGE48_Q60, L2_VOLCL_RET48_Q55, L2_TAKER10_RANGE48_ABS060). 1 three-layer candidate tested and dropped (L3_VOLCL_RANGE48_Q60_ENTRY_TAKER6_ABS052 — trade-count collapse, degraded performance).

- **Candidate comparison & elimination:** Specify the frozen comparison set of 10 candidates (7 single + 3 layered). Specify paired-bootstrap configuration (block sizes 5, 10, 20; metrics: mean daily return, CAGR, Sharpe; run on discovery and pre-reserve segments). Explain each elimination:
  - `L2_VOLCL_RANGE48_Q60`: better discovery Sharpe (1.588 vs 1.267) and lower MDD (-23.4% vs -51.6%), but did NOT show meaningful paired advantage over simpler S_D1_VOLCL5_20_LOW_F1 on pre-reserve data (p_mean_daily_gt0 = 0.825 but p_sharpe_gt0 = 0.271 — mixed). Complexity rule: simpler wins when complex rival lacks meaningful paired advantage. Reserve/internal confirmed: CAGR −25.0%, Sharpe −1.31.
  - `S_H4_RANGE48_HI_Q60`: strongest genuine native H4 rival, but S_D1_VOLCL5_20_LOW_F1 showed meaningful paired advantage on pre-reserve (p_mean_daily_gt0_min = 0.777, p_cagr_gt0 = 0.723, p_sharpe_gt0 = 0.625). Reserve/internal: CAGR −20.2%, Sharpe −0.69.
  - `S_H4_RET48_HI_Q55`: broader plateau (0.75 vs 0.33) but weaker pre-reserve metrics (Sharpe 0.844 vs 1.170). Eliminated by H4 range on paired test.
  - `S_D1_ATR10_HI_Q60`: same broad family as winner, but very sparse trades (32 discovery, 5 holdout, 8 reserve). Pre-reserve paired advantage for winner not meaningful (mixed signals), but ATR10's reserve CAGR −1.3% vs winner's +29.2%.
  - Other candidates eliminated by weaker discovery + holdout + reserve performance.

- **Plateau analysis:** Strict local 80% plateau score. For the winner S_D1_VOLCL5_20_LOW_F1: 3 local cells tested, 1 qualifying → score 0.33. Document that this is NOT a flat tabletop, but accepted because: (a) all coarse volatility-clustering perturbations stayed directionally positive, (b) the broader volatility-state family was independently corroborated by the D1 ATR family, (c) reserve/internal supported this candidate while alternatives broke.

- **Reserve/internal evaluation:** The frozen winner S_D1_VOLCL5_20_LOW_F1 on reserve (2024-10-01 to 2026-03-17): CAGR 29.2%, Sharpe 0.98, MDD −21.1%, 51 trades. Stayed positive. All main rivals turned negative on reserve:
  - L2_VOLCL_RANGE48_Q60: CAGR −25.0%, Sharpe −1.31, MDD −40.8%
  - S_H4_RANGE48_HI_Q60: CAGR −20.2%, Sharpe −0.69, MDD −51.4%
  - S_H4_TAKER6_HI_ABS052: CAGR −29.8%, Sharpe −2.88, MDD −41.0%
  Explain why the V7 protocol does not permit redesign after freeze.

- **Ablation:** Include the ablation table for the volcluster_range_family: gate_only (winner) vs controller_only vs layered_2L vs layered_3L_with_entry, across all segments.

- **Provenance:** Clean independent re-derivation. Only admissible artifacts: RESEARCH_PROMPT_V7.md, data_btcusdt_4h.csv, data_btcusdt_1d.csv. No disallowed prior artifacts consulted. No benchmark specifications supplied or consulted. All tables generated inside the session from raw data.

---

## Spec 2 — System Specification (Frozen winner `S_D1_VOLCL5_20_LOW_F1`)

Describe the final system from `frozen_system.json` with enough precision for an engineer to reimplement it and achieve bit-level matching output.

### Mandatory requirements

- **Signal logic:** The exact signal formula: compute `volcluster_5_20 = rolling_std(log_returns, 5) / rolling_std(log_returns, 20)` on native D1 bars. Log returns = `ln(close_t / close_{t-1})`. Rolling std uses the standard population-or-sample convention used in the research (specify which). The signal is computed on the **previous completed D1 bar** (day t−1).

- **Entry/exit rules:** On day t, be long if `volcluster_5_20` computed from completed day t−1 is ≤ 1.0; go flat if > 1.0. Signal computed at D1 bar close, fill at next D1 bar open. Position direction: long-only / long-flat. No intrabar assumptions.

- **Position sizing:** 100% notional when long, 0% when flat. No leverage, no partial sizing.

- **Regime gate:** No separate regime gate. The volcluster_5_20 threshold IS the complete signal. No additional regime filter.

- **Cost model:** 10 bps per side, 20 bps round-trip. Applied at each entry and each exit.

- **Edge cases:** Specify handling for:
  - Shortened H4 bars (19 nonstandard durations): not relevant — system operates on native D1 only
  - Gaps between D1 bars: none observed in data; if encountered, use next available open for execution
  - Missing data: no missing values in dataset; if encountered, do not invent bars
  - Insufficient history (fewer than 20 bars) to compute volcluster_5_20: no signal generated, no trade during warmup before 2020-01-01
  - Duplicate rows: none observed; if encountered, retain both and log
  - Zero-activity rows: not present in D1 data

- **Conventions:** All timestamps UTC. D1 bar: open_time 00:00:00 UTC to close_time 23:59:59.999 UTC. No H4-to-D1 alignment needed — system uses native D1 bars only. No rounding rules applied.

- **Test vectors:** Include at least 10 test cases with specific input rows (D1 timestamp, close prices for the rolling window) and expected output (volcluster_5_20 value, signal state long/flat, entry/exit price if state change, PnL after cost if trade completed) so an engineer can verify implementation correctness.

---

## General requirements

Both specs must be fully self-contained, written in clear and unambiguous technical language, and must never use phrases like "as described above" — repeat in full wherever needed. The goal: a person who has never seen this research should be able to read the spec, rerun everything from the raw CSVs, and arrive at exactly the same results.
