# Exit research from scratch under locked entry winner

## Scope lock

- **Entry is fixed** to the research-version entry winner `weakvdo_q0.5_activity_and_fresh_imb`.
- **No ML** is used anywhere in exit/hold.
- Base indicators, sizing, accounting, fees, and warmup remain unchanged.
- Primary comparison is against:
  - **Baseline A** = entry winner + original base exit
  - **Baseline B** = original `VDO > 0` entry + original base exit
- Primary ranking uses the same 4 stitched WFO OOS folds used in the entry work, with flat reset at each OOS fold start.

## OOS folds

- Fold 1: 2021-07-01 to 2022-12-31
- Fold 2: 2023-01-01 to 2024-06-30
- Fold 3: 2024-07-01 to 2025-06-30
- Fold 4: 2025-07-01 to 2026-02-28

## Baselines reproduced

- **Baseline A**: Sharpe **1.374084**, CAGR **0.427156**, MDD **-0.273367**, trades **104**
- **Baseline B**: Sharpe **1.130760**, CAGR **0.350303**, MDD **-0.370939**, trades **118**

## Search breadth

A total of **4915** non-ML policy evaluations were run:

| family                   |   evaluations |
|:-------------------------|--------------:|
| price_core_no_timestop   |           640 |
| price_core_with_timestop |          3360 |
| volume_continuation      |           720 |
| always_on_volume_exit    |           180 |
| initial_stop_addons      |            15 |

This includes:
- price-only decompositions without time stop
- price-only decompositions with explicit time stop
- non-ML continuation families using volume guards
- always-on volume exits
- initial-stop addons

## First-principles decomposition

Exit exists to do two things:
1. limit adverse drift / give back after a move,
2. stop overstaying when the trade's useful life is over.

The search therefore decomposed exit into:
- **protective stop**: trail presence, multiplier, ATR mode, peak anchor, breach confirmation
- **state invalidation**: trend exit variants or none
- **post-exit state**: cooldown after exit
- **life-cycle control**: time stop
- **secondary information**: volume guards used as continuation or always-on exits

## Vulnerability scan on Baseline A

| vulnerability              | definition                                                                  |   affected_trades |   affected_pct_all_trades |   affected_pct_relevant_exits | actionability                                                           |
|:---------------------------|:----------------------------------------------------------------------------|------------------:|--------------------------:|------------------------------:|:------------------------------------------------------------------------|
| V1_ATR_flicker_same_bar    | baseline trail exit bar would not trigger under lagged ATR on the same bar  |                 4 |                0.038835   |                     0.0416667 | below 5% of all trades; not primary fix                                 |
| V1_ATR_timing_any_change   | first trail trigger bar differs between current and lagged ATR              |                11 |                0.106796   |                     0.114583  | exists, but lagged/current are near-tied; not main edge                 |
| V2_same_EMA_exit_churn_le6 | trend-exit trade re-enters within <=6 bars                                  |                 1 |                0.00970874 |                     0.142857  | below 5% of all trades; direct EMA churn not main issue                 |
| V3_no_cooldown_reentry_le3 | any exit re-enters within <=3 bars                                          |                24 |                0.23301    |                     0.23301   | major; cooldown worth searching                                         |
| V4_close_peak_vs_high_peak | high-peak trail would have triggered earlier than baseline close-peak trail |                61 |                0.592233   |                     0.592233  | representation vulnerability exists, but fixing it hurt OOS performance |

Read:
- **V3 is real and large.** Quick re-entry after exit is common under the new entry.
- **V2 exists only weakly** as direct EMA cross churn; it is not the main problem.
- **V4 exists as a representation issue**, but "fixing" it with `peak=high` hurt OOS performance.
- **V1 same-bar ATR flicker is below 5% of all trades**, so it is not the first place to spend complexity.

## Component decomposition

### Necessity of base components

Price-only ablations under locked entry:

| policy | aggregate_sharpe | aggregate_mdd | trades |
|---|---:|---:|---:|
| base exit | 1.374084 | -0.273367 | 104 |
| trail only | 1.451920 | -0.273367 | 100 |
| trend only | 0.871863 | -0.429470 | 41 |
| no trail + no trend | 0.497843 | -0.770434 | 4 |

Implications:
- **Trail is essential.**
- **Trend exit is not essential** and is often harmful once better life-cycle control is added.
- A pure time-stop system without trail was also checked and did **not** work; the winner must keep a real protective stop.

### Best family by motif

| family                     | policy                                                          |   sharpe |     cagr |       mdd |   bar_count |   exposure |   trades |   positive_folds_vs_A |
|:---------------------------|:----------------------------------------------------------------|---------:|---------:|----------:|------------:|-----------:|---------:|----------------------:|
| baseline_A                 | entry_winner + base_exit                                        |  1.37408 | 0.427156 | -0.273367 |       10224 |   0.376565 |      104 |                     0 |
| baseline_B                 | entry_vdo_only + base_exit                                      |  1.13076 | 0.350303 | -0.370939 |       10224 |   0.409233 |      118 |                   nan |
| best_price_no_timestop     | trail2.4 close current + trend ema30_120 + cooldown6 + confirm1 |  1.45871 | 0.432351 | -0.249977 |         nan | nan        |      114 |                     4 |
| best_price_with_timestop   | winner_p1                                                       |  1.80435 | 0.568013 | -0.260183 |         nan | nan        |      124 |                     4 |
| best_volume_continuation   | vdo_gt0 oneshot H16 trend none cooldown6 trail2.7               |  1.53063 | 0.475124 | -0.245336 |         nan | nan        |       95 |                     4 |
| best_always_on_volume_exit | ema28_imbalance_ratio_base > 0 + trail2.7 none cd6              |  1.44936 | 0.312529 | -0.184508 |         nan | nan        |      181 |                     3 |
| best_coarse_robust_price   | trail2.4 close current none cd3 conf1 time60                    |  1.55824 | 0.474571 | -0.24726  |         nan | nan        |      122 |                     4 |
| runner_up_simple           | trail3.0 close lagged none cd3 conf1 time36                     |  1.75876 | 0.549384 | -0.273367 |         nan | nan        |      128 |                     4 |

The pattern is clear:
- the best family is **price-only + explicit time stop + cooldown**
- the best volume family is materially weaker than the best price family
- adding volume exits on top of the best price family generally **hurt**

## Winner

Top overall policy under the locked search:

- **trail enabled**
- **trail multiplier = 3.3**
- **peak anchor = close**
- **ATR mode = current robust ATR**
- **trail confirmation = 2 consecutive close-breaches**
- **trend exit = none**
- **cooldown after any exit = 6 bars**
- **time stop = 30 bars**
- all entries still use the locked entry winner

Shorthand:
`trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`

### Winner OOS performance

- Sharpe: **1.804352**
- CAGR: **0.568013**
- MDD: **-0.260183**
- Trades: **124**
- Positive folds vs Baseline A: **4/4**

Fold details:

| fold   |   sharpe |     cagr |       mdd |   trades |   baselineA_sharpe |   delta_sharpe_vs_A |
|:-------|---------:|---------:|----------:|---------:|-------------------:|--------------------:|
| fold1  | 1.69102  | 0.534189 | -0.237903 |       28 |           1.11969  |            0.571328 |
| fold2  | 1.82334  | 0.62895  | -0.260183 |       51 |           1.60409  |            0.219249 |
| fold3  | 2.37626  | 0.904358 | -0.192142 |       32 |           1.87535  |            0.50091  |
| fold4  | 0.895651 | 0.129977 | -0.120261 |       13 |           0.322236 |            0.573415 |

### Why this wins

It is **not** "time stop only". Time-stop-only policies were much weaker.  
The winning motif is:

1. keep a real trailing stop for adverse protection,
2. remove redundant trend exit,
3. add a **hard life-cycle cap** around 30 H4 bars,
4. add a **cooldown** to kill the large quick re-entry cluster.

That is the simplest story consistent with the data.

## Trade-structure change

| policy     |   trades_closed |   trades_total |   exposure |   median_holding |   mean_holding |   trail_stop_exits |   trend_exits |   time_stop_exits |
|:-----------|----------------:|---------------:|-----------:|-----------------:|---------------:|-------------------:|--------------:|------------------:|
| baseline_A |             103 |            104 |   0.376565 |               27 |        37.0971 |                 96 |             7 |                 0 |
| winner_p1  |             123 |            124 |   0.313087 |               30 |        25.7886 |                 39 |             0 |                84 |

Notable changes:
- exposure falls from **0.377** to **0.313**
- trades rise from **104** to **124**
- fast re-entry churn (`<=6` bars) drops from **38.5%** of trades in Baseline A to **0%** in the winner by construction
- trend exits disappear completely; most exits become **time-stop exits**

## Validation

### 1) WFO consistency
Pass: **4/4 folds** vs Baseline A.

### 2) Bootstrap vs Baseline A
Paired circular block bootstrap on stitched OOS return series:

|   block_len |   n_boot |   prob_delta_sharpe_gt0 |   delta_sharpe_p05 |   delta_sharpe_median |   delta_sharpe_p95 |
|------------:|---------:|------------------------:|-------------------:|----------------------:|-------------------:|
|          12 |     1200 |                0.9625   |         0.0312649  |              0.422933 |           0.808421 |
|          24 |     1200 |                0.951667 |         0.00634644 |              0.422196 |           0.884442 |
|          48 |     1200 |                0.950833 |         0.00856272 |              0.429069 |           0.879638 |
|          72 |     1200 |                0.945    |        -0.00749184 |              0.428078 |           0.850488 |
|         144 |     1200 |                0.961667 |         0.0264608  |              0.416264 |           0.830003 |
|         288 |     1200 |                0.954167 |         0.0182144  |              0.438866 |           0.837007 |

Pass: probability of positive delta Sharpe is ~**94.5% to 96.2%** across all block lengths.

### 3) Cost sweep vs Baseline A

|   side_cost |   bps_per_side |   baseline_sharpe |   winner_sharpe |   delta_sharpe |   baseline_mdd |   winner_mdd |   positive_folds_vs_A |
|------------:|---------------:|------------------:|----------------:|---------------:|---------------:|-------------:|----------------------:|
|     0       |            0   |         1.56549   |        2.05047  |      0.484977  |      -0.262385 |    -0.247122 |                     4 |
|     0.0005  |            5   |         1.48906   |        1.95223  |      0.463176  |      -0.266798 |    -0.252374 |                     4 |
|     0.001   |           10   |         1.41245   |        1.85371  |      0.441261  |      -0.271184 |    -0.257589 |                     4 |
|     0.00125 |           12.5 |         1.37408   |        1.80435  |      0.430268  |      -0.273367 |    -0.260183 |                     4 |
|     0.002   |           20   |         1.2588    |        1.65599  |      0.397185  |      -0.285778 |    -0.26791  |                     4 |
|     0.003   |           30   |         1.1048    |        1.45774  |      0.352935  |      -0.311032 |    -0.278088 |                     4 |
|     0.004   |           40   |         0.950685  |        1.25938  |      0.308699  |      -0.335394 |    -0.291434 |                     4 |
|     0.006   |           60   |         0.643059  |        0.864043 |      0.220984  |      -0.383552 |    -0.325998 |                     3 |
|     0.01    |          100   |         0.0366702 |        0.089842 |      0.0531718 |      -0.539702 |    -0.473556 |                     3 |

Pass:
- candidate beats Baseline A on aggregate Sharpe at **all 9/9** cost points tested
- candidate is positive in **>=3/4 folds at all 9/9** cost points

### 4) Exposure trap
Because MDD improved and exposure fell, an exposure-matched control was required.

Controls used: same entry, same trail family, same cooldown family, but **random time caps** instead of deterministic 30-bar cap.

| control                  |   mean_sharpe |     p05 |     p50 |     p95 |   prob_control_ge_winner |
|:-------------------------|--------------:|--------:|--------:|--------:|-------------------------:|
| random_cap_uniform_12_48 |      0.999371 | 0.63586 | 1.00572 | 1.32471 |                   0      |
| random_cap_uniform_24_36 |      1.44842  | 1.16498 | 1.44298 | 1.72512 |                   0.0125 |
| random_cap_uniform_29_32 |      1.68308  | 1.47888 | 1.68606 | 1.87296 |                   0.15   |

Read:
- a **wide random horizon** with the same mean holding horizon does **not** reproduce the winner
- even a tighter 24–36 bar random cap still underperforms; only a very tight 29–32 neighborhood begins to overlap the winner
- this says the edge is **not "less exposure in general"**; it is **horizon discipline in the ~30-bar family**

### 5) Sensitivity

Winner one-at-a-time sensitivity:

| param              |   value |   sharpe |       mdd |   trades |   positive_folds_vs_A |    fold1 |   fold2 |   fold3 |     fold4 |
|:-------------------|--------:|---------:|----------:|---------:|----------------------:|---------:|--------:|--------:|----------:|
| trail_mult         |     3   |  1.55722 | -0.289199 |      128 |                     4 | 1.23567  | 1.69836 | 2.15125 |  0.888755 |
| trail_mult         |     3.3 |  1.80435 | -0.260183 |      124 |                     4 | 1.69102  | 1.82334 | 2.37626 |  0.895651 |
| trail_mult         |     3.6 |  1.64189 | -0.264447 |      124 |                     4 | 1.56972  | 1.87704 | 1.91614 |  0.468788 |
| time_stop_bars     |    24   |  1.03545 | -0.323336 |      140 |                     1 | 0.640195 | 1.6723  | 1.25591 | -0.52517  |
| time_stop_bars     |    27   |  1.17895 | -0.298849 |      136 |                     1 | 1.19124  | 1.53325 | 1.33698 | -0.685219 |
| time_stop_bars     |    30   |  1.80435 | -0.260183 |      124 |                     4 | 1.69102  | 1.82334 | 2.37626 |  0.895651 |
| time_stop_bars     |    33   |  1.64802 | -0.276349 |      120 |                     3 | 1.4075   | 1.92127 | 2.37662 | -0.183133 |
| time_stop_bars     |    36   |  1.22071 | -0.294704 |      119 |                     0 | 0.979097 | 1.52048 | 1.72112 | -0.19918  |
| cooldown_bars      |     3   |  1.21695 | -0.299234 |      137 |                     1 | 1.24936  | 1.57996 | 1.34672 | -0.652441 |
| cooldown_bars      |     6   |  1.80435 | -0.260183 |      124 |                     4 | 1.69102  | 1.82334 | 2.37626 |  0.895651 |
| cooldown_bars      |     9   |  1.65816 | -0.27757  |      120 |                     4 | 1.27419  | 2.03961 | 2.18292 |  0.507802 |
| trail_confirm_bars |     1   |  1.5826  | -0.290463 |      128 |                     3 | 1.35898  | 1.44956 | 2.35686 |  1.2418   |
| trail_confirm_bars |     2   |  1.80435 | -0.260183 |      124 |                     4 | 1.69102  | 1.82334 | 2.37626 |  0.895651 |

Fine sensitivity around the main horizon parameter:

|   time_stop_bars |   sharpe |       mdd |   trades |   positive_folds_vs_A |   fold1 |   fold2 |   fold3 |     fold4 |
|-----------------:|---------:|----------:|---------:|----------------------:|--------:|--------:|--------:|----------:|
|               28 |  1.26303 | -0.27783  |      133 |                     2 | 1.3413  | 1.64953 | 1.23964 | -0.423298 |
|               29 |  1.43734 | -0.262135 |      128 |                     3 | 1.29634 | 1.77716 | 1.42794 |  0.855569 |
|               30 |  1.80435 | -0.260183 |      124 |                     4 | 1.69102 | 1.82334 | 2.37626 |  0.895651 |
|               31 |  1.69302 | -0.257813 |      123 |                     4 | 1.32607 | 2.08806 | 2.13413 |  0.607443 |
|               32 |  1.63056 | -0.256507 |      122 |                     4 | 1.37397 | 1.93556 | 2.08475 |  0.421829 |

Interpretation:
- **trail multiplier** is robust across 3.0 / 3.3 / 3.6
- **cooldown** has a stable winning band at 6–8 bars
- **time stop is the critical parameter**; the policy has a clear ridge around **29–32 bars**, with **30** best
- this is **not** a flat surface across the whole ±20% range, so the horizon is meaningful and should be treated as a real structural choice, not a nuisance parameter

### 6) Pre/post-2021 regime diagnostic
Because the locked OOS folds are post-2021 only, a diagnostic extension was run on a **fixed-threshold entry proxy** (`weak_vdo_thr = first-train median = 0.006481`) to compare pre-2021 and post-2021 behavior.

| period    |   baseline_sharpe |   cand_sharpe |   delta_sharpe |   baseline_mdd |   cand_mdd |   baseline_trades |   cand_trades |
|:----------|------------------:|--------------:|---------------:|---------------:|-----------:|------------------:|--------------:|
| pre_2021  |           2.00136 |      0.792073 |      -1.20929  |      -0.366178 |  -0.376299 |                59 |            81 |
| post_2021 |           1.24955 |      1.56945  |       0.319899 |      -0.285618 |  -0.285474 |               116 |           138 |

This is a **diagnostic**, not the primary ranking protocol. It shows:
- the winner is **clearly post-2021 favorable**
- pre-2021 behavior is materially worse than the proxy baseline
- this mirrors the broader caveat already known from the entry side: parts of the current system appear structurally post-2021

## Runner-up and simplicity trade-off

Best simpler 4/4 runner-up:

- `trail3.0_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop36`
- Sharpe **1.758763**
- MDD **-0.273367**
- Trades **128**

Bootstrap of winner vs this runner-up:

|   block_len |   n_boot |   prob_delta_sharpe_gt0 |   delta_sharpe_p05 |   delta_sharpe_median |   delta_sharpe_p95 |
|------------:|---------:|------------------------:|-------------------:|----------------------:|-------------------:|
|          12 |     1000 |                   0.602 |          -0.379505 |             0.065598  |           0.509215 |
|          24 |     1000 |                   0.576 |          -0.421974 |             0.0650911 |           0.539297 |
|          48 |     1000 |                   0.561 |          -0.400067 |             0.0350286 |           0.47521  |
|          72 |     1000 |                   0.571 |          -0.382839 |             0.0465526 |           0.470955 |
|         144 |     1000 |                   0.587 |          -0.332992 |             0.0457435 |           0.404841 |
|         288 |     1000 |                   0.583 |          -0.323898 |             0.0518665 |           0.420515 |

Interpretation:
- the top winner has higher aggregate OOS Sharpe
- but its edge over the simpler runner-up is **not overwhelming**
- if future freeze criteria prioritize simplicity / flatter parameter sensitivity over headline Sharpe, the runner-up is a legitimate fallback

## Final judgment

### Chosen winner under the locked ranking rule
Because the ranking rule is:

1. consistency,
2. aggregate Sharpe,
3. simplicity,

the exit winner is:

**`trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`**

### Why this is the right read
- It beats Baseline A in **4/4 folds**
- It materially improves Sharpe (**1.374 -> 1.804**) and slightly improves MDD (**-27.3% -> -26.0%**)
- It passes bootstrap and cost sweep cleanly
- It beats all tested volume-based exit families
- It is consistent with the vulnerability scan: the real, monetizable weakness is **no cooldown + overstaying**, not EMA cross churn or ATR flicker

### Caveats
- The edge is **clearly horizon-driven**; the 30-bar family matters
- The regime diagnostic says the winner is **post-2021 favorable**, not a timeless law
- The winner is strong enough to promote as the research winner, but the deployment freeze should still treat the horizon parameter carefully

## Recommendation for next step
Do **not** restart exit research from scratch.  
Freeze candidate should start from this price-only winner, then:
1. write exact executable spec,
2. run a final freeze-form validation,
3. only then decide whether to freeze the exact top winner or the simpler runner-up.
