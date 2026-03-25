# Executive summary

Primary baseline: **`VDO > 0`** with locked base exit.

What was tested:
- **94** natural / structural entry rules
- **16** train-threshold one-signal ceiling tests
- Same 4-fold expanding WFO OOS protocol as the prior entry study

## Winner

**`weakvdo_q0.5_activity_and_fresh_imb`**

Logic:
- keep `VDO > 0` as the core gate
- define `weak_vdo_thr` as the **median positive VDO** on the fold's train slice (core-active bars only)
- if `VDO > weak_vdo_thr`, enter normally
- if `0 < VDO <= weak_vdo_thr`, enter **only if**:
  - `EMA12(vol_surprise_quote_28) >= 1`
  - `EMA28(imbalance_ratio_base) <= 0`

OOS result:
- Sharpe: **1.374084** vs baseline **1.130760**
- CAGR: **0.427156** vs **0.350303**
- MDD: **-0.273367** vs **-0.370939**
- Positive folds vs baseline: **4/4**
- OOS trades: **104** vs **118**

## What this means

The extra entry information is real, but its correct role is **bounded conditional veto**, not:
- replacing VDO with another standalone signal
- global hard-AND confirmation
- rescue-heavy logic
- threshold tuning around zero

A key control:
- `VDO > 0 AND activity AND freshness` globally gives Sharpe **1.244475**
- the **bounded** weak-VDO version gives **1.374084**

So boundedness is not cosmetic; it is the whole point.

## Secondary findings

- Best weak-negative rescue: `weakneg_q0.5_osc_12_28_net_quote_norm_28`
  - Sharpe **1.152770**
  - positive folds **4/4**
  - real, but much smaller than the veto winner

- Best train-threshold one-signal veto:
  - `train_veto_ema28_net_quote_norm_28`
  - Sharpe **1.373652**
  - only **2/4** positive folds
  - looks extractive, not robust

## Mechanism

Direct OOS comparison vs baseline shows **39** direct veto events:
- **10 full vetoes**: baseline trades were **all losers**
- **29 delays**: candidate re-entered later by about **10.6 bars** on average

So the winning rule works by:
1. removing a small set of pure junk weak-VDO entries
2. retiming a larger set of weak early entries


## Caveat

A frozen approximation of the winner with `weak_vdo_thr = 0.006481` does **not** beat the baseline on the older pre-2021 training era. So this looks like a later-epoch improvement inside the validated OOS protocol, not a universal full-history law.
