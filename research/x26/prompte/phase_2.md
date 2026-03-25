PREPEND PROMPT 0 tại: /var/www/trading-bots/btc-spot-dev/research/prompte/phase_0.md
======================================================================

Bạn đang ở PHASE 2: FLAT-PERIOD RAW EDA.

Đầu vào:
- 01_audit_state_map.md
- state_classification.csv

Mục tiêu:
Characterize return và price behavior trong VTREND FLAT periods.
Chỉ mô tả. Không interpret. Không suggest strategy.

Bước thực hiện:

1. FLAT-period return distribution (H4)
- Compute H4 log-returns cho FLAT bars only
- Distribution statistics: mean, std, skew, kurtosis, Jarque-Bera test
- Histogram + Q-Q plot vs Normal
- Compare với IN_TRADE return distribution (overlay)
- Compare với FULL-sample return distribution

2. Autocorrelation structure (FLAT bars only)
- ACF lag 1–50 cho returns
- ACF lag 1–50 cho absolute returns (volatility proxy)
- PACF lag 1–20 cho returns
- Compare mỗi cái với FULL-sample ACF
- Mark bất kỳ lags nào FLAT-period ACF là statistically significant
- Variance ratio test (Lo-MacKinlay) ở holding periods 2, 5, 10, 20 bars
- Hurst exponent estimate (R/S method hoặc DFA)

3. Volatility structure (FLAT bars only)
- Realized volatility: rolling 20-bar std of returns
- Compare FLAT-period vol vs IN_TRADE vol vs FULL-sample vol
- Vol clustering: FLAT-period |returns| có GARCH-like persistence không?
  (ACF of |r| lag 1–20)
- Vol-of-vol: rolling vol của realized vol
- Volatility ở đầu flat period vs cuối flat period: có systematic pattern không?
  (Normalized: relative position within each flat period)

4. Flat-period internal structure
- Cho MỖI flat period (gap giữa hai trades):
  - Total return start-to-end
  - Max drawdown within period
  - Max runup within period
  - Duration (bars)
  - Volatility (std of returns within period)
- Scatter plots:
  - flat_duration vs flat_total_return
  - flat_duration vs next_trade_return (causality OK: flat ends before next trade)
  - flat_total_return vs next_trade_return
  - flat_volatility vs next_trade_return
- Statistical tests cho mỗi relationship (Spearman ρ, p-value)

5. Transition dynamics
- Average return profile trong 20 bars TRƯỚC new trade entry
  (từ flat → trade, aligned at entry bar)
- Average return profile trong 20 bars SAU trade exit
  (từ trade → flat, aligned at exit bar)
- Overlay volume và volatility trong cùng windows
- Split by: winning trades vs losing trades
- Mô tả cái nhìn thấy. KHÔNG interpret.

6. Cross-timeframe check
- Repeat items 1–2 ở H1 resolution (cho FLAT periods only, mapped from H4 states)
- Brief D1 check: daily returns during FLAT periods
- Có patterns visible ở một timeframe mà không ở timeframe khác không?

7. Calendar effects (H1 data, FLAT periods only)
- Mean return by hour of day (24 bins)
- Mean |return| by hour of day (volatility proxy)
- Mean return by day of week (7 bins)
- Mean |return| by day of week
- Statistical test cho significant deviation from uniformity
  (chi-squared hoặc Kruskal-Wallis)
- Nếu có significant effect: kiểm tra stability bằng cách split data thành 2 halves

Deliverables bắt buộc:
- research/beyond_trend_lab/02_flat_period_eda.md
- research/beyond_trend_lab/code/phase2_flat_eda.py
- Figures: Fig04 trở đi (đánh số tiếp từ Phase 1)
  Bắt buộc tối thiểu:
  - Fig04: FLAT return histogram + Q-Q plot
  - Fig05: ACF comparison (FLAT vs FULL)
  - Fig06: Variance ratio + Hurst
  - Fig07: Flat-period vol vs position
  - Fig08: Scatter matrix (flat characteristics vs next trade)
  - Fig09: Transition dynamics (pre-entry, post-exit)
  - Fig10: Calendar effects heatmap (hour × day)
- Tables: Tbl03 trở đi
  Bắt buộc tối thiểu:
  - Tbl03: FLAT return distribution statistics
  - Tbl04: Variance ratio tests
  - Tbl05: Flat-period predictive relationships
  - Tbl06: Calendar effect tests

Cấm:
- Không nói "this suggests we should..."
- Không đề xuất trading rule hay indicator
- Chỉ mô tả statistical properties
- Nếu thấy pattern: mô tả shape, magnitude, significance — không hơn
