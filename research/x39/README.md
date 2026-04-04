# x39 — Feature Invention Explorer

Tools to look at BTC H4 data and find what existing quantities don't capture.
52 experiments across 17 categories. **Status: CLOSED** (experiments complete).

## Key Result

**1 WFO-validated mechanism** out of 52 experiments: **vol compression entry gate**
(`vol_ratio_5_20 < threshold`). WFO 4/4, mean d_Sharpe +0.26, cost-independent.

Formal validation pending — see [Formal Validation](#formal-validation) below.

## Sections (explore.py)

1. **Anomaly Atlas** — Multi-dimensional outliers. Bars where multiple things are extreme simultaneously.
2. **Loss Anatomy** — Replay E5-ema21D1, compare entry features of winning vs losing trades.
3. **Residual Scan** — Which bar features predict returns AFTER conditioning on EMA/VDO/D1 regime?

## Usage

```bash
cd /var/www/trading-bots/btc-spot-dev
source /var/www/trading-bots/.venv/bin/activate
python research/x39/explore.py              # all sections
python research/x39/explore.py --section 3  # residual scan only
```

## Output

- `output/bar_features.csv` — Every H4 bar with ~25 features
- `output/anomalies_top100.csv` — 100 most unusual bars
- `output/trades.csv` — Replayed trades with entry features
- `output/residual_corr.csv` — Feature × fwd-return correlations conditioned on regime

## Experiments (52 total)

Master plan with all 52 experiments and verdicts: [PLAN.md](PLAN.md)

### Results by category

| Category | Experiments | WFO PASS | Key finding |
|----------|------------|----------|-------------|
| A-filter (entry gates) | 01-06 | 0 | D1 anti-vol = risk reducer, not alpha |
| B-replace (core swap) | 07-10 | 0 | Not executed (pending) |
| C-exit (exit signals) | 11-13 | 0 | rangepos exit promising but fragile (L=84) |
| D-compare (head-to-head) | 14-16 | — | E5 dominates Gen4 C3 and Gen1 V6 |
| E-ensemble (voting/OR) | 17-18 | 0 | E5 signal strictly dominant |
| F-stacked (stacked exits) | 19-24 | 0 | No stacked exit beats rangepos-only |
| G-robust (lookback) | 23 | 0 | rangepos L=84 is sharp peak, not plateau |
| H-validate (AND-gate) | 25-27, 30-31 | 0 | AND-gate WFO 2/4 FAIL (bear-only) |
| I-velocity (exit) | 28-29 | 0 | Velocity weaker than level-based exit |
| J-entry (new entry) | 32-39 | 1 | **Vol compression (exp34) → exp42 WFO PASS** |
| K-regime (adaptive) | 36-39 | 0 | Fixed params optimal (adaptive adds noise) |
| L-wfo (validation) | 40-42 | 1 | **exp42: 4/4 windows, d_Sharpe +0.26** |
| M-combo (stacking) | 43-45 | 0 | Compression + decay: decay adds zero OOS value |
| N-next (adaptive) | 46-47 | 0 | Regime-adaptive decay / accel trail both fail |
| O-screen (batch) | 48 | — | Only trendq_84 selective (1/7 features) |
| P-final (validation) | 49-50, 52 | 1 | Compression cost-independent (+0.17 Sh at 15 bps) |
| Q-newentry | 51 | 0 | Momentum persistence redundant with D1 EMA(21) |

### Critical findings

1. **Fat-tail constraint**: Top 5% trades = 129.5% profits. Exit-shortening mechanisms kill bull alpha.
2. **Selectivity > Timing**: Only filters that block LOSERS (blocked WR < baseline WR) survive WFO.
3. **Unconditional ≠ Conditional**: vol_ratio_5_20 has zero residual-scan significance but strong conditional value.
4. **E5 exit is optimal**: 12 exit experiments, all FAIL WFO. Trail + EMA cross-down cannot be improved.
5. **E5 signal is dominant**: Ensemble/hybrid/multi-asset all degrade vs E5 standalone.

## Formal Validation

x39 used a simplified replay (not v10 BacktestEngine). Before concluding,
the vol compression finding must pass formal validation.

**Spec**: [specs/formal_validation_spec.md](specs/formal_validation_spec.md)

### Execution (3 tasks, sequential)

| Task | File | What | Gate |
|------|------|------|------|
| **B** | [task_b_implement_and_reproduce.md](specs/task_b_implement_and_reproduce.md) | Create strategy class + reproduce x39 results in v10 | d_Sharpe same sign, ±30% |
| **C** | [task_c_formal_validation.md](specs/task_c_formal_validation.md) | Run 7-gate pipeline for thr=0.6 and thr=0.7 | Not REJECT |
| **D** | [task_d_multiple_testing_and_verdict.md](specs/task_d_multiple_testing_and_verdict.md) | DSR (N=52), MDD analysis, final verdict | CONCLUDE/REJECT/INCONCLUSIVE |

### How to run each task

Start a new session and paste the session prompt from the task file. Example:

```
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/formal_validation_spec.md
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/task_b_implement_and_reproduce.md

Execute Phase 1 + Phase 2 of the formal validation spec.
```

Dependency: B → C → D (sequential, each must pass its gate before proceeding).
