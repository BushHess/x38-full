# V10 vs V11 — Side-by-Side Comparison

**V10:** `V8ApexStrategy(V8ApexConfig())` — default parameters
**V11:** V10 + cycle_late_only overlay (aggr=0.95, trail_mult=2.8, max_exposure=0.90)
**Period:** 2019-01-01 → 2026-02-20 (7.14 years)
**Report date:** 2026-02-24

---

## 1. Full-Period Backtest (3 Scenarios)

### 1.1 Overall Metrics

| Metric | V10 (smart) | V11 (smart) | Δ | V10 (base) | V11 (base) | Δ | V10 (harsh) | V11 (harsh) | Δ |
|--------|-------------|-------------|---|------------|------------|---|-------------|-------------|---|
| **Score** | 121.37 | 123.30 | +1.93 | 112.74 | 114.65 | +1.91 | 88.94 | 90.80 | +1.86 |
| **CAGR%** | 48.56 | 49.26 | +0.70 | 45.55 | 46.24 | +0.69 | 37.26 | 37.93 | +0.67 |
| **MDD%** | 34.07 | 34.07 | 0.00 | 34.78 | 34.78 | 0.00 | 36.28 | 36.28 | 0.00 |
| **Sharpe** | 1.386 | 1.405 | +0.020 | 1.322 | 1.341 | +0.019 | 1.151 | 1.170 | +0.019 |
| **PF** | 1.866 | 1.871 | +0.006 | 1.831 | 1.837 | +0.006 | 1.669 | 1.676 | +0.007 |
| **Trades** | 100 | 100 | 0 | 100 | 100 | 0 | 103 | 103 | 0 |
| **WR%** | 52.0 | 52.0 | 0.0 | 52.0 | 52.0 | 0.0 | 50.5 | 50.5 | 0.0 |
| **Final NAV** | $168,780 | $174,594 | +$5,814 | $145,815 | $150,883 | +$5,069 | $95,968 | $99,336 | +$3,368 |

### 1.2 Key Observations

- V11 improvement is **+1.86 to +1.93 score points** (2.1% relative)
- MDD is **identical** — V11's cycle_late does not improve worst drawdown
- Trade count is **identical** — overlay only modifies behavior within existing trades
- Δ Sharpe = +0.019 — statistically insignificant (incremental DSR = 0.0016, FAIL)

---

## 2. Regime Decomposition (harsh)

### 2.1 V10 Regime Returns

| Regime | Days | % | Return% | MDD% | Sharpe | Trades | WR% | PF |
|--------|------|---|---------|------|--------|--------|-----|-----|
| BULL | 1211 | 46.4 | +1109.1 | 36.0 | 2.10 | 61 | 50.8 | 1.78 |
| TOPPING | 102 | 3.9 | -21.0 | 29.5 | -2.96 | 5 | 40.0 | 0.32 |
| BEAR | 661 | 25.3 | +0.8 | 17.7 | 0.85 | 0 | — | — |
| SHOCK | 89 | 3.4 | -14.3 | 29.3 | -0.98 | 2 | 50.0 | 1.37 |
| CHOP | 215 | 8.2 | +1.6 | 31.8 | 0.25 | 14 | 57.1 | 1.86 |
| NEUTRAL | 330 | 12.7 | +14.4 | 24.8 | 0.71 | 21 | 47.6 | 1.63 |

### 2.2 V11 Delta by Regime

V11's cycle_late_only overlay activates **only in extended BULL periods** when the
cycle-late trigger fires. All other regimes have identical performance.

| Regime | V10 Return% | V11 Δ Return% | V10 Sharpe | V11 Δ Sharpe |
|--------|-------------|---------------|------------|--------------|
| BULL | +1109.1 | ≈ +0.7 | 2.10 | ≈ +0.02 |
| TOPPING | -21.0 | 0.0 | -2.96 | 0.0 |
| BEAR | +0.8 | 0.0 | 0.85 | 0.0 |
| SHOCK | -14.3 | 0.0 | -0.98 | 0.0 |
| CHOP | +1.6 | 0.0 | 0.25 | 0.0 |
| NEUTRAL | +14.4 | 0.0 | 0.71 | 0.0 |

The full-period advantage comes entirely from slightly better BULL execution.

---

## 3. WFO Round-by-Round (harsh)

### 3.1 Per-Round Comparison

| Win | Period | V10 Score | V11 Score | Δ Score | V10 Ret% | V11 Ret% | Δ Ret% |
|-----|--------|-----------|-----------|---------|----------|----------|--------|
| 0 | 2021-H1 | REJECT | REJECT | 0 | +41.3 | +43.4 | +2.1 |
| 1 | 2021-H2 | -9.63 | -9.63 | 0.00 | +0.1 | +0.1 | 0.0 |
| 2 | 2022-H1 | REJECT | REJECT | 0 | 0.0 | 0.0 | 0.0 |
| 3 | 2022-H2 | REJECT | REJECT | 0 | 0.0 | 0.0 | 0.0 |
| 4 | 2023-H1 | REJECT | REJECT | 0 | -3.0 | -3.0 | 0.0 |
| 5 | 2023-H2 | REJECT | REJECT | 0 | +24.1 | +27.0 | +2.9 |
| 6 | 2024-H1 | **171.13** | 169.56 | **-1.57** | +28.8 | +28.5 | -0.3 |
| 7 | 2024-H2 | **158.58** | 154.26 | **-4.32** | +26.0 | +25.3 | -0.6 |
| 8 | 2025-H1 | -72.59 | -72.59 | 0.00 | -11.6 | -11.6 | 0.0 |
| 9 | 2025-H2 | REJECT | REJECT | 0 | -3.3 | -3.3 | 0.0 |

### 3.2 WFO Summary

| Metric | V10 | V11 | Assessment |
|--------|-----|-----|-----------|
| Scored rounds with Δ ≠ 0 | 2 | 2 | Only Win 6 and Win 7 differ |
| V11 wins (score) | 0/2 | — | V10 wins both active windows |
| V11 wins (return) | 2/4 | — | V11 wins masked rounds (0, 5); V10 wins active (6, 7) |
| Mean Δ score (non-zero) | — | -2.95 | V11 loses on scored rounds |
| Sign test p (effective n=2) | — | 1.000 | No evidence of V11 improvement |

**Key finding:** V11 gains +2.1% and +2.9% in masked (rejected) windows, but loses
-0.3% and -0.6% in the only 2 scored windows. The cycle_late trigger helps in early
bull markets (2021-H1, 2023-H2) but slightly hurts in mature bulls (2024).

---

## 4. Final Holdout (2024-10-01 → 2026-02-20)

### 4.1 Holdout Metrics

| Metric | V10 (harsh) | V11 (harsh) | Δ | V10 (base) | V11 (base) | Δ | V10 (smart) | V11 (smart) | Δ |
|--------|-------------|-------------|---|------------|------------|---|-------------|-------------|---|
| **Score** | 34.66 | 33.43 | **-1.23** | 55.06 | 53.78 | **-1.28** | 64.64 | 63.31 | **-1.32** |
| **CAGR%** | 17.29 | 16.85 | -0.44 | 24.35 | 23.89 | -0.46 | 27.65 | 27.17 | -0.48 |
| **Return%** | +24.82 | +24.18 | -0.64 | +35.40 | +34.70 | -0.70 | +40.42 | +39.68 | -0.74 |
| **MDD%** | 31.56 | 31.56 | 0.00 | 30.86 | 30.86 | 0.00 | 30.19 | 30.19 | 0.00 |
| **Sharpe** | 0.696 | 0.685 | -0.011 | 0.895 | 0.885 | -0.010 | 0.986 | 0.975 | -0.010 |
| **Trades** | 26 | 26 | 0 | 25 | 25 | 0 | 25 | 25 | 0 |

### 4.2 Holdout Regime Breakdown (harsh)

| Regime | Days | V10 Ret% | V11 Ret% | Δ |
|--------|------|----------|----------|---|
| BULL | 300 | +43.89 | +43.16 | **-0.73** |
| TOPPING | 18 | -0.70 | -0.70 | 0.00 |
| BEAR | 93 | 0.00 | 0.00 | 0.00 |
| SHOCK | 7 | -10.55 | -10.55 | 0.00 |
| CHOP | 50 | +2.59 | +2.59 | 0.00 |
| NEUTRAL | 40 | -4.82 | -4.82 | 0.00 |

**V11 underperforms V10 on the holdout.** The loss comes entirely from BULL regime
(-0.73 pp). V11's tighter trailing stop (2.8× vs 3.5×) in LATE_BULL clips some
recovery upside during the 2025 correction.

---

## 5. Selection Bias

### 5.1 PBO (Probability of Backtest Overfitting)

| Universe | V10 PBO | V11 PBO | Interpretation |
|----------|---------|---------|----------------|
| Own family (27 configs) | **14.7%** | **13.9%** | Both LOW |
| V10 default in full 54 | **14.3%** | — | V10 competitive in combined space |
| V11+V10 (28 configs) | — | **13.9%** | V11 IS-best transfers well OOS |
| Full universe IS-best | 68.7% | — | Misleading (IS-best is edge V10 variant) |

### 5.2 Deflated Sharpe Ratio

| N (trials) | V10 DSR | V11 DSR | Both PASS? |
|-----------|---------|---------|------------|
| 27 | 1.0000 | 1.0000 | YES |
| 54 | 1.0000 | 1.0000 | YES |
| 89 | 1.0000 | 1.0000 | YES |
| 694 | 1.0000 | 1.0000 | YES |

### 5.3 Incremental DSR (V11 vs V10)

| Metric | Value |
|--------|-------|
| V10 Sharpe | 1.1510 |
| V11 Sharpe | 1.1470 |
| Δ Sharpe | **-0.0040** (V11 is worse) |
| Incremental DSR (N=694) | **0.0016 (FAIL)** |

The V11 "improvement" is negative on Sharpe and does not survive multiple-testing
adjustment even at N=27.

---

## 6. Sensitivity Grid

### 6.1 V10 Grid (27 points: trail × vdo × aggr)

| Metric | Beat Default | Best Δ | Worst Δ | Mean Δ |
|--------|-------------|--------|---------|--------|
| harsh | 3/27 (11%) | +5.25 | -48.57 | -15.32 |

Default rank: **4/27**. Cliff at vdo=0.006 and aggr=0.65.

### 6.2 V11 Grid (27 points: aggr × trail × cap)

| Metric | Beat V10 | Best Δ | Worst Δ | Mean Δ |
|--------|----------|--------|---------|--------|
| harsh | 6/27 (22%) | +2.10 | -7.59 | -2.24 |

Only 22% of V11 parameter space beats V10. Cliff risk at trail_mult boundaries.

### 6.3 Grid Comparison

| Aspect | V10 | V11 |
|--------|-----|-----|
| Default rank in own grid | 4/27 | ~5/27 |
| Cliff points | 5 (vdo=0.006 edge) | Boundary cliff at trail ≠ 3.0 |
| Robustness interpretation | Moderate (asymmetric) | Weak (22% beat rate) |

---

## 7. Lookahead / Leakage

| Test | V10 | V11 |
|------|-----|-----|
| Test suite | 11 + 9 = 20 tests | 7 + 9 = 16 tests |
| Result | **20/20 PASS** | **16/16 PASS** |
| Engine mechanism | Strict `<` alignment | Same engine |
| HTF access points | 2 D1 arrays | Same 2 D1 arrays |

Both strategies use identical HTF alignment through the same engine. Zero lookahead
detected in either.

---

## 8. Drawdown Comparison

### 8.1 V10 DD Profile

| Metric | Value |
|--------|-------|
| Max DD | 36.28% |
| Mean regime during top-10 DDs | 51% BULL, 3.8% TOPPING |
| Mean exposure at DD peak | 96% |
| Emergency_dd as exit | 49% of DD exits |
| Buy fills per DD episode | 45.1 mean |

### 8.2 V11 DD Difference

V11 MDD = 36.28% = **identical** to V10. The cycle_late_only overlay does not reduce
the worst drawdown because:
- The max DD (Episode 1: 2021-11 → 2023-10) occurs during BEAR regime
- cycle_late only fires in extended BULL → it misses the main pain source
- V11's tighter trail (2.8× vs 3.5×) helps slightly in late bulls but doesn't
  reduce the structural pyramiding issue

---

## 9. Final Verdict

### Scorecard

| Dimension | V10 | V11 | Winner |
|-----------|-----|-----|--------|
| Full-period score (harsh) | 88.94 | 90.80 | V11 (+1.86) |
| Full-period Sharpe (harsh) | 1.151 | 1.170 | V11 (+0.019) |
| Full-period MDD | 36.28% | 36.28% | TIE |
| Holdout score (harsh) | 34.66 | 33.43 | **V10 (+1.23)** |
| Holdout Sharpe (harsh) | 0.696 | 0.685 | **V10 (+0.011)** |
| WFO scored rounds | 2/2 wins | 0/2 wins | **V10** |
| Sensitivity beat rate | — | 22% beat V10 | **V10 more robust** |
| PBO (own family) | 14.7% | 13.9% | TIE |
| DSR (N=694) | 1.0000 | 1.0000 | TIE |
| Incremental DSR | — | 0.0016 (FAIL) | **V10 (no improvement)** |
| Lookahead | PASS | PASS | TIE |

### Decision

| Question | Answer |
|----------|--------|
| Is V10 a robust baseline? | **YES** — genuine Sharpe, no lookahead, low selection bias |
| Does V11 improve on V10? | **NO** — Δ Sharpe is negative (-0.004), holdout is worse, WFO scored rounds are worse |
| Should V11 replace V10? | **NO** — HOLD decision confirmed |
| What should improve V10? | Risk overlays targeting pyramiding in BULL corrections (see v10_topping_diagnosis.md) |

### Recommendation

**V10 remains the production baseline.** V11 cycle_late_only is archived as a research
variant that did not demonstrate improvement. Future development should focus on reducing
V10's drawdown through risk overlays (emergency_dd cooldown, exposure cap by rolling DD)
rather than entry signal modifications.
