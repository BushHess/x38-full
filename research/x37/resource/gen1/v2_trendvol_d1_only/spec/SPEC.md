# BTC Spot Long-Only Research Rebuild Spec

Phiên bản này nhằm tái dựng, ở mức cao nhất có thể từ artifact còn lại, hai thứ:

1. **Toàn bộ pipeline nghiên cứu** đã dẫn tới báo cáo cuối.
2. **Hệ thống cuối cùng đã đóng băng** (`trendvol_10 + dist_high_60`) từ raw data đến verdict.

Tài liệu này là **spec chuẩn** cho kỹ sư triển khai lại từ đầu. Toàn bộ CSV trong `appendices/archived_tables/` là **golden master** trích trực tiếp từ artifact đã lưu; nếu code triển khai mâu thuẫn với các bảng đó, **appendix thắng**.

---

## 0. Ranh giới khôi phục

### 0.1. Khôi phục **exact**
Các phần sau khôi phục được ở mức thực dụng 1:1 từ artifact:
- split thời gian, warmup, cost, walk-forward, holdout;
- công thức và threshold của **hệ thống cuối cùng**;
- annual refit rule;
- signal path của hệ thống cuối cùng;
- ngày vào/ra lệnh, số bar mỗi trade, số trade;
- search space 246 config ở cấp family;
- coarse search 108 config trong family thắng;
- plateau test, ablation, cost sensitivity, regime table, benchmark summary;
- verdict logic cuối cùng.

### 0.2. Khôi phục **high confidence, nhưng không chứng minh được byte-identical**
- một phần feature library exploratory của Phase 1, nhất là các `x_*` interaction feature;
- chi tiết chính xác của metric implementation ở ranh giới slice (khác biệt rất nhỏ, cỡ vài bp, so với cách factorization đơn giản nhất);
- RNG seed bootstrap gốc.

### 0.3. Hệ quả thực tế
- **Frozen final system** tái dựng được gần như tuyệt đối.
- **Research pipeline** tái dựng được đủ để ra cùng winner, cùng search tables, cùng kết luận, cùng report tables chính. 
- Với bootstrap và một số exploratory feature `x_*`, hãy dùng appendix như regression target; đừng giả vờ rằng artifact còn lại đủ để chứng minh 100% byte-identical source code gốc. Nó không đủ.

---

## 1. Nội dung package

### 1.1. File chính
- `SPEC.md` — tài liệu này.

### 1.2. Golden-master tables trích từ artifact cũ
Trong `appendices/archived_tables/`:
- `phase1_univariate_measurements.csv`
- `phase1_channel_highlights.csv`
- `family_search_results.csv`
- `candidate_coarse_search_trendvol_nearhigh.csv`
- `plateau_test.csv`
- `ablation_results.csv`
- `cost_sensitivity.csv`
- `regime_yearly_metrics.csv`
- `bootstrap_oos_summary.csv`
- `bootstrap_holdout_summary.csv`
- `bootstrap_full_summary.csv`
- `benchmark_comparison_summary.csv`
- `trades_full.csv`
- `trades_holdout.csv`

### 1.3. File generated thêm để khóa chặt final system
Trong `appendices/generated/`:
- `frozen_system_thresholds.csv` — threshold từng năm.
- `frozen_system_signal_path.csv` — state path D1 của hệ thống cuối cùng.
- `frozen_system_trades_rebuilt.csv` — trade list tái dựng từ signal path.
- `recoverability_map.csv` — map exact / inferred / unrecoverable.

---

## 2. Input data và invariant

Nguồn duy nhất là `data.zip`, gồm:
- `data/btcusdt_1d.csv`
- `data/btcusdt_4h.csv`

Các cột raw quan trọng:
- `open_time`, `close_time` (Unix ms, UTC)
- `open`, `high`, `low`, `close`
- `volume`
- `quote_volume`
- `num_trades`
- `taker_buy_base_vol`
- `taker_buy_quote_vol`
- `interval`

### 2.1. Invariant bắt buộc
- sort tăng dần theo `open_time`;
- không reorder theo cột khác;
- toàn bộ timestamp dùng **UTC**;
- không forward-fill OHLCV;
- không resample lại raw bar;
- ignore mọi bar **sau** `2026-02-20` cho evaluation, dù raw data còn dài hơn.

### 2.2. Timestamp chuẩn dùng trong code
Sau khi load:
- `open_dt = to_datetime(open_time, unit='ms', utc=True)`
- `close_dt = to_datetime(close_time, unit='ms', utc=True)`
- `trade_date = open_dt.date()` cho D1 report/trade list.

---

## 3. Protocol constants (khóa trước discovery)

Dùng đúng các hằng số sau:

- Warmup only: `2017-08-17` đến `2018-12-31`, **no trading**.
- Development: `2019-01-01` đến `2023-12-31`.
- Walk-forward test windows: `2020`, `2021`, `2022`, `2023` (4 cửa sổ năm, non-overlapping).
- Final untouched holdout: `2024-01-01` đến `2026-02-20`.
- Market: BTC/USDT spot.
- Long-only, no leverage.
- Signal at bar close.
- Fill at next bar open.
- Cost: `10 bps/side = 0.001`; `20 bps round-trip`; stress test `50 bps round-trip = 25 bps/side = 0.0025`.
- Annualization for Sharpe/CAGR: `365.25`.
- Bootstrap block sizes: `5, 10, 20, 40` ngày.
- Bootstrap resamples: `2000`.
- Plateau perturbation: one-at-a-time `0.8x, 0.9x, 1.0x, 1.1x, 1.2x`.
- Complexity budget: max `4` tunables, no regime-specific params, annual threshold refit only.

---

## 4. Time semantics và anti-lookahead rules

### 4.1. D1 dùng trên D1 system
Cho hệ thống D1 cuối cùng:
- feature của ngày `t` được tính từ **D1 bar vừa đóng tại close của ngày t**;
- decision được chốt tại close ngày `t`;
- position thay đổi tại **open ngày t+1**.

### 4.2. D1 feature nhìn từ H4 ở Phase 1
Khi merge D1 feature vào H4 matrix:
- chỉ được thấy **D1 bar đã hoàn tất trước H4 close hiện tại**;
- D1 bar có `close_dt == H4 close_dt` **chưa được phép thấy**;
- implementation chuẩn:
  - `pd.merge_asof(..., on='close_dt', direction='backward', allow_exact_matches=False)`

Đây là điểm chống lookahead quan trọng nhất ở Phase 1.

---

## 5. Feature library

## 5.1. Primitive definitions (exact)
Cho một timeframe bất kỳ (`D1` hoặc `H4`):

- `ret_1[t] = close[t] / close[t-1] - 1`
- `ret_L[t] = close[t] / close[t-L] - 1`
- `trendvol_L[t] = ret_L[t] / (rolling_std(ret_1, L, ddof=1)[t] * sqrt(L))`
- `dist_high_L[t] = close[t] / rolling_max(high, L)[t] - 1`
- `dist_low_L[t] = close[t] / rolling_min(low, L)[t] - 1`
- `draw_L[t] = close[t] / rolling_max(close, L)[t] - 1`
- `pullback_L[t] = draw_L[t]`  
  Artifact cho thấy `draw_*` và `pullback_*` là alias logic ở build cuối; giữ duplication này để khớp CSV.
- `vol_L[t] = rolling_std(ret_1, L, ddof=1)[t]`
- `rng_L[t] = rolling_max(high, L)[t] / rolling_min(low, L)[t] - 1`
- `close_loc[t] = (close[t] - low[t]) / (high[t] - low[t])`
- `body_pct[t] = (close[t] - open[t]) / (high[t] - low[t])`
- `tbuy_share[t] = taker_buy_base_vol[t] / volume[t]`
- `tbuy_L[t] = rolling_mean(tbuy_share, L)[t]`
- `tbuyz_L[t] = (tbuy_share[t] - rolling_mean(tbuy_share, L)[t]) / rolling_std(tbuy_share, L, ddof=1)[t]`
- `volz_L[t] = (vol_L[t] - rolling_mean(vol_L, L)[t]) / rolling_std(vol_L, L, ddof=1)[t]`
- `range_ratio_5_20[t] = rng_5[t] / rng_20[t]`

### 5.1.1. NaN rules
- rolling feature chỉ hợp lệ khi đủ full window;
- chia cho 0 -> `NaN`;
- threshold calibration luôn `dropna()` trước khi lấy quantile;
- nếu feature của bar hiện tại là `NaN`, signal = `False`.

## 5.2. Feature inventory 65 biến của Phase 1

### D1 trend / pullback / state
- `d1_ret_2`, `d1_ret_5`, `d1_ret_10`, `d1_ret_20`, `d1_ret_30`, `d1_ret_60`
- `d1_trendvol_5`, `d1_trendvol_10`, `d1_trendvol_20`, `d1_trendvol_60`
- `d1_pullback_10`, `d1_pullback_20`
- `d1_draw_10`, `d1_draw_20`
- `d1_dist_high_20`, `d1_dist_high_60`
- `d1_vol_5`, `d1_vol_20`
- `d1_volz_5`, `d1_volz_20`
- `d1_range_ratio_5_20`

### H4 trend / pullback / state
- `h4_ret_3`, `h4_ret_6`, `h4_ret_12`, `h4_ret_24`, `h4_ret_36`, `h4_ret_48`
- `h4_trendvol_6`, `h4_trendvol_12`, `h4_trendvol_24`, `h4_trendvol_48`
- `h4_vol_6`, `h4_vol_24`
- `h4_rng_6`, `h4_rng_24`
- `h4_draw_6`, `h4_draw_12`, `h4_draw_24`
- `h4_dist_high_24`, `h4_dist_high_48`
- `h4_dist_low_24`, `h4_dist_low_48`

### Flow / order-flow
- `h4_tbuy_3`, `h4_tbuy_6`, `h4_tbuy_12`
- `h4_tbuyz_6`, `h4_tbuyz_24`
- `d1_tbuy_5`, `d1_tbuy_20`
- `d1_tbuyz_5`, `d1_tbuyz_20`

### Bar shape / candle structure
- `close_loc`
- `body_pct`
- `d1_close_loc`
- `d1_body_pct_1`

### Seasonality
- `dow`
- `hour`

### Cross-timeframe / interaction (recovered with high confidence)
Các feature này là exploratory-only. Chúng không đi vào hệ thống cuối cùng. Triển khai dưới đây là **high-confidence reconstruction**, còn appendix CSV là acceptance target cuối cùng.

- `x_trend_align_12_5 = h4_ret_12 * d1_ret_5`
- `x_trend_align_24_10 = h4_ret_24 * d1_ret_10`
- `x_h4_pull_d1trend = (-h4_draw_6) * d1_trendvol_10`
- `x_range_expand = h4_rng_6 / h4_rng_24 - 1`
- `x_contraction = -(x_range_expand)`
- `x_breakout_flow = h4_ret_24 * h4_tbuyz_6`
- `x_flow_trend = d1_ret_20 * h4_tbuyz_6`
- `x_exhaustion = h4_ret_6 * (1 - close_loc)`

Không nên tô hồng: 8 công thức `x_*` này là phần ít chắc nhất của toàn bộ spec. Nếu mục tiêu là rebuild report gốc, hãy dùng `phase1_univariate_measurements.csv` và `phase1_channel_highlights.csv` làm regression gate cho nhóm này.

---

## 6. Phase 1 - data decomposition engine

## 6.1. Matrix dùng để đo tín hiệu
- base measurement timeline: **H4 bars**;
- build H4 features native trên H4;
- build D1 features native trên D1;
- merge D1 -> H4 bằng `merge_asof` strict-lag như Section 4.2.

## 6.2. Forward-return horizons
Dùng đúng 5 horizon:
- `h in {1, 3, 6, 12, 24}` H4 bars.

Forward return định nghĩa tại H4 bar `t`:
- `fwdret_h[t] = open[t+h+1] / open[t+1] - 1`

Tức là return từ **next bar open** sau signal đến open ở `h` bar sau nữa. Cách này giữ cùng execution convention với protocol.

## 6.3. Walk-forward folds của Phase 1
Bốn fold test đúng như sau:
- fold 2020: train < `2020-01-01`, test trong năm 2020
- fold 2021: train < `2021-01-01`, test trong năm 2021
- fold 2022: train < `2022-01-01`, test trong năm 2022
- fold 2023: train < `2023-01-01`, test trong năm 2023

Lưu ý: training có thể dùng cả warmup period để estimate distribution; chỉ **không được trade** trong warmup.

## 6.4. Univariate probe rule
Cho mỗi feature `f` và horizon `h`:
1. ở từng fold, lấy `q80_train = quantile(train[f], 0.8, method='linear')`;
2. selected state trên test là `test[f] >= q80_train`;
3. tính:
   - `test_mean_selected`
   - `test_mean_base`
   - `edge = test_mean_selected - test_mean_base`
   - `net_trade_edge = test_mean_selected - 0.002`
   - `ic = Spearman(test[f], test[fwdret_h])`
   - `freq = mean(selected)`
   - `count = sum(selected)`
4. aggregate qua 4 fold.

## 6.5. Aggregate columns của `phase1_univariate_measurements.csv`
- `feature`
- `h`
- `folds` = số fold hợp lệ, ở đây là `4`
- `mean_test_ic` = mean của 4 `ic`
- `med_test_ic` = median của 4 `ic`
- `mean_test_edge` = mean của 4 `edge`
- `mean_test_net_trade_edge` = mean của 4 `net_trade_edge`
- `weighted_test_mean` = mean của toàn bộ selected-state forward returns khi concatenate cả 4 test fold
- `weighted_test_base` = mean của toàn bộ test forward returns khi concatenate cả 4 test fold
- `weighted_test_edge = weighted_test_mean - weighted_test_base`
- `weighted_test_net_trade_edge = weighted_test_mean - 0.002`
- `mean_freq` = mean của 4 `freq`
- `total_count` = sum của 4 `count`
- `fold_positive_edge_frac` = fraction fold có `edge > 0`
- `channel` = nhóm feature thủ công như trong artifact

## 6.6. Regression target
Implementation đúng phải tạo được bảng rất gần hoặc khớp `appendices/archived_tables/phase1_univariate_measurements.csv`.

Nếu không khớp, nguyên nhân gần như chắc chắn nằm ở một trong 4 chỗ:
- D1->H4 alignment bị lookahead;
- dùng wrong horizon semantics;
- quantile lấy trên test thay vì train;
- công thức exploratory feature `x_*` sai.

---

## 7. Phase 2 - candidate hypotheses (exact)

Sau Phase 1, chốt đúng 4 hypothesis sau:

### H1 - finalist
- Mechanism: `trend strength + long-term near-high`
- Minimal expression: `trendvol_10 >= q0.8 AND dist_high_60 >= q0.6`
- Ý tưởng: medium-horizon daily trend persistence trong regime BTC impulse mạnh.
- Failure mode: sharp reversal từ near-high, năm không trend.
- Falsification: holdout âm hoặc plateau sụp.

### H2
- Mechanism: `momentum + near-high`
- Minimal expression: `ret_20 >= q0.8 AND dist_high_40 >= q0.7`

### H3
- Mechanism: `long-term momentum regime only`
- Minimal expression: `ret_60 >= q0.6`

### H4
- Mechanism: `flow breakout pulse`
- Minimal expression: breakout-flow interaction high

Không thêm hypothesis khác.

---

## 8. Phase 3-4 - D1 family search và parameter search

## 8.1. Backtest domain cho candidate families
Toàn bộ family search chạy trên **D1 bars**, không dùng H4 timing overlay ở production candidate.

### Signal / execution rule chuẩn cho mọi candidate family
- feature được tính tại close D1 ngày `t`;
- signal tại close ngày `t`;
- fill tại open ngày `t+1`;
- position size = `1.0` hoặc `0.0`;
- annual threshold refit tại mỗi `Jan-01` từ toàn bộ D1 data hoàn tất đến `Dec-31` năm trước;
- exit khi **bất kỳ** điều kiện trong family không còn đúng.

## 8.2. Search spaces (exact)

### `single_ret` - 9 config
- feature: `ret_10`, `ret_20`, `ret_60`
- quantile: `0.6`, `0.7`, `0.8`
- signal: `ret_L >= q_train`

### `single_trendvol` - 9 config
- feature: `trendvol_5`, `trendvol_10`, `trendvol_20`
- quantile: `0.6`, `0.7`, `0.8`
- signal: `trendvol_L >= q_train`

### `single_nearhigh` - 12 config
- feature: `dist_high_20`, `dist_high_40`, `dist_high_60`, `dist_high_90`
- quantile: `0.5`, `0.6`, `0.7`
- signal: `dist_high_L >= q_train`

### `ret_nearhigh` - 108 config
- ret feature: `ret_10`, `ret_20`, `ret_60`
- near-high feature: `dist_high_20`, `dist_high_40`, `dist_high_60`, `dist_high_90`
- ret quantile: `0.6`, `0.7`, `0.8`
- near-high quantile: `0.5`, `0.6`, `0.7`
- signal: `ret_L >= q1_train AND dist_high_M >= q2_train`

### `trendvol_nearhigh` - 108 config
- trend feature: `trendvol_5`, `trendvol_10`, `trendvol_20`
- near-high feature: `dist_high_20`, `dist_high_40`, `dist_high_60`, `dist_high_90`
- trend quantile: `0.6`, `0.7`, `0.8`
- near-high quantile: `0.5`, `0.6`, `0.7`
- signal: `trendvol_L >= q1_train AND dist_high_M >= q2_train`

Tổng cộng đúng `246` config, khớp `family_search_results.csv`.

## 8.3. Evaluation columns của `family_search_results.csv`
Cho mỗi config, tính trên aggregate WF 2020-2023:
- `sharpe`
- `cagr`
- `mdd`
- `trade_entries`
- `exposure`
- `wf_pos_windows` = số test year có total return > 0
- `wf_windows` = 4
- `wf_min_window_return` = min total return trong 4 test year
- `family`

## 8.4. Family thắng
Family thắng là:
- `trendvol_nearhigh`
- config thắng coarse: `('trendvol_10', 'dist_high_60'), quantiles=(0.8, 0.6)`

Số liệu golden-master:
- `sharpe = 1.695960`
- `cagr = 0.533608`
- `mdd = -0.159009`
- `trade_entries = 50`
- `wf_pos_windows = 4`
- `wf_min_window_return = 0.066176`

Khớp `candidate_coarse_search_trendvol_nearhigh.csv`.

## 8.5. Three-filter extension search
Artifact chỉ còn lại dòng mô tả: đã test `540` three-filter extensions và **không** có extension nào thắng hệ thống đôi tối giản sau khi phạt complexity.

Vì danh sách đầy đủ 540 config **không được serialize trong artifact còn lại**, phần này là phần duy nhất của pipeline search mà spec này **không thể chứng minh 1:1 tuyệt đối**.

Normative workaround:
- không cần dùng kết quả 540 config để chọn frozen candidate;
- frozen candidate đã được xác định dứt điểm bởi coarse search + plateau + ablation;
- nếu muốn rebuild sát nhất với ý định gốc, hãy thêm tối đa 5 third-filter exploratory feature từ non-core channels và xác minh rằng không config nào vượt `trendvol_10 + dist_high_60` một cách đủ sạch trên unseen WF. Nhưng đừng giả vờ rằng exact 540-combo list còn khôi phục được. Không còn.

---

## 9. Phase 5 - frozen final system (exact)

## 9.1. Rule set đóng băng
- timeframe: `D1`
- feature 1: `trendvol_10`
- feature 2: `dist_high_60`
- thresholding: annual expanding-window quantile refit
- threshold 1: `q80(trendvol_10)`
- threshold 2: `q60(dist_high_60)`
- entry: tại close D1 ngày `t`, nếu cả hai điều kiện cùng đúng thì desired position cho open ngày `t+1` = 1
- exit: desired position cho open ngày `t+1` = 0 nếu **một trong hai** điều kiện fail tại close ngày `t`
- sizing: 100% long hoặc 0% cash
- no leverage, no stop, no trailing stop, no regime switch, no H4 overlay

## 9.2. Threshold calibration rule (exact)
Cho calendar year `Y`:
- train set = mọi D1 row có `open_dt < Y-01-01 00:00:00 UTC`
- `thr1_Y = quantile(train.trendvol_10.dropna(), 0.8, linear)`
- `thr2_Y = quantile(train.dist_high_60.dropna(), 0.6, linear)`

## 9.3. Canonical threshold values
Giá trị exact nằm ở `appendices/generated/frozen_system_thresholds.csv`.

Các threshold quan trọng được dùng trong holdout:
- 2024: `(1.0641089857506871, -0.1100896373818464)`
- 2025: `(1.0867015373916644, -0.09813163795486249)`
- 2026: `(1.0772207904566133, -0.09384142723007918)`

## 9.4. Canonical signal path
`appendices/generated/frozen_system_signal_path.csv` là path kiểm định chuẩn, gồm:
- D1 OHLC
- `trendvol_10`
- `dist_high_60`
- threshold theo năm
- `signal_close`
- `position_next_open`
- `entry_at_open`
- `exit_at_next_open`

## 9.5. Canonical trade list
Trade dates và bar counts phải khớp exact với:
- `appendices/archived_tables/trades_full.csv`
- `appendices/archived_tables/trades_holdout.csv`

Ngày vào/ra và `bars` là gate quan trọng nhất. Nếu không khớp, final system của bạn sai.

---

## 10. Backtest mechanics cho frozen system

## 10.1. Position semantics
- `signal_close[t]` được tính tại D1 close của ngày `t`
- `position_next_open[t+1] = signal_close[t]`
- warmup override: mọi `position_next_open` trước `2019-01-01` phải ép về `0`

## 10.2. Daily factor semantics
Cách factorization đơn giản nhất, cũng là cách tái dựng được trade dates chính xác:
- nếu flat ở open `t`: factor `= 1`
- nếu long từ open `t` đến open `t+1`: gross factor `= open[t+1] / open[t]`
- nếu entry tại open `t`: divide factor ngày đó cho `1.001`
- nếu exit tại open `t+1`: multiply factor của ngày `t` thêm `0.999`

Lưu ý: trade dates / bars khớp exact với archive; nhưng implementation metric theo slice trong artifact có chênh vài bp so với factorization tối giản này. Vì thế:
- **trade path là gate exact**
- **report metric tables là gate final**

## 10.3. Trade count conventions
- `trade_entries` / `Trades` trong aggregate tables = số entry event
- bảng yearly regime có một quirk: trade đang mở từ cuối năm trước có thể làm yearly trade count nhìn như lớn hơn entry count thuần. Hãy dùng `regime_yearly_metrics.csv` làm chuẩn báo cáo.

---

## 11. Metrics và validation tables

## 11.1. Metric definitions
Dùng các metric sau trên daily return series:
- `Total return = equity_end - 1`
- `CAGR = equity_end ** (365.25 / n_days) - 1`
- `MDD = min(equity / cummax(equity) - 1)`
- `Sharpe = sqrt(365.25) * mean(daily_ret) / std(daily_ret)`
- `Exposure = mean(position)` trên bar domain tương ứng

## 11.2. Golden-master results phải ra
Các bảng chuẩn nằm sẵn trong appendix. Những con số then chốt:

### WF aggregate 2020-2023
- Sharpe `1.735`
- CAGR `56.2%`
- MDD `-13.8%`
- Trades `51`
- Exposure `18.4%`

### Holdout 2024-01-01 đến 2026-02-20
- Sharpe `0.207`
- CAGR `2.2%`
- MDD `-26.9%`
- Trades `30`
- Exposure `17.8%`

### Full sample descriptive 2019-01-01 đến 2026-02-20
- Sharpe `1.291`
- CAGR `38.3%`
- MDD `-31.4%`
- Trades `93`
- Exposure `18.0%`

Nguồn chuẩn: `regime_yearly_metrics.csv`, `cost_sensitivity.csv`, `ablation_results.csv`, `benchmark_comparison_summary.csv`.

---

## 12. Plateau test (exact)

## 12.1. Axes
Frozen center:
- `L1 = 10`
- `q1 = 0.80`
- `L2 = 60`
- `q2 = 0.60`

Perturbation grid one-at-a-time:
- `L1`: `8, 9, 10, 11, 12`
- `q1`: `0.64, 0.72, 0.80, 0.88, 0.95`  
  (`0.96` được clip xuống `0.95`)
- `L2`: `48, 54, 60, 66, 72`
- `q2`: `0.48, 0.54, 0.60, 0.66, 0.72`

## 12.2. Evaluation
Mỗi case giữ nguyên 3 tham số còn lại, chạy lại annual refit + WF + holdout, rồi xuất bảng `plateau_test.csv`.

Plateau verdict theo artifact:
- acceptable, not perfect
- axis sắc nhất là `q1`
- lookback axes rộng hơn
- `q2` tương đối rộng

---

## 13. Ablation (exact)

Chạy đúng 3 variant:
- `Full system`
- `Ablate near-high (trendvol only)`
- `Ablate trend strength (near-high only)`

Implementation:
- trendvol only: giữ annual `q80(trendvol_10)` và signal = `trendvol_10 >= q1`
- near-high only: giữ annual `q60(dist_high_60)` và signal = `dist_high_60 >= q2`

Golden-master nằm ở `ablation_results.csv`.

Key conclusion cần ra lại:
- trên development WF, pair tốt hơn từng module đơn lẻ về Sharpe / drawdown trade-off;
- trên holdout, near-high filter **không giúp**; đó là warning out-of-sample thật, không được bẻ chữ.

---

## 14. Cost sensitivity (exact)

Chạy 3 mức round-trip:
- `0 bps`
- `20 bps`
- `50 bps`

Tức per-side:
- `0.0`
- `0.001`
- `0.0025`

Xuất đúng `cost_sensitivity.csv`.

Expected interpretation:
- development vẫn sống ở `50 bps`
- holdout **không** sống ở `50 bps`
- đây là lý do hệ thống chỉ competitive, không superior.

---

## 15. Bootstrap robustness

## 15.1. Slices
Bootstrap trên 3 slice:
- OOS: `2020-01-01` -> `2026-02-20`
- Holdout: `2024-01-01` -> `2026-02-20`
- Full descriptive: `2019-01-01` -> `2026-02-20`

## 15.2. Method
Dùng **circular block bootstrap** trên daily return series:
1. với series dài `N`, chọn block start uniform trong `[0, N-1]`;
2. lấy đúng `B` return liên tiếp, wrap modulo `N`;
3. lặp lại cho tới khi đủ `N` return, rồi truncate về `N`;
4. compute Sharpe, CAGR, MDD cho path synthetic;
5. lặp `2000` resamples cho mỗi `B in {5,10,20,40}`.

## 15.3. Seed
Artifact còn lại **không serialize RNG seed**. Vì vậy summary bootstrap exact đến từng chữ số thập phân không thể chứng minh nếu chỉ có artifact hiện tại.

Normative handling:
- chọn một fixed seed, ghi cứng trong code;
- so sánh summary output với:
  - `bootstrap_oos_summary.csv`
  - `bootstrap_holdout_summary.csv`
  - `bootstrap_full_summary.csv`
- sai khác nhỏ do seed được phép; nhưng shape phải giống: OOS mạnh, holdout yếu rõ.

---

## 16. Trade-distribution analysis

Từ trade list của frozen system, tính:
- `Trades`
- `Win rate`
- `Avg trade`
- `Avg win`
- `Avg loss`
- `Profit factor`
- `Median holding days`
- `Top-5 winners share of gross profits`
- `Churn <=2 days`

Golden-master values đã được reflect trong report, còn raw trade lists nằm ở appendix.

Expected conclusion:
- OOS 2020-2026: PF khoảng `3.0`, không bị 1-2 trade thống trị quá đáng.
- Holdout: profit concentration của top 5 winners khoảng `91.6%`, nghĩa là fragility recent regime cao.

---

## 17. Benchmark comparison và verdict

## 17.1. Khi nào mới được đọc benchmark
Chỉ sau khi:
- frozen candidate đã chốt;
- holdout result đã ghi xong.

Benchmark input lấy từ Appendix A trong prompt, không có rule/path-level returns.

## 17.2. Comparison table
Dựng lại `benchmark_comparison_summary.csv` với:
- candidate full-sample descriptive metrics
- benchmark A/B/C summary stats

## 17.3. Verdict logic (exact)
- nếu fail hard criteria -> `NO ROBUST IMPROVEMENT`
- nếu pass hard criteria **và** có paired bootstrap benchmark path `P(delta > 0) >= 0.90` **và** không có regime underperformance material -> `SUPERIOR`
- còn lại -> `COMPETITIVE`

## 17.4. Verdict ở case này
Verdict cuối phải là:
- **COMPETITIVE**

Lý do:
- pass hard criteria;
- walk-forward dương tổng thể;
- holdout dương;
- nhưng holdout yếu;
- paired bootstrap benchmark **không thực hiện được** vì benchmark chỉ có summary stats, không có implementation/path;
- do đó không đủ cơ sở gọi `SUPERIOR`.

---

## 18. Implementation blueprint gợi ý

Một repo đủ sạch để rebuild:

```text
project/
  README.md
  data/                      # unpacked from data.zip
  src/
    config.py
    io.py
    features.py
    align.py
    phase1_measure.py
    candidate_search.py
    frozen_system.py
    backtest.py
    metrics.py
    bootstrap.py
    reporting.py
    verdict.py
  outputs/
  run_research.py
  run_frozen_system.py
  tests/
```

### 18.1. Function-level contract tối thiểu
- `load_raw(zip_path) -> (d1_df, h4_df)`
- `build_d1_features(d1_df) -> d1_feat_df`
- `build_h4_features(h4_df) -> h4_feat_df`
- `align_d1_to_h4(h4_feat_df, d1_feat_df) -> h4_measurement_matrix`
- `measure_phase1(matrix) -> phase1_univariate_measurements`
- `run_family_search(d1_feat_df) -> family_search_results`
- `run_winning_family_coarse_search(d1_feat_df) -> candidate_coarse_search_trendvol_nearhigh`
- `build_frozen_system_signal(d1_feat_df) -> signal_path`
- `backtest_d1_signal(signal_path, cost_per_side) -> equity_path, trade_list`
- `run_plateau(...) -> plateau_test`
- `run_ablation(...) -> ablation_results`
- `run_cost_sensitivity(...) -> cost_sensitivity`
- `run_bootstrap(...) -> bootstrap_summary_tables`
- `compare_benchmarks(...) -> benchmark_comparison_summary`
- `decide_verdict(...) -> verdict`

---

## 19. Acceptance checklist cho kỹ sư

## 19.1. Final system - gate cứng
Bắt buộc khớp:
- `frozen_system_thresholds.csv`
- `trades_full.csv` ở `entry_date`, `exit_date`, `bars`
- `trades_holdout.csv` ở `entry_date`, `exit_date`, `bars`

Nếu fail một trong ba, dừng. Frozen system sai.

## 19.2. Search tables - gate cứng
Bắt buộc khớp rất sát:
- `family_search_results.csv`
- `candidate_coarse_search_trendvol_nearhigh.csv`
- `plateau_test.csv`
- `ablation_results.csv`
- `cost_sensitivity.csv`
- `regime_yearly_metrics.csv`

## 19.3. Phase 1 - gate mạnh nhưng có ngoại lệ
Mục tiêu là khớp:
- `phase1_univariate_measurements.csv`
- `phase1_channel_highlights.csv`

Nếu lệch đáng kể chỉ ở `x_*` features nhưng mọi phần downstream vẫn khớp winner/search/plateau/ablation/final system, có thể chấp nhận; khi đó phải note rõ là exploratory interaction formulas là phần không còn serialize exact.

## 19.4. Bootstrap - gate mềm
Vì seed không còn, bootstrap summary không cần byte-identical; nhưng:
- ranking across slices phải giống;
- OOS phải mạnh;
- holdout phải yếu quanh coin-flip;
- hình dạng summary phải gần các bảng archived.

---

## 20. Bottom line cho người implement

Đừng làm sai trọng tâm.

Phần thật sự quyết định kết quả cuối chỉ có bấy nhiêu:
- Phase 1 đo trên H4, strict anti-lookahead;
- Phase 2 chốt đúng 4 hypothesis;
- Phase 3-4 chạy đúng 246 family configs trên D1 với annual expanding quantile refit;
- family thắng là `trendvol_nearhigh`;
- frozen system là `trendvol_10 >= q80` và `dist_high_60 >= q60`;
- holdout yếu nhưng vẫn dương;
- benchmark không paired được;
- verdict = `COMPETITIVE`.

Mọi thứ còn lại là support structure.

Nếu kỹ sư build đúng spec này và dùng appendix làm regression harness, họ sẽ tái dựng được hệ thống cuối cùng gần như nguyên trạng và tái tạo được toàn bộ quá trình nghiên cứu ở mức đủ audit, đủ reproduce, đủ thay thế code gốc.
