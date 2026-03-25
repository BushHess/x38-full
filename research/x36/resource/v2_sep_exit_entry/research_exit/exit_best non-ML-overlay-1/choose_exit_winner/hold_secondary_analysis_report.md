# Secondary signals in continuation/hold context

## Protocol

- Entry core locked: `EMA30 > EMA120 AND VDO > 0 AND D1 regime_ok`.

- Baseline exit: ATR trail-stop (`close < peak_close - 3*robust_ATR`) or trend cross-down.

- Hold decision universe: all baseline trail-stop episodes (`n = 178`).

- WFO folds are identical to the frozen validation protocol.

- Two baselines are used:

  - **Base exit baseline** aggregate WFO OOS Sharpe = **1.130760**, CAGR = **0.350303**, MDD = **-0.370939**.

  - **Incumbent price-only churn model** (reconstructed from the frozen feature set / hyperparameters / p70 threshold rule) aggregate WFO OOS Sharpe = **1.194133**, CAGR = **0.384831**, MDD = **-0.358168**.

    - Reconstructed fold thresholds: F1=0.720880, F2=0.709776, F3=0.746120, F4=0.757253.

## Roles tested

- **one_shot**: at the trail-stop event, continue if the signal passes; then ignore later trail signals until trend exit or forced expiry `H=16`.

- **stateful**: same entry into continuation, but while in continuation the same signal is checked every bar; if it fails, exit next open (`guard_exit`).

- **additive model**: price-only churn model + one extra signal, same elastic-net logistic family / hyperparameters, same p70 train-score threshold.

## Threshold rules

- **fixed_natural**: physically natural support threshold (`>= 0` for imbalance / normalized net-flow families, `>= 1` for volume-surprise family).

- **train_threshold**: train-only search over directions `{ge, le}` and fold-train deciles (plus `always` / `never`) selected by train-slice Sharpe.

## Headline result

- **14** simple signal policies beat the **base exit baseline** on aggregate WFO OOS Sharpe with `>= 3/4` positive folds.

- **0** simple signal policies beat the **incumbent price-only hold model** with both aggregate Sharpe improvement and `>= 3/4` positive folds.

- **0** additive one-signal extensions beat the **incumbent price-only hold model** with both aggregate Sharpe improvement and `>= 3/4` positive folds.

## Best simple policies vs base exit

| signal                      | measurement           | operator   | role     | rule_type       |   aggregate_sharpe |   delta_sharpe_vs_base_exit |   positive_folds_vs_base_exit |   positive_folds_vs_price_model |   aggregate_mdd |
|:----------------------------|:----------------------|:-----------|:---------|:----------------|-------------------:|----------------------------:|------------------------------:|--------------------------------:|----------------:|
| ema12_net_quote_norm_28     | net_quote_norm_28     | ema12      | stateful | train_threshold |            1.21625 |                   0.08549   |                             3 |                               1 |       -0.336275 |
| ema28_net_quote_norm_28     | net_quote_norm_28     | ema28      | stateful | train_threshold |            1.21122 |                   0.0804568 |                             3 |                               1 |       -0.315795 |
| ema12_imbalance_ratio_base  | imbalance_ratio_base  | ema12      | stateful | fixed_natural   |            1.20061 |                   0.0698528 |                             3 |                               1 |       -0.336646 |
| ema12_imbalance_ratio_quote | imbalance_ratio_quote | ema12      | stateful | fixed_natural   |            1.20061 |                   0.0698528 |                             3 |                               1 |       -0.336646 |
| ema12_net_quote_norm_28     | net_quote_norm_28     | ema12      | stateful | fixed_natural   |            1.19762 |                   0.0668556 |                             4 |                               1 |       -0.342735 |
| ema28_imbalance_ratio_quote | imbalance_ratio_quote | ema28      | stateful | fixed_natural   |            1.19348 |                   0.06272   |                             4 |                               2 |       -0.348281 |
| ema28_imbalance_ratio_base  | imbalance_ratio_base  | ema28      | stateful | fixed_natural   |            1.19348 |                   0.06272   |                             4 |                               2 |       -0.348281 |
| ema28_imbalance_ratio_quote | imbalance_ratio_quote | ema28      | one_shot | train_threshold |            1.19034 |                   0.0595777 |                             3 |                               2 |       -0.385861 |
| ema28_net_quote_norm_28     | net_quote_norm_28     | ema28      | stateful | fixed_natural   |            1.18609 |                   0.0553338 |                             3 |                               1 |       -0.3205   |
| ema28_imbalance_ratio_base  | imbalance_ratio_base  | ema28      | one_shot | train_threshold |            1.17922 |                   0.0484577 |                             3 |                               2 |       -0.385861 |
| imbalance_ratio_quote       | imbalance_ratio_quote | level      | one_shot | fixed_natural   |            1.1715  |                   0.0407436 |                             3 |                               1 |       -0.346154 |
| net_quote_norm_28           | net_quote_norm_28     | level      | one_shot | fixed_natural   |            1.1715  |                   0.0407436 |                             3 |                               1 |       -0.346154 |
| ema12_imbalance_ratio_base  | imbalance_ratio_base  | ema12      | one_shot | fixed_natural   |            1.17012 |                   0.0393559 |                             2 |                               1 |       -0.397576 |
| ema12_imbalance_ratio_quote | imbalance_ratio_quote | ema12      | one_shot | fixed_natural   |            1.17012 |                   0.0393559 |                             2 |                               1 |       -0.397576 |
| imbalance_ratio_base        | imbalance_ratio_base  | level      | one_shot | fixed_natural   |            1.16288 |                   0.0321235 |                             3 |                               1 |       -0.346154 |

## Best additive models vs incumbent price-only hold model

| signal                           | measurement           | operator   |   aggregate_sharpe |   delta_sharpe_vs_price |   positive_folds_vs_price |   avg_auc |   delta_avg_auc_vs_price |   avg_log_loss |   delta_avg_log_loss_vs_price |
|:---------------------------------|:----------------------|:-----------|-------------------:|------------------------:|--------------------------:|----------:|-------------------------:|---------------:|------------------------------:|
| ema28_vol_surprise_quote_28      | vol_surprise_quote_28 | ema28      |            1.20997 |             0.015839    |                         1 |  0.824719 |              0.0155812   |       0.554868 |                   0.00123192  |
| pos_count4_imbalance_ratio_quote | imbalance_ratio_quote | pos_count4 |            1.20158 |             0.0074475   |                         1 |  0.819404 |              0.0102664   |       0.546116 |                  -0.007521    |
| pos_count4_net_quote_norm_28     | net_quote_norm_28     | pos_count4 |            1.20158 |             0.0074475   |                         1 |  0.819404 |              0.0102664   |       0.546116 |                  -0.007521    |
| osc_12_28_imbalance_ratio_base   | imbalance_ratio_base  | osc_12_28  |            1.19449 |             0.000360149 |                         1 |  0.812753 |              0.00361502  |       0.543639 |                  -0.00999715  |
| osc_12_28_imbalance_ratio_quote  | imbalance_ratio_quote | osc_12_28  |            1.19449 |             0.000360149 |                         1 |  0.812753 |              0.00361502  |       0.543735 |                  -0.00990198  |
| pos_count4_vol_surprise_quote_28 | vol_surprise_quote_28 | pos_count4 |            1.19413 |             0           |                         0 |  0.808296 |             -0.000841751 |       0.552821 |                  -0.000815104 |
| ema28_imbalance_ratio_base       | imbalance_ratio_base  | ema28      |            1.19413 |             0           |                         0 |  0.802788 |             -0.00635027  |       0.556283 |                   0.00264615  |
| osc_12_28_vol_surprise_quote_28  | vol_surprise_quote_28 | osc_12_28  |            1.19413 |             0           |                         0 |  0.812565 |              0.00342713  |       0.553832 |                   0.000195595 |
| ema28_imbalance_ratio_quote      | imbalance_ratio_quote | ema28      |            1.19413 |             0           |                         0 |  0.802788 |             -0.00635027  |       0.556296 |                   0.00265994  |
| ema12_vol_surprise_quote_28      | vol_surprise_quote_28 | ema12      |            1.18918 |            -0.00495687  |                         0 |  0.821043 |              0.0119048   |       0.554064 |                   0.000427765 |
| ema28_net_quote_norm_28          | net_quote_norm_28     | ema28      |            1.1874  |            -0.00673705  |                         0 |  0.79189  |             -0.0172479   |       0.554647 |                   0.00101055  |
| ema12_net_quote_norm_28          | net_quote_norm_28     | ema12      |            1.18477 |            -0.00936456  |                         0 |  0.802    |             -0.00713764  |       0.551075 |                  -0.00256148  |
| pos_count4_imbalance_ratio_base  | imbalance_ratio_base  | pos_count4 |            1.1828  |            -0.0113358   |                         1 |  0.819404 |              0.0102664   |       0.547008 |                  -0.00662902  |
| net_quote_norm_28                | net_quote_norm_28     | level      |            1.18207 |            -0.0120608   |                         1 |  0.777156 |             -0.0319817   |       0.555159 |                   0.00152254  |
| vol_surprise_quote_28            | vol_surprise_quote_28 | level      |            1.18207 |            -0.0120608   |                         1 |  0.806876 |             -0.00226221  |       0.546338 |                  -0.00729808  |

## Interpretation

- **Best standalone role = stateful guard**, not one-shot continuation gate. The strongest family is **normalized net quote flow** (`net_quote_norm_28`) or its smoothed EMAs. Those rules only continue a small subset of episodes and then require the signal to stay supportive during continuation.

- **Best natural rule** (no threshold tuning) is close to: `continue if EMA12(net_quote_norm_28) >= 0`, then exit continuation as soon as it drops below zero. Aggregate WFO OOS Sharpe = **1.197615** vs base-exit **1.130760**.

- **Best train-threshold simple rule** is `stateful EMA12(net_quote_norm_28)` with fold-selected thresholds clustered just below zero. Aggregate WFO OOS Sharpe = **1.216250**; however it only beats the incumbent price-only model in **1/4 folds**.

- **Volume surprise** carries some descriptive information at the episode level, but it does not translate into a robust hold policy. It neither produces a strong simple policy nor a robust additive gain over the incumbent model.

- **Base-vs-quote ratio duplication remains real** here as well: imbalance-base and imbalance-quote variants behave nearly identically in hold context.

- The incumbent price-only hold model is already strong. Secondary volume signals can improve **base exit**, but they do **not** robustly improve the incumbent hold model under this methodology.

## Practical conclusion

1. If the system had **no** hold model, the least-wrong secondary-signal use would be a **stateful continuation guard** based on smoothed normalized net flow or smoothed imbalance, not a one-shot hard gate and not a volume-surprise veto.

2. With the incumbent price-only hold model already in place, these secondary volume signals look **mostly redundant** at the policy level. They do not pass the same robustness bar against the incumbent.

3. Therefore, the current evidence supports: **keep secondary volume signals out of the promoted hold actuator unless they are part of a new model class / label / role that can beat the incumbent in fold-consistent OOS tests**.

## Notes

- The reconstructed price-only hold baseline closely matches the frozen winner WFO anchors, which supports the validity of this hold-context research protocol.

- Episode-level descriptive metrics are included separately because some signals improve churn classification or descriptive AUC without producing policy-level Sharpe gains.
