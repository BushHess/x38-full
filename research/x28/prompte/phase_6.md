PHASE 6: DESIGN
======================================================================

Điều kiện: Phase 5 = GO_TO_DESIGN. Nếu không → SKIP phase này.

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x28/prompte/phase_0.md
  Đọc deliverables Phase 2 (observations, Obs## tags):
  - /var/www/trading-bots/btc-spot-dev/research/x28/02_price_behavior_eda.md
  Đọc deliverables Phase 3 (signal landscape, impact analysis, TOP-N):
  - /var/www/trading-bots/btc-spot-dev/research/x28/03_signal_landscape_eda.md
  Đọc deliverables Phase 4 (function classes, propositions, DOF):
  - /var/www/trading-bots/btc-spot-dev/research/x28/04_formalization.md
  Đọc deliverables Phase 5 (go/no-go, design constraints):
  - /var/www/trading-bots/btc-spot-dev/research/x28/05_go_no_go.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/
- Function classes đã chọn từ Phase 4
- Design constraints từ Phase 5 Section 6
- Phase 3 TOP-N analysis (Tbl_top20_sharpe)
- Phase 3 impact analysis (Tbl_sharpe_drivers)
- Phase 3 decomposition (Tbl_decomposition)

Mục tiêu:
Thiết kế candidate algorithms CỤ THỂ, MINIMAL, TESTABLE.
Mỗi candidate là một COMPLETE pipeline (entry + exit + filter nếu cần).

======================================================================
1. CANDIDATE SELECTION — DATA-DRIVEN (KHÁC X27)
======================================================================

Candidates PHẢI được chọn từ Phase 3 grid results, KHÔNG từ trực giác.

Quy trình:
a. Lấy Tbl_top20_sharpe từ Phase 3 Part E
b. Lấy design constraints từ Phase 5 Section 6
c. Filter TOP-20 theo constraints (e.g., exposure ≥ X%, avg_loser ≤ Y%)
d. Từ configs thỏa constraints, chọn ≤ 3 candidates:
   - Cand01: TOP-1 config thỏa constraints (highest Sharpe)
   - Cand02: TOP config khác KIỂU so với Cand01
     (khác entry type HOẶC khác exit type — đảm bảo diversity)
   - Cand03 (optional): TOP config khác cả Cand01 và Cand02

Nếu TOP-1 đã chứa composite exit → Cand01 CÓ composite exit.
Nếu TOP-1 là simple exit → Cand02 PHẢI là composite exit
(để đảm bảo ít nhất 1 composite candidate nếu Phase 3 decomposition
cho thấy composite contributes > 0.05 Sharpe).

KHÔNG được tự nghĩ ra candidate ngoài Phase 3 grid.
Candidate = Phase 3 config + Phase 4 function class constraints.

======================================================================
2. CANDIDATE SPECIFICATION (mỗi candidate)
======================================================================

- Cand## ID
- SOURCE: "Tbl_top20_sharpe rank #N, grid config [entry_type × exit_type × filter]"
- PROVENANCE CHAIN: Cand## ← Prop## ← Obs## ← Fig##/Tbl##
  (chain phải complete — nếu thiếu bước nào → candidate bị loại)
- CONSTRAINT SATISFACTION: kiểm tra từng constraint từ Phase 5
  | Constraint | Required | Candidate Value | PASS/FAIL |
- Complete rule set:
  - Entry condition: exact formula, thời điểm evaluate
  - Exit condition: exact formula (CÓ THỂ là composite: "exit nếu A OR B")
  - Filter condition: exact formula (nếu có)
  - Position sizing: rule (e.g., fixed fraction, vol-target)
- All parameters: name, default value, admissible range
- DOF count: phải ≤ 10 tổng pipeline

======================================================================
3. PARAMETER DEFAULTS — EVIDENCE-BASED
======================================================================

Mỗi parameter default PHẢI có justification từ evidence:
  "lookback = 40 vì ACF returns significant đến lag ~40 (Obs##, Fig##)"
  "trail_mult = 3.0 vì exit frontier optimal ở capture 65%+ (Obs##, Fig##)"

KHÔNG được dùng: "common value", "standard", "typical", "industry practice"

Nếu không có evidence cho default → chọn TRUNG ĐIỂM của admissible range
  và nói rõ "no evidence — midpoint of range"

Nếu Phase 3 grid đã sweep parameter space → dùng optimal value từ grid.

======================================================================
4. COMPOSITE EXIT SPECIFICATION (nếu applicable)
======================================================================

Nếu candidate có composite exit (A ∪ B):
- Specify CHÍNH XÁC logic: "exit khi condition_A fires OR condition_B fires,
  whichever happens first"
- Mỗi component phải có own parameters
- Document expected interaction:
  "Component A sẽ fire trước trong scenario X (roughly Y% of trades)"
  "Component B sẽ fire trước trong scenario Z (roughly W% of trades)"
- Evidence: Phase 3 decomposition cho thấy Δ = ? khi bỏ từng component

======================================================================
5. TÍNH ĐƠN GIẢN
======================================================================

- Tối đa 3 candidates (tránh multiple testing penalty)
- Mỗi candidate ≤ 10 DOF
- Prefer candidate ít DOF hơn nếu evidence tương đương
- Nếu 2 candidates equivalent → giữ cái ít DOF

======================================================================
6. BENCHMARK COMPARISON PLAN
======================================================================

- Implement best-known strategy (Section D, Phase 0) cho so sánh
- Metrics đo: Sharpe, CAGR, MDD, Calmar, trade count,
  win rate, exposure, avg duration, max consecutive losses
- Same data, same cost model (50 bps RT)

======================================================================
7. PRE-COMMITTED REJECTION CRITERIA
======================================================================

Định nghĩa TRƯỚC KHI backtest — không được sửa sau:
- Sharpe < 0 → REJECT (negative EV)
- Sharpe < benchmark × 0.80 → REJECT (significantly worse)
- MDD > 75% → REJECT (unacceptable risk)
- Trade count < 15 → REJECT (insufficient sample)
- WFO win rate < 50% → REJECT (out-of-sample failure)
- Bootstrap P(Sharpe > 0) < 60% → REJECT (luck)
- Ghi rõ: criteria này KHÔNG được thay đổi sau khi Phase 7 bắt đầu

======================================================================
8. EXPECTED BEHAVIOR (pre-backtest estimates)
======================================================================

Cho MỖI candidate, ước lượng TỪ Phase 3 grid data:
- Phase 3 grid Sharpe cho config này: X.XX
- Estimated trade count (from Phase 3)
- Estimated exposure (% of time)
- Estimated holding period
- Estimated avg_loser, avg_winner
- Constraint satisfaction margin (bao nhiêu headroom vs Phase 5 constraints)

Ước lượng này dùng để Phase 7 sanity check.
Nếu Phase 7 result sai lệch > 30% vs estimate → cần giải thích.

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x28/):
======================================================================
- 06_design.md
- Candidate specification sheets (mỗi candidate: complete, exact, traceable)

======================================================================
Cấm:
======================================================================
- Không backtest — chỉ design
- Không tune parameters — chỉ set defaults từ evidence hoặc Phase 3 grid
- Không thêm features "just in case"
- Mỗi component phải justify từ evidence chain
- Candidate KHÔNG có complete provenance chain → loại ngay
- KHÔNG tự nghĩ ra candidate ngoài Phase 3 grid
- KHÔNG bỏ qua composite exits nếu Phase 3 cho thấy chúng contribute
- KHÔNG bỏ qua design constraints từ Phase 5
