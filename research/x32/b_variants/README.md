# Branch B — VP1 Parameter Variants

## Objective
Systematic single-dimension parameter exploration around VP1 baseline.
Each variant changes ONE parameter, evaluated against VP1 baseline (not E5).

## Prerequisite
Branch A must pass acceptance tests (A2) before any variant work begins.

## Variant Registry

| ID | Dimension | Values | VP1 default | Rationale |
|---|---|---|---|---|
| B1 | ATR type (VP1-E5exit) | RATR | Standard Wilder | E5 uses RATR — does ATR type matter? |
| B2 | ATR period | 14, 16, 20, 24, 28 | 20 | Sensitivity of trail stop to ATR lookback |
| B3 | trail_mult | 2.0, 2.5, 3.0, 3.5, 4.0 | 2.5 | Return/risk tradeoff (proven in E5 trail sweep) |
| B4 | d1_ema_period | 15, 21, 28, 35, 40 | 28 | Regime filter speed; 21 is E5 default |
| B5 | slow_period | 80, 100, 120, 140, 160 | 140 | EMA crossover speed; 120 is E5 default |
| B6 | fast_period rule | N/3, N/4, N/5, fixed 21 | floor(N/4) | Entry sensitivity |
| B7 | Combined best (VP1-FULL) | ALL E5 changes | — | Full E5 parameter set on VP1 structure |

## Implemented Variants

### VP1-E5exit (B1 — ATR type swap)
- **Strategy**: `strategies/vtrend_vp1_e5exit/`
- **Config**: `configs/vtrend_vp1_e5exit/vtrend_vp1_e5exit_default.yaml`
- **Changes**: Standard Wilder ATR(20) → RATR (quantile-capped, cap_q=0.90, cap_lb=100)
- **Keeps**: VP1 structure (prevday D1, per-bar VDO, anomaly), VP1 parameters (slow=140, trail=2.5, d1_ema=28)
- **Isolates**: does RATR improve VP1's trailing stop?

### VP1-FULL (B7 — all E5 changes combined)
- **Strategy**: `strategies/vtrend_vp1_full/`
- **Config**: `configs/vtrend_vp1_full/vtrend_vp1_full_default.yaml`
- **Changes**: RATR + slow=120 + trail=3.0 + d1_ema=21 (all E5 parameter values)
- **Keeps**: VP1 structure (prevday D1, per-bar VDO, anomaly)
- **Isolates**: how much of the E5-VP1 gap comes from structure vs parameter tuning?

## Evaluation per variant
- Full validation pipeline (`--suite all`, 17 suites)
- Full-history backtest (3 cost scenarios)
- WFO (8-fold rolling)
- Bootstrap CI (VCBB, N=2000)
- Holdout (20%)
- PSR gate
- Trade-level analysis
- Regime decomposition
- Cost sensitivity sweep
- Delta vs VP1 baseline AND vs E0 (vtrend) baseline
- Pass/fail against standard gates (G0-G3)

## Status: IN PROGRESS
- [x] VP1-E5exit: strategy implemented, validation running
- [x] VP1-FULL: strategy implemented, validation running
- [ ] B2-B6: parameter sweeps (pending)
