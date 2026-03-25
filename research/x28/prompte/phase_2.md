======================================================================
PHASE 2: BTC H4 PRICE BEHAVIOR EDA
======================================================================

Điều kiện: Phase 1 hoàn thành, dữ liệu đạt chất lượng.

Bước 0 — CONTEXT LOADING (bắt buộc):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x28/prompte/phase_0.md
  Đọc deliverables Phase 1:
  - /var/www/trading-bots/btc-spot-dev/research/x28/01_data_audit.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/

Mục tiêu:
Mô tả statistical properties của BTC H4.
CHỈ MÔ TẢ — không interpret, không đề xuất strategy.
Để Phase 3 và 4 quyết định cái gì exploitable.

======================================================================
PHẦN 1: RETURN DISTRIBUTION
======================================================================
- Log returns: mean, std, skew, kurtosis
- Jarque-Bera normality test
- Tail behavior: empirical vs normal tails
- QQ plot
- Fig01: return distribution histogram + normal overlay

======================================================================
PHẦN 2: SERIAL DEPENDENCE (CORE)
======================================================================
- ACF returns: lag 1-100, mark significant lags
  Fig02: ACF plot
- ACF |returns|: lag 1-100 (volatility clustering)
  Fig03: ACF absolute returns
- PACF returns: lag 1-20
  Fig04: PACF plot
- Variance ratio (Lo-MacKinlay): k = 2, 5, 10, 20, 40, 60, 80, 100, 120
  Test: VR > 1 (persistence) vs VR ≈ 1 (random walk)
  Tbl04: VR values + p-values
- Hurst exponent (R/S method):
  - Full sample + rolling (window = 500 bars)
  Fig05: rolling Hurst

Mô tả observation (Obs##) cho mỗi finding.

======================================================================
PHẦN 3: TREND ANATOMY
======================================================================
Định nghĩa "trend" KHÁCH QUAN:
- Threshold: cumulative return ≥ 10% (primary), ≥ 20% (secondary)
- Thuật toán: tìm tất cả up-moves vượt threshold

Đo:
- Count, mean duration (bars), mean magnitude (%)
- Temporal distribution (histogram theo năm)
- Average profile: 20 bars trước, trong trend, 20 bars sau
  (giá, volume, volatility)
- Tbl06: trend anatomy summary
- Fig06: average trend profile (price + volume overlay)

======================================================================
PHẦN 4: VOLATILITY STRUCTURE
======================================================================
- Rolling realized vol (20-bar, 100-bar)
- Vol ACF structure (lag 1-100)
- Vol-return correlation (contemporaneous + lagged)
- Vol regimes: define 3 regimes (low/mid/high), count transitions
- Tbl07: vol regimes (bars, mean vol, mean return per regime)
- Fig07: vol timeseries
- Fig08: vol vs next-period return scatter

======================================================================
PHẦN 5: VOLUME STRUCTURE
======================================================================
- Volume distribution, trend
- Taker-buy ratio: mean, stability, info content
- Volume-return correlation:
  - Contemporaneous: volume × |return|
  - Leading: volume_t → return_{t+k} (k = 1, 5, 10, 20)
  - At trend events: volume before/during/after trends
- Tbl08: volume correlation table
- Fig09: volume distribution + taker-buy ratio

======================================================================
PHẦN 6: D1 CONTEXT
======================================================================
- D1 return distribution (brief)
- D1 regime identification:
  - close > SMA(200)
  - close > EMA(21)
  - close > EMA(50)
  - Return differential per regime (above vs below)
  - Statistical test (Welch t, Mann-Whitney)
- Tbl09: regime return differentials (all 3 variants)
- Cross-timeframe: H4 returns conditioned on D1 regime
- Tbl10: H4 stats conditioned on D1 regime

======================================================================
PHẦN 7: OBSERVATION SUMMARY
======================================================================
- Tổng hợp TẤT CẢ Obs## đã tạo
- Xếp hạng theo effect size
- Mark: "likely exploitable" / "not exploitable" / "unclear"
  (dựa trên effect size + significance, KHÔNG dựa trên narrative)

======================================================================
Deliverables:
======================================================================
- 02_price_behavior_eda.md
- code/phase2_eda.py
- figures/Fig01-Fig09 (tối thiểu 9 figures)
- tables/Tbl04-Tbl10 (tối thiểu 7 tables)
- Observation log: Obs## cho mỗi finding
- manifest.json cập nhật

======================================================================
Cấm:
======================================================================
- KHÔNG nêu tên indicator (RSI, MACD, Bollinger, etc.)
- KHÔNG đề xuất "dùng X để trade"
- KHÔNG nói "điều này gợi ý strategy Y"
- CHỈ mô tả statistical properties
- Kết luận "BTC H4 gần random walk" là hoàn toàn hợp lệ
