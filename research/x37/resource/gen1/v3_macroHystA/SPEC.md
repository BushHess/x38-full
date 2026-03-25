# BTC Spot Root-Cause Redesign Rebuild Spec

Tài liệu này là spec standalone để một kỹ sư có thể rebuild từ raw data, không cần chat history, code gốc, hay bất kỳ tài liệu nào khác ngoài:

- `data.zip`
- `RESEARCH_PROMPT_V4.md`
- bundle artifact gốc của nghiên cứu root-cause (`btc_root_cause_research.zip`) **nếu muốn đối chiếu regression target**

Mục tiêu của spec là tái dựng hai thứ:

1. **Toàn bộ pipeline nghiên cứu** đã dẫn tới hệ thống `Slow D1 macro trend + H4 trend-quality hysteresis`.
2. **Hệ thống cuối cùng đã đóng băng** từ raw data đến threshold, signal path, trade list, daily equity, headline metrics, và quyết định cuối.

Nguyên tắc phân xử cuối cùng:

- Nếu code triển khai mâu thuẫn với `appendices/archived_tables/*.csv`, **archived tables thắng**.
- Nếu có chỗ nào không thể chứng minh byte-identical từ artifact còn lại, spec sẽ ghi rõ là `high_confidence` hoặc `unrecoverable_noncritical`, không che.

---

## 0. Kết luận ngắn gọn về mức độ tái dựng

### 0.1. Phần khôi phục **exact**
Các phần sau khôi phục được ở mức thực dụng 1:1 từ artifact còn lại:

- loader dữ liệu, kiểu dữ liệu, timestamp semantics;
- cross-timeframe alignment của final system;
- công thức feature `d1_ret_60`, `d1_trendq_60`, `h4_trendq_84`;
- annual threshold calibration của final system;
- state machine của final system;
- `final_yearly_thresholds.csv`;
- `final_signal_path.csv`;
- `final_trades.csv`;
- `final_daily_equity.csv`;
- metric semantics cho Sharpe / CAGR / MDD / exposure / trade-event counting;
- `macro_channel_compare.csv`;
- `macro_only` baseline;
- `+micro_hysteresis` baseline-final;
- `+anti_chase_cap` extension ở mức **decision-equivalent exact**;
- `cost_sensitivity.csv`;
- `plateau_perturbations.csv`;
- `epoch_breakdown.csv`;
- `walkforward_year_table.csv`;
- `holdout_year_table.csv`.

### 0.2. Phần khôi phục **high confidence**
Các phần sau khôi phục được ở mức rất sát nhưng không có đủ artifact để chứng minh byte-identical source code gốc:

- bootstrap helper defaults: gần như chắc dùng moving-block bootstrap với `n_boot = 1000`, `seed = 123`, blocks `5/10/20`;
- paired bootstrap dùng cùng block-index sample cho hai hệ;
- encoding chính xác ban đầu của `h4_ma_gap_84` trong anti-chase cap. Spec khóa dạng:
  `close / rolling_mean(close, 84) - 1`.  
  Dạng này tái tạo **đúng cùng entry-block decisions** trên dữ liệu hiện có.

### 0.3. Phần **không thể khôi phục đầy đủ**, nhưng không chặn rebuild đúng kết luận cuối
Các phần sau không còn đủ artifact để chứng minh exact original code path:

- exact exploratory branch của `+flow_entry (optional)`;
- exact comparator branch của `fast_old_like`;
- exact HTML/CSS/plot styling của `report.html`.

Điểm quan trọng: các nhánh trên **không phải hệ thống đã freeze**. Chúng chỉ là supporting experiments. Chúng được giữ lại trong archived tables để đối chiếu output, nhưng không cần để rebuild final frozen system.

---

## 1. Package contents mà kỹ sư phải có

### 1.1. Input bắt buộc
- `data.zip`
- `RESEARCH_PROMPT_V4.md`

### 1.2. Artifact đối chiếu
- `btc_root_cause_research.zip`
- hoặc thư mục unpack tương đương với các file:
  - `macro_channel_compare.csv`
  - `ablation_summary.csv`
  - `cost_sensitivity.csv`
  - `bootstrap_wf_summary.csv`
  - `bootstrap_holdout_summary.csv`
  - `paired_vs_fast_wf.csv`
  - `paired_vs_fast_holdout.csv`
  - `paired_vs_macro_wf.csv`
  - `paired_vs_macro_holdout.csv`
  - `plateau_perturbations.csv`
  - `epoch_breakdown.csv`
  - `walkforward_year_table.csv`
  - `holdout_year_table.csv`
  - `final_daily_equity.csv`
  - `final_signal_path.csv`
  - `final_trades.csv`
  - `final_yearly_thresholds.csv`
  - `final_frozen_system.json`
  - `optional_cap_extension_compare.csv`
  - `entry_cohort_overextension.csv`
  - `overextension_trade_cohort_on_no_cap.csv`
  - `report.html`

### 1.3. Generated appendix trong package spec này
Trong `appendices/generated/`:

- `data_fingerprints.csv`
- `rebuilt_final_yearly_thresholds.csv`
- `rebuilt_final_signal_path.csv`
- `rebuilt_final_trades.csv`
- `rebuilt_final_daily_equity.csv`
- `rebuilt_headline_metrics.csv`
- `rebuild_verification.csv`
- `verification_summary.json`
- `recoverability_map.csv`

---

## 2. Fingerprints và environment khóa chặt

### 2.1. File hashes
- `data.zip`: `dc6524c7935efc7f1164ba1660ef69ae953c2a3a0d87216b146a0682cf158721`
- `RESEARCH_PROMPT_V4.md`: `61312d889494646fb5186399ce905fa9e2f9134f6ac41aedff5b7f50c4b5f9d3`
- `btc_root_cause_research.zip`: `90577e05746f9fb3cffc3e2c04fa365a34bc4316eb1a2e07bccd0d6cd88fb0b3`
- `final_frozen_system.json`: `c2dc35cd57d062de9e21864944673812b2116b25f65659dac8de593b98a76c59`
- `report.html`: `936892acf4e0dcabce512fbd696576cd14f19e028650f1382ed902ef2fc6accc`

### 2.2. Reconstruction environment khuyến nghị
Để giảm mọi lệch do thư viện:

- Python `3.13.5`
- pandas `2.2.3`
- numpy `2.3.5`
- matplotlib `3.10.8` (chỉ để vẽ chart; không ảnh hưởng final numbers)

### 2.3. Numeric contract
- toàn bộ numeric phải là `float64`;
- `num_trades` có thể là `int64`;
- timestamp phải là timezone-aware UTC;
- quantile phải dùng pandas `Series.quantile(q)` default behavior trên `float64`, tức linear interpolation kiểu pandas;
- rolling std phải dùng `ddof=1`.

Nếu triển khai ngoài Python/pandas, output phải match acceptance tests ở Mục 24.

---

## 3. Raw data contract

Trong `data.zip` có 2 file:

- `data/btcusdt_1d.csv`
- `data/btcusdt_4h.csv`

Cấu trúc cột:

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

### 3.1. Invariants bắt buộc
- sort tăng dần theo `open_time`;
- không resample lại raw OHLCV;
- không forward-fill bất kỳ OHLCV field nào;
- không dùng dữ liệu sau `2026-02-20 23:59:59.999+00:00` cho final evaluation;
- phải giữ **row index toàn cục** của raw H4 file, gọi là `raw_idx`, vì `final_trades.csv` dùng index này.

### 3.2. Timestamp parsing exact
```python
df["open_dt"]  = pd.to_datetime(df["open_time"], unit="ms", utc=True)
df["close_dt"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
df["raw_idx"]  = np.arange(len(df))
```

### 3.3. H4/D1 path windows dùng trong final system
- Final signal path bắt đầu ở **H4 close**: `2019-01-01 03:59:59.999+00:00`
- Final signal path kết thúc ở **H4 close**: `2026-02-20 23:59:59.999+00:00`

Đây là lý do `final_signal_path.csv` có 15,643 rows thay vì toàn bộ 18,752 rows của raw H4 data.

---

## 4. Protocol đã khóa và trạng thái nghiên cứu thực tế

### 4.1. Protocol gốc trong `RESEARCH_PROMPT_V4.md`
Spec này giữ nguyên các fixed assumptions cốt lõi của prompt:

- BTC/USDT spot
- long-only
- signal tại close
- fill tại next open
- cost cơ sở 10 bps/side = 20 bps round-trip
- warmup không trade
- split thời gian leakage-safe
- cần walk-forward, holdout, plateau, bootstrap, ablation, cost sensitivity, regime decomposition

### 4.2. Trạng thái nghiên cứu thực tế của hệ này
Hệ `Slow D1 macro trend + H4 trend-quality hysteresis` là kết quả của **post-holdout redesign**.

Nghĩa là:
- dữ liệu holdout `2024-01-01` đến `2026-02-20` đã bị nhìn thấy từ các vòng trước;
- không được mô tả hệ này như một untouched-holdout discovery proof;
- frozen-system vẫn hợp lệ như một **practical best-so-far algorithm**, nhưng không được đóng gói như proof khoa học untouched.

Điểm này phải được giữ nguyên trong mọi rebuild và mọi tài liệu đi kèm.

---

## 5. Time splits exact

### 5.1. Time buckets
- warmup only: `2017-08-17` đến `2018-12-31`
- threshold-build / pre-live calibration context: `2019-01-01` đến `2019-12-31`
- walk-forward test years: `2020`, `2021`, `2022`, `2023`
- final holdout window: `2024-01-01` đến `2026-02-20`
- descriptive full-context:
  - `2019-01-01` đến `2026-02-20`
  - `2020-01-01` đến `2026-02-20`

### 5.2. Epoch decomposition exact
Epoch labels dùng trong `epoch_breakdown.csv`:

- `2019_mixed`: `2019-01-01` → `2019-12-31`
- `2020_2021_bull`: `2020-01-01` → `2021-12-31`
- `2022_bear`: `2022-01-01` → `2022-12-31`
- `2023_2024_recovery`: `2023-01-01` → `2024-12-31`
- `2025_2026_chop`: `2025-01-01` → `2026-02-20`

---

## 6. Global execution semantics

### 6.1. Market model
- spot only
- full-notional long/flat
- không leverage
- không short
- không funding
- không slippage ngoài transaction cost cố định

### 6.2. Signal / execution
- signal được tính tại **close của bar hiện tại**
- vị thế mới có hiệu lực tại **open của bar kế tiếp**

### 6.3. Cost
Base system:
- `cost_per_side = 0.001`
- tương đương `20 bps round-trip`

Cost stress test trong `cost_sensitivity.csv`:
- `rt_bps ∈ {0, 10, 20, 30, 50}`
- `cost_per_side = rt_bps / 20000`

Ví dụ:
- `20 rt_bps => 0.001 per side`
- `50 rt_bps => 0.0025 per side`

---

## 7. Cross-timeframe alignment exact

Đây là điểm dễ sai nhất của toàn bộ rebuild.

### 7.1. Final system alignment
Khi merge D1 feature vào H4 path của final system, phải dùng:

```python
pd.merge_asof(
    h4.sort_values("close_dt"),
    d1_features.sort_values("close_dt"),
    on="close_dt",
    direction="backward",
    allow_exact_matches=True,
)
```

### 7.2. Ý nghĩa exact
- D1 bar chỉ được nhìn thấy sau khi nó đã đóng.
- Nếu có một H4 bar đóng **đúng cùng timestamp** với D1 close (`23:59:59.999+00:00`), thì D1 bar đó **được phép nhìn thấy** trên H4 row đó.
- Đây là interpretation đúng của câu “A D1 bar is not available until its close time has passed.”
- Nếu dùng `allow_exact_matches=False`, signal path sẽ lệch archived file.

### 7.3. Kết quả kiểm chứng
`allow_exact_matches=True` là cấu hình duy nhất khớp archived `final_signal_path.csv` 1:1 ở:
- `macro_on`
- `pos`
- `trade`
- trade dates
- yearly thresholds usage

---

## 8. Core feature formulas exact

### 8.1. D1 raw-return trend carrier
Trên D1 bars:

```python
d1_ret_60[t] = close[t] / close[t-60] - 1
```

### 8.2. D1 trend-quality variant dùng trong macro diagnosis
Trên D1 bars:

```python
logret_1d[t] = log(close[t] / close[t-1])
vol_60[t]    = rolling_std(logret_1d, 60, ddof=1).shift(1)
d1_trendq_60[t] = (close[t] / close[t-60] - 1) / (vol_60[t] * sqrt(60))
```

### 8.3. H4 trend-quality controller
Trên H4 bars:

```python
logret_4h[t] = log(close[t] / close[t-1])
vol_84[t]    = rolling_std(logret_4h, 84, ddof=1).shift(1)
h4_trendq_84[t] = (close[t] / close[t-84] - 1) / (vol_84[t] * sqrt(84))
```

### 8.4. Anti-chase cap feature (high-confidence exact-decision)
Trên H4 bars:

```python
h4_ma_gap_84[t] = close[t] / rolling_mean(close, 84)[t] - 1
```

Ghi chú:
- artifact không đủ để chứng minh original encoding chính xác tuyệt đối;
- nhưng biểu thức trên tạo ra **đúng cùng decision path** của cap extension trên dữ liệu hiện có.

### 8.5. NaN handling
- rolling windows thiếu dữ liệu đầu kỳ => `NaN`
- threshold calibration luôn `dropna()`
- boolean signal với giá trị `NaN` phải đánh giá là `False`

---

## 9. Threshold calibration exact

## 9.1. Final system: macro threshold
Mỗi năm `y ∈ {2020, 2021, ..., 2026}`:

- calibration window trên D1 `close_dt`:
  `[{
      max(2019-01-01 00:00:00+00:00, y-01-01 - 1095 days)
   }, {
      y-01-01 00:00:00+00:00
   })`

- threshold:
```python
macro_thr_y = quantile(d1_ret_60 over calibration window, 0.50)
```

### 9.2. Final system: micro entry / hold thresholds
Mỗi năm `y`:

- calibration window trên H4 `close_dt`:
  `[2019-01-01 00:00:00+00:00, y-01-01 00:00:00+00:00)`

- thresholds:
```python
entry_thr_y = quantile(h4_trendq_84 over H4 calibration window, 0.60)
hold_thr_y  = quantile(h4_trendq_84 over H4 calibration window, 0.50)
```

### 9.3. 2019 behavior
- 2019 không có prior-year threshold theo protocol này;
- archived path để `macro_thr`, `entry_thr`, `exit_thr` là `NaN` trong 2019;
- `pos = 0` toàn bộ 2019.

---

## 10. Final frozen system specification exact

### 10.1. Tên hệ thống
`Slow D1 macro trend + H4 trend-quality hysteresis`

### 10.2. State variables
Trên mỗi H4 row `t` sau khi merge D1 feature:

```python
macro_on[t]       = d1_ret_60[t]     > macro_thr[year(t)]
micro_entry_on[t] = h4_trendq_84[t]  > entry_thr[year(t)]
micro_hold_on[t]  = h4_trendq_84[t]  > hold_thr[year(t)]
```

### 10.3. State machine exact
`pos[t]` là position held from `open[t]` to `open[t+1]`.

Khởi tạo:
```python
pos[0] = 0
```

Transition:
```python
for t in range(0, n-1):
    if pos[t] == 0:
        pos[t+1] = int(
            close_dt[t] >= Timestamp("2020-01-01", tz="UTC")
            and macro_on[t]
            and micro_entry_on[t]
        )
    else:
        pos[t+1] = int(
            macro_on[t]
            and micro_hold_on[t]
        )
```

Giải thích:
- entry được quyết định trên row `t`, và position long bắt đầu từ row `t+1`;
- exit cũng được quyết định trên row `t`, và position flat bắt đầu từ row `t+1`;
- hysteresis nằm ở việc `entry_thr > hold_thr`.

### 10.4. Per-row path returns exact
```python
oo_ret[t] = open[t+1] / open[t] - 1
oo_ret[last] = NaN
```

Trade-event flag:
```python
trade[t] = abs(pos[t] - pos[t-1])
trade[0] = 0
```

Per-row strategy return:
```python
ret[t] = pos[t] * oo_ret[t] - cost_per_side * trade[t]
```

Xử lý row cuối:
```python
ret[last] = pos[last] * 0.0 - cost_per_side * trade[last]
```

### 10.5. Ý nghĩa accounting exact
- row entry: `pos=1`, `trade=1`, `ret = held-bar-return - entry_cost`
- row exit: `pos=0`, `trade=1`, `ret = -exit_cost`
- row flat thường: `pos=0`, `trade=0`, `ret=0`

Đây là semantics chính xác của archived path.

---

## 11. Frozen yearly thresholds exact

Bảng dưới phải match `final_yearly_thresholds.csv` và `final_frozen_system.json`.

|   year |   d1_ret_60_q50_trailing1095d |   h4_trendq_84_entry_q60_expanding |   h4_trendq_84_hold_q50_expanding |
|-------:|------------------------------:|-----------------------------------:|----------------------------------:|
|   2020 |                     0.0173312 |                           0.44318  |                          0.184693 |
|   2021 |                     0.117939  |                           0.594489 |                          0.373153 |
|   2022 |                     0.166432  |                           0.530317 |                          0.273489 |
|   2023 |                     0.028801  |                           0.395668 |                          0.121045 |
|   2024 |                     0.0383361 |                           0.415426 |                          0.150153 |
|   2025 |                     0.0137233 |                           0.430228 |                          0.15891  |
|   2026 |                     0.0793314 |                           0.389857 |                          0.126499 |

---

## 12. Trade list semantics exact

`final_trades.csv` không phải là event log từng bar. Nó là round-trip list.

### 12.1. Entry / exit row indices
- `entry_idx` = `raw_idx` của **H4 row đầu tiên có `pos=1`**
- `exit_idx`  = `raw_idx` của **H4 row đầu tiên có `pos=0` sau khi đang long**
- vì dùng `raw_idx` toàn cục của raw H4 file, index không reset từ 2019

Ví dụ trade đầu tiên:
- `entry_idx = 5269`
- `exit_idx = 5330`
- chênh lệch đúng `61` bars

### 12.2. Entry signal metadata
Tất cả trường `entry_signal_*` và feature/threshold entry trong trade row phải lấy từ **signal row ngay trước entry row**:

```python
entry_signal_idx     = entry_idx - 1
entry_signal_year    = year(entry_signal_idx)
entry_d1_ret_60      = d1_ret_60[entry_signal_idx]
entry_h4_trendq_84   = h4_trendq_84[entry_signal_idx]
macro_thr            = macro_thr[entry_signal_idx]
entry_thr            = entry_thr[entry_signal_idx]
hold_thr             = hold_thr[entry_signal_idx]
```

### 12.3. Bars
```python
bars = exit_idx - entry_idx
```

### 12.4. Net trade return
Phải tính bằng product của **path returns** từ entry row đến exit row inclusive:

```python
net_ret = prod(1 + ret[row] for row in entry_row ... exit_row) - 1
```

Lưu ý:
- exit row phải được include vì nó mang `-exit_cost`.

---

## 13. Daily equity and metric semantics exact

### 13.1. Daily equity file
`final_daily_equity.csv` được tạo bằng cách collapse H4 path theo UTC date:

```python
equity_step = cumprod(1 + ret)
daily_equity[date] = last(equity_step within that UTC date)
daily_ret[date]    = prod(1 + ret of all H4 rows that UTC date) - 1
daily_drawdown     = daily_equity / cummax(daily_equity) - 1
```

### 13.2. Sharpe exact
Cho một segment `[start_date, end_date]` theo UTC date inclusive:

```python
seg = daily_equity where start_date <= date <= end_date
seg_daily_ret = seg["equity"].pct_change().dropna()
sharpe = mean(seg_daily_ret) / std(seg_daily_ret, ddof=1) * sqrt(365.25)
```

Hệ quả rất quan trọng:
- first day return của segment **không** được đưa vào Sharpe;
- điều này đúng với archived `walkforward_year_table.csv` và `holdout_year_table.csv`.

### 13.3. CAGR exact
Cho segment `[S, T]`:

- `E_prev` = daily equity của ngày giao dịch gần nhất **trước** `S`; nếu không có thì `1.0`
- `E_end`  = daily equity tại `T`
- `span_days = (T - S).days`  
  (**không phải** số ngày inclusive)

```python
cagr = (E_end / E_prev) ** (365.25 / span_days) - 1
```

Ví dụ:
- `2020-01-01` → `2023-12-31` có `days` field = `1461`
- nhưng CAGR dùng `span_days = 1460`

### 13.4. MDD exact
Cho segment `[S, T]`:

```python
eq_norm = [E_prev] + list(seg_equity)
eq_norm = eq_norm / E_prev
drawdown = eq_norm / cummax(eq_norm) - 1
mdd = min(drawdown)
```

Tức là MDD của segment phải bắt đầu từ base equity của ngày trước segment.

### 13.5. Trade count exact
Headline `trades` trong year tables / holdout / full context là **trade events**, không phải round-trips:

```python
trades = sum(trade over H4 rows in segment)
```

Do đó:
- `final_trades.csv` có `86` rows
- nhưng full-context headline trades = `172`

### 13.6. Exposure exact
```python
exposure = mean(pos over H4 rows in segment)
```

### 13.7. Days field exact
`days` trong summary tables là số ngày calendar inclusive:

```python
days = (T - S).days + 1
```

---

## 14. Pipeline nghiên cứu để đi tới final system

Phần này mô tả **đúng pipeline có thể rebuild từ artifact còn lại**. Nó không giả vờ khôi phục những exploratory notebook branches mà artifact không còn.

### 14.1. Phase A — Macro channel diagnosis (exact)
Mục tiêu: xác định alpha carrier thực sự nằm ở đâu trên D1.

Xây 4 macro-only candidates exact như bảng sau:

| spec               | feature      |   q | cal_lb    |   wf_sharpe |   hold_sharpe |   wf_cagr |   hold_cagr |   wf_pos_years |   wf_min_year_cagr |   hold_trades |   hold_mdd |
|:-------------------|:-------------|----:|:----------|------------:|--------------:|----------:|------------:|---------------:|-------------------:|--------------:|-----------:|
| fast_30d_ret       | d1_ret_30    | 0.6 | expanding |     1.66692 |      0.44502  |  0.748324 |    0.109913 |              3 |        -0.0228758  |            47 |  -0.286136 |
| mid_40d_ret        | d1_ret_40    | 0.6 | expanding |     1.75736 |      0.662432 |  0.861514 |    0.177041 |              3 |        -0.0758156  |            47 |  -0.289757 |
| slow_60d_ret_3y    | d1_ret_60    | 0.5 | 1095      |     1.58837 |      0.877196 |  0.843303 |    0.29246  |              4 |         0.0376219  |            43 |  -0.289964 |
| slow_60d_trendq_3y | d1_trendq_60 | 0.5 | 1095      |     1.4872  |      1.01419  |  0.751131 |    0.351955 |              4 |         0.00210829 |            35 |  -0.244497 |

#### 14.1.1. Feature definitions
- `d1_ret_30 = close / close.shift(30) - 1`
- `d1_ret_40 = close / close.shift(40) - 1`
- `d1_ret_60 = close / close.shift(60) - 1`
- `d1_trendq_60` theo công thức ở Mục 8.2

#### 14.1.2. Threshold rules
- `cal_lb = expanding` nghĩa là calibration window `[2019-01-01, y-01-01)`
- `cal_lb = 1095` nghĩa là trailing 1095 days, clipped bởi `2019-01-01`

#### 14.1.3. Simulation rule cho macro-only compare
- align D1 feature sang H4 bằng exact rule ở Mục 7
- signal:
  ```python
  macro_on[t] = aligned_feature[t] > yearly_threshold[year(t)]
  ```
- state:
  ```python
  pos[t+1] = int(close_dt[t] >= 2020-01-01 and macro_on[t])
  ```
- cost, path return, trade-event counting, daily metrics: dùng đúng semantics ở Mục 10–13

#### 14.1.4. Decision logic
Từ `macro_channel_compare.csv`, kết luận root-cause là:
- fast 30–40 day states đẹp ở development nhưng yếu hơn ở late regime;
- slow 60-day states bền hơn;
- final family phải bám một **slow D1 regime state**, không phải fast continuation state.

Ghi chú trung thực:
- artifact đủ để chứng minh exact `macro_channel_compare.csv`;
- artifact **không** đủ để chứng minh toàn bộ discarded-search branches giữa `slow_60d_ret_3y` và `slow_60d_trendq_3y`;
- final frozen system dùng `d1_ret_60`, và đó là branch phải rebuild exact.

### 14.2. Phase B — Build macro-only baseline (exact)
Fix macro branch:

- macro feature = `d1_ret_60`
- macro threshold = yearly `q50` trên trailing `1095` days

Đây là row `macro_only` trong `ablation_summary.csv`.

### 14.3. Phase C — Add H4 hysteresis controller (exact)
Add micro controller:

- micro feature = `h4_trendq_84`
- entry threshold = yearly `q60` trên expanding H4 window từ `2019-01-01`
- hold threshold = yearly `q50` trên cùng expanding window

State machine exact như Mục 10.

Đây là row `+micro_hysteresis` trong `ablation_summary.csv`, cũng chính là **frozen base system**.

### 14.4. Phase D — Test anti-chase cap extension (high-confidence exact-decision)
Extension rule:

- feature: `h4_ma_gap_84 = close / rolling_mean(close,84) - 1`
- yearly cap threshold: `q90` trên trailing 1095-day H4 calibration window
- apply **only on new entries**, không apply trên hold state

Entry rule của extension:
```python
if flat and macro_on and micro_entry_on and h4_ma_gap_84 <= cap_thr:
    enter next H4 open
```

Hold/exit không đổi.

Kết quả exact-decision được archive trong:
- `optional_cap_extension_compare.csv`
- `entry_cohort_overextension.csv`
- `overextension_trade_cohort_on_no_cap.csv`

### 14.5. Phase E — Test buyer-imbalance flow confirmation (unrecoverable_noncritical)
Artifact cho biết có một branch `+flow_entry (optional)` và report mô tả đó là buyer-imbalance entry confirmation.

Nhưng artifact không còn đủ để xác định exact:
- feature formula cuối cùng,
- lookback,
- thresholding,
- whether gate was hard/soft,
- whether it gated entry only or both entry/hold.

Vì branch này **không được freeze**, archived row trong `ablation_summary.csv` là canonical reference; không được bịa thêm exact code path.

### 14.6. Phase F — Compare vs fast_old_like comparator (unrecoverable_noncritical)
Artifact giữ lại row `fast_old_like` và paired-bootstrap tables vs fast system.

Nhưng exact comparator code path không còn đủ để khôi phục 1:1 từ artifact.  
Do đó:
- archived tables là canonical;
- spec không bịa source code exact cho comparator.

### 14.7. Phase G — Freeze decision (exact narrative from artifact)
Decision cuối cùng là **freeze base no-cap** (`+micro_hysteresis`), không freeze `+anti_chase_cap` hay `+flow_entry`.

Lý do exact theo archived evidence:
- core gain đã xuất hiện khi thêm H4 hysteresis vào macro-only;
- anti-chase cap chỉ cải thiện realized metrics một chút;
- holdout đã bị contaminate từ trước;
- freeze bản đơn giản hơn là quyết định trung thực hơn.

---

## 15. Core archived research tables phải tái tạo / tôn trọng

### 15.1. Ablation summary
| variant                 |   wf_sharpe |   wf_cagr |    wf_mdd |   wf_trades |   hold_sharpe |   hold_cagr |   hold_mdd |   hold_trades |   yr2025_cagr |   yr2025_sharpe |   full_sharpe |   full_cagr |   full_mdd |
|:------------------------|------------:|----------:|----------:|------------:|--------------:|------------:|-----------:|--------------:|--------------:|----------------:|--------------:|------------:|-----------:|
| macro_only              |     1.58837 |  0.843303 | -0.296215 |          39 |      0.877196 |    0.29246  |  -0.289964 |            43 |    0.00925129 |        0.118583 |       1.28864 |    0.520969 |  -0.296215 |
| +micro_hysteresis       |     1.628   |  0.665331 | -0.232214 |         116 |      1.37476  |    0.403157 |  -0.152208 |            56 |    0.0723581  |        0.465835 |       1.4467  |    0.472709 |  -0.232214 |
| +anti_chase_cap (final) |     1.65249 |  0.657756 | -0.230059 |         110 |      1.4197   |    0.418757 |  -0.152208 |            56 |    0.07313    |        0.469672 |       1.47587 |    0.473827 |  -0.230059 |
| +flow_entry (optional)  |     1.68313 |  0.650841 | -0.249701 |         106 |      1.40268  |    0.412513 |  -0.142312 |            56 |    0.0812948  |        0.510202 |       1.49262 |    0.46844  |  -0.249701 |
| fast_old_like           |     1.56468 |  0.678485 | -0.369478 |          65 |      0.593999 |    0.154258 |  -0.266449 |            37 |   -0.0591124  |       -0.340029 |       1.20691 |    0.395164 |  -0.369478 |

### 15.2. Optional cap comparison
| variant                |   sharpe |     cagr |       mdd |   trades |   exposure |   days |   hold_sharpe |   hold_cagr |   hold_mdd |   hold_trades |   hold_exposure |   hold_days |
|:-----------------------|---------:|---------:|----------:|---------:|-----------:|-------:|--------------:|------------:|-----------:|--------------:|----------------:|------------:|
| chosen_final_no_cap    |  1.628   | 0.665331 | -0.232214 |      116 |   0.296634 |   1461 |       1.37476 |    0.403157 |  -0.152208 |            56 |        0.264066 |         782 |
| optional_cap_extension |  1.65249 | 0.657756 | -0.230059 |      110 |   0.283172 |   1461 |       1.4197  |    0.418757 |  -0.152208 |            56 |        0.262788 |         782 |

### 15.3. Walk-forward year table
|   year |   sharpe |      cagr |        mdd |   trades |   exposure |   days |
|-------:|---------:|----------:|-----------:|---------:|-----------:|-------:|
|   2020 | 2.19163  | 1.26416   | -0.232214  |       39 |  0.429157  |    366 |
|   2021 | 1.79846  | 1.09542   | -0.212931  |       33 |  0.315525  |    365 |
|   2022 | 0.744581 | 0.0542492 | -0.0417994 |        2 |  0.0347032 |    365 |
|   2023 | 1.50227  | 0.542908  | -0.183768  |       42 |  0.406849  |    365 |

### 15.4. Holdout year table
|   year |     sharpe |      cagr |       mdd |   trades |   exposure |   days |
|-------:|-----------:|----------:|----------:|---------:|-----------:|-------:|
|   2024 |   2.0577   | 0.925352  | -0.135182 |       34 |   0.321949 |    366 |
|   2025 |   0.465835 | 0.0723581 | -0.152208 |       22 |   0.242922 |    365 |
|   2026 | nan        | 0         |  0        |        0 |   0        |     51 |

### 15.5. Cost sensitivity
|   rt_bps |   wf_sharpe |   wf_cagr |    wf_mdd |   hold_sharpe |   hold_cagr |   hold_mdd |
|---------:|------------:|----------:|----------:|--------------:|------------:|-----------:|
|        0 |     1.71298 |  0.714343 | -0.219987 |       1.47661 |    0.440373 |  -0.14625  |
|       10 |     1.67052 |  0.689666 | -0.225798 |       1.42574 |    0.421648 |  -0.149234 |
|       20 |     1.628   |  0.665331 | -0.232214 |       1.37476 |    0.403157 |  -0.152208 |
|       30 |     1.58544 |  0.641335 | -0.238789 |       1.32372 |    0.384897 |  -0.155174 |
|       50 |     1.50026 |  0.59434  | -0.252351 |       1.22145 |    0.349062 |  -0.16119  |

### 15.6. Bootstrap summary — walk-forward
|   block |   median_sharpe |   q05_sharpe |   q95_sharpe |   p_sharpe_gt0 |   median_cagr |   median_mdd |
|--------:|----------------:|-------------:|-------------:|---------------:|--------------:|-------------:|
|       5 |         1.65015 |     0.859992 |      2.37407 |       0.999167 |      0.673081 |    -0.270611 |
|      10 |         1.63902 |     0.853203 |      2.36989 |       1        |      0.657341 |    -0.270452 |
|      20 |         1.61825 |     0.79297  |      2.41551 |       1        |      0.651965 |    -0.28342  |

### 15.7. Bootstrap summary — holdout
|   block |   median_sharpe |   q05_sharpe |   q95_sharpe |   p_sharpe_gt0 |   median_cagr |   median_mdd |
|--------:|----------------:|-------------:|-------------:|---------------:|--------------:|-------------:|
|       5 |         1.41112 |     0.310276 |      2.49307 |       0.98     |      0.385904 |    -0.187398 |
|      10 |         1.39591 |     0.229134 |      2.4286  |       0.974167 |      0.382719 |    -0.176459 |
|      20 |         1.38646 |     0.175586 |      2.38703 |       0.966667 |      0.375916 |    -0.177591 |

### 15.8. Paired bootstrap vs fast on holdout
|   block |   median_delta_sharpe |   p_delta_sharpe_gt0 |   median_delta_cagr |   p_delta_cagr_gt0 |   median_delta_mdd |   p_delta_mdd_lt0 |
|--------:|----------------------:|---------------------:|--------------------:|-------------------:|-------------------:|------------------:|
|       5 |              0.798438 |             0.984167 |            0.242595 |           0.9825   |          0.0717749 |         0.105     |
|      10 |              0.798195 |             0.990833 |            0.24335  |           0.988333 |          0.0886833 |         0.0633333 |
|      20 |              0.771296 |             0.994167 |            0.231927 |           0.9925   |          0.0959214 |         0.0375    |

### 15.9. Paired bootstrap vs macro-only on holdout
|   block |   median_delta_sharpe |   p_delta_sharpe_gt0 |   median_delta_cagr |   p_delta_cagr_gt0 |   median_delta_mdd |   p_delta_mdd_lt0 |
|--------:|----------------------:|---------------------:|--------------------:|-------------------:|-------------------:|------------------:|
|       5 |              0.470143 |             0.879167 |           0.101898  |           0.739167 |           0.101076 |         0.0575    |
|      10 |              0.478694 |             0.898333 |           0.101778  |           0.77     |           0.108058 |         0.0508333 |
|      20 |              0.449661 |             0.896667 |           0.0976273 |           0.7675   |           0.109659 |         0.0366667 |

### 15.10. Plateau perturbations
| case                 |   wf_sharpe |   hold_sharpe |   wf_cagr |   hold_cagr |    wf_mdd |   hold_mdd |   wf_trades |   hold_trades |   wf_pos_years |      wf_min |
|:---------------------|------------:|--------------:|----------:|------------:|----------:|-----------:|------------:|--------------:|---------------:|------------:|
| baseline             |    1.628    |      1.37476  |  0.665331 |   0.403157  | -0.232214 |  -0.152208 |         116 |            56 |              4 |  0.0542492  |
| macro_feature_lb_48  |    1.59368  |      0.55294  |  0.637948 |   0.138536  | -0.255144 |  -0.292525 |         114 |            80 |              4 |  0.00357651 |
| macro_feature_lb_72  |    1.06527  |      1.63961  |  0.349005 |   0.512729  | -0.343367 |  -0.180016 |         130 |            64 |              3 | -0.0718541  |
| macro_q_0.4          |    1.57881  |      1.06733  |  0.658515 |   0.32208   | -0.310683 |  -0.268979 |         132 |            74 |              3 | -0.124597   |
| macro_q_0.6          |    0.982601 |      1.31778  |  0.299883 |   0.356477  | -0.29437  |  -0.14186  |         110 |            58 |              4 |  0.0109807  |
| macro_cal_lb_876     |    1.65202  |      0.997882 |  0.680165 |   0.269055  | -0.232214 |  -0.240352 |         116 |            66 |              4 |  0.0448954  |
| macro_cal_lb_1314    |    1.65851  |      1.64235  |  0.683902 |   0.487579  | -0.232214 |  -0.107122 |         114 |            52 |              4 |  0.0542492  |
| micro_feature_lb_67  |    1.09535  |      0.417616 |  0.393283 |   0.0765277 | -0.396567 |  -0.248746 |         136 |            84 |              4 |  0.0484798  |
| micro_feature_lb_101 |    1.60164  |      0.78646  |  0.655182 |   0.189237  | -0.239473 |  -0.195311 |          96 |            54 |              4 |  0.0590579  |
| entry_q_0.48         |    1.50269  |      0.742416 |  0.616288 |   0.204097  | -0.253269 |  -0.258729 |         281 |           173 |              4 |  0.0378913  |
| entry_q_0.72         |    1.78776  |      0.697342 |  0.732851 |   0.147555  | -0.221461 |  -0.208441 |          76 |            34 |              4 |  0.0542492  |
| exit_q_0.4           |    1.49254  |      0.945389 |  0.627304 |   0.265956  | -0.297395 |  -0.212166 |          78 |            44 |              4 |  0.0542492  |
| exit_q_0.6           |    1.50622  |      0.92958  |  0.56519  |   0.239086  | -0.262532 |  -0.17865  |         224 |           112 |              4 |  0.0542492  |

### 15.11. Epoch breakdown
| system        | epoch              |     sharpe |        cagr |        mdd |   trades |   exposure |   days |
|:--------------|:-------------------|-----------:|------------:|-----------:|---------:|-----------:|-------:|
| final         | 2019_mixed         | nan        |  0          |  0         |        0 |  0         |    365 |
| final         | 2020_2021_bull     |   1.99675  |  1.17595    | -0.232214  |       72 |  0.372406  |    731 |
| final         | 2022_bear          |   0.744581 |  0.0542492  | -0.0417994 |        2 |  0.0347032 |    365 |
| final         | 2023_2024_recovery |   1.83904  |  0.722531   | -0.183768  |       76 |  0.364341  |    731 |
| final         | 2025_2026_chop     |   0.436332 |  0.0631911  | -0.152208  |       22 |  0.213141  |    416 |
| fast_old_like | 2019_mixed         | nan        |  0          |  0         |        0 |  0         |    365 |
| fast_old_like | 2020_2021_bull     |   1.7474   |  1.06224    | -0.369478  |       40 |  0.480958  |    731 |
| fast_old_like | 2022_bear          |   0.768378 |  0.0616833  | -0.0622713 |       10 |  0.0543379 |    365 |
| fast_old_like | 2023_2024_recovery |   1.57849  |  0.609976   | -0.266449  |       38 |  0.421341  |    731 |
| fast_old_like | 2025_2026_chop     |  -0.439806 | -0.0689183  | -0.187303  |       14 |  0.168269  |    416 |
| macro_only    | 2019_mixed         | nan        |  0          |  0         |        0 |  0         |    365 |
| macro_only    | 2020_2021_bull     |   1.77481  |  1.32315    | -0.296215  |       24 |  0.672976  |    731 |
| macro_only    | 2022_bear          |   0.516383 |  0.0376219  | -0.0611284 |        6 |  0.0410959 |    365 |
| macro_only    | 2023_2024_recovery |   1.75397  |  0.880725   | -0.289964  |       35 |  0.642955  |    731 |
| macro_only    | 2025_2026_chop     |   0.111077 |  0.00810978 | -0.209349  |       17 |  0.425481  |    416 |

---

## 16. Exact output file contracts

Kỹ sư rebuild phải sinh được các file sau với cùng schema:

### 16.1. `final_yearly_thresholds.csv`
Columns:
- `year`
- `d1_ret_60_q50_trailing1095d`
- `h4_trendq_84_entry_q60_expanding`
- `h4_trendq_84_hold_q50_expanding`

### 16.2. `final_signal_path.csv`
Columns:
- `close_dt`
- `date`
- `year`
- `open`
- `close`
- `oo_ret`
- `d1_ret_60`
- `h4_trendq_84`
- `macro_thr`
- `entry_thr`
- `exit_thr`
- `macro_on`
- `micro_entry_on`
- `micro_hold_on`
- `pos`
- `trade`
- `ret`

### 16.3. `final_trades.csv`
Columns:
- `entry_idx`
- `exit_idx`
- `entry_dt`
- `exit_dt`
- `net_ret`
- `bars`
- `entry_signal_idx`
- `entry_signal_year`
- `entry_d1_ret_60`
- `entry_h4_trendq_84`
- `macro_thr`
- `entry_thr`
- `hold_thr`

### 16.4. `final_daily_equity.csv`
Columns:
- `date`
- `ret`
- `equity`
- `drawdown`

---

## 17. Pseudocode — full final-system rebuild

```python
# 1) load raw D1 + H4
d1 = load_and_parse("data/btcusdt_1d.csv")
h4 = load_and_parse("data/btcusdt_4h.csv")

# 2) preserve raw row ids
d1["raw_idx"] = np.arange(len(d1))
h4["raw_idx"] = np.arange(len(h4))

# 3) compute exact features
d1["d1_ret_60"] = d1["close"] / d1["close"].shift(60) - 1

h4_logret = np.log(h4["close"] / h4["close"].shift(1))
h4_vol84  = h4_logret.rolling(84).std(ddof=1).shift(1)
h4["h4_trendq_84"] = (h4["close"] / h4["close"].shift(84) - 1) / (h4_vol84 * np.sqrt(84))

# 4) align D1 feature to H4
path = pd.merge_asof(
    h4.sort_values("close_dt"),
    d1[["close_dt", "d1_ret_60"]].sort_values("close_dt"),
    on="close_dt",
    direction="backward",
    allow_exact_matches=True,
)

# 5) restrict final path window
path = path[(path["close_dt"] >= "2019-01-01 03:59:59.999+00:00") &
            (path["close_dt"] <= "2026-02-20 23:59:59.999+00:00")].copy()

path["date"] = path["close_dt"].dt.floor("D")
path["year"] = path["close_dt"].dt.year

# 6) build yearly thresholds
thr_rows = []
for y in range(2020, 2027):
    y0 = Timestamp(f"{y}-01-01", tz="UTC")

    d1_cal_start = max(Timestamp("2019-01-01", tz="UTC"), y0 - Timedelta(days=1095))
    d1_cal = d1[(d1["close_dt"] >= d1_cal_start) & (d1["close_dt"] < y0)]["d1_ret_60"].dropna()

    h4_cal = h4[(h4["close_dt"] >= Timestamp("2019-01-01", tz="UTC")) &
                (h4["close_dt"] < y0)]["h4_trendq_84"].dropna()

    thr_rows.append({
        "year": y,
        "macro_thr": float(d1_cal.quantile(0.50)),
        "entry_thr": float(h4_cal.quantile(0.60)),
        "exit_thr":  float(h4_cal.quantile(0.50)),
    })

thr = DataFrame(thr_rows)
path = path.merge(thr, on="year", how="left")

# 7) state booleans
path["macro_on"]       = path["d1_ret_60"]    > path["macro_thr"]
path["micro_entry_on"] = path["h4_trendq_84"] > path["entry_thr"]
path["micro_hold_on"]  = path["h4_trendq_84"] > path["exit_thr"]

# 8) position state machine
pos = np.zeros(len(path), dtype=int)
live_start = Timestamp("2020-01-01", tz="UTC")

for t in range(len(path)-1):
    if pos[t] == 0:
        pos[t+1] = int(path["close_dt"].iat[t] >= live_start
                       and path["macro_on"].iat[t]
                       and path["micro_entry_on"].iat[t])
    else:
        pos[t+1] = int(path["macro_on"].iat[t]
                       and path["micro_hold_on"].iat[t])

path["pos"] = pos

# 9) per-row returns
path["oo_ret"] = path["open"].shift(-1) / path["open"] - 1
path["trade"] = np.abs(np.diff(pos, prepend=pos[0]))
path["ret"] = path["pos"] * path["oo_ret"].fillna(0.0) - 0.001 * path["trade"]
path.loc[path.index[-1], "ret"] = path["pos"].iat[-1] * 0.0 - 0.001 * path["trade"].iat[-1]

# 10) daily equity
path["equity_step"] = (1 + path["ret"]).cumprod()
daily = path.groupby("date", as_index=False).agg(
    ret=("ret", lambda s: float((1+s).prod() - 1)),
    equity=("equity_step", "last"),
)
daily["drawdown"] = daily["equity"] / daily["equity"].cummax() - 1

# 11) trade list
# entry row: 0->1 in pos
# exit row: 1->0 in pos
# entry_idx / exit_idx are RAW H4 row ids, not path-local row ids
```

---

## 18. Pseudocode — trade list exact

```python
entries = np.where((shift(pos, 1, fill=0) == 0) & (pos == 1))[0]
exits   = np.where((shift(pos, 1, fill=0) == 1) & (pos == 0))[0]

rows = []
exit_ptr = 0

for e in entries:
    while exit_ptr < len(exits) and exits[exit_ptr] <= e:
        exit_ptr += 1
    if exit_ptr >= len(exits):
        break

    x = exits[exit_ptr]

    rows.append({
        "entry_idx": path["raw_idx"].iat[e],
        "exit_idx":  path["raw_idx"].iat[x],
        "entry_dt":  path["close_dt"].iat[e],
        "exit_dt":   path["close_dt"].iat[x],
        "net_ret":   prod(1 + path["ret"].iloc[e:x+1]) - 1,
        "bars":      path["raw_idx"].iat[x] - path["raw_idx"].iat[e],
        "entry_signal_idx":  path["raw_idx"].iat[e] - 1,
        "entry_signal_year": path["year"].iat[e-1],
        "entry_d1_ret_60":   path["d1_ret_60"].iat[e-1],
        "entry_h4_trendq_84":path["h4_trendq_84"].iat[e-1],
        "macro_thr":         path["macro_thr"].iat[e-1],
        "entry_thr":         path["entry_thr"].iat[e-1],
        "hold_thr":          path["exit_thr"].iat[e-1],
    })

    exit_ptr += 1
```

---

## 19. Pseudocode — segment metrics exact

```python
def segment_metrics(path, daily, start_date, end_date):
    S = Timestamp(start_date, tz="UTC")
    T = Timestamp(end_date, tz="UTC")

    seg_path  = path[(path["date"] >= S) & (path["date"] <= T)]
    seg_daily = daily[(daily["date"] >= S) & (daily["date"] <= T)]

    prev_daily = daily[daily["date"] < S]
    E_prev = 1.0 if len(prev_daily) == 0 else float(prev_daily["equity"].iloc[-1])

    # Sharpe: ignore first segment day
    r = seg_daily["equity"].pct_change().dropna()
    sharpe = mean(r) / std(r, ddof=1) * sqrt(365.25)

    # CAGR: use prior-day equity and NON-inclusive span
    span_days = (T - S).days
    cagr = (float(seg_daily["equity"].iloc[-1]) / E_prev) ** (365.25 / span_days) - 1

    # MDD: prepend E_prev
    eq_norm = concat([Series([E_prev]), seg_daily["equity"]], ignore_index=True) / E_prev
    mdd = min(eq_norm / cummax(eq_norm) - 1)

    trades = int(seg_path["trade"].sum())   # trade events
    exposure = float(seg_path["pos"].mean())
    days = span_days + 1                    # inclusive calendar days

    return sharpe, cagr, mdd, trades, exposure, days
```

---

## 20. Cost sensitivity exact

Re-run **final frozen system only**, với cùng thresholds / rules / path semantics, nhưng thay `cost_per_side` theo table ở Mục 15.5.

Không recalibrate thresholds theo cost.

---

## 21. Plateau / perturbation check exact

Re-run one-at-a-time perturbations sau, đúng như `plateau_perturbations.csv`:

- `baseline`
- `macro_feature_lb_48`
- `macro_feature_lb_72`
- `macro_q_0.4`
- `macro_q_0.6`
- `macro_cal_lb_876`
- `macro_cal_lb_1314`
- `micro_feature_lb_67`
- `micro_feature_lb_101`
- `entry_q_0.48`
- `entry_q_0.72`
- `exit_q_0.4`
- `exit_q_0.6`

### 21.1. Exact meaning
- `macro_feature_lb_48`: replace `d1_ret_60` by `d1_ret_48`
- `macro_feature_lb_72`: replace `d1_ret_60` by `d1_ret_72`
- `macro_q_0.4 / 0.6`: giữ `d1_ret_60`, đổi macro quantile
- `macro_cal_lb_876 / 1314`: giữ feature và q, đổi trailing macro calibration length
- `micro_feature_lb_67 / 101`: replace `h4_trendq_84` by `h4_trendq_67` hoặc `h4_trendq_101`
- `entry_q_0.48 / 0.72`: giữ micro feature, đổi entry quantile
- `exit_q_0.4 / 0.6`: giữ micro feature, đổi hold quantile

Mọi perturbation phải giữ nguyên:
- signal timing
- next-open execution
- cost
- metric semantics
- yearly recalibration structure

---

## 22. Bootstrap and paired bootstrap (high-confidence)

Artifact cho biết bootstrap tables sau tồn tại và nhất quán với helper defaults đã dùng ở các vòng trước.

### 22.1. High-confidence reconstruction
Khuyến nghị rebuild như sau:

```python
def block_bootstrap_returns(ret, block=10, n_boot=1000, seed=123):
    # moving-block bootstrap trên DAILY returns
    # sample block start indices with replacement
    # stitch until đủ length, truncate đúng chiều dài original
```

### 22.2. Blocks
- `5`
- `10`
- `20`

### 22.3. Bootstrap summaries
Cho mỗi bootstrap path:
- compute Sharpe / CAGR / MDD trên cùng segment semantics như main metrics
- summarize:
  - `median_sharpe`
  - `q05_sharpe`
  - `q95_sharpe`
  - `p_sharpe_gt0`
  - `median_cagr`
  - `median_mdd`

### 22.4. Paired bootstrap
Cho compare `A vs B`:
- dùng **cùng block-start samples** cho cả hai hệ
- summarize deltas:
  - `median_delta_sharpe`
  - `p_delta_sharpe_gt0`
  - `median_delta_cagr`
  - `p_delta_cagr_gt0`
  - `median_delta_mdd`
  - `p_delta_mdd_lt0`

### 22.5. Truth source
Vì seed original không được artifact chứng minh 100%, `bootstrap_*.csv` và `paired_*.csv` archived phải được coi là canonical truth source.  
Nếu kỹ sư dùng đúng helper defaults ở trên, rất có khả năng match hoàn toàn hoặc cực sát.

---

## 23. Decision log exact

### 23.1. Root-cause findings cần preserved
Research này đi đến 4 kết luận gốc:

1. alpha carrier thực sự nằm ở **slow D1 macro trend state**, không nằm ở fast continuation state;
2. H4 không nên đóng vai trò alpha carrier chính; H4 nên là **state controller có hysteresis** bên trong slow D1 regime;
3. improvement đến từ việc **tránh micro deterioration**, không phải từ một breakout predictor thần kỳ;
4. flow / buyer-imbalance có ích một chút nhưng **không phải lõi của edge**.

### 23.2. Freeze decision
Freeze:
- `d1_ret_60` macro gate
- `h4_trendq_84` entry/hold hysteresis
- no anti-chase cap
- no flow gate

### 23.3. Final verdict exact
Theo archived report:
- hệ này là **best post-holdout redesign so far**
- verdict thực dụng: **COMPETITIVE**
- không được gọi là untouched-holdout proof

---

## 24. Acceptance tests bắt buộc

Một rebuild được xem là đạt nếu thỏa toàn bộ các điều sau.

### 24.1. Raw-data fingerprints
Match:
- `appendices/generated/data_fingerprints.csv`

### 24.2. Final thresholds
`rebuilt_final_yearly_thresholds.csv` phải match archived table với tolerance:
- `<= 1e-12`

### 24.3. Final signal path
`rebuilt_final_signal_path.csv` phải match archived table theo rules:

- `close_dt`, `date`: exact string equality
- `year`, `pos`, `trade`: exact integer equality
- `macro_on`, `micro_entry_on`, `micro_hold_on`: exact boolean equality
- `open`, `close`: exact float equality
- `oo_ret`, `d1_ret_60`, `macro_thr`, `entry_thr`, `exit_thr`, `ret`: `<= 1e-12`
- `h4_trendq_84`: `<= 1e-10`

### 24.4. Final trade list
`rebuilt_final_trades.csv` phải match archived table theo rules:

- `entry_idx`, `exit_idx`, `bars`, `entry_signal_idx`, `entry_signal_year`: exact integer equality
- `entry_dt`, `exit_dt`: exact string equality
- `net_ret`, `entry_d1_ret_60`, `macro_thr`, `entry_thr`, `hold_thr`: `<= 1e-12`
- `entry_h4_trendq_84`: `<= 1e-10`

### 24.5. Final daily equity
`rebuilt_final_daily_equity.csv` phải match archived table với tolerance:
- `date`: exact string equality
- `ret`: `<= 1e-12`
- `equity`: `<= 1e-12`
- `drawdown`: `<= 1e-12`

### 24.6. Core research tables
Các bảng sau phải match archived outputs:
- `macro_channel_compare.csv`
- `ablation_summary.csv` ít nhất exact cho rows:
  - `macro_only`
  - `+micro_hysteresis`
  - `+anti_chase_cap (final)`
- `cost_sensitivity.csv`
- `plateau_perturbations.csv`
- `epoch_breakdown.csv`
- `walkforward_year_table.csv`
- `holdout_year_table.csv`

### 24.7. Bootstrap tables
- Nếu dùng exact helper defaults khôi phục ở Mục 22, nhiều khả năng match archived tables.
- Nếu vẫn lệch do RNG/seed gốc không được prove, archived bootstrap tables là canonical reference.

---

## 25. Rebuild status already verified in package này

Kết quả rebuild trong `appendices/generated/verification_summary.json` hiện tại là:

- `all_threshold_fields_pass = true`
- `all_path_fields_pass = true`
- `all_trade_fields_pass = true`
- `all_daily_fields_pass = true`

`rebuild_verification.csv` ghi lại max-abs-diff field-by-field.

---

## 26. Những gì kỹ sư không được tự ý thay đổi

- không đổi `allow_exact_matches=True` thành `False`
- không reset H4 index rồi dùng local index cho trade list
- không dùng rolling std của simple returns; phải dùng **log returns**
- không bỏ `.shift(1)` ở volatility denominator của `trendq`
- không tính Sharpe trên H4 returns; archived tables dùng **daily**
- không đếm `final_trades.csv` rows như headline trade count
- không tính CAGR bằng inclusive day count
- không forced-close position cuối mẫu nếu archived path đang flat
- không retro-fit untouched-holdout claim cho một hệ có `research_status = post_holdout_redesign`

---

## 27. Minimal implementation checklist

Một implementation được coi là đủ nếu có đúng các module:

1. `load_raw_data()`
2. `compute_d1_ret(df, L)`
3. `compute_trendq(df, L, timeframe)`
4. `align_d1_to_h4_allow_exact_matches()`
5. `build_yearly_thresholds_final()`
6. `simulate_final_system()`
7. `build_trade_list_from_path()`
8. `build_daily_equity_from_path()`
9. `segment_metrics()`
10. `run_macro_channel_compare()`
11. `run_ablation_core()`
12. `run_cost_sensitivity()`
13. `run_plateau_perturbations()`
14. `run_epoch_breakdown()`
15. `run_bootstrap()`  *(high-confidence)*
16. `run_paired_bootstrap()` *(high-confidence)*
17. `write_output_bundle()`

---

## 28. Final frozen-system JSON contract

`final_frozen_system.json` phải encode tối thiểu các trường sau:

- name
- research_status
- evidence caveat
- market / direction / timeframes
- signal timing / fill timing / cost
- warmup / development / holdout date ranges
- exact feature formulas
- exact calibration rules
- exact trading rules
- frozen params
- optional not frozen extension
- yearly thresholds
- headline metrics

Truth source là archived `final_frozen_system.json`.

---

## 29. Kết luận thực dụng

Với dữ liệu và artifact còn lại, có thể rebuild:

- **hệ thống cuối cùng đã đóng băng** ở mức 1:1 thực dụng, đã verified bằng regression;
- **pipeline nghiên cứu cốt lõi** đủ để đi từ raw data → macro diagnosis → ablation → frozen final decision, với ranh giới exact / high-confidence / unrecoverable đã được chỉ rõ.

Điểm không được phép làm là giả vờ rằng mọi exploratory branch đều byte-identical recoverable. Chúng không phải vậy. Nhưng điều đó **không cản trở** việc tái dựng đúng final system và đúng quyết định cuối.

