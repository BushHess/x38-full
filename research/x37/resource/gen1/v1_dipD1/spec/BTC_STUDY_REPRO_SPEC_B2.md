# SPEC tái dựng 1:1 nghiên cứu BTC spot long-only và hệ thống B2_pullback

## 1. Mục tiêu và phạm vi

Tài liệu này là **spec tái dựng vận hành được** cho:

1. **toàn bộ nghiên cứu đã công bố** trong báo cáo BTC spot long-only discovery,
2. **hệ thống cuối cùng đã được đóng băng trước holdout**: `B2_pullback`.

Mục tiêu của spec là để một kỹ sư có thể, chỉ với:

- file dữ liệu gốc `data.zip`, và
- chính spec này,

mà dựng lại:

- pipeline dữ liệu,
- engine backtest,
- protocol validation,
- ngưỡng freeze trước holdout,
- các bảng/đồ thị chính,
- và **quyết định cuối cùng**: `COMPETITIVE`.

### Ranh giới fidelity

Spec này cố ý đóng băng **candidate slate nghiêm túc** và toàn bộ logic adjudication như là **đơn vị tái dựng chính thức** của nghiên cứu.

Lý do: phần brainstorming sơ khai của discovery không phải artifact cần tái dựng 1:1; thứ cần tái dựng 1:1 là:

- protocol đã khóa,
- feature/engine đã khóa,
- candidate slate đã khóa,
- hệ thống thắng cuộc đã freeze,
- các kiểm định đã khóa,
- và verdict cuối cùng.

Nói ngắn gọn: **đừng tái dựng “scratchpad”; hãy tái dựng đúng research artifact đã freeze.**

---

## 2. Input, schema, timezone, quarantine

### 2.1. Input bắt buộc

Giả định file nạp vào là `data.zip` và có đúng cấu trúc:

- `data/btcusdt_1d.csv`
- `data/btcusdt_4h.csv`

### 2.2. Schema CSV

Cả hai file đều có cùng schema cột:

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

### 2.3. Datetime convention

- `open_time` và `close_time` là Unix epoch **milliseconds**, timezone **UTC**.
- Chuyển sang datetime timezone-aware UTC:
  - `open_dt = to_datetime(open_time, unit='ms', utc=True)`
  - `close_dt = to_datetime(close_time, unit='ms', utc=True)`
- Sắp xếp tăng dần theo `close_dt`.

### 2.4. Quarantine dữ liệu sau cutoff

Cutoff toàn nghiên cứu là:

- `2026-02-20 23:59:59.999 UTC`

Giữ **chỉ** những row thỏa:

- `close_dt <= 2026-02-20 23:59:59.999 UTC`

Tức là:

- D1 giữ đến bar đóng ngày `2026-02-20`
- H4 giữ đến bar đóng lúc `2026-02-20 23:59:59.999 UTC`

### 2.5. Expected retained row counts

Sau khi quarantine, expected counts là:

- D1: `3110` rows
- H4: `18642` rows

Nếu row count lệch, dừng pipeline và kiểm tra lại cách đọc thời gian/cutoff.

---

## 3. Data integrity rules

### 3.1. Không resample, không vá gap, không chèn synthetic bar

Dữ liệu H4 có gap thật. **Giữ nguyên raw archive**.

Không được:

- resample H4 thành lưới đều rồi ffill,
- thêm synthetic OHLC,
- nội suy volume,
- sửa missing bar để “đẹp số”.

### 3.2. Expected missing H4 bars

Expected missing H4 **open timestamps** sau khi so với lưới 4h đều từ bar đầu đến bar cuối:

- `2017-09-06 16:00:00+00:00`
- `2018-02-08 04:00:00+00:00`
- `2018-02-08 08:00:00+00:00`
- `2018-02-08 12:00:00+00:00`
- `2018-02-08 16:00:00+00:00`
- `2018-02-08 20:00:00+00:00`
- `2018-02-09 00:00:00+00:00`
- `2018-02-09 04:00:00+00:00`
- `2018-06-26 04:00:00+00:00`
- `2018-06-26 08:00:00+00:00`
- `2018-07-04 04:00:00+00:00`
- `2018-11-14 04:00:00+00:00`
- `2019-03-12 04:00:00+00:00`
- `2019-05-15 04:00:00+00:00`
- `2019-05-15 08:00:00+00:00`
- `2019-08-15 04:00:00+00:00`
- `2020-02-19 12:00:00+00:00`

Tổng missing H4 bars: `17`

Phân bổ theo segment:

- warmup: `12`
- development: `5`
- holdout: `0`

---

## 4. Split nghiên cứu đã khóa

Protocol phải khóa **trước discovery** và không được đổi sau khi thấy kết quả.

### 4.1. Segment gốc

- **Warmup only**: `2017-08-17` đến `2018-12-31`
- **Development**: `2019-01-01` đến `2023-12-31`
- **Final untouched holdout**: `2024-01-01` đến `2026-02-20`

### 4.2. Walk-forward folds trên development

Dùng 6 fold anchored, unseen test window 6 tháng:

1. `2021-01-01` → `2021-06-30`
2. `2021-07-01` → `2021-12-31`
3. `2022-01-01` → `2022-06-30`
4. `2022-07-01` → `2022-12-31`
5. `2023-01-01` → `2023-06-30`
6. `2023-07-01` → `2023-12-31`

Train cho mỗi fold là **anchored expanding history** bắt đầu từ `2019-01-01` và kết thúc ngay trước test-start của fold đó.

### 4.3. Development OOS horizon dùng cho headline WFO

Headline development WFO chỉ tính trên phần unseen concatenated:

- `2021-01-01` → `2023-12-31`
- `days = 1095`

---

## 5. Complexity budget đã khóa

Áp dụng cho toàn nghiên cứu:

- long-only, long/cash 100%/0%
- không short
- không leverage
- không pyramiding
- không partial sizing
- không path-dependent stack filter phức tạp
- tối đa 4 tunable số học cho một ứng viên nghiêm túc
- signal tại bar close, fill tại next bar open
- cost: `10 bps/side = 20 bps round-trip`

---

## 6. Align D1 sang H4: quy ước quan trọng nhất

Mọi D1 feature phải được align vào H4 theo **latest completed D1 bar**, không được dùng D1 bar chưa đóng.

Triển khai đúng như sau:

- tính feature trên bảng D1 trước,
- sau đó `merge_asof` vào H4:
  - key: `close_dt`
  - `direction='backward'`
  - `allow_exact_matches=True`

Pseudo:

```python
h4 = pd.merge_asof(
    h4.sort_values('close_dt'),
    d1_features.sort_values('close_dt'),
    on='close_dt',
    direction='backward',
    allow_exact_matches=True,
)
```

Hệ quả:

- H4 bar đóng lúc `03:59`, `07:59`, `11:59`, `15:59`, `19:59` UTC của một ngày chỉ nhìn thấy D1 bar **ngày trước**.
- H4 bar đóng lúc `23:59:59.999` UTC nhìn thấy D1 bar **vừa đóng cùng ngày**.

Nếu align khác quy ước này, toàn bộ threshold và kết quả sẽ lệch.

---

## 7. Feature library cần có để tái dựng nghiên cứu

Chỉ các feature dưới đây là bắt buộc cho research artifact này.

### 7.1. D1 features

#### 7.1.1. Distance-from-mean (SMA)

Với `n` ngày:

```text
d1_dist_mean_n[t] = close_D1[t] / SMA_n(close_D1)[t] - 1
```

Dùng các lookback:

- `n ∈ {17, 21, 25}`

Trong hệ thống thắng cuộc B2, feature chính là:

- `d1_dist_mean_21`

#### 7.1.2. Daily return / drift (chỉ để decomposition hoặc comparator)

Nếu cần tái hiện decomposition/comparator, dùng thêm:

```text
d1_ret_n[t] = close_D1[t] / close_D1[t-n] - 1
```

Khuyến nghị có:

- `n = 21`

### 7.2. H4 features

#### 7.2.1. Pullback return

Với `n` H4 bars:

```text
ret_n[t] = close_H4[t] / close_H4[t-n] - 1
```

Dùng các lookback:

- `n ∈ {5, 6, 7}`

Trong B2, feature chính là:

- `ret_6`

#### 7.2.2. H4 distance-from-mean (phục vụ decomposition / persistence family)

```text
h4_dist_mean_n[t] = close_H4[t] / SMA_n(close_H4)[t] - 1
```

Tối thiểu cần:

- `n = 48`

#### 7.2.3. H4 efficiency ratio (phục vụ decomposition / persistence family)

```text
h4_eff_n[t] = abs(close_H4[t] - close_H4[t-n])
              / sum_{i=t-n+1..t} abs(close_H4[i] - close_H4[i-1])
```

Tối thiểu cần:

- `n = 24`

### 7.3. Rolling convention

Cho mọi rolling mean / rolling sum:

- trailing window,
- **bao gồm current bar**,
- `min_periods = window`

Các bar chưa đủ warmup feature sẽ là `NaN` và **không được giao dịch**.

### 7.4. Quantile convention

Mọi threshold định lượng trong nghiên cứu dùng empirical quantile với nội suy tuyến tính kiểu pandas mặc định:

```python
series.quantile(q)
```

Tức là interpolation mặc định kiểu `linear`.

---

## 8. Backtest engine: định nghĩa chuẩn

Đây là phần phải khớp chính xác nhất.

### 8.1. Position model

- position ∈ {0, 1}
- `1` nghĩa là long 100% notional
- `0` nghĩa là flat
- không có overlapping positions

### 8.2. Signal timing

- Signal luôn được tính tại **H4 close**.
- Nếu signal true tại bar `i` close và hiện đang flat, thì **entry** ở `open` của bar `i+1`.
- Với fixed-hold rule, nếu vào ở `entry_idx`, thì **exit** ở `open` của bar `entry_idx + hold_bars`.
- Với state rule, nếu state false tại bar `i` close trong khi đang long, thì exit ở `open` bar `i+1`.

### 8.3. Cost model

Chi phí chuẩn:

- `cost_per_side = 0.001`
- entry open: equity nhân `0.999`
- exit open: equity nhân `0.999`

Trade net return chuẩn:

```text
trade_net_ret = (1 - cost_per_side) * (exit_open / entry_open) * (1 - cost_per_side) - 1
```

### 8.4. Mark-to-market tại H4 close

Equity path được mark tại mỗi **H4 close**, không phải chỉ ở entry/exit.

Giả sử trade active trên interval bar index `[e, x)`:

- entry tại `open[e]`
- exit tại `open[x]`
- trade active trong các bar `e, e+1, ..., x-1`

Return từng H4 close của trade:

- bar đầu tiên active (`j = e`):

```text
bar_ret[e] = close[e] / open[e] - 1
```

- bar active tiếp theo (`e+1 <= j <= x-1`):

```text
bar_ret[j] = close[j] / close[j-1] - 1
```

- bar exit `x` không có price return của trade nữa; chỉ có **exit cost** tại `open[x]`.

Nếu bar không active:

```text
bar_ret[j] = 0
```

### 8.5. Daily equity / daily returns

- Sau khi có equity được mark ở mọi H4 close, group theo ngày UTC:

```text
daily_equity[date] = last equity value of that UTC date
```

- Daily return:

```text
daily_ret = daily_equity.pct_change().fillna(0)
```

### 8.6. Exposure

Exposure cho một scope là:

```text
Exposure = (# raw H4 bars in scope with active position) / (# raw H4 bars in scope)
```

Lưu ý:

- denominator là **raw retained bars**, không phải số bar “đáng ra phải có” theo lưới đều,
- vì dataset có missing H4 bars và spec yêu cầu giữ raw y nguyên.

---

## 9. Metric definitions: công thức phải khớp

### 9.1. Scope và `days`

Với mọi scope ngày `[start_date, end_date]`:

```text
days = calendar_day_count_inclusive(start_date, end_date)
```

Ví dụ:

- `2019-01-01` → `2026-02-20` ⇒ `2608`
- `2024-01-01` → `2026-02-20` ⇒ `782`
- `2021-01-01` → `2023-12-31` ⇒ `1095`

### 9.2. Trades trong scope

Một trade được tính thuộc scope nếu:

```text
entry_open_dt ∈ [scope_start, scope_end_endofday]
```

### 9.3. Total return

`total_return` của một scope **không** lấy từ daily equity product. Nó lấy từ **chuỗi trade net returns được compound theo thứ tự thời gian**:

```text
total_return = Π(1 + trade_net_ret_k) - 1
```

Đây là lý do total_return/CAGR có thể hơi lệch nhẹ nếu so trực tiếp với product của daily returns.

### 9.4. CAGR

```text
CAGR = (1 + total_return) ** (365 / days) - 1
```

### 9.5. Sharpe

Tính trên `daily_ret` của scope:

```text
Sharpe = mean(daily_ret_scope) / std(daily_ret_scope, ddof=0) * sqrt(365)
```

### 9.6. Sortino

Tính trên downside daily returns của scope:

```text
Sortino = mean(daily_ret_scope) / std(daily_ret_scope[daily_ret_scope < 0], ddof=0) * sqrt(365)
```

Nếu không có downside returns, cho `NaN`.

### 9.7. MDD

Từ daily returns trong scope:

```text
scope_equity = cumprod(1 + daily_ret_scope)
MDD = min(scope_equity / cummax(scope_equity) - 1)
```

### 9.8. Calmar

```text
Calmar = CAGR / abs(MDD)
```

### 9.9. Trades / Turnover

```text
Trades = count(scoped trades)
Turnover = 2 * Trades
```

### 9.10. WinRate

```text
WinRate = mean(trade_net_ret > 0)
```

### 9.11. ProfitFactor

```text
ProfitFactor = sum(positive trade_net_ret) / abs(sum(negative trade_net_ret))
```

Nếu không có trade thua, để `NaN`.

### 9.12. AvgTrade

```text
AvgTrade = mean(trade_net_ret)
```

### 9.13. MedianHoldDays trong bảng công bố

Để khớp **đúng bảng công bố**, không dùng actual clock duration.

Dùng công thức:

```text
MedianHoldDays = median((exit_idx - entry_idx + 1) * 4 / 24)
```

Tức là dùng **inclusive raw bar count** quy đổi sang ngày.

Lý do:

- đây là cách duy nhất khớp đúng các giá trị công bố như `4.1667` cho B2 dù actual fixed hold là 24 H4 bars,
- và vẫn ổn khi dataset có missing H4 bars.

### 9.14. Top5TradePnLShare

Để khớp đúng bảng công bố:

```text
Top5TradePnLShare = sum(5 trade_net_ret lớn nhất trong scope) / total_return_scope
```

Lưu ý:

- numerator dùng **simple trade net returns**, không weight theo equity,
- denominator dùng `total_return_scope` đã compound.

---

## 10. Phase 0: protocol khóa trước discovery

Phải được coi là immutable.

- splits như mục 4,
- metric như mục 9,
- bootstrap: circular daily block bootstrap, block sizes `10 / 20 / 40`, primary = `20`, resamples = `2000`,
- plateau: `±20%` trên mỗi tunable số học,
- complexity budget như mục 5,
- no leakage / no lookahead / no intrabar assumptions.

Không được đổi protocol sau khi nhìn candidate result.

---

## 11. Phase 1: data decomposition — bản tái dựng chính thức

### 11.1. Mục tiêu

Không bắt đầu từ strategy family có sẵn. Bắt đầu từ measurement. Nhưng **artifact tái dựng chính thức** của Phase 1 là **candidate slate đã freeze**, không phải mọi nhánh scratchwork bị loại.

### 11.2. Kết luận phải tái lập

Báo cáo decomposition phải dẫn tới đúng các kết luận sau:

1. **Raw autocorrelation H4/D1** không tạo ra edge standalone ổn định.
2. **H4 persistence/drift state** có edge chọn lọc, nhưng gãy rõ ở `2022` nếu dùng standalone.
3. **Daily drift/trend state** có edge standalone với turnover thấp hơn, nhưng bear-rally vulnerable nếu dùng một mình.
4. **H4 pullback standalone** không đủ; đứng một mình thì CAGR âm hoặc gần phẳng sau phí.
5. **Cross-timeframe interaction** mạnh nhất là:
   - D1 drift đủ mạnh,
   - H4 vừa pullback ngắn hạn,
   - vào ở nhịp hồi, không chase breakout.
6. Volatility / flow / seasonality chỉ đóng vai trò phụ hoặc không đủ robust.

### 11.3. Minimum measurable channels cần có

Phải đo tối thiểu các channel sau và kết luận theo đúng hướng ở 11.2:

- autocorrelation / raw continuation
- H4 persistence state (`h4_dist_mean_48`, `h4_eff_24`)
- daily drift state (`d1_dist_mean_21`)
- H4 pullback (`ret_6` và các lookback lân cận)
- cross-timeframe drift + pullback interaction
- volatility level / expansion (descriptor-only)
- flow / taker imbalance (descriptor-only)
- seasonality (reject)

### 11.4. Frozen serious candidate slate sau Phase 1

Kết quả chính thức của Phase 1 là giữ lại đúng 4 family nghiêm túc để đi vào WFO/hard validation:

- `A_persistence`
- `B2_pullback`
- `B4_sparse_pullback`
- `D_breakout`

Trong nghiên cứu đã freeze, chỉ `B2_pullback` đi tiếp đến final freeze.

---

## 12. Candidate slate: cách dùng trong bản tái dựng chính thức

### 12.1. Quan trọng

Để tái dựng **nghiên cứu đã công bố** 1:1, không cần tái tạo toàn bộ tree tìm kiếm đã bị discard. Thay vào đó:

- dùng candidate slate đã freeze,
- dùng đúng protocol WFO / plateau / ablation / cost / bootstrap,
- rồi ra quyết định như nghiên cứu gốc.

### 12.2. Ứng viên bắt buộc phải tái dựng chi tiết

Ứng viên bắt buộc phải tái dựng chi tiết tới cấp công thức là:

- `B2_pullback`

### 12.3. Ba ứng viên còn lại trong study artifact

Ba ứng viên còn lại (`A_persistence`, `B4_sparse_pullback`, `D_breakout`) tồn tại trong research artifact với vai trò:

- comparator trong development WFO,
- comparator trong holdout,
- comparator cho selection trước holdout,
- comparator cho regime/cost discussion.

Trong bản tái dựng chính thức, các bảng headline của 3 comparator này phải khớp với **expected outputs** ở mục 21.

Lưu ý thực dụng: final verdict **không phụ thuộc** vào việc ba comparator kia có được phát sinh lại bằng một notebook discovery tự do; verdict phụ thuộc vào:

- `B2` có pass hard criteria hay không,
- `B2` có beat frontier benchmark hay không.

---

## 13. Thiết kế và search space của family B (daily-gate + H4 pullback)

Đây là phần cần tái dựng hoàn toàn vì nó sinh ra `B2_pullback`.

### 13.1. Conceptual family freeze

Freeze concept trước search:

- higher timeframe gate = D1 drift state,
- lower timeframe timing = H4 pullback,
- entry only when flat,
- fixed-hold exit,
- no overlap.

### 13.2. Main coarse grid (plateau-ready grid)

Grid coarse bắt buộc:

#### D1 gate feature

- `d1_dist_mean_17`
- `d1_dist_mean_21`
- `d1_dist_mean_25`

#### H4 pullback feature

- `ret_5`
- `ret_6`
- `ret_7`

#### Hold bars

- `19`
- `24`
- `29`

#### Quantile convention cho coarse grid

- `q_gate = 0.80`
- `q_pull = 0.80`

Trong coarse grid:

- gate threshold = empirical quantile `0.80` của gate feature trên **training distribution**
- pull threshold = empirical quantile `0.20` của pull feature trên **training distribution**

Tổng số config: `3 × 3 × 3 = 27`

### 13.3. Walk-forward evaluation cho mỗi config

Cho mỗi config trong 27 config:

1. chạy 6 fold development WFO,
2. ở mỗi fold:
   - train = anchored history `2019-01-01` → ngay trước test-start,
   - thresholds lấy từ train distribution,
   - test = fold đang xét,
   - reset flat tại đầu mỗi fold,
   - không carry position giữa các fold,
3. aggregate kết quả OOS trên 6 fold.

### 13.4. Aggregate development-OOS metrics cho một config

- `total_return` = compound product của 6 fold total_returns
- `days = 1095`
- `CAGR = (1 + total_return)^(365/1095) - 1`
- `Sharpe/MDD/Sortino/Exposure/...` tính trên concatenated OOS daily returns / OOS trades của 6 fold

### 13.5. Published plateau summary phải khớp

Expected summary cho center được chọn:

- `center_sharpe = 1.17098`
- `center_cagr = 0.275438`
- `median_neighbor_sharpe = 0.996605`
- `median_neighbor_cagr = 0.256413`
- `all_27_positive_overall = 1`

### 13.6. Center được chọn từ coarse grid

Center được chọn trước holdout là:

- gate feature = `d1_dist_mean_21`
- pull feature = `ret_6`
- hold = `24`

Tên center trong plateau grid:

- `P_d1_dist_mean_21_ret_6_h24`

### 13.7. Lý do chọn center

Không chọn config có CAGR cao nhất. Chọn config có trade-off tốt nhất giữa:

- positive unseen performance,
- worst-fold stability,
- plateau breadth,
- simplicity.

Cụ thể, `q=0.80 / 0.80` không phải top-return quantile setting, nhưng là setting **cân bằng nhất** về fold stability.

---

## 14. Quantile stress test quanh center

Đây là robustness stress test, **không dùng để chọn parameter**.

### 14.1. Grid

Giữ lookback center:

- gate = `d1_dist_mean_21`
- pull = `ret_6`
- hold = `24`

Stress quantiles:

- `q_gate ∈ {0.75, 0.80, 0.85}`
- `q_pull ∈ {0.75, 0.80, 0.85}`

Quy ước threshold:

- gate threshold = `quantile(q_gate)`
- pull threshold = `quantile(1 - q_pull)`

Ví dụ:

- `q_pull = 0.80` nghĩa là bottom 20%
- `q_pull = 0.85` nghĩa là bottom 15%
- `q_pull = 0.75` nghĩa là bottom 25%

### 14.2. Published quantile-stress results phải khớp

| q_gate | q_pull | Sharpe | CAGR | worst_fold_cagr |
|---:|---:|---:|---:|---:|
| 0.80 | 0.85 | 1.30456 | 0.310929 | -0.140633 |
| 0.85 | 0.85 | 1.22809 | 0.273539 | -0.061299 |
| 0.80 | 0.80 | 1.17098 | 0.275438 | -0.00875129 |
| 0.85 | 0.75 | 1.03088 | 0.228728 | -0.0814449 |
| 0.85 | 0.80 | 1.01268 | 0.214441 | -0.0814449 |
| 0.80 | 0.75 | 0.891416 | 0.215666 | -0.134322 |
| 0.75 | 0.85 | 0.867389 | 0.194666 | -0.203209 |
| 0.75 | 0.80 | 0.561661 | 0.116169 | -0.341903 |
| 0.75 | 0.75 | 0.482257 | 0.0980012 | -0.241754 |

---

## 15. Freeze final spec trước holdout: `B2_pullback`

Đây là system cuối cùng đã được freeze **trước khi chạm final holdout**.

### 15.1. Feature definition

#### Higher timeframe gate

```text
d1_dist_mean_21 = close_D1 / SMA_21(close_D1) - 1
```

#### Lower timeframe pullback

```text
ret_6 = close_H4 / close_H4[-6] - 1
```

### 15.2. Threshold freeze rule

Threshold được freeze **từ toàn bộ development period** (`2019-01-01` → `2023-12-31`) sau khi center đã được chọn.

Cách tính:

- dùng H4 dataset đã được align D1 feature như mục 6,
- chỉ lấy H4 rows có `close_dt` nằm trong development,
- gate threshold = quantile `0.80` của `d1_dist_mean_21`,
- pull threshold = quantile `0.20` của `ret_6`.

### 15.3. Frozen numeric thresholds

Expected exact values:

```text
gate_thr = 0.07897335915171078
pull_thr = -0.018023643839895964
```

Trong report headline, chúng được làm tròn thành:

- `d1_dist_mean_21 >= 0.078973`
- `ret_6 <= -0.018024`

### 15.4. Entry rule

Tại H4 close của bar `i`, nếu đồng thời:

```text
d1_dist_mean_21[i] >= gate_thr
ret_6[i] <= pull_thr
position == flat
```

thì:

- vào long tại `open[i+1]`

### 15.5. Exit rule

- exit sau đúng `24` H4 bars,
- tức exit tại `open[entry_idx + 24]`.

### 15.6. Không persistence requirement sau entry

Sau khi vào lệnh, **không cần** gate còn đúng. Trade giữ nguyên tới time stop.

### 15.7. Position sizing

- `100% long / 0% flat`

### 15.8. Cost

- `10 bps mỗi chiều`
- `20 bps round-trip`

### 15.9. Data usage freeze

- chỉ dùng data tới `2026-02-20`
- không dùng gì sau cutoff để re-tune hoặc tái gắn nhãn

---

## 16. Development WFO của B2: expected fold-level checkpoints

Bảng sau là **golden reference** cho 6 fold unseen của B2.

| fold | test_start | test_end | days | total_return | CAGR | Sharpe | MDD | TradesEst | Exposure |
|---:|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2021-01-01 | 2021-06-30 | 181 | 0.092645 | 0.195628 | 0.626468 | -0.199436 | 7.5 | 0.156682 |
| 2 | 2021-07-01 | 2021-12-31 | 184 | 0.451509 | 1.094118 | 3.024429 | -0.058994 | 8.0 | 0.174071 |
| 3 | 2022-01-01 | 2022-06-30 | 181 | -0.004349 | -0.008751 | -0.092024 | -0.045050 | 2.0 | 0.044240 |
| 4 | 2022-07-01 | 2022-12-31 | 184 | -0.001273 | -0.002523 | 0.040009 | -0.081340 | 2.0 | 0.043518 |
| 5 | 2023-01-01 | 2023-06-30 | 181 | 0.276667 | 0.636491 | 2.312997 | -0.042296 | 6.0 | 0.132719 |
| 6 | 2023-07-01 | 2023-12-31 | 184 | 0.030499 | 0.061408 | 0.925556 | -0.030886 | 3.0 | 0.065277 |

### 16.1. Aggregate development-OOS headline của B2

Expected values:

| candidate | days | total_return | CAGR | Sharpe | Sortino | MDD | Calmar | Trades | WinRate | ProfitFactor | Exposure | Turnover | AvgTrade | MedianHoldDays | Top5TradePnLShare | pos_fold_sharpe_frac | pos_fold_cagr_frac | worst_fold_sharpe | worst_fold_cagr |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B2_pullback | 1095 | 1.0748 | 0.2754 | 1.1710 | 0.7989 | -0.1994 | 1.3811 | 29 | 0.7241 | 2.9953 | 0.1027 | 57.0 | 0.0283 | 4.1667 | 0.6793 | 0.8333 | 0.6667 | -0.0920 | -0.0088 |

Ghi chú:

- `Trades = 29` là rounded form của `sum(fold TradesEst) = 28.5`
- `Turnover = 57 = 2 * 28.5`

---

## 17. Holdout cuối cùng của B2

Scope:

- `2024-01-01` → `2026-02-20`

Expected holdout headline:

| candidate | days | total_return | CAGR | Sharpe | Sortino | MDD | Calmar | Trades | WinRate | ProfitFactor | Exposure | Turnover | AvgTrade | MedianHoldDays | Top5TradePnLShare |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B2_pullback | 782 | 0.3843 | 0.1639 | 1.2717 | 0.5827 | -0.0861 | 1.9032 | 14 | 0.7857 | 5.5417 | 0.0716 | 28.0 | 0.0244 | 4.1667 | 0.8859 |

---

## 18. Full-sample descriptive context của B2

Scope:

- `2019-01-01` → `2026-02-20`

Expected headline:

| candidate | days | total_return | CAGR | Sharpe | Sortino | MDD | Calmar | Trades | WinRate | ProfitFactor | Exposure | Turnover | AvgTrade | MedianHoldDays | Top5TradePnLShare |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B2_pullback | 2608 | 8.0281 | 0.3606 | 1.3447 | 0.8825 | -0.3527 | 1.0224 | 87 | 0.6897 | 3.1874 | 0.1335 | 174.0 | 0.0280 | 4.1667 | 0.1180 |

---

## 19. Ablation bắt buộc phải chạy

Ablation là mandatory để chứng minh từng module “kiếm được chỗ đứng”.

### 19.1. Variants cần có

Ít nhất phải có đúng các variant headline dưới đây:

- `Full B2`
- `Gate only state`
- `Pullback only`
- `H4 gate + pullback`
- `Breakout alt`

### 19.2. Expected development-OOS ablation table

| variant | CAGR | Sharpe | MDD | Exposure | TradesEst |
|:---|---:|---:|---:|---:|---:|
| Full B2 | 0.2754 | 1.1710 | -0.1994 | 0.1027 | 28.5 |
| Gate only state | 0.2520 | 0.9569 | -0.2240 | 0.1370 | 24.5 |
| Pullback only | -0.0449 | 0.1845 | -0.6209 | 0.6249 | 171.5 |
| H4 gate + pullback | 0.1417 | 0.7098 | -0.2510 | 0.0698 | 19.5 |
| Breakout alt | 0.1702 | 1.0894 | -0.1723 | 0.0402 | 44.0 |

### 19.3. Interpretation phải giữ nguyên

Báo cáo tái dựng phải giữ nguyên thông điệp:

- pullback-only không phải system hợp lệ,
- gate-only có edge nhưng yếu hơn B2 trong 2022,
- daily gate + H4 pullback là interaction thật sự, không phải redundancy,
- H4-only gate + pullback kém hơn daily-gate + pullback,
- breakout tradable nhưng yếu hơn B2.

---

## 20. Plateau và robustness bắt buộc của B2

### 20.1. ±20% numeric plateau quanh center

Tham số center:

- daily gate lookback = `21`
- pullback lookback = `6`
- hold = `24`

Perturb ±20% và round thành integer như sau:

- gate lookback: `{17, 21, 25}`
- pullback lookback: `{5, 6, 7}`
- hold: `{19, 24, 29}`

### 20.2. Expected plateau headline

| metric | value |
|:---|---:|
| center_sharpe | 1.17098 |
| center_cagr | 0.275438 |
| median_neighbor_sharpe | 0.996605 |
| median_neighbor_cagr | 0.256413 |
| all_27_positive_overall | 1 |

### 20.3. Required interpretation

Báo cáo tái dựng phải khẳng định đúng:

- plateau là **broad**, không phải sharp spike,
- cả 27 configs quanh center đều positive overall,
- center `21 / 6 / 24` được chọn vì ổn định nhất về fold behavior, không phải vì CAGR cao nhất.

---

## 21. Cost sensitivity bắt buộc của B2

Rerun final frozen B2 với round-trip cost:

- `0`
- `10`
- `20`
- `30`
- `40` bps

Cost per side tương ứng:

```text
cost_per_side = roundtrip_bps / 2 / 10000
```

Expected table:

| scope | roundtrip_bps | CAGR | Sharpe | MDD | Trades |
|:---|---:|---:|---:|---:|---:|
| full | 0 | 0.394178 | 1.440872 | -0.346877 | 87 |
| holdout | 0 | 0.179194 | 1.369703 | -0.085284 | 14 |
| full | 10 | 0.377305 | 1.392848 | -0.349816 | 87 |
| holdout | 10 | 0.171526 | 1.320947 | -0.085284 | 14 |
| full | 20 | 0.360628 | 1.344676 | -0.352743 | 87 |
| holdout | 20 | 0.163903 | 1.271680 | -0.086120 | 14 |
| full | 30 | 0.344145 | 1.296368 | -0.355658 | 87 |
| holdout | 30 | 0.156327 | 1.221925 | -0.087036 | 14 |
| full | 40 | 0.327853 | 1.247940 | -0.358561 | 87 |
| holdout | 40 | 0.148796 | 1.171712 | -0.087951 | 14 |

Required interpretation:

- edge vẫn positive ở `40 bps round-trip`.

---

## 22. Bootstrap robustness bắt buộc

### 22.1. Bootstrap type

Dùng **circular moving block bootstrap** trên `daily_ret` của scope.

### 22.2. Algorithm

Cho daily returns vector độ dài `N`:

1. chọn block size `b`,
2. với mỗi resample:
   - chọn ngẫu nhiên một sequence các block-start indices trên `[0, N-1]`, uniform,
   - mỗi block lấy `b` returns liên tiếp với wraparound circular,
   - concatenate cho đến khi độ dài ≥ `N`,
   - cắt về đúng `N`,
3. từ resampled daily return series tính lại:
   - Sharpe
   - CAGR
   - MDD
4. lặp `2000` lần.

### 22.3. Block sizes

- `10`
- `20`
- `40`

Primary diagnostic block size:

- `20`

### 22.4. Scope phải bootstrap

Bootstrap bắt buộc cho B2 ở 3 scope:

- development WFO unseen concatenated
- full sample descriptive
- holdout only

### 22.5. Expected B2 bootstrap summary

#### Development WFO (unseen concatenated)

- Block 10: median Sharpe `1.189`, median CAGR `0.272`, `P(Sharpe>0)=0.982`
- Block 20: median Sharpe `1.167`, median CAGR `0.268`, `P(Sharpe>0)=0.985`
- Block 40: median Sharpe `1.179`, median CAGR `0.268`, `P(Sharpe>0)=0.995`

#### Full sample

- Block 10: median Sharpe `1.356`, median CAGR `0.364`, `P(Sharpe>0)=1.000`
- Block 20: median Sharpe `1.343`, median CAGR `0.357`, `P(Sharpe>0)=1.000`
- Block 40: median Sharpe `1.343`, median CAGR `0.353`, `P(Sharpe>0)=1.000`

#### Holdout only

- Block 10: median Sharpe `1.269`, median CAGR `0.156`, `P(Sharpe>0)=0.976`
- Block 20: median Sharpe `1.247`, median CAGR `0.150`, `P(Sharpe>0)=0.981`
- Block 40: median Sharpe `1.246`, median CAGR `0.148`, `P(Sharpe>0)=0.989`

---

## 23. Regime decomposition bắt buộc

Phải chạy final frozen B2 trên các epoch sau:

- `2019-2020` = `2019-01-01` → `2020-12-31`
- `2021` = `2021-01-01` → `2021-12-31`
- `2022` = `2022-01-01` → `2022-12-31`
- `2023` = `2023-01-01` → `2023-12-31`
- `2024-2026-02` = `2024-01-01` → `2026-02-20`
- `2024` = `2024-01-01` → `2024-12-31`
- `2025` = `2025-01-01` → `2025-12-31`
- `2026-YTD` = `2026-01-01` → `2026-02-20`

Expected headline:

| epoch | CAGR | Sharpe | MDD | Trades |
|:---|---:|---:|---:|---:|
| 2019-2020 | 0.718005 | 1.787484 | -0.267622 | 38 |
| 2021 | 0.623925 | 1.409177 | -0.352743 | 21 |
| 2022 | -0.005616 | -0.006552 | -0.081340 | 4 |
| 2023 | 0.366339 | 1.959714 | -0.042296 | 11 |
| 2024-2026-02 | 0.163903 | 1.271680 | -0.086120 | 14 |
| 2024 | 0.301849 | 1.561109 | -0.086120 | 10 |
| 2025 | 0.062552 | 1.602862 | -0.017529 | 4 |
| 2026-YTD | 0.000000 | NaN | 0.000000 | 0 |

Required interpretation:

- `2022` gần như flat nhưng **không collapse**,
- holdout `2024-2026-02` rõ ràng positive,
- vì vậy B2 pass “no major historical epoch showing clear collapse”.

---

## 24. Comparator tables của candidate slate

Các bảng sau là part của research artifact và phải được tái xuất đúng.

### 24.1. Development walk-forward comparison

| candidate | Sharpe | CAGR | MDD | Trades | WinRate | ProfitFactor | pos_fold_sharpe_frac | pos_fold_cagr_frac | worst_fold_sharpe | worst_fold_cagr |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_persistence | 1.1233 | 0.2462 | -0.2105 | 70 | 0.3571 | 2.0106 | 0.6667 | 0.6667 | -1.8771 | -0.2139 |
| B2_pullback | 1.1710 | 0.2754 | -0.1994 | 29 | 0.7241 | 2.9953 | 0.8333 | 0.6667 | -0.0920 | -0.0088 |
| B4_sparse_pullback | 0.8512 | 0.1782 | -0.2663 | 28 | 0.5357 | 2.3594 | 0.8333 | 0.8333 | 0.1158 | 0.0000 |
| D_breakout | 1.0894 | 0.1702 | -0.1723 | 44 | 0.5000 | 2.0520 | 0.6667 | 0.6667 | -1.4460 | -0.0422 |

### 24.2. Final holdout comparison

| candidate | Sharpe | CAGR | MDD | Trades | WinRate | ProfitFactor | Exposure | MedianHoldDays |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|
| A_persistence | 0.5562 | 0.0857 | -0.2301 | 53 | 0.2642 | 1.5895 | 0.1006 | 0.5000 |
| B2_pullback | 1.2717 | 0.1639 | -0.0861 | 14 | 0.7857 | 5.5417 | 0.0716 | 4.1667 |
| B4_sparse_pullback | 0.8028 | 0.1095 | -0.2001 | 13 | 0.3846 | 2.2282 | 0.0569 | 3.1667 |
| D_breakout | 0.4602 | 0.0478 | -0.1072 | 29 | 0.4483 | 1.4541 | 0.0371 | 1.1667 |

### 24.3. Full-sample descriptive comparison

| candidate | Sharpe | CAGR | MDD | Trades | WinRate | ProfitFactor | Exposure | MedianHoldDays |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|
| A_persistence | 0.8747 | 0.2169 | -0.3358 | 211 | 0.2701 | 1.7758 | 0.1328 | 0.6667 |
| B2_pullback | 1.3447 | 0.3606 | -0.3527 | 87 | 0.6897 | 3.1874 | 0.1335 | 4.1667 |
| B4_sparse_pullback | 0.9626 | 0.2108 | -0.2967 | 79 | 0.5570 | 2.4739 | 0.1068 | 4.1667 |
| D_breakout | 0.3556 | 0.0475 | -0.3460 | 143 | 0.4615 | 1.2341 | 0.0549 | 1.1667 |

### 24.4. Pre-holdout selection logic phải ra đúng kết luận

Trước khi chạm holdout, phải chọn `B2_pullback` vì:

- strongest trade-off growth / regime hardness,
- worst unseen fold gần như flat thay vì collapse,
- interaction gate + pullback là edge thật,
- H4-only gate variants yếu hơn daily-gate variants.

---

## 25. Benchmark comparison và verdict logic

### 25.1. Benchmark context (không recompute từ raw data)

Dùng nguyên benchmark headline từ prompt:

| System | Scope | Sharpe | CAGR | MDD | Trades | Bootstrap_median_Sharpe | Bootstrap_median_CAGR | P_Sharpe_gt_0 | Notes |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|:---|
| E5+EMA21D1 | Provided benchmark | 1.638 | 0.728 | -0.385 | 186 | 0.766 | 0.244 | 0.968 | Robustness leader |
| V4 | Provided benchmark | 1.830 | 0.804 | -0.336 | 196 | 0.733 | 0.217 | 0.966 | Best full-sample variant |
| V3 | Provided comparator | 1.533 | 0.578 | -0.373 | 211 | 0.516 | 0.122 | 0.894 | Diagnostic only |
| B2 pullback (this study) | Fixed-rule full sample 2019-2026 | 1.3447 | 0.3606 | -0.3527 | 87 | 1.34311 | 0.356792 | 1.000 | Bootstrap method may differ |

### 25.2. Hard acceptance criteria

B2 chỉ được coi là winner nếu đồng thời:

- positive edge sau `20 bps round-trip`
- positive development unseen WFO overall
- positive final untouched holdout
- không có epoch collapse rõ ràng
- plateau rộng, không phải narrow optimum
- không leakage / không protocol drift hậu nghiệm

B2 pass toàn bộ.

### 25.3. Verdict mapping

- `SUPERIOR` nếu system mới beat frontier benchmark một cách đủ thuyết phục cả về robustness lẫn practical trade-off
- `COMPETITIVE` nếu pass hard criteria và là system mới khả dụng, nhưng chưa đủ bằng chứng để tuyên bố vượt frontier
- `NO ROBUST IMPROVEMENT` nếu không pass hard criteria

### 25.4. Required final verdict

Verdict cuối cùng **phải là**:

```text
COMPETITIVE
```

### 25.5. Lý do verdict phải là COMPETITIVE

Báo cáo tái dựng phải giữ nguyên logic sau:

1. `B2` pass hard criteria dưới protocol đã khóa.
2. `B2` mạnh trên unseen development WFO và positive trên untouched holdout.
3. `B2` đơn giản, cost-resilient, regime-hardened hơn các ứng viên yếu hơn trong study này.
4. Nhưng `B2` **không beat rõ ràng** frontier benchmarks (`E5+EMA21D1`, `V4`) trên headline full-sample Sharpe/CAGR.
5. Benchmark bootstrap method trong prompt không được public đầy đủ, nên bootstrap comparison chỉ mang tính directional.
6. Vì thế **không đủ cơ sở để gọi `SUPERIOR`**.

---

## 26. Output artifacts phải sinh ra

Tối thiểu phải sinh đúng các file artifact sau:

- `btc_research_report.md`
- `dev_candidate_comparison.csv`
- `holdout_candidate_results.csv`
- `fullsample_candidate_results.csv`
- `benchmark_comparison.csv`
- `b2_wfv_folds.csv`
- `b2_plateau_grid.csv`
- `b2_cost_sensitivity.csv`
- `regime_breakdown.csv`
- `bootstrap_summary.csv`
- `b2_equity_full.png`
- `b2_drawdown_full.png`
- `b2_walkforward_dev.png`
- `b2_bootstrap_sharpe_full.png`
- `regime_breakdown_candidates.png`
- `cost_sensitivity_candidates.png`

Nếu muốn nén lại thì tạo thêm:

- `btc_research_outputs.zip`

---

## 27. Plot specs tối thiểu

### 27.1. `b2_equity_full.png`

- equity curve full sample của B2
- trục thời gian: `2019-01-01` → `2026-02-20`

### 27.2. `b2_drawdown_full.png`

- drawdown curve full sample của B2

### 27.3. `b2_walkforward_dev.png`

- fold-level development WFO visualization của B2

### 27.4. `b2_bootstrap_sharpe_full.png`

- bootstrap Sharpe distribution của B2 full sample

### 27.5. `regime_breakdown_candidates.png`

- so sánh regime breakdown giữa các serious candidates

### 27.6. `cost_sensitivity_candidates.png`

- cost sensitivity so sánh candidates hoặc riêng B2 full/holdout

Màu sắc/format cụ thể không phải artifact cốt lõi; dữ liệu plotted mới là thứ phải khớp.

---

## 28. Pseudocode triển khai B2 end-to-end

```python
# 1) read raw csvs
# 2) convert timestamps -> UTC-aware datetimes
# 3) sort ascending by close_dt
# 4) quarantine rows with close_dt > 2026-02-20 23:59:59.999 UTC
# 5) keep H4 raw as-is; do not fill missing bars

# 6) compute D1 features
for n in [17, 21, 25]:
    d1[f'd1_dist_mean_{n}'] = d1['close'] / d1['close'].rolling(n).mean() - 1

# 7) compute H4 features
for n in [5, 6, 7]:
    h4[f'ret_{n}'] = h4['close'] / h4['close'].shift(n) - 1
h4['h4_dist_mean_48'] = h4['close'] / h4['close'].rolling(48).mean() - 1
h4['h4_eff_24'] = abs(h4['close'] - h4['close'].shift(24)) / h4['close'].diff().abs().rolling(24).sum()

# 8) align D1 -> H4 using merge_asof on close_dt, backward, allow_exact_matches=True

# 9) build B-family coarse grid over:
#    gate_feature in {d1_dist_mean_17, d1_dist_mean_21, d1_dist_mean_25}
#    pull_feature in {ret_5, ret_6, ret_7}
#    hold in {19, 24, 29}
#    q_gate=0.80, q_pull=0.80
#    evaluate each config on 6 anchored WFO folds

# 10) choose center = d1_dist_mean_21 + ret_6 + hold 24

# 11) stress quantiles around center with q_gate, q_pull in {0.75, 0.80, 0.85}
#     but do not use this stress grid to re-select the system

# 12) freeze final thresholds from whole development period
mask_dev = (h4['close_dt'] >= '2019-01-01 UTC') & (h4['close_dt'] <= '2023-12-31 23:59:59.999 UTC')
gate_thr = h4.loc[mask_dev, 'd1_dist_mean_21'].quantile(0.80)
pull_thr = h4.loc[mask_dev, 'ret_6'].quantile(0.20)

# 13) final B2 rule
# if flat and gate >= gate_thr and ret_6 <= pull_thr at bar i close:
#     enter at open[i+1]
# exit at open[entry_idx + 24]
# no overlap
# cost 10bps each side

# 14) evaluate on:
#     a) untouched holdout 2024-01-01..2026-02-20
#     b) full sample 2019-01-01..2026-02-20 (descriptive only)
#     c) regime epochs
#     d) cost sensitivity
#     e) bootstrap (10/20/40-day circular blocks, 2000 resamples)

# 15) compare against prompt benchmarks, then issue verdict = COMPETITIVE
```

---

## 29. Implementation traps dễ làm lệch kết quả

1. **Sai align D1→H4**
   - Đây là lỗi hay gặp nhất.
   - Nếu dùng D1 bar cùng ngày cho mọi H4 bar trong ngày, bạn sẽ leak.

2. **Resample/ffill H4 gaps**
   - Không được làm.

3. **Tính total_return từ daily returns**
   - Sai so với artifact công bố.
   - `total_return` phải compound từ scoped trade returns.

4. **Tính MedianHoldDays bằng actual timediff**
   - Sẽ không khớp bảng công bố.
   - Dùng inclusive bar-count formula ở mục 9.13.

5. **Tính Top5TradePnLShare theo equity-weighted PnL**
   - Sẽ không khớp bảng công bố.
   - Dùng công thức ở mục 9.14.

6. **Retune sau holdout**
   - Cấm tuyệt đối.

7. **Dùng benchmark bootstrap như apples-to-apples**
   - Không được. Prompt không công bố toàn bộ benchmark bootstrap protocol.

---

## 30. Acceptance checklist cuối cùng

Một bản rebuild được coi là đúng nếu đồng thời đạt:

- row counts sau quarantine khớp: D1=`3110`, H4=`18642`
- H4 missing bars count khớp: `17`
- frozen thresholds khớp:
  - `gate_thr = 0.07897335915171078`
  - `pull_thr = -0.018023643839895964`
- B2 holdout headline khớp gần đúng với bảng ở mục 17
- B2 full-sample headline khớp gần đúng với bảng ở mục 18
- B2 cost table khớp với mục 21
- B2 bootstrap summary khớp với mục 22
- B2 regime table khớp với mục 23
- development WFO B2 fold table khớp với mục 16
- verdict cuối cùng là `COMPETITIVE`

### Tolerance khuyến nghị

Vì report headline được làm tròn và có vài chỗ aggregate mang tính artifact presentation, dùng tolerance:

- thresholds: `±1e-12`
- metrics dạng số thực headline: `±5e-4`
- bảng hiển thị đã làm tròn 4 chữ số: match theo rounded display là đủ

---

## 31. Kết luận điều hành của spec

Nếu kỹ sư triển khai đúng spec này, họ phải đi đến cùng một kết luận như nghiên cứu gốc:

- edge đáng tin nhất trong dữ liệu này là **mua pullback H4 ngắn trên nền drift D1 đủ mạnh**,
- hệ thống `B2_pullback` là ứng viên thắng cuộc nội bộ của study,
- `B2_pullback` pass holdout, plateau, cost stress, bootstrap, regime checks,
- nhưng **chưa đủ bằng chứng để tuyên bố vượt frontier benchmark**, nên verdict đúng là:

```text
COMPETITIVE
```

