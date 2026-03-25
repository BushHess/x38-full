======================================================================
PHASE 5: GO / NO-GO DECISION
======================================================================

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x27/prompte/phase_0.md
  Đọc deliverables Phase 2 (observations):
  - /var/www/trading-bots/btc-spot-dev/research/x27/02_price_behavior_eda.md
  Đọc deliverables Phase 3 (signal landscape):
  - /var/www/trading-bots/btc-spot-dev/research/x27/03_signal_landscape_eda.md
  Đọc deliverables Phase 4 (formalization, function classes, power analysis):
  - /var/www/trading-bots/btc-spot-dev/research/x27/04_formalization.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl_information_ranking*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl_dof_budget*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl_power_analysis*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/manifest.json

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/

Mục tiêu:
Synthesis evidence → quyết định: có đủ basis để design algorithm không?

======================================================================
Cấu trúc bắt buộc:
======================================================================

1. EVIDENCE FOR DESIGN (provenance tags bắt buộc)
- Liệt kê 5-10 findings ủng hộ việc design algorithm mới
- Mỗi finding: Obs##, Prop##, effect size, significance

2. EVIDENCE AGAINST DESIGN (provenance tags bắt buộc)
- Liệt kê TẤT CẢ findings gợi ý không nên design
- Bao gồm: complexity ceiling, underpowered tests, unstable patterns
- Không được giấu evidence bất lợi

3. PRIOR HYPOTHESIS VERIFICATION STATUS
- Bảng: H_prior_1 through H_prior_10
- Mỗi cái: CONFIRMED / REFUTED / PARTIALLY CONFIRMED / NOT TESTABLE
- Evidence reference cho mỗi verdict

4. DETECTABILITY ASSESSMENT
- Strongest phenomenon: effect size bao nhiêu?
- Power: POWERED / BORDERLINE / UNDERPOWERED?
- Stability: consistent across time blocks?
- Combined judgment: CÓ ĐỦ signal để detect reliably?

5. IMPROVEMENT POTENTIAL
- Best entry type (from frontier): ước tính improvement vs simplest approach?
- Best exit type (from frontier): ước tính improvement vs simplest approach?
- Best regime filter: ước tính improvement?
- Combined expected ΔSharpe vs benchmark?
- Nếu expected ΔSharpe < 0.10: flag as "marginal improvement"

6. DECISION (chọn đúng MỘT):

GO_TO_DESIGN — Đủ evidence để design.
  Điều kiện:
  - ≥ 1 phenomenon POWERED (effect > MDE)
  - ≥ 1 entry type trên efficiency frontier rõ ràng
  - ≥ 1 exit type trên efficiency frontier rõ ràng
  - Expected ΔSharpe > 0.10 (net of cost)

  Nếu GO: specify which function classes to use, why, và expected outcome.

STOP_NO_ALPHA — Không có alpha đáng kể.
  Điều kiện:
  - Variance ratio ≈ 1.0 ở mọi scale (no persistence, no mean-reversion)
  - Tất cả signal types cho false positive > 70%

STOP_BENCHMARK_NEAR_OPTIMAL — Benchmark đã gần optimal.
  Điều kiện:
  - Best frontier position ≈ benchmark performance
  - Expected improvement < 0.10 Sharpe
  - Không có fundamentally different approach nào dominate

STOP_INCONCLUSIVE — Evidence mixed, underpowered.
  Điều kiện:
  - Some phenomena interesting nhưng UNDERPOWERED
  - Stability unclear (need more data)

7. NẾU STOP:
- Recommend next direction:
  - "Reduce cost" (engineering, not research)
  - "Different instrument" (futures/perps for new alpha surface)
  - "More data" (longer history or higher frequency)
  - "Different market" (not BTC)
- Giải thích tại sao mỗi recommendation

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x27/):
======================================================================
- 05_go_no_go.md
- manifest.json cập nhật

======================================================================
Cấm:
======================================================================
- Không force GO nếu evidence yếu
- Không STOP nếu evidence thực sự mạnh
- Phải viết CẢ hai sides (for + against) TRƯỚC khi quyết định
- "Promising" không phải evidence — cần numbers
