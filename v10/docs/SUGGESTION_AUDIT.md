# Đối chiếu gợi ý chống whipsaw vs Code & Nghiên cứu V10

**Date:** 2026-02-23
**Ref:** 6 gợi ý anti-whipsaw cho trend-following

---

## Tổng quan nhanh

| # | Gợi ý | Đã implement? | Đã test? | Kết quả |
|:-:|-------|:---:|:---:|---------|
| 1 | Hiểu khi nào bị "cưa" | Có (regime.py) | Có | TOPPING -17.5%, structural |
| 2a | Bộ lọc volatility | **Có** (vol brake) | Có | Đang dùng production |
| 2b | Bộ lọc regime (ADX, Hurst, Choppiness) | **Một phần** | Một phần | ADX trong analysis, không trong trading |
| 2c | Bộ lọc volume/on-chain | **Có** (VDO) | Có | Core signal, đang dùng |
| 3 | Mean-reversion vùng cực đoan | **Một phần** | Có | RSI gating, nhưng chưa có MR strategy |
| 4a | Vol-adjusted sizing | **Có** | Có | Đang dùng production |
| 4b | DD-based scaling | **Có code**, disabled | Có (cô lập) | HOLD (harsh -28 điểm) |
| 5 | Multi-timeframe confirmation | **Có** | Có | H4 signal + D1 regime, đang dùng |
| 6 | Framework tổng hợp | **Phần lớn** | Có | Thiếu ADX gating + MR mode |

---

## Chi tiết từng gợi ý

### 1. Hiểu rõ vấn đề: Khi nào trend-following bị "cưa"?

**Trạng thái: ĐÃ NGHIÊN CỨU KỸ**

**Code:** `v10/research/regime.py` — Hệ thống phân loại 6 regime:
```
SHOCK   — |daily return| > 8%
BEAR    — close < EMA_slow AND EMA_fast < EMA_slow
CHOP    — ATR% > 3.5% AND ADX < 20
TOPPING — |close − EMA_fast|/EMA_fast < 1% AND ADX < 25
BULL    — close > EMA_slow AND EMA_fast > EMA_slow
NEUTRAL — everything else
```

**Lưu ý:** Hệ thống này dùng cho **phân tích hậu kỳ** (research/reporting), KHÔNG
dùng trực tiếp trong trading logic. Trading logic dùng hệ thống 3 regime riêng
(RISK_ON / CAUTION / RISK_OFF) dựa trên EMA50/200 với hysteresis.

**Nghiên cứu đã xác nhận:**
- TOPPING gây thua lỗ -17.5% (base scenario) — structural weakness
- SHOCK gây -14.1% — nhưng ngắn hạn, recovery nhanh
- CHOP gây false exits 16.67% (thấp nhất!)
- 3 vòng optimization (20 configs) không tìm được cách giảm TOPPING loss mà không
  phá hủy BULL capture

**Kết luận:** Vấn đề được hiểu rất rõ. Sideway/TOPPING là structural limitation của
trend-following, không phải bug có thể fix bằng parameter tuning.

---

### 2a. Bộ lọc Volatility (ATR / Bollinger Width)

**Trạng thái: ĐÃ IMPLEMENT & ĐANG DÙNG**

**Code:** `v8_apex.py` lines 421-426 — **Vol Brake**
```python
# Vol brake: khi ATR/price > ngưỡng → giảm size
if c.enable_vol_brake and mid > 0:
    atr_f = self._h4_atr_f[idx]
    if atr_f / mid > c.vol_brake_atr_ratio:  # 0.035 = 3.5%
        base *= c.vol_brake_mult  # ×0.40 = giảm 60%
```

**Params:**
- `enable_vol_brake: True` (bật mặc định)
- `vol_brake_atr_ratio: 0.035` — ngưỡng ATR/price
- `vol_brake_mult: 0.40` — giảm sizing xuống 40%

**Code:** `v8_apex.py` lines 458-461 — **Compression Detection**
```python
# ATR fast/slow ratio < 0.75 → compression breakout boost
is_comp = atr_s > 0 and (atr_f / atr_s) < c.compression_ratio
if is_comp:
    sz *= c.compression_boost  # ×1.0 (neutral hiện tại)
```

**Đánh giá:**
- Vol brake xử lý vùng "volatility quá cao" (shock/topping) → DONE
- Compression detection xử lý vùng "volatility quá thấp" → DONE nhưng boost=1.0
  (neutral, không tăng size khi compression)
- **CHƯA CÓ:** "Chỉ vào lệnh khi ATR ở vùng vừa phải" — không có hard gate
  chặn entry khi ATR quá thấp. Vol brake chỉ giảm size, không chặn hoàn toàn.
  Tuy nhiên, VDO entry threshold + HMA confirmation đã làm vai trò lọc gián tiếp
  (VDO yếu trong sideway → không vào lệnh).

---

### 2b. Bộ lọc Regime (ADX, Hurst Exponent, Choppiness Index)

**Trạng thái: MỘT PHẦN — ADX dùng trong analysis, KHÔNG trong trading**

**ADX:**
- `v10/research/regime.py` line 65-110: ADX **đã implement** đầy đủ, dùng trong
  phân loại CHOP (ADX < 20) và TOPPING (ADX < 25).
- **NHƯNG:** ADX chỉ dùng trong research regime classifier, KHÔNG nằm trong
  `v8_apex.py` trading logic. Strategy dùng EMA50/200 hysteresis thay vì ADX.

**Hurst Exponent:**
- **CHƯA implement.** Không có code, không có nghiên cứu.

**Choppiness Index:**
- **CHƯA implement.** Không có code, không có nghiên cứu.

**Nghiên cứu liên quan:**
- Gate study test `d1_regime_off_bars: 4→2` (faster regime switching, tương tự ADX
  gating nhanh hơn) → **HOLD**: harsh score giảm 16.6 điểm. Regime switching
  nhanh hơn gây whipsaw trong BULL.

**Đánh giá:**
- ADX tồn tại trong codebase nhưng **chỉ dùng cho post-hoc analysis**, không gating
  entry/exit. Đây là gap lớn nhất so với gợi ý.
- Hurst và Choppiness chưa implement. Tuy nhiên, EMA50/200 regime + vol brake
  đang đảm nhận vai trò tương tự (nhận diện trending vs non-trending).
- **Rủi ro nếu thêm ADX gating:** Nghiên cứu cho thấy thêm filters thường hại
  BULL capture nhiều hơn lợi ích giảm TOPPING loss.

---

### 2c. Bộ lọc Volume / On-chain

**Trạng thái: VOLUME ĐÃ IMPLEMENT (CORE SIGNAL). ON-CHAIN CHƯA CÓ.**

**Volume — VDO (Volume Delta Oscillator):**
- `v8_apex.py` lines 217-226: VDO là **tín hiệu entry chính**
```python
# VDO = EMA_fast(taker_buy_ratio) − EMA_slow(taker_buy_ratio)
vdr = tbv / sv  # taker buy base vol / total vol
self._h4_vdo = _ema(vdr, c.vdr_fast_period) - _ema(vdr, c.vdr_slow_period)
```
- Entry gate: `vdo > vdo_entry_threshold (0.004)` — chỉ mua khi taker buy
  pressure tăng
- Entry sizing: `vc = vdo / vdo_scale` — size tỷ lệ với VDO strength
- "Volume giảm dần khi giá tăng → topping" → VDO tự nhiên giảm khi taker buying
  yếu đi, nên strategy tự động giảm/dừng entry

**On-chain (exchange inflow, funding rate, etc.):**
- **CHƯA CÓ.** Không có code, không có data pipeline.
- Data file `data/bars_btcusdt_2016_now_h1_4h_1d.csv` chỉ chứa OHLCV + taker_buy_vol.
- Không có exchange reserve, funding rate, hoặc on-chain metrics.

**Đánh giá:**
- VDO đã capture "volume confirmation" rất hiệu quả — đây là core edge của strategy
- On-chain data có thể giúp detect topping sớm hơn nhưng đòi hỏi:
  - Data pipeline mới (API Glassnode/CryptoQuant hoặc tương tự)
  - Backtest data lịch sử (khó tìm cho on-chain)
  - Thêm indicators + gates vào strategy
  - Risk of overfitting (on-chain relationships may not be stationary)

---

### 3. Kết hợp Mean-Reversion ở vùng cực đoan

**Trạng thái: MỘT PHẦN — có RSI gating, KHÔNG CÓ mean-reversion strategy**

**Đã implement:**

1. **RSI overbought → giảm size 50%** (line 463-464):
```python
if rsi_v > c.rsi_overbought:  # 75.0
    sz *= 0.50
```

2. **RSI oversold → bypass HMA, tăng size 30%** (lines 405-406, 465-466):
```python
oversold = rsi_v < c.rsi_oversold  # 30.0
# ... cho phép entry dưới HMA nếu oversold
if oversold:
    sz *= 1.30
```

3. **Trailing stop tighten khi profit đạt 25%** (lines 344-346):
```python
# Siết trailing từ 3.5×ATR → 2.5×ATR khi đã lãi >= 25%
if self._peak_profit >= c.trail_tighten_profit_pct:
    mult = c.trail_tighten_mult  # 2.5
```

**CHƯA implement:**
- **Không có mean-reversion mode:** Khi RSI > 80 trên daily/weekly, strategy chỉ
  giảm size 50%, KHÔNG chuyển sang sell/short hoặc đứng ngoài hoàn toàn.
  (Spot-only, long-only → không thể short. Nhưng có thể exit hoàn toàn.)
- **Không check khoảng cách giá vs MA200:** Gợi ý "giá xa MA200 >40-50% → giảm
  exposure" chưa implement.
- **Bollinger Band:** Chưa implement.

**Nghiên cứu:**
- Test `rsi_overbought: 75→70` → **REJECT** (MDD 43.17%). Tighter RSI chặn quá
  nhiều entry BULL.
- Test `trail_tighten_profit_pct: 0.20→0.25` → **APPLIED**. Trail tighten sớm hơn
  giúp chốt lời tốt hơn.

**Đánh giá:**
- Strategy đang ở mức "giảm size khi overbought" nhưng chưa "chuyển mode". Tuy
  nhiên, do là spot long-only, mean-reversion thực sự (short) không khả thi.
- Có thể thêm: giá xa MA200 >X% → giảm max_exposure hoặc dừng entry mới. Nhưng
  rủi ro kill parabolic runs (BTC thường xa MA200 >50% trong BULL runs).

---

### 4a. Volatility-Adjusted Sizing

**Trạng thái: ĐÃ IMPLEMENT & ĐANG DÙNG**

**Code:** `v8_apex.py` lines 410-418:
```python
# Base exposure = target_vol / actual_vol (D1 annualized)
va = self._d1_vol_ann[d1i]     # D1 realized vol (annualized)
base = min(c.max_total_exposure, c.target_vol_annual / va)
if regime == Regime.CAUTION:
    base *= c.caution_mult  # ×0.50
```

**Cơ chế:**
- `target_vol_annual: 0.85` — target volatility portfolio
- `d1_vol_ann` = annualized D1 realized volatility (30-day EWM)
- Khi vol cao (topping/shock): `va` tăng → `base = 0.85/va` giảm → size nhỏ hơn
- Khi vol thấp (sideway): `va` giảm → `base` tăng → size lớn hơn
- Cap bởi `max_total_exposure: 1.0` (không leverage)

**Đánh giá:** Đúng như gợi ý "Size = Risk% / ATR". Đã implement đầy đủ.

---

### 4b. Drawdown-Based Scaling

**Trạng thái: ĐÃ IMPLEMENT NHƯNG DISABLED. ĐÃ TEST → REJECT.**

**Code:** `v8_apex.py` lines 429-441:
```python
# DD adaptive: giảm size tuyến tính khi drawdown tăng
if c.enable_dd_adaptive and ...:
    dd = 1.0 - state.nav / self._equity_peak
    if dd > c.dd_adaptive_start:    # 0.16 = 16%
        prog = min((dd - 0.16) / (0.28 - 0.16), 1.0)
        base *= 1.0 - prog * (1.0 - c.dd_adaptive_floor)  # floor = 0.35
```

**Params:**
- `enable_dd_adaptive: False` — **disabled mặc định**
- `dd_adaptive_start: 0.16` — bắt đầu giảm khi DD > 16%
- `dd_adaptive_floor: 0.35` — giảm tối đa xuống 35% size
- Tuyến tính từ 100%→35% trong khoảng DD 16%→28%

**Nghiên cứu:**
- Gate study (`out_v10_full_eval`): `peak_dd_adaptive` = enable_dd_adaptive + peak
  emergency ref → **REJECT**, score 22.95, MDD 40.41%
- V9 MDD analysis: "DD-adaptive sizing: WORTH TESTING — trades MDD for recovery speed"
- V8 opt_aggressive: Có enable dd_adaptive → Calmar 0.70 (tốt hơn baseline V8)

**Test cô lập (2026-02-23, `out_v10_dd_adaptive/`):**
- `dd_adaptive_only`: harsh 60.90 (−28), CAGR 26.56% (−10.7%) → HOLD
- `dd_adaptive_gentle` (start=0.20): harsh 81.72 (−7.2), CAGR 33.97% → HOLD
- `dd_adaptive_mild` (floor=0.50): harsh 72.01 (−16.9), CAGR 31.43% → HOLD

**Đánh giá:** DD-adaptive **KHÔNG hiệu quả** cho BTC spot long-only, kể cả khi
test cô lập. Nguyên nhân: giảm size trong drawdown cũng giảm size trong recovery.
BTC recovery thường rất mạnh (V-shape), nên mất profit recovery > tiết kiệm từ
giảm drawdown. Gap nghiên cứu đã được lấp — kết luận: disable là đúng.

---

### 5. Multi-Timeframe Confirmation

**Trạng thái: ĐÃ IMPLEMENT & ĐANG DÙNG**

**Code:**

- **D1 (daily):** Regime gating — EMA50/200 hysteresis
  - RISK_OFF → chặn mọi entry
  - CAUTION → giảm size 50%
  - RISK_ON → full entry

- **H4 (4-hour):** Tất cả signal + indicators
  - VDO (entry signal)
  - HMA55 (trend confirmation)
  - RSI14 (overbought/oversold)
  - ATR14/50 (volatility, trailing stop)
  - Acceleration (momentum confirmation)

- **Logic MTF:**
  ```
  D1 regime = RISK_ON + H4 VDO > threshold + H4 price > HMA → entry
  D1 regime = CAUTION + same signals → entry with 50% size
  D1 regime = RISK_OFF → no entry regardless of H4 signals
  ```

**Đánh giá:** Đúng như gợi ý "khung lớn xác định trend, khung trung cho signal".
Đã implement 2-timeframe (D1+H4). Chưa có weekly (W1) — nhưng D1 EMA200 ~ weekly
trend, nên overlap đáng kể.

**Chưa implement:** "Weekly cho dấu hiệu suy yếu (momentum giảm, divergence)" —
không có weekly momentum divergence check. Tuy nhiên, D1 regime hysteresis
(confirm_bars, off_bars) đảm nhận vai trò tương tự.

---

### 6. Framework tổng hợp (bảng ADX + Volume + RSI)

**Đối chiếu từng hàng:**

| Điều kiện gợi ý | Code V10 | Trạng thái |
|---|---|---|
| ADX > 25 + Volume tăng → full size | RISK_ON + VDO > threshold → full size | **Tương đương** (dùng VDO thay ADX) |
| ADX 20-25 + volume yếu → 50% size | CAUTION regime → 50% size | **Tương đương** (dùng EMA crossover thay ADX) |
| ADX < 20 → không giao dịch | RISK_OFF → no entry | **Tương đương** |
| RSI > 80 + xa MA200 → chốt lời, no entry | RSI > 75 → 50% size + trail tighten | **Một phần**: giảm size nhưng không chặn entry, không check MA200 distance |
| Funding rate + exchange inflow → giảm exposure | Không có | **CHƯA IMPLEMENT** |

---

## Tóm tắt: Cái gì thiếu?

### Đã implement tốt (6/10):
1. Vol brake (ATR filter) ✓
2. VDO (volume/buying pressure) ✓
3. Vol-adjusted sizing ✓
4. Multi-timeframe (D1+H4) ✓
5. Regime gating (EMA hysteresis) ✓
6. RSI overbought giảm size + trailing tighten ✓

### Implement nhưng disabled — đã test cô lập → CONFIRMED KHÔNG HIỆU QUẢ (1/10):
7. DD-adaptive sizing — đã test cô lập (2026-02-23), tất cả 3 variants HOLD.
   Giảm size trong DD cũng giảm recovery capture → net negative. Disable đúng.

### Chưa implement (3/10):
8. **ADX gating trực tiếp trong trading logic** — ADX tồn tại trong research nhưng
   không dùng cho entry/exit decisions
9. **On-chain data** (exchange inflow, funding rate) — không có data pipeline
10. **Price distance from MA200 gate** — không check "giá xa MA >X% → giảm exposure"

### Chưa implement và khó implement (conceptual):
11. **Hurst Exponent** — cần thêm indicator + backtest
12. **Choppiness Index** — cần thêm indicator + backtest
13. **Mean-reversion mode switch** — spot long-only nên giới hạn (chỉ có thể exit,
    không short)
14. **Weekly timeframe divergence** — D1 EMA200 đã cover phần lớn

---

## Khuyến nghị ưu tiên

### ~~Ưu tiên 1: Test cô lập `enable_dd_adaptive`~~ → ĐÃ TEST, KHÔNG HIỆU QUẢ

**Study:** `out_v10_dd_adaptive/` (2026-02-23)

Test 3 variants DD-adaptive cô lập (giữ emergency_ref=pre_cost_legacy):

| Variant | Harsh Score | CAGR% | TOPPING% | Tag |
|---------|:---:|:---:|:---:|:---:|
| **baseline** | **88.94** | **37.26** | **-17.5%** | **PROMOTE** |
| dd_adaptive_only (start=0.16, floor=0.35) | 60.90 | 26.56 | -22.0% | HOLD |
| dd_adaptive_gentle (start=0.20) | 81.72 | 33.97 | -17.7% | HOLD |
| dd_adaptive_mild (floor=0.50) | 72.01 | 31.43 | -21.5% | HOLD |

**Kết luận:** DD-adaptive giảm size trong drawdown nhưng CŨNG giảm size trong
RECOVERY (BTC recovery thường rất mạnh) → mất profit recovery lớn hơn tiết kiệm
từ giảm DD. Kể cả variant nhẹ nhất (gentle, start=20%) vẫn kém baseline 7 điểm
harsh score. **CONFIRMED: DD-adaptive không phù hợp cho BTC spot long-only.**

### Ưu tiên 2: Thêm ADX gating vào trading logic (FEATURE MỚI)
- ADX đã có trong codebase (`regime.py`)
- Cần port vào `v8_apex.py` và thêm params (adx_min_trend, adx_sideway_threshold)
- Rủi ro: thêm filter có thể hại BULL capture (evidence từ regime study)

### Ưu tiên 3: Price-to-MA200 distance gate (FEATURE MỚI)
- Dễ implement (EMA200 đã tính sẵn ở line 215)
- Khi price/ema200 > 1.4 → giảm max_exposure
- Rủi ro: kill parabolic BTC runs

### Ưu tiên thấp: On-chain data
- Đòi hỏi data pipeline mới, historical data, API
- ROI không rõ ràng — on-chain relationships có thể non-stationary
