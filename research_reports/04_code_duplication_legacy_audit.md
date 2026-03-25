# Audit Report 04: Code Duplication & Legacy Audit

**Date**: 2026-03-03
**Auditor**: Claude Opus 4.6
**Scope**: Full `/var/www/trading-bots/btc-spot-dev/` repository
**Verdict**: **1 dead framework**, **2 code duplications**, **~2.4 GB archivable outputs**, **~15 GB total output artifacts**

---

## 1. Executive Summary

The btc-spot-dev repository has accumulated layers of code across 6 major version iterations (v3→v6→v7→v8→v9→v10/v11→v12→v13). This audit identifies what is **active**, what is **legacy-but-referenced**, what is **dead**, and what is **duplicated**.

| Category | Count | Status |
|----------|-------|--------|
| Active validation framework | 1 (`validation/`) | LIVE |
| Dead validation framework | 1 (`v10/validation/`) | **DEAD — zero external imports** |
| Bootstrap libraries | 2 (different algorithms) | Both LIVE, not duplicates |
| DSR implementations | 3 (same algorithm) | **DUPLICATED** |
| Annualization constants | 2 values (2190 vs 2191.5) | **INCONSISTENT** |
| Legacy strategy dirs | 2 (`v6/`, `v7/`) | Referenced by live bots |
| Output directories | 118 (`out_*`) | ~15 GB total, ~2.4 GB archivable |

---

## 2. Dead Code: `v10/validation/` Framework

### 2.1 Evidence of Death

**Zero external imports.** No file outside `v10/validation/` imports from it:

```
$ grep -r "from v10\.validation" --include="*.py" -l | grep -v __pycache__ | grep -v "^v10/"
(empty — no results)
```

**Entry point confirms top-level is active:**

```python
# validate_strategy.py (the CLI entry point)
from validation.cli import main   # ← top-level, NOT v10
```

### 2.2 Comparison: v10/validation/ vs validation/

| Metric | `v10/validation/` | `validation/` (top-level) |
|--------|-------------------|--------------------------|
| Core modules LOC | 1,075 | 3,256 |
| Suite files | 13 | 19 (+6 new) |
| Suites LOC | 1,781 | 7,298 |
| Config fields | ~50 | ~166 |
| CLI args | 21 | 60+ |
| External importers | **0** | 5 files |
| Tests | 0 | 9 test files |

**New suites in top-level only** (not in v10):
- `data_integrity.py` — data completeness validation
- `cost_sweep.py` — cost robustness sweep
- `invariants.py` — mathematical invariant checks
- `regression_guard.py` — golden path regression detection
- `churn_metrics.py` — trade churn analysis
- `common.py` — shared helpers (`ensure_backtest`, `scenario_costs`)

**New core modules in top-level only:**
- `config_audit.py` — ConfigProxy, access tracking
- `discovery.py` — test discovery and enumeration
- `score_decomposition.py` — metric decomposition

### 2.3 Relationship

`v10/validation/` is the **original prototype**. `validation/` (top-level) is the **evolved production framework** — it grew from v10 but diverged significantly (4× more code, +6 suites, full audit trail).

### 2.4 Why v10/ Still Exists

The `v10/` directory as a whole is **NOT dead**:

| Subdirectory | Status | Reason |
|-------------|--------|--------|
| `v10/core/` | **LIVE** | Engine, types, data — imported by validation/ |
| `v10/research/` | **LIVE** | bootstrap, subsampling, wfo — imported by validation/ |
| `v10/strategies/` | **LIVE** | Strategy implementations |
| `v10/tests/` | **LIVE** | Unit tests for v10/research/ |
| `v10/validation/` | **DEAD** | Superseded by top-level validation/ |

### 2.5 Verdict

**`v10/validation/` (22 files, 2,856 LOC) is dead code.** It can be safely archived or deleted. The active pipeline does not use it.

---

## 3. Bootstrap Files: NOT Duplicated

### 3.1 Two Libraries, Two Purposes

| | `research/lib/bootstrap.py` (493 LOC) | `v10/research/bootstrap.py` (250 LOC) |
|--|---|---|
| **Purpose** | Generate synthetic **price paths** | Compute **confidence intervals** on equity curves |
| **Input** | OHLCV bar arrays | `list[EquitySnap]` (backtest output) |
| **Output** | `(close, high, low, vol, time)` arrays | `PairedBootstrapResult` (p_a_better, CI, delta) |
| **Algorithm** | VCBB — vol-conditioned block resampling | Circular block bootstrap (Politis & Romano 1994) |
| **Key functions** | `gen_path()`, `gen_path_vcbb()`, `precompute_vcbb()` | `paired_block_bootstrap()`, `calc_sharpe()`, `run_bootstrap_suite()` |
| **Imported by** | 11 research scripts | 7 files (validation suites + tests + runners) |

These serve **complementary roles** in the research pipeline:
1. `research/lib/bootstrap.py` → generate 2000 synthetic BTC paths (VCBB preserves vol clustering)
2. Run strategy on each path → get equity curves
3. `v10/research/bootstrap.py` → compute CI on strategy performance vs baseline

**Not duplicates. Both are live and necessary.**

### 3.2 Validation Suite Layer

| Suite | Framework | Imports from | Status |
|-------|-----------|-------------|--------|
| `validation/suites/bootstrap.py` (112 LOC) | Top-level (active) | `v10.research.bootstrap` | **LIVE** |
| `v10/validation/suites/bootstrap.py` (141 LOC) | v10 (dead) | `v10.research.bootstrap` | **DEAD** (part of dead v10/validation/) |

Only 1 suite is active. The v10 copy is dead as part of the dead v10/validation/ framework.

### 3.3 Research Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `research/validate_bootstrap.py` (28 KB) | VCBB quality validation (4 tests) | LIVE — in `run_all_studies.sh` |
| `research/bootstrap_regime.py` (25 KB) | Bootstrap + regime analysis | LIVE — in `run_all_studies.sh` |
| `research/v8_vs_vtrend_bootstrap.py` (31 KB) | V8 vs VTREND paired comparison | LIVE — in `run_all_studies.sh` |
| `run_v11_wfo_bootstrap.py` (12 KB) | WFO + bootstrap analysis | LIVE — standalone runner |
| `out_trade_analysis/bootstrap_paired.py` (11 KB) | Trade-level bootstrap | LIVE — standalone analysis |

All 5 scripts are registered in runners or used as standalone tools. None are dead.

---

## 4. Code Duplication: DSR (Deflated Sharpe Ratio)

### 4.1 Three Implementations of the Same Math

**Location A — Canonical** (`research/lib/dsr.py`, 167 LOC):
```python
from statistics import NormalDist
_GAMMA = 0.5772156649015329     # full precision
z = NormalDist()
z1 = z.inv_cdf(max(1e-12, 1.0 - 1.0 / num_trials))   # exact inverse CDF
```
- Well-documented, 19 unit tests (`research/lib/test_dsr.py`)
- Uses `statistics.NormalDist` for exact probit/CDF
- Returns full diagnostic dict
- Uses `ddof=1` for SR (per paper specification)

**Location B — Inline Copy** (`validation/suites/selection_bias.py`, lines 21-51):
```python
gamma_em = 0.5772156649         # truncated precision (10 digits vs 16)
def _probit(p):                 # hand-rolled approximation (Abramowitz & Stegun)
    t = math.sqrt(-2.0 * math.log(min(p, 1 - p)))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    ...
```
- No tests
- Uses hand-rolled `_probit()` approximation instead of `NormalDist.inv_cdf()`
- Uses `_norm_cdf()` via `math.erf()` instead of `NormalDist.cdf()`
- Comment explicitly says `# from selection_bias_v10_v11.py` — this was copy-pasted

**Location C — Another Inline Copy** (`v10/validation/suites/selection_bias.py`, lines 21-51):
- Nearly identical to Location B
- Same truncated gamma, same hand-rolled probit
- Part of the dead v10/validation/ framework

### 4.2 Mathematical Differences

| Aspect | `dsr.py` (canonical) | `selection_bias.py` (copies) |
|--------|---------------------|------------------------------|
| Euler-Mascheroni γ | `0.5772156649015329` (16 digits) | `0.5772156649` (10 digits) |
| Probit function | `NormalDist.inv_cdf()` (exact) | Abramowitz & Stegun rational approx |
| Normal CDF | `NormalDist.cdf()` (exact) | `0.5 * (1 + erf(z/√2))` (equivalent) |
| Denominator form | `√(n-1)` factor | `variance / T` then `√variance` |
| Benchmark SR₀ | `SR₀ · √(1/(n-1))` | `sr_std · E[max_z]` (different factoring) |

The probit approximation has error < 4.5×10⁻⁴ for typical inputs — unlikely to change pass/fail decisions, but unnecessary duplication with a lower-quality implementation.

### 4.3 Verdict

`validation/suites/selection_bias.py` should import from `research.lib.dsr` instead of reimplementing 30 lines of DSR math inline.

---

## 5. Code Duplication: Metric Calculations

### 5.1 Sharpe Ratio — 8 Locations

| File | Annualization | ddof |
|------|--------------|------|
| `v10/core/metrics.py:181` | `sqrt(2190)` | 0 |
| `v10/research/bootstrap.py:43` | `sqrt(2190)` | 0 |
| `research/lib/dsr.py:94` | `sqrt(6.0 * 365.25)` = `sqrt(2191.5)` | 1 |
| `research/cross_check_vs_vtrend.py` | `sqrt(6.0 * 365.25)` | 0 |
| `research/vtrend_param_sensitivity.py` | `sqrt(6.0 * 365.25)` | 0 |
| `research/trail_sweep.py` | `sqrt(6.0 * 365.25)` | 0 |
| `research/regime_sizing.py` | `sqrt(6.0 * 365.25)` | 0 |
| `research/multiple_comparison.py` | `sqrt(6.0 * 365.25)` | 0 |

**Inconsistency**: `v10/` uses `2190` (integer), `research/` uses `6.0 * 365.25 = 2191.5`. The difference is 0.03% — negligible for inference but a maintenance hazard.

Per MEMORY.md convention: `sqrt(6.0 * 365.25)` is canonical. The `v10/` constant `PERIODS_PER_YEAR_4H = 2190` is the approximation.

### 5.2 Max Drawdown — 2 Locations

| File | Implementation |
|------|---------------|
| `v10/core/metrics.py:159` | Takes NAV array directly |
| `v10/research/bootstrap.py:57` | Builds equity from returns, then same logic |

Functionally identical. The bootstrap version exists because it operates on returns (from resampled blocks) rather than NAV.

### 5.3 CAGR — 2 Locations

| File | Implementation |
|------|---------------|
| `v10/core/metrics.py:62` | From NAV ratio with overflow fallback |
| `v10/research/bootstrap.py:46` | From returns product |

Slightly different entry points (NAV vs returns), same formula.

### 5.4 Verdict

Sharpe/CAGR/MDD duplication between `v10/core/metrics.py` and `v10/research/bootstrap.py` is **semi-justified** — the research module needs standalone calculators that work on resampled return arrays without a full BacktestResult. However, the annualization constant should be unified.

---

## 6. Legacy Directories: v6/ and v7/

### 6.1 Status

| Directory | Size | Files | Imported By |
|-----------|------|-------|-------------|
| `v6/` | 172 KB | 6 .py files | `btc_only_bot_v6.py`, `btc_only_backtest_v6.py`, `btc_only_backtest_v7.py` |
| `v7/` | 156 KB | 3 .py files | `btc_only_backtest_v7.py` |

### 6.2 Import Chain

```
btc_only_bot_v6.py (LIVE BOT)
  └── imports 31 objects from v6/

btc_only_backtest_v6.py (comparison backtester)
  └── imports from v6/

btc_only_backtest_v7.py (comparison backtester)
  ├── imports from v6/ (V7 extends V6)
  └── imports from v7/
```

### 6.3 Verdict

v6/ and v7/ are **NOT dead** — `btc_only_bot_v6.py` is a live trading bot that directly imports v6 modules. However, they are **legacy** and not part of the current research/validation pipeline (v10+). They should be clearly marked as legacy but NOT deleted while the v6 bot is in use.

---

## 7. Output Directories

### 7.1 Inventory

| Version Group | Count | Total Size | Status |
|--------------|-------|-----------|--------|
| v6 outputs | 11 | **641 MB** | Archivable (historical experiments) |
| v7 outputs | 19 | **1,538 MB** | Archivable (rejected; incl. 779 MB trail scan) |
| v8 outputs | 29 | **219 MB** | Archivable (superseded by v10+) |
| v9 outputs | 4 | ~13 MB | Small, keep |
| v10 outputs | 21 | ~230 MB | Active research |
| v11 outputs | 10 | ~210 MB | Active research |
| v12 outputs | 7 | ~1 MB | Active (audit) |
| v13 outputs | 3 | ~9 MB | Active (latest) |
| Other | 14 | ~12.1 GB | Various validation/analysis |
| **TOTAL** | **118** | **~15 GB** | |

### 7.2 Archivable

v6 + v7 + v8 outputs = **~2.4 GB**. These correspond to rejected algorithm iterations (per MEMORY.md, V8 complexity adds ZERO value over VTREND). The largest single artifact is `out_v7_hybrid_manual_trail_scan_1771609305` at **779 MB** — an exhaustive parameter grid that led to the rejection of v7 pivot scoring.

---

## 8. Namespace Confusion

### 8.1 Two `bootstrap.py` with Same Name, Different Content

```
research/lib/bootstrap.py    → VCBB (path generation)
v10/research/bootstrap.py    → Paired block bootstrap (CI comparison)
```

The name collision is confusing but not a bug. Recommendation: rename `research/lib/bootstrap.py` → `research/lib/vcbb.py` to disambiguate.

### 8.2 Two `selection_bias.py` with Inline DSR

```
validation/suites/selection_bias.py       → Active (has inline DSR copy)
v10/validation/suites/selection_bias.py   → Dead (has inline DSR copy)
```

The active copy should import from `research/lib/dsr.py`.

---

## 9. Full Dead Code Inventory

| Item | LOC | Size | Reason Dead |
|------|-----|------|-------------|
| `v10/validation/__init__.py` | 1 | 50 B | Part of dead framework |
| `v10/validation/cli.py` | 110 | 4 KB | Superseded by `validation/cli.py` |
| `v10/validation/config.py` | 139 | 5 KB | Superseded by `validation/config.py` |
| `v10/validation/decision.py` | 110 | 4 KB | Superseded by `validation/decision.py` |
| `v10/validation/output.py` | 144 | 5 KB | Superseded by `validation/output.py` |
| `v10/validation/report.py` | 144 | 5 KB | Superseded by `validation/report.py` |
| `v10/validation/runner.py` | 211 | 7 KB | Superseded by `validation/runner.py` |
| `v10/validation/strategy_factory.py` | 82 | 3 KB | Superseded by `validation/strategy_factory.py` |
| `v10/validation/suites/__init__.py` | 1 | 50 B | Part of dead framework |
| `v10/validation/suites/backtest.py` | ~100 | 3 KB | Superseded |
| `v10/validation/suites/base.py` | ~70 | 2 KB | Superseded |
| `v10/validation/suites/bootstrap.py` | 141 | 5 KB | Superseded |
| `v10/validation/suites/dd_episodes.py` | ~80 | 3 KB | Superseded |
| `v10/validation/suites/holdout.py` | ~100 | 4 KB | Superseded |
| `v10/validation/suites/lookahead.py` | ~80 | 3 KB | Superseded |
| `v10/validation/suites/overlay.py` | ~100 | 4 KB | Superseded |
| `v10/validation/suites/regime.py` | ~80 | 3 KB | Superseded |
| `v10/validation/suites/selection_bias.py` | ~160 | 6 KB | Superseded |
| `v10/validation/suites/sensitivity.py` | ~100 | 4 KB | Superseded |
| `v10/validation/suites/subsampling.py` | ~100 | 4 KB | Superseded |
| `v10/validation/suites/trade_level.py` | 188 | 7 KB | Superseded |
| `v10/validation/suites/wfo.py` | 119 | 4 KB | Superseded |
| **TOTAL** | **~2,856** | **~87 KB** | |

---

## 10. Recommendations (Prioritized)

### P0 — No Action Required (Confirmed NOT Duplicates)
- `research/lib/bootstrap.py` (VCBB) vs `v10/research/bootstrap.py` (paired CI) — different algorithms, both live
- 5 research/runner scripts — all registered and active

### P1 — Document as Dead
- **`v10/validation/`** (22 files, ~2,856 LOC): Zero external imports. Can be archived.
- No risk — nothing imports from it.

### P2 — Fix Code Duplication
- **DSR**: `validation/suites/selection_bias.py` should import from `research.lib.dsr` (removes 30 lines of inferior inline math)
- **Annualization**: Unify `PERIODS_PER_YEAR_4H` to `6.0 * 365.25 = 2191.5` across `v10/` modules

### P3 — Improve Naming
- Rename `research/lib/bootstrap.py` → `research/lib/vcbb.py` to avoid confusion with `v10/research/bootstrap.py`

### P4 — Archive Outputs
- Archive `out_v6_*`, `out_v7_*`, `out_v8_*` (~2.4 GB) — keep 1 representative per version for regression
- The 779 MB `out_v7_hybrid_manual_trail_scan` alone accounts for 5% of total output

### P5 — Mark Legacy
- Add `v6/LEGACY.md` and `v7/LEGACY.md` noting these are referenced by live bots but not part of current research pipeline

---

## 11. Artifacts

| File | Description |
|------|-------------|
| `research_reports/04_code_duplication_legacy_audit.md` | This report |

---

*Report generated 2026-03-03 by Claude Opus 4.6. No production code was modified.*
