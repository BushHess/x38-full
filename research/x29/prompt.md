# X29: Optimal Stack — Prompt khởi động nghiên cứu

Copy toàn bộ nội dung bên dưới vào phiên mới để bắt đầu.

---

## PROMPT

```
NGHIÊN CỨU X29: OPTIMAL STACK — TỔ HỢP TỐI ƯU CÁC OVERLAY TRÊN E5+EMA1D21

======================================================================
BỐI CẢNH
======================================================================

Bạn sẽ triển khai nghiên cứu X29 theo spec đã có sẵn tại:
  /var/www/trading-bots/btc-spot-dev/research/x29/SPEC.md

Đọc SPEC.md TRƯỚC khi làm bất cứ gì. Spec định nghĩa đầy đủ:
- 12 strategies (2 Monitor × 3 Churn × 2 Trail)
- 9 cost levels (10-100 bps)
- 5 tests (T0-T5) với gates rõ ràng
- Decision tree
- Anti-self-deception checklist

======================================================================
MỤC TIÊU
======================================================================

Viết và chạy code/x29_benchmark.py để thực hiện 5 tests theo thứ tự:

T0: Full-sample matrix (108 backtests)
    → Heatmaps, line plots, gate check
T1: Interaction analysis (factorial decomposition)
    → Đo synergy/interference giữa Monitor × Churn × Trail
T2: WFO 4-fold (top strategies)
    → OOS robustness check
T3: Bootstrap VCBB (top strategies)
    → Statistical significance
T4: Cost-crossover map
    → Recommendation matrix theo cost regime
T5: Dominance / Pareto analysis
    → Efficient frontier

Sau mỗi test, in gate status. Nếu gate FAIL → dừng theo decision tree.

======================================================================
TÀI NGUYÊN QUAN TRỌNG
======================================================================

Data:
  /var/www/trading-bots/btc-spot-dev/data/btcusdt_*.csv

Base strategy code (E5+EMA1D21):
  /var/www/trading-bots/btc-spot-dev/strategies/vtrend_e5_ema21_d1/strategy.py

Regime Monitor V2:
  /var/www/trading-bots/btc-spot-dev/monitoring/regime_monitor.py

Churn filter reference (X14D mechanism):
  /var/www/trading-bots/btc-spot-dev/research/x14/benchmark.py

Churn filter reference (X18 mechanism):
  /var/www/trading-bots/btc-spot-dev/research/x18/benchmark.py

Bootstrap library:
  /var/www/trading-bots/btc-spot-dev/research/lib/vcbb.py

Prior cost study (X22, reference):
  /var/www/trading-bots/btc-spot-dev/research/x22/

Shared backtest infrastructure (prior X-series):
  Xem research/x14/benchmark.py và research/x22/ để hiểu cách chạy
  backtest và tính metrics trong codebase này. Các scripts trước đó
  đều dùng run_backtest() từ strategies/ hoặc tự implement engine.

======================================================================
QUY TẮC BẮT BUỘC
======================================================================

1. ZERO NEW DOF — Mọi parameter đã frozen từ prior studies.
   Không tune threshold, không thay đổi feature set, không refit model.

2. REPORT ALL COST LEVELS — Không cherry-pick. Primary comparison ở 25 bps.

3. CODE TRƯỚC, KẾT LUẬN SAU — Chạy 108 backtests thật, tạo artifacts thật.
   Không giả vờ đã chạy. Không ước lượng kết quả.

4. HONEST STOPPING — Nếu T0 cho thấy không combination nào beat base,
   kết luận "overlays incompatible" là hoàn toàn hợp lệ.

5. GATE-DRIVEN — Tuân thủ decision tree trong SPEC.md.
   Gate FAIL → dừng hoặc downgrade recommendation theo quy định.

6. INTERACTION REPORTING — Interaction terms phải được tính và report
   cho MỌI pair, kể cả khi nhỏ. Đây là câu hỏi nghiên cứu chính.

======================================================================
OUTPUT
======================================================================

Thư mục làm việc:
  /var/www/trading-bots/btc-spot-dev/research/x29/

Code:       code/x29_benchmark.py
Tables:     tables/Tbl_*.csv (6 files per SPEC)
Figures:    figures/Fig_*.png (8 files per SPEC)
Report:     x29_report.md
Results:    x29_results.json

======================================================================
BẮT ĐẦU
======================================================================

Bước 1: Đọc SPEC.md
Bước 2: Đọc strategy code (E5+EMA1D21) và monitor code để hiểu interface
Bước 3: Đọc X14 và X18 benchmark.py để hiểu churn filter mechanism
Bước 4: Viết code/x29_benchmark.py
Bước 5: Chạy T0 → report gate → tiếp tục hoặc dừng

Hãy bắt đầu từ Bước 1.
```
