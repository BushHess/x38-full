# c_stress_state_diagnostic — Stress / Drawdown State Survey

**Status**: DONE → `NO_GO_STRESS_FAMILY`  
**Nguồn gốc**: [../../program/02_phenomenon_survey.md](../../program/02_phenomenon_survey.md) Family F3  
**Runner**: `code/run_c_stress_state_diagnostic.py`

---

## Mục tiêu

Kiểm tra xem **stress state** ở horizon nhiều tuần có làm baseline `E5+EMA21D1`
xấu đi rõ rệt hay không.

Branch này vẫn là **phenomenon survey**, không phải candidate overlay validation.

## Vì sao đây là bước tiếp theo đúng hơn

Sau khi `a_state_diagnostic` fail trên menu close-vs-EMA / EMA-cross, bước hợp lý
không phải thử thêm slow price filter na ná nhau, mà là chuyển sang một family
orthogonal hơn:

- **stress / drawdown state**

Nếu outer overlay thực sự có giá trị, rất có thể nó đến từ việc nhận diện
**hostile environments** hơn là “bull state” kiểu price-above-EMA đơn giản.

## Frozen Feature Menu

Tất cả feature được định nghĩa sao cho **giá trị cao hơn = stress hơn**.

| Feature | Định nghĩa | Ý nghĩa |
|---------|------------|---------|
| `dd63_depth` | `1 - close / rolling_max_63d` | drawdown depth ~ 3 tháng |
| `dd126_depth` | `1 - close / rolling_max_126d` | drawdown depth ~ 6 tháng |
| `vol_shock_30_180` | `rv_30d / rv_180d` | short-vol shock vs background |

Không thêm feature khác trong branch này.

## Thiết kế

1. Chạy baseline `E5+EMA21D1` trên window chuẩn.
2. Map feature values của D1 stress state vào entry timestamps của baseline trades.
3. Với mỗi feature:
   - đo Spearman rank correlation với trade return;
   - chia baseline trades thành 4 quantile theo mức stress;
   - đo mean return, median return, win rate, profit/loss concentration theo quantile.

## Branch GO / NO-GO

Một feature được xem là **promising** nếu thỏa đồng thời:

1. `rho_spearman < 0`
2. mean return ở `Q1` (stress thấp nhất) > 0
3. mean return ở `Q4` (stress cao nhất) < 0
4. `delta_mean_return = mean(Q1) - mean(Q4) >= 2.0 pp`
5. `loss_share_q4 >= 0.40`

Branch verdict:

- Nếu có ≥1 feature promising → `GO_STRESS_FAMILY`
- Nếu không có feature nào promising → `NO_GO_STRESS_FAMILY`

## Kết quả thực tế

Branch verdict: **`NO_GO_STRESS_FAMILY`**

| Feature | Spearman rho | Q1-Q4 mean delta | Q4 loss share | Verdict |
|---------|--------------|------------------|---------------|---------|
| `dd63_depth` | +0.0147 | -1.20 pp | 18.48% | NO_GO |
| `dd126_depth` | +0.0085 | -2.16 pp | 22.96% | NO_GO |
| `vol_shock_30_180` | -0.0349 | -1.50 pp | 30.47% | NO_GO |

Diễn giải:

- drawdown depth không cho quan hệ monotonic kiểu “càng stress càng tệ”;
- loss không tập trung đủ vào quartile stress cao;
- vol shock không đóng vai hostile-state theo cách branch hypothesis mong đợi.

## Deliverables

- `results/stress_state_scan.json`
- `results/stress_state_scan.md`
