PHASE 8: FINAL RESEARCH MEMO
======================================================================

Bước 0 — CONTEXT LOADING (bắt buộc trước khi làm bất kỳ gì):
  Đọc protocol:
  - /var/www/trading-bots/btc-spot-dev/research/x28/prompte/phase_0.md
  Đọc TẤT CẢ báo cáo các phase trước:
  - /var/www/trading-bots/btc-spot-dev/research/x28/01_data_audit.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/02_price_behavior_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/03_signal_landscape_eda.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/04_formalization.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/05_go_no_go.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/06_design.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/07_validation.md
  - /var/www/trading-bots/btc-spot-dev/research/x28/manifest.json
  Đọc key tables từ Phase 7:
  - /var/www/trading-bots/btc-spot-dev/research/x28/tables/Tbl_full_sample_comparison*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x28/tables/Tbl_bootstrap_summary*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x28/tables/Tbl_wfo_results*.csv
  - /var/www/trading-bots/btc-spot-dev/research/x28/tables/Tbl_sharpe_attribution*.csv

Đầu vào:
- Dữ liệu tại /var/www/trading-bots/btc-spot-dev/data/

Mục tiêu:
Viết final report sạch, thẳng, không né tránh.
Đánh giá kết quả theo OBJECTIVE (maximize Sharpe, MDD ≤ 60%).

======================================================================
Cấu trúc bắt buộc:
======================================================================

1. EXECUTIVE CONCLUSION (chọn đúng MỘT)
- "Algorithm Cand## [tên ngắn] is the recommended system."
  Sharpe = X.XX, CAGR = X.X%, MDD = X.X%
  ΔSharpe vs best-known = +X.XX
- "No improvement over best-known. [Best-known name] remains optimal."
  Lý do: [1-2 câu]
- "Inconclusive. Phenomena exist but underpowered."
  Next step: [1 câu]

2. RESEARCH PATH
- Phase 1: [2 câu — đã làm gì, tìm thấy gì]
- Phase 2: [2-3 câu]
- Phase 3: [2-3 câu — ĐẶC BIỆT: impact analysis tìm thấy gì? decomposition?]
- Phase 4: [2 câu]
- Phase 5: [1-2 câu]
- Phase 6: [2 câu, nếu applicable — candidates chọn từ đâu trong grid?]
- Phase 7: [2-3 câu, nếu applicable]
Chỉ nêu cái ĐÃ LÀM, không nêu cái dự định.

3. STRONGEST EVIDENCE (5-8 findings)
- Mỗi finding: 1-2 câu + provenance tags (Obs##, Prop##, Fig##, Tbl##)
- Xếp theo strength descending
- PHẢI include Phase 3 impact analysis findings (Sharpe drivers)
- PHẢI include Phase 3 decomposition findings

4. WHAT FAILED
- Signal type nào bị dominated? Entry/exit pair nào worst?
- Candidate nào bị REJECT? Gate nào fail?
- Class nào bị loại ở formalization? Tại sao?
- Design constraint nào không thỏa mãn?
- Assumption nào sai? (e.g., "Phase 3 grid predicted Sharpe X,
  actual was Y — grid overestimated by Z%")

5. KEY DISCOVERIES (thay thế "Prior Hypothesis Final Status")
Bảng: những gì DATA tiết lộ, KHÔNG phải kiểm tra giả thuyết sẵn.

| # | Discovery | Evidence | Surprise Level |
|---|-----------|----------|----------------|
| 1 | "Exposure là predictor #1 của Sharpe (β=0.X, R²=0.XX)" | Tbl_sharpe_drivers | HIGH/MED/LOW |
| 2 | "Composite exit contributes +0.XX Sharpe vs simple" | Tbl_decomposition | ... |
| ... | ... | ... | ... |

"Surprise Level" = mức độ bất ngờ so với intuition trước khi chạy.
Findings với HIGH surprise là valuable nhất.

6. MATHEMATICAL CONCLUSION
- BTC H4 returns có exploitable structure ở đâu?
- Structure đó best captured bởi function class nào?
- Tại sao class đó và không phải class khác?
- Information ceiling: còn bao nhiêu room để improve?
- Complexity vs performance: optimal DOF là bao nhiêu?
- Sharpe attribution: candidate {tốt/kém} hơn benchmark vì [property]

7. PRACTICAL RECOMMENDATION

Nếu candidate PROMOTE:
- Algorithm specification (complete, reproducible)
- Key metrics vs benchmark
- Sharpe attribution: WHY it's better (property-level explanation)
- Caveats: regime dependency, cost sensitivity, sample limitations
- What monitoring needed for live deployment

Nếu STOP / REJECT:
- Nói thẳng: tại sao không tìm được gì tốt hơn
- Nêu rõ: "best-known strategy đã exploit [top Sharpe driver]
  hiệu quả, candidate không cải thiện được [property] này"
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
- Protocol limitations: research agent bị bias theo hướng nào?
  (e.g., "Phase 3 grid coverage chỉ sweep X configs, có thể miss
  configs ngoài grid")

9. RESEARCH PROTOCOL REVIEW (MỚI)
Mục đích: cải thiện protocol cho studies tương lai.
- Phase nào tạo NHIỀU giá trị nhất? (e.g., "Phase 3 impact analysis
  revealed exposure is the key driver — without this, we would have
  optimized the wrong property")
- Phase nào tạo ÍT giá trị nhất?
- Decisions nào bị protocol miss? (blind spots)
- Recommendations cho protocol X29

10. FINAL STATUS (chọn đúng MỘT)
- FINALIZED_PROMOTE_CAND## — Algorithm mới tốt hơn best-known
- FINALIZED_BENCHMARK_OPTIMAL — Best-known đã gần optimal
- FINALIZED_INCONCLUSIVE — Cần thêm data/research
- FINALIZED_NO_ALPHA — BTC H4 long-only không có alpha đáng kể

======================================================================
Deliverables (lưu tại /var/www/trading-bots/btc-spot-dev/research/x28/):
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
- Không blame protocol cho kết quả yếu — protocol là tool,
  kết quả phụ thuộc data và market structure
