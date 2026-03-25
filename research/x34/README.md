# X34 — VDO Replacement Research

**Status**: CLOSED for Q-VDO-RH family (Option A REJECT + c_ablation close)
**Ngày bắt đầu**: 2026-03-13

---

## Mục tiêu

Nghiên cứu và xác nhận các biến thể thay thế VDO gốc (ratio-based, bounded [-1,1])
trong VTREND. Bắt đầu với Q-VDO-RH, có thể mở rộng sang R-WVDO hoặc biến thể khác.

**Nguyên tắc cốt lõi**: Mọi biến thể là indicator MỚI. Bằng chứng của VDO gốc
KHÔNG transfer sang. Phải chứng minh từ đầu qua branch-local research runner và
preregistered verdict criteria.

## Kế hoạch chi tiết

→ [PLAN.md](PLAN.md)

---

## Branch Index

Mỗi nhánh là thư mục riêng với PLAN.md riêng, hoàn toàn cách ly.

| Nhánh | Thư mục | Mô tả | Status | Gate bởi |
|-------|---------|-------|--------|----------|
| — | `shared/` | Indicator code + unit tests | DONE | — |
| Diagnostic | [`a_diagnostic/`](branches/a_diagnostic/PLAN.md) | So sánh signal Q-VDO-RH vs VDO | DONE → GO | Phase 1 |
| Option A | [`b_e0_entry/`](branches/b_e0_entry/PLAN.md) | E0 + Q-VDO-RH (preregistered) | DONE → **REJECT** | a_ |
| Ablation | [`c_ablation/`](branches/c_ablation/PLAN.md) | A3/A5: input vs threshold | DONE → **CLOSE family** | b_ findings |
| Regime switch | [`d_regime_switch/`](branches/d_regime_switch/PLAN.md) | Conditional edge by regime (F-03) | CLOSED | c_ |
| Level/Hysteresis | [`e_level_hysteresis/`](branches/e_level_hysteresis/PLAN.md) | Untested components (F-02) | CLOSED | c_ + d_ |

Thêm nhánh mới → lấy chữ cái tiếp theo: `f_`, `g_`, ...

**Nhánh tương lai** (nếu cần):
- `f_e0_rwvdo/` — R-WVDO (ratio-bounded weighted)
- `g_e0_mode_b/` — Q-VDO-RH Mode B (Student-t BVC fallback)
- `h_e0_adaptive_theta/` — giữ lại như ý tưởng lịch sử; không còn active sau c_

---

## Infrastructure Gap

~~**CRITICAL**: `Bar` dataclass thiếu `quote_volume` và `taker_buy_quote_vol`.~~
**DONE** (Phase 0): `v10/core/types.py` và `v10/core/data.py` đã patched. Xem PLAN.md §Phase 0.

---

## Isolation Rules

1. **`resource/`** — FROZEN, read-only. Không sửa, chỉ đọc.
2. **`shared/`** — Source duy nhất cho indicator code. Variants import từ đây.
3. **Mỗi variant (`b_`, `c_`, ...)** — tự chứa: `code/`, `results/`, `figures/`.
4. **Variant KHÔNG sửa variant khác** — không cross-reference results, không import strategy.
5. **Không sửa `strategies/` hoặc `v10/`** trong quá trình nghiên cứu — strategies nghiên cứu nằm trong `x34/*/code/`.
6. **Hệ thống chính chỉ bị sửa khi**: Phase 0 (infrastructure) hoặc sau verdict cuối cùng (nếu PROMOTE).

---

## Resource — READ-ONLY

```
resource/
├── phan-bien-avfc-wvdo-qvdo-rh.md       ← phân biệt AVFC / WVDO / Q-VDO / RH
└── Q-VDO-RH_danh-gia-va-ket-luan.md     ← đánh giá và kết luận Q-VDO-RH
```

---

## Directory Structure

```
x34/
├── README.md                    ← FILE NÀY — index + status
├── PLAN.md                      ← Kế hoạch index (dependency graph, branch table)
│
├── resource/                    ← FROZEN (read-only)
│   ├── phan-bien-avfc-wvdo-qvdo-rh.md
│   └── Q-VDO-RH_danh-gia-va-ket-luan.md
│
├── shared/                      ← Code dùng chung cho TẤT CẢ branches
│   ├── indicators/
│   │   └── q_vdo_rh.py
│   └── tests/
│       └── test_q_vdo_rh.py
│
├── branches/                    ← Tất cả nhánh nghiên cứu
│   ├── a_diagnostic/            ← DONE → GO
│   ├── b_e0_entry/              ← DONE → REJECT
│   ├── c_ablation/              ← DONE → CLOSE family
│   ├── d_regime_switch/         ← CLOSED (gate failed at c_)
│   ├── e_level_hysteresis/      ← CLOSED (gate failed at c_)
│   └── [f_..., g_..., ...]     ← Branches tương lai
│
├── debate/                      ← Post-hoc adversarial review
│   └── 001-x34-findings/
```

---

## Key Results

| Nhánh | Sharpe | CAGR % | MDD % | Trades | vs E0 | Verdict |
|-------|--------|--------|-------|--------|-------|---------|
| b_e0_entry (full Q-VDO-RH) | 1.151 | 42.8% | 45.0% | 154 | -0.115 Sharpe vs E0 | **REJECT** |
| c_ablation A5 | 1.255 | 49.2% | 44.7% | 162 | -0.010 Sharpe vs E0 | recovers toward E0 |
| c_ablation A3 | 1.257 | 49.3% | 44.4% | 162 | -0.008 Sharpe vs E0 | recovers toward E0 |
| E0 baseline | 1.265 | 52.0% | 41.6% | 192 | — | baseline winner |

---

## Decision Authority

Hiện tại X34 dùng branch-local research workflow, không hook vào `validation/`.

| Thành phần | Source of truth |
|---|---|
| Branch status | `PLAN.md` + từng `branches/*/PLAN.md` |
| c_ablation verdict | `branches/c_ablation/code/run_c_ablation.py` + `branches/c_ablation/results/attribution_matrix.md` |
| Shared indicator behavior | `shared/indicators/q_vdo_rh.py` + `shared/tests/test_q_vdo_rh.py` |

Legacy note:
- `branches/b_e0_entry/results/validation/` là historical artifact từ workflow cũ, giữ lại làm evidence. Xem `branches/b_e0_entry/results/validation/LEGACY_NOTE.md`.

---

## References

- [PLAN.md](PLAN.md) — Kế hoạch index (dependency graph, branch table)
- [resource/Q-VDO-RH_danh-gia-va-ket-luan.md](resource/Q-VDO-RH_danh-gia-va-ket-luan.md) — Q-VDO-RH spec
- [resource/phan-bien-avfc-wvdo-qvdo-rh.md](resource/phan-bien-avfc-wvdo-qvdo-rh.md) — AVFC/WVDO analysis
- [branches/c_ablation/results/attribution_matrix.md](branches/c_ablation/results/attribution_matrix.md) — final ablation verdict
- [LARGER_PATH_THESIS.md](LARGER_PATH_THESIS.md) — project-level interpretation
