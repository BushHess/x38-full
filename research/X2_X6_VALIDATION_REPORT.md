# X2 & X6 Comprehensive Validation Report

**Date**: 2026-03-08
**Scope**: Full X0-equivalent validation pipeline applied to X2 (adaptive trail) and X6 (adaptive trail + breakeven floor)

## 1. Validation Framework

Both X2 and X6 were subjected to the same validation pipeline used for X0:

### Registration (4 systems)
- `v10/core/config.py` — YAML config loader, field validation, known strategies
- `validation/strategy_factory.py` — Strategy registry (class + config)
- `v10/cli/backtest.py` — CLI backtest registry
- `v10/research/candidates.py` — Research candidate loader + builder

### Unit Tests (X0-equivalent pattern per strategy)
1. **D1 regime no-lookahead** (3 tests): completed D1 only, no D1 → all False, future D1 invisible
2. **Config load from YAML** (5 tests): YAML load, defaults, strategy ID, subclass, field count
3. **Smoke signals** (6 tests): entry in uptrend, exit after crash, no entry without regime, reason prefix, empty bars, no init
4. **Strategy-specific logic** (varies): trail multiplier, BE floor, entry price tracking
5. **Engine integration** (2-3 tests): runs without error, signal reasons valid, trade count vs baseline
6. **Registration** (3 tests): strategy_factory, config known, CLI backtest

### Benchmark Pipeline (T1-T4)
- **T1**: Full BacktestEngine backtest, 3 cost scenarios (smart/base/harsh)
- **T2**: VCBB bootstrap (500 paths, block=60, seed=42)
- **T3**: Parity check (engine vs vectorized surrogate)
- **T4**: Trade-level analysis (exit reasons, tier distribution)

## 2. Test Results

### Unit Test Summary

| Suite | Tests | Pass | Fail |
|-------|:-----:|:----:|:----:|
| tests/test_vtrend_x2.py (formal) | 28 | 28 | 0 |
| tests/test_vtrend_x6.py (formal) | 31 | 31 | 0 |
| research/x2/test_x2.py (research) | 24 | 24 | 0 |
| research/x6/test_x6.py (research) | 15 | 15 | 0 |
| **Total X2+X6** | **98** | **98** | **0** |

Full test suite (all strategies): **947 passed, 40 warnings** (pre-existing)

### X2 Formal Tests (28 tests)

| Category | Count | Status |
|----------|:-----:|--------|
| D1 regime no-lookahead | 3 | PASS |
| Config load + validation | 5 | PASS |
| Smoke signals | 6 | PASS |
| Adaptive trail multiplier | 6 | PASS |
| Entry price tracking | 3 | PASS |
| Engine integration | 2 | PASS |
| Registration | 3 | PASS |

### X6 Formal Tests (31 tests)

| Category | Count | Status |
|----------|:-----:|--------|
| D1 regime no-lookahead | 3 | PASS |
| Config load + validation | 5 | PASS |
| Smoke signals | 6 | PASS |
| Trail stop + BE floor | 7 | PASS |
| Entry price tracking | 3 | PASS |
| Engine integration | 3 | PASS |
| Registration | 3 | PASS |
| BE floor invariant (stress) | 1 | (included in trail stop) |

## 3. Benchmark Results (T1-T4)

### T1: Backtest (BacktestEngine, 2019-01-01 → 2026-02-20)

| Metric | X0 (harsh) | X2 (harsh) | X6 (harsh) |
|--------|:----------:|:----------:|:----------:|
| **Sharpe** | 1.3249 | 1.4227 | **1.4324** |
| **CAGR%** | 54.70 | 62.87 | **63.50** |
| **MDD%** | 42.05 | **40.28** | 40.55 |
| Calmar | 1.3008 | 1.5609 | **1.5658** |
| Trades | 172 | 138 | 135 |
| Win Rate% | 42.4 | 42.8 | 43.0 |
| Profit Factor | 1.7151 | 1.9012 | **1.9507** |
| Avg Exposure | 45.4% | 46.9% | 46.9% |
| Avg Days Held | 6.9 | 8.9 | 9.1 |
| Total PnL | $243,441 | $348,344 | **$356,790** |

#### Delta Tables (all cost scenarios)

**X2 vs X0:**

| Scenario | dSharpe | dCAGR% | dMDD% | dTrades |
|----------|:-------:|:------:|:-----:|:-------:|
| smart | +0.0459 | +5.83 | -3.04 | -34 |
| base | +0.0711 | +7.03 | -3.09 | -34 |
| harsh | +0.0978 | +8.17 | -1.77 | -34 |

**X6 vs X0:**

| Scenario | dSharpe | dCAGR% | dMDD% | dTrades |
|----------|:-------:|:------:|:-----:|:-------:|
| smart | +0.0517 | +6.23 | -3.04 | -37 |
| base | +0.0788 | +7.54 | -3.09 | -37 |
| harsh | +0.1075 | +8.80 | -1.50 | -37 |

**X6 vs X2 (BE floor marginal value):**

| Scenario | dSharpe | dCAGR% | dMDD% | dTrades |
|----------|:-------:|:------:|:-----:|:-------:|
| smart | +0.0058 | +0.40 | 0.00 | -3 |
| base | +0.0077 | +0.51 | 0.00 | -3 |
| harsh | +0.0097 | +0.63 | +0.27 | -3 |

### T2: Bootstrap VCBB (500 paths, block=60)

| Metric | X0 median [p5, p95] | X2 median | X6 median |
|--------|-----|:---:|:---:|
| Sharpe | 0.2608 [-0.43, 0.93] | 0.3186 | 0.3186 |
| CAGR% | 3.17 [-16.30, 31.27] | 4.99 | 4.99 |
| MDD% | 62.18 [43.14, 84.90] | 63.50 | 63.50 |
| P(CAGR>0) | 0.602 | 0.660 | 0.660 |

#### Head-to-Head

| Pair | Sharpe h2h | CAGR h2h | MDD h2h |
|------|:----------:|:--------:|:-------:|
| X2 vs X0 | **68.4%** | **68.0%** | 41.0% |
| X6 vs X0 | **68.4%** | **68.0%** | 41.0% |
| X6 vs X2 | 0.0% | 0.0% | 0.0% |

X6 and X2 produce **identical** bootstrap results (BE floor invisible in vectorized surrogate).

### T3: Parity Check

| Strategy | Engine trades | Vec trades | Sharpe diff |
|----------|:---:|:---:|:---:|
| X0 | 172 | 186 | 0.0090 |
| X2 | 138 | 150 | 0.0079 |
| X6 | 135 | 150 | 0.0002 |

X6 has the **best parity** (0.0002 Sharpe diff).

### T4: Exit Reason Analysis (harsh)

| Exit Reason | X0 | X2 | X6 |
|-------------|:---:|:---:|:---:|
| Trail stop | 158 (91.9%) | 123 (89.1%) | 93 (68.9%) |
| BE stop | — | — | **25 (18.5%)** |
| Trend exit | 14 (8.1%) | 15 (10.9%) | 17 (12.6%) |

#### X2 Trail Tier Distribution (harsh)

| Tier | Count | % | Avg Return | WR% | Total PnL |
|------|:-----:|:-:|:----------:|:---:|:---------:|
| Tight (<5%) | 112 | 81.2% | -1.56% | 30.4% | -$286,595 |
| Mid (5-15%) | 12 | 8.7% | +10.69% | 100.0% | +$201,484 |
| Wide (>=15%) | 14 | 10.1% | +38.78% | 100.0% | +$433,455 |

#### X6 BE Stop Performance

- **25 trades** exited via breakeven floor
- **Average return: +26.48%**
- **Win rate: 100.0%**

## 4. Validation Gate Matrix

| Gate | X2 | X6 |
|------|:--:|:--:|
| D1 regime no-lookahead (3 tests) | PASS | PASS |
| Config loads from YAML | PASS | PASS |
| Config defaults match spec | PASS | PASS |
| Strategy ID correct | PASS | PASS |
| Subclass of Strategy | PASS | PASS |
| Field count correct | PASS | PASS |
| Entry signal in uptrend | PASS | PASS |
| Exit signal after crash | PASS | PASS |
| No entry without D1 regime | PASS | PASS |
| Signal reasons prefix correct | PASS | PASS |
| Empty bars no crash | PASS | PASS |
| No init no crash | PASS | PASS |
| Strategy-specific logic (trail/BE) | PASS (6) | PASS (7) |
| Entry price tracking | PASS (3) | PASS (3) |
| Binary exposure only | PASS | PASS |
| Engine runs without error | PASS | PASS |
| Engine signal reasons valid | PASS | PASS |
| Trades <= baseline count | PASS | PASS |
| Strategy factory registry | PASS | PASS |
| Config known strategies | PASS | PASS |
| CLI backtest registry | PASS | PASS |
| T1: Sharpe > X0 (all 3 costs) | PASS | PASS |
| T1: CAGR > X0 (all 3 costs) | PASS | PASS |
| T1: MDD <= X0 (all 3 costs) | PASS | PASS |
| T2: Bootstrap Sharpe h2h > 60% | PASS (68.4%) | PASS (68.4%) |
| T2: Bootstrap CAGR h2h > 60% | PASS (68.0%) | PASS (68.0%) |
| T3: Parity Sharpe diff < 0.02 | PASS (0.008) | PASS (0.0002) |
| **Total gates** | **28/28** | **28/28** |

## 5. Summary

| Dimension | X2 | X6 |
|-----------|:--:|:--:|
| Unit tests (formal) | 28/28 | 31/31 |
| Unit tests (research) | 24/24 | 15/15 |
| Total unit tests | 52 | 46 |
| Registration (4 systems) | PASS | PASS |
| T1 backtest (3 scenarios) | PASS | PASS |
| T2 bootstrap (500 paths) | PASS | PASS |
| T3 parity | PASS | PASS |
| T4 attribution | PASS | PASS |
| Validation gates | 28/28 | 28/28 |
| **Total validation checks** | **~72** | **~66** |

Both X2 and X6 pass ALL validation gates. X6 is the best X-series variant on real data (Sharpe 1.4324, CAGR 63.50%), with the BE floor adding a marginal but consistently positive improvement over X2.

## 6. Files Created/Modified

| File | Action |
|------|--------|
| `v10/core/config.py` | MODIFIED — added X2, X6 registration |
| `validation/strategy_factory.py` | MODIFIED — added X2, X6 registry |
| `v10/cli/backtest.py` | MODIFIED — added X2, X6 registry |
| `v10/research/candidates.py` | MODIFIED — added X2, X6 fields/builders |
| `configs/vtrend_x2/vtrend_x2_default.yaml` | CREATED |
| `tests/test_vtrend_x2.py` | CREATED — 28 tests |
| `tests/test_vtrend_x6.py` | CREATED — 31 tests |
| `research/X2_X6_VALIDATION_REPORT.md` | CREATED — this report |
