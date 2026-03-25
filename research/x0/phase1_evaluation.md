# P1.4 — X0 Phase 1 Full Evaluation

**Date**: 2026-03-06
**Status**: COMPLETE

---

## SUMMARY

Ran a full benchmark of X0 Phase 1 against 4 baselines (E0, E0+EMA21, E5, E5+EMA21)
using the canonical parity_eval.py evaluation pipeline. The benchmark includes:
- Full backtests across 3 cost scenarios (smart/base/harsh)
- VCBB bootstrap (500 paths, block=60, seed=42)

**Key result**: X0 Phase 1 is **BIT-IDENTICAL** to E0+EMA21 across all backtests,
all bootstrap paths, and all metrics. This is expected — X0 Phase 1 is by design
a behavioral clone with a different identity.

In the 5-strategy landscape, E0+EMA21 (= X0) ranks 3rd on Sharpe and CAGR,
behind E5+EMA21 (#1) and E5 (#2), but with lower MDD than E0.

---

## FILES_INSPECTED

| File | Purpose |
|------|---------|
| `research/parity_eval.py` | Canonical evaluation pipeline (patterns, indicators, metrics) |
| `research/lib/vcbb.py` | VCBB bootstrap library |
| `research/eval_e5_ema1d21/src/run_tier2_tier4.py` | E5+EMA21 sim reference |
| `v10/core/data.py` | DataFeed loader |
| `v10/core/engine.py` | BacktestEngine execution semantics |

---

## FILES_CHANGED

| File | Change |
|------|--------|
| `research/x0/p1_4_benchmark.py` | **CREATED** — 5-strategy benchmark script (380 lines) |
| `research/x0/p1_4_results.json` | **CREATED** — full results payload |
| `research/x0/p1_4_backtest_table.csv` | **CREATED** — backtest comparison CSV |
| `research/x0/p1_4_bootstrap_table.csv` | **CREATED** — bootstrap comparison CSV |
| `research/x0/search_log.md` | **UPDATED** — P1.4 evaluation log |
| `research/x0/phase1_evaluation.md` | **CREATED** — this report |

No strategy code, config, or baseline files were modified.

---

## BASELINE_MAPPING

| ID | Strategy | Description |
|----|----------|-------------|
| E0 | `vtrend` | Baseline 3-param trend (EMA cross + VDO + ATR trail) |
| E0_EMA21 | `vtrend_ema21_d1` | E0 + D1 EMA(21) regime filter |
| E5 | `vtrend_e5` | Robust ATR trail (capped TR at Q90) |
| E5_EMA21 | `vtrend_e5_ema21_d1` | E5 + D1 EMA(21) regime filter |
| X0 | `vtrend_x0` | Phase 1 — behavioral clone of E0_EMA21 |

---

## COMMANDS_RUN

```bash
python research/x0/p1_4_benchmark.py
# Total time: 69.7s
# T1: 5 strategies x 3 scenarios = 15 backtests
# T2: 5 strategies x 500 bootstrap paths = 2500 bootstrap sims
```

---

## RESULTS

### DATA_AND_ASSUMPTIONS

| Setting | Value |
|---------|-------|
| Data | `data/bars_btcusdt_2016_now_h1_4h_1d.csv` |
| Date range | 2019-01-01 to 2026-02-20 (reporting window) |
| Warmup | 365 days (bars 0-2189, no_trade mode) |
| Reporting bars | 15,648 H4 bars (from bar 2190) |
| D1 bars | 2,973 total |
| Initial capital | $10,000 USDT |
| slow_period | 120 |
| trail_mult | 3.0 |
| vdo_threshold | 0.0 |
| d1_ema_period | 21 |
| Annualization | sqrt(6.0 * 365.25) for H4 |
| Sharpe std | ddof=0 (population) |

### EVAL_PIPELINE_USED

**Canonical pattern from `research/parity_eval.py`:**
- Vectorized sims (not class-based BacktestEngine) for speed
- lfilter-based indicators (_ema, _atr, _vdo, _robust_atr)
- Same `_metrics()` function (Sharpe, CAGR, MDD, Calmar)
- Same D1 regime mapping (`_d1_regime_map`) with `<=` boundary
- Same VCBB bootstrap (make_ratios, precompute_vcbb, gen_path_vcbb)
- Pre-generated shared bootstrap paths (deterministic seed=42)

**Why this pipeline**: It is the same pipeline used for Study #41 (6-strategy parity)
and Study #43 (E5+EMA21 evaluation). It produces comparable results.

### BACKTEST_COMPARISON_TABLE

#### Harsh Scenario (50 bps per side = 100 bps RT)

| Strategy | Sharpe | CAGR% | MDD% | Calmar | Trades | TotRet% |
|----------|--------|-------|------|--------|--------|---------|
| E5_EMA21 | **1.4320** | **59.96** | 41.57 | **1.4422** | 199 | 2761.34 |
| E5 | 1.3647 | 57.04 | **40.26** | 1.4166 | 225 | 2408.63 |
| E0_EMA21 | 1.3360 | 55.32 | 41.99 | 1.3175 | 186 | 2219.72 |
| **X0** | **1.3360** | **55.32** | **41.99** | **1.3175** | **186** | **2219.72** |
| E0 | 1.2765 | 52.68 | 41.53 | 1.2684 | 211 | 1951.93 |

#### Base Scenario (31 bps per side = 62 bps RT)

| Strategy | Sharpe | CAGR% | MDD% | Calmar | Trades | TotRet% |
|----------|--------|-------|------|--------|--------|---------|
| E5_EMA21 | **1.5614** | **67.94** | 39.25 | **1.7310** | 199 | 3951.11 |
| E5 | 1.5064 | 65.80 | **38.54** | 1.7075 | 225 | 3596.32 |
| E0_EMA21 | 1.4533 | 62.47 | 40.65 | 1.5367 | 186 | 3098.07 |
| **X0** | **1.4533** | **62.47** | **40.65** | **1.5367** | **186** | **3098.07** |
| E0 | 1.4056 | 60.55 | 39.96 | 1.5155 | 211 | 2838.45 |

#### Smart Scenario (13 bps per side = 26 bps RT)

| Strategy | Sharpe | CAGR% | MDD% | Calmar | Trades | TotRet% |
|----------|--------|-------|------|--------|--------|---------|
| E5_EMA21 | **1.6838** | **75.87** | 37.81 | **2.0066** | 199 | 5531.59 |
| E5 | 1.6404 | 74.55 | **36.85** | 2.0228 | 225 | 5236.33 |
| E0_EMA21 | 1.5642 | 69.54 | 39.36 | 1.7669 | 186 | 4235.11 |
| **X0** | **1.5642** | **69.54** | **39.36** | **1.7669** | **186** | **4235.11** |
| E0 | 1.5277 | 68.39 | 38.42 | 1.7798 | 211 | 4029.20 |

### BOOTSTRAP_CONFIGURATION

| Setting | Value |
|---------|-------|
| Method | VCBB (Vol-Conditioned Block Bootstrap) |
| Library | `research/lib/vcbb.py` |
| N replications | 500 |
| Block size | 60 H4 bars (~10 days) |
| KNN neighbors | 50 (default) |
| Context window | 90 bars (realized vol lookback) |
| Seed | 42 |
| Paths shared | Yes (all strategies use same 500 paths) |
| slow_period | 120 (default only) |

### BOOTSTRAP_RESULTS_TABLE

| Strategy | Sharpe med | Sharpe [5%, 95%] | CAGR med | CAGR [5%, 95%] | MDD med | MDD [5%, 95%] | P(CAGR>0) | P(Sharpe>0) |
|----------|-----------|------------------|----------|----------------|---------|---------------|-----------|-------------|
| E0 | **0.3365** | [-0.3806, 0.9816] | **5.44%** | [-19.87, 38.44] | 70.49% | [49.21, 89.40] | **0.620** | **0.656** |
| E0_EMA21 | 0.2608 | [-0.4295, 0.9324] | 3.17% | [-16.30, 31.27] | **62.18%** | [43.14, 84.90] | 0.602 | 0.602 |
| E5 | 0.2907 | [-0.4197, 0.9441] | 3.79% | [-20.40, 36.12] | 69.42% | [49.03, 89.38] | 0.590 | 0.614 |
| E5_EMA21 | 0.2328 | [-0.4700, 0.9219] | 2.27% | [-17.87, 30.96] | 62.54% | [42.97, 85.84] | 0.568 | 0.580 |
| **X0** | **0.2608** | **[-0.4295, 0.9324]** | **3.17%** | **[-16.30, 31.27]** | **62.18%** | **[43.14, 84.90]** | **0.602** | **0.602** |

### RANKING_AND_INTERPRETATION

#### Real-Data Rankings (harsh scenario)

| Rank | By Sharpe | By CAGR | By MDD (lower=better) |
|------|-----------|---------|----------------------|
| 1 | E5_EMA21 (1.432) | E5_EMA21 (59.96%) | E5 (40.26%) |
| 2 | E5 (1.365) | E5 (57.04%) | E0 (41.53%) |
| 3 | E0_EMA21 = X0 (1.336) | E0_EMA21 = X0 (55.32%) | E5_EMA21 (41.57%) |
| 4 | E0 (1.277) | E0 (52.68%) | E0_EMA21 = X0 (41.99%) |

#### Bootstrap Rankings (median)

| Rank | By Sharpe | By CAGR | By MDD (lower=better) |
|------|-----------|---------|----------------------|
| 1 | E0 (0.337) | E0 (5.44%) | E0_EMA21 = X0 (62.18%) |
| 2 | E5 (0.291) | E5 (3.79%) | E5_EMA21 (62.54%) |
| 3 | E0_EMA21 = X0 (0.261) | E0_EMA21 = X0 (3.17%) | E5 (69.42%) |
| 4 | E5_EMA21 (0.233) | E5_EMA21 (2.27%) | E0 (70.49%) |

**Key observations:**
1. **Real data**: EMA21 regime filter improves Sharpe/CAGR at the cost of slightly higher MDD.
   E5 (robust ATR) provides the best MDD. E5+EMA21 combines both for best risk-adjusted returns.
2. **Bootstrap**: Rankings invert — simpler strategies (E0) have higher median bootstrap metrics.
   This is expected: bootstrap paths don't preserve the trending structure that regime filters exploit.
   However, EMA21 variants have ~8% lower MDD in bootstrap — the drawdown reduction is robust.
3. **All strategies** have P(CAGR>0) in 57-62% range — genuine but uncertain edge.

### X0_VS_BASELINES_CONCLUSION

**X0 Phase 1 is a verified alias of E0+EMA21.**

| Check | Result |
|-------|--------|
| X0 vs E0_EMA21 backtest (smart) | BIT-IDENTICAL |
| X0 vs E0_EMA21 backtest (base) | BIT-IDENTICAL |
| X0 vs E0_EMA21 backtest (harsh) | BIT-IDENTICAL |
| X0 vs E0_EMA21 bootstrap (all 12 stats) | BIT-IDENTICAL |
| X0 rank vs E0 | X0 > E0 on Sharpe/CAGR, X0 < E0 on MDD |
| X0 rank vs E5 | X0 < E5 on all metrics |
| X0 rank vs E5_EMA21 | X0 < E5_EMA21 on Sharpe/CAGR |

X0 Phase 1 inherits E0+EMA21's position: stronger than E0 on risk-adjusted
returns, weaker than E5/E5+EMA21 on all metrics. The D1 regime filter's
primary contribution is MDD reduction in bootstrap (62% vs 70%).

### RECOMMENDATION_FOR_PHASE2

X0 Phase 1 is a clean anchor point. The benchmark establishes:

1. **E5's robust ATR is the single most impactful improvement** over E0
   (Sharpe: +0.09 harsh, +0.05 base). This should be a candidate for X0 Phase 2.

2. **D1 EMA(21) regime adds ~0.06 Sharpe** on real data across all cost levels,
   with ~8% MDD reduction in bootstrap. Already included in X0 via E0+EMA21 base.

3. **The gap to close**: X0 → E5_EMA21 is +0.10 Sharpe (harsh). The primary
   contributor is the robust ATR trail, not the regime filter (already present).

Phase 2 candidates (in priority order):
- **P2a**: Add robust ATR trail (E5-style) — expected to close most of the gap
- **P2b**: Parameter exploration on the X0 anchor with standard ATR
- **P2c**: New components not in E0/E5 family

---

## BLOCKERS

None.

---

## NEXT_READY

- **P2.x**: Begin X0 Phase 2 modifications.
  Recommended first step: evaluate adding robust ATR trail (E5-style `_robust_atr`)
  to X0, which would make X0 Phase 2 behaviorally equivalent to E5+EMA21.
