# b_e0_entry — E0 + Q-VDO-RH (Entry Filter Only, Option A)

**Status**: DONE → REJECT (exit 2, 2026-03-13)
**Nguồn gốc**: [../../PLAN.md](../../PLAN.md) Phase 3
**Findings**: [debate/001-x34-findings/](../../debate/001-x34-findings/) (F-01→F-09, F-13→F-15, meta-insight)

---

## Mục tiêu

Test Q-VDO-RH với params preregistered từ spec. Path A: params chọn TRƯỚC KHI nhìn data.

## Preregistered parameters

Cơ sở: giữ nguyên fast/slow từ VDO gốc (12/28), k=1.0 là neutral multiplier.

```
qvdo_fast   = 12     ← giữ nguyên VDO gốc
qvdo_slow   = 28     ← giữ nguyên VDO gốc
qvdo_k      = 1.0    ← neutral (1× MAD scale)
slow_period = 120    ← giữ nguyên E0
trail_mult  = 3.0    ← giữ nguyên E0
```

## Thiết kế

**Option A** (variant này): Entry filter only
- Entry: `trend_up AND qvdo_momentum > qvdo_theta`
- Exit: không đổi (ATR trail + EMA cross-down)
- Hysteresis KHÔNG dùng cho exit

## Bước thực hiện

1. Clone strategy từ `strategies/vtrend/strategy.py`
2. Thay entry condition: `vdo_val > threshold` → `momentum[i] > theta[i]`
3. Full validation `--suite all` — 7 gates, baseline = E0, cost harsh (50 bps RT)

## Verdict criteria

- PROMOTE (exit 0) → skip Phase 4, đi thẳng propagation
- HOLD (exit 1) → GO nested search + ablation (Phase 4)
- REJECT (exit 2) → STOP

## Kết quả thực tế

**Verdict: REJECT (exit 2)**

| Metric | Candidate | Baseline | Delta |
|--------|-----------|----------|-------|
| Sharpe | 1.151 | 1.265 | -0.115 |
| CAGR | 42.8% | 52.0% | -9.2pp |
| MDD | 45.0% | 41.6% | +3.4pp |
| Score (harsh) | 97.36 | 123.32 | -25.97 |

Gates: full_harsh_delta FAIL (-25.97), WFO FAIL (Wilcoxon p=0.68), PSR FAIL (0.005).
Holdout PASS (+19.12) — nghịch lý, gợi ý conditional edge (xem F-03).

**Phase 4 (sweep/ablation) KHÔNG chạy** vì REJECT. Ablation A3/A5 chuyển sang nhánh
riêng [c_ablation/](../c_ablation/) do causal question vẫn có giá trị.
