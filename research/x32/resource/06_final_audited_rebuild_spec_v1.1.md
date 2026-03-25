# Final audited rebuild spec v1.1 — VP1 (VTREND-P1)

## 1. Identity
- **Strategy name: VP1** (short for VTREND-P1)
- Legacy Candidate ID: `Phase1ParentCore_ATRstandard_REVon_D1ON`
- Historical alias seen in logs only: `Phase1ParentCore_ATRstandard_REVon_D1on`
- Provenance label: `performance-dominant leader`
- Research status:
  - lead hypothesis: yes
  - not a proven winner: yes
  - not best current provisional system: yes

## 2. Frozen facts
| Item | Value | Confidence |
|---|---|---|
| market | BTC spot only | CONFIRMED |
| symbol assumption | BTCUSDT bars | CONFIRMED |
| main timeframe | H4 | CONFIRMED |
| higher timeframe | D1 context/filter only | CONFIRMED / INFERRED |
| long-only | yes | CONFIRMED |
| binary sizing | 100% NAV or 0% only | CONFIRMED |
| slow_period | 140 | CONFIRMED |
| fast_period | 35 via `max(5, floor(140 / 4))` | INFERRED |
| ATR architecture | standard ATR | CONFIRMED |
| ATR period | 20 | INFERRED |
| ATR smoothing | Wilder | INFERRED |
| trail_mult | 2.5 | CONFIRMED |
| reversal exit | ON | CONFIRMED |
| VDO use | ON, entry confirmation only | CONFIRMED / INFERRED |
| vdo_threshold | 0.0, strict `>` | CONFIRMED / INFERRED |
| d1_ema_period | 28 | CONFIRMED |
| D1 policy | prevday only | CONFIRMED |
| headline execution | decision at H4 close bar i; fill at H4 open bar i+1 | CONFIRMED |
| valuation clock | H4 open post-fill | CONFIRMED |
| accounting | cash + shares event accounting | CONFIRMED |
| benchmark headline cost | 50 bps round-trip = 25 bps per side | CONFIRMED |
| warmup | 365 calendar days, no-trade | INFERRED |

## 3. Data contract
### 3.1 Required H4 columns
`open_time, close_time, open, high, low, close, volume, num_trades, taker_buy_base_vol`

Optional but ignored by strategy logic:
`quote_volume, taker_buy_quote_vol, symbol, interval`

### 3.2 Required D1 columns
`open_time, close_time, close`

Optional but allowed:
other OHLCV fields may be present but are not required for VP1 logic.

### 3.3 Timestamp semantics
- All timestamps are UTC.
- Bars are uniquely identified by `open_time`.
- Input must be strictly ascending by `open_time`.

### 3.4 Bar completeness
- Every H4 and D1 row must represent a completed bar.
- Canonical H4 schedule is 6 bars per UTC day at `00:00, 04:00, 08:00, 12:00, 16:00, 20:00`.

### 3.5 Dirty-data handling
- Duplicate timestamps: hard fail. **FORCED-RESOLUTION**
- Non-monotonic timestamps: hard fail. **FORCED-RESOLUTION**
- Structural missing bars / compressed time: hard fail. **FORCED-RESOLUTION**
- Non-positive prices: hard fail. **FORCED-RESOLUTION**
- `anomaly_flag = (volume <= 0) OR (num_trades <= 0)` on H4.
- If the entire taker column is absent, run fallback-only VDO globally. **FORCED-RESOLUTION**
- If taker data is missing only on some bars, use auto path per bar.

### 3.6 D1/H4 join
- `h4.date_utc = floor_utc_day(h4.open_time)`
- `d1.date_utc = floor_utc_day(d1.open_time)`
- `h4.d1_key = h4.date_utc - 1 day`
- Join `h4.d1_key` to `d1.date_utc`
- If no D1 row exists for `d1_key`, set `regime = False`. **FORCED-RESOLUTION**

## 4. Clock and causality contract
### 4.1 Four clocks
- decision timestamp = H4 `close_time[i]`
- fill timestamp = H4 `open_time[i+1]`
- fill price = `open[i+1]`
- valuation timestamp = H4 open post-fill

### 4.2 No-lookahead
- All signal features are evaluated only on completed bar `i`.
- No bar may use H4 bar `i+1` information for decision-making.
- No H4 bar on date `d` may use D1 date `d`; all use D1 date `d-1`.
- Same-day D1 usage is forbidden in headline evaluation.

### 4.3 Same bar event ordering
At bar `j`:
1. Process any pending fill at `open[j]`
2. Mark NAV at `open[j]` post-fill
3. Later, after bar `j` completes, evaluate the close-of-bar decision for possible fill at `open[j+1]`

A bar may therefore host:
- an exit fill at its open
- then a new entry decision at its close

## 5. Features and exact formulas
### 5.1 EMA fast / slow
For any period `p`:
- `alpha = 2 / (p + 1)`
- `ema[0] = close[0]`
- `ema[i] = alpha * close[i] + (1 - alpha) * ema[i-1]`

VP1 values:
- `ema_slow = EMA(close, 140)`
- `ema_fast = EMA(close, 35)`

Trend states:
- `trend_up = ema_fast > ema_slow`
- `trend_down = ema_fast < ema_slow`
- `neutral = ema_fast == ema_slow`

### 5.2 Standard ATR20
For H4 bar `i`:
- if `i == 0`, `TR[0] = NaN`
- if `i > 0`,
  `TR[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))`

Wilder ATR20:
- `ATR[19] = nanmean(TR[0:20])`
- for `i > 19`:
  `ATR[i] = (ATR[i-1] * 19 + TR[i]) / 20`

The decision bar uses current completed-bar `ATR[i]`, not lagged `ATR[i-1]`.

### 5.3 VDO
#### Primary path
If `taker_buy_base_vol` finite and `volume > 0`:
- `taker_sell = volume - taker_buy_base_vol`
- `vdr = (taker_buy_base_vol - taker_sell) / volume`
- equivalently: `vdr = (2 * taker_buy_base_vol - volume) / volume`

#### Fallback path
If primary path unavailable and `high > low`:
- `vdr = ((close - low) / (high - low)) * 2 - 1`
Else:
- `vdr = NaN`

#### Path selection
Per bar:
- use primary path if possible
- else fallback path if possible
- else `vdr = NaN`

#### EMA_nan_carry
For period `p`:
- find first finite input index `k`
- `ema[k] = input[k]`
- for `i > k`:
  - if current input finite: ordinary EMA update
  - else: `ema[i] = ema[i-1]`
- if no finite input has ever appeared: EMA stays `NaN`

#### VP1 VDO
- `vdo_fast = EMA_nan_carry(vdr, 12)`
- `vdo_slow = EMA_nan_carry(vdr, 28)`
- `VDO = vdo_fast - vdo_slow`

Threshold:
- entry requires `VDO > 0.0`
- `VDO == 0.0` is not sufficient

VDO is entry-only.

### 5.4 D1 regime
D1 EMA28:
- `alpha = 2 / 29`
- `d1_ema[0] = d1_close[0]`
- `d1_ema[t] = alpha * d1_close[t] + (1 - alpha) * d1_ema[t-1]`

Regime:
- `regime = (d1_close > d1_ema_28)`

Prevday mapping:
- every H4 bar on UTC date `d` uses D1 date `d-1`
- this includes the final H4 bar opened at 20:00 UTC on date `d`
- if prevday D1 row is missing, `regime = False`

D1 regime is entry-only.

## 6. State machine
### 6.1 States
- `FLAT`: `cash > 0`, `shares = 0`, `peak_price = 0`
- `LONG`: `cash = 0`, `shares > 0`, `peak_price > 0`

### 6.2 Runtime variables
- `cash`
- `shares`
- `peak_price`
- optional pending order object maintained by the execution wrapper

### 6.3 Persistence
Persist across bars:
- `cash`
- `shares`
- `peak_price`
- pending order until filled

Reset on buy fill:
- `peak_price = peak_seed = close[decision_bar]`

Reset on sell fill:
- `peak_price = 0`

### 6.4 Anomaly bars
If `anomaly_flag = True`:
- no entry decision
- no exit decision
- no `peak_price` update
- existing position is still carried and marked to market at the next valuation open

## 7. Entry logic
A BUY signal may be emitted on completed H4 bar `i` only if all are true:
1. current state is `FLAT`
2. bar `i+1` exists for fill
3. `open_time[i] >= warmup_cut`
4. `anomaly_flag[i] == False`
5. `ema_fast[i]` and `ema_slow[i]` are finite
6. `VDO[i]` is finite
7. `regime[i] == True`
8. `ema_fast[i] > ema_slow[i]`
9. `VDO[i] > 0.0`

If all are true:
- emit BUY at `close_time[i]`
- fill at `open_time[i+1]`, price `open[i+1]`
- target exposure becomes 100% NAV
- store `peak_seed = close[i]`

Equality cases:
- `ema_fast == ema_slow` -> no entry
- `VDO == 0.0` -> no entry

## 8. Exit logic
While LONG, on completed H4 bar `i`, if `anomaly_flag[i] == False` and `open_time[i] >= warmup_cut`:

### Step 1 — update peak
`peak_price = max(peak_price, close[i])`

### Step 2 — trailing stop
- require finite `ATR[i]`
- `trail_stop = peak_price - 2.5 * ATR[i]`
- if `close[i] < trail_stop`, emit SELL with reason `trailing_stop`

### Step 3 — trend reversal
If trailing stop did not trigger:
- if `ema_fast[i] < ema_slow[i]`, emit SELL with reason `trend_reversal`

Priority:
- trailing stop first
- trend reversal second

Equality cases:
- `close == trail_stop` -> no trailing-stop exit
- `ema_fast == ema_slow` -> no reversal exit

D1 and VDO do not participate in exit.

## 9. Accounting and cost
### 9.1 Strategy / harness boundary
The strategy itself is cost-agnostic.  
Canonical benchmark reproduction uses the frozen headline harness cost.

### 9.2 Canonical benchmark cost
- round-trip cost = 50 bps
- side cost = 25 bps = 0.0025

### 9.3 BUY accounting
At buy fill price `P_buy`:
- `shares = cash / (P_buy * (1 + 0.0025))`
- `cash = 0`

### 9.4 SELL accounting
At sell fill price `P_sell`:
- `cash = shares * P_sell * (1 - 0.0025)`
- `shares = 0`

### 9.5 Valuation
At each H4 open post-fill:
- `NAV = cash + shares * open_price`

Assumptions:
- fractional shares allowed
- no lot-size rounding
- no spread/slippage model beyond the explicit flat side cost
- no kill switch
- no portfolio overlay

## 10. Warmup and eligibility
- `warmup_days = 365`
- `warmup_cut = first_h4_open_time + 365 calendar days`
- Before warmup_cut:
  - indicators still compute
  - no trading allowed
- After warmup_cut:
  - entry still requires all entry-side features finite
  - exit still requires finite ATR for trailing stop evaluation

If one required feature is NaN on a decision bar:
- missing EMA or VDO on FLAT -> no entry
- missing ATR on LONG -> trailing stop not evaluated on that bar
- reversal exit may still evaluate if EMAs are finite

## 11. Benchmark wrapper rules (not intrinsic strategy rules)
- In open-ended operation, the strategy has no EOF exit.
- In finite benchmark windows only, the wrapper may apply synthetic `window_flatten` at the final allowed window open.
- `window_flatten` is not part of strategy logic and must not be coded as a strategy exit condition.

## 12. Canonical verification trace
### Artifact-backed trace
Use the first Tier-2 trade cycle from `tier2_one_shot_artifact/candidate/trade_log.csv` as the canonical frozen trace:

- signal_time = `2024-09-15 15:59:59.999000+00:00`
- entry_time = `2024-09-15 16:00:00+00:00`
- entry_price = `60335.41`
- exit_time = `2024-09-16 16:00:00+00:00`
- exit_price = `57881.70`
- bars_held = `6`
- entry_reason = `entry_signal`
- exit_reason = `trailing_stop`

This trace is the acceptance anchor.
Indicator-number reconstruction around this cycle is allowed as a local verification exercise, but those numbers are not part of the frozen artifact truth unless separately preserved.

## 13. Acceptance tests
### 13.1 Artifact-backed hard acceptance gates
The rebuilt VP1 must reproduce these exact Tier-2 artifact-backed checks under the frozen manifest:
- trade count on Tier-2 block = `43`
- first three entry fill timestamps:
  1. `2024-09-15 16:00:00+00:00`
  2. `2024-09-16 20:00:00+00:00`
  3. `2024-09-30 20:00:00+00:00`
- first three exit fill timestamps:
  1. `2024-09-16 16:00:00+00:00`
  2. `2024-09-30 12:00:00+00:00`
  3. `2024-10-01 20:00:00+00:00`
- first trade:
  - signal_time = `2024-09-15 15:59:59.999000+00:00`
  - entry_time = `2024-09-15 16:00:00+00:00`
  - entry_price = `60335.41`
  - exit_time = `2024-09-16 16:00:00+00:00`
  - exit_price = `57881.70`
  - exit_reason = `trailing_stop`

### 13.2 Deterministic formula/unit tests
- `fast_period == 35`
- `warmup_cut = first_h4_open + 365 days`
- `ema_fast == ema_slow` produces no entry and no reversal exit
- `VDO == 0.0` produces no entry
- `close == trail_stop` produces no trailing-stop exit
- missing prevday D1 row -> `regime = False`
- absent full taker column -> fallback-only VDO globally
- partial missing taker -> per-bar auto path
- duplicate timestamps -> hard fail
- structural gaps -> hard fail

### 13.3 VP1-vs-Baseline divergence checkpoints
These are **soft audit checks**, not primary acceptance gates, because the shipped Tier-2 package does not include a Baseline trade log:
- Tier-2 headline artifact shows VP1 ahead of Baseline on total return, CAGR, and MAR
- Tier-2 headline artifact shows VP1 trade count `43` vs Baseline `39`

## 14. Ambiguity ledger
| Field / rule | Why ambiguous in v1.0 | Canonical v1.1 resolution | Confidence |
|---|---|---|---|
| VP1 name casing (legacy) | two spellings in artifacts/logs | canonical ID fixed to `...D1ON`; `...D1on` is log alias only | FORCED-RESOLUTION |
| fast period | not directly in candidate artifact | `35 = max(5, floor(140/4))` | INFERRED |
| ATR period / smoothing | candidate artifact only said standard ATR | ATR20 Wilder | INFERRED |
| warmup | candidate artifact did not restate it | 365 calendar days, no-trade | INFERRED |
| VDO partial-missing behavior | path selection vs EMA carry not fully locked | per-bar auto path + EMA_nan_carry semantics explicit | INFERRED |
| absent full taker column | not directly specified | fallback-only VDO globally | FORCED-RESOLUTION |
| duplicate/gap handling | not specified in artifact | hard fail | FORCED-RESOLUTION |
| terminal open position | strategy vs wrapper not sharply separated | no intrinsic EOF exit; wrapper-only `window_flatten` | INFERRED |
| benchmark cost vs strategy cost | boundary not sharp enough | strategy is cost-agnostic; canonical benchmark uses flat 50 bps RT | CONFIRMED / FORCED-RESOLUTION |

## 15. Final executable rule summary
If someone rebuilds VP1 from scratch, the exact rules are:

- Use BTC spot H4 bars and D1 closes in UTC.
- Compute EMA140 and EMA35 on H4 close.
- Compute standard Wilder ATR20 on H4.
- Compute VDO from per-bar auto primary/fallback VDR, then EMA_nan_carry(12) minus EMA_nan_carry(28).
- Compute D1 EMA28 and map D1 regime to H4 by strict prevday.
- Do not trade before first H4 open + 365 calendar days.
- Enter LONG 100% NAV at next H4 open if, on completed decision bar:
  - FLAT
  - no anomaly
  - EMA35 > EMA140
  - VDO > 0
  - D1 regime true
  - next bar exists
- On entry, seed `peak_price = decision-bar close`.
- While LONG, on each completed non-anomaly bar:
  - update `peak_price = max(peak_price, close)`
  - if `close < peak_price - 2.5 * ATR20`, exit next open
  - else if `EMA35 < EMA140`, exit next open
- D1 and VDO are entry-only.
- Headline benchmark reproduction uses next-open event accounting with flat 25 bps per side.

This is the standalone canonical executable rebuild spec.
