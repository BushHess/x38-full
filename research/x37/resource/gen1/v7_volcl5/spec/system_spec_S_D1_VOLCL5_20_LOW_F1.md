# Spec 2 — System Specification for the frozen winner `S_D1_VOLCL5_20_LOW_F1`

## 1. Scope

This specification defines the final frozen trading system precisely enough to reimplement it from raw data and reproduce the saved outputs for the final leader. The system is native D1 only. The H4 file is part of the research process but is not used by the live signal logic of this final system.

## 2. Required input file and exact schema

Use the raw native D1 CSV with this exact schema:

| column | type | meaning |
|---|---|---|
| `symbol` | string | expected `BTCUSDT` |
| `interval` | string | expected `1d` on all rows |
| `open_time` | int64 epoch milliseconds UTC | day open timestamp |
| `close_time` | int64 epoch milliseconds UTC | day close timestamp |
| `open` | float64 | open price |
| `high` | float64 | high price |
| `low` | float64 | low price |
| `close` | float64 | close price |
| `volume` | float64 | base volume |
| `quote_volume` | float64 | quote volume |
| `num_trades` | int64 | trade count |
| `taker_buy_base_vol` | float64 | taker-buy base volume |
| `taker_buy_quote_vol` | float64 | taker-buy quote volume |

Expected parse rules:

- parse `open_time` and `close_time` from epoch milliseconds to timezone-aware UTC
- sort ascending by `open_time`, then `close_time`
- do not invent, fill, repair, or resample bars
- retain duplicate rows if they ever occur and log them; none were observed in the D1 file used for the final system

## 3. Time and bar conventions

- all timestamps are UTC
- D1 bar open is `00:00:00 UTC`
- D1 bar close is `23:59:59.999 UTC`
- no H4-to-D1 alignment is needed
- signal is computed from the **previous completed D1 bar**
- the next D1 open is the only execution price used
- there are no intrabar assumptions and no midpoint assumptions
- no rounding is applied to features, thresholds, positions, or returns

## 4. Exact signal definition

### 4.1 Primitive series

For D1 bar index `t`:

- `close_t` = D1 close on day `t`
- `logret_t = ln(close_t / close_(t-1))`

### 4.2 Rolling standard-deviation convention

Use **sample standard deviation** with `ddof=1`.

This convention is not optional. It is the only convention that exactly reproduces the saved discovery metrics for the frozen winner.

### 4.3 Feature formula

For every D1 bar `t` with sufficient history:

- `std5_t = sample_std(logret_(t-4) ... logret_t, ddof=1)`
- `std20_t = sample_std(logret_(t-19) ... logret_t, ddof=1)`
- `volcluster_5_20_t = std5_t / std20_t`

This requires 20 valid one-bar log returns, which means 21 close prices.

### 4.4 Binary signal on the completed bar

For completed D1 bar `t`:

- `signal_bar_t = 1` if `volcluster_5_20_t <= 1.0`
- `signal_bar_t = 0` if `volcluster_5_20_t > 1.0`
- `signal_bar_t = 0` when `volcluster_5_20_t` is `NaN`

The threshold mode is **fixed_one** and the tail is **low**.

## 5. Entry, hold, and exit state machine

For D1 open on day `t+1`:

- `position_(t+1) = signal_bar_t`

Equivalently:

- be **long** on day `t+1` if the completed D1 bar on day `t` has `volcluster_5_20 <= 1.0`
- be **flat** on day `t+1` if the completed D1 bar on day `t` has `volcluster_5_20 > 1.0`

Position direction is strictly **long-only / long-flat**.

Position sizing is exact and binary:

- `1.0` = 100% notional long
- `0.0` = flat

There is no leverage, no partial sizing, no pyramiding, and no separate regime gate.

## 6. Warmup and live start

- no live trading is allowed before `2020-01-01`
- earlier data may be used for feature warmup only
- if `open_time < 2020-01-01 00:00:00 UTC`, force `position = 0`
- if the previous completed bar does not yet have a valid `volcluster_5_20`, force `position = 0`

## 7. Cost model and realized-return formula

Cost model:

- `10 bps` per side
- `20 bps` round-trip

For each scored D1 bar `j`:

- `position_j ∈ {0,1}`
- `gross_return_j = open_(j+1) / open_j - 1`
- `turnover_cost_j = 0.001 * 1[position_j != position_(j-1)]`
- `realized_return_j = position_j * gross_return_j - turnover_cost_j`

Interpretation:

- entry day: you pay `0.001` at the entry open and then earn or lose the open-to-open market return while long
- hold day: you pay no cost and earn or lose the open-to-open market return while long
- exit day: you pay `0.001` at the exit open and, because you are flat for that interval, the day return is exactly `-0.001`

A completed trade PnL after cost is:

`Π(1 + realized_return_j over all days from entry day through exit day inclusive) - 1`

The terminal D1 bar with no next open is not scoreable and must be excluded from realized-return scoring.

## 8. Edge cases

Handle edge cases exactly this way:

- **Shortened H4 bars:** irrelevant to this final system because the system uses native D1 only.
- **Gaps between D1 bars:** none were observed. If one appears in future data, do not invent missing bars. Use the next available actual open for execution.
- **Missing data:** none were observed. If a missing value appears, do not invent data. The affected derived feature becomes `NaN` until enough valid history exists again.
- **Insufficient history:** before 20 valid log returns exist, `volcluster_5_20` is `NaN`, `signal_bar=0`, and `position=0`.
- **Duplicate rows:** none were observed in the D1 file. If duplicates appear, retain both rows and log them.
- **Zero-activity rows:** none were observed in the D1 file.
- **No next open on terminal bar:** exclude that last bar from realized-return scoring because `open_(j+1)` does not exist.

## 9. Reference pseudocode

```python
import numpy as np
import pandas as pd

def build_system(d1: pd.DataFrame) -> pd.DataFrame:
    d1 = d1.copy()
    d1["open_time"] = pd.to_datetime(d1["open_time"], unit="ms", utc=True)
    d1["close_time"] = pd.to_datetime(d1["close_time"], unit="ms", utc=True)
    d1 = d1.sort_values(["open_time", "close_time"]).reset_index(drop=True)

    d1["logret"] = np.log(d1["close"] / d1["close"].shift(1))
    d1["std5"] = d1["logret"].rolling(5, min_periods=5).std(ddof=1)
    d1["std20"] = d1["logret"].rolling(20, min_periods=20).std(ddof=1)
    d1["volcluster_5_20"] = d1["std5"] / d1["std20"]

    d1["signal_bar"] = (d1["volcluster_5_20"] <= 1.0).fillna(False).astype(int)

    d1["position"] = d1["signal_bar"].shift(1).fillna(0).astype(int)
    d1.loc[d1["open_time"] < pd.Timestamp("2020-01-01", tz="UTC"), "position"] = 0

    d1["prev_position"] = d1["position"].shift(1).fillna(0).astype(int)
    d1["next_open"] = d1["open"].shift(-1)

    d1["realized_return"] = (
        d1["position"] * (d1["next_open"] / d1["open"] - 1.0).fillna(0.0)
        - 0.001 * (d1["position"] != d1["prev_position"]).astype(int)
    )

    scored = d1[d1["next_open"].notna()].copy()
    return scored
```

## 10. Exact whole-system verification targets

A correct implementation reproduces this verification table for the frozen leader:

| segment       |   bars |   days |     cagr |   sharpe_daily |   max_drawdown |   trade_count_overlap_segment |   exposure |   total_return |
|:--------------|-------:|-------:|---------:|---------------:|---------------:|------------------------------:|-----------:|---------------:|
| discovery     |   1277 |   1277 | 0.708447 |       1.2668   |      -0.516179 |                           126 |   0.602976 |       5.50474  |
| holdout       |    458 |    458 | 0.262315 |       0.84405  |      -0.363689 |                            32 |   0.60262  |       0.339238 |
| reserve       |    531 |    531 | 0.292342 |       0.979103 |      -0.211357 |                            51 |   0.59322  |       0.451846 |
| pre_reserve   |   1735 |   1735 | 0.57727  |       1.17013  |      -0.516179 |                           157 |   0.602882 |       7.71139  |
| full_internal |   2266 |   2266 | 0.505322 |       1.12298  |      -0.516179 |                           208 |   0.600618 |      11.6476   |

These values were produced from the locked research outputs and are the acceptance targets for system-level verification.

## 11. Ten deterministic test vectors

Each test case below gives the exact rolling close window, the expected `volcluster_5_20` on the previous completed bar, the expected state at the next open, and—when applicable—the exact completed-trade PnL after cost.

#### Case 1

- `position_date_open_utc`: 2017-09-06 00:00:00 UTC
- `previous_completed_bar_utc`: 2017-09-05 00:00:00 UTC
- `close_window_count`: 20
- `close_window_ending_prev_bar`: `[4285.08, 4108.37, 4139.98, 4086.29, 4016.0, 4040.0, 4114.01, 4316.01, 4280.68, 4337.44, 4310.01, 4386.69, 4587.48, 4555.14, 4724.89, 4834.91, 4472.14, 4509.08, 4100.11, 4366.47]`
- `volcluster_5_20_prev_bar`: `NaN`
- `signal_for_position_date`: `NO_SIGNAL`
- `position_at_open`: `0`
- `state_change_at_open`: `no_signal`
- `entry_price_if_state_change`: `none`
- `exit_price_if_state_change`: `none`
- `completed_trade_entry_open_utc`: `none`
- `completed_trade_exit_open_utc`: `none`
- `completed_trade_pnl_after_cost`: `none`

#### Case 2

- `position_date_open_utc`: 2020-01-01 00:00:00 UTC
- `previous_completed_bar_utc`: 2019-12-31 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[7210.0, 7198.08, 7258.48, 7064.05, 7118.59, 6891.72, 6623.82, 7277.83, 7150.3, 7187.83, 7132.75, 7501.44, 7317.09, 7255.77, 7204.63, 7202.0, 7254.74, 7316.14, 7388.24, 7246.0, 7195.23]`
- `volcluster_5_20_prev_bar`: `0.429404565402912`
- `signal_for_position_date`: `LONG`
- `position_at_open`: `1`
- `state_change_at_open`: `entry_long`
- `entry_price_if_state_change`: `7195.24000000`
- `exit_price_if_state_change`: `none`
- `completed_trade_entry_open_utc`: `2020-01-01 00:00:00 UTC`
- `completed_trade_exit_open_utc`: `2020-01-04 00:00:00 UTC`
- `completed_trade_pnl_after_cost`: `0.018773936675363`

#### Case 3

- `position_date_open_utc`: 2020-01-02 00:00:00 UTC
- `previous_completed_bar_utc`: 2020-01-01 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[7198.08, 7258.48, 7064.05, 7118.59, 6891.72, 6623.82, 7277.83, 7150.3, 7187.83, 7132.75, 7501.44, 7317.09, 7255.77, 7204.63, 7202.0, 7254.74, 7316.14, 7388.24, 7246.0, 7195.23, 7200.85]`
- `volcluster_5_20_prev_bar`: `0.407809278661773`
- `signal_for_position_date`: `LONG`
- `position_at_open`: `1`
- `state_change_at_open`: `hold_long`
- `entry_price_if_state_change`: `none`
- `exit_price_if_state_change`: `none`
- `completed_trade_entry_open_utc`: `none`
- `completed_trade_exit_open_utc`: `none`
- `completed_trade_pnl_after_cost`: `none`

#### Case 4

- `position_date_open_utc`: 2020-01-04 00:00:00 UTC
- `previous_completed_bar_utc`: 2020-01-03 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[7064.05, 7118.59, 6891.72, 6623.82, 7277.83, 7150.3, 7187.83, 7132.75, 7501.44, 7317.09, 7255.77, 7204.63, 7202.0, 7254.74, 7316.14, 7388.24, 7246.0, 7195.23, 7200.85, 6965.71, 7344.96]`
- `volcluster_5_20_prev_bar`: `1.021954837839479`
- `signal_for_position_date`: `FLAT`
- `position_at_open`: `0`
- `state_change_at_open`: `exit_to_flat`
- `entry_price_if_state_change`: `none`
- `exit_price_if_state_change`: `7345.00000000`
- `completed_trade_entry_open_utc`: `2020-01-01 00:00:00 UTC`
- `completed_trade_exit_open_utc`: `2020-01-04 00:00:00 UTC`
- `completed_trade_pnl_after_cost`: `0.018773936675363`

#### Case 5

- `position_date_open_utc`: 2020-01-05 00:00:00 UTC
- `previous_completed_bar_utc`: 2020-01-04 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[7118.59, 6891.72, 6623.82, 7277.83, 7150.3, 7187.83, 7132.75, 7501.44, 7317.09, 7255.77, 7204.63, 7202.0, 7254.74, 7316.14, 7388.24, 7246.0, 7195.23, 7200.85, 6965.71, 7344.96, 7354.11]`
- `volcluster_5_20_prev_bar`: `0.972854204445185`
- `signal_for_position_date`: `LONG`
- `position_at_open`: `1`
- `state_change_at_open`: `entry_long`
- `entry_price_if_state_change`: `7354.19000000`
- `exit_price_if_state_change`: `none`
- `completed_trade_entry_open_utc`: `2020-01-05 00:00:00 UTC`
- `completed_trade_exit_open_utc`: `2020-01-07 00:00:00 UTC`
- `completed_trade_pnl_after_cost`: `0.052922700312720`

#### Case 6

- `position_date_open_utc`: 2020-01-07 00:00:00 UTC
- `previous_completed_bar_utc`: 2020-01-06 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[6623.82, 7277.83, 7150.3, 7187.83, 7132.75, 7501.44, 7317.09, 7255.77, 7204.63, 7202.0, 7254.74, 7316.14, 7388.24, 7246.0, 7195.23, 7200.85, 6965.71, 7344.96, 7354.11, 7358.75, 7758.0]`
- `volcluster_5_20_prev_bar`: `1.193745320488822`
- `signal_for_position_date`: `FLAT`
- `position_at_open`: `0`
- `state_change_at_open`: `exit_to_flat`
- `entry_price_if_state_change`: `none`
- `exit_price_if_state_change`: `7758.90000000`
- `completed_trade_entry_open_utc`: `2020-01-05 00:00:00 UTC`
- `completed_trade_exit_open_utc`: `2020-01-07 00:00:00 UTC`
- `completed_trade_pnl_after_cost`: `0.052922700312720`

#### Case 7

- `position_date_open_utc`: 2020-01-20 00:00:00 UTC
- `previous_completed_bar_utc`: 2020-01-19 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[7246.0, 7195.23, 7200.85, 6965.71, 7344.96, 7354.11, 7358.75, 7758.0, 8145.28, 8055.98, 7817.76, 8197.02, 8020.01, 8184.98, 8110.34, 8810.01, 8821.41, 8720.01, 8913.28, 8915.96, 8701.7]`
- `volcluster_5_20_prev_bar`: `0.532060125824813`
- `signal_for_position_date`: `LONG`
- `position_at_open`: `1`
- `state_change_at_open`: `entry_long`
- `entry_price_if_state_change`: `8701.72000000`
- `exit_price_if_state_change`: `none`
- `completed_trade_entry_open_utc`: `2020-01-20 00:00:00 UTC`
- `completed_trade_exit_open_utc`: `2020-02-01 00:00:00 UTC`
- `completed_trade_pnl_after_cost`: `0.072541032450084`

#### Case 8

- `position_date_open_utc`: 2020-02-01 00:00:00 UTC
- `previous_completed_bar_utc`: 2020-01-31 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[8020.01, 8184.98, 8110.34, 8810.01, 8821.41, 8720.01, 8913.28, 8915.96, 8701.7, 8642.35, 8736.03, 8682.36, 8404.52, 8439.0, 8340.58, 8615.0, 8907.57, 9374.21, 9301.53, 9513.21, 9352.89]`
- `volcluster_5_20_prev_bar`: `1.031426324206796`
- `signal_for_position_date`: `FLAT`
- `position_at_open`: `0`
- `state_change_at_open`: `exit_to_flat`
- `entry_price_if_state_change`: `none`
- `exit_price_if_state_change`: `9351.71000000`
- `completed_trade_entry_open_utc`: `2020-01-20 00:00:00 UTC`
- `completed_trade_exit_open_utc`: `2020-02-01 00:00:00 UTC`
- `completed_trade_pnl_after_cost`: `0.072541032450084`

#### Case 9

- `position_date_open_utc`: 2024-10-03 00:00:00 UTC
- `previous_completed_bar_utc`: 2024-10-02 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[58132.32, 60498.0, 59993.03, 59132.0, 58213.99, 60313.99, 61759.99, 62947.99, 63201.05, 63348.96, 63578.76, 63339.99, 64262.7, 63152.01, 65173.99, 65769.95, 65858.0, 65602.01, 63327.59, 60805.78, 60649.28]`
- `volcluster_5_20_prev_bar`: `0.932985163490803`
- `signal_for_position_date`: `LONG`
- `position_at_open`: `1`
- `state_change_at_open`: `entry_long`
- `entry_price_if_state_change`: `60649.27000000`
- `exit_price_if_state_change`: `none`
- `completed_trade_entry_open_utc`: `2024-10-03 00:00:00 UTC`
- `completed_trade_exit_open_utc`: `2024-10-04 00:00:00 UTC`
- `completed_trade_pnl_after_cost`: `-0.000294996802599`

#### Case 10

- `position_date_open_utc`: 2024-10-04 00:00:00 UTC
- `previous_completed_bar_utc`: 2024-10-03 00:00:00 UTC
- `close_window_count`: 21
- `close_window_ending_prev_bar`: `[60498.0, 59993.03, 59132.0, 58213.99, 60313.99, 61759.99, 62947.99, 63201.05, 63348.96, 63578.76, 63339.99, 64262.7, 63152.01, 65173.99, 65769.95, 65858.0, 65602.01, 63327.59, 60805.78, 60649.28, 60752.71]`
- `volcluster_5_20_prev_bar`: `1.028874837901384`
- `signal_for_position_date`: `FLAT`
- `position_at_open`: `0`
- `state_change_at_open`: `exit_to_flat`
- `entry_price_if_state_change`: `none`
- `exit_price_if_state_change`: `60752.72000000`
- `completed_trade_entry_open_utc`: `2024-10-03 00:00:00 UTC`
- `completed_trade_exit_open_utc`: `2024-10-04 00:00:00 UTC`
- `completed_trade_pnl_after_cost`: `-0.000294996802599`


## 12. Practical implementation notes

- The signal uses only native D1 close prices.
- The threshold is always exactly `1.0`.
- The standard-deviation convention is always sample std with `ddof=1`.
- The live position always lags the computed signal by one full D1 bar because execution occurs at the next D1 open.
- The system is entirely self-contained. There is no hidden regime filter, no additional confirmation layer, and no use of the H4 file.

## 13. Minimal acceptance checklist

A reimplementation is correct only if all of the following hold:

1. the first valid `volcluster_5_20` value appears on `2017-09-06`,
2. `position` is forced to `0` before `2020-01-01`,
3. the discovery metrics match the verification table,
4. the holdout and reserve metrics match the verification table,
5. the 10 test vectors match exactly,
6. the first trade from `2020-01-01` to `2020-01-04` has PnL `0.018773936675363`,
7. the quick reserve trade from `2024-10-03` to `2024-10-04` has PnL `-0.000294996802599`.
