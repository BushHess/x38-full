# c_ablation — Input vs Threshold Ablation (F-12)

**Status**: DONE → CLOSE Q-VDO-RH family (2026-03-14)
**Nguồn gốc**: Finding F-12 (ablation A3/A5, nay đã chạy)
**Gate cho**: [d_regime_switch](../d_regime_switch/), [e_level_hysteresis](../e_level_hysteresis/)
**Evidence**: [debate/001-x34-findings/findings-under-review.md](../../debate/001-x34-findings/findings-under-review.md) §F-11, §F-12

## Kết quả thực chạy

- Scenario: `harsh`
- Window: `2019-01-01 -> 2026-02-20`
- E0 Sharpe: `1.2653`
- Full Q-VDO-RH Sharpe: `1.1507`
- A5 Sharpe: `1.2552`
- A3 Sharpe: `1.2572`
- Verdict: `CLOSE Q-VDO-RH family`

Diễn giải: cả A5 và A3 đều hồi gần về E0 và cải thiện mạnh so với full Q-VDO-RH,
nhưng không vượt E0. Đây là evidence rằng full variant thua chủ yếu vì normalized
input; hai ablation chỉ gỡ hại, không mở ra edge mới. Theo prereg, `d_` và `e_`
không mở.

---

## Giả thuyết

X34 Phase 3 REJECT, nhưng CHƯA trả lời: thất bại chủ yếu từ (a) quote-notional
normalized input `x_t`, (b) adaptive threshold `θ`, hay (c) interaction?

θ là nghi phạm mạnh nhất (evidence: θ evolution plots, Phase 1 constant-pressure
test), nhưng cần ablation để có proof of causation.

## Thiết kế — 2 ablation tests

### A5: VDO gốc + adaptive θ

- Input: `vdr = (taker_buy - taker_sell) / volume` (VDO gốc, bounded [-1,1])
- Threshold: adaptive `θ = k * EMA(|m - EMA(m)|)` (từ Q-VDO-RH)
- Entry: `vdo_momentum > adaptive_theta`
- Mục đích: **Isolate θ contribution**

Kỳ vọng:
- Nếu A5 ≈ full Q-VDO-RH (cả hai REJECT tương tự) → θ là thủ phạm chính
- Nếu A5 >> full Q-VDO-RH → normalized input `x_t` là thủ phạm

### A3: Ratio mode (no magnitude)

- Input: `x_t = delta_t / quote_volume_t` (per-bar quote ratio, mất magnitude)
- Threshold: adaptive θ (giữ nguyên)
- Entry: `ratio_momentum > adaptive_theta`
- Mục đích: **Test giả thuyết cốt lõi** — magnitude có thêm giá trị không?

**Confound note**: A3 dùng quote-currency per-bar ratio, trong khi VDO gốc dùng
base-currency per-bar ratio (`(taker_buy - taker_sell) / volume`). A3 là isolate
tốt so với full Q-VDO-RH (chỉ thay EMA normalization bằng per-bar), nhưng không
phải isolate hoàn hảo so với VDO gốc (khác cả currency). Cho mục đích chính
(A3 vs full = test magnitude), confound này chấp nhận được.

Kỳ vọng:
- Nếu A3 ≈ full Q-VDO-RH → magnitude không thêm value
- Nếu A3 < full Q-VDO-RH → normalization by `EMA(quote_volume)` có giá trị

### Ngưỡng verdict

Tất cả so sánh dùng ΔSharpe (harsh, cùng evaluation region):

- **≈** (tương đương): |ΔSharpe| < 0.03
- **>>** (tốt hơn rõ): ΔSharpe ≥ +0.03
- **<<** (tệ hơn rõ): ΔSharpe ≤ -0.03

### Ma trận kết quả

So sánh A5 và A3 với full Q-VDO-RH (rerun, cùng evaluation region — xem §Bước 3):

| A5 vs full | A3 vs full | Kết luận | Hành động |
|------------|------------|----------|-----------|
| ≈ (cả hai bad) | ≈ | θ là thủ phạm, input không quan trọng | CLOSE Q-VDO-RH family |
| ≈ | << | θ là thủ phạm, nhưng normalized input có value | GO d_ (normalized input, θ=0) |
| >> | ≈ | Input `x_t` là thủ phạm, θ không quan trọng | Xem §A5 vs E0 key test |
| >> | << | Cả hai contribute | GO d_ (test cả normalized input lẫn θ-free variant). d_ phải preregister cách dùng 2 components — xem §Mixed-case |
| << | bất kỳ | Normalized input tốt hơn VDO gốc khi cùng θ | Ghi nhận, kết hợp với A5 vs E0 |
| bất kỳ | >> | Per-bar ratio tốt hơn EMA-normalized | Unexpected — ghi nhận, review giả thuyết |

### A5 vs E0 — key test

Phép thử trực tiếp nhất cho "adaptive θ phá hủy signal VDO gốc":

- A5 = VDO gốc + adaptive θ
- E0 = VDO gốc, θ = 0

| A5 vs E0 | Kết luận |
|----------|----------|
| A5 << E0 (ΔSharpe ≤ -0.03) | **θ phá hủy signal VDO gốc** — proof trực tiếp |
| A5 ≈ E0 | θ không giúp cũng không hại trên VDO gốc |
| A5 >> E0 | θ cải thiện VDO gốc — đáng khám phá thêm |

**Nếu A5 >> full (ma trận row 3) VÀ A5 << E0**: input normalization hại, θ cũng hại.
→ CLOSE toàn bộ Q-VDO-RH family (không có component nào cứu được).

**Nếu A5 >> full VÀ A5 ≈ E0**: input normalization hại, θ trung tính.
→ CLOSE (θ không thêm value, input hại — không có gì để mở nhánh).

**Nếu A5 >> full VÀ A5 >> E0**: input normalization hại, nhưng θ cải thiện VDO gốc.
→ Kết quả bất ngờ. Ghi nhận vào `attribution_matrix.md`, review lại giả thuyết
  trước khi quyết định mở nhánh nào. KHÔNG tự động GO.

### Mixed-case preregistration

Nếu ma trận ra ô "cả hai contribute" (A5 >> full, A3 << full):
- d_regime_switch sẽ test **normalized input (`x_t`) với θ=0** (dùng như regime signal,
  không dùng adaptive threshold)
- Nếu d_ STOP → e_ KHÔNG mở (không còn viable component)
- Nếu d_ positive → e_ test level field `l_t` từ cùng normalized input pipeline

## Bước thực hiện

1. **Implement A5 strategy** (`c_ablation/code/strategy_a5.py`):
   - Clone từ `strategies/vtrend_qvdo/strategy.py` (canonical implementation)
   - Thay Q-VDO-RH normalized input bằng VDO gốc input (`vdr`)
   - Giữ adaptive θ mechanism
   - Expose qua standalone runner `c_ablation/code/run_c_ablation.py`

2. **Implement A3 strategy** (`c_ablation/code/strategy_a3.py`):
   - Clone từ `strategies/vtrend_qvdo/strategy.py`
   - Thay `x_t = delta / EMA(quote_vol)` bằng `x_t = delta / quote_vol_t` (per-bar ratio)
   - Expose qua standalone runner `c_ablation/code/run_c_ablation.py`

3. **Chạy backtest** cho cả 4 variants trên **cùng evaluation region**:
   - **Rerun tất cả 4**: E0, A3, A5, full Q-VDO-RH — không reuse kết quả b_e0_entry
   - Evaluation region: 2019-01-01 → 2026-02-20 (giữ nguyên với b_e0_entry để
     so sánh apples-to-apples; region 2023-01 bị bỏ vì không có lý do documented
     để cắt bớt data)
   - Baseline: E0 (VDO gốc, `vtrend`)
   - Cost: harsh (50 bps RT)
   - Validation scope: comparison metrics (Sharpe/CAGR/MDD harsh) cho attribution.
     Chỉ mở rộng sang smart/base hoặc suite sâu hơn nếu có variant vượt ngưỡng GO.

4. **So sánh**: attribution matrix (E0, A3, A5, full Q-VDO-RH)
   - Key comparisons: A5 vs full (isolate input), A3 vs full (isolate magnitude),
     **A5 vs E0** (isolate θ trực tiếp)

## STOP criteria

- A5 ≈ full AND A3 ≈ full AND A5 << E0 → **CLOSE** toàn bộ Q-VDO-RH family.
  θ là thủ phạm, không có component có giá trị. d_ và e_ không mở.
- A3 ≈ full (magnitude vô giá trị) → **CLOSE** normalized input direction.
- A5 >> full AND A5 << E0 → **CLOSE** (input hại, θ cũng hại).
- A5 >> full AND A5 ≈ E0 → **CLOSE** (input hại, θ trung tính — không có value).

## GO criteria → d_regime_switch

Tất cả điều kiện phải thỏa mãn đồng thời:

1. ≥ 1 component có ΔSharpe ≥ 0.03 vs full Q-VDO-RH (component đó cải thiện
   được tình hình so với full Q-VDO-RH)
2. Component đó KHÔNG tệ hơn E0 (ΔSharpe vs E0 ≥ -0.03) — gate chống lại việc
   mở downstream cho variant vẫn thua baseline
3. Causal attribution rõ ràng (biết component nào có giá trị và sẽ dùng gì ở d_)

## Deliverables

- `code/run_c_ablation.py` — standalone Pattern A runner
- `code/smoke_checks.py` — branch-local smoke checks cho A3/A5
- `results/a5_validation_report.md`
- `results/a3_validation_report.md`
- `results/attribution_matrix.md` — bảng 4 chiều + A5 vs E0 key test + verdict
