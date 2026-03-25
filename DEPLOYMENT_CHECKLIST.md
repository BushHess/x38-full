# Deployment Checklist — E5_ema21D1

**Last updated**: 2026-03-17
**Algorithm**: E5_ema21D1 (robust ATR trail + D1 EMA(21) regime filter)
**Status**: HOLD (2026-03-17, 6/7 gates PASS, WFO robustness FAIL: Wilcoxon p=0.125, underresolved)

---

## KEEP — Proven Components

### Core Algorithm (4 params)

| Component | Parameter | Value | Evidence |
|-----------|-----------|-------|----------|
| EMA crossover entry | `slow_period` | 120 | p=0.0003, plateau 60-144 |
| ATR trail + EMA exit (E5) | `trail_mult` | 3.0 | p=0.0003, Q90-capped robust ATR |
| VDO filter | `vdo_threshold` | 0.0 | 16/16 TS, DOF-corrected p=0.031 |
| D1 EMA regime filter | `d1_ema_period` | 21 | p=1.5e-5, range 15-40d proven |

### Robust ATR Structural Params (frozen, not tunable)

| Param | Value | Note |
|-------|-------|------|
| `ratr_cap_q` | 0.90 | Q90 cap on True Range |
| `ratr_cap_lb` | 100 | Lookback for Q90 calculation |
| `ratr_period` | 20 | Wilder EMA smoothing period |

E5S simplification REJECTED (Sharpe loss 0.088 > 0.02 threshold).

### Regime Monitor V2 (entry prevention overlay)

| Threshold | Value | Action |
|-----------|-------|--------|
| AMBER (6m MDD) | > 45% | Reduce size or pause new entries |
| AMBER (12m MDD) | > 60% | Reduce size or pause new entries |
| RED (6m MDD) | > 55% | Halt new entries |
| RED (12m MDD) | > 70% | Halt new entries |

Code: `monitoring/regime_monitor.py`
Mechanism: entry prevention ONLY (0 forced exits in backtest). Layered defense with EMA(21).

### Operational Parameters

| Parameter | Value |
|-----------|-------|
| Resolution | H4 bars |
| Position sizing | f=0.30 (vol-target 15%) |
| Cost budget (backtest) | 50 bps RT (harsh — deliberately above real-world) |
| Realistic cost (Binance VIP0+BNB) | 20-30 bps RT (X22: skip churn filter at this level) |
| Warmup | 365 days (no_trade mode) |
| Initial capital | $10,000 (configurable) |

### Expected Performance

| Metric | Real Data | Bootstrap (VCBB) |
|--------|-----------|-------------------|
| Sharpe | 1.19 | 0.54 |
| CAGR | 52.6% | 14.2% |
| MDD | 61.4% | 61.0% |
| Trades | 226 | — |
| P(CAGR > 0) | — | 80.3% |
| Avg exposure | 45.2% | — |

### Risk Guards (R1-R4)

| Guard | Config Key | Default | Status |
|-------|-----------|---------|--------|
| Max exposure | `max_total_exposure` | 1.0 | Wired (PaperRunner) |
| Min notional | `min_notional_usdt` | $10 | Wired (PaperRunner) |
| Kill switch | `kill_switch_dd_total` | 0.45 | Wired (PaperRunner) |
| Max daily orders | `max_daily_orders` | 5 | Wired (PaperRunner) |

---

## DROP — Not for Production

| Component | Reason |
|-----------|--------|
| E0_ema21D1 | HOLD — WFO robustness FAIL. PSR demoted to info. |
| X1-X6 (all variants) | REDUNDANT or CONFLICTING with E5_ema21D1 |
| SM (State Machine) | ALT PROFILE — different risk/return, not replacement |
| LATCH (Hysteretic) | ALT PROFILE — different risk/return, not replacement |
| E5S (simplified ATR) | REJECTED — Sharpe loss 0.088 |
| V8 Apex | 40+ params, ZERO value over VTREND 3 params |
| V11-V13 | Legacy, superseded |
| E6, E7, VPULL, VBREAK, etc. | All failed to beat E0 on ALL metrics |
| Regime Monitor V1 | REJECTED — raw ATR structurally broken (71.6% false RED) |
| X23 (exit geometry) | REJECT — Sh -0.229 vs E5, increases churn |
| X24 (trail arming) | REJECT — Sh -0.067 vs E5, never-armed entries |
| X27 Cand01 (breakout) | Lower Sharpe (0.907 vs 1.432), only wins >105 bps cost |
| X28 Cand01 (from-scratch) | Valid (Sh 1.251, 9/9 gates) but < E5_ema21D1 on ALL metrics |
| x37v4 macroHystB | V4_COMPETITIVE (Sh 1.865, MDD 23.9%). Better risk profile but ~10 params, WFO underpowered, yearly recalibration. NOT promoted. |

---

## INFRASTRUCTURE — Needed Before Live

| Item | Status | Location |
|------|--------|----------|
| LiveRunner | **BUILT** (2026-03-09) | `v10/cli/live.py` — 4 modes: soak_orders, soak_notrade, replay, realtime |
| Risk guards (live) | **BUILT** (2026-03-09) | `v10/cli/live.py` RiskGuards class — kill-switch DD, max daily orders, max exposure |
| C4 smoke test | **BUILT** (2026-03-09) | `v10/tests/smoke_c4_live.py` — planner + crash + reconcile |
| C5 testnet validation | **BUILT** (2026-03-09) | `v10/tests/smoke_c5_testnet.py` — E5_ema21D1 replay with real testnet orders |
| Backtest CLI registration | **FIXED** (2026-03-09) | `v10/cli/backtest.py` — E5_ema21D1 now in STRATEGY_REGISTRY |
| Paper CLI registration | **FIXED** (2026-03-09) | `v10/cli/paper.py` — E5_ema21D1 now in STRATEGY_REGISTRY |
| Monitoring dashboard | **BUILT** (2026-03-09) | `v10/cli/monitor.py` — terminal dashboard (account, regime, risk, orders, system) |
| Alert system | **BUILT** (2026-03-09) | `monitoring/alerts.py` — Telegram + webhook + console. Wired into LiveRunner (--alerts) |
| C4 testnet RUN | **PASSED** (2026-03-09) | `out/c4/` — 5 orders, 0 duplicates, crash BEFORE_PERSIST+AFTER_SEND verified, reconcile OK |
| C5 testnet RUN | **PASSED** (2026-03-09) | `out/c5/` — 500 bars → 6 signals → 6 fills, 0 duplicates. Slippage WARN (testnet liquidity) |

---

## DOF Context (statistical confidence)

16 timescales are NOT independent (~4.35 effective per Nyholt M_eff).

| Comparison | Nominal p | Nyholt p | Confidence |
|------------|-----------|----------|------------|
| E5 vs X0 | 1.5e-5 | 0.0625 | 93.8% |
| E5 vs E5S | 1.5e-5 | 0.0312 | 96.9% |

Effect size +0.089 Sharpe, consistent at ALL 16 timescales (min +0.042).

---

## Latency Sensitivity

E5_ema21D1 requires automated execution with ≤4h restart SLA (LT1).
At D1 (4h delay): combined delta -0.186 → PASS. At D2 (8h): -0.396 → FAIL.

- **LT1 (<4h)**: E5_ema21D1 (this checklist)
- **LT2 (4-16h)**: Fallback to E0_ema21D1 — lower delay fragility
- **LT3 (>16h)**: SM only, or flatten+halt

Fallback trigger: 2 consecutive missed H4 bars → switch to E0_ema21D1.
Recovery: 1 successful bar → switch back.

**Full details**: [`LATENCY_TIER_DEPLOYMENT_GUIDE.md`](docs/algorithm/LATENCY_TIER_DEPLOYMENT_GUIDE.md)

---

## Key Files

| Purpose | Path |
|---------|------|
| Strategy code | `strategies/vtrend_e5_ema21_d1/strategy.py` |
| Config | `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml` |
| Regime monitor | `monitoring/regime_monitor.py` |
| Validation results | `results/full_eval_e5_ema21d1/` |
| Prod readiness research | `research/prod_readiness_e5_ema1d21/` (E5_ema21D1, legacy dir name) |
| Status matrix | `STRATEGY_STATUS_MATRIX.md` |
| Latency tier guide | `docs/algorithm/LATENCY_TIER_DEPLOYMENT_GUIDE.md` |
| Blueprint | `docs/algorithm/VTREND_BLUEPRINT.md` (Section 7 SUPERSEDED) |

---

## Cross-Reference Rule

**Every research output MUST be indexed in at least one of:**
1. `STRATEGY_STATUS_MATRIX.md` (verdicts and key findings)
2. `MEMORY.md` (operational values and parameters)
3. This checklist (if deployment-relevant)

If a study produces operational parameters (thresholds, monitor values, rejection criteria), it MUST appear here.
