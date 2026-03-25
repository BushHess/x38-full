# E5 + EMA21D1 — Đặc tả Thuật toán Giao dịch

> **Loại:** Long-only, Trend-following, BTC-USDT Spot
> **Phiên bản:** 1.0 · Tháng 3 / 2026
> **Tài liệu Nội bộ — Không Phát hành Công khai**

---

## 1. Tổng quan

- **Timeframe chính:** H4 (4 giờ)
- **Timeframe phụ:** D1 (ngày) — chỉ dùng cho regime filter
- **Position sizing:** Binary — 100% NAV hoặc 0% (all-in / all-out)
- **Số tham số tối ưu:** 4

---

## 2. Tham số tối ưu

| Tham số | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `slow_period` | 120 | Chu kỳ EMA chậm trên H4. Fast period tự suy: `max(5, slow_period // 4) = 30` |
| `trail_mult` | 3.0 | Hệ số nhân Robust ATR cho trailing stop |
| `vdo_threshold` | 0.0 | Ngưỡng VDO tối thiểu để vào lệnh |
| `d1_ema_period` | 21 | Chu kỳ EMA trên D1 cho regime filter |

---

## 3. Hằng số cấu trúc (không tối ưu)

| Hằng số | Giá trị | Mục đích |
|---|---|---|
| `vdo_fast` | 12 | EMA nhanh của VDO |
| `vdo_slow` | 28 | EMA chậm của VDO |
| `ratr_cap_q` | 0.90 | Phân vị cap TR (percentile 90) |
| `ratr_cap_lb` | 100 | Lookback cửa sổ rolling quantile |
| `ratr_period` | 20 | Chu kỳ Wilder EMA cho robust ATR |

---

## 4. Chỉ báo

### 4.1 EMA Fast & Slow

Hướng trend, tính trên H4 close.

```
alpha  = 2 / (period + 1)
ema[0] = close[0]
ema[i] = alpha × close[i] + (1 − alpha) × ema[i−1]
```

- **EMA_slow** = EMA(close_h4, 120) ← 20 ngày
- **EMA_fast** = EMA(close_h4, 30) ← 5 ngày
- `trend_up = ema_fast > ema_slow`
- `trend_down = ema_fast < ema_slow`

### 4.2 Robust ATR — Đổi mới cốt lõi của E5

Standard ATR bị spike cực đại làm "nổ" (ví dụ COVID crash), giữ trailing stop quá rộng nhiều tuần. Robust ATR giải quyết bằng cách cap True Range tại percentile 90 trước khi smooth.

#### Bước 1 — True Range

```
TR[i] = max(high[i]−low[i], |high[i]−close[i−1]|, |low[i]−close[i−1]|)
```

#### Bước 2 — Cap tại rolling Q90

```
Với mỗi bar i (i >= 100):
  q = percentile(TR[i−100 : i], 90)
  TR_capped[i] = min(TR[i], q)
```

#### Bước 3 — Wilder EMA (period=20)

```
rATR[119] = mean(TR_capped[100:120])   ← seed
rATR[i]   = (rATR[i−1] × 19 + TR_capped[i]) / 20
```

### 4.3 VDO — Volume Delta Oscillator

MACD-style trên volume delta ratio. **Chỉ dùng cho ENTRY, không dùng cho exit.**

**Yêu cầu dữ liệu `taker_buy_base_vol`** — fail-closed nếu thiếu:

```
taker_sell = volume − taker_buy
vdr[i] = (taker_buy[i] − taker_sell[i]) / volume[i]   phạm vi [−1, +1]
```

> **Không có fallback.** Nếu thiếu taker data, strategy raise RuntimeError.
> OHLC fallback `(close-low)/(high-low)*2-1` đã bị xóa (2026-03-14, P0)
> vì lỗi semantic: price-location proxy không phải order-flow, cùng tên
> feature mà đổi bản chất là rủi ro vận hành nghiêm trọng.

**Tính VDO:**

```
VDO = EMA(vdr, 12) − EMA(vdr, 28)
VDO > 0 → áp lực mua tăng
```

### 4.4 D1 EMA Regime Filter — Đổi mới của EMA21D1

```
d1_ema    = EMA(d1_close, 21)
regime_ok = d1_close > d1_ema   ← boolean, tính trên D1
```

**Mapping sang H4:** mỗi bar H4 kế thừa regime của bar D1 hoàn thành gần nhất (`close_time D1 ≤ close_time H4`).

**Tại sao D1 chứ không phải H4?** EMA(126) trên H4 ≈ EMA(21) trên D1 về lookback, nhưng cập nhật 6× mỗi ngày và whipsaw nhiều hơn. D1 EMA(21) bản chất mượt hơn.

---

## 5. Logic vào lệnh (ENTRY)

Tất cả **4 điều kiện đồng thời:**

| # | Điều kiện | Mô tả |
|---|---|---|
| 1 | Đang FLAT | Không có vị thế hiện tại |
| 2 | `ema_fast[i] > ema_slow[i]` | Trend H4 đang lên |
| 3 | `vdo[i] > vdo_threshold` | Volume xác nhận (mặc định > 0.0) |
| 4 | `d1_regime_ok[i] == True` | D1 close > D1 EMA(21) |

**Kết quả:** `target_exposure = 1.0` (long 100% NAV), `peak_price = close[i]`

---

## 6. Logic thoát lệnh (EXIT)

Một trong hai điều kiện (kiểm tra theo thứ tự):

### Exit 1 — Robust ATR Trailing Stop

```
peak_price = max(peak_price, close[i])   ← cập nhật mỗi bar
trail_stop = peak_price − trail_mult × rATR[i]
Nếu close[i] < trail_stop → EXIT
```

### Exit 2 — Trend Reversal

```
Nếu ema_fast[i] < ema_slow[i] → EXIT
```

**Kết quả:** `target_exposure = 0.0`, reset `peak_price = 0`

---

## 7. Lưu ý quan trọng

- VDO **KHÔNG** dùng cho exit
- D1 regime **KHÔNG** dùng cho exit
- Không có take-profit cố định — lời chạy qua trailing stop
- Không có stop-loss cố định — trailing stop là dynamic
- Thứ tự kiểm tra: trailing stop trước, trend reversal sau

### 7.1 Regime Monitor (optional guard)

Tắt mặc định (`enable_regime_monitor: false`). Khi bật, thêm 2 hành vi:

- **Entry bị chặn** nếu monitor ở mức RED (`alert == 2`)
- **Exit bắt buộc** nếu đang giữ vị thế và monitor chuyển RED

Điều kiện RED: MDD 6 tháng > 55% HOẶC MDD 12 tháng > 70% (tính trên D1 close).

Đã PROMOTE trong research (Sharpe +0.14, chặn 15 entries — 12/15 lỗ). Xem `monitoring/regime_monitor.py`.

---

## 7b. Latency Sensitivity

> **CẢNH BÁO**: E5_ema21D1 yêu cầu thực thi tự động với SLA khởi động lại ≤ 4h (LT1).
> Tại D1 (4h delay): combined delta -0.186 → PASS.
> Tại D2 (8h delay): combined delta -0.396 → FAIL.
>
> Nếu không đảm bảo LT1, chuyển sang E0_ema21D1 (fallback) hoặc SM (manual).
> Chi tiết: [`LATENCY_TIER_DEPLOYMENT_GUIDE.md`](../../docs/algorithm/LATENCY_TIER_DEPLOYMENT_GUIDE.md)

---

## 8. Execution Model

- Signal tại bar `i` (close) → fill tại `open` bar `i+1`
- Warmup: 365 ngày đầu ở chế độ `no_trade` (chỉ tính indicator, không giao dịch)

**Cost model research (harsh — dùng trong mọi kết quả báo cáo):**

| Thành phần | Giá trị |
|---|---|
| Spread | 10 bps |
| Slippage | 5 bps |
| Taker fee | 0.15% |
| **Tổng round-trip** | **50 bps** |

Có 3 scenario: `smart` (13 bps RT), `base` (31 bps RT), `harsh` (50 bps RT). Config YAML dưới đây dùng `harsh` để khớp với kết quả research.

---

## 9. Config YAML tối thiểu

```yaml
engine:
  symbol: BTCUSDT
  timeframe_h4: 4h
  timeframe_d1: 1d
  warmup_days: 365
  warmup_mode: no_trade
  scenario_eval: harsh
  initial_cash: 10000.0

strategy:
  name: vtrend_e5_ema21_d1
  slow_period: 120.0
  trail_mult: 3.0
  vdo_threshold: 0.0
  d1_ema_period: 21

risk:
  max_total_exposure: 1.0
  kill_switch_dd_total: 0.45
```

---

## 10. Dòng chảy tín hiệu

**Precompute (on_init):**

- EMA_fast(30), EMA_slow(120) ← H4 close
- Robust ATR (Q90, lb=100, p=20) ← H4 HLC
- VDO(12, 28) ← H4 OHLCV + taker_buy
- D1 EMA(21) regime → map to H4 ← D1 close

**Bar-by-bar (on_bar):**

```
FLAT?
  trend_up AND vdo > 0 AND d1_regime → LONG 100%

IN POSITION?
  close < peak − 3 × rATR → EXIT (trailing stop)
  ema_fast < ema_slow      → EXIT (trend reversal)
```
