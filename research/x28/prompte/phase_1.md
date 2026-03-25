======================================================================
PHASE 1: DATA AUDIT
======================================================================

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x28/prompte/phase_0.md

Đầu vào:
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_15m.csv
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_1h.csv
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_4h.csv
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_1d.csv

Mục tiêu:
Verify dữ liệu đủ chất lượng để phân tích. KHÔNG phân tích giá.

======================================================================
Tasks:
======================================================================

1. SCHEMA CHECK
- Load mỗi file, verify columns:
  symbol, interval, open_time, close_time, open, high, low, close,
  volume, quote_volume, num_trades, taker_buy_base_vol, taker_buy_quote_vol
- Verify dtypes (numeric), row count, date range

2. DATA QUALITY
- Missing values per column
- Duplicate timestamps
- Gaps > expected interval (>4h cho H4, >1d cho D1, etc.)
- Zero-volume bars
- Price integrity: close ≤ high, close ≥ low, open trong [low, high]
- Extreme moves: |log_return| > 0.20 (flag, verify vs known events)

3. DESCRIPTIVE STATISTICS
- Per timeframe: count, mean, std, min, 25%, 50%, 75%, max cho OHLCV
- taker_buy_base_vol: mean ratio (taker_buy / volume), range

4. TIME COVERAGE
- Year-by-year bar count cho H4 và D1
- Identify any gaps > 12 hours (H4) hoặc > 2 days (D1)

======================================================================
Deliverables:
======================================================================
- 01_data_audit.md
- code/phase1_audit.py
- tables/Tbl01_h4_descriptive.csv
- tables/Tbl02_d1_descriptive.csv
- tables/Tbl03_data_quality.csv
- manifest.json (khởi tạo)

======================================================================
Cấm:
======================================================================
- KHÔNG tính returns, correlations, distributions
- KHÔNG vẽ price chart
- KHÔNG interpret dữ liệu
- Chỉ verify chất lượng
