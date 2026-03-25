# e_transition_instability_diagnostic — Transition / Instability State Survey

**Status**: DONE → `NO_GO_F4_TRANSITION_FAMILY`  
**Nguồn gốc**: [../../program/02_phenomenon_survey.md](../../program/02_phenomenon_survey.md) Family F4  
**Runner**: `code/run_e_transition_instability_diagnostic.py`

---

## Mục tiêu

Kiểm tra xem **macro ambiguity / instability** ở weekly structure có tạo ra một
`unstable state` đủ hostile với baseline `E5+EMA21D1` hay không.

Branch này vẫn chỉ là **phenomenon survey**:

- không backtest overlay;
- không mở forced-exit logic;
- không combine nhiều family sau khi nhìn kết quả;
- không coi một binary instability flag là candidate design sẵn.

## Vì sao đây là bước nền đúng tiếp theo

Sau khi:

- Family F1 pilot menu fail;
- Family F2 minimal weekly trend structure fail;
- Family F3 coarse stress/drawdown fail;

family còn lại hợp logic nhất là:

- **F4 transition / instability**

Research question hẹp:

> Có phải E5 không thua vì market “bear” nói chung, mà thua vì market đang ở
> trạng thái slow-structure mơ hồ, flip nhiều, hoặc bất ổn?

## Frozen Instability Menu

Tất cả feature/state đều dùng **completed W1 bars**.

| Spec | Unstable state definition | Ý nghĩa |
|------|---------------------------|---------|
| `wk_mixed_structure_flag` | `alignment_score in {1, 2}` | horizons disagree instead of full alignment |
| `wk_flip_count_8w_ge_2` | weekly `alignment_score` changed at least 2 times in last 8 completed weeks | recent slow-state choppiness |
| `wk_score_range_8w_ge_2` | rolling 8-week range of `alignment_score` is at least 2 | structural instability amplitude |

Trong đó:

`alignment_score = 1(close > EMA26) + 1(EMA13 > EMA26) + 1(EMA26 > EMA52)`

Không thêm spec khác trong branch này.

## Thiết kế

1. Chạy baseline `E5+EMA21D1`.
2. Tạo weekly structure score từ D1 bars.
3. Tạo 3 binary instability states frozen ở trên.
4. Map states vào:
   - D1 report calendar;
   - entry timestamps của baseline trades.
5. Với mỗi spec, đo:
   - persistence;
   - stable-vs-unstable trade split;
   - sign separation;
   - concentration;
   - chronological stability.

## Branch GO / NO-GO

Một spec được xem là **promising** nếu thỏa đồng thời:

1. `warmup_ok = True`
2. `flips_per_year <= 20`
3. `median_spell_days >= 7`
4. `n_stable >= 20` và `n_unstable >= 20`
5. `mean_return_stable > 0`
6. `mean_return_unstable < 0`
7. `profit_share_stable >= 0.70`
8. `loss_share_unstable >= 0.55`
9. `valid_folds >= 5` và `fold_win_rate >= 0.625`

Branch verdict:

- Nếu có ≥1 spec promising → `GO_F4_TRANSITION_FAMILY`
- Nếu không có spec nào promising → `NO_GO_F4_TRANSITION_FAMILY`

## Deliverables

- `results/transition_instability_scan.json`
- `results/transition_instability_scan.md`

## Kết quả thực tế

Branch verdict: **`NO_GO_F4_TRANSITION_FAMILY`**

| Spec | Stable mean % | Unstable mean % | Profit stable % | Loss unstable % | Fold WR % | Verdict |
|------|---------------|-----------------|-----------------|-----------------|-----------|---------|
| `wk_mixed_structure_flag` | 2.5430 | 2.8022 | 76.33 | 31.08 | 50.0 | NO_GO |
| `wk_flip_count_8w_ge_2` | 3.0359 | 1.2352 | 88.79 | 15.63 | 100.0* | NO_GO |
| `wk_score_range_8w_ge_2` | 2.8182 | 1.0594 | 97.60 | 5.07 | 100.0* | NO_GO |

\* Fold win rate cao nhưng không đủ `valid_folds`, nên vẫn fail stability gate.

Diễn giải:

- mixed-structure state không hostile; unstable mean còn cao hơn stable mean;
- choppy / wide-range states có mean return thấp hơn, nhưng không tạo loss concentration vào unstable state;
- vì vậy ambiguity/instability không giải thích được bad entries theo cách đủ mạnh để mở overlay.
