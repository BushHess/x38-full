# Report 00 -- Setup and Scope

**Date**: 2026-03-05
**Namespace**: `research/eval_vtrend_latch_20260305/`
**Phase**: Step 0 -- Branch creation, repo scan, scope lock

---

## 1. Namespace

Repository is **not git-initialized**. A logical research namespace was created:

```
btc-spot-dev/research/eval_vtrend_latch_20260305/
  docs/       -- design notes, specifications
  reports/    -- numbered reports (this file is 00)
  artifacts/  -- intermediate data, CSVs, plots
  src/        -- research harness code (read-only imports from main repo)
  tests/      -- harness tests
  configs/    -- evaluation configs
  logs/       -- run logs
```

**Invariant**: No file outside this namespace will be created, modified, or deleted.

---

## 2. Repo Scan -- Notable Files

### 2.1 Strategy Implementations (btc-spot-dev)

All strategies in `btc-spot-dev/strategies/` share the **same BacktestEngine** (`v10/core/engine.py`).

| Strategy | Path | Lines | Tunable Params | Sizing Model | Avg Exposure |
|----------|------|------:|:--------------:|:------------:|:------------:|
| **VTREND (E0)** | `strategies/vtrend/strategy.py` | 177 | 3 | Binary 100% | 46.8% |
| **VTREND-SM** | `strategies/vtrend_sm/strategy.py` | 363 | 8 | Vol-targeted fractional | 11.8% |
| **VTREND-P** | `strategies/vtrend_p/strategy.py` | 297 | 6 | Vol-targeted fractional | 10.3% |
| **LATCH** | `strategies/latch/strategy.py` | 526 | 13 + 15 VDO | Vol-targeted fractional + floor | 9.5% |

### 2.2 LATCH Standalone Package (Latch/)

A separate self-contained implementation exists at `/var/www/trading-bots/Latch/research/Latch/`:

| File | Lines | Role |
|------|------:|------|
| `strategy.py` | 218 | Core `run_latch()` function |
| `state_machine.py` | 77 | Hysteretic regime computation |
| `indicators.py` | 113 | EMA, ATR Wilder, rolling H/L, realized vol |
| `backtest.py` | 350 | **Own backtest engine** (execute_target_weights) |
| `config.py` | 153 | LatchParams, CostModel, VDOOverlayParams |
| `overlays.py` | 76 | Soft VDO modulation |
| `LATCH_ALGORITHM_SPEC.md` | 398 | Formal reconstruction spec |

**Also**: `Latch/research/vtrend_variants.py` (895 lines) -- standalone VTREND-SM and VTREND-P runners with their own backtest loop.

### 2.3 Backtest Infrastructure (v10/core/)

| File | Lines | Role |
|------|------:|------|
| `engine.py` | 337 | Event-driven BacktestEngine, next-open fills |
| `data.py` | 100 | DataFeed: CSV loading, H4/D1 splitting |
| `execution.py` | 230 | ExecutionModel (spread/slip/fee), Portfolio |
| `types.py` | 184 | Bar, CostConfig, Signal, Fill, Trade |
| `metrics.py` | 190 | Sharpe, CAGR, MDD, Calmar, turnover |
| `config.py` | 270 | LiveConfig = Engine + Strategy + Risk |

### 2.4 Cost Models

**btc-spot-dev (v10/core/types.py)**:
```
smart:  spread=3.0 bps, slip=1.5 bps, fee=0.035%  -->  RT ~13 bps
base:   spread=5.0 bps, slip=3.0 bps, fee=0.10%   -->  RT ~31 bps
harsh:  spread=10.0 bps, slip=5.0 bps, fee=0.15%  -->  RT ~50 bps
```

**Latch (config.py)**:
```
one_way_rate = (fee_bps + half_spread_bps + slippage_bps) / 10_000
default: fee=25.0 bps, spread=0, slip=0 --> 25 bps one-way = 50 bps RT
```

### 2.5 Existing Evaluation Results

Three comparisons already ran (2026-03-05) via `validate_strategy.py`:

| Comparison | Verdict | Candidate Sharpe (harsh) | Baseline Sharpe (harsh) | Cand. Exposure | Base Exposure |
|------------|---------|:------------------------:|:-----------------------:|:--------------:|:-------------:|
| LATCH vs E0 | **REJECT** | 1.44 | 1.27 | 9.5% | 46.8% |
| SM vs E0 | (run) | 1.44 | 1.27 | 11.8% | 46.8% |
| P vs E0 | (run) | 1.40 | 1.27 | 10.3% | 46.8% |

**Critical observation**: LATCH was REJECTED on absolute score delta, but its **Sharpe is HIGHER** than E0 (1.44 vs 1.27). The rejection is driven entirely by the massive CAGR gap (12.8% vs 52.0%) which is a **direct consequence of 5x lower average exposure** (9.5% vs 46.8%).

### 2.6 Research Library

| File | Role |
|------|------|
| `research/lib/vcbb.py` | VCBB bootstrap path generation |
| `research/lib/dsr.py` | Deflated Sharpe Ratio |
| `research/lib/effective_dof.py` | M_eff DOF correction |

### 2.7 Documentation & Specs

| File | Role |
|------|------|
| `VTREND_BLUEPRINT.md` | Complete VTREND rebuild spec |
| `Latch/research/VTREND_SPEC_AND_GUIDE.md` | VTREND-SM/P spec and usage |
| `Latch/research/Latch/LATCH_ALGORITHM_SPEC.md` | Formal LATCH spec |
| `docs/specs/SPEC_EXECUTION.md` | v10 execution semantics |
| `docs/specs/SPEC_METRICS.md` | v10 metrics definitions |
| `docs/specs/SEMANTICS_CONTRACT.md` | Core execution contract |

### 2.8 Test Suites

| File | Tests | Coverage |
|------|------:|----------|
| `tests/test_latch.py` | ~50 | State machine, VDO, rebalance |
| `tests/test_vtrend_sm.py` | 56 | Entry, exit, regime, rebalance |
| `tests/test_vtrend_p.py` | ~40 | Price-first entry, sizing |
| `Latch/research/test_latch.py` | ~15 | LATCH core (standalone package) |
| `Latch/research/test_vtrend_variants.py` | 8 | VTREND-SM/P (standalone) |

---

## 3. Research Questions

This study must answer:

### Q1: Signal Quality Isolation
Are VTREND-E0, VTREND-SM, VTREND-P, and LATCH producing different **signals** (entry/exit timing), or are the performance differences primarily an artifact of **sizing** (binary 100% vs vol-targeted fractional)?

### Q2: Sizing Decomposition
What fraction of performance difference (CAGR, Sharpe, MDD) is attributable to:
- (a) Signal quality (entry/exit timing)
- (b) Position sizing (binary vs vol-targeted)
- (c) Exposure level (46.8% vs ~10%)
- (d) Fee drag (turnover 52x/yr vs 5-7x/yr)

### Q3: Backtest Engine Equivalence
The `Latch/research/Latch/backtest.py` engine and `v10/core/engine.py` are **two different implementations**. Are they semantically identical? Specifically:
- Fill price computation (spread, slippage application)
- Cost deduction mechanics (pre-fill vs post-fill)
- NAV calculation (mid vs liquidation)
- Rebalance threshold logic
- Warmup handling

### Q4: Fair Head-to-Head
Under **identical** sizing, exposure, and cost models, which signal generator (VTREND-E0, SM, P, LATCH) produces superior risk-adjusted returns?

### Q5: Regime Overlap
Do the strategies agree on regime state (trending vs flat)? What is the signal overlap (concordance) between VTREND-E0 and LATCH on the same data?

### Q6: Complexity-Adjusted Value
VTREND-E0 has 3 params. LATCH has 28. Does the additional complexity produce measurably better outcomes after proper correction for overfitting risk (DSR, M_eff)?

---

## 4. Prohibitions

To protect the existing project:

1. **NO modification** of any file outside `research/eval_vtrend_latch_20260305/`
2. **NO renaming, deletion, or overwriting** of existing code, configs, results, or reports
3. **NO git operations** (repo is not git-initialized)
4. **NO parameter optimization** -- this study evaluates existing algorithms at their default parameters
5. **NO deployment recommendations** until all research questions are answered with statistical proof
6. **NO import-time side effects** -- research code must import from main repo read-only
7. **NO modification** of `research/lib/`, `v10/core/`, `strategies/`, `validation/`, or `Latch/`

---

## 5. Key Sources of Confounding (Identified at Scan)

### 5.1 Exposure Mismatch
VTREND-E0 runs at ~47% average exposure (binary 100% when in position).
All competitors run at ~10% average exposure (vol-targeted).
Raw CAGR comparison is meaningless without exposure normalization.

### 5.2 Sizing Model Asymmetry
E0 uses binary in/out. SM/P/LATCH use continuous fractional sizing.
A strategy can have superior signal timing but appear worse due to conservative sizing.

### 5.3 Two Backtest Engines
`Latch/research/` has its own backtest engine. `btc-spot-dev/strategies/latch/` is integrated into v10 engine.
Any comparison must verify that both engines produce identical results for the same signal stream.

### 5.4 Fee Drag Amplification
E0 at 52x/yr turnover pays ~7.84% annual fee drag (harsh).
LATCH at 5.6x/yr turnover pays ~0.84% annual fee drag (harsh).
Fee drag alone accounts for ~7% annual return difference.

### 5.5 Evaluation Framework Bias
The existing `validate_strategy.py` scoring function rewards absolute CAGR heavily, penalizing low-exposure strategies regardless of risk-adjusted performance.

---

## 6. Next Steps (Not Executed Yet)

Pending user approval before proceeding:

- Step 1: Engine equivalence test (v10 engine vs Latch/research engine)
- Step 2: Signal extraction and concordance analysis
- Step 3: Exposure-normalized comparison (equal-vol or equal-exposure basis)
- Step 4: Sizing decomposition (signal x sizing factorial)
- Step 5: Statistical significance testing on decomposed components
- Step 6: Final synthesis report

---

*End of Report 00. No harness code written. No backtests run. No performance conclusions drawn.*
