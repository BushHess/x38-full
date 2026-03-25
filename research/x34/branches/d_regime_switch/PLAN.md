# d_regime_switch — Conditional Edge by Regime (F-03)

**Status**: CLOSED — gate failed at [c_ablation](../c_ablation/) (2026-03-14)
**Nguồn gốc**: Finding F-03 (holdout paradox, conditional edge)
**Gate cho**: [e_level_hysteresis](../e_level_hysteresis/)
**Evidence**: [debate/001-x34-findings/findings-under-review.md](../../debate/001-x34-findings/findings-under-review.md) §F-03, §F-05

---

## Điều kiện tiên quyết

c_ablation cho thấy ≥ 1 component Q-VDO-RH có giá trị. Nếu c_ → CLOSE → nhánh
này KHÔNG mở.

Observed status:
- c_ablation closed the Q-VDO-RH family.
- A5 và A3 chỉ phục hồi gần về E0, không tạo edge mới hơn baseline.
- Vì vậy nhánh này được giữ như archival prereg, không triển khai.

## Giả thuyết

Q-VDO-RH có conditional edge trong một số regime. Evidence:
- Full-sample thua (-25.97) nhưng holdout thắng (+19.12)
- WFO: thắng rõ ở 3 windows (+80, +47, +29), thua nặng ở 2 (-90, -90)
- Pattern: Q-VDO-RH thắng khi baseline Sharpe thấp/âm, thua khi baseline >2.0
- Regime decomposition: thắng bear/topping, thua bull/chop

Nếu đúng, Q-VDO-RH không phải entry filter (always-on) mà là **regime switch**:
dùng Q-VDO-RH trong regime X, giữ VDO trong regime Y.

## Bước thực hiện

### Phase D1 — Regime characterization

1. **Map WFO windows → regime labels**:
   - 3 winning windows (2022-H1, 2023-H1, 2025-H1): dominant regime?
   - 2 losing windows (2023-H2, 2024-H2): dominant regime?
   - Dùng regime decomposition có sẵn từ b_e0_entry

2. **Correlation analysis**: baseline_sharpe vs Q-VDO-RH delta
   - Scatter plot: x = baseline window Sharpe, y = delta
   - Spearman ρ — nếu |ρ| > 0.7 → regime conditioning khả thi
   - Nếu |ρ| < 0.3 → pattern ngẫu nhiên → **STOP**

3. **Identify candidate regime signal**:
   - Dùng component có giá trị từ c_ablation (nếu normalized input → dùng nó)
   - Test: trailing volatility, trend strength, hay chính `l_t` (level) từ Q-VDO-RH?

### Phase D2 — Regime switch backtest

4. **Thiết kế regime switch**:
   - Switch ON: dùng Q-VDO-RH khi regime = {candidate regime}
   - Switch OFF: dùng VDO gốc khi regime ≠ {candidate regime}
   - Regime signal phải **lagging** (không dùng future data)

5. **WFO validation**:
   - Train: identify regime boundaries
   - Test: apply switch, measure delta vs always-VDO

6. **Full validation `--suite all`**:
   - Baseline: E0 (always VDO)
   - Candidate: E0 + regime switch

## STOP criteria

- Phase D1 correlation |ρ| < 0.3 → **STOP** (no regime structure)
- Phase D2 WFO win rate < 50% → **STOP** (regime signal not predictive OOS)
- Regime switch thắng nhưng ΔSharpe < 0.05 → **STOP** (quá nhỏ, không đáng complexity)

## GO criteria → e_level_hysteresis

- Regime switch PROMOTE hoặc HOLD với promising direction
- Regime signal identified → có thể test level field `l_t` trong e_

## Deliverables

- `results/regime_characterization.md`
- `results/switch_validation_report.md`
- `figures/baseline_sharpe_vs_delta.png`
