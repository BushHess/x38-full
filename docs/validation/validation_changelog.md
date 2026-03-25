# Validation Changelog

## 2026-03-16 — Robustness Fixes

### Fixed

- **selection_bias fallback bypass**: Decision engine now detects when the suite
  fell back from `pbo` to `none` (via `requested_method != method` or
  `fallback_reason` present). Gate unconditionally FAILs on fallback, preventing
  false PROMOTE when PSR passes but PBO was never computed.
  Changed `bool(psr_pass)` → `_strict_bool(psr_pass)` to prevent string coercion.
  Same `_strict_bool` hardening applied to `wilcoxon_sufficient` and
  `bootstrap_excludes_zero` in WFO robustness gate.
- **PBO proxy sentinel corruption**: Windows where `compute_objective()` returns
  the -1M reject sentinel (n_trades < 10) are now excluded from PBO
  `negative_delta_ratio` inference. Reports `n_windows_rejected` in
  `selection_bias.json`.
- **Holdout/WFO overlap off-by-one**: Changed from exclusive to inclusive
  end-date math (`+1` day). DataFeed `end` is inclusive (see `data.py` line 78),
  so `holdout_days` and `overlap_days` now use `(end - start).days + 1`.
  Previously, a 31-day inclusive overlap was computed as 30, potentially missing
  the `>30` warning threshold. Same fix applied to `holdout.py:_resolve_holdout_window`
  where `total_days` was 1 day short, shifting the auto-computed holdout boundary.
  Same fix applied to `scripts/p1_add_throttle_grid_3x3.py` and
  `research/x0_drought_analysis/p0_1_x0e5_drought.py` (rolling window length).
- **Warnings/errors not rendered**: `decision.warnings` and `decision.errors` are
  now rendered as dedicated sections in `validation_report.md`. Overlap warnings
  from `decision.deltas` are collected into `decision.warnings`. WFO low-power
  warning is emitted whenever low power is detected, not only when trade_level
  is also auto-enabled. Pipe characters in gate detail are escaped (`\|`) to
  prevent markdown table breakage.
- **trade_level format crash**: `ci_up` raw dict value now passed through
  `_safe_float()` before `:.4f` formatting (prevents crash if value is string).

### Cleaned

- Removed dead `is not None` guards on `_safe_float()` return values in
  `trade_level_bootstrap` gate logic (always returns float, never None).
- Removed redundant `_safe_float()` wrapping on variables already converted.

## 2026-03-09 — Framework Reform

### Added

- Wilcoxon signed-rank test for WFO round deltas (replaces binary win-rate as gate)
- Bootstrap CI for WFO deltas
- PSR (Probabilistic Sharpe Ratio) gate in `selection_bias` suite (threshold=0.95)
- Holdout/WFO overlap detection and reporting

### Changed

- WFO gate now uses Wilcoxon p-value (< α=0.1) instead of binary win-rate threshold
- Selection bias suite adds PSR check: candidate Sharpe must be statistically
  distinguishable from selection noise at PSR ≥ 0.95

### Impact

- E5_ema21D1: all 7 gates PASS, PSR=0.9993 → PROMOTE
- E0_ema21D1: PSR=0.8908 < 0.95 → HOLD (was PROMOTE under old framework)

## 2026-02-24

### Added

- Unified CLI entrypoint: `validate_strategy.py`
- New package: `validation/` with modular suites:
  - `backtest`
  - `regime`
  - `wfo`
  - `bootstrap`
  - `sensitivity`
  - `holdout`
  - `selection_bias`
  - `lookahead`
  - `trade_level`
  - `dd_episodes`
  - `overlay`
- Discovery report: `reports/discovered_tests.md`
- Output-contract verification at end of run (missing required files -> exit `3`)
- Acceptance tests: `validation/tests/test_acceptance.py`

### Changed

- Decision engine chuẩn hóa gate cứng/mềm với payload `reports/decision.json`
- WFO low-trade handling:
  - auto-enable `trade_level` khi có low-trade windows
  - emit warning trong `validation_report.md` và `run.log`
- Chuẩn hóa tên output chính:
  - `full_backtest_summary.csv`
  - `wfo_per_round_metrics.csv`
  - `bootstrap_paired_test.csv`
  - `final_holdout_metrics.csv`

### Notes

- Nếu update threshold/gate/output name trong tương lai, phải cập nhật đồng thời:
  1. `docs/validation/decision_policy.md`
  2. `docs/validation/output_contract.md`
  3. file này (`validation_changelog.md`)

