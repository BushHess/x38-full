======================================================================
PHASE 1: DATA AUDIT
======================================================================

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x27/prompte/phase_0.md

Đầu vào:
- Dữ liệu BTC spot tại /var/www/trading-bots/btc-spot-dev/data/:
  - btcusdt_15m.csv (15-minute bars)
  - btcusdt_1h.csv  (1-hour bars)
  - btcusdt_4h.csv  (4-hour bars, PRIMARY)
  - btcusdt_1d.csv  (daily bars, CONTEXT)

Mục tiêu:
Load dữ liệu, verify chất lượng, ghi nhận cấu trúc cơ bản.
Phase này chỉ KIỂM TRA — không phân tích, không vẽ chart, không interpret.

Lưu tất cả artifacts vào: /var/www/trading-bots/btc-spot-dev/research/x27/

======================================================================
Bước thực hiện:
======================================================================

1. Load & schema
- Đọc từng file CSV từ thư mục data/
- Liệt kê tất cả columns, dtypes
- Primary: btcusdt_4h.csv (H4), Context: btcusdt_1d.csv (D1)
- Bổ sung: btcusdt_1h.csv (H1), btcusdt_15m.csv (15m) nếu cần
- Count rows mỗi file
- Date range: start date, end date, total duration
- Verify: không trùng timestamp, không gaps bất thường (>3 bars liên tiếp)

2. Data quality
- Missing values: columns nào, count, % tổng
- Zero volume bars: count, phân bố theo năm
- Price integrity: close > high? close < low? open <= 0?
- Extreme moves: |log_return| > 15% trong 1 H4 bar? Khi nào?
- taker_buy_base_vol: range, missing count, mean ratio vs total volume

3. Basic descriptive statistics
- H4: bảng thống kê (mean, std, min, Q25, Q50, Q75, max) cho OHLCV
- D1: tương tự
- Price range: lowest close, highest close, max/min ratio
- Bars per day: mean, std (H4 should be ~6)

4. Time coverage
- Year-by-year bar count (H4 và D1)
- Gaps > 12h: list dates and durations
- Có period nào data sparse hoặc suspicious không?

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x27/):
======================================================================
- 01_data_audit.md
- tables/Tbl01_h4_descriptive.csv
- tables/Tbl02_d1_descriptive.csv
- tables/Tbl03_data_quality.csv
- code/phase1_audit.py
- manifest.json (khởi tạo)

======================================================================
Cấm:
======================================================================
- Không tính returns, correlations, hay bất kỳ derived metric nào
- Không vẽ price chart
- Không nói gì về trading, trends, hay strategy
- Chỉ audit data quality và structure
