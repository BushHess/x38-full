# X36 VCBB Bias Test Battery — Results

**Date**: 2026-03-17 00:39
**Bootstrap paths**: 500 per configuration
**Cost**: 20 bps RT | **Seed**: 42

## Test 1: Block-Size Sensitivity

**Question**: Does bootstrap Sharpe change with block size? If V3 improves disproportionately → VCBB was unfairly penalizing V3.

### Median Bootstrap Sharpe by Block Size

| Block Size | Days | V3 | V4 | E5+EMA21D1 | V3/E5 Ratio |
|-----------|------|----|----|------------|-------------|
| 30 | 5d | 0.406 | 0.603 | 0.616 | 0.659 |
| 60 | 10d | 0.547 | 0.791 | 0.785 | 0.697 |
| 120 | 20d | 0.741 | 1.023 | 1.030 | 0.719 |
| 180 | 30d | 0.860 | 1.117 | 1.114 | 0.772 |
| 360 | 60d | 1.009 | 1.392 | 1.331 | 0.758 |

### P(Sharpe > 0) by Block Size

| Block Size | V3 | V4 | E5+EMA21D1 |
|-----------|----|----|------------|
| 30 | 85.4% | 93.2% | 93.6% |
| 60 | 90.4% | 96.6% | 96.8% |
| 120 | 97.2% | 99.2% | 99.2% |
| 180 | 97.0% | 99.2% | 98.8% |
| 360 | 99.0% | 100.0% | 100.0% |

### Test 1 Interpretation

- V3/E5 ratio range: 0.659 — 0.772 (spread: 0.113)
- Monotonically increasing: NO
- **VERDICT**: Non-monotonic pattern — relationship is complex. No clear regime destruction bias.

---

## Test 2: Regime-Conditioned Bootstrap

**Question**: Does sampling from same-regime source data help V3 disproportionately?

*Note: This method samples ratios from same-regime segments of the original data. The realized regime on synthetic paths (as measured by D1 EMA(21)) may differ from the source regime due to path-dependent EMA accumulation.*

### VCBB vs Regime-Conditioned: Median Sharpe

| Strategy | VCBB | Regime-Conditioned | Delta | % Change |
|----------|------|-------------------|-------|----------|
| V3 | 0.554 | 0.309 | -0.245 | -44.2% |
| V4 | 0.783 | 0.497 | -0.286 | -36.5% |
| E5+EMA21D1 | 0.786 | 0.522 | -0.265 | -33.7% |

### P(Sharpe > 0) Comparison

| Strategy | VCBB P(Sh>0) | Regime P(Sh>0) |
|----------|-------------|----------------|
| V3 | 92.6% | 80.6% |
| V4 | 97.6% | 88.8% |
| E5+EMA21D1 | 97.4% | 91.4% |

### Test 2 Interpretation

- V3 gain from regime-conditioned source: -0.245
- E5 gain from regime-conditioned source: -0.265
- Differential (V3 gain - E5 gain): +0.020
- **VERDICT**: Both strategies gain similarly (differential +0.020). Regime-conditioned source does not differentially affect V3 vs E5.

---

## Test 3: Time-Stop / Cooldown Ablation

**Question**: Do V3's time_stop (30 bars) and cooldown (6 bars) improve or hurt E5's performance?

### Full-Sample Results

| Variant | Sharpe | CAGR% | MDD% | Trades |
|---------|--------|-------|------|--------|
| E5_base | 1.663 | 74.9 | 36.3 | 188 |
| E5+TS30 | 1.464 | 60.2 | 37.2 | 294 |
| E5+CD6 | 1.508 | 62.7 | 36.3 | 175 |
| E5+TS30+CD6 | 1.473 | 56.8 | 39.5 | 258 |
| V3 | 1.496 | 55.5 | 37.3 | 211 |

### Bootstrap Results (blksz=60, 500 paths)

| Variant | Med Sharpe | P(Sh>0) | Med CAGR% | Med MDD% |
|---------|-----------|---------|-----------|----------|
| E5_base | 0.817 | 98.0% | 26.5 | 51.3 |
| E5+TS30 | 0.727 | 96.2% | 21.8 | 52.4 |
| E5+CD6 | 0.709 | 96.4% | 21.1 | 51.9 |
| E5+TS30+CD6 | 0.601 | 94.4% | 15.7 | 51.4 |
| V3 | 0.569 | 93.6% | 14.3 | 51.5 |

### Regime Decomposition (Sharpe)

| Variant | Pre-2021 | 2021-2022 | 2023-2024 | 2025+ |
|---------|-------|-------|-------|-------|
| E5_base | 2.57 | 1.00 | 1.86 | 0.42 |
| E5+TS30 | 2.28 | 0.88 | 1.61 | 0.09 |
| E5+CD6 | 2.43 | 0.94 | 1.47 | 0.51 |
| E5+TS30+CD6 | 1.86 | 1.19 | 1.64 | 0.92 |
| V3 | 1.18 | 1.17 | 2.31 | 0.74 |

### Test 3 Interpretation

- E5_base bootstrap: 0.817
- E5+TS30: 0.727 (delta: -0.090)
- E5+CD6: 0.709 (delta: -0.108)
- E5+TS30+CD6: 0.601 (delta: -0.215)
- V3 reference: 0.569

- **VERDICT**: Time-stop and/or cooldown HURT E5's bootstrap Sharpe. V3's regime stability comes at the COST of robustness. These mechanisms are NOT free improvements — they trade fat-tail alpha for per-epoch consistency.

---

## Overall Conclusion

The three tests empirically answer: "Does VCBB unfairly penalize V3?"

| Test | Question | Answer |
|------|----------|--------|
| Block-size sensitivity | Ranking changes with blksz? | UNCLEAR — non-monotonic pattern |
| Regime conditioning | V3 helped more than E5? | NO — equal effect (+0.020) |
| Time-stop/cooldown ablation | V3's mechanisms help E5? | HURT bootstrap (-0.215 Sharpe) |