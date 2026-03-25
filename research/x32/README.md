# X32 — VP1 (VTREND-P1) Research

## Objective
Rigorous study of VP1 (Phase 1 performance-dominant leader) and its parameter variants,
followed by systematic comparison against E5+EMA1D21 (current primary).

## VP1 Frozen Identity (from `resource/`)
| Parameter | VP1 value |
|---|---|
| slow_period | 140 |
| fast_period | 35 (= floor(140/4)) |
| ATR type | Standard Wilder |
| ATR period | 20 |
| trail_mult | 2.5 |
| d1_ema_period | 28 |
| VDO threshold | 0.0 (strict >) |
| Timeframe | H4 main, D1 context |
| Sizing | Binary (100% NAV or 0%) |
| Cost (benchmark) | 50 bps RT |

## E5+EMA1D21 Reference (comparison target)
| Parameter | E5+EMA1D21 value |
|---|---|
| slow_period | 120 |
| ATR type | RATR |
| trail_mult | 3.0 |
| d1_ema_period | 21 |

## Directory Structure

```
x32/
├── README.md                  ← this file
├── resource/                  ← FROZEN (read-only), VP1 canonical spec audit pack
│
├── a_vp1_baseline/            ← Branch A: VP1 original as-is
│   ├── code/                  ← rebuild implementation from spec v1.1
│   ├── results/               ← backtest outputs, trade logs, metrics
│   └── figures/               ← equity curves, drawdown plots
│
├── b_variants/                ← Branch B: VP1 parameter variants
│   ├── code/                  ← variant runners, sweep scripts
│   ├── results/               ← per-variant outputs
│   └── figures/               ← comparison charts
│
├── c_comparison/              ← Branch C: VP1 family vs E5+EMA1D21
│   ├── code/                  ← head-to-head evaluation, bootstrap, WFO
│   ├── results/               ← final comparison tables
│   └── figures/               ← overlay plots
│
└── shared/                    ← shared utilities
    ├── code/                  ← data loading, metrics, bootstrap lib
    └── data/                  ← symlinks or refs to canonical data
```

## Research Plan

### Branch A — VP1 Baseline (must complete first)
1. **A1**: Implement VP1 exactly from `resource/06_final_audited_rebuild_spec_v1.1.md`
2. **A2**: Pass all acceptance tests (Section 13 of spec — Tier-2 trade count, timestamps, first trade cycle)
3. **A3**: Full-history backtest (2017-08 → 2026-02) with headline metrics
4. **A4**: Bootstrap confidence intervals (VCBB method, same as E5 evaluation)
5. **A5**: Trade structure analysis (avg winner/loser, exposure, regime breakdown)

Gate: A2 must pass before any Branch B/C work begins.

### Branch B — VP1 Variants
Systematic exploration of VP1's parameter sensitivity. Each variant changes ONE dimension.

| Variant ID | Description | What changes |
|---|---|---|
| B1 | RATR swap | Standard Wilder ATR(20) → RATR (match E5) |
| B2 | ATR period sweep | ATR period: 14, 16, 20, 24, 28 |
| B3 | Trail multiplier sweep | trail_mult: 2.0, 2.5, 3.0, 3.5, 4.0 |
| B4 | D1 EMA period sweep | d1_ema: 15, 21, 28, 35, 40 |
| B5 | Slow period sweep | slow_period: 80, 100, 120, 140, 160 |
| B6 | Fast period rule | Alternative fast derivations (floor(N/3), floor(N/5), fixed 21) |
| B7 | Combined best | Best single-dimension winners combined (if any pass gates) |

Each variant evaluated with:
- Full-history backtest
- Bootstrap P(d_sharpe > 0) vs VP1 baseline
- WFO (4-fold) pass/fail

### Branch C — Final Comparison vs E5+EMA1D21
Only after A and B complete. Compares:
- VP1 baseline vs E5+EMA1D21
- Best VP1 variant (if any) vs E5+EMA1D21
- Wilcoxon signed-rank on WFO folds
- Bootstrap delta distributions
- Cost sensitivity analysis (15, 25, 50 bps)

## Evaluation Framework
Same gates as existing pipeline (from `memory/evaluation_playbook.md`):
- G0: Full-sample delta direction
- G1: WFO ≥ 50% win rate
- G2: Bootstrap P(d > 0) ≥ 55%
- G3: PSR ≥ 0.95
- Additional: JK stability, cost sensitivity

## Status: CLOSED (2026-03-12)
- [x] Branch A: COMPLETE — 15/15 acceptance, full validation 17/17 suites
- [x] Branch B: COMPLETE — VP1-E5exit (RATR swap), VP1-FULL (all E5 params), both validated
- [x] Branch C: COMPLETE — comparison report at `c_comparison/results/comparison_report.md`
- [x] Transfer Analysis: COMPLETE — no VP1 features worth transferring to E5+EMA1D21

## Key Results (harsh, 50 bps RT, validation window 2019-01 → 2026-02)

| Strategy | Sharpe | CAGR % | MDD % | Trades | Verdict |
|----------|--------|--------|-------|--------|---------|
| VP1 | 1.452 | 61.7 | 40.5 | 194 | ERROR (holdout FAIL) |
| VP1-E5exit | **1.488** | **62.5** | **36.6** | 213 | ERROR (holdout FAIL) |
| VP1-FULL | 1.461 | 62.0 | 41.0 | 187 | ERROR (WFO FAIL) |
| E5+EMA1D21 | 1.430 | 59.9 | 41.6 | 186 | **PROMOTE** |
| E0 baseline | 1.265 | 52.0 | 41.6 | 192 | — |

## Conclusion
All VP1 variants beat E5+EMA1D21 on full-sample but FAIL validation gates (holdout/WFO).
VP1's structural features add value but its parameter set (slow=140, trail=2.5, d1_ema=28) overfits.
**E5+EMA1D21 remains PRIMARY** — only strategy to achieve PROMOTE.

## Transfer Analysis (VP1 → E5+EMA1D21)

Systematic evaluation of whether any VP1 structural features or spec techniques should transfer:

### 3 Structural Features Evaluated
1. **Prevday D1 mapping** (date-based vs close_time-based): Affects ~17% of H4 bars where mapping differs. But D1 regime rarely flips intra-day, so practical impact is negligible on BTCUSDT.
2. **Per-bar VDO auto path** (taker/fallback selection per bar vs global): BTCUSDT has complete taker_buy data since 2017-08. Zero bars trigger the fallback path. No difference.
3. **Anomaly bar handling** (volume<=0 skip): Zero anomaly bars exist in BTCUSDT H4 data. No impact.

### Spec Coding Techniques Evaluated
- **EMA NaN carry-forward**: E5's `_ema()` initializes from bar 0, no NaN gaps. Not needed.
- **Volume anomaly detection**: No anomalous bars in dataset. Guard would never fire.
- **Per-bar taker data validation**: Redundant — all BTCUSDT bars have valid taker data.

### VP1-FULL Test (Combined Structural Transfer)
VP1-FULL already tests ALL structural features combined with E5 parameters:
- VP1-FULL Sharpe 1.461 vs E5+EMA1D21 Sharpe 1.430 → Δ = +0.031
- This +0.031 is underpowered (bootstrap CI includes zero)
- VP1-FULL FAILS WFO gate (Wilcoxon p=0.125)

### Decision: No Transfer Warranted
VP1 structural features are irrelevant on BTCUSDT H4 data. Combined test (VP1-FULL) shows +0.031 Sharpe is underpowered/inconclusive (bootstrap CI includes zero) and fails WFO validation. **No code changes to E5+EMA1D21.**

> **Supersession note (2026-03-13)**: Original text used "noise" — corrected to "underpowered/inconclusive" per methodology reform (Report 21 compliance). See `memory/methodology.md` §8c.

### Production Note
E5 line 164 blocks ALL signals (including exits) when RATR=NaN. VP1's approach allows EMA reversal exits even during RATR warmup. This is an engineering robustness fix, not a research study — noted for future production hardening.

## Artifacts
- `EVALUATION_CHECKLIST.md` — standard protocol for all variant evaluations
- `a_vp1_baseline/results/full_validation/` — VP1 full 17-suite validation
- `b_variants/results/vp1_e5exit_validation/` — VP1-E5exit 17-suite validation
- `b_variants/results/vp1_full_validation/` — VP1-FULL 17-suite validation
- `c_comparison/results/comparison_report.md` — comprehensive comparison
