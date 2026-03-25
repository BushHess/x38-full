# X31: D1 Regime Exit — Phase 0 Diagnostic

## Hypothesis

D1 EMA(21) regime filter is the strongest proven signal in the system (p=1.5e-5,
16/16 ALL metrics). Currently it is used **only at entry**. During a trade, if
D1 regime flips bearish (D1_close < D1_EMA(21)), the strategy ignores this and
waits for either:

1. Trail stop: price < peak - 3.0 × RobustATR(20)
2. EMA cross-down: EMA(30) < EMA(120)

**Question**: Does D1 regime flip occur during trades BEFORE trail/EMA exit fires?
If so, would exiting at D1 flip reduce avg_loser (the #1 Sharpe predictor per
X28, R²=0.306) without cutting too many winners?

## Why This Is Different From Previous Exit Research

| Study | What was tried | Why it failed |
|-------|---------------|---------------|
| X16-F | Adaptive trail width (churn-conditioned) | Trail width not bottleneck (ΔSh=-0.006) |
| X23 | State-conditioned pullback multipliers | Increased churn (+exits → Sh -0.229) |
| X24 | Trail arming (delay trail activation) | 53 never-armed entries degrade exits |
| X30 | Fractional exit at trail stop | Bootstrap 30-43% (path-specific) |

X31 is different because:
- Uses a PROVEN signal (D1 EMA 21, p=1.5e-5) not a churn model
- Adds an INDEPENDENT exit condition, doesn't modify trail/EMA exit
- Zero new parameters (reuses existing d1_ema_period=21)
- Addresses avg_loser directly (earlier exit on regime deterioration)

## Phase 0: Diagnostic (Go/No-Go)

Before any backtest, answer:

1. **Coverage**: In how many trades does D1 regime flip bearish DURING the trade,
   BEFORE trail/EMA exit fires? If < 10% of trades → STOP (redundant signal).

2. **Timing**: For those trades, how many H4 bars earlier would D1 exit be vs
   actual exit? If median < 2 bars → STOP (no meaningful timing advantage).

3. **P&L split**: Among trades where D1 flips first:
   - What fraction are losers vs winners at actual exit?
   - What would P&L be if we exited at D1 flip instead?
   - Does D1 exit predominantly save on losers or cut winners?

4. **Winner damage**: Among the strategy's top-20 winners, how many had D1
   regime flip during the trade? If > 50% → WARNING (risk of cutting alpha).

### Decision Matrix

| Coverage | Timing | Loser/Winner | Decision |
|----------|--------|-------------|----------|
| < 10% | any | any | STOP — redundant |
| ≥ 10% | < 2 bars median | any | STOP — no timing edge |
| ≥ 10% | ≥ 2 bars | mostly cuts losers | PROCEED to Phase 1 |
| ≥ 10% | ≥ 2 bars | cuts losers AND winners equally | STOP — no selectivity |
| ≥ 10% | ≥ 2 bars | mostly cuts winners | STOP — destroys alpha |

## Constraints

- Cost: 50 bps RT (harsh, consistent with all prior research)
- Data: 2019-01-01 to 2026-02-20, warmup 365 days
- Resolution: H4 + D1
- No new parameters allowed in Phase 0
- Report all numbers, don't cherry-pick

## Resources

```
Data:     btc-spot-dev/data/bars_btcusdt_2016_now_h1_4h_1d.csv
Strategy: btc-spot-dev/strategies/vtrend_e5_ema21_d1/strategy.py
```
