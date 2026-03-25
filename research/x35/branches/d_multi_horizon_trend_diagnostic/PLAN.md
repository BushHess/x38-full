# d_multi_horizon_trend_diagnostic — Multi-Horizon Trend State Survey

**Status**: DONE → `NO_GO_F2_TREND_FAMILY`  
**Nguồn gốc**: [../../program/02_phenomenon_survey.md](../../program/02_phenomenon_survey.md) Family F2  
**Runner**: `code/run_d_multi_horizon_trend_diagnostic.py`

---

## Mục tiêu

Kiểm tra xem **cấu trúc trend đa horizon ở weekly timeframe** có thật sự tách được
baseline trade quality của `E5+EMA21D1` hay không.

Branch này chỉ làm **phenomenon survey**:

- không backtest overlay;
- không mở candidate design;
- không thay thế `D1 EMA21`;
- không diễn giải kết quả như verdict cuối của toàn bộ `x35`.

## Vì sao đây là bước cơ bản đúng đắn tiếp theo

Sau khi:

- `a_state_diagnostic` cho thấy các rule kiểu `close > slow EMA` / `EMA cross`
  đơn giản là quá yếu;
- `c_stress_state_diagnostic` cho thấy coarse stress/drawdown không phải hostile
  state hữu ích;

bước nền tảng kế tiếp phải là đo **trend structure**, không phải đo thêm filter
slow-price na ná nhau.

Research question hẹp của branch này:

> Khi weekly trend structure mạnh hơn hoặc đồng thuận hơn trên nhiều horizon,
> quality của baseline E5 entries có tốt hơn một cách có hệ thống không?

## Frozen Feature Menu

Tất cả feature đều được xây từ **completed W1 bars** để bảo đảm causal.

| Feature | Định nghĩa | Ý nghĩa |
|---------|------------|---------|
| `wk_gap_13_26` | `EMA13(W1) / EMA26(W1) - 1` | fast-vs-mid trend coherence |
| `wk_gap_26_52` | `EMA26(W1) / EMA52(W1) - 1` | mid-vs-slow trend coherence |
| `wk_alignment_score_13_26_52` | `1(close > EMA26) + 1(EMA13 > EMA26) + 1(EMA26 > EMA52)` | ordinal weekly structure score from 0 to 3 |

Không thêm feature khác trong branch này.

## Thiết kế

1. Chạy baseline `E5+EMA21D1` trên window chuẩn.
2. Tạo completed W1 bars từ D1 bars có sẵn.
3. Tính 3 feature frozen ở trên.
4. Map feature values vào:
   - D1 report calendar để đo persistence/choppiness;
   - entry timestamps của baseline trades.
5. Với mỗi feature:
   - đo Spearman correlation với trade return;
   - chia entry trades thành ordered buckets:
     - quartiles cho `wk_gap_13_26` và `wk_gap_26_52`;
     - natural buckets `S0..S3` cho `wk_alignment_score_13_26_52`;
   - đo top-vs-bottom separation, profit/loss concentration, và chronological stability.

## Branch GO / NO-GO

Một feature được xem là **promising** nếu thỏa đồng thời:

1. `warmup_ok = True`
2. `flips_per_year <= 18`
3. `median_spell_days >= 14`
4. `n_bottom >= 20` và `n_top >= 20`
5. `rho_spearman > 0`
6. `top_mean_return_pct > 0`
7. `delta_mean_return_pct_top_minus_bottom >= 2.0`
8. `delta_win_rate_pct_top_minus_bottom >= 10.0`
9. `profit_share_top >= 0.35` hoặc `loss_share_bottom >= 0.40`
10. `valid_folds >= 5` và `fold_win_rate >= 0.625`

Branch verdict:

- Nếu có ≥1 feature promising → `GO_F2_TREND_FAMILY`
- Nếu không có feature nào promising → `NO_GO_F2_TREND_FAMILY`

## Deliverables

- `results/multi_horizon_trend_scan.json`
- `results/multi_horizon_trend_scan.md`

## Kết quả thực tế

Branch verdict: **`NO_GO_F2_TREND_FAMILY`**

| Feature | Spearman rho | Top-bottom mean delta | Top-bottom win-rate delta | Profit top % | Loss bottom % | Verdict |
|---------|--------------|-----------------------|---------------------------|--------------|---------------|---------|
| `wk_gap_13_26` | -0.0414 | 1.23 pp | 2.13 pp | 21.88 | 25.20 | NO_GO |
| `wk_gap_26_52` | +0.0355 | 0.46 pp | 8.51 pp | 30.38 | 25.47 | NO_GO |
| `wk_alignment_score_13_26_52` | +0.0016 | 0.69 pp | 3.49 pp | 69.33 | 10.60 | NO_GO |

Diễn giải:

- weekly multi-horizon trend structure này quá yếu để tách baseline trade quality;
- score alignment chủ yếu gom nhiều profit vào bucket `S3`, nhưng không tạo hostile state rõ;
- các gap feature chậm hơn có persistence tốt, nhưng hiệu ứng kinh tế quá nhỏ và không ổn định theo thời gian.
