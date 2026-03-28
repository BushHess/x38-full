# x39 — Feature Invention Explorer & Experiment Plan

## Context

x39 started as exploration tools to find what OHLCV features existing indicators
don't capture. After incorporating gen4/gen1 research, the residual scan identified
features that predict returns INDEPENDENTLY of EMA/VDO/D1 regime.

## Key Findings (from explore.py)

| Feature | Sig horizons | Direction | Source |
|---|---|---|---|
| d1_rangevol84_rank365 | 4/5 | + all | Gen4 C1 |
| ret_168 | 4/5 | + all | Gen1 V6 |
| trendq_84 | 3/5 | + med-long | Gen1 V3 |
| rangepos_84 | 3/5 | dual | Gen4 |
| vol_per_range | 3/5 | + med-long | x39 original |
| body_consist_6 | 3/5 | dual | x39 original |
| trade_surprise_168 | 2/5 | dual | Gen4 C3 |
| d1_taker_imbal_12 | 2/5 | - med | Gen4 C2 |
| ratr_pct | 2/5 | + med | x39 original |

Loss anatomy: 0/31 features separate winners from losers at entry (all p > 0.05).

## Baseline

E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Experiments

24 experiments in 7 categories. Each is self-contained with its own spec file.
Run ONE experiment per session. Each session reads its spec, runs the test,
writes results back to the spec file.

| # | Category | Name | Spec file |
|---|----------|------|-----------|
| 01 | A-filter | D1 anti-vol gate | specs/exp01_d1_antivol_gate.md |
| 02 | A-filter | Trend quality gate | specs/exp02_trendq_gate.md |
| 03 | A-filter | Liquidity gate | specs/exp03_liquidity_gate.md |
| 04 | A-filter | Trade surprise gate | specs/exp04_trade_surprise_gate.md |
| 05 | A-filter | D1 taker exhaustion block | specs/exp05_d1_taker_block.md |
| 06 | A-filter | Body consistency block | specs/exp06_body_consist_block.md |
| 07 | B-replace | Replace EMA with ret_168 | specs/exp07_replace_ema_ret168.md |
| 08 | B-replace | Replace EMA with rangepos_168 | specs/exp08_replace_ema_rangepos.md |
| 09 | B-replace | Replace D1 EMA(21) with D1 anti-vol | specs/exp09_replace_d1regime.md |
| 10 | B-replace | Replace VDO with trade_surprise | specs/exp10_replace_vdo.md |
| 11 | C-exit | Anti-vol dynamic trail | specs/exp11_antivol_trail.md |
| 12 | C-exit | Range position exit | specs/exp12_rangepos_exit.md |
| 13 | C-exit | Trend quality exit | specs/exp13_trendq_exit.md |
| 14 | D-compare | E5 vs Gen4 C3 head-to-head | specs/exp14_vs_gen4c3.md |
| 15 | D-compare | E5 vs Gen1 V6 head-to-head | specs/exp15_vs_gen1v6.md |
| 16 | D-compare | Hybrid Gen4 entry + E5 exit | specs/exp16_hybrid_gen4_e5.md |
| 17 | E-ensemble | Vote ensemble (2/3 agree) | specs/exp17_vote_ensemble.md |
| 18 | E-ensemble | OR ensemble (any signal) | specs/exp18_or_ensemble.md |
| 19 | F-stacked  | Stacked supplementary exits | specs/exp19_stacked_exits.md |
| 20 | F-stacked  | Rangepos-adaptive trail | specs/exp20_rangepos_adaptive_trail.md |
| 21 | F-stacked  | ret_168 momentum exit | specs/exp21_ret168_momentum_exit.md |
| 22 | F-stacked  | AND-gated feature interaction exit | specs/exp22_and_gated_exit.md |
| 23 | G-robust   | Rangepos lookback robustness | specs/exp23_rangepos_lookback_robustness.md |
| 24 | F-stacked  | Volume anomaly exit | specs/exp24_volume_anomaly_exit.md |

## How to run

Each spec file contains everything needed to execute the experiment:
- Exact feature formula
- Parameter sweep values
- Entry/exit logic changes
- Comparison metrics
- Expected output format

```
# In a new session:
# 1. Read the spec file
# 2. Write and run the experiment script
# 3. Write results back to the spec file
# 4. Update this PLAN.md with verdict
```

## Results Summary

| # | Name | Verdict | Sharpe | CAGR | MDD | Trades | Notes |
|---|------|---------|--------|------|-----|--------|-------|
| 01 | D1 anti-vol gate | — | — | — | — | — | — |
| 02 | Trend quality gate | — | — | — | — | — | — |
| 03 | Liquidity gate | — | — | — | — | — | — |
| 04 | Trade surprise gate | — | — | — | — | — | — |
| 05 | D1 taker block | — | — | — | — | — | — |
| 06 | Body consist block | — | — | — | — | — | — |
| 07 | Replace EMA→ret_168 | — | — | — | — | — | — |
| 08 | Replace EMA→rangepos | — | — | — | — | — | — |
| 09 | Replace D1 regime | — | — | — | — | — | — |
| 10 | Replace VDO→trade_surp | — | — | — | — | — | — |
| 11 | Anti-vol trail | — | — | — | — | — | — |
| 12 | Rangepos exit | — | — | — | — | — | — |
| 13 | Trendq exit | FAIL | 1.248 | 53.7% | 47.4% | 294 | Best th=-0.2: MDD -3.9pp but Sharpe -0.049. All thresholds degrade Sharpe. |
| 14 | vs Gen4 C3 | — | — | — | — | — | — |
| 15 | vs Gen1 V6 | — | — | — | — | — | — |
| 16 | Hybrid Gen4+E5 | — | — | — | — | — | — |
| 17 | Vote ensemble | — | — | — | — | — | — |
| 18 | OR ensemble | — | — | — | — | — | — |
| 19 | Stacked exits | — | — | — | — | — | — |
| 20 | Rangepos-adaptive trail | — | — | — | — | — | — |
| 21 | ret_168 momentum exit | — | — | — | — | — | — |
| 22 | AND-gated exit | — | — | — | — | — | — |
| 23 | Rangepos lookback robust | — | — | — | — | — | — |
| 24 | Volume anomaly exit | — | — | — | — | — | — |
