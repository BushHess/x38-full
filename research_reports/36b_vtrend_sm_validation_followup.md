# Report 36b — VTREND-SM Validation Pipeline Follow-up

**Date**: 2026-03-04
**Scope**: Unblock and execute the unified validation pipeline for VTREND-SM (candidate) vs VTREND E0 (baseline)
**Authority**: Repo state (ground truth) > Report 36 > Report 35 > Report 34c

---

## 1. Blocker Verification (Step A)

End-to-end code trace through the validation pipeline:

```
validate_strategy.py
  → validation/cli.py::main()
    → ValidationConfig(strategy_name, baseline_name, config_path, baseline_config_path, ...)
      → ValidationRunner.run()
        → load_config(config_path)         → LiveConfig  [uses v10/core/config.py]
        → load_config(baseline_config_path) → LiveConfig
        → _build_config_obj(live.strategy.name, params)  [uses validation/strategy_factory.py]
        → make_factory(live_config)                      [uses validation/strategy_factory.py]
        → BacktestEngine(feed, strategy=factory(), ...)  [standard engine]
```

### 1.1 Confirmed Blockers

| # | Blocker | Location | Failure Mode |
|---|---------|----------|--------------|
| 1 | `"vtrend"` NOT in `validation/strategy_factory.py::STRATEGY_REGISTRY` | runner.py L149 | `ValueError("Unknown strategy: 'vtrend'")` when loading baseline |
| 2 | No YAML config for `vtrend_sm` | CLI requires `--config` path | FileNotFoundError |

### 1.2 Non-Blockers (Verified)

| Component | Status | Evidence |
|-----------|--------|----------|
| `v10/core/config.py` `_KNOWN_STRATEGIES` | `"vtrend"` present (L42) | YAML loading works for both strategies |
| `v10/core/config.py` `_VTREND_FIELDS` / `_VTREND_SM_FIELDS` | Present (L34-35) | Strategy param validation works |
| `v10/core/config.py` `validate_config()` | Both branches exist (L216-223) | Config validation works |
| `v10/core/config.py` `_unknown_yaml_keys()` | Both in `strategy_fields_by_name` (L155-156) | Unknown key detection works |
| `BacktestEngine` | Generic, no strategy-specific behavior | Instantiation via `factory()` |
| Cost scenarios | "smart", "base", "harsh" all in `v10/core/types.py::SCENARIOS` | Standard |
| `v10/cli/backtest.py` | NOT used by validation pipeline | Separate CLI path |
| `v10/research/candidates.py` | NOT used by validation pipeline | Separate research path |

### 1.3 Report 36 Claim Audit

Report 36 §7.1 stated:
> "YAML config file — MISSING — no configs/vtrend_sm/ directory exists"

Report 36 §7.2 stated:
> "The pipeline infrastructure (registration, factory, runner) is ready. Only the YAML config file is missing."

**Correction**: Report 36 was partially wrong. TWO blockers existed:
1. Missing YAML config (as stated)
2. Missing baseline registration in `validation/strategy_factory.py` (not mentioned in Report 36)

Report 36 §7.1 showed `validation/strategy_factory.py STRATEGY_REGISTRY` as "Registered" for `vtrend_sm` — this was correct for the CANDIDATE. But the BASELINE (`vtrend` E0) was NOT registered, which was not checked.

---

## 2. Fixes Applied (Step B + C)

### 2.1 `validation/strategy_factory.py` — Add "vtrend" to STRATEGY_REGISTRY

**Change**: Added import and registry entry for VTrendStrategy/VTrendConfig.

```python
# Added import:
from strategies.vtrend.strategy import (
    VTrendConfig,
    VTrendStrategy,
)

# Added to STRATEGY_REGISTRY:
    "vtrend": (VTrendStrategy, VTrendConfig),
```

**Verification**: `python -c "from validation.strategy_factory import STRATEGY_REGISTRY; print(sorted(STRATEGY_REGISTRY.keys()))"`
→ `['buy_and_hold', 'v11_hybrid', 'v12_emdd_ref_fix', 'v13_add_throttle', 'v8_apex', 'vtrend', 'vtrend_sm']`

### 2.2 `configs/vtrend_sm/vtrend_sm_default.yaml` — New File

```yaml
engine:
  symbol: BTCUSDT
  timeframe_h4: 4h
  timeframe_d1: 1d
  warmup_days: 365
  warmup_mode: no_trade
  scenario_eval: base
  initial_cash: 10000.0

strategy:
  name: vtrend_sm
  slow_period: 120
  atr_mult: 3.0
  target_vol: 0.15

risk:
  max_total_exposure: 1.0
  min_notional_usdt: 10
  kill_switch_dd_total: 0.45
  max_daily_orders: 5
```

**Design notes**:
- Only 3 non-default strategy params specified (slow_period, atr_mult, target_vol) — matches Report 35 defaults
- Engine/risk sections match E0 baseline config (`configs/vtrend/vtrend_default.yaml`)
- Follows LiveConfig schema exactly

### 2.3 End-to-End Verification

```
YAML → load_config() → LiveConfig → _build_config_obj() → make_factory() → strategy instance
```

Both candidate and baseline paths verified:
- Candidate: `vtrend_sm_default.yaml` → `VTrendSMConfig(slow_period=120, atr_mult=3.0, target_vol=0.15)` → `VTrendSMStrategy`
- Baseline: `vtrend_default.yaml` → `VTrendConfig(slow_period=120.0, trail_mult=3.0, vdo_threshold=0.0)` → `VTrendStrategy`

---

## 3. Changes NOT Made

| Item | Reason |
|------|--------|
| Strategy logic (`strategies/vtrend_sm/strategy.py`) | Prompt 7 rule: no strategy logic changes |
| Strategy logic (`strategies/vtrend/strategy.py`) | Prompt 7 rule: no baseline strategy changes |
| Engine / execution / metrics | Prompt 7 rule: no engine changes |
| `v10/cli/backtest.py` | Not used by validation pipeline |
| `v10/research/candidates.py` | Not used by validation pipeline |

---

## 4. Validation Pipeline Execution (Step D)

### 4.1 Command

```bash
python validate_strategy.py \
  --strategy vtrend_sm \
  --baseline vtrend \
  --config configs/vtrend_sm/vtrend_sm_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out/validation_vtrend_sm_full \
  --suite full \
  --force \
  --dataset data/bars_btcusdt_2016_now_h1_4h_1d.csv \
  --scenarios smart,base,harsh \
  --bootstrap 2000 \
  --seed 1337
```

### 4.2 Suite Results

| Suite | Status | Detail |
|-------|--------|--------|
| lookahead | **PASS** | 27/27 tests pass, 0 violations |
| data_integrity | **PASS** | 0 issues, all H4/D1 intervals clean |
| backtest | **FAIL** | harsh score delta = −67.63 (threshold: −0.20) |
| cost_sweep | **PASS** | SM viable at all cost levels 0–100 bps |
| invariants | **PASS** | 0 violations |
| churn_metrics | **PASS** | SM fee drag 2.5% (base), E0 fee drag 4.4% |
| regime | **INFO** | 6-regime decomposition complete |
| wfo | **PASS** | win_rate=0.625 ≥ 0.600, 8 windows (6 with power) |
| bootstrap | **INFO** | harsh p=0.759 (SM better), CI=[−0.297, +0.628] |
| subsampling | **INFO** | p(SM>E0 growth)=0.031 (all block sizes reject H0) |
| holdout | **FAIL** | harsh score delta = −33.61 (threshold: −0.20) |
| selection_bias | **PASS** | DSR=1.0 across N=27..700 trials |

### 4.3 Verdict

```
VERDICT: ERROR (exit code 3)
```

**Reasons**:
1. Candidate harsh score delta too low (−67.63)
2. Holdout harsh score delta too low (−33.61)
3. Unused strategy config fields detected

### 4.4 Verdict Decomposition

**Reason 1–2 (score delta FAIL)**: Expected and correct. The validation scoring function (`v10/research/objective.py`) heavily weights return_term (CAGR-proportional). SM's CAGR is 3.6× lower than E0, producing a massive score gap. This is an inherent property of comparing a vol-targeted fractional strategy (~10% avg exposure) against a binary all-in strategy (~47% avg exposure). The scoring function does not adjust for exposure differences.

**Reason 3 (unused config fields)**: FALSE POSITIVE. The ConfigProxy/AccessTracker pattern used by the validation pipeline wraps the config object and intercepts `__getattr__` calls to track field usage. VTrendSMStrategy calls `self._config.resolved()` which uses `dataclasses.asdict()` internally — this accesses fields through `__dict__`, bypassing the proxy's `__getattr__`. Result: all 16 VTrendSMConfig fields are marked "unused" even though they are all consumed by `resolved()` → `on_init()` → `on_bar()`.

Note: VTrendStrategy (baseline) passes the unused-fields check because it accesses `self._c.slow_period`, `self._c.trail_mult` etc. directly through attribute access, which the proxy correctly intercepts.

This is an architectural mismatch between ConfigProxy and the `resolved()` pattern, not a defect in VTrendSMStrategy.

---

## 5. Full Backtest Metrics

### 5.1 Core Metrics (validation date range: 2019-01-01 to 2026-02-20)

| Metric | SM smart | SM base | SM harsh | E0 smart | E0 base | E0 harsh |
|--------|----------|---------|----------|----------|---------|----------|
| **CAGR %** | 17.49 | 16.77 | 16.00 | 67.95 | 60.01 | 52.04 |
| **Sharpe** | 1.5648 | 1.5070 | 1.4437 | 1.5205 | 1.3964 | 1.2653 |
| **Sortino** | 1.3551 | 1.3073 | 1.2540 | 1.4239 | 1.3133 | 1.1952 |
| **MDD %** | 13.52 | 14.23 | 15.09 | 38.51 | 40.04 | 41.61 |
| **Calmar** | 1.2935 | 1.1787 | 1.0599 | 1.7646 | 1.4989 | 1.2507 |
| Trades | 65 | 65 | 65 | 192 | 192 | 192 |
| Win Rate % | 40.0 | 40.0 | 40.0 | 42.19 | 41.67 | 40.10 |
| Avg Exposure | 0.1177 | 0.1177 | 0.1177 | 0.4682 | 0.4682 | 0.4682 |
| Fee Drag %/yr | 0.25 | 0.72 | 1.07 | 1.83 | 5.23 | 7.84 |
| Score | 62.42 | 59.24 | 55.70 | 167.90 | 145.71 | 123.32 |

### 5.2 Score Breakdown (harsh scenario)

| Component | SM | E0 | Delta |
|-----------|-----|-----|-------|
| return_term | 40.00 | 130.10 | −90.10 |
| mdd_penalty | −9.05 | −24.97 | +15.91 |
| sharpe_term | 11.55 | 10.12 | +1.43 |
| profit_factor_term | 8.20 | 3.07 | +5.14 |
| trade_count_term | 5.00 | 5.00 | 0.00 |
| **total_score** | **55.70** | **123.32** | **−67.63** |

SM wins on sharpe_term (+1.43), profit_factor_term (+5.14), and mdd_penalty (+15.91). E0 dominates on return_term (+90.10). The scoring function's CAGR weight makes it impossible for SM to outscore E0.

### 5.3 Holdout Metrics (last 20%)

| Metric | SM harsh | E0 harsh |
|--------|----------|----------|
| CAGR % | 7.97 | 24.99 |
| Sharpe | 0.8807 | 0.9601 |
| MDD % | 6.10 | 19.13 |
| Trades | 15 | 35 |
| Score | 31.81 | 65.42 |

---

## 6. Walk-Forward Optimization (WFO)

8 rolling windows (24-month train, 6-month test):

| Window | Period | SM Score | E0 Score | Delta | SM Trades | Winner |
|--------|--------|----------|----------|-------|-----------|--------|
| 0 | 2022-01 → 2022-07 | −7.81 | −43.28 | +35.47 | 2* | SM |
| 1 | 2022-07 → 2023-01 | −36.23 | −104.20 | +67.97 | 5 | SM |
| 2 | 2023-01 → 2023-07 | 169.57 | 35.42 | +134.15 | 3* | SM |
| 3 | 2023-07 → 2024-01 | 27.86 | 225.49 | −197.62 | 5 | E0 |
| 4 | 2024-01 → 2024-07 | 78.69 | 46.48 | +32.20 | 5 | SM |
| 5 | 2024-07 → 2025-01 | 23.74 | 274.31 | −250.56 | 8 | E0 |
| 6 | 2025-01 → 2025-07 | 17.47 | 30.47 | −13.00 | 5 | E0 |
| 7 | 2025-07 → 2026-01 | −1.00 | −30.71 | +29.71 | 5 | SM |

(*) = low trade window (< 5 trades, excluded from power analysis)

**Summary**:
- All valid: 5/8 SM wins (62.5%) — **PASS** (threshold 60%)
- Power only: 3/6 SM wins (50.0%) — near threshold
- SM excels in drawdown periods (W0, W1, W7); E0 excels in strong trends (W3, W5)
- Worst SM loss: −250.56 (W5, Jul-Dec 2024 bull run where E0 captured +101.88% CAGR)

---

## 7. Bootstrap Analysis

Paired block bootstrap (n=2000, block sizes 10/20/40) on harsh scenario:

| Metric | Block=10 | Block=20 | Block=40 |
|--------|----------|----------|----------|
| p(SM Sharpe > E0 Sharpe) | 0.759 | 0.740 | 0.724 |
| CI lower | −0.297 | −0.327 | −0.356 |
| CI upper | +0.628 | +0.662 | +0.687 |

SM has higher Sharpe in 72–76% of bootstraps. Consistent with Report 36's PairDiagnostic (p_E0>SM = 0.214, i.e. p_SM>E0 = 0.786).

---

## 8. Subsampling Analysis

Paired block subsampling (all overlapping blocks) on harsh scenario:

| Block Size | p(SM growth > E0 growth) | CI lower | CI upper |
|-----------|--------------------------|----------|----------|
| 10 | 0.031 | −0.411 | +0.030 |
| 20 | 0.037 | −0.406 | +0.048 |
| 40 | 0.039 | −0.398 | +0.042 |

E0 geometric growth significantly exceeds SM at p < 0.04 across all block sizes. This is consistent with the 3.6× CAGR gap.

---

## 9. Cost Sweep

| Cost (bps RT) | SM CAGR | E0 CAGR | SM Score | E0 Score | SM Wins Score? |
|--------------|---------|---------|----------|----------|---------------|
| 0 | 11.73 | 42.31 | 45.12 | 111.01 | No |
| 10 | 11.25 | 38.33 | 43.04 | 98.93 | No |
| 25 | 10.54 | 32.57 | 39.96 | 81.40 | No |
| 50 | 9.36 | 23.49 | 34.93 | 53.67 | No |
| 75 | 8.19 | 15.04 | 30.01 | 27.72 | **Yes** |
| 100 | 7.04 | 7.17 | 25.09 | 3.44 | **Yes** |

SM breaks even on score at ~70 bps RT and dominates above 75 bps. SM CAGR degradation: 11.73% → 7.04% (−4.69pp over 100 bps). E0 CAGR degradation: 42.31% → 7.17% (−35.14pp over 100 bps). SM's low turnover (7.2×/yr vs 52.3×/yr) provides extreme cost resilience.

---

## 10. Regime Decomposition

| Regime | SM Return % | E0 Return % | SM MDD % | E0 MDD % | SM Sharpe | E0 Sharpe |
|--------|------------|------------|----------|----------|-----------|-----------|
| SHOCK | −6.14 | −33.57 | 13.01 | 35.22 | −1.62 | −2.68 |
| BEAR | 39.85 | 109.14 | 8.94 | 32.57 | 1.84 | 1.51 |
| CHOP | −1.63 | 32.30 | 7.60 | 30.39 | −0.32 | 1.58 |
| TOPPING | 0.67 | −4.58 | 4.57 | 30.12 | 0.81 | −0.87 |
| BULL | 118.28 | 846.54 | 10.80 | 40.61 | 2.05 | 1.71 |
| NEUTRAL | 1.68 | 19.97 | 6.37 | 32.72 | 0.27 | 0.81 |

**Observations**:
- SM MDD capped at 13.01% across ALL regimes (E0 ranges 15–41%)
- SM Sharpe > E0 Sharpe in 3/6 regimes: SHOCK, BEAR, BULL
- E0 Sharpe > SM Sharpe in 3/6 regimes: CHOP, TOPPING (E0 negative), NEUTRAL
- SM loses most ground in CHOP regime (−1.63% vs +32.30%) — low trend environment where vol-targeted sizing produces near-zero exposure while E0's binary position captures mean-reversion

---

## 11. Selection Bias

Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014):

| N trials | DSR | Expected max SR | Pass |
|----------|-----|----------------|------|
| 27 | 1.0 | 0.166 | Yes |
| 54 | 1.0 | 0.188 | Yes |
| 100 | 1.0 | 0.207 | Yes |
| 200 | 1.0 | 0.226 | Yes |
| 500 | 1.0 | 0.249 | Yes |
| 700 | 1.0 | 0.257 | Yes |

SM's observed Sharpe (1.44 harsh) vastly exceeds the expected maximum Sharpe from random selection at all trial counts. DSR = 1.0 uniformly.

---

## 12. Cross-Reference with Report 36 (Step E)

### 12.1 Date Range Difference

Report 36 used full data range (no start/end filter → ~18,662 H4 bars from 2017-08).
Validation pipeline uses `start=2019-01-01, end=2026-02-20` (~15,648 H4 bars, CLI defaults).

This systematically changes all metrics because the 2017-08 to 2018-12 period includes the crypto bubble peak and crash.

### 12.2 Metric Comparison

| Metric | Report 36 (full) | Validation (2019+) | Direction Consistent? |
|--------|-----------------|-------------------|----------------------|
| SM base CAGR | 14.80% | 16.77% | Yes (shorter period, no crash) |
| SM base Sharpe | 1.3895 | 1.5070 | Yes |
| SM base MDD | 14.23% | 14.23% | Exact match (MDD from same period) |
| SM base trades | 76 | 65 | Yes (fewer bars → fewer trades) |
| E0 base CAGR | 52.59% | 60.01% | Yes |
| E0 base Sharpe | 1.1944 | 1.3964 | Yes |
| E0 base MDD | 61.37% | 40.04% | Yes (2018 crash excluded) |
| E0 base trades | 226 | 192 | Yes |

### 12.3 Directional Consistency

All key relationships hold across both date ranges:
- SM Sharpe > E0 Sharpe (all scenarios): **Confirmed**
- E0 CAGR >> SM CAGR (~3.6×): **Confirmed** (3.58× in validation vs 3.55× in Report 36)
- SM MDD << E0 MDD: **Confirmed** (2.8× in validation vs 4.3× in Report 36)
- SM higher profit factor: **Confirmed** (2.64 vs 1.61 harsh in validation)

### 12.4 Report 36 Validation Pipeline Prediction

Report 36 §7.3 predicted the pipeline would provide WFO, cost sweep, holdout, bootstrap, subsampling, DSR, data integrity, churn metrics. All were delivered. Report 36 §7.2 identified one blocker (YAML config) but missed the second (baseline factory registration).

---

## 13. Unused Config Fields Issue

### 13.1 Root Cause

The `ConfigProxy` wrapper (validation/config_audit.py) intercepts `__getattr__` calls to track which config fields are accessed at runtime. VTrendSMStrategy reads config via:

```python
self._config = config  # ConfigProxy wrapping VTrendSMConfig
self._r = self._config.resolved()  # single __getattr__ call to "resolved"
```

`resolved()` internally calls `dataclasses.asdict(self)` which accesses fields through `__dict__`, bypassing `__getattr__`. All subsequent accesses use `self._r["field_name"]` (dict), never `self._config.field_name` (proxy).

Result: 16/16 VTrendSMConfig fields marked "unused". The baseline (VTrendStrategy) passes because it accesses `self._c.slow_period` etc. directly through attribute access.

### 13.2 Assessment

This is an architectural mismatch between ConfigProxy and the `resolved()` pattern. Not a defect in VTrendSMStrategy. No code change made (per Prompt 7 rules).

Possible future fixes (not implemented):
- Add field access tracking inside `resolved()`
- Allowlist known patterns in the audit system
- Have strategies access config fields directly instead of through resolved()

---

## 14. Summary

### 14.1 Files Created

| File | Purpose |
|------|---------|
| `configs/vtrend_sm/vtrend_sm_default.yaml` | SM YAML config for validation pipeline |

### 14.2 Files Modified

| File | Change |
|------|--------|
| `validation/strategy_factory.py` | Added "vtrend" (VTrendStrategy, VTrendConfig) to STRATEGY_REGISTRY |

### 14.3 Completion Conditions

| # | Condition | Status |
|---|-----------|--------|
| 1 | Pipeline runs end-to-end without crash | **DONE** — Exit code 3 (ERROR verdict, not crash) |
| 2 | All suites execute (no import failures) | **DONE** — 12/12 suites completed |
| 3 | Results cross-referenced with Report 36 | **DONE** — §12, directionally consistent |
| 4 | Blockers verified directly (not repeated from claims) | **DONE** — §1, found additional blocker Report 36 missed |
| 5 | Code changes minimal and documented | **DONE** — 1 file modified (3 lines), 1 file created |
| 6 | Report 36b written | **DONE** — this document |

### 14.4 Verdict Interpretation

The `ERROR(3)` verdict reflects three factors:
1. **Score delta**: SM cannot outscore E0 under the current scoring function because CAGR weight dominates. This is a scoring-function property, not a strategy defect. SM trades ~3.6× less return for ~4.3× less risk.
2. **Holdout delta**: Same direction, same cause.
3. **Unused config fields**: False positive from ConfigProxy/resolved() incompatibility.

The validation pipeline confirms what Report 36 found through independent analysis: SM and E0 are materially different strategies with different risk/return profiles. SM has higher Sharpe, lower CAGR, dramatically lower MDD, and extreme cost resilience (breaks even on score at ~70 bps, dominates above 75 bps).

---

## 15. Output Artifacts

All validation output at: `out/validation_vtrend_sm_full/`

```
out/validation_vtrend_sm_full/
├── configs/
│   ├── candidate_vtrend_sm_default.yaml
│   └── baseline_vtrend_default.yaml
├── logs/
│   └── run.log
├── reports/
│   ├── audit_effective_config.md
│   ├── audit_score_decomposition.md
│   ├── audit_wfo_invalid_windows.md
│   ├── decision.json
│   ├── discovered_tests.md
│   ├── quality_checks.md
│   └── validation_report.md
├── results/
│   ├── bootstrap_paired_test.csv
│   ├── churn_metrics.csv
│   ├── config_unused_fields.json
│   ├── config_used_fields.json
│   ├── cost_sweep.csv
│   ├── data_integrity.json
│   ├── data_integrity_issues.csv
│   ├── effective_config_baseline.json
│   ├── effective_config_candidate.json
│   ├── final_holdout_metrics.csv
│   ├── full_backtest_detail.json
│   ├── full_backtest_summary.csv
│   ├── invariant_violations.csv
│   ├── lookahead_check.txt
│   ├── regime_decomposition.csv
│   ├── score_breakdown_full.csv
│   ├── score_breakdown_holdout.csv
│   ├── selection_bias.json
│   ├── subsampling_paired_test.csv
│   ├── wfo_per_round_metrics.csv
│   └── wfo_summary.json
├── index.txt
└── run_meta.json
```
