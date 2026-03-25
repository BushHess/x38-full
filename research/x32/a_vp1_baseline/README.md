# Branch A — VP1 Baseline Implementation & Validation

## Status: COMPLETE (2026-03-12)

All 5 steps completed. VP1 rebuild matches frozen spec v1.1.

## Reference
- Canonical spec: `../resource/06_final_audited_rebuild_spec_v1.1.md` (READ-ONLY)
- Machine-readable: `../resource/07_final_audited_rebuild_spec_v1.1.json` (READ-ONLY)

## Steps
- [x] A1: Implement VP1 strategy from spec
- [x] A2: Pass acceptance tests (15/15 PASS)
- [x] A3: Full-history backtest (2017-08 → 2026-02)
- [x] A4: Bootstrap CI (VCBB)
- [x] A5: Trade structure analysis

## Results Summary

### A2: Acceptance Tests — 15/15 PASS
- Tier-2 trade count = 43 (exact match)
- First 3 entry/exit fill timestamps (exact match)
- First trade cycle: entry 60335.41 → exit 57881.70, trailing_stop (exact match)
- All deterministic formula tests pass

### A3: Full-History Backtest (2017-08 → 2026-02)

| Scenario | Cost (bps) | Sharpe | CAGR % | MDD % | Trades |
|---|---|---|---|---|---|
| smart | 13 | 1.3853 | 64.08 | 61.55 | 232 |
| base | 31 | 1.2691 | 56.22 | 63.37 | 232 |
| harsh | 50 | 1.1461 | 48.34 | 65.24 | 232 |

### A4: Bootstrap CIs (VCBB, harsh, N=2000)

| Metric | Observed | 95% CI | P(>0) |
|---|---|---|---|
| Sharpe | 1.1461 | [0.46, 1.81] | 99.9% |
| CAGR % | 48.30 | [10.97, 96.27] | 99.7% |
| MDD % | 65.24 | [35.81, 74.83] | — |

### A5: Trade Structure (harsh)
- 232 trades (99W / 133L), win rate 42.7%
- Avg winner: +9.95%, Avg loser: -3.48%
- Top 5 trades = 65.6% of total PnL (fat-tail alpha)
- Exit: 94.8% trailing stop, 5.2% trend reversal
- Avg exposure: 42.3%, avg days held: 5.7

### Quick Comparison vs E5+EMA1D21 (harsh)

| Metric | VP1 | E5+EMA1D21 | Delta |
|---|---|---|---|
| Sharpe | 1.1461 | 1.1944 | -0.048 |
| CAGR % | 48.34 | 52.59 | -4.25 |
| MDD % | 65.24 | 61.37 | +3.87 |
| Trades | 232 | 226 | +6 |

VP1 slightly worse than E5+EMA1D21 on all headline metrics.

### A6: Full Validation Pipeline (17 suites, vs E0 baseline)

Run: `python validate_strategy.py --strategy vtrend_vp1 --baseline vtrend --suite all`

| Gate | Result | Detail |
|------|--------|--------|
| Lookahead | PASS | No future data access |
| Data integrity | PASS | |
| Full delta (G0) | PASS | +27.46 score |
| Holdout | **FAIL** | -8.02 (underperforms E0 in 2024-09 → 2026-02) |
| WFO Wilcoxon | PASS | p=0.055, 6/8 windows positive |
| Bootstrap P(d>0) | PASS | 92.4% |
| PSR | PASS | 0.9998 |
| **Verdict** | **ERROR** | Holdout FAIL blocks PROMOTE |

Validation window metrics (2019-01 → 2026-02, harsh):
- Sharpe 1.452, CAGR 61.7%, MDD 40.5%, 194 trades (vs E0: 1.265, 52.0%, 41.6%)

WFO wins 6/8 windows. Losses in 2025-H1 (-41.3) and 2025-H2 (-12.3).
Regime: wins BULL, NEUTRAL, TOPPING, SHOCK. Loses BEAR, CHOP (slow=140 whipsaws in chop).

## Artifacts
- `code/acceptance_test.py` — spec §13 acceptance tests
- `code/full_evaluation.py` — A3+A4+A5 combined evaluation
- `results/acceptance_test/` — acceptance test outputs
- `results/full_eval/` — backtest results, bootstrap CIs, trade analysis
- `results/full_validation/` — 17-suite validation pipeline output

## VP1 Frozen Parameters
```
slow_period = 140
fast_period = 35
atr_type = standard_wilder
atr_period = 20
trail_mult = 2.5
d1_ema_period = 28
vdo_threshold = 0.0
warmup_days = 365
cost = 50 bps RT (benchmark)
```

## Implementation
- Strategy: `strategies/vtrend_vp1/strategy.py`
- Config: `VP1Config` dataclass
- CLI: registered as `vtrend_vp1` in `v10/cli/backtest.py`
