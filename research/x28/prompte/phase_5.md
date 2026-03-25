PHASE 5: GO / NO-GO DECISION
======================================================================

Điều kiện: Phase 4 hoàn thành.

Bước 0 — CONTEXT LOADING (bắt buộc):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x28/prompte/phase_0.md
  Đọc deliverables Phase 2, 3, 4:
  - /var/www/trading-bots/btc-spot-dev/research/x28/02_price_behavior_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/03_signal_landscape_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/04_formalization.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/manifest.json

Mục tiêu:
Quyết định có đủ evidence để design algorithm hay không.
Quyết định dựa trên OBJECTIVE (maximize Sharpe, MDD ≤ 60%).

======================================================================
1. EVIDENCE FOR DESIGN
======================================================================
Liệt kê findings ủng hộ việc design:
| # | Finding | Obs/Prop | Effect Size | Significance |

======================================================================
2. EVIDENCE AGAINST DESIGN
======================================================================
Liệt kê findings phản đối:
| # | Finding | Obs/Prop | Effect Size | Implication |

PHẢI include:
- Nếu TOP-N từ Phase 3 không beat prior art Sharpe 1.08
- Nếu regression cho thấy không có property nào predict Sharpe (R² ≈ 0)
- Nếu decomposition cho thấy prior art đã gần optimal

======================================================================
3. DETECTABILITY ASSESSMENT
======================================================================
- Phenomenon mạnh nhất: effect size, power, stability
- Kết luận: "CÓ ĐỦ signal?" (YES / NO / UNCLEAR)

======================================================================
4. IMPROVEMENT POTENTIAL
======================================================================
So sánh với OBJECTIVE, không với benchmark cụ thể:

a. Best combination từ Phase 3 grid: Sharpe = ?
b. Prior art best known: Sharpe = 1.08
c. Theoretical ceiling (from information analysis): Sharpe ≈ ?

Nếu (a) > (b): "Phase 3 đã tìm được config tốt hơn prior art"
Nếu (a) ≈ (b): "Phase 3 confirms prior art near-optimal"
Nếu (a) < (b): "Phase 3 grid chưa cover config tốt nhất"
   → Xem xét: Phase 3 có miss combination nào không?

ΔSharpe vs buy-and-hold (simplest approach): phải > 0.10

======================================================================
5. DECISION — chọn MỘT
======================================================================

**GO_TO_DESIGN** nếu TẤT CẢ:
- ≥ 1 phenomenon POWERED (effect > MDE)
- ≥ 1 combination trên efficiency frontier
- Expected Sharpe > buy-and-hold + 0.10
- Phase 3 impact analysis xác định ≥ 1 actionable Sharpe driver

**STOP_BENCHMARK_NEAR_OPTIMAL** nếu:
- Phase 3 TOP-N ≈ prior art (ΔSharpe < 0.05)
- Decomposition cho thấy prior art đã exploit hết available info
- Không có combination nào exceed prior art meaningfully

**STOP_NO_ALPHA** nếu:
- VR ≈ 1.0 ở mọi scale
- Tất cả signal types FP > 70%
- Regression R² < 0.10

**STOP_INCONCLUSIVE** nếu:
- Phenomena interesting nhưng underpowered
- Stability unclear

======================================================================
6. NẾU GO — SPECIFY CONSTRAINTS CHO PHASE 6
======================================================================
Dựa trên Phase 3 impact analysis, specify:
- "Candidate PHẢI có exposure ≥ X%" (từ regression)
- "Candidate PHẢI có avg_loser ≤ Y%" (từ regression)
- "Candidate NÊN dùng [exit class] vì decomposition Δ = Z"
- Mỗi constraint PHẢI reference Obs## hoặc Tbl##

Đây KHÔNG phải prescriptive design — chỉ là constraints
rút ra từ data analysis. Phase 6 agent tự do thiết kế
TRONG constraints này.

======================================================================
7. NẾU STOP
======================================================================
Recommend next direction:
- Giảm cost (engineering, không algorithm)
- Futures/perps thay vì spot
- Multi-asset
- Thêm data
Rank theo effort/payoff.

======================================================================
Deliverables:
======================================================================
- 05_go_no_go.md
- manifest.json cập nhật (phase=5, gate_status)

======================================================================
Cấm:
======================================================================
- KHÔNG GO chỉ vì "có vẻ có alpha"
- KHÔNG STOP chỉ vì "không beat benchmark" (có thể có alpha mới chưa test)
- Quyết định PHẢI dựa trên quantitative evidence
