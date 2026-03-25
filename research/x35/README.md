# X35 — Long Horizon Regime Research

**Status**: FINALIZED for current scope  
**Current research status**: entry pass DONE → negative; hazard pass DONE → negative; program closed  
**Ngày bắt đầu**: 2026-03-14

---

## Origin Status

`Longer-horizon regime research` ban đầu chỉ là **một category hypothesis** được nêu ra
từ evidence của `x25` và `x26`, chưa phải một kế hoạch nghiên cứu đã formalize sâu.

`x35` là nỗ lực biến category đó thành **một research program cụ thể**:

- xác định đúng decision problem;
- xác định đúng information families;
- tách rõ phenomenon survey khỏi candidate design;
- chỉ freeze candidate sau khi evidence đủ mạnh.

Vì vậy, một branch heuristic fail KHÔNG tự động đóng toàn bộ `x35`.

## Mục tiêu

Kiểm tra xem BTC spot OHLCV có chứa một **outer regime state** chậm hơn D1 EMA(21)
hay không, đủ để cải thiện `E5+EMA21D1` bằng một overlay ngoài ở horizon nhiều tuần/tháng.

Trong first validation pass, ưu tiên overlay nhẹ nhất:

- `entry_prevention_only`

Nhưng ở level research program, `x35` còn khảo sát cả không gian hành động rộng hơn:

- `NORMAL` — E5 chạy bình thường
- `DEFENSIVE` — chỉ admissible nếu evidence cho thấy sizing/state effect là thật
- `OFF` — chỉ admissible nếu evidence cho thấy hostile regime rõ ràng

Điều này được formalize ở [program/03_formalization.md](program/03_formalization.md).

## Kế hoạch chi tiết

→ [PLAN.md](PLAN.md)

## Branch Index

`x35` được tổ chức theo kiến trúc gần với `x34`: shared layer + branch-local runners
và branch-local results.

| Nhánh | Thư mục | Mô tả | Status | Gate bởi |
|-------|---------|-------|--------|----------|
| — | `shared/` | Calendar aggregation + frozen regime definitions | DONE | — |
| Pilot probe | [`a_state_diagnostic/`](branches/a_state_diagnostic/PLAN.md) | Heuristic menu pre-screen: state map, trade split, concentration, stability | DONE → **NO_GO current menu** | Phase 2 pilot |
| Stress scan | [`c_stress_state_diagnostic/`](branches/c_stress_state_diagnostic/PLAN.md) | Stress/drawdown family survey on baseline entries | DONE → **NO_GO stress family** | Phase 2 survey |
| Trend scan | [`d_multi_horizon_trend_diagnostic/`](branches/d_multi_horizon_trend_diagnostic/PLAN.md) | Multi-horizon weekly trend-structure survey | DONE → **NO_GO F2 trend family** | Phase 2 survey |
| Transition scan | [`e_transition_instability_diagnostic/`](branches/e_transition_instability_diagnostic/PLAN.md) | Transition / instability family survey | DONE → **NO_GO F4 transition family** | Phase 2 survey |
| Price-level scan | [`f_price_level_state_diagnostic/`](branches/f_price_level_state_diagnostic/PLAN.md) | Residual F1 signed-distance survey | DONE → **NO_GO F1 price-level family** | Phase 2 survey |
| Hazard scan | [`g_mid_trade_hazard_diagnostic/`](branches/g_mid_trade_hazard_diagnostic/PLAN.md) | Class B falsification pass: mid-trade hazard / force-flat | DONE → **NO_GO mid-trade hazard family** | Phase 4 continuation |
| Entry overlay | [`b_entry_overlay/`](branches/b_entry_overlay/PLAN.md) | Candidate validation branch after first-principles GO | ARCHIVED_UNOPENED | Phase 5 gate |

## Cấu trúc thư mục

```
x35/
├── README.md
├── PLAN.md
├── x35_RULES.md
├── manifest.json
│
├── program/                    ← numbered phase docs 01..07
│   ├── README.md
│   ├── 01_problem_statement.md
│   ├── 02_phenomenon_survey.md
│   ├── 03_formalization.md
│   ├── 04_go_no_go.md
│   ├── 05_design.md
│   ├── 06_validation.md
│   └── 07_final_report.md
│
├── code/                       ← root-level convenience wrappers only
│   └── run_all.py
│
├── shared/                     ← dùng chung cho mọi branch
│   ├── common.py
│   ├── state_definitions.py
│   └── tests/
│
├── branches/
│   ├── a_state_diagnostic/
│   │   ├── PLAN.md
│   │   ├── code/
│   │   └── results/
│   ├── c_stress_state_diagnostic/
│   │   ├── PLAN.md
│   │   ├── code/
│   │   └── results/
│   ├── d_multi_horizon_trend_diagnostic/
│   │   ├── PLAN.md
│   │   ├── code/
│   │   └── results/
│   ├── e_transition_instability_diagnostic/
│   │   ├── PLAN.md
│   │   ├── code/
│   │   └── results/
│   ├── f_price_level_state_diagnostic/
│   │   ├── PLAN.md
│   │   ├── code/
│   │   └── results/
│   ├── g_mid_trade_hazard_diagnostic/
│   │   ├── PLAN.md
│   │   ├── code/
│   │   └── results/
│   └── b_entry_overlay/
│       └── PLAN.md
│
└── results/                    ← root index only, canonical outputs nằm trong branch
```

## Kết quả hiện tại

Branch `a_state_diagnostic` đã chạy xong một **pilot heuristic menu**:

- `wk_close_above_ema26`
- `wk_ema13_above_ema26`
- `mo_close_above_ema6`

Kết quả: cả 3 đều pass warmup/persistence/trade-split, nhưng đều fail ở:

- sign separation;
- concentration;
- chronological stability.

Điều này chỉ có nghĩa:

- menu heuristic hiện tại không đủ tốt.

Nó **không** có nghĩa:

- `longer-horizon regime research` đã bị bác toàn bộ.

Do đó `x35` bây giờ được định nghĩa lại như một program first-principles với các
tài liệu pha nằm trong `program/`:

- [program/01_problem_statement.md](program/01_problem_statement.md)
- [program/02_phenomenon_survey.md](program/02_phenomenon_survey.md)
- [program/03_formalization.md](program/03_formalization.md)
- [program/04_go_no_go.md](program/04_go_no_go.md)
- [program/05_design.md](program/05_design.md)

Thêm vào đó, branch `c_stress_state_diagnostic` đã scan Family F3 và cho kết quả âm:

- drawdown depth 63d/126d không làm trade quality xấu đi theo cách monotonic hữu ích;
- vol shock 30d/180d thậm chí nghiêng ngược giả thuyết hostile-state;
- verdict của branch là `NO_GO_STRESS_FAMILY`.

Các branch khảo sát còn lại cũng cho kết quả âm:

- `e_transition_instability_diagnostic`: instability/ambiguity không tạo hostile state đủ rõ;
- `f_price_level_state_diagnostic`: signed distance tới slow anchor không có rho dương hay concentration đủ mạnh.

Vì vậy, sau `a_`, `c_`, `d_`, `e_`, `f_`, basic survey cho **entry-prevention outer state** hiện đang âm trên toàn bộ menu cơ bản đã khảo sát.

Branch `g_mid_trade_hazard_diagnostic` sau đó kiểm tra continuation admissible cuối cùng:

- force-flat giả định khi weekly instability xuất hiện giữa-trade;
- coverage chỉ `1.6%–2.7%` trades;
- spec tốt nhất vẫn fail selectivity threshold;
- branch verdict: `NO_GO_MID_TRADE_HAZARD_FAMILY`.

Branch `d_multi_horizon_trend_diagnostic` cụ thể cho Family F2 như sau:

- `wk_gap_13_26`: rho âm, separation yếu;
- `wk_gap_26_52`: rho dương nhưng delta mean return chỉ `0.46 pp`;
- `wk_alignment_score_13_26_52`: gom profit vào `S3` nhưng không tạo hostile state đủ rõ;
- branch verdict: `NO_GO_F2_TREND_FAMILY`.

Kết luận thực dụng hiện tại:

- **không mở `b_entry_overlay`**
- **không mở Class B force-flat validation**
- current `x35` scope nên được xem là **đã đóng với verdict âm**
- final verdict của current program là: `NO_ACTIONABLE_OUTER_STATE_IN_CURRENT_SCOPE`

## Decision Authority

| Thành phần | Source of truth |
|---|---|
| Study status | `README.md` + `PLAN.md` + `program/` docs + `manifest.json` |
| Shared regime logic | `shared/state_definitions.py` |
| Pilot current-menu verdict | `branches/a_state_diagnostic/results/phase1_regime_decomposition.md` |
| First-principles problem definition | `program/01_problem_statement.md` + `program/03_formalization.md` |
| Next branch gate | `program/04_go_no_go.md` + `branches/b_entry_overlay/PLAN.md` |

## References

- [PLAN.md](PLAN.md) — master index + dependency graph
- [program/01_problem_statement.md](program/01_problem_statement.md) — concrete research question
- [program/03_formalization.md](program/03_formalization.md) — first-principles formalization
- [program/07_final_report.md](program/07_final_report.md) — final verdict
- [x35_RULES.md](x35_RULES.md) — study-specific rules
- [branches/a_state_diagnostic/PLAN.md](branches/a_state_diagnostic/PLAN.md) — pilot prereg for current menu
