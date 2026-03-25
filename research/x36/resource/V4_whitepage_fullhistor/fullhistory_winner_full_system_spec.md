# VTREND full-history winner — self-contained freeze spec

## 1. Purpose

This document fully specifies the **entire long-only system** selected by the white-page full-history research on the supplied BTCUSDT H4/D1 data.

It is intended to be **self-contained**. A competent engineer must be able to rebuild the strategy **1:1 from raw data** using only:

- this specification, and
- the supplied H4 and D1 CSV files.

No chat history, original code, or other documents are required.

---

## 2. What is frozen here

### 2.1 Frozen system identifier

This spec freezes the following system exactly:

- **Entry**: `weak_f_0065`
- **Exit**: `trail2.8_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop60`

Compact system name:

**`weak_f_0065 + trail2.8_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop60`**

### 2.2 Scope lock

This spec includes:

- raw data schema
- timestamp semantics
- warmup / eligibility rules
- indicator formulas
- entry logic
- stop / exit logic
- cooldown logic
- sizing and accounting
- state machine and event ordering
- full-history diagnostic validation targets
- known caveats

### 2.3 Locked unchanged assumptions

Do **not** change any of the following:

- asset universe (single BTCUSDT series)
- timeframe (H4 execution, D1 regime context)
- EMA convention
- robust ATR construction
- long-only / full-notional sizing
- no leverage / no pyramiding
- per-side cost
- next-open execution semantics
- no intrabar peeking
- no forced liquidation at the final bar
- fixed weak-VDO threshold `0.0065`
- fixed exit parameters in this spec

---

## 3. Raw data requirements

## 3.1 H4 CSV

One H4 CSV, sorted ascending by time, with at least these columns:

- `open_time` (Unix ms, UTC)
- `close_time` (Unix ms, UTC)
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `taker_buy_base_vol`
- `taker_buy_quote_vol`

The validated supplied file is:

- `btcusdt_4h.csv`

## 3.2 D1 CSV

One D1 CSV, sorted ascending by time, with at least these columns:

- `open_time` (Unix ms, UTC)
- `close_time` (Unix ms, UTC)
- `close`

The validated supplied file is:

- `btcusdt_1d.csv`

## 3.3 Raw-data assumptions

- timestamps are UTC
- bars are complete OHLCV bars
- rows are strictly time-ascending
- duplicates / gaps are not allowed in the validated rebuild
- all calculations use `float64`

`num_trades` may exist in the H4 CSV, but it is **unused** by this system.

---

## 4. Time semantics and execution model

- all signals are computed on **closed H4 bars**
- a decision formed on H4 close bar `t` is executed at **open of H4 bar `t+1`**
- there is no intrabar peeking
- position state is binary:
  - `FLAT`
  - `LONG_100`
- no leverage
- no pyramiding
- no partial exits

## 4.1 Per-bar event order

For each H4 bar index `t`, in chronological order:

1. **At open of bar `t`**
   - execute any pending order scheduled from close of bar `t-1`
   - possible order types:
     - full entry
     - full exit

2. **During bar `t`**
   - no intrabar decisions are allowed

3. **At close of bar `t`**
   - mark equity to `close_t`
   - if flat: evaluate entry logic
   - if long: evaluate exit logic
   - any order generated at close `t` fills at open `t+1`

## 4.2 Last-bar rule

On the final H4 bar of the simulation window:

- do **not** schedule new orders, because `open[t+1]` does not exist
- if a position remains open, final equity is **close-marked equity**, not forced liquidation cash

---

## 5. Simulation window, warmup, and eligibility

## 5.1 Warmup

Use:

- `WARMUP_DAYS = 365`

Let:

- `first_h4_open_dt = earliest H4 open timestamp`

Define:

- `eligible_from = first_h4_open_dt + 365 calendar days`

The strategy may only make decisions on H4 bars whose:

- `close_dt >= eligible_from`

## 5.2 Full-history diagnostic window

The official full-history research diagnostic window for this winner is:

- **start**: first eligible H4 close after warmup
  - `2018-08-17 07:59:59.999 UTC`
- **end**: last available H4 close in the supplied data
  - `2026-03-11 07:59:59.999 UTC`

On the validated dataset this window contains:

- `bar_count = 16573`

## 5.3 Undefined-indicator rule

If a required signal is undefined on a would-be decision bar:

- no entry or exit signal may be emitted on that bar

In the validated rebuild, all official bars are well past warmup and indicator seed requirements.

---

## 6. Constants

Use these exact constants.

| name | value |
|---|---:|
| `INITIAL_CASH` | `10000.0` |
| `SIDE_COST` | `0.00125` |
| `H4_BARS_PER_DAY` | `6` |
| `DAYS_PER_YEAR` | `365.25` |
| `SHARPE_ANNUALIZATION` | `sqrt(365.25 * 6)` |
| `EMA_FAST_H4` | `30` |
| `EMA_SLOW_H4` | `120` |
| `EMA_D1_REGIME` | `21` |
| `ATR_PERIOD` | `20` |
| `TR_CAP_LOOKBACK` | `100` |
| `TR_CAP_Q` | `0.90` |
| `VDO_FAST` | `12` |
| `VDO_SLOW` | `28` |
| `WEAK_VDO_THR` | `0.0065` |
| `TRAIL_MULT` | `2.8` |
| `TRAIL_CONFIRM_BARS` | `1` |
| `COOLDOWN_BARS` | `3` |
| `TIME_STOP_BARS` | `60` |

All inequality directions used below are also frozen.

---

## 7. Timestamp derivation

From raw files:

- `open_dt = to_datetime(open_time, unit="ms", utc=True)`
- `close_dt = to_datetime(close_time, unit="ms", utc=True)`

All timestamp comparisons in this spec are on UTC datetimes.

---

## 8. EMA convention (frozen)

For any series `x_t` and EMA period `p`:

- `alpha_p = 2 / (p + 1)`
- `EMA_p(x)_0 = x_0`
- `EMA_p(x)_t = alpha_p * x_t + (1 - alpha_p) * EMA_p(x)_(t-1)` for `t >= 1`

This exact EMA convention must be used everywhere:

- H4 EMA30
- H4 EMA120
- D1 EMA21
- VDO EMA12
- VDO EMA28
- freshness EMA28

No alternative seeding is allowed.

---

## 9. Core indicators

## 9.1 H4 trend EMAs

On H4 `close`:

- `ema_fast_t = EMA_30(close)_t`
- `ema_slow_t = EMA_120(close)_t`

Define trend-up:

- `trend_up_t = (ema_fast_t > ema_slow_t)`

Strict `>` is required.

## 9.2 D1 regime filter

On D1 `close`:

- `d1_ema21_t = EMA_21(d1_close)_t`
- `d1_regime_ok_t = (d1_close_t > d1_ema21_t)`

Strict `>` is required.

### 9.2.1 Mapping D1 onto H4

For each H4 bar, attach the **most recent completed D1 bar** satisfying:

- `d1_close_time < h4_close_time`

Use backward `merge_asof` semantics on `close_time`.

Mapped fields onto each H4 bar:

- `mapped_d1_close`
- `mapped_d1_ema21`
- `mapped_regime_ok`

Define:

- `regime_ok_t = mapped_regime_ok_t`

## 9.3 Robust ATR (unchanged base definition)

### 9.3.1 True Range

For H4 bar `t`:

- `TR_0 = high_0 - low_0`

For `t >= 1`:

- `TR_t = max(high_t - low_t, abs(high_t - close_(t-1)), abs(low_t - close_(t-1)))`

### 9.3.2 Outlier cap

Use:

- `TR_CAP_LOOKBACK = 100`
- `TR_CAP_Q = 0.90`

For `t < 100`:

- `TR_capped_t = TR_t`

For `t >= 100`:

- compute `q_t = quantile(TR_(t-100) ... TR_(t-1), 0.90, method="linear")`
- `TR_capped_t = min(TR_t, q_t)`

Use:

- `numpy.quantile(..., 0.90, method="linear")`

No other quantile method is allowed.

### 9.3.3 Wilder ATR(20)

Let:

- `ATR_PERIOD = 20`
- `seed_idx = 100 + 20 - 1 = 119`

Set:

- `robust_atr_t = NaN` for `t < 119`
- `robust_atr_119 = mean(TR_capped_100 ... TR_capped_119)`

Then for `t > 119`:

- `robust_atr_t = (robust_atr_(t-1) * 19 + TR_capped_t) / 20`

This is Wilder smoothing.

## 9.4 Base imbalance ratio

Define H4 taker-sell base volume:

- `taker_sell_base_t = volume_t - taker_buy_base_vol_t`

Define base imbalance ratio:

- `imbalance_ratio_base_t = (taker_buy_base_vol_t - taker_sell_base_t) / volume_t`

Equivalent form:

- `imbalance_ratio_base_t = (2 * taker_buy_base_vol_t - volume_t) / volume_t`

If `volume_t == 0`:

- `imbalance_ratio_base_t = 0.0`

## 9.5 VDO

- `vdo_fast_t = EMA_12(imbalance_ratio_base)_t`
- `vdo_slow_t = EMA_28(imbalance_ratio_base)_t`
- `VDO_t = vdo_fast_t - vdo_slow_t`

## 9.6 Freshness score and support

Define:

- `freshness_score_t = EMA_28(imbalance_ratio_base)_t`

This is numerically identical to the `vdo_slow_t` leg above, but it is named separately here because it plays a distinct logical role in entry gating.

Freshness support is:

- `freshness_support_t = (freshness_score_t <= 0.0)`

Strict frozen rule:

- use `<= 0.0`

---

## 10. Entry system — `weak_f_0065`

## 10.1 High-level logic

Entry keeps the standard trend/regime/VDO core, but adds a **bounded freshness veto** only inside the **weak positive VDO** zone.

Interpretation:

- `VDO <= 0`: reject
- `VDO > 0.0065`: accept immediately
- `0 < VDO <= 0.0065`: accept only if the slower imbalance backdrop is still fresh (`EMA28(imbalance_ratio_base) <= 0`)

## 10.2 Frozen weak-VDO threshold

Use exactly:

- `WEAK_VDO_THR = 0.0065`

This value is **fixed** in this spec. It is **not** adaptively re-estimated.

## 10.3 Entry decision rule

At H4 close bar `t`, while flat, define:

- `core_t = trend_up_t AND regime_ok_t`

The long entry signal is:

- `enter_t = core_t AND (VDO_t > 0) AND [ (VDO_t > 0.0065) OR (0 < VDO_t <= 0.0065 AND freshness_support_t) ]`

Expanded piecewise form:

### Case A — strong positive VDO
Enter if all are true:

1. `trend_up_t == True`
2. `regime_ok_t == True`
3. `VDO_t > 0.0065`

### Case B — weak positive VDO with freshness support
Enter if all are true:

1. `trend_up_t == True`
2. `regime_ok_t == True`
3. `0 < VDO_t <= 0.0065`
4. `freshness_support_t == True`

Since `freshness_support_t` means `EMA28(imbalance_ratio_base)_t <= 0.0`, this is equivalent to:

- `0 < VDO_t <= 0.0065` and `EMA28(imbalance_ratio_base)_t <= 0.0`

### Case C — reject
Reject if any of the following is true:

- `trend_up_t == False`
- `regime_ok_t == False`
- `VDO_t <= 0`
- `0 < VDO_t <= 0.0065` and `freshness_support_t == False`

## 10.4 Entry execution

If `enter_t == True` on H4 close bar `t`:

- schedule one full long entry at `open_(t+1)`

No other entry action exists.

---

## 11. Exit system — `trail2.8_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop60`

## 11.1 High-level design

Exit uses:

- mandatory trailing stop
- close-based peak anchor
- **lagged** robust ATR
- first-breach confirmation (`confirm1`)
- **no** EMA trend exit
- cooldown after every exit
- hard maximum trade age of 60 H4 bars

## 11.2 Required state variables

Maintain at simulation level:

- `cash`
- `qty`
- `position_fraction` in `{0,1}`
- `trade_id`
- `full_entry_fill_bar_index`
- `full_entry_fill_price`
- `live_peak_close`
- `last_exit_fill_bar_index`
- `pending_order_type`
- `pending_order_reason`

Because this policy uses `confirm1`, no multi-bar trail-breach counter is required.

### Initial state
At simulation start:

- `cash = 10000.0`
- `qty = 0.0`
- `position_fraction = 0`
- `trade_id = 0`
- `full_entry_fill_bar_index = None`
- `full_entry_fill_price = None`
- `live_peak_close = None`
- `last_exit_fill_bar_index = None`
- `pending_order_type = None`
- `pending_order_reason = None`

## 11.3 Entry-fill initialization

When a long entry fills at `open_t`:

- `trade_id += 1`
- `qty = cash_before / (open_t * (1 + SIDE_COST))`
- `cash = 0.0`
- `position_fraction = 1`
- `full_entry_fill_bar_index = t`
- `full_entry_fill_price = open_t`
- `live_peak_close = open_t`

Important:

- `live_peak_close` is initialized to the **entry fill open price**, not to the first close after entry.

## 11.4 Peak anchor

Because this policy uses `peak_anchor = close`, while long:

- `live_peak_close_t = max(live_peak_close_(t-1), close_t)`

`high_t` is deliberately ignored.

## 11.5 Lagged ATR mode

This policy uses:

- `atr_mode = lagged`

Therefore when evaluating exits on H4 close bar `t`, the trail uses:

- `robust_atr_(t-1)`

not `robust_atr_t`.

Define:

- `lagged_robust_atr_t = robust_atr_(t-1)`

## 11.6 Trail stop level

While long on close bar `t`:

- `trail_stop_t = live_peak_close_t - 2.8 * lagged_robust_atr_t`

Use:

- current `live_peak_close_t`
- lagged `robust_atr_(t-1)`

## 11.7 Trail breach and confirmation

At close bar `t`, while long, define:

- `trail_breach_t = (close_t < trail_stop_t)`

Strict `<` is required.

Because this policy uses:

- `TRAIL_CONFIRM_BARS = 1`

trail exit triggers immediately on the **first** breach close.

If `trail_breach_t == True`:

- schedule full exit at `open_(t+1)`
- `pending_order_reason = "trail_stop"`

## 11.8 No trend exit

This policy uses:

- `trend_exit = none`

Therefore, while long:

- `ema_fast_t < ema_slow_t` has **no exit effect**
- `regime_ok_t == False` has **no exit effect**
- there is no trend-confirmation counter
- there is no EMA cross-down branch in the exit stack

EMAs remain required for **entry**, but are ignored by **exit**.

## 11.9 Time stop

Let:

- `TIME_STOP_BARS = 60`

At close bar `t`, while long, if no trail-stop exit has already been scheduled on that bar, then trigger time stop exactly when:

- `(t + 1) == full_entry_fill_bar_index + 60`

If true:

- schedule full exit at `open_(t+1)`
- `pending_order_reason = "time_stop"`

Equivalent interpretation:

- the position may be held through close of bar `full_entry_fill_bar_index + 59`
- if still alive there, it must exit at open of bar `full_entry_fill_bar_index + 60`

That gives a maximum in-position lifetime of **60 H4 bars**.

## 11.10 Exit precedence

On any close bar while long, exit conditions are tested in this order:

1. `trail_breach_t == True`
2. `time_stop`

If both are true on the same bar:

- exit reason must be `"trail_stop"`

There is no trend-exit branch.

## 11.11 Exit-fill reset

When any exit fills at `open_t`:

- `gross = qty_before * open_t`
- `cash_after = cash_before + gross * (1 - SIDE_COST)`
- `qty = 0.0`
- `position_fraction = 0`
- `full_entry_fill_bar_index = None`
- `full_entry_fill_price = None`
- `live_peak_close = None`
- `last_exit_fill_bar_index = t`

Allowed exit reasons in this system:

- `"trail_stop"`
- `"time_stop"`

---

## 12. Cooldown rule

## 12.1 Definition

Cooldown applies **after every exit fill**, regardless of exit reason.

Use:

- `COOLDOWN_BARS = 3`

## 12.2 Exact fill-index rule

When flat and evaluating entry on close bar `t`, the next-open entry fill at `t+1` is allowed **only if**:

- `last_exit_fill_bar_index is None`
- or `(t + 1) > last_exit_fill_bar_index + 3`

Equivalent earliest re-entry:

- if an exit fills at open bar index `e`
- earliest new entry fill is open bar index `e + 4`

Equivalent earliest new entry decision:

- close bar index `e + 3`

Any entry signal during cooldown is ignored and not queued.

---

## 13. Full state machine

Only two live states exist:

1. `FLAT`
2. `LONG_100`

## 13.1 State `FLAT`

At close bar `t`:

1. if bar is not eligible or `t` is the last bar of the window:
   - do nothing

2. else check cooldown:
   - entry fill at `t+1` is allowed only if:
     - `last_exit_fill_bar_index is None`
     - or `(t + 1) > last_exit_fill_bar_index + 3`

3. if cooldown allows, evaluate the entry rule from Section 10

4. if entry rule is true:
   - set:
     - `pending_order_type = "entry"`
     - `pending_order_reason = "entry"`

## 13.2 State `LONG_100`

At close bar `t`:

1. update:
   - `live_peak_close = max(live_peak_close, close_t)`

2. compute:
   - `trail_stop_t = live_peak_close - 2.8 * robust_atr_(t-1)`
   - `trail_breach_t = (close_t < trail_stop_t)`

3. if `trail_breach_t == True`:
   - schedule full exit at `open_(t+1)`
   - reason = `"trail_stop"`

4. else if `(t + 1) == full_entry_fill_bar_index + 60`:
   - schedule full exit at `open_(t+1)`
   - reason = `"time_stop"`

5. else:
   - hold

No trend-down EMA exit is evaluated.

---

## 14. Reference pseudocode

```python
for each H4 bar index t in chronological order:

    # 1) execute pending order at bar open
    if pending_order_type is not None:
        open_price = open[t]

        if pending_order_type == "entry":
            trade_id += 1
            qty = cash / (open_price * (1 + SIDE_COST))
            cash = 0.0
            position_fraction = 1

            full_entry_fill_bar_index = t
            full_entry_fill_price = open_price
            live_peak_close = open_price

        elif pending_order_type == "exit":
            gross = qty * open_price
            cash = cash + gross * (1 - SIDE_COST)
            qty = 0.0
            position_fraction = 0

            full_entry_fill_bar_index = None
            full_entry_fill_price = None
            live_peak_close = None
            last_exit_fill_bar_index = t

        pending_order_type = None
        pending_order_reason = None

    # 2) mark equity to bar close
    equity_t = cash + qty * close[t]

    # 3) no decision if last bar or ineligible
    if t == last_bar_index_of_window:
        continue
    if close_dt[t] < eligible_from:
        continue

    # 4) flat state: entry only
    if qty == 0.0:
        cooldown_ok = (
            last_exit_fill_bar_index is None
            or (t + 1) > last_exit_fill_bar_index + 3
        )

        if cooldown_ok:
            trend_up = ema_fast[t] > ema_slow[t]
            regime_ok = mapped_regime_ok[t]
            vdo = VDO[t]
            freshness_support = (freshness_score[t] <= 0.0)

            if trend_up and regime_ok:
                if vdo > 0.0065:
                    pending_order_type = "entry"
                    pending_order_reason = "entry"

                elif 0.0 < vdo <= 0.0065 and freshness_support:
                    pending_order_type = "entry"
                    pending_order_reason = "entry"

        continue

    # 5) long state: exit only
    live_peak_close = max(live_peak_close, close[t])
    trail_stop = live_peak_close - 2.8 * robust_atr[t - 1]

    if close[t] < trail_stop:
        pending_order_type = "exit"
        pending_order_reason = "trail_stop"

    elif (t + 1) == full_entry_fill_bar_index + 60:
        pending_order_type = "exit"
        pending_order_reason = "time_stop"

    else:
        pass
```

---

## 15. Accounting and mark-to-market

## 15.1 Entry fill accounting

At entry fill on `open_t`:

- `qty = cash_before / (open_t * (1 + SIDE_COST))`
- `cash_after = 0.0`

This implies all available cash is deployed, including entry fee.

## 15.2 Exit fill accounting

At exit fill on `open_t`:

- `gross = qty_before * open_t`
- `cash_after = cash_before + gross * (1 - SIDE_COST)`

Since `cash_before = 0` while fully long, this is equivalent to:

- `cash_after = qty_before * open_t * (1 - SIDE_COST)`

## 15.3 Equity at close

At each H4 close bar `t`:

- `equity_t = cash_t + qty_t * close_t`

This close-marked equity series is used for:

- bar returns
- Sharpe
- CAGR
- MDD
- exposure

## 15.4 No forced liquidation at final bar

At the end of the full-history window:

- leave any open trade marked to close
- do **not** force an end-of-window liquidation

---

## 16. Metric formulas

These formulas are used for diagnostic validation.

## 16.1 Bar returns

On the full-history close-marked equity series:

- `ret_t = equity_t / equity_(t-1) - 1`

Set first return of the window to:

- `ret_0 = 0.0`

## 16.2 Sharpe

- `Sharpe = mean(bar_returns) / std(bar_returns, ddof=0) * sqrt(365.25 * 6)`

## 16.3 CAGR

Let:

- `years = (bar_count - 1) / (365.25 * 6)`
- `end_equity_multiple = product(1 + bar_returns)`

Then:

- `CAGR = end_equity_multiple ** (1 / years) - 1`

## 16.4 MDD

On the close-marked equity curve:

- `MDD = min(equity / cumulative_max(equity) - 1)`

## 16.5 Exposure

- `exposure = mean(position_fraction_after_open_fill_marked_through_bar_close)`

Equivalent in the validated engine:

- fraction of counted bars whose close-marked portfolio was long

---

## 17. Full-history diagnostic acceptance targets

These numbers are **diagnostic rebuild targets**, not a walk-forward acceptance harness.

They are included so an engineer can verify that the rebuild matches the white-page full-history winner.

## 17.1 Official full-history winner targets

Simulation window:

- start: `2018-08-17 07:59:59.999 UTC`
- end: `2026-03-11 07:59:59.999 UTC`
- `bar_count = 16573`

Expected continuous full-history metrics for the winner frozen in this spec:

- `Sharpe = 1.685344430964974`
- `CAGR = 0.6970696389618467`
- `MDD = -0.3398050630294229`
- `trades = 200`
- `exposure = 0.39220418753394076`

Derived end-equity diagnostics under the metric formulas above:

- `end_equity_multiple ≈ 54.57276597245069`
- `final_equity_cash ≈ 545727.6597245069`

Minor floating-point noise is acceptable; meaningful deviations are not.

## 17.2 Original baseline targets

For comparison, the original baseline on the same full-history continuous window is:

- entry = `orig_vdo`
- exit = original base exit

Expected metrics:

- `Sharpe = 1.464621325818716`
- `CAGR = 0.6076005660846722`
- `MDD = -0.38861559449066774`
- `trades = 191`
- `exposure = 0.43299342303747057`

Derived end-equity diagnostics:

- `end_equity_multiple ≈ 36.233275965017164`
- `final_equity_cash ≈ 362332.7596501716`

## 17.3 Broad epoch diagnostics

These epoch checks were used to reject designs that only fit one segment of history.

### Epoch boundaries

- `pre_2021`: from `eligible_from` through `2020-12-31 23:59:59.999 UTC`
- `y2021_2023`: `2021-01-01 00:00:00 UTC` through `2023-12-31 23:59:59.999 UTC`
- `y2024_2026`: `2024-01-01 00:00:00 UTC` through last available close in the supplied data

### Winner vs baseline Sharpe by broad epoch

Winner frozen in this spec:

- `pre_2021 = 2.1811757065540665`
- `y2021_2023 = 1.3884175248911865`
- `y2024_2026 = 1.2172429581057307`

Original baseline:

- `pre_2021 = 2.0204038086697604`
- `y2021_2023 = 1.1465820347112217`
- `y2024_2026 = 1.1490908728792937`

## 17.4 Plateau diagnostics used to defend this freeze

This system was selected not because it was the single highest local peak, but because it lived on a materially wider plateau.

### Entry plateau (holding the selected exit fixed)
Representative full-history Sharpe values:

- `WEAK_VDO_THR = 0.0060` -> `1.623`
- `WEAK_VDO_THR = 0.0065` -> `1.685`
- `WEAK_VDO_THR = 0.0070` -> `1.661`
- `WEAK_VDO_THR = 0.0075` -> `1.671`
- `WEAK_VDO_THR = 0.0080` -> `1.666`

Interpretation:

- the chosen `0.0065` sits inside a real plateau around roughly `0.006 .. 0.009`

### Exit plateau (holding the selected entry fixed)
Representative full-history Sharpe values:

Trail multiplier with `cooldown=3`, `time_stop=60`:

- `2.8` -> `1.685344430964974`
- `2.9` -> `1.6035429902834988`
- `3.0` -> `1.6443878977069821`
- `3.1` -> `1.6231132650439517`

Cooldown with `trail=2.8`, `time_stop=60`:

- `2` -> `1.6634574861114861`
- `3` -> `1.685344430964974`
- `4` -> `1.6729964056723479`

Time stop with `trail=2.8`, `cooldown=3`:

- `54` -> `1.6040277417206914`
- `60` -> `1.685344430964974`
- `66` -> `1.634099875790928`

Interpretation:

- defended plateau family is approximately:
  - `trail ≈ 2.8–3.1`
  - `cooldown ≈ 2–4`
  - `time_stop ≈ 54–66`

## 17.5 Robustness diagnostics against the original baseline

These were part of the white-page full-history selection logic:

- paired circular block bootstrap on full-history bar returns:
  - `P(delta Sharpe > 0)` is about `94%–95%` across block lengths `12, 24, 48, 72, 144, 288`
- cost sweep:
  - winner stays ahead of the original baseline from `0` to `100 bps/side`

These robustness checks defend the **family** around this winner, but do **not** turn this full-history research result into a walk-forward OOS deployment proof.

---

## 18. Known caveats

## 18.1 This is a full-history winner, not a post-2021 OOS freeze

This spec freezes the winner of the **whole-history 2018–2026 question**.

It is **not** the same object as the separate post-2021 end-to-end combo that won under the stitched OOS validation protocol.

Those are different research questions and therefore different winners.

## 18.2 Fixed threshold, not adaptive threshold

`WEAK_VDO_THR = 0.0065` is a **fixed research constant** in this spec.

It is intentionally **not** re-estimated online. The whole-history winner was chosen partly because this threshold sits inside a reasonably broad plateau.

## 18.3 No claim of universal transfer

This system is justified on the supplied BTCUSDT history. This spec does **not** claim that the same exact constants will survive:

- another exchange
- another asset
- another fee regime
- radically different market structure

## 18.4 “Whole-history better” does not mean “best in every sub-window”

The selected winner is stronger than the original baseline on the full continuous tape and on broad epoch checks, but that does **not** mean it wins every smaller calendar segment.

## 18.5 No ML overlay

This system is deliberately non-ML. There is no classifier, no probability score, no adaptive optimizer, and no learned threshold in the execution path.

---

## 19. Minimal checklist for a correct rebuild

A rebuild should be considered correct only if all of the following match:

1. H4 and D1 bars are mapped by **last completed D1 close**
2. EMAs use the exact seeding rule `EMA_0 = x_0`
3. robust ATR uses:
   - 100-bar backward TR cap at 90th percentile
   - `numpy.quantile(..., method="linear")`
   - Wilder ATR(20) seeded at index 119
4. entry accepts:
   - all `VDO > 0.0065` bars inside core
   - weak positive `0 < VDO <= 0.0065` only when `EMA28(imbalance_ratio_base) <= 0`
5. trail stop uses:
   - peak = `close`
   - ATR = `robust_atr_(t-1)`
   - multiplier = `2.8`
   - first breach only (`confirm1`)
6. there is **no** trend exit of any kind
7. cooldown blocks entry fills until `(t+1) > last_exit_fill_bar_index + 3`
8. time stop exits exactly at open bar index `entry_fill_index + 60`
9. final bar is **not** force-liquidated
10. continuous full-history diagnostics match Section 17 within minor floating-point tolerance

