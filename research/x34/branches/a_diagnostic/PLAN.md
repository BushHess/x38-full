# a_diagnostic — So sánh tín hiệu Q-VDO-RH vs VDO gốc

**Status**: DONE → GO (2026-03-13)
**Nguồn gốc**: [../../PLAN.md](../../PLAN.md) Phase 2
**Findings**: [debate/001-x34-findings/](../../debate/001-x34-findings/) (F-10, F-11)

---

## Mục tiêu

Hiểu behavior TRƯỚC KHI chạy backtest. "Nhìn trước khi nhảy".

## Bước thực hiện

1. **Chạy cả hai indicator trên full data** (2017-08 → 2026-02, H4):
   - VDO gốc: `_vdo(close, high, low, volume, taker_buy_base, fast=12, slow=28)`
   - Q-VDO-RH: `q_vdo_rh(taker_buy_quote, quote_volume, fast=12, slow=28, k=1.0)`

2. **Thống kê so sánh**:
   - Rank correlation (Spearman) giữa `VDO_t` và `momentum_t` (Q-VDO-RH)
   - Percentage agreement trên signal direction (cùng dương/cùng âm)
   - Histogram distribution: VDO gốc (bounded [-1,1]) vs Q-VDO-RH momentum (unbounded)
   - Signal frequency: số bars có trigger ON cho mỗi indicator

3. **Phân tích divergence**:
   - Tìm các giai đoạn VDO > 0 nhưng Q-VDO-RH < θ (và ngược lại)
   - Phân loại divergence theo regime: high-vol, low-vol, trending, ranging
   - Câu hỏi then chốt: Q-VDO-RH lọc thêm những entry nào? Bỏ lỡ những entry nào?

4. **Visual inspection** (4-6 plots):
   - Overlay VDO vs Q-VDO-RH momentum trên 2-3 giai đoạn tiêu biểu
   - Adaptive threshold θ evolution qua thời gian
   - Scatter plot: VDO value vs Q-VDO-RH momentum tại mỗi entry bar

## STOP criteria

- Spearman ρ > 0.95 → hai indicator gần identical → STOP
- Q-VDO-RH trigger < 50% hoặc > 200% so với VDO → FLAG (không STOP)
- ρ < 0.3 → FLAG: Q-VDO-RH là indicator KHÁC, không phải "bản sửa"

## GO criteria → b_e0_entry

- ρ ≤ 0.95 (không identical)
- Signal frequency ghi nhận (không gate)

## Kết quả thực tế

- Spearman ρ = 0.887 → GO
- Q-VDO-RH triggers: 4,477 vs VDO 9,378 (ratio 0.477) → **FLAG** (< 50%)
- Divergence: 4,962 bars "VDO yes / Q-VDO no" vs 71 ngược lại
- Dynamic range: Q-VDO max 0.287 vs VDO max 0.171 (+68%)
- Verdict: **GO → Phase 3** (dù có frequency flag)
