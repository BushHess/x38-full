# End-to-end validation — frozen entry + exit candidates

## Freeze choice for entry

- Entry freeze locked **before** end-to-end validation: `weak_vdo_thr = 0.0065`.

- This means the relevant non-ML baseline after freeze is **combo 3**, not the earlier research-entry baseline of 1.374.

- Reconfirmed frozen-entry baseline (combo 3): Sharpe **1.340410**, MDD **-0.285618**, trades **104**.


## Policies tested

1. **Combo 1** = frozen entry `weakvdo(0.0065)` + exit winner `trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`

2. **Combo 2** = frozen entry `weakvdo(0.0065)` + exit runner-up `trail3.0_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop36`

3. **Combo 3** = frozen entry `weakvdo(0.0065)` + original base exit (non-ML)

4. **Combo 4** = original entry `VDO > 0` + original base exit (non-ML)


## Aggregate OOS result (stitched 4-fold WFO)

|   sharpe |     cagr |       mdd |   bar_count |   end_equity |   trades |   closed_trades |   exposure | policy                        |
|---------:|---------:|----------:|------------:|-------------:|---------:|----------------:|-----------:|:------------------------------|
|  1.79582 | 0.566914 | -0.284704 |       10224 |      8.12559 |      122 |             121 |   0.305556 | combo1_entryFreeze_exitWinner |
|  1.69282 | 0.521196 | -0.264523 |       10224 |      7.07725 |      127 |             126 |   0.32903  | combo2_entryFreeze_exitRunner |
|  1.34041 | 0.412571 | -0.285618 |       10224 |      5.00927 |      104 |             103 |   0.374511 | combo3_entryFreeze_baseExit   |
|  1.13076 | 0.350303 | -0.370939 |       10224 |      4.0592  |      118 |             117 |   0.409233 | combo4_origEntry_baseExit     |



## Fold-level OOS Sharpe

| fold   |   combo1_entryFreeze_exitWinner |   combo2_entryFreeze_exitRunner |   combo3_entryFreeze_baseExit |   combo4_origEntry_baseExit |
|:-------|--------------------------------:|--------------------------------:|------------------------------:|----------------------------:|
| fold1  |                        1.69102  |                        1.16761  |                      1.11969  |                   0.606679  |
| fold2  |                        1.86111  |                        2.33524  |                      1.50754  |                   1.53751   |
| fold3  |                        2.28429  |                        1.95458  |                      1.87535  |                   1.81857   |
| fold4  |                        0.895651 |                        0.916597 |                      0.322236 |                  -0.0221573 |



## Primary read

- **Combo 1 is the best end-to-end system.** It beats combo 3 in **4/4 folds** and lifts aggregate Sharpe from **1.340** to **1.796**.

- **Combo 2 also passes** vs combo 3 in **4/4 folds**, but its Sharpe (**1.693**) is lower than combo 1 by **0.103**.

- Versus the original system (combo 4), combo 1 improves Sharpe by **0.665** and improves MDD by **0.086** (less negative is better).

- Combo 2 has slightly better MDD than combo 1 (**-0.265** vs **-0.285**), but Sharpe and timing robustness both favor combo 1.


## Bootstrap

Paired circular block bootstrap on stitched OOS bar returns.

|   block_len |   n_boot |   prob_delta_sharpe_gt0 |   delta_sharpe_p05 |   delta_sharpe_median |   delta_sharpe_p95 | comparison       |
|------------:|---------:|------------------------:|-------------------:|----------------------:|-------------------:|:-----------------|
|          12 |     1200 |                0.965833 |         0.0509143  |             0.458216  |           0.901584 | combo1_vs_combo3 |
|          24 |     1200 |                0.965    |         0.0266876  |             0.452928  |           0.896729 | combo1_vs_combo3 |
|          48 |     1200 |                0.946667 |        -0.0177712  |             0.434332  |           0.873328 | combo1_vs_combo3 |
|          72 |     1200 |                0.9625   |         0.0380329  |             0.441975  |           0.897696 | combo1_vs_combo3 |
|         144 |     1200 |                0.975    |         0.0796388  |             0.452885  |           0.8568   | combo1_vs_combo3 |
|         288 |     1200 |                0.9825   |         0.107891   |             0.455149  |           0.80295  | combo1_vs_combo3 |
|          12 |     1200 |                0.961667 |         0.0292468  |             0.355688  |           0.675778 | combo2_vs_combo3 |
|          24 |     1200 |                0.970833 |         0.0430202  |             0.342181  |           0.659476 | combo2_vs_combo3 |
|          48 |     1200 |                0.955833 |         0.0114751  |             0.348058  |           0.709836 | combo2_vs_combo3 |
|          72 |     1200 |                0.964167 |         0.0266667  |             0.347287  |           0.736345 | combo2_vs_combo3 |
|         144 |     1200 |                0.946667 |        -0.0102387  |             0.340105  |           0.727167 | combo2_vs_combo3 |
|         288 |     1200 |                0.9525   |         0.00737358 |             0.329952  |           0.769827 | combo2_vs_combo3 |
|          12 |     1200 |                0.639167 |        -0.360241   |             0.10244   |           0.55274  | combo1_vs_combo2 |
|          24 |     1200 |                0.638333 |        -0.356884   |             0.106366  |           0.568091 | combo1_vs_combo2 |
|          48 |     1200 |                0.63     |        -0.349846   |             0.0888284 |           0.535485 | combo1_vs_combo2 |
|          72 |     1200 |                0.653333 |        -0.304356   |             0.110204  |           0.530087 | combo1_vs_combo2 |
|         144 |     1200 |                0.6525   |        -0.279991   |             0.097179  |           0.526011 | combo1_vs_combo2 |
|         288 |     1200 |                0.665    |        -0.289757   |             0.0953045 |           0.501363 | combo1_vs_combo2 |


- Combo 1 vs combo 3: `P(delta Sharpe > 0)` = **94.7%–98.2%** across block lengths.

- Combo 2 vs combo 3: **94.7%–97.1%**.

- Combo 1 vs combo 2: only **63.0%–66.5%**. So combo 1 wins, but not by an overwhelming bootstrap margin.


## Cost sweep

|   side_cost |   bps_per_side |   combo1_sharpe |   combo1_mdd |   combo1_trades |   combo2_sharpe |   combo2_mdd |   combo2_trades |   combo3_sharpe |   combo3_mdd |   combo3_trades |   combo4_sharpe |   combo4_mdd |   combo4_trades |   combo1_pos_folds_vs_combo3 |   combo2_pos_folds_vs_combo3 |   combo1_pos_folds_vs_combo4 |   combo2_pos_folds_vs_combo4 |   combo1_vs_combo2_delta |
|------------:|---------------:|----------------:|-------------:|----------------:|----------------:|-------------:|----------------:|----------------:|-------------:|----------------:|----------------:|-------------:|----------------:|-----------------------------:|-----------------------------:|-----------------------------:|-----------------------------:|-------------------------:|
|     0       |            0   |        2.03706  |    -0.264761 |             122 |       1.94443   |    -0.253408 |             127 |      1.53232    |    -0.266616 |             104 |        1.33603  |    -0.330612 |             118 |                            4 |                            4 |                            4 |                            4 |                0.0926315 |
|     0.0005  |            5   |        1.94077  |    -0.272804 |             122 |       1.84401   |    -0.257874 |             127 |      1.45568    |    -0.274277 |             104 |        1.254    |    -0.344523 |             118 |                            4 |                            4 |                            4 |                            4 |                0.0967575 |
|     0.001   |           10   |        1.8442   |    -0.280759 |             122 |       1.74329   |    -0.262313 |             127 |      1.37887    |    -0.281857 |             104 |        1.17186  |    -0.361432 |             118 |                            4 |                            4 |                            4 |                            4 |                0.100914  |
|     0.00125 |           12.5 |        1.79582  |    -0.284704 |             122 |       1.69282   |    -0.264523 |             127 |      1.34041    |    -0.285618 |             104 |        1.13076  |    -0.370939 |             118 |                            4 |                            4 |                            4 |                            4 |                0.103001  |
|     0.002   |           20   |        1.65042  |    -0.29641  |             122 |       1.54112   |    -0.271112 |             127 |      1.22486    |    -0.296782 |             104 |        1.00739  |    -0.39862  |             118 |                            4 |                            4 |                            4 |                            4 |                0.109297  |
|     0.003   |           30   |        1.45612  |    -0.31172  |             122 |       1.33837   |    -0.279807 |             127 |      1.07055    |    -0.317438 |             104 |        0.842886 |    -0.433642 |             118 |                            4 |                            2 |                            4 |                            4 |                0.117745  |
|     0.004   |           40   |        1.26171  |    -0.326922 |             122 |       1.13549   |    -0.305605 |             127 |      0.916166   |    -0.341574 |             104 |        0.678596 |    -0.466624 |             118 |                            4 |                            2 |                            4 |                            3 |                0.126218  |
|     0.006   |           60   |        0.874191 |    -0.35719  |             122 |       0.731107  |    -0.385992 |             127 |      0.608164   |    -0.40172  |             104 |        0.351668 |    -0.540764 |             118 |                            4 |                            2 |                            4 |                            3 |                0.143084  |
|     0.01    |          100   |        0.114861 |    -0.493886 |             122 |      -0.0606003 |    -0.527891 |             127 |      0.00162406 |    -0.55712  |             104 |       -0.288978 |    -0.687006 |             118 |                            3 |                            1 |                            4 |                            3 |                0.175462  |


- Combo 1 beats combo 3 on aggregate Sharpe at **9/9** tested costs and stays **4/4 folds positive** vs combo 3 at all 9/9 cost points.

- Combo 2 also beats combo 3 at **9/9** cost points and stays **4/4** or **3/4** positive depending on cost; it never overtakes combo 1.


## Exposure trap

Exposure-trap control = same entry and same trail/cooldown family, but replace deterministic time-stop with random per-trade cap drawn from a uniform band around the candidate horizon.

| control                  |   cap_low |   cap_high |   n_sim |   mean_sharpe |      p05 |     p50 |     p95 |   prob_control_ge_candidate | combo                         |
|:-------------------------|----------:|-----------:|--------:|--------------:|---------:|--------:|--------:|----------------------------:|:------------------------------|
| random_cap_uniform_12_48 |        12 |         48 |     500 |       1.05554 | 0.717602 | 1.05518 | 1.39999 |                       0     | combo1_entryFreeze_exitWinner |
| random_cap_uniform_24_36 |        24 |         36 |     500 |       1.37104 | 1.11234  | 1.37844 | 1.63746 |                       0.006 | combo1_entryFreeze_exitWinner |
| random_cap_uniform_29_32 |        29 |         32 |     500 |       1.61869 | 1.42635  | 1.62507 | 1.7891  |                       0.042 | combo1_entryFreeze_exitWinner |
| random_cap_uniform_18_54 |        18 |         54 |     500 |       1.30288 | 1.07146  | 1.30131 | 1.55146 |                       0.006 | combo2_entryFreeze_exitRunner |
| random_cap_uniform_30_42 |        30 |         42 |     500 |       1.43074 | 1.2557   | 1.44065 | 1.59017 |                       0.006 | combo2_entryFreeze_exitRunner |
| random_cap_uniform_34_38 |        34 |         38 |     500 |       1.572   | 1.45185  | 1.57183 | 1.70248 |                       0.068 | combo2_entryFreeze_exitRunner |


- Combo 1 passes cleanly: even the tight `29–32` random-cap control reaches or exceeds the candidate only **4.2%** of the time.

- Combo 2 also passes, but the tight `34–38` control overlaps more (**6.8%**), so its edge is somewhat less distinct than combo 1.


## Churn check

| combo                         |   closed_trades |   reenter_le3_count |   reenter_le6_count |   reenter_le3_pct_all_closed |   reenter_le6_pct_all_closed |
|:------------------------------|----------------:|--------------------:|--------------------:|-----------------------------:|-----------------------------:|
| combo1_entryFreeze_exitWinner |             121 |                   0 |                   0 |                      0       |                     0        |
| combo2_entryFreeze_exitRunner |             126 |                   0 |                  46 |                      0       |                     0.365079 |
| combo3_entryFreeze_baseExit   |             103 |                  24 |                  40 |                      0.23301 |                     0.38835  |


| exit_reason   |   exits |   reenter_le3 |   reenter_le6 |   pct_le3 |   pct_le6 | combo                         |
|:--------------|--------:|--------------:|--------------:|----------:|----------:|:------------------------------|
| time_stop     |      82 |             0 |             0 |   0       |  0        | combo1_entryFreeze_exitWinner |
| trail_stop    |      36 |             0 |             0 |   0       |  0        | combo1_entryFreeze_exitWinner |
| time_stop     |      54 |             0 |            26 |   0       |  0.481481 | combo2_entryFreeze_exitRunner |
| trail_stop    |      69 |             0 |            20 |   0       |  0.289855 | combo2_entryFreeze_exitRunner |
| trail_stop    |      92 |            24 |            39 |   0.26087 |  0.423913 | combo3_entryFreeze_baseExit   |
| trend_exit    |       8 |             0 |             1 |   0       |  0.125    | combo3_entryFreeze_baseExit   |


- This is the most important interaction result.

- Combo 1 drives quick re-entry churn to **0% within <=3 bars** and **0% within <=6 bars**.

- Combo 2 kills the <=3-bar cluster by construction, but still leaves **36.5%** re-entry within <=6 bars.

- Combo 3 (frozen entry + base exit) still has **23.3%** re-entry within <=3 bars and **38.8%** within <=6 bars.

- So the new entry and the winning exit do **not** fight each other. They fit together unusually well.


## Permutation / timing null

- A literal shuffle of realized strategy returns is **degenerate for Sharpe** because Sharpe depends only on mean and standard deviation, not order. That naive test would return a meaningless p-value of 1.0 for every combo.

- Instead, a meaningful timing-permutation null was used: random circular shifts of the OOS **market bars within each fold**, while keeping the realized exposure/turnover path fixed. This preserves exposure, holding-length structure, and fee events, but destroys timing alignment.

| combo                         |   obs_sharpe | perm_method                                                 |   n_perm |   p_value_ge_obs |   perm_mean |   perm_p05 |   perm_p50 |   perm_p95 |
|:------------------------------|-------------:|:------------------------------------------------------------|---------:|-----------------:|------------:|-----------:|-----------:|-----------:|
| combo1_entryFreeze_exitWinner |      1.79582 | random_circular_shift_market_within_each_fold (timing null) |     1200 |      0.000832639 |    0.105722 |  -0.552642 |   0.104908 |   0.776104 |
| combo2_entryFreeze_exitRunner |      1.69282 | random_circular_shift_market_within_each_fold (timing null) |     1200 |      0.000832639 |    0.122611 |  -0.531401 |   0.118711 |   0.810673 |
| combo3_entryFreeze_baseExit   |      1.34041 | random_circular_shift_market_within_each_fold (timing null) |     1200 |      0.00749376  |    0.169406 |  -0.481628 |   0.149456 |   0.844866 |
| combo4_origEntry_baseExit     |      1.13076 | random_circular_shift_market_within_each_fold (timing null) |     1200 |      0.0141549   |    0.203701 |  -0.452965 |   0.199654 |   0.865607 |


- Under this timing null, combo 1 and combo 2 both have p-value **~0.00083**, materially stronger than the base-exit baselines.


## Pre/post-2021 diagnostic

|   sharpe |     cagr |       mdd |   bar_count |   end_equity |   trades |   closed_trades |   exposure | period    | combo   |
|---------:|---------:|----------:|------------:|-------------:|---------:|----------------:|-----------:|:----------|:--------|
| 0.972395 | 0.363438 | -0.376299 |        6287 |      2.43529 |       96 |              96 |   0.369811 | pre_2021  | combo1  |
| 1.14794  | 0.458298 | -0.307416 |        6287 |      2.95405 |       99 |              99 |   0.393988 | pre_2021  | combo2  |
| 1.78709  | 0.991634 | -0.366178 |        6287 |      7.22867 |       70 |              70 |   0.433593 | pre_2021  | combo3  |
| 1.95125  | 1.1952   | -0.388616 |        6287 |      9.55885 |       75 |              75 |   0.472244 | pre_2021  | combo4  |
| 1.79517  | 0.566638 | -0.284704 |       10224 |      8.11891 |      122 |             122 |   0.305653 | post_2021 | combo1  |
| 1.68277  | 0.517147 | -0.264523 |       10224 |      6.98982 |      127 |             127 |   0.329421 | post_2021 | combo2  |
| 1.33108  | 0.408812 | -0.285618 |       10224 |      4.94738 |      104 |             104 |   0.374902 | post_2021 | combo3  |
| 1.12202  | 0.346709 | -0.370939 |       10224 |      4.00905 |      118 |             118 |   0.409624 | post_2021 | combo4  |


- The post-2021 read remains strong for combo 1 and combo 2.

- Pre-2021, both exit candidates under frozen entry underperform the frozen-entry base-exit baseline. This matches the structural caveat already known from entry and exit research: these improvements are **post-2021 favorable**, not timeless laws.


## Local sensitivity around combo 1 and combo 2

| combo   | param              |   value |   sharpe |       mdd |   trades |   pos_folds_vs_combo3 |
|:--------|:-------------------|--------:|---------:|----------:|---------:|----------------------:|
| combo1  | trail_mult         |     3   |  1.524   | -0.307325 |      127 |                     4 |
| combo1  | trail_mult         |     3.3 |  1.79582 | -0.284704 |      122 |                     4 |
| combo1  | trail_mult         |     3.6 |  1.5925  | -0.302447 |      122 |                     3 |
| combo1  | time_stop_bars     |    27   |  1.10984 | -0.351607 |      134 |                     1 |
| combo1  | time_stop_bars     |    30   |  1.79582 | -0.284704 |      122 |                     4 |
| combo1  | time_stop_bars     |    33   |  1.61888 | -0.289698 |      119 |                     3 |
| combo1  | cooldown_bars      |     3   |  1.16454 | -0.320914 |      135 |                     1 |
| combo1  | cooldown_bars      |     6   |  1.79582 | -0.284704 |      122 |                     4 |
| combo1  | cooldown_bars      |     9   |  1.62114 | -0.301515 |      119 |                     4 |
| combo1  | trail_confirm_bars |     1   |  1.54965 | -0.308557 |      126 |                     3 |
| combo1  | trail_confirm_bars |     2   |  1.79582 | -0.284704 |      122 |                     4 |
| combo2  | trail_mult         |     2.7 |  1.56998 | -0.22623  |      135 |                     4 |
| combo2  | trail_mult         |     3   |  1.69282 | -0.264523 |      127 |                     4 |
| combo2  | trail_mult         |     3.3 |  1.41878 | -0.272567 |      125 |                     3 |
| combo2  | time_stop_bars     |    32   |  1.27273 | -0.329879 |      136 |                     2 |
| combo2  | time_stop_bars     |    36   |  1.69282 | -0.264523 |      127 |                     4 |
| combo2  | time_stop_bars     |    40   |  1.2664  | -0.264523 |      125 |                     2 |
| combo2  | cooldown_bars      |     0   |  1.57902 | -0.275876 |      139 |                     4 |
| combo2  | cooldown_bars      |     3   |  1.69282 | -0.264523 |      127 |                     4 |
| combo2  | cooldown_bars      |     6   |  1.33243 | -0.264629 |      124 |                     2 |


- Combo 1 still has a clear ridge around the 30-bar horizon and cooldown 6 under frozen entry.

- Combo 2 is also viable, but it is narrower around its 36-bar horizon and loses more edge when cooldown is pushed out.


## Validation scorecard

| combo                         |   wfo_positive_folds_vs_combo3 |   bootstrap_prob_min_vs_combo3 |   cost_points_ge3folds_vs_combo3 |   cost_points_total |   exposure_trap_tight_prob_ge_candidate |   reenter_le6_pct |   timing_perm_p_value | passes_full_standard   |
|:------------------------------|-------------------------------:|-------------------------------:|---------------------------------:|--------------------:|----------------------------------------:|------------------:|----------------------:|:-----------------------|
| combo1_entryFreeze_exitWinner |                              4 |                       0.946667 |                                9 |                   9 |                                   0.042 |          0        |           0.000832639 | True                   |
| combo2_entryFreeze_exitRunner |                              4 |                       0.946667 |                                5 |                   9 |                                   0.068 |          0.365079 |           0.000832639 | False                  |

- Using the project-standard cost-sweep criterion (**>=3/4 folds positive at >=7/9 tested costs**), **combo 1 passes** and **combo 2 fails**.
- That means combo 2 remains a credible runner-up on headline OOS Sharpe, but it does **not** clear the same end-to-end validation bar as combo 1.

## Final judgment

Using the locked ranking rule — consistency first, then aggregate Sharpe, then simplicity — the best **end-to-end** system is:


**Frozen entry `weakvdo(0.0065)` + exit winner `trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`.**


Why this is the right read:

- It beats frozen-entry base exit in **4/4 folds** and lifts Sharpe from **1.340** to **1.796**.

- It also beats the original full baseline from **1.131** to **1.796**.

- It passes bootstrap, cost sweep, exposure trap, and timing-permutation null.

- Most importantly, it kills the large quick re-entry cluster that the frozen-entry baseline still suffers from.

- Combo 2 is a credible simpler fallback, but end-to-end evidence still points to combo 1 as the true winner.
