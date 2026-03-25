# X0A — Runtime Regime Monitor Research Report

## 1. Objective

Evaluate a runtime regime monitor that detects dangerous market conditions
using two complementary signals:

1. **Rolling 6-month MDD**: captures sustained drawdowns
2. **Rolling ATR Q90**: captures volatility regime shifts

Alert thresholds calibrated against training-period statistics.

## 2. Monitor Parameters

| Parameter | Value |
|-----------|-------|
| Rolling window | 180 D1 bars (~6 months) |
| ATR period | 14 (Wilder) |
| ATR percentile | Q90 |
| Training period | 365 D1 bars |
| Training ATR Q90 mean (raw) | 535.77 |
| AMBER thresholds | MDD > 55% OR ATR ratio > 1.40x |
| RED thresholds | MDD > 65% OR ATR ratio > 1.60x |

## 3. Raw ATR Monitor (FLAWED — Section retained for documentation)

### 3.1 Alert Distribution (raw ATR)

| Level | Count | % of Total |
|-------|------:|----------:|
| NORMAL | 739 | 24.9% |
| AMBER | 104 | 3.5% |
| RED | 2130 | 71.6% |

**DIAGNOSIS**: 71.6% of bars flagged RED. Root cause: raw ATR scales linearly with
BTC price ($535 training mean at $4K BTC becomes permanently >7x at $90K BTC).
99.7% of RED days triggered by ATR channel alone. Raw ATR is **structurally
broken** as a regime monitor signal.

### 3.2 Backtest (raw ATR, harsh)

| Metric | X0 Vanilla | X0+Monitor | Delta |
|--------|----------:|----------:|------:|
| Sharpe | 1.0269 | 0.9300 | -0.0969 |
| CAGR % | 37.99 | 20.30 | -17.69 |
| MDD % | 46.73 | 32.45 | -14.29 |
| Trades | 186 | 54 | -132 |

MDD improves -14.3% but at catastrophic CAGR cost (-17.7%) because the monitor
is flat during the entire 2021-2026 bull market.

## 4. Corrected Monitor: ATR% (ATR/price, normalized)

Training ATR% Q90 mean: 8.4130%

### 4.1 Alert Distribution (ATR% normalized)

| Level | Count | % of Total |
|-------|------:|----------:|
| NORMAL | 2727 | 91.7% |
| AMBER | 220 | 7.4% |
| RED | 26 | 0.9% |

RED trigger breakdown: MDD-only=0, ATR%-only=20, both=6

### 4.2 AMBER Episodes (corrected): 4 (246 total days, mean 61.5d)

| # | Start | End | Duration | BTC Return |
|---|-------|-----|----------|------------|
| 1 | 2018-06-29 | 2018-07-28 | 30d | +32.7% |
| 2 | 2018-12-05 | 2019-03-02 | 88d | +1.3% |
| 3 | 2022-05-11 | 2022-05-12 | 2d | -0.3% |
| 4 | 2022-06-13 | 2022-10-16 | 126d | -14.3% |

### 4.2 RED Episodes (corrected): 1 (26 total days, mean 26.0d)

| # | Start | End | Duration | BTC Return |
|---|-------|-----|----------|------------|
| 1 | 2018-06-29 | 2018-07-24 | 26d | +35.5% |

### 4.3 False Positive Analysis (corrected, reporting period)

No RED episodes in reporting period.

### 4.4 Backtest Comparison (corrected, harsh)

| Metric | X0 Vanilla | X0+Monitor(corr) | Delta |
|--------|----------:|----------:|------:|
| Sharpe | 1.0269 | 1.0269 | -0.0000 |
| CAGR % | 37.99 | 37.99 | +0.00 |
| MDD % | 46.73 | 46.73 | -0.00 |
| Trades | 186 | 184 | -2 |
| Monitor exits | - | 0 | |
| Final NAV | 73041.93 | 65552.19 | -7489.74 |

## 5. Diagnostic: Why RED Never Fires in Reporting Period

Peak rolling 6-month MDD values at key bear markets:

| Period | Event | Peak 6m MDD | vs RED (65%) |
|--------|-------|:-----------:|:------------:|
| 2019 H2 | Post-July crash | 49.4% | -15.6% |
| 2020 Q1 | COVID crash | 53.6% | -11.4% |
| 2021 Q2 | May crash | 53.1% | -11.9% |
| 2022 Q2-Q3 | Luna + FTX | **62.7%** | **-2.3%** |

The 2022 bear market (total drawdown ~77%, $69K to $15.5K) was the worst in our
data. But the 6-month rolling window only captured 62.7% — just 2.3% below RED.

**Root cause**: The 77% drawdown spanned ~12 months. A 6-month window structurally
caps how much of a slow, extended drawdown it can detect. For a crash to trigger
65% rolling MDD, it must happen mostly within 6 months.

ATR% channel (corrected): during 2022, ATR% ratio peaked at AMBER level only.
Normalized volatility didn't reach extreme levels because BTC's percentage moves
were large but within historical range (ATR% Q90 ~8-12% vs training mean 8.4%).

## 6. Verdict

### Raw ATR monitor: REJECT

Raw ATR scales with price, producing 71.6% RED rate and destroying returns.
Fundamentally broken — must always normalize by price.

### Corrected ATR% monitor: NOT ACTIONABLE (as configured)

- **Zero RED triggers** in reporting period (2019-2026)
- Worst real-world case (2022 bear: 77% total DD) only reached 62.7% rolling MDD
- RED threshold of 65% is 2.3% above the historical peak — never fires
- Monitor is correctly calibrated (no spurious triggers) but provides **no
  protective value** at these thresholds

### Key Findings

1. **Raw ATR is structurally broken** as a monitor signal. Must use ATR%
   (ATR/price). This is a hard requirement for any production implementation.

2. **6-month rolling MDD has a structural ceiling** for slow drawdowns.
   A 12-month bear market only produces ~63% rolling 6-month MDD. To catch it,
   either: (a) lower RED to 55-60%, or (b) use 12-month window.

3. **False positive rate of raw version: 50%** (1 TP + 1 FP, where the FP
   covers the entire 2021-2026 bull run = catastrophic cost).

4. **AMBER (corrected) is useful**: correctly identifies 2022 bear (episodes #3
   and #4), with reasonable specificity (4 episodes, 246 total days).

### Recommendation

If pursuing this monitor design:
- Use ATR% (normalized), never raw ATR
- Lower RED MDD threshold to **55%** or extend rolling window to **360 days**
- AMBER at 50% MDD as early warning
- Consider MDD-only monitor (ATR% channel adds little value when normalized)
- Any threshold choice needs forward-looking validation; current thresholds
  are statistically underpowered (N=1 near-miss in 7 years)

---
*Generated by x0a/regime_monitor.py*
