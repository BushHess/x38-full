# b_entry_overlay — Entry Prevention Overlay

**Status**: ARCHIVED_UNOPENED  
**Nguồn gốc**: [../../PLAN.md](../../PLAN.md) Phase 5

---

## Mục tiêu

Branch này được giữ lại như một prereg template archived.

Trong current `x35` scope, branch **không được mở** vì program-level evidence đã kết thúc
ở `STOP_WHOLE_X35_CURRENT_SCOPE`.

Về mặt lịch sử, nếu program-level evidence từng đủ mạnh, branch này sẽ test:

- baseline `E5+EMA21D1`;
- overlay `entry_prevention_only` bằng single selected outer state.

## Thiết kế preregistered

- Overlay chỉ được chặn entry mới khi `risk_off`.
- Không forced exit.
- Không giảm size trung gian.
- Không combine nhiều state.

## Validation Gates

| Gate | Condition |
|------|-----------|
| `V0_direction` | full-sample `Delta Sharpe > 0` at 50 bps RT |
| `V1_robustness` | chronological fold win rate >= 50% |
| `V2_bootstrap` | paired bootstrap `P(Delta Sharpe > 0) >= 0.55` |
| `V3_cagr_retention` | CAGR retained >= 85% of baseline OR `Delta Sharpe >= 0.10` |
| `V4_overblocking` | retained trade count >= 60% of baseline |

## Gate Status

Current reason not opened:

- no candidate emerged from the first-principles program with enough evidence;
- current scope is already closed by [../../program/07_final_report.md](../../program/07_final_report.md).

Important:

- `a_state_diagnostic` failing its pilot menu did **not** tự nó đóng branch này;
- nhưng sau khi `c_`, `d_`, `e_`, `f_`, và `g_` cũng fail, branch này được archive mà không chạy;
- bất kỳ validation work tương lai nào phải diễn ra trong study mới, không revive branch này bên trong `x35`.
