PREPEND PROMPT 0 tại: /var/www/trading-bots/btc-spot-dev/research/prompte/phase_0.md
======================================================================

Bạn đang ở PHASE 3: PHENOMENON SURVEY & SCORING.

Đầu vào:
- 01_audit_state_map.md
- 02_flat_period_eda.md
- Tất cả observations từ Phase 1–2

Mục tiêu:
Đánh giá MỌI observation từ Phase 2 theo 5 tiêu chí.
Xếp hạng phenomena.
Xác định: có phenomenon nào đủ mạnh để formalize không?

Bước thực hiện:

1. Filter observations
- Liệt kê TẤT CẢ observations từ Phase 2 có evidence of structure
- Chỉ giữ những observations có:
  p < 0.10 HOẶC effect size > 0.20 HOẶC visual pattern rõ ràng
- LOẠI BỎ:
  - Observations đã known và universal (e.g., vol clustering tồn tại everywhere)
  - Observations đã captured bởi VTREND (e.g., trend persistence ở H4)
  - Observations là mechanical consequence của VTREND states
    (e.g., "price rises before entry" — đó LÀ entry condition)
- Mỗi observation bị loại: ghi rõ lý do

2. Cho MỖI observation còn lại, đánh giá 5 tiêu chí:

S1: SIGNAL STRENGTH
- Effect size (Cohen's d, Spearman ρ, rank-biserial, R²)
- Statistical significance (p-value)
- Score:
  STRONG: d > 0.4 AND p < 0.01
  MODERATE: d > 0.2 AND p < 0.05
  WEAK: d < 0.2 OR p > 0.05

S2: TEMPORAL STABILITY
- Split data thành 4 equal-time blocks
- Compute effect in EACH block
- Effect sign consistent across all blocks?
- Score:
  STABLE: ≥ 3/4 blocks same sign, ≥ 2/4 significant
  MIXED: 2-3/4 same sign
  UNSTABLE: sign flips OR ≤ 1/4 consistent

S3: ECONOMIC MAGNITUDE
- Estimate: nếu phenomenon này perfectly exploited, ΔSharpe bao nhiêu?
- Method: effect_size × sqrt(n_opportunities_per_year) × estimated_return_per_opportunity
- Account for cost (50 bps RT per trade)
- Score:
  MATERIAL: ΔSharpe > 0.30
  MARGINAL: ΔSharpe 0.10–0.30
  NEGLIGIBLE: ΔSharpe < 0.10

S4: COMPLEMENTARITY WITH VTREND
- Correlation giữa phenomenon-based returns và VTREND returns
  (estimate, không cần full backtest — dùng timing overlap)
- Phenomenon có operate primarily during FLAT periods không?
- Score:
  COMPLEMENTARY: ρ < 0.2, >70% of signals during FLAT
  PARTIAL: ρ 0.2–0.5, 40–70% during FLAT
  OVERLAPPING: ρ > 0.5 OR <40% during FLAT

S5: SAMPLE ADEQUACY
- N observations for this phenomenon
- Compute MDE at 80% power, α = 0.05
- So sánh observed effect vs MDE
- Score:
  ADEQUATE: observed effect > 1.5 × MDE
  BORDERLINE: observed effect between 1.0–1.5 × MDE
  UNDERPOWERED: observed effect < MDE

3. Scoring matrix
- Tạo bảng: Phenomenon × [S1, S2, S3, S4, S5, Total]
- Total = count of {STRONG, STABLE, MATERIAL, COMPLEMENTARY, ADEQUATE}
  (i.e., count of top-tier scores)
- Xếp hạng theo Total descending

4. Supplementary stability analysis
- Cho mỗi phenomenon với Total ≥ 2:
  - Rolling window analysis (500-bar window, giống entry_filter_lab Fig08 approach)
  - Plot rolling effect size over time
  - Ghi nhận nếu effect weakens/strengthens/disappears in recent data

5. Gate decision rule
- ≥ 3 top-tier scores trên ÍT NHẤT 1 phenomenon
  → PASS_TO_NEXT_PHASE
- Tất cả phenomena < 3 top-tier scores
  → STOP (chọn stop type phù hợp: NO_ALPHA, NOISE, INCONCLUSIVE)
- ≥ 2 top-tier scores nhưng S5 = UNDERPOWERED
  → STOP_INCONCLUSIVE (evidence suggestive nhưng cannot validate)

6. Nếu PASS: chọn top 1–2 phenomena cho Phase 4
   Nếu STOP: viết rõ kết luận và recommended next direction

Deliverables bắt buộc:
- research/beyond_trend_lab/03_phenomenon_survey.md
- research/beyond_trend_lab/code/phase3_scoring.py
- research/beyond_trend_lab/tables/Tbl_scoring_matrix.csv
- research/beyond_trend_lab/tables/Tbl_stability_blocks.csv
- Figures bổ sung (stability rolling plots) nếu applicable
- Observation log cập nhật

Cấm:
- Không propose strategy hay trading rule
- Không thiên vị: nếu tất cả phenomena weak, nói thẳng
- Không inflate scores để justify design
- Không override gate decision rule
- Nếu scoring cho STOP, accept STOP
