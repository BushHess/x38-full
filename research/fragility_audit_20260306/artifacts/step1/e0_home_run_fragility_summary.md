# E0 Home-Run Dependence & Behavioral Fragility Summary

## Classification

| Dimension | Label | Confidence |
|-----------|-------|------------|
| Native view (pnl_usd) | **home-run** | High |
| Unit-size view (return_pct) | **home-run** | High |
| Overall | **home-run** | High |
| Dependence shape | **cliff-like** | High |
| Skip-after-N harmful? | Yes (N<=3), No (N>=4) | High |

## The Core Finding

E0 is a home-run dependent strategy. Six trades out of 192 (3.1%) determine whether the strategy is profitable at all.

- **Top 5 trades contribute 90.2% of total net PnL** ($197K of $218K)
- **Top 10 trades contribute 143.2%** — the other 182 trades are net negative ($-94K)
- **Removing trade #6** collapses CAGR from 19.3% to -26.1% (cliff score 17.4)
- **Gini coefficient: 0.609** (moderate-high concentration)
- **Skewness: 3.66** (extreme positive skew, characteristic of trend-following)

This is not a deficiency. It is the structural signature of trend-following with an ATR trail stop. The strategy has a 42% win rate with 3.3:1 average win/loss ratio. It must lose often on small amounts to capture rare, large directional moves.

## Sensitivity Curve Key Points

### Native View (ranked by pnl_usd)

| Trades Removed | % Removed | Terminal Value | CAGR | Sharpe |
|---------------|-----------|---------------|------|--------|
| 0 | 0.0% | $228,480 | 61.8% | 1.138 |
| 1 | 0.5% | $178,541 | 55.8% | 1.073 |
| 3 | 1.6% | $93,764 | 41.1% | 0.943 |
| 5 | 2.6% | $31,435 | 19.3% | 0.775 |
| **6** | **3.1%** | **$1,403** | **-26.1%** | **0.687** |
| 10 | 5.2% | -$84,372 | -100.0% | 0.462 |

### Unit-Size View (ranked by return_pct)

| Trades Removed | % Removed | Terminal Value | CAGR | Sharpe |
|---------------|-----------|---------------|------|--------|
| 0 | 0.0% | $354,311 | 73.1% | 1.138 |
| 1 | 0.5% | $188,548 | 57.1% | 1.094 |
| 5 | 2.6% | $45,031 | 26.0% | 0.753 |
| 10 | 5.2% | $11,559 | 2.3% | 0.217 |
| **12** | **6.3%** | **$7,634** | **-4.1%** | **-0.017** |

Unit-size view is slightly more resilient (zero-cross at 12 vs 6 trades) because compounding amplifies the value of large return_pct trades.

## Cliff-Edge Detection

| View | Metric | Cliff Detected | Max Score | At Trade # |
|------|--------|---------------|-----------|-----------|
| Native | Terminal | Yes | 3.60 | 1 |
| Native | CAGR | Yes | 17.36 | 5 (the $30K trade that pushes CAGR below zero) |
| Native | Sharpe | Yes | 4.21 | 28 |
| Unit-size | Terminal | Yes | 17.81 | 1 (the 87.9% return trade) |
| Unit-size | CAGR | Yes | 5.64 | 1 |
| Unit-size | Sharpe | No | 1.32 | - |

Threshold: cliff_score > 3.0. Both views show cliff-like behavior in terminal and CAGR metrics. The defining cliff in native view is trade #6 (episode 103, 2023-01-09, +$30K, +32.8%) whose removal drops CAGR from 19.3% to -26.1%.

## Giveback Ratio

| Statistic | Value |
|-----------|-------|
| Valid trades | 188 / 192 |
| Mean giveback | 4.08x |
| Median giveback | 1.21x |
| P90 | 6.89x |
| P95 | 17.94x |
| Trades giving back >50% MFE | 81.9% |
| Trades giving back >75% MFE | 69.1% |

By holding time:
- **<1 day**: mean giveback 17.0x (mostly quick losers — MFE tiny, loss large)
- **1-3 days**: mean giveback 5.4x
- **3-7 days**: mean giveback 2.7x
- **7-14 days**: mean giveback 0.77x
- **14+ days**: mean giveback 0.33x (winners run — trail captures the move)

The trail stop works well for sustained moves but gives back heavily on short, choppy entries. The 83.9% of trades exiting via trail stop have mean giveback 3.15x vs 8.96x for trend-exit trades.

## Skip-After-N-Losses

| N | Trades Skipped | Winners Skipped | Top-10 Trades Hit | Delta Sharpe | Verdict |
|---|---------------|----------------|-------------------|-------------|---------|
| 2 | 37 | 18 | 3 | -0.263 (-23.1%) | HARMFUL |
| 3 | 16 | 7 | 2 | -0.109 (-9.6%) | HARMFUL |
| 4 | 8 | 3 | 0 | +0.001 (+0.1%) | NEUTRAL |
| 5 | 5 | 1 | 0 | +0.004 (+0.3%) | NEUTRAL |

**Key insight**: At N=2, the strategy skips 37 trades (19.3%), of which 18 are winners and 3 are top-10 trades. Behavioral loss aversion at this threshold destroys 23% of Sharpe. At N=4-5, the skip count drops to 5-8 and avoids hitting home-run trades, making it neutral.

**Implication**: A trader who loses discipline after 2-3 consecutive losses will miss critical winning trades. The big winners often follow loss clusters — this is the nature of trend-following. Every signal must be taken.

## Implications for Live Trading

1. **Every signal matters.** Missing 6 trades (3.1%) can make the difference between 62% CAGR and bankruptcy. Automation is essential.
2. **Behavioral discipline is critical.** Skip-after-2-losses destroys 23% of Sharpe. The emotional temptation to "sit out" after a losing streak is the primary behavioral risk.
3. **The strategy is not a grinder.** It will have long losing streaks (max: 9 consecutive losses) and most trades lose money (58.3%). The payoff comes from rare, sustained moves.
4. **Giveback is inherent to the trail stop.** Median giveback of 1.21x means the typical trade gives back slightly more MFE than it keeps. This is acceptable because the few trades that run far (14d+) give back only 0.33x.
5. **Outage risk is extreme.** Missing the wrong week could eliminate 23% of total PnL (top trade = $49.9K, 22.9% of total).
