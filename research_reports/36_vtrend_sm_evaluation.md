# Report 36: VTREND-SM Post-Integration Evaluation

> **Phase**: 6 — Evaluation (repo-state first, no code changes)
> **Date**: 2026-03-04
> **Status**: Complete
> **Prerequisite reports**: 34 (survey), 34b (pre-integration audit), 34c (design contract), 35 (integration)

---

## 1. Audit Scope

Evaluate VTREND-SM as implemented in `btc-spot-dev` against the VTREND E0 baseline.
This report is **evaluation and reporting only** — no source code, test, or framework
changes were made.

Deliverables:
- Implementation reality check (8 mandatory audit items)
- Baseline naming resolution
- PairDiagnostic harness output
- Side-by-side metrics across 3 cost scenarios
- Regime decomposition
- Data-only observations (no promote/reject)

---

## 2. Authority Order Applied

| Rank | Source | Role |
|------|--------|------|
| 1 | **Repo state** (source code, test code, engine) | Ground truth |
| 2 | Report 35 (integration report) | Claims to verify |
| 3 | Report 34c (design contract) | Canonical spec |
| 4 | Report 34b (pre-integration audit) | Deviation catalog |
| 5 | Report 34 (survey) | Background context |
| 6 | Latch source | Reference only (not authoritative) |

---

## 3. Implementation Reality Check

### 3.1 Summary Table

| # | Item | Implementation (repo state) | Test Coverage | Report/Docstring Claims | Verdict |
|---|------|----------------------------|---------------|------------------------|---------|
| 1 | **Entry guard weight>0.0** | `strategy.py:331` — `if weight > 0.0: self._active = True` | T9 + D2 canonical (3 tests) | 34c D2: canonical adaptation; 35 §6 I4: PASS | **COVERED** |
| 2 | **Rebalance gating location** | `strategy.py:354-355` — strategy-side gating in `on_bar()` | T15-T16 (2 tests) | 34b §3.5: MISMATCH (source: execution engine); 34c D3: framework adaptation; 35 §6 I12: PASS | **COVERED** |
| 3 | **Rebalance comparison basis** | `strategy.py:354` — `abs(new_weight - state.exposure)`, where `state.exposure` is computed at **bar close** price | T15-T16 use synthetic bars where close ≈ open — do NOT exercise close-vs-open divergence | 34b §3.5: MISMATCH (source: actual weight at bar open); 34c D4: noted "rare boundary-case divergence"; 35 §5.4: "zero divergence observed" with defaults | **DOC_DRIFT** — basis difference acknowledged but not tested. T15-T16 don't exercise the divergence path. |
| 4 | **Zero-crossing semantics** | Implicit via separate entry/exit code paths. Entry → weight>0. Exit → weight=0. No explicit `crossing_zero` variable. | T9 (entry), T11 (floor exit), T12 (regime exit) — all test flat↔long transitions | 34b §3.5: SEMANTIC_MATCH | **COVERED** |
| 5 | **Engine integration test reality** | T20 `test_smoke_test_with_synthetic_data` (`test_vtrend_sm.py:690-714`): imports `BacktestEngine` but **does NOT instantiate it**. Calls `strategy.on_init()` + `strategy.on_bar()` loop only. | Strategy interface tested; engine integration NOT tested | 35 §3.1: "T20: Engine integration smoke test — PASS"; test docstring: "BacktestEngine + VTrendSMStrategy runs without crash" — **factually incorrect** | **TEST_LABEL_DRIFT** — test label and report claim engine integration but code only exercises strategy interface. |
| 6 | **VDO coverage reality** | `_vdo()` at `strategy.py:129-147`. Two paths: taker (lines 137-140) and OHLC proxy (lines 142-145). | `TestVDOFilter` (1 test): behavioral — filter blocks entry. No numerical `_vdo()` unit test. OHLC proxy path NOT tested. | 34b §3.2: taker EXACT_MATCH, OHLC proxy MISMATCH (source has no proxy); 35 §3.1: T18 PASS | **TEST_COVERAGE_GAP** — VDO taker arithmetic NOT unit-tested. OHLC proxy NOT tested. Default `use_vdo_filter=False` means VDO rarely exercised. |
| 7 | **Registration reality** | (a) `v10/core/config.py`: `"vtrend_sm"` in `_KNOWN_STRATEGIES`, `_VTREND_SM_FIELDS`, validate_config branch. (b) `v10/research/candidates.py`: load_candidates + build_strategy branches. (c) `validation/strategy_factory.py`: `"vtrend_sm": (VTrendSMStrategy, VTrendSMConfig)`. (d) `v10/cli/backtest.py`: `"vtrend_sm": VTrendSMStrategy`. | 5 registration tests pass (35 §3.1) | 35 §2.2: 4 files modified | **FULLY_REGISTERED** — all 4 integration points, tested. |
| 8 | **nav_mid reality** | `metrics.py:48` — `navs = np.array([e.nav_mid for e in equity])`. All Sharpe/CAGR/MDD computed from nav_mid. `engine.py:161` — `nav_mid=pf.nav(mid)` where `mid = bar.close`. `execution.py:86` — `nav(mid) = cash + btc_qty * mid`. | Metrics tests use nav_mid. MDD also computed for nav_liq (supplementary). | 35: doesn't explicitly distinguish nav_mid vs nav_liq basis | **CORRECT** — nav_mid is primary metric basis. nav_liq is supplementary (max_drawdown_liq_pct). |

### 3.2 Findings Summary

- **2 issues found**:
  - Item 5 (TEST_LABEL_DRIFT): T20 claims engine integration but only tests strategy interface
  - Item 6 (TEST_COVERAGE_GAP): `_vdo()` numerical correctness not unit-tested; OHLC proxy path untested
- **1 documentation gap**:
  - Item 3 (DOC_DRIFT): Rebalance close-vs-open basis difference acknowledged in reports but not specifically tested
- **5 items fully covered**: Items 1, 2, 4, 7, 8

---

## 4. Baseline Naming Resolution

| Label used in Report 36 | Strategy module | Class | Strategy ID (`.name()`) | Config class |
|--------------------------|-----------------|-------|------------------------|--------------|
| **VTREND_E0** | `strategies/vtrend/strategy.py` | `VTrendStrategy` | `"vtrend"` | `VTrendConfig` |
| **VTREND_SM** | `strategies/vtrend_sm/strategy.py` | `VTrendSMStrategy` | `"vtrend_sm"` | `VTrendSMConfig` |

### E0 Registration Status

| Integration Point | Registered? |
|-------------------|------------|
| `v10/core/config.py` (`_KNOWN_STRATEGIES`) | YES — as `"vtrend"` |
| `v10/research/candidates.py` | **NO** |
| `v10/cli/backtest.py` (`STRATEGY_REGISTRY`) | **NO** |
| `validation/strategy_factory.py` (`STRATEGY_REGISTRY`) | **NO** |

E0 is recognized in config validation but NOT registered in CLI, validation, or candidate search. E0 backtests were run via direct Python instantiation.

### Naming Note

"VTREND E0" in MEMORY.md refers to the algorithm with EMA(21d) D1 regime filter. The `strategies/vtrend/strategy.py` implementation does NOT include a D1 regime filter — it is pure H4-only (EMA crossover + VDO + ATR trail). The E0 results in this report reflect the **as-implemented** strategy without D1 regime overlay.

---

## 5. Evaluation Setup

### 5.1 Cost Scenarios

| Label | CostConfig | spread_bps | slippage_bps | taker_fee_pct | RT bps |
|-------|-----------|-----------|-------------|--------------|--------|
| base | `SCENARIOS['base']` | 5.0 | 3.0 | 0.10 | 31 |
| harsh | `SCENARIOS['harsh']` | 10.0 | 5.0 | 0.15 | 50 |
| extreme | `CostConfig(14.0, 8.0, 0.15)` | 14.0 | 8.0 | 0.15 | 60 |

### 5.2 Data and Parameters

- **Data**: `data/bars_btcusdt_2016_now_h1_4h_1d.csv` (2017-08 to 2026-02)
- **Range**: full data, no start/end filter (matching CLI defaults)
- **Warmup**: 365 days, mode=no_trade
- **Initial cash**: $10,000
- **Equity bars**: 18,662 (identical for both strategies)
- **Years**: 8.52
- **E0 config**: `VTrendConfig()` defaults (slow=120.0, trail=3.0, vdo_threshold=0.0)
- **SM config**: `VTrendSMConfig()` defaults (slow=120, target_vol=0.15, atr_mult=3.0)

### 5.3 Metric Definitions

All metrics computed by `v10/core/metrics.py`:
- **CAGR**: `(final_nav / report_start_nav)^(1/years) - 1` using nav_mid
- **Sharpe**: `mean(returns) / std(returns, ddof=0) * sqrt(2190)` using nav_mid
- **MDD**: `max(1 - nav / cummax(nav)) * 100` using nav_mid
- **Calmar**: `CAGR / MDD`
- **Sortino**: `mean(returns) / std(downside_returns, ddof=0) * sqrt(2190)` using nav_mid

---

## 6. PairDiagnostic Output

### 6.1 Machine Diagnostic

Harness: `research/lib/pair_diagnostic.py::run_pair_diagnostic()`
Pair: VTREND_E0 (equity_a) vs VTREND_SM (equity_b)
Scenario: base (31 bps RT)

**Classification**: `materially_different`
- near_equal_1bp_rate = 51.9%
- return_correlation = 0.729
- subsampling_reliable = True

**Pair Profile** (n_bars = 18,661):

| Metric | Value |
|--------|-------|
| equal_rate_tol (machine ε) | 51.0% |
| near_equal_1bp | 51.9% |
| near_equal_10bp | 59.7% |
| same_direction_rate | 82.8% |
| return_correlation | 0.729 |
| exposure_agreement | 83.2% |

**Bootstrap (Sharpe)**: p(E0>SM) = 0.214, CI = [−0.655, +0.290], width = 0.945, observed Δ = −0.195
**Bootstrap (geo growth)**: p(E0>SM) = 0.989, CI = [+0.000017, +0.000238]
**Subsampling (geo growth)**: p(E0>SM) = 0.967, CI = [−0.030, +0.705], support = 0.00
**Consensus**: gap = 2.2pp — OK

**DSR (advisory)**:

| Trials | E0 p-value | SM p-value |
|--------|-----------|-----------|
| 27 | 0.93 | 0.98 |
| 54 | 0.88 | 0.96 |
| 100 | 0.83 | 0.94 |
| 200 | 0.76 | 0.91 |
| 500 | 0.67 | 0.85 |
| 700 | 0.63 | 0.82 |

**Caveats**:
- Subsampling support=0.00 (expected for available effect sizes)

**Suggested route**: `inconclusive_default` — materially_different pair, diagnostics consistent, power limitation applies

### 6.2 Interpretation Notes (data-only)

- Classification `materially_different` is expected: SM uses fractional vol-targeted sizing (~10% avg exposure) while E0 uses binary all-in (~45% avg exposure).
- Bootstrap Sharpe p=0.214 means SM has non-significantly higher Sharpe (observed Δ = −0.195 favors SM). CI width 0.945 indicates low discriminative power for Sharpe.
- Bootstrap geo-growth p=0.989 overwhelmingly favors E0 — E0 produces higher absolute geometric returns.
- The Sharpe/geo-growth divergence (p=0.214 vs p=0.989) reflects that SM reduces both returns AND volatility, improving risk-adjusted performance while sacrificing absolute performance.
- DSR p-values are high for both strategies (>0.63 at all trial counts), consistent with trend-following strategies requiring large trial counts to distinguish from random.
- Subsampling support=0.00: all block sizes agree on direction but none meet significance threshold. Expected for materially_different pairs with high absolute-return divergence but ambiguous risk-adjusted comparison.

---

## 7. Validation Pipeline

### 7.1 Infrastructure Status

| Component | vtrend_sm Status |
|-----------|-----------------|
| `validation/strategy_factory.py` STRATEGY_REGISTRY | **Registered** |
| `validation/cli.py` CLI parsing | Compatible (strategy name accepted) |
| `validation/runner.py` execution | Compatible (uses factory) |
| YAML config file | **MISSING** — no `configs/vtrend_sm/` directory exists |

### 7.2 Execution Status

**BLOCKED**: The validation pipeline (`validate_strategy.py`) requires `--config` and `--baseline-config` pointing to YAML config files conforming to the `LiveConfig` schema (engine + strategy + risk sections). No such file exists for `vtrend_sm`.

The existing `configs/vtrend/vtrend_default.yaml` is for E0, not SM.

The pipeline infrastructure (registration, factory, runner) is ready. Only the YAML config file is missing. This is not a code defect — Report 35 §2 noted "No YAML config file creation — No `configs/` directory exists in repo; not part of current workflow." A `configs/vtrend_sm/` directory would need to be created to run the full validation pipeline.

### 7.3 What the Pipeline Would Provide (if run)

- Walk-forward optimization (WFO) with rolling/fixed windows
- Cost sweep across 0–100 bps
- Holdout period testing
- Bootstrap + subsampling pair comparison vs baseline
- Data integrity checks
- Selection bias (Deflated Sharpe Ratio)
- Churn metrics

---

## 8. Side-by-Side Metrics

### 8.1 Core Metrics (3 cost scenarios)

| Metric | E0 base | SM base | E0 harsh | SM harsh | E0 extreme | SM extreme |
|--------|---------|---------|----------|----------|------------|------------|
| **CAGR %** | 52.59 | 14.80 | 45.08 | 14.11 | 41.28 | 13.75 |
| **Sharpe** | 1.1944 | 1.3895 | 1.0773 | 1.3302 | 1.0157 | 1.2995 |
| **Sortino** | 1.0495 | 1.1623 | 0.9501 | 1.1142 | 0.8973 | 1.0894 |
| **MDD %** | 61.37 | 14.23 | 63.30 | 15.09 | 64.28 | 15.54 |
| **Calmar** | 0.8568 | 1.0402 | 0.7121 | 0.9348 | 0.6422 | 0.8850 |
| Trades | 226 | 76 | 226 | 76 | 226 | 76 |
| Win Rate % | 39.82 | 39.47 | 38.50 | 39.47 | 37.61 | 39.47 |
| Profit Factor | 1.6859 | 2.6627 | 1.5900 | 2.5512 | 1.5263 | 2.4780 |
| Avg Exposure | 0.4523 | 0.1065 | 0.4523 | 0.1065 | 0.4523 | 0.1065 |
| Time in Market % | 45.23 | 34.56 | 45.23 | 34.56 | 45.23 | 34.56 |
| Fees Total $ | 65,170 | 1,225 | 71,940 | 1,783 | 61,443 | 1,756 |
| Fee Drag %/yr | 5.22 | 0.68 | 7.83 | 1.02 | 7.83 | 1.02 |
| Turnover/yr | 52.22 | 6.83 | 52.21 | 6.81 | 52.20 | 6.80 |

### 8.2 Cost Sensitivity

| Metric | E0 Δ (base→extreme) | SM Δ (base→extreme) |
|--------|---------------------|---------------------|
| CAGR | −11.31 pp | −1.05 pp |
| Sharpe | −0.1787 | −0.0900 |
| MDD | +2.91 pp | +1.31 pp |
| Fee Drag %/yr | +2.61 pp | +0.34 pp |

SM degrades ~5–10× less than E0 under cost escalation.

### 8.3 Report 35 Consistency Check

Report 35 §4 results (base/harsh/extreme) for SM: CAGR 14.80/14.11/13.75, Sharpe 1.3895/1.3302/1.2995, MDD 14.23/15.09/15.54, Trades 76/76/76.

This evaluation SM results: CAGR 14.80/14.11/13.75, Sharpe 1.3895/1.3302/1.2995, MDD 14.23/15.09/15.54, Trades 76/76/76.

**Exact match** — all SM metrics identical to Report 35 §4. Initial discrepancy (65 trades) was caused by passing `start='2019-01-01'` to DataFeed, which narrows the data range vs CLI defaults (no start/end filter). Corrected by matching CLI invocation pattern (full data range, warmup_days=365).

---

## 9. Regime Decomposition

### 9.1 D1 Regime Distribution

Classifier: `v10/research/regime.py::classify_d1_regimes()` (6-class analytical)
Parameters: ema_fast=50, ema_slow=200, adx_period=14, shock_threshold=8%

| Regime | D1 Bars | Share % |
|--------|---------|---------|
| BULL | 1,320 | 42.4% |
| BEAR | 917 | 29.5% |
| NEUTRAL | 398 | 12.8% |
| CHOP | 230 | 7.4% |
| SHOCK | 142 | 4.6% |
| TOPPING | 103 | 3.3% |

### 9.2 Per-Regime Returns (base scenario)

| Regime | E0 Return % | SM Return % | E0 MDD % | SM MDD % | E0 Sharpe | SM Sharpe |
|--------|------------|------------|---------|---------|----------|----------|
| **BULL** | 1350.53 | 132.35 | 49.08 | 10.53 | 1.6670 | 2.0141 |
| **BEAR** | 121.30 | 44.20 | 37.60 | 8.56 | 1.2283 | 1.6465 |
| **CHOP** | 31.25 | −2.42 | 25.96 | 7.36 | 1.4070 | −0.4768 |
| **NEUTRAL** | 22.00 | 3.56 | 28.29 | 6.22 | 0.7266 | 0.4357 |
| **TOPPING** | −3.30 | 0.84 | 24.89 | 4.41 | −0.5950 | 1.0062 |
| **SHOCK** | −26.51 | −5.11 | 60.57 | 12.22 | −0.8834 | −0.9197 |

### 9.3 Regime Observations (data-only)

- **E0 profits in 4/6 regimes** (BULL, BEAR, CHOP, NEUTRAL); loses in TOPPING and SHOCK.
- **SM profits in 4/6 regimes** (BULL, BEAR, TOPPING, NEUTRAL); loses in CHOP and SHOCK.
- SM has higher Sharpe than E0 in BULL (+0.35), BEAR (+0.42), and TOPPING (+1.60).
- E0 has higher Sharpe than SM in CHOP (+1.88) and NEUTRAL (+0.29).
- SM per-regime MDD is 3–5× lower than E0 in every regime (vol-targeting effect).
- Both strategies lose in SHOCK (|daily return| > 8%). SM's SHOCK loss is 5.2× smaller than E0.
- E0's TOPPING regime loss (−3.30%, MDD 24.89%) vs SM's gain (+0.84%, MDD 4.41%) — SM's adaptive floor catches the turn more effectively.
- SHOCK: SM Sharpe (−0.92) slightly worse than E0 (−0.88), but SM SHOCK MDD 12.22% vs E0 60.57% — SM controls SHOCK drawdown 5× better.

---

## 10. Observations (data-only, no recommendation)

### 10.1 Structural Differences

1. **Exposure profile**: E0 average exposure 45.23% vs SM 10.65% — SM deploys ~4.2× less capital.
2. **Trade frequency**: E0 226 trades (52 turnover/yr) vs SM 76 trades (6.8 turnover/yr) — SM trades ~7.6× less.
3. **Cost sensitivity**: SM fee drag 0.68%/yr vs E0 5.22%/yr (base). SM is ~7.7× more cost-efficient.
4. **Sizing mechanism**: E0 binary (all-in/flat). SM fractional (target_vol / realized_vol, clamped [0,1]).

### 10.2 Risk/Return Profile

5. **CAGR**: E0 delivers 3.6× higher absolute CAGR (52.59% vs 14.80%, base).
6. **MDD**: SM drawdown 4.3× smaller (14.23% vs 61.37%, base).
7. **Sharpe**: SM Sharpe 16.3% higher (1.3895 vs 1.1944, base). Not statistically significant (PairDiagnostic bootstrap p=0.214).
8. **Calmar**: SM Calmar 21% higher (1.0402 vs 0.8568, base) — SM's MDD advantage outweighs E0's CAGR advantage at this cost level. Reverses at extreme: E0 Calmar 0.6422 vs SM 0.8850.
9. **Profit Factor**: SM 2.66 vs E0 1.69 (base). SM's winning trades are more profitable relative to losers.

### 10.3 Bootstrap Context (from Report 35 §9)

10. **SM VCBB bootstrap** (2000 paths, harsh): Sharpe median 0.78, CAGR median 7.5%, MDD median 17.4%, P(CAGR>0)=95.0%.
11. **E0 VCBB bootstrap** (from prior research): Sharpe median 0.54, CAGR median 14.2%, MDD median 61.0%, P(CAGR>0)=80.3%.
12. SM has higher P(CAGR>0) (95% vs 80%) and lower median MDD (17% vs 61%) in bootstrap.

### 10.4 PairDiagnostic Summary

13. Classification: `materially_different` (correlation 0.729, near_equal_1bp 51.9%).
14. Geo-growth: E0 overwhelmingly higher (p=0.989). Sharpe: SM non-significantly higher (p=0.214).
15. Suggested route: `inconclusive_default` — power limitation applies.

---

## 11. Caveats

### 11.1 Mandatory Caveats

1. **PairDiagnostic has zero decision authority.** The `inconclusive_default` route is a non-binding machine label. The harness produces computed values only (per Report 22B design contract).

2. **Single-timescale limitation.** All results are from one data sample (BTC H4, 2017-08 to 2026-02). Cross-timescale, cross-asset, and out-of-sample robustness are NOT tested.

3. **Report 35 §4 consistency**: SM metrics in this evaluation match Report 35 §4 exactly (verified by matching CLI invocation pattern: full data range, no start/end filter, warmup_days=365).

4. **E0 baseline note**: The `strategies/vtrend/strategy.py` implementation does NOT include the D1 EMA(21d) regime filter referenced in MEMORY.md. E0 results here are for the as-implemented pure H4 strategy.

5. **Validation pipeline not run**: No YAML config file exists for vtrend_sm. The full validation pipeline (WFO, holdout, cost sweep, selection bias) was not executed.

6. **DSR p-values are advisory only**: Both strategies show high DSR p-values (>0.70 at all trial counts). This is expected for trend-following strategies and does not indicate an issue.

### 11.2 Regime Decomposition Caveats

7. **Regime classifier is post-hoc analytical** — it uses D1 EMA(50,200) + ADX, which is NOT used by either strategy for trading decisions. Regime labels are for attribution analysis only.

8. **Per-regime Sharpe uses non-contiguous bars** — bars from the same regime are not necessarily adjacent. Max drawdown within a regime is computed from the regime's bars only (not the full equity curve), which may understate actual drawdown experienced during that regime.

---

## 12. Open Questions

| # | Question | Blocking? | Notes |
|---|----------|-----------|-------|
| Q1 | Should YAML config for vtrend_sm be created to enable validation pipeline? | No | Infrastructure is ready. Only config file missing. |
| Q2 | T20 engine integration test: should it be updated to actually instantiate BacktestEngine? | No | Current test covers strategy interface. Backtest correctness verified separately in Report 35 §4-5. |
| Q3 | VDO `_vdo()` numerical unit test: should coverage gap be addressed? | No | VDO disabled by default. Behavioral test exists. Risk is low. |
| Q4 | E0 D1 regime filter: is the baseline comparison meaningful without it? | No | This report compares as-implemented strategies. The D1 filter is an overlay, not part of core E0. |
| Q5 | Rebalance close-vs-open basis: should a specific test be added? | No | Zero divergence with default params (35 §5.4). Theoretical edge case only. |

---

## 13. Metadata

| Item | Value |
|------|-------|
| Report created | 2026-03-04 |
| Data file | data/bars_btcusdt_2016_now_h1_4h_1d.csv |
| Equity bars | 18,662 |
| PairDiagnostic seed | 1337 |
| PairDiagnostic bootstrap | 2000 iterations |
| PairDiagnostic block sizes | 10, 20, 40 |
| Regime classifier | `v10/research/regime.py::classify_d1_regimes()` |
| E0 strategy | `strategies/vtrend/strategy.py` VTrendStrategy(VTrendConfig()) |
| SM strategy | `strategies/vtrend_sm/strategy.py` VTrendSMStrategy(VTrendSMConfig()) |
| Engine | `v10/core/engine.py` BacktestEngine, warmup_mode='no_trade' |
| Metrics | `v10/core/metrics.py` compute_metrics(), nav_mid basis |
| No code changes made | ✓ |
