# e_level_hysteresis — Untested Q-VDO-RH Components (F-02)

**Status**: CLOSED — gate failed at [c_ablation](../c_ablation/) (2026-03-14)
**Nguồn gốc**: Finding F-02 (scope chưa bác — level field và hysteresis chưa test)
**Evidence**: [debate/001-x34-findings/findings-under-review.md](../../debate/001-x34-findings/findings-under-review.md) §F-02

---

## Điều kiện tiên quyết

1. c_ablation cho thấy normalized input hoặc adaptive θ có giá trị riêng
2. d_regime_switch cho kết quả positive (regime conditioning khả thi)

Nếu c_ → CLOSE toàn bộ family → nhánh này KHÔNG mở.
Nếu d_ → STOP (no regime structure) → nhánh này KHÔNG mở (trừ khi có lý do
riêng để test hysteresis independent of regime).

Observed status:
- c_ablation closed the Q-VDO-RH family before d_ opened.
- Vì vậy `e_` được giữ như archival prereg, không triển khai.

## Giả thuyết

Q-VDO-RH có 3 thành phần. X34 chỉ bác momentum `m_t > θ` (Option A entry-only).
Hai thành phần còn lại chưa test:

### Level field `l_t = EMA(x, slow)`

- Thông tin regime tĩnh. Spec §5.4 nói chỉ dùng làm context, không làm gate.
- Có thể dùng làm **regime indicator** (liên quan d_regime_switch):
  `l_t` cao → strong buy regime → VDO đủ, `l_t` thấp → weak regime → Q-VDO-RH
- Ưu điểm: derived từ quote-notional flow (genuinely new data vs OHLCV)

### Hysteresis (Option B)

- Entry: `momentum > θ`, hold tới `momentum < 0.5θ`
- Anti-churn mechanism — liên quan trực tiếp X14/X18 churn research
- **Cảnh báo**: X31-A selectivity 0.21 — mid-trade exit rất rủi ro trên BTC.
  Nhưng hysteresis là HOLD condition (giữ lâu hơn), không phải early exit.

## Bước thực hiện

### Phase E1 — Level as regime indicator

1. **Diagnostic**: `l_t` correlation với known regime labels (bull/bear/chop)
2. **Test**: dùng `l_t` làm regime switch signal trong d_regime_switch framework
3. **So sánh**: `l_t` vs trailing volatility vs D1 EMA — cái nào discriminate tốt hơn?

### Phase E2 — Hysteresis (Option B)

4. **Implement Option B** (`e_level_hysteresis/code/strategy_optb.py`):
   - Entry: `momentum > theta`
   - Hold: `momentum > 0.5 * theta` (giữ position lâu hơn)
   - Exit: `momentum < 0.5 * theta` OR existing ATR trail/EMA exit

5. **Full validation**:
   - Baseline: E0 (VDO gốc)
   - Cost: harsh (50 bps RT)
   - So sánh vs Option A (b_e0_entry) — hysteresis thêm value?

6. **Ablation A2** (thuộc nhánh này, không phải b_e0_entry):
   - Option B without hysteresis = Option A → Δ = hysteresis contribution

## STOP criteria

- E1: `l_t` không discriminate regime tốt hơn trailing vol → **STOP** level direction
- E2: Hysteresis tệ hơn Option A → **STOP** (X31-A selectivity warning confirmed)
- E2: Hysteresis ≈ Option A → **STOP** (không thêm value)

## GO criteria

- Level hoặc hysteresis PROMOTE → integrate vào recommendation cuối X34

## Deliverables

- `results/level_regime_analysis.md`
- `results/optionb_validation_report.md`
- `results/a2_ablation_report.md`
