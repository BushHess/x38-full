# 04 — X39 Residual Sprint Playbook

## 1. Vai trò của x39 trong hệ thống này

x39 **không** phải nơi chọn baseline chính thức.  
x39 là nơi:
- phát minh concept mới,
- kiểm tra residual hypothesis nhanh,
- làm characterization,
- đóng gói challenger đủ chín để gửi lên x40.

Nếu x39 tự ra verdict authoritative, hệ thống sẽ drift.

---

## 2. Khi nào mới được mở x39 sprint

Chỉ mở khi:
- league có baseline active (`B1_QUALIFIED` hoặc `B0_INCUMBENT`),
- baseline đó không `BROKEN`,
- `next_action` cho phép sprint trong league đó,
- sprint brief đã chỉ rõ incumbent là ai và mục tiêu challenge là gì.

Nếu chưa có các điều trên => không mở sprint.

---

## 3. Mục tiêu đúng của sprint

Mục tiêu **không** phải:
- scan thêm 100 formulas,
- cherry-pick config đẹp,
- beat baseline bằng simplified replay rồi tự tuyên bố thắng.

Mục tiêu đúng là:
- nhìn đúng residual của baseline active,
- phát minh ra concept family có claim rõ,
- giết family đó bằng falsification trước khi yêu cầu x40 replay canonical.

---

## 4. Sprint inputs bắt buộc từ x40

Mỗi sprint phải đọc:
- `baseline_manifest.json`
- `durability_summary.json`
- `a04_directional_research_advice.json`
- `next_action.md`
- `forward_evaluation_ledger.csv`
- relevant trade/episode extracts của incumbent

Nếu sprint không đọc `next_action.md`, sprint coi như mở sai.

---

## 5. Sprint types

## 5.1 GENERAL_RESIDUAL
Dùng khi:
- baseline còn sống,
- chưa có bằng chứng mạnh entry đã cạn hoặc exit mới là nơi còn lại.

## 5.2 EXIT_FOCUSED
Dùng khi:
- A04 cho thấy entry residuals null,
- exit/path-quality/de-risking có giá trị hơn.

## 5.3 CHARACTERIZATION_ONLY
Dùng khi:
- muốn hiểu mechanism,
- chưa có ý định build overlay/replace ngay.

---

## 6. Quy trình sprint chuẩn

## S0 — Residual brief
X40 phải cấp cho sprint brief:
- incumbent baseline
- target league
- current durability state
- current weak points
- primary research focus
- forbidden directions

## S1 — Episode explorer
Không bắt đầu từ công thức. Bắt đầu từ episode.

Mỗi sprint phải trích ít nhất:
- 20 best trades
- 20 worst trades
- 20 stop-out rồi continuation
- 20 missed moves
- 20 extreme bars / sequences

Mỗi episode phải hiển thị:
- context trước/sau,
- signals incumbent,
- ATR / VDO / EMA / range position / volume anomalies (nếu có),
- annotation bằng mắt.

### Câu hỏi phải hỏi
- baseline sai ở đâu?
- baseline vào đúng nhưng thoát sai ở đâu?
- baseline không vào nhưng sau đó giá chạy mạnh vì sao?
- có hình dạng path nào lặp đi lặp lại mà baseline chưa đo?

## S2 — Concept card
Không được nhảy thẳng vào formula. Mỗi ý tưởng phải có `concept_card.md` trước.

### Concept card bắt buộc có
- tên khái niệm
- motivation
- claim: đo cái gì
- non-claim: **không** đo cái gì
- observable domain
- expected signature
- expected failure mode
- counterexample
- family sketch
- type: `entry` / `exit` / `filter` / `characterization`

## S3 — Family formalization
Mỗi concept phải có **một family**, không phải một công thức đơn lẻ.

### Quy tắc
- tối thiểu 5 variants
- tối đa 20 variants trong một family
- variants phải là láng giềng hợp lý của cùng concept
- không được nhảy lung tung giữa nhiều concept trong cùng family

### Ví dụ
Nếu concept là “failed expansion” thì family có thể thay:
- lookback,
- range normalization,
- close-position clause,
- persistence clause,
- reabsorption window

Nhưng không được lẫn sang concept hoàn toàn khác.

## S4 — Kill battery
Mỗi family phải đi qua tối thiểu 8 cổng:

1. **Semantic admissibility**  
   Có đang nói quá dữ liệu không?
2. **Null / falsification**  
   Có còn “work” trên dữ liệu surrogate hoặc shuffled mechanism không?
3. **Robustness to formalization**  
   Lân cận công thức có cùng dấu không?
4. **Temporal stability**  
   Có chỉ sống ở một đoạn lịch sử không?
5. **Orthogonality**  
   Có chỉ là bản sao EMA/VDO/ATR/regime không?
6. **Multi-timeframe meaning**  
   Hành vi có nghĩa nhất quán trên clock liên quan không?
7. **Incremental value vs incumbent**  
   Thêm vào baseline có cải thiện thực không?
8. **Cost robustness**  
   Có chết ngay khi chi phí tăng vừa phải không?

Nếu chết ở bất kỳ cổng nào, ghi rõ lý do chết. Không cứu.

## S5 — Promotion package
Chỉ family nào sống mới được đóng gói gửi về x40.

Package bắt buộc có:
- `concept_card.md`
- `feature_family.md`
- exact formulas
- robustness grid
- falsification summary
- simplified replay delta vs incumbent
- recommendation:
  - `entry`
  - `exit`
  - `filter`
  - `replace`
  - `characterization`

## S6 — Handoff
Không được merge vào baseline.  
Chỉ được nộp package cho x40 canonical replay.

---

## 7. Ba lane phát minh ý tưởng được phép dùng

Để generate concept, sprint được dùng cả ba lane:

1. **behavior -> signature**  
   từ hành vi / mechanism suy ra dấu vết;
2. **anomaly observation**  
   thấy pattern lạ trong episodes rồi formalize;
3. **statistical invariants**  
   từ cấu trúc thống kê ổn định suy ra measurement mới.

Nhưng nhớ:
- story chỉ để generate,
- data mới judge.

---

## 8. Anti-patterns phải cấm

- dùng simplified replay để tự promote,
- formula lottery,
- chọn config đẹp nhất rồi retro-explain,
- trộn league,
- dùng `PF0` như thể nó là OHLCV-only,
- thêm feature nhưng không khai báo claim/non-claim,
- bỏ qua falsification,
- cứu family chết bằng post-hoc tuning.

---

## 9. Thứ nên ưu tiên đầu tiên

Với evidence hiện tại, sprint đầu tiên **nên ưu tiên exit-focused hoặc path-quality-focused** trước khi quay lại entry-focused, trừ khi A04 chứng minh entry residuals còn rõ.

Các family ưu tiên:
- failed expansion / reabsorption
- effort-vs-progress persistence
- path-quality deterioration
- maturity / exhaustion exits
- anti-crowding de-risking

---

## 10. Sprint stop rules

Dừng sprint nếu:
- 3 concept families liên tiếp chết sạch ở kill battery,
- hoặc simplified replay chỉ cho delta mỏng và không robust,
- hoặc A04 / next_action cho thấy sprint đi sai hướng.

Khi dừng, phải ghi:
- cái gì đã thử,
- chết ở cổng nào,
- bài học gì,
- có cần `open_x37_challenge` không.

---

## 11. Quy tắc một câu

x39 không có nhiệm vụ “tìm cái gì chạy đẹp.”  
x39 có nhiệm vụ **tìm ra challenger đáng để x40 nghiêm túc tốn tài nguyên replay canonical**.
