# Spec Request Prompt

Write two separate spec documents, each self-contained enough for an engineer to rebuild everything from scratch without access to chat history, original code, or any other documentation beyond these specs and the two input data files (raw H4 CSV and raw D1 CSV — specify the expected schema, column names, and format of each file within the spec).

---

## Spec 1 — Research Reproduction Spec (Full research process)

Describe every step taken to go from raw data to the frozen winner. No step may be omitted. Each step must specify: **input → logic → output → decision rule**.

### Mandatory requirements

- **Data pipeline & anomaly handling:** Specify how each logged anomaly type was handled — all retained exactly as supplied, with no synthetic repair or row removal except one deterministic drop. The anomaly classes and their dispositions are:
  - **D1 data** (3,134 rows, 2017-08-17 to 2026-03-16): 0 duplicate open_time, 0 duplicate close_time, 0 null values in any column, 0 malformed rows, 0 nonstandard durations (all exactly 86,400,000 ms), 0 irregular open gaps, 0 zero-activity rows, 0 impossible OHLC — completely clean, all retained
  - **H4 data** (18,791 rows, 2017-08-17 04:00 to 2026-03-17 16:00 UTC):
    - 20 H4 bars with nonstandard duration (not exactly 14,400,000 ms; includes durations of 7,200,000 ms (9 bars), 10,800,000 ms (2 bars), and various others) — retained, close_time governs feature visibility
    - 8 H4 bars preceded by irregular open gaps (> 14,400,000 ms between consecutive opens; gaps of 28,800,000 ms (5), 43,200,000 ms (2), 115,200,000 ms (1)) — retained, next available open used for execution
    - 1 duplicated H4 close_time pair — both rows retained because no duplicate open_time
    - 1 malformed H4 row — retained in audit but excluded from scoring by deterministic drop rule
    - 1 H4 zero-activity row — **deterministically dropped** (the only row removal in the entire pipeline), yielding 18,790 scoring bars
    - 0 null values in any column, 0 duplicate open_time, 0 impossible OHLC
  - **D1-H4 reconciliation**: 3,134 overlapping days match with 0 material OHLC mismatches (max absolute difference 0.0); volume reconciliation: negligible floating-point variance (max absolute diff ~1.16e-10, max pct diff ~2.20e-16). 11 days have non-6 H4 bars (early exchange anomalies, all in 2017-2020: 2017-08-17 (5), 2017-09-06 (5), 2018-02-08 (1), 2018-02-09 (4), 2018-06-26 (4), 2018-07-04 (5), 2018-11-14 (5), 2019-03-12 (5), 2019-05-15 (4), 2019-08-15 (5), 2020-02-19 (5))
  - Specify the exact order of processing steps (parse UTC → sort by open_time → check duplicates/nulls/OHLC → deterministic drop → reconcile D1 vs H4 → log anomaly register).

- **Input file schema:** Both CSVs share the same 13-column schema: `symbol, interval, open_time, close_time, open, high, low, close, volume, quote_volume, num_trades, taker_buy_base_vol, taker_buy_quote_vol`. All timestamps are integer milliseconds since epoch, interpreted as UTC.

- **Data splits:** Specify the exact date ranges for each partition:
  - Context/warmup: 2017-08-17 to 2019-12-31
  - Discovery: 2020-01-01 to 2023-06-30
  - Candidate-selection holdout: 2023-07-01 to 2024-09-30
  - Reserve/internal: 2024-10-01 to dataset end
  Specify that the warmup/discovery/holdout/reserve ordering is strict temporal, that holdout stays sealed until the comparison set is frozen from discovery only, and that reserve stays sealed until the exact frozen leader and comparison set are recorded.

- **Discovery walk-forward structure:** 14 quarterly, non-overlapping unseen test folds within the discovery window (2020-Q1 through 2023-Q2), each with expanding training/calibration on all data preceding the test fold. All train-window calibrations (quantile thresholds) recomputed fold by fold. The 14 folds are:

  | Fold | Train ends (exclusive) | Test start | Test end |
  |------|----------------------|------------|----------|
  | 1 | 2020-01-01 | 2020-01-01 | 2020-03-31 |
  | 2 | 2020-04-01 | 2020-04-01 | 2020-06-30 |
  | 3 | 2020-07-01 | 2020-07-01 | 2020-09-30 |
  | 4 | 2020-10-01 | 2020-10-01 | 2020-12-31 |
  | 5 | 2021-01-01 | 2021-01-01 | 2021-03-31 |
  | 6 | 2021-04-01 | 2021-04-01 | 2021-06-30 |
  | 7 | 2021-07-01 | 2021-07-01 | 2021-09-30 |
  | 8 | 2021-10-01 | 2021-10-01 | 2021-12-31 |
  | 9 | 2022-01-01 | 2022-01-01 | 2022-03-31 |
  | 10 | 2022-04-01 | 2022-04-01 | 2022-06-30 |
  | 11 | 2022-07-01 | 2022-07-01 | 2022-09-30 |
  | 12 | 2022-10-01 | 2022-10-01 | 2022-12-31 |
  | 13 | 2023-01-01 | 2023-01-01 | 2023-03-31 |
  | 14 | 2023-04-01 | 2023-04-01 | 2023-06-30 |

- **Feature engineering:** List every feature computed across all four buckets, the exact formula, all lookback periods, all threshold modes, and all admissible tails. The full Stage 1 library contains 29 feature families across 4 buckets, generating 1,234 feature-parameter-threshold configurations:

  - **Native D1** (369 configs scanned, 221 promoted; 12 families):
    - `D1_MOM_RET` (directional_persistence): `close_t / close_{t-n} - 1`, n ∈ {3, 5, 10, 20, 40, 80}, tails: high/low, thresholds: sign (0.0) + train_quantile (0.6, 0.7, 0.8)
    - `D1_UP_FRAC` (directional_persistence): rolling mean over n of indicator(close_t > close_{t-1}), n ∈ {3, 5, 10, 20, 40}, tails: high/low, thresholds: structural_level (high: 0.6, low: 0.4) + train_quantile (0.6, 0.7, 0.8)
    - `D1_TREND_QUAL` (trend_quality): n-bar return / (rolling_std(log_return, n) × sqrt(n)), n ∈ {5, 10, 20, 40, 80}, tails: high/low, thresholds: sign (0.0) + train_quantile (0.6, 0.7, 0.8)
    - `D1_RANGE_POS` (location_within_range): (close - rolling_low_n) / (rolling_high_n - rolling_low_n), n ∈ {5, 10, 20, 40, 80}, tails: high/low, thresholds: structural_level (high: 0.8, low: 0.2) + train_quantile (0.6, 0.7, 0.8)
    - `D1_DRAWDOWN` (drawdown_pullback_state): close / rolling_high_n - 1, n ∈ {5, 10, 20, 40, 80}, tails: high/low, thresholds: train_quantile (0.6, 0.7, 0.8) only
    - `D1_ATR_PCT` (volatility_level): ATR_n / close, n ∈ {5, 10, 20, 40}, tails: high/low, thresholds: train_quantile (0.6, 0.7, 0.8) only
    - `D1_VOL_RATIO` (volatility_clustering): ATR_short / ATR_long, (short, long) ∈ {(5,20), (10,40), (20,80)}, tails: high/low, thresholds: train_quantile (0.6, 0.7, 0.8) only
    - `D1_VOL_Z` (participation_flow): (log(volume) - rolling_mean(log(volume), n)) / rolling_std(log(volume), n), n ∈ {5, 10, 20, 40}, tails: high/low, thresholds: sign (0.0) + train_quantile (0.6, 0.7, 0.8)
    - `D1_BUY_RATIO` (participation_flow): rolling mean over n of taker_buy_quote_vol / quote_volume, n ∈ {3, 5, 10, 20}, tails: high/low, thresholds: structural_level (high: 0.55, low: 0.45) + train_quantile (0.6, 0.7, 0.8)
    - `D1_BODY_FRAC` (candle_structure): rolling mean over n of abs(close-open)/(high-low), n ∈ {3, 5, 10, 20}, tails: high/low, thresholds: train_quantile (0.6, 0.7, 0.8) only
    - `D1_CLV_MEAN` (candle_structure): rolling mean over n of ((close-low)/(high-low) - 0.5), n ∈ {3, 5, 10, 20}, tails: high/low, thresholds: sign (0.0) + train_quantile (0.6, 0.7, 0.8)
    - `D1_DOW` (calendar_effect): UTC day-of-week of current daily bar open, categories ∈ {0, 1, 2, 3, 4, 5, 6, weekday, weekend}, tails: categorical, thresholds: categorical (no calibration)

  - **Native H4** (368 configs scanned, 131 promoted; 12 families):
    Same 12 family structure as D1, with H4-appropriate lookback ladders:
    - `H4_MOM_RET`: n ∈ {6, 12, 24, 48, 96, 168}
    - `H4_UP_FRAC`: n ∈ {6, 12, 24, 48, 96}
    - `H4_TREND_QUAL`: n ∈ {12, 24, 48, 96, 168}
    - `H4_RANGE_POS`: n ∈ {12, 24, 48, 96, 168}
    - `H4_DRAWDOWN`: n ∈ {12, 24, 48, 96, 168}
    - `H4_ATR_PCT`: n ∈ {12, 24, 48, 96}
    - `H4_VOL_RATIO`: (short, long) ∈ {(12,48), (24,96), (48,168)}
    - `H4_VOL_Z`: n ∈ {12, 24, 48, 96}
    - `H4_BUY_RATIO`: n ∈ {6, 12, 24, 48}
    - `H4_BODY_FRAC`: n ∈ {6, 12, 24, 48}
    - `H4_CLV_MEAN`: n ∈ {6, 12, 24, 48}
    - `H4_OPEN_HOUR`: categories ∈ {0, 4, 8, 12, 16, 20, weekday, weekend}

  - **Cross-timeframe** (128 configs scanned, 53 promoted; 5 families):
    - `XR_CLOSE_VS_D1_EMA`: H4 close / latest completed D1 EMA_n - 1, n ∈ {5, 10, 20, 40}, tails: high/low, thresholds: sign (0.0) + train_quantile (0.6, 0.7, 0.8)
    - `XR_POS_IN_PREV_D1_RANGE`: (H4 close - latest completed D1 low) / (latest completed D1 high - low) - 0.5, context: latest_completed_d1_bar, tails: high/low, thresholds: sign (0.0) + train_quantile (0.6, 0.7, 0.8)
    - `XR_CLOSE_VS_D1_ROLLHIGH`: H4 close / latest completed D1 rolling_high_n - 1, n ∈ {5, 10, 20, 40}, tails: high/low, thresholds: train_quantile (0.6, 0.7, 0.8) only
    - `XR_MOM_ALIGNMENT`: H4 n-bar return × latest completed D1 m-bar return, (d1,h4) ∈ {(5,6), (10,24), (20,48), (40,96)}, tails: high/low, thresholds: sign (0.0) + train_quantile (0.6, 0.7, 0.8)
    - `XR_H4_RETURN_OVER_D1_ATR`: H4 n-bar return / (latest completed D1 ATR_m / close), (d1,h4) ∈ {(5,6), (10,24), (20,48), (40,96)}, tails: high/low, thresholds: sign (0.0) + train_quantile (0.6, 0.7, 0.8)

  - **Transported D1 on H4** (369 configs scanned, 226 promoted): All 12 D1 feature families evaluated on H4 bars using the latest completed D1 signal as redundancy controls. Transported configs use the same parameter ladders, tails, and thresholds as their native D1 counterparts. Each transported config maps 1:1 to a native D1 source (e.g., `D1_MOM_RET|n=40|high|sign|thr=0.0|TRANSPORT_TO_H4` → source `D1_MOM_RET|n=40|high|sign|thr=0.0`).

- **Threshold calibration modes:** Specify the four allowed modes:
  - `sign`: fixed structural threshold at 0.0 (no calibration)
  - `train_quantile`: percentiles {60%, 70%, 80%} computed on expanding training distribution, recalibrated per fold
  - `structural_level`: fixed structural thresholds — range_pos (high: 0.8, low: 0.2), up_frac (high: 0.6, low: 0.4), buy_ratio (high: 0.55, low: 0.45)
  - `categorical`: no calibration (calendar features)

- **Stage 1 screening gate:** Specify all criteria. A config is promoted if ALL of the following hold:
  - Positive edge after 20 bps RT cost on aggregate discovery walk-forward (`stage1_gate_positive_edge`)
  - ≥ 20 entry trades across discovery folds (`stage1_gate_trades`)
  - ≥ 50% of 14 folds nonnegative after cost (`stage1_gate_fold_share`)
  - No single isolated quarter dependence: at least 3 positive folds, and no single positive fold contributes > 65% of the sum of all positive fold net returns (`stage1_gate_isolated_quarter`)
  - No unresolved leakage or anomaly ambiguity
  Result: 631 of 1,234 configs promoted (221 native D1, 131 native H4, 53 cross-TF, 226 transported).

- **Stage 2 shortlist formation:** Specify the keep/drop ledger. From 631 promoted configs, form candidate systems by selecting best representative per family-cluster. 30 candidates evaluated:
  - **11 kept** (for comparison set or layering):
    - `S_D1_TREND` (comparison_set): Strong native D1 trend frontier; simplest slow-trend representative
    - `S_D1_VOLHIGH` (layering_only): Useful orthogonal slower volatility context for layering search
    - `S_H4_TREND` (comparison_set): Strongest simple native H4 trend representative
    - `S_H4_TREND_Q` (comparison_set): Nearest calibrated nonlinear rival in H4 trend cluster
    - `S_H4_PULLBACK` (layering_only): Very consistent controller candidate with low drawdown
    - `S_H4_VOLQUIET` (layering_only): Most useful native H4 volatility controller candidate
    - `S_H4_CANDLE` (layering_only): Optional entry/confirmation hypothesis
    - `S_XR_D1EMA` (comparison_set): Strong simple cross-timeframe candidate with broad plateau
    - `S_XR_D1ROLL` (comparison_set): Nearest nonlinear cross-timeframe rival
    - `L2_D1_TREND_AND_H4_VOLQUIET` (comparison_set): Best two-layer defensive alternative
    - `L2_D1_VOLHIGH_AND_H4_PULLBACK` (comparison_set): Backup layered alternative with different permission gate
  - **1 audit-only** (dropped): `S_D1_TREND_TRANSPORT` — retained only for transport-vs-native redundancy audit; not eligible as independent frontier
  - **1 dropped Stage 2**: `S_D1_CLV` — positive but weaker and less orthogonal than retained slow-trend/volatility reps
  - **10 dropped Stage 5A** (two-layer): L2_H4_TREND_AND_H4_VOLQUIET, L2_XR_D1EMA_AND_H4_VOLQUIET, L2_D1_TREND_AND_H4_PULLBACK, L2_D1_VOLHIGH_AND_H4_CANDLE, L2_H4_TREND_AND_H4_PULLBACK, L2_XR_D1EMA_AND_H4_PULLBACK, L2_D1_VOLHIGH_AND_H4_VOLQUIET, L2_D1_TREND_AND_H4_CANDLE, L2_H4_TREND_AND_H4_CANDLE, L2_XR_D1EMA_AND_H4_CANDLE — all inferior to retained layered alternatives
  - **6 dropped Stage 5A** (three-layer): L3_D1_TREND_AND_H4_VOLQUIET_ENTRY_H4_BODYCONF, L3_D1_TREND_AND_H4_VOLQUIET_ENTRY_H4_BUYCONF, L3_D1_VOLHIGH_AND_H4_PULLBACK_ENTRY_H4_BODYCONF, L3_D1_VOLHIGH_AND_H4_PULLBACK_ENTRY_H4_BUYCONF, L3_H4_TREND_AND_H4_VOLQUIET_ENTRY_H4_BODYCONF, L3_H4_TREND_AND_H4_VOLQUIET_ENTRY_H4_BUYCONF — third layer did not beat simpler two-layer core and reduced trade count
  Explain why transported clones did not survive (near-perfect correlation ρ with native counterpart, e.g., transported D1_MOM_RET|n=40 has discovery Sharpe 1.716 vs native 1.694, near-identical fold structure).

- **Stage 3 layered architectures:** 12 two-layer candidates constructed from 4 frontiers × 3 controllers (S_D1_TREND, S_D1_VOLHIGH, S_H4_TREND, S_XR_D1EMA as gates with S_H4_PULLBACK, S_H4_VOLQUIET, S_H4_CANDLE as controllers). 2 two-layer candidates kept for comparison set. 6 three-layer candidates tested (2 two-layer cores × 3 entry filters using H4_BODYCONF, H4_BUYCONF) — all dropped because third layer did not beat simpler two-layer core.

- **Candidate comparison & elimination:** Specify the frozen comparison set of 7 candidates (5 single + 2 layered). Specify paired-bootstrap configuration:
  - Method: moving block bootstrap on daily UTC returns
  - Block sizes: 5, 10, 20 days
  - Resamples per block size: 3,000
  - Seed: 20260318
  - Paired bootstrap uses common resampled indices
  - Meaningful paired advantage definition: P(mean_daily_return_diff > 0) ≥ 0.95 on pooled resamples AND on at least 2 of 3 block sizes, with point estimate ≥ 5e-5
  - Common daily domain: 1,735 days for all pre-reserve pairwise comparisons

  Explain each elimination step:
  - **Cluster reduction (H4 trend):** `S_H4_TREND` chosen over `S_H4_TREND_Q` because the more complex calibrated rival failed to show meaningful paired daily-return advantage (pooled P = 0.560, indeterminate).
  - **Cluster reduction (cross-TF):** `S_XR_D1EMA` chosen over `S_XR_D1ROLL` because the more complex rival failed to show meaningful paired daily-return advantage (pooled P = 0.682, indeterminate).
  - **Layered elimination:** `S_D1_TREND` showed meaningful paired advantage over `L2_D1_TREND_AND_H4_VOLQUIET` (point diff = +0.00114/day, pooled P = 0.985) and over `L2_D1_VOLHIGH_AND_H4_PULLBACK` (point diff = +0.00149/day, pooled P = 0.990). Both layered candidates eliminated.
  - **Final choice among cluster winners:** `S_D1_TREND` vs `S_H4_TREND` vs `S_XR_D1EMA` — none showed meaningful paired daily-return advantage over the others (S_D1_TREND vs S_H4_TREND: P = 0.518; S_D1_TREND vs S_XR_D1EMA: P = 0.671). `S_D1_TREND` chosen because: (a) simplest native single-timeframe leader (1 layer, 1d execution, no cross-TF dependence), (b) highest pre-reserve mean daily return among cluster winners, (c) strongest cost resilience (discovery CAGR drops only from 101.2% to 96.0% when cost rises from 20 to 50 bps RT, whereas S_XR_D1EMA drops from 90.1% to 77.4%).
  - **Deterministic tie-break rule** (if needed): broader plateau → lower pre-reserve drawdown at comparable growth → stronger fold consistency → higher trade count → lower cross-timeframe dependence → fixed lexical order.

- **Plateau analysis:** For the winner `S_D1_TREND` (D1_MOM_RET, n=40, high, sign, thr=0.0):
  - Tunable quantity: lookback n. Parameter ladder: {3, 5, 10, 20, 40, 80}.
  - Nearest perturbations approximating ±20% of 40: n=20 (0.8×) and n=80 (1.2×).
  - n=20 (sign, thr=0.0): Discovery Sharpe 1.174 (69.3% of winner's 1.694). Directionally positive but below 80% retention threshold.
  - n=80 (sign, thr=0.0): Discovery Sharpe 0.691 (40.8% of winner's 1.694). Directionally positive but below 80% retention threshold.
  - Strict plateau score: 0/2 = 0.00 (no perturbation reaches 80% of the winner's Sharpe).
  - Accepted despite low plateau score because: (a) ALL 6 lookback values (n=3 through n=80) remain directionally positive on discovery (Sharpe 0.545 to 1.694), demonstrating the momentum family is robustly directional; (b) the broader D1 momentum family with train_quantile thresholds also shows strong performance at n=40 (train_quantile Q60: 1.551, Q70: 1.594), confirming n=40 is a genuine peak, not a spike; (c) reserve/internal supported this candidate while alternatives broke.

- **Reserve/internal evaluation:** The frozen winner `S_D1_TREND` on reserve (2024-10-01 to dataset end, at 20 bps RT):
  - Sharpe 0.8734, CAGR 24.2%, MDD −24.0%, 35 trades, exposure 53.6%
  - Win rate 47.1%, mean trade return +2.83%, median trade return −0.99%
  - Top 5 winner concentration 95.2%, mean holding 16.6 bars, median holding 7 bars

  All comparison set rivals on reserve at 20 bps RT:
  - `S_H4_TREND`: Sharpe 0.652, CAGR 16.4%, MDD −29.6%, 120 trades
  - `S_H4_TREND_Q`: Sharpe 0.772, CAGR 16.4%, MDD −22.5%, 72 trades
  - `S_XR_D1EMA`: Sharpe 0.455, CAGR 9.6%, MDD −32.9%, 108 trades
  - `S_XR_D1ROLL`: Sharpe 0.814, CAGR 19.6%, MDD −18.9%, 104 trades
  - `L2_D1_TREND_AND_H4_VOLQUIET`: Sharpe 0.644, CAGR 8.6%, MDD −14.2%, 47 trades
  - `L2_D1_VOLHIGH_AND_H4_PULLBACK`: Sharpe 0.439, CAGR 5.5%, MDD −13.3%, 24 trades

  At 50 bps RT, all candidates remain positive except `S_XR_D1EMA` (CAGR −1.9%, Sharpe 0.089), confirming `S_D1_TREND`'s cost resilience advantage (CAGR 19.8% at 50 bps).

  Explain why the V8 protocol does not permit redesign after freeze: the comparison set was locked before reserve was unblinded; redesign after observing reserve results would invalidate the temporal separation.

- **Evidence label:** `INTERNAL ROBUST CANDIDATE`. Explain the three-tier label hierarchy:
  - `CLEAN OOS CONFIRMED`: requires globally independent out-of-sample data (not achievable within same file)
  - `INTERNAL ROBUST CANDIDATE`: procedurally independent within-session selection, positive on reserve, but discovery/holdout/reserve all from the same file
  - `NO ROBUST IMPROVEMENT`: freeze failed to produce a credible candidate

- **Provenance:** Clean independent re-derivation. Only admissible artifacts: RESEARCH_PROMPT_V8.md, data_btcusdt_4h.csv, data_btcusdt_1d.csv. No prior-session reports, logs, shortlist tables, frozen candidates, benchmark specifications, or serialized outputs from earlier sessions consulted before freeze. All non-raw artifacts generated inside the current session from admissible raw inputs. Global cross-session split independence NOT claimed (discovery, holdout, reserve all from same file).

- **Complexity budget:** Specify the limits that governed the search:
  - Max 3 logical layers, max 1 slower contextual layer, max 1 faster state layer, max 1 optional entry-only confirmation layer
  - Max 6 tunable quantities in final candidate
  - No regime-specific parameter sets

- **Finality statement:** This V8 run is the final same-file audit on the current BTC/USDT file pair. After reserve/internal evaluation is reported, same-file prompt iteration stops; stronger claims require appended future data.

---

## Spec 2 — System Specification (Frozen winner `S_D1_TREND`)

Describe the final system from `frozen_system.json` with enough precision for an engineer to reimplement it and achieve bit-level matching output.

### Mandatory requirements

- **Signal logic:** The exact signal formula: compute `D1_MOM_RET(n=40) = close_t / close_{t-40} - 1` on native D1 bars. `close_t` is the close price of the current completed D1 bar. `close_{t-40}` is the close price of the D1 bar 40 bars prior. The signal is computed on the **previous completed D1 bar** (day t−1). No logarithm, no normalization — simple arithmetic return over 40 trading days.

- **Entry/exit rules:** On day t, be long if `D1_MOM_RET(n=40)` computed from completed day t−1 is > 0.0; go flat if ≤ 0.0. Signal computed at D1 bar close, fill at next D1 bar open. Position direction: long-only / long-flat. No intrabar assumptions. Threshold is structural at 0.0 (sign-based), not calibrated from training data.

- **Position sizing:** 100% notional when long, 0% when flat. No leverage, no partial sizing, no pyramiding, no discretionary overrides.

- **Regime gate:** No separate regime gate. The D1_MOM_RET(n=40) > 0.0 condition IS the complete signal. No additional regime filter, volatility filter, or second layer.

- **Cost model:** 10 bps per side, 20 bps round-trip. Applied at each entry and each exit. Cost deducted from portfolio value at execution time.

- **Architecture summary:**
  - Layers: 1 (single-feature state system)
  - Execution timeframe: native D1
  - Native timeframe: D1
  - Cross-timeframe dependence: none
  - Feature family: directional_persistence
  - Calibration mode: fixed_structural (no parameter tuning from data)

- **Edge cases:** Specify handling for:
  - H4 bars (nonstandard durations, gaps, etc.): not relevant — system operates on native D1 only
  - Gaps between D1 bars: none observed in data; if encountered, use next available open for execution
  - Missing data: no missing values in dataset; if encountered, do not invent bars
  - Insufficient history (fewer than 40 bars) to compute D1_MOM_RET(n=40): no signal generated, no trade during warmup before 2020-01-01
  - Duplicate rows: none observed in D1 data; if encountered, retain both and log
  - Zero-activity rows: not present in D1 data; if encountered, retain and log

- **Conventions:** All timestamps UTC. D1 bar: open_time 00:00:00 UTC, close_time 23:59:59.999 UTC. Duration: 86,400,000 ms. No H4-to-D1 alignment needed — system uses native D1 bars only. No rounding rules applied. Daily return alignment: aggregate realized strategy bar returns to daily UTC returns by compounding all open-to-open interval returns whose interval starts on the UTC date.

- **Key results (for verification):**

  | Segment | Cost RT | Sharpe | CAGR | Max DD | Trades | Pos fold share |
  |---------|---------|--------|------|--------|--------|----------------|
  | Discovery WFO | 20 bps | 1.6941 | 101.2% | −48.3% | 61 | 64.3% (9/14) |
  | Discovery WFO | 50 bps | 1.6396 | 96.0% | −50.9% | 61 | 64.3% (9/14) |
  | Holdout | 20 bps | 1.0819 | 40.8% | −43.4% | 34 | — |
  | Holdout | 50 bps | 0.9751 | 35.2% | −44.9% | 34 | — |
  | Reserve | 20 bps | 0.8734 | 24.2% | −24.0% | 35 | — |
  | Reserve | 50 bps | 0.7518 | 19.8% | −25.4% | 35 | — |

  Discovery fold-level net returns (14 folds, 20 bps):
  `[0.188, 0.434, 0.068, 1.506, 1.031, −0.047, 0.088, 0.154, −0.130, −0.099, −0.119, −0.091, 0.592, 0.044]`

  Discovery fold-level trade counts:
  `[4, 4, 8, 1, 0, 3, 2, 4, 7, 7, 6, 11, 2, 2]`

- **Test vectors:** Include at least 10 test cases with specific input rows (D1 timestamp, close prices for the rolling window) and expected output (D1_MOM_RET value, signal state long/flat, entry/exit price if state change, PnL after cost if trade completed) so an engineer can verify implementation correctness. Test vectors should include:
  - A normal long entry (D1_MOM_RET crosses above 0.0)
  - A normal flat exit (D1_MOM_RET crosses below 0.0)
  - The warmup boundary (first tradeable signal after 2020-01-01)
  - A case near zero threshold (D1_MOM_RET very close to 0.0)
  - A cost deduction example (entry + exit with explicit PnL after 20 bps RT)
  - A consecutive-same-signal case (no position change, no cost)

---

## General requirements

Both specs must be fully self-contained, written in clear and unambiguous technical language, and must never use phrases like "as described above" — repeat in full wherever needed. The goal: a person who has never seen this research should be able to read the spec, rerun everything from the raw CSVs, and arrive at exactly the same results.

Every numeric value referenced in the spec must match the frozen artifacts:
- `frozen_system.json` — system architecture and results
- `frozen_system_spec.md` — human-readable system specification
- `locked_protocol_settings.json` — execution protocol and validation rules
- `data_audit_summary.json` — data quality audit metrics
- `provenance_declaration.json` — session provenance and independence claims
- `stage1_feature_registry.csv` — 1,234 feature evaluation records
- `frozen_stage1_feature_manifest.csv` — 29 feature family definitions
- `shortlist_ledger.csv` — 30 candidate systems and decisions
- `frozen_comparison_set_ledger.csv` — 7 frozen comparison set members
- `validation_results.csv` — 7 systems × 3 segments × 2 costs = 42 evaluation records
- `reserve_internal_summary.csv` — reserve detailed metrics for all 7 systems
- `pre_reserve_pairwise_matrix_long.csv` — 42 pairwise bootstrap comparisons
