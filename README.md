# btc-spot-dev — BTC Spot Trend-Following

Consolidated repository for **E5_ema21D1** (VTREND E5 + D1 EMA(21) regime filter) — the validated primary BTC spot trend-following algorithm.
Includes research, validation framework, X-series variants (X0-X37), and production readiness evaluation.

## Primary Strategy: E5_ema21D1

- **Strategy**: E5_ema21D1 (4 params: slow_period, trail_mult, vdo_threshold, d1_ema_period)
- **Exit**: Robust ATR trail (Q90-capped TR, Wilder EMA(20)) + EMA cross-down
- **Regime filter**: EMA(21d) on D1 timeframe
- **Default params**: N=120, trail=3.0, vdo_threshold=0.0, d1_ema_period=21
- **Cost model**: 50 bps RT (harsh)
- **Validation (2026-03-09)**: PROMOTE — all 7 gates PASS, PSR=0.9993
  - Harsh: Sharpe 1.432, CAGR 59.96%, MDD 41.57%, 199 trades
  - Full delta +21.64, holdout delta +9.54 vs E0 baseline
  - Wilcoxon WFO p=0.074 (< α=0.1), selection-bias PSR=0.9993
  - **STALE (2026-03-16)**: Multiple framework fixes (WFO overlap, holdout off-by-one,
    Trade.pnl net-of-fees, lookahead scope) require re-validation. See PENDING_RERUN.md.

## E0_ema21D1 (vtrend_ema21_d1) — HOLD (not deployed)

- **Validation (2026-03-09)**: HOLD — PSR=0.8908 < 0.95 threshold
- E0_ema21D1 was previous best (Study #41). After framework reform (Wilcoxon WFO, PSR gate,
  holdout/WFO overlap check), E0_ema21D1 no longer clears selection-bias bar vs E0 baseline.
- E5_ema21D1 dominates on 6/7 dimensions; E0_ema21D1 only leads on WFO win rate (75% vs 62.5%).
- **HOLD ≠ FALLBACK**: E0_ema21D1 has no designated deployment role. Infrastructure-gated
  fallback (LT2+) is a research concept only — see `research/x6/DEPLOYMENT_SPEC_E5_EMA1D21_LT1.yaml`.

Full specification: [VTREND_BLUEPRINT.md](docs/algorithm/VTREND_BLUEPRINT.md)

## Project Structure

```
btc-spot-dev/
├── validate_strategy.py              # CLI entry point for validation
├── data/bars_btcusdt_2016_now_h1_4h_1d.csv  # H4+D1 OHLCV data (2017-08 to 2026-02)
├── data/bars_btcusdt_2017_now_15m.csv       # 15m data (for amt_research)
│
├── v10/                              # Core framework
│   ├── core/                         #   Engine, types, data, metrics, config
│   ├── strategies/                   #   v8_apex, v11_hybrid, buy_and_hold
│   ├── research/                     #   bootstrap, objective, wfo, regime
│   ├── tests/                        #   372 tests (all pass)
│   ├── cli/                          #   backtest, paper, research CLIs
│   ├── exchange/                     #   Order planner, filters, bar clock
│   └── configs/                      #   YAML configs
│
├── strategies/                       # 29 registered strategy variants
│   ├── vtrend/                       #   E0 baseline
│   ├── vtrend_e5_ema21_d1/           #   E5_ema21D1 — PRIMARY (2026-03-09)
│   ├── vtrend_ema21_d1/              #   E0_ema21D1 — HOLD (PSR insufficient)
│   ├── vtrend_e5/                    #   E5 — HOLD (WFO 4/8)
│   ├── vtrend_sm/                    #   State machine — alternative profile
│   ├── latch/                        #   Hysteretic — alternative profile
│   └── ...                           #   + 23 more (see STRATEGY_STATUS_MATRIX.md)
│
├── research/                         # 72 research studies (+ infrastructure)
│   ├── lib/                          #   Shared libraries (vcbb, dsr, effective_dof)
│   ├── results/                      #   Study results + COMPLETE_RESEARCH_REGISTRY.md
│   ├── x0/ .. x37/                   #   X-series study dirs (each self-contained)
│   └── run_all_studies.sh            #   Runner for all studies
│
├── validation/                       # Validation framework (19 suites)
│   └── suites/                       #   backtest, bootstrap, wfo, holdout, etc.
│
├── experiments/                      # Overlay/conditional analysis experiments
│   ├── overlayA/
│   ├── conditional_analysis/
│   └── leave_one_out/
│
├── out/                              # All backtest output artifacts
├── research_reports/                 # Audit & research reports (01-37)
├── legacy/                           # Orphaned files from V10/V11 era
└── docs/                             # Organized documentation (see docs/README.md)
```

## Key Commands

```bash
# Run validation
python validate_strategy.py --strategy v8_apex --config v10/configs/v10_overlayA.yaml

# Run all research studies
cd research && bash run_all_studies.sh

# Run tests
PYTHONPATH=. python -m pytest v10/tests/ -q
```
