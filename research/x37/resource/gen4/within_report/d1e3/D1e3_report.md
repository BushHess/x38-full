# D1e3 Report — Bootstrap & Final Ranking

## Bootstrap Check

Bootstrap chạy trên full discovery WFO daily returns đã lưu trong `d1d_wfo_daily_returns.csv`, không re-run backtest.

**Thiết lập:**

- moving block bootstrap
- block sizes: 5, 10, 20
- 3000 resamples mỗi block size
- seed: 20260319
- common block indices dùng chung giữa các candidate

LB5 dùng để kiểm tra hard constraint là 5th percentile của mean daily return ở block size 10.

| Candidate | LB5 block 5 | LB5 block 10 | LB5 block 20 | Bootstrap pass |
|---|---|---|---|---|
| `btcsd_20260318_c1_av4h` | 0.00008639 | 0.00003937 | -0.00004974 | **PASS** |
| `btcsd_20260318_c3_trade4h15m` | 0.00018046 | 0.00016503 | 0.00017942 | **PASS** |

**Kết quả:**

- 2/2 candidate pass điều kiện `bootstrap_lb5_mean_daily_return > 0`
- Không có candidate nào bị loại ở bước này

## Final Ranking

Xếp hạng ở bước này dùng đúng tiêu chí prompt yêu cầu: `adjusted_preference` từ D1e1.
Tie-break không kích hoạt vì adjusted_preference không hòa nhau.

Bảng dưới đây là bản tóm tắt các trường quan trọng nhất ở 50 bps. File CSV lưu đầy đủ thêm cả các trường 20 bps cho discovery / holdout / reserve.

| Rank | Candidate | Config | Adjusted preference | Calmar_50bps | Discovery CAGR | Discovery Sharpe | Discovery MDD | Holdout CAGR | Holdout Sharpe | Holdout MDD | Holdout constraints | Reserve CAGR | Reserve Sharpe | Reserve MDD | Bootstrap LB5 | Layers | Tunables | Ablation review |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `btcsd_20260318_c1_av4h` | cfg_001 | 0.935877 | 1.065877 | 22.9900% | 0.976175 | 21.5691% | 17.3999% | 1.169409 | 6.7520% | FAIL | 12.8182% | 0.655578 | 21.1660% | 0.00003937 | 2 | 3 | True |
| 2 | `btcsd_20260318_c3_trade4h15m` | cfg_025 | 0.889666 | 1.039666 | 39.7348% | 1.010698 | 38.2188% | 33.6548% | 1.075025 | 29.6983% | PASS | -11.5998% | -0.355020 | 43.9382% | 0.00016503 | 3 | 3 | True |

**Điểm cần đọc cho đúng:**

- **c1_av4h** đứng hạng 1 vì adjusted_preference cao hơn, dù holdout không đạt hard constraints và bootstrap LB5 thấp hơn c3
- **c3_trade4h15m** đứng hạng 2 vì adjusted_preference thấp hơn, dù:
  - holdout 50 bps pass
  - bootstrap LB5 mạnh hơn rõ rệt
- Cả hai vẫn còn `ablation_review_flag = True`, nên D1f vẫn phải xử lý phần governance/selection cẩn thận, không được nhảy cóc

## Files Saved

- `d1e_final_ranking.csv`
- `d1e3_summary.md`

---

**Sẵn cho D1f.**
