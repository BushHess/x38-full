# X29: Optimal Stack — Combination of Validated Overlays on E5+EMA1D21

**Status**: SPEC
**Date**: 2026-03-11
**Predecessor**: X22 (cost sensitivity), X14 (churn filter MDD), X18 (churn filter return), prod_readiness (Monitor V2)

---

## 1. Research Question

> Với VTREND E5+EMA1D21 làm base, tổ hợp nào của các overlay đã validated
> (Monitor V2, X14D, X18, trail=4.5) tối ưu Sharpe tại mỗi mức cost thực tế?
> Các overlay có synergy hay interference khi kết hợp?

**Không phải from-scratch discovery.** Đây là factorial optimization trên
các component đã PASS validation gates riêng lẻ.

---

## 2. Inventory of Validated Overlays

### 2.1 Base (always present)

| Component | Parameter | Value | Evidence |
|-----------|-----------|-------|----------|
| EMA crossover entry | slow_period | 120 | p=0.0003 |
| Robust ATR trail + EMA exit (E5) | trail_mult | 3.0 | p=0.0003, Q90-capped |
| VDO filter | vdo_threshold | 0.0 | DOF-corrected p=0.031 |
| D1 EMA regime filter | d1_ema_period | 21 | p=1.5e-5, 16/16 TS |

Standalone: Sharpe 1.432, CAGR 59.96%, MDD 41.57%, 199 trades (50 bps RT).

### 2.2 Factor A: Regime Monitor V2 (entry prevention)

| Property | Value |
|----------|-------|
| Mechanism | Block new entries when rolling MDD exceeds threshold |
| RED gate | 6m MDD > 55% OR 12m MDD > 70% |
| AMBER gate | 6m MDD > 45% OR 12m MDD > 60% |
| Acts at | Entry ONLY (0 forced exits) |
| Cost-sensitive? | NO — always improves regardless of cost |
| Standalone delta | Sharpe +0.158, MDD -5.67pp, blocks 17 entries |
| Code | `monitoring/regime_monitor.py` |
| Validation | 5/6 gates PASS, WFO sparse (guard rarely triggers) |

### 2.3 Factor B: Churn Filter (mutually exclusive options)

X14D và X18 dùng **cùng 7 features, cùng logistic model, suppress cùng trail-stop events**.
Khác nhau ở **threshold**: X14D dùng P(churn)>0.5 cố định; X18 dùng α-percentile (α=40%).
→ **KHÔNG THỂ stack cả hai** — suppression sets overlap lớn, redundant.

#### Option B1: X14D (MDD-focused)

| Property | Value |
|----------|-------|
| Threshold | P(churn) > 0.5 (fixed) |
| 7 features | ema_ratio, atr_pctl, bar_range_atr, close_position, vdo_at_exit, d1_regime_str, trail_tightness |
| Suppressions | ~812 trail-stop bars (5.4%) |
| Delta (50 bps) | Sharpe +0.092, MDD -5.3pp, 133 trades |
| WFO | 75% (3/4) |
| Cost crossover | ~70 bps RT (negative below) |

#### Option B2: X18 (return-focused)

| Property | Value |
|----------|-------|
| Threshold | α-percentile, α=40% (rank-based) |
| 7 features | Same 7 as X14D |
| Suppressions | ~530 trail-stop bars (3.5%) |
| Delta (50 bps) | Sharpe +0.145, CAGR +11.3pp, MDD -0.2pp |
| WFO | 100% (4/4) |
| Cost crossover | ~35 bps RT (negative below) |

### 2.4 Factor C: Trail Multiplier (return/risk tradeoff)

| Property | trail=3.0 (default) | trail=4.5 |
|----------|---------------------|-----------|
| CAGR (bootstrap) | 14/16 baseline | 14/16 PROVEN higher |
| MDD (bootstrap) | baseline | 1/16 PROVEN WORSE |
| Mechanism | Tighter stop, more churn | Wider stop, less churn, deeper DD |
| Cost interaction | More churn = more cost drag | Less churn = less cost drag |

---

## 3. Factorial Design

### 3.1 Factor Space

| Factor | Levels | Values |
|--------|--------|--------|
| A: Monitor V2 | 2 | OFF, ON |
| B: Churn filter | 3 | NONE, X14D, X18 |
| C: Trail mult | 2 | 3.0, 4.5 |

**Total strategy configs**: 2 × 3 × 2 = **12 strategies**

### 3.2 Naming Convention

| ID | A (Monitor) | B (Churn) | C (Trail) | Short Name |
|----|-------------|-----------|-----------|------------|
| S01 | OFF | NONE | 3.0 | Base |
| S02 | OFF | NONE | 4.5 | Base+T45 |
| S03 | OFF | X14D | 3.0 | X14D |
| S04 | OFF | X14D | 4.5 | X14D+T45 |
| S05 | OFF | X18 | 3.0 | X18 |
| S06 | OFF | X18 | 4.5 | X18+T45 |
| S07 | ON | NONE | 3.0 | Mon |
| S08 | ON | NONE | 4.5 | Mon+T45 |
| S09 | ON | X14D | 3.0 | Mon+X14D |
| S10 | ON | X14D | 4.5 | Mon+X14D+T45 |
| S11 | ON | X18 | 3.0 | Mon+X18 |
| S12 | ON | X18 | 4.5 | Mon+X18+T45 |

### 3.3 Cost Sweep

Mỗi strategy chạy tại **9 cost levels**:
- 10, 15, 20, 25, 30, 35, 50, 75, 100 bps RT

**Total backtests**: 12 strategies × 9 costs = **108 runs**

### 3.4 Data

- File: `data/btcusdt_*.csv` (2017-08 to 2026-03, H4+D1)
- Period: 2019-01 to 2026-03 (matching validation window)
- Warmup: 365 days (2017-08 to 2018-08)

---

## 4. Test Plan

### T0: Full-Sample Matrix (108 backtests)

**Output**: `tables/Tbl_full_matrix.csv`

Columns: strategy_id, cost_bps, sharpe, cagr, mdd, calmar, n_trades, exposure,
win_rate, avg_winner, avg_loser, profit_factor, avg_hold, churn_rate, suppressions

**Deliverables**:
1. Heatmap: Sharpe(strategy × cost) — `figures/Fig_sharpe_heatmap.png`
2. Heatmap: MDD(strategy × cost) — `figures/Fig_mdd_heatmap.png`
3. Line plot: Sharpe vs cost per strategy — `figures/Fig_sharpe_vs_cost.png`
4. Pareto frontier: Sharpe vs MDD at each cost — `figures/Fig_pareto.png`

**Gate T0**: Ít nhất 1 combination phải beat S01 (base) tại mỗi cost level.
Nếu FAIL: kết luận overlays không tương thích → STOP.

### T1: Interaction Analysis (factorial decomposition)

**Question**: Hiệu ứng kết hợp có phải additive, hay có synergy/interference?

Đo **interaction term** cho mỗi pair:
```
Interaction(A,B) = Sharpe(A+B) - Sharpe(A) - Sharpe(B) + Sharpe(base)
```

Nếu > 0: synergy (tổ hợp tốt hơn tổng riêng lẻ)
Nếu < 0: interference (tổ hợp kém hơn tổng riêng lẻ)
Nếu ≈ 0: additive (không tương tác)

**Pairs to test** (at each cost level):
1. Monitor × X14D
2. Monitor × X18
3. Monitor × Trail4.5
4. X14D × Trail4.5
5. X18 × Trail4.5
6. Monitor × X14D × Trail4.5 (3-way)
7. Monitor × X18 × Trail4.5 (3-way)

**Output**: `tables/Tbl_interactions.csv`
**Figure**: `figures/Fig_interaction_by_cost.png` (interaction terms vs cost)

**Gate T1**: |interaction| < 0.10 Sharpe cho mỗi pair ở majority cost levels.
Nếu FAIL (strong interference > 0.10): cảnh báo và ghi nhận.

### T2: Walk-Forward Optimization (4-fold, top strategies only)

Chọn **top-6 strategies** từ T0 (3 highest Sharpe + 3 lowest MDD, deduplicated).
Thêm S01 (base) và S07 (Monitor only) làm benchmark.

WFO setup:
- 4 expanding folds (train: 2019-01→{2021-06, 2022-06, 2023-06, 2024-06})
- Test: subsequent 12 months
- Metric: OOS Sharpe vs S01 benchmark

**Output**: `tables/Tbl_wfo_results.csv`
**Figure**: `figures/Fig_wfo_bars.png`

**Gate T2**: Best combination WFO win rate ≥ 50% (2/4 folds) tại realistic cost (25 bps).
Nếu FAIL: kết luận stacking không robust OOS → recommendation = Monitor V2 only.

### T3: Bootstrap Validation (VCBB, top strategies only)

Same top strategies from T2.

Bootstrap setup:
- 500 VCBB paths × 16 timescales (từ `research/lib/vcbb.py`)
- Head-to-head: each candidate vs S01 (base)
- Metrics: P(d_sharpe > 0), P(d_mdd < 0), median delta

**Output**: `tables/Tbl_bootstrap.csv`
**Figure**: `figures/Fig_bootstrap_violin.png`

**Gate T3**: P(d_sharpe > 0) ≥ 55% tại realistic cost cho best combination.

### T4: Cost-Crossover Map (production recommendation)

Từ T0 data, xác định **optimal strategy tại mỗi cost level**:

```
For each cost c in [10, 15, ..., 100]:
    optimal_sharpe[c] = argmax_s Sharpe(s, c)
    optimal_calmar[c] = argmax_s Calmar(s, c)
    optimal_mdd[c] = argmin_s MDD(s, c)  (among strategies with Sharpe > 0.8 × best)
```

**Output**: `tables/Tbl_recommendation_matrix.csv`

| Cost Range | Optimal (Sharpe) | Optimal (MDD) | Recommendation |
|------------|-----------------|---------------|----------------|
| 10-20 bps | ? | ? | ? |
| 20-30 bps | ? | ? | ? |
| 30-50 bps | ? | ? | ? |
| 50-75 bps | ? | ? | ? |
| 75-100 bps | ? | ? | ? |

**Gate T4**: Recommendation table phải consistent với X22 findings:
- Base wins at <30 bps (confirmed or refuted with Monitor V2 in mix)
- Churn filter wins at >35 bps (confirmed or refuted with Monitor V2 in mix)

### T5: Dominance Analysis

Tìm **Pareto-efficient** strategies (no other strategy beats on BOTH Sharpe AND MDD).

**Output**: `tables/Tbl_pareto_efficient.csv`
**Figure**: `figures/Fig_dominance_frontier.png` (Sharpe vs MDD scatter, Pareto front highlighted)

Tại mỗi cost level, ghi nhận:
- Dominated strategies (strictly worse on both metrics)
- Pareto-efficient set
- Trade-off curve

---

## 5. Anti-Self-Deception Checklist

| Risk | Mitigation |
|------|-----------|
| Cherry-picking best cost level | Report ALL 9 cost levels. Primary comparison at 25 bps (realistic). |
| Over-reading interaction terms | Gate at |interaction| < 0.10. Smaller is noise. |
| Confirmation bias toward stacking | S01 (base) included in every comparison. Must beat base at realistic cost. |
| WFO overfitting to fold structure | Use same 4-fold structure as X14/X18/X22 for comparability. |
| Bootstrap flattery | VCBB preserves vol clustering. Report P(d>0), not just median. |
| Ignoring Monitor V2 WFO weakness | Monitor rarely triggers (sparse guard). WFO may be underpowered. |
| Trail=4.5 MDD risk downplayed | Always report MDD alongside Sharpe. Pareto analysis catches this. |

---

## 6. Constraints

| Constraint | Value |
|-----------|-------|
| Asset | BTC spot, BTCUSDT |
| Resolution | H4 primary, D1 context |
| Direction | Long-only |
| Sizing | f=0.30 (vol-target 15%), binary (in/out) |
| Cost range | 10-100 bps RT |
| Primary cost | 25 bps RT (Binance VIP0+BNB realistic) |
| Base strategy | E5+EMA1D21 (frozen, not modified) |
| Churn filter model | Frozen from X14/X18 (no retraining, no feature changes) |
| Monitor thresholds | Frozen from prod_readiness (no threshold tuning) |
| New DOF | 0 (all params frozen from prior studies) |

**Critical**: X29 tunes ZERO parameters. Mọi component đã validated riêng lẻ.
X29 chỉ đo **interaction effects** và xác định **optimal selection** tại mỗi cost regime.

---

## 7. Expected Outcomes

### 7.1 Hypothesis: Monitor V2 Always Helps (cost-invariant)

- Prior evidence: +0.158 Sharpe standalone, cost-invariant mechanism
- Expected: Mon strategies (S07-S12) dominate non-Mon (S01-S06) at ALL cost levels
- If FALSE: interaction with churn filter creates interference → important finding

### 7.2 Hypothesis: Churn Filter Only Helps at High Cost

- Prior evidence (X22): X18 crossover ~35 bps, X14D crossover ~70 bps
- Expected: S01/S07 win at <30 bps; S05/S11 or S03/S09 win at >35 bps
- Key question: does Monitor V2 shift churn filter crossover point?
  (Monitor removes some bad entries → fewer trail stops → less churn → filter less needed?)

### 7.3 Hypothesis: Trail=4.5 Shifts Churn Filter Value

- Prior: Trail=4.5 has less churn (wider stop = fewer premature exits)
- Expected: churn filter delta SMALLER with trail=4.5 (less churn to fix)
- Key question: does trail=4.5 + Monitor V2 dominate trail=3.0 + churn filter?

### 7.4 Hypothesis: Best Stack is Cost-Dependent

- Expected: no single combination dominates at ALL costs
- 10-25 bps: Mon only (S07)
- 25-35 bps: Mon + trail=4.5 (S08) or Mon only (S07)
- 35-50 bps: Mon + X18 (S11) or Mon + X18 + trail=4.5 (S12)
- 50-100 bps: Mon + X14D (S09) or Mon + X14D + trail=4.5 (S10)

---

## 8. Deliverables

### Reports
- `x29_report.md` — Full analysis with all test results, interactions, recommendations

### Tables (CSV)
- `tables/Tbl_full_matrix.csv` — 108 backtests (12 strategies × 9 costs)
- `tables/Tbl_interactions.csv` — Factorial interaction terms
- `tables/Tbl_wfo_results.csv` — WFO results for top strategies
- `tables/Tbl_bootstrap.csv` — Bootstrap P(d>0) and deltas
- `tables/Tbl_recommendation_matrix.csv` — Optimal strategy per cost regime
- `tables/Tbl_pareto_efficient.csv` — Pareto-efficient strategies

### Figures
- `figures/Fig_sharpe_heatmap.png` — Sharpe heatmap (strategy × cost)
- `figures/Fig_mdd_heatmap.png` — MDD heatmap (strategy × cost)
- `figures/Fig_sharpe_vs_cost.png` — Sharpe curves per strategy
- `figures/Fig_pareto.png` — Sharpe vs MDD Pareto frontier
- `figures/Fig_interaction_by_cost.png` — Interaction terms vs cost
- `figures/Fig_wfo_bars.png` — WFO OOS results
- `figures/Fig_bootstrap_violin.png` — Bootstrap distributions
- `figures/Fig_dominance_frontier.png` — Dominance frontier at key costs

### Code
- `code/x29_benchmark.py` — Main script (T0-T5)

### Summary Artifact
- `x29_results.json` — Machine-readable results

---

## 9. Decision Tree

```
T0: Full-sample matrix (108 backtests)
 │
 ├─ Gate T0 FAIL (no combination beats base) → STOP: overlays incompatible
 │
 ├─ Gate T0 PASS
 │   │
 │   T1: Interaction analysis
 │   │
 │   ├─ Strong interference (>0.10) → WARN, document, may still proceed
 │   │
 │   T2: WFO (top strategies, realistic cost)
 │   │
 │   ├─ Gate T2 FAIL (WFO <50%) → RECOMMEND: Monitor V2 only (safest)
 │   │
 │   ├─ Gate T2 PASS
 │   │   │
 │   │   T3: Bootstrap
 │   │   │
 │   │   ├─ Gate T3 FAIL (P(d>0) < 55%) → RECOMMEND: Monitor V2 only
 │   │   │
 │   │   ├─ Gate T3 PASS
 │   │   │   │
 │   │   │   T4: Cost-crossover map → RECOMMENDATION MATRIX
 │   │   │   │
 │   │   │   T5: Dominance analysis → PARETO FRONTIER
 │   │   │   │
 │   │   │   └─ FINALIZE: full recommendation by cost regime
```

---

## 10. Relationship to Prior Studies

| Prior Study | What X29 Uses | What X29 Adds |
|-------------|--------------|--------------|
| X14 | Design D logistic model (frozen) | Tests interaction with Monitor V2 and trail=4.5 |
| X18 | α=40% static mask (frozen) | Tests interaction with Monitor V2 and trail=4.5 |
| X22 | Cost crossover points | Verifies crossovers WITH Monitor V2 in the mix |
| prod_readiness | Monitor V2 thresholds (frozen) | Tests interaction with churn filters |
| trail_sweep | trail=4.5 tradeoff data | Tests trail in combination with overlays |
| X15 | Interaction penalty warning (0.096) | Validates if proven filters have same issue |
| Fragility audit | Step 5 sign-off matrix | Informs risk interpretation |

**X29 does NOT discover new components.** It optimizes selection and combination
of existing validated components across realistic operating conditions.
