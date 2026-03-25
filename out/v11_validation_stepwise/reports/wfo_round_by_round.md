# Nhiệm vụ B1: WFO Round-by-Round Robustness

**Script:** `out_v11_validation_stepwise/scripts/wfo_round_by_round.py`
**Scenario:** harsh (50 bps round-trip)
**Baseline:** V10 = V8ApexConfig() defaults
**Candidate:** V11 WFO-opt = cycle_late_aggression=0.95, cycle_late_trail_mult=2.8, cycle_late_max_exposure=0.90

---

## 1. Per-Round Results

### 1.1 Score & Return Summary

| Window | OOS Period | V10 Score | V11 Score | Δ Score | V10 Ret% | V11 Ret% | Δ Ret% |
|--------|-----------|-----------|-----------|---------|----------|----------|--------|
| 0 | 2021-H1 | -1,000,000 | -1,000,000 | 0.00 | +41.25 | +43.36 | **+2.11** |
| 1 | 2021-H2 | -9.63 | -9.63 | 0.00 | +0.12 | +0.12 | 0.00 |
| 2 | 2022-H1 | -1,000,000 | -1,000,000 | 0.00 | 0.00 | 0.00 | 0.00 |
| 3 | 2022-H2 | -1,000,000 | -1,000,000 | 0.00 | 0.00 | 0.00 | 0.00 |
| 4 | 2023-H1 | -1,000,000 | -1,000,000 | 0.00 | -3.04 | -3.04 | 0.00 |
| 5 | 2023-H2 | -1,000,000 | -1,000,000 | 0.00 | +24.11 | +27.00 | **+2.89** |
| 6 | 2024-H1 | **171.13** | **169.56** | **-1.57** | +28.78 | +28.53 | -0.25 |
| 7 | 2024-H2 | **158.58** | **154.26** | **-4.32** | +25.98 | +25.34 | -0.64 |
| 8 | 2025-H1 | -72.59 | -72.59 | 0.00 | -11.55 | -11.55 | 0.00 |
| 9 | 2025-H2 | -24.22 | -24.22 | 0.00 | -3.26 | -3.26 | 0.00 |

### 1.2 Regime Decomposition (BULL / TOPPING)

| Window | OOS Period | Δ BULL Ret% | Δ TOPPING Ret% | Δ MDD% |
|--------|-----------|-------------|----------------|--------|
| 0 | 2021-H1 | **+2.32** | 0.00 | -0.87 (better) |
| 1 | 2021-H2 | 0.00 | 0.00 | 0.00 |
| 2 | 2022-H1 | 0.00 | 0.00 | 0.00 |
| 3 | 2022-H2 | 0.00 | 0.00 | 0.00 |
| 4 | 2023-H1 | 0.00 | 0.00 | 0.00 |
| 5 | 2023-H2 | **+2.51** | 0.00 | 0.00 |
| 6 | 2024-H1 | -0.22 | 0.00 | 0.00 |
| 7 | 2024-H2 | -0.58 | 0.00 | 0.00 |
| 8 | 2025-H1 | 0.00 | 0.00 | 0.00 |
| 9 | 2025-H2 | 0.00 | 0.00 | 0.00 |

---

## 2. Thống kê tổng hợp

| Metric | Value |
|--------|-------|
| Tổng windows | 10 |
| Δ score > 0 | **0** |
| Δ score = 0 | 8 |
| Δ score < 0 | **2** |
| Median Δ score | 0.0000 |
| Mean Δ score | **-0.5893** |
| Worst Δ score | **-4.3222** (window 7: 2024-H2) |
| Best Δ score | 0.0000 |
| Sign test p-value | **1.0000** (effective n = 2, ties excluded) |

### Robustness Criteria

| Criterion | Threshold | Actual | PASS/FAIL |
|-----------|-----------|--------|-----------|
| Positive rate (non-zero rounds) | ≥ 60% | **0/2 = 0%** | **FAIL** |
| Worst round Δ score | > -5.0 | -4.32 | PASS (marginal) |

---

## 3. Phân tích: Tại sao 8/10 rounds có delta = 0?

### Nguyên nhân gốc: Score rejection threshold

Objective function (`v10/research/objective.py:21`):
```python
if n_trades < 10:
    return -1_000_000.0
```

Trong OOS windows 6 tháng, hầu hết periods có **< 10 trades** → cả V10 và V11 đều nhận score = -1,000,000 → delta = 0 cho dù return_pct khác nhau.

### Windows bị mask bởi -1M:

- **Window 0** (2021-H1): 8 trades, score = -1M. Nhưng V11 return **cao hơn 2.11%** so với V10.
- **Window 5** (2023-H2): 6 trades, score = -1M. Nhưng V11 return **cao hơn 2.89%** so với V10.

→ V11's cycle phase **có tác dụng** ở 2 windows này (BULL regime), nhưng score metric **không ghi nhận** do rejection threshold.

### 2 windows có score thực (trades ≥ 10):

- **Window 6** (2024-H1): V11 score = 169.56, V10 = 171.13 → **V11 thua 1.57 điểm**
- **Window 7** (2024-H2): V11 score = 154.26, V10 = 158.58 → **V11 thua 4.32 điểm**

Cả 2 windows này V11 đều **thua** V10. Nguyên nhân: V11 cycle phase thay đổi trail mult, nhưng trong giai đoạn 2024 (extended bull → correction), trail adjustment **gây ra exits sớm hơn**, làm miss recovery.

---

## 4. Dual-metric view: Score vs Return

| Metric | V11 wins | V11 ties | V11 loses | Verdict |
|--------|----------|----------|-----------|---------|
| **Harsh score** | 0 | 8 | **2** | V11 thua |
| **Total return** | 2 (+2.1%, +2.9%) | 6 | 2 (-0.3%, -0.6%) | Mixed |
| **BULL return** | 2 (+2.3%, +2.5%) | 6 | 2 (-0.2%, -0.6%) | Mixed |
| **TOPPING return** | 0 | 10 | 0 | Identical |
| **MDD** | 1 (-0.87%) | 9 | 0 | Neutral |

Return_pct cho thấy bức tranh khác: V11 **thắng 2 windows** trên return (magnitude lớn hơn: +2.1%, +2.9%) nhưng **thua 2 windows** (magnitude nhỏ hơn: -0.3%, -0.6%). Tuy nhiên, score metric — bao gồm Sharpe, PF, MDD penalty — cho kết quả nghiêm ngặt hơn.

---

## 5. Kết luận

### Verdict: **INCONCLUSIVE → leaning NEGATIVE**

**Lý do:**

1. **Sign test không có power**: 8/10 ties, effective n = 2, p = 1.0. Không thể kết luận gì từ sign test.

2. **Trong 2 rounds có score thực, V11 thua cả 2**: Đây là bằng chứng tiêu cực mạnh nhất. V11 không cải thiện score ở bất kỳ window nào có đủ trades để đo lường.

3. **V11 cải thiện return ở 2 windows khác** (+2.1%, +2.9%), nhưng những windows này không đạt ngưỡng 10 trades để tính score → không thể so sánh chất lượng risk-adjusted.

4. **Score metric limitation**: Objective score phù hợp cho full-period (4+ năm, 100+ trades) nhưng **không phù hợp cho per-window 6 tháng** do rejection threshold. Điều này có nghĩa round-by-round test bằng score metric **structurally biased** — nó chỉ đánh giá được periods có nhiều trades (thường là volatile/active markets), bỏ qua quiet periods.

### Implications cho V11:

- V11's cycle phase **chỉ hoạt động trong BULL regime** → majority of windows không có delta
- Khi V11 hoạt động (windows 6, 7 — có đủ trades), nó **làm xấu hơn**, không cải thiện
- Return improvement ở windows 0, 5 là **real** nhưng **nhỏ** (+2-3%) và **không risk-adjusted**

### Recommendation:

Cần thêm Nhiệm vụ B2 hoặc C với **return-based metric** (e.g., total_return_pct, Sharpe trên return) thay vì objective score để có kết luận đầy đủ. Score metric làm mất 80% thông tin do rejection threshold.

---

## Data Files

- `out_v11_validation_stepwise/per_round_metrics.csv` — Full per-round data (30 rows)
- `out_v11_validation_stepwise/sign_test.json` — Sign test statistics
- `out_v11_validation_stepwise/scripts/wfo_round_by_round.py` — Reproducible script
