# X40 — Quy Định Riêng

**Kế thừa: [`CLAUDE.md`](../../CLAUDE.md) → [`RESEARCH_RULES.md`](../../docs/research/RESEARCH_RULES.md) → file này.**
**Tài liệu này bổ sung quy định riêng cho `research/x40/`.**

---

## 0. x40 KHÔNG phải research study

x40 khác x0-x39: nó là **operational infrastructure** cho baseline qualification
và durability monitoring, không phải discovery hay experiment.

| | x0-x39 | x40 |
|---|--------|-----|
| Mục đích | Discovery, experiment | Verification, monitoring |
| Lifecycle | Chạy xong → đóng | Sống lâu dài, append data |
| Output | Report + verdict | Baseline status + decay metrics |

---

## 1. Write zone

```
research/x40/**/*          ← toàn bộ code, data, results
```

Không ngoại lệ. x40 KHÔNG sửa `v10/`, `strategies/`, `validation/`, `tests/`.

---

## 2. Import nội bộ x40

Ngoài các import chung (xem `RESEARCH_RULES.md` §3), x40 có thêm:

```python
# v10 data loading (cho cả OH0 và PF0)
from v10.core.data import DataFeed

# Self-contained baseline simulators (Pattern B)
from research.x40.oh0_strategy import run_oh0_sim
from research.x40.pf0_strategy import run_pf0_sim
```

x40 KHÔNG import từ `strategies/` hay `v10.core.engine`. Cả hai baselines đều
tự chứa (Pattern B). DataFeed chỉ dùng để load CSV, không dùng BacktestEngine.

---

## 3. Hai baseline chính thức

| ID | League | Source | Status |
|----|--------|--------|--------|
| `OH0_D1_TREND40` | `OHLCV_ONLY` | `x37/resource/gen1/v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md` | Control baseline |
| `PF0_E5_EMA21D1` | `PUBLIC_FLOW` | `research/x40/pf0_strategy.py` (self-contained) | Incumbent (HOLD) |

**League rule**: Không so sánh cross-league trừ khi ghi rõ là diagnostic.

---

## 4. Baseline levels & durability statuses

### Levels (qualification state)
- `B0_INCUMBENT` — best-known reference, chưa qualified đầy đủ
- `B1_QUALIFIED` — passed source parity + qualification gates
- `B_FAIL` — failed

### Durability (A01 output, chỉ cho active baselines)
- `DURABLE` / `WATCH` / `DECAYING` / `BROKEN`

Hai namespace này TÁCH BIỆT. `B1_QUALIFIED + WATCH` là hợp lệ.

---

## 5. Study scopes

### Active (implemented)
- **A00**: Source parity replay — reproduce authoritative source artifacts
- **A01**: Temporal decay — era splits + rolling Sharpe

### Deferred (specs preserved, activate khi cần)
- A02 (alpha half-life), A03 (capacity/crowding), A04 (entry/exit attribution)
- A05 (canary drift), A06 (requalification), A07 (league pivot)

Xem `DEFERRED.md` cho full specs.

---

## 6. Runner pattern

Cả hai baselines đều dùng **Pattern B** (vectorized indicators + sequential
position loop, self-contained). Không dùng BacktestEngine.

- OH0: `oh0_strategy.py` — D1 vectorized sim
- PF0: `pf0_strategy.py` — H4+D1 vectorized sim

Cost model: simple per-side fraction, **default 20 bps RT** cho cả hai.
Cost sweep [10, 20, 30, 50, 75, 100] bps RT cho sensitivity analysis.

```bash
cd /var/www/trading-bots/btc-spot-dev
source /var/www/trading-bots/.venv/bin/activate
python research/x40/replay.py                    # A00: cả 2 baselines
python research/x40/studies/a01_temporal_decay.py # A01: decay analysis
```

---

## 7. Output layout

```
research/x40/
├── results/
│   ├── OH0_D1_TREND40/
│   │   ├── a00_parity_result.json
│   │   └── a01_decay_summary.json
│   └── PF0_E5_EMA21D1/
│       ├── a00_parity_result.json
│       └── a01_decay_summary.json
└── output/
    └── (plots, CSVs from studies)
```

---

## 8. Checklist

- [ ] Code chỉ nằm trong `research/x40/`
- [ ] Runner tự chứa, chạy được standalone
- [ ] Import từ strategies/ chỉ để ĐỌC (baseline replay)
- [ ] Không sửa file nào ngoài write zone
- [ ] Output vào `results/` hoặc `output/`
