# Spec tái dựng 1:1 entry winner `weakvdo_q0.5_activity_and_fresh_imb`

## 1) Mục tiêu và phạm vi

Tài liệu này đặc tả **duy nhất** thành phần entry winner của nghiên cứu entry:

- **Winner ID:** `weakvdo_q0.5_activity_and_fresh_imb`
- **Vai trò:** thay **điều kiện entry liên quan đến VDO**
- **Giữ nguyên hoàn toàn:**
  - exit logic hiện tại của base strategy
  - D1 regime filter
  - EMA trend core
  - robust ATR
  - sizing
  - accounting / costs
  - event ordering của base strategy

Tài liệu này đủ để một kỹ sư tái dựng lại **đúng thuật toán đã được validate trong nghiên cứu WFO OOS** mà **không cần truy cập code gốc hay chat history**.

Quan trọng:
- Đây là **spec của research winner trong protocol WFO**, không phải deployment freeze cuối cùng.
- Winner này dùng **`weak_vdo_thr` được ước lượng lại theo từng fold từ train slice**. Vì vậy, để tái dựng đúng headline metrics của nghiên cứu, **không được** freeze về một threshold toàn cục duy nhất.
- Exit chưa chốt. Nếu sau này đổi exit/hold overlay, toàn bộ entry winner này phải được **re-validate lại end-to-end**.

---

## 2) Data contract

### 2.1 Raw inputs bắt buộc

Dùng đúng hai file CSV raw trong `data.zip`:

- `data/btcusdt_4h.csv`
- `data/btcusdt_1d.csv`

Schema bắt buộc của cả hai file:

- `symbol`
- `interval`
- `open_time`
- `close_time`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `num_trades`
- `taker_buy_base_vol`
- `taker_buy_quote_vol`

### 2.2 Timestamp và timeline

- Timestamps là **Unix epoch milliseconds**.
- Múi giờ làm việc là **UTC**.
- Dùng timeline H4 **đúng như raw**.
- **Không impute gaps. Không regularize timeline. Không resample H4.**

### 2.3 Ordering

- Sort cả H4 và D1 theo `close_time` tăng dần trước khi tính chỉ báo.
- Mọi chỉ báo được tính **causal**, chỉ dùng dữ liệu hiện tại và quá khứ.

### 2.4 H4/D1 mapping rule

Mỗi H4 bar tại close time `h4_close_time_t` kế thừa regime state của **D1 bar hoàn tất gần nhất** thỏa:

- `d1_close_time < h4_close_time_t`

Cách triển khai tương đương 1:1:
- `merge_asof(..., direction="backward")` trên trường `close_time`

Không được dùng D1 bar đang chưa đóng.

---

## 3) Warmup, trade eligibility, và execution semantics

### 3.1 Warmup

- **Warmup = 365 calendar days** kể từ `open_dt` của H4 bar đầu tiên trong raw dataset.
- Trong warmup:
  - vẫn cập nhật indicator đầy đủ
  - **không được phép trade**

Với dataset nghiên cứu này:
- H4 bar đầu tiên mở tại: `2017-08-17 04:00:00+00:00`
- `eligible_from = 2018-08-17 04:00:00+00:00`
- H4 close đầu tiên đủ điều kiện giao dịch là:
  - `2018-08-17 07:59:59.999+00:00`
  - bar index `2179`

### 3.2 Signal / fill semantics

- Mọi điều kiện entry được đánh giá tại **H4 close bar `t`**.
- Nếu entry signal đúng tại close `t`, lệnh mua được **schedule** và fill tại **open bar `t+1`**.
- Không same-bar fill.
- Không pyramiding.
- Không mở lệnh mới khi đang giữ vị thế.

### 3.3 Position model

- Long-only
- Binary exposure: `0%` hoặc `100% NAV`

---

## 4) Các thành phần base giữ nguyên

Phần này **không phải thứ được tối ưu trong nghiên cứu entry winner**, nhưng bắt buộc phải giữ nguyên để tái dựng đúng kết quả.

### 4.1 Trend core H4

Trên H4 close:
- `ema_fast_t = EMA_30(close)_t`
- `ema_slow_t = EMA_120(close)_t`

Trend core bật khi:
- `ema_fast_t > ema_slow_t`

### 4.2 D1 regime filter

Trên D1:
- `d1_ema21 = EMA_21(d1_close)`

Regime filter bật khi:
- `regime_ok_t = (mapped_d1_close_t > mapped_d1_ema21_t)`

### 4.3 Exit logic

Giữ nguyên exit của base strategy. Để tái dựng headline metrics của entry study, exit phải là đúng base-exit sau đây:

1. **Trailing stop**
   - duy trì `live_peak_close = max(live_peak_close, close_t)` khi đang long
   - `trail_stop_t = live_peak_close - 3.0 * robust_atr_t`
   - nếu `close_t < trail_stop_t` thì schedule full exit tại open `t+1`

2. **Trend reversal**
   - nếu không hit trailing stop ở bar đó, và `ema_fast_t < ema_slow_t`, schedule full exit tại open `t+1`

Precedence giữa hai exit check ở close bar khi đang long:
- trailing stop trước
- trend reversal sau

### 4.4 robust ATR

Giữ nguyên đúng base spec:

1. `TR_t = max(high_t - low_t, abs(high_t - close_{t-1}), abs(low_t - close_{t-1}))`
2. Với mỗi bar `t >= 100`, cap `TR_t` tại rolling quantile `q=0.90` của **100 giá trị TR trước đó**
3. Wilder ATR period `20` trên `TR_capped`
4. Seed:
   - `rATR[119] = mean(TR_capped[100:120])`

### 4.5 Accounting / sizing

Giữ nguyên base semantics:

- `initial_cash = 10_000.0`
- `side_cost = 0.00125` (12.5 bps mỗi chiều)
- full-entry tại open:
  - `qty = cash_before / (open_price * (1 + side_cost))`
- full-exit tại open:
  - `cash_after = qty_before * open_price * (1 - side_cost)`
- không leverage
- không partial fill
- không same-bar flip

---

## 5) EMA conventions — áp dụng cho mọi series

Mọi EMA trong spec này đều dùng **cùng một convention**, không dùng pandas `adjust=True`.

Với series `x_t` và chu kỳ `p`:

- `alpha_p = 2 / (p + 1)`
- `EMA_p[x]_0 = x_0`
- `EMA_p[x]_t = alpha_p * x_t + (1 - alpha_p) * EMA_p[x]_{t-1}` với `t >= 1`

Điểm này áp dụng cho tất cả:
- `EMA30(close)`
- `EMA120(close)`
- `EMA21(d1_close)`
- `EMA12(imbalance_ratio_base)`
- `EMA28(imbalance_ratio_base)`
- `EMA28(quote_volume)`
- `EMA12(vol_surprise_quote_28)`

Không được đổi seed rule.

---

## 6) Công thức đầy đủ của entry winner từ raw data

Ký hiệu tại mỗi H4 close bar `t`:

### 6.1 Base imbalance ratio

Từ raw H4 bar:

- `buy_base_t = taker_buy_base_vol_t`
- `sell_base_t = volume_t - taker_buy_base_vol_t`

Định nghĩa:

- `imbalance_ratio_base_t = (buy_base_t - sell_base_t) / volume_t`
- tương đương:
  - `imbalance_ratio_base_t = (2 * taker_buy_base_vol_t - volume_t) / volume_t`

Nếu `volume_t == 0`, đặt:
- `imbalance_ratio_base_t = 0.0`

### 6.2 VDO core

Định nghĩa VDO đúng 1:1:

- `vdo_fast_t = EMA_12(imbalance_ratio_base)_t`
- `vdo_slow_t = EMA_28(imbalance_ratio_base)_t`
- `VDO_t = vdo_fast_t - vdo_slow_t`

Lưu ý:
- `EMA_28(imbalance_ratio_base)` cũng chính là slow level của cùng input với VDO.

### 6.3 Activity support

Từ raw H4 `quote_volume`:

- `quote_vol_ema28_t = EMA_28(quote_volume)_t`
- `vol_surprise_quote_28_t = quote_volume_t / quote_vol_ema28_t`
- `activity_smoothed_t = EMA_12(vol_surprise_quote_28)_t`

Nếu `quote_vol_ema28_t == 0`, đặt:
- `vol_surprise_quote_28_t = 0.0`

Activity support đúng khi:
- `activity_support_t = (activity_smoothed_t >= 1.0)`

**Không được** thay `>= 1.0` bằng threshold khác.

### 6.4 Freshness support

Định nghĩa:

- `freshness_level_t = EMA_28(imbalance_ratio_base)_t`

Freshness support đúng khi:
- `freshness_support_t = (freshness_level_t <= 0.0)`

**Không được** thay `<= 0.0` bằng threshold khác.

### 6.5 Core entry state trước khi áp bounded veto

Bar `t` là core-active nếu đồng thời:

1. `ema_fast_t > ema_slow_t`
2. `regime_ok_t == True`
3. đang `flat`

Lưu ý:
- Điều kiện `flat` chỉ áp cho **quyết định entry runtime**.
- Khi tính `weak_vdo_thr` trên train slice, **không dùng trạng thái position**; xem mục 7.

---

## 7) Weak-VDO boundary được học theo từng fold

### 7.1 Bản chất của boundary

Winner này **không** dùng threshold toàn cục cố định cho weak-VDO zone.

Thay vào đó, với từng WFO fold, tính:

- `weak_vdo_thr_fold = median(positive VDO values on train slice, restricted to bars where trend core and regime filter are on)`

Cụ thể hơn:

Từ tất cả H4 bars trong **train slice** của fold, lấy tập:

`S_fold = { VDO_t | close_dt_t thuộc train slice, eligible_t = True, ema_fast_t > ema_slow_t, regime_ok_t = True, VDO_t > 0 }`

Sau đó định nghĩa:

- `weak_vdo_thr_fold = quantile(S_fold, 0.5, method="linear")`

Tức là **median positive VDO** trên train slice.

### 7.2 Những gì KHÔNG được làm

Để tái dựng đúng research winner, **không được**:

- fit threshold trên OOS slice
- fit threshold trên toàn sample
- fit threshold chỉ trên các bar thực sự flat
- fit threshold trên các trade đã khớp
- fit threshold riêng cho activity/freshness subgroup
- thay median bằng percentile khác
- round threshold trước khi so sánh

### 7.3 Threshold values đã được freeze trong nghiên cứu WFO

Nếu triển khai đúng 1:1 theo spec, kỹ sư phải tái tạo lại đúng các giá trị sau (sai số chỉ được ở mức floating-point rất nhỏ):

| Fold | Train slice UTC (close-date inclusive) | OOS slice UTC (close-date inclusive) | `weak_vdo_thr_fold` |
|---|---|---|---:|
| Fold 1 | 2018-08-17 → 2021-06-30 | 2021-07-01 → 2022-12-31 | 0.00648105072393846 |
| Fold 2 | 2018-08-17 → 2022-12-31 | 2023-01-01 → 2024-06-30 | 0.00579974887202656 |
| Fold 3 | 2018-08-17 → 2024-06-30 | 2024-07-01 → 2025-06-30 | 0.00566306040566206 |
| Fold 4 | 2018-08-17 → 2025-06-30 | 2025-07-01 → 2026-02-28 | 0.00606372077122927 |

Equivalent bar-index checks trên raw H4 timeline sau warmup:

| Fold | Train index range | OOS index range |
|---|---|---|
| Fold 1 | `2179..8465` | `8466..11759` |
| Fold 2 | `2179..11759` | `11760..15041` |
| Fold 3 | `2179..15041` | `15042..17231` |
| Fold 4 | `2179..17231` | `17232..18689` |

---

## 8) Rule entry winner — logic quyết định cuối cùng

### 8.1 Intuition đúng của rule

Rule này **không thay VDO**.

Nó làm đúng việc sau:

- giữ `VDO > 0` làm core gate
- chia positive-VDO thành hai vùng:
  - **strong positive VDO**
  - **weak positive VDO**
- chỉ trong vùng **weak positive VDO**, mới áp thêm một **bounded conditional veto**

### 8.2 Strong zone vs weak zone

Tại H4 close bar `t`, dùng `weak_vdo_thr_fold` của fold hiện hành:

- **Strong positive VDO zone:** `VDO_t > weak_vdo_thr_fold`
- **Weak positive VDO zone:** `0 < VDO_t <= weak_vdo_thr_fold`
- **Negative / zero VDO zone:** `VDO_t <= 0`

### 8.3 Final entry decision

Khi đang flat, tại H4 close `t`, schedule full long entry tại open `t+1` **iff** tất cả điều kiện sau đúng:

1. `ema_fast_t > ema_slow_t`
2. `regime_ok_t == True`
3. và thêm phần VDO winner:
   - nếu `VDO_t <= 0`: **không vào**
   - nếu `VDO_t > weak_vdo_thr_fold`: **vào ngay**
   - nếu `0 < VDO_t <= weak_vdo_thr_fold`: **chỉ vào nếu đồng thời**
     - `activity_support_t == True`
     - `freshness_support_t == True`

### 8.4 Compact Boolean form

Định nghĩa:

- `trend_ok_t = (ema_fast_t > ema_slow_t)`
- `entry_core_t = flat_t AND trend_ok_t AND regime_ok_t`

Khi đó:

`enter_t = entry_core_t AND [ (VDO_t > weak_vdo_thr_fold) OR (0 < VDO_t <= weak_vdo_thr_fold AND activity_support_t AND freshness_support_t) ]`

Chú ý:
- Support signals **chỉ được dùng** trong weak positive VDO zone.
- Không có rescue cho `VDO_t <= 0`.
- Không có global hard-AND kiểu `VDO>0 AND activity AND freshness`.

---

## 9) Pseudocode chuẩn tái dựng

### 9.1 Chuẩn bị dữ liệu và chỉ báo

```python
# load raw CSV, parse UTC timestamps, sort ascending by close_time

eligible_from = first_h4_open_dt + 365 calendar days
eligible_t = (h4_close_dt_t >= eligible_from)

ema_fast = EMA(close, 30)
ema_slow = EMA(close, 120)

d1_ema21 = EMA(d1_close, 21)
regime_ok_d1 = d1_close > d1_ema21
map latest completed D1 bar backward onto each H4 close

imbalance_ratio_base = np.where(volume != 0,
                                (2 * taker_buy_base_vol - volume) / volume,
                                0.0)

VDO = EMA(imbalance_ratio_base, 12) - EMA(imbalance_ratio_base, 28)

quote_vol_ema28 = EMA(quote_volume, 28)
vol_surprise_quote_28 = np.where(quote_vol_ema28 != 0,
                                 quote_volume / quote_vol_ema28,
                                 0.0)
activity_smoothed = EMA(vol_surprise_quote_28, 12)
freshness_level = EMA(imbalance_ratio_base, 28)
```

### 9.2 WFO fold threshold estimation

```python
for each fold:
    train = bars with eligible_t == True and close_dt_t in fold.train_range

    threshold_sample = train[
        (ema_fast > ema_slow) &
        (regime_ok == True) &
        (VDO > 0)
    ]["VDO"]

    weak_vdo_thr = np.quantile(threshold_sample, 0.5, method="linear")
```

### 9.3 Runtime entry decision trong OOS fold

```python
for each OOS bar t, evaluated at H4 close:
    if not eligible_t:
        continue
    if t is the last bar of the OOS fold:
        continue  # cannot fill at t+1 inside fold
    if already in position:
        continue  # entry logic is inactive while long

    trend_ok = (ema_fast_t > ema_slow_t)
    regime_ok = mapped_regime_ok_t
    vdo = VDO_t
    activity_support = (activity_smoothed_t >= 1.0)
    freshness_support = (freshness_level_t <= 0.0)

    if not trend_ok:
        no entry
    elif not regime_ok:
        no entry
    elif vdo <= 0.0:
        no entry
    elif vdo > weak_vdo_thr:
        schedule full long entry at open t+1
    else:
        # this branch means 0 < vdo <= weak_vdo_thr
        if activity_support and freshness_support:
            schedule full long entry at open t+1
        else:
            no entry
```

### 9.4 Exit interaction

```python
while long:
    keep base exit exactly unchanged
    do not inject activity/freshness logic into exit
```

---

## 10) WFO protocol cần dùng để reproduce research result

### 10.1 Fold dates

Dùng đúng 4 expanding WFO OOS folds sau, với **flat reset tại đầu mỗi OOS fold**:

| Fold | Train slice | OOS slice |
|---|---|---|
| Fold 1 | 2018-08-17 → 2021-06-30 | 2021-07-01 → 2022-12-31 |
| Fold 2 | 2018-08-17 → 2022-12-31 | 2023-01-01 → 2024-06-30 |
| Fold 3 | 2018-08-17 → 2024-06-30 | 2024-07-01 → 2025-06-30 |
| Fold 4 | 2018-08-17 → 2025-06-30 | 2025-07-01 → 2026-02-28 |

Quy ước chính xác:
- Train/OOS được xác định theo **H4 `close_dt` UTC**.
- Ngày ở bảng là **inclusive theo calendar date UTC**.
- Tương đương với OOS windows:
  - Fold 1: `2021-07-01 00:00:00+00:00 <= close_dt < 2023-01-01 00:00:00+00:00`
  - Fold 2: `2023-01-01 00:00:00+00:00 <= close_dt < 2024-07-01 00:00:00+00:00`
  - Fold 3: `2024-07-01 00:00:00+00:00 <= close_dt < 2025-07-01 00:00:00+00:00`
  - Fold 4: `2025-07-01 00:00:00+00:00 <= close_dt < 2026-03-01 00:00:00+00:00`

### 10.2 Reset rules

Tại đầu mỗi OOS fold:
- reset portfolio về `flat`
- reset `cash = 10_000.0`
- **không reset indicators**
- **không reset EMA / ATR history**

Indicators phải tiếp tục dùng full lịch sử từ raw data start, vì đây là điều kiện causal đúng và cũng là cách nghiên cứu đã làm.

### 10.3 Aggregation của headline metrics

Headline metrics được tính trên **stitched OOS sample**:
- chạy riêng từng fold với flat reset
- nối OOS bar-return của 4 folds theo thứ tự thời gian
- tính aggregate Sharpe/CAGR/MDD trên stitched OOS sample đó

---

## 11) Acceptance checks — nếu tái dựng đúng phải ra gần như vậy

### 11.1 Aggregate OOS targets của winner

Với đúng spec này + base exit locked:

- `aggregate_sharpe = 1.3740835418443529`
- `aggregate_cagr = 0.4271561335683262`
- `aggregate_mdd = -0.2733669220869338`
- `oos_trades = 104`

Baseline `VDO > 0` cùng protocol:

- `aggregate_sharpe = 1.1307597999722059`
- `aggregate_cagr = 0.3503025443385248`
- `aggregate_mdd = -0.3709393067151723`
- `oos_trades = 118`

### 11.2 Fold-by-fold winner targets

| Fold | `weak_vdo_thr_fold` | OOS Sharpe | OOS CAGR | OOS MDD | OOS trades |
|---|---:|---:|---:|---:|---:|
| Fold 1 | 0.00648105072393846 | 1.1196934805892897 | 0.34049090794934056 | -0.2289902947255631 | 25 |
| Fold 2 | 0.00579974887202656 | 1.6040926839062521 | 0.5741559544810797 | -0.2733669220869336 | 41 |
| Fold 3 | 0.00566306040566206 | 1.8753474413200957 | 0.6725487817062583 | -0.13669452357361356 | 27 |
| Fold 4 | 0.00606372077122927 | 0.3222358854220594 | 0.039629685918125324 | -0.12775209903264362 | 11 |

### 11.3 Fold-by-fold baseline targets

| Fold | OOS Sharpe | OOS CAGR | OOS MDD | OOS trades |
|---|---:|---:|---:|---:|
| Fold 1 | 0.606679459597133 | 0.1565414550920552 | -0.3648484810818692 | 31 |
| Fold 2 | 1.5375055975163145 | 0.5856032823972903 | -0.30918733110768204 | 47 |
| Fold 3 | 1.818573333257709 | 0.6554226646434065 | -0.13236946834247343 | 28 |
| Fold 4 | -0.022157305304334646 | -0.01664756943298129 | -0.12477834959494816 | 12 |

Nếu kết quả lệch có hệ thống, gần như chắc chắn implementation đã sai ở một trong các điểm sau:
- EMA convention khác spec
- D1 mapping dùng daily bar chưa hoàn tất
- threshold sample lấy sai universe
- entry decision đánh giá ở open thay vì close
- threshold bị freeze toàn cục thay vì recompute theo fold train
- reset indicators ở đầu fold
- exit không còn là base exit locked

---

## 12) Những caveat phải giữ nguyên khi triển khai / diễn giải

### 12.1 Đây không phải universal full-history law

Phát hiện này nên được đọc là:
- **một cải thiện OOS có thật trong protocol WFO đã khóa từ 2021-07 trở đi**
- **không phải** quy luật bất biến đúng cho toàn bộ lịch sử trước đó

Kiểm tra robustness đã cho thấy:
- frozen approximation với `weak_vdo_thr = 0.00648105072393846` **không thắng** baseline trên pre-OOS era `2018-08-17 → 2021-06-30`
- baseline `VDO > 0`: Sharpe khoảng `1.951254`
- frozen approximation winner: Sharpe khoảng `1.787091`

Kết luận đúng:
- motif `weak-VDO bounded veto` có tín hiệu thật
- nhưng edge này mang màu **post-2021 structure** hơn là một luật timeless

### 12.2 Không được diễn giải sai thành “VDO mới”

Winner này **không** chứng minh rằng một oscillator volume khác đã thay VDO.

Nó chứng minh điều hẹp hơn nhưng quan trọng hơn:
- `VDO > 0` vẫn là entry core đúng
- thông tin phụ chỉ nên dùng như **bounded conditional veto** trên weak positive VDO
- không nên dùng như global AND confirm
- không nên dùng để rescue negative VDO entries
- không nên ưu tiên threshold massage quanh zero

### 12.3 Churn risk nếu sau này exit dùng cùng gốc tín hiệu

Winner này đã dùng hai companion signals tại entry:
- `EMA12(vol_surprise_quote_28)`
- `EMA28(imbalance_ratio_base)`

Nếu sau này exit/hold overlay cũng dùng chính các biến này hoặc các biến cùng họ rất gần như:
- `ema12/ema28/net_quote_norm_28`
- `ema28(imbalance_ratio_base)`
- `ema12(vol_surprise_quote_28)`

thì có rủi ro:

1. **double-counting cùng một motif flow/activity**
   - entry đã bias sample về phía “activity-supported, not-late”
   - exit dùng cùng motif rất dễ chỉ lặp lại logic đó trong trạng thái đã được chọn lọc

2. **apparent improvement do correlated selection**, không phải independent hold edge
   - trade nào được vào đã là trade “hợp” với activity/freshness
   - exit dùng cùng family có thể giữ lâu hơn đúng vì entry đã pre-filter, chứ không vì exit thật sự thêm thông tin mới

3. **churn / actuator coupling** nếu exit sau này cũng phản ứng trực tiếp với cùng flow family
   - đặc biệt nếu exit logic tương lai dùng dạng dynamic suppress / continue / veto trên chính family tín hiệu này
   - nguy cơ tạo feedback loop mềm: entry chọn flow-state này, exit lại thiên vị giữ đúng flow-state đó

Quy tắc an toàn:
- Khi nghiên cứu exit sau entry winner này, phải **lock entry winner** trước
- rồi chạy **WFO OOS mới toàn hệ thống**
- không được dùng lại headline metrics cũ của exit research làm bằng chứng trực tiếp

### 12.4 Không có single deployment threshold bị freeze ở đây

Research winner hợp lệ nhờ:
- train-slice median positive VDO
- recompute theo từng fold

Vì vậy:
- `0.0060` hoặc `0.00648105` chỉ là **approximation checks**
- chúng **không phải** định nghĩa chính thức của winner research
- nếu muốn promote sang deployment, cần một bước freeze riêng sau khi re-validate full system

---

## 13) Tóm tắt một câu cho kỹ sư

**Giữ nguyên toàn bộ base strategy; chỉ thay điều kiện `VDO > 0` ở entry bằng rule sau: nếu `VDO <= 0` thì không vào, nếu `VDO > weak_vdo_thr_fold` thì vào, còn nếu `0 < VDO <= weak_vdo_thr_fold` thì chỉ vào khi `EMA12(quote_volume / EMA28(quote_volume)) >= 1` và `EMA28((2*taker_buy_base_vol - volume)/volume) <= 0`; trong đó `weak_vdo_thr_fold` là median của các giá trị VDO dương trên train slice của từng WFO fold, tính trên mọi bar eligible mà `EMA30 > EMA120` và D1 regime đang on.**
