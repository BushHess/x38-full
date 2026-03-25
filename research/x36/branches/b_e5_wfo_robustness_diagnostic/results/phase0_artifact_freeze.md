# Phase 0 — Artifact Freeze

- Source dir: `/var/www/trading-bots/btc-spot-dev/results/full_eval_e5_ema21d1`
- Source timestamp: `2026-03-16T20:22:51Z`
- Canonical verdict: `HOLD`
- Canonical failures: `wfo_robustness_failed`
- Canonical warnings: `Holdout/WFO overlap detected: 184 days (35.3% of holdout period)`

## Frozen Run Config

- Period: `2019-01-01 -> 2026-02-20`
- Warmup days: `365`
- Initial cash: `10000.0`
- Harsh cost bps RT: `50.0`
- WFO: train `24m`, test `6m`, slide `6m`, cap `8`

## Canonical WFO Snapshot

- Windows valid: `8/8`
- Power windows: `8`
- Invalid windows: `0`
- Low-trade windows: `0`
- Low-power delegation active: `False`
- Positive windows: `5`
- Win rate: `0.625`
- Mean delta score: `12.4563`
- Wilcoxon p: `0.125`
- Bootstrap CI: `[-3.4378, 29.279]`
