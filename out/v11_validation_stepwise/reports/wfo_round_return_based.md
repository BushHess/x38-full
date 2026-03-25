# Nhiệm vụ B1b: WFO Round-by-Round — Return-Based Metrics

**Script:** `out_v11_validation_stepwise/scripts/wfo_round_return_based.py`
**Scenario:** harsh (50 bps round-trip)
**Baseline:** V10 = V8ApexConfig() defaults
**Candidate:** V11 WFO-opt = cycle_late_aggression=0.95, cycle_late_trail_mult=2.8, cycle_late_max_exposure=0.90

**Motivation:** B1 (score-based) cho kết quả INCONCLUSIVE vì `compute_objective()` trả về -1M khi trades < 10, mask 80% windows. Bài này thay thế bằng 4 return-based metrics không có rejection threshold.

---

## 1. Metric Definitions

| Metric | Mô tả | Tại sao dùng |
|--------|--------|---------------|
| **total_return_pct** | Return thô trên 6-month window | Không rejection, so sánh trực tiếp |
| **score_no_reject** | Cùng formula `2.5*cagr - 0.6*mdd + 8*sharpe + 5*PF + 5*trades_ramp` nhưng **bỏ guard `if trades < 10: return -1M`** | Risk-adjusted, không bị mask |
| **sharpe** | Annualized Sharpe ratio | Risk-adjusted per unit of volatility |
| **mdd_pct** | Max drawdown (%) | Risk metric (Δ < 0 = V11 tốt hơn) |

---

## 2. Per-Round Results

### 2.1 Score No-Reject & Return

| Window | OOS Period | V10 score_nr | V11 score_nr | **Δ score_nr** | V10 ret% | V11 ret% | **Δ ret%** |
|--------|-----------|-------------|-------------|----------------|----------|----------|-----------|
| 0 | 2021-H1 | +265.35 | +281.88 | **+16.53** | +41.25 | +43.36 | **+2.11** |
| 1 | 2021-H2 | -9.63 | -9.63 | 0.00 | +0.12 | +0.12 | 0.00 |
| 2 | 2022-H1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 3 | 2022-H2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 4 | 2023-H1 | -23.46 | -23.46 | 0.00 | -3.04 | -3.04 | 0.00 |
| 5 | 2023-H2 | +148.29 | +167.61 | **+19.33** | +24.11 | +27.00 | **+2.89** |
| 6 | 2024-H1 | +171.13 | +169.56 | **-1.57** | +28.78 | +28.53 | **-0.25** |
| 7 | 2024-H2 | +158.58 | +154.26 | **-4.32** | +25.98 | +25.34 | **-0.64** |
| 8 | 2025-H1 | -72.59 | -72.59 | 0.00 | -11.55 | -11.55 | 0.00 |
| 9 | 2025-H2 | -24.22 | -24.22 | 0.00 | -3.26 | -3.26 | 0.00 |

### 2.2 Sharpe & MDD

| Window | OOS Period | V10 Sharpe | V11 Sharpe | **Δ Sharpe** | V10 MDD% | V11 MDD% | **Δ MDD%** |
|--------|-----------|-----------|-----------|-------------|----------|----------|-----------|
| 0 | 2021-H1 | 1.872 | 1.982 | **+0.110** | 17.83 | 16.96 | **-0.87** |
| 1 | 2021-H2 | 0.192 | 0.192 | 0.000 | 21.76 | 21.76 | 0.00 |
| 2 | 2022-H1 | 0.000 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 |
| 3 | 2022-H2 | 0.000 | 0.000 | 0.000 | 0.00 | 0.00 | 0.00 |
| 4 | 2023-H1 | -0.209 | -0.209 | 0.000 | 14.73 | 14.73 | 0.00 |
| 5 | 2023-H2 | 1.702 | 1.886 | **+0.185** | 15.04 | 15.04 | 0.00 |
| 6 | 2024-H1 | 1.604 | 1.608 | **+0.005** | 19.14 | 19.14 | 0.00 |
| 7 | 2024-H2 | 1.530 | 1.510 | **-0.020** | 15.39 | 15.39 | 0.00 |
| 8 | 2025-H1 | -0.607 | -0.607 | 0.000 | 31.56 | 31.56 | 0.00 |
| 9 | 2025-H2 | -0.186 | -0.186 | 0.000 | 15.57 | 15.57 | 0.00 |

### 2.3 Regime Decomposition

| Window | OOS Period | Δ BULL ret% | Δ TOPPING ret% | Ghi chú |
|--------|-----------|-------------|----------------|---------|
| 0 | 2021-H1 | **+2.32** | 0.00 | V11 cycle → aggressive hơn trong early bull |
| 5 | 2023-H2 | **+2.51** | 0.00 | V11 cycle → wider trail, capture more bull |
| 6 | 2024-H1 | -0.22 | 0.00 | V11 trail adjustment → miss nhẹ |
| 7 | 2024-H2 | -0.58 | 0.00 | V11 trail adjustment → miss nhẹ |
| Others | — | 0.00 | 0.00 | V11 cycle inactive (BEAR/CHOP) |

---

## 3. Statistical Tests

### 3.1 Sign Test (exact binomial, one-sided, H0: P(Δ>0) = 0.5, ties excluded)

| Metric | n_eff | Positive | Negative | p-value | Verdict |
|--------|-------|----------|----------|---------|---------|
| **total_return_pct** | 4 | 2 | 2 | **0.6875** | Not significant |
| **score_no_reject** | 4 | 2 | 2 | **0.6875** | Not significant |
| **sharpe** | 4 | 3 | 1 | **0.3125** | Not significant |
| **mdd_pct** | 1 | 0 (V11 lower) → 1 good | 0 bad | **1.0000** | n too small |

### 3.2 Wilcoxon Signed-Rank Test (normal approx, one-sided)

| Metric | n_eff | W+ | W- | p-value | Verdict |
|--------|-------|----|----|---------|---------|
| **total_return_pct** | 4 | 7.0 | 3.0 | **0.2326** | Not significant |
| **score_no_reject** | 4 | 7.0 | 3.0 | **0.2326** | Not significant |
| **sharpe** | 4 | 8.0 | 2.0 | **0.1367** | Not significant |
| **mdd_pct** | 1 | — | — | — | n too small |

### 3.3 Magnitude Analysis (V11 wins are bigger than V11 losses?)

| Metric | Σ positive Δ | Σ negative Δ | **Net Δ** | Mean Δ | Ratio |
|--------|-------------|-------------|-----------|--------|-------|
| **total_return_pct** | +5.00% | -0.89% | **+4.11%** | +0.41%/window | 5.6× |
| **score_no_reject** | +35.85 | -5.89 | **+29.96** | +3.00/window | 6.1× |
| **sharpe** | +0.299 | -0.020 | **+0.279** | +0.028/window | 15.0× |
| **mdd_pct** | 0.00 | -0.87 | **-0.87** | -0.09%/window | V11 tốt hơn |

---

## 4. So sánh B1 (score-based) vs B1b (return-based)

| Aspect | B1 (harsh_score) | B1b (return-based) |
|--------|-------------------|--------------------|
| Metric chính | compute_objective (reject < 10 trades) | score_no_reject, return_pct, sharpe, mdd |
| Windows có delta ≠ 0 | 2/10 | 4/10 |
| V11 thắng | 0 | 2 (score_nr, return), 3 (sharpe) |
| V11 thua | 2 | 2 (score_nr, return), 1 (sharpe) |
| Sign test p | 1.0 | 0.31–0.69 |
| Magnitude asymmetry | N/A (all losses) | **V11 wins 5.6–15× lớn hơn losses** |
| Verdict | INCONCLUSIVE → leaning NEGATIVE | INCONCLUSIVE → leaning POSITIVE |

**Key insight:** Khi bỏ rejection threshold, **bức tranh đảo chiều**. V11 thắng lớn (+16.5, +19.3 score points) ở 2 windows, thua nhỏ (-1.6, -4.3) ở 2 windows khác. Net delta **rõ ràng dương** trên mọi metric.

---

## 5. Phân tích 4 windows có delta ≠ 0

### Windows V11 thắng:

| Window | Period | Regime | Δ ret% | Δ score_nr | Cơ chế V11 |
|--------|--------|--------|--------|------------|-------------|
| **0** | 2021-H1 | Strong BULL (BTC $29k → $65k) | +2.11 | +16.53 | Cycle phase → early_aggression=1.0, trail_mult=3.5 → wider trail captures more upside |
| **5** | 2023-H2 | Moderate BULL (BTC $27k → $43k) | +2.89 | +19.33 | Cycle phase → aggressive re-entry + wider trail in early bull |

### Windows V11 thua:

| Window | Period | Regime | Δ ret% | Δ score_nr | Cơ chế V11 |
|--------|--------|--------|--------|------------|-------------|
| **6** | 2024-H1 | Extended BULL (BTC $44k → $63k) | -0.25 | -1.57 | Cycle → late_aggression=0.95, late_trail=2.8 → tighter trail gây exit sớm nhẹ |
| **7** | 2024-H2 | BULL → correction (BTC $63k → $93k) | -0.64 | -4.32 | Cycle → late detection → tighter trail → miss part of recovery |

### Pattern:
- V11 **thắng ở early/moderate bull** (windows 0, 5): wider trail captures more upside
- V11 **thua ở late/extended bull** (windows 6, 7): tighter trail exits too early
- **Magnitude asymmetry**: wins (+2.1%, +2.9%) > losses (-0.25%, -0.64%) vì early bull moves lớn hơn late-stage slippage
- **TOPPING regime**: Δ = 0 ở tất cả windows → V11 **không gây hại** trong downturns

---

## 6. Kết luận

### Verdict: **INCONCLUSIVE — leaning POSITIVE (weak)**

### Lý do INCONCLUSIVE:

1. **Statistical power quá thấp**: n_eff = 4 (6/10 windows = ties). Sign test p = 0.31–0.69, Wilcoxon p = 0.14–0.23. Không metric nào đạt p < 0.05. Với n_eff = 4, ngay cả 4/4 positive chỉ cho p = 0.0625 — **structurally impossible** để đạt p < 0.05 với 10 windows và 60% ties.

2. **V11 cycle phase là conditional feature**: Chỉ fire khi price > EMA200 (bull regime). Trong 60% windows (bear, chop, sideways), V11 = V10 exactly. Đây không phải bug — đây là design. Nhưng nó khiến per-window statistical test **không thể đạt significance** trừ khi backtest period dài hơn (nhiều windows hơn).

### Lý do leaning POSITIVE:

1. **Magnitude asymmetry mạnh**: V11 wins 5.6× lớn hơn losses trên return, 6.1× trên score. Net Δ return = +4.11% trên 10 windows, net Δ score = +29.96.

2. **Sharpe ratio best metric**: 3/4 positive, 1/4 negative. Đây là metric risk-adjusted duy nhất không bị ties dominate. Wilcoxon p = 0.14 — lowest among all metrics (nhưng vẫn > 0.05).

3. **MDD**: V11 không bao giờ tăng drawdown (Δ MDD ≤ 0 ở mọi window). Worst case = identical.

4. **No TOPPING damage**: Δ TOPPING = 0.00 ở tất cả 10 windows. V11 cycle phase **không gây hại trong bear/correction**.

5. **Cơ chế hợp lý**: V11 thắng ở early bull (wider trail) và thua ở late bull (tighter trail). Asymmetry thuận lợi vì early bull moves typically có magnitude lớn hơn.

### Limitations:

- **n_eff = 4 quá nhỏ** cho bất kỳ test thống kê nào. Cần ít nhất n_eff ≥ 8–10 (tức ~20 windows) để có power.
- **6-month windows** khiến nhiều periods có 0 trades (V10 cũng vậy) → ties unavoidable.
- **Magnitude analysis không phải hypothesis test** — nó chỉ ra pattern nhưng không chứng minh significance.

### Recommendation:

V11's return-based evidence **tích cực nhưng chưa đạt ngưỡng thống kê**. Combined với B1:
- B1 (score): 0 wins, 2 losses → negative
- B1b (returns): 2 wins (lớn), 2 losses (nhỏ), asymmetry 5.6× → positive
- **Reconciliation**: Score metric bị mask bởi rejection. Return metrics cho bức tranh đầy đủ hơn. Nhưng cả hai đều INCONCLUSIVE.

**Để có kết luận rõ ràng**, cần một trong hai:
1. **Longer OOS** — dùng 12-month windows thay vì 6-month để tăng trade count và giảm ties
2. **Full-period bootstrap** — so sánh trên toàn bộ 2019–2026 (đã làm: P = 91.7%, chưa đạt 95%)

---

## 7. Data Files

| File | Mô tả |
|------|--------|
| `out_v11_validation_stepwise/per_round_return_metrics.csv` | 30 rows (10 windows × 3: V10, V11, DELTA) |
| `out_v11_validation_stepwise/sign_test_returns.json` | Multi-metric stats + robustness verdicts |
| `out_v11_validation_stepwise/scripts/wfo_round_return_based.py` | Reproducible script |
| `out_v11_validation_stepwise/reports/wfo_round_return_based.md` | This report |
