======================================================================
PHASE 6: DESIGN
======================================================================

Điều kiện: Phase 5 = GO_TO_DESIGN. Nếu không → SKIP phase này.

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x27/prompte/phase_0.md
  Đọc deliverables Phase 2 (observations, Obs## tags):
  - /var/www/trading-bots/btc-spot-dev/research/x27/02_price_behavior_eda.md
  Đọc deliverables Phase 3 (signal landscape, Obs## tags):
  - /var/www/trading-bots/btc-spot-dev/research/x27/03_signal_landscape_eda.md
  Đọc deliverables Phase 4 (function classes, propositions, DOF):
  - /var/www/trading-bots/btc-spot-dev/research/x27/04_formalization.md
  Đọc deliverables Phase 5 (go/no-go decision, selected classes):
  - /var/www/trading-bots/btc-spot-dev/research/x27/05_go_no_go.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/
- Function classes đã chọn từ Phase 4-5

Mục tiêu:
Thiết kế candidate algorithms CỤ THỂ, MINIMAL, TESTABLE.
Mỗi candidate là một COMPLETE pipeline (entry + exit + filter nếu cần).

======================================================================
Cấu trúc bắt buộc:
======================================================================

1. CANDIDATE SPECIFICATION (mỗi candidate)
- Cand## ID
- PROVENANCE CHAIN: Cand## ← Prop## ← Obs## ← Fig##
  (chain phải complete — nếu thiếu bước nào → candidate bị loại)
- Complete rule set:
  - Entry condition: exact formula, thời điểm evaluate
  - Exit condition: exact formula
  - Filter condition: exact formula (nếu có)
  - Position sizing: rule (e.g., fixed fraction, vol-target)
- All parameters: name, default value, admissible range
- DOF count: phải ≤ 10 tổng pipeline

2. PARAMETER DEFAULTS — EVIDENCE-BASED
- Mỗi parameter default PHẢI có justification từ evidence:
  "lookback = 40 vì ACF returns significant đến lag ~40 (Obs##, Fig##)"
  "trail_mult = 3.0 vì exit frontier optimal ở capture 65%+ (Obs##, Fig##)"
- KHÔNG được dùng: "common value", "standard", "typical", "industry practice"
- Nếu không có evidence cho default → chọn TRUNG ĐIỂM của admissible range
  và nói rõ "no evidence — midpoint of range"

3. TÍNH ĐƠN GIẢN
- Tối đa 3 candidates (tránh multiple testing penalty)
- Mỗi candidate ≤ 10 DOF
- Prefer candidate ít DOF hơn nếu evidence tương đương
- Nếu 2 candidates equivalent → giữ cái ít DOF

4. BENCHMARK COMPARISON PLAN
- Implement VTREND benchmark (Section D, Phase 0) cho so sánh
- Metrics đo: Sharpe, CAGR, MDD, Calmar, trade count,
  win rate, exposure, avg duration, max consecutive losses
- Same data, same cost model (50 bps RT)

5. PRE-COMMITTED REJECTION CRITERIA
Định nghĩa TRƯỚC KHI backtest — không được sửa sau:
- Sharpe < 0 → REJECT (negative EV)
- Sharpe < benchmark × 0.80 → REJECT (significantly worse)
- MDD > 75% → REJECT (unacceptable risk)
- Trade count < 15 → REJECT (insufficient sample)
- WFO win rate < 50% → REJECT (out-of-sample failure)
- Bootstrap P(Sharpe > 0) < 60% → REJECT (luck)
- Ghi rõ: criteria này KHÔNG được thay đổi sau khi Phase 7 bắt đầu

6. EXPECTED BEHAVIOR (pre-backtest estimates)
- Estimated trade count (from Phase 3 signal frequency)
- Estimated exposure (% of time)
- Estimated holding period
- Estimated ΔSharpe vs benchmark (from power analysis, Phase 4)

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x27/):
======================================================================
- 06_design.md
- Candidate specification sheets (mỗi candidate: complete, exact, traceable)

======================================================================
Cấm:
======================================================================
- Không backtest — chỉ design
- Không tune parameters — chỉ set defaults từ evidence
- Không thêm features "just in case"
- Mỗi component phải justify từ evidence chain
- Candidate KHÔNG có complete provenance chain → loại ngay
