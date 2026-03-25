# Audit Report 05: Code Cleanup Execution

**Date**: 2026-03-03
**Auditor**: Claude Opus 4.6
**Scope**: 4 issues identified in Report 04
**Status**: All 4 issues resolved. Tests pass.

---

## Issue 1: Delete Dead `v10/validation/` Framework

### Pre-conditions Verified

| Check | Result |
|-------|--------|
| External imports from `v10.validation` | **ZERO** — `grep -r "from v10\.validation" | grep -v v10/validation/` → empty |
| Entry point `validate_strategy.py` | Imports `from validation.cli import main` (top-level, NOT v10) |
| Newer files in v10? | Timestamps within seconds (batch edit artifact), v10 content is strict subset |

### Action

```
rm -rf v10/validation/
```

### Files Deleted (22)

| Directory | Files |
|-----------|-------|
| `v10/validation/` | `__init__.py`, `cli.py`, `config.py`, `decision.py`, `output.py`, `report.py`, `runner.py`, `strategy_factory.py` |
| `v10/validation/suites/` | `__init__.py`, `backtest.py`, `base.py`, `bootstrap.py`, `dd_episodes.py`, `holdout.py`, `lookahead.py`, `overlay.py`, `regime.py`, `selection_bias.py`, `sensitivity.py`, `subsampling.py`, `trade_level.py`, `wfo.py` |

### What Remains in `v10/`

| Subdirectory | Status | Reason |
|-------------|--------|--------|
| `v10/core/` | **LIVE** | Engine, types, data — imported by `validation/` and research |
| `v10/research/` | **LIVE** | `bootstrap.py` (paired CI), `subsampling.py`, `wfo.py` — imported by `validation/suites/` |
| `v10/strategies/` | **LIVE** | Strategy implementations |
| `v10/tests/` | **LIVE** | Unit tests for v10/research (25 tests, all pass) |

---

## Issue 2: Consolidate DSR (Deflated Sharpe Ratio)

### Problem

Three implementations of the same Bailey & López de Prado (2014) math:
- `research/lib/dsr.py` — canonical, 19 tests, uses `NormalDist` (exact)
- `validation/suites/selection_bias.py` lines 21-51 — inline copy, uses Abramowitz & Stegun probit approximation
- `v10/validation/suites/selection_bias.py` — another inline copy (deleted in Issue 1)

### Solution

1. Added `deflated_sharpe()` to `research/lib/dsr.py` with the **exact same interface** as the inline `_deflated_sharpe()`:

```python
def deflated_sharpe(
    sr_observed: float,
    n_trials: int,
    t_samples: int,
    skew: float,
    kurt: float,
) -> tuple[float, float, float]:
    """Returns (dsr_pvalue, expected_max_sr, sr_std)"""
```

2. Replaced 30 lines of inline DSR math in `validation/suites/selection_bias.py` with:

```python
from research.lib.dsr import deflated_sharpe as _deflated_sharpe
```

3. Removed unused `import math` from `selection_bias.py`.

### Cross-validation

```
compute_dsr  pvalue: 0.046974
deflated_sharpe pv: 0.047417
Delta: 0.00044  (from ddof=1 vs T difference — matches original inline behavior)
```

### Improvements Over Inline Version

| Aspect | Old (inline) | New (canonical) |
|--------|-------------|-----------------|
| Euler-Mascheroni γ | `0.5772156649` (10 digits) | `0.5772156649015329` (16 digits) |
| Probit function | Abramowitz & Stegun rational approx (error < 4.5e-4) | `NormalDist.inv_cdf()` (exact) |
| Normal CDF | `erf()` approximation | `NormalDist.cdf()` (exact) |
| Unit tests | 0 | 19 |

---

## Issue 3: Rename `research/lib/bootstrap.py` → `vcbb.py`

### Action

```
mv research/lib/bootstrap.py research/lib/vcbb.py
```

### Imports Updated (12 files)

| File | Old Import | New Import |
|------|-----------|------------|
| `research/config_compare.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/creative_exploration.py` | `from lib.bootstrap import` | `from lib.vcbb import` |
| `research/ema_ablation.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/multicoin_diversification.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/multicoin_ema_regime.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/trail_sweep.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/vtrend_param_sensitivity.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/vcbb_vs_uniform.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/validate_bootstrap.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/e5_vcbb_test.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/binomial_correction.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |
| `research/audit_phase1_3.py` | `from research.lib.bootstrap import` | `from research.lib.vcbb import` |

### Docstring Updated

Module docstring changed from "Shared block bootstrap module" to "Volatility-Conditioned Block Bootstrap (VCBB)".

### Remaining `bootstrap.py` (NOT renamed — different algorithm)

`v10/research/bootstrap.py` — paired block bootstrap for equity curve CI. This is a **different algorithm** (statistical comparison, not path generation). Keeping the name `bootstrap.py` is correct since it's the standard Politis & Romano paired block bootstrap.

---

## Issue 4: Remove Old Uniform Bootstrap, Migrate to VCBB

### Functions Removed from `research/lib/vcbb.py`

| Function | LOC | Reason |
|----------|-----|--------|
| `gen_path()` | 13 | Superseded by `gen_path_vcbb()` |
| `gen_path_6ch()` | 12 | Superseded; **zero** external callers |
| `gen_path_vcbb_6ch()` | 12 | **Zero** external callers |
| `make_ratios_6ch()` | 12 | **Zero** external callers |
| `_select_blocks_uniform()` | 3 | Internal helper for `gen_path()` |
| `_build_path_6ch()` | 28 | Internal helper for removed 6ch functions |
| **Total removed** | **80 LOC** | |

### Functions Retained in `research/lib/vcbb.py`

| Function | Purpose |
|----------|---------|
| `VCBBState` | Precomputed vol lookup dataclass |
| `make_ratios()` | Convert OHLCV to 5-channel ratios (shared) |
| `precompute_vcbb()` | One-time O(N log N) vol precomputation |
| `gen_path_vcbb()` | VCBB path generation (5-channel) |
| `_build_idx()` | Internal: flat index from block starts |
| `_build_path_5ch()` | Internal: reconstruct price path |
| `_compute_rvol()` | Internal: rolling realized vol |
| `_knn_select()` | Internal: K-nearest-neighbor vol matching |
| `_select_blocks_vcbb()` | Internal: VCBB block selection |

### Scripts Migrated to `gen_path_vcbb` (11 files)

**Group A — Import-only (8 scripts, used `gen_path` from library):**

| File | Changes |
|------|---------|
| `research/config_compare.py` | Import updated, added `precompute_vcbb`, migrated 1 call |
| `research/creative_exploration.py` | Import updated, added `precompute_vcbb`, migrated 1 call |
| `research/ema_ablation.py` | Import updated, added `precompute_vcbb`, migrated 1 call |
| `research/multicoin_diversification.py` | Import updated, added `precompute_vcbb` per-coin, migrated 1 call |
| `research/multicoin_ema_regime.py` | Import updated, added `precompute_vcbb`, migrated 1 call |
| `research/trail_sweep.py` | Import updated, added `precompute_vcbb`, migrated 1 call |
| `research/vtrend_param_sensitivity.py` | Import updated, added `precompute_vcbb`, migrated 1 call |
| `research/audit_phase1_3.py` | Cross-check test (Test 7) updated to skip — no longer meaningful |

**Group B — Comparative scripts (3 scripts, used both `gen_path` and `gen_path_vcbb`):**

| File | Changes |
|------|---------|
| `research/vcbb_vs_uniform.py` | Removed `gen_path` import, replaced 1 uniform call with VCBB |
| `research/validate_bootstrap.py` | Removed `gen_path` import, replaced 3 uniform calls with VCBB |
| `research/e5_vcbb_test.py` | Removed `gen_path` import, replaced 1 uniform call with VCBB |

**Group C — Standalone scripts (22 scripts with LOCAL `gen_path` definitions):**

Not modified. These scripts define `gen_path` inline (copy-pasted uniform bootstrap). They are self-contained research studies with results already saved. They do not depend on the library.

### Migration Pattern

```python
# BEFORE:
from research.lib.bootstrap import make_ratios, gen_path
cr, hr, lr, vol, tb = make_ratios(cl, hi, lo, vo, tb_raw)
# ... in loop:
c, h, l, v, t = gen_path(cr, hr, lr, vol, tb, n_trans, BLKSZ, p0, rng)

# AFTER:
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
cr, hr, lr, vol, tb = make_ratios(cl, hi, lo, vo, tb_raw)
vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
# ... in loop:
c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tb, n_trans, BLKSZ, p0, rng, vcbb=vcbb_state)
```

---

## Verification

### Syntax Check

All 12 modified research scripts pass `py_compile`:

```
OK: research/vcbb_vs_uniform.py
OK: research/validate_bootstrap.py
OK: research/e5_vcbb_test.py
OK: research/config_compare.py
OK: research/creative_exploration.py
OK: research/ema_ablation.py
OK: research/multicoin_diversification.py
OK: research/multicoin_ema_regime.py
OK: research/trail_sweep.py
OK: research/vtrend_param_sensitivity.py
OK: research/audit_phase1_3.py
OK: research/binomial_correction.py
```

### Import Verification

```
vcbb OK       — from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
dsr OK        — from research.lib.dsr import compute_dsr, deflated_sharpe, benchmark_sr0
selection_bias OK — from validation.suites.selection_bias import SelectionBiasSuite
```

### Unit Tests

| Suite | Result |
|-------|--------|
| `research/lib/test_dsr.py` | **19/19 passed** |
| `v10/tests/test_bootstrap.py` | **16/16 passed** |
| `v10/tests/test_subsampling.py` | **9/9 passed** |

### Remaining Grep

```
grep -rn "from.*vcbb import.*\bgen_path\b" --include="*.py" | grep -v gen_path_vcbb
→ (empty — zero remaining imports of removed gen_path)

grep -rn "lib\.bootstrap" --include="*.py" | grep -v __pycache__ | grep -v research_reports/
→ (empty — zero remaining references to old filename)

grep -rn "from v10\.validation" --include="*.py" | grep -v __pycache__ | grep -v v10/validation/
→ (empty — zero references to deleted framework)
```

---

## Summary of Changes

| Category | Files Modified | Files Deleted | LOC Removed |
|----------|---------------|---------------|-------------|
| Issue 1: Dead framework | 0 | 22 | ~2,856 |
| Issue 2: DSR consolidation | 2 (dsr.py, selection_bias.py) | 0 | 30 removed, 40 added |
| Issue 3: Rename | 12 (imports) + 1 (file) | 0 | 0 |
| Issue 4: Remove uniform | 1 (vcbb.py) + 11 (scripts) | 0 | 80 removed |
| **Total** | **27 files** | **22 files** | **~2,866 net** |

---

## Note on Group C Scripts (22 with inline `gen_path`)

These scripts contain their own copy-pasted `gen_path()` definitions. They are standalone research studies that have already been run (results in `research/results/`). They are NOT affected by the library cleanup because they don't import from the library. Examples:

- `bootstrap_regime.py`, `v8_vs_vtrend_bootstrap.py` — registered in `run_all_studies.sh`
- `timescale_robustness.py`, `e5_validation.py`, `e7_study.py` — parameter studies
- `cost_study.py`, `pe_study.py` — cost/PE analysis

If these scripts need to be re-run in the future, they should be updated to use `gen_path_vcbb` from `research.lib.vcbb`. For now, they remain functional with their local definitions.

---

*Report generated 2026-03-03 by Claude Opus 4.6.*
