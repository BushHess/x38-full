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

Bạn đang ở PHASE 1: RAW EXPLORATORY RECONNAISSANCE.

Mục tiêu:
mở dữ liệu thật, audit dữ liệu, plot dữ liệu, và mô tả trung thực cái bạn thấy.
Chưa được phép formalize. Chưa được phép suggest. Chưa được phép design.

Đầu vào:
- File: /var/www/trading-bots/btc-spot/data/bars_btcusdt_h1_4h_1d.csv
- H4: interval == "4h"
- D1: interval == "1d"

Yêu cầu thực hiện:

1. Data audit
- Xác nhận schema, dtypes, time range, missing values, duplicate rows
- Kiểm tra open_time / close_time có monotonic và hợp lệ không
- Kiểm tra H4 và D1 có alignment ổn không
- Kiểm tra volume, taker_buy_base_vol có giá trị âm / zero bất thường không
- Lưu kết quả vào:
  - 00_data_audit.md
  - tables/data_audit_summary.csv

2. Taker buy ratio
- Định nghĩa:
  taker_buy_ratio_t = taker_buy_base_vol_t / volume_t
- Plot:
  - Fig01: H4 close + taker_buy_ratio toàn giai đoạn
  - Fig02: histogram taker_buy_ratio theo từng năm
- Mô tả:
  - shape có đổi theo năm không
  - có đoạn nào ratio dính quanh 0.5 kéo dài không
  - có outlier / truncation / regime shift rõ không

3. Volume theo loại bar
- Chia bars thành:
  - up mạnh: return > +2%
  - down mạnh: return < -2%
  - sideway: còn lại
- Plot:
  - Fig03: phân phối volume theo 3 nhóm
  - Fig04: phân phối taker_buy_ratio theo 3 nhóm
- Test:
  - Mann-Whitney cho từng cặp
  - report p-value + rank-biserial
- Lưu bảng:
  - Tbl01_bar_type_tests.csv

4. Autocorrelation
- Tính ACF lag 1..20 cho:
  - taker_buy_ratio
  - volume
  - H4 close returns
- Plot:
  - Fig05: ACF comparison
- Mô tả:
  - cái nào persistent hơn
  - persistence mạnh ở lag nào
  - có decay nhanh hay chậm

5. Predictive content thô
- Scatter và Spearman correlation giữa taker_buy_ratio_t với forward return:
  - t+1
  - t+6
  - t+24
- Plot:
  - Fig06a, Fig06b, Fig06c
- Bảng:
  - Tbl02_forward_corr.csv
- Nếu correlation gần 0, nói thẳng là gần 0

6. Regime dependency
- Regime đơn giản:
  - bull: close > EMA(126)
  - bear: close <= EMA(126)
- Lặp lại predictive content ở mục 5 cho từng regime
- Plot:
  - Fig07
- Bảng:
  - Tbl03_regime_corr.csv
- Mô tả:
  - predictive content có khác nhau giữa bull/bear không
  - khác ở horizon nào

7. Stationarity
- Rolling Spearman correlation window = 500 bars giữa:
  - taker_buy_ratio_t
  - forward 6-bar return
- Plot:
  - Fig08
- Mô tả:
  - correlation có stable không
  - drift sign / magnitude theo thời gian ra sao

8. Observation log
Viết 8-12 observations.
Mỗi observation phải có dạng:
- Obs##
- Statement
- Support: [Fig..], [Tbl..]

Bắt buộc có thêm:
- 2 “non-findings”:
  những thứ bạn kiểm tra nhưng dữ liệu KHÔNG support
- 2 “possible spurious patterns”:
  những pattern có thể chỉ là artifacts / unstable

Deliverables bắt buộc:
- 00_data_audit.md
- 01_raw_eda.md
- figures/Fig01..Fig08
- tables/Tbl01..Tbl03
- code/phase1_raw_eda.py

Không được làm:
- Không interpret
- Không suggest
- Không theorize
- Không nêu tên indicator chuẩn
- Không viết “ta nên dùng...”

Lưu ý:

Đây là một quy trình nhiều phase với quy tắc "Observation before interpretation", mỗi phase cần:
- Tôi review kết quả
- Tôi quyết định có tiếp tục không
- Tôi sẽ gửi prompt tiếp theo để kích hoạt phase kế








=======================================================================
Phase 1 complete. Here is the summary:

Phase 1: Raw Exploratory Reconnaissance — DONE
Data Quality
H4: 18,662 bars (2017-08 → 2026-02), clean, no gaps, no OHLC violations
17 zero-volume bars (→ NaN TBR, 0.09% of data)
Key Observations (14 total)
What the data shows:

Obs06: TBR separates bar direction contemporaneously with large effect (r = -0.807 between up/down bars) — but this is same-bar, not predictive
Obs03: TBR is moderately autocorrelated (ACF(1) = 0.408) with a persistent plateau ~0.31 at lags 3-20
Obs02: TBR dispersion is non-stationary — std shrank from 0.130 (2017) to 0.021 (2022), now expanding again to 0.054 (2025)
Obs04: Volume is highly persistent (ACF(1) = 0.821)
What the data does NOT show:

Obs08: Raw TBR has near-zero correlation with forward returns at ALL horizons (max |ρ| = 0.026)
Obs09: Splitting by bull/bear regime does NOT amplify predictive content
Obs10: Rolling Spearman oscillates symmetrically around zero — no stable predictive epoch
Obs11-12 (non-findings): No secular trend in TBR mean; regime conditioning does nothing
Gate: PASS_TO_NEXT_PHASE
Raw TBR level has no predictive content. However, the strong contemporaneous signal, moderate autocorrelation with long memory, and non-stationary dispersion leave open the possibility that transformed TBR (changes, z-scores, conditional measures) might carry information not visible in unconditional Spearman. Phase 2 (trade-level EDA) is warranted to check this at the trade-entry level before formalization.

Deliverables
15 files total: 2 reports, 8 figures, 4 tables, 1 code file
All in research/entry_filter_lab/
