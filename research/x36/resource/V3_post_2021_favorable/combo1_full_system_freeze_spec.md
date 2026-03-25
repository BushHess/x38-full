# VTREND combo 1 — full-system freeze spec (entry freeze + exit winner)

## 1. Purpose

This document fully specifies the **entire promoted non-ML system** that passed end-to-end validation as **combo 1**:

- **Entry**: frozen weak-positive-VDO bounded veto
- **Exit**: `trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`

The document is intended to be **self-contained**. A competent engineer should be able to rebuild the strategy **1:1 from raw data** using only this spec and the supplied data files.

---

## 2. Scope lock

This spec freezes the full system exactly as validated end-to-end.

### 2.1 Included
- raw data schema
- timestamp semantics
- warmup / eligibility
- indicator formulas
- entry rule
- exit rule
- position state machine
- sizing and accounting
- walk-forward validation protocol
- acceptance targets
- known caveats

### 2.2 Excluded / locked unchanged
Do **not** change any of the following:

- asset universe
- timeframe
- base indicator definitions
- EMA convention
- robust ATR construction
- per-side cost
- full-notional sizing
- no leverage / no pyramiding semantics
- frozen entry threshold
- exit parameters
- no-ML requirement

### 2.3 Final frozen system identifier
Use the following frozen configuration exactly:

- `ENTRY_ID = weakvdo_freeze_0.0065`
- `EXIT_ID = trail3.3_close_current_confirm2_noTrend_cd6_time30`

Compact system name:

**`weakvdo_freeze_0.0065 + trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`**

---

## 3. Raw data requirements

## 3.1 Required H4 file

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

Validated file in the supplied dataset:
- `btcusdt_4h.csv`

## 3.2 Required D1 file

One D1 CSV, sorted ascending by time, with at least these columns:

- `open_time` (Unix ms, UTC)
- `close_time` (Unix ms, UTC)
- `close`

Validated file in the supplied dataset:
- `btcusdt_1d.csv`

## 3.3 Raw-data assumptions

- Timestamps are UTC.
- Bars are complete OHLCV bars.
- Files are strictly ascending in time.
- No missing / duplicated bars are allowed in the validated rebuild.
- All floating-point calculations use `float64`.

The final system uses only:
- H4 OHLCV
- H4 taker-buy base / quote volume
- D1 close

`num_trades` exists in the supplied CSVs but is **unused** by combo 1.

---

## 4. Time semantics and execution model

- All signals are computed on **closed bars**.
- A decision formed on H4 close bar `t` is executed at **open of H4 bar `t+1`**.
- There is no intrabar peeking.
- Position state is binary:
  - `FLAT`
  - `LONG_100`
- No pyramiding.
- No partial exits.
- No leverage.

### 4.1 Per-bar event order

For each H4 bar `t`:

1. **At open of bar `t`**  
   Execute any pending order that was scheduled from the previous close:
   - full entry
   - full exit

2. **At close of bar `t`**  
   Mark equity to `close_t`, then evaluate:
   - entry logic if flat
   - exit logic if long

3. Orders created at close `t` fill only at open `t+1`.

### 4.2 Last-bar rule
On the last bar of any simulation slice, do **not** schedule new orders, because `open[t+1]` does not exist.

---

## 5. Warmup, eligibility, and cutoff

### 5.1 Warmup
Warmup is:

- `WARMUP_DAYS = 365`

Let:
- `first_h4_open_dt = earliest H4 open timestamp`

Then:
- `eligible_from = first_h4_open_dt + 365 calendar days`

The strategy may only take decisions on H4 bars whose `close_dt >= eligible_from`.

### 5.2 Hard validation cutoff
For project acceptance and all official metrics in this spec:

- `VALIDATION_CUTOFF = 2026-02-28 23:59:59.999 UTC`

Bars after this timestamp are ignored in acceptance calculations.

### 5.3 Undefined-indicator rule
If any required indicator for a bar is undefined (`NaN`) on a would-be decision bar:
- no signal may be emitted on that bar.

On the supplied BTCUSDT data, all official OOS bars are well past warmup, so required signals are defined.

---

## 6. Constants

Use these exact constants:

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
| `TRAIL_MULT` | `3.3` |
| `TRAIL_CONFIRM_BARS` | `2` |
| `COOLDOWN_BARS` | `6` |
| `TIME_STOP_BARS` | `30` |

All inequality directions are also frozen; they are specified below exactly.

---

## 7. EMA convention (frozen)

For any series `x_t` and EMA period `p`:

- `alpha_p = 2 / (p + 1)`
- `EMA_p(x)_0 = x_0`
- `EMA_p(x)_t = alpha_p * x_t + (1 - alpha_p) * EMA_p(x)_(t-1)` for `t >= 1`

This exact convention must be used everywhere:
- H4 EMA30
- H4 EMA120
- D1 EMA21
- VDO EMAs
- quote-volume EMA28
- activity EMA12
- freshness EMA28

No alternative seeding is allowed.

---

## 8. Derived timestamps

From raw files:

- `open_dt = to_datetime(open_time, unit="ms", utc=True)`
- `close_dt = to_datetime(close_time, unit="ms", utc=True)`

All comparisons in this spec are on UTC timestamps.

---

## 9. Core indicators

## 9.1 H4 trend EMAs

On H4 `close`:

- `ema_fast_t = EMA_30(close)_t`
- `ema_slow_t = EMA_120(close)_t`

Trend-up condition:
- `trend_up_t = (ema_fast_t > ema_slow_t)`

Strict `>` is required.

## 9.2 D1 regime filter

On D1 `close`:

- `d1_ema21_t = EMA_21(d1_close)_t`
- `d1_regime_ok_t = (d1_close_t > d1_ema21_t)`

Strict `>` is required.

### 9.2.1 Mapping D1 to H4
For each H4 bar, attach the **most recent completed D1 bar** whose:

- `d1_close_time < h4_close_time`

Use backward `merge_asof` semantics on `close_time`.

Mapped fields onto each H4 bar:
- `d1_close`
- `d1_ema21`
- `regime_ok`

Then:
- `regime_ok_t = mapped_d1_regime_ok_t`

---

## 10. Robust ATR (unchanged base definition)

## 10.1 True Range

For H4 bar `t`:

- `TR_0 = high_0 - low_0`

For `t >= 1`:

- `TR_t = max( high_t - low_t, abs(high_t - close_(t-1)), abs(low_t - close_(t-1)) )`

## 10.2 Outlier cap
Let:

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

## 10.3 Wilder ATR

Let:
- `ATR_PERIOD = 20`

Seed index:
- `seed_idx = 100 + 20 - 1 = 119`

Set:
- `robust_atr_t = NaN` for `t < 119`
- `robust_atr_119 = mean(TR_capped_100 ... TR_capped_119)`

Then for `t > 119`:

- `robust_atr_t = ( robust_atr_(t-1) * 19 + TR_capped_t ) / 20`

This is Wilder smoothing.

---

## 11. Entry system (frozen deployment form)

## 11.1 Base imbalance ratio

Define H4 taker-sell base volume:

- `taker_sell_base_t = volume_t - taker_buy_base_vol_t`

Define base imbalance ratio:

- `imbalance_ratio_base_t = (taker_buy_base_vol_t - taker_sell_base_t) / volume_t`

Equivalent form:

- `imbalance_ratio_base_t = (2 * taker_buy_base_vol_t - volume_t) / volume_t`

If `volume_t == 0`:
- `imbalance_ratio_base_t = 0.0`

## 11.2 VDO

- `vdo_fast_t = EMA_12(imbalance_ratio_base)_t`
- `vdo_slow_t = EMA_28(imbalance_ratio_base)_t`
- `VDO_t = vdo_fast_t - vdo_slow_t`

## 11.3 Activity support

Define:
- `ema28_quote_volume_t = EMA_28(quote_volume)_t`
- `vol_surprise_quote_28_t = quote_volume_t / ema28_quote_volume_t`
- `activity_score_t = EMA_12(vol_surprise_quote_28)_t`

Activity support:

- `activity_support_t = (activity_score_t >= 1.0)`

Strict frozen rule:
- use `>= 1.0`

## 11.4 Freshness support

Define:
- `freshness_score_t = EMA_28(imbalance_ratio_base)_t`

Freshness support:

- `freshness_support_t = (freshness_score_t <= 0.0)`

Strict frozen rule:
- use `<= 0.0`

## 11.5 Frozen weak-VDO boundary

Deployment constant:

- `WEAK_VDO_THR = 0.0065`

### 11.5.1 Provenance of the frozen approximation
This constant is the rounded deployment freeze of the pre-live causal estimate:

- pre-live estimation end:
  - `2021-06-30 23:59:59.999 UTC`
- exact pre-live estimate:
  - median of `VDO_t`
  - over all H4 bars satisfying:
    - `close_dt >= eligible_from`
    - `close_dt <= 2021-06-30 23:59:59.999 UTC`
    - `trend_up_t == True`
    - `regime_ok_t == True`
    - `VDO_t > 0`

Exact pre-live median on the validated dataset:
- `0.00648105072393846`

Frozen deployment approximation:
- `0.0065`

No online re-estimation is allowed in combo 1.

## 11.6 Entry decision

At H4 close bar `t`, when flat, define:
- `core_t = trend_up_t AND regime_ok_t`

The long entry signal is:

- `enter_t = core_t AND (VDO_t > 0) AND [ (VDO_t > 0.0065) OR (0 < VDO_t <= 0.0065 AND activity_support_t AND freshness_support_t) ]`

Expanded piecewise form:

### Case A — strong positive VDO
Enter if:
1. `trend_up_t == True`
2. `regime_ok_t == True`
3. `VDO_t > WEAK_VDO_THR`

### Case B — weak positive VDO
Enter if:
1. `trend_up_t == True`
2. `regime_ok_t == True`
3. `0 < VDO_t <= WEAK_VDO_THR`
4. `activity_support_t == True`
5. `freshness_support_t == True`

### Case C — reject
Reject if any of the following:
- `trend_up_t == False`
- `regime_ok_t == False`
- `VDO_t <= 0`
- `0 < VDO_t <= WEAK_VDO_THR` but either support condition is false

## 11.7 Entry execution
If `enter_t == True` on close of H4 bar `t`:
- schedule one full long entry at `open_(t+1)`

No other entry action exists.

---

## 12. Exit system (winner)

## 12.1 High-level design
Exit winner is:

**`trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`**

That means:

- protective stop exists and is mandatory
- peak anchor is `close`, not `high`
- ATR mode is **current bar** robust ATR, not lagged ATR
- trail breach must occur on **2 consecutive closes**
- EMA cross-down trend exit is fully removed
- after any exit, new entries are blocked for 6 H4 bars
- every trade has a hard 30-bar maximum lifetime

## 12.2 Required exit state variables

Per running simulation, maintain:

- `cash`
- `qty`
- `position_fraction` in `{0,1}`
- `trade_id`
- `full_entry_fill_bar_index`
- `full_entry_fill_price`
- `live_peak_close`
- `trail_breach_streak`
- `last_exit_fill_bar_index`
- `pending_order_type`
- `pending_order_reason`

### Initial state
At simulation start:
- `cash = 10000.0`
- `qty = 0.0`
- `position_fraction = 0`
- `trade_id = 0`
- `full_entry_fill_bar_index = None`
- `full_entry_fill_price = None`
- `live_peak_close = None`
- `trail_breach_streak = 0`
- `last_exit_fill_bar_index = None`
- `pending_order_type = None`
- `pending_order_reason = None`

## 12.3 Entry-fill initialization
When a long entry fills at `open_t`:

- `trade_id += 1`
- `qty = cash_before / (open_t * (1 + SIDE_COST))`
- `cash = 0.0`
- `position_fraction = 1`
- `full_entry_fill_bar_index = t`
- `full_entry_fill_price = open_t`
- `live_peak_close = open_t`
- `trail_breach_streak = 0`

Important:
- `live_peak_close` is initialized to the **entry fill open price**, not to the first close after entry.

## 12.4 Peak anchor
Because this policy uses `peak_anchor = close`, while long:

- `live_peak_close_t = max(live_peak_close_(t-1), close_t)`

`high_t` is deliberately ignored.

## 12.5 Trail stop level
While long on close bar `t`:

- `trail_stop_t = live_peak_close_t - 3.3 * robust_atr_t`

This uses:
- **current** `robust_atr_t`
- not `robust_atr_(t-1)`

## 12.6 Trail breach and confirmation
At close bar `t`, while long, define:

- `trail_breach_t = (close_t < trail_stop_t)`

Strict `<` is required.

Update streak:

- if `trail_breach_t == True`:
  - `trail_breach_streak_t = trail_breach_streak_(t-1) + 1`
- else:
  - `trail_breach_streak_t = 0`

Exit trigger from trail:

- if `trail_breach_streak_t >= 2`:
  - schedule full exit at `open_(t+1)`
  - `pending_order_reason = "trail_stop"`

This is the exact meaning of `confirm2`.

## 12.7 No trend exit
The winner uses:

- `trend_exit = none`

Therefore, while long:
- `ema_fast_t < ema_slow_t` has **no exit effect**
- there is no EMA cross-down exit
- there is no trend-confirmation counter
- there is no recursive decision tree

Entry still uses `trend_up` as part of the entry gate.  
Exit ignores EMA trend-down completely.

## 12.8 Time stop
Let:
- `TIME_STOP_BARS = 30`

Define `entry_fill_bar_index = full_entry_fill_bar_index`.

At close bar `t`, while long, if no trail-stop exit has already been scheduled on that bar, then trigger time stop exactly when:

- `(t + 1) == entry_fill_bar_index + 30`

If true:
- schedule full exit at `open_(t+1)`
- `pending_order_reason = "time_stop"`

Equivalent interpretation:
- the position may be held through close of bar `entry_fill_bar_index + 29`
- if still alive there, it must exit at open of bar `entry_fill_bar_index + 30`

That gives a maximum in-position lifetime of **30 H4 bars**.

## 12.9 Precedence inside the exit stack
On any close bar while long, exit conditions are tested in this order:

1. `trail_breach_streak >= 2`
2. `time_stop`

If both are true on the same bar:
- exit reason must be `trail_stop`

There is no trend-exit branch.

## 12.10 Exit-fill reset
When any exit fills at `open_t`:

- `gross = qty_before * open_t`
- `cash_after = cash_before + gross * (1 - SIDE_COST)`
- `qty = 0.0`
- `position_fraction = 0`
- `full_entry_fill_bar_index = None`
- `full_entry_fill_price = None`
- `live_peak_close = None`
- `trail_breach_streak = 0`
- `last_exit_fill_bar_index = t`

Allowed reasons in combo 1:
- `"trail_stop"`
- `"time_stop"`

---

## 13. Cooldown rule

## 13.1 Definition
Cooldown applies **after every exit fill**, regardless of exit reason.

Frozen parameter:
- `COOLDOWN_BARS = 6`

## 13.2 Exact fill-index rule
When flat and evaluating entry on close bar `t`, the next-open entry fill at `t+1` is allowed **only if**:

- `last_exit_fill_bar_index is None`
- or `(t + 1) > last_exit_fill_bar_index + 6`

Equivalent earliest re-entry:
- if an exit fills at open bar index `e`
- earliest new entry fill is open bar index `e + 7`

Equivalent earliest new entry **decision**:
- close bar index `e + 6`

Any entry signal during cooldown is ignored and not queued.

## 13.3 Consequence
This exact cooldown rule is why combo 1 achieved:

- `re-entry <= 3 bars = 0%`
- `re-entry <= 6 bars = 0%`

in the official end-to-end validation.

---

## 14. Full per-bar state machine

There are only two live states:

1. `FLAT`
2. `LONG_100`

## 14.1 State `FLAT`
At close bar `t`:

1. if bar is not eligible or `t` is the last bar of the slice:
   - do nothing

2. else check cooldown:
   - entry fill at `t+1` is allowed only if:
     - `last_exit_fill_bar_index is None`
     - or `(t+1) > last_exit_fill_bar_index + 6`

3. if cooldown allows, evaluate the frozen entry rule from Section 11

4. if entry rule is true:
   - set:
     - `pending_order_type = "entry"`
     - `pending_order_reason = "entry"`

## 14.2 State `LONG_100`
At close bar `t`:

1. update:
   - `live_peak_close = max(live_peak_close, close_t)`

2. compute:
   - `trail_stop_t = live_peak_close - 3.3 * robust_atr_t`
   - `trail_breach_t = (close_t < trail_stop_t)`

3. update streak:
   - if breach: `trail_breach_streak += 1`
   - else: `trail_breach_streak = 0`

4. if `trail_breach_streak >= 2`:
   - schedule full exit at `open_(t+1)`
   - reason = `"trail_stop"`

5. else if `(t+1) == full_entry_fill_bar_index + 30`:
   - schedule full exit at `open_(t+1)`
   - reason = `"time_stop"`

6. else:
   - hold

No trend-down EMA exit is evaluated.

---

## 15. Full pseudocode (reference)

```python
for each H4 bar index t in chronological order:

    # --- 1) execute pending order at bar open ---
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
            trail_breach_streak = 0

        elif pending_order_type == "exit":
            gross = qty * open_price
            cash = cash + gross * (1 - SIDE_COST)
            qty = 0.0
            position_fraction = 0

            full_entry_fill_bar_index = None
            full_entry_fill_price = None
            live_peak_close = None
            trail_breach_streak = 0
            last_exit_fill_bar_index = t

        pending_order_type = None
        pending_order_reason = None

    # --- 2) mark equity to bar close ---
    equity_t = cash + qty * close[t]

    # --- 3) no decision if last bar or ineligible ---
    if t == last_bar_index_of_slice:
        continue
    if close_dt[t] < eligible_from:
        continue

    # --- 4) flat state: entry only ---
    if qty == 0.0:
        cooldown_ok = (
            last_exit_fill_bar_index is None
            or (t + 1) > last_exit_fill_bar_index + 6
        )

        if cooldown_ok:
            trend_up = ema_fast[t] > ema_slow[t]
            regime_ok = mapped_d1_regime_ok[t]

            if trend_up and regime_ok:
                vdo = VDO[t]

                if vdo > 0.0065:
                    pending_order_type = "entry"
                    pending_order_reason = "entry"

                elif 0.0 < vdo <= 0.0065:
                    activity_support = activity_score[t] >= 1.0
                    freshness_support = freshness_score[t] <= 0.0

                    if activity_support and freshness_support:
                        pending_order_type = "entry"
                        pending_order_reason = "entry"

        continue

    # --- 5) long state: exit only ---
    live_peak_close = max(live_peak_close, close[t])
    trail_stop = live_peak_close - 3.3 * robust_atr[t]

    breach = close[t] < trail_stop
    if breach:
        trail_breach_streak += 1
    else:
        trail_breach_streak = 0

    if trail_breach_streak >= 2:
        pending_order_type = "exit"
        pending_order_reason = "trail_stop"

    elif (t + 1) == full_entry_fill_bar_index + 30:
        pending_order_type = "exit"
        pending_order_reason = "time_stop"

    else:
        pass
```

---

## 16. Accounting and mark-to-market

## 16.1 Entry fill accounting
At entry fill on `open_t`:

- `qty = cash_before / (open_t * (1 + SIDE_COST))`
- `cash_after = 0.0`

This implies all available cash is deployed, including entry fee.

## 16.2 Exit fill accounting
At exit fill on `open_t`:

- `gross = qty_before * open_t`
- `cash_after = cash_before + gross * (1 - SIDE_COST)`

Since `cash_before = 0` while fully long, this is equivalent to:

- `cash_after = qty_before * open_t * (1 - SIDE_COST)`

## 16.3 Equity at close
At each close bar `t`:

- `equity_t = cash_t + qty_t * close_t`

This close-marked equity is the series used for:
- bar returns
- Sharpe
- MDD
- exposure calculations

## 16.4 No forced liquidation at final bar
At the end of a validation slice:
- leave any open trade marked to close
- do **not** force an end-of-slice liquidation

This is required to reproduce the official `trades` vs `closed_trades` counts.

---

## 17. Validation protocol (official acceptance harness)

This section defines the exact end-to-end validation protocol used to accept combo 1.

## 17.1 Four OOS folds
Use the following 4 OOS folds:

1. **Fold 1**
   - `2021-07-01 00:00:00 UTC` to `2022-12-31 23:59:59.999 UTC`

2. **Fold 2**
   - `2023-01-01 00:00:00 UTC` to `2024-06-30 23:59:59.999 UTC`

3. **Fold 3**
   - `2024-07-01 00:00:00 UTC` to `2025-06-30 23:59:59.999 UTC`

4. **Fold 4**
   - `2025-07-01 00:00:00 UTC` to `2026-02-28 23:59:59.999 UTC`

For the supplied dataset, the corresponding H4 close-index ranges are:

- Fold 1: `8466 .. 11759`
- Fold 2: `11760 .. 15041`
- Fold 3: `15042 .. 17231`
- Fold 4: `17232 .. 18689`

## 17.2 Fold reset semantics
At the start of each OOS fold:

- start **flat**
- `cash = 10000.0`
- `qty = 0.0`
- `position_fraction = 0`
- `pending_order_type = None`
- `pending_order_reason = None`
- `trade_id = 0` (or reset per fold if fold-local IDs are used)
- `last_exit_fill_bar_index = None`
- no carry of any open position or pending order from the prior fold

Important:
- indicator history is still computed on the full dataset before fold start
- only portfolio state is reset

## 17.3 Official baselines
The official non-ML baselines are:

### Baseline A (combo 3)
Frozen entry + original base exit:

- entry = frozen weak-VDO rule
- exit = base exit:
  - trail stop `3.0 * current robust ATR`
  - close peak anchor
  - no trail confirmation (effectively confirm1)
  - trend exit on `ema_fast < ema_slow`
  - no cooldown
  - no time stop

### Baseline B (combo 4)
Original entry + original base exit:

- entry = `trend_up AND regime_ok AND (VDO > 0)`
- exit = same base exit as above

## 17.4 Official metrics
For each fold:
- build close-marked equity series
- compute close-to-close bar returns:
  - `ret_t = equity_t / equity_(t-1) - 1`
  - first return of each fold = `0.0`

Aggregate stitched-OOS series:
- concatenate fold return vectors in fold order
- compute aggregate metrics on this stitched return vector

### 17.4.1 Sharpe
- `Sharpe = mean(bar_returns) / std(bar_returns, ddof=0) * sqrt(365.25 * 6)`

### 17.4.2 End equity multiple
- `end_equity = product(1 + stitched_bar_returns)`

### 17.4.3 CAGR
Use:
- `years = (bar_count - 1) / (365.25 * 6)`

Then:
- `CAGR = end_equity ** (1 / years) - 1`

### 17.4.4 MDD
On the stitched equity curve:
- `MDD = min( equity / cumulative_max(equity) - 1 )`

### 17.4.5 Exposure
- `exposure = mean(position_fraction_after_open_fill_marked_through_bar_close)`
- equivalently on the validated engine:
  - fraction of counted OOS bars whose close-marked portfolio was long

---

## 18. Official acceptance targets for combo 1

A correct rebuild should reproduce approximately the following values.

### 18.1 Aggregate stitched OOS — combo 1
- `Sharpe = 1.7958240267954706`
- `CAGR = 0.5669140340440590`
- `MDD = -0.2847041449518986`
- `bar_count = 10224`
- `end_equity = 8.125587882832642`
- `trades = 122`
- `closed_trades = 121`
- `exposure = 0.3055555555555556`

### 18.2 Fold-level OOS — combo 1

| fold | Sharpe | CAGR | MDD | trades | closed_trades | exposure |
|---|---:|---:|---:|---:|---:|---:|
| fold1 | `1.6910214277580962` | `0.5341892626385096` | `-0.2379029296102133` | `28` | `28` | `0.2216150576806314` |
| fold2 | `1.8611140268623398` | `0.6557935990458621` | `-0.2847041449518990` | `49` | `49` | `0.3668494820231566` |
| fold3 | `2.2842856084485310` | `0.8521942020154314` | `-0.1921421175155594` | `32` | `31` | `0.3863013698630137` |
| fold4 | `0.8956505477176805` | `0.1299767936832199` | `-0.1202608071542969` | `13` | `13` | `0.2359396433470508` |

### 18.3 Official baselines for comparison

#### Combo 3 — frozen entry + base exit
- `Sharpe = 1.3404104320598558`
- `CAGR = 0.4125709635076083`
- `MDD = -0.2856178360798716`
- `trades = 104`
- `closed_trades = 103`
- `exposure = 0.3745109546165884`

#### Combo 4 — original entry + base exit
- `Sharpe = 1.1307597999722059`
- `CAGR = 0.3503025443385248`
- `MDD = -0.3709393067151730`
- `trades = 118`
- `closed_trades = 117`
- `exposure = 0.4092331768388107`

### 18.4 Validation summary that combo 1 passed
Against combo 3, combo 1 passed the project-standard end-to-end bar:

- **WFO**: `4 / 4` positive folds
- **Bootstrap** `P(delta Sharpe > 0)` across circular block lengths `12, 24, 48, 72, 144, 288`:
  - from `0.946667` to `0.982500`
- **Cost sweep**:
  - wins `9 / 9` tested costs from `0` to `100 bps/side`
  - retains `>= 3 / 4` positive folds at all `9 / 9` tested costs
- **Exposure trap**:
  - tight control `prob(control >= candidate) = 0.042`
- **Churn**:
  - `re-entry <= 3 bars = 0%`
  - `re-entry <= 6 bars = 0%`
- **Timing-permutation null p-value**:
  - `0.000832639`

These are validation results, not additional deployment rules.

---

## 19. Known caveats

## 19.1 Post-2021 structure caveat
This system should be described as a **post-2021 favorable system**, not a timeless law.

Official diagnostic result under the same frozen entry:

### Pre-2021 diagnostic
- combo 1:
  - `Sharpe = 0.972395`
  - `CAGR = 0.363438`
  - `MDD = -0.376299`
  - `trades = 96`
  - `exposure = 0.369811`

- frozen-entry base-exit baseline:
  - `Sharpe = 1.787090`
  - `CAGR = 0.991634`
  - `MDD = -0.366178`
  - `trades = 70`
  - `exposure = 0.433593`

Read:
- combo 1 is materially better in the official post-2021 OOS regime,
- but it is not a timeless all-history rule.

## 19.2 Frozen approximation caveat
The entry winner originally came from a fold-adaptive research threshold.  
Deployment uses the frozen approximation:

- `WEAK_VDO_THR = 0.0065`

This is deliberate and must remain frozen unless a new freeze-form study is performed.

Do **not** replace it with:
- per-fold train medians
- trailing online median
- adaptive thresholds
- percentile retuning

without a new end-to-end validation cycle.

## 19.3 Exit-coupling caveat
Combo 1’s exit winner is price/time-only and was validated with the frozen entry above.  
If future work changes either:
- entry motif,
- exit family,
- or reintroduces volume-derived exit logic,

the full end-to-end system must be re-validated from scratch.

## 19.4 Horizon caveat
The exit edge is structurally tied to the time-cap family around 30 H4 bars.

Do not treat `TIME_STOP_BARS = 30` as a nuisance default.  
It is a real structural parameter of the accepted system.

---

## 20. Minimal implementation checklist

A rebuild is correct only if all of the following are true:

1. EMA convention matches Section 7 exactly.
2. D1 regime uses backward `merge_asof` on `close_time`.
3. Robust ATR uses:
   - TR definition from Section 10.1
   - 100-bar 90th-percentile cap with `method="linear"`
   - Wilder ATR(20) seeded at index `119`.
4. `imbalance_ratio_base` uses base taker flow and total base volume.
5. `VDO = EMA12(imbalance_ratio_base) - EMA28(imbalance_ratio_base)`.
6. `activity_support = EMA12(quote_volume / EMA28(quote_volume)) >= 1.0`.
7. `freshness_support = EMA28(imbalance_ratio_base) <= 0.0`.
8. `WEAK_VDO_THR` is hard-coded to `0.0065`.
9. Entry is decided on H4 close and filled next open.
10. Exit uses:
    - `trail_mult = 3.3`
    - `peak_anchor = close`
    - `atr_mode = current`
    - `trail_confirm_bars = 2`
    - `trend_exit = none`
    - `cooldown_bars = 6`
    - `time_stop_bars = 30`
11. Trail breach uses strict `<` and resets the streak to zero on any non-breach bar.
12. Time stop triggers on condition `(t + 1) == entry_fill_bar_index + 30`.
13. Cooldown allows a new entry fill only when `(t + 1) > last_exit_fill_bar_index + 6`.
14. No forced liquidation at fold end / cutoff.
15. Aggregate OOS acceptance targets from Section 18 are matched within normal floating-point tolerance.

---

## 21. One-line summary

**Trade long only when trend, regime, and frozen weak-VDO entry conditions are satisfied; once long, ignore trend exits, protect with a close-anchored current-ATR trail that needs two consecutive close breaches, force an exit after 30 H4 bars if still alive, and enforce a 6-bar cooldown after every exit.**
