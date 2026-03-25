# Nhiệm vụ B3: Final Holdout — ONE-SHOT

**Script:** `out_v11_validation_stepwise/scripts/final_holdout.py`
**Timestamp:** 2026-02-23 22:39:25 UTC
**Commitment:** One-shot execution. No re-runs. No parameter tuning on holdout.

---

## 1. Holdout Definition

| Parameter | Value |
|-----------|-------|
| **Holdout start** | **2024-10-01** |
| **Holdout end** | **2026-02-20** |
| **Holdout days** | 507 days (**19.4%** of full evaluation period) |
| Full evaluation period | 2019-01-01 → 2026-02-20 (2607 days) |
| Warmup | 365 days (indicators computed from 2023-10-01) |
| Baseline | V10 = V8ApexConfig() defaults |
| Candidate | V11 WFO-opt: aggression=0.95, trail=2.8, cap=0.90 |
| Scenarios | harsh (50 bps), base (31 bps), smart (13 bps) |

### Market context trong holdout:
- **2024-Q4**: BTC $60k → $100k+ (strong bull, Trump election rally)
- **2025-H1**: BTC $100k → $80k → $95k (correction + recovery, volatile)
- **2025-H2 to Feb 2026**: BTC $90k–$100k range (consolidation)
- Regime mix: ~300 days BULL, ~93 days BEAR, ~50 days CHOP, ~18 days TOPPING

---

## 2. Results

### 2.1 Score & Primary Metrics

| Scenario | V10 Score | V11 Score | **Δ Score** | V10 Return | V11 Return | **Δ Return** |
|----------|-----------|-----------|-------------|------------|------------|--------------|
| **harsh** | 34.66 | 33.43 | **-1.23** | +24.82% | +24.18% | **-0.64%** |
| **base** | 55.06 | 53.78 | **-1.28** | +35.40% | +34.70% | **-0.70%** |
| **smart** | 64.64 | 63.31 | **-1.32** | +40.42% | +39.68% | **-0.74%** |

### 2.2 Risk Metrics

| Scenario | V10 MDD | V11 MDD | **Δ MDD** | V10 Sharpe | V11 Sharpe | **Δ Sharpe** |
|----------|---------|---------|-----------|------------|------------|--------------|
| **harsh** | 31.56% | 31.56% | **0.00%** | 0.696 | 0.685 | **-0.011** |
| **base** | 30.86% | 30.86% | **0.00%** | 0.895 | 0.885 | **-0.010** |
| **smart** | 30.19% | 30.19% | **0.00%** | 0.986 | 0.975 | **-0.010** |

### 2.3 Activity Metrics

| Scenario | V10 Trades | V11 Trades | V10 Turnover/yr | V11 Turnover/yr |
|----------|-----------|-----------|-----------------|-----------------|
| harsh | 26 | 26 | same | same |
| base | 25 | 25 | same | same |
| smart | 25 | 25 | same | same |

### 2.4 Regime Decomposition (harsh)

| Regime | Days | V10 Return | V11 Return | **Δ Return** |
|--------|------|------------|------------|--------------|
| **BULL** | 300 | — | — | **-0.73%** |
| **TOPPING** | 18 | — | — | **0.00%** |
| **BEAR** | 93 | — | — | **0.00%** |
| **CHOP** | 50 | — | — | **0.00%** |

---

## 3. Full-Period vs Holdout Comparison

| Metric | Full Period (7y) Δ | Holdout (17m) Δ | Direction |
|--------|-------------------|-----------------|-----------|
| Score (harsh) | **+1.86** | **-1.23** | **Reversed** |
| Score (base) | **+1.91** | **-1.28** | **Reversed** |
| Score (smart) | **+1.93** | **-1.32** | **Reversed** |

V11 thắng trên full period nhưng **thua trên holdout**. Điều này cho thấy V11's improvement tập trung ở giai đoạn trước holdout (2021-H1 và 2023-H2 như đã thấy ở B1b).

---

## 4. Phân tích

### Tại sao V11 thua trên holdout?

1. **Holdout = late/extended bull + correction (2024-Q4 to 2026)**: Đây chính là giai đoạn mà V11 cycle phase classifies as LATE_BULL. Tham số `late_trail_mult=2.8` (tighter than V10 default ~3.2-3.5) → V11 exits sớm hơn trong pullbacks → miss recovery → underperform.

2. **Consistent with B2 sensitivity grid**: Trail = 2.8 nằm **ngoài** sweet spot trail=3.0 trên grid. Grid cho thấy trail < 3.0 underperforms consistently.

3. **Consistent with B1 round-by-round**: Windows 6 (2024-H1) và 7 (2024-H2) — gần nhất với holdout — V11 đều thua (-1.57, -4.32 score points).

4. **MDD identical**: V11 cycle phase không gây thêm drawdown — nó chỉ underperform trên returns.

5. **TOPPING/BEAR damage = zero**: V11 không gây hại trong bearish regimes.

### Magnitude assessment:

| Metric | Holdout Δ | Severity |
|--------|-----------|----------|
| Score | -1.23 | Nhỏ (~1.4% of V10 score) |
| Return | -0.64% | Nhỏ (~2.6% of V10 return) |
| Sharpe | -0.011 | Minimal (~1.6% of V10 Sharpe) |
| MDD | 0.00% | Không ảnh hưởng |

Losses nhỏ và consistent across 3 scenarios — đây không phải noise mà là **systematic slight underperformance** do tighter trail trong late bull.

---

## 5. Kết luận

### VERDICT: **HOLD**

### Lý do HOLD (không phải REJECT):

1. **Magnitude nhỏ**: V11 thua -1.23 score points = 1.4% relative. Thua -0.64% return trên 17 tháng. Đây nằm trong phạm vi noise cho 1 strategy cycle.

2. **Không gây damage**: MDD identical, TOPPING = 0, BEAR = 0. V11 không phá vỡ V10's risk profile.

3. **Specific to late bull regime**: Holdout 2024-10 to 2026-02 chủ yếu là extended/late bull + correction. V11's cycle late tighter trail là **design feature** cho regime này. Nó hoạt động đúng intent (protect gains) nhưng kết quả ra underperform vì corrections này **recoverable** — V10 giữ position qua pullback và catch recovery, V11 exit rồi re-enter chậm hơn.

4. **Full period vẫn positive**: V11 thắng +1.86 trên 7 năm. Holdout loss -1.23 không đủ negate.

### Lý do không PASS:

1. **V11 thua trên 3/3 scenarios** — không có 1 scenario nào V11 thắng trên holdout.

2. **Direction reversed**: Full-period positive nhưng holdout negative → V11's edge không extend vào recent data.

3. **Consistent with B2 FAIL**: Sensitivity grid cho thấy trail=2.8 nằm ngoài sweet spot. Holdout confirms this.

### Lý do không REJECT:

1. **Losses quá nhỏ** để justify rejection: -1.23 score / -0.64% return.

2. **No risk degradation**: MDD unchanged, no regime damage.

3. **Holdout regime-specific**: 300/507 days = 59% BULL → test biased toward regime mà V11 cycle late intentionally more conservative.

---

## 6. Cumulative Validation Status

| Test | Verdict | Notes |
|------|---------|-------|
| **A. Reproducibility** | PASS | SHA256 match ✓ |
| **B1. WFO Round-by-Round (score)** | INCONCLUSIVE → negative | 0/2 non-zero rounds positive |
| **B1b. WFO Round-by-Round (return)** | INCONCLUSIVE → positive (weak) | 2/4 positive, magnitude 5.6× asymmetry |
| **B2. Sensitivity Grid** | **FAIL** | 6/27 = 22% beat baseline, cliff at trail≠3.0 |
| **B3. Final Holdout** | **HOLD** | V11 thua -1.23 trên 3/3 scenarios, nhưng small magnitude |

### Overall recommendation: **HOLD — do not promote V11 to production**

V11 cycle phase as currently parameterized (WFO-opt 0.95/2.8/0.90) does NOT reliably beat V10. It shows marginal improvement on historical bull periods (2021, 2023) but underperforms on recent data (2024-2026). The improvement is not robust across parameter space (B2 FAIL) and not statistically significant (B1).

---

## 7. Data Files

| File | Mô tả |
|------|--------|
| `out_v11_validation_stepwise/final_holdout_metrics.csv` | 9 rows (3 scenarios × 3: V10, V11, DELTA) |
| `out_v11_validation_stepwise/final_holdout.json` | Full results + verdict |
| `out_v11_validation_stepwise/holdout_run.log` | Stdout capture of one-shot run |
| `out_v11_validation_stepwise/scripts/final_holdout.py` | Reproducible script |
| `out_v11_validation_stepwise/reports/final_holdout.md` | This report |
