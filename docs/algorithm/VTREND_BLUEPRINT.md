# VTREND: Complete Rebuild Blueprint

> **⚠ CORRECTION (2026-03-09):** Section 7 below is frozen at Study #41 (2026-03-05)
> and states E0_ema21D1 = PROMOTE, E5 = HOLD. This is **OUTDATED**. After framework
> reform (Wilcoxon WFO, PSR gate, bootstrap CI), re-validation results:
>
> - **E5_ema21D1 = PRIMARY CANDIDATE (HOLD)** — 6/7 gates PASS, WFO robustness
>   FAIL (Wilcoxon p=0.125, Bootstrap CI crosses zero). Underresolved, not negative.
> - **E0_ema21D1 = HOLD** — WFO robustness FAIL (PSR demoted to info)
>
> See `CHANGELOG.md` (2026-03-17) and `results/full_eval_e5_ema21d1/` for details.
> Section 7 is preserved as historical record only.

> Tài liệu này chứa đầy đủ thông tin để xây dựng lại VTREND và toàn bộ bộ nghiên
> cứu/xác thực từ đầu, sạch sẽ, không phụ thuộc codebase cũ.
>
> Nguyên tắc: mỗi bước phải được chứng minh bằng toán học trước khi tiến sang bước tiếp.

---

## Mục lục

1. [Thuật toán VTREND](#1-thuật-toán-vtrend)
2. [Kết luận đã chứng minh](#2-kết-luận-đã-chứng-minh)
3. [Kết luận đã bác bỏ](#3-kết-luận-đã-bác-bỏ)
4. [Bộ công cụ xác thực](#4-bộ-công-cụ-xác-thực)
5. [Trình tự xây dựng lại](#5-trình-tự-xây-dựng-lại)
6. [Phụ lục: Công thức & Hằng số](#6-phụ-lục-công-thức--hằng-số)
7. [Parity Evaluation — 6 Strategy Comparison](#7-parity-evaluation--6-strategy-comparison-study-41-2026-03-05)

---

## 1. Thuật toán VTREND

### 1.1 Tổng quan

VTREND là chiến lược trend-following đơn giản cho BTC-USDT spot trên khung H4.
Long-only, binary (vào 100% hoặc ra 0%), 3 tham số có thể điều chỉnh.

### 1.2 Ba tham số

| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| `slow_period` | 120 (H4 bars = 20 ngày) | Chu kỳ EMA chậm — xác định xu hướng |
| `trail_mult` | 3.0 | Hệ số nhân ATR cho trailing stop |
| `vdo_threshold` | 0.0 | Ngưỡng VDO để lọc entry (0.0 = bất kỳ dòng tiền dương) |

Tham số dẫn xuất: `fast_period = max(5, slow_period // 4)`.

### 1.3 Hằng số cấu trúc (không tối ưu)

| Hằng số | Giá trị | Lý do |
|---------|---------|-------|
| `atr_period` | 14 | ATR 14 bars tiêu chuẩn (~2.3 ngày H4) — E0 only |
| `vdo_fast` | 12 | Chu kỳ nhanh VDO (~2 ngày) |
| `vdo_slow` | 28 | Chu kỳ chậm VDO (~4.7 ngày) |

> **Note**: E5 (PRIMARY since 2026-03-09) replaces `atr_period` with robust ATR
> parameters: `ratr_cap_q=0.90`, `ratr_cap_lb=100`, `ratr_period=20`.

### 1.4 Chỉ báo

#### EMA (Exponential Moving Average)
```
alpha = 2 / (period + 1)
ema[0] = series[0]
ema[i] = alpha * series[i] + (1 - alpha) * ema[i-1]
```

#### ATR (Average True Range — Wilder's RMA)
```
TR[i] = max(high[i] - low[i], |high[i] - close[i-1]|, |low[i] - close[i-1]|)
ATR[0..period-1] = mean(TR[0..period-1])
ATR[i] = (ATR[i-1] * (period-1) + TR[i]) / period    (i >= period)
```

#### VDO (Volume Delta Oscillator)
```
Yêu cầu taker_buy_base_vol — RuntimeError nếu thiếu.

taker_sell = volume - taker_buy
vdr = (taker_buy - taker_sell) / volume

VDO = EMA(vdr, fast=12) - EMA(vdr, slow=28)
```

VDO là oscillator MACD-style trên tỷ lệ dòng tiền mua/bán. Dương = áp lực mua tăng.

> **Không có fallback OHLC.** Fallback cũ `(close-low)/(high-low)*2-1` đã bị xóa
> (2026-03-14, P0) vì lỗ semantic: price-location ≠ order-flow.

### 1.5 Logic Entry/Exit

```
TẠI MỖI BAR i:

NẾU ĐANG FLAT (không có vị thế):
    NẾU ema_fast[i] > ema_slow[i]      # xu hướng tăng
    VÀ vdo[i] > vdo_threshold:          # dòng tiền xác nhận
        → SIGNAL: mua tại close bar tiếp theo

NẾU ĐANG CÓ VỊ THẾ:
    peak = max(peak, close[i])          # cập nhật đỉnh trailing

    NẾU close[i] < peak - trail_mult * atr[i]:    # trailing stop kích hoạt
        → SIGNAL: bán tại close bar tiếp theo

    HOẶC NẾU ema_fast[i] < ema_slow[i]:           # xu hướng đảo chiều
        → SIGNAL: bán tại close bar tiếp theo
```

**Lưu ý quan trọng:**
- VDO chỉ dùng cho ENTRY, không dùng cho EXIT
- Tín hiệu tạo ở bar `i`, khớp lệnh ở bar `i+1` (close bar trước làm proxy cho open)
- Trailing peak reset mỗi khi vào vị thế mới

### 1.6 Mô hình chi phí

```
cost_per_side = 25 bps = 0.0025

Mua:  qty = cash / (price * (1 + 0.0025))
Bán:  cash = qty * price * (1 - 0.0025)

Round-trip: 50 bps (cố ý cao hơn thực tế để tạo cushion)
```

Ba kịch bản chi phí trong hệ thống:
- **smart**: 13 bps RT (spread=3, slip=1.5, fee=0.035%)
- **base**: 31 bps RT (spread=5, slip=3, fee=0.10%)
- **harsh**: 50 bps RT (spread=10, slip=5, fee=0.15%) ← dùng cho tất cả nghiên cứu

### 1.7 Metric

```
ANN = sqrt(6.0 * 365.25)            # H4: sqrt(2191.5) ≈ 46.813

Sharpe = (mean(bar_returns) / std(bar_returns)) * ANN
         # std dùng population variance (ddof=0)

CAGR = ((1 + total_return)^(1/years) - 1) * 100
       # years = n_bars / bars_per_year

MDD = max(1 - NAV/peak_NAV) * 100

Calmar = CAGR / MDD                 # 0 nếu MDD < 0.01%
```

---

## 2. Kết luận đã chứng minh

### 2.1 EMA trend signal là genuine

| Bằng chứng | Kết quả |
|------------|---------|
| Permutation test (10K, circular-shift) | p = 0.0003 |
| Bonferroni correction (K=16) | PASS (threshold 0.003125) |
| Holm correction | PASS |
| Benjamini-Hochberg | PASS |

**Null**: Circular-shift cả hai mảng EMA bởi offset ngẫu nhiên ∈ [500, n-500].
Bảo toàn: smoothness, số lần cross. Phá vỡ: alignment với giá.

### 2.2 ATR trailing stop là genuine

| Bằng chứng | Kết quả |
|------------|---------|
| Permutation test (10K, block-shuffle) | p = 0.0003 |
| Bonferroni (K=16) | PASS |

**Null**: Block-shuffle mảng ATR (block=40 bars ≈ 7 ngày).
Bảo toàn: phân phối ATR, autocorrelation trong block. Phá vỡ: local volatility ↔ stop distance.

### 2.3 VDO filter là genuine (qua consistency, không qua single-point)

| Bằng chứng | Kết quả |
|------------|---------|
| Permutation (single timescale) | p = 0.060 (marginal, fail Bonferroni) |
| Bootstrap consistency (16 timescales) | VDO helps 16/16 timescales |
| Binomial test (16/16) | p = 1.5e-5 |
| Mean Sharpe lift | +0.16 to +0.21 across all timescales |
| P(VDO helps) per timescale | 55-63% (mild but consistent) |

**Kết luận**: VDO yếu ở bất kỳ timescale đơn lẻ nào, nhưng **consistency** qua 16
timescales chứng minh nó là genuine filter (không phải noise). Giá trị chính: giảm trade
count, giảm MDD.

### 2.4 Alpha tồn tại trên vùng timescale rộng (robust, không phải overfit)

| Metric | Giá trị |
|--------|---------|
| Productive region (med Sharpe > 0) | slow = 30-720 H4 bars (5-120 ngày) |
| Productive width | 24x |
| Strong region (P(CAGR>0) > 70%) | slow = 60-144 (10-24 ngày) |
| Strong width | 2.4x |
| Sharpe plateau trong strong region | 0.425 - 0.442 (spread chỉ 0.017) |
| Smoothness (adjacent-timescale r) | 0.86-0.95 |
| Real data percentile | 94-99% ở mọi timescale |

**Ý nghĩa**: Alpha đến từ GENERIC trend-following, không phải lựa chọn slow_period cụ
thể. Bất kỳ slow_period nào trong vùng 60-144 đều cho kết quả tương đương.

### 2.5 H4 là resolution tối ưu

| Resolution | Productive | Strong | Peak Sharpe | Peak Calmar |
|-----------|-----------|--------|-------------|-------------|
| H1 | NONE | NONE | -0.288 | -0.195 |
| **H4** | **10-120d (24x)** | **10-24d (2.4x)** | **0.442** | **0.160** |
| D1 | 5-120d (24x) | NONE | 0.419 | 0.140 |

- H1 bị cost drag phá hủy (600-800 trades, toàn bộ negative Sharpe)
- D1 productive nhưng yếu hơn H4 ở vùng 10-28 ngày, mạnh hơn ở vùng 33-120 ngày
- H4 thắng ở cả peak Sharpe và peak Calmar

### 2.6 Vol-target 15% là sizing tối ưu

| Method | Sharpe | Calmar | MDD | CAGR |
|--------|--------|--------|-----|------|
| f=1.0 (binary) | 1.276 | 1.268 | 41.5% | 52.7% |
| f=0.30 (fixed) | 1.263 | 1.041 | 16.1% | 16.7% |
| **vol=15%** | **1.526** | **1.608** | **14.5%** | **23.4%** |

Sharpe gần bất biến với fraction (toán học: μ/σ cancels scalar scaling).
Vol-targeting thắng vì tập trung exposure khi vol thấp, giảm khi vol cao.

### 2.7 V8 complexity không có giá trị

V8 Apex (40+ params) vs VTREND (3 params):
- Bootstrap: không khác biệt Sharpe (P(V8 better) = 44.8%)
- V8 có MDD cao hơn đáng kể
- VTREND 3 params đạt hiệu quả tương đương V8 40+ params

---

## 3. Kết luận đã bác bỏ

### 3.1 VPULL (pullback entry)

| Test | Kết quả |
|------|---------|
| Permutation (10K, random skip) | p = 1.000 (TỆ HƠN random!) |
| Real score vs null median | 27.01 vs 115.22 |
| Paired bootstrap Sharpe | 0.258 vs 0.432 (VTREND thắng) |
| VPULL thắng bao nhiêu timescales | 0/16 |
| Skip rate | 48.3% (bỏ lỡ gần nửa entries) |

**Cơ chế thất bại**: BTC trending mạnh không pullback. Chờ pullback = bỏ lỡ moves lớn nhất.

### 3.2 Regime gates (thêm điều kiện EMA dài hạn vào entry)

- gate360 (price > EMA360): P(better) = 49.3% → no signal
- gate500 (price > EMA500): P(better) = 46.2% → no signal
- gate360x (entry + exit gate): P(better) = 32.6% → slightly harmful

### 3.3 Regime-aware position sizing

Không regime approach nào beat vol=15%:
- return_prop: P(better) = 52.7%
- regime_vol: P(better) = 41.0%
- hand_cons: P(better) = 37.6%
- half_kelly: P(better) = 37.0%

**Lý do**: VTREND profitable trong TẤT CẢ 6 regimes → không regime nào cần tránh.

### 3.4 H1 resolution

Toàn bộ 16 timescales negative (median Sharpe -0.29 to -0.38). P(CAGR>0) = 5-10%.
Cost drag từ 600-800 trades phá hủy signal.

---

## 4. Bộ công cụ xác thực

### 4.1 Block Bootstrap

**Mục đích**: Ước lượng phân phối metrics trong điều kiện thị trường tương tự nhưng
không giống hệt lịch sử. Model-free, không giả định phân phối.

**Xây dựng**:
```
1. Tính return ratios từ dữ liệu thật:
   cr[i] = close[i+1] / close[i]
   hr[i] = high[i+1] / close[i]     # high ratio so với close trước
   lr[i] = low[i+1] / close[i]      # low ratio

2. Chọn n_blocks = ceil(n_bars / block_size) block starts ngẫu nhiên đều
   mỗi start ∈ [0, len(cr) - block_size]

3. Ghép index liên tiếp từ mỗi block, cắt còn đúng n_bars

4. Tái tạo giá synthetic:
   c[0] = p0
   c[1:] = p0 * cumprod(cr[sampled_indices])

5. Tái tạo high/low/volume từ ratios × close trước đó
   h = max(h_reconstructed, c)     # enforce h >= c
   l = min(l_reconstructed, c)     # enforce l <= c
```

**Tham số chuẩn**:
- Paths: 2000
- Seed: 42
- Block size: ~10 ngày vật lý (H1=240, H4=60, D1=10 bars)
- Initial price: close đầu tiên sau warmup

**Tính chất bảo toàn**: Phân phối đồng thời (return, high, low, vol, taker_buy) trong
mỗi block. Biên giới giữa blocks là independent.

### 4.2 Permutation Tests

Ba loại null hypothesis, mỗi loại phá vỡ đúng một feature:

#### EMA Circular-Shift
```
offset = random ∈ [500, n - 500]
ema_fast_null = np.roll(ema_fast, offset)
ema_slow_null = np.roll(ema_slow, offset)
```
Bảo toàn: smoothness, transition count. Phá vỡ: temporal alignment với giá.

#### VDO Random Filter
```
1. Chạy chiến lược KHÔNG có VDO → đếm trades = T_base
2. Chạy chiến lược CÓ VDO → đếm trades = T_real
3. skip_rate = 1 - T_real / T_base

Null: tại mỗi entry tiềm năng (EMA cross up), skip với xác suất skip_rate
```
Bảo toàn: trend structure, trade frequency. Phá vỡ: VDO lựa chọn entry nào.

#### ATR Block-Shuffle
```
Chia mảng ATR thành blocks 40 bars (~7 ngày)
Xáo trộn thứ tự blocks (giữ nguyên nội dung trong block)
```
Bảo toàn: ATR distribution, within-block autocorrelation.
Phá vỡ: local volatility ↔ stop distance alignment.

**Tham số**: N_PERM = 10,000. P-value = mean(null_scores >= real_score).

### 4.3 Composite Score (test statistic cho permutation)

```
score = 2.5 * cagr_pct
      - 0.60 * mdd_pct
      + 8.0 * max(0, sharpe)
      + 5.0 * max(0, min(profit_factor, 3.0) - 1.0)
      + min(n_trades / 50, 1.0) * 5.0

Nếu n_trades < 10: return -1,000,000
```

| Thành phần | Trọng số | Vai trò |
|-----------|---------|---------|
| CAGR | +2.5 | Thưởng tăng trưởng |
| MDD | -0.60 | Phạt drawdown |
| Sharpe | +8.0 | Thưởng risk-adjusted (chỉ Sharpe dương) |
| Profit Factor | +5.0 | Thưởng PF (cap tại 3.0, shift -1.0) |
| Trade count | +5.0 | Ramp tuyến tính 0→50 trades |

### 4.4 Paired Comparison Protocol

```
Trên CÙNG bootstrap path, chạy cả hai variant.
delta = metric_A - metric_B (mỗi path)

Significance: P(delta > 0) > 97.5% → significant ở α=0.05 (one-sided)
95% CI: percentile [2.5, 97.5] của phân phối delta

Cho MDD (thấp hơn = tốt hơn): delta = B_MDD - A_MDD
```

### 4.5 Multiple Comparison Correction

Khi test K hypotheses đồng thời:

| Method | Type | Threshold | Tính chất |
|--------|------|-----------|-----------|
| Bonferroni | FWER | α/K | Nghiêm nhất, hay bỏ sót |
| Holm Step-Down | FWER | α/(K-i) cho rank i | Bớt nghiêm, vẫn kiểm soát FWER |
| Benjamini-Hochberg | FDR | α×i/K cho rank i | Kiểm soát tỷ lệ false discovery |

Luôn bao gồm cả null results vào tổng K (tăng K → correction nghiêm hơn).

### 4.6 Robustness Definitions

| Khái niệm | Định nghĩa | Ngưỡng |
|-----------|-----------|--------|
| Productive | Median bootstrap Sharpe > 0 | - |
| Strong | P(CAGR > 0) > 70% | - |
| Width (broad) | max/min productive timescale ≥ 3x | Generic trend-following |
| Width (moderate) | ≥ 2x | Acceptable |
| Width (narrow) | < 2x | Fragile, suspect |
| Smooth | Adjacent-timescale Sharpe correlation r > 0.8 | Genuine effect |
| Real data percentile > 97.5% | Suspect overfit | Flag |
| Real data percentile > 95% | Questionable | Monitor |

### 4.7 Anti-Overfitting Checklist

1. **Harsh cost** (50 bps RT) — cao hơn thực tế
2. **Block bootstrap** — model-free, không giả định phân phối
3. **Permutation tests** — null chỉ phá vỡ đúng một feature
4. **Paired comparison** — cùng path, loại bỏ path variance
5. **Multiple comparison correction** — Bonferroni/Holm/BH
6. **Robustness width** — vùng rộng = generic, vùng hẹp = fragile
7. **Smoothness** — surface erratic = suspect
8. **Real data percentile** — > 97.5% = period luck
9. **Binary sizing** — Sharpe bất biến với scaling
10. **Min trade gate** — < 10 trades = reject
11. **Warmup exclusion** — 365 ngày chỉ cho indicators
12. **Walk-Forward OOS** — metrics chưa bao giờ thấy khi selection

---

## 5. Trình tự xây dựng lại

### Phase 0: Data Foundation

**Đầu vào**: File CSV chứa OHLCV + taker_buy_base_vol + interval (1h, 4h, 1d).

**Xây dựng**:
- DataFeed class: load CSV, filter theo interval và date range, warmup days
- Bar type: `(open_time, open, high, low, close, volume, close_time, taker_buy_base_vol, interval)`
- Date range: 2019-01-01 → present, warmup 365 ngày trước start

**Xác thực**:
- Đếm bars khớp: H1 ≈ 74K, H4 ≈ 18K, D1 ≈ 3K
- Không gap lớn (kiểm tra open_time liên tục)
- Volume > 0 cho mọi bar

---

### Phase 1: VTREND Engine (core algorithm)

**Xây dựng**:
1. Implement `_ema(series, period)` — recursive EMA
2. Implement `_atr(high, low, close, period)` — Wilder's ATR
3. Implement `_vdo(close, high, low, volume, taker_buy, fast, slow)` — VDO oscillator
4. Implement sim engine:
   - Entry: `ema_fast > ema_slow AND vdo > threshold`
   - Exit: `close < peak - trail * atr OR ema_fast < ema_slow`
   - Fill ở bar tiếp theo, cost 25 bps/side
5. Implement metrics: Sharpe, CAGR, MDD, Calmar (incremental, không allocate array)

**Xác thực Phase 1**:
- Unit test mỗi indicator vs reference implementation
- Chạy trên real data (slow=120, trail=3.0, vdo=0.0): kỳ vọng CAGR ≈ 52%, Sharpe ≈ 1.27
- Verify trade count ≈ 211, MDD ≈ 41.5%
- So sánh với pandas-based version (phải khớp chính xác)

---

### Phase 2: Component Proof (EMA, ATR, VDO)

**Xây dựng**:
1. Composite score function (Section 4.3)
2. EMA circular-shift permutation test (10K perms)
3. ATR block-shuffle permutation test (10K perms, block=40)
4. VDO random-filter permutation test (10K perms, calibrated skip rate)

**Xác thực Phase 2** (kỳ vọng):

| Component | p-value kỳ vọng | Bonferroni (K=16) |
|-----------|----------------|-------------------|
| EMA | ≈ 0.0003 | PASS |
| ATR trail | ≈ 0.0003 | PASS |
| VDO filter | ≈ 0.0003 - 0.06 | MARGINAL |

**Nếu sai lệch lớn**: Kiểm tra lại implementation (phổ biến nhất: lỗi ở circular-shift
range, hoặc skip_rate calibration).

---

### Phase 3: Block Bootstrap Infrastructure

**Xây dựng**:
1. `make_ratios(close, high, low, volume, taker_buy)` — pre-compute return ratios
2. `gen_path(ratios, n_bars, blksz, p0, rng)` — generate synthetic path
3. `sim_fast(arrays, params)` — fast incremental sim (no array allocation)
4. Parallel sweep: loop 2000 paths × N timescales × M variants

**Xác thực Phase 3**:
- Một path: verify high >= close, low <= close, volume > 0 cho mọi bar
- 100 paths: histogram of terminal NAV nên có fat tails (không Normal)
- Metrics từ 2000 paths: Sharpe 95% CI nên chứa real data value
- Seed reproducibility: cùng seed → cùng output chính xác

---

### Phase 4: Timescale Robustness

**Xây dựng**:
- 16 timescales × 2 VDO variants × 2000 paths = 64,000 sims
- Grid: slow ∈ [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
- VDO_ON: threshold = 0.0, VDO_OFF: threshold = -1e9
- Sizing: binary f=1.0

**Xác thực Phase 4** (kỳ vọng):

| Metric | Giá trị kỳ vọng |
|--------|----------------|
| Productive width | 24x (30-720) |
| Strong region | slow 60-144 (10-24 ngày) |
| Peak median Sharpe | ~0.442 ở slow ≈ 96 |
| Sharpe plateau spread | < 0.02 trong strong region |
| VDO helps | 16/16 timescales |
| Smoothness r | > 0.85 |
| Real data percentile | 94-99% (period luck, KHÔNG phải overfit) |

**Kết luận Phase 4**: Alpha là GENERIC trend-following. Không phải overfit vào slow=120.

---

### Phase 5: Multiple Comparison Correction

**Xây dựng**:
- Thu thập tất cả p-values từ Phase 2 + mọi hypothesis khác đã test
- K = tổng số hypotheses
- Apply Bonferroni, Holm, BH

**Xác thực Phase 5**: Chỉ EMA và ATR survive Bonferroni. VDO survive Holm+BH.

---

### Phase 6: Position Sizing

**Xây dựng**:
1. Kelly fraction estimation (grid search f ∈ [0.01, 2.0], maximize E[log(1+fr)])
2. Fixed fraction sweep: f ∈ [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00]
3. Vol-targeting: target_vol ∈ [10%, 15%, 20%, 25%, 30%, 40%, 50%]
   - Rolling vol: 60-bar std of log returns, annualized by √(bars/year)
   - Dynamic fraction: f = min(1, target / realized_vol)
4. Bootstrap 2000 paths, paired comparison vs f=0.30 baseline

**Xác thực Phase 6** (kỳ vọng):
- Sharpe gần bất biến với fraction (toán học)
- Vol=15% đạt Sharpe ~1.53, Calmar ~1.61
- Full Kelly (f=2.0) catastrophic: median MDD > 90%
- Không fraction nào significantly beat f=0.30 trên Sharpe (P < 97.5%)

---

### Phase 7: Resolution Sweep (H1, H4, D1)

**Xây dựng**:
- Cùng day grid [5, 8, 10, ..., 120] ngày quy đổi theo bars_per_day
- Parameters scaled theo resolution (Section 6.2)
- H4 có thể load từ cache Phase 4

**Xác thực Phase 7** (kỳ vọng):
- H1: toàn bộ negative (cost drag)
- H4: peak Sharpe ~0.442, productive 10-120d
- D1: peak Sharpe ~0.419, productive 5-120d
- VDO behavior: essential (H1), marginal (H4), useless (D1)

---

### Phase 8: Comparative Studies (optional, để confirm nulls)

Những thứ đã bác bỏ — chạy lại nếu muốn confirm:

1. **VPULL pullback entry**: Permutation 10K, kỳ vọng p ≈ 1.0
2. **Regime gates**: Bootstrap 2K, kỳ vọng P(better) ≈ 50%
3. **Regime sizing**: Bootstrap 2K, kỳ vọng P(better) < 97.5%
4. **V8 vs VTREND**: Bootstrap 2K, kỳ vọng no significant difference

---

### Phase 9: Integration (engine, risk, execution)

Sau khi thuật toán đã proven:

1. **Backtest engine**: Full engine với fills, trades, equity curve
2. **Risk guards**: max_exposure, min_notional, kill_switch_dd, max_daily_orders
3. **Paper runner**: Real-time execution loop
4. **Live runner**: Exchange integration

Mỗi bước tích hợp cần:
- Unit tests cho component mới
- Integration tests với engine
- Regression test: metrics phải khớp Phase 1 reference

---

## 6. Phụ lục: Công thức & Hằng số

### 6.1 Hằng số toàn cục

```python
COST_PER_SIDE = 0.0025          # 25 bps
INITIAL_CASH  = 10_000.0
WARMUP_DAYS   = 365
N_BOOT        = 2000
SEED          = 42
N_PERM        = 10_000
MIN_TRADES    = 10              # cho composite score
```

### 6.2 Hằng số theo resolution

```python
RESOLUTIONS = {
    "H1": {
        "bars_per_day": 24,
        "ann": sqrt(24 * 365.25),     # 93.6
        "atr_period": 56,             # 56h = 2.3 ngày
        "vdo_fast": 48,               # 48h = 2 ngày
        "vdo_slow": 112,              # 112h = 4.7 ngày
        "block_size": 240,            # 240h = 10 ngày
        "min_fast_period": 5,
    },
    "H4": {
        "bars_per_day": 6,
        "ann": sqrt(6 * 365.25),      # 46.8
        "atr_period": 14,
        "vdo_fast": 12,
        "vdo_slow": 28,
        "block_size": 60,             # 60 × 4h = 10 ngày
        "min_fast_period": 5,
    },
    "D1": {
        "bars_per_day": 1,
        "ann": sqrt(365.25),          # 19.1
        "atr_period": 14,
        "vdo_fast": 12,
        "vdo_slow": 28,
        "block_size": 10,             # 10 ngày
        "min_fast_period": 3,
    },
}
```

### 6.3 Timescale Grids (tương đương ngày)

```python
DAY_GRID = [5, 8, 10, 12, 14, 16, 18, 20, 24, 28, 33, 40, 50, 60, 83, 120]

# Quy đổi sang bars: slow_period = day × bars_per_day
# H4 grid: [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
# H1 grid: [120, 192, 240, 288, 336, 384, 432, 480, 576, 672, 792, 960, 1200, 1440, 1992, 2880]
# D1 grid: [5, 8, 10, 12, 14, 16, 18, 20, 24, 28, 33, 40, 50, 60, 83, 120]
```

### 6.4 Reference Real Data Results (H4, slow=120, trail=3.0, vdo=0.0, harsh cost)

```
CAGR:    52.7%
MDD:     41.5%
Sharpe:  1.276
Calmar:  1.268
Trades:  211
Period:  2019-01-01 → 2026-02-20
```

Đây là số liệu tham chiếu để verify implementation mới khớp chính xác.

### 6.5 VDO Behavior Across Resolutions

| Resolution | VDO Sharpe lift | P(VDO helps) | Interpretation |
|-----------|----------------|--------------|----------------|
| H1 | +0.47 | 97-99% | ESSENTIAL — giảm cost drag |
| H4 | +0.01 | 55-63% | MARGINAL — mild filter |
| D1 | -0.02 | 44-53% | USELESS — slightly harmful |

VDO giá trị tỷ lệ nghịch với trade frequency. Trade nhiều → VDO filtering giá trị. Trade
ít → VDO filtering bỏ bớt good entries.

---

---

## 7. Parity Evaluation — 6 Strategy Comparison (Study #41, 2026-03-05) ⚠ SUPERSEDED

> **SUPERSEDED (2026-03-09):** This section's verdicts are outdated. After framework
> reform, E5_ema21D1 = PRIMARY (PROMOTE), E0_ema21D1 = HOLD (PSR < 0.95).
> Preserved below as historical record of Study #41 methodology and results.

### 7.1 Tổng quan

Parity evaluation so sánh 6 chiến lược qua đầy đủ validation framework (13 suites) và
research studies (T1-T7). Kết quả: **EMA21-D1 là variant duy nhất đạt PROMOTE**.

### 7.2 Các chiến lược đã đánh giá

| Chiến lược | Code | Mô tả | Verdict |
|------------|------|-------|---------|
| E0 | `strategies/vtrend/` | Baseline (EMA cross + ATR trail) | HOLD |
| E5 | `strategies/vtrend_e5/` | Robust ATR (capped TR tại Q90) | HOLD |
| SM | `strategies/vtrend_sm/` | State machine, vol-targeted sizing | REJECT |
| LATCH | `strategies/latch/` | Hysteretic EMA regime, vol-targeted | REJECT |
| EMA21 | `strategies/vtrend_ema21/` | E0 + EMA(126) regime trên H4 | REJECT |
| EMA21-D1 | `strategies/vtrend_ema21_d1/` | E0 + EMA(21) regime trên D1 | **PROMOTE** |

### 7.3 EMA21-D1 — Variant được chứng minh tối ưu

**Logic bổ sung so với E0:**
```
# Thêm điều kiện regime filter vào entry
NẾU ĐANG FLAT:
    NẾU ema_fast[i] > ema_slow[i]         # xu hướng tăng (H4)
    VÀ vdo[i] > vdo_threshold:            # dòng tiền xác nhận (H4)
    VÀ close_d1 > ema_21d:                # regime tăng (D1)
        → SIGNAL: mua tại close bar tiếp theo

# Exit KHÔNG thay đổi so với E0
```

**Tham số bổ sung:** `ema_regime_period = 21` (tính trên D1 timeframe, = 126 H4 bars tương đương)

**Kết quả (harsh cost, 2019-01 → 2026-02):**

| Metric | EMA21-D1 | E0 | Delta |
|--------|----------|----| ------|
| Sharpe | 1.336 | 1.277 | +4.6% |
| CAGR % | 55.32 | 52.68 | +2.64pp |
| MDD % | 41.99 | 41.53 | +0.46pp |
| Trades | 186 | 211 | -25 |

**Validation:** ALL gates pass — full_harsh_delta +7.37, holdout +5.98, WFO 6/8 (75%).
**Permutation:** p = 0.0001 (10K shuffles). **Timescale:** 16/16 positive Sharpe.
**Cost:** Beats E0 at ALL cost levels 0-100 bps.

### 7.4 E5 — Strongest E0-class performer (HOLD)

**Thay đổi so với E0:** Dùng robust ATR (capped TR tại Q90 trên 100-bar rolling window).

| Metric | E5 | E0 | Delta |
|--------|----|----|-------|
| Sharpe | 1.365 | 1.277 | +6.9% |
| CAGR % | 57.04 | 52.68 | +4.36pp |
| MDD % | 40.26 | 41.53 | -1.27pp |
| Trades | 225 | 211 | +14 |

WFO 4/8 (chỉ thiếu 1 window so với threshold 0.600). Bootstrap MDD 16/16 vs E0.

### 7.5 SM/LATCH — Alternative profiles (không phải thay thế E0)

SM và LATCH có profile risk/return khác hoàn toàn E0:
- CAGR thấp hơn 3-4× (14.8-16.0% vs 52.7%)
- MDD thấp hơn 3-4× (11.2-14.9% vs 41.5%)
- Turnover thấp hơn 7-9× (5.6-7.2×/yr vs 52.3×/yr)
- Dominate tại cost >50 bps RT
- P(CAGR>0) = 97.8% vs 88.2% cho E0

Rejected bởi validation framework do CAGR-weighted scoring, nhưng là chiến lược valid cho
người muốn risk/return profile khác.

### 7.6 Kết quả đầy đủ

- Validation: `results/parity_20260305/PARITY_REPORT.md`
- Research JSON: `research/results/parity_eval/parity_eval_results.json`
- Research log: `research/results/parity_eval/parity_eval_stdout.log`

---

> **Ghi chú cuối**: Tài liệu này đủ để xây dựng lại toàn bộ hệ thống từ Phase 0 đến Phase 9.
> Mỗi Phase có verification criteria rõ ràng — nếu output không khớp kỳ vọng, kiểm tra
> lại implementation trước khi tiến sang Phase tiếp theo. Không bao giờ skip verification.
> ~~Parity Evaluation (Section 7) xác nhận EMA21-D1 là variant tối ưu duy nhất (PROMOTE).~~
> **Update 2026-03-09**: E5_ema21D1 is the PRIMARY strategy after framework reform.
> See CHANGELOG.md for details.
