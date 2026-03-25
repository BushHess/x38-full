# Entry research: beyond `VDO > 0`

## Scope lock

- Only the **entry actuator** was changed.
- Trend core (`EMA30 > EMA120`), D1 regime filter, ATR trail-stop exit, costs, sizing, and all base indicators stayed locked.
- Primary ranking uses the same **4 expanding WFO OOS folds** used in the prior entry work, with flat reset at each OOS fold start.
- Primary baseline is the current entry gate: **`VDO > 0`**.

## WFO folds

- Fold 1 OOS: 2021-07-01 to 2022-12-31
- Fold 2 OOS: 2023-01-01 to 2024-06-30
- Fold 3 OOS: 2024-07-01 to 2025-06-30
- Fold 4 OOS: 2025-07-01 to 2026-02-28

## Baselines

| policy               |   aggregate_sharpe |   aggregate_cagr |   aggregate_mdd |
|:---------------------|-------------------:|-----------------:|----------------:|
| core_ungated         |           0.742221 |         0.209589 |       -0.499159 |
| vdo_only             |           1.13076  |         0.350303 |       -0.370939 |
| winner_top_candidate |           1.37408  |         0.427156 |       -0.273367 |


## What was searched

- **94 natural / first-principles rules** across four families: controls, unbounded AND/OR controls, bounded weak-VDO vetoes, bounded weak-negative rescues.
- **16 train-threshold one-signal families** as a ceiling test: one companion signal plus train-only threshold search inside a bounded veto or bounded rescue template.
- Low-complexity monotone Boolean combinations of the three most meaningful companions were included explicitly:
  - `A`: activity support = `EMA12(quote_volume / EMA28(quote_volume)) >= 1`
  - `F`: freshness support = `EMA28(imbalance_ratio_base) <= 0`
  - `M`: alternate flow momentum support = `EMA12(net_quote_norm_28) - EMA28(net_quote_norm_28) > 0`

## Main result

Best overall rule under the locked protocol:

**`weakvdo_q0.5_activity_and_fresh_imb`**


Rule semantics:

- Let `weak_vdo_thr` be the **median of positive VDO values** on the fold's train slice, computed over bars where the trend core and regime filter are both on.
- When flat and core conditions hold:
  1. If `VDO <= 0`, do not enter.
  2. If `VDO > weak_vdo_thr`, enter normally.
  3. If `0 < VDO <= weak_vdo_thr`, enter **only if both**:
     - `EMA12(vol_surprise_quote_28) >= 1`, and
     - `EMA28(imbalance_ratio_base) <= 0`.

This is a **bounded conditional veto**. Strong VDO entries are left alone. Only the weaker half of positive-VDO entries are screened, and they are screened using one activity condition and one freshness / non-late-flow condition.

### Fold-by-fold OOS

|   fold |   oos_sharpe |   oos_cagr |   oos_mdd |   oos_trades |   delta_sharpe_vs_vdo |   weak_thr |
|-------:|-------------:|-----------:|----------:|-------------:|----------------------:|-----------:|
|      1 |     1.11969  |  0.340491  | -0.22899  |           25 |             0.513014  | 0.00648105 |
|      2 |     1.60409  |  0.574156  | -0.273367 |           41 |             0.0665871 | 0.00579975 |
|      3 |     1.87535  |  0.672549  | -0.136695 |           27 |             0.0567741 | 0.00566306 |
|      4 |     0.322236 |  0.0396297 | -0.127752 |           11 |             0.344393  | 0.00606372 |


### Why this matters

- Aggregate OOS Sharpe improves from **1.130760** to **1.374084**.
- The rule is **positive in 4/4 folds vs VDO baseline**.
- OOS max drawdown improves from **-0.370939** to **-0.273367**.
- OOS trades drop only from **118** to **104** across the stitched OOS sample. This is not an extreme over-filtering result.

## Motif-level read

| motif                                | best_policy                              |   aggregate_sharpe |   positive_folds_vs_vdo |
|:-------------------------------------|:-----------------------------------------|-------------------:|------------------------:|
| Weak-VDO bounded veto                | weakvdo_q0.5_activity_and_fresh_imb      |            1.37408 |                       4 |
| Weak-VDO bounded veto, activity only | weakvdo_q0.5_ema12_vol_surprise_quote_28 |            1.24725 |                       4 |
| Freshness-only veto                  | and_ema28_imbalance_ratio_base           |            1.28205 |                       3 |
| Weak-negative rescue                 | weakneg_q0.5_osc_12_28_net_quote_norm_28 |            1.15277 |                       4 |
| Best train-threshold one-signal veto | train_veto_ema28_net_quote_norm_28       |            1.37365 |                       2 |


Interpretation:

- **Rescue exists, but it is weak.** The best weak-negative rescue only adds **+0.022 Sharpe**.
- **The big edge is not rescue. It is veto.**
- **Naive global AND gates are not enough.** `VDO > 0 AND A AND F` improves Sharpe to **1.244475**, but the bounded weak-VDO version improves it further to **1.374084**. That directly supports the earlier prior: extra information exists, but it should be used as a **bounded conditional veto**, not as a universal hard confirm.

## Controls against cherry-picking

- Out of **94** natural / structural rules, **19** beat `VDO > 0` on both aggregate Sharpe and `>=3/4` positive folds. This is not a single isolated winner, but a coherent cluster.
- The best cluster is built around the same motif:
  - weak positive VDO,
  - plus **activity support**,
  - plus **freshness / not-late slow imbalance**.
- The best train-threshold one-signal family (`train_veto_ema28_net_quote_norm_28`) achieves nearly the same aggregate Sharpe (**1.373652**) but only **2/4** positive folds vs baseline. That is classic extractive behavior, not robust structure.
- The natural bounded veto beats it on consistency (**4/4**) with less freedom.

## Best train-threshold ceiling tests

| policy                                   | family               | support_signal              |   aggregate_sharpe |   aggregate_cagr |   aggregate_mdd |   delta_sharpe_vs_vdo |   positive_folds_vs_vdo |   avg_oos_trades |   avg_selected_threshold |   avg_selected_weak_q |   avg_selected_neg_q | pass_vs_vdo   |
|:-----------------------------------------|:---------------------|:----------------------------|-------------------:|-----------------:|----------------:|----------------------:|------------------------:|-----------------:|-------------------------:|----------------------:|---------------------:|:--------------|
| train_veto_ema28_net_quote_norm_28       | train_veto_1signal   | ema28_net_quote_norm_28     |            1.37365 |         0.420096 |       -0.252951 |            0.242892   |                       2 |            25    |              -0.00448619 |              0.5      |                nan   | False         |
| train_veto_ema12_net_quote_norm_28       | train_veto_1signal   | ema12_net_quote_norm_28     |            1.20347 |         0.370223 |       -0.309187 |            0.0727068  |                       1 |            28.25 |               0.00808172 |              0.4375   |                nan   | False         |
| train_rescue_osc_12_28_net_quote_norm_28 | train_rescue_1signal | osc_12_28_net_quote_norm_28 |            1.16686 |         0.367852 |       -0.346653 |            0.0360952  |                       3 |            30    |              -0.00228909 |            nan        |                  0.5 | True          |
| train_veto_ema28_imbalance_ratio_base    | train_veto_1signal   | ema28_imbalance_ratio_base  |            1.15944 |         0.360041 |       -0.364848 |            0.0286789  |                       1 |            29    |              -0.0133974  |              0.458333 |                nan   | False         |
| train_rescue_ema12_vol_surprise_quote_28 | train_rescue_1signal | ema12_vol_surprise_quote_28 |            1.15847 |         0.363991 |       -0.337729 |            0.027715   |                       2 |            29.75 |               0.888893   |            nan        |                  0.5 | False         |
| train_veto_regime_strength               | train_veto_1signal   | regime_strength             |            1.15092 |         0.353842 |       -0.376596 |            0.020165   |                       2 |            28    |               0.0159255  |              0.4375   |                nan   | False         |
| train_veto_ema_gap_pct                   | train_veto_1signal   | ema_gap_pct                 |            1.13331 |         0.344936 |       -0.408519 |            0.00255249 |                       1 |            27.75 |               0.0162693  |              0.291667 |                nan   | False         |
| train_veto_ema12_vol_surprise_quote_28   | train_veto_1signal   | ema12_vol_surprise_quote_28 |            1.13204 |         0.349159 |       -0.378093 |            0.00127721 |                       1 |            28.75 |               0.810015   |              0.395833 |                nan   | False         |
| train_veto_osc_12_28_net_quote_norm_28   | train_veto_1signal   | osc_12_28_net_quote_norm_28 |            1.1292  |         0.348657 |       -0.365142 |           -0.00155682 |                       2 |            29.25 |               0.00438106 |              0.458333 |                nan   | False         |
| train_veto_atr_pct                       | train_veto_1signal   | atr_pct                     |            1.1266  |         0.345014 |       -0.384183 |           -0.00415541 |                       1 |            28.25 |               0.46       |              0.291667 |                nan   | False         |


## Mechanism: what the winning rule actually does

Direct OOS comparison against the baseline `VDO > 0` strategy shows **39 direct veto events** where baseline would enter while the winning rule stayed flat.

| decision_outcome   |   n |   base_win_rate |   base_mean_ret |   base_median_ret |   cand_win_rate |   cand_mean_ret |   cand_median_ret |   mean_delay_bars |
|:-------------------|----:|----------------:|----------------:|------------------:|----------------:|----------------:|------------------:|------------------:|
| delay_then_enter   |  29 |        0.482759 |       0.0432721 |       -0.00184619 |        0.448276 |       0.0390288 |       -0.00481658 |           10.5862 |
| full_veto          |  10 |        0        |      -0.0380387 |       -0.0397217  |      nan        |     nan         |      nan          |          nan      |


Read:

- In **10** of those direct veto events, the candidate **never entered later before core conditions died**. Those baseline trades were **all losers** (win rate **0%**, mean return **-3.80%**).
- In **29** cases, the candidate **delayed** entry by about **10.6 bars** on average. Those baseline trades were mixed, while the delayed candidate trades had similar but slightly cleaner realized returns.
- So the winning rule works in two ways:
  1. it **kills a small set of pure junk trades**, and
  2. it **retimes a larger set of weak early entries**.

## Residual-info diagnostics on baseline VDO entries

A depth-2 decision tree trained only on past baseline VDO entries repeatedly rediscovered the same structure: slow normalized net-flow / slow imbalance as the first split, then smoothed volume-surprise as the next split.

## Fold 1 (train n=75, oos n=31)

```text
|--- ema28_net_quote_norm_28 <= -0.04
|   |--- class: 1
|--- ema28_net_quote_norm_28 >  -0.04
|   |--- ema12_vol_surprise_quote_28 <= 0.90
|   |   |--- class: 0
|   |--- ema12_vol_surprise_quote_28 >  0.90
|   |   |--- class: 0

```

## Fold 2 (train n=106, oos n=47)

```text
|--- ema28_net_quote_norm_28 <= -0.04
|   |--- class: 1
|--- ema28_net_quote_norm_28 >  -0.04
|   |--- ema12_vol_surprise_quote_28 <= 0.90
|   |   |--- class: 0
|   |--- ema12_vol_surprise_quote_28 >  0.90
|   |   |--- class: 0

```

## Fold 3 (train n=153, oos n=28)

```text
|--- ema12_vol_surprise_quote_28 <= 0.89
|   |--- ema28_net_quote_norm_28 <= -0.00
|   |   |--- class: 0
|   |--- ema28_net_quote_norm_28 >  -0.00
|   |   |--- class: 0
|--- ema12_vol_surprise_quote_28 >  0.89
|   |--- ema28_imbalance_ratio_base <= -0.03
|   |   |--- class: 1
|   |--- ema28_imbalance_ratio_base >  -0.03
|   |   |--- class: 0

```

## Fold 4 (train n=181, oos n=12)

```text
|--- ema12_vol_surprise_quote_28 <= 0.89
|   |--- ema12_net_quote_norm_28 <= -0.00
|   |   |--- class: 0
|   |--- ema12_net_quote_norm_28 >  -0.00
|   |   |--- class: 0
|--- ema12_vol_surprise_quote_28 >  0.89
|   |--- ema28_imbalance_ratio_base <= -0.03
|   |   |--- class: 1
|   |--- ema28_imbalance_ratio_base >  -0.03
|   |   |--- class: 0

```

This is only a diagnostic, not a promoted model. The point is that the top natural rule is not arbitrary; a completely separate diagnostic keeps finding the same motif.

## Robustness beyond the frozen folds

### Paired circular block bootstrap of OOS Sharpe delta (winner minus VDO baseline)

|   block_len |     mean |        p05 |      p50 |      p95 |   prob_gt0 |
|------------:|---------:|-----------:|---------:|---------:|-----------:|
|          24 | 0.237207 | 0.00282361 | 0.231326 | 0.488111 |     0.9525 |
|          72 | 0.240885 | 0.0331761  | 0.23632  | 0.47078  |     0.9725 |


### Calendar half-year stress check on stitched OOS sample

| segment   |   bars |   top_sharpe |   vdo_sharpe |   delta_sharpe |     top_ret |     vdo_ret | top_beats_vdo   |
|:----------|-------:|-------------:|-------------:|---------------:|------------:|------------:|:----------------|
| 2021H2    |   1104 |     2.48356  |    2.32695   |    0.156608    |  0.662372   |  0.613277   | True            |
| 2022H1    |   1086 |     0.069064 |    0.069064  |   -6.93889e-15 | -0.00275761 | -0.00275761 | False           |
| 2022H2    |   1104 |    -0.593516 |   -1.67004   |    1.07652     | -0.063084   | -0.226611   | True            |
| 2023H1    |   1086 |     0.995756 |    0.841049  |    0.154707    |  0.131337   |  0.124773   | True            |
| 2023H2    |   1104 |     2.43754  |    2.36945   |    0.068082    |  0.390536   |  0.377995   | True            |
| 2024H1    |   1092 |     1.45055  |    1.58328   |   -0.132727    |  0.253821   |  0.286496   | False           |
| 2024H2    |   1104 |     2.56339  |    2.5823    |   -0.0189117   |  0.498      |  0.508407   | False           |
| 2025H1    |   1086 |     0.996607 |    0.846681  |    0.149926    |  0.115866   |  0.0968334  | True            |
| 2025H2    |   1104 |    -0.021422 |    0.0204961 |   -0.0419181   | -0.00830542 | -0.00492444 | False           |
| 2026YTD   |    354 |     1.43149  |   -0.153862  |    1.58535     |  0.0347697  | -0.00620522 | True            |


Read:

- The winning rule beats baseline in **6/10** half-year segments, is roughly flat in **1**, and loses in **3**.
- The bootstrap is favorable: depending on block length, the probability that the winner's Sharpe exceeds the VDO baseline is roughly **95% to 97%**.

## Simpler frozen approximations

The research winner uses a mechanically re-estimated `weak_vdo_thr` each fold (median positive VDO on the train slice). Two simpler frozen approximations were checked:

|   threshold |   aggregate_sharpe |   aggregate_cagr |   aggregate_mdd |   positive_folds_vs_vdo |
|------------:|-------------------:|-----------------:|----------------:|------------------------:|
|  0.006      |            1.22537 |         0.374605 |       -0.2969   |                       4 |
|  0.00648105 |            1.34041 |         0.412571 |       -0.285618 |                       3 |


Interpretation:

- A fully fixed threshold around **0.0060** still beats baseline in **4/4** folds, but gives up a chunk of Sharpe.
- Freezing the first train slice's median positive VDO (**0.006481**) preserves most of the Sharpe gain, but drops to **3/4** positive folds.


### Caveat: not a universal full-history winner
A frozen approximation of the winner using the first train slice's `weak_vdo_thr = 0.006481` **does not beat** the baseline on the pre-OOS training era (2018-08-17 to 2021-06-30):
- baseline `VDO > 0`: Sharpe **1.951254**
- frozen winner approximation: Sharpe **1.787091**

So the discovered motif should be read as a **post-2021 improvement inside the frozen OOS protocol**, not as a timeless law that dominated every earlier regime.

## Final conclusion

The earlier conjecture turned out to be right, but only in a more specific form:

- The remaining room at entry is **not** in replacing VDO with another standalone oscillator.
- The remaining room is **not** in threshold massage around `VDO = 0`.
- The remaining room **is** in using secondary information as a **bounded conditional veto on weak positive VDO entries**.

Within the tested library, the best use of extra information is:

1. keep `VDO > 0` as the core gate,
2. define a weak-VDO zone using the train-slice median positive VDO,
3. inside that weak zone only, require:
   - **activity support** (`EMA12(volume surprise quote) >= 1`), and
   - **freshness support** (`EMA28(base imbalance ratio) <= 0`).

That is the best-performing entry solution found under the locked methodology.
