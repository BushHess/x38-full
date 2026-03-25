# X35 — Kế hoạch nghiên cứu

**Tài liệu này là INDEX của research program.**  
Nhánh nghiên cứu chỉ là một phần của chương trình; xem thêm [README.md](README.md),
[program/01_problem_statement.md](program/01_problem_statement.md), [program/03_formalization.md](program/03_formalization.md),
và [x35_RULES.md](x35_RULES.md).

---

## Trạng thái nhận thức

`Longer-horizon regime research` không phải là một “plan đã nghiên cứu sâu sẵn”.
Nó khởi đầu như một **category hypothesis** suy ra từ prior evidence của repo.

`x35` có nhiệm vụ biến category đó thành:

1. problem statement cụ thể;
2. information families rõ ràng;
3. go/no-go criteria đúng;
4. candidate design thấp DOF nếu evidence đủ mạnh.

## Giả thuyết chính

Một **outer regime state** ở horizon weekly/monthly có thể bổ sung thông tin
orthogonal cho `E5+EMA21D1`, nhưng chỉ nếu nó:

- thật sự chậm hơn D1 inner filter;
- tách được good entries khỏi bad entries;
- tránh rơi vào tradeoff quen thuộc của slow daily filters: chỉ giảm MDD nhưng không
  cải thiện Sharpe/return profile.

## Điều x35 KHÔNG làm

- không tinh chỉnh `D1 EMA21` strength;
- không thay inner D1 filter bằng `EMA63d/126d/200d`;
- không chạm exit, cooldown, vol-target sizing;
- không dùng class dữ liệu mới ngoài OHLCV hiện có.

## Chương trình nghiên cứu first-principles

| Phase | File | Mục tiêu | Status |
|------|------|----------|--------|
| 1 | [program/01_problem_statement.md](program/01_problem_statement.md) | Định nghĩa câu hỏi và boundary | DONE |
| 2 | [program/02_phenomenon_survey.md](program/02_phenomenon_survey.md) | Khảo sát phenomenon và unknowns | DONE for current entry-state pass |
| 3 | [program/03_formalization.md](program/03_formalization.md) | Formalize decision problem, action classes, state families | DONE |
| 4 | [program/04_go_no_go.md](program/04_go_no_go.md) | Tách menu-level no-go khỏi program-level no-go | DONE |
| 5 | [program/05_design.md](program/05_design.md) | Freeze candidate only after evidence | SKIPPED_NO_CANDIDATE |
| 6 | [program/06_validation.md](program/06_validation.md) | Validation branch results | SKIPPED_NO_CANDIDATE |
| 7 | [program/07_final_report.md](program/07_final_report.md) | Final verdict | DONE |

## Bảng nhánh nghiên cứu

| Nhánh | Thư mục | Mô tả | Status | Gate bởi |
|-------|---------|-------|--------|----------|
| Shared | `shared/` | Aggregation + frozen state definitions + tests | DONE | — |
| Pilot probe | [a_state_diagnostic/](branches/a_state_diagnostic/PLAN.md) | Heuristic menu pre-screen inside the broader program | DONE → **NO_GO current menu** | Phase 2 pilot |
| Stress scan | [c_stress_state_diagnostic/](branches/c_stress_state_diagnostic/PLAN.md) | F3 survey: stress/drawdown family scan | DONE → **NO_GO stress family** | Phase 2 survey |
| Trend scan | [d_multi_horizon_trend_diagnostic/](branches/d_multi_horizon_trend_diagnostic/PLAN.md) | F2 survey: weekly multi-horizon trend structure scan | DONE → **NO_GO F2 trend family** | Phase 2 survey |
| Transition scan | [e_transition_instability_diagnostic/](branches/e_transition_instability_diagnostic/PLAN.md) | F4 survey: transition / instability scan | DONE → **NO_GO F4 transition family** | Phase 2 survey |
| Price-level scan | [f_price_level_state_diagnostic/](branches/f_price_level_state_diagnostic/PLAN.md) | Residual F1 survey: signed distance to slow anchors | DONE → **NO_GO F1 price-level family** | Phase 2 survey |
| Hazard scan | [g_mid_trade_hazard_diagnostic/](branches/g_mid_trade_hazard_diagnostic/PLAN.md) | Class B falsification pass for `FORCE_FLAT` | DONE → **NO_GO mid-trade hazard family** | Phase 4 continuation |
| Entry overlay | [b_entry_overlay/](branches/b_entry_overlay/PLAN.md) | Validation branch after first-principles GO | ARCHIVED_UNOPENED | Phase 5 gate |

## Dependency graph

```
problem statement
      │
      ▼
phenomenon survey ──► pilot branch a_state_diagnostic
      │                     │
      │                     └── NO_GO current menu
      ▼
formalization
      │
      ▼
go/no-go at program level
      │
      ├── insufficient evidence across families / actions ──► stop x35
      │
      └── sufficient evidence ──► design ──► branch b_entry_overlay
```

## Kết quả hiện tại

Branch `a_state_diagnostic` đã chạy xong current heuristic menu và không tìm được
candidate nào vượt toàn bộ diagnostic gates. Branch `c_stress_state_diagnostic`
cũng không tìm thấy feature stress/drawdown nào đạt branch GO criteria.
Các branch `d_`, `e_`, `f_` lần lượt loại F2, F4, và residual F1 signed-distance.
Branch `g_` loại continuation Class B ở dạng weekly instability force-flat.

Kết luận đúng hiện tại là:

- menu hiện tại fail;
- stress family hiện tại fail;
- F2/F4/residual F1 đều fail ở level survey;
- Class B hazard pass fail do coverage quá thấp và selectivity không đủ;
- `x35` không còn basis để mở branch validation;
- current program should be treated as **complete and negative**.

## Nguyên tắc xuyên suốt

- Mỗi branch có runner riêng và kết quả ghi branch-local.
- Parameter/state menu phải freeze trước khi nhìn kết quả branch đó.
- Heuristic probe fail không được phép tự động đóng cả research program.
- Nếu PLAN mô tả khác với code runner, **code thắng**.
- Root `code/` chỉ là wrapper; canonical logic nằm trong `shared/` và `branches/`.

## Kế hoạch chi tiết các nhánh

1. [branches/a_state_diagnostic/PLAN.md](branches/a_state_diagnostic/PLAN.md) — pilot branch đã chạy
2. [branches/c_stress_state_diagnostic/PLAN.md](branches/c_stress_state_diagnostic/PLAN.md) — stress family scan đã chạy
3. [branches/d_multi_horizon_trend_diagnostic/PLAN.md](branches/d_multi_horizon_trend_diagnostic/PLAN.md) — F2 trend-structure scan đã chạy, verdict âm
4. [branches/e_transition_instability_diagnostic/PLAN.md](branches/e_transition_instability_diagnostic/PLAN.md) — F4 transition / instability scan đã chạy, verdict âm
5. [branches/f_price_level_state_diagnostic/PLAN.md](branches/f_price_level_state_diagnostic/PLAN.md) — residual F1 signed-distance scan đã chạy, verdict âm
6. [branches/g_mid_trade_hazard_diagnostic/PLAN.md](branches/g_mid_trade_hazard_diagnostic/PLAN.md) — Class B hazard scan đã chạy, verdict âm
7. [branches/b_entry_overlay/PLAN.md](branches/b_entry_overlay/PLAN.md) — validation branch, không mở trong current program
