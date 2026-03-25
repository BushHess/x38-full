======================================================================
PHASE 4: FORMALIZATION
======================================================================

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x27/prompte/phase_0.md
  Đọc deliverables Phase 2 (observations, phenomena):
  - /var/www/trading-bots/btc-spot-dev/research/x27/02_price_behavior_eda.md
  Đọc deliverables Phase 3 (signal landscape, frontiers):
  - /var/www/trading-bots/btc-spot-dev/research/x27/03_signal_landscape_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl07*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl08*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl09*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl10*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/
- Signal landscape: frontier positions, interaction matrix, regime effects (Phase 3)
- Observations về BTC price behavior (Phase 2)

Mục tiêu:
Translate EDA evidence thành decision framework toán học.
Derive admissible function classes cho entry VÀ exit — từ DATA, không từ memory.

======================================================================
Cấu trúc bắt buộc:
======================================================================

1. PHENOMENON SUMMARY
- Tóm tắt 5-10 strongest observations từ Phase 2-3 (với Obs## tags)
- Cho mỗi observation: effect size, significance, stability
- Phân loại: phenomena CHẮC CHẮN exploitable / CÓ THỂ exploitable / KHÔNG exploitable

2. DECISION PROBLEM
- Formal definition:
  - State space: S_t = observable information tại thời điểm t
  - Action space: A = {ENTER_LONG, EXIT, HOLD_FLAT, HOLD_POSITION}
  - Transition: P(S_{t+1} | S_t, A_t) — estimated từ data
  - Reward: R(S_t, A_t) = return - cost
  - Objective: maximize E[Σ R_t] (hoặc risk-adjusted variant)

3. INFORMATION SETS — CÁI GÌ OBSERVABLE VÀ HỮU ÍCH?
- Cho mỗi loại information, estimate mutual information với future returns:
  - Price-based: returns, moving averages, momentum (from Phase 2)
  - Volume-based: volume, TBR, volume momentum (from Phase 2)
  - Volatility-based: realized vol, vol changes (from Phase 2)
  - D1 context: regime indicators (from Phase 2)
- Rank by information content
- Ghi nhận: information set nào THỰC SỰ có predictive power?

4. ADMISSIBLE FUNCTION CLASSES — ENTRY
- Derive từ signal landscape (Phase 3 frontier):
  - Frontier-dominant signal types → derive mathematical form
  - Mỗi class: formula, DOF count, evidence reference
  - KHÔNG quá 3 classes
- Rejected classes: types bị dominated trên frontier, với evidence

5. ADMISSIBLE FUNCTION CLASSES — EXIT
- Tương tự, derive từ exit efficiency frontier (Phase 3):
  - High-capture + low-churn types → mathematical form
  - Mỗi class: formula, DOF count, evidence reference
  - KHÔNG quá 3 classes
- Rejected classes: types với churn > threshold hoặc capture < threshold

6. ADMISSIBLE FUNCTION CLASSES — FILTER / REGIME
- Nếu Phase 2-3 cho thấy regime conditioning hữu ích:
  - Derive regime function class
  - DOF count
- Nếu KHÔNG hữu ích: ghi nhận "no filter needed" (valid conclusion)

7. TOTAL DOF BUDGET
- Sum DOF across entry + exit + filter classes
- Phải ≤ 10 cho toàn pipeline
- Nếu tổng > 10: phải prune classes (loại bớt DOF-expensive classes)

8. POWER ANALYSIS
- Cho mỗi admissible class combination (entry × exit × filter):
  - Expected trade count (from Phase 3 signal frequency)
  - MDE at 80% power, α = 0.05
  - So sánh observed effect sizes (Phase 2-3) vs MDE
  - Verdict: POWERED / BORDERLINE / UNDERPOWERED
- Nếu tất cả UNDERPOWERED → flag as blocker

9. PROPOSITIONS
- Derive từ evidence chain: Obs## → analysis → Prop##
- Mỗi Prop: confidence HIGH / MEDIUM / LOW
- Mỗi Prop: traceable to specific Figures/Tables

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x27/):
======================================================================
- 04_formalization.md
- code/ — scripts cho information estimation, power analysis
- tables/Tbl_information_ranking, Tbl_dof_budget, Tbl_power_analysis

======================================================================
Cấm:
======================================================================
- Không propose SPECIFIC candidates (chỉ CLASSES)
- Không nhớ ra strategy rồi justify bằng formalization
- Derive từ Phase 2-3 evidence, không từ textbooks
- Nếu power analysis cho UNDERPOWERED → nói thẳng
