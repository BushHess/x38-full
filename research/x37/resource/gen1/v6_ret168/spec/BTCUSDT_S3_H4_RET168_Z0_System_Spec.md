# BTCUSDT Frozen System Specification — `S3_H4_RET168_Z0`

## Document purpose

This document is a complete standalone implementation specification for the frozen winner `S3_H4_RET168_Z0`. It is written so that an engineer can reimplement the system from scratch and reproduce the same signals, entries, exits, and completed-trade PnL from the raw files alone.

This system is the frozen pre-reserve winner exported in the run's machine-readable artifact `frozen_system.json`. There was no separate machine-readable file named `final_practical_system.json` in the artifact bundle. The frozen winner itself is unambiguous: `S3_H4_RET168_Z0`.

## Required input files

### File 1: raw H4 file — required by this system

- expected content: native BTC/USDT H4 bars
- expected `interval` value: `4h`
- expected row count in the supplied run: 18,791

### File 2: raw D1 file — not used by this system, but schema included for completeness

- expected content: native BTC/USDT D1 bars
- expected `interval` value: `1d`
- expected row count in the supplied run: 3,134

### Required schema for both files

| column              | type    | required   | description                                                        |
|:--------------------|:--------|:-----------|:-------------------------------------------------------------------|
| symbol              | string  | yes        | instrument symbol; all rows in supplied files are BTCUSDT          |
| interval            | string  | yes        | bar interval literal; H4 file contains `4h`, D1 file contains `1d` |
| open_time           | int64   | yes        | UTC bar open timestamp in Unix epoch milliseconds                  |
| close_time          | int64   | yes        | UTC bar close timestamp in Unix epoch milliseconds                 |
| open                | float64 | yes        | bar open price                                                     |
| high                | float64 | yes        | bar high price                                                     |
| low                 | float64 | yes        | bar low price                                                      |
| close               | float64 | yes        | bar close price                                                    |
| volume              | float64 | yes        | base-asset traded volume during bar                                |
| quote_volume        | float64 | yes        | quote-asset traded volume during bar                               |
| num_trades          | int64   | yes        | trade count during bar                                             |
| taker_buy_base_vol  | float64 | yes        | base-asset volume of taker buys during bar                         |
| taker_buy_quote_vol | float64 | yes        | quote-asset volume of taker buys during bar                        |

## Scope of the frozen system

- candidate ID: `S3_H4_RET168_Z0`
- market: BTC/USDT spot
- direction: long-only
- execution frame: native H4 only
- D1 dependency: none
- regime gate: none
- leverage: none
- pyramiding: no
- position sizes: either 100% long or 100% cash

## Time and bar conventions

- timezone: UTC only
- bars are identified by raw `open_time` and raw `close_time`
- signal is computed at H4 bar close
- execution happens at the next H4 bar open
- bar alignment uses the retained raw row order after stable sorting by `open_dt`, then `close_dt`
- H4 rows are **not** repaired for shortened durations or gaps
- the duplicate zero-duration H4 row is retained and counts toward row-based lookbacks
- the system starts live scoring at `2020-01-01 00:00:00+00:00`
- rows before `2020-01-01 00:00:00+00:00` may be used only for history warmup, not for live positions

## Exact preprocessing order

### Step 1 — Parse and sort

1. parse `open_time` and `close_time` as UTC datetimes called `open_dt` and `close_dt`
2. stable-sort ascending by `open_dt`, then `close_dt`
3. reset row index to a zero-based integer index

### Step 2 — Retain raw anomalies unchanged

Do not drop, fill, merge, or normalize:

- 19 shortened H4 rows
- 8 H4 timing gaps
- the 1 duplicate zero-duration H4 row

### Step 3 — Compute the feature on the retained full H4 frame

For every sorted H4 row `t`:

`ret168_t = close_t / close_(t-168) - 1`

This is a row-count shift on the retained sorted H4 frame. It is **not** a time-based 28-day return. Removing the duplicate row or filling gaps would change `close_(t-168)` and therefore change the signal.

## Exact signal logic

### Signal formula

For every sorted H4 row `t`:

- price field used: `close`
- lookback: 168 retained H4 rows
- feature: `ret168_t = close_t / close_(t-168) - 1`
- signal decision at row `t` close:
  - long if `ret168_t > 0`
  - flat if `ret168_t <= 0`
  - flat if `ret168_t` is `NaN`

### Strict comparison rule

The comparison is strict greater-than:

- `ret168_t > 0` produces signal `1`
- `ret168_t == 0` produces signal `0`
- `ret168_t < 0` produces signal `0`
- `ret168_t = NaN` produces signal `0`

## Exact entry and exit rules

### Live-start rule

No live trade may exist before the first H4 row whose `open_dt >= 2020-01-01 00:00:00+00:00`.

### State machine

- entry rule: if signal changes `0 -> 1` at H4 close on row `t`, buy at H4 open on row `t+1`
- hold rule: stay long while the close-time signal remains `1`
- exit rule: if signal changes `1 -> 0` at H4 close on row `t`, sell at H4 open on row `t+1`
- direction: long-flat only; short positions are never allowed

### Position vector used for execution

Define the live H4 slice as all sorted H4 rows with `open_dt >= 2020-01-01 00:00:00+00:00`. Index those live rows by `j = 0, 1, 2, ...`.

- `position_0 = 0`
- for `j >= 1`, `position_j = signal_(j-1)` where `signal_(j-1)` means the signal computed on the immediately previous live H4 row close

Interpretation:

- `position_j` is the position held during the interval from `open_j` to `open_(j+1)`
- entry and exit happen exactly at `open_j` when `position_j` differs from `position_(j-1)`

## Exact position sizing

- when long: gross exposure = `1.0`
- when flat: gross exposure = `0.0`
- leverage = `0.0` in the frozen JSON, which means no borrowed exposure beyond the 100% cash-to-spot allocation
- no fractional scaling
- no pyramiding
- no partial exits

## Exact regime gate

There is no regime gate.

- no D1 gate
- no epoch gate
- no conditional parameter switch
- no external filter

The system is a pure native-H4 one-feature state machine.

## Exact cost model

### Base cost model

- entry cost: 10 bps = `0.001`
- exit cost: 10 bps = `0.001`
- round-trip cost: 20 bps

### Completed trade PnL formula

For a completed trade entered at price `E` and exited at price `X`:

`trade_return = X * (1 - 0.001) / (E * (1 + 0.001)) - 1`

This is multiplicative, not an arithmetic subtraction of 20 bps from raw return.

### Interval multiplier formula for full-path simulation

On live H4 row `j`, let `prev_position = position_(j-1)` with `prev_position = 0` for `j = 0`.

- if `prev_position = 0` and `position_j = 1`, interval multiplier from `open_j` to `open_(j+1)` is:
  - `(1 / 1.001) * open_(j+1) / open_j`
- if `prev_position = 1` and `position_j = 1`, interval multiplier is:
  - `open_(j+1) / open_j`
- if `prev_position = 1` and `position_j = 0`, interval multiplier is:
  - `0.999`
- if `prev_position = 0` and `position_j = 0`, interval multiplier is:
  - `1.0`

No interval multiplier exists on the final live H4 row if there is no `open_(j+1)`.

### Stress cost model used only in validation, not in the frozen live rule

- 25 bps per side
- 50 bps round-trip

## Edge-case handling

### Shortened bars

Retain every shortened H4 bar exactly as supplied. Feature calculation uses the retained row count. Execution uses the next available raw open. Do not normalize duration to 4 hours.

### Gaps between bars

Retain every gap exactly as supplied. Do not fill missing bars. If the next raw H4 bar is 8 hours or 32 hours later, that next raw H4 open is still the next executable open.

### Missing data

If any field needed for `ret168` is missing or if there are fewer than 168 prior retained H4 rows, set `ret168 = NaN` and signal = `0`.

### Insufficient history

Rows with fewer than 168 prior retained H4 rows are flat. This includes the retained duplicate zero-duration row in early history.

### Duplicate rows

Do not drop duplicate timestamps. The one duplicate zero-duration H4 row remains in the sorted series and affects the row-count position of every later `shift(168)`.

### Dataset end

Do **not** force a final liquidation at dataset end.

- a trade still open on the last row remains open
- `open_trade_count` increases by 1
- `exit_idx`, `exit_time`, `exit_open`, and `trade_return` stay `NaN` in the open-trade ledger row
- realized performance stops at the last available interval ending at the final observed next open

## Optional validation outputs if reproducing the research metrics

These outputs are not needed to generate the raw trading logic, but they were part of the research run.

### Daily returns

For UTC day `D`, daily return is:

`product(interval_multiplier_j for all live H4 rows j with open_dt.floor('D') == D) - 1`

### Daily exposure

For UTC day `D`, daily exposure is:

`mean(position_j for all live H4 rows j with open_dt.floor('D') == D)`

### Completed-trade ledger fields

For each completed trade:

- `entry_idx`: live-row index of the entry open
- `exit_idx`: live-row index of the exit open
- `entry_time`
- `exit_time`
- `entry_open`
- `exit_open`
- `trade_return`
- `holding_bars = exit_idx - entry_idx`
- `holding_days = holding_bars * 4 / 24`

## Canonical warmup/live boundary for this system

- last pre-live H4 row: raw sorted H4 row 5185, `open_dt = 2019-12-31 20:00:00+00:00`
- first live H4 row: raw sorted H4 row 5186, `open_dt = 2020-01-01 00:00:00+00:00`

The first possible live entry cannot occur until the next open after the first live row close.

## Test vectors

The following cases are sufficient to verify a bit-level implementation of the signal, state machine, retained-row semantics, and trade-return formula.

### Test case 1

Input rows:

- entry-trigger row: live index `0`, raw sorted H4 row `5186`
  - `open_dt = 2020-01-01T00:00:00Z`
  - `close_dt = 2020-01-01T03:59:59.999000Z`
  - `OHLC = (7195.24, 7245.0, 7175.46, 7225.01)`
  - `ret168 = 0.010421663410480`
- exit-trigger row: live index `2`, raw sorted H4 row `5188`
  - `open_dt = 2020-01-01T08:00:00Z`
  - `close_dt = 2020-01-01T11:59:59.999000Z`
  - `OHLC = (7209.83, 7237.73, 7180.0, 7197.2)`
  - `ret168 = -0.000436090517948`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-01-01T04:00:00Z`
- entry price: `7225.0`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-01-01T12:00:00Z`
- exit price: `7197.2`
- holding bars: `2`
- completed trade return after 10 bps entry + 10 bps exit: `-0.005838065049138`
### Test case 2

Input rows:

- entry-trigger row: live index `5`, raw sorted H4 row `5191`
  - `open_dt = 2020-01-01T20:00:00Z`
  - `close_dt = 2020-01-01T23:59:59.999000Z`
  - `OHLC = (7229.48, 7242.98, 7175.15, 7200.85)`
  - `ret168 = 0.000907660487718`
- exit-trigger row: live index `6`, raw sorted H4 row `5192`
  - `open_dt = 2020-01-02T00:00:00Z`
  - `close_dt = 2020-01-02T03:59:59.999000Z`
  - `OHLC = (7200.77, 7212.5, 7120.37, 7129.61)`
  - `ret168 = -0.013011517802758`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-01-02T00:00:00Z`
- entry price: `7200.77`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-01-02T04:00:00Z`
- exit price: `7129.25`
- holding bars: `1`
- completed trade return after 10 bps entry + 10 bps exit: `-0.011910428432550`
### Test case 3

Input rows:

- entry-trigger row: live index `14`, raw sorted H4 row `5200`
  - `open_dt = 2020-01-03T08:00:00Z`
  - `close_dt = 2020-01-03T11:59:59.999000Z`
  - `OHLC = (7202.28, 7371.92, 7202.28, 7340.46)`
  - `ret168 = 0.000245276385607`
- exit-trigger row: live index `15`, raw sorted H4 row `5201`
  - `open_dt = 2020-01-03T12:00:00Z`
  - `close_dt = 2020-01-03T15:59:59.999000Z`
  - `OHLC = (7340.46, 7380.0, 7229.3, 7320.18)`
  - `ret168 = -0.007446678689103`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-01-03T12:00:00Z`
- entry price: `7340.46`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-01-03T16:00:00Z`
- exit price: `7320.17`
- holding bars: `1`
- completed trade return after 10 bps entry + 10 bps exit: `-0.004756611204981`
### Test case 4

Input rows:

- entry-trigger row: live index `24`, raw sorted H4 row `5210`
  - `open_dt = 2020-01-05T00:00:00Z`
  - `close_dt = 2020-01-05T03:59:59.999000Z`
  - `OHLC = (7354.19, 7482.87, 7354.11, 7475.99)`
  - `ret168 = 0.009735396567489`
- exit-trigger row: live index `26`, raw sorted H4 row `5212`
  - `open_dt = 2020-01-05T08:00:00Z`
  - `close_dt = 2020-01-05T11:59:59.999000Z`
  - `OHLC = (7463.64, 7472.0, 7400.0, 7422.33)`
  - `ret168 = -0.012991969446930`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-01-05T04:00:00Z`
- entry price: `7476.0`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-01-05T12:00:00Z`
- exit price: `7422.27`
- holding bars: `2`
- completed trade return after 10 bps entry + 10 bps exit: `-0.009170640755713`
### Test case 5

Input rows:

- entry-trigger row: live index `30`, raw sorted H4 row `5216`
  - `open_dt = 2020-01-06T00:00:00Z`
  - `close_dt = 2020-01-06T03:59:59.999000Z`
  - `OHLC = (7357.64, 7580.0, 7346.76, 7540.9)`
  - `ret168 = 0.004071730631984`
- exit-trigger row: live index `335`, raw sorted H4 row `5521`
  - `open_dt = 2020-02-26T00:00:00Z`
  - `close_dt = 2020-02-26T03:59:59.999000Z`
  - `OHLC = (9316.48, 9377.44, 9111.0, 9170.13)`
  - `ret168 = -0.021770367849664`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-01-06T04:00:00Z`
- entry price: `7540.9`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-02-26T04:00:00Z`
- exit price: `9170.13`
- holding bars: `305`
- completed trade return after 10 bps entry + 10 bps exit: `0.213622785335711`
### Test case 6

Input rows:

- entry-trigger row: live index `595`, raw sorted H4 row `5781`
  - `open_dt = 2020-04-09T08:00:00Z`
  - `close_dt = 2020-04-09T11:59:59.999000Z`
  - `OHLC = (7329.99, 7349.0, 7150.0, 7183.98)`
  - `ret168 = 0.184105514907673`
- exit-trigger row: live index `887`, raw sorted H4 row `6073`
  - `open_dt = 2020-05-28T00:00:00Z`
  - `close_dt = 2020-05-28T03:59:59.999000Z`
  - `OHLC = (9204.07, 9280.78, 9155.67, 9172.91)`
  - `ret168 = -0.012495451599637`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-04-09T12:00:00Z`
- entry price: `7184.0`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-05-28T04:00:00Z`
- exit price: `9171.6`
- holding bars: `292`
- completed trade return after 10 bps entry + 10 bps exit: `0.274119588651883`
### Test case 7

Input rows:

- entry-trigger row: live index `889`, raw sorted H4 row `6075`
  - `open_dt = 2020-05-28T08:00:00Z`
  - `close_dt = 2020-05-28T11:59:59.999000Z`
  - `OHLC = (9150.06, 9280.0, 9110.0, 9266.89)`
  - `ret168 = 0.048334602240139`
- exit-trigger row: live index `933`, raw sorted H4 row `6119`
  - `open_dt = 2020-06-04T16:00:00Z`
  - `close_dt = 2020-06-04T19:59:59.999000Z`
  - `OHLC = (9829.4, 9881.63, 9725.0, 9817.64)`
  - `ret168 = -0.004692855687338`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-05-28T12:00:00Z`
- entry price: `9267.22`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-06-04T20:00:00Z`
- exit price: `9817.65`
- holding bars: `44`
- completed trade return after 10 bps entry + 10 bps exit: `0.057278700158658`
### Test case 8

Input rows:

- entry-trigger row: live index `942`, raw sorted H4 row `6128`
  - `open_dt = 2020-06-06T04:00:00Z`
  - `close_dt = 2020-06-06T07:59:59.999000Z`
  - `OHLC = (9636.17, 9640.0, 9580.0, 9609.84)`
  - `ret168 = 0.001779465159698`
- exit-trigger row: live index `944`, raw sorted H4 row `6130`
  - `open_dt = 2020-06-06T12:00:00Z`
  - `close_dt = 2020-06-06T15:59:59.999000Z`
  - `OHLC = (9693.85, 9735.0, 9625.33, 9651.67)`
  - `ret168 = -0.003813752629374`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-06-06T08:00:00Z`
- entry price: `9609.85`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-06-06T16:00:00Z`
- exit price: `9651.59`
- holding bars: `2`
- completed trade return after 10 bps entry + 10 bps exit: `0.002336779855680`
### Test case 9

Input rows:

- entry-trigger row: live index `946`, raw sorted H4 row `6132`
  - `open_dt = 2020-06-06T20:00:00Z`
  - `close_dt = 2020-06-06T23:59:59.999000Z`
  - `OHLC = (9658.15, 9729.74, 9633.7, 9666.3)`
  - `ret168 = 0.013302723441726`
- exit-trigger row: live index `974`, raw sorted H4 row `6160`
  - `open_dt = 2020-06-11T12:00:00Z`
  - `close_dt = 2020-06-11T15:59:59.999000Z`
  - `OHLC = (9787.58, 9796.29, 9502.0, 9521.11)`
  - `ret168 = -0.023373727302754`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-06-07T00:00:00Z`
- entry price: `9666.85`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-06-11T16:00:00Z`
- exit price: `9521.54`
- holding bars: `28`
- completed trade return after 10 bps entry + 10 bps exit: `-0.016999752343737`
### Test case 10

Input rows:

- entry-trigger row: live index `981`, raw sorted H4 row `6167`
  - `open_dt = 2020-06-12T16:00:00Z`
  - `close_dt = 2020-06-12T19:59:59.999000Z`
  - `OHLC = (9417.98, 9457.99, 9301.0, 9431.21)`
  - `ret168 = 0.010000182055145`
- exit-trigger row: live index `985`, raw sorted H4 row `6171`
  - `open_dt = 2020-06-13T08:00:00Z`
  - `close_dt = 2020-06-13T11:59:59.999000Z`
  - `OHLC = (9437.69, 9470.0, 9380.0, 9405.1)`
  - `ret168 = -0.001001643204706`

Expected outputs:

- signal on entry-trigger close: `1`
- action at next open: `BUY`
- entry next-open time: `2020-06-12T20:00:00Z`
- entry price: `9431.11`
- signal on exit-trigger close: `0`
- action at next open: `SELL`
- exit next-open time: `2020-06-13T12:00:00Z`
- exit price: `9405.13`
- holding bars: `4`
- completed trade return after 10 bps entry + 10 bps exit: `-0.004747210936090`


### Edge case E1 — retained duplicate zero-duration row

Input row:

- raw sorted H4 row `123`
- `open_dt = 2017-09-06T16:00:00Z`
- `close_dt = 2017-09-06T16:00:00Z`
- `OHLC = (4619.43, 4619.43, 4619.43, 4619.43)`
- `volume = 0.0`
- `num_trades = 0`

Expected outputs:

- `ret168 = NaN`
- signal = `0`
- no trade action
- no de-duplication
- this row remains in the retained row count and therefore affects later `shift(168)` indexing exactly as in the original run
### Edge case E2

Input row:

- raw sorted H4 row `5482`
- `open_dt = 2020-02-19T08:00:00Z`
- `close_dt = 2020-02-19T11:35:32.286000Z`
- `OHLC = (10059.08, 10161.99, 10011.06, 10148.93)`
- `ret168 = 0.171949463444601`

Expected outputs:

- signal on this row close = `1`
- position during the next interval = `1`
- next raw open used by the engine = `2020-02-19T16:00:00Z` at price `10149.99`
- interval multiplier on that retained raw interval = `1.009037605824787`
- expected action = `hold`
- reason = `shortened live bar retained; signal remains 1`
### Edge case E3

Input row:

- raw sorted H4 row `5483`
- `open_dt = 2020-02-19T16:00:00Z`
- `close_dt = 2020-02-19T19:59:59.999000Z`
- `OHLC = (10149.99, 10250.0, 10131.25, 10139.22)`
- `ret168 = 0.171436922973830`

Expected outputs:

- signal on this row close = `1`
- position during the next interval = `1`
- next raw open used by the engine = `2020-02-19T20:00:00Z` at price `10138.59`
- interval multiplier on that retained raw interval = `0.998876846184085`
- expected action = `hold`
- reason = `8-hour gap after shortened bar retained; signal remains 1`


## Minimal implementation checklist

An implementation matches the frozen system if and only if it does all of the following:

1. parses and stable-sorts the raw H4 file by `open_dt`, then `close_dt`
2. retains the shortened bars, gaps, and duplicate zero-duration row unchanged
3. computes `ret168` as a retained-row-count shift on `close`
4. sets signal to `1` only when `ret168 > 0`
5. stays flat before `2020-01-01 00:00:00+00:00`
6. executes entries and exits only at the next H4 open
7. sizes at exactly 100% long or 0% cash
8. applies 10 bps on entry and 10 bps on exit multiplicatively
9. does not force-close an open trade on the final row
10. never uses the D1 file for this frozen system

Any implementation that fills missing bars, removes the duplicate row, shifts by elapsed time instead of row count, uses close-to-close returns, uses same-bar fills, or subtracts costs arithmetically instead of multiplicatively will not reproduce the frozen winner.
