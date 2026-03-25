# Phase 4: Synthesis & Verdict — Tổng Hợp Và Phán Quyết Cuối Cùng

Copy nội dung trong block ` ``` ` vào phiên mới.

---

```
NGHIÊN CỨU X30 / PHIÊN 4: SYNTHESIS & VERDICT

======================================================================
BỐI CẢNH
======================================================================

Đây là phiên cuối (4/4) của nghiên cứu X30 (Fractional Actuator).

TRƯỚC KHI LÀM GÌ, đọc TẤT CẢ kết quả từ 3 phiên trước:

1. Signal quality (phase 1):
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/signal_summary.json
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_temporal_stability.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_oos_quartiles.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_feature_importance.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_calibration.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_score_distribution.csv

2. Actuator optimization (phase 2):
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/actuator_summary.json
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_partial_sweep.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_continuous_sizing.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_mdd_decomposition.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_cost_interaction.csv

3. Validation (phase 3):
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/validation_summary.json
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_wfo_results.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_bootstrap.csv
   /var/www/trading-bots/btc-spot-dev/research/x30/tables/Tbl_bootstrap_diagnostics.csv  (nếu G3 fail)

4. Context chung:
   /var/www/trading-bots/btc-spot-dev/research/x30/prompte/context.md
   /var/www/trading-bots/btc-spot-dev/research/x29/x29_report.md

======================================================================
MỤC TIÊU
======================================================================

Phiên này KHÔNG chạy code mới (trừ khi cần supplementary analysis).
Nhiệm vụ: tổng hợp toàn bộ evidence thành:

1. REPORT — Tường thuật khoa học hoàn chỉnh
2. VERDICT — PROMOTE / WATCH / REJECT với justification
3. DECISION MATRIX — Recommendation theo cost regime
4. MEMORY UPDATE — Cập nhật kết quả vào hệ thống memory

======================================================================
VIẾT BÁO CÁO
======================================================================

File: /var/www/trading-bots/btc-spot-dev/research/x30/x30_report.md

Cấu trúc:

### 1. Executive Summary (3-5 câu)
- What was tested, what was found, verdict

### 2. Research Path
- Bảng tóm tắt 4 phiên: câu hỏi → phương pháp → kết quả → gate

### 3. Signal Anatomy (từ phiên 1)
- Temporal stability: giữ ở bao nhiêu periods?
- OOS AUC vs full-sample AUC
- Feature importance ranking
- Calibration quality
- Score distribution characteristics
- Verdict signal: reliable / unreliable

### 4. Actuator Optimization (từ phiên 2)
- Optimal discrete partial_frac (Sharpe-optimal vs Calmar-optimal)
- Continuous vs discrete: worth the complexity?
- MDD mechanism: exposure vs timing attribution
  → Report mechanism: exposure reduction vs timing? So sánh với Base(f=0.20).
- Cost interaction: alpha hay cost-saving?
- Full results table (best config × 9 costs)

### 5. Validation Results (từ phiên 3)
- WFO: fold-by-fold results, win rate
- Bootstrap: P(ΔSh>0), median ΔSh, P(ΔMDD<0)
- Diagnostics (nếu có): signal preservation, conditional analysis
- Final gate status: G0, G1, G2, G3

### 6. Comparison With Prior Work
- PRIMARY comparison: vs Base E5+EMA1D21 (doing nothing). Đây là bar THẬT.
- SECONDARY: vs Base(f=0.20) — dumb exposure reduction benchmark
- TERTIARY: vs X14D, X18, X19, X29:
  | Study | Actuator | Sharpe@25bps | MDD | Bootstrap | WFO | Verdict |
- Nếu partial actuator pass: giải thích TẠI SAO nó vượt rào cản binary không qua
- Nếu partial actuator fail: giải thích nó fail Ở ĐÂU và HỌC ĐƯỢC GÌ
- CẢNH BÁO: so sánh với X14D/X18/X19 (toàn fail) tạo bar thấp giả tạo.
  Bar thực sự là Base (no overlay, zero DOF).

### 7. Theoretical Framework — XÂY TỪ DATA, KHÔNG ÁP ĐẶT TRƯỚC
- Dựa trên kết quả THỰC TẾ từ phiên 1-3, trả lời:
  → Partial exit có thực sự tốt hơn binary? Nếu có, GIẢI THÍCH tại sao.
    Nếu KHÔNG (continuous ≈ discrete, hoặc cả hai fail) → giải thích cũng vậy.
  → MDD reduction mechanism (từ phiên 2 decomposition): exposure hay timing?
    So sánh với Base(f=0.20) benchmark cho answer cụ thể.
  → KHÔNG ÉP data vào framework sẵn có. Nếu kết quả mâu thuẫn với lý thuyết
    information gradient hoặc Kelly, report mâu thuẫn đó thẳng thắn.

  Possible outcome: "Partial exit không tốt hơn binary một cách có ý nghĩa
  thống kê. Theoretical argument về information gradient đúng về logic
  nhưng effect size quá nhỏ để detect trên 7 năm data." — Đây là kết luận
  hoàn toàn hợp lệ.

### 8. Production Implications
- Nếu PROMOTE: config chính xác, parameters, code reference
- Nếu WATCH: điều kiện promote trong tương lai (thêm data? lower cost?)
- Nếu REJECT: lý do, bài học
- Nếu continuous > discrete PASS validation: insight "binary actuator wastes
  information" có thể áp dụng cho future signals
- Nếu continuous ≈ discrete hoặc cả hai fail: insight KHÔNG được generalize.
  Logic đúng không có nghĩa effect size đủ lớn để matter.

### 9. Hypotheses Evaluation
- H1: Partial fraction tối ưu gần 0.50 → TRUE/FALSE (actual optimal?)
- H2: Continuous sizing > discrete → TRUE/FALSE
- H3: MDD reduction từ timing, không chỉ exposure → TRUE/FALSE
- H4: Bootstrap gap là structural (VCBB phá signal) → TRUE/FALSE
- H5: Fractional actuator giá trị ở mọi cost → TRUE/FALSE

### 10. Artifacts Index
- Liệt kê mọi file tạo ra trong 4 phiên

======================================================================
VIẾT KẾT QUẢ JSON
======================================================================

File: /var/www/trading-bots/btc-spot-dev/research/x30/x30_results.json

{
  "study": "X30",
  "title": "Fractional Actuator for Churn Signal",
  "date": "2026-03-XX",
  "signal": {
    "oos_auc": float,
    "temporal_stable": true/false,
    "calibration_ece": float,
    "dominant_features": ["fX", "fY"]
  },
  "actuator": {
    "best_type": "discrete" / "continuous",
    "best_config": {...},
    "sharpe_25bps": float,
    "mdd_25bps": float,
    "calmar_25bps": float,
    "delta_sh_vs_base": float,
    "delta_mdd_vs_base": float,
    "mdd_timing_attribution": float
  },
  "validation": {
    "wfo_wins": "X/4",
    "wfo_mean_delta_sh": float,
    "bootstrap_p_delta_sh_pos": float,
    "bootstrap_median_delta_sh": float,
    "permutation_p": float
  },
  "gates": {
    "G0": true/false,  // signal reliable
    "G1": true/false,  // actuator > Base full-sample
    "G2": true/false,  // WFO >= 75%
    "G3": true/false   // Bootstrap >= 55%
  },
  "verdict": "PROMOTE" / "WATCH" / "REJECT",
  "verdict_reason": "string"
}

======================================================================
CẬP NHẬT MEMORY
======================================================================

SAU KHI viết report và results, cập nhật 2 nơi:

1. /var/www/trading-bots/btc-spot-dev/research/results/COMPLETE_RESEARCH_REGISTRY.md
   → Thêm entry cho X30

2. /root/.claude/projects/-var-www-trading-bots/memory/MEMORY.md
   → Cập nhật section "X30" hoặc thêm entry mới
   → Nếu PROMOTE: cập nhật "Final Algorithm" section
   → Nếu WATCH/REJECT: thêm vào rejected/watch list

3. /var/www/trading-bots/btc-spot-dev/STRATEGY_STATUS_MATRIX.md
   → Cập nhật status

======================================================================
QUY TẮC
======================================================================

1. ĐỌC TẤT CẢ ARTIFACTS TRƯỚC — Không tự đoán kết quả.
   Nếu một phiên trước không tạo artifact (vì gate fail sớm),
   report dựa trên những gì CÓ.

2. HONEST VERDICT — Nếu evidence mixed, verdict = WATCH (không PROMOTE).
   PROMOTE chỉ khi CẢ 4 gates pass.

3. THEORETICAL DEPTH — Section 7 (framework) là giá trị lâu dài.
   Ngay cả khi verdict = REJECT, insight về binary vs continuous actuator
   và MDD mechanism là valuable.

4. COMPARISON FAIRNESS — Khi so sánh với X14D, X18, X19, dùng cùng
   cost level (25 bps) và cùng metrics.

5. KHÔNG overfit verdict — Nếu data ambiguous, nói thẳng "inconclusive"
   thay vì ép vào PROMOTE hoặc REJECT.

======================================================================
BẮT ĐẦU
======================================================================

Bước 1: Đọc context.md
Bước 2: Đọc signal_summary.json, actuator_summary.json, validation_summary.json
Bước 3: Đọc tất cả CSV tables
Bước 4: Viết x30_report.md
Bước 5: Viết x30_results.json
Bước 6: Cập nhật memory/registry/status matrix
Bước 7: Tóm tắt verdict cho user

Hãy bắt đầu từ Bước 1.
```
