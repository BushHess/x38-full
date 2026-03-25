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

Bạn đang ở PHASE 6: FINAL RESEARCH MEMO.

Đầu vào:
- toàn bộ artifacts từ các phase trước

Mục tiêu:
viết một final report sạch, thẳng, không né tránh.

Cấu trúc bắt buộc:

1. Executive conclusion
Chọn đúng một:
- Keep VDO: headroom too small
- Keep VDO: volume information ceiling too low
- Replace VDO with Cand##
- Inconclusive: need more data / different alpha surface

2. Research path
- Tóm tắt phase 1 -> phase 5
- mỗi phase 2-4 câu
- chỉ nêu cái đã thực sự được làm

3. Strongest evidence
- 5-8 findings mạnh nhất
- mỗi finding phải có provenance tags

4. What failed
- những giả thuyết / class hàm / candidate nào đã bị loại
- loại vì lý do gì

5. Mathematical conclusion
- volume/taker_buy thực sự mang information gì
- information đó có usable không
- usable ở class hàm nào
- hay không đủ để justify filter mới

6. Practical recommendation
Nếu không thay VDO:
- nói thẳng alpha nên tìm ở đâu tiếp theo:
  exit / regime / sizing / more data / different instrument structure

Nếu thay VDO:
- nêu candidate được chọn
- lý do ngắn gọn
- caveats

7. Anti-self-deception section
Bắt buộc có một mục tên:
“What would make this conclusion wrong?”
Trong đó nêu:
- assumptions dễ sai nhất
- phần nào còn underpowered
- điều kiện nào có thể đảo ngược kết luận

8. Final status line
Chọn đúng một:
- FINALIZED_KEEP_VDO
- FINALIZED_REPLACE_WITH_CAND##
- FINALIZED_INCONCLUSIVE

Deliverables bắt buộc:
- 07_final_report.md
- cập nhật manifest.json

Cấm:
- Không quảng cáo candidate nếu evidence không đủ
- Không làm giọng “có vẻ hứa hẹn” nếu validation không qua
- Không che failure bằng ngôn ngữ mơ hồ

Lưu ý:

Đây là một quy trình nhiều phase với quy tắc "Observation before interpretation", mỗi phase cần:
- Tôi review kết quả
- Tôi quyết định có tiếp tục không
- Tôi sẽ gửi prompt tiếp theo để kích hoạt phase kế



=======================================================================
Done. Here's the summary:

Phase 6: FINALIZED_KEEP_VDO

The final report is at 07_final_report.md.

Executive conclusion: Keep VDO — volume information ceiling too low. The existing VDO > 0 gate is at or near the extractable optimum. I(ΔU; V_t | P_t) ≤ 2% of variance, and the strongest residual signal (VDO level, p=0.086, d≈0.29) is below the MDE of 0.406.

Key evidence chain:

5/5 volume/TBR features fail at entry (all p > 0.39) → Prop01
Volume profiles identical W vs L across 30-bar window → Obs15
TBR→return is non-stationary (sign oscillates 3-6 months) → Prop04
Volume is directionally symmetric → Prop05
VDO residual is truncated, underpowered, likely artifactual → Prop02
Convergent from X21: entry features have zero CV IC
Phases 5-6 skipped per STOP gate. No candidates designed, no validation performed. This is an honest stopping conclusion.

Next alpha directions: cost reduction (Sharpe 1.19→1.67 at 15 bps), longer-horizon regime research, different instrument structure (perpetuals/funding), execution quality.
