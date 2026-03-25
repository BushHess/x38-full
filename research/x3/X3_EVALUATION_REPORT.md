# X3 Evaluation Report: Graduated Exposure

**Date**: 2026-03-08
**Baseline**: E0+EMA21(D1) (X0)
**Variant**: X3 — graduated exposure (3 tiers) + graduated exit

## Design

### Entry (relaxed vs baseline)
- Baseline: EMA cross + D1 regime + VDO > 0 → 100%
- X3: EMA cross + D1 regime → enter (VDO determines tier, not gate)
  - Tier 1 (40%): VDO ≤ 0
  - Tier 2 (70%): VDO > 0
  - Tier 3 (100%): VDO > 0.02

### Exit (graduated vs binary)
- Baseline: trail stop → 0%, EMA cross → 0%
- X3: trail stop → core (40%), EMA cross → 0%
- After trail stop: CORE_ONLY state, locked at 40% until EMA reversal

### Parameters
8 tunable: slow_period=120, trail_mult=3.0, vdo_threshold=0.0, vdo_strong=0.02,
d1_ema_period=21, expo_core=0.40, expo_moderate=0.70, expo_full=1.00

## T1: Backtest Results (BacktestEngine)

| Metric | E0_EMA21 (harsh) | X3 (harsh) | Delta |
|--------|:-:|:-:|:-:|
| Sharpe | 1.3249 | 0.9636 | **-0.3613** |
| CAGR% | 54.70 | 20.93 | **-33.77** |
| MDD% | 42.05 | 29.52 | **-12.53** |
| Calmar | 1.3008 | 0.7089 | **-0.5919** |
| Trades | 172 | 71 | -101 |
| Win Rate% | 42.4 | 29.6 | -12.9 |
| Avg Exposure | 0.4544 | 0.2618 | -0.1926 |
| Time-in-Market% | 45.44 | 54.02 | **+8.58** |
| Avg Days Held | 6.89 | 19.84 | +12.95 |

### Signal Breakdown (harsh)
- X3 entries: 71 (all `x3_entry`)
- X3 exits: 64 `x3_core_exit` (trail→core→EMA reversal), 7 `x3_trend_exit`
- 1005 VDO-based rebalances during positions

## T2: Bootstrap VCBB (500 paths)

| Metric | E0_EMA21 | X3 |
|--------|:-:|:-:|
| Sharpe median | 0.2608 | 0.1235 |
| CAGR median% | 3.17 | 0.51 |
| MDD median% | 62.18 | **47.51** |
| P(CAGR>0) | 0.602 | 0.524 |

### Head-to-Head
| Metric | X3 Win Rate | Mean Delta |
|--------|:-:|:-:|
| Sharpe | 26.2% | -0.154 |
| CAGR | 36.4% | -3.94% |
| **MDD** | **94.8%** | **-14.12%** |

## T4: Exposure Tier Distribution

| Tier | Bars | % of Total |
|------|:-:|:-:|
| Flat (0%) | 8,640 | 48.4% |
| Core (40%) | 7,430 | **41.7%** |
| Moderate (70%) | 1,578 | 8.8% |
| Full (100%) | 190 | **1.1%** |

## Diagnosis

### What worked
1. **MDD dramatically reduced**: -12.5% real data, -14.1% bootstrap (94.8% h2h win)
2. **Time-in-market increased**: +8.6% (54.0% vs 45.4%) — catches trend starts earlier
3. **Longer trades**: avg 19.8 days vs 6.9 days — graduated exit lets winners run in core

### What failed
1. **Average exposure only 26%** (vs 45%): the strategy is stuck at 40% core most of the time
2. **VDO > 0.02 almost never achieved**: only 1.1% of bars at full exposure
3. **CAGR destroyed**: -33.8% — far too much alpha diluted by low exposure
4. **Calmar worse**: 0.71 vs 1.30 — MDD improvement doesn't compensate CAGR loss
5. **Sharpe worse**: -0.36 — not even risk-adjusted improvement
6. **Win rate cratered**: 29.6% vs 42.4% — entering at 40% on weak VDO means many losing small positions

### Root cause
The graduated approach creates an **asymmetric payoff problem**:
- On winning trends: enters at 40%, slowly scales to 70-100% → captures only fraction of upside
- On losing trends: enters at 40%, trail stop fires, stays at 40% core → full downside at core level
- VDO > 0.02 (strong) is a very rare condition → Tier 3 is almost never reached
- 90% of positioned time is at core (40%) → effectively a 40% allocation strategy

The 37.8% time-in-market "problem" in the baseline is actually a feature, not a bug.
The VDO gate in E0+EMA21 ensures you only enter with volume confirmation — removing
this gate lets in low-quality entries that drag down returns.

## Verdict

**REJECT** — graduated exposure degrades all performance metrics except MDD.
The MDD improvement (+94.8% bootstrap h2h) does not compensate for the massive
CAGR/Sharpe loss. Calmar (risk-adjusted) is strictly worse.

The baseline's binary exposure (0%/100% with VDO gate) is mathematically superior
because it concentrates capital on high-conviction entries. Graduated exposure
dilutes alpha across low-conviction periods.

## Files
- Strategy: `strategies/vtrend_x3/strategy.py`
- Benchmark: `research/x3/benchmark.py`
- Tests: `research/x3/test_x3.py` (27/27 pass)
- Artifacts: `research/x3/x3_results.json`, `x3_*_table.csv`
