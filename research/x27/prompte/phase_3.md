======================================================================
PHASE 3: SIGNAL LANDSCAPE EDA
======================================================================

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x27/prompte/phase_0.md
  Đọc deliverables Phase 1:
  - /var/www/trading-bots/btc-spot-dev/research/x27/01_data_audit.md
  Đọc deliverables Phase 2:
  - /var/www/trading-bots/btc-spot-dev/research/x27/02_price_behavior_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl04*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl05*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl06*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/
- Observations Phase 2 về trend persistence, volatility structure, volume

Mục tiêu:
Khảo sát LANDSCAPE of possible signals — không đề xuất strategy cụ thể.
Phase này trả lời: "signal TYPES nào detect trends? exit TYPES nào preserve alpha?"
bằng cách ĐO LƯỜNG trên dữ liệu, không bằng ý kiến.

CHỈ MÔ TẢ VÀ ĐO. KHÔNG PROPOSE TRADING RULES.

======================================================================
Bước thực hiện:
======================================================================

PHẦN A: ENTRY SIGNAL LANDSCAPE

1. Định nghĩa "target event" (từ Phase 2 trend anatomy)
- Dùng kết quả Phase 2 để định nghĩa: thế nào là "trend đáng bắt"
  (threshold từ Phase 2 data, e.g., moves > X% lasting > Y bars)
- Đánh dấu MỌI target events trên H4 time series
- Count: bao nhiêu events, distribution over time

2. Signal type comparison — GENERIC, không phải specific parameters
Cho MỖI signal TYPE dưới đây, sweep một dải parameters hợp lý,
rồi đo metrics TRUNG BÌNH (không cherry-pick best param):

Type A: Momentum crossover
  - Fast/slow smoothed price: fast crosses above slow
  - Sweep: fast ∈ {5,10,20,30}, slow ∈ {50,80,120,160,200}

Type B: Breakout
  - Price breaks above N-bar high
  - Sweep: N ∈ {20, 40, 60, 80, 120, 160}

Type C: Momentum threshold
  - Rate of change over N bars exceeds threshold
  - Sweep: N ∈ {10, 20, 40, 60}, threshold ∈ {5%, 10%, 15%, 20%}

Type D: Volatility breakout
  - Price exceeds channel defined by volatility measure
  - Sweep: lookback ∈ {20, 40, 60}, width ∈ {1.5, 2.0, 2.5, 3.0}

Type E: Volume-confirmed price move (nếu Phase 2 cho thấy volume informative)
  - Price move + volume surge
  - Skip nếu Phase 2 xác nhận H_prior_5 (volume ≈ 0)

3. Cho MỖI signal type, đo (averaged over parameter sweep):
- Detection rate: bao nhiêu % target events được signal bắt?
- False positive rate: bao nhiêu % signals KHÔNG dẫn tới target event?
- Average lag: signal fires bao lâu SAU trend thực sự bắt đầu? (bars)
- Average slip: price đã di chuyển bao nhiêu % khi signal fires?
- Signal frequency: signals per year

4. Signal efficiency frontier (KEY PLOT)
- Plot: lag (x-axis) vs false_positive_rate (y-axis) cho tất cả types (Fig10)
- Mỗi type là một cluster of points (parameter variants)
- Frontier = lower-left boundary (low lag AND low false positives)
- GHI NHẬN: type nào nằm trên frontier? Type nào bị dominated?

5. Signal robustness
- Cho mỗi type: split data thành 4 time blocks
- Detection rate và false positive rate STABLE qua các blocks không?
- Type nào stable nhất? Type nào unstable?

PHẦN B: EXIT SIGNAL LANDSCAPE

6. Cho MỖI exit type, sweep parameters:

Type X: Trailing stop (fixed %)
  - Trail ∈ {3%, 5%, 8%, 12%, 15%, 20%}

Type Y: ATR trailing stop
  - ATR period ∈ {14, 20, 30}, multiplier ∈ {2.0, 2.5, 3.0, 3.5, 4.0, 5.0}

Type Z: Signal reversal
  - Same signal types as entry (A-D) nhưng ngược chiều

Type W: Time-based
  - Fixed holding period ∈ {20, 40, 60, 80, 120, 160, 200} bars

Type V: Volatility-based
  - Exit khi vol exceeds threshold hoặc vol compression

7. Cho MỖI exit type, đo (apply to target events):
- Capture ratio: % of trend được capture trước khi exit
- Churn rate: % exits followed by re-entry within 10 bars
- Average holding period (bars)
- Average return per trade (after cost 50 bps RT)
- Max drawdown during holding

8. Exit efficiency frontier (KEY PLOT)
- Plot: capture_ratio (x) vs churn_rate (y) cho tất cả types (Fig11)
- Frontier = upper-left (high capture AND low churn)
- Plot: capture_ratio (x) vs max_drawdown (y) (Fig12)

PHẦN C: ENTRY × EXIT INTERACTION

9. Pairing analysis
- Cho top-3 entry types (from frontier) × top-3 exit types:
  compute simple long-only equity curve
- Metrics: Sharpe, CAGR, MDD, trade count, churn count
- Heatmap: entry_type × exit_type → Sharpe (Fig13)
- CÂU HỎI: có entry types pair tốt hơn với certain exit types?

10. Regime conditioning
- Từ Phase 2 D1 analysis:
  define regime (bull/bear/neutral) bằng phương pháp đơn giản nhất
- Repeat heatmap #9 conditioned on regime
- Regime filter có cải thiện across the board hay chỉ specific pairs?

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x27/):
======================================================================
- 03_signal_landscape_eda.md
- code/phase3_signal_landscape.py
- figures/Fig10–Fig13+ (tối thiểu 4 key plots)
- tables/:
  - Tbl07: Entry signal comparison (type × metrics)
  - Tbl08: Exit signal comparison (type × metrics)
  - Tbl09: Entry × exit pairing matrix
  - Tbl10: Regime conditioning effect
- Observation log: Obs## (tiếp tục numbering từ Phase 2)

======================================================================
Cấm:
======================================================================
- Không chọn "winner" — chỉ mô tả landscape
- Không recommend "dùng type X" — chỉ ghi nhận frontier position
- Không tối ưu parameters — chỉ sweep và report AVERAGES
- Nếu tất cả types cho kết quả gần nhau → ghi nhận đó là finding
- Nếu một type dominate rõ ràng → ghi nhận nhưng KHÔNG propose strategy

======================================================================
Verify prior hypotheses:
======================================================================
- H_prior_3 (entry lag): So sánh lag across types.
  Có type nào đạt lag < 20 bars mà false positive < 50% không?
- H_prior_4 (exit churn): So sánh churn rate across exit types.
  Có exit type nào churn < 10% mà capture > 60% không?
- H_prior_7 (low exposure): Tính exposure cho mỗi entry×exit pair.
  Có pair nào exposure > 60% không?
- H_prior_10 (complexity ceiling): Đơn giản nhất vs phức tạp nhất
  trong landscape — gap bao nhiêu?
