# a_state_diagnostic — Outer State Diagnostic

**Status**: DONE → `NO_GO_CURRENT_MENU` (2026-03-14)  
**Nguồn gốc**: [../../PLAN.md](../../PLAN.md) Phase 2 pilot probe  
**Runner**: `code/run_a_state_diagnostic.py`

---

## Mục tiêu

Trước khi formalize candidate design, branch này trả lời một câu hỏi hẹp hơn:

> Outer state weekly/monthly có thật sự tách được quality của baseline E5 entries hay không?

Branch này chỉ làm diagnostic cho **một menu heuristic frozen sớm**. Nó không backtest
candidate overlay, và cũng không có authority để đóng toàn bộ `x35`.

## Frozen Candidate Menu

| Spec id | Clock | Rule |
|---------|-------|------|
| `wk_close_above_ema26` | W1 | risk_on if completed W1 close > W1 EMA(26) |
| `wk_ema13_above_ema26` | W1 | risk_on if completed W1 EMA(13) > EMA(26) |
| `mo_close_above_ema6` | M1 | risk_on if completed M1 close > M1 EMA(6) |

Không thêm candidate mới trong branch này.

Lưu ý: menu này là **pilot menu**, không phải toàn bộ state space của `x35`.

## Thiết kế

1. Phase 0: data audit cho H4/D1/W1/M1 coverage và warmup sufficiency.
2. Phase 1: map outer state vào:
   - lịch D1 report window;
   - entry timestamps của baseline `E5+EMA21D1`.
3. Đo 3 nhóm evidence:
   - sign separation;
   - profit/loss concentration;
   - chronological stability.

## Diagnostic Gates

| Gate | Condition |
|------|-----------|
| `D0_warmup` | warmup sufficiency = PASS |
| `D1_persistence` | flips/year <= 12 AND median_spell_days >= 14 |
| `D2_trade_split` | at least 20 baseline trades in each state |
| `D3_sign_separation` | mean return `risk_on` > 0 AND mean return `risk_off` < 0 |
| `D4_concentration` | `profit_share_on >= 0.70` AND `loss_share_off >= 0.55` |
| `D5_stability` | valid_folds >= 5 AND fold win rate >= 5/8 |

## GO / STOP

- Nếu có ít nhất 1 candidate PASS toàn bộ gates → branch này cho `GO_CURRENT_MENU`.
- Nếu không có candidate nào PASS → branch này cho `NO_GO_CURRENT_MENU`.

## Kết quả thực tế

Không candidate nào PASS toàn bộ gates.

| Spec | On trades | Off trades | Profit on % | Loss off % | Fold WR % | Verdict |
|------|-----------|------------|-------------|------------|-----------|---------|
| `wk_ema13_above_ema26` | 131 | 55 | 81.43 | 28.90 | 50.00 | STOP |
| `wk_close_above_ema26` | 137 | 49 | 80.08 | 23.26 | 57.14 | STOP |
| `mo_close_above_ema6` | 130 | 56 | 75.02 | 24.57 | 28.57 | STOP |

Diễn giải:

- positive PnL vẫn nằm chủ yếu ở `risk_on`, nhưng loss không tập trung vào `risk_off`;
- cả `risk_on` lẫn `risk_off` mean returns đều dương trong 2/3 candidates;
- stability theo chronological folds không đủ mạnh.

Kết luận đúng:

- menu heuristic hiện tại không tạo ra outer-state đủ hostile/favorable để mở overlay branch.
- Branch này là evidence chống lại **menu hiện tại**, không phải bằng chứng đủ để đóng cả `x35`.

## Deliverables

- `results/phase0_data_audit.json`
- `results/phase0_data_audit.md`
- `results/phase1_regime_decomposition.json`
- `results/phase1_regime_decomposition.md`
