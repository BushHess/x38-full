# Spec 2 — System Specification (Frozen winner `S_D1_TREND`)

## 1. Purpose

This document defines the final frozen trading system `S_D1_TREND` with enough precision for an engineer to reimplement it from the raw native D1 CSV and achieve bit-level matching output.

The system is a native D1, long-only, long/flat BTC/USDT spot system. It uses exactly one signal. There is no second layer, no regime gate, no volatility filter, no cross-timeframe dependence, and no parameter calibration from data.

## 2. Expected input file schema

The implementation needs the raw native D1 CSV. The raw native H4 CSV is not used by the frozen system itself, but the full research run used both raw files and both files share the same schema.

The D1 CSV must contain these 13 columns, in this order:

1. `symbol`
2. `interval`
3. `open_time`
4. `close_time`
5. `open`
6. `high`
7. `low`
8. `close`
9. `volume`
10. `quote_volume`
11. `num_trades`
12. `taker_buy_base_vol`
13. `taker_buy_quote_vol`

Field rules:

- `open_time` and `close_time` are integer milliseconds since Unix epoch.
- Interpret all timestamps as UTC.
- The D1 file must have `interval = 1d`.
- Observed native D1 file quality in the frozen run:
  - 3,134 rows
  - date coverage 2017-08-17 through 2026-03-16
  - zero duplicate `open_time`
  - zero duplicate `close_time`
  - zero nulls
  - zero malformed rows
  - zero nonstandard durations
  - zero irregular gaps
  - zero zero-activity rows
  - zero impossible OHLC rows

## 3. Native D1 preprocessing

### Input
The raw native D1 CSV.

### Logic
1. Parse `open_time` and `close_time` as UTC timestamps.
2. Sort rows ascending by `open_time`.
3. Preserve every row exactly as supplied.
4. Do not resample.
5. Do not fill missing bars.
6. Do not remove duplicates even if a future file ever contains them; retain and log.
7. Do not invent bars or prices if a future file ever contains gaps; use the next available native open.

### Output
One sorted native D1 frame.

### Decision rule
The frozen `S_D1_TREND` system uses only this D1 frame. H4 anomalies are irrelevant to the system because the system never touches H4 data.

## 4. System architecture

- system ID: `S_D1_TREND`
- evidence label: `INTERNAL ROBUST CANDIDATE`
- layers: 1
- logic type: single-feature state system
- execution timeframe: native D1
- native timeframe: D1
- cross-timeframe dependence: none
- market: BTC/USDT spot
- directionality: long-only
- position sizing: 100% long when active, 0% when inactive
- leverage: none
- pyramiding: none
- discretionary overrides: none
- threshold calibration mode: fixed structural
- threshold value: 0.0
- threshold tuning from training data: none

## 5. Exact signal formula

### Signal feature
`D1_MOM_RET(n=40) = close_t / close_(t-40) - 1`

Definitions:

- `close_t` is the close of the current completed native D1 bar.
- `close_(t-40)` is the close of the native D1 bar 40 bars earlier.
- This is a simple arithmetic return.
- No logarithm is used in this feature.
- No normalization is used in this feature.
- The lookback uses completed D1 bars only.
- The lookback window is inclusive of the current completed bar and reaches exactly 40 bars backward.

### Signal state
On completed day `t`:

- `signal_t = 1` if `D1_MOM_RET(t, 40) > 0.0`
- `signal_t = 0` if `D1_MOM_RET(t, 40) <= 0.0`
- `signal_t = undefined` if fewer than 40 prior completed bars exist

Strict threshold rule:

- equality to zero is **flat**, not long
- the long condition is strict `>` only

## 6. Entry, hold, and exit rules

### Observation time
Compute the signal at the close of the completed D1 bar.

### Execution time
Apply the resulting state at the next D1 bar open.

### State machine
On day `t` open, the held position is determined by the signal computed from completed day `t−1`.

Equivalent rules:

- be **long** during day `t` if `D1_MOM_RET` computed on completed day `t−1` is `> 0.0`
- be **flat** during day `t` if `D1_MOM_RET` computed on completed day `t−1` is `<= 0.0`

This is a long-only / long-flat state system.

There is no separate regime gate. The `D1_MOM_RET(40) > 0.0` condition is the entire system.

## 7. Exact implementation pseudocode

```python
# input: native D1 rows sorted by open_time ascending
# each row i has open_i, close_i, open_time_i, close_time_i

for i in range(len(rows)):
    if i < 40:
        mom40[i] = NaN
        signal[i] = NaN
    else:
        mom40[i] = close[i] / close[i - 40] - 1.0
        signal[i] = 1 if mom40[i] > 0.0 else 0

for i in range(len(rows)):
    if i == 0:
        position[i] = 0
    else:
        position[i] = 0 if open_time[i] < UTC("2020-01-01 00:00:00") else int(signal[i - 1] == 1)

# position[i] is the state held from open_i to open_(i+1)
```

## 8. Exact cost model and return multiplier

Trading cost is 10 bps per side, 20 bps round-trip.

Let:

- `c = 0.001`
- `position[i]` = state held from `open_i` to `open_(i+1)`
- `prev_position[i]` = `position[i-1]`, with `prev_position[0] = 0`
- `next_open[i] = open_(i+1)`

The open-to-open interval multiplier for row `i` is:

- flat to flat (`prev_position = 0`, `position = 0`): `mult_i = 1.0`
- entry (`prev_position = 0`, `position = 1`): `mult_i = (1 - c) * (next_open_i / open_i)`
- stay long (`prev_position = 1`, `position = 1`): `mult_i = next_open_i / open_i`
- exit (`prev_position = 1`, `position = 0`): `mult_i = 1 - c`

The realized interval return is `ret_i = mult_i - 1`.

Round-trip net return for one completed trade from entry open `E` to exit open `X` is:

`net_trade_return = (X / E) * (1 - 0.001) * (1 - 0.001) - 1`

No other fee, slippage, leverage, borrow cost, or spread model is used.

## 9. Daily alignment and metric definitions

### Daily return alignment
The frozen protocol aligns candidate returns on a daily UTC domain by compounding all open-to-open interval returns whose interval starts on that UTC date.

For this native D1 system, one D1 interval starts on each UTC date, so the daily return is exactly the D1 open-to-next-open realized return for that date.

### Sharpe
Use sample standard deviation:

`Sharpe_daily_365 = mean(daily_returns) / std(daily_returns, ddof=1) * sqrt(365)`

### CAGR
Let `equity_end` be the final cumulative equity multiplier over the segment. Let `N_days` be the number of UTC dates in the segment, including the last date even if no new open-to-open interval starts from that final date. Then:

`CAGR = equity_end ** (365 / N_days) - 1`

This definition reproduces the frozen artifacts exactly.

### Max drawdown
Compute cumulative equity from the interval multipliers, then:

`drawdown_t = equity_t / running_peak_t - 1`

`max_drawdown = min(drawdown_t)`

### Trade-count field
The frozen validation artifacts serialize the following `trade_count_entries` field values for `S_D1_TREND`:

- discovery WFO: 61
- holdout: 34
- reserve: 35

Exact definition:
- on any segment or fold, count the number of execution-open state transitions `position_i != position_(i-1)`;
- for the first bar inside the segment or fold, compare its position against the immediately preceding bar from prior history;
- this field therefore counts `entries + exits` that occur inside the segment or fold;
- it does **not** count completed round trips only.

Those values must be matched exactly when reproducing the frozen artifacts. Completed trade-quality statistics such as win rate, mean trade return, and median trade return are computed from completed round trips only.

## 10. Edge-case handling

- **H4 anomalies:** not relevant; the system does not use H4 data.
- **Gaps between D1 bars:** none were observed in the frozen D1 file. If a future file contains a gap, do not invent bars. Execute at the next available native D1 open.
- **Missing data:** none were observed in the frozen D1 file. If a future file contains missing values, do not synthesize replacements.
- **Insufficient history:** if fewer than 40 prior bars exist, `D1_MOM_RET(40)` is undefined and the system cannot generate a long signal from that bar.
- **Warmup:** no live trading before `2020-01-01`. Historical pre-2020 bars may be used only to provide the 40-bar lookback.
- **Duplicate rows:** none were observed in the frozen D1 file. If a future file contains duplicates, retain them and log them; do not silently de-duplicate.
- **Zero-activity rows:** none were observed in the frozen D1 file. If a future file contains them, retain them and log them; do not invent prices.
- **Threshold equality:** `D1_MOM_RET(40) == 0.0` is flat.
- **No rounding rule:** use raw parsed numeric precision from the CSV. Do not round intermediate calculations.
- **D1 timestamp convention in the frozen file:** native D1 bars open at `00:00:00.000 UTC`, close at `23:59:59.999 UTC`, duration `86,400,000 ms`.

## 11. Verification targets

The following values must match the frozen artifacts exactly.

| Segment | Cost RT | Sharpe | CAGR | Max DD | Trade-count field (`trade_count_entries`) | Pos fold share |
| --- | --- | --- | --- | --- | --- | --- |
| Discovery WFO | 20 bps | 1.6941 | 101.2% | -48.3% | 61 | 64.3% (9/14) |
| Discovery WFO | 50 bps | 1.6396 | 96.0% | -50.9% | 61 | 64.3% (9/14) |
| Holdout | 20 bps | 1.0819 | 40.8% | -43.4% | 34 | — |
| Holdout | 50 bps | 0.9751 | 35.2% | -44.9% | 34 | — |
| Reserve | 20 bps | 0.8734 | 24.2% | -24.0% | 35 | — |
| Reserve | 50 bps | 0.7518 | 19.8% | -25.4% | 35 | — |

The column labeled “Trade-count field” is the serialized `trade_count_entries` state-transition count, not completed round trips.

Rounded discovery fold-level net returns at 20 bps RT:
`[0.188, 0.434, 0.068, 1.506, 1.031, −0.047, 0.088, 0.154, −0.130, −0.099, −0.119, −0.091, 0.592, 0.044]`

Discovery fold-level trade-count field values:
`[4, 4, 8, 1, 0, 3, 2, 4, 7, 7, 6, 11, 2, 2]`

Exact discovery fold table:
| Fold | Discovery fold net return (20 bps RT) | Trade-count field |
| --- | --- | --- |
| 1 | 0.187943504808364 | 4 |
| 2 | 0.433786220506584 | 4 |
| 3 | 0.068004599648130 | 8 |
| 4 | 1.506428246636089 | 1 |
| 5 | 1.030846750563468 | 0 |
| 6 | -0.046825249899488 | 3 |
| 7 | 0.088047091137327 | 2 |
| 8 | 0.154084432496297 | 4 |
| 9 | -0.130490143961046 | 7 |
| 10 | -0.098965369715036 | 7 |
| 11 | -0.119482395543679 | 6 |
| 12 | -0.091438470498662 | 11 |
| 13 | 0.592169987330745 | 2 |
| 14 | 0.044230202133128 | 2 |

Reserve trade-quality targets at 20 bps RT:

- exposure: `0.5357142857142857`
- win rate: `0.47058823529411764`
- mean trade return: `0.028326253857519936`
- median trade return: `-0.009932977384205066`
- mean holding bars: `16.647058823529413`
- median holding bars: `7`
- top 5 winner concentration: `0.951833824623945`

## 12. Test vectors

The following vectors are sufficient to validate observation timing, threshold semantics, next-open execution, cost deduction, warmup behavior, and no-change behavior. All real-data vectors come from the frozen native D1 CSV. `TV11` is a synthetic unit test for the equality branch.

| ID | Scenario | Observation D1 date | Observation `open_time` ms | `close_t` | `close_(t-40)` | `D1_MOM_RET(40)` | Signal at observation close | Next execution date | Next open price | State change at next open | Position after next open | Expected completed-trade PnL (if applicable) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TV01 | Insufficient history before 40-bar lookback | 2017-09-25 | 1506297600000 | 3920.75000000 | n/a | undefined | NO_SIGNAL | 2017-09-26 | 3928.00000000 | NONE | FLAT | no completed trade attached to this vector |
| TV02 | First valid 40-bar computation, still pre-live warmup | 2017-09-26 | 1506384000000 | 3882.35000000 | 4285.08000000 | -0.093984243001297 | FLAT | 2017-09-27 | 3882.36000000 | NONE | FLAT | no completed trade attached to this vector |
| TV03 | Warmup boundary: 2019-12-31 signal governs 2020-01-01 open, remains flat | 2019-12-31 | 1577750400000 | 7195.23000000 | 7627.74000000 | -0.056702247323585 | FLAT | 2020-01-01 | 7195.24000000 | NONE | FLAT | no completed trade attached to this vector |
| TV04 | First live long entry after 2020-01-01 | 2020-01-03 | 1578009600000 | 7344.96000000 | 6903.28000000 | 0.063981179960830 | LONG | 2020-01-04 | 7345.00000000 | ENTRY | LONG | entry 7345.00000000 → exit 8786.00000000; gross 0.196187882913547; net20 0.193796703335602 |
| TV05 | Consecutive same-signal long; no new order, no cost | 2020-01-04 | 1578096000000 | 7354.11000000 | 7109.57000000 | 0.034395891734662 | LONG | 2020-01-05 | 7354.19000000 | NONE | LONG | no completed trade attached to this vector |
| TV06 | Normal flat exit of the first live trade | 2020-02-26 | 1582675200000 | 8785.25000000 | 8913.28000000 | -0.014363960292956 | FLAT | 2020-02-27 | 8786.00000000 | EXIT | FLAT | entry 7345.00000000 → exit 8786.00000000; gross 0.196187882913547; net20 0.193796703335602 |
| TV07 | Near-zero positive observation that still triggers a long entry | 2020-07-08 | 1594166400000 | 9436.06000000 | 9427.07000000 | 0.000953636707906 | LONG | 2020-07-09 | 9436.06000000 | ENTRY | LONG | entry 9436.06000000 → exit 9232.42000000; gross -0.021581041239670; net20 -0.023536900738232 |
| TV08 | Near-zero negative observation while already flat; no state change | 2020-02-28 | 1582848000000 | 8692.91000000 | 8701.70000000 | -0.001010147442454 | FLAT | 2020-02-29 | 8690.80000000 | NONE | FLAT | no completed trade attached to this vector |
| TV09 | Cost-deduction example: one-day losing trade exits next day | 2020-07-09 | 1594252800000 | 9232.43000000 | 9697.72000000 | -0.047979318850204 | FLAT | 2020-07-10 | 9232.42000000 | EXIT | FLAT | entry 9436.06000000 → exit 9232.42000000; gross -0.021581041239670; net20 -0.023536900738232 |
| TV10 | Near-zero positive observation while already long; no state change | 2022-10-18 | 1666051200000 | 19327.44000000 | 19319.77000000 | 0.000397002655829 | LONG | 2022-10-19 | 19327.44000000 | NONE | LONG | no completed trade attached to this vector |
| TV11 | Synthetic exact-zero equality case; threshold is strict > 0, so equality stays flat | 2099-01-31 | synthetic | 100.00000000 | 100.00000000 | 0.000000000000000 | FLAT | 2099-02-01 | 100.00000000 | NONE | FLAT | no completed trade attached to this vector |

## 13. Worked examples from the test vectors

### Example A — first live entry
Observation date `2020-01-03`:

- `close_t = 7344.96`
- `close_(t-40) = 6903.28`
- `D1_MOM_RET(40) = 7344.96 / 6903.28 - 1 = 0.0639811799608303`
- signal at the 2020-01-03 close: `LONG`
- next execution open: `2020-01-04 00:00:00 UTC`
- entry price: `7345.00`

### Example B — first live exit and completed-trade PnL
Observation date `2020-02-26`:

- `close_t = 8785.25`
- `close_(t-40) = 8913.28`
- `D1_MOM_RET(40) = -0.014363960292956168`
- signal at the 2020-02-26 close: `FLAT`
- next execution open: `2020-02-27 00:00:00 UTC`
- exit price: `8786.00`

The completed trade that started on `2020-01-04` therefore has:

- entry open `E = 7345.00`
- exit open `X = 8786.00`
- gross return `X / E - 1 = 0.1961878829135466`
- net 20 bps round-trip return `(X / E) * 0.999 * 0.999 - 1 = 0.19379670333560228`

### Example C — near-zero positive observation still enters
Observation date `2020-07-08`:

- `close_t = 9436.06`
- `close_(t-40) = 9427.07`
- `D1_MOM_RET(40) = 0.000953636707905936`
- because the threshold is strict `> 0.0`, this is `LONG`
- next execution open `2020-07-09`: entry at `9436.06`

### Example D — next-day exit of that near-zero entry
Observation date `2020-07-09`:

- `close_t = 9232.43`
- `close_(t-40) = 9697.72`
- `D1_MOM_RET(40) = -0.0479793188502039`
- signal becomes `FLAT`
- next execution open `2020-07-10`: exit at `9232.42`

Completed-trade return:

- entry open `9436.06`
- exit open `9232.42`
- gross return `-0.021581041239669863`
- net 20 bps round-trip return `-0.02353690073823178`

## 14. Final frozen identity

The frozen winner is:

- `system_id = S_D1_TREND`
- feature = `D1_MOM_RET`
- lookback = `40`
- tail = `high`
- threshold mode = `sign`
- threshold value = `0.0`
- calibration mode = `fixed_structural`
- state rule = `long if D1_MOM_RET(40) > 0 else flat`
- execution = `next D1 open`
- sizing = `100% long or 0% flat`

No other hidden rule exists.
