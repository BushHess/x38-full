# Phase 2: Actuator Design — Cách Tối Ưu Để Hành Động Trên Score

Copy nội dung trong block ` ``` ` vào phiên mới.

---

```
NGHIÊN CỨU X30 / PHIÊN 2: ACTUATOR DESIGN

======================================================================
BỐI CẢNH
======================================================================

Đây là phiên 2/4 của nghiên cứu X30 (Fractional Actuator).

TRƯỚC KHI LÀM GÌ:
1. Đọc context: /var/www/trading-bots/btc-spot-dev/research/x30/prompte/context.md
2. Đọc kết quả phiên 1:
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/signal_summary.json
   → Nếu verdict = "STOP" → DỪNG NGAY. Signal không đáng tin, không cần actuator.
   → Nếu verdict = "PROCEED" → tiếp tục.
3. Đọc các tables từ phiên 1 để hiểu signal characteristics:
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_calibration.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_score_distribution.csv

Phiên 1 đã chứng minh (hoặc bác bỏ) rằng churn score là tín hiệu đáng tin.
Phiên này tìm câu trả lời cho: **Cách tốt nhất để hành động dựa trên score?**

======================================================================
CÂU HỎI SÂU — TẠI SAO PHIÊN NÀY QUAN TRỌNG
======================================================================

Cả X12-X19 (8 studies) đều dùng BINARY actuator: suppress 100% hoặc exit 100%.
Kết quả: 2 PROMOTE (X14D, X18) nhưng cả hai chỉ thắng ở cost > 30-35 bps.
Tại cost thực tế (15-25 bps), chúng THUA Base.

X29 pilot gợi ý partial exit (50%) có thể thắng Base trong full-sample.
Nhưng: (1) đây là 1 pilot run với selection bias, (2) bootstrap fail 37.2%,
(3) partial_frac=0.50 là con số tùy ý. Câu hỏi thực sự:

1. Partial fraction tối ưu phụ thuộc vào GÌ?
   - Nó phụ thuộc vào score? (high score → keep more)
   - Nó phụ thuộc vào cost? (high cost → keep more vì re-entry đắt)
   - Hay nó flat? (một fraction cố định cho mọi trường hợp)

2. Continuous sizing (keep_frac = f(score)) có giá trị so với discrete?
   - Phiên 1 cho biết calibration tốt hay xấu
   - Nếu calibration xấu → dùng rank-based (percentile) thay vì raw score
   - Nếu calibration tốt → score trực tiếp map sang keep_frac

3. MDD reduction (-12pp) đến từ ĐÂU?
   - Từ reduced exposure? (vì partial exit = less capital at risk)
   - Từ timing? (partial exit tại đúng thời điểm drawdown bắt đầu)
   - Hay từ cả hai?
   Hiểu mechanism QUAN TRỌNG cho production: nó cho biết benefit robust hay fragile.

======================================================================
THIẾT KẾ THÍ NGHIỆM
======================================================================

Viết file: /var/www/trading-bots/btc-spot-dev/research/x30/code/x30_actuator.py

Gồm 4 phân tích (A-D):

--- A: PARTIAL FRACTION SWEEP ---

Sweep partial_frac ∈ {0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00}
× 9 cost levels = 99 backtests

NOTE: 0.00 = full exit always (≡ Base with extra model overhead — should match Base).
      1.00 = full suppress always (≡ X18 binary — should match X18).
      Include BOTH endpoints to verify sim engine correctness AND see full response curve.

Cơ chế (giống pilot, sweep fraction):
- Khi trail fires AND score > threshold: bán (1-partial_frac) position, giữ partial_frac
- Khi trail fires AND score ≤ threshold: exit 100% (bình thường)
- Trend exit: exit 100% bất kể score

Metrics: Sharpe, CAGR, MDD, Calmar, trades, avg_exposure, n_partial_exits

So sánh hai cách chọn optimal:
  (a) Max Sharpe tại 25 bps
  (b) Max Calmar tại 25 bps (MDD reduction was notable in pilot, needs validation)
  (c) Plateau analysis: nếu Sharpe flat trong range → chọn giữa (robust)

Gate A (strengthened — pilot already showed 1 value works, gate must be harder):
  (a) ≥ 3 consecutive partial_frac values beat Base tại 25 bps (plateau, not point-optimal)
  (b) Best ΔSh > 0.03 tại 25 bps (meaningful effect, not noise)
  (c) Best partial_frac also beats Base ở ≥ 7/9 cost levels (robustness)
  Tất cả 3 điều kiện phải đạt. Nếu chỉ 1 giá trị thắng → fragile, not robust.

--- B: CONTINUOUS SIZING ---

Thay vì threshold binary (score > thresh → keep frac, else exit 100%),
dùng score trực tiếp để quyết định keep fraction.

3 designs:

B1: Linear map
  Khi trail fires:
    keep_frac = clip(score, floor, ceiling)
  floor = 0.0, ceiling = 1.0
  → score=0 → exit 100%, score=1 → keep 100%
  Không có threshold — MỌI trail-stop đều partial

B2: Threshold + continuous
  Khi trail fires:
    if score ≤ low_thresh: exit 100% (Q1 trades → always exit)
    elif score ≥ high_thresh: keep max_frac (Q4 trades → near-full suppress)
    else: keep_frac = linear_interp(score, low_thresh, high_thresh, 0, max_frac)
  low_thresh = P25 of score distribution
  high_thresh = P75 of score distribution
  max_frac ∈ {0.60, 0.70, 0.80, 0.90}
  → 4 configs

B3: Rank-based (nếu phiên 1 cho thấy calibration xấu)
  Khi trail fires:
    rank = percentile_rank(score) in [0, 1]  (within all trail-stop scores)
    keep_frac = rank * max_frac
  max_frac ∈ {0.60, 0.70, 0.80, 0.90}
  → 4 configs

Tổng: 1 + 4 + 4 = 9 continuous designs × 9 costs = 81 backtests

DOF WARNING: Phase A (9) + Phase B (9) = 18 configs tổng cộng.
  Multiple comparison risk. Report:
  - Best config kèm note "best of 18 comparisons"
  - Nếu best ΔSh < 0.03 → coi như noise (threshold đã account for 18 configs)
  - Cross-check: second-best config có similar performance? (convergence = robust)

Gate B: Best continuous > best discrete (Phase A) tại 25 bps?
  → Đây là thước đo xem continuous có giá trị gia tăng so với discrete.
  → Nếu KHÔNG → discrete đủ tốt, giữ đơn giản. Simplicity wins by default.

--- C: MDD MECHANISM ANALYSIS ---

Câu hỏi: TẠI SAO MDD giảm ~12pp?

Phương pháp:
1. Chạy Base và best X18(partial) tại 25 bps
2. Xác định TOP 5 drawdown episodes (deepest) của Base
3. Với mỗi episode:
   - Base: peak NAV, trough NAV, drawdown %, duration
   - X18(partial): peak NAV, trough NAV, drawdown %, duration
   - Số partial exits trong episode
   - Avg keep_frac trong episode
   - Exposure trung bình trong episode (Base vs partial)
4. Decompose:
   - ΔDD_from_exposure = DD_base * (avg_exposure_partial / avg_exposure_base - 1)
   - ΔDD_from_timing = actual_ΔDD - ΔDD_from_exposure
5. Attribution: % of MDD reduction từ exposure vs timing

CÂU HỎI CHÍNH — dùng BENCHMARK COMPARISON để trả lời:
  Chạy thêm 1 config: Base(f=0.20) — giảm position size cố định từ 30% xuống 20%,
  KHÔNG CÓ churn model, KHÔNG CÓ signal. Đây là "dumb exposure reduction" benchmark.

  - Nếu X18(partial) MDD ≈ Base(f=0.20) MDD → MDD reduction CHỈ từ exposure.
    Churn signal không đóng góp gì cho risk management. Bạn có thể đạt cùng
    kết quả bằng cách giảm f — đơn giản hơn nhiều, zero DOF.
  - Nếu X18(partial) MDD < Base(f=0.20) MDD → có TIMING component.
    Signal biết KHI NÀO nên giảm exposure → conditional risk management → giá trị thật.
  - Nếu X18(partial) Sharpe > Base(f=0.20) Sharpe → signal giữ upside tốt hơn
    dumb reduction → genuinely useful.

  Report: Bảng 3 cột: Base(f=0.30), Base(f=0.20), X18(partial) — Sharpe, MDD, Calmar.

--- D: COST INTERACTION ANALYSIS ---

Câu hỏi: Partial actuator value thay đổi thế nào theo cost?

Phương pháp:
1. Với best actuator (discrete hoặc continuous):
   - Plot ΔSh vs cost (9 points)
   - Plot ΔMDD vs cost
   - Plot ΔCalmar vs cost
2. Tìm: giá trị TĂNG hay GIẢM theo cost?
   - Nếu tăng: partial actuator là cost-saving mechanism (kém thú vị)
   - Nếu flat: partial actuator mang alpha ròng (rất thú vị — X22 cho thấy
     binary churn filter là cost-saving → tăng theo cost)
   - Nếu giảm: partial actuator HURT ở high cost (concerning)

3. Crossover analysis: tại cost nào partial actuator = Base?
   Ghi nhận kết quả (có crossover hay không) mà không đánh giá trước.

======================================================================
SIM ENGINE
======================================================================

Reuse sim logic từ x29_signal_diagnostic.py:
  _sim_x18_partial() — cho Phase A (discrete)
  Mới viết: _sim_x18_continuous() — cho Phase B

BUG QUAN TRỌNG (KHÔNG lặp lại):
  Khi full exit fires sau partial exits:
  WRONG: cash = received
  RIGHT: total_received = cash + received; cash = total_received
  Partial exit cash tích lũy trong biến `cash`. Full exit phải CỘNG thêm,
  không được GHI ĐÈ.

Churn model training: cùng protocol x29_signal_diagnostic.py.
  - Train trên trades ở 50 bps
  - 7 features, L2 logistic, 5-fold CV for C
  - Threshold = P(100-α) with α=40

======================================================================
TÀI NGUYÊN CODE
======================================================================

Đọc TRƯỚC KHI viết code:
1. /var/www/trading-bots/btc-spot-dev/research/x29/code/x29_signal_diagnostic.py
   → _sim_x18_partial() (reference implementation, đã debug)
   → _sim_base(), _train_churn_model(), _extract_features_7()
   → Tất cả indicators

2. Phiên 1 results:
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/signal_summary.json
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_calibration.csv

======================================================================
OUTPUT
======================================================================

Thư mục: /var/www/trading-bots/btc-spot-dev/research/x30/

Code:
  code/x30_actuator.py

Tables:
  tables/Tbl_partial_sweep.csv
    Columns: partial_frac, cost_bps, sharpe, cagr, mdd, calmar, trades,
             n_partial_exits, avg_exposure
  tables/Tbl_continuous_sizing.csv
    Columns: design, param, cost_bps, sharpe, cagr, mdd, calmar, trades
  tables/Tbl_mdd_decomposition.csv
    Columns: episode, base_dd, partial_dd, delta_dd, exposure_component,
             timing_component, n_partials
  tables/Tbl_cost_interaction.csv
    Columns: cost_bps, base_sharpe, best_sharpe, delta_sh, base_mdd, best_mdd, delta_mdd

  tables/actuator_summary.json
    {
      "best_discrete_frac": float,
      "best_discrete_sharpe_25": float,
      "best_continuous_design": "B1/B2/B3",
      "best_continuous_sharpe_25": float,
      "continuous_beats_discrete": true/false,
      "mdd_from_exposure_pct": float,  // % MDD reduction từ exposure
      "mdd_from_timing_pct": float,    // % MDD reduction từ timing
      "cost_interaction": "increasing/flat/decreasing",
      "candidates_for_wfo": [
        {"name": "config1", "type": "discrete/continuous", "partial_frac": float,
         "design": null/"B1"/"B2"/"B3", "params": {...}},
        ...
      ],
      "gate_A": true/false,
      "gate_B": true/false
    }

Figures:
  figures/Fig_partial_sweep.png      (heatmap: partial_frac × cost → Sharpe)
  figures/Fig_partial_sweep_mdd.png  (heatmap: partial_frac × cost → MDD)
  figures/Fig_continuous_compare.png  (bar chart: designs at 25 bps)
  figures/Fig_mdd_decomposition.png  (stacked bar: exposure vs timing per episode)
  figures/Fig_cost_interaction.png   (line plot: ΔSh, ΔMDD vs cost)

======================================================================
QUY TẮC
======================================================================

1. ĐỌC signal_summary.json TRƯỚC — nếu verdict="STOP" → dừng ngay.

2. CODE TRƯỚC, KẾT LUẬN SAU — 180 backtests thật (99+81).

3. MDD MECHANISM — so sánh với Base(f=0.20) benchmark. Nếu X18(partial)
   không thắng Base(f=0.20) trên cả Sharpe lẫn MDD → partial exit không
   có giá trị vượt trội so với giảm position size đơn giản.

4. KHÔNG cherry-pick — report TẤT CẢ partial_frac values, TẤT CẢ cost levels.
   Nếu optimal là 0.90 (gần binary suppress) → report thẳng.

5. SAVE ARTIFACTS — Phase 3 đọc actuator_summary.json để chọn candidates
   cho WFO validation.

======================================================================
BẮT ĐẦU
======================================================================

Bước 1: Đọc context.md
Bước 2: Đọc signal_summary.json → kiểm tra verdict
Bước 3: Đọc x29_signal_diagnostic.py (sim engine reference)
Bước 4: Viết code/x30_actuator.py
Bước 5: Chạy Phase A (sweep) → report gate A
  → NẾU GATE A FAIL (no plateau, ΔSh < 0.03, hoặc fragile): DỪNG.
    Ghi actuator_summary.json với verdict="STOP_FRAGILE".
    Pilot result là outlier, không robust. Không cần Phase B-D.
Bước 6: Chạy Phase B (continuous) → report gate B
Bước 7: Chạy Phase C (MDD decomposition — bao gồm Base(f=0.20) benchmark)
Bước 8: Chạy Phase D (cost interaction)
Bước 9: Ghi actuator_summary.json
Bước 10: Kết luận: Top 2-3 candidates cho WFO (HOẶC "STOP" nếu no viable candidate)

Hãy bắt đầu từ Bước 1.
```
