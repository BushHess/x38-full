# Research Index

> **PARTIAL INDEX — covers early studies (X0-X6) and top-level scripts only.**
> For the authoritative 72-study registry (X0-X37), see `results/COMPLETE_RESEARCH_REGISTRY.md`.
> For X34-X37 (current), see their `README.md` files.
> For algorithm status summary, see `STRATEGY_STATUS_MATRIX.md`.
>
> *Last reviewed: 2026-03-14*

---

## Study Directories

| Directory | Purpose | Date | Key Result | Strategy | Status |
|-----------|---------|------|------------|----------|--------|
| `x0/` | Phase 1-3 anchor: E0+EMA21(D1) behavioral clone | 2026-03 | Sharpe 1.325, CAGR 54.7%, MDD 42.1%, 172 trades | `vtrend_ema21_d1` | **COMPLETED** — frozen baseline |
| `x1/` | Re-entry separation variant | 2026-03 | Sharpe −0.105 vs X0, all dimensions fail | X0 + re-entry split | **REJECTED** |
| `x2/` | Adaptive trail (widen with gain) | 2026-03 | Sharpe +0.098 in-sample, WFO 4/8 (50%) | X0 + adaptive trail | **REJECTED** |
| `x3/` | Graduated exposure (3-tier by VDO) | 2026-03 | Sharpe −0.361, CAGR −33.8% | X0 + graduated sizing | **REJECTED** |
| `x4/` | Entry signal speed (faster EMAs, breakout) | 2026-03 | Completed — see x4_results.json | X0 + alt entry | **COMPLETED** |
| `x5/` | Partial profit-taking (TP1/TP2 milestones) | 2026-03 | Sharpe −0.042, CAGR −13.3%, MDD −2.9% | X0 + partial exits | **REJECTED** (tradeoff) |
| `x6/` | Adaptive trail + breakeven floor | 2026-03 | Sharpe +0.108, CAGR +8.8%, 15 Q-series substudies | X0 + trail+BE | **COMPLETED** — promote candidate |
| `prod_readiness_e5_ema1d21/` | Production readiness: regime monitor + E5 DOF + E5S simplification | 2026-03-09 | V2 monitor promoted; E5S rejected; E5 vs X0 p=0.063 (Nyholt) | E5+EMA1D21 | **COMPLETED** |
| `ml0_feasibility/` | ML feasibility gate (pre-XGBoost screening) | 2026-03 | Archived — ML on OHLCV CLOSED | ML overlay | **CLOSED** |
| `next_wave/` | Derivatives, breadth, re-entry diagnostics | 2026-03-07 | All tracks WEAK/PARKED. See MEMORY.md | Multiple overlays | **CLOSED** |
| `x7/`-`x33/` | 27 studies — see `results/COMPLETE_RESEARCH_REGISTRY.md` | 2026-03 | Various | Various | Various |
| `x34/` | Q-VDO-RH family diagnostic | 2026-03-13 | REJECT/CLOSED | E0 + Q-VDO-RH | **CLOSED** |
| `x35/` | State diagnostic (active) | 2026-03-14 | In progress | E5+EMA21D1 | **IN PROGRESS** |
| `x37/branches/a_v4_vs_e5_fair_comparison/` | V4 macroHystB (x37v4) vs E5_ema21D1 | 2026-03-17 | V4_COMPETITIVE (3/4, WFO underpowered). Sh 1.865, MDD 23.9%, 51 trades. NOT promoted. | macroHystB vs E5_ema21D1 | **DONE** |

## Shared Libraries (`lib/`)

| Module | Purpose |
|--------|---------|
| `vcbb.py` | Volume-chunked block bootstrap (gen_path_vcbb) |
| `effective_dof.py` | M_eff corrections (Nyholt/Li-Ji/Galwey) |
| `dsr.py` | Deflated Sharpe Ratio (Bailey & López de Prado, 2014) |
| `pair_diagnostic.py` | Strategy pair comparison diagnostics |

## Top-Level Research Scripts (59 files)

Organized by category. All re-run 2026-03-02 (0 failures, 9h 22m).

### Proven Components

| Script | Study | Verdict |
|--------|-------|---------|
| `multiple_comparison.py` | EMA crossover entry signal | **PROVEN** (p=0.0003) |
| `timescale_robustness.py` | 16-timescale sweep (slow=30-720) | **PROVEN** (plateau 60-144) |
| `ema_ablation.py` | D1 EMA regime filter ablation | **PROVEN** (16/16 all metrics) |
| `ema_regime_sweep.py` | EMA regime period sweep | **PROVEN** (range 15-40d) |
| `ema_regime_fine.py` | Fine-grained EMA 21/63/126 | 21d **PROVEN**, 63/126 MDD-only |
| `binomial_correction.py` | DOF-corrected binomial tests | VDO corrected p=0.031 |

### Parameter Studies

| Script | Study | Verdict |
|--------|-------|---------|
| `trail_sweep.py` | Trail multiplier 2.0-5.0 | **TRADEOFF** (higher trail = return↑ MDD↑) |
| `config_compare.py` | slow=200 vs 120 | **REJECTED** |
| `vtrend_param_sensitivity.py` | Full parameter sensitivity | **REJECTED** (no combo beats default on ALL metrics) |

### Rejected Strategies

| Script | Strategy | Verdict |
|--------|----------|---------|
| `pullback_strategy.py` | VPULL | **REJECTED** (p=1.0) |
| `vbreak_test.py` | VBREAK | **REJECTED** (p=0.0026) |
| `vcusum_test.py` | VCUSUM | **REJECTED** (p=0.0186) |
| `vtwin_test.py` | VTWIN | **REJECTED** (DOF→p=0.145) |
| `pe_study.py` / `pe_study_v2.py` | PE/PE* candle quality | **REJECTED** (zero provable value) |
| `e6_staleness_study.py` | E6 staleness exit | **REJECTED** (smooth surface of damage) |
| `e7_study.py` | E7 trail-only exit | **REJECTED** (trades Sharpe for MDD) |
| `d1_ema200_filter.py` | D1 EMA(200) regime | **REJECTED** (kills returns) |

### Exit & Signal Variants

| Script | Study | Verdict |
|--------|-------|---------|
| `exit_family_study.py` | Comprehensive exit variant comparison | Baseline exits **PROVEN** |
| `e5_validation.py` | E5 robust ATR | **HOLD** (MDD 16/16, WFO 4/8) |
| `e5r_test.py` / `e5_vcbb_test.py` | E5 bootstrap validation | Confirms MDD improvement |
| `vexit_study.py` | VTWIN + ratcheting trail | **REJECTED** |
| `creative_exploration.py` | E7, ensemble, exploratory | E7/ensemble **REJECTED** |

### Multi-Coin

| Script | Study | Verdict |
|--------|-------|---------|
| `multicoin_ema_regime.py` | EMA(21d) regime across 14 coins | 11/14 improved |
| `multicoin_200v120.py` | slow=200 vs 120 multi-coin | 8/14 coin flip, **REJECTED** |
| `multicoin_exit_variants.py` | E5/E6/E7 multi-coin | E5 catastrophic on altcoins |
| `multicoin_diversification.py` | Portfolio diversification | Sharpe **PROVEN**, MDD worse |

### Parity & Evaluation

| Script | Study | Verdict |
|--------|-------|---------|
| `parity_eval.py` | 6-strategy T1-T7 comparison | EMA21-D1 **PROMOTE** |
| `parity_eval_x.py` | X-series T2-T4 comparison | X6 best real-data |

### Infrastructure & Audit

| Script | Purpose |
|--------|---------|
| `audit_phase1_3.py` / `audit_phase4.py` | System audit (5/5 phases PASS) |
| `cross_check_vs_vtrend.py` | Parity vs btc-spot-dev (BIT-IDENTICAL) |
| `invariant_tests.py` | 17/17 mathematical invariants |
| `validate_bootstrap.py` | VCBB validation |
| `vcbb_vs_uniform.py` | VCBB vs uniform bootstrap |

### Supporting Analysis

| Script | Purpose |
|--------|---------|
| `component_analysis.py` | Signal/sizing decomposition |
| `signal_vs_sizing.py` | Signal vs sizing contribution |
| `cost_study.py` | Cost sensitivity (15/25/50 bps) |
| `position_sizing.py` | Vol-target f=0.30 optimal |
| `regime_sizing.py` | VTREND profits ALL 6 regimes |
| `resolution_sweep.py` | H1/H4/D1 resolution (H4 best) |
| `bootstrap_regime.py` | Regime-conditional bootstrap |
| `monthly_pnl.py` | Monthly P&L breakdown |
| `trade_profile_8x5.py` | 40-cell trade analysis matrix |
| `true_wfo_compare.py` | True WFO + permutation |
| `v8_vs_vtrend_bootstrap.py` | V8 (40+ params) adds ZERO value |
| `vtrend_postmortem.py` | Strategy postmortem analysis |
| `roadmap_diagnostic.py` | Feasibility analysis |
| `amt_research.py` / `amt_research_part6.py` | Alternative market timing |
| `rcssb_diagnostics.py` | Rolling-correlation diagnostics |
| `psr_comparison.py` | Probabilistic Sharpe comparison |
| `vdo_standalone_test.py` | VDO standalone test |

## Results Directory (`results/`)

Contains output artifacts for all studies. Key index: `results/COMPLETE_RESEARCH_REGISTRY.md`.

## Tests (`tests/`)

Research test runner entrypoint. Individual test files live within each study directory.

---

## Status Legend

| Status | Meaning |
|--------|---------|
| **COMPLETED** | Study finished, conclusions final |
| **REJECTED** | Hypothesis disproven, not used |
| **SUPERSEDED** | Replaced by newer study |
| **IN PROGRESS** | Active research |
| **PENDING** | Not yet fully evaluated |

---

*Last updated: 2026-03-14*
