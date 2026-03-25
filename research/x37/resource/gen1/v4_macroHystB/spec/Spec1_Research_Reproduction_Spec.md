# Spec 1 — Research Reproduction Spec for `new_base` and `new_final_flow`

Tài liệu này là spec standalone để một kỹ sư tái dựng lại **đúng decision path nghiên cứu đã được bảo toàn trong artifact**: từ raw data → data audit → feature engineering → shortlist measurement → coarse dual-gate search → local family search → practical refinement → hai ứng viên cuối `new_base` và `new_final_flow`.

Bundle này **không cần chat history, code gốc, hay bất kỳ tài liệu nào khác** ngoài:

- `data.zip`
- `RESEARCH_PROMPT_V4.md`
- chính thư mục spec này

## 0. Phạm vi và quy tắc phân xử

### 0.1. Cái gì được khôi phục exact
Các phần sau khôi phục được exact hoặc decision-equivalent exact từ artifact còn lại:

- raw-data parsing, UTC semantics, gap handling, no-fill policy;
- H4-base research frame và D1 backward as-of alignment trên `close_dt`;
- feature formulas của các biến còn sống tới shortlist và final candidates;
- threshold calibration cho `new_base` và `new_final_flow`;
- state-machine semantics dùng trong mọi shortlisted systems;
- toàn bộ outputs của hai ứng viên cuối:
  - yearly thresholds,
  - signal path,
  - trade list,
  - daily equity,
  - final JSON specs;
- các bảng preserved dùng để ra quyết định:
  - `top_d1_single.csv`,
  - `top_h4_single.csv`,
  - `top_dual_dev.csv`,
  - `top_local_hold.csv`,
  - `plateau_base.csv`,
  - `plateau_final_flow.csv`,
  - `systems_summary.csv`,
  - `ablation.csv`,
  - `paired_bootstrap.csv`,
  - `cost_sensitivity.csv`,
  - `trade_compare.csv`,
  - `yearly_compare.csv`.

### 0.2. Cái gì chỉ khôi phục high-confidence
Artifact **không giữ lại toàn bộ loser universe** của broad scans. Vì vậy:

- broad single-feature scan đầy đủ chỉ còn preserved top rows, không còn mọi cấu hình bị loại;
- coarse dual-gate search đầy đủ chỉ còn preserved finalist table `top_dual_dev.csv`;
- bootstrap helper implementation chỉ còn suy ra được ở mức high-confidence từ bảng đầu ra:
  moving-block bootstrap trên daily returns, block sizes `5/10/20/40`, paired resampling dùng cùng block-index sequence, `n_boot = 800` (suy ra từ bước nhảy xác suất `0.00125`).

**Quy tắc phân xử:** nếu một chi tiết implementation mơ hồ, nhưng bảng archived đã khóa output, thì **archived table thắng**.

### 0.3. Mục tiêu của spec này
Mục tiêu không phải tái tạo từng dòng code exploratory đã thất lạc. Mục tiêu là tái dựng:

1. pipeline preserved đã thực sự dẫn tới `new_base` và `new_final_flow`;
2. toàn bộ outputs đủ để audit và verify quyết định cuối.

## 1. Files bắt buộc trong package này

### 1.1. Input
- `data.zip`
- `RESEARCH_PROMPT_V4.md`

### 1.2. Archived outputs được bundle sẵn
Trong `appendices/archived/` có đủ những file preserved cần để regression:

- `self_prompt.md`
- `scientific_candidate.json`
- `final_practical_system.json`
- `data_audit.json`
- `systems_summary.csv`
- `ablation.csv`
- `bootstrap_summary.csv`
- `paired_bootstrap.csv`
- `yearly_compare.csv`
- `cost_sensitivity.csv`
- `top_d1_single.csv`
- `top_h4_single.csv`
- `top_dual_dev.csv`
- `top_local_hold.csv`
- `plateau_base.csv`
- `plateau_final_flow.csv`
- `yearly_thresholds_base.csv`
- `yearly_thresholds_final.csv`
- `signal_path_new_base.csv`
- `daily_new_base.csv`
- `trades_new_base.csv`
- `signal_path_new_final_flow.csv`
- `daily_new_final_flow.csv`
- `trades_new_final_flow.csv`
- `trade_compare.csv`
- `report.html`

### 1.3. Generated verification files trong package này (practical-exact, không giả vờ bit-identical cho float64 CSV)
Trong `appendices/generated/`:

- `rebuilt_yearly_thresholds_base.csv`
- `rebuilt_yearly_thresholds_final.csv`
- `rebuilt_signal_path_new_base.csv`
- `rebuilt_daily_new_base.csv`
- `rebuilt_trades_new_base.csv`
- `rebuilt_signal_path_new_final_flow.csv`
- `rebuilt_daily_new_final_flow.csv`
- `rebuilt_trades_new_final_flow.csv`
- `rebuild_verification.csv`
- `verification_summary.json`
- `data_fingerprints.csv`

## 2. Environment và numeric contract

### 2.1. Reconstruction environment khuyến nghị
- Python `3.13.5`
- pandas `2.2.3`
- numpy `2.3.5`

### 2.2. Numeric contract
- dùng `float64` cho mọi numeric;
- timestamp phải là timezone-aware UTC;
- `rolling(...).std(ddof=1)`;
- quantile dùng pandas default linear interpolation;
- không resample raw OHLCV;
- không forward-fill gap H4;
- không sort lại theo thứ tự khác ngoài tăng dần `open_time`/`close_time`.

### 2.3. File fingerprints
`appendices/generated/data_fingerprints.csv` khóa SHA-256 của các file đầu vào và core archived artifacts.

## 3. Protocol lock đã dùng trong research redo

### 3.1. Input tư duy
`appendices/archived/self_prompt.md` là self-prompt đã dùng để tái khung nghiên cứu.

### 3.2. Protocol thực thi đã khóa
Các assumption bị khóa trước discovery:

- Market: BTCUSDT spot
- Side: long-only
- Base execution timeframe: H4
- Signal timing: bar close
- Fill model: next bar open
- Trading cost: `0.001` mỗi phía = `0.002` round trip
- Warmup/no-trade: không trade trước `2020-01-01`
- D1 chỉ được nhìn thấy trên H4 sau khi D1 bar đã đóng
- No lookahead, no intrabar fill, no future leakage qua feature/threshold/selection

### 3.3. Segment definitions
- warmup data context: `2017-08-17` → `2018-12-31`
- calibration context start: `2019-01-01`
- development / walk-forward reported: `2020-01-01` → `2023-12-31`
- diagnostic post-dev: `2024-01-01` → `2026-02-20`
- micro untouched slice: `2026-02-21` → `2026-03-10`

**Cảnh báo khoa học:** đoạn `2024-01-01` → `2026-02-20` đã bị contaminated bởi các vòng nghiên cứu trước trong chat gốc; vì vậy ở nghiên cứu này nó chỉ còn giá trị diagnostic, không phải untouched holdout proof.

## 4. Raw-data contract và data audit

### 4.1. Raw files
Trong `data.zip` có 2 file:

- `data/btcusdt_1d.csv`
- `data/btcusdt_4h.csv`

Các cột raw cần dùng:

- `open_time`, `close_time`
- `open`, `high`, `low`, `close`
- `volume`
- `taker_buy_base_vol`

### 4.2. Timestamp parsing exact
```python
df["open_dt"]  = pd.to_datetime(df["open_time"], unit="ms", utc=True)
df["close_dt"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
```

### 4.3. Audit preserved
`appendices/archived/data_audit.json` là source of truth.

Tóm tắt:

- D1: `3,128` rows, từ `2017-08-17 00:00:00+00:00` đến `2026-03-10 23:59:59.999000+00:00`
- H4: `18,752` rows, từ `2017-08-17 04:00:00+00:00` đến `2026-03-11 07:59:59.999000+00:00`
- D1: không duplicate, không non-24h gap
- H4: không duplicate; có `9` gap hiếm, **giữ nguyên**, không fill

Decision rule ở bước audit:

- nếu duplicate timestamp hoặc missing OHLCV lõi → fail build;
- nếu H4 gap hiếm nhưng dữ liệu còn nguyên thứ tự → **giữ nguyên** và tiếp tục.

## 5. Research frame exact: H4 base + D1 backward as-of

### 5.1. Base frame
Mọi scan preserved trong nghiên cứu này chạy trên **H4 research frame**. Không có engine riêng cho D1 execution.

Hệ quả quan trọng:

- kể cả D1-only hoặc D1-led candidates vẫn trade theo H4 open-to-next-open;
- mọi D1 feature trước khi dùng đều được merge vào H4 bằng backward as-of;
- distribution dùng để calibrate D1 thresholds cũng là distribution của **D1 feature sau khi đã được repeat trên H4 frame**.

### 5.2. As-of merge exact
Sort cả 2 frame theo `close_dt`, rồi:

```python
path = pd.merge_asof(
    h4_frame.sort_values("close_dt"),
    d1_feature_frame.sort_values("close_dt"),
    on="close_dt",
    direction="backward",
)
```

Ý nghĩa:
- tại H4 close `t`, path chỉ nhìn thấy D1 bar gần nhất có `d1.close_dt <= h4.close_dt`.

### 5.3. Không shift thêm sau merge
Không cộng thêm `shift(1)` sau `merge_asof`. Delay execution đã được xử lý đúng bằng state machine “signal at close, fill at next open”.

## 6. Feature engineering exact cho preserved decision path

Spec này chỉ khóa **feature set còn sống tới preserved shortlist**. Không cố bịa lại những exploratory features không còn artifact.

### 6.1. Generic helpers
```python
logret_1 = np.log(close / close.shift(1))
ret_n = close / close.shift(n) - 1
trendq_n = ret_n / (rolling_std(logret_1, n, ddof=1) * sqrt(n))
range_pos_n = (close - rolling_min(low, n)) / (rolling_max(high, n) - rolling_min(low, n))
buyimb_n = 2 * (rolling_sum(taker_buy_base_vol, n) / rolling_sum(volume, n)) - 1
```

### 6.2. Exact preserved features
```python
d1_ret_60      = d1.close / d1.close.shift(60) - 1
d1_trendq_60   = d1_ret_60 / (d1_logret_1.rolling(60).std(ddof=1) * sqrt(60))
d1_range_pos_60 = (d1.close - d1.low.rolling(60).min()) / (d1.high.rolling(60).max() - d1.low.rolling(60).min())

h4_ret_84      = h4.close / h4.close.shift(84) - 1
h4_ret_168     = h4.close / h4.close.shift(168) - 1
h4_trendq_84   = h4_ret_84 / (h4_logret_1.rolling(84).std(ddof=1) * sqrt(84))
h4_range_pos_168 = (h4.close - h4.low.rolling(168).min()) / (h4.high.rolling(168).max() - h4.low.rolling(168).min())
h4_buyimb_12   = 2 * (h4.taker_buy_base_vol.rolling(12).sum() / h4.volume.rolling(12).sum()) - 1
```

### 6.3. Tail semantics
- `high` tail: entry/hold khi `feature > threshold`
- `low` tail: entry/hold khi `feature < threshold`

### 6.4. Threshold window modes
- `expanding`: lịch sử từ `2019-01-01` đến trước `year_start`
- `tr1095`: lịch sử từ `year_start - 1095 ngày` đến trước `year_start`
- `tr365`: lịch sử từ `year_start - 365 ngày` đến trước `year_start`

Mọi threshold đều được tính trên **H4 research frame** đã merge xong.

## 7. State-machine template dùng cho tất cả preserved candidates

### 7.1. Evaluation timing
- features và thresholds được đọc ở **row H4 close hiện tại**
- position thay đổi ở **row H4 open kế tiếp**

### 7.2. Core state machine
Cho row `i` quyết định `pos[i+1]`:

```python
if current_pos == 0:
    desired_next = 1 nếu mọi điều kiện entry đúng
    else 0
else:
    desired_next = 1 nếu mọi điều kiện hold đúng
    else 0
```

### 7.3. Execution path
```python
trade[i+1] = 1 if desired_next != current_pos else 0
pos[i+1]   = desired_next
ret_h4[i]  = pos[i] * (open[i+1] / open[i] - 1) - trade[i] * 0.001
equity[i]  = cumprod(1 + ret_h4)[i]
```

### 7.4. No-trade warmup
Bất kể feature signal thế nào, nếu `open_dt < 2020-01-01 00:00:00+00:00` thì `desired_next = 0`.

## 8. Phase 1 — Measurement shortlist from single-feature systems

### 8.1. What survives from the artifact
Artifact không giữ full scan universe. Vì vậy **official preserved output** của Phase 1 là:

- `appendices/archived/top_d1_single.csv`
- `appendices/archived/top_h4_single.csv`

### 8.2. D1 single-feature preserved leaders
Top rows preserved:

| feature              | tail   |   q_on |   q_off | mode      |   sharpe |     cagr |       mdd |   trades |   pos_years |
|:---------------------|:-------|-------:|--------:|:----------|---------:|---------:|----------:|---------:|------------:|
| d1_range_compress_10 | low    |    0.3 |     0.4 | expanding | 1.43181  | 0.461434 | -0.393017 |       49 |           4 |
| d1_range_compress_10 | low    |    0.3 |     0.4 | tr1095    | 1.38755  | 0.444326 | -0.393017 |       48 |           4 |
| d1_atrn_20           | high   |    0.6 |     0.5 | expanding | 1.29529  | 0.717266 | -0.501313 |       14 |           4 |
| d1_atrn_20           | high   |    0.6 |     0.5 | tr1095    | 1.29529  | 0.717266 | -0.501313 |       14 |           4 |
| d1_range_compress_20 | high   |    0.7 |     0.5 | expanding | 1.13877  | 0.52272  | -0.465853 |       20 |           4 |
| d1_range_compress_20 | high   |    0.7 |     0.5 | tr1095    | 1.13877  | 0.52272  | -0.465853 |       20 |           4 |
| d1_vol_20            | high   |    0.7 |     0.5 | expanding | 1.00756  | 0.461171 | -0.534225 |       14 |           4 |
| d1_vol_20            | high   |    0.7 |     0.5 | tr1095    | 1.00756  | 0.461171 | -0.534225 |       14 |           4 |
| d1_range_compress_20 | high   |    0.8 |     0.6 | expanding | 0.991374 | 0.351094 | -0.31521  |       16 |           4 |
| d1_range_compress_20 | high   |    0.8 |     0.6 | tr1095    | 0.991374 | 0.351094 | -0.31521  |       16 |           4 |
| d1_ma_gap_40         | high   |    0.6 |     0.5 | expanding | 1.81551  | 0.938841 | -0.336869 |       21 |           3 |
| d1_ma_gap_40         | high   |    0.6 |     0.5 | tr1095    | 1.79744  | 0.925749 | -0.336869 |       21 |           3 |

Decision rule sau D1 shortlist:

- giữ lại **hai cụm cơ chế**:
  1. **range/location** (`d1_range_pos_60`) vì headline dev mạnh;
  2. **slow return persistence** (`d1_ret_60`, `d1_trendq_60`) vì mechanism sạch, phù hợp luận đề macro persistence và nổi lên mạnh ở các dual-gate steps sau đó.

### 8.3. H4 single-feature preserved leaders
Top rows preserved:

| feature               | tail   |   q_on |   q_off | mode      |   sharpe |     cagr |       mdd |   trades |   pos_years |
|:----------------------|:-------|-------:|--------:|:----------|---------:|---------:|----------:|---------:|------------:|
| h4_ret_168            | high   |    0.7 |     0.5 | expanding |  1.56595 | 0.700734 | -0.332391 |       23 |           4 |
| h4_ret_168            | high   |    0.7 |     0.5 | tr1095    |  1.53136 | 0.67764  | -0.332391 |       23 |           4 |
| h4_vol_42             | high   |    0.8 |     0.6 | tr365     |  1.22245 | 0.583743 | -0.48256  |       16 |           4 |
| h4_vol_42             | high   |    0.7 |     0.6 | tr365     |  1.16492 | 0.587909 | -0.48256  |       29 |           4 |
| h4_range_compress_126 | high   |    0.6 |     0.5 | tr1095    |  1.15438 | 0.567468 | -0.501068 |       21 |           4 |
| h4_range_compress_126 | high   |    0.6 |     0.5 | expanding |  1.13758 | 0.554248 | -0.501068 |       21 |           4 |
| h4_atrn_63            | high   |    0.6 |     0.5 | tr1095    |  1.13485 | 0.602053 | -0.501313 |       18 |           4 |
| h4_atrn_63            | high   |    0.6 |     0.5 | expanding |  1.12843 | 0.596468 | -0.501313 |       18 |           4 |
| h4_atrn_84            | high   |    0.6 |     0.5 | tr1095    |  1.11706 | 0.584984 | -0.501313 |       15 |           4 |
| h4_atrn_84            | high   |    0.6 |     0.5 | expanding |  1.11254 | 0.581154 | -0.501313 |       15 |           4 |
| h4_atrn_84            | high   |    0.7 |     0.5 | expanding |  1.10802 | 0.56417  | -0.501313 |       13 |           4 |
| h4_atrn_84            | high   |    0.7 |     0.5 | tr1095    |  1.10802 | 0.563792 | -0.501313 |       13 |           4 |

Decision rule sau H4 shortlist:

- giữ lại **trend/state layer**: `h4_trendq_84`
- giữ lại **fast return proxies**: `h4_ret_84`, `h4_ret_168`
- giữ lại **range location alternative**: `h4_range_pos_168`
- giữ **flow family** (`h4_buyimb_12`) dưới dạng **entry-only confirmation candidate**, không làm core alpha carrier.

### 8.4. Mechanism inference locked from Phase 1
Từ preserved Phase 1, research kết luận:

- alpha carrier chính không nằm ở H4 nhanh đơn lẻ;
- D1 chậm mang signal regime tốt hơn;
- H4 hợp vai state/timing controller;
- flow hữu ích nhất khi dùng như entry filter, không phải hold/exit engine.

## 9. Phase 2 — Coarse dual-gate search

### 9.1. Official preserved coarse search output
`appendices/archived/top_dual_dev.csv` là coarse dual-gate finalist table preserved từ Phase 2.

| macro_feature   | macro_mode   |   macro_q_on | micro_feature    | micro_mode   |   micro_q_on |   micro_q_off | use_macro_exit   |   sharpe |     cagr |       mdd |   trades |   pos_years |
|:----------------|:-------------|-------------:|:-----------------|:-------------|-------------:|--------------:|:-----------------|---------:|---------:|----------:|---------:|------------:|
| d1_range_pos_60 | expanding    |          0.6 | h4_trendq_84     | expanding    |          0.7 |           0.5 | True             |  1.99428 | 0.873376 | -0.237084 |       32 |           4 |
| d1_range_pos_60 | expanding    |          0.6 | h4_trendq_84     | expanding    |          0.7 |           0.5 | False            |  1.99428 | 0.873376 | -0.237084 |       32 |           4 |
| d1_range_pos_60 | expanding    |          0.6 | h4_ret_84        | tr365        |          0.7 |           0.5 | True             |  1.98173 | 0.892186 | -0.235036 |       33 |           4 |
| d1_range_pos_60 | expanding    |          0.6 | h4_ret_84        | tr365        |          0.7 |           0.5 | False            |  1.97711 | 0.889125 | -0.235036 |       33 |           4 |
| d1_ret_60       | tr1095       |          0.5 | h4_trendq_84     | expanding    |          0.7 |           0.5 | False            |  1.84343 | 0.767545 | -0.235036 |       34 |           4 |
| d1_ret_60       | tr1095       |          0.5 | h4_trendq_84     | expanding    |          0.7 |           0.5 | True             |  1.79886 | 0.732779 | -0.235036 |       39 |           4 |
| d1_ret_60       | tr1095       |          0.5 | h4_ret_84        | tr365        |          0.7 |           0.5 | False            |  1.78436 | 0.755348 | -0.235036 |       35 |           4 |
| d1_ret_60       | tr1095       |          0.5 | h4_ret_84        | tr365        |          0.7 |           0.5 | True             |  1.74    | 0.720822 | -0.235036 |       40 |           4 |
| d1_ret_60       | tr1095       |          0.5 | h4_range_pos_168 | tr365        |          0.6 |           0.5 | True             |  1.70162 | 0.706762 | -0.265333 |       41 |           4 |
| d1_range_pos_60 | expanding    |          0.6 | h4_ret_168       | expanding    |          0.7 |           0.5 | True             |  1.67142 | 0.723396 | -0.26539  |       20 |           4 |
| d1_ret_60       | tr1095       |          0.5 | h4_trendq_84     | expanding    |          0.6 |           0.5 | False            |  1.6665  | 0.686975 | -0.235036 |       53 |           4 |
| d1_range_pos_60 | expanding    |          0.6 | h4_ret_168       | tr1095       |          0.7 |           0.5 | True             |  1.62551 | 0.694263 | -0.26539  |       20 |           4 |

### 9.2. Candidate semantics
Các row trong `top_dual_dev.csv` dùng template:

- macro gate dùng feature D1 trên H4 merged frame;
- micro gate dùng feature H4;
- `use_macro_exit = True` nghĩa là:
  - đang long thì giữ khi **macro_on và micro_hold_on**
- `use_macro_exit = False` nghĩa là:
  - đang long thì chỉ cần **micro_hold_on**

### 9.3. Decision rule sau coarse dual search
Không chọn hàng đầu dev headline một cách máy móc.

Lý do:
- `d1_range_pos_60 × h4_trendq_84` cho dev Sharpe cao nhất, nhưng câu chuyện cơ chế thiên về location hơn là persistence;
- family `d1_ret_60 / d1_trendq_60 × h4_trendq_84` cho ra cluster sạch hơn để đào sâu ở step kế tiếp;
- artifact downstream (`top_local_hold.csv`, `ablation.csv`) xác nhận **D1 slow persistence + H4 trend-quality hysteresis** là family đúng để đóng băng thành scientific candidate.

Output của bước này:
- shortlist đưa sang local family search:
  - `d1_ret_60 × h4_trendq_84`
  - `d1_trendq_60 × h4_trendq_84`
  - các comparator `h4_ret_84`, `h4_ret_168`, `h4_range_pos_168` để loại.

## 10. Phase 3 — Local family search và chọn `new_base`

### 10.1. Official preserved local-family output
`appendices/archived/top_local_hold.csv` là source of truth.

| macro_feature   | macro_mode   |   macro_q_on | micro_feature   | micro_mode   |   micro_q_on |   micro_q_off | use_macro_exit   |   dev_sharpe |   hold_sharpe |   dev_trades |   hold_trades |
|:----------------|:-------------|-------------:|:----------------|:-------------|-------------:|--------------:|:-----------------|-------------:|--------------:|-------------:|--------------:|
| d1_ret_60       | expanding    |          0.5 | h4_trendq_84    | expanding    |          0.6 |           0.5 | False            |     1.6665   |       1.89204 |           53 |            23 |
| d1_trendq_60    | expanding    |          0.5 | h4_trendq_84    | expanding    |          0.6 |           0.5 | False            |     1.56358  |       1.66791 |           53 |            24 |
| d1_ret_60       | expanding    |          0.5 | h4_trendq_84    | tr1095       |          0.7 |           0.6 | False            |     1.59926  |       1.6083  |           53 |            21 |
| d1_ret_60       | tr1095       |          0.5 | h4_trendq_84    | expanding    |          0.6 |           0.5 | False            |     1.6665   |       1.587   |           53 |            25 |
| d1_trendq_60    | tr1095       |          0.5 | h4_trendq_84    | expanding    |          0.6 |           0.5 | False            |     1.56358  |       1.587   |           53 |            25 |
| d1_trendq_60    | tr1095       |          0.5 | h4_trendq_84    | expanding    |          0.6 |           0.5 | True             |     1.51538  |       1.55458 |           57 |            28 |
| d1_ret_60       | expanding    |          0.5 | h4_trendq_84    | tr1095       |          0.6 |           0.5 | False            |     1.6746   |       1.48759 |           53 |            28 |
| d1_ret_60       | tr1095       |          0.5 | h4_trendq_84    | expanding    |          0.6 |           0.5 | True             |     1.62238  |       1.48371 |           58 |            28 |
| d1_ret_60       | expanding    |          0.5 | h4_ret_168      | tr1095       |          0.7 |           0.5 | False            |     1.46232  |       1.48321 |           20 |             6 |
| d1_ret_60       | expanding    |          0.5 | h4_ret_84       | tr1095       |          0.6 |           0.5 | False            |     1.43015  |       1.47658 |           52 |            24 |
| d1_ret_60       | tr1095       |          0.6 | h4_trendq_84    | expanding    |          0.6 |           0.5 | True             |     0.993717 |       1.46771 |           54 |            29 |
| d1_ret_60       | expanding    |          0.5 | h4_trendq_84    | tr1095       |          0.7 |           0.5 | False            |     1.86634  |       1.45885 |           34 |            17 |

### 10.2. Why row 0 wins
Row thắng cuộc trong preserved table là:

- `macro_feature = d1_ret_60`
- `macro_mode = expanding`
- `macro_q_on = 0.5`
- `micro_feature = h4_trendq_84`
- `micro_mode = expanding`
- `micro_q_on = 0.6`
- `micro_q_off = 0.5`
- `use_macro_exit = False`

Decision rule exact:

1. ưu tiên family có `hold_sharpe` cao nhất trong các core systems đơn giản;
2. loại các row phải dùng `macro_exit=True` nếu `ablation` sau đó cho thấy macro exit làm tệ đi;
3. giữa `d1_ret_60` và `d1_trendq_60`, chọn `d1_ret_60` vì:
   - `hold_sharpe` cao nhất preserved table (`1.892037`);
   - dev Sharpe vẫn cao (`1.666501`);
   - ít giả định hơn `trendq`;
   - mechanism story trực tiếp hơn.

### 10.3. Plateau test exact quanh `new_base`
Official output: `appendices/archived/plateau_base.csv`

Grid exact:

- `macro_q ∈ (0.4, 0.5, 0.6)`
- `micro_on ∈ (0.5, 0.6, 0.7)`
- `micro_off ∈ (0.4, 0.5, 0.6)` với ràng buộc `micro_off <= micro_on`
- macro feature cố định: `d1_ret_60`
- micro feature cố định: `h4_trendq_84`
- macro mode = `expanding`
- micro mode = `expanding`
- `use_macro_exit = False`

Official preserved table:

|   macro_q |   micro_on |   micro_off |   dev_sharpe |   dev_cagr |   hold_sharpe |   hold_cagr |   dev_trades |   hold_trades |   pos_years |
|----------:|-----------:|------------:|-------------:|-----------:|--------------:|------------:|-------------:|--------------:|------------:|
|       0.4 |        0.5 |         0.4 |      1.44255 |   0.614529 |      0.681441 |    0.169891 |           55 |            39 |           3 |
|       0.4 |        0.5 |         0.5 |      1.41631 |   0.576849 |      0.686459 |    0.16584  |          134 |            81 |           3 |
|       0.4 |        0.6 |         0.4 |      1.39837 |   0.577319 |      0.818982 |    0.211801 |           42 |            26 |           3 |
|       0.4 |        0.6 |         0.5 |      1.50655 |   0.611654 |      1.21303  |    0.339592 |           64 |            33 |           3 |
|       0.4 |        0.6 |         0.6 |      1.52358 |   0.595504 |      0.934933 |    0.229049 |          124 |            69 |           3 |
|       0.4 |        0.7 |         0.4 |      1.60769 |   0.682229 |      0.381745 |    0.067818 |           30 |            20 |           3 |
|       0.4 |        0.7 |         0.5 |      1.65634 |   0.675348 |      0.525834 |    0.10518  |           41 |            23 |           3 |
|       0.4 |        0.7 |         0.6 |      1.49904 |   0.553648 |      0.298362 |    0.043312 |           60 |            33 |           3 |
|       0.5 |        0.5 |         0.4 |      1.56022 |   0.673491 |      1.33837  |    0.381411 |           46 |            28 |           3 |
|       0.5 |        0.5 |         0.5 |      1.58665 |   0.660187 |      1.41273  |    0.3914   |          110 |            59 |           3 |
|       0.5 |        0.6 |         0.4 |      1.5496  |   0.652614 |      1.48888  |    0.424525 |           34 |            17 |           4 |
|       0.5 |        0.6 |         0.5 |      1.6665  |   0.686975 |      1.89204  |    0.550885 |           53 |            23 |           4 |
|       0.5 |        0.6 |         0.6 |      1.60505 |   0.623852 |      1.18198  |    0.27529  |          107 |            47 |           4 |
|       0.5 |        0.7 |         0.4 |      1.76729 |   0.76433  |      0.965278 |    0.224566 |           25 |            13 |           4 |
|       0.5 |        0.7 |         0.5 |      1.84343 |   0.767545 |      1.12744  |    0.260581 |           34 |            16 |           4 |
|       0.5 |        0.7 |         0.6 |      1.60288 |   0.593065 |      0.590711 |    0.107629 |           53 |            23 |           4 |
|       0.6 |        0.5 |         0.4 |      1.21114 |   0.440415 |      0.712403 |    0.142954 |           38 |            20 |           3 |
|       0.6 |        0.5 |         0.5 |      1.23874 |   0.437703 |      0.781613 |    0.156559 |           88 |            42 |           3 |
|       0.6 |        0.6 |         0.4 |      1.11926 |   0.389596 |      0.963636 |    0.203654 |           32 |            12 |           3 |
|       0.6 |        0.6 |         0.5 |      1.25027 |   0.430716 |      1.40318  |    0.310363 |           47 |            16 |           3 |
|       0.6 |        0.6 |         0.6 |      1.15038 |   0.368611 |      1.14162  |    0.230314 |          101 |            32 |           3 |
|       0.6 |        0.7 |         0.4 |      1.34129 |   0.485182 |      0.68418  |    0.121911 |           23 |             9 |           3 |
|       0.6 |        0.7 |         0.5 |      1.39947 |   0.486232 |      0.823703 |    0.148302 |           32 |            10 |           3 |
|       0.6 |        0.7 |         0.6 |      1.12518 |   0.341005 |      0.526023 |    0.082056 |           51 |            14 |           3 |

Decision rule:
- giữ điểm giữa plateau, không chọn spike ở `micro_on=0.7`;
- chọn `macro_q=0.5`, `micro_on=0.6`, `micro_off=0.5`.

### 10.4. `new_base` exact frozen outcome
`new_base` là row được archive trong `scientific_candidate.json` và `yearly_thresholds_base.csv`.

Headline metrics preserved:

- dev 2020–2023: Sharpe `1.658285`, CAGR `0.688084`, MDD `-0.223571`, trades `53`
- diagnostic 2024–2026-02-20: Sharpe `1.766141`, CAGR `0.522566`, MDD `-0.107122`, trades `23`

## 11. Phase 4 — Practical refinement và chọn `new_final_flow`

### 11.1. Allowed modification budget
Sau khi `new_base` được freeze như scientific candidate, chỉ cho phép **một refinement module**:

- thêm **entry-only flow confirmation** `h4_buyimb_12`
- cấm:
  - đổi core mechanism,
  - đổi execution model,
  - dùng flow làm hold/exit,
  - thêm nhiều hơn một module mới.

### 11.2. Search grid exact cho practical refinement
Official output: `appendices/archived/plateau_final_flow.csv`

Grid exact:

- core grid y hệt `plateau_base.csv`:
  - `macro_q ∈ (0.4, 0.5, 0.6)`
  - `micro_on ∈ (0.5, 0.6, 0.7)`
  - `micro_off ∈ (0.4, 0.5, 0.6)`, `micro_off <= micro_on`
- thêm:
  - `flow_q ∈ (0.5, 0.55, 0.6, 0.65)`
- flow feature cố định: `h4_buyimb_12`
- flow calibration mode cố định: `tr365`
- flow tail: `high`
- flow chỉ áp dụng cho **entry**, không áp dụng cho hold/exit

Official preserved table:

|   macro_q |   micro_on |   micro_off |   flow_q |   dev_sharpe |   dev_cagr |   dev_mdd |   dev_trades |   hold_sharpe |   hold_cagr |   hold_mdd |   hold_trades |   pos_years |
|----------:|-----------:|------------:|---------:|-------------:|-----------:|----------:|-------------:|--------------:|------------:|-----------:|--------------:|------------:|
|       0.4 |        0.5 |         0.4 |     0.5  |      1.47461 |   0.593783 | -0.376856 |           40 |      0.646689 |    0.154885 |  -0.329494 |            30 |           3 |
|       0.4 |        0.5 |         0.4 |     0.55 |      1.52556 |   0.620102 | -0.370099 |           40 |      0.721874 |    0.179441 |  -0.333147 |            29 |           3 |
|       0.4 |        0.5 |         0.4 |     0.6  |      1.52283 |   0.617138 | -0.378626 |           40 |      0.896367 |    0.237201 |  -0.273433 |            26 |           3 |
|       0.4 |        0.5 |         0.4 |     0.65 |      1.50867 |   0.604729 | -0.37589  |           39 |      0.892434 |    0.235831 |  -0.273433 |            26 |           3 |
|       0.4 |        0.5 |         0.5 |     0.5  |      1.63995 |   0.652349 | -0.303218 |           71 |      0.820543 |    0.204849 |  -0.312145 |            53 |           3 |
|       0.4 |        0.5 |         0.5 |     0.55 |      1.7537  |   0.713517 | -0.303218 |           68 |      0.999168 |    0.262771 |  -0.298781 |            46 |           3 |
|       0.4 |        0.5 |         0.5 |     0.6  |      1.75504 |   0.711548 | -0.31561  |           65 |      1.02673  |    0.266914 |  -0.243822 |            43 |           3 |
|       0.4 |        0.5 |         0.5 |     0.65 |      1.70666 |   0.677408 | -0.332815 |           63 |      1.03166  |    0.268552 |  -0.243822 |            43 |           3 |
|       0.4 |        0.6 |         0.4 |     0.5  |      1.45054 |   0.573209 | -0.337804 |           35 |      0.98018  |    0.259739 |  -0.269739 |            21 |           3 |
|       0.4 |        0.6 |         0.4 |     0.55 |      1.49429 |   0.594883 | -0.337804 |           35 |      1.06444  |    0.287893 |  -0.281105 |            20 |           3 |
|       0.4 |        0.6 |         0.4 |     0.6  |      1.47237 |   0.581955 | -0.358623 |           35 |      1.15176  |    0.317107 |  -0.247777 |            19 |           3 |
|       0.4 |        0.6 |         0.4 |     0.65 |      1.44352 |   0.56181  | -0.374162 |           34 |      1.26672  |    0.356749 |  -0.207044 |            18 |           3 |
|       0.4 |        0.6 |         0.5 |     0.5  |      1.5778  |   0.607139 | -0.361127 |           45 |      1.1578   |    0.312277 |  -0.249202 |            26 |           3 |
|       0.4 |        0.6 |         0.5 |     0.55 |      1.67495 |   0.656758 | -0.361127 |           43 |      1.33405  |    0.371606 |  -0.226628 |            23 |           3 |
|       0.4 |        0.6 |         0.5 |     0.6  |      1.65201 |   0.643328 | -0.3627   |           43 |      1.31879  |    0.360562 |  -0.199796 |            22 |           3 |
|       0.4 |        0.6 |         0.5 |     0.65 |      1.6113  |   0.615753 | -0.365648 |           42 |      1.384    |    0.382262 |  -0.187195 |            21 |           3 |
|       0.4 |        0.6 |         0.6 |     0.5  |      1.51586 |   0.543485 | -0.283871 |           74 |      0.927148 |    0.220346 |  -0.217642 |            50 |           3 |
|       0.4 |        0.6 |         0.6 |     0.55 |      1.59853 |   0.581746 | -0.285312 |           69 |      1.08327  |    0.265443 |  -0.211575 |            46 |           3 |
|       0.4 |        0.6 |         0.6 |     0.6  |      1.56454 |   0.563735 | -0.284042 |           69 |      1.05193  |    0.249135 |  -0.206124 |            43 |           3 |
|       0.4 |        0.6 |         0.6 |     0.65 |      1.51849 |   0.536201 | -0.287437 |           64 |      1.10925  |    0.2649   |  -0.193212 |            42 |           3 |
|       0.4 |        0.7 |         0.4 |     0.5  |      1.67484 |   0.67927  | -0.283554 |           23 |      0.423817 |    0.078896 |  -0.245139 |            18 |           3 |
|       0.4 |        0.7 |         0.4 |     0.55 |      1.72136 |   0.702405 | -0.283554 |           23 |      0.520892 |    0.105816 |  -0.24925  |            17 |           3 |
|       0.4 |        0.7 |         0.4 |     0.6  |      1.71706 |   0.69984  | -0.283554 |           23 |      0.55057  |    0.114101 |  -0.241437 |            17 |           3 |
|       0.4 |        0.7 |         0.4 |     0.65 |      1.6519  |   0.660825 | -0.292838 |           23 |      0.549199 |    0.113716 |  -0.2402   |            17 |           3 |  

(đủ full table trong file CSV archived)

### 11.3. Selection rule cho `new_final_flow`
Chọn row:

- `macro_q = 0.5`
- `micro_on = 0.6`
- `micro_off = 0.5`
- `flow_q = 0.55`

Lý do preserved:

1. giữ nguyên core thresholds của `new_base` → không phá mechanism gốc;
2. flow filter giảm churn mạnh:
   - trades full từ `76` xuống `51`;
3. tăng trade quality:
   - win rate từ `0.460526` lên `0.588235`;
4. paired bootstrap so với `new_base` dương ở dev / hold / full;
5. `ablation.csv` cho thấy flow thật sự add value, nhưng chỉ khi đứng vai **entry confirmation**.

### 11.4. `new_final_flow` exact frozen outcome
Headline metrics preserved:

- dev 2020–2023: Sharpe `1.833771`, CAGR `0.733855`, MDD `-0.227295`, trades `35`
- diagnostic 2024–2026-02-20: Sharpe `1.835893`, CAGR `0.532426`, MDD `-0.112882`, trades `16`
- full 2020–2026-02-20: Sharpe `1.839461`, CAGR `0.671428`, MDD `-0.227295`, trades `51`

## 12. Robustness screens và lý do loại các nhánh khác

### 12.1. Systems summary preserved
| system          |   dev_sharpe |   dev_cagr |   dev_mdd |   dev_trades |   hold_sharpe |   hold_cagr |   hold_mdd |   hold_trades |   full_sharpe |   full_cagr |   full_mdd |   full_trades |
|:----------------|-------------:|-----------:|----------:|-------------:|--------------:|------------:|-----------:|--------------:|--------------:|------------:|-----------:|--------------:|
| new_base        |      1.65829 |   0.688084 | -0.223571 |           53 |      1.76614  |    0.522566 |  -0.107122 |            23 |       1.69015 |    0.638881 |  -0.223571 |            76 |
| new_final_flow  |      1.83377 |   0.733855 | -0.227295 |           35 |      1.83589  |    0.532426 |  -0.112882 |            16 |       1.83946 |    0.671428 |  -0.227295 |            51 |
| root_cause_old  |      1.61269 |   0.655432 | -0.238928 |           58 |      1.37518  |    0.376584 |  -0.152208 |            28 |       1.54977 |    0.562389 |  -0.238928 |            86 |
| fresh_start_old |      1.57012 |   0.522456 | -0.199552 |           58 |      0.101963 |   -0.002379 |  -0.278839 |            30 |       1.13252 |    0.313667 |  -0.278839 |            88 |
| h4d1_old        |      1.55706 |   0.634159 | -0.266875 |           74 |      0.150998 |    0.006951 |  -0.350875 |            44 |       1.15817 |    0.380105 |  -0.350875 |           118 |

Decision rule:
- `new_final_flow` thắng cả `new_base` lẫn các hệ cũ trên context đã contaminated;
- `fresh_start_old` và `h4d1_old` bị loại vì recent regime yếu rõ;
- `root_cause_old` bị loại vì không bằng `new_final_flow` ở combined robustness + trade quality.

### 12.2. Ablation preserved
| name                       |   dev_sharpe |   dev_cagr |   dev_mdd |   dev_trades |   hold_sharpe |   hold_cagr |   hold_mdd |   hold_trades |
|:---------------------------|-------------:|-----------:|----------:|-------------:|--------------:|------------:|-----------:|--------------:|
| macro_only                 |      1.59532 |   0.849874 | -0.296215 |           19 |      0.805387 |    0.222025 |  -0.195076 |            21 |
| micro_only                 |      1.40941 |   0.633479 | -0.462777 |           93 |      1.42325  |    0.462757 |  -0.241004 |            39 |
| micro_flow_only            |      1.49765 |   0.622572 | -0.442638 |           65 |      1.44789  |    0.448295 |  -0.17148  |            26 |
| macro_micro_macroexit_true |      1.62398 |   0.662049 | -0.238928 |           57 |      1.20746  |    0.300958 |  -0.163044 |            30 |
| macro_micro_base           |      1.65829 |   0.688084 | -0.223571 |           53 |      1.76614  |    0.522566 |  -0.107122 |            23 |
| macro_micro_flow_final     |      1.83377 |   0.733855 | -0.227295 |           35 |      1.83589  |    0.532426 |  -0.112882 |            16 |

Key inference locked:
- `macro_only`: D1 một mình chưa đủ
- `micro_only`: H4 một mình churn cao hơn
- `macro_micro_macroexit_true`: D1 **không nên** làm exit
- `macro_micro_flow_final`: practical best

### 12.3. Paired bootstrap preserved
Subtable phục vụ decision:

| segment   | comparator      |   block |   median_delta_sharpe |   p_delta_sharpe_gt_0 |   median_delta_cagr |   p_delta_cagr_gt_0 |   median_delta_mdd |   p_delta_mdd_gt_0 |
|:----------|:----------------|--------:|----------------------:|----------------------:|--------------------:|--------------------:|-------------------:|-------------------:|
| hold      | new_base        |      10 |              0.05816  |               0.7375  |            0.00647  |             0.565   |           0.004105 |            0.72875 |
| hold      | new_base        |      20 |              0.076039 |               0.78875 |            0.01137  |             0.61125 |           0.004187 |            0.7375  |
| hold      | new_base        |      40 |              0.07734  |               0.81375 |            0.011231 |             0.63125 |           0.007085 |            0.755   |
| hold      | root_cause_old  |      20 |              0.484993 |               0.98125 |            0.162285 |             0.9575  |           0.04486  |            0.90375 |
| hold      | fresh_start_old |      20 |              1.73043  |               1       |            0.52454  |             1       |           0.195165 |            0.995   |
| hold      | h4d1_old        |      20 |              1.72192  |               1       |            0.524125 |             1       |           0.171122 |            0.99375 |
| full2020  | new_base        |      10 |              0.145727 |               0.91375 |            0.030325 |             0.7175  |           0.028648 |            0.82875 |
| full2020  | new_base        |      20 |              0.145477 |               0.93    |            0.034176 |             0.7375  |           0.038452 |            0.84875 |
| full2020  | new_base        |      40 |              0.140315 |               0.9325  |            0.028655 |             0.7375  |           0.046128 |            0.85375 |
| full2020  | root_cause_old  |      20 |              0.287309 |               0.9875  |            0.108264 |             0.95    |           0.053856 |            0.9025  |
| full2020  | fresh_start_old |      20 |              0.734265 |               1       |            0.365556 |             1       |           0.100867 |            0.89125 |
| full2020  | h4d1_old        |      20 |              0.690979 |               0.99875 |            0.308546 |             0.9975  |           0.112625 |            0.90375 |
| dev       | new_base        |      10 |              0.152673 |               0.895   |            0.032696 |             0.67625 |           0.033465 |            0.83    |
| dev       | new_base        |      20 |              0.156032 |               0.85875 |            0.038109 |             0.675   |           0.044213 |            0.87    |
| dev       | new_base        |      40 |              0.140091 |               0.87125 |            0.030939 |             0.67375 |           0.047379 |            0.8475  |

Interpretation:
- `new_final_flow` > `new_base` với xác suất delta Sharpe dương đủ tích cực;
- `new_final_flow` thắng rõ các prior internal systems ở hold/full.

### 12.4. Cost sensitivity preserved
| system         |   cost_per_side | segment   |   sharpe |     cagr |       mdd |   equity_final |   trades |   exposure |
|:---------------|----------------:|:----------|---------:|---------:|----------:|---------------:|---------:|-----------:|
| new_final_flow |          0      | dev       |  1.88874 | 0.764497 | -0.221957 |        9.66348 |       35 |   0.253796 |
| new_final_flow |          0      | hold      |  1.89572 | 0.554841 | -0.107529 |        2.56655 |       16 |   0.246692 |
| new_final_flow |          0      | full2020  |  1.89573 | 0.699443 | -0.221957 |       25.8852  |       51 |   0.251208 |
| new_final_flow |          0.001  | dev       |  1.83377 | 0.733855 | -0.227295 |        9.01036 |       35 |   0.253796 |
| new_final_flow |          0.001  | hold      |  1.83589 | 0.532426 | -0.112882 |        2.48818 |       16 |   0.246692 |
| new_final_flow |          0.001  | full2020  |  1.83946 | 0.671428 | -0.227295 |       23.3754  |       51 |   0.251208 |
| new_final_flow |          0.0025 | dev       |  1.75098 | 0.68883  | -0.236511 |        8.11144 |       35 |   0.253796 |
| new_final_flow |          0.0025 | hold      |  1.74552 | 0.499368 | -0.120861 |        2.37496 |       16 |   0.246692 |
| new_final_flow |          0.0025 | full2020  |  1.75463 | 0.630218 | -0.236511 |       20.0557  |       51 |   0.251208 |
| new_base       |          0      | dev       |  1.736   | 0.733442 | -0.215899 |        9.0018  |       53 |   0.306085 |
| new_base       |          0      | hold      |  1.8503  | 0.555001 | -0.106357 |        2.56711 |       23 |   0.263124 |
| new_base       |          0      | full2020  |  1.76924 | 0.67997  | -0.215899 |       24.1181  |       76 |   0.290982 |
| new_base       |          0.001  | dev       |  1.65829 | 0.688084 | -0.223571 |        8.09712 |       53 |   0.306085 |
| new_base       |          0.001  | hold      |  1.76614 | 0.522566 | -0.107122 |        2.45412 |       23 |   0.263124 |
| new_base       |          0.001  | full2020  |  1.69015 | 0.638881 | -0.223571 |       20.7186  |       76 |   0.290982 |
| new_base       |          0.0025 | dev       |  1.54153 | 0.622181 | -0.237127 |        6.90632 |       53 |   0.306085 |
| new_base       |          0.0025 | hold      |  1.63922 | 0.475119 | -0.117785 |        2.29369 |       23 |   0.263124 |
| new_base       |          0.0025 | full2020  |  1.5712  | 0.579052 | -0.237127 |       16.4917  |       76 |   0.290982 |

Interpretation:
- edge không biến mất ở cost stress 25 bps/side;
- `new_final_flow` vẫn duy trì ưu thế headline.

### 12.5. Trade quality preserved
| system          |   trades |   win_rate |   avg_net_ret |   med_net_ret |   avg_hold_days |   med_hold_days |   top5_sum |   bottom5_sum |   total_net_factor |
|:----------------|---------:|-----------:|--------------:|--------------:|----------------:|----------------:|-----------:|--------------:|-------------------:|
| new_final_flow  |       51 |   0.588235 |      0.075133 |      0.003649 |        11.0458  |         6.33333 |    2.59848 |     -0.303592 |           23.3739  |
| new_base        |       76 |   0.460526 |      0.049465 |     -0.003293 |         8.58553 |         3.16667 |    2.63945 |     -0.318527 |           20.7156  |
| root_cause_old  |       86 |   0.418605 |      0.039693 |     -0.006332 |         7.4438  |         2.83333 |    2.4727  |     -0.330328 |           15.449   |
| fresh_start_old |       88 |   0.329545 |      0.024204 |     -0.012281 |         6.08144 |         2.83333 |    1.98289 |     -0.309999 |            5.33347 |
| h4d1_old        |      118 |   0.423729 |      0.020064 |     -0.004824 |         5.37994 |         4.16667 |    1.51186 |     -0.406253 |            7.21612 |

Interpretation:
- `new_final_flow` tăng hit-rate, kéo dài thời gian giữ lệnh, giữ top winners gần như nguyên vẹn và giảm trade count.

## 13. Acceptance contract cho Spec 1

Một rebuild Research Reproduction được coi là đạt nếu:

1. raw-data audit khớp `data_audit.json`;
2. H4 research frame + D1 as-of merge tái tạo đúng yearly thresholds của `new_base` và `new_final_flow`;
3. `scientific_candidate.json` và `final_practical_system.json` được regenerate đúng logic;
4. outputs generated trong `appendices/generated/` match archived tables của:
   - thresholds,
   - signal path,
   - daily equity,
   - trade list;
   - với numeric fields dùng tolerance `max_abs_diff <= 1e-12`, còn timestamp/string/discrete fields phải exact equality;
5. decision path preserved vẫn giữ nguyên:
   - Phase 1: D1 slow persistence + H4 trend/state + flow entry-only
   - Phase 2: shortlist sang local family search
   - Phase 3: `new_base`
   - Phase 4: `new_final_flow`

## 14. Appendix map

### 14.1. Archived source-of-truth files
- `appendices/archived/top_d1_single.csv`
- `appendices/archived/top_h4_single.csv`
- `appendices/archived/top_dual_dev.csv`
- `appendices/archived/top_local_hold.csv`
- `appendices/archived/plateau_base.csv`
- `appendices/archived/plateau_final_flow.csv`
- `appendices/archived/ablation.csv`
- `appendices/archived/paired_bootstrap.csv`
- `appendices/archived/cost_sensitivity.csv`
- `appendices/archived/systems_summary.csv`
- `appendices/archived/trade_compare.csv`

### 14.2. Generated verification files
- `appendices/generated/rebuild_verification.csv`
- `appendices/generated/verification_summary.json`
- `appendices/generated/rebuilt_*`
