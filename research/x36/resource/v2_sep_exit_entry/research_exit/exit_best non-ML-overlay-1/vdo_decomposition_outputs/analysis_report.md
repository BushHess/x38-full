# VDO decomposition + candidate-signal analysis

## 1) Core protocol
- Core entry universe: trend-up (`EMA30 > EMA120`) and D1 regime-on, no volume gate.
- All signal candidates were tested as 1D entry filters on the *same* core architecture with fixed-date expanding-window WFO folds.
- WFO folds: 2021H2-2022, 2023H1-2024H1, 2024H2-2025H1, 2025H2-2026-02.

## 2) Baseline
- Ungated core WFO OOS Sharpe: **0.742**, CAGR **0.210**, MDD **-0.499**.

## 3) Best single-signal hard gates (aggregate WFO OOS)
| signal                           | measurement           | operator          | rule_type       |   natural_center |   aggregate_sharpe |   aggregate_cagr |   aggregate_mdd |   positive_folds_vs_baseline |   avg_selected_threshold |
|:---------------------------------|:----------------------|:------------------|:----------------|-----------------:|-------------------:|-----------------:|----------------:|-----------------------------:|-------------------------:|
| osc_12_28_imbalance_ratio_base   | imbalance_ratio_base  | osc_12_28         | fixed_natural   |                0 |            1.13076 |         0.350303 |       -0.370939 |                            3 |            nan           |
| osc_12_28_imbalance_ratio_quote  | imbalance_ratio_quote | osc_12_28         | fixed_natural   |                0 |            1.13076 |         0.350303 |       -0.370939 |                            3 |            nan           |
| vdo                              | imbalance_ratio_base  | osc_12_28_builtin | fixed_natural   |                0 |            1.13076 |         0.350303 |       -0.370939 |                            3 |            nan           |
| ema12_vol_surprise_quote_28      | vol_surprise_quote_28 | ema12             | train_threshold |                1 |            1.10153 |         0.336404 |       -0.324224 |                            3 |              1.0869      |
| osc_12_28_imbalance_ratio_base   | imbalance_ratio_base  | osc_12_28         | train_threshold |                0 |            1.09744 |         0.337028 |       -0.339223 |                            4 |             -0.000675859 |
| vdo                              | imbalance_ratio_base  | osc_12_28_builtin | train_threshold |                0 |            1.09744 |         0.337028 |       -0.339223 |                            4 |             -0.000675859 |
| osc_12_28_net_quote_norm_28      | net_quote_norm_28     | osc_12_28         | fixed_natural   |                0 |            1.08123 |         0.32052  |       -0.331808 |                            4 |            nan           |
| osc_12_28_imbalance_ratio_quote  | imbalance_ratio_quote | osc_12_28         | train_threshold |                0 |            1.07027 |         0.32553  |       -0.364848 |                            4 |             -0.000691889 |
| osc_12_28_net_quote_norm_28      | net_quote_norm_28     | osc_12_28         | train_threshold |                0 |            1.06523 |         0.320826 |       -0.311952 |                            3 |             -0.00262663  |
| pos_count4_vol_surprise_quote_28 | vol_surprise_quote_28 | pos_count4        | train_threshold |              nan |            0.989   |         0.292221 |       -0.400481 |                            4 |              1.25        |
| imbalance_ratio_base             | imbalance_ratio_base  | level             | train_threshold |                0 |            0.8972  |         0.210994 |       -0.357073 |                            2 |              0.0792283   |
| imbalance_ratio_quote            | imbalance_ratio_quote | level             | train_threshold |                0 |            0.8972  |         0.210994 |       -0.357073 |                            2 |              0.0793474   |

## 4) Measurement layer: best operator per measurement
| measurement           | signal                          | operator   |   aggregate_sharpe |   positive_folds_vs_baseline |
|:----------------------|:--------------------------------|:-----------|-------------------:|-----------------------------:|
| imbalance_ratio_base  | osc_12_28_imbalance_ratio_base  | osc_12_28  |            1.09744 |                            4 |
| imbalance_ratio_quote | osc_12_28_imbalance_ratio_quote | osc_12_28  |            1.07027 |                            4 |
| net_quote_norm_28     | osc_12_28_net_quote_norm_28     | osc_12_28  |            1.06523 |                            3 |
| vol_surprise_quote_28 | ema12_vol_surprise_quote_28     | ema12      |            1.10153 |                            3 |

## 5) Operator layer on the original VDO measurement (base imbalance ratio)
| signal                          | operator          |   aggregate_sharpe |   positive_folds_vs_baseline |
|:--------------------------------|:------------------|-------------------:|-----------------------------:|
| osc_12_28_imbalance_ratio_base  | osc_12_28         |          1.09744   |                            4 |
| vdo                             | osc_12_28_builtin |          1.09744   |                            4 |
| imbalance_ratio_base            | level             |          0.8972    |                            2 |
| pos_count4_imbalance_ratio_base | pos_count4        |          0.724759  |                            1 |
| ema12_imbalance_ratio_base      | ema12             |          0.600235  |                            3 |
| ema28_imbalance_ratio_base      | ema28             |          0.0662445 |                            1 |

## 6) Decision layer on VDO
- Fold-selected VDO thresholds (train-only) mean = **-0.000676**, std = **0.001658**.
|   fold | direction   |    threshold |   sharpe |   trades |
|-------:|:------------|-------------:|---------:|---------:|
|      1 | ge          | -0.000649018 |  1.9585  |       75 |
|      2 | ge          |  0.000621296 |  1.58998 |      104 |
|      3 | ge          | -0.00339102  |  1.5996  |      162 |
|      4 | ge          |  0.000715311 |  1.58988 |      175 |

## 7) Trade-level information metrics
| signal                           |   spearman_ret |      mi_win |   auc_win_raw |   auc_win_oriented |   top_minus_bottom_win_rate |   top_minus_bottom_mean_ret |
|:---------------------------------|---------------:|------------:|--------------:|-------------------:|----------------------------:|----------------------------:|
| ema28_imbalance_ratio_base       |    -0.132611   | 0.057602    |      0.41945  |           0.58055  |                  -0.18      |                 -0.00863505 |
| ema28_imbalance_ratio_quote      |    -0.1325     | 0.0521174   |      0.419584 |           0.580416 |                  -0.18      |                 -0.00863505 |
| ema28_net_quote_norm_28          |    -0.0790684  | 0.0361781   |      0.44118  |           0.55882  |                  -0.1       |                  0.00765104 |
| osc_12_28_imbalance_ratio_quote  |     0.0753264  | 0.000946897 |      0.549363 |           0.549363 |                   0.1       |                  0.0417478  |
| osc_12_28_imbalance_ratio_base   |     0.0744441  | 0           |      0.54896  |           0.54896  |                   0.1       |                  0.0417478  |
| vdo                              |     0.0744441  | 0           |      0.54896  |           0.54896  |                   0.1       |                  0.0417478  |
| ema12_imbalance_ratio_base       |    -0.0682788  | 0           |      0.456405 |           0.543595 |                  -0.1       |                  0.00516103 |
| ema12_imbalance_ratio_quote      |    -0.0672006  | 0           |      0.457009 |           0.542991 |                  -0.1       |                  0.00516103 |
| osc_12_28_net_quote_norm_28      |     0.0841363  | 0           |      0.54118  |           0.54118  |                   0.14      |                  0.0494769  |
| vol_surprise_quote_28            |     0.00635159 | 0           |      0.538364 |           0.538364 |                   0.12      |                 -0.0196129  |
| pos_count4_vol_surprise_quote_28 |    -0.0483128  | 0.0236081   |      0.467471 |           0.532529 |                  -0.0992556 |                 -0.0257872  |
| ema28_vol_surprise_quote_28      |    -0.020649   | 0.00829556  |      0.472569 |           0.527431 |                  -0.1       |                 -0.0172397  |

## 8) Incremental model WFO (beyond price-only baseline)
| signal                          | model                |   aggregate_log_loss |   aggregate_auc |   delta_auc_vs_baseline |   delta_log_loss_vs_baseline |
|:--------------------------------|:---------------------|---------------------:|----------------:|------------------------:|-----------------------------:|
| ema28_imbalance_ratio_base      | baseline_plus_signal |             0.693335 |        0.493605 |               0.0137164 |                  -0.00424219 |
| ema28_imbalance_ratio_base      | baseline_price       |             0.697578 |        0.479889 |             nan         |                 nan          |
| ema28_imbalance_ratio_base      | signal_only          |             0.688683 |        0.528267 |             nan         |                 nan          |
| osc_12_28_imbalance_ratio_quote | baseline_plus_signal |             0.693356 |        0.517331 |               0.0374421 |                  -0.00422152 |
| osc_12_28_imbalance_ratio_quote | baseline_price       |             0.697578 |        0.479889 |             nan         |                 nan          |
| osc_12_28_imbalance_ratio_quote | signal_only          |             0.689384 |        0.519926 |             nan         |                 nan          |
| osc_12_28_net_quote_norm_28     | baseline_plus_signal |             0.695013 |        0.511029 |               0.0311399 |                  -0.0025647  |
| osc_12_28_net_quote_norm_28     | baseline_price       |             0.697578 |        0.479889 |             nan         |                 nan          |
| osc_12_28_net_quote_norm_28     | signal_only          |             0.691223 |        0.492493 |             nan         |                 nan          |
| vdo                             | baseline_plus_signal |             0.693328 |        0.517702 |               0.0378128 |                  -0.00424962 |
| vdo                             | baseline_price       |             0.697578 |        0.479889 |             nan         |                 nan          |
| vdo                             | signal_only          |             0.689381 |        0.519741 |             nan         |                 nan          |
| vol_surprise_quote_28           | baseline_plus_signal |             0.691376 |        0.517331 |               0.0374421 |                  -0.00620175 |
| vol_surprise_quote_28           | baseline_price       |             0.697578 |        0.479889 |             nan         |                 nan          |
| vol_surprise_quote_28           | signal_only          |             0.684934 |        0.542354 |             nan         |                 nan          |

## 9) Combination-gate tests around VDO
| combo_name                         | fold      | selected_direction   |   selected_threshold |      sharpe |        cagr |       mdd |   trades |   end_equity |   bar_count | companion_signal           | direction   |    threshold |
|:-----------------------------------|:----------|:---------------------|---------------------:|------------:|------------:|----------:|---------:|-------------:|------------:|:---------------------------|:------------|-------------:|
| vdo_and_vol_surprise_quote_28      | 1         | le                   |           1.11258    |  0.786201   |  0.224284   | -0.294094 |       29 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_vol_surprise_quote_28      | 2         | le                   |           1.11531    |  1.41785    |  0.511603   | -0.283594 |       43 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_vol_surprise_quote_28      | 3         | le                   |           1.45606    |  1.47643    |  0.481186   | -0.18556  |       28 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_vol_surprise_quote_28      | 4         | ge                   |           0.405993   | -0.0538476  | -0.0216687  | -0.127752 |       12 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_vol_surprise_quote_28      | aggregate | nan                  |         nan          |  1.0741     |  0.321519   | -0.294094 |      nan |      3.67103 |       10224 | nan                        | nan         | nan          |
| vdo_and_vol_surprise_quote_28      | 1         | nan                  |         nan          |  1.99048    |  1.22927    | -0.385704 |       73 |    nan       |         nan | vol_surprise_quote_28      | le          |   1.11258    |
| vdo_and_vol_surprise_quote_28      | 2         | nan                  |         nan          |  1.64428    |  0.814324   | -0.385704 |      102 |    nan       |         nan | vol_surprise_quote_28      | le          |   1.11531    |
| vdo_and_vol_surprise_quote_28      | 3         | nan                  |         nan          |  1.58447    |  0.732251   | -0.388967 |      148 |    nan       |         nan | vol_surprise_quote_28      | le          |   1.45606    |
| vdo_and_vol_surprise_quote_28      | 4         | nan                  |         nan          |  1.58353    |  0.708241   | -0.388616 |      180 |    nan       |         nan | vol_surprise_quote_28      | ge          |   0.405993   |
| vdo_and_net_quote_norm_28          | 1         | le                   |           0.146639   |  0.606679   |  0.156541   | -0.364848 |       31 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_net_quote_norm_28          | 2         | ge                   |          -0.0154724  |  1.49563    |  0.562018   | -0.309187 |       46 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_net_quote_norm_28          | 3         | ge                   |          -0.00955434 |  1.48916    |  0.488255   | -0.173342 |       28 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_net_quote_norm_28          | 4         | ge                   |          -0.132155   | -0.00342199 | -0.0136316  | -0.124778 |       12 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_net_quote_norm_28          | aggregate | nan                  |         nan          |  1.04597    |  0.314112   | -0.370939 |      nan |      3.57603 |       10224 | nan                        | nan         | nan          |
| vdo_and_net_quote_norm_28          | 1         | nan                  |         nan          |  1.96864    |  1.21211    | -0.387743 |       74 |    nan       |         nan | net_quote_norm_28          | le          |   0.146639   |
| vdo_and_net_quote_norm_28          | 2         | nan                  |         nan          |  1.5922     |  0.775757   | -0.388616 |      103 |    nan       |         nan | net_quote_norm_28          | ge          |  -0.0154724  |
| vdo_and_net_quote_norm_28          | 3         | nan                  |         nan          |  1.58565    |  0.731239   | -0.366083 |      148 |    nan       |         nan | net_quote_norm_28          | ge          |  -0.00955434 |
| vdo_and_net_quote_norm_28          | 4         | nan                  |         nan          |  1.57348    |  0.702835   | -0.388616 |      181 |    nan       |         nan | net_quote_norm_28          | ge          |  -0.132155   |
| vdo_and_ema28_imbalance_ratio_base | 1         | le                   |           0.0707091  |  0.606679   |  0.156541   | -0.364848 |       31 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_ema28_imbalance_ratio_base | 2         | le                   |           0.0658889  |  1.53751    |  0.585603   | -0.309187 |       47 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_ema28_imbalance_ratio_base | 3         | le                   |          -0.00769351 |  1.63133    |  0.526312   | -0.137752 |       26 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_ema28_imbalance_ratio_base | 4         | le                   |          -0.00710093 |  0.113686   |  0.00584608 | -0.108584 |       10 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_ema28_imbalance_ratio_base | aggregate | nan                  |         nan          |  1.09685    |  0.331312   | -0.370939 |      nan |      3.79966 |       10224 | nan                        | nan         | nan          |
| vdo_and_ema28_imbalance_ratio_base | 1         | nan                  |         nan          |  2.01989    |  1.26189    | -0.388616 |       72 |    nan       |         nan | ema28_imbalance_ratio_base | le          |   0.0707091  |
| vdo_and_ema28_imbalance_ratio_base | 2         | nan                  |         nan          |  1.60683    |  0.789922   | -0.388616 |      103 |    nan       |         nan | ema28_imbalance_ratio_base | le          |   0.0658889  |
| vdo_and_ema28_imbalance_ratio_base | 3         | nan                  |         nan          |  1.76219    |  0.633363   | -0.30604  |       77 |    nan       |         nan | ema28_imbalance_ratio_base | le          |  -0.00769351 |
| vdo_and_ema28_imbalance_ratio_base | 4         | nan                  |         nan          |  1.72642    |  0.611024   | -0.30604  |      104 |    nan       |         nan | ema28_imbalance_ratio_base | le          |  -0.00710093 |
| vdo_only                           | 1         | nan                  |         nan          |  0.606679   |  0.156541   | -0.364848 |       31 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_only                           | 2         | nan                  |         nan          |  1.53751    |  0.585603   | -0.309187 |       47 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_only                           | 3         | nan                  |         nan          |  1.81857    |  0.655423   | -0.132369 |       28 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_only                           | 4         | nan                  |         nan          | -0.0221573  | -0.0166476  | -0.124778 |       12 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_only                           | aggregate | nan                  |         nan          |  1.13076    |  0.350303   | -0.370939 |      nan |      4.0592  |       10224 | nan                        | nan         | nan          |
| vdo_and_volsurp_ge1                | 1         | nan                  |         nan          |  0.29622    |  0.0447006  | -0.406419 |       29 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_volsurp_ge1                | 2         | nan                  |         nan          |  1.64156    |  0.618335   | -0.273149 |       42 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_volsurp_ge1                | 3         | nan                  |         nan          |  2.05597    |  0.74416    | -0.121571 |       25 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_volsurp_ge1                | 4         | nan                  |         nan          |  0.179029   |  0.0159276  | -0.133576 |       11 |    nan       |         nan | nan                        | nan         | nan          |
| vdo_and_volsurp_ge1                | aggregate | nan                  |         nan          |  1.12316    |  0.336363   | -0.406419 |      nan |      3.86739 |       10224 | nan                        | nan         | nan          |

## 10) Practical read
- Current VDO hard gate (`vdo >= 0`) gives aggregate WFO OOS Sharpe **1.131** vs ungated **0.742**.
- Letting VDO threshold float on train folds changes little: aggregate WFO OOS Sharpe **1.097**. So the decision surface is already near the right place; the remaining room is unlikely to come from threshold fiddling.
- Best aggregate combination gate in this sweep: **vdo_only** with Sharpe **1.131**.
- Interpretation rule: if a signal only works after train-threshold search and not with a natural physical threshold, it carries weak/extractive information, not robust first-principles information.