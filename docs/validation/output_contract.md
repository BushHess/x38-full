# Output Contract

Tài liệu chuẩn cho artifacts do `validate_strategy.py` tạo trong `--out <dir>`.

Runner kiểm tra contract ở cuối run. Nếu thiếu file bắt buộc -> verdict `ERROR`, exit code `3`.

## Always required

- `logs/run.log`
- `configs/candidate_<name>.yaml`
- `configs/baseline_<name>.yaml`
- `reports/validation_report.md`
- `reports/quality_checks.md`
- `reports/decision.json`
- `reports/discovered_tests.md`
- `reports/audit_effective_config.md`
- `reports/audit_score_decomposition.md`
- `results/effective_config_candidate.json`
- `results/effective_config_baseline.json`
- `results/config_used_fields.json`
- `results/config_unused_fields.json`
- `index.txt`

## Required by suite/flag

### Backtest

- `results/full_backtest_summary.csv`
- `results/score_breakdown_full.csv`
- `results/add_throttle_stats.json`

### Regime

- `results/regime_decomposition.csv`

### WFO

- `results/wfo_per_round_metrics.csv`
- `results/wfo_summary.json`
- `reports/audit_wfo_invalid_windows.md`

### Bootstrap (`--bootstrap > 0`)

- `results/bootstrap_paired_test.csv`

### Subsampling (`--subsampling`)

- `results/subsampling_paired_test.csv`

### Sensitivity (`--sensitivity-grid`)

- `results/sensitivity_grid.csv`

### Holdout

- `results/final_holdout_metrics.csv`
- `results/score_breakdown_holdout.csv`

### Selection bias (`--selection-bias != none`)

- `results/selection_bias.json`

### Lookahead (`--lookahead-check on`)

- `results/lookahead_check.txt`

### Trade-level (`--trade-level on`, `suite=trade/all`, hoặc auto-enable do low-trade WFO)

- `results/trades_candidate.csv`
- `results/trades_baseline.csv`
- `results/matched_trades.csv`
- `results/regime_trade_summary.csv`
- `results/window_trade_counts.csv`
- `results/bootstrap_return_diff.json`
- `reports/trade_level_analysis.md`

### DD episodes (`--dd-episodes on` hoặc `suite=dd/all`)

- `results/dd_episodes_candidate.csv`
- `results/dd_episodes_baseline.csv`

### Quality checks

- Data integrity (`--data-integrity-check on`)
  - `results/data_integrity.json`
  - `results/data_integrity_issues.csv`
- Cost sweep (`--cost-sweep-bps ...`)
  - `results/cost_sweep.csv`
- Invariants (`--invariant-check on`)
  - `results/invariant_violations.csv`
- Regression guard (`--regression-guard on`)
  - `results/regression_guard.json`
- Churn metrics (`--churn-metrics on`)
  - `results/churn_metrics.csv`

## Report structure: `reports/validation_report.md`

Sections appear in this order (conditional sections omitted when empty):

1. **Header** — candidate, baseline, dataset, period, suite, seed.
2. **Decision** — verdict tag, exit code, reasons.
3. **Gate Summary** — table of all gate checks (name, status, severity, detail).
   Pipe characters in detail are escaped (`\|`) to prevent table breakage.
4. **Key Deltas** — all diagnostic values from `decision.deltas`.
5. **Warnings** — `decision.warnings` (overlap, low-power WFO, cost sweep, churn).
   Only rendered if warnings list is non-empty.
6. **Errors** — `decision.errors` (suite errors, data integrity, invariants,
   regression guard). Only rendered if errors list is non-empty.
7. **Suite Results** — per-suite status, duration, artifacts, and suite-specific
   tables (backtest rows, WFO summary, bootstrap gate, trade-level stats, churn).
8. **Additional checks** — discovered tests from `reports/discovered_tests.md`.

## Report structure: `reports/decision.json`

Top-level keys: `verdict`, `exit_code`, `deltas`, `trade_level_bootstrap`,
`failures`, `warnings`, `errors`, `reasons`, `key_links`, `gates`, `metadata`.

## Khuyến nghị audit nhanh

1. Mở `index.txt` để xem danh sách file thực tế.
2. Mở `reports/decision.json` để xác nhận gate pass/fail.
3. Nếu fail contract, đọc `logs/run.log` để thấy danh sách file thiếu.
