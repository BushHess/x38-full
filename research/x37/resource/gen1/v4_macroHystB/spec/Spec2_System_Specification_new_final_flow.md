# Spec 2 — System Specification for `new_final_flow`

Tài liệu này khóa **chính xác ở mức implementable / practical-exact** hệ thống `final_practical_system.json` có short name `new_final_flow`, đủ để một kỹ sư implement lại từ raw data và reproduce:

- yearly thresholds
- full H4 signal path
- trade list
- daily equity
- final JSON
- headline metrics

## 0. Quy tắc phân xử

Nếu implementation mâu thuẫn với một trong các file sau trong bundle này, thứ tự ưu tiên là:

1. `appendices/archived/final_practical_system.json`
2. `appendices/archived/yearly_thresholds_final.csv`
3. `appendices/archived/signal_path_new_final_flow.csv`
4. `appendices/archived/trades_new_final_flow.csv`
5. `appendices/archived/daily_new_final_flow.csv`

## 1. Identity của hệ thống

- Name: `D1 ret_60 regime-entry gate + H4 trendq_84 hysteresis + H4 buyimb_12 entry confirmation`
- Short name: `new_final_flow`
- Status: `practical_final_candidate`
- Market: `BTCUSDT spot`
- Side: `long_only`
- Timeframes: `4h, 1d`
- Execution base timeframe: `4h`
- Signal time: `bar_close`
- Fill time: `next_bar_open`
- Cost per side: `0.001`
- Round-trip cost: `0.002`

## 2. Input data contract

### 2.1. Raw files
- `data/btcusdt_1d.csv`
- `data/btcusdt_4h.csv`

### 2.2. Timestamp parsing exact
```python
df["open_dt"]  = pd.to_datetime(df["open_time"], unit="ms", utc=True)
df["close_dt"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
```

### 2.3. Raw windows
- D1 start: `2017-08-17`
- D1 end: `2026-03-10`
- H4 start: `2017-08-17 04:00:00 UTC`
- H4 end: `2026-03-11 07:59:59 UTC`

### 2.4. Preserve raw row order
Không drop row, không resample. `entry_idx`/`exit_idx` trong trade list là **row index gốc của H4 raw file** (0-based).

## 3. Feature engineering exact

### 3.1. D1 features
```python
d1_logret_1 = np.log(d1.close / d1.close.shift(1))
d1_ret_60   = d1.close / d1.close.shift(60) - 1
```

### 3.2. H4 features
```python
h4_logret_1   = np.log(h4.close / h4.close.shift(1))
h4_trendq_84  = (h4.close / h4.close.shift(84) - 1) / (h4_logret_1.rolling(84).std(ddof=1) * np.sqrt(84))
h4_buyimb_12  = 2 * (h4.taker_buy_base_vol.rolling(12).sum() / h4.volume.rolling(12).sum()) - 1
```

### 3.3. Numeric notes
- `rolling.std(ddof=1)` là bắt buộc
- mọi feature giữ nguyên `NaN` ở vùng đầu không đủ lookback
- không clip, không winsorize, không z-score thêm

## 4. Cross-timeframe alignment exact

### 4.1. Base frame
Dùng H4 làm frame chính:

```python
path = h4[["open_dt","close_dt","open","h4_trendq_84","h4_buyimb_12"]].copy()
```

### 4.2. Merge D1 vào H4
```python
path = pd.merge_asof(
    path.sort_values("close_dt"),
    d1[["close_dt", "d1_ret_60"]].sort_values("close_dt"),
    on="close_dt",
    direction="backward",
)
```

Giải thích:
- ở H4 close `t`, path nhìn thấy D1 bar gần nhất đã đóng (`d1.close_dt <= h4.close_dt`)
- không shift thêm sau merge

## 5. Yearly threshold calibration exact

### 5.1. Threshold windows
Cho từng năm `Y ∈ {2020,2021,2022,2023,2024,2025,2026}`:

- `y0 = Timestamp(f"{Y}-01-01 00:00:00+00:00")`
- `expanding_window = rows có 2019-01-01 <= close_dt < y0`
- `tr365_window = rows có y0 - 365 days <= close_dt < y0`

### 5.2. Important subtlety
Thresholds được tính trên **H4 merged frame**, không phải trực tiếp trên raw D1 frame.

Hệ quả:
- `d1_ret_60` distribution bị “repeat” theo số H4 bars mà D1 value đó sống trên H4 frame;
- đây là lý do threshold D1 trong final JSON match H4-merged distribution chứ không match raw-D1-only quantile.

### 5.3. Quantiles exact
```python
macro_threshold_y = quantile(expanding_window["d1_ret_60"], 0.50)
entry_threshold_y = quantile(expanding_window["h4_trendq_84"], 0.60)
hold_threshold_y  = quantile(expanding_window["h4_trendq_84"], 0.50)
flow_threshold_y  = quantile(tr365_window["h4_buyimb_12"], 0.55)
```

### 5.4. Yearly thresholds exact
|   year |   d1_ret_60_q50_expanding |   h4_trendq_84_entry_q60_expanding |   h4_trendq_84_hold_q50_expanding |   h4_buyimb_12_entry_confirm_q55_tr365 |
|-------:|--------------------------:|-----------------------------------:|----------------------------------:|---------------------------------------:|
|   2020 |                 0.0173312 |                           0.444561 |                          0.18495  |                             0.0349419  |
|   2021 |                 0.117017  |                           0.597676 |                          0.37281  |                            -0.0221051  |
|   2022 |                 0.165514  |                           0.532719 |                          0.273341 |                            -0.0117066  |
|   2023 |                 0.0247632 |                           0.397969 |                          0.121188 |                            -0.00430096 |
|   2024 |                 0.0782634 |                           0.416247 |                          0.150298 |                            -0.0136145  |
|   2025 |                 0.0791529 |                           0.431109 |                          0.158561 |                            -0.00484446 |
|   2026 |                 0.0613922 |                           0.391328 |                          0.126915 |                            -0.030804   |

`appendices/archived/yearly_thresholds_final.csv` là regression target canonical.  
`appendices/generated/rebuilt_yearly_thresholds_final.csv` là file rebuilt từ spec này.

## 6. Signal logic exact

### 6.1. Entry conditions
Tại H4 row `i` (signal evaluated at close of row `i`), nếu đang flat thì mở long ở row `i+1` open khi đồng thời đúng:

1. `d1_ret_60[i] > macro_threshold[year(i)]`
2. `h4_trendq_84[i] > entry_threshold[year(i)]`
3. `h4_buyimb_12[i] > flow_threshold[year(i)]`

### 6.2. Hold conditions
Nếu đang long ở row `i`, giữ long sang row `i+1` **chỉ** khi:

- `h4_trendq_84[i] > hold_threshold[year(i)]`

### 6.3. Exit rule
Nếu đang long mà condition hold không còn đúng, thoát ở row `i+1` open.

### 6.4. Deliberate non-use of D1 on exit
Sau khi đã long, **bỏ qua D1 macro** như exit clause.  
Đây là quyết định có chủ ý của thiết kế; `ablation.csv` cho thấy bật macro exit làm tệ đi.

### 6.5. NaN handling
- bất kỳ condition nào có feature `NaN` → coi là `False`
- vì không trade trước `2020-01-01`, NaN warmup không gây side effect thực chiến

## 7. State machine exact

### 7.1. Initialization
```python
pos[0] = 0
trade[0] = 0
```

### 7.2. No-trade warmup
Nếu `open_dt[i] < 2020-01-01 00:00:00+00:00`, force `desired_next = 0`.

### 7.3. Transition pseudocode exact
```python
current = 0
for i in range(n_rows - 1):
    if open_dt[i] < live_start:
        desired_next = 0
    else:
        y = open_dt[i].year
        macro_on = pd.notna(d1_ret_60[i]) and d1_ret_60[i] > macro_thr[y]
        entry_on = pd.notna(h4_trendq_84[i]) and h4_trendq_84[i] > entry_thr[y]
        hold_on  = pd.notna(h4_trendq_84[i]) and h4_trendq_84[i] > hold_thr[y]
        flow_on  = pd.notna(h4_buyimb_12[i]) and h4_buyimb_12[i] > flow_thr[y]

        if current == 0:
            desired_next = 1 if (macro_on and entry_on and flow_on) else 0
        else:
            desired_next = 1 if hold_on else 0

    pos[i + 1] = desired_next
    trade[i + 1] = 1 if desired_next != current else 0
    current = desired_next
```

### 7.4. Interpretation of `trade`
`trade` là **số side transaction tại bar open đó**, không có dấu:
- entry row: `trade = 1`
- exit row: `trade = 1`
- no change: `trade = 0`

## 8. Position sizing và return model exact

### 8.1. Position sizing
- long: `1.0` notional
- flat: `0.0`
- không leverage, không scale in/out, không fractional sizing động

### 8.2. H4 return exact
Cho H4 row `i`:

```python
gross_open_to_open_i = open[i+1] / open[i] - 1
ret_h4[i] = pos[i] * gross_open_to_open_i - trade[i] * 0.001
```

Special cases:
- nếu `pos[i] == 0` và `trade[i] == 0` → `ret_h4[i] = 0`
- entry row: ăn return open→next_open của bar đó **minus entry cost**
- exit row: vì `pos[i] == 0`, row đó chỉ mang `-exit cost`
- row cuối cùng không có `open[i+1]` → force `ret_h4[last] = 0`

### 8.3. Equity path exact
```python
equity[i] = np.cumprod(1 + ret_h4)[i]
```

## 9. Output files exact

### 9.1. H4 signal path
Cột exact:

- `open_dt_naive`
- `close_dt_naive`
- `date`
- `open`
- `pos`
- `trade`
- `ret_h4`
- `equity`

Regression target:
- `appendices/archived/signal_path_new_final_flow.csv`

### 9.2. Trade list
Trade rows được build từ:
- entry rows: `(trade == 1) & (pos == 1)`
- exit rows: `(trade == 1) & (pos == 0)`

Pair sequentially 1 entry → exit kế tiếp.

Per-trade fields exact:
```python
gross_ret = exit_px / entry_px - 1
net_ret   = (exit_px / entry_px) * (1 - 0.001) * (1 - 0.001) - 1
hold_days = (exit_dt - entry_dt) / Timedelta(days=1)
```

Regression target:
- `appendices/archived/trades_new_final_flow.csv`

### 9.3. Daily equity
Collapse theo UTC date của `open_dt`:

```python
daily_equity[date] = last(H4 equity in that UTC date)
daily_ret[date]    = daily_equity.pct_change().fillna(0)
daily_drawdown     = daily_equity / cummax(daily_equity) - 1
```

Regression target:
- `appendices/archived/daily_new_final_flow.csv`

## 10. Headline outputs exact

### 10.1. Frozen JSON fields
Core JSON preserved trong `appendices/archived/final_practical_system.json`.

### 10.2. Exact performance constants
- Dev 2020–2023:
  - Sharpe `1.833770680270839`
  - CAGR `0.733854660289620`
  - MDD `-0.227294597845199`
  - Trades `35`
- Diagnostic 2024–2026-02-20:
  - Sharpe `1.835893028286043`
  - CAGR `0.532426009375124`
  - MDD `-0.112881915026007`
  - Trades `16`
- Full 2020–2026-02-20:
  - Sharpe `1.839460799131448`
  - CAGR `0.671427797149873`
  - MDD `-0.227294597845199`
  - Trades `51`

### 10.3. Trade-distribution constants
- trades `51`
- win_rate `0.588235294117647`
- avg_net_ret `0.075132640896960`
- med_net_ret `0.003648952064789`
- avg_hold_days `11.045751633986926`
- med_hold_days `6.333333333333333`
- top5_sum `2.598480625040422`
- bottom5_sum `-0.303592286058997`
- total_net_factor `23.373880541394410`

## 11. Acceptance tests exact

Một implementation đạt spec này nếu:

1. `rebuilt_yearly_thresholds_final.csv` match `yearly_thresholds_final.csv`
2. `rebuilt_signal_path_new_final_flow.csv` match `signal_path_new_final_flow.csv`
3. `rebuilt_trades_new_final_flow.csv` match `trades_new_final_flow.csv`
4. `rebuilt_daily_new_final_flow.csv` match `daily_new_final_flow.csv`

Value-level tolerances:
- numeric fields: `max_abs_diff <= 1e-12`
- string / timestamp fields: exact equality
- `pos` và `trade`: exact equality

Giải thích trung thực:
- với CSV float64, “bit-level identical” không phải tiêu chí thực tế;
- package này tái dựng **exact-for-practical-purposes**: toàn bộ cột rời rạc/timestamp khớp tuyệt đối, còn các cột số chỉ lệch ở mức IEEE-754 floating epsilon;
- trên package hiện tại, sai khác lớn nhất của `new_final_flow` là `3.552714e-15` ở `equity`, `9.974660e-17` ở `ret_h4`, và `3.552714e-15` ở `hold_days`.

Current package verification status:
```json
{
  "signal_path_practical_exact": true,
  "daily_practical_exact": true,
  "trades_practical_exact": true
}
```

## 12. First 5 và last 5 trades for smoke testing

### 12.1. First 5 trades
|   entry_idx |   exit_idx | entry_dt            | exit_dt             |   entry_px |   exit_px |   gross_ret |     net_ret |   hold_days |
|------------:|-----------:|:--------------------|:--------------------|-----------:|----------:|------------:|------------:|------------:|
|        5342 |       5378 | 2020-01-27 04:00:00 | 2020-02-02 04:00:00 |    8670.11 |   9266.79 |  0.0688203  |  0.0666838  |      6      |
|        5400 |       5484 | 2020-02-05 20:00:00 | 2020-02-20 00:00:00 |    9655.93 |   9594.65 | -0.00634636 | -0.00833267 |     14.1667 |
|        6103 |       6106 | 2020-06-02 04:00:00 | 2020-06-02 16:00:00 |   10096.9  |   9468.08 | -0.0622757  | -0.0641502  |      0.5    |
|        6433 |       6549 | 2020-07-27 04:00:00 | 2020-08-15 12:00:00 |   10248.9  |  11843    |  0.155547   |  0.153237   |     19.3333 |
|        6949 |       7216 | 2020-10-21 04:00:00 | 2020-12-04 16:00:00 |   12182.3  |  18944.1  |  0.555048   |  0.551939   |     44.5    |

### 12.2. Last 5 trades
|   entry_idx |   exit_idx | entry_dt            | exit_dt             |   entry_px |   exit_px |   gross_ret |     net_ret |   hold_days |
|------------:|-----------:|:--------------------|:--------------------|-----------:|----------:|------------:|------------:|------------:|
|       16236 |      16265 | 2025-01-16 00:00:00 | 2025-01-20 20:00:00 |     100497 |    103692 |  0.0317848  |  0.0297223  |     4.83333 |
|       16290 |      16330 | 2025-01-25 00:00:00 | 2025-01-31 16:00:00 |     104871 |    105464 |  0.00565926 |  0.00364895 |     6.66667 |
|       16851 |      17045 | 2025-04-28 12:00:00 | 2025-05-30 20:00:00 |      95320 |    104640 |  0.0977812  |  0.0955867  |    32.3333  |
|       17246 |      17377 | 2025-07-03 08:00:00 | 2025-07-25 04:00:00 |     109280 |    115420 |  0.0561828  |  0.0540715  |    21.8333  |
|       17493 |      17500 | 2025-08-13 12:00:00 | 2025-08-14 16:00:00 |     120570 |    118257 | -0.0191851  | -0.0211457  |     1.16667 |

## 13. Appendix map

- Canonical frozen JSON:
  - `appendices/archived/final_practical_system.json`
- Canonical yearly thresholds:
  - `appendices/archived/yearly_thresholds_final.csv`
- Canonical signal path:
  - `appendices/archived/signal_path_new_final_flow.csv`
- Canonical trade list:
  - `appendices/archived/trades_new_final_flow.csv`
- Canonical daily equity:
  - `appendices/archived/daily_new_final_flow.csv`
- Rebuilt outputs from this spec:
  - `appendices/generated/rebuilt_yearly_thresholds_final.csv`
  - `appendices/generated/rebuilt_signal_path_new_final_flow.csv`
  - `appendices/generated/rebuilt_trades_new_final_flow.csv`
  - `appendices/generated/rebuilt_daily_new_final_flow.csv`
