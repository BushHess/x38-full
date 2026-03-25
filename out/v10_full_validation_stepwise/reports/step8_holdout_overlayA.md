# Step 8: Holdout Validation — Overlay A

**Date:** 2026-02-24
**Holdout period:** 2024-10-01 → 2026-02-20 (locked from V11 validation)
**Overlay A param:** cooldown_after_emergency_dd_bars = 12
**Rule:** If overlay degrades harsh score (>5 pts) or MDD (>5pp) on holdout → HOLD/REJECT.

---

## 1. Executive Summary

**Verdict: PASS**
- harsh score delta +30.99 within threshold, MDD delta -5.80pp within threshold

| | Harsh | Base |
|--|-------|------|
| Score delta | +30.99 | +22.17 |
| CAGR delta | +9.55pp | +6.45pp |
| MDD delta | -5.80pp | -5.76pp |
| ED delta | -2 | -1 |

---

## 2. KPI Comparison

### Harsh scenario

| Metric | Baseline | Overlay A | Delta | % Change |
|--------|----------|-----------|-------|----------|
| score | 34.6563 | 65.6458 | 30.9895 | +89.42% |
| cagr_pct | 17.29 | 26.84 | 9.55 | +55.23% |
| final_nav_mid | 12481.72 | 13918.04 | 1436.32 | +11.51% |
| max_drawdown_mid_pct | 31.56 | 25.76 | -5.8 | -18.38% |
| sharpe | 0.6961 | 0.9616 | 0.2655 | +38.14% |
| sortino | 0.727 | 1.0191 | 0.2921 | +40.18% |
| calmar | 0.5477 | 1.0421 | 0.4944 | +90.27% |
| trades | 26 | 24 | -2 | -7.69% |
| wins | 15 | 15 | 0 | +0.00% |
| losses | 11 | 9 | -2 | -18.18% |
| win_rate_pct | 57.69 | 62.5 | 4.81 | +8.34% |
| profit_factor | 1.4397 | 1.7818 | 0.3421 | +23.76% |
| avg_trade_pnl | 112.7 | 181.39 | 68.69 | +60.95% |
| fees_total | 901.86 | 877.63 | -24.23 | -2.69% |
| fee_drag_pct_per_year | 5.19 | 4.75 | -0.44 | -8.48% |
| emergency_dd_count | 10 | 8 | -2 | -20.00% |
| time_in_market_pct | 61.19 | 60.63 | -0.56 | -0.92% |
| avg_exposure | 0.507 | 0.5097 | 0.0027 | +0.53% |

### Base scenario

| Metric | Baseline | Overlay A | Delta | % Change |
|--------|----------|-----------|-------|----------|
| score | 55.0562 | 77.2247 | 22.1685 | +40.27% |
| cagr_pct | 24.35 | 30.8 | 6.45 | +26.49% |
| final_nav_mid | 13539.92 | 14524.9 | 984.98 | +7.27% |
| max_drawdown_mid_pct | 30.86 | 25.1 | -5.76 | -18.66% |
| sharpe | 0.8954 | 1.0674 | 0.172 | +19.21% |
| sortino | 0.937 | 1.1275 | 0.1905 | +20.33% |
| calmar | 0.7892 | 1.2267 | 0.4375 | +55.44% |
| trades | 25 | 24 | -1 | -4.00% |
| wins | 15 | 15 | 0 | +0.00% |
| losses | 10 | 9 | -1 | -10.00% |
| win_rate_pct | 60.0 | 62.5 | 2.5 | +4.17% |
| profit_factor | 1.6068 | 1.8691 | 0.2623 | +16.32% |
| avg_trade_pnl | 153.42 | 200.89 | 47.47 | +30.94% |
| fees_total | 595.06 | 598.21 | 3.15 | +0.53% |
| fee_drag_pct_per_year | 3.29 | 3.15 | -0.14 | -4.26% |
| emergency_dd_count | 9 | 8 | -1 | -11.11% |
| time_in_market_pct | 61.42 | 60.63 | -0.79 | -1.29% |
| avg_exposure | 0.5151 | 0.5096 | -0.0055 | -1.07% |

---

## 3. Cascade Metrics (Holdout)

| | Baseline | Overlay A | Delta |
|--|----------|-----------|-------|
| **Harsh** | | | |
| ED exits | 10 | 8 | -2 |
| Cascade ≤3 bars | 0.0% | 0.0% | +0.0pp |
| Cascade ≤6 bars | 30.0% | 0.0% | -30.0pp |
| **Base** | | | |
| ED exits | 9 | 8 | -1 |
| Cascade ≤3 bars | 0.0% | 0.0% | +0.0pp |
| Cascade ≤6 bars | 33.3% | 0.0% | -33.3pp |

---

## 4. Blocked Trades (Holdout, Harsh)

| Metric | Value |
|--------|-------|
| N Blocked | 7 |
| N Total Baseline | 26 |
| Pct Blocked | +26.90 |
| Mean Net Pnl | -283.82 |
| Median Net Pnl | -373.57 |
| Total Net Pnl | -1,986.73 |
| Pct Exit Emergency Dd | +42.90 |

Overlay A blocked 88 entry attempts on holdout. The 7 blocked trades have negative median PnL ($-374) and 43% exit via emergency_dd.

---

## 5. Verdict

**PASS.**

Overlay A passes out-of-sample validation on the holdout period (2024-10-01 → 2026-02-20).

Evidence:
- Harsh score delta: +30.99 (threshold: >-5.0)
- Harsh MDD delta: -5.80pp (threshold: <+5.0pp)
- ED exits: 10 → 8 (-2)
- Blocked trades median PnL: $-374 (43% ED)
- Base scenario score delta: +22.17