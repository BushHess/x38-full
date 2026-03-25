# Step 1: Logging Schema — Trade-Level & Event-Level CSVs

**Script:** `out_v10_fix_loop/step1_export.py`
**Date:** 2026-02-24
**Scenario:** harsh (50 bps RT)
**Period:** 2019-01-01 → 2026-02-20 (warmup 365d, reporting events only)

---

## 1. Deliverables

| File | Rows | Description |
|------|------|-------------|
| `out_v10_fix_loop/v10_baseline_trades_harsh.csv` | 103 | Closed trades with regime labels |
| `out_v10_fix_loop/v10_baseline_events_harsh.csv` | 8,177 | Bar-by-bar event log |

**Verification:** Trade count = 103 → **PASS** (matches backtest summary)

---

## 2. Trades CSV Schema (`v10_baseline_trades_harsh.csv`)

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `trade_id` | int | — | Sequential trade number (1-103), deterministic |
| `entry_ts` | str | UTC | ISO-8601 entry timestamp (first buy fill) |
| `exit_ts` | str | UTC | ISO-8601 exit timestamp (sell fill) |
| `entry_price` | float | USD | Weighted-average entry fill price (includes spread+slippage) |
| `exit_price` | float | USD | Exit fill price (includes spread+slippage) |
| `qty` | float | BTC | Total position size at close |
| `notional` | float | USD | qty × entry_price |
| `gross_pnl` | float | USD | net_pnl + fees_total |
| `net_pnl` | float | USD | Realized PnL (= Trade.pnl, cost-embedded fill prices) |
| `fees_total` | float | USD | Sum of all buy+sell fill fees for this trade |
| `return_pct` | float | % | (exit_price / entry_price - 1) × 100 |
| `bars_held` | int | — | Number of H4 bars during [entry, exit] |
| `days_held` | float | days | Calendar days held |
| `mfe_pct` | float | % | Max favorable excursion: (max_high - entry) / entry × 100 |
| `mae_pct` | float | % | Max adverse excursion: (entry - min_low) / entry × 100 |
| `entry_reason` | str | — | Signal reason at entry (see §4) |
| `exit_reason` | str | — | Signal reason at exit (see §4) |
| `exposure_at_entry` | float | 0-1 | Portfolio exposure before entry fill (from equity snap) |
| `exposure_at_exit` | float | 0-1 | Portfolio exposure at exit bar close |
| `regime_at_entry` | str | — | 6-class D1 analytical regime at entry (strict < alignment) |
| `regime_at_exit` | str | — | 6-class D1 analytical regime at exit |
| `holding_regime_mode` | str | — | Most common D1 regime during hold (by D1 bar count) |
| `worst_regime` | str | — | Worst regime encountered: SHOCK > BEAR > CHOP > TOPPING > NEUTRAL > BULL |
| `n_buy_fills` | int | — | Number of buy fills (entry + pyramids) |
| `n_sell_fills` | int | — | Number of sell fills (always 1 for V10) |

### Notes on PnL columns

- **`net_pnl`** = Trade.pnl from the engine. This is the actual portfolio impact: fill prices already embed spread + slippage, and fill fees are deducted separately.
- **`fees_total`** = sum of Fill.fee for all matched fills (buy + sell). This is the explicit exchange fee component.
- **`gross_pnl`** = net_pnl + fees_total. This removes the fee component but NOT spread/slippage (which is baked into fill prices). True mid-price gross would require reconstructing mid from fill prices.
- **Slippage** is not exported as a separate column because it is embedded in fill prices by the ExecutionModel. The cost model applies `spread_bps` and `slippage_bps` to compute fill prices from bar mid; these are not tracked separately per-trade.

### MFE/MAE computation

- Source: H4 bar high/low during `[entry_ts, exit_ts]` holding period
- MFE = (max H4 high − entry_price) / entry_price × 100, clipped ≥ 0
- MAE = (entry_price − min H4 low) / entry_price × 100, clipped ≥ 0
- These are price-level excursions, not equity-level

### Regime labels

- **Source:** `classify_d1_regimes()` applied to D1 bars
- **6 classes:** BULL, NEUTRAL, CHOP, TOPPING, SHOCK, BEAR
- **Alignment:** strict `bisect_left(d1_close_times, ts_ms) - 1` — uses the latest D1 bar whose close_time is BEFORE the event timestamp (no lookahead)
- **`holding_regime_mode`:** counts each D1 bar in [entry, exit) range, takes most common
- **`worst_regime`:** rank order SHOCK(0) > BEAR(1) > CHOP(2) > TOPPING(3) > NEUTRAL(4) > BULL(5), takes minimum rank

---

## 3. Events CSV Schema (`v10_baseline_events_harsh.csv`)

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `ts` | str | UTC | ISO-8601 timestamp of the event |
| `bar_index` | int/blank | — | H4 bar index (for signal events; blank for fill events) |
| `event_type` | str | — | One of 6 types (see §3.1) |
| `reason` | str | — | Signal/block/fill reason (see §4) |
| `price` | float | USD | Bar close (signals) or fill price (fills) |
| `nav` | float | USD | Portfolio NAV at event time (blank for fills) |
| `exposure_before` | float | 0-1 | Exposure before this event |
| `exposure_after` | float | 0-1 | Exposure after this event |
| `notional_before` | float | USD | nav × exposure_before |
| `notional_after` | float | USD | nav × exposure_after |
| `regime_label` | str | — | Strategy's 3-class regime (RISK_ON/CAUTION/RISK_OFF) — for signal events |
| `regime_d1_analytical` | str | — | 6-class analytical regime (BULL/TOPPING/etc.) |
| `fill_qty` | float/blank | BTC | Fill quantity (fill events only) |
| `fill_fee` | float/blank | USD | Fill fee (fill events only) |
| `trade_id_ref` | int/blank | — | Associated trade_id (fill events only) |

### 3.1 Event Types

| event_type | Count | When | Description |
|------------|-------|------|-------------|
| `entry_signal` | 103 | Bar close | Strategy decided to open position from flat |
| `add_signal` | 473 | Bar close | Strategy decided to add (pyramid) to existing position |
| `exit_signal` | 103 | Bar close | Strategy decided to close entire position |
| `entry_blocked` | 6,819 | Bar close | Strategy was flat, entry gates rejected |
| `entry_fill` | 576 | Next bar open | Buy fill executed (entry + pyramid adds) |
| `exit_fill` | 103 | Next bar open | Sell fill executed (position closed) |

### 3.2 Signal → Fill Timing

Signals are generated at **H4 bar close** (step 4 of engine loop). Fills execute at the **next H4 bar open** (step 1 of next iteration). There is a 1-bar delay between signal and execution.

Example:
```
2019-04-10T19:59:59Z  entry_signal  vdo_trend_accel  (bar close decision)
2019-04-10T20:00:00Z  entry_fill    vdo_trend_accel  (next bar open execution)
```

### 3.3 Fill-to-Trade Matching

Each fill is matched to a trade by timestamp range: `trade.entry_ts_ms <= fill.ts_ms <= trade.exit_ts_ms`. The `trade_id_ref` column links fills to their parent trade.

- 576 entry_fill events map to 103 trades (mean 5.6 buy fills per trade = pyramiding)
- 103 exit_fill events map 1:1 to 103 trades

---

## 4. Reason Codes

### 4.1 Entry Reasons (for `entry_signal`, `add_signal`, `entry_fill`)

| Reason | Description | Source |
|--------|-------------|--------|
| `vdo_trend_accel` | VDO above threshold + above HMA + positive acceleration | `v8_apex.py:479-480` |
| `vdo_trend` | VDO above threshold + above HMA (no acceleration) | `v8_apex.py:482` |
| `vdo_dip_buy` | VDO above threshold + RSI oversold | `v8_apex.py:477-478` |
| `vdo_compression` | ATR compression + high VDO | `v8_apex.py:475-476` |

### 4.2 Exit Reasons (for `exit_signal`, `exit_fill`)

| Reason | Description | Source |
|--------|-------------|--------|
| `emergency_dd` | Portfolio DD from inflated ref_nav ≥ 28% (effective ~5% per-trade) | `v8_apex.py:324-332` |
| `trailing_stop` | Price below peak − ATR_mult × ATR (after profit threshold) | `v8_apex.py:338-350` |
| `fixed_stop` | Price below entry − 15% (safety net before trail activates) | `v8_apex.py:352-356` |
| `regime_off` | D1 regime = RISK_OFF (disabled by default) | `v8_apex.py:335-336` |

### 4.3 Block Reasons (for `entry_blocked`)

| Reason | Count | Description |
|--------|-------|-------------|
| `regime_off` | 4,711 | D1 regime = RISK_OFF (EMA50 < EMA200, price below EMA200) |
| `vdo_below_threshold` | 1,722 | VDO ≤ 0.004 (no momentum) |
| `cooldown_exit` | 286 | Within 3 bars of last exit (exit cooldown) |
| `trend_not_confirmed` | 98 | Price below HMA AND RSI not oversold |
| `cooldown_add` | 2 | Within 3 bars of last add (add cooldown) |

Block reasons are diagnosed in priority order (same gate sequence as `_check_entry`):
1. Regime gate → `regime_off`
2. Add cooldown → `cooldown_add`
3. Exit cooldown → `cooldown_exit`
4. VDO threshold → `vdo_below_threshold`
5. Trend confirmation → `trend_not_confirmed`
6. Exposure gap → `exposure_gap_small`
7. Size minimum → `size_below_min`

---

## 5. Key Statistics

| Metric | Value |
|--------|-------|
| Total trades | 103 |
| Total fills | 679 (576 buy + 103 sell) |
| Mean buy fills per trade | 5.6 |
| Total events | 8,177 |
| Event period | 2019-01-01 → 2026-02-20 |
| Exit breakdown | trailing_stop: 64, emergency_dd: 36, fixed_stop: 3 |
| Bars blocked by regime_off | 4,711 / 6,819 = 69% of blocked bars |
| Bars blocked by vdo_below | 1,722 / 6,819 = 25% of blocked bars |
| Cooldown blocks after exit | 286 = 2.8 bars/exit average |

---

## 6. Usage for Churn Analysis

The event log enables measurement of the stop-out → re-enter → stop-out cycle:

1. **Find exit→entry pairs:** Filter `exit_signal` or `exit_fill` events, then find the next `entry_signal` or `entry_fill` for the same strategy.

2. **Measure re-entry delay:** Time gap between `exit_fill.ts` and next `entry_fill.ts`.

3. **Count blocked bars:** Between each exit and re-entry, count `entry_blocked` events and their reasons.

4. **Fee drag per cycle:** Sum `fill_fee` for entry fills + exit fill of each trade in the cycle.

5. **Churn identification:** Trades with `exit_reason=emergency_dd` followed by quick re-entry (`cooldown_exit` → `entry_signal`) within a few bars.
