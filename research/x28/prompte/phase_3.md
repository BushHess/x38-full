PHASE 3: SIGNAL LANDSCAPE EDA
======================================================================

Điều kiện: Phase 2 hoàn thành.

Bước 0 — CONTEXT LOADING (bắt buộc):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x28/prompte/phase_0.md
  Đọc deliverables Phase 2:
  - /var/www/trading-bots/btc-spot-dev/research/x28/02_price_behavior_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/
- Observations từ Phase 2

Mục tiêu:
Sweep TOÀN BỘ không gian entry × exit × filter.
Đo IMPACT lên Sharpe. KHÔNG chọn winner. Report everything.

======================================================================
PART A: ENTRY SIGNALS
======================================================================

Định nghĩa target event:
- Dùng trend anatomy từ Phase 2 (threshold ≥ 10% cumulative return)
- Target event = bắt đầu của trend period

Sweep các LOẠI entry signal (tối thiểu 4, được thêm nếu có evidence):
- Type A: Momentum crossover (EMA fast/slow, sweep periods)
- Type B: Breakout (close > N-bar high, sweep N)
- Type C: Momentum threshold (ROC > τ, sweep N và τ)
- Type D: Volatility breakout (close > SMA + k × ATR, sweep params)
- Type E: Volume-confirmed entry (nếu Phase 2 cho thấy volume có info)
- Type F+: BẤT KỲ loại khác nếu Phase 2 evidence gợi ý

Với MỖI loại, sweep parameter space và đo:
- Detection rate (bao nhiêu target events được bắt)
- False positive rate (bao nhiêu entries KHÔNG phải target)
- Lag (bars giữa target start và entry signal)
- Frequency (entries per year)

Lưu ý: KHÔNG đánh giá entry type nào "tốt hơn" ở phase này.
Chỉ đo và report. Frontier plot (Fig10).

======================================================================
PART B: EXIT SIGNALS
======================================================================

Sweep CẢ simple VÀ composite exits:

SIMPLE exits (tối thiểu 5):
- Type X: Fixed % trailing stop (sweep %)
- Type Y: ATR trailing stop (sweep period, multiplier)
- Type Z: Signal reversal (đảo ngược entry signal)
- Type W: Time-based (fixed holding period)
- Type V: Volatility-based (vol spike/compression)

COMPOSITE exits (BẮT BUỘC — đây là phần X27 bỏ qua):
- Type Y∪Z: trail stop OR reversal signal (whichever fires first)
- Type Y∪W: trail stop OR time limit
- Type Y∪V: trail stop OR vol signal
- Sweep TỔNG SỐ ≥ 4 composite exits dạng A∪B

Với MỖI exit (simple VÀ composite), đo:
- Capture ratio (return captured / total trend return)
- Churn rate (exit → re-entry within 10 bars)
- Average holding period
- Return per trade (after 50 bps RT cost)
- Max drawdown at trade level
- Average loser size

Frontier plots: Fig11 (capture vs churn), Fig12 (capture vs MDD)

QUAN TRỌNG: Composite exits (ví dụ trail OR reversal) có thể có
properties khác HOÀN TOÀN so với các thành phần riêng lẻ.
KHÔNG giả sử composite = trung bình của components. PHẢI đo trực tiếp.

======================================================================
PART C: ENTRY × EXIT PAIRING (Full Grid)
======================================================================

1. Simple grid: entry × exit
   - Tối thiểu: 4 entry × (5 simple + 4 composite) exit = 36 pairs
   - Với MỖI pair, chạy full backtest (50 bps RT, binary sizing)
   - Metrics: Sharpe, CAGR, MDD, trade count, exposure, churn rate,
     avg_winner, avg_loser, profit factor

2. Heatmap (Fig13): entry × exit → Sharpe
   PHẢI bao gồm composite exits trong heatmap.

3. Filter layer: thêm filters lên TOP-10 pairs (theo Sharpe)
   - Filter F1: D1 regime (close > D1 EMA, sweep period)
   - Filter F2: Volume filter (VDO, TBR, hoặc khác nếu Phase 2 suggest)
   - Filter F3: Volatility regime (vol > threshold)
   - Filter F4: BẤT KỲ filter khác nếu Phase 2 evidence gợi ý
   - Đo: Sharpe WITH filter vs WITHOUT filter → ΔSharpe per filter

4. Best-known strategy decomposition (BẮT BUỘC):
   Prior research cho thấy config tốt nhất đã biết là:
   "EMA cross + dual exit (trail OR reversal) + VDO filter + D1 regime"
   Sharpe = 1.08 (tại 50 bps RT).

   PHẢI decompose strategy này bằng cách BỎ TỪNG component:
   a. Full config:                          Sharpe = ?
   b. Remove VDO filter:                    Sharpe = ? → ΔVDO = ?
   c. Remove D1 regime filter:              Sharpe = ? → ΔRegime = ?
   d. Remove reversal exit (trail only):    Sharpe = ? → ΔDualExit = ?
   e. Remove trail (reversal only):         Sharpe = ? → ΔTrail = ?
   f. Remove both filters (entry+exit only): Sharpe = ? → ΔFilters = ?

   Kết quả decomposition → Tbl_decomposition
   Đây cho biết CONTRIBUTION THẬT SỰ của mỗi component.

======================================================================
PART D: IMPACT ANALYSIS (X27 KHÔNG CÓ PHẦN NÀY)
======================================================================

QUAN TRỌNG — đây là phần quyết định Phase 6 design đúng hướng.

Từ full grid (≥ 36 pairs + filter variants), bạn có ≥ 50 data points.
Mỗi data point có: Sharpe, CAGR, MDD, exposure, churn, trade_count,
avg_winner, avg_loser, avg_hold, win_rate, profit_factor.

1. Regression: property nào PREDICT Sharpe?

   Chạy OLS regression:
   Sharpe_i = β₀ + β₁·exposure_i + β₂·churn_i + β₃·trade_count_i
              + β₄·avg_loser_i + β₅·win_rate_i + β₆·avg_hold_i + ε_i

   Report:
   - Coefficient, p-value, R² cho mỗi predictor
   - Partial R² (marginal contribution)
   - Scatter plots: top-3 predictors vs Sharpe (Fig_impact)

2. Ranking: xếp hạng predictors theo |β × std(x)| (standardized impact)

   Ví dụ kết quả CÓ THỂ là:
   "Exposure giải thích 45% variance trong Sharpe.
    Avg_loser giải thích 25%. Churn giải thích 8%."
   → Điều này cho biết: optimize exposure quan trọng HƠN fix churn.

   NHƯNG bạn KHÔNG BIẾT kết quả trước khi chạy.
   Có thể churn THẬT SỰ quan trọng nhất. Để data quyết định.

3. Tbl_sharpe_drivers: bảng xếp hạng predictors

======================================================================
PART E: TOP-N ANALYSIS
======================================================================

1. Xếp hạng TẤT CẢ configs (entry × exit × filter) theo Sharpe
2. Report TOP-20 (Tbl_top20_sharpe) và TOP-20 theo Calmar
3. Cho TOP-5 theo Sharpe: phân tích TẠI SAO chúng tốt
   - Chúng có chung entry type? Exit type? Filter?
   - Chúng có chung PROPERTY nào? (high exposure? low avg_loser?)
   - Patterns → Observations (Obs##)

======================================================================
Deliverables:
======================================================================

- 03_signal_landscape_eda.md
- code/phase3_signal_landscape.py (complete, runnable)
- figures/:
  - Fig10: entry efficiency frontier (lag vs FP)
  - Fig11: exit capture vs churn
  - Fig12: exit capture vs MDD
  - Fig13: entry × exit Sharpe heatmap (BẮT BUỘC bao gồm composite exits)
  - Fig_impact: top-3 Sharpe predictors scatter plots
  - Fig_decomposition: component contribution bar chart
- tables/:
  - Tbl07: entry signals summary
  - Tbl08: exit signals summary (simple VÀ composite)
  - Tbl09: entry × exit pairing (full grid)
  - Tbl10: filter effects on TOP-10 pairs
  - Tbl_decomposition: best-known strategy decomposition
  - Tbl_sharpe_drivers: regression results (predictors ranked by impact)
  - Tbl_top20_sharpe: TOP-20 configs by Sharpe
- Observation log: Obs## for each significant finding
- manifest.json cập nhật

======================================================================
Cấm:
======================================================================
- KHÔNG chọn winner ("Type B tốt nhất")
- KHÔNG đề xuất trading rule
- KHÔNG interpret beyond data ("nên dùng X vì...")
- KHÔNG bỏ qua composite exits
- KHÔNG bỏ qua impact analysis
- KẾT LUẬN "tất cả entries/exits gần nhau" hoặc
  "không có exit type nào dominate" là hoàn toàn hợp lệ
