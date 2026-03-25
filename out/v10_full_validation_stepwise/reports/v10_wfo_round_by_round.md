# V10 WFO Round-by-Round Analysis

## Setup

- Strategy: `V8ApexStrategy(V8ApexConfig())` — fixed params, no optimization
- WFO: 24m train / 6m test / 6m slide (train window unused — V10 has no per-window tuning)
- Windows: 10 OOS periods (2021-01 → 2026-01)
- Cost scenarios: smart (13 bps), base (31 bps), harsh (50 bps RT)
- Regime classifier: `v10/research/regime.py::classify_d1_regimes()`
- Score rejection: `n_trades < 10` → score = -1,000,000 (sentinel, not a real score)

## Per-Round Metrics

**Note:** Score = -1M means the window had <10 trades (rejected by `compute_objective`).
The raw return/MDD/regime data is still valid for those windows.

| Win | Period | Trades | Return% | Harsh Score | Base Score | Smart Score | MDD% | BULL% | TOP% | Fees |
|-----|--------|--------|---------|-------------|------------|-------------|------|-------|------|------|
| 0 | 2021-01 → 2021-07 | 8 | +41.3 | REJECT | REJECT | REJECT | 17.8 | +10.1 | +0.0 | 212 |
| 1 | 2021-07 → 2022-01 | 10 | +0.1 | -9.63 | REJECT | REJECT | 21.8 | +2.5 | -8.4 | 239 |
| 2 | 2022-01 → 2022-07 | 0 | 0.0 | REJECT | REJECT | REJECT | 0.0 | +0.0 | +0.0 | 0 |
| 3 | 2022-07 → 2023-01 | 0 | 0.0 | REJECT | REJECT | REJECT | 0.0 | +0.0 | +0.0 | 0 |
| 4 | 2023-01 → 2023-07 | 4 | -3.0 | REJECT | REJECT | REJECT | 14.7 | +12.4 | -11.3 | 110 |
| 5 | 2023-07 → 2024-01 | 6 | +24.1 | REJECT | REJECT | REJECT | 15.0 | +8.0 | +6.0 | 194 |
| 6 | 2024-01 → 2024-07 | 11 | +28.8 | **171.13** | **188.08** | **204.61** | 19.1 | +50.8 | -3.8 | 372 |
| 7 | 2024-07 → 2025-01 | 10 | +26.0 | **158.58** | **174.03** | **189.15** | 15.4 | +14.1 | +1.3 | 296 |
| 8 | 2025-01 → 2025-07 | 10 | -11.6 | -72.59 | -64.87 | -57.31 | 31.6 | +2.0 | -0.5 | 259 |
| 9 | 2025-07 → 2026-01 | 10 | -3.3 | -24.22 | REJECT | REJECT | 15.6 | -0.2 | -1.0 | 285 |

### Trade Count Issue

6/10 windows have <10 trades (the `compute_objective` rejection threshold).
This is inherent to V10's design: a long-only trend-follower on 6-month windows
in bear/chop markets often opens very few positions.

- **Windows 2-3 (2022 bear):** Zero trades — EMA regime gate correctly blocks all entries
- **Window 0 (2021-H1 bull):** 8 trades, +41% return — just below threshold
- **Windows 4-5:** 4-6 trades — mixed bull/topping periods

## Per-Round Regime Returns (harsh scenario)

| Win | BULL% | TOPPING% | BEAR% | SHOCK% | CHOP% | NEUTRAL% |
|-----|-------|----------|-------|--------|-------|----------|
| 0 | +10.1 | +0.0 | +0.0 | +9.0 | +20.3 | -2.2 |
| 1 | +2.5 | -8.4 | +0.8 | -0.3 | +0.0 | +6.2 |
| 2 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| 3 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| 4 | +12.4 | -11.3 | +0.0 | +0.0 | -1.8 | -0.9 |
| 5 | +8.0 | +6.0 | +0.0 | +2.5 | +0.0 | +5.8 |
| 6 | +50.8 | -3.8 | +0.0 | -6.4 | -5.1 | +0.0 |
| 7 | +14.1 | +1.3 | +0.0 | -1.5 | +3.3 | +7.2 |
| 8 | +2.0 | -0.5 | +0.0 | -10.2 | -0.2 | -2.8 |
| 9 | -0.2 | -1.0 | +0.0 | +0.0 | +0.0 | -2.1 |

## Stability Summary

### Scored rounds only (harsh_score != -1M, N=4)

| Metric | Median | Worst | Best | Mean | Std |
|--------|--------|-------|------|------|-----|
| Harsh Score | -16.93 | -72.59 | 171.13 | 55.77 | 115.92 |
| Harsh CAGR% | -3.17 | -21.86 | 65.74 | 23.84 | 40.41 |
| Harsh MDD% | 18.35 | 15.39 | 31.56 | 20.52 | 7.52 |
| Harsh Sharpe | -0.07 | -0.61 | 1.60 | 0.58 | 1.03 |

### All 10 rounds (using raw return, not sentinel score)

| Metric | Median | Worst | Best | Mean | Std |
|--------|--------|-------|------|------|-----|
| Harsh Return% | +0.1 | -11.6 | +41.3 | +10.3 | +17.7 |
| Harsh MDD% | 15.5 | 0.0 | 31.6 | 15.1 | 9.4 |
| Harsh Trades | 9.0 | 0 | 11 | 6.9 | 4.2 |
| BULL Return% | +5.2 | -0.2 | +50.8 | +10.0 | 15.3 |
| TOPPING Return% | -0.3 | -11.3 | +6.0 | -1.8 | 5.0 |
| Fees (harsh) | 212 | 0 | 372 | 197 | 109 |
| Turnover (harsh) | 141K | 0 | 248K | 131K | 73K |

## Key Observations

**Score acceptance rate:**
- Harsh: 4/10 rounds scored (40%), 2 positive, 2 negative
- Base: 3/10 scored (30%) — all base/smart have ≥10 trades only in windows 6-8
- Root cause: V10 averages ~7 trades per 6-month window; the 10-trade threshold
  rejects most windows

**Where V10 performs well (harsh):**
- **Window 6** (2024-H1): harsh_score=171, return=+29%, strong BULL (+51%)
- **Window 7** (2024-H2): harsh_score=159, return=+26%, diversified gains
- **Window 0** (2021-H1): return=+41% but only 8 trades (rejected)

**Where V10 struggles (harsh):**
- **Window 8** (2025-H1): harsh_score=-73, return=-12%, MDD=32% — worst scored round
- **Window 4** (2023-H1): return=-3%, TOPPING=-11.3% — worst TOPPING hit
- **Windows 2-3** (2022 bear): zero activity, zero return — correct behavior for long-only

**TOPPING damage:**
- 5/10 rounds have negative TOPPING return
- Worst: Window 4 at -11.3% (2023-H1)
- TOPPING losses are concentrated in specific windows, not spread evenly

**BEAR protection:**
- BEAR return is 0.0% in 9/10 rounds — regime gate works perfectly
- Exception: Window 1 at +0.8% (residual position carrying into BEAR)

**MDD profile:**
- Only 1/10 rounds exceeds 30% MDD (Window 8 at 31.6%)
- Median MDD = 15.5% across all rounds — well-controlled outside bull corrections
