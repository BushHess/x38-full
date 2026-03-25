# f_price_level_state_diagnostic — Price-Level Distance Survey

**Status**: DONE → `NO_GO_F1_PRICE_LEVEL_FAMILY`  
**Nguồn gốc**: [../../program/02_phenomenon_survey.md](../../program/02_phenomenon_survey.md) residual Family F1  
**Runner**: `code/run_f_price_level_state_diagnostic.py`

---

## Mục tiêu

Kiểm tra phần còn lại của Family F1:

> signed distance tới slow anchor có tách baseline trade quality tốt hơn binary
> `above/below EMA` hay không?

Branch này chỉ là **phenomenon survey**:

- không backtest overlay;
- không threshold sweep;
- không combine nhiều anchor sau khi nhìn kết quả.

## Vì sao branch này còn cần thiết

`a_state_diagnostic` đã test F1 ở dạng rất hẹp:

- close above EMA
- EMA cross

Nhưng F1 vẫn còn một phần chưa test:

- **distance to slow anchor**

Nếu sau F2/F3/F4 đều fail, đây là bước nền cuối cùng cần đóng để biết liệu
`x35` còn basic family nào thực sự chưa được khảo sát hay không.

## Frozen Feature Menu

Tất cả feature đều dùng **completed outer bars**.

| Feature | Clock | Định nghĩa | Ý nghĩa |
|---------|-------|------------|---------|
| `wk_dist_to_ema26` | W1 | `close / EMA26(W1) - 1` | signed distance to quarterly slow anchor |
| `wk_dist_to_ema52` | W1 | `close / EMA52(W1) - 1` | signed distance to yearly slow anchor |
| `mo_dist_to_ema6` | M1 | `close / EMA6(M1) - 1` | signed distance to slow monthly anchor |

Không thêm feature khác trong branch này.

## Thiết kế

1. Chạy baseline `E5+EMA21D1`.
2. Tạo W1/M1 completed bars từ D1 bars.
3. Tính 3 signed-distance feature frozen ở trên.
4. Map feature values vào:
   - D1 report calendar để đo persistence;
   - entry timestamps của baseline trades.
5. Với mỗi feature:
   - đo Spearman correlation với trade return;
   - bucketize entries theo quartiles `Q1..Q4`;
   - đo top-vs-bottom separation, concentration, và chronological stability.

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

- Nếu có ≥1 feature promising → `GO_F1_PRICE_LEVEL_FAMILY`
- Nếu không có feature nào promising → `NO_GO_F1_PRICE_LEVEL_FAMILY`

## Deliverables

- `results/price_level_state_scan.json`
- `results/price_level_state_scan.md`

## Kết quả thực tế

Branch verdict: **`NO_GO_F1_PRICE_LEVEL_FAMILY`**

| Feature | Spearman rho | Top-bottom mean delta | Top-bottom win-rate delta | Profit top % | Loss bottom % | Verdict |
|---------|--------------|-----------------------|---------------------------|--------------|---------------|---------|
| `wk_dist_to_ema26` | -0.0299 | 2.20 pp | 4.26 pp | 24.41 | 20.18 | NO_GO |
| `wk_dist_to_ema52` | -0.0198 | 0.27 pp | -2.13 pp | 24.12 | 24.60 | NO_GO |
| `mo_dist_to_ema6` | -0.0742 | 1.98 pp | 1.06 pp | 32.91 | 17.38 | NO_GO |

Diễn giải:

- signed distance tới slow anchor không cho rho dương như hypothesis mong đợi;
- một vài top quartile có mean cao hơn, nhưng effect không đi cùng concentration hay stability;
- do đó phần residual của Family F1 cũng không mở ra candidate entry overlay.
