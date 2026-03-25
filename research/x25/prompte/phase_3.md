RESEARCH OPERATING PROTOCOL — PHẢI GIỮ NGUYÊN TRONG MỌI PHASE

Bạn không phải là “indicator generator”.
Bạn đang đóng vai một research agent làm việc theo giao thức lab:
quan sát dữ liệu -> mô tả -> formalize -> ra quyết định go/no-go -> chỉ khi cần mới thiết kế.

Mục tiêu của bạn không phải là “đưa ra một ý tưởng hay”.
Mục tiêu của bạn là:
(1) tạo evidence,
(2) ghi nhận cả evidence ủng hộ lẫn phản bác,
(3) formalize đúng cái dữ liệu support,
(4) dừng lại nếu dữ liệu không support.

======================================================================
A. QUY TẮC PHƯƠNG PHÁP
======================================================================

1. Empirical-first
- Nếu phase yêu cầu plot, audit, hoặc exploratory:
  phải mở dữ liệu thật, chạy code, tạo artifacts thật.
- Không được giả vờ như đã plot nếu chưa plot.
- Nếu dữ liệu/code không truy cập được, dừng lại và nói rõ.

2. Observation before interpretation
- Khi prompt nói “chỉ mô tả”, bạn chỉ được mô tả cái nhìn thấy.
- Không được dùng câu kiểu:
  “điều này gợi ý rằng ta nên…”
  “có thể dùng indicator…”
  “một filter hợp lý là…”
- Những câu đó chỉ được phép xuất hiện ở phase được cho phép.

3. Candidate moratorium
- Trước phase design, không được nêu tên indicator chuẩn,
  không được đề xuất signal, threshold, hay formula cuối cùng.
- Nếu bạn làm vậy, coi toàn bộ phase là INVALID và tự khởi động lại.

4. Derive before propose
- Mọi candidate ở phase design phải truy ngược được về:
  - Figure ID
  - Observation ID
  - Proposition ID
- Nếu không truy ngược được, candidate đó bị loại.

5. Anti-post-hoc
- Không được nhớ ra một indicator có sẵn rồi bọc nó bằng ngôn ngữ toán học.
- Nếu candidate cuối cùng tương đương với một indicator quen thuộc,
  bạn phải giải thích vì sao nó xuất hiện như hệ quả tất yếu
  của evidence + formalization, không phải vì hồi tưởng.

6. Honest stopping
- “Không có signal đủ mạnh”
- “VDO đã gần optimal”
- “Volume information ceiling thấp”
- “Evidence underpowered / inconclusive”
đều là kết luận hợp lệ.
Không được cố thiết kế chỉ để có cái gì đó mới.

======================================================================
B. RÀNG BUỘC KỸ THUẬT
======================================================================

Bài toán:
- BTC spot, H4 trend-following, long-only
- Base entry: EMA_fast(30) cross above EMA_slow(120) trên H4 close
- Regime filter: D1 close > D1 EMA(21)
- Exit: trailing stop ATR-based hoặc EMA cross-down
- Chỉ nghiên cứu entry filter volume/microstructure
- Không đổi exit
- Không đổi bản chất long-only

Dữ liệu:
- /var/www/trading-bots/btc-spot/data/bars_btcusdt_h1_4h_1d.csv
- H4: interval == "4h"
- D1: interval == "1d"

Ràng buộc:
- Entry filter tối đa 2 tham số tự do
- Pipeline tổng DOF mục tiêu <= 6
- Sample khoảng 226 trades
- Phải tôn trọng causality, không lookahead
- Phải chịu được regime switching
- Không ensemble / ML / high-DOF controller

======================================================================
C. ARTIFACTS BẮT BUỘC
======================================================================

Tạo và duy trì thư mục làm việc:
research/entry_filter_lab/

Bắt buộc có các file sau:
- research/entry_filter_lab/00_data_audit.md
- research/entry_filter_lab/01_raw_eda.md
- research/entry_filter_lab/02_trade_eda.md
- research/entry_filter_lab/03_formalization.md
- research/entry_filter_lab/04_go_no_go.md
- research/entry_filter_lab/05_design.md
- research/entry_filter_lab/06_validation.md
- research/entry_filter_lab/07_final_report.md
- research/entry_filter_lab/manifest.json

Thư mục con:
- research/entry_filter_lab/figures/
- research/entry_filter_lab/tables/
- research/entry_filter_lab/code/

======================================================================
D. TAGGING / PROVENANCE
======================================================================

Mọi phase phải dùng các tag sau:

- Fig01, Fig02, ...
- Tbl01, Tbl02, ...
- Obs01, Obs02, ...
- Hyp01, Hyp02, ...
- Prop01, Prop02, ...
- Cand01, Cand02, ...
- Test01, Test02, ...

Quy tắc:
- Observation phải trỏ tới ít nhất một Figure hoặc Table.
- Proposition phải trỏ tới ít nhất một Observation.
- Candidate phải trỏ tới ít nhất một Proposition và một Observation.
- Kết luận cuối phải trỏ tới ít nhất:
  - 2 observations
  - 1 proposition
  - 1 validation result (nếu có design)

Nếu một claim không có provenance tag, đánh dấu nó là:
UNSUPPORTED
và không được dùng để kết luận.

======================================================================
E. END-OF-PHASE CHECKLIST
======================================================================

Cuối mỗi phase, luôn in ra đúng 4 mục:

1. Files created
2. Key Obs / Prop IDs created
3. Blockers / uncertainties
4. Gate status:
   - PASS_TO_NEXT_PHASE
   - STOP_NO_SIGNAL
   - STOP_VDO_NEAR_OPTIMAL
   - STOP_INCONCLUSIVE
   - GO_TO_DESIGN
   - DESIGN_REJECTED
   - FINALIZED

[PREPEND PROMPT 0 Ở TRÊN]

Bạn đang ở PHASE 3: FORMALIZATION FROM EVIDENCE.

Đầu vào được phép dùng:
- 01_raw_eda.md
- 02_trade_eda.md
- các figures/tables của phase 1 và 2

Bạn không được phép mở phase này bằng một candidate.
Bạn không được phép nêu tên indicator chuẩn.
Bạn không được phép “nhớ ra” công thức.
Bạn phải formalize từ evidence đã có.

Mục tiêu:
định nghĩa đúng bài toán quyết định, xác định information set,
và suy ra class hàm admissible dưới các ràng buộc DOF / detectability / causality.

Yêu cầu thực hiện:

1. Formalize decision problem
Định nghĩa:
- E_t = event “base system phát tín hiệu entry tại bar t”
- a_t ∈ {0,1}:
  - 1 = cho phép entry
  - 0 = chặn entry

Định nghĩa một đại lượng utility hợp lý:
ΔU_t = utility(accept entry at t) - utility(reject entry at t)

Bạn phải nói rõ:
- entry filter đang cố tối ưu cái gì
- ΔU_t nên được hiểu như expectancy improvement, utility-adjusted return,
  hoặc proxy nào
- tại sao definition đó phù hợp với long-only trend-following trên BTC H4

2. Formalize information sets
Định nghĩa rõ:
- P_t = price-only information available at t
- V_t = volume / taker_buy information available at t

Phân tích:
- volume/taker_buy có mang incremental information cho ΔU_t ngoài P_t không
- formalize quanh đối tượng:
  I(ΔU_t ; V_t | P_t)
hoặc một formalism tương đương nếu bạn thấy mutual information
không phải cách diễn đạt tốt nhất với sample này

3. Build propositions from evidence
Viết 3-6 propositions:
- Prop##
- Statement
- Support: [Obs..]
- Confidence: high / medium / low

Ví dụ kiểu proposition hợp lệ:
- một đại lượng volume chỉ mang information dưới regime nào đó
- information nằm ở ratio chứ không nằm ở level tuyệt đối
- information tồn tại nhưng SNR quá thấp để justify thêm DOF
- predictive content chỉ xuất hiện ở anomaly chứ không ở level
- cái tưởng như informative thực ra chỉ là noisy echo của price

4. Derive admissible function classes
Dưới các ràng buộc:
- causality
- scale invariance hoặc normalization hợp lý
- regime robustness
- <= 2 DOF
- detectability với ~226 trades
- chống overfit trong WFO/bootstrap/jackknife

Hãy suy ra class hàm nào là admissible.
Ví dụ ở mức class, không phải candidate:
- scalar threshold trên normalized statistic
- conditional threshold theo 1 state variable
- anomaly detector kiểu percentile / z-score
- signed imbalance với 1 horizon
- v.v.

Với mỗi class:
- vì sao admissible
- vì sao compact
- mất thông tin gì nếu nén về scalar
- DOF cost là bao nhiêu

5. Reject inadmissible classes
Viết 3-6 class hàm bị loại.
Ví dụ lý do loại:
- cần quá nhiều DOF
- không detect được với n~226
- đòi hỏi stationarity quá mạnh
- không truy ngược được về evidence
- chỉ là post-hoc rephrasing của pattern yếu

6. Detectability / power
Không cần đưa ra con số “chuẩn xác tuyệt đối”.
Nhưng phải lập luận về order-of-magnitude:
- với ~226 trades, mức effect size nào là quá nhỏ để đáng theo đuổi
- mức improvement kiểu ΔSharpe nào mới đáng test nghiêm túc
- loại thiết kế nào gần như chắc underpowered
- loại thiết kế nào có hy vọng tạo effect size đủ lớn

7. Kết luận phase
Kết thúc file bằng đúng 3 mục:
- Allowed function classes
- Rejected function classes
- Design gate recommendation:
  - GO_TO_SYNTHESIS_WITH_REAL_HEADROOM
  - GO_TO_SYNTHESIS_BUT_EXPECT_SMALL_HEADROOM
  - GO_TO_SYNTHESIS_NO_INCREMENTAL_INFO
  - GO_TO_SYNTHESIS_INCONCLUSIVE

Deliverables bắt buộc:
- 03_formalization.md
- code/phase3_formalization_notes.py (nếu có code hỗ trợ)
- cập nhật manifest.json

Không được làm:
- Không nêu candidate formula cuối cùng
- Không nêu indicator chuẩn
- Không nói “hãy thử X”
- Không nhảy sang backtest

Lưu ý:

Đây là một quy trình nhiều phase với quy tắc "Observation before interpretation", mỗi phase cần:
- Tôi review kết quả
- Tôi quyết định có tiếp tục không
- Tôi sẽ gửi prompt tiếp theo để kích hoạt phase kế




=======================================================================
Phase 3 complete. Here's the summary:

6 Propositions formalized (all derived from Phase 1–2 evidence):

Prop01 (HIGH): Volume/TBR carry zero incremental info at entry
Prop02 (MEDIUM): VDO marginal signal (p=0.086) likely a truncation artifact
Prop03 (HIGH): Pre-entry TBR rise is mechanical, not predictive
Prop04 (HIGH): TBR→return relationship non-stationary, negligible
Prop05 (HIGH): Volume is directionally symmetric — useless for long-only
Prop06 (MED-HIGH): Volatility gap is regime-level, not entry-bar
3 Admissible function classes: VDO threshold tightening (1 DOF), volume percentile gate (1–2 DOF), regime-conditional VDO (2 DOF). Only Class A has any evidence support, and even that is marginal.

6 Rejected classes: Multi-feature models, TBR-based anything, volume directionality, lookback TBR anomaly, volatility gate, volume temporal patterns.

Critical power finding: MDE = 0.406 (Cohen's d) at 80% power. The strongest observed signal (VDO, d ≈ 0.29) is below the detection threshold. VDO explains ~2.1% of win/lose variance. Any validation will likely be inconclusive.

Gate: GO_TO_SYNTHESIS_BUT_EXPECT_SMALL_HEADROOM — proceeding is not unreasonable (Class A has minimal overfit risk), but the evidence strongly suggests VDO > 0 is already near the extractable optimum for volume information at entry.
