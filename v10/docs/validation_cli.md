# Validation CLI

Strategy-agnostic backtest validation pipeline. Runs 11 suites against a candidate/baseline pair and outputs a standardized validation pack.

## Quick Start

```bash
# Full validation: E5_ema21D1 vs E0 baseline (recommended)
python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_val_e5_ema21d1 --suite full --bootstrap 2000

# Basic suite (no sensitivity/holdout/selection-bias)
python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_val_quick --suite basic

# Trade-level analysis
python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_val_trades --suite trade --trade-level

# All suites including selection-bias PSR gate
python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_val_all --suite all

# Smoke test (no bootstrap, fast)
python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1 --baseline vtrend \
  --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out_val_smoke --suite basic --bootstrap 0
```

## CLI Arguments

### Required
| Arg | Description |
|-----|-------------|
| `--strategy` | Candidate strategy name (e.g. `vtrend_e5_ema21_d1`, `vtrend_ema21_d1`, `vtrend`) |
| `--baseline` | Baseline strategy name |
| `--config` | Path to candidate YAML config |
| `--baseline-config` | Path to baseline YAML config |
| `--out` | Output directory |

### Data
| Arg | Default | Description |
|-----|---------|-------------|
| `--dataset` | `data/bars_btcusdt_2016_now_h1_4h_1d.csv` | Path to dataset CSV |
| `--start` | `2019-01-01` | Backtest start date |
| `--end` | `2026-02-20` | Backtest end date |
| `--warmup-days` | `365` | Warmup period in days |
| `--initial-cash` | `10000` | Starting capital |

### Suite Selection
| Arg | Default | Description |
|-----|---------|-------------|
| `--suite` | `full` | Suite group: `basic`, `full`, `trade`, `dd`, `overlay`, `all` |
| `--scenarios` | `smart base harsh` | Cost scenarios to run |
| `--trade-level` | off | Enable trade-level analysis |
| `--dd-episodes` | off | Enable drawdown episode detection |
| `--overlay-test` | off | Enable overlay comparison |
| `--no-lookahead` | off | Disable lookahead check |

### Suite Groups
| Group | Suites |
|-------|--------|
| `basic` | backtest, regime, wfo, bootstrap |
| `full` | basic + sensitivity, holdout, selection_bias, lookahead |
| `trade` | backtest, trade_level |
| `dd` | backtest, dd_episodes |
| `overlay` | backtest, overlay |
| `all` | all 11 suites |

### Bootstrap
| Arg | Default | Description |
|-----|---------|-------------|
| `--bootstrap` | `2000` | Number of resamples (0=disable) |
| `--bootstrap-block-sizes` | `10 20 40` | Block sizes for block bootstrap |

### Walk-Forward
| Arg | Default | Description |
|-----|---------|-------------|
| `--wfo-train-months` | `24` | Training window size |
| `--wfo-test-months` | `6` | Test window size |
| `--wfo-slide-months` | `6` | Slide step |

### Other
| Arg | Default | Description |
|-----|---------|-------------|
| `--seed` | `42` | Random seed |
| `--force` | off | Force re-run |
| `--force-holdout` | off | Force holdout even if lock exists |
| `--holdout-frac` | `0.2` | Holdout fraction |
| `--sensitivity-grid` | auto | JSON dict of param grids |
| `--selection-bias` | `deflated` | `none`, `pbo`, or `deflated` |

## Output Structure

```
out/
  run_meta.json                 # git hash, argv, data fingerprint
  index.txt                     # file listing + verdict summary
  logs/
    run.log                     # full debug log
  configs/
    candidate_*.yaml            # copied configs
    baseline_*.yaml
  results/
    backtest_summary.csv
    backtest_detail.json
    regime_decomposition.csv
    regime_decomposition.json
    wfo_per_round.csv
    wfo_summary.json
    bootstrap_paired.csv        # if bootstrap>0
    bootstrap_summary.json
    sensitivity_grid.csv        # if enabled
    sensitivity_detail.json
    holdout_metrics.csv
    holdout_detail.json
    holdout_regime.csv
    holdout_lock.json
    selection_bias.json         # if enabled
    lookahead_check.txt
    trades_candidate.csv        # if --trade-level
    trades_baseline.csv
    matched_trades.csv
    regime_trade_summary.csv
    trade_level_summary.json
    dd_episodes_candidate.csv   # if --dd-episodes
    dd_episodes_baseline.csv
    dd_episodes_summary.json
    overlay_comparison.json     # if --overlay-test
    overlay_wfo.csv
  reports/
    validation_report.md
    decision.json
```

## Decision Policy

The CLI produces a verdict:

| Verdict | Exit Code | Meaning |
|---------|-----------|---------|
| **PROMOTE** | 0 | All gates passed — safe to deploy |
| **HOLD** | 1 | Soft gate(s) failed — needs review |
| **REJECT** | 2 | Hard gate(s) failed — do not deploy |

### Hard Gates (veto power)
- **Lookahead**: pytest must pass (exit code 0)
- **Min trades**: candidate must have >= 10 trades under harsh scenario

### Soft Gates (advisory)
- **WFO win rate**: >= 60% windows with positive delta
- **Bootstrap**: P(candidate better) >= 80% AND CI lower > -0.01
- **Holdout**: candidate harsh score >= baseline - 0.2
- **Selection bias**: DSR passes at all tested N levels

## Architecture

```
CLI args → cli.py::main()
  → ValidationConfig
  → ValidationRunner(config)
      → DataFeed (loaded once, shared)
      → SuiteContext (feed, factories, configs, paths)
      → for suite in resolved_suites:
            suite.run(ctx) → SuiteResult
      → evaluate_decision(results) → DecisionVerdict
      → generate_validation_report()
      → sys.exit(verdict.exit_code)
```

### 11 Suites
1. **lookahead** — pytest HTF lookahead tests
2. **backtest** — full-period backtest × scenarios (candidate + baseline)
3. **regime** — regime decomposition (SHOCK/BEAR/CHOP/TOPPING/BULL/NEUTRAL)
4. **wfo** — walk-forward per-window OOS testing
5. **bootstrap** — paired + individual block bootstrap
6. **sensitivity** — parameter perturbation grid
7. **holdout** — one-shot holdout with lock file
8. **selection_bias** — Deflated Sharpe Ratio + optional CSCV/PBO
9. **trade_level** — trade export, matching, regime enrichment
10. **dd_episodes** — drawdown episode detection and comparison
11. **overlay** — with-overlay vs without-overlay comparison
