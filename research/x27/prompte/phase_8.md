======================================================================
PHASE 8: FINAL RESEARCH MEMO
======================================================================

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x27/prompte/phase_0.md
  Đọc TẤT CẢ báo cáo các phase trước:
  - /var/www/trading-bots/btc-spot-dev/research/x27/01_data_audit.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/02_price_behavior_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/03_signal_landscape_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/04_formalization.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/05_go_no_go.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/06_design.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/07_validation.md
  - /var/www/trading-bots/btc-spot-dev/research/x27/manifest.json
  Đọc key tables từ Phase 7:
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl_full_sample_comparison*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl_bootstrap_summary*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x27/tables/Tbl_wfo_results*.csv

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/

Mục tiêu:
Viết final report sạch, thẳng, không né tránh.

======================================================================
Cấu trúc bắt buộc:
======================================================================

1. EXECUTIVE CONCLUSION (chọn đúng MỘT)
- "Algorithm Cand## [tên ngắn] is the recommended system."
  Sharpe = X.XX, CAGR = X.X%, MDD = X.X%
- "No improvement over benchmark. VTREND remains best known."
  Lý do: [1-2 câu]
- "Inconclusive. Phenomena exist but underpowered."
  Next step: [1 câu]

2. RESEARCH PATH
- Phase 1: [2 câu — đã làm gì, tìm thấy gì]
- Phase 2: [2-3 câu]
- Phase 3: [2-3 câu]
- Phase 4: [2 câu]
- Phase 5: [1-2 câu]
- Phase 6: [2 câu, nếu applicable]
- Phase 7: [2-3 câu, nếu applicable]
Chỉ nêu cái ĐÃ LÀM, không nêu cái dự định.

3. STRONGEST EVIDENCE (5-8 findings)
- Mỗi finding: 1-2 câu + provenance tags (Obs##, Prop##, Fig##, Tbl##)
- Xếp theo strength descending

4. WHAT FAILED
- Hypothesis nào bị refute?
- Signal type nào bị dominated?
- Candidate nào bị REJECT? Gate nào fail?
- Class nào bị loại ở formalization? Tại sao?

5. PRIOR HYPOTHESIS FINAL STATUS
Bảng: H_prior_1 → H_prior_10, mỗi cái:
- CONFIRMED / REFUTED / PARTIALLY CONFIRMED / NOT TESTED
- Evidence reference
- Surprise: cái nào unexpected?

6. MATHEMATICAL CONCLUSION
- BTC H4 returns có exploitable structure ở đâu?
- Structure đó best captured bởi function class nào?
- Tại sao class đó và không phải class khác?
- Information ceiling: còn bao nhiêu room để improve?
- Complexity vs performance: optimal DOF là bao nhiêu?

7. PRACTICAL RECOMMENDATION

Nếu candidate PROMOTE:
- Algorithm specification (complete, reproducible)
- Key metrics vs benchmark
- Caveats: regime dependency, cost sensitivity, sample limitations
- What monitoring needed for live deployment

Nếu STOP / REJECT:
- Nói thẳng: tại sao không tìm được gì tốt hơn
- Rank recommended directions:
  1. Cost reduction (biggest lever — engineering)
  2. Instrument change (futures/perps — new alpha surface)
  3. Different market
  4. More data (longer history)
- Cho mỗi direction: estimated effort vs expected payoff

8. ANTI-SELF-DECEPTION
Bắt buộc có mục: "What would make this conclusion wrong?"
- Assumptions dễ sai nhất
- Data limitations (sample size, regime coverage, survivorship)
- Method limitations (WFO folds, bootstrap assumptions)
- Conditions có thể đảo ngược kết luận
  (e.g., "if BTC volatility regime changes permanently...")
- Known unknowns: những gì chưa test được với data hiện tại

9. FINAL STATUS (chọn đúng MỘT)
- FINALIZED_PROMOTE_CAND## — Algorithm mới tốt hơn benchmark
- FINALIZED_BENCHMARK_OPTIMAL — Benchmark đã gần optimal
- FINALIZED_INCONCLUSIVE — Cần thêm data/research
- FINALIZED_NO_ALPHA — BTC H4 long-only không có alpha đáng kể

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x27/):
======================================================================
- 08_final_report.md
- manifest.json (final)

======================================================================
Cấm:
======================================================================
- Không quảng cáo candidate nếu gates không pass
- Không dùng "promising" cho kết quả không significant
- Không che failure bằng ngôn ngữ mơ hồ
- Không suggest "future work" dài dòng để bù cho kết quả yếu
- Nếu kết quả yếu → nói "kết quả yếu"
- Nếu benchmark tốt hơn → nói "benchmark tốt hơn"
