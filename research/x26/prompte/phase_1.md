PREPEND PROMPT 0 tại: /var/www/trading-bots/btc-spot-dev/research/prompte/phase_0.md
======================================================================

Bạn đang ở PHASE 1: DATA AUDIT & VTREND STATE MAP.

Mục tiêu:
(a) Verify data (brief — tham chiếu entry_filter_lab audit cho chi tiết)
(b) Implement VTREND E5+EMA21D1 và classify MỌI H4 bar thành states
(c) Characterize temporal structure của VTREND states

Bước thực hiện:

1. Data load & quick verify
- Load bars_btcusdt_h1_4h_1d.csv
- Confirm: H4 = 18,662 bars, D1 = 3,110, H1 = 74,651
- Reference entry_filter_lab/00_data_audit.md cho full audit (không lặp lại)
- Flag bất kỳ discrepancy nào

2. Implement VTREND state classifier
- Reproduce VTREND E5+EMA21D1 trades trên H4 data:
  - EMA fast=30, slow=120 on H4 close
  - VDO fast=12, slow=28, threshold=0.0
  - D1 close > D1 EMA(21) regime filter
  - ATR trailing stop (trail_mult=3.0) + EMA cross-down exit
  - Cost: 50 bps RT
- Verify: phải tạo ~201 trades, Sharpe ~1.19, win rate ~38.8%
- Classify MỌI H4 bar:
  - IN_TRADE: bar nằm trong active trade (entry bar through exit bar)
  - FLAT: bar không thuộc trade nào
- Save state classification CSV (open_time, state, trade_id nếu applicable)

3. Temporal statistics
- Tổng bars IN_TRADE vs FLAT (count, percentage)
- Distribution of FLAT period durations (bars và hours/days):
  - Mean, median, min, max, Q25, Q75
  - Histogram
- Distribution of IN_TRADE durations (verify against known: median 29 bars)
- Time series plot: price + state overlay (dùng colored background)
- Year-by-year breakdown: fraction of time in mỗi state

4. Transition analysis
- Count: trade → flat → trade sequences
- Gap distribution: time giữa consecutive trades
- Re-entry rate: bao nhiêu % trades bắt đầu within 5/10/20 bars of previous exit?
- Quick-flip rate: trades exit rồi re-enter trong gap rất ngắn

5. Cross-reference
- Verify total trade count match known (201 with D1 filter, 226 without)
- Verify key metrics match known values
- Nếu discrepancy > 1%, STOP và investigate

Deliverables bắt buộc:
- research/beyond_trend_lab/01_audit_state_map.md
- research/beyond_trend_lab/code/phase1_state_map.py
- research/beyond_trend_lab/tables/state_classification.csv
- research/beyond_trend_lab/tables/Tbl01_state_summary.csv
- research/beyond_trend_lab/tables/Tbl02_flat_durations.csv
- research/beyond_trend_lab/figures/Fig01_price_state_overlay.png
- research/beyond_trend_lab/figures/Fig02_flat_duration_hist.png
- research/beyond_trend_lab/figures/Fig03_yearly_state_fraction.png
- manifest.json (initial)

Cấm:
- Không phân tích return hay volume trong phase này
- Không đề xuất strategy hay pattern
- Chỉ map states và mô tả temporal structure
