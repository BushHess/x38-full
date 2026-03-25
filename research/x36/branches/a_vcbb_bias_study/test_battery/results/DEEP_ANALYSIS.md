# X36 Deep Analysis — Path-Level & Trade-Level Evidence

**Date**: 2026-03-16 21:11
**Bootstrap paths**: 500 per config | **Cost**: 20 bps RT | **Seed**: 42

## Test 4: Paired Path Delta + Wilcoxon

For each bootstrap path, both V3 and E5 see identical synthetic data. δ_i = Sharpe(V3) − Sharpe(E5). Paired analysis is strictly more powerful than comparing medians.

| Block Size | δ Median | δ Mean | δ Std | P(V3>E5) | Wilcoxon p | N |
|-----------|----------|--------|-------|----------|-----------|---|
| 60 (10d) | -0.2530 | -0.2450 | 0.239 | 15.4% | 6.52e-61 | 500 |
| 360 (60d) | -0.2995 | -0.3202 | 0.278 | 10.2% | 1.71e-69 | 500 |

### Test 4 Interpretation

- blksz=60: δ median = -0.2530, P(V3>E5) = 15.4%
- blksz=360: δ median = -0.2995, P(V3>E5) = 10.2%
- V3 win rate WORSENS by -5.2pp with larger blocks → longer blocks hurt V3 relatively
- **VERDICT**: E5 > V3 is **HIGHLY SIGNIFICANT** on paired paths (Wilcoxon p = 6.52e-61). Not noise — E5 genuinely outperforms V3 on the same data.

---

## Test 5: δ vs Regime Quality Correlation

If VCBB destroys regimes that V3 needs, δ should correlate positively with regime quality: V3 should do relatively better on paths with cleaner/longer regimes.

- **Spearman ρ = -0.1153** (p = 0.0098)
- Pearson r = -0.1079 (p = 0.0158)
- Regime quality range: 6.8 — 11.1 D1 bars (median: 8.4)

### Tercile Analysis

| Regime Quality | RQ Range | δ Median | P(V3>E5) | N |
|---------------|----------|----------|----------|---|
| Low (choppy) | 6.8–8.2 | -0.2221 | 16.8% | 167 |
| Medium | 8.2–8.7 | -0.2654 | 15.5% | 168 |
| High (clean) | 8.8–11.1 | -0.2896 | 13.9% | 165 |

### Test 5 Interpretation

- NEGATIVE correlation: V3 does WORSE on cleaner-regime paths
- **VERDICT**: Regime quality HURTS V3 relative to E5. Opposite of analyst's hypothesis.

---

## Test 6: Trade-Duration P&L Decomposition (Real Data)

Shows exactly where E5's alpha comes from and what V3's time_stop=30 bars would truncate.

### E5 Trade Statistics

- Total trades: 188
- Avg duration: 37.0 bars (6.2 days)
- Median duration: 28.0 bars (4.7 days)
- Max duration: 212 bars (35 days)

### P&L by Duration Bucket

| Duration | Trades | % Trades | P&L Contribution | Avg Return | Max Return | Win Rate |
|----------|--------|----------|-----------------|------------|------------|----------|
| ≤10 bars (≤1.7d) | 31 | 16.5% | -33.5% | -2.15% | 8.05% | 16.1% |
| 11-30 bars (1.7-5d) | 73 | 38.8% | -53.7% | -2.41% | 7.88% | 19.2% |
| 31-60 bars (5-10d) | 54 | 28.7% | 40.5% | 3.09% | 25.07% | 64.8% |
| 61-120 bars (10-20d) | 24 | 12.8% | 83.0% | 14.02% | 61.74% | 95.8% |
| >120 bars (>20d) | 6 | 3.2% | 63.7% | 39.38% | 68.07% | 100.0% |

### V3 Time-Stop Truncation Impact

- E5 trades > 30 bars: **84** (44.7% of all trades)
- P&L exposure (upper bound): **187.2%** of total profit — these trades WOULD BE AFFECTED, not fully lost
- **Actual ablation loss** (E5 vs E5+TS30): **47.3%** of profit (E5+TS30: 294 trades, Sharpe 1.464, CAGR 60.2%)

#### Top 5 Longest E5 Trades

| Bars | Days | Return% | P&L | Exit |
|------|------|---------|-----|------|
| 212 | 35.3 | 40.77% | $105437.75 | vtrend_e5_ema21_d1_trail_stop |
| 175 | 29.2 | 25.51% | $44237.50 | vtrend_e5_ema21_d1_trail_stop |
| 147 | 24.5 | 68.07% | $34682.42 | vtrend_e5_ema21_d1_trail_stop |
| 131 | 21.8 | 32.76% | $51854.37 | vtrend_e5_ema21_d1_trail_stop |
| 123 | 20.5 | 58.34% | $50670.92 | vtrend_e5_ema21_d1_trail_stop |

#### Top 5 Most Profitable E5 Trades

| Bars | Days | Return% | P&L | Exit |
|------|------|---------|-----|------|
| 212 | 35.3 | 40.77% | $105437.75 | vtrend_e5_ema21_d1_trail_stop |
| 73 | 12.2 | 25.38% | $89679.87 | vtrend_e5_ema21_d1_trail_stop |
| 115 | 19.2 | 31.80% | $52811.92 | vtrend_e5_ema21_d1_trail_stop |
| 131 | 21.8 | 32.76% | $51854.37 | vtrend_e5_ema21_d1_trail_stop |
| 121 | 20.2 | 10.79% | $51273.30 | vtrend_e5_ema21_d1_trail_stop |

### V3 vs E5 Comparison

| Metric | E5 | V3 | Δ |
|--------|----|----|---|
| Trades | 188 | 211 | +23 |
| Avg bars held | 37.0 | 25.1 | -11.9 |
| Max bars held | 212 | 30 | -182 |
| Sharpe | 1.663 | 1.496 | -0.168 |
| CAGR% | 74.9 | 55.5 | -19.3 |
| MDD% | 36.3 | 37.3 | +1.0 |

### Test 6 Interpretation

- P&L exposure: 187% of E5 profits come from trades > 30 bars (upper bound)
- Actual ablation loss (E5 vs E5+TS30): **47.3%** of total profit
- **VERDICT**: Fat-tail truncation is the DOMINANT mechanism explaining V3 < E5. V3's time_stop curtails the highest-returning trades, causing 47% realized profit loss.

---

## Overall Conclusion

| Test | Question | Finding |
|------|----------|---------|
| Paired delta | Is E5>V3 statistically significant? | **YES** (Wilcoxon p = 6.52e-61) |
| Regime correlation | Does regime quality help V3? | **WEAK** (ρ = -0.115) |
| Trade decomposition | What does V3 sacrifice? | **47%** actual profit loss from time_stop truncation |