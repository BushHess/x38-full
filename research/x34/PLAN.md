# X34 — Kế hoạch nghiên cứu

**Tài liệu này là INDEX. Kế hoạch chi tiết nằm trong PLAN.md của từng nhánh.**
Xem [README.md](README.md) cho status tổng quát và isolation rules.

---

## Giả thuyết chính

Q-VDO-RH sửa đúng lỗi cấu trúc của VDO gốc (mất magnitude vì normalize per-bar)
sẽ cải thiện chất lượng entry filter, từ đó cải thiện Sharpe/MDD/CAGR.

Status sau c_ablation: giả thuyết này đã bị bác cho hướng `Q-VDO-RH Mode A`
dùng như entry gate. Full variant thua chủ yếu vì normalized input; A3/A5 chỉ
phục hồi gần về E0, không vượt baseline.

### Sự khác biệt cốt lõi

| | VDO gốc | Q-VDO-RH |
|---|---|---|
| **Input** | `(taker_buy - taker_sell) / volume` (base BTC) | `(2*takerBuyQuote - quoteVolume) / EMA(quoteVolume, slow)` (quote USDT) |
| **Range** | Bounded [-1, +1] | Unbounded, regime-adaptive |
| **Magnitude** | Mất (per-bar ratio) | Giữ (normalized by activity regime) |
| **Threshold** | Fixed (`vdo_threshold = 0.0`) | Adaptive (`k * robust_MAD_scale`) |
| **Smoothing** | `EMA(vdr, fast) - EMA(vdr, slow)` | `EMA(x, fast) - EMA(x, slow)` (tương tự nhưng input khác) |
| **Hysteresis** | Không | Có (entry `> θ`, hold tới `< 0.5θ`) |
| **Fallback (no taker)** | OHLC range: `(C-L)/(H-L)*2-1` | BVC proxy: Student-t CDF *(deferred)* |
| **Params (tunable)** | 2: `vdo_fast`, `vdo_slow` + 1 threshold | 3: `fast`, `slow`, `k` |

---

## Bảng nhánh nghiên cứu

| Nhánh | Thư mục | Mô tả | Status | Gate bởi |
|-------|---------|-------|--------|----------|
| Phase 0 | *(v10/core/)* | Infrastructure: thêm quote_volume vào Bar | DONE | — |
| Phase 1 | `shared/` | Implement Q-VDO-RH indicator (Mode A) | DONE | — |
| Diagnostic | [a_diagnostic/](branches/a_diagnostic/PLAN.md) | So sánh signal Q-VDO-RH vs VDO gốc | DONE → GO | Phase 1 |
| Option A | [b_e0_entry/](branches/b_e0_entry/PLAN.md) | E0 + Q-VDO-RH (preregistered defaults) | DONE → **REJECT** | Diagnostic |
| Ablation | [c_ablation/](branches/c_ablation/PLAN.md) | A3/A5: input vs threshold causation | DONE → **CLOSE family** | b_ REJECT findings |
| Regime switch | [d_regime_switch/](branches/d_regime_switch/PLAN.md) | F-03: conditional edge by regime | CLOSED (gate failed at c_) | c_ (≥1 component có giá trị) |
| Level/Hysteresis | [e_level_hysteresis/](branches/e_level_hysteresis/PLAN.md) | F-02: untested Q-VDO-RH components | CLOSED (gate failed at c_) | c_ + d_ positive |
| ~~Option B~~ | ~~c_e0_hysteresis/~~ | ~~E0 + Q-VDO-RH + hysteresis exit~~ | SUPERSEDED | Merged into e_ |
| ~~Propagation~~ | ~~d_e5ema21_qvdo/~~ | ~~E5+EMA1D21 + Q-VDO-RH~~ | SUPERSEDED | Gated by b_ PROMOTE (never) |
| ~~Cross-variant~~ | ~~e_cross_variant/~~ | ~~So sánh cuối cùng~~ | SUPERSEDED | Gated by propagation (never) |

---

## Dependency graph

```
Phase 0 (infrastructure) → Phase 1 (indicator) → a_diagnostic (GO)
                                                       │
                                                       ▼
                                                  b_e0_entry (REJECT)
                                                       │
                                    ┌──────────────────┘
                                    │ Findings F-03, F-12, F-02
                                    ▼
                               c_ablation (DONE → CLOSE)
                                    │
                                    ▼
                           full loses mainly from
                           normalized input
                                    │
                                    ▼
                         d_ and e_ stay CLOSED
```

---

## Nguyên tắc xuyên suốt

- Mỗi nhánh có STOP criteria rõ ràng — dừng ngay khi thấy tín hiệu thất bại
- Baseline luôn là thuật toán ĐANG chạy, không phải benchmark lý thuyết
- **Anti-leakage**: Parameter phải được chọn TRƯỚC KHI nhìn evaluation data
- Kết quả nằm TRONG thư mục nhánh tương ứng, không trộn lẫn
- Nếu PLAN.md mô tả gate khác với code → **code thắng**

---

## Phase 0 — Hạ tầng dữ liệu (DONE)

**Scope**: Mở rộng `Bar` dataclass để load `quote_volume` và `taker_buy_quote_vol`.
Đây là NGOẠI LỆ DUY NHẤT cho rule "không sửa hệ thống chính".

- `v10/core/types.py` — Bar mở rộng (thêm 2 fields với defaults)
- `v10/core/data.py` — `_row_to_bar()` patched với `.get()` fallback
- Regression: tất cả test pass, backtest E0/E5/E5+EMA1D21 bit-for-bit identical

---

## Phase 1 — Implement Q-VDO-RH (DONE)

**Output**: `shared/indicators/q_vdo_rh.py` + `shared/tests/test_q_vdo_rh.py`

Mode A only (có taker quote data). Mode B (BVC fallback) deferred — spec chưa freeze.

```
delta_t = 2 * taker_buy_quote_t - quote_volume_t
x_t = delta_t / (EMA(quote_volume, slow) + eps)
m_t = EMA(x, fast) - EMA(x, slow)        ← momentum
l_t = EMA(x, slow)                        ← level (context only)
scale_t = EMA(|m - EMA(m, slow)|, slow) + eps
theta_t = k * scale_t                     ← adaptive threshold
```

Output struct: `momentum`, `level`, `scale`, `theta`, `long_trigger`, `long_hold`,
`high_confidence`.

---

## Kế hoạch chi tiết các nhánh

Xem PLAN.md trong từng thư mục:

1. [branches/a_diagnostic/PLAN.md](branches/a_diagnostic/PLAN.md) — diagnostic (DONE)
2. [branches/b_e0_entry/PLAN.md](branches/b_e0_entry/PLAN.md) — Option A validation (DONE → REJECT)
3. [branches/c_ablation/PLAN.md](branches/c_ablation/PLAN.md) — A3/A5 ablation (DONE → CLOSE family)
4. [branches/d_regime_switch/PLAN.md](branches/d_regime_switch/PLAN.md) — archival prereg, not opened
5. [branches/e_level_hysteresis/PLAN.md](branches/e_level_hysteresis/PLAN.md) — archival prereg, not opened

---

## Rủi ro & biện pháp giảm thiểu

| Rủi ro | Khả năng | Biện pháp |
|---|---|---|
| Q-VDO-RH ≈ VDO gốc (ρ > 0.95) | — | a_ phát hiện sớm (ρ=0.887, OK) |
| Adaptive θ overfit | Cao | c_ ablation A5 isolate |
| Improvement chỉ từ threshold | Trung bình | c_ ablation A5 vs A3 |
| Conditional edge là noise | Trung bình | d_ correlation test + WFO |
| Hysteresis complexity không value | Trung bình | e_ ablation A2 |
| Toàn bộ Q-VDO-RH family vô giá trị | Trung bình | c_ là gate — CLOSE sớm nếu cả A3 và A5 fail |

---

## Mở rộng sau này

Nếu Q-VDO-RH family CLOSE nhưng diagnostic cho tín hiệu thú vị:

| Variant | Thư mục | Mô tả |
|---|---|---|
| R-WVDO | `f_e0_rwvdo/` | Ratio-bounded weighted VDO (bounded, giữ magnitude) |
| Mode B | `g_e0_mode_b/` | Q-VDO-RH fallback proxy (Student-t BVC) |
| Adaptive θ only | `h_e0_adaptive_theta/` | Ý tưởng lịch sử; không được support bởi kết quả `c_ablation` hiện tại |
