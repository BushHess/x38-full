PREPEND PROMPT 0 tại: /var/www/trading-bots/btc-spot-dev/research/prompte/phase_0.md
======================================================================

Bạn đang ở PHASE 5: GO / NO-GO DECISION.

Đầu vào:
- Tất cả artifacts từ Phase 1–4

Mục tiêu:
Synthesis toàn bộ evidence → quyết định go/no-go.

Cấu trúc bắt buộc:

1. Evidence summary
- Liệt kê 5–10 findings mạnh nhất (với provenance tags)
- Liệt kê TẤT CẢ findings phản bác (với provenance tags)
- Balance sheet: FOR vs AGAINST design

2. SNR / Detectability judgment
- Information strength: STRONG / MODERATE / WEAK / ABSENT
- Stability: STABLE / MIXED / UNSTABLE
- Detectability: POWERED / BORDERLINE / UNDERPOWERED

3. Complementarity assessment
- New strategy operates during VTREND FLAT: bao nhiêu % of time?
- Expected correlation with VTREND returns?
- Risk of interference (missed VTREND entries due to capital lock)?

4. Cost-benefit analysis
- Expected ΔSharpe from adding new strategy (range estimate)
- Additional DOF cost (new params added to pipeline)
- Additional complexity cost (new code, monitoring, execution)
- Risk of degrading VTREND if combined poorly
- Compare: expected gain vs certain costs

5. Quyết định (chọn đúng MỘT):

(A) GO_TO_DESIGN
    Evidence đủ mạnh, complementary, powered.
    Điều kiện: ≥ 1 phenomenon passed Phase 3 scoring (≥ 3 top-tier)
    VÀ Phase 4 formalization shows powered + complementary
    VÀ expected ΔSharpe > 0.15 (net of costs)

(B) STOP_NO_ALPHA_BEYOND_TREND
    Flat periods show no exploitable structure.
    Điều kiện: tất cả phenomena WEAK hoặc UNSTABLE ở Phase 3

(C) STOP_FLAT_PERIODS_ARE_NOISE
    Specific variant of (B): flat-period returns are IID noise.
    Điều kiện: ACF insignificant, Hurst ≈ 0.5, no calendar effects,
    no duration dependency, variance ratio ≈ 1.0

(D) STOP_NEED_DIFFERENT_INSTRUMENT
    Alpha exists nhưng needs futures/perps/options/on-chain data.
    Điều kiện: evidence suggests exploitable pattern BUT
    requires short selling, funding rates, or data not available in spot OHLCV

(E) STOP_INCONCLUSIVE
    Evidence mixed, underpowered.
    Điều kiện: some phenomena MODERATE nhưng UNDERPOWERED,
    hoặc stability unclear

6. Nếu GO: specify which phenomenon + which function class → Phase 6
   Nếu STOP: specify honest conclusion, reasoning, recommended next direction

   Recommended directions (khi STOP):
   - Nếu (B) hoặc (C): "BTC spot alpha = trend-following. Optimize cost."
   - Nếu (D): "Collect futures data. Research funding/basis/short alpha."
   - Nếu (E): "Need more data (longer history or higher frequency)."

Deliverables bắt buộc:
- research/beyond_trend_lab/05_go_no_go.md
- manifest.json cập nhật

Cấm:
- Không force GO nếu evidence yếu
- Không STOP nếu evidence thực sự đủ mạnh
- Phải viết CẢ two sides (for + against) TRƯỚC KHI quyết định
- Không sử dụng "promising" hoặc "could potentially" để justify GO
  nếu scoring matrix không đạt threshold
