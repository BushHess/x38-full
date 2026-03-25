# X1 Research: Re-entry Separation

**Date**: 2026-03-08
**Status**: REJECT
**Baseline**: E0+EMA21(D1)

## Hypothesis

Separating re-entry (after trailing stop) from fresh entry (after trend exit)
improves performance by re-entering trends faster when the main trend is intact.

- **Fresh entry** (after trend exit or first trade): all 3 conditions — EMA cross + VDO > 0 + D1 regime
- **Re-entry** (after trailing stop, ema_fast > ema_slow still true): relaxed — VDO > 0 OR price > last_trail_stop. No D1 regime check.

## Implementation

- Strategy: `strategies/vtrend_x1/strategy.py`
- State added: `last_exit_reason` ("trail_stop" | "trend_exit" | None), `last_trail_stop`
- Same 4 tunable params as baseline: slow=120, trail=3.0, vdo_threshold=0.0, d1_ema=21

## T1: Backtest Results (Engine, 2019-01 to 2026-02)

| Strategy | Scenario | Sharpe | CAGR% | MDD% | Calmar | Trades | WR% | PF | AvgExpo |
|----------|----------|--------|-------|------|--------|--------|-----|-------|---------|
| E0_EMA21 | smart | 1.5572 | 69.12 | 39.42 | 1.7535 | 172 | 44.2 | 1.8964 | 45.4% |
| E0_EMA21 | base | 1.4443 | 61.94 | 40.71 | 1.5214 | 172 | 43.6 | 1.8108 | 45.4% |
| E0_EMA21 | harsh | 1.3249 | 54.70 | 42.05 | 1.3008 | 172 | 42.4 | 1.7151 | 45.4% |
| X1 | smart | 1.4848 | 67.19 | 40.35 | 1.6651 | 204 | 44.1 | 1.6300 | 49.0% |
| X1 | base | 1.3558 | 58.81 | 43.38 | 1.3555 | 204 | 43.1 | 1.5634 | 49.0% |
| X1 | harsh | 1.2194 | 50.42 | 46.42 | 1.0861 | 204 | 42.2 | 1.4895 | 49.0% |

### Delta (X1 - Baseline)

| Scenario | dSharpe | dCAGR | dMDD | dTrades | dWR |
|----------|---------|-------|------|---------|-----|
| smart | -0.0724 | -1.93% | +0.93% | +32 | -0.1% |
| base | -0.0885 | -3.13% | +2.67% | +32 | -0.5% |
| harsh | -0.1055 | -4.28% | +4.37% | +32 | -0.3% |

X1 is **worse on every metric at every cost level**. Delta worsens with cost.

## T2: Bootstrap (500 VCBB paths)

| Strategy | Sharpe med [p5, p95] | CAGR med [p5, p95] | MDD med [p5, p95] | P(CAGR>0) |
|----------|---------------------|--------------------|--------------------|-----------|
| E0_EMA21 | 0.2608 [-0.43, 0.93] | 3.17% [-16.3, 31.3] | 62.18% [43.1, 84.9] | 60.2% |
| X1 | 0.2795 [-0.44, 0.94] | 3.23% [-20.8, 35.6] | 69.37% [48.3, 90.6] | 56.6% |

### Head-to-Head (500 paths)

| Metric | X1 wins | Baseline wins | Mean delta |
|--------|---------|---------------|------------|
| Sharpe | 233 (46.6%) | 267 (53.4%) | -0.0094 |
| CAGR | 225 (45.0%) | 275 (55.0%) | -0.41% |
| MDD | 108 (21.6%) | 392 (78.4%) | +6.22% |

Bootstrap confirms: X1 loses on all 3 dimensions. MDD is decisively worse (21.6% win rate).

## T4: Re-entry Statistics (harsh)

| Entry type | Count | % | WR | AvgRet | AvgDays | PnL |
|------------|-------|---|-----|--------|---------|-----|
| Fresh (x1_entry) | 35 | 17.2% | 48.6% | 5.77% | 7.5 | $149,328 |
| Re-entry (x1_reentry) | 169 | 82.8% | 40.8% | 1.52% | 6.0 | $58,278 |

### Exit breakdown (harsh)

- E0_EMA21: 158 trail stops, 14 trend exits (172 total)
- X1: 169 trail stops, 35 trend exits (204 total)

Re-entries dominate (82.8% of trades) but have lower WR (40.8% vs 48.6%) and
much lower avg return (1.52% vs 5.77%). They are mostly noise, not alpha.

## Root Cause Analysis

1. **D1 regime filter is protective, not redundant**: Removing it for re-entries
   lets in trades during bearish regime transitions. This explains the +4.37% MDD increase.

2. **Re-entries are low-quality trades**: After a trailing stop, the price is
   by definition declining. Re-entering quickly without full confirmation
   catches falling knives rather than trend continuations.

3. **Cost amplification**: 32 extra trades x round-trip cost = drag that
   scales with cost scenario (delta worsens: smart -0.07, harsh -0.11).

4. **Exposure increase hurts**: AvgExpo rises from 45.4% to 49.0% — more time
   in market during low-quality signals means more drawdown exposure.

## Verdict: REJECT

X1 fails on ALL dimensions:
- Lower Sharpe (-0.11 harsh)
- Lower CAGR (-4.28% harsh)
- Higher MDD (+4.37% harsh)
- Lower profit factor (1.49 vs 1.72 harsh)
- Bootstrap h2h: loses Sharpe 53%, CAGR 55%, MDD 78%

The D1 regime filter should NOT be bypassed for re-entries.
Re-entry separation as designed adds noise, not alpha.

## Files

- `strategies/vtrend_x1/strategy.py` — strategy code
- `research/x1/benchmark.py` — evaluation script
- `research/x1/test_x1.py` — 17 unit tests (all pass)
- `research/x1/x1_results.json` — full results
- `research/x1/x1_backtest_table.csv` — backtest table
- `research/x1/x1_bootstrap_table.csv` — bootstrap table
