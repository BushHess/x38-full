# Recommended entry rule spec (research winner)

## Purpose
This is the highest-performing entry rule found under the locked entry-study methodology.

## Inputs
On each H4 bar close `t`:

- `ema_fast_t = EMA30(close)_t`
- `ema_slow_t = EMA120(close)_t`
- `regime_ok_t = D1_close_t > D1_EMA21_t`

### VDO core
Let:
- `taker_sell_base_t = volume_t - taker_buy_base_vol_t`
- `imbalance_ratio_base_t = (taker_buy_base_vol_t - taker_sell_base_t) / volume_t`
- `VDO_t = EMA12(imbalance_ratio_base)_t - EMA28(imbalance_ratio_base)_t`

### Secondary activity support
Let:
- `vol_surprise_quote_28_t = quote_volume_t / EMA28(quote_volume)_t`
- `activity_support_t = [ EMA12(vol_surprise_quote_28)_t >= 1.0 ]`

### Secondary freshness support
Let:
- `freshness_support_t = [ EMA28(imbalance_ratio_base)_t <= 0.0 ]`

## Weak-VDO boundary
For each WFO fold, compute on the **train slice only**:

- collect all bars where:
  - `ema_fast > ema_slow`
  - `regime_ok == True`
  - `VDO > 0`

- define:
  - `weak_vdo_thr = median(VDO on those bars)`

In the frozen 4-fold research run, the selected values were:

|   fold |   oos_sharpe |   oos_cagr |   oos_mdd |   oos_trades |   delta_sharpe_vs_vdo |   selected_weak_vdo_median |
|-------:|-------------:|-----------:|----------:|-------------:|----------------------:|---------------------------:|
|      1 |     1.11969  |  0.340491  | -0.22899  |           25 |             0.513014  |                 0.00648105 |
|      2 |     1.60409  |  0.574156  | -0.273367 |           41 |             0.0665871 |                 0.00579975 |
|      3 |     1.87535  |  0.672549  | -0.136695 |           27 |             0.0567741 |                 0.00566306 |
|      4 |     0.322236 |  0.0396297 | -0.127752 |           11 |             0.344393  |                 0.00606372 |

## Entry decision
When flat, at H4 close bar `t`, schedule a full long entry at the next open `t+1` if and only if:

1. `ema_fast_t > ema_slow_t`
2. `regime_ok_t == True`
3. `VDO_t > 0`
4. and additionally:
   - if `VDO_t > weak_vdo_thr`: **allow**
   - else (`0 < VDO_t <= weak_vdo_thr`): allow **only if**
     - `activity_support_t == True`
     - `freshness_support_t == True`

Equivalent compact form:

`enter_t = core_t AND [ VDO_t > weak_vdo_thr OR (0 < VDO_t <= weak_vdo_thr AND activity_support_t AND freshness_support_t) ]`

Since `VDO_t > weak_vdo_thr` already implies `VDO_t > 0`, this can be written more simply as:

`enter_t = core_t AND [ (VDO_t > weak_vdo_thr) OR (0 < VDO_t <= weak_vdo_thr AND activity_support_t AND freshness_support_t) ]`

## Execution semantics
- All indicators use the closed bar `t`
- Entry fills at next bar open `t+1`
- No pyramiding
- Exit logic remains unchanged:
  - robust ATR trail-stop
  - EMA30 / EMA120 cross-down trend exit
- Costs remain unchanged:
  - 12.5 bps per side

## Simpler frozen approximations
Two lower-complexity approximations were also checked:
- fixed `weak_vdo_thr = 0.0060`: Sharpe **1.225367**, positive folds **4/4**
- fixed `weak_vdo_thr = 0.006481` (first-train median): Sharpe **1.340410**, positive folds **3/4**

Those are simpler, but the fold-adaptive median boundary remained the top performer under the locked protocol.
