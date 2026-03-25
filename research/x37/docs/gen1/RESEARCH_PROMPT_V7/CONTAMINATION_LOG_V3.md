# CONTAMINATION_LOG_V3

**Purpose:** this file intentionally contains prior-session, data-derived specifics. It should **not** be loaded into a clean re-derivation session before that session has independently frozen its own candidate.

This log lists what is recoverable from the earlier sessions about:

- data ranges that were used,
- splits that are contaminated,
- specific features, lookbacks, thresholds, calibration modes, and candidate families that were tried or selected.

Where the exact loser universe is not fully recoverable, that is stated explicitly.

## Strict bottom line

Under a strict cross-session standard, the current data file no longer contains a globally clean untouched range.

At this point, the union of prior work has touched **every within-file period from `2017-08-17` to dataset end** in at least one of these roles:

- warmup / context / audit / calibration,
- discovery / walk-forward / internal comparison,
- holdout / diagnostic / redesign input,
- reserve/internal evaluation,
- full-file audit through dataset end.

Therefore, **no within-file period should be called globally untouched OOS for a new session**. A new session can still be run on a different split for independent re-derivation, but any within-file “OOS” should be labeled internal unless genuinely new data is appended after the current file end.

## Session-level summary

| Session | Final frozen outcome | Independence status | Clean OOS status |
|---|---|---|---|
| Session 1 (historical multi-round session preserved in the original log) | `new_final_flow` | not independent now; all specifics contaminated | no clean within-file OOS |
| Session 2 (Protocol V5 session) | `SF_EFF40_Q70_STATIC` | **not** a strict blind re-derivation; shortlist / freeze tables were reproduced from an earlier internal run before final validation | no clean within-file OOS |
| Session 3 (Protocol V6 session) | `S3_H4_RET168_Z0` | procedurally blind to prior artifacts before freeze, but not globally independent because the same file was already contaminated across sessions | no clean within-file OOS |

## 1) Exact data-range usage by research round

| Round | Description | Warmup / context | Discovery / development | Holdout / diagnostic / reserve | Full-context usage | Notes |
|---|---|---|---|---|---|---|
| 1 | D1-only system discovery | 2017-08-17 to 2018-12-31 | 2019-01-01 to 2023-12-31, with WF test years 2020/2021/2022/2023 | 2024-01-01 to 2026-02-20 | 2019-01-01 to 2026-02-20 | Raw file extended beyond 2026-02-20 but evaluation stopped there |
| 2 | First H4+D1 re-run | 2017-08-17 to 2018-12-31 | 2019-01-01 to 2023-12-31, with WF test years 2020/2021/2022/2023 | 2024-01-01 to 2026-02-20 | 2019-01-01 to 2026-02-20 | Same core split as Round 1 |
| 3 | Root-cause redesign | 2017-08-17 to 2018-12-31 | Threshold-build context 2019-01-01 to 2019-12-31; WF evaluation 2020-01-01 to 2023-12-31 | 2024-01-01 to 2026-02-20 | 2019-01-01 to 2026-02-20 and 2020-01-01 to 2026-02-20 | Explicitly post-holdout redesign |
| 4 | Fresh-start scientific re-run | 2017-08-17 to 2018-12-31 | Discovery base from 2019-01-01 onward; WF test years 2020/2021/2022/2023 | 2024-01-01 to 2026-02-20 used as contaminated diagnostic; 2026-02-21 to 2026-03-10 used as micro-holdout | Full file audited to dataset end | This round touched the late-March 2026 slice |
| 5 | Reframed first-principles re-run | 2017-08-17 to 2018-12-31 | 2019-01-01 onward expanding context; reported dev 2020-01-01 to 2023-12-31 | 2024-01-01 to 2026-02-20 used as diagnostic | 2020-01-01 to 2026-02-20 | Produced `new_base` and `new_final_flow` |
| 6 | Protocol V5 execution / artifact-assisted internal re-derivation | 2017-08-17 to 2018-12-31 used as context and threshold history; full-file audit through dataset end | 2019-01-01 to 2022-12-31 by split logic, with WF test years 2020/2021/2022 | 2023-01-01 to 2024-12-31 selection holdout; 2025-01-01 to dataset end reserve/internal | D1 and H4 files audited to dataset end; frozen D1 rule revalidated from raw data to dataset end | Shortlist and freeze-selection tables were reproduced from an earlier internal run; not a strict blind re-derivation |
| 7 | Protocol V6 clean-blind internal re-derivation | 2017-08-17 to 2019-12-31 | 2020-01-01 to 2022-12-31, with semiannual unseen folds from 2020-H1 through 2022-H2 | 2023-01-01 to 2024-06-30 selection holdout; 2024-07-01 to dataset end reserve/internal | D1 and H4 files audited to dataset end | No prior result artifacts consulted before freeze; still internal only because the file was already contaminated |

## 2) Union contamination map

| Range | How it was used | Contamination level |
|---|---|---|
| 2017-08-17 to 2019-12-31 | warmup, context, audit, calibration support, yearly-threshold history, fold initialization | contaminated |
| 2020-01-01 to 2024-06-30 | discovery, walk-forward, candidate selection, redesign, internal comparison, selection holdout | heavily contaminated |
| 2024-07-01 to dataset end | reserve/internal evaluation, late-slice diagnostic, full-file audit, frozen-rule validation through file end | contaminated |
| Entire file from 2017-08-17 to dataset end | union of all sessions now touches every within-file bar in at least one research role | not eligible for global untouched OOS |

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


## Round 6 — Protocol V5 execution / artifact-assisted internal re-derivation that froze `SF_EFF40_Q70_STATIC`

### Recoverability status

This round is **highly recoverable at the frozen-rule and final-ranking level**, but **not** fully recoverable as a strict blind re-derivation.

What is recoverable exactly from surviving artifacts:

- data-audit coverage,
- the declared V5 split,
- Stage 1 aggregate counts and representative leaders,
- the serious-candidate shortlist,
- the pre-reserve ranking,
- the reserve/internal ranking,
- the local plateau table around the final family,
- the frozen winner and its exact yearly threshold table,
- validation metrics for discovery, holdout, reserve/internal, cost stress, bootstrap, and regime decomposition.

What is **not** fully recoverable byte-for-byte:

- the full underlying Stage 1 registry for all `99` D1 features and `162` H4 features,
- every loser config inside the broader search universe,
- the exact raw-code implementation of the non-winning layered rivals.

Additional caveat:

- the report explicitly states that the shortlist tables and frozen-candidate selection tables were **reproduced from an earlier internal run**, while the frozen-rule validation charts were re-derived directly from the supplied raw CSVs;
- therefore this round should be logged as **artifact-assisted**, not as a strict clean blind re-derivation.

### Exact data coverage and split usage

**Exact preserved data-audit coverage**

| timeframe   |   rows | start_open           | end_open             |   dup_open |   dup_close |   gap_events |   missing_expected_bars |   nonstandard_duration_rows |   zero_volume_rows |
|:------------|-------:|:---------------------|:---------------------|-----------:|------------:|-------------:|------------------------:|----------------------------:|-------------------:|
| D1          |   3134 | 2017-08-17 00:00 UTC | 2026-03-16 00:00 UTC |          0 |           0 |            0 |                       0 |                           0 |                  0 |
| H4          |  18791 | 2017-08-17 04:00 UTC | 2026-03-17 12:00 UTC |          0 |           1 |            8 |                      16 |                          20 |                  1 |

**Protocol V5 split actually used**

- Context / warmup only: `2017-08-17` to `2018-12-31`
- Discovery window: `2019-01-01` to `2022-12-31`
- Discovery walk-forward scored on unseen years: `2020`, `2021`, `2022`
- Candidate-selection holdout: `2023-01-01` to `2024-12-31`
- Reserve/internal: `2025-01-01` to dataset end
- Full-file audit touched the raw file to dataset end on both D1 and H4
- Frozen D1 rule was revalidated from raw data across the live range ending at dataset end

### Exact preserved Stage 1 scan summary

| timeframe   |   n_features |   median_sharpe20 |   top_sharpe20 | pct_positive_sharpe20   | pct_positive_2022   |
|:------------|-------------:|------------------:|---------------:|:------------------------|:--------------------|
| D1          |           99 |              0.43 |           1.74 | 74.7%                   | 5.1%                |
| H4          |          162 |             -0.03 |           1.7  | 46.9%                   | 2.5%                |

Interpretation preserved by the report:

- slower D1 context features dominated native H4 standalone continuation logic after cost;
- H4 still mattered in layered rivals, but native fast-only edge was materially weaker and less stable.

### Exact preserved representative leaders from the Round 6 scan

**Top representative feature per category and timeframe**

| timeframe   | category                | feature                       |   sharpe20 | cagr20   | mdd20   |   entries20 | exposure20   |   sharpe50 |
|:------------|:------------------------|:------------------------------|-----------:|:---------|:--------|------------:|:-------------|-----------:|
| D1          | trend_quality           | d1_ema_gap_40                 |       1.74 | 92.7%    | -26.9%  |          31 | 40.2%        |       1.67 |
| D1          | drawdown_pullback       | d1_bounce_40                  |       1.7  | 93.9%    | -29.0%  |          24 | 37.1%        |       1.65 |
| D1          | directional_persistence | d1_ret_40                     |       1.56 | 78.5%    | -37.6%  |          18 | 37.4%        |       1.51 |
| D1          | range_location          | d1_range_pos_40               |       1.48 | 64.3%    | -26.2%  |          47 | 30.1%        |       1.36 |
| D1          | volatility              | d1_tr_mean_20                 |       1.13 | 55.0%    | -51.1%  |          18 | 34.9%        |       1.09 |
| D1          | participation_flow      | d1_rel_qvol_40                |       1.08 | 43.2%    | -34.1%  |         116 | 28.9%        |       0.8  |
| D1          | candle_structure        | d1_gap_prevclose              |       0.87 | 37.7%    | -56.7%  |         206 | 51.7%        |       0.48 |
| D1          | calendar                | d1_is_weekend                 |       0.44 | 7.0%     | -77.2%  |         156 | 71.5%        |       0.19 |
| H4          | drawdown_pullback       | x_aligned_d1_bounce_40        |       1.7  | 93.8%    | -32.3%  |          24 | 37.1%        |       1.65 |
| H4          | directional_persistence | x_aligned_d1_ret_40           |       1.56 | 78.4%    | -39.3%  |          18 | 37.4%        |       1.51 |
| H4          | cross_timeframe         | x_h4_vs_d1_sma_40             |       1.5  | 76.1%    | -42.0%  |          63 | 41.6%        |       1.35 |
| H4          | range_location          | x_aligned_d1_range_pos_40     |       1.48 | 64.3%    | -27.1%  |          47 | 30.1%        |       1.36 |
| H4          | trend_quality           | x_aligned_d1_sma_gap_20       |       1.26 | 56.2%    | -55.3%  |          56 | 40.1%        |       1.13 |
| H4          | volatility              | x_aligned_d1_rv_40            |       1.06 | 44.9%    | -43.4%  |          10 | 26.2%        |       1.04 |
| H4          | participation_flow      | x_aligned_d1_taker_buy_mean_3 |       0.77 | 4.7%     | -3.9%   |           6 | 0.6%         |       0.69 |
| H4          | calendar                | h4_is_weekend                 |       0.76 | 31.9%    | -71.5%  |         156 | 71.5%        |       0.53 |
| H4          | candle_structure        | h4_close_loc                  |      -0.72 | -29.5%   | -71.2%  |        1347 | 25.9%        |      -4.28 |

**Best native H4 features (not transported slower-state clones)**

| feature       | category          |   sharpe20 | cagr20   | mdd20   |   entries20 |   year2020_sh |   year2021_sh |   year2022_sh |
|:--------------|:------------------|-----------:|:---------|:--------|------------:|--------------:|--------------:|--------------:|
| h4_bounce_48  | drawdown_pullback |       0.96 | 41.5%    | -48.6%  |         145 |          2.44 |          0.8  |         -0.98 |
| h4_is_weekend | calendar          |       0.76 | 31.9%    | -71.5%  |         156 |          2.14 |          0.69 |         -0.77 |
| h4_sma_gap_48 | trend_quality     |       0.75 | 25.5%    | -43.9%  |         195 |          1.4  |          0.84 |         -0.59 |
| h4_tr_mean_48 | volatility        |       0.64 | 21.2%    | -48.3%  |          28 |          1    |          1.1  |         -0.44 |
| h4_ema_gap_24 | trend_quality     |       0.59 | 17.4%    | -42.8%  |         223 |          1.66 |          0.56 |         -1.06 |

Important recoverability note:

- the tables above preserve the representative leaders, not the entire raw Stage 1 registry;
- therefore the full exact loser universe from this round is **not** fully serialized.

### Exact serious-candidate families preserved by the report

- Single-feature D1 context systems:
  - `SF_EMA40_Q65_STATIC`
  - `SF_EFF40_Q70_STATIC`
  - `d1_tr_mean_20` family
- Layered alternatives preserved in the final comparison set:
  - `L2_EMA40S70__H4B48E65`
  - `L2_EFF40S70__H4TR48R55`
  - `L2_EFF40S70__XH4D1SMA20S60`

### Exact pre-reserve ranking (recorded)

| candidate                  |   sharpe20 | cagr20   | mdd20   |   trades | exposure   | win_rate   | mean_trade   | median_trade   |   mean_hold_days |   median_hold_days | top_winner_conc   | bottom_tail   |
|:---------------------------|-----------:|:---------|:--------|---------:|:-----------|:-----------|:-------------|:---------------|-----------------:|-------------------:|:------------------|:--------------|
| SF_EMA40_Q65_STATIC        |       1.6  | 72.2%    | -40.9%  |       62 | 38.2%      | 43.5%      | 6.0%         | -0.8%          |            11.26 |               4    | 62.5%             | -6.1%         |
| L2_EMA40S70__H4B48E65      |       1.58 | 51.9%    | -23.5%  |      102 | 17.1%      | 33.3%      | 2.4%         | -0.6%          |             3.07 |               0.83 | 46.2%             | -4.8%         |
| L2_EFF40S70__H4TR48R55     |       1.35 | 45.4%    | -27.1%  |       52 | 18.3%      | 61.5%      | 4.2%         | 0.8%           |             6.45 |               1.83 | 63.2%             | -7.9%         |
| SF_EFF40_Q70_STATIC        |       1.34 | 52.9%    | -33.3%  |       55 | 27.0%      | 65.5%      | 4.7%         | 1.5%           |             8.98 |               5    | 57.2%             | -11.1%        |
| L2_EFF40S70__XH4D1SMA20S60 |       1.2  | 33.3%    | -27.3%  |       68 | 17.6%      | 38.2%      | 2.5%         | -0.4%          |             4.73 |               1.33 | 67.1%             | -4.8%         |

Recorded selection hinge from the report:

- `SF_EMA40_Q65_STATIC` was the **headline leader before reserve/internal**;
- the simpler efficiency family remained alive because it was competitive, simpler, and sat inside a viable plateau;
- the final comparison set was frozen before reserve/internal was opened.

### Exact reserve/internal ranking after freeze (recorded)

| candidate                  |   sharpe20 | cagr20   | mdd20   |   trades20 | exp20   |   sharpe50 | cagr50   |   2025_sh |   2026_sh |
|:---------------------------|-----------:|:---------|:--------|-----------:|:--------|-----------:|:---------|----------:|----------:|
| SF_EFF40_Q70_STATIC        |       0.74 | 15.9%    | -31.2%  |         17 | 19.1%   |       0.56 | 11.1%    |      0.08 |      2.41 |
| L2_EFF40S70__H4TR48R55     |       0.71 | 14.2%    | -25.8%  |         17 | 13.4%   |       0.52 | 9.5%     |     -0.04 |      2.37 |
| L2_EFF40S70__XH4D1SMA20S60 |      -0.64 | -6.5%    | -18.3%  |         13 | 6.3%    |      -0.94 | -9.5%    |     -1.17 |      1.83 |
| SF_EMA40_Q65_STATIC        |      -0.72 | -9.7%    | -14.0%  |         12 | 14.8%   |      -0.94 | -12.3%   |     -0.68 |     -2.38 |
| L2_EMA40S70__H4B48E65      |      -2.02 | -11.7%   | -15.6%  |         16 | 4.1%    |      -2.4  | -15.1%   |     -2.22 |    nan    |

Recorded interpretation:

- `SF_EMA40_Q65_STATIC` failed reserve/internal and was rejected;
- `L2_EMA40S70__H4B48E65` failed reserve/internal even more severely;
- `L2_EFF40S70__XH4D1SMA20S60` also failed reserve/internal;
- `L2_EFF40S70__H4TR48R55` stayed positive but lost on simplicity and paired holdout evidence;
- `SF_EFF40_Q70_STATIC` became the final winner because it survived reserve/internal while the more elaborate or stronger pre-reserve rivals did not.

### Exact plateau evidence preserved around the winning family

|   lookback |    q | mode      |   disc_sh | disc_cagr   | disc_mdd   |   disc_trades |   hold_sh | hold_cagr   | hold_mdd   |   hold_trades |   pre_sh | pre_cagr   | pre_mdd   |   pre_trades |   reserve_sh |
|-----------:|-----:|:----------|----------:|:------------|:-----------|--------------:|----------:|:------------|:-----------|--------------:|---------:|:-----------|:----------|-------------:|-------------:|
|         32 | 0.7  | static    |      1.18 | 47.6%       | -35.7%     |            47 |      1.84 | 58.5%       | -15.3%     |            21 |     1.37 | 51.8%      | -35.7%    |           68 |         0.23 |
|         32 | 0.75 | static    |      1.31 | 46.2%       | -22.3%     |            38 |      1.69 | 47.7%       | -12.2%     |            20 |     1.42 | 46.8%      | -22.3%    |           58 |        -0.04 |
|         40 | 0.7  | static    |      1.24 | 52.7%       | -33.3%     |            40 |      1.61 | 53.3%       | -18.4%     |            15 |     1.34 | 52.9%      | -33.3%    |           55 |         0.74 |
|         40 | 0.75 | static    |      1.07 | 39.1%       | -35.8%     |            39 |      1.61 | 52.3%       | -18.4%     |            14 |     1.25 | 44.2%      | -35.8%    |           53 |         0.68 |
|         48 | 0.7  | expanding |      1.13 | 46.1%       | -46.6%     |            42 |      1.69 | 60.2%       | -15.2%     |            18 |     1.31 | 51.5%      | -46.6%    |           60 |         0.92 |
|         48 | 0.7  | rolling   |      0.66 | 19.9%       | -65.8%     |            50 |      1.63 | 58.4%       | -23.0%     |            22 |     1    | 34.0%      | -65.8%    |           72 |         0.55 |

Interpretation preserved by the report:

- the winning family lived on a usable plateau rather than a single isolated spike;
- `lookback = 40`, `q = 0.70`, static calendar-year thresholds was chosen as a balanced cell, not as a fragile headline maximum.

### Exact frozen winner and calibration details

**Frozen winner**
- `SF_EFF40_Q70_STATIC`

**Exact preserved system-level details**
- Market: BTC/USDT spot
- Direction: long only
- Base timeframe: D1
- Feature: `d1_eff_40`
- Feature family: Kaufman-style efficiency ratio on D1 close
- Lookback: `40`
- Signal timing: compute on D1 close
- Fill timing: next D1 open
- Threshold quantile: `0.70`
- Quantile method: linear / Hyndman–Fan type 7
- Calibration mode: calendar-year static threshold, expanding-history calibration
- Visibility rule: for each calendar year, use only feature values whose `close_time` is earlier than that year start
- Within-year threshold behavior: constant inside the year
- Position sizing: binary notional `1.0` long / `0.0` flat
- Regime gate: implicit; the efficiency threshold itself is the regime gate
- Separate exit layer: none
- Separate entry confirmation layer: none

**Exact yearly thresholds recoverable from the reconstructed frozen-system spec**

|   year |   threshold_eff40_q70 |
|-------:|----------------------:|
|   2018 |              0.414047 |
|   2019 |              0.271547 |
|   2020 |              0.276491 |
|   2021 |              0.290809 |
|   2022 |              0.282524 |
|   2023 |              0.27323  |
|   2024 |              0.276921 |
|   2025 |              0.271404 |
|   2026 |              0.264156 |

**Exact signal rule**
- Long if `d1_eff_40 >= threshold_for_that_calendar_year`
- Flat otherwise
- Evaluate on D1 close, execute state at next D1 open

### Exact preserved validation metrics for the frozen winner

**By period**
- Discovery `2020–2022`: Sharpe `1.24`, CAGR `52.7%`, max drawdown `-33.3%`, trades `40`
- Holdout `2023–2024`: Sharpe `1.61`, CAGR `53.3%`, max drawdown `-18.4%`, trades `15`
- Reserve/internal `2025+`: Sharpe `0.74`, CAGR `15.9%`, max drawdown `-31.2%`, trades `17`

**Cost stress table preserved by the report**

|   round_trip_bps | period        |   sharpe | cagr   | mdd    |
|-----------------:|:--------------|---------:|:-------|:-------|
|                0 | Discovery_All |     1.32 | 57.4%  | -29.6% |
|                0 | Holdout_All   |     1.66 | 55.6%  | -18.2% |
|                0 | Reserve_All   |     0.79 | 17.6%  | -31.2% |
|                0 | Live_2020_end |     1.31 | 48.1%  | -31.2% |
|               20 | Discovery_All |     1.25 | 53.3%  | -32.4% |
|               20 | Holdout_All   |     1.61 | 53.3%  | -18.4% |
|               20 | Reserve_All   |     0.67 | 14.3%  | -32.4% |
|               20 | Live_2020_end |     1.25 | 44.8%  | -32.4% |
|               50 | Discovery_All |     1.16 | 47.5%  | -36.6% |
|               50 | Holdout_All   |     1.53 | 49.9%  | -18.8% |
|               50 | Reserve_All   |     0.5  | 9.5%   | -34.2% |
|               50 | Live_2020_end |     1.15 | 39.9%  | -36.6% |
|              100 | Discovery_All |     1    | 38.2%  | -42.9% |
|              100 | Holdout_All   |     1.4  | 44.4%  | -20.0% |
|              100 | Reserve_All   |     0.2  | 2.0%   | -37.2% |
|              100 | Live_2020_end |     0.98 | 32.1%  | -42.9% |

### Exact evidence label recorded for this round

- Evidence label: `INTERNAL ROBUST CANDIDATE`
- The label was **not** `CLEAN OOS CONFIRMED`, because the reserve window could not be treated as globally untouched across sessions.
- This round therefore contributes useful internal evidence and a fully recoverable frozen system, but **not** a clean cross-session OOS proof.

### Bottom line for contamination purposes

This round contaminated the following additional knowledge beyond the prior log:

- the V5 split `2019-01-01` to dataset end at discovery / holdout / reserve granularity,
- the final frozen winner `SF_EFF40_Q70_STATIC`,
- the exact frozen winner thresholds by calendar year,
- the preserved serious-candidate shortlist and reserve ranking,
- the preserved plateau table around the winning family.

It also extended practical file-end contact to the current dataset end through audit and frozen-rule validation.


## Round 7 — Protocol V6 clean-blind internal re-derivation that froze `S3_H4_RET168_Z0`

### Recoverability status

This round is **highly recoverable** from surviving artifacts. Unlike the Protocol V5 session, this run did **not** consult prior reports, prior frozen systems, prior shortlist tables, or prior contamination logs before freeze.

Important caveat:

- this was procedurally blind to prior artifacts before freeze,
- but it was still run on a file that was already contaminated by earlier sessions,
- therefore it is **not** globally clean within-file OOS evidence.

### Exact data coverage and split usage

**Exact preserved data-audit coverage**

| timeframe   |   rows | open_time_start_utc             | open_time_end_utc               | close_time_start_utc            | close_time_end_utc              |   duplicate_open_time_rows |   duplicate_close_time_rows |   rows_with_any_missing_value |   nonstandard_duration_rows |   irregular_gap_rows |   zero_volume_or_zero_trade_rows |
|:------------|-------:|:--------------------------------|:--------------------------------|:--------------------------------|:--------------------------------|---------------------------:|----------------------------:|------------------------------:|----------------------------:|---------------------:|---------------------------------:|
| H4          |  18791 | 2017-08-17T04:00:00.000000+0000 | 2026-03-17T12:00:00.000000+0000 | 2017-08-17T07:59:59.999000+0000 | 2026-03-17T15:59:59.999000+0000 |                          0 |                           1 |                             0 |                          19 |                    8 |                                1 |
| D1          |   3134 | 2017-08-17T00:00:00.000000+0000 | 2026-03-16T00:00:00.000000+0000 | 2017-08-17T23:59:59.999000+0000 | 2026-03-16T23:59:59.999000+0000 |                          0 |                           0 |                             0 |                           0 |                    0 |                                0 |

**Protocol V6 split actually used**

- Context / warmup only: `2017-08-17` to `2019-12-31`
- Discovery window: `2020-01-01` to `2022-12-31`
- Discovery walk-forward scored on six semiannual unseen folds:
  - `2020-01-01` to `2020-06-30`
  - `2020-07-01` to `2020-12-31`
  - `2021-01-01` to `2021-06-30`
  - `2021-07-01` to `2021-12-31`
  - `2022-01-01` to `2022-06-30`
  - `2022-07-01` to `2022-12-31`
- Candidate-selection holdout: `2023-01-01` to `2024-06-30`
- Reserve/internal: `2024-07-01` to dataset end
- Full-file audit touched the raw file to dataset end on both D1 and H4

### Exact anomaly handling in this round

- `19` H4 nonstandard-duration rows were **retained exactly as supplied** and logged explicitly.
- `8` H4 irregular gap events were **retained exactly as supplied**; no synthetic bars were inserted.
- `1` H4 zero-duration zero-activity row causing a duplicate `close_time` was **retained exactly as supplied** in the raw audit and logged explicitly.
- No missing-value repairs were needed.
- D1 was structurally clean.

### Exact preserved Stage 1 scan summary

**Actual number of scored Stage 1 configs**

| bucket    |   n_configs |
|:----------|------------:|
| native_d1 |         703 |
| native_h4 |         731 |
| xtf       |         785 |

**Actual Stage 1 config counts by bucket and family**

| bucket    | family                       |   n_configs |
|:----------|:-----------------------------|------------:|
| native_d1 | calendar_effect              |           9 |
| native_d1 | candle_structure             |         112 |
| native_d1 | directional_persistence      |         112 |
| native_d1 | drawdown_pullback            |          60 |
| native_d1 | location_within_range        |          60 |
| native_d1 | participation_flow           |         112 |
| native_d1 | trend_quality                |         144 |
| native_d1 | volatility_clustering        |          54 |
| native_d1 | volatility_level             |          40 |
| native_h4 | calendar_effect              |          19 |
| native_h4 | candle_structure             |         112 |
| native_h4 | directional_persistence      |         112 |
| native_h4 | drawdown_pullback            |          60 |
| native_h4 | location_within_range        |          60 |
| native_h4 | participation_flow           |         112 |
| native_h4 | trend_quality                |         144 |
| native_h4 | volatility_clustering        |          72 |
| native_h4 | volatility_level             |          40 |
| xtf       | calendar_effect              |           9 |
| xtf       | candle_structure             |         112 |
| xtf       | cross_timeframe_relationship |          82 |
| xtf       | directional_persistence      |         112 |
| xtf       | drawdown_pullback            |          60 |
| xtf       | location_within_range        |          60 |
| xtf       | participation_flow           |         112 |
| xtf       | trend_quality                |         144 |
| xtf       | volatility_clustering        |          54 |
| xtf       | volatility_level             |          40 |

**Exact preserved Stage 1 feature-library manifest — native D1**

| feature_name   | family                  | formula                                                                       | params                      | tails        | calibration_modes           | threshold_params                             |
|:---------------|:------------------------|:------------------------------------------------------------------------------|:----------------------------|:-------------|:----------------------------|:---------------------------------------------|
| atr_pct        | volatility_level        | rolling_mean(true_range, L) / close                                           | 10, 20, 40, 5               | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| body_frac      | candle_structure        | rolling_mean(abs(close - open) / (high - low), L)                             | 1, 10, 3, 5                 | lower, upper | fixed_level                 | 0.2, 0.4, 0.6                                |
| close_in_bar   | candle_structure        | rolling_mean((close - low) / (high - low), L)                                 | 1, 10, 3, 5                 | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| dir_body       | candle_structure        | rolling_mean((close - open) / (high - low), L)                                | 1, 10, 3, 5                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| drawdown       | drawdown_pullback       | close / rolling_max(close, L) - 1                                             | 10, 20, 3, 40, 5, 80        | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| flow_impulse   | participation_flow      | rolling_mean((2*taker_share_raw - 1) * (volume / rolling_mean(volume, L)), L) | 10, 20, 40, 5               | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| ma_gap         | trend_quality           | close / rolling_mean(close, L) - 1                                            | 10, 20, 3, 40, 5, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| range_loc      | location_within_range   | (close - rolling_low(L)) / (rolling_high(L) - rolling_low(L))                 | 10, 20, 3, 40, 5, 80        | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| ret            | directional_persistence | close / close.shift(L) - 1                                                    | 10, 20, 3, 40, 5, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| taker_share    | participation_flow      | rolling_mean(taker_buy_base_vol / volume, L)                                  | 10, 20, 40, 5               | lower, upper | fixed_level                 | 0.45, 0.5, 0.55, 0.6                         |
| trend_quality  | trend_quality           | (close / close.shift(L) - 1) / (rolling_std(log_close_ret, L) * sqrt(L))      | 10, 20, 3, 40, 5, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| up_frac        | directional_persistence | rolling_mean(close.diff() > 0, L)                                             | 10, 20, 3, 40, 5            | lower, upper | fixed_level                 | 0.4, 0.5, 0.6, 0.7                           |
| vol_cluster    | volatility_clustering   | rolling_std(log_close_ret, short) / rolling_std(log_close_ret, long)          | (10, 40), (20, 80), (5, 20) | lower, upper | fixed_level, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, 1.0, 1.2, 1.5     |
| volume_ratio   | participation_flow      | volume / rolling_mean(volume, L)                                              | 10, 20, 40, 5               | lower, upper | fixed_level                 | 0.8, 1.0, 1.2, 1.5                           |
| weekday        | calendar_effect         | bar weekday category                                                          | None                        | category     | category                    | (0, 1, 2, 3, 4), (5, 6), 0, 1, 2, 3, 4, 5, 6 |

**Exact preserved Stage 1 feature-library manifest — native H4**

| feature_name   | family                  | formula                                                                       | params                                 | tails        | calibration_modes           | threshold_params                                        |
|:---------------|:------------------------|:------------------------------------------------------------------------------|:---------------------------------------|:-------------|:----------------------------|:--------------------------------------------------------|
| atr_pct        | volatility_level        | rolling_mean(true_range, L) / close                                           | 12, 24, 48, 96                         | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                               |
| body_frac      | candle_structure        | rolling_mean(abs(close - open) / (high - low), L)                             | 1, 12, 3, 6                            | lower, upper | fixed_level                 | 0.2, 0.4, 0.6                                           |
| close_in_bar   | candle_structure        | rolling_mean((close - low) / (high - low), L)                                 | 1, 12, 3, 6                            | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                               |
| dir_body       | candle_structure        | rolling_mean((close - open) / (high - low), L)                                | 1, 12, 3, 6                            | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| drawdown       | drawdown_pullback       | close / rolling_max(close, L) - 1                                             | 12, 168, 24, 48, 6, 96                 | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                               |
| flow_impulse   | participation_flow      | rolling_mean((2*taker_share_raw - 1) * (volume / rolling_mean(volume, L)), L) | 12, 24, 48, 96                         | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| ma_gap         | trend_quality           | close / rolling_mean(close, L) - 1                                            | 12, 168, 24, 48, 6, 96                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| range_loc      | location_within_range   | (close - rolling_low(L)) / (rolling_high(L) - rolling_low(L))                 | 12, 168, 24, 48, 6, 96                 | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                               |
| ret            | directional_persistence | close / close.shift(L) - 1                                                    | 12, 168, 24, 48, 6, 96                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| slot_hour      | calendar_effect         | H4 bar open-hour slot category                                                | None                                   | category     | category                    | (0, 4), (16, 20), (20, 0), (8, 12), 0, 12, 16, 20, 4, 8 |
| taker_share    | participation_flow      | rolling_mean(taker_buy_base_vol / volume, L)                                  | 12, 24, 48, 96                         | lower, upper | fixed_level                 | 0.45, 0.5, 0.55, 0.6                                    |
| trend_quality  | trend_quality           | (close / close.shift(L) - 1) / (rolling_std(log_close_ret, L) * sqrt(L))      | 12, 168, 24, 48, 6, 96                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| up_frac        | directional_persistence | rolling_mean(close.diff() > 0, L)                                             | 12, 24, 48, 6, 96                      | lower, upper | fixed_level                 | 0.4, 0.5, 0.6, 0.7                                      |
| vol_cluster    | volatility_clustering   | rolling_std(log_close_ret, short) / rolling_std(log_close_ret, long)          | (12, 48), (24, 96), (48, 168), (6, 24) | lower, upper | fixed_level, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, 1.0, 1.2, 1.5                |
| volume_ratio   | participation_flow      | volume / rolling_mean(volume, L)                                              | 12, 24, 48, 96                         | lower, upper | fixed_level                 | 0.8, 1.0, 1.2, 1.5                                      |
| weekday        | calendar_effect         | bar weekday category                                                          | None                                   | category     | category                    | (0, 1, 2, 3, 4), (5, 6), 0, 1, 2, 3, 4, 5, 6            |

**Exact preserved Stage 1 feature-library manifest — cross-timeframe relations**

| feature_name   | family                       | formula                                                                               | params            | tails        | calibration_modes          | threshold_params                |
|:---------------|:-----------------------------|:--------------------------------------------------------------------------------------|:------------------|:-------------|:---------------------------|:--------------------------------|
| h4_in_d1_range | cross_timeframe_relationship | (H4 close - last_completed_D1_low) / (last_completed_D1_high - last_completed_D1_low) | None              | lower, upper | fixed_level                | 0.2, 0.35, 0.5, 0.65, 0.8       |
| h4_vs_d1_close | cross_timeframe_relationship | H4 close / last_completed_D1_close - 1                                                | None              | lower, upper | fixed_zero, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, None |
| h4_vs_d1_ma    | cross_timeframe_relationship | H4 close / last_completed_D1_MA(L) - 1                                                | 10, 20, 40, 5, 80 | lower, upper | fixed_zero, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, None |

**Exact preserved Stage 1 feature-library manifest — transported slower-state audit on H4**

| feature_name   | family                  | formula                                                                                                                                         | params                      | tails        | calibration_modes           | threshold_params                             |
|:---------------|:------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------|:-------------|:----------------------------|:---------------------------------------------|
| atr_pct        | volatility_level        | transport(last_completed_D1 rolling_mean(true_range, L) / close) onto H4 by backward as-of close_time                                           | 10, 20, 40, 5               | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| body_frac      | candle_structure        | transport(last_completed_D1 rolling_mean(abs(close - open) / (high - low), L)) onto H4 by backward as-of close_time                             | 1, 10, 3, 5                 | lower, upper | fixed_level                 | 0.2, 0.4, 0.6                                |
| close_in_bar   | candle_structure        | transport(last_completed_D1 rolling_mean((close - low) / (high - low), L)) onto H4 by backward as-of close_time                                 | 1, 10, 3, 5                 | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| dir_body       | candle_structure        | transport(last_completed_D1 rolling_mean((close - open) / (high - low), L)) onto H4 by backward as-of close_time                                | 1, 10, 3, 5                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| drawdown       | drawdown_pullback       | transport(last_completed_D1 close / rolling_max(close, L) - 1) onto H4 by backward as-of close_time                                             | 10, 20, 3, 40, 5, 80        | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| flow_impulse   | participation_flow      | transport(last_completed_D1 rolling_mean((2*taker_share_raw - 1) * (volume / rolling_mean(volume, L)), L)) onto H4 by backward as-of close_time | 10, 20, 40, 5               | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| ma_gap         | trend_quality           | transport(last_completed_D1 close / rolling_mean(close, L) - 1) onto H4 by backward as-of close_time                                            | 10, 20, 3, 40, 5, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| range_loc      | location_within_range   | transport(last_completed_D1 (close - rolling_low(L)) / (rolling_high(L) - rolling_low(L))) onto H4 by backward as-of close_time                 | 10, 20, 3, 40, 5, 80        | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| ret            | directional_persistence | transport(last_completed_D1 close / close.shift(L) - 1) onto H4 by backward as-of close_time                                                    | 10, 20, 3, 40, 5, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| taker_share    | participation_flow      | transport(last_completed_D1 rolling_mean(taker_buy_base_vol / volume, L)) onto H4 by backward as-of close_time                                  | 10, 20, 40, 5               | lower, upper | fixed_level                 | 0.45, 0.5, 0.55, 0.6                         |
| trend_quality  | trend_quality           | transport(last_completed_D1 (close / close.shift(L) - 1) / (rolling_std(log_close_ret, L) * sqrt(L))) onto H4 by backward as-of close_time      | 10, 20, 3, 40, 5, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| up_frac        | directional_persistence | transport(last_completed_D1 rolling_mean(close.diff() > 0, L)) onto H4 by backward as-of close_time                                             | 10, 20, 3, 40, 5            | lower, upper | fixed_level                 | 0.4, 0.5, 0.6, 0.7                           |
| vol_cluster    | volatility_clustering   | transport(last_completed_D1 rolling_std(log_close_ret, short) / rolling_std(log_close_ret, long)) onto H4 by backward as-of close_time          | (10, 40), (20, 80), (5, 20) | lower, upper | fixed_level, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, 1.0, 1.2, 1.5     |
| volume_ratio   | participation_flow      | transport(last_completed_D1 volume / rolling_mean(volume, L)) onto H4 by backward as-of close_time                                              | 10, 20, 40, 5               | lower, upper | fixed_level                 | 0.8, 1.0, 1.2, 1.5                           |
| weekday        | calendar_effect         | transport(last_completed_D1 bar weekday category) onto H4 by backward as-of close_time                                                          | None                        | category     | category                    | (0, 1, 2, 3, 4), (5, 6), 0, 1, 2, 3, 4, 5, 6 |

### Exact top representative leaders by family and bucket

| bucket    | timeframe   | feature_name   | param    | family                       | tail     | calibration_mode   | threshold_param   |   sharpe_daily |     cagr |   max_drawdown |   trade_count |   positive_fold_share |
|:----------|:------------|:---------------|:---------|:-----------------------------|:---------|:-------------------|:------------------|---------------:|---------:|---------------:|--------------:|----------------------:|
| native_d1 | D1          | weekday        | nan      | calendar_effect              | category | category           | 1                 |       0.535545 | 0.121986 |      -0.330696 |           157 |              0.666667 |
| native_d1 | D1          | close_in_bar   | 10       | candle_structure             | upper    | fixed_level        | 0.65              |       0.979913 | 0.234821 |      -0.295622 |            38 |              0.5      |
| native_d1 | D1          | ret            | 40       | directional_persistence      | upper    | fixed_zero         | nan               |       1.55674  | 0.907849 |      -0.483106 |            29 |              0.666667 |
| native_d1 | D1          | drawdown       | 40       | drawdown_pullback            | upper    | train_quantile     | 0.65              |       1.52914  | 0.722316 |      -0.408268 |            40 |              0.666667 |
| native_d1 | D1          | range_loc      | 40       | location_within_range        | upper    | fixed_level        | 0.65              |       1.54463  | 0.807609 |      -0.456816 |            26 |              0.666667 |
| native_d1 | D1          | flow_impulse   | 10       | participation_flow           | lower    | train_quantile     | 0.2               |       1.17907  | 0.467805 |      -0.359407 |            34 |              0.5      |
| native_d1 | D1          | trend_quality  | 40       | trend_quality                | upper    | fixed_zero         | nan               |       1.55674  | 0.907849 |      -0.483106 |            29 |              0.666667 |
| native_d1 | D1          | vol_cluster    | (5, 20)  | volatility_clustering        | lower    | train_quantile     | 0.65              |       1.33419  | 0.812205 |      -0.528787 |           110 |              0.833333 |
| native_d1 | D1          | atr_pct        | 10       | volatility_level             | upper    | train_quantile     | 0.5               |       1.29174  | 0.723025 |      -0.463599 |            43 |              0.833333 |
| native_h4 | H4          | weekday        | nan      | calendar_effect              | category | category           | (0, 1, 2, 3, 4)   |       0.759672 | 0.318626 |      -0.71039  |           157 |              0.666667 |
| native_h4 | H4          | close_in_bar   | 6        | candle_structure             | lower    | fixed_level        | 0.35              |       0.967105 | 0.151971 |      -0.149884 |           141 |              0.5      |
| native_h4 | H4          | ret            | 168      | directional_persistence      | upper    | train_quantile     | 0.5               |       1.63312  | 0.950578 |      -0.433209 |            94 |              0.666667 |
| native_h4 | H4          | drawdown       | 168      | drawdown_pullback            | upper    | train_quantile     | 0.65              |       1.14647  | 0.460445 |      -0.429246 |           126 |              0.666667 |
| native_h4 | H4          | range_loc      | 168      | location_within_range        | upper    | fixed_level        | 0.5               |       1.255    | 0.633146 |      -0.426245 |            87 |              0.5      |
| native_h4 | H4          | flow_impulse   | 96       | participation_flow           | upper    | train_quantile     | 0.2               |       0.798626 | 0.342934 |      -0.630035 |            26 |              0.666667 |
| native_h4 | H4          | trend_quality  | 168      | trend_quality                | upper    | fixed_zero         | nan               |       1.63222  | 0.984197 |      -0.435532 |            82 |              0.666667 |
| native_h4 | H4          | vol_cluster    | (24, 96) | volatility_clustering        | lower    | train_quantile     | 0.8               |       0.961401 | 0.504476 |      -0.762926 |            86 |              0.666667 |
| native_h4 | H4          | atr_pct        | 48       | volatility_level             | upper    | train_quantile     | 0.65              |       1.00489  | 0.458305 |      -0.457836 |            41 |              0.666667 |
| xtf       | H4          | weekday        | nan      | calendar_effect              | category | category           | 1                 |       0.535108 | 0.12177  |      -0.330558 |           157 |              0.666667 |
| xtf       | H4          | close_in_bar   | 10       | candle_structure             | upper    | fixed_level        | 0.65              |       0.979911 | 0.234775 |      -0.295646 |            38 |              0.5      |
| xtf       | H4          | h4_vs_d1_ma    | 40       | cross_timeframe_relationship | upper    | train_quantile     | 0.5               |       1.6133   | 0.920928 |      -0.349089 |            56 |              0.666667 |
| xtf       | H4          | ret            | 40       | directional_persistence      | upper    | fixed_zero         | nan               |       1.55658  | 0.907682 |      -0.483202 |            29 |              0.666667 |
| xtf       | H4          | drawdown       | 40       | drawdown_pullback            | upper    | train_quantile     | 0.65              |       1.52887  | 0.722068 |      -0.408298 |            40 |              0.666667 |
| xtf       | H4          | range_loc      | 40       | location_within_range        | upper    | fixed_level        | 0.65              |       1.54449  | 0.807469 |      -0.45686  |            26 |              0.666667 |
| xtf       | H4          | flow_impulse   | 10       | participation_flow           | lower    | train_quantile     | 0.2               |       1.17496  | 0.465449 |      -0.359465 |            34 |              0.5      |
| xtf       | H4          | trend_quality  | 40       | trend_quality                | upper    | fixed_zero         | nan               |       1.55658  | 0.907682 |      -0.483202 |            29 |              0.666667 |
| xtf       | H4          | vol_cluster    | (5, 20)  | volatility_clustering        | lower    | fixed_level        | 1.0               |       1.31132  | 0.782575 |      -0.516259 |           108 |              0.833333 |
| xtf       | H4          | atr_pct        | 10       | volatility_level             | upper    | train_quantile     | 0.5               |       1.29146  | 0.722726 |      -0.463599 |            43 |              0.833333 |

Interpretation preserved by the report:

- native slower D1 state systems and native H4 trend-state systems both produced serious leaders,
- transported slower-state clones were strong but were treated as redundancy evidence rather than independent faster information,
- the final live shortlist preserved both simple and layered families before reserve.

### Exact shortlisted candidates and frozen comparison set

**Shortlist ledger**

| candidate                        | cluster                       | stage             | status   | type                         | spec_summary                                              | reason                                                                                                                                            |
|:---------------------------------|:------------------------------|:------------------|:---------|:-----------------------------|:----------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------|
| S1_D1_RET40_Z0                   | simple_slow_trend             | shortlist         | kept     | single_native                | Native D1 40-day return > 0                               | Strong simple slower trend representative; broad local plateau around 32-48 days; credible simplest frontier.                                     |
| S2_D1_VCL5_20_LT1.0              | simple_slow_vol_regime        | shortlist         | kept     | single_native                | Native D1 short/long volatility ratio (5,20) < 1.0        | Strong slower low-volatility regime representative; materially different failure mode versus pure trend.                                          |
| S3_H4_RET168_Z0                  | simple_fast_trend             | shortlist         | kept     | single_native                | Native H4 168-bar return > 0                              | Strong simple native H4 trend state with broad plateau and better pre-reserve risk-adjusted performance than nearby simple rivals.                |
| S4_H4_UPFR48_LT0.4               | simple_fast_timing_sparse     | shortlist         | kept     | single_native                | Native H4 up-bar fraction over 48 bars < 0.4              | Genuinely orthogonal sparse timing representative; very low correlation to trend cluster.                                                         |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 | layered_vol_gate_fast_trend   | shortlist         | kept     | layered_and_h4               | D1 low-volatility gate AND H4 trend state                 | Best two-layer volatility-gated trend family; broad plateau in nearby cells.                                                                      |
| L2_D1RET40_Z0_AND_H4RET168_Z0    | layered_slow_trend_fast_trend | shortlist         | kept     | layered_and_h4               | D1 trend gate AND H4 trend state                          | Best two-layer trend-plus-trend family; strong headline pre-reserve metrics but must beat simpler frontier on paired tests.                       |
| XTF_TRANS_RET40_Z0               | transported_slow_clone        | shortlist         | dropped  | cross_timeframe_transport    | D1 40-day return transported to H4                        | Perfectly redundant with native D1_RET40 representative (daily return correlation 1.00); transport does not add independent information.          |
| XTF_H4_D1MA40_U_q50              | cross_timeframe_relation      | shortlist         | dropped  | cross_timeframe_relationship | H4 close vs D1 MA40 relation, thresholded by train median | Strong discovery metrics but ~0.91 correlation with H4_RET168 trend cluster; not sufficiently orthogonal after paired comparison.                 |
| D1_RANGE40_U_065                 | slow_trend_location           | shortlist         | dropped  | single_native                | D1 range location over 40 bars > 0.65                     | Serious slower trend/location candidate but dominated by simpler D1_RET40 on explanatory clarity and similar unseen behavior.                     |
| D1_DRAWDOWN40_U_q65              | slow_drawdown_pullback        | shortlist         | dropped  | single_native                | D1 drawdown state over 40 bars in upper train quantile    | Useful evidence that pullback state matters, but not sufficiently distinct from slower trend cluster to keep as separate frontier representative. |
| D1_FLOW10_L_q20                  | participation_flow            | shortlist         | dropped  | single_native                | D1 flow impulse over 10 bars in lower train quantile      | Meaningfully lower correlation to trend than many features, but weaker and less stable than retained short-list representatives.                  |
| H4_CLOSE6_L_035                  | fast_candle_filter            | entry_filter_test | dropped  | entry_only_confirmation      | H4 close-in-bar over 6 bars < 0.35                        | Entry-only filter improved selectivity in a few cells but generally reduced trade count too far and did not justify a third layer.                |
| H4_BODY6_U_06                    | fast_candle_filter            | entry_filter_test | dropped  | entry_only_confirmation      | H4 body fraction over 6 bars > 0.6                        | No consistent incremental edge once layered on top of already-strong two-layer cores.                                                             |
| H4_FLOW24_Z0                     | fast_flow_filter              | entry_filter_test | dropped  | entry_only_confirmation      | H4 flow impulse over 24 bars > 0                          | Third-layer confirmation reduced robustness and added complexity without a clear paired advantage.                                                |

**Frozen comparison set ledger**

| candidate                        | cluster                       | stage   | status                | type           | spec_summary                                                                                                                                                                                                                                                                                              | reason                                                                                                                                  |
|:---------------------------------|:------------------------------|:--------|:----------------------|:---------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------|
| S1_D1_RET40_Z0                   | simple_slow_trend             | freeze  | frozen_comparison_set | single_native  | {"type": "single_native", "timeframe": "D1", "feature_name": "ret", "param": 40, "tail": "upper", "mode": "fixed_zero", "threshold": null, "family_cluster": "simple_slow_trend"}                                                                                                                         | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| S2_D1_VCL5_20_LT1.0              | simple_slow_vol_regime        | freeze  | frozen_comparison_set | single_native  | {"type": "single_native", "timeframe": "D1", "feature_name": "vol_cluster", "param": [5, 20], "tail": "lower", "mode": "fixed_level", "threshold": 1.0, "family_cluster": "simple_slow_vol_regime"}                                                                                                       | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| S3_H4_RET168_Z0                  | simple_fast_trend             | freeze  | frozen_comparison_set | single_native  | {"type": "single_native", "timeframe": "H4", "feature_name": "ret", "param": 168, "tail": "upper", "mode": "fixed_zero", "threshold": null, "family_cluster": "simple_fast_trend"}                                                                                                                        | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| S4_H4_UPFR48_LT0.4               | simple_fast_timing_sparse     | freeze  | frozen_comparison_set | single_native  | {"type": "single_native", "timeframe": "H4", "feature_name": "up_frac", "param": 48, "tail": "lower", "mode": "fixed_level", "threshold": 0.4, "family_cluster": "simple_fast_timing_sparse"}                                                                                                             | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 | layered_vol_gate_fast_trend   | freeze  | frozen_comparison_set | layered_and_h4 | {"type": "layered_and_h4", "slow": {"feature_name": "vol_cluster", "param": [5, 20], "tail": "lower", "mode": "fixed_level", "threshold": 1.0}, "fast": {"feature_name": "ret", "param": 168, "tail": "upper", "mode": "fixed_zero", "threshold": null}, "family_cluster": "layered_vol_gate_fast_trend"} | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| L2_D1RET40_Z0_AND_H4RET168_Z0    | layered_slow_trend_fast_trend | freeze  | frozen_comparison_set | layered_and_h4 | {"type": "layered_and_h4", "slow": {"feature_name": "ret", "param": 40, "tail": "upper", "mode": "fixed_zero", "threshold": null}, "fast": {"feature_name": "ret", "param": 168, "tail": "upper", "mode": "fixed_zero", "threshold": null}, "family_cluster": "layered_slow_trend_fast_trend"}            | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |

### Exact paired-bootstrap configuration and pre-reserve selection judgment

**Paired-bootstrap configuration**
- method: moving-block bootstrap on daily returns
- block sizes: `5`, `10`, `20` trading days
- resamples: `2000`
- paired paths: yes
- selection objective: determine whether more complex internal rivals earned enough incremental advantage over simpler nearby frontiers

**Selection judgment preserved by the report**

| comparison                                          | stage                 |   delta_pre_res_sharpe |   delta_pre_res_cagr |   paired_p_sharpe_gt0_range |   paired_p_cagr_gt0_range | verdict                                                                                                                                                          |
|:----------------------------------------------------|:----------------------|-----------------------:|---------------------:|----------------------------:|--------------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L2_D1RET40_Z0_AND_H4RET168_Z0 vs S3_H4_RET168_Z0    | pre_reserve_selection |               0.084515 |             0.001689 |                         nan |                       nan | No meaningful paired advantage for more complex L2; protocol awards decision to simpler S3.                                                                      |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 vs S3_H4_RET168_Z0 | pre_reserve_selection |              -0.074981 |            -0.276098 |                         nan |                       nan | Inferior to S3 on paired bootstrap and pre-reserve growth; dropped as leader.                                                                                    |
| S3_H4_RET168_Z0 vs S1_D1_RET40_Z0                   | pre_reserve_selection |               0.044975 |             0.044149 |                         nan |                       nan | Not cleanly separated by paired bootstrap; S3 selected on slightly stronger pre-reserve Sharpe/CAGR, lower drawdown, broader H4 plateau, and higher trade count. |

This is the exact preserved reason `L2_D1RET40_Z0_AND_H4RET168_Z0` was not selected:

- it had slightly stronger headline pre-reserve metrics than `S3_H4_RET168_Z0`,
- but it did **not** show a meaningful paired-bootstrap advantage over the simpler system,
- therefore the V6 protocol awarded leadership to the simpler `S3_H4_RET168_Z0`.

### Exact ablation and plateau evidence preserved around the final family

**Ablation table**

| layered_candidate                | comparator          | comparison_type   |   delta_pre_res_sharpe |   delta_pre_res_cagr | verdict                                                                                                               | paired_p_sharpe_gt0_range   | paired_p_cagr_gt0_range   |
|:---------------------------------|:--------------------|:------------------|-----------------------:|---------------------:|:----------------------------------------------------------------------------------------------------------------------|:----------------------------|:--------------------------|
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 | S2_D1_VCL5_20_LT1.0 | ablate_fast_layer |               0.438587 |             0.111995 | Fast trend layer adds substantial edge to slow low-vol regime core.                                                   | nan                         | nan                       |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 | S3_H4_RET168_Z0     | ablate_slow_layer |              -0.074981 |            -0.276098 | Slow low-vol gate does not improve enough over simple H4 trend frontier to justify leadership.                        | 0.394-0.429                 | 0.126-0.174               |
| L2_D1RET40_Z0_AND_H4RET168_Z0    | S1_D1_RET40_Z0      | ablate_fast_layer |               0.084515 |             0.045838 | Fast layer improves headline metrics over slow trend alone.                                                           | nan                         | nan                       |
| L2_D1RET40_Z0_AND_H4RET168_Z0    | S3_H4_RET168_Z0     | ablate_slow_layer |               0.084515 |             0.001689 | Slow trend gate does not earn enough incremental advantage over simple H4 trend frontier to justify extra complexity. | 0.654-0.692                 | 0.469-0.506               |

**Plateau table for the H4 return family**

| family   |   lookback | mode           |    thr |   sharpe_daily |     cagr |   max_drawdown |   trade_count |   exposure |   net_return |   positive_fold_share |   min_fold_cagr |
|:---------|-----------:|:---------------|-------:|---------------:|---------:|---------------:|--------------:|-----------:|-------------:|----------------------:|----------------:|
| h4_ret   |        168 | train_quantile |   0.5  |       1.63312  | 0.950578 |      -0.433209 |            94 |   0.493232 |      6.42486 |              0.666667 |       -0.530549 |
| h4_ret   |        168 | fixed_zero     | nan    |       1.63222  | 0.984197 |      -0.435532 |            82 |   0.534144 |      6.81553 |              0.666667 |       -0.502287 |
| h4_ret   |        168 | train_quantile |   0.65 |       1.57589  | 0.754616 |      -0.287505 |            64 |   0.347376 |      4.40398 |              0.666667 |       -0.100136 |
| h4_ret   |        202 | fixed_zero     | nan    |       1.54629  | 0.895838 |      -0.397158 |            72 |   0.530494 |      5.81701 |              0.666667 |       -0.338842 |
| h4_ret   |        202 | train_quantile |   0.5  |       1.50094  | 0.824213 |      -0.505825 |            80 |   0.491863 |      5.07303 |              0.666667 |       -0.438695 |
| h4_ret   |        202 | train_quantile |   0.65 |       1.47799  | 0.707986 |      -0.274334 |            73 |   0.358631 |      3.98439 |              0.666667 |       -0.355008 |
| h4_ret   |        202 | train_quantile |   0.35 |       1.22046  | 0.656354 |      -0.508703 |            77 |   0.632091 |      3.54579 |              0.666667 |       -0.459336 |
| h4_ret   |        168 | train_quantile |   0.35 |       1.17949  | 0.616889 |      -0.494759 |            91 |   0.644715 |      3.22847 |              0.666667 |       -0.427859 |
| h4_ret   |        134 | fixed_zero     | nan    |       1.08249  | 0.508822 |      -0.544799 |           126 |   0.546616 |      2.43587 |              0.666667 |       -0.518592 |
| h4_ret   |        134 | train_quantile |   0.5  |       1.05134  | 0.469581 |      -0.562531 |           127 |   0.504183 |      2.17464 |              0.666667 |       -0.527357 |
| h4_ret   |        134 | train_quantile |   0.65 |       0.990412 | 0.371488 |      -0.453184 |            93 |   0.32654  |      1.5803  |              0.5      |       -0.442445 |
| h4_ret   |        134 | train_quantile |   0.35 |       0.917392 | 0.414496 |      -0.668164 |            93 |   0.664943 |      1.83079 |              0.5      |       -0.573491 |

Interpretation preserved by the report:

- the H4 trend family lived on a real local plateau rather than a single isolated spike,
- `S3_H4_RET168_Z0` sat in a defensible simple frontier,
- the stronger-looking two-layer rival was not allowed to win without clearer paired evidence.

### Exact frozen winner and calibration details

**Frozen winner**
- `S3_H4_RET168_Z0`

**Exact preserved system-level details**
- Market: BTC/USDT spot
- Direction: long only
- Base timeframe: H4
- Feature: `h4_ret_168`
- Feature family: directional persistence
- Lookback: `168`
- Formula: `close_t / close_(t-168) - 1`
- Threshold mode: `fixed_zero`
- Threshold: `0.0`
- Signal timing: compute on H4 close
- Fill timing: next H4 open
- Position sizing: binary notional `1.0` long / `0.0` flat
- Regime gate: none beyond the feature threshold itself
- Separate entry confirmation layer: none
- Separate exit layer: none
- Cost model: `10` bps per side, `20` bps round-trip base, `50` bps stress test

### Exact preserved validation metrics for the frozen comparison set

| candidate                        |   disc_sharpe_daily |   disc_cagr |   disc_max_drawdown |   disc_trade_count |   hold_sharpe_daily |   hold_cagr |   hold_max_drawdown |   hold_trade_count |   res_sharpe_daily |   res_cagr |   res_max_drawdown |   res_trade_count |   pre_res_sharpe |   pre_res_cagr |   pre_res_mdd |
|:---------------------------------|--------------------:|------------:|--------------------:|-------------------:|--------------------:|------------:|--------------------:|-------------------:|-------------------:|-----------:|-------------------:|------------------:|-----------------:|---------------:|--------------:|
| S1_D1_RET40_Z0                   |             1.55674 |    0.907849 |           -0.483106 |                 29 |            1.94147  |    1.03038  |           -0.283581 |                 12 |           0.525713 |   0.118734 |          -0.240051 |                25 |          1.66343 |       0.947797 |     -0.483106 |
| S2_D1_VCL5_20_LT1.0              |             1.31154 |    0.782865 |           -0.516179 |                108 |            0.922704 |    0.297448 |           -0.31328  |                 43 |           0.91281  |   0.272303 |          -0.211357 |                58 |          1.19483 |       0.603854 |     -0.516179 |
| S3_H4_RET168_Z0                  |             1.63222 |    0.984197 |           -0.435532 |                 82 |            1.91476  |    1.00756  |           -0.224064 |                 52 |          -0.041922 |  -0.057544 |          -0.346367 |                76 |          1.7084  |       0.991947 |     -0.435532 |
| S4_H4_UPFR48_LT0.4               |             1.58595 |    0.277391 |           -0.12925  |                 62 |            0.780877 |    0.051932 |           -0.058333 |                 31 |           0.389713 |   0.049423 |          -0.168957 |                35 |          1.36921 |       0.197419 |     -0.12925  |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 |             1.85543 |    0.969024 |           -0.230279 |                113 |            1.07427  |    0.302316 |           -0.271431 |                 60 |          -0.156174 |  -0.062753 |          -0.220798 |                82 |          1.63342 |       0.715849 |     -0.271431 |
| L2_D1RET40_Z0_AND_H4RET168_Z0    |             1.78391 |    1.04565  |           -0.340576 |                 49 |            1.82972  |    0.893368 |           -0.239014 |                 39 |           0.042514 |  -0.025554 |          -0.290908 |                57 |          1.79292 |       0.993635 |     -0.340576 |

Key preserved winner metrics:

- Discovery `2020–2022`: Sharpe `1.632222`, CAGR `98.4197%`, max drawdown `-43.5532%`, trades `82`
- Holdout `2023-01-01` to `2024-06-30`: Sharpe `1.914757`, CAGR `100.7564%`, max drawdown `-22.4064%`, trades `52`
- Pre-reserve combined: Sharpe `1.708401`, CAGR `99.1947%`, max drawdown `-43.5532%`
- Reserve/internal `2024-07-01+`: Sharpe `-0.041922`, CAGR `-5.7544%`, max drawdown `-34.6367%`, trades `76`

### Exact reserve/internal ranking after freeze

| candidate                        |   res_days |   res_sharpe_daily |   res_cagr |   res_max_drawdown |   res_trade_count |   res_exposure |   res_net_return |   res_win_rate |   res_mean_trade_return |   res_median_trade_return |
|:---------------------------------|-----------:|-------------------:|-----------:|-------------------:|------------------:|---------------:|-----------------:|---------------:|------------------------:|--------------------------:|
| S1_D1_RET40_Z0                   |        624 |           0.525713 |   0.118734 |          -0.240051 |                25 |       0.514423 |         0.211284 |       0.36     |                0.013001 |                 -0.014284 |
| S2_D1_VCL5_20_LT1.0              |        624 |           0.91281  |   0.272303 |          -0.211357 |                58 |       0.596154 |         0.508983 |       0.578947 |                0.007794 |                  0.006991 |
| S3_H4_RET168_Z0                  |        625 |          -0.041922 |  -0.057544 |          -0.346367 |                76 |       0.519477 |        -0.09644  |       0.306667 |               -7.5e-05  |                 -0.006364 |
| S4_H4_UPFR48_LT0.4               |        625 |           0.389713 |   0.049423 |          -0.168957 |                35 |       0.046158 |         0.08605  |       0.628571 |                0.002693 |                  0.005313 |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 |        625 |          -0.156174 |  -0.062753 |          -0.220798 |                82 |       0.324973 |        -0.10497  |       0.407407 |               -0.001463 |                 -0.004425 |
| L2_D1RET40_Z0_AND_H4RET168_Z0    |        625 |           0.042514 |  -0.025554 |          -0.290908 |                57 |       0.409018 |        -0.043329 |       0.25     |                0.001914 |                 -0.007713 |

Recorded interpretation:

- the frozen winner `S3_H4_RET168_Z0` weakened materially in reserve/internal;
- `S1_D1_RET40_Z0` outperformed it in reserve/internal despite losing pre-reserve;
- `S2_D1_VCL5_20_LT1.0` was the best reserve/internal performer in this frozen set, but it was not the pre-reserve winner and could not be promoted post hoc under V6;
- reserve/internal therefore reduced confidence in the frozen winner but did **not** permit redesign.

### Exact cost sensitivity preserved for the frozen winner

| candidate       |   disc_cagr |   hold_cagr |   disc_cagr_50bps |   disc_sharpe_50bps |   hold_cagr_50bps |   hold_sharpe_50bps |   disc_delta_50bps |   hold_delta_50bps |
|:----------------|------------:|------------:|------------------:|--------------------:|------------------:|--------------------:|-------------------:|-------------------:|
| S3_H4_RET168_Z0 |    0.984197 |     1.00756 |          0.827791 |             1.46228 |           0.80865 |             1.64959 |          -0.156406 |          -0.198914 |

### Exact regime decomposition preserved for the frozen winner

**Pre-reserve**

| regime   |   days |   active_days |   exposure_mean |   ret_sharpe |   ret_cagr |   ret_mdd |   active_mean_daily_ret |   active_ci05 |   active_ci95 | signal_label   |
|:---------|-------:|--------------:|----------------:|-------------:|-----------:|----------:|------------------------:|--------------:|--------------:|:---------------|
| bear     |    481 |           153 |        0.265419 |    -0.837877 |  -0.092704 | -0.470869 |               -0.002031 |     -0.00547  |      0.00133  | noise-only     |
| bull     |    829 |           712 |        0.808203 |     2.64537  |   1.02564  | -0.251923 |                0.004932 |      0.002986 |      0.006887 | effective      |
| neutral  |    333 |           141 |        0.382883 |     1.34943  |   0.079714 | -0.198789 |                0.00274  |     -0.0008   |      0.006265 | noise-only     |

**Full internal**

| regime   |   days |   active_days |   exposure_mean |   ret_sharpe |   ret_cagr |   ret_mdd |   active_mean_daily_ret |   active_ci05 |   active_ci95 | signal_label   |
|:---------|-------:|--------------:|----------------:|-------------:|-----------:|----------:|------------------------:|--------------:|--------------:|:---------------|
| bear     |    689 |           221 |        0.259797 |    -1.38728  |  -0.113925 | -0.657307 |               -0.003087 |     -0.005806 |     -0.000499 | sign-reversed  |
| bull     |   1100 |           937 |        0.799848 |     2.53346  |   0.899624 | -0.251923 |                0.004412 |      0.002813 |      0.00606  | effective      |
| neutral  |    478 |           215 |        0.397838 |     0.323891 |   0.011611 | -0.369842 |                0.000597 |     -0.001868 |      0.003205 | noise-only     |

Important preserved interpretation:

- pre-reserve, the frozen winner was effective in bull conditions and mostly noise outside them,
- on full internal data, the bear regime became sign-reversed,
- this was a material warning sign, but under V6 it could not be used to redesign after freeze.

### Exact evidence label recorded for this round

- Evidence label: `INTERNAL ROBUST CANDIDATE`
- The label was **not** `CLEAN OOS CONFIRMED`, because the reserve window was internal only and the current file was already contaminated across sessions.
- This round therefore contributes a fully recoverable frozen system and a procedurally blind internal re-derivation, but **not** a clean cross-session OOS proof.

### Bottom line for contamination purposes

This round contaminated the following additional knowledge beyond V2:

- the V6 split `2020-01-01` to dataset end at discovery / holdout / reserve granularity,
- the full Stage 1 library manifest for this session,
- the exact shortlist and frozen comparison set,
- the exact frozen winner `S3_H4_RET168_Z0`,
- the paired-bootstrap selection judgment versus nearby internal rivals,
- the plateau table around the winning H4 trend family,
- the reserve/internal contradiction against the frozen winner.


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

- **Split D** (Protocol V5 session)
  - warmup/context: 2017-08-17 to 2018-12-31
  - discovery: 2019-01-01 to 2022-12-31
  - selection holdout: 2023-01-01 to 2024-12-31
  - reserve/internal: 2025-01-01 to dataset end
  - notes: full-file audit to dataset end; strict independence not achieved because selection tables were reproduced from an earlier internal run

- **Split E** (Protocol V6 session)
  - warmup/context: 2017-08-17 to 2019-12-31
  - discovery: 2020-01-01 to 2022-12-31
  - discovery walk-forward: six semiannual unseen test folds from 2020-H1 through 2022-H2
  - selection holdout: 2023-01-01 to 2024-06-30
  - reserve/internal: 2024-07-01 to dataset end
  - notes: procedurally blind to prior artifacts before freeze, but still same-file internal evidence only

## 5) Suggested alternative split options for a new session

### Option 1 — the only strict cross-session clean-OOS option
- Append genuinely new data **after** the current file end.
- Use the current file for discovery and internal selection.
- Reserve only the appended future period as final true OOS.
- Status: **strictly valid**

### Option 2 — final same-file convergence-audit split V7
- warmup/context: 2017-08-17 to 2019-12-31
- discovery: 2020-01-01 to 2023-06-30
- discovery walk-forward: quarterly unseen folds from 2020-Q1 through 2023-Q2
- selection holdout: 2023-07-01 to 2024-09-30
- reserve/internal: 2024-10-01 to dataset end
- Status: **internal only**, not globally clean

### Option 3 — alternate internal-only same-file audit split
- warmup/context: 2017-08-17 to 2020-06-30
- discovery: 2020-07-01 to 2023-09-30
- discovery walk-forward: quarterly unseen folds from 2020-Q3 through 2023-Q3
- selection holdout: 2023-10-01 to 2024-12-31
- reserve/internal: 2025-01-01 to dataset end
- Status: **internal only**, not globally clean

## 6) Practical conclusion for a new session

A new session can still be useful for independent re-derivation and convergence testing, but it should proceed under these truths:

- prior specific features, lookbacks, thresholds, calibration modes, and winners listed above are already contaminated;
- the current file contains **no** globally untouched within-file OOS range;
- after three completed sessions with different frozen outcomes, at most **one more same-file session** is scientifically worthwhile, and it should be framed as a **final same-file convergence audit** rather than as further optimization;
- any same-file session beyond that point would mainly add prompt-level search and governance churn, not new clean evidence;
- the scientifically correct path to a truly clean OOS proof is to freeze a candidate and evaluate it on **new data not present in the current file**.
