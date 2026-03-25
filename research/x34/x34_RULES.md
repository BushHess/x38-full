# X34 — Quy Định Riêng

**Kế thừa: [`CLAUDE.md`](../../CLAUDE.md) → [`RESEARCH_RULES.md`](../../docs/research/RESEARCH_RULES.md) → file này.**
**Tài liệu này bổ sung quy định riêng cho `research/x34/`.**

---

## 1. Write zone

```
research/x34/**/*          ← toàn bộ code, data, results
```

**Ngoại lệ duy nhất đã cấp (DONE, không mở thêm)**: Phase 0 — thêm `quote_volume`
và `taker_buy_quote_vol` vào `v10/core/types.py` và `v10/core/data.py`.

---

## 2. Import nội bộ x34

Ngoài các import chung (xem `RESEARCH_RULES.md` §3), x34 có thêm:

```python
# Shared indicators
from research.x34.shared.indicators.q_vdo_rh import q_vdo_rh, QVDOResult

# Branch code (ví dụ)
from research.x34.branches.c_ablation.code.strategy_a5 import VTrendA5Strategy, VTrendA5Config
from research.x34.branches.c_ablation.code.common import adaptive_gate, ema, atr
```

Import giữa branches được phép nhưng nên hạn chế — mỗi branch tự chứa tốt nhất.

---

## 3. Cấu trúc thư mục chuẩn cho mỗi nhánh

```
branches/<branch_name>/
├── PLAN.md                 ← preregistered design + verdict criteria
├── code/
│   ├── __init__.py
│   ├── common.py           ← shared helpers (EMA, ATR, adaptive_gate, ...)
│   ├── strategy_xxx.py     ← Strategy subclass (Pattern A)
│   └── run_<branch>.py     ← standalone runner
├── results/
│   ├── *_report.md
│   └── attribution_matrix.md
└── figures/                ← plots (optional)
```

**Lưu ý**: YAML configs (`configs/`) không cần cho Pattern A (instantiate trực tiếp).
Nếu branch cũ có `configs/` từ trước khi rules này được viết — đó là vestigial, có thể xóa.

---

## 4. Checklist bổ sung (ngoài checklist chung)

- [ ] Code chỉ nằm trong `research/x34/`
- [ ] Runner tự chứa, chạy được bằng `python run_<branch>.py`
- [ ] Results output vào `branches/<branch>/results/`
- [ ] PLAN.md có verdict criteria preregistered
- [ ] Không sử dụng Phase 0 exception (đã DONE, đóng)

---

## 5. Tham khảo x34

| Branch | Status | Mô tả |
|--------|--------|-------|
| a_diagnostic | DONE | Signal comparison diagnostic |
| b_e0_entry | DONE (REJECT) | Q-VDO-RH Option A entry-only test |
| c_ablation | DONE → CLOSE family | Input vs threshold causal attribution |
| d_regime_switch | CLOSED (gate failed at c_) | Conditional edge by regime |
| e_level_hysteresis | CLOSED (gate failed at c_) | Level field + hysteresis test |

Xem thêm: [`PLAN.md`](PLAN.md) (master plan), [`LARGER_PATH_THESIS.md`](LARGER_PATH_THESIS.md) (project-level thesis).
