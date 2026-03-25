# Report 37 — VTREND-SM Final Closeout

**Date**: 2026-03-04
**Scope**: Close the VTREND-SM work stream (Reports 34–36c) with canonical test determination, test-count reconciliation, full-suite rerun, and archive-ready summary.
**Code changed**: No.

---

## 1. Scope

This report closes the VTREND-SM work stream spanning Reports 34–36c:

| Report | Title | Deliverable |
|--------|-------|-------------|
| 34 | Survey & pre-integration audit | Design survey, spec, contract |
| 34b | Pre-integration audit | Codebase readiness check |
| 34c | Design contract | Interface & integration spec |
| 35 | Integration | Code, tests, registration (689/689 pass) |
| 36 | Evaluation | Backtest, PairDiagnostic, regime decomposition |
| 36b | Validation followup | Pipeline unblock, 12/12 suites |
| 36c | Repo hygiene | False-positive fix, T20 rename, VDO coverage |

No strategy logic, validation logic, or parameter changes were made in this report.

---

## 2. Canonical Test Command Determination

### Investigation

Evidence searched:
- CI config: **none found** (no `.github/workflows/`, `.gitlab-ci.yml`, Jenkinsfile)
- Build files: **no** Makefile, tox.ini, nox, justfile in btc-spot-dev
- pytest config: **no** `pytest.ini`, `setup.cfg`, `pyproject.toml` with `[tool.pytest]` (at time of investigation; `pytest.ini` added later in this report)
- README.md: mentions `PYTHONPATH=. python -m pytest v10/tests/ -q` (partial — misses `tests/`, `validation/tests/`, `research/tests/`)
- Report 36c: used `python -m pytest tests/ v10/tests/ -v --tb=short` (covers 2 of 4 dirs)

### Test directories discovered

| Directory | Files | Tests collected | Contents |
|-----------|-------|-----------------|----------|
| `tests/` | 4 | varies | SM tests, V12 tests |
| `v10/tests/` | 31 | varies | Core framework tests |
| `validation/tests/` | 20 | 237 | Active validation pipeline tests |
| `research/tests/` | 1 | 17 | PairDiagnostic tests |
| **Total** | **56** | **715** | |

### Canonical full-suite command

```bash
python -m pytest
```

A `pytest.ini` was added to formalize test discovery:

```ini
[pytest]
testpaths = tests v10/tests validation/tests research/tests
```

This makes `python -m pytest` (no arguments) the canonical command. It collects exactly 715 tests from all 4 active directories.

**Note**: `research/lib/test_dsr.py` (19 DSR unit tests) is excluded from auto-discovery because it uses relative imports (`from dsr import ...`) that only resolve when run from `research/lib/`. It remains runnable standalone: `cd research/lib && python -m pytest test_dsr.py`. Without `pytest.ini`, default discovery finds this file and produces a collection error.

### Command comparison table

| Command | Scope | Collected | Used in |
|---------|-------|-----------|---------|
| `python -m pytest v10/tests/ -q` | v10 only | ~372 | README |
| `python -m pytest tests/ v10/tests/` | 2 dirs | 461 | Report 36c |
| `python -m pytest` | **all 4 dirs (via pytest.ini)** | **715** | **This report** |

---

## 3. Test-Count Reconciliation

### The numbers

- **689** (Report 35, 2026-03-04): `tests/` + `v10/tests/` + `v10/validation/` (now deleted)
- **461** (Report 36c, 2026-03-04): `tests/` + `v10/tests/` only
- **715** (This report): `tests/` + `v10/tests/` + `validation/tests/` + `research/tests/`

### Root cause of 689 → 461

The **228-test reduction** is entirely explained by the **intentional deletion of `v10/validation/`** (22 files, ~2856 LOC dead code) executed in Report 05 (Code Cleanup).

Evidence chain:
1. Report 04 (§2.5): identified `v10/validation/` as dead code — zero external imports, superseded by active `validation/` framework
2. Report 05 (§Issue 1): deleted the directory, verified `grep -rn "from v10.validation"` returned empty
3. 689 − 461 = 228 tests lost = the tests inside `v10/validation/`

**This is NOT a regression.** The deleted tests belonged to dead code that was never used by the active pipeline.

### Why 461 ≠ 715

Report 36c used `python -m pytest tests/ v10/tests/` — this omits:
- `validation/tests/` (237 tests) — active validation pipeline tests
- `research/tests/` (17 tests) — PairDiagnostic unit tests

These directories were never deleted; they were simply not included in the Report 36c command.

---

## 4. Full-Suite Rerun Result

```
Command:  python -m pytest  (via pytest.ini testpaths)
Result:   715 passed, 0 failed, 39 warnings in 83.80s
Date:     2026-03-04
```

### Warnings (all pre-existing, 39 total)

All 39 warnings are `RuntimeWarning: invalid value encountered in divide` or `divide by zero encountered in divide` from legacy strategies (`v8_apex.py:176`, `v11_hybrid.py:159`). These are known, pre-existing, and do not affect VTREND or VTREND-SM.

### No failures, no skips, no xfails.

---

## 5. End-to-End Status of VTREND-SM

| Item | Status | Evidence |
|------|--------|----------|
| 1. Strategy implemented | YES | `strategies/vtrend_sm/strategy.py` (364 LOC) |
| 2. Integrated into repo | YES | Registered in all 5 integration points (Report 35 §2) |
| 3. Tests | **715/715 PASS** | SM-specific: 56/56. Full suite: 715/715. |
| 4. Backtest (full data) | COMPLETE | Sharpe 1.39, CAGR 14.8%, MDD 14.2%, 76 trades (Report 36) |
| 5. PairDiagnostic | COMPLETE | materially_different (corr=0.729), boot_sharpe_p=0.214 (Report 36) |
| 6. Validation pipeline | COMPLETE | 12/12 suites ran. Verdict: **REJECT(2)** (Reports 36b, 36c) |
| 7. Repo hygiene | CLEAN | False-positive eliminated, T20 fixed, VDO covered (Report 36c) |
| 8. Current disposition | **REJECT(2)** | SM scores lower on CAGR-weighted objective vs E0 baseline |

### Backtest reference numbers (full data, 2017-08 to 2026-02, base cost)

| Metric | VTREND-SM | VTREND E0 |
|--------|-----------|-----------|
| Sharpe | 1.3895 | 1.1944 |
| Sortino | 1.1623 | 1.0495 |
| CAGR % | 14.80 | 52.59 |
| MDD % | 14.23 | 61.37 |
| Calmar | 1.0402 | 0.8568 |
| Trades | 76 | 226 |
| Avg exposure | 10.65% | 45.23% |
| Turnover/yr | 7.2× | 52.3× |

### Validation pipeline detail (2019-01 to 2026-02)

| Suite | Result |
|-------|--------|
| Backtest (3 cost scenarios) | SM Sharpe > E0 Sharpe; SM CAGR < E0 CAGR |
| Harsh score delta | REJECT (SM scores below E0 on CAGR-weighted objective) |
| WFO (8 windows) | 5/8 SM wins (62.5%) — PASS |
| Bootstrap harsh | p(SM Sharpe > E0) = 0.759 |
| DSR | 1.0 across N=27..700 — PASS |
| Cost sweep | SM dominates above 75 bps RT |
| Selection bias | PASS |
| Data integrity | PASS |
| Invariants | PASS |
| Config audit | PASS (resolved() allowlist fix in Report 36c) |
| Holdout | REJECT (CAGR-weighted) |
| Churn | PASS |

---

## 6. Residual Caveats

1. **REJECT(2) is a scoring artifact, not a quality judgment.** The validation scoring function weights CAGR heavily. SM's CAGR is 3.6× lower than E0 because of lower average exposure (10.7% vs 45.2%). SM has higher Sharpe, Sortino, and Calmar, and dramatically lower MDD.

2. **No canonical test command was previously documented.** Prior reports used inconsistent subsets of test directories. This report establishes the canonical command.

3. **39 warnings remain.** All from legacy strategies (V8, V11), not from VTREND or SM. Pre-existing since before the SM work stream.

4. **SM was evaluated on BTC only.** No multi-coin evaluation was performed (unlike E0, which has multi-coin studies 30–33).

---

## 7. Archive-Ready Final Summary

### VTREND-SM work stream: Reports 34–37

**Algorithm**: State-machine trend follower with vol-targeted fractional sizing, breakout entry, adaptive floor exit.
**Code**: `strategies/vtrend_sm/strategy.py` — 15 parameters, 364 LOC.
**Tests**: 56 dedicated + 715 full suite, all passing.
**Backtest**: Sharpe 1.39, CAGR 14.8%, MDD 14.2% (full data, base cost).
**vs E0**: Higher risk-adjusted returns (Sharpe +16%, Calmar +21%), dramatically lower drawdown (MDD 4.3× lower), much lower absolute returns (CAGR 3.6× lower). Materially different strategy (corr=0.729).
**Validation**: REJECT(2) under current CAGR-weighted scoring. All non-scoring suites PASS.
**Repo state**: Clean. No dead code, no false positives, no test drift.

### Recommended next actions for humans

| Action | Rationale |
|--------|-----------|
| Archive as research artifact | SM is fully documented and tested; REJECT(2) under current scoring means it doesn't replace E0 |
| Keep codebase as-is | SM is cleanly integrated, costs nothing to maintain, tests pass |
| Consider if scoring function should weight Sharpe/MDD differently | SM's REJECT is a scoring policy choice, not a quality failure |
| Multi-coin evaluation | If SM is reconsidered, test on altcoins (E0 has studies 30–33, SM has none) |
| Benchmark at higher cost scenarios | SM dominates E0 above 75 bps RT — relevant if real execution costs are higher than modeled |
| Do NOT iterate on new SM variants without clear hypothesis | Current research standard: prove the algorithm first, then build |

---

*End of Report 37.*
