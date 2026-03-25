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

Bạn đang ở PHASE 2: CONDITIONAL ANALYSIS AROUND ACTUAL TRADES.

Mục tiêu:
phân tích những gì xảy ra quanh các entry thực tế của base system.
Vẫn chưa được phép design. Vẫn chưa được phép formalize công thức filter.

Đầu vào:
- Data: /var/www/trading-bots/btc-spot/data/bars_btcusdt_h1_4h_1d.csv
- Strategy code: /var/www/trading-bots/btc-spot-dev/strategies/vtrend_ema21_d1/strategy.py
- Entry rule:
  EMA_fast(30) crosses above EMA_slow(120) trên H4 close
  AND D1 close > D1 EMA(21)
- Cost: 50 bps round-trip

Yêu cầu thực hiện:

0. Reproduce trades
- Reproduce chính xác trades từ strategy code
- Report số trades tạo được
- Nếu không ra gần 226 trades, dừng lại và nói rõ mismatch nằm ở đâu
- Lưu:
  - tables/trade_list.csv
  - tables/trade_repro_check.csv

1. Chia trades thành hai nhóm
- Winners: net trade return > 0 sau 50 bps RT cost
- Losers: net trade return <= 0
- Report:
  - số lượng mỗi nhóm
  - median return mỗi nhóm
  - median hold time mỗi nhóm
- Lưu:
  - Tbl04_trade_groups.csv

2. Volume profile quanh entry
- Với mỗi nhóm winners / losers:
  - median volume từ bar -20 đến +10 quanh entry
  - median taker_buy_ratio từ bar -20 đến +10
  - IQR shaded
- Plot:
  - Fig09: volume profile
  - Fig10: taker_buy_ratio profile
- Chỉ mô tả:
  - hai nhóm có tách biệt visually không
  - nếu có, tách biệt ở trước entry, tại entry, hay sau entry

3. Volatility profile quanh entry
- Tính ATR(20)/price từ bar -20 đến +10
- Plot:
  - Fig11
- Mô tả:
  - winners vào lúc vol cao hơn hay thấp hơn losers
  - khác biệt có local hay kéo dài

4. Statistical separation tại bar entry
Tính các feature sau tại entry:
- taker_buy_ratio (single bar)
- mean taker_buy_ratio 5 bars trước entry
- mean taker_buy_ratio 10 bars trước entry
- volume / rolling_median_volume(20)
- ATR(20) / price

Cho từng feature:
- Mann-Whitney U winners vs losers
- p-value
- rank-biserial effect size
- direction
- Lưu:
  - Tbl05_entry_separation.csv

5. VDO tại entry
- Nếu có code VDO:
  - tính VDO tại mỗi entry bar
  - plot histogram winners vs losers
  - scatter VDO vs trade return
  - Mann-Whitney test
- Plot:
  - Fig12 histogram
  - Fig13 scatter
- Lưu:
  - Tbl06_vdo_entry_stats.csv
- Nếu VDO không tách biệt được, nói thẳng là không tách biệt được

6. False entries
- Lấy 5 worst losers
- Plot:
  - Fig14a..Fig14e
  - price + volume + taker_buy_ratio
  - từ bar -20 đến +20 quanh entry
- Chỉ mô tả:
  - có pattern nào lặp lại nhìn bằng mắt không
  - hay chúng trông gần như giống winners tại entry

7. Observation log
Viết 8-12 observations.
Mỗi observation phải có:
- Obs##
- Statement
- Support: [Fig..], [Tbl..]

Bắt buộc có:
- 2 observations về “winners vs losers trông giống nhau ở đâu”
- 2 observations về “nếu có separation thì separation nằm ở đâu”
- 1 mục riêng: “What is visually tempting but statistically weak”

Deliverables bắt buộc:
- 02_trade_eda.md
- figures/Fig09..Fig14e
- tables/Tbl04..Tbl06
- code/phase2_trade_eda.py

Không được làm:
- Không interpret
- Không suggest
- Không thiết kế filter
- Không nêu tên candidate
- Không rationalize VDO

Lưu ý:

Đây là một quy trình nhiều phase với quy tắc "Observation before interpretation", mỗi phase cần:
- Tôi review kết quả
- Tôi quyết định có tiếp tục không
- Tôi sẽ gửi prompt tiếp theo để kích hoạt phase kế











======================================================================

All deliverables complete. Phase 2 summary:

Trade reproduction: 201 trades (E0 base = 226, minus 25 blocked by D1 EMA(21) filter). 78 winners (38.8%), 123 losers (61.2%).

Core findings (12 observations, Obs15-Obs26):

Area	Result
Volume profile	No separation (Fig09). Medians overlap completely.
TBR profile	No separation (Fig10). Mechanical rise at entry is identical for both groups.
Volatility profile	Winners slightly higher ATR, but persistent across window, not localized (Fig11). p=0.715 at entry.
5 entry features	All p > 0.39. No feature separates winners from losers (Tbl05).
VDO at entry	Marginal (p=0.086, r_rb=0.144). Only signal approaching significance, but does not pass 0.05. VDO-return correlation also non-significant (r=0.093, p=0.19).
5 worst losers	No common pattern at entry. They look like typical entries (Fig14a-e).
Gate: PASS_TO_NEXT_PHASE — The data is clear and all artifacts are generated. One marginal VDO signal exists but the overall picture is dominated by nulls. Phase 3 (formalization) can determine whether to proceed to design or call STOP.
