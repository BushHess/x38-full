======================================================================
PHASE 2: BTC H4 PRICE BEHAVIOR EDA
======================================================================

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x27/prompte/phase_0.md
  Đọc deliverables Phase 1:
  - /var/www/trading-bots/btc-spot-dev/research/x27/01_data_audit.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl01_h4_descriptive.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl02_d1_descriptive.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl03_data_quality.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/ (đã audit Phase 1)

Mục tiêu:
Characterize statistical properties của BTC H4 price.
Hiểu BTC "hành xử" thế nào trước khi nghĩ tới bất kỳ trading system nào.

CHỈ MÔ TẢ. KHÔNG INTERPRET. KHÔNG SUGGEST STRATEGY.

======================================================================
Bước thực hiện:
======================================================================

1. RETURN DISTRIBUTION (H4)
- Compute log-returns: r_t = ln(close_t / close_{t-1})
- Distribution: mean, std, skew, kurtosis
- Jarque-Bera test cho normality
- Histogram + Q-Q plot vs Normal (Fig01)
- Tail analysis: % returns beyond ±2σ, ±3σ (so với Normal expected)
- Có asymmetry giữa up-tail và down-tail không?

2. SERIAL DEPENDENCE — THE CORE QUESTION
- ACF of returns: lag 1-100 (Fig02)
  Mark significance bands. Đánh dấu lags nào significant.
- ACF of |returns|: lag 1-100 (Fig03)
  (volatility clustering proxy)
- PACF of returns: lag 1-30 (Fig04)
- Variance ratio test (Lo-MacKinlay):
  holding periods k = 2, 5, 10, 20, 40, 60 bars (Tbl04)
  VR > 1 = persistence, VR < 1 = mean-reversion
- Hurst exponent (R/S method): (Tbl05)
  overall + rolling 500-bar windows (Fig05)
  H > 0.5 = persistent, H = 0.5 = random walk, H < 0.5 = mean-reverting

Ghi nhận: Ở SCALE NÀO BTC persistent? Ở scale nào random? Ở scale nào mean-reverting?

3. TREND ANATOMY
- Định nghĩa objective: một "trend" = chuỗi bars liên tiếp mà
  cumulative return > X% (với X = 10%, 20%, 30%, 50%)
  HOẶC price liên tục > đường hồi quy tuyến tính qua N bars gần nhất
- Cho mỗi threshold/method:
  - Có bao nhiêu trends trong data?
  - Duration distribution (bars): mean, median, Q25, Q75 (Tbl06)
  - Magnitude distribution (%): mean, median (Tbl06)
  - Tốc độ: return/bar trung bình
  - Trends bắt đầu thế nào? (price pattern trong 20 bars trước)
  - Trends kết thúc thế nào? (price pattern trong 20 bars sau peak)
- Average trend profile plot: aligned at start, aligned at end (Fig06)

4. VOLATILITY STRUCTURE
- Realized volatility: rolling 20-bar std of returns
- Time series plot (Fig07)
- ACF of realized vol: lag 1-50
- Vol-return correlation: scatter plot vol_t vs r_{t+1..t+20} (Fig08)
- Vol regimes: split into high/low vol (above/below median)
  - Return characteristics in each regime
  - Trend frequency in each regime

5. VOLUME STRUCTURE
- Volume distribution (H4): histogram (Fig09)
- Volume trend: is average volume changing over time?
- Volume-return relationship:
  - Contemporaneous: cor(volume_t, |r_t|)
  - Leading: cor(volume_t, |r_{t+1}|), ..., lag 1-10
- Taker buy ratio: taker_buy_vol / total_vol
  - Distribution
  - Is it informative? cor(TBR_t, r_{t+1..t+k}) for k = 1, 5, 10, 20
- Volume at trend starts vs trend ends (from trend anatomy)

6. D1 CONTEXT
- Same analysis items 1-2 ở D1 resolution (brief)
- D1 regime identification: có cách nào tự nhiên chia D1 thành regimes?
  (e.g., above/below long-term average, vol regime, etc.)
- D1 regime vs H4 trend frequency: trends xảy ra nhiều hơn ở regime nào?

7. CROSS-TIMEFRAME
- H4 returns conditioned on D1 state
- Có information ở D1 mà H4 không thấy được?

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x27/):
======================================================================
- 02_price_behavior_eda.md
- code/phase2_eda.py
- figures/Fig01–Fig09+ (tối thiểu 9, thêm nếu cần)
- tables/Tbl04–Tbl06+ (tối thiểu 3, thêm nếu cần)
- Observation log: Obs01–Obs##

======================================================================
Cấm:
======================================================================
- Không dùng từ "indicator" hay nêu tên indicator nào
- Không nói "ta nên dùng X để trade"
- Không đề xuất entry/exit rule
- Chỉ mô tả PROPERTIES: shape, magnitude, significance, stability
- Nếu thấy pattern: ghi "pattern observed at lag X with magnitude Y,
  p-value Z" — không hơn

======================================================================
Verify prior hypotheses:
======================================================================
Dựa trên EDA, ghi nhận status cho mỗi H_prior:
- H_prior_1 (trend persistence): CONFIRMED / REFUTED / PARTIAL
- H_prior_2 (cross-scale redundancy): check qua variance ratio multi-scale
- H_prior_5 (volume info ≈ 0): check qua volume-return correlations
- H_prior_6 (D1 regime useful): check qua D1 conditioning
Ghi nhận rõ ràng ở cuối report. Không cần verify tất cả — chỉ những cái
EDA phase này có thể address.
