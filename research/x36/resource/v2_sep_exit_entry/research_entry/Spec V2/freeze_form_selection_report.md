# Freeze-form selection for `weak_vdo_thr`

## Decision
Chosen deployment freeze form: **Direction A — frozen approximation**.

Chosen threshold: **`weak_vdo_thr = 0.0065`**.

This is the 4-decimal rounding of the causal pre-live median:
`median(VDO | core_on, regime_ok, VDO>0, train_end=2021-06-30) = 0.00648105072393846`.

The rounded constant is **decision-equivalent on the study sample** to the exact first-train median:
- identical aggregate OOS metrics
- identical trade count (**104**)
- identical fold-level Sharpe vector
- lower implementation complexity

## Why A beats B

### A. Fixed threshold
`weak_vdo_thr = 0.0065`

- Aggregate OOS Sharpe: **1.340410**
- CAGR: **0.412714**
- MDD: **-0.285618**
- Trades: **104**
- Exposure: **0.374511**
- Positive folds vs baseline: **3/4**

Fold Sharpe:
- Fold 1: **1.119693**
- Fold 2: **1.507544**
- Fold 3: **1.875347**
- Fold 4: **0.322236**

### Best B found in the coarse online grid
Trailing median over the **last 2000 positive-core bars**

- Aggregate OOS Sharpe: **1.265291**
- CAGR: **0.386799**
- MDD: **-0.317859**
- Trades: **106**
- Exposure: **0.377543**
- Positive folds vs baseline: **3/4**

Fold Sharpe:
- Fold 1: **0.929356**
- Fold 2: **1.478766**
- Fold 3: **1.882109**
- Fold 4: **0.322236**

### Direct read
A wins on:
- higher OOS Sharpe: **+0.075119**
- higher CAGR: **+0.025916**
- lower drawdown: **+0.032241** (less negative is better)
- fewer trades: **104 vs 106**
- lower complexity: hard-coded constant vs rolling stateful estimator

## Robustness comparison

### Bootstrap
Paired circular block bootstrap on stitched OOS bar returns.

A (`0.0065`) vs baseline:
|   block_len |   mean_delta_sharpe |   p05_delta_sharpe |   p50_delta_sharpe |   p95_delta_sharpe |   prob_delta_gt0 |
|------------:|--------------------:|-------------------:|-------------------:|-------------------:|-----------------:|
|          24 |            0.209231 |        -0.0318861  |           0.203195 |           0.463184 |           0.926  |
|          72 |            0.208379 |        -0.0019456  |           0.204739 |           0.427053 |           0.948  |
|         144 |            0.211187 |         0.00599922 |           0.204951 |           0.437756 |           0.9555 |
|         288 |            0.203673 |         0.00669186 |           0.198553 |           0.427986 |           0.959  |

Best B (`2000`) vs baseline:
|   block_len |   mean_delta_sharpe |   p05_delta_sharpe |   p50_delta_sharpe |   p95_delta_sharpe |   prob_delta_gt0 |
|------------:|--------------------:|-------------------:|-------------------:|-------------------:|-----------------:|
|          24 |            0.132024 |         -0.0954316 |           0.133513 |           0.363321 |            0.823 |
|          72 |            0.132121 |         -0.0776886 |           0.133854 |           0.347437 |            0.838 |
|         144 |            0.126348 |         -0.0780301 |           0.124323 |           0.338378 |            0.84  |
|         288 |            0.130339 |         -0.0569285 |           0.126709 |           0.322746 |            0.874 |

A vs B directly:
|   block_len |   mean_delta_sharpe |   p05_delta_sharpe |   p50_delta_sharpe |   p95_delta_sharpe |   prob_delta_gt0 |
|------------:|--------------------:|-------------------:|-------------------:|-------------------:|-----------------:|
|          24 |           0.0741079 |         -0.0599263 |          0.0678718 |           0.227277 |           0.786  |
|          72 |           0.0727847 |         -0.0522455 |          0.0623965 |           0.235322 |           0.785  |
|         144 |           0.0738719 |         -0.0450216 |          0.0639802 |           0.234354 |           0.7935 |
|         288 |           0.0783043 |         -0.0361458 |          0.0678984 |           0.230232 |           0.8235 |

Read:
- A has materially higher `prob_delta_gt0` than B against the baseline.
- A also beats B directly in about **79% to 82%** of bootstrap resamples depending on block length.

### Cost sweep
|   side_cost_bps |   baseline_sharpe |   A_sharpe |   B_sharpe |   A_delta_vs_base |   B_delta_vs_base |   A_positive_folds_vs_base |   B_positive_folds_vs_base |
|----------------:|------------------:|-----------:|-----------:|------------------:|------------------:|---------------------------:|---------------------------:|
|             0   |          1.33603  | 1.53232    |  1.45899   |          0.196298 |          0.122968 |                          3 |                          3 |
|             2.5 |          1.29503  | 1.49403    |  1.42032   |          0.198999 |          0.125299 |                          3 |                          3 |
|             5   |          1.254    | 1.45568    |  1.38162   |          0.201686 |          0.127621 |                          3 |                          3 |
|             7.5 |          1.21294  | 1.41729    |  1.34287   |          0.204356 |          0.129934 |                          3 |                          3 |
|            10   |          1.17186  | 1.37887    |  1.3041    |          0.207011 |          0.132237 |                          3 |                          3 |
|            12.5 |          1.13076  | 1.34041    |  1.26529   |          0.209651 |          0.134531 |                          3 |                          3 |
|            15   |          1.08965  | 1.30192    |  1.22646   |          0.212274 |          0.136816 |                          3 |                          3 |
|            20   |          1.00739  | 1.22486    |  1.14875   |          0.217471 |          0.141355 |                          3 |                          3 |
|            25   |          0.925128 | 1.14773    |  1.07098   |          0.2226   |          0.145852 |                          3 |                          3 |
|            30   |          0.842886 | 1.07055    |  0.993193  |          0.227661 |          0.150307 |                          3 |                          3 |
|            35   |          0.760699 | 0.99335    |  0.915415  |          0.232651 |          0.154716 |                          3 |                          3 |
|            40   |          0.678596 | 0.916166   |  0.837676  |          0.237569 |          0.159079 |                          4 |                          3 |
|            50   |          0.514775 | 0.761959   |  0.682436  |          0.247184 |          0.167661 |                          4 |                          3 |
|            75   |          0.108869 | 0.378749   |  0.297085  |          0.269881 |          0.188217 |                          4 |                          3 |
|           100   |         -0.288978 | 0.00162406 | -0.0815851 |          0.290602 |          0.207393 |                          4 |                          4 |

Read:
- A beats the baseline at every tested cost point from **0 to 100 bps**.
- B also beats baseline on aggregate Sharpe, but by a smaller margin.
- Across the cost sweep, A keeps a larger Sharpe delta than B at every cost point.

## Why the online form underperforms
The research winner's fold medians only move in a narrow band:
- fold 1: **0.006481**
- fold 2: **0.005800**
- fold 3: **0.005663**
- fold 4: **0.006064**

That drift exists, but it is modest. In contrast, trailing online windows move around more aggressively inside folds.

Threshold path summary:
| series                     |   fold |   start_threshold |   median_threshold_within_fold |   end_threshold |   min_threshold |   max_threshold |   std_threshold |
|:---------------------------|-------:|------------------:|-------------------------------:|----------------:|----------------:|----------------:|----------------:|
| research_fold_train_median |      1 |        0.00648105 |                     0.00648105 |      0.00648105 |      0.00648105 |      0.00648105 |     0           |
| research_fold_train_median |      2 |        0.00579975 |                     0.00579975 |      0.00579975 |      0.00579975 |      0.00579975 |     0           |
| research_fold_train_median |      3 |        0.00566306 |                     0.00566306 |      0.00566306 |      0.00566306 |      0.00566306 |     0           |
| research_fold_train_median |      4 |        0.00606372 |                     0.00606372 |      0.00606372 |      0.00606372 |      0.00606372 |     0           |
| A_fixed_0065               |      1 |        0.0065     |                     0.0065     |      0.0065     |      0.0065     |      0.0065     |     2.60209e-18 |
| A_fixed_0065               |      2 |        0.0065     |                     0.0065     |      0.0065     |      0.0065     |      0.0065     |     1.73472e-18 |
| A_fixed_0065               |      3 |        0.0065     |                     0.0065     |      0.0065     |      0.0065     |      0.0065     |     0           |
| A_fixed_0065               |      4 |        0.0065     |                     0.0065     |      0.0065     |      0.0065     |      0.0065     |     1.73472e-18 |
| B_online_poscore_2000      |      1 |        0.00648105 |                     0.00640114 |      0.00569734 |      0.00569734 |      0.00654968 |     0.000248851 |
| B_online_poscore_2000      |      2 |        0.00569734 |                     0.0050298  |      0.00505232 |      0.00489213 |      0.00569734 |     0.000152685 |
| B_online_poscore_2000      |      3 |        0.00505232 |                     0.00517311 |      0.00557126 |      0.00501561 |      0.00564547 |     0.000182799 |
| B_online_poscore_2000      |      4 |        0.00557126 |                     0.00603783 |      0.00610465 |      0.00557126 |      0.00611355 |     0.000136851 |
| B_online_expanding         |      1 |        0.00648105 |                     0.00640114 |      0.00579975 |      0.00579975 |      0.00654968 |     0.000220095 |
| B_online_expanding         |      2 |        0.00579975 |                     0.00541912 |      0.00566306 |      0.00519759 |      0.00579975 |     0.000171726 |
| B_online_expanding         |      3 |        0.00566306 |                     0.00585956 |      0.00606372 |      0.00566306 |      0.0060673  |     0.000110356 |
| B_online_expanding         |      4 |        0.00606372 |                     0.00627019 |      0.0063037  |      0.00606372 |      0.00631208 |     6.18233e-05 |

Practical read:
- B adapts, but over-adapts.
- The OOS sample does not reward that extra motion.
- The distribution drift is not large enough to pay for online complexity.

## Why not freeze at `0.0060`
`0.0060` is the strongest ex-post simple fixed approximation on pure fold-consistency:
- aggregate Sharpe **1.225367**
- positive folds vs baseline **4/4**

But it was **not** chosen because:
1. it is not causally anchored to a single pre-live estimate,
2. it is weaker on aggregate Sharpe than `0.0065`,
3. its bootstrap edge vs baseline is materially weaker than `0.0065`.

So the final freeze principle is:
- prefer the **causal pre-live anchor**
- round it to a simple deployable constant
- keep the implementation deterministic

## Relationship to the research winner
`0.0065` stays very close to the original fold-adaptive research winner.

Entry-time comparison:
|   common_entries_A_vs_research |   A_only_entries |   research_only_entries |   common_entries_B_vs_research |   B_only_entries |   research_only_entries_vs_B |
|-------------------------------:|-----------------:|------------------------:|-------------------------------:|-----------------:|-----------------------------:|
|                            101 |                3 |                       3 |                            102 |                4 |                            2 |

Interpretation:
- fixed `0.0065` shares **101 / 104** entry timestamps with the research winner
- only **3** entries are retimed relative to the fold-adaptive object
- so the freeze cost is small, while deployment complexity drops sharply

## Final recommendation
Freeze the entry rule with:

- `weak_vdo_thr = 0.0065`
- keep the bounded conditional veto structure unchanged
- do **not** use causal online re-estimation for deployment

## Caveats that still apply
1. **Post-2021 structure caveat**  
   This should still be read as a post-2021 OOS improvement, not as a timeless full-history law.

2. **Exit coupling caveat**  
   Exit is still the locked base exit here. If exit later changes, especially toward the same activity / flow family, entry must be re-validated.

3. **No threshold optimization around 0 afterwards**  
   The main lesson remains unchanged: the edge is the bounded weak-VDO veto motif itself, not endless threshold massage.
