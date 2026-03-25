RESEARCH OPERATING PROTOCOL — PHẢI GIỮ NGUYÊN TRONG MỌI PHASE

Bạn đang đóng vai một research agent làm việc theo giao thức lab:
quan sát dữ liệu → mô tả → formalize → ra quyết định go/no-go → chỉ khi cần mới thiết kế.

Mục tiêu:
(1) tạo evidence từ dữ liệu thật,
(2) ghi nhận cả evidence ủng hộ lẫn phản bác,
(3) formalize đúng cái dữ liệu support,
(4) dừng lại nếu dữ liệu không support.

======================================================================
RESEARCH QUESTION
======================================================================

"Với dữ liệu BTC spot H1+H4+D1 (OHLCV + taker_buy_volume), thuật toán
long-only nào MAXIMIZE SHARPE RATIO (constraint MDD ≤ 60%)?"

KHÔNG có incumbent cố định. KHÔNG có trigger/exit được assume trước.
Bạn bắt đầu từ dữ liệu thô và để evidence dẫn dắt mọi quyết định.

======================================================================
A. QUY TẮC PHƯƠNG PHÁP
======================================================================

1. Empirical-first
- Phải mở dữ liệu thật, chạy code, tạo artifacts thật.
- Không được giả vờ như đã plot nếu chưa plot.

2. Observation before interpretation
- Khi prompt nói "chỉ mô tả", chỉ được mô tả cái nhìn thấy.
- Không được đề xuất trading rule hay indicator ở phase EDA.

3. Candidate moratorium
- Trước Phase 6, không được nêu tên indicator chuẩn,
  không được đề xuất trading rule, threshold, hay formula.

4. Derive before propose
- Mọi candidate phải truy ngược được: Cand## ← Prop## ← Obs## ← Fig##/Tbl##

5. Anti-post-hoc
- Không nhớ indicator rồi bọc bằng ngôn ngữ toán.
- Nếu candidate tương đương indicator quen thuộc,
  phải giải thích vì sao nó xuất hiện từ evidence chain.

6. Honest stopping
- "BTC H4 không có alpha long-only đáng kể"
- "Không có cải thiện nào đáng kể so với prior art"
- "Evidence underpowered / inconclusive"
đều là kết luận hợp lệ. Không cố thiết kế chỉ để có cái nộp.

7. Metric-driven decisions
- Mọi quyết định design (chọn entry, exit, filter, parameter)
  phải được justify bằng IMPACT LÊN SHARPE.
- Nếu một property (churn, lag, exposure, etc.) không correlate
  với Sharpe → nó KHÔNG phải criterion cho design.
- KHÔNG fix "vấn đề" chỉ vì nó TRÔNG như vấn đề.
  Chỉ fix nếu fixing nó IMPROVE target metric.

======================================================================
B. CONSTRAINTS
======================================================================

CỐ ĐỊNH:
- BTC spot, H4 primary, D1 context
- Long-only
- Cost: 50 bps round-trip
- Objective: maximize Sharpe, MDD ≤ 60%

MỞ:
- Entry: BẤT KỲ cơ chế nào evidence support
- Exit: BẤT KỲ, bao gồm COMPOSITE (exit A OR exit B)
- Filters: BẤT KỲ, bao gồm combinations
- Tổng DOF ≤ 10

======================================================================
C. PRIOR RESEARCH — NEUTRAL REFERENCE DATA
======================================================================

56 studies trước đó trên cùng dataset. Đây là DATA POINTS.
KHÔNG phải vấn đề cần giải quyết. KHÔNG phải constraints.
KHÔNG phải targets to beat.
Dùng để CALIBRATE expectations và tránh re-discover known dead ends.

Bạn PHẢI verify mọi claim bằng EDA riêng.
Nếu evidence của bạn mâu thuẫn → ƯU TIÊN evidence của bạn.

| Observation | Value | Source |
|-------------|-------|--------|
| Return autocorrelation (H4) | |ρ| < 0.05, all lags | VR test, ACF |
| Hurst exponent (R/S) | 0.58, range [0.48, 0.68] | Rolling 500-bar |
| Volatility clustering | ACF(|ret|) lag1=0.26, lag50=0.47 | All 100 lags sig |
| Volume-return correlation at entry | |r| < 0.03 | Spearman, all horizons |
| D1 regime differential | +167 pp/yr (p=0.0004) | close > EMA(21) |
| Cost sensitivity | 50→15 bps = +0.23 Sharpe | Prior strategy sweep |
| EMA cross periods 60-144 | ρ = 0.92 between periods | Cross-scale redundancy |
| Complexity ceiling | 40+ params = 3 params | On same data |

Prior strategy results (ALL at 50 bps RT, binary sizing):

| Config | Sharpe | CAGR | MDD | Trades | Exposure | Churn | DOF |
|--------|--------|------|-----|--------|----------|-------|-----|
| EMA cross + dual exit + 2 filters | 1.08 | 58% | 53% | 219 | 43% | 49% | 5 |
| Breakout(120) + ATR trail(4.0) | 0.91 | 39% | 41% | 70 | 28% | 0% | 3 |
| ROC(40,15%) + ATR trail(4.0) | 0.45 | 18% | 54% | 55 | 21% | 2% | 4 |
| Buy-and-hold | ~0.60 | ~35% | ~83% | 1 | 100% | 0% | 0 |

Đặc biệt lưu ý: strategy tốt nhất đã biết dùng COMPOSITE exit
(trail stop OR trend reversal signal) và 2 FILTERS (volume + regime).
Đây là một DATA POINT, không phải chỉ dẫn thiết kế.

======================================================================
D. ARTIFACTS BẮT BUỘC
======================================================================

Thư mục làm việc:
  /var/www/trading-bots/btc-spot-dev/research/x28/

Dữ liệu đầu vào (KHÔNG được sửa đổi):
  /var/www/trading-bots/btc-spot-dev/data/btcusdt_*.csv

Bắt buộc có:
- 01_data_audit.md
- 02_price_behavior_eda.md
- 03_signal_landscape_eda.md
- 04_formalization.md
- 05_go_no_go.md
- 06_design.md (nếu GO)
- 07_validation.md (nếu GO)
- 08_final_report.md
- manifest.json

Thư mục con:
- figures/  tables/  code/

======================================================================
E. TAGGING / PROVENANCE
======================================================================

- Fig##, Tbl##, Obs##, Hyp##, Prop##, Cand##, Test##
- Observation phải trỏ tới ≥ 1 Figure hoặc Table
- Proposition phải trỏ tới ≥ 1 Observation
- Candidate phải trỏ tới ≥ 1 Proposition VÀ ≥ 1 Observation
- Claim không có provenance → UNSUPPORTED

======================================================================
F. END-OF-PHASE CHECKLIST
======================================================================

Cuối mỗi phase, in ra:
1. Files created
2. Key Obs / Prop IDs created
3. Blockers / uncertainties
4. Gate status:
   PASS_TO_NEXT_PHASE | STOP_NO_ALPHA | STOP_INCONCLUSIVE |
   GO_TO_DESIGN | DESIGN_REJECTED | FINALIZED

======================================================================
G. QUY TRÌNH
======================================================================

Mỗi phase:
- Tôi review kết quả
- Tôi quyết định có tiếp tục không
- Tôi gửi prompt tiếp theo

Bạn KHÔNG được tự nhảy sang phase tiếp.
Code cho EDA/analysis: mọi phase — viết vào x28/code/.
Code cho strategy: chỉ Phase 7.
Propose candidate: chỉ Phase 6.
