# X36 — Non-ML Trail-Stop Continuation

**Date**: 2026-03-14
**Registry**: X36
**Status**: DONE — non-ML candidate selected, spec complete
**Prerequisite**: E5+EMA1D21 (PROMOTE), X14D/X18 (churn research)

---

## 1. Objective

Replace the ML overlay (which decides whether to hold past the first trail-stop hit) with a
deterministic, non-ML signal based on normalized net taker flow.

## 2. Results

### 2.1 Summary comparison

| Variant             | Sharpe  | Δ vs base exit | Δ vs incumbent ML |
|---------------------|---------|----------------|--------------------|
| Base exit           | 1.1308  | —              | —                  |
| Incumbent ML overlay| 1.1941  | +0.0634        | —                  |
| **Chosen non-ML**   | **1.1976** | **+0.0669** | **+0.0035**        |

### 2.2 WFO fold-by-fold

| Fold | Non-ML | Base exit | ML overlay | Non-ML > Base | Non-ML > ML |
|------|--------|-----------|------------|---------------|-------------|
| 1    | 0.660  | 0.607     | 0.547      | +0.053        | +0.113      |
| 2    | 1.628  | 1.538     | 1.703      | +0.090        | -0.075      |
| 3    | 1.835  | 1.819     | 1.837      | +0.016        | -0.002      |
| 4    | 0.111  | -0.022    | 0.228      | +0.133        | -0.117      |
| **Win rate** | | | | **4/4** | **1/4** |

### 2.3 Interpretation

- Beats base exit in all 4 folds — continuation mechanism has value.
- Does NOT convincingly beat incumbent ML overlay (1/4 folds).
- Advantage: zero model risk, zero fit, fully deterministic.

---

## 3. Implementation Spec

### 3.1 Scope lock

Replaces **only** the ML overlay decision (hold vs exit after first trail-stop hit).

Unchanged:
- Entry logic (EMA crossover + VDO + D1 regime)
- D1 regime filter
- EMA / VDO base indicators
- Robust ATR
- Position sizing
- Cost / accounting
- Horizon continuation H = 16 bars

### 3.2 Timeframe & execution semantics

- Timeframe: **H4**
- All indicators use **closed bars only**
- Decisions at close of bar `t` execute at open of bar `t+1`
- No partial exit — position is always **FLAT** or **100% LONG**

### 3.3 Entry (unchanged)

At H4 close bar `t`, when FLAT, schedule full entry at open `t+1` if **all** conditions hold:

1. `EMA(30, close)_t > EMA(120, close)_t`
2. `VDO_t > 0`
3. Completed D1 regime OK: `D1_close > D1_EMA(21)`

### 3.4 Trail-stop (unchanged)

State maintained per trade:
- `full_entry_fill_bar_index`
- `full_entry_fill_price`
- `live_peak_close`

At each H4 close `t` while LONG:

```
live_peak_close_t = max(live_peak_close_{t-1}, close_t)
trail_stop_t      = live_peak_close_t - 3.0 * robust_ATR_t
```

**Robust ATR** (unchanged from base spec):

```
TR_t = max(high_t - low_t, |high_t - close_{t-1}|, |low_t - close_{t-1}|)

For t >= 100:
    cap_t = rolling_quantile(TR_{t-100..t-1}, q=0.90)
    TR_t  = min(TR_t, cap_t)

robust_ATR_t = Wilder_ATR(period=20, TR)
```

### 3.5 Hold signal (new)

**3.5.1 Measurement**

```
net_quote_t = 2 * taker_buy_quote_vol_t - quote_volume_t
```

**3.5.2 Normalization**

```
net_quote_norm_28_t = net_quote_t / EMA(28, quote_volume)_t
```

**3.5.3 Operator**

```
hold_signal_t = EMA(12, net_quote_norm_28)_t
```

**3.5.4 EMA convention (fixed)**

For period `p`:

```
alpha_p    = 2 / (p + 1)
EMA_p[x]_0 = x_0
EMA_p[x]_t = alpha_p * x_t + (1 - alpha_p) * EMA_p[x]_{t-1}
```

No standardization, no percentile transform, no model fitting.

### 3.6 Threshold

Fixed threshold: **0.0**

| Condition              | Interpretation |
|------------------------|----------------|
| `hold_signal_t >= 0.0` | Supportive     |
| `hold_signal_t < 0.0`  | Unsupportive   |

### 3.7 State machine

Valid states: `FLAT`, `BASE_LONG`, `CONTINUATION_LONG`

State variables:

| Variable | Type | Purpose |
|----------|------|---------|
| `cash` | float | Available capital |
| `qty` | float | Position size |
| `position_fraction` | float | Allocation fraction |
| `trade_id` | int | Current trade identifier |
| `full_entry_fill_bar_index` | int | Entry bar |
| `full_entry_fill_price` | float | Entry price |
| `live_peak_close` | float | Running peak close |
| `continuation_active` | bool | In continuation phase |
| `continuation_start_open_bar_index` | int | When continuation started |
| `forced_expiry_open_bar_index` | int | Hard deadline for continuation |
| `later_trail_signal_count_during_continuation` | int | Trail hits during continuation |
| `pending_order_type` | str | Pending order action |
| `pending_order_reason` | str | Why order was placed |

### 3.8 Event order per bar

**At open bar `t`** — execute pending order from previous close, by precedence:

1. `trend_exit_during_continuation` (highest)
2. `guard_exit`
3. `baseline trail-stop exit`
4. `forced_expiry`
5. `entry` (lowest)

If multiple reasons target the same open, take the highest precedence.

**At close bar `t`** — mark-to-market, then evaluate logic.

### 3.9 Logic: BASE_LONG

1. Update `live_peak_close`
2. Compute `trail_stop_t`
3. **If `close_t < trail_stop_t`** — this is the sole decision point of the trade:
   - Compute `hold_signal_t`
   - If `hold_signal_t >= 0.0` → **CONTINUE**
   - If `hold_signal_t < 0.0` → **EXIT_BASELINE**
4. **EXIT_BASELINE**: schedule full exit at open `t+1`, reason = `trail_stop`
5. **CONTINUE**: do not sell; set:
   - `continuation_active = True`
   - `continuation_start_open_bar_index = t + 1`
   - `forced_expiry_open_bar_index = (t + 1) + 16`
   - `later_trail_signal_count_during_continuation = 0`
6. **Only if no trail-stop decision on this bar**: if `EMA(30)_t < EMA(120)_t`, schedule `trend_exit` at open `t+1`

> **Priority rule**: if the same bar has both `close_t < trail_stop_t` AND `EMA(30)_t < EMA(120)_t`,
> the trail-stop continuation decision takes precedence. No separate trend exit is scheduled from that bar.

### 3.10 Logic: CONTINUATION_LONG

1. Update `live_peak_close`
2. Compute `trail_stop_t` (log/reference only)
3. If `close_t < trail_stop_t`: increment `later_trail_signal_count_during_continuation` (no direct exit)
4. Compute `hold_signal_t`
5. Check exit conditions in order:

| Priority | Condition | Action |
|----------|-----------|--------|
| 1 | `EMA(30)_t < EMA(120)_t` | Schedule `trend_exit_during_continuation` at open `t+1` |
| 2 | `hold_signal_t < 0.0` | Schedule `guard_exit` at open `t+1` |
| 3 | `(t + 1) == forced_expiry_open_bar_index` | Schedule `forced_expiry` at open `t+1` |
| — | None of the above | Continue holding |

### 3.11 Continuation semantics

- Position: 100% throughout (no partial)
- No rescoring, no ML, no threshold tuning
- Maximum continuation: **16 H4 bars** from `continuation_start_open_bar_index`
- Allowed end reasons: `guard_exit`, `trend_exit_during_continuation`, `forced_expiry`

### 3.12 Accounting (unchanged)

- Per-side cost: **12.5 bps**
- Full entry at next open: `qty = cash / (open_price * (1 + side_cost))`
- Full exit at next open: `cash = cash + qty * open_price * (1 - side_cost)`
- No leverage, no pyramiding, no partial exits

---

## 4. One-line summary

When a trade first hits the trail-stop, allow continuation only if EMA(12) of normalized net
taker quote flow is non-negative; once in continuation, keep holding only while that signal
remains non-negative, unless a trend exit triggers first or the 16-bar horizon expires.

============================================================
============================================================

"""

Đúng. Đối chiếu với protocol validation đã freeze từ dự án gốc, cả entry winner và exit research đều chỉ mới pass WFO fold test. Còn thiếu:

Bootstrap — P(ΔSharpe > 0) ≥ 55%, 500 paths, block size 60. Đây là kiểm tra xem edge có robust hay chỉ do một vài trade may mắn. Entry winner có Sharpe 1.374 trông đẹp, nhưng chỉ bỏ 14 trades so với baseline — bootstrap sẽ cho biết 14 trades đó có thực sự mang tính hệ thống không.

Cost sweep — phải thắng baseline ở ≥ 7/9 mức chi phí. Entry winner được đánh giá ở 25bps, nhưng nếu cost tăng lên 35–50bps (thực tế có thể xảy ra với slippage), liệu edge còn không? Đặc biệt quan trọng vì winner chỉ bỏ 14 trades — nếu edge đến từ việc tránh vài trade lỗ nhỏ, cost cao hơn có thể xóa sạch lợi ích.

Exposure trap — nếu MDD cải thiện (entry winner giảm MDD từ 37.1% xuống 27.3%), cần kiểm tra: cải thiện đó có đơn giản vì ít trade hơn (giảm exposure) hay vì chọn trade tốt hơn? Cách kiểm tra: lấy baseline, giảm exposure xuống bằng mức entry winner, rồi so sánh. Nếu baseline giảm exposure cũng cho MDD tương đương thì winner không thực sự thông minh hơn, chỉ trade ít hơn.

Thêm một cái dự án gốc không có nhưng nên có cho entry mới: kiểm tra churn rate giữa entry mới và exit hiện tại. Đếm số lần exit rồi re-entry trong ≤ 2 bar. Đây không phải validation gate truyền thống nhưng là rủi ro thực tế đã bàn.

Tóm lại, thiếu ba gate chính: bootstrap, cost sweep, exposure trap. Cả ba đều đã có protocol freeze sẵn từ dự án gốc, chỉ cần chạy lại trên kết quả mới. Nên yêu cầu chạy đủ ba gate này cho entry winner trước khi freeze, và sau này cho exit winner cũng vậy.

"""
