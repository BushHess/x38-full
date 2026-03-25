# CONTAMINATION_LOG

**Purpose:** this file intentionally contains prior-session, data-derived specifics. It should **not** be loaded into a clean re-derivation session before that session has independently frozen its own candidate.

This log lists what is recoverable from the prior session about:

- data ranges that were used,
- splits that are contaminated,
- specific features, lookbacks, thresholds, calibration modes, and candidate families that were tried or selected.

Where the exact loser universe is not fully recoverable, that is stated explicitly.

## Strict bottom line

Under a strict cross-session standard, the current data file no longer contains a globally clean untouched range:

- `2017-08-17` to `2018-12-31` was repeatedly used for warmup, context, audit, and calibration.
- `2019-01-01` to `2023-12-31` was repeatedly used for discovery, walk-forward, model comparison, and redesign.
- `2024-01-01` to `2026-02-20` was repeatedly used as holdout, diagnostic, post-holdout redesign input, and full-context evaluation.
- `2026-02-21` to `2026-03-10` was touched once as a micro-holdout in a later round.

Therefore, **no within-file period should be called globally untouched OOS for a new session**. A new session can still be run on a different split for independent re-derivation, but any within-file “OOS” should be labeled internal unless truly new data is appended.

## 1) Exact data-range usage by research round

| Round | Description | Warmup / context | Discovery / development | Holdout / diagnostic / reserve | Full-context usage | Notes |
|---|---|---|---|---|---|---|
| 1 | D1-only system discovery | 2017-08-17 to 2018-12-31 | 2019-01-01 to 2023-12-31, with WF test years 2020/2021/2022/2023 | 2024-01-01 to 2026-02-20 | 2019-01-01 to 2026-02-20 | Raw file extended beyond 2026-02-20 but evaluation stopped there |
| 2 | First H4+D1 re-run | 2017-08-17 to 2018-12-31 | 2019-01-01 to 2023-12-31, with WF test years 2020/2021/2022/2023 | 2024-01-01 to 2026-02-20 | 2019-01-01 to 2026-02-20 | Same core split as Round 1 |
| 3 | Root-cause redesign | 2017-08-17 to 2018-12-31 | Threshold-build context 2019-01-01 to 2019-12-31; WF evaluation 2020-01-01 to 2023-12-31 | 2024-01-01 to 2026-02-20 | 2019-01-01 to 2026-02-20 and 2020-01-01 to 2026-02-20 | Explicitly post-holdout redesign |
| 4 | Fresh-start scientific re-run | 2017-08-17 to 2018-12-31 | Discovery base from 2019-01-01 onward; WF test years 2020/2021/2022/2023 | 2024-01-01 to 2026-02-20 used as contaminated diagnostic; 2026-02-21 to 2026-03-10 used as micro-holdout | Full file audited to dataset end | This round touched the late-March 2026 slice |
| 5 | Reframed first-principles re-run | 2017-08-17 to 2018-12-31 | 2019-01-01 onward expanding context; reported dev 2020-01-01 to 2023-12-31 | 2024-01-01 to 2026-02-20 used as diagnostic | 2020-01-01 to 2026-02-20 | Produced `new_base` and `new_final_flow` |

## 2) Union contamination map

| Range | How it was used | Contamination level |
|---|---|---|
| 2017-08-17 to 2018-12-31 | warmup, context, audit, calibration support | contaminated |
| 2019-01-01 to 2023-12-31 | discovery, walk-forward, candidate selection, redesign, internal comparison | heavily contaminated |
| 2024-01-01 to 2026-02-20 | final holdout in early rounds, later diagnostic input, post-holdout redesign input, full-context comparison | heavily contaminated |
| 2026-02-21 to 2026-03-10 | micro-holdout in a later round | contaminated |
| Dataset end bars after the last executable next-open return | structurally present but not part of a clean scientific reserve because the late slice was already touched | not eligible for global untouched OOS |

## 3) Data-derived specifics by round

## Round 1 — D1-only system discovery

### Recoverability status
This round is largely recoverable at the feature-family and winner level.

### Exact feature inventory used in Phase 1 (recoverable)

**D1 trend / pullback / state**
- `d1_ret_2`, `d1_ret_5`, `d1_ret_10`, `d1_ret_20`, `d1_ret_30`, `d1_ret_60`
- `d1_trendvol_5`, `d1_trendvol_10`, `d1_trendvol_20`, `d1_trendvol_60`
- `d1_pullback_10`, `d1_pullback_20`
- `d1_draw_10`, `d1_draw_20`
- `d1_dist_high_20`, `d1_dist_high_60`
- `d1_vol_5`, `d1_vol_20`
- `d1_volz_5`, `d1_volz_20`
- `d1_range_ratio_5_20`

**H4 trend / pullback / state**
- `h4_ret_3`, `h4_ret_6`, `h4_ret_12`, `h4_ret_24`, `h4_ret_36`, `h4_ret_48`
- `h4_trendvol_6`, `h4_trendvol_12`, `h4_trendvol_24`, `h4_trendvol_48`
- `h4_vol_6`, `h4_vol_24`
- `h4_rng_6`, `h4_rng_24`
- `h4_draw_6`, `h4_draw_12`, `h4_draw_24`
- `h4_dist_high_24`, `h4_dist_high_48`
- `h4_dist_low_24`, `h4_dist_low_48`

**Flow / order flow**
- `h4_tbuy_3`, `h4_tbuy_6`, `h4_tbuy_12`
- `h4_tbuyz_6`, `h4_tbuyz_24`
- `d1_tbuy_5`, `d1_tbuy_20`
- `d1_tbuyz_5`, `d1_tbuyz_20`

**Bar-shape / candle structure**
- `close_loc`
- `body_pct`
- `d1_close_loc`
- `d1_body_pct_1`

**Seasonality**
- `dow`
- `hour`

**Cross-timeframe / interaction features (recoverable at high confidence, not byte-level guaranteed)**
- `x_trend_align_12_5`
- `x_trend_align_24_10`
- `x_h4_pull_d1trend`
- `x_range_expand`
- `x_contraction`
- `x_breakout_flow`
- `x_flow_trend`
- `x_exhaustion`

### Exact candidate-family search space (recoverable)

- `single_ret`: 9 configs  
  - features: `ret_10`, `ret_20`, `ret_60`
  - quantiles: `0.6`, `0.7`, `0.8`

- `single_trendvol`: 9 configs  
  - features: `trendvol_5`, `trendvol_10`, `trendvol_20`
  - quantiles: `0.6`, `0.7`, `0.8`

- `single_nearhigh`: 12 configs  
  - features: `dist_high_20`, `dist_high_40`, `dist_high_60`, `dist_high_90`
  - quantiles: `0.5`, `0.6`, `0.7`

- `ret_nearhigh`: 108 configs  
  - return features: `ret_10`, `ret_20`, `ret_60`
  - near-high features: `dist_high_20`, `dist_high_40`, `dist_high_60`, `dist_high_90`
  - return quantiles: `0.6`, `0.7`, `0.8`
  - near-high quantiles: `0.5`, `0.6`, `0.7`

- `trendvol_nearhigh`: 108 configs  
  - trend features: `trendvol_5`, `trendvol_10`, `trendvol_20`
  - near-high features: `dist_high_20`, `dist_high_40`, `dist_high_60`, `dist_high_90`
  - trend quantiles: `0.6`, `0.7`, `0.8`
  - near-high quantiles: `0.5`, `0.6`, `0.7`

### Exact selected winner

- Family: `trendvol_nearhigh`
- Selected features: `trendvol_10` + `dist_high_60`
- Selected thresholds: annual expanding quantiles `q80(trendvol_10)` and `q60(dist_high_60)`
- Execution: D1 close signal, next D1 open fill
- Exit: exit when either condition is no longer satisfied
- Reported verdict at that time: internally competitive, not clearly superior to frontier benchmark

## Round 2 — First H4+D1 re-run

### Recoverability status
The full loser universe from this round is **not** fully recoverable. What is recoverable exactly is the finalist set, plateau grid, and frozen winner.

### Exact recoverable slower-timeframe features mentioned in the search and finalist tables

- `d1_ret_40`
- `d1_trendq_40`
- `d1_range_pos_60`
- `d1_dist_high_60`
- `d1_up_frac_10`
- `d1_rvol_10`
- `d1_rvol_5`
- `d1_drawdown_60`
- `d1_range_pos_120`
- `d1_trendq_10`
- `d1_dist_high_120`
- `d1_atrp_60`

### Exact recoverable faster-timeframe features mentioned in the search and finalist tables

- `h4_ret_42`
- `h4_trendq_42`
- `h4_range_pos_42`
- `h4_dist_low_42`
- `h4_buy_ratio_6`

### Exact recoverable finalist pair-family candidates

| Pair family | q1 entry | q1 exit | q2 entry | q2 exit | Dev Sharpe | Dev CAGR | Dev MDD | Trades | Positive windows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `d1_range_pos_60(gt) + h4_trendq_42(gt)` | 0.60 | 0.20 | 0.60 | 0.50 | 1.745 | 71.2% | -25.8% | 75 | 4 |
| `d1_dist_high_60(gt) + h4_range_pos_42(gt)` | 0.70 | 0.60 | 0.70 | 0.40 | 1.655 | 58.5% | -16.7% | 53 | 4 |
| `d1_up_frac_10(gt) + h4_trendq_42(gt)` | 0.60 | 0.20 | 0.60 | 0.50 | 1.651 | 67.3% | -22.4% | 61 | 4 |
| `d1_rvol_10(lt) + h4_dist_low_42(gt)` | 0.40 | 0.80 | 0.60 | 0.50 | 1.577 | 50.7% | -27.5% | 53 | 4 |
| `d1_rvol_5(lt) + h4_dist_low_42(gt)` | 0.40 | 0.50 | 0.70 | 0.60 | 1.561 | 32.9% | -21.5% | 47 | 4 |
| `d1_trendq_40(gt) + h4_buy_ratio_6(lt)` | 0.60 | 0.50 | 0.40 | 0.50 | 1.545 | 58.8% | -26.5% | 119 | 4 |
| `d1_dist_high_60(gt) + h4_dist_low_42(gt)` | 0.70 | 0.60 | 0.70 | 0.50 | 1.602 | 51.1% | -29.5% | 32 | 3 |
| `d1_ret_40(gt) + h4_buy_ratio_6(lt)` | 0.60 | 0.20 | 0.40 | 0.60 | 1.579 | 68.3% | -25.5% | 91 | 3 |
| `d1_range_pos_60(gt) + h4_dist_low_42(gt)` | 0.70 | 0.20 | 0.70 | 0.40 | 1.567 | 58.2% | -31.6% | 31 | 3 |
| `d1_dist_high_120(gt) + h4_dist_low_42(gt)` | 0.70 | 0.20 | 0.70 | 0.40 | 1.547 | 53.3% | -25.2% | 28 | 3 |
| `d1_atrp_60(lt) + h4_dist_low_42(gt)` | 0.40 | 0.50 | 0.70 | 0.20 | 1.410 | 41.9% | -36.5% | 21 | 3 |

### Exact recoverable plateau grid around the winner

- D1 lookback perturbations: `48`, `60`, `72`
- H4 lookback perturbations: `34`, `42`, `50`
- D1 entry quantile perturbations: `0.48`, `0.60`, `0.72`
- H4 entry quantile perturbations: `0.48`, `0.60`, `0.72`
- H4 exit quantile perturbations: `0.40`, `0.50`, `0.60`

### Exact selected winner

- Slower feature: `d1_range_pos_60`
- Faster feature: `h4_trendq_42`
- Entry thresholds: D1 `q60`, H4 `q60`
- Exit threshold: H4 `q50`
- Selected design rule: **no D1 exit clause**
- Final interpretation at that time: D1 regime carries the primary edge; H4 improves timing

## Round 3 — Root-cause redesign

### Recoverability status
The frozen system and the main ablation path are recoverable. A small optional branch (`+flow_entry`) and an old-style comparator branch (`fast_old_like`) are not fully recoverable byte-for-byte.

### Exact macro-channel comparison that was tried

| Label | Feature | Quantile | Calibration lookback | WF Sharpe | Holdout Sharpe |
|---|---|---:|---|---:|---:|
| `fast_30d_ret` | `d1_ret_30` | 0.6 | expanding | 1.6669 | 0.4450 |
| `mid_40d_ret` | `d1_ret_40` | 0.6 | expanding | 1.7574 | 0.6624 |
| `slow_60d_ret_3y` | `d1_ret_60` | 0.5 | trailing 1095d | 1.5884 | 0.8772 |
| `slow_60d_trendq_3y` | `d1_trendq_60` | 0.5 | trailing 1095d | 1.4872 | 1.0142 |

### Exact ablation / refinement variants that were tried

- `macro_only`
- `+micro_hysteresis`
- `+anti_chase_cap (final)`  
  - optional cap feature: `h4_ma_gap_84`
  - cap rule: block entries when above yearly `q90` on trailing `1095d`
- `+flow_entry (optional)`  
  - exact original implementation not fully recoverable
- `fast_old_like`  
  - exact original implementation not fully recoverable

### Exact selected frozen system for that round

- Slower feature: `d1_ret_60`
- Slower quantile: `q50`
- Slower calibration mode: trailing `1095d`
- Faster feature: `h4_trendq_84`
- Faster entry threshold: yearly expanding `q60`
- Faster hold threshold: yearly expanding `q50`
- Execution: H4 close signal, next H4 open fill
- Entry: flat + macro on + faster state above entry threshold
- Hold: long + macro on + faster state above hold threshold
- Exit: long and (macro off or faster state <= hold threshold)
- This round also explicitly considered, but did **not** freeze, an anti-chase cap using `h4_ma_gap_84`

## Round 4 — Fresh-start scientific re-run

### Recoverability status
This round is highly recoverable. The single-feature scan and both combination scans were preserved.

### Exact single-feature scan universe

**Number of configs:** `1440`

**D1 features scanned**
- `d1_atrp_20`, `d1_atrp_60`
- `d1_body_mean_20`
- `d1_close_loc_mean_20`
- `d1_dd_60`
- `d1_dist_high_20`, `d1_dist_high_40`, `d1_dist_high_60`, `d1_dist_high_90`, `d1_dist_high_120`
- `d1_flow_mean_20`, `d1_flow_mean_60`
- `d1_flow_z_20`, `d1_flow_z_60`
- `d1_range_pos_20`, `d1_range_pos_40`, `d1_range_pos_60`, `d1_range_pos_90`, `d1_range_pos_120`
- `d1_ret_20`, `d1_ret_40`, `d1_ret_60`, `d1_ret_90`, `d1_ret_120`
- `d1_ret_over_atr_60`
- `d1_rvol_20`, `d1_rvol_60`
- `d1_trendq_20`, `d1_trendq_40`, `d1_trendq_60`, `d1_trendq_90`, `d1_trendq_120`
- `d1_up_from_low_60`
- `d1_vol_z_20`, `d1_vol_z_60`
- `d1_wick_bias_20`

**H4 features scanned**
- `h4_atrp_12`, `h4_atrp_42`
- `h4_body_mean_12`
- `h4_close_loc_mean_12`
- `h4_dd_42`
- `h4_dist_high_12`, `h4_dist_high_24`, `h4_dist_high_42`, `h4_dist_high_63`, `h4_dist_high_84`
- `h4_flow_mean_12`, `h4_flow_mean_42`
- `h4_flow_z_12`, `h4_flow_z_42`
- `h4_range_pos_12`, `h4_range_pos_24`, `h4_range_pos_42`, `h4_range_pos_63`, `h4_range_pos_84`
- `h4_ret_12`, `h4_ret_24`, `h4_ret_42`, `h4_ret_63`, `h4_ret_84`
- `h4_ret_over_atr_42`
- `h4_rvol_12`, `h4_rvol_42`
- `h4_trendq_12`, `h4_trendq_24`, `h4_trendq_42`, `h4_trendq_63`, `h4_trendq_84`
- `h4_up_from_low_42`
- `h4_vol_z_12`, `h4_vol_z_42`
- `h4_wick_bias_12`

**Exact quantile grids used in the single-feature scan**
- `q_on ∈ {0.4, 0.5, 0.6, 0.7, 0.8}`
- `q_off ∈ {0.3, 0.4, 0.5, 0.6, 0.7, 0.8}` subject to valid state-system ordering
- tails: `high` and `low`

### Exact combo scan stages

**Stage 1 combo scan**
- `1600` configs
- D1 features:
  - `d1_dist_high_60`
  - `d1_range_pos_120`
  - `d1_range_pos_60`
  - `d1_ret_120`
  - `d1_ret_40`
  - `d1_ret_60`
  - `d1_ret_over_atr_60`
  - `d1_trendq_40`
  - `d1_trendq_60`
  - `d1_trendq_90`
- H4 features:
  - `h4_dist_high_63`
  - `h4_flow_mean_12`
  - `h4_range_pos_63`
  - `h4_ret_42`
  - `h4_ret_63`
  - `h4_ret_84`
  - `h4_ret_over_atr_42`
  - `h4_trendq_42`
  - `h4_trendq_84`
  - `h4_up_from_low_42`
- D1 quantiles: `{0.4, 0.5, 0.6, 0.7}`
- H4 quantiles: `{0.5, 0.6, 0.7, 0.8}`

**Refined combo scan**
- `784` configs
- D1 features:
  - `d1_dist_high_60`
  - `d1_range_pos_60`
  - `d1_ret_60`
  - `d1_trendq_60`
  - `d1_trendq_90`
- H4 features:
  - `h4_ret_84`
  - `h4_trendq_42`
  - `h4_trendq_84`
  - `h4_up_from_low_42`
- D1 modes: `expanding`, `rolling`
- H4 modes: `expanding`, `rolling`
- `d1_q_on ∈ {0.4, 0.5, 0.6, 0.7}`
- `d1_q_off ∈ {0.3, 0.4, 0.5, 0.6, 0.7}`
- `h4_q_on ∈ {0.5, 0.6, 0.7, 0.8}`
- `h4_q_off ∈ {0.4, 0.5, 0.6, 0.7, 0.8}` subject to valid state ordering

### Exact selected winner

- Slower feature: `d1_dist_high_60`
- Faster feature: `h4_trendq_84`
- Slower mode: annual expanding
- Faster mode: annual expanding
- Entry thresholds: D1 `q70`, H4 `q70`
- Hold thresholds: D1 `q70`, H4 `q60`
- Position logic: long when both gates are true; flat otherwise
- This round also evaluated alternative candidates labeled `alt_pullback` and `alt_range_state`

## Round 5 — Reframed first-principles re-run that produced `new_base` and `new_final_flow`

### Recoverability status
The preserved decision path is recoverable at the shortlist, family-search, and final-system levels. The full loser universe of the earliest broad scans was not preserved, but the promoted shortlist and all final decisions were preserved.

### Exact preserved D1 single-feature survivor set

- `d1_atrn_20`
- `d1_break_high_40`
- `d1_dist_high_40`
- `d1_ma_gap_40`
- `d1_ma_gap_60`
- `d1_range_compress_10`
- `d1_range_compress_20`
- `d1_range_pos_40`
- `d1_range_pos_60`
- `d1_trendq_40`
- `d1_vol_20`

### Exact preserved H4 single-feature survivor set

- `h4_atrn_42`
- `h4_atrn_63`
- `h4_atrn_84`
- `h4_range_compress_42`
- `h4_range_compress_84`
- `h4_range_compress_126`
- `h4_range_compress_168`
- `h4_ret_168`
- `h4_vol_42`
- `h4_vol_84`
- `h4_vol_126`
- `h4_vol_168`

### Exact promoted shortlist used in the layered search

**Slower candidates**
- `d1_ret_60`
- `d1_trendq_60`
- `d1_range_pos_60`

**Faster candidates**
- `h4_trendq_84`
- `h4_ret_84`
- `h4_ret_168`
- `h4_range_pos_168`

**Optional entry-only filter candidate**
- `h4_buyimb_12`

### Exact coarse dual-gate finalist set (preserved)

| Slower feature | Slower mode | Slower q_on | Faster feature | Faster mode | Faster q_on | Faster q_off | Macro exit used? |
|---|---|---:|---|---|---:|---:|---|
| `d1_range_pos_60` | expanding | 0.6 | `h4_trendq_84` | expanding | 0.7 | 0.5 | yes / no variants both preserved |
| `d1_range_pos_60` | expanding | 0.6 | `h4_ret_84` | trailing-365d | 0.7 | 0.5 | yes / no variants preserved |
| `d1_ret_60` | trailing-1095d | 0.5 | `h4_trendq_84` | expanding | 0.7 | 0.5 | yes / no variants preserved |
| `d1_ret_60` | trailing-1095d | 0.5 | `h4_ret_84` | trailing-365d | 0.7 | 0.5 | yes / no variants preserved |
| `d1_ret_60` | trailing-1095d | 0.5 | `h4_range_pos_168` | trailing-365d | 0.6 | 0.5 | macro-exit variant preserved |
| `d1_range_pos_60` | expanding | 0.6 | `h4_ret_168` | expanding or trailing-1095d | 0.7 | 0.5 | macro-exit variants preserved |
| `d1_ret_60` | trailing-1095d | 0.5 | `h4_trendq_84` | expanding | 0.6 | 0.5 | no-macro-exit variant preserved |

### Exact local-family search that produced `new_base`

Preserved local search compared these core rows:

- `d1_ret_60` or `d1_trendq_60`
- slower mode: `expanding` or `trailing-1095d`
- faster feature: primarily `h4_trendq_84`, plus comparator rows using `h4_ret_84` or `h4_ret_168`
- faster mode: `expanding` or `trailing-1095d`
- `macro_q_on = 0.5` (plus one preserved `0.6` macro row)
- `micro_q_on ∈ {0.6, 0.7}`
- `micro_q_off ∈ {0.5, 0.6}`
- `use_macro_exit ∈ {True, False}`

### Exact selected scientific candidate: `new_base`

- Slower feature: `d1_ret_60`
- Slower calibration mode: `expanding`
- Slower entry quantile: `q50`
- Faster feature: `h4_trendq_84`
- Faster calibration mode: `expanding`
- Faster entry quantile: `q60`
- Faster hold quantile: `q50`
- No macro exit
- Interpretation: slower return persistence as regime-entry gate, faster trend quality as state / hold controller

### Exact plateau grid for `new_base`

- `macro_q ∈ {0.4, 0.5, 0.6}`
- `micro_on ∈ {0.5, 0.6, 0.7}`
- `micro_off ∈ {0.4, 0.5, 0.6}`, with `micro_off <= micro_on`
- macro feature fixed: `d1_ret_60`
- micro feature fixed: `h4_trendq_84`
- modes fixed: both `expanding`
- macro exit fixed: `False`

### Exact practical-refinement search that produced `new_final_flow`

- Base core fixed to the `new_base` family
- Added entry-only flow filter: `h4_buyimb_12`
- Flow tail: `high`
- Flow calibration mode: trailing `365d`
- Flow quantile grid: `{0.50, 0.55, 0.60, 0.65}`
- Base plateau grid retained:
  - `macro_q ∈ {0.4, 0.5, 0.6}`
  - `micro_on ∈ {0.5, 0.6, 0.7}`
  - `micro_off ∈ {0.4, 0.5, 0.6}`, with `micro_off <= micro_on`

### Exact selected practical final candidate: `new_final_flow`

- Slower feature: `d1_ret_60`
- Slower calibration mode: `expanding`
- Slower entry quantile: `q50`
- Faster feature: `h4_trendq_84`
- Faster calibration mode: `expanding`
- Faster entry quantile: `q60`
- Faster hold quantile: `q50`
- Entry-only confirmation filter: `h4_buyimb_12`
- Filter calibration mode: trailing `365d`
- Filter entry quantile: `q55`
- No macro exit
- Entry rule: flat + slower gate on + faster state above entry threshold + flow above confirmation threshold
- Hold rule: once long, ignore slower gate as exit clause; remain long while faster state > hold threshold
- Exit rule: faster state falls to or below hold threshold

## 4) Splits and ranges that are contaminated

The following splits have already been used and should be treated as contaminated for cross-session proof purposes:

- **Split A**
  - warmup: 2017-08-17 to 2018-12-31
  - dev: 2019-01-01 to 2023-12-31
  - final holdout: 2024-01-01 to 2026-02-20

- **Split B**
  - context / calibration: 2019-01-01 onward expanding
  - reported dev: 2020-01-01 to 2023-12-31
  - contaminated diagnostic: 2024-01-01 to 2026-02-20
  - micro-holdout: 2026-02-21 to 2026-03-10

- **Split C**
  - warmup/context: 2017-08-17 to 2018-12-31
  - discovery train base: 2019-01-01 onward
  - walk-forward test years: 2020 / 2021 / 2022 / 2023
  - full-context comparisons through 2026-02-20

## 5) Suggested alternative split options for a new session

### Option 1 — the only strict cross-session clean-OOS option
- Append genuinely new data **after** the current file end.
- Use the current file for discovery and internal selection.
- Reserve only the appended future period as final true OOS.
- Status: **strictly valid**

### Option 2 — internal re-derivation split A
- warmup/context: 2017-08-17 to 2018-12-31
- discovery: 2019-01-01 to 2022-12-31
- selection holdout: 2023-01-01 to 2024-12-31
- reserve: 2025-01-01 to dataset end
- Status: **internal only**, not globally clean

### Option 3 — internal re-derivation split B
- warmup/context: 2017-08-17 to 2018-12-31
- discovery: 2019-01-01 to 2021-12-31
- selection holdout: 2022-01-01 to 2023-12-31
- reserve: 2024-01-01 to dataset end
- Status: **internal only**, not globally clean

## 6) Practical conclusion for a new session

A new session can still be useful for independent re-derivation and convergence testing, but it should proceed under these truths:

- prior specific features, lookbacks, thresholds, and winners listed above are already contaminated;
- no within-file slice currently qualifies as globally untouched OOS under a strict cross-session standard;
- the scientifically correct path to a truly clean OOS proof is to freeze a candidate and evaluate it on **new data not present in the current file**.