PREPEND PROMPT 0 tại: /var/www/trading-bots/btc-spot-dev/research/prompte/phase_0.md
======================================================================

Bạn đang ở PHASE 8: FINAL RESEARCH MEMO.

Đầu vào:
- Toàn bộ artifacts từ các phase trước

Mục tiêu:
Viết một final report sạch, thẳng, không né tránh.

Cấu trúc bắt buộc:

1. Executive conclusion
Chọn đúng một:
- BTC spot alpha = trend-following alpha. No complementary source found.
- Complementary alpha found: Cand## [brief description]. Combined Sharpe = X.XX.
- Inconclusive: phenomena exist but underpowered / unstable.
- Different instrument needed: [which and why].

2. Research path
- Tóm tắt Phase 1 → Phase 7
- Mỗi phase 2–4 câu
- Chỉ nêu cái đã thực sự được làm, không nêu cái dự định

3. Strongest evidence
- 5–8 findings mạnh nhất
- Mỗi finding phải có provenance tags (Obs##, Prop##, Fig##, Tbl##)

4. What failed
- Những phenomena / function classes / candidates nào đã bị loại
- Loại vì lý do gì (cụ thể: gate nào fail, p-value bao nhiêu)

5. Mathematical conclusion
- BTC spot returns beyond trend-following có statistical structure không?
- Structure đó exploitable không?
- Nếu exploitable: complementary với VTREND ở mức nào?
  - Return correlation
  - Timing overlap
  - Combined Sharpe vs VTREND-only
- Nếu không exploitable: tại sao?
  - Information ceiling estimate: I(ΔU; V_new | P_t, VT_t)
  - Comparison với VTREND information content

6. Practical recommendation

Nếu found complementary alpha:
- Candidate ID, key metrics, DOF
- Integration plan với VTREND (capital split, priority rules)
- Caveats (regime dependency, cost sensitivity, sample size)
- What monitoring is needed in production

Nếu không found:
- Nói thẳng: alpha surface cho BTC spot ≈ VTREND ceiling
- Rank recommended next directions:
  1. Cost reduction / execution quality (biggest lever, engineering not research)
  2. Instrument change: futures/perps (short-side, funding rate alpha)
  3. Different market entirely
  4. Wait for more data (longer BTC history)
- Cho mỗi direction: estimated effort vs expected payoff

7. Anti-self-deception section
Bắt buộc có mục: "What would make this conclusion wrong?"

Nêu rõ:
- Assumptions dễ sai nhất
  (e.g., "flat period returns are IID" — could this be wrong?)
- Phần nào còn underpowered
  (e.g., "calendar effects at H1 tested with limited data")
- Điều kiện nào có thể đảo ngược kết luận
  (e.g., "if BTC market structure changes dramatically...")
- Data limitations
  (e.g., "no order book data, no funding rates, no on-chain")
- Method limitations
  (e.g., "WFO with 4 folds may miss regime-dependent effects")

8. Comparison with prior research
- How does this study relate to the 56 existing studies?
- Does it confirm, contradict, or extend prior conclusions?
- Updated alpha map: what is now known about BTC spot alpha?

9. Final status line
Chọn đúng một:
- FINALIZED_NO_COMPLEMENTARY_ALPHA
- FINALIZED_PROMOTE_CAND##
- FINALIZED_INCONCLUSIVE
- FINALIZED_NEED_DIFFERENT_INSTRUMENT

Deliverables bắt buộc:
- research/beyond_trend_lab/08_final_report.md
- manifest.json cập nhật (final)

Cấm:
- Không quảng cáo candidate nếu evidence không đủ
- Không làm giọng "có vẻ hứa hẹn" nếu validation không qua
- Không che failure bằng ngôn ngữ mơ hồ
- Không suggest "future work" dài dòng để bù cho kết quả yếu
  (nếu kết quả yếu, nói thẳng "kết quả yếu")
