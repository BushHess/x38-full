# Phase 1: Signal Anatomy — Churn Score Có Đáng Tin?

Copy nội dung trong block ` ``` ` vào phiên mới.

---

```
NGHIÊN CỨU X30 / PHIÊN 1: SIGNAL ANATOMY

======================================================================
BỐI CẢNH
======================================================================

Đây là phiên 1/4 của nghiên cứu X30 (Fractional Actuator).

TRƯỚC KHI LÀM GÌ, đọc file context:
  /var/www/trading-bots/btc-spot-dev/research/x30/prompte/context.md

Tóm tắt: X29 pilot quan sát thấy churn score (logistic, 7 features, L2
penalty) phân loại trail-stop outcomes theo quartile TRONG FULL-SAMPLE:
  Q1: avg ret=-3.44%, WR=8.7%
  Q4: avg ret=+13.61%, WR=84.8%

CẢNH BÁO: Đây là kết quả IN-SAMPLE — model trained và evaluated trên cùng data.
Chưa kiểm tra:
- Có ổn định qua thời gian không? (overfitting vào specific market regimes?)
- Có works ngoài mẫu training không? (model generalize hay chỉ memorize?)
- Feature nào thực sự drive signal? (1 feature fragile hay nhiều features robust?)
- Model calibration có tốt không? (score có meaningful magnitude hay chỉ ordering?)

NULL HYPOTHESIS (H0): Churn score KHÔNG mang thông tin predictive về trail-stop
outcomes ngoài mẫu training. Monotonic Q1→Q4 là artifact của in-sample overfitting.

PHIÊN NÀY cố gắng BÁC BỎ H0. Nếu không bác bỏ được → dừng nghiên cứu.

SELECTION BIAS NOTE: Chúng ta nghiên cứu signal này vì pilot trông tốt.
Nếu pilot trông xấu, sẽ không có study này. Vì vậy tiêu chuẩn evidence
phải CAO HƠN bình thường để bù cho selection effect.

======================================================================
THIẾT KẾ THÍ NGHIỆM
======================================================================

Viết file: /var/www/trading-bots/btc-spot-dev/research/x30/code/x30_signal.py

Gồm 5 phân tích (A-E), mỗi phân tích trả lời một sub-question:

--- A: TEMPORAL STABILITY ---

Câu hỏi: Q1→Q4 monotonicity có ổn định qua các giai đoạn khác nhau?

Phương pháp:
1. Chia data thành 3 periods (roughly equal bars):
   - P1: 2019-01 → 2021-06 (bull + COVID crash + recovery)
   - P2: 2021-07 → 2023-06 (bear market + bottom)
   - P3: 2023-07 → 2026-02 (recovery + new ATH)
2. Với MỖI period:
   a. Train churn model trên trades trong period đó (50 bps, same protocol)
   b. Compute score cho trail-stop trades trong period
   c. Chia thành quartiles, compute avg ret và WR mỗi quartile
3. Kiểm tra: Q1→Q4 monotonicity giữ ở MỖI period?
   (avg_ret và WR tăng monotonic từ Q1 đến Q4)

Gate A: monotonicity giữ ở ≥ 2/3 periods (cho phép 1 period break).
  NHƯNG: nếu period BREAK là P3 (2023-2026, gần nhất) → coi như FAIL.
  P3 là dữ liệu gần production nhất — nếu signal không work ở đó,
  nó irrelevant cho tương lai dù P1 và P2 đẹp.

--- B: OUT-OF-SAMPLE SIGNAL QUALITY ---

Câu hỏi: Model trained trên nửa đầu có discriminate tốt trên nửa sau?

Phương pháp:
1. Split: train trên P1+P2 (2019-2023), test trên P3 (2023-2026)
2. Train model bình thường (logistic L2, 7 features, CV for C)
3. Score tất cả trail-stops trong P3 bằng model trained on P1+P2
4. Compute:
   a. AUC trên P3 (so sánh vs full-sample AUC=0.805 từ X13)
   b. Quartile analysis trên P3 (Q1-Q4 avg ret, WR)
   c. Rank correlation (Spearman) giữa score và trade return trên P3

Gate B: OOS AUC > 0.65 AND P3 quartiles maintain monotonicity
  (0.65, not 0.60, to compensate for selection bias — we picked this signal
  BECAUSE it looked good in-sample, so OOS bar must be higher than normal)

--- C: FEATURE IMPORTANCE ---

Câu hỏi: Feature nào thực sự drive signal? Có feature nào dominant?

Phương pháp (leave-one-out permutation importance):
1. Train full model → compute AUC (baseline)
2. Với mỗi feature (f1-f7):
   a. Shuffle feature đó (permute values across samples)
   b. Re-compute AUC
   c. Importance = baseline_AUC - permuted_AUC
3. Rank features by importance
4. Leave-one-out: retrain model WITHOUT mỗi feature, report AUC drop

Interpretation quan trọng:
- Nếu 1-2 features dominate → signal fragile (dependent on specific features)
- Nếu importance spread → signal robust (redundancy)
- Feature f7 (trail width relative) đặc biệt quan trọng vì nó encoding của
  trail multiplier — nếu f7 dominates, signal chỉ là proxy cho trail width

--- D: CALIBRATION ---

Câu hỏi: Khi model nói P(churn)=0.7, thực sự có 70% churn không?

Phương pháp:
1. Score tất cả trail-stops, chia thành 10 bins theo score
2. Với mỗi bin: actual_churn_rate vs mean_predicted_score
3. Plot calibration curve (predicted vs actual)
4. Compute Brier score và Expected Calibration Error (ECE)

Interpretation:
- Well-calibrated → có thể dùng score trực tiếp cho continuous sizing
- Poorly calibrated → phải dùng rank-based (percentile) thay vì score thô

--- E: SCORE DISTRIBUTION ANALYSIS ---

Câu hỏi: Score distribution có bimodal không? Có cluster tự nhiên?

Phương pháp:
1. Histogram của score trên tất cả trail-stops
2. KDE plot so sánh churn vs non-churn trails
3. Score at X18 threshold (P60) — bao nhiêu % mass mỗi bên?
4. Optimal threshold by Youden's J = sensitivity + specificity - 1
5. So sánh Youden threshold vs X18 percentile threshold

Interpretation:
- Bimodal → clear separation, binary OK cho extremes
- Unimodal overlapping → continuous actuator cần thiết
- Threshold comparison → X18's α=40 có gần optimal không?

======================================================================
THAM SỐ (FROZEN — KHÔNG THAY ĐỔI)
======================================================================

Từ E5+EMA1D21: SLOW=120, TRAIL=3.0, VDO_THR=0.0, D1_EMA=21
                RATR={P=20, Q=0.90, LB=100}
Churn: 7 features (f1-f7), L2 logistic, C via 5-fold CV
       C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]
       churn_window = 20 bars
Training cost: 50 bps (harsh)
Data window: 2019-01 to 2026-02, warmup=365d

======================================================================
CODE REFERENCE
======================================================================

Đọc TRƯỚC KHI viết code:
1. /var/www/trading-bots/btc-spot-dev/research/x29/code/x29_signal_diagnostic.py
   → Hàm _extract_features_7(), _label_churn(), _train_churn_model()
   → Hàm _sim_base() để tạo trades
   → Tất cả indicators: _ema(), _robust_atr(), _vdo(), _compute_d1_regime()

2. /var/www/trading-bots/btc-spot-dev/research/x29/code/x29_benchmark.py
   → Data loading pattern, DataFeed usage

3. /var/www/trading-bots/btc-spot-dev/research/x14/benchmark.py
   → Logistic fitting, AUC computation

======================================================================
OUTPUT
======================================================================

Thư mục: /var/www/trading-bots/btc-spot-dev/research/x30/

Code:
  code/x30_signal.py

Tables (CSV — sẽ được đọc bởi phase 2):
  tables/Tbl_temporal_stability.csv
    Columns: period, quartile, n_trades, avg_ret, median_ret, win_rate, n_trail_stops
  tables/Tbl_oos_quartiles.csv
    Columns: quartile, n, avg_ret, median_ret, win_rate, avg_score
  tables/Tbl_feature_importance.csv
    Columns: feature, permutation_imp, loo_auc, loo_auc_drop
  tables/Tbl_calibration.csv
    Columns: bin, mean_score, actual_churn_rate, n_samples
  tables/Tbl_score_distribution.csv
    Columns: metric, value (AUC_full, AUC_oos, brier, ece, youden_thresh, x18_thresh, ...)

Figures:
  figures/Fig_temporal_quartiles.png  (3×1 subplot: bar chart Q1-Q4 per period)
  figures/Fig_oos_quartiles.png      (Q1-Q4 bars, OOS data only)
  figures/Fig_feature_importance.png  (horizontal bar chart)
  figures/Fig_calibration.png        (calibration curve + histogram)
  figures/Fig_score_kde.png          (KDE: churn vs non-churn)

JSON summary:
  tables/signal_summary.json
    {
      "gate_A": true/false,  // temporal stability
      "gate_B": true/false,  // OOS signal quality
      "oos_auc": float,
      "periods_monotonic": int,  // out of 3
      "dominant_feature": "fX",
      "calibration_ece": float,
      "score_bimodal": true/false,
      "verdict": "PROCEED" / "STOP"
    }

======================================================================
QUY TẮC
======================================================================

1. CODE TRƯỚC, KẾT LUẬN SAU — Chạy phân tích thật, không ước lượng.

2. HONEST ASSESSMENT — Nếu signal không stable OOS, kết luận "STOP" thẳng.
   Đây là checkpoint quan trọng nhất: nếu signal giả → mọi actuator đều vô nghĩa.

3. KHÔNG FIT LẠI model — Model training protocol giữ nguyên (L2, 7 features,
   5-fold CV for C, churn_window=20). Chỉ thay đổi TRAINING DATA khi test
   temporal stability và OOS.

4. REPORT TẤT CẢ con số — Kể cả khi xấu. Đặc biệt Part B (OOS) — nếu AUC
   drop nhiều, report bao nhiêu.

5. SAVE ARTIFACTS — Phase 2 sẽ đọc signal_summary.json để quyết định
   có tiếp tục không. Tables CSV cho reproducibility.

======================================================================
BẮT ĐẦU
======================================================================

Bước 1: Đọc context.md
Bước 2: Đọc x29_signal_diagnostic.py (code patterns)
Bước 3: Đọc x14/benchmark.py (logistic training)
Bước 4: Viết code/x30_signal.py
Bước 5: Chạy → report từng phân tích A-E
Bước 6: Ghi signal_summary.json
Bước 7: Kết luận: PROCEED hoặc STOP

Hãy bắt đầu từ Bước 1.
```
