# g_mid_trade_hazard_diagnostic — Mid-Trade Hazard Survey

**Status**: DONE → `NO_GO_MID_TRADE_HAZARD_FAMILY`  
**Nguồn gốc**: [../../program/03_formalization.md](../../program/03_formalization.md) Class B (`FORCE_FLAT`)  
**Runner**: `code/run_g_mid_trade_hazard_diagnostic.py`

---

## Mục tiêu

Kiểm tra câu hỏi còn lại của `x35`:

> Nếu outer state xấu xuất hiện **sau khi trade đã mở**, force-flat có giúp
> hơn exit thực tế của baseline hay không?

Branch này là **hazard diagnostic**, không phải validation branch:

- không backtest policy force-flat hoàn chỉnh;
- không sửa exit geometry;
- không combine nhiều weak states sau khi nhìn kết quả.

## Vì sao branch này mới admissible

Current pass của `x35` đã loại toàn bộ basic entry-state menu.

Do đó continuation hợp lệ duy nhất còn lại là:

- **mid-trade hazard / force-flat question**

Nhưng branch này phải được làm như một **falsification pass** vì repo đã có prior mạnh
chống mid-trade interventions:

- `x31-A` cho D1 flip verdict `STOP`
- `x31-B` cho re-entry oracle verdict `STOP`
- `x16/x23` cho stateful exit / exit geometry đều không robust

## Frozen Hazard Menu

Branch này chỉ dùng Family F4 weekly instability states, vì đây là family hợp logic nhất
cho “hazard xuất hiện giữa-trade”:

| Spec | Hazard hit definition |
|------|------------------------|
| `wk_mixed_structure_flag` | trade entered in `stable`, then first later H4 close mapped to `unstable` |
| `wk_flip_count_8w_ge_2` | same rule |
| `wk_score_range_8w_ge_2` | same rule |

Không thêm spec khác trong branch này.

## Thiết kế

1. Chạy baseline `E5+EMA21D1`.
2. Build weekly instability states từ `shared/`.
3. Map states vào H4 bars.
4. Với mỗi trade:
   - xác định `entry_state`;
   - chỉ xét trades vào ở `stable`;
   - tìm **first in-trade hazard hit** (`stable -> unstable`) trước actual exit.
5. Nếu hit tồn tại:
   - hypothetical force-flat fill = `next H4 open` sau hazard hit;
   - `edge_pct = force_flat_price / actual_exit_price - 1`.
6. Tổng hợp:
   - coverage;
   - timing (`bars_saved`);
   - loser benefit vs winner cost;
   - selectivity ratio;
   - top-20 winner damage.

## Branch GO / NO-GO

Một spec được xem là **promising** nếu thỏa đồng thời:

1. `coverage_pct >= 10`
2. `median_bars_saved >= 2`
3. `loser_mean_edge_pct > 0`
4. `winner_mean_edge_pct < 0`
5. `selectivity_ratio >= 1.5`
6. `top20_hit_count <= 2`

Trong đó:

`selectivity_ratio = loser_mean_edge_pct / abs(winner_mean_edge_pct)`

Branch verdict:

- Nếu có ≥1 spec promising → `GO_MID_TRADE_HAZARD_FAMILY`
- Nếu không có spec nào promising → `NO_GO_MID_TRADE_HAZARD_FAMILY`

## Deliverables

- `results/mid_trade_hazard_scan.json`
- `results/mid_trade_hazard_scan.md`

## Kết quả thực tế

Branch verdict: **`NO_GO_MID_TRADE_HAZARD_FAMILY`**

| Spec | Coverage % | Median bars saved | Loser mean edge % | Winner mean edge % | Selectivity | Verdict |
|------|------------|-------------------|-------------------|--------------------|-------------|---------|
| `wk_mixed_structure_flag` | 1.61 | 37.0 | 3.2510 | -2.4057 | 1.3514 | NO_GO |
| `wk_flip_count_8w_ge_2` | 2.69 | 10.0 | 4.3713 | 0.7773 | 0.0000 | NO_GO |
| `wk_score_range_8w_ge_2` | 1.61 | 12.0 | 0.0000 | 5.4336 | 0.0000 | NO_GO |

Diễn giải:

- timing có tồn tại, nhưng coverage chỉ `1.6%–2.7%` trades, quá thấp để thành actuator thực dụng;
- `wk_mixed_structure_flag` là spec tốt nhất nhưng vẫn fail coverage và fail selectivity threshold;
- hai spec còn lại cắt winners nhiều hơn hoặc không tạo loser benefit.

Kết luận đúng:

- weekly instability không tạo `force-flat` signal có giá trị kinh tế;
- continuation Class B trong current scope là âm.
