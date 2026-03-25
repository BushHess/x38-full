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

Bạn đang ở PHASE 4: SYNTHESIS / GO-NO-GO DECISION.

Đầu vào:
- 01_raw_eda.md
- 02_trade_eda.md
- 03_formalization.md
- toàn bộ figures/tables liên quan

Mục tiêu:
tổng hợp evidence thực nghiệm + formalization và ra một kết luận rõ ràng.
Vẫn chưa được design ở phase này.

Bạn phải chọn MỘT trong 4 kết luận sau:

(A) Có incremental information rõ ràng trong volume/taker_buy,
    VDO chưa capture hết, và tồn tại ít nhất một admissible low-DOF class
    có expected effect size đủ lớn để đáng thiết kế.

(B) Có một ít information, nhưng VDO đã capture phần lớn.
    Improvement headroom rất nhỏ; không đáng mở nhánh design.

(C) Volume/taker_buy gần như không mang incremental information đáng kể
    so với price-only cho bài toán entry timing này.
    Entry filter volume-based có ceiling thấp.

(D) Evidence mâu thuẫn / yếu / underpowered.
    Chưa đủ cơ sở để design, nhưng cũng chưa đủ để tuyên bố
    volume vô ích. Kết luận đúng là inconclusive.

Yêu cầu trả lời theo cấu trúc sau:

1. What the data actually showed
- Tóm tắt 6-10 findings quan trọng nhất
- Mỗi finding phải trỏ tới [Obs..] và [Fig../Tbl..]

2. What survived formalization
- Tóm tắt 3-6 propositions còn đứng vững
- Mỗi proposition phải trỏ tới [Prop..]

3. SNR / detectability judgment
- Nói thẳng:
  - information mạnh hay yếu
  - stable hay regime-dependent
  - detectable hay underpowered

4. VDO judgment
- VDO đang:
  - capture phần lớn,
  - bỏ lỡ một phần rõ ràng,
  - hay bản thân bài toán đã có ceiling thấp
- Không được trả lời chung chung

5. Chọn đúng MỘT kết luận: A, B, C, hoặc D
- Phải viết 1 đoạn justification chặt
- Phải có provenance tags

6. Gate
- Nếu A:
  viết thêm 2 dòng:
  - Exact pattern to exploit:
  - Admissible function class to design:
- Nếu B/C/D:
  dừng lại.
  Viết:
  - “Do not design a new filter.”
  - “Final direction for alpha search: [exit / regime / sizing / more data]”

Deliverables bắt buộc:
- 04_go_no_go.md
- cập nhật manifest.json

Không được làm:
- Không design
- Không nêu công thức cuối cùng
- Không đề xuất “thử vài candidate”

Lưu ý:

Đây là một quy trình nhiều phase với quy tắc "Observation before interpretation", mỗi phase cần:
- Tôi review kết quả
- Tôi quyết định có tiếp tục không
- Tôi sẽ gửi prompt tiếp theo để kích hoạt phase kế



=======================================================================

Phase 4 complete. Here's the summary:

Phase 4: STOP_VDO_NEAR_OPTIMAL — Conclusion (B)
Decision: Do not design a new volume/microstructure entry filter. VDO > 0 has already captured the bulk of extractable volume information.

Key evidence chain:

Comprehensive nulls on non-VDO features — 5 features × multiple lookbacks all fail at entry bar (p > 0.39, |r_rb| < 0.08) [Prop01 ← Obs15, Obs16, Obs17]. Volume and TBR carry no incremental entry-bar information.

VDO residual is marginal and likely artifactual — The sole approaching-significance signal (p=0.086, d≈0.29) is below MDE of 0.41. VDO-return correlation is NOT significant (p=0.190). The truncated distribution at VDO=0 compresses dynamic range to IQR 0.001–0.010 [Prop02 ← Obs18, Obs24, Obs25].

Non-stationarity kills TBR-based designs — Rolling correlation oscillates in sign with 3–6 month half-cycles [Prop04 ← Obs07]. No stable relationship to exploit.

Convergent external evidence — X21 (Conviction Sizing) independently found zero IC for entry features (CV IC = -0.039). The information is exhausted.

Power constraints — Even the best-case design (Class A, 1 DOF VDO tightening) achieves ~45% power. More likely to produce an inconclusive result than a discovery.

Final direction for alpha search: Cost reduction (X22 showed Sharpe 1.19→1.67 at 15 bps) and execution quality — the largest marginal gain comes from reducing transaction costs, not adding entry filters.

Files created: 04_go_no_go.md
Manifest updated: phases 04=DONE, 05/06=SKIPPED.
