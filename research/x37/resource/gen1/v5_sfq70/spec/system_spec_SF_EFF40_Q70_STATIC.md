
# System Specification — `SF_EFF40_Q70_STATIC`

## 1. Mục đích

Tài liệu này mô tả chính xác frozen system `SF_EFF40_Q70_STATIC` ở mức **implementation-level**.

Mục tiêu thực tế của spec này là:
- kỹ sư khác có thể implement lại **signal / position / trade log** khớp với bản đã freeze;
- có regression fixtures đủ mạnh để biết mình đã làm đúng;
- không cần chat history hay code gốc.

## 2. Ranh giới “bit-level” cần hiểu đúng

Bundle hiện còn lại cho thấy có **bookkeeping drift rất nhỏ** giữa vài bảng summary trong report; chính report cũng ghi rõ rằng trade-count / bookkeeping có thể lệch 1 đơn vị tùy convention phân bổ fee lên daily-return bar.

Vì vậy:
- **Bit-level bắt buộc phải khóa trên các object bất biến**: feature series, yearly thresholds, close-signal vector, next-open position vector, trade log.
- Các metric như Sharpe/CAGR ở chữ số thập phân sâu có thể lệch cực nhỏ nếu bạn phân bổ exit fee vào bar trước hay bar sau; điều đó **không** làm system khác đi.

Spec này vì thế cung cấp:
1. thuật toán exact cho signal/state machine;
2. threshold table exact cho chính file dữ liệu này;
3. regression hashes cho signal/position và trade log;
4. trade samples đầu/cuối để smoke-test.

---

## 3. Reconstructed `final_practical_system.json`

```json
{
  "system_id": "SF_EFF40_Q70_STATIC",
  "reconstruction_status": "reconstructed_from_prompt_and_report_artifacts",
  "market": "BTCUSDT_spot",
  "direction": "long_only",
  "base_timeframe": "1d",
  "signal_timing": {
    "compute_on": "D1_close",
    "execute_on": "next_D1_open",
    "timezone": "UTC"
  },
  "cost_model": {
    "per_side_bps": 10,
    "round_trip_bps": 20
  },
  "warmup_and_live_bounds": {
    "raw_context_start": "2017-08-17T00:00:00Z",
    "no_live_before": "2019-01-01T00:00:00Z",
    "validation_live_metrics_start": "2020-01-01T00:00:00Z"
  },
  "position_sizing": {
    "type": "binary_notional",
    "long_size": 1.0,
    "flat_size": 0.0,
    "leverage": 1.0,
    "pyramiding": false,
    "partial_positions": false
  },
  "feature": {
    "name": "d1_eff_40",
    "family": "Kaufman_efficiency_ratio",
    "source_series": "D1.close",
    "lookback_bars": 40,
    "formula": "abs(close_t - close_t-40) / sum_{i=t-39..t} abs(close_i - close_i-1)"
  },
  "threshold_calibration": {
    "quantile": 0.7,
    "quantile_method": "linear_type7",
    "mode": "calendar_year_static_expanding_history",
    "recompute_time": "00:00:00 UTC on January 1 each year",
    "history_visibility_rule": "use only feature values from rows with close_time < year_start",
    "within_year_threshold_constant": true,
    "thresholds_by_year": {
      "2018": 0.414047393230044,
      "2019": 0.271546675746471,
      "2020": 0.276491163806202,
      "2021": 0.290809063586932,
      "2022": 0.282524032890244,
      "2023": 0.273229571849102,
      "2024": 0.276921292380782,
      "2025": 0.271403540648469,
      "2026": 0.264156443160826
    }
  },
  "signal_logic": {
    "long_if": "d1_eff_40 >= threshold_for_open_time_year",
    "flat_if": "otherwise_or_when_feature_or_threshold_is_nan"
  },
  "regime_gate": {
    "type": "implicit",
    "description": "No separate external regime model; the efficiency threshold itself is the regime gate."
  }
}
```

---

## 4. Input contract

## 4.1 File bắt buộc
- `data_btcusdt_1d.csv`

## 4.2 Columns bắt buộc
- `open_time`
- `close_time`
- `open`
- `close`

Các cột khác có thể tồn tại nhưng frozen rule không dùng.

## 4.3 Preprocessing exact
1. Parse `open_time`, `close_time` từ epoch-milliseconds sang UTC.
2. Sort tăng dần theo `open_time`.
3. Giữ nguyên native D1 bars; không resample, không fill missing bars.
4. Cast `open`, `close` sang float64.

---

## 5. Feature definition exact

## 5.1 `d1_eff_40`
Với bar chỉ số `t` trên D1:

- `delta_40_t = abs(close_t - close_(t-40))`
- `path_40_t = sum(abs(close_i - close_(i-1)))` cho `i = t-39 .. t`
- `d1_eff_40_t = delta_40_t / path_40_t`

### Quy tắc edge-case
- Nếu chưa đủ `40` daily diffs thì `d1_eff_40_t = NaN`.
- Nếu `path_40_t == 0`, đặt `d1_eff_40_t = 0.0`.  
  Với bộ dữ liệu BTC/USDT này case đó không xảy ra, nhưng rule phải được khóa.

### Tương đương pandas / numpy
```python
change = (close - close.shift(40)).abs()
path = close.diff().abs().rolling(40).sum()
d1_eff_40 = change / path
```

---

## 6. Threshold calibration exact

## 6.1 Ý nghĩa của `STATIC`
Ở đây `STATIC` **không** có nghĩa “một ngưỡng cố định cho toàn bộ sample”.  
Nó có nghĩa:

- ngưỡng được **recompute đúng 1 lần mỗi năm dương lịch**;
- sau khi tính xong ở đầu năm, ngưỡng đó **được giữ cố định cho toàn bộ các bar có `open_time` trong năm đó**.

Nói cách khác: **calendar-year static, history-expanding**.

## 6.2 Rule exact
Cho năm dương lịch `Y`:

1. Đặt `year_start = Y-01-01 00:00:00 UTC`
2. Lấy tập:
   - `H_Y = { d1_eff_40_t | close_time_t < year_start and d1_eff_40_t is finite }`
3. Tính:
   - `threshold_Y = quantile(H_Y, q=0.70, method="linear")`
4. Gán `threshold_Y` cho **mọi** D1 bar có `open_time.year == Y`

### Quantile method exact
Dùng **Hyndman–Fan type 7 / pandas-numpy linear interpolation**.

Ví dụ tương đương:
```python
threshold_Y = hist_values.quantile(0.70, interpolation="linear")
```
hoặc với API mới:
```python
threshold_Y = np.quantile(hist_values, 0.70, method="linear")
```

## 6.3 Yearly thresholds exact cho bộ dữ liệu này

|   year |   threshold_eff40_q70 |
|-------:|----------------------:|
|   2018 |              0.414047 |
|   2019 |              0.271547 |
|   2020 |              0.276491 |
|   2021 |              0.290809 |
|   2022 |              0.282524 |
|   2023 |              0.27323  |
|   2024 |              0.276921 |
|   2025 |              0.271404 |
|   2026 |              0.264156 |

Ghi chú:
- `2018` có threshold vì raw file đã có enough 2017 history để tính `eff_40`.
- Theo protocol, mọi trade trước `2019-01-01` chỉ là context/research, không phải “live allowed”.
- Validation metrics chính trong report bắt đầu từ `2020-01-01`, nhưng frozen rule bản thân nó vẫn có thể phát signal từ 2018 nếu bạn backfill.

---

## 7. Signal, regime gate, entry/exit rules

## 7.1 Close-signal exact
Với mỗi D1 bar `t`:

- `signal_close_t = 1` nếu `d1_eff_40_t >= threshold_(year(open_time_t))`
- `signal_close_t = 0` nếu ngược lại
- Nếu `d1_eff_40_t` là `NaN` hoặc `threshold` là `NaN` thì `signal_close_t = 0`

## 7.2 Regime gate exact
Không có regime model riêng.

**Regime gate chính là same condition as signal**:
- chỉ chấp nhận directional risk khi daily trend efficiency đủ cao so với ngưỡng 70th-percentile của prior history.

## 7.3 Position state machine exact
State space chỉ có:
- `FLAT`
- `LONG`

Transition rule:
- `position_at_open_(t+1) = signal_close_t`
- tức là signal ở D1 close của bar `t` có hiệu lực từ open của bar `t+1`

### Consequences
- Entry tại open `t+1` nếu `signal_close_t = 1` và `signal_close_(t-1) = 0`
- Exit tại open `t+1` nếu `signal_close_t = 0` và `signal_close_(t-1) = 1`

### Không có:
- short
- leverage
- pyramiding
- partial scaling
- stop-loss discretionary
- take-profit discretionary
- extra entry filter
- extra exit filter

## 7.4 Position sizing exact
- Long = `1.0` notional unit
- Flat = `0.0`
- Không partial.
- Không chồng vị thế.

---

## 8. Trade construction exact

## 8.1 Gross open-to-open path
Một trade từ entry-open index `e` đến exit-open index `x` có gross factor:

`G = Π(open_(k+1) / open_k)` cho `k = e .. x-1`

## 8.2 Net costs exact
- Entry fee: `0.001`
- Exit fee: `0.001`

Net factor trade:
`N = G * (1 - 0.001) * (1 - 0.001)`

Net return trade:
`trade_return = N - 1`

Hold days:
`hold_days = (open_time_x - open_time_e).days`

## 8.3 Nếu file kết thúc khi đang LONG
- Không synthesize forced close bằng invented price.
- Last bar không có next-open thì không đánh giá tiếp.
- Với bộ dữ liệu đầu vào hiện tại, frozen system **không** cần forced close ở cuối file.

---

## 9. Daily-return evaluation path khuyến nghị

Để tính daily return series phục vụ Sharpe/CAGR trên D1 open-to-open, dùng một trong hai convention nhất quán sau:
- allocate exit fee vào interval kết thúc tại exit-open; hoặc
- allocate exit fee vào interval bắt đầu tại exit-open.

Cả hai đều cho **signal / position / trade log giống nhau**.  
Regression bắt buộc trong spec này vì vậy khóa trên signal/trade log thay vì ép mọi Sharpe decimal phải tuyệt đối trùng nhau.

Nếu muốn gần nhất với trade-level semantics trong spec này, dùng:

```python
entry_t = 1 if pos_t == 1 and pos_(t-1) == 0 else 0
exit_next_t = 1 if pos_t == 1 and pos_(t+1) == 0 else 0

factor_t = (1 - 0.001 * entry_t) * ((open_(t+1) / open_t) if pos_t == 1 else 1.0) * (1 - 0.001 * exit_next_t)
ret_t = factor_t - 1
```

---

## 10. Reference metrics từ archived report

### 10.1 Recorded period metrics tại 20 bps round-trip

| period               |   sharpe20 | cagr20   | mdd20   |   trades | exposure   | win_rate   | mean_trade   | median_trade   |   mean_hold_days |   median_hold_days | top_winner_conc   | bottom_tail   |
|:---------------------|-----------:|:---------|:--------|---------:|:-----------|:-----------|:-------------|:---------------|-----------------:|-------------------:|:------------------|:--------------|
| Discovery_2020       |       2.49 | 191.9%   | -25.9%  |       15 | 40.2%      | 60.0%      | 6.4%         | 0.7%           |             8.8  |                2   | 96.6%             | -4.2%         |
| Discovery_2021       |       0.38 | 7.6%     | -30.8%  |       14 | 21.1%      | 50.0%      | 0.7%         | 1.5%           |             5.5  |                2.5 | 79.6%             | -5.9%         |
| Discovery_2022       |       0.55 | 13.3%    | -25.3%  |       11 | 16.4%      | 81.8%      | 1.5%         | 2.6%           |             5.45 |                5   | 85.5%             | -4.7%         |
| Discovery_All        |       1.24 | 52.7%    | -33.3%  |       40 | 25.9%      | 62.5%      | 4.0%         | 1.4%           |             7.1  |                3   | 66.3%             | -10.5%        |
| Holdout_2023         |       1.65 | 54.3%    | -15.9%  |        9 | 35.6%      | 66.7%      | 5.8%         | 1.0%           |            14.44 |                7   | 98.5%             | -2.7%         |
| Holdout_2024         |       1.57 | 52.4%    | -18.4%  |        6 | 21.9%      | 83.3%      | 7.8%         | 2.1%           |            13.33 |                5.5 | 100.0%            | 4.0%          |
| Holdout_All          |       1.61 | 53.3%    | -18.4%  |       15 | 28.7%      | 73.3%      | 6.6%         | 1.5%           |            14    |                6   | 93.1%             | -3.8%         |
| Reserve_2025         |       0.08 | -0.3%    | -31.2%  |       14 | 16.2%      | 42.9%      | 0.1%         | -0.4%          |             4.21 |                1   | 96.3%             | -4.7%         |
| Reserve_2026YTD      |       2.41 | 146.4%   | -8.3%   |        3 | 33.8%      | 100.0%     | 6.3%         | 5.3%           |             8.33 |                2   | 100.0%            | 6.3%          |
| Reserve_All          |       0.74 | 15.9%    | -31.2%  |       17 | 19.1%      | 52.9%      | 1.2%         | 1.0%           |             4.94 |                1   | 87.1%             | -4.7%         |
| PreReserve_2020_2024 |       1.34 | 52.9%    | -33.3%  |       55 | 27.0%      | 65.5%      | 4.7%         | 1.5%           |             8.98 |                5   | 57.2%             | -11.1%        |
| Live_2020_end        |       1.25 | 44.9%    | -33.3%  |       72 | 25.5%      | 62.5%      | 3.9%         | 1.2%           |             8.03 |                3   | 50.8%             | -11.6%        |

### 10.2 Recorded period metrics tại 50 bps round-trip

| period               |   sharpe50 | cagr50   | mdd50   |   trades | exposure   |
|:---------------------|-----------:|:---------|:--------|---------:|:-----------|
| Discovery_2020       |       2.39 | 178.6%   | -27.0%  |       15 | 40.2%      |
| Discovery_2021       |       0.28 | 3.3%     | -32.6%  |       14 | 21.1%      |
| Discovery_2022       |       0.45 | 9.6%     | -26.6%  |       11 | 16.4%      |
| Discovery_All        |       1.14 | 46.7%    | -37.5%  |       40 | 25.9%      |
| Holdout_2023         |       1.55 | 50.2%    | -16.9%  |        9 | 35.6%      |
| Holdout_2024         |       1.51 | 49.7%    | -18.8%  |        6 | 21.9%      |
| Holdout_All          |       1.53 | 49.8%    | -18.8%  |       15 | 28.7%      |
| Reserve_2025         |      -0.15 | -4.4%    | -33.0%  |       14 | 16.2%      |
| Reserve_2026YTD      |       2.3  | 135.5%   | -8.3%   |        3 | 33.8%      |
| Reserve_All          |       0.56 | 11.1%    | -33.0%  |       17 | 19.1%      |
| PreReserve_2020_2024 |       1.25 | 47.9%    | -37.5%  |       55 | 27.0%      |
| Live_2020_end        |       1.15 | 39.9%    | -37.5%  |       72 | 25.5%      |

Các bảng trên là **reference checkpoints** của archived report, không phải ground-truth duy nhất cho bookkeeping convention ở daily-return level.  
Ground-truth implementation trong spec này là **feature → threshold → signal → position → trade log**.

---

## 11. Regression fixtures exact

## 11.1 Signal/position hash
Tạo CSV canonical với các cột:
- `open_time_iso` dưới format `%Y-%m-%dT%H:%M:%S.%fZ`
- `eff`
- `thr`
- `sig_close`
- `pos_next_open`

Serialize bằng `to_csv(index=False, float_format="%.15f")` rồi SHA-256.

**Expected SHA-256**
- `feature+threshold+signal+position`: `0e66e2669ca6575c8fd266f0c0c1b598cb4fffbdeff895e46d0f0693fb429cea`

## 11.2 Trade-log hash
Tạo trade log canonical với các cột:
- `entry_time`
- `exit_time`
- `net_return`
- `hold_days`

Serialize bằng:
- datetime format `%Y-%m-%dT%H:%M:%S.%fZ`
- `to_csv(index=False, float_format="%.15f")`
- SHA-256

**Expected SHA-256**
- `trade_log`: `80d29e5d3b5c4e2a94caaaaab21a0a728a066637ed2274c7d8b4e96670331732`

## 11.3 First 15 trades từ 2020 trở đi

| entry_time           | exit_time            |   net_return |   hold_days |
|:---------------------|:---------------------|-------------:|------------:|
| 2020-01-27 00:00 UTC | 2020-01-28 00:00 UTC |     0.031967 |           1 |
| 2020-01-29 00:00 UTC | 2020-02-17 00:00 UTC |     0.05499  |          19 |
| 2020-02-19 00:00 UTC | 2020-02-20 00:00 UTC |    -0.057976 |           1 |
| 2020-03-13 00:00 UTC | 2020-03-25 00:00 UTC |     0.402332 |          12 |
| 2020-03-26 00:00 UTC | 2020-03-27 00:00 UTC |     0.006946 |           1 |
| 2020-03-30 00:00 UTC | 2020-03-31 00:00 UTC |     0.085225 |           1 |
| 2020-04-26 00:00 UTC | 2020-04-29 00:00 UTC |     0.024417 |           3 |
| 2020-04-30 00:00 UTC | 2020-05-11 00:00 UTC |    -0.008344 |          11 |
| 2020-05-14 00:00 UTC | 2020-05-16 00:00 UTC |    -0.00129  |           2 |
| 2020-05-21 00:00 UTC | 2020-05-22 00:00 UTC |    -0.048578 |           1 |
| 2020-05-31 00:00 UTC | 2020-06-01 00:00 UTC |    -0.02767  |           1 |
| 2020-06-02 00:00 UTC | 2020-06-03 00:00 UTC |    -0.068973 |           1 |
| 2020-07-28 00:00 UTC | 2020-08-03 00:00 UTC |     0.001747 |           6 |
| 2020-08-04 00:00 UTC | 2020-08-26 00:00 UTC |     0.006784 |          22 |
| 2020-10-20 00:00 UTC | 2020-12-09 00:00 UTC |     0.556188 |          50 |

## 11.4 Last 10 trades trong file

| entry_time           | exit_time            |   net_return |   hold_days |
|:---------------------|:---------------------|-------------:|------------:|
| 2025-08-11 00:00 UTC | 2025-08-12 00:00 UTC |    -0.007088 |           1 |
| 2025-08-14 00:00 UTC | 2025-08-15 00:00 UTC |    -0.042559 |           1 |
| 2025-10-07 00:00 UTC | 2025-10-08 00:00 UTC |    -0.028623 |           1 |
| 2025-10-09 00:00 UTC | 2025-10-10 00:00 UTC |    -0.015302 |           1 |
| 2025-11-14 00:00 UTC | 2025-11-27 00:00 UTC |    -0.094179 |          13 |
| 2025-12-02 00:00 UTC | 2025-12-03 00:00 UTC |     0.055738 |           1 |
| 2025-12-06 00:00 UTC | 2025-12-09 00:00 UTC |     0.012573 |           3 |
| 2026-02-06 00:00 UTC | 2026-02-07 00:00 UTC |     0.119684 |           1 |
| 2026-02-11 00:00 UTC | 2026-03-05 00:00 UTC |     0.05346  |          22 |
| 2026-03-08 00:00 UTC | 2026-03-10 00:00 UTC |     0.01535  |           2 |

---

## 12. Pseudocode end-to-end exact

```python
# 1) ingest D1
df = read_csv("data_btcusdt_1d.csv")
df["open_time"] = to_utc_ms(df["open_time"])
df["close_time"] = to_utc_ms(df["close_time"])
df = df.sort_values("open_time").reset_index(drop=True)

open_ = df["open"].astype(float)
close = df["close"].astype(float)

# 2) feature
change = (close - close.shift(40)).abs()
path = close.diff().abs().rolling(40).sum()
eff = change / path
eff = eff.where(path != 0, 0.0)

# 3) yearly thresholds
threshold = Series(index=df.index, dtype=float)
for Y in sorted(unique(year(df["open_time"]))):
    year_start = Timestamp(f"{Y}-01-01 00:00:00", tz="UTC")
    hist = eff[(df["close_time"] < year_start) & eff.notna()]
    thr = quantile_linear(hist, 0.70) if len(hist) else np.nan
    threshold[year(df["open_time"]) == Y] = thr

# 4) close signal
sig_close = ((eff >= threshold) & eff.notna() & threshold.notna()).astype(int)

# 5) next-open position
pos = sig_close.shift(1).fillna(0).astype(int)

# 6) trades
# entry when pos turns 0 -> 1 at an open
# exit when pos turns 1 -> 0 at an open
# trade PnL = open-to-open gross path * (1-0.001)^2 - 1
```

---

## 13. Tối thiểu phải đúng những gì để xem là “implemented đúng”

1. Yearly thresholds phải khớp bảng threshold.
2. Close-signal vector và next-open position vector phải cho ra hash đúng.
3. Trade log phải cho ra hash đúng.
4. First 15 trades từ 2020 và last 10 trades phải khớp.
5. Sau đó summary metrics có thể chênh rất nhỏ ở chữ số sâu nếu bạn dùng convention fee allocation khác, nhưng nếu signal/trade hash đã khớp thì system đã đúng.

