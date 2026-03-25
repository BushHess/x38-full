# X36: V3 vs V4 vs E5+EMA21D1 — Comprehensive Comparison

**Date**: 2026-03-15 | **Cost**: 20 bps RT | **Bootstrap**: 500 VCBB paths

> Status note (2026-03-17): this branch is a frozen historical comparison study.
> Current validation authority lives in `validation/` plus the active x36 branch.
> Quantitative authority inside this branch is `results/*.csv`, `results/*.json`,
> and `results/comparison_report.md`.

## Quick Navigation

- **[METHODOLOGY.md](METHODOLOGY.md)** — Legacy evaluation framework + validation references
- **[CONCLUSIONS.md](results/CONCLUSIONS.md)** — Historical narrative snapshot
- **[comparison_report.md](results/comparison_report.md)** — Tables + chart references
- **[../../program/02_methodology_consistency_audit.md](../../program/02_methodology_consistency_audit.md)** — authority and caveats

## Results Summary

| | V3 | V4 | E5+EMA21D1 |
|--|----|----|------------|
| Full-sample Sharpe | 1.496 | **1.789** | 1.664 |
| Bootstrap median Sharpe | 0.507 | 0.744 | **0.768** |
| P(Sharpe > 0) | 89.0% | 96.8% | **97.0%** |
| WFO positive windows | **11/12** | 10/12 | 10/12 |
| Holdout Sharpe | **1.899** | 1.211 | 1.285 |

**Historical branch-local verdict**: E5+EMA21D1 leads the branch-local bootstrap layer,
while V3/V4 lead other descriptive layers. Do not read this as the current repo-wide
validation verdict.

## File Structure

```
x36/branches/a_vcbb_bias_study/
├── README.md                  # This file
├── METHODOLOGY.md             # Reusable evaluation framework
├── run_comparison.py          # Main experiment runner
├── v3v4_strategies.py         # V3 + V4 strategy implementations
├── regen_report.py            # Report regenerator (from saved data)
├── results/
│   ├── CONCLUSIONS.md         # Full experimental conclusions
│   ├── comparison_report.md   # Formatted comparison tables
│   ├── full_sample_metrics.csv
│   ├── holdout_metrics.csv
│   ├── wfo_results.csv
│   ├── cost_sweep.csv
│   ├── regime_decomposition.csv
│   ├── trade_stats.csv
│   ├── bootstrap_summary.json
│   └── psr.json
└── figures/
    ├── equity_drawdown.png
    ├── bootstrap_distributions.png
    ├── wfo_sharpe.png
    ├── cost_sensitivity.png
    └── regime_decomposition.png
```

## Reproducing

```bash
cd /var/www/trading-bots/btc-spot-dev
source /var/www/trading-bots/.venv/bin/activate
PYTHONUNBUFFERED=1 python research/x36/branches/a_vcbb_bias_study/run_comparison.py
# ~25 minutes (bootstrap is the bottleneck)
```
