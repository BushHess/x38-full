PHASE 4: FORMALIZATION
======================================================================

Điều kiện: Phase 3 hoàn thành.

Bước 0 — CONTEXT LOADING (bắt buộc):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x28/prompte/phase_0.md
  Đọc deliverables Phase 2 và 3:
  - /var/www/trading-bots/btc-spot-dev/research/x28/02_price_behavior_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/03_signal_landscape_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/manifest.json

Mục tiêu:
Derive admissible function classes từ evidence.
Quantify information content. Power analysis.
XÁC ĐỊNH cái gì drive Sharpe (từ Phase 3 Part D).

======================================================================
1. PHENOMENON SUMMARY
======================================================================
Liệt kê 5-10 findings mạnh nhất từ Phase 2-3:
- Mỗi finding: Obs## tag, effect size, significance, stability
- Classify: CERTAINLY exploitable / POSSIBLY / NOT exploitable
- QUAN TRỌNG: xếp hạng theo IMPACT LÊN SHARPE (từ Tbl_sharpe_drivers),
  KHÔNG theo "tầm quan trọng trực giác"

======================================================================
2. SHARPE DRIVER SYNTHESIS
======================================================================
Từ Phase 3 Part D (impact analysis), tổng hợp:
- Top-3 predictors of Sharpe (với coefficient, R²)
- Implications cho design:
  Ví dụ: nếu exposure là predictor #1 → candidate PHẢI có exposure cao
  Ví dụ: nếu avg_loser là predictor #2 → candidate CẦN exit mechanism
  giảm avg_loser (dual exit? tighter stop?)

KHÔNG prescribe solution — chỉ state constraint:
"Candidate must have [property] ≥ [threshold] based on regression."

======================================================================
3. INFORMATION SETS
======================================================================
Estimate mutual information / Spearman correlation:
- 20+ features × 6+ forward return horizons (k=1,5,10,20,40,60)
- Features: price-based, volume-based, volatility-based, D1 context
- Tbl11: information ranking table
- Identify: WHICH features carry information at WHICH horizons

======================================================================
4-6. ADMISSIBLE FUNCTION CLASSES
======================================================================

Entry classes (≤ 3):
- Derive from Phase 3 frontier + information ranking
- Mathematical form, DOF count
- Rejection evidence: classes NOT on frontier → document WHY rejected

Exit classes (≤ 3):
- PHẢI include ≥ 1 composite exit class nếu Phase 3 decomposition
  cho thấy composite exit contributes > 0.05 Sharpe
- Mathematical form, DOF count

Filter classes:
- Include nếu Phase 3 Tbl10 cho thấy ΔSharpe > 0.05 consistently
- Skip nếu filters don't improve Sharpe (document evidence)

======================================================================
7. DOF BUDGET
======================================================================
- Mỗi class: DOF count
- Combinations: total DOF per combination
- Tbl12: DOF budget table
- Prune nếu total > 10

======================================================================
8. POWER ANALYSIS
======================================================================
Cho mỗi admissible combination:
- Expected trade count (từ Phase 3 grid)
- MDE at α=0.05, 80% power
- Observed effect / MDE ratio
- Verdict: POWERED / BORDERLINE / UNDERPOWERED
- Tbl13: power analysis table

======================================================================
9. PROPOSITIONS
======================================================================
Derive Prop## từ Obs## + analysis:
- Prop## ← Obs## chain
- Confidence: HIGH / MEDIUM / LOW
- Testable implication

======================================================================
Deliverables:
======================================================================
- 04_formalization.md
- code/phase4_information.py
- tables/Tbl11_information_ranking.csv
- tables/Tbl12_dof_budget.csv
- tables/Tbl13_power_analysis.csv
- Observation + Proposition logs
- manifest.json cập nhật

======================================================================
Cấm:
======================================================================
- KHÔNG propose SPECIFIC candidates (chỉ function CLASSES)
- KHÔNG post-hoc wrap known indicators
- KHÔNG ignore Phase 3 impact analysis results
- Nếu top Sharpe driver là exposure → function class PHẢI preserve exposure
  (không được chọn class có low exposure rồi ignore regression evidence)
