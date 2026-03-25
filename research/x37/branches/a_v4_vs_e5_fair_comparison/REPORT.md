# X37 Branch A: V4 macroHystB vs E5_ema21D1 — Fair Comparison Report

**Date**: 2026-03-17
**Short ID**: x37v4
**Algorithm name**: macroHystB
**Verdict**: **V4_COMPETITIVE** (V4 wins 3/4, WFO underpowered → TIE)
**Cost**: 20 bps RT (primary)

---

## 1. Strategy Profiles

### V4 macroHystB (x37v4)
- **Source**: `research/x37/resource/gen1/v4_macroHystB/`
- **Features**: d1_ret_60 (macro regime), h4_trendq_84 (trend quality), h4_buyimb_12 (flow)
- **State machine**: 2-state hysteresis (FLAT→LONG: macro+entry+flow; LONG→FLAT: ¬hold)
- **Calibration**: Expanding quantile to year boundary (macro/entry/hold) + trailing 365d (flow)
- **D1→H4 alignment**: `<=` (allow_exact_matches, spec-exact)
- **Parameters**: ~10 (3 lookbacks, 4 quantiles, 2 modes, 1 anchor)
- **Trade start**: 2020-01-01

### E5_ema21D1
- **Source**: `strategies/vtrend_e5_ema21_d1/`
- **Features**: EMA crossover + VDO + ATR trailing stop + D1 EMA(21) regime
- **Parameters**: 4 (slow_period=120, trail_mult=3.0, vdo_threshold=0.0, d1_ema_period=21)
- **D1→H4 alignment**: `<` (strict, codebase convention)

---

## 2. Acceptance Test (Phase 2)

| Check | Status |
|-------|--------|
| Thresholds (7 years) | **ALL PASS** (delta=0.000000 for all years) |
| Trade path (51 trades) | **PASS** (0 timestamp mismatches, max net_ret delta=1.76e-6) |
| Performance (5 metrics) | **ALL PASS** (trades=51, Sharpe=1.865, CAGR=67.1%, MDD=23.9%, WR=58.8%) |
| Overall | **PASS** |

---

## 3. Performance Summary (20 bps RT)

| Metric | V4 Dev | E5 Dev | V4 Holdout | E5 Holdout | V4 Full | E5 Full |
|--------|--------|--------|------------|------------|---------|---------|
| Sharpe | 1.849 | 1.713 | 1.965 | 1.285 | **1.865** | 1.607 |
| CAGR % | 73.3 | **84.3** | **56.1** | 38.9 | 67.1 | **69.0** |
| MDD % | **23.9** | 35.4 | **12.2** | 21.6 | **23.9** | 35.4 |
| Trades | 35 | 105 | 16 | 57 | 51 | 162 |
| Profit Factor | **3.75** | 1.81 | **11.75** | 1.88 | **6.27** | 1.90 |
| Win Rate | **58.8%** | 44.4% | — | — | **58.8%** | 44.4% |

---

## 4. Verdict Breakdown

| Dimension | Winner | Evidence |
|-----------|--------|----------|
| **Sharpe** | **V4** | 1.865 vs 1.607 (+16.1%) |
| **MDD** | **V4** | 23.9% vs 35.4% (−32.5% relative) |
| **WFO** | **TIE** | V4 wins 5/7 valid, 2/3 power-only. But Wilcoxon p=1.0 (n=3 < min 6). Statistically unsupported. |
| **Paired bootstrap** | **V4** | P(V4>E5) = 93.6% (full, block=20) |
| **Sensitivity** | **E5** | V4 spread 0.535 > E5 0.413 (V4 more fragile) |

**Final: V4_COMPETITIVE (3 wins, 0 losses, 1 TIE)**

Cannot reach V4_SUPERIOR because WFO = TIE (requires 4/4 including WFO).

---

## 5. WFO Head-to-Head Details

| Window | Period | V4 Score | E5 Score | Delta | V4 Trades | E5 Trades | Valid | Power |
|--------|--------|----------|----------|-------|-----------|-----------|-------|-------|
| 0 | 2022H1 | 4.65 | -7.09 | +11.74 | 1 | 5 | Yes | Low |
| 1 | 2022H2 | 0.00 | -111.34 | — | **0** | 14 | **No** | — |
| 2 | 2023H1 | 275.56 | 64.50 | **+211.07** | 7 | 17 | Yes | Yes |
| 3 | 2023H2 | 142.84 | 259.89 | **-117.04** | 6 | 14 | Yes | Yes |
| 4 | 2024H1 | 370.42 | 139.39 | **+231.03** | 7 | 16 | Yes | Yes |
| 5 | 2024H2 | 295.60 | 341.96 | -46.36 | 4 | 15 | Yes | Low |
| 6 | 2025H1 | 85.76 | 55.03 | +30.72 | 3 | 13 | Yes | Low |
| 7 | 2025H2 | 23.23 | -4.19 | +27.42 | 2 | 9 | Yes | Low |

- Power-only windows: 3 (need ≥6 for Wilcoxon)
- Wilcoxon: W+=NaN, p=1.0, sufficient=False
- Bootstrap CI: [-117.04, 231.03] (crosses zero)
- **Root cause**: V4's 51 trades spread across 8 windows → most windows have <5 V4 trades

---

## 6. Cost Sensitivity

| Cost (bps RT) | V4 Sharpe | E5 Sharpe | V4 CAGR | E5 CAGR |
|---------------|-----------|-----------|---------|---------|
| 10 | 1.893 | 1.679 | 68.5% | 73.5% |
| 15 | 1.879 | 1.643 | 67.8% | 71.2% |
| 20 | 1.865 | 1.607 | 67.1% | 69.0% |
| 25 | 1.851 | 1.571 | 66.4% | 66.7% |
| 30 | 1.837 | 1.536 | 65.7% | 64.6% |
| 50 | 1.781 | 1.392 | 63.0% | 56.1% |
| 100 | 1.640 | 1.032 | 56.3% | 36.8% |

**No crossover found** — V4 Sharpe > E5 Sharpe at all cost levels tested.

---

## 7. Why V4 Is Not Promoted

1. **WFO underpowered** — only 3/8 windows have sufficient trades for both strategies. Cannot confirm OOS robustness.
2. **Higher complexity** — ~10 params vs 4. Yearly recalibration creates implicit in-sample dependence.
3. **Lower statistical power** — 51 trades vs 162. All inference is weaker.
4. **Wider sensitivity spread** — 0.535 vs 0.413. More fragile to parameter perturbation.
5. **CAGR not superior** — V4 67.1% < E5 69.0%. V4 wins Sharpe via lower MDD, not higher returns.
6. **Order-flow dependency** — requires taker_buy_base_vol data, less portable.

---

## 8. Artifacts

| File | Description |
|------|-------------|
| `results/acceptance_test.json` | Phase 2: V4 rebuild acceptance (PASS) |
| `results/v4_backtest.json` | Phase 3a: V4 backtest all periods |
| `results/e5_backtest.json` | Phase 3a: E5 backtest all periods |
| `results/wfo_summary.json` | Phase 3b: WFO head-to-head summary |
| `results/wfo_head_to_head.csv` | Phase 3b: WFO per-window details |
| `results/paired_bootstrap.csv` | Phase 3d: Paired bootstrap results |
| `results/cost_sweep.csv` | Phase 3f: Cost sensitivity |
| `results/regime_decomposition.csv` | Phase 3g: Regime analysis |
| `results/v4_sensitivity.csv` | Phase 3h: V4 parameter sensitivity |
| `results/e5_sensitivity.csv` | Phase 3h: E5 parameter sensitivity |
| `results/selection_bias.json` | Phase 3i: DSR advisory |
| `results/verdict.json` | Phase 4: Machine verdict |
| `results/comparison_report.md` | Phase 4: Full comparison report |
