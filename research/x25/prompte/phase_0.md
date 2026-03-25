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
/var/www/trading-bots/btc-spot-dev/research/entry_filter_lab/

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

Lưu ý:

Đây là một quy trình nhiều phase với quy tắc "Observation before interpretation", mỗi phase cần:
- Tôi review kết quả
- Tôi quyết định có tiếp tục không
- Tôi sẽ gửi prompt tiếp theo để kích hoạt phase kế




=======================================================================
Workspace ready:


research/entry_filter_lab/
├── manifest.json
├── figures/
├── tables/
└── code/
Protocol acknowledged:

Empirical-first, observation before interpretation, candidate moratorium
Provenance tagging (Fig/Tbl/Obs/Hyp/Prop/Cand/Test)
End-of-phase checklist with gate status
You review and trigger each phase
Data verified: bars_btcusdt_h1_4h_1d.csv exists with columns: symbol, interval, open_time, close_time, OHLCV, quote_volume, num_trades, taker_buy volumes.

Waiting for your prompt to start Phase 00: Data Audit.
