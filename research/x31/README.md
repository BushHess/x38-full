# X31 — Final Closure Studies (D1 Regime Exit + Re-entry Barrier)

**Date**: 2026-03-12
**Registry**: Studies #68 (X31-A) and #69 (X31-B)
**Verdict**: **STOP** (both branches)

---

## X31-A: D1 Regime Exit — Mid-Trade D1 EMA Flip

### Hypothesis

D1 EMA(21) is the strongest proven signal (p=1.5e-5, 16/16 ALL metrics),
currently used only at entry. If D1 regime flips bearish during a trade
BEFORE trail/EMA exit fires, exiting early might reduce avg_loser
(the #1 Sharpe predictor per X28, R²=0.306).

### Results

| Metric | Value | Gate |
|--------|-------|------|
| Coverage | 35/199 trades (17.6%) | G1 PASS (>10%) |
| Timing | Median 5 bars (20h) earlier | G2 PASS (>2 bars) |
| Losers saved | +2.13% avg delta | — |
| Winners cut | -10.39% avg delta | G4 PASS |
| **Selectivity** | **0.21** | **G3 FAIL (<< 1.5 threshold)** |
| Top-20 flips | 1/20 | Low winner damage |

### Verdict: STOP (not selective)

The D1 flip occurs in 35 trades but has selectivity ratio 0.21 — it cuts
winners 5× more severely than it saves on losers. Per-trade loser benefit
+2.13% vs winner cost -10.39%.

Same fundamental constraint as X5/X10/X23: fat-tail alpha concentration
(top 5% trades = 129.5% of profits) means ANY mid-trade exit risks cutting
the trades that matter most.

---

## X31-B: Re-entry Barrier Oracle

### Hypothesis

After a churn exit (trail stop followed by re-entry within N bars),
a perfect oracle that blocks only losing re-entries should improve Sharpe.
If oracle ceiling is high enough (> +0.08), a learned barrier is worth pursuing.

### Results

| Cost | Oracle ΔSharpe | Anti-Oracle ΔSharpe | Ratio |
|------|----------------|---------------------|-------|
| 15 bps | +0.033 | -0.199 | 6.0x |
| 20 bps | +0.038 | -0.204 | 5.4x |
| 25 bps | +0.026 | -0.189 | 7.3x |

- Oracle ΔSharpe: +0.038 at 20 bps — below +0.08 GO threshold (G1 FAIL)
- Anti-oracle: blocking GOOD re-entries costs -0.204 Sharpe
- Error cost ratio: 8.1× benefit per event → any real model's mistakes dominate
- LOYO stability: worst year 2022 (+0.019), all years positive

### Verdict: STOP (oracle ceiling too low)

**Closure is due to economic ceiling, not model quality or overfit.**
Even a perfect oracle cannot improve Sharpe enough to justify the risk of
error. At 8.1× asymmetry, a model would need >90% precision to break even —
far beyond any achievable level on OHLCV features (cf. X13 AUC=0.805).

---

## Combined Conclusion

Both X31-A and X31-B confirm the structural constraints identified across
the 68-study research program:

1. **Fat-tail alpha** (129.5% in top 5%) blocks mid-trade interventions
2. **Payoff asymmetry** (8:1) makes errors catastrophic
3. **No viable mid-trade action** exists — static suppress is the only actuator

## Artifacts

```
code/
  x31_diagnostic.py           — D1 regime exit diagnostic (Phase 0A)
  x31_phase0_reentry_barrier.py — Re-entry barrier oracle (Phase 0B)
figures/
  Fig_bars_saved_hist.png      — Distribution of bars saved by early exit
  Fig_concentration.png        — PnL concentration analysis
  Fig_loyo_stability.png       — Leave-one-year-out stability
  Fig_oracle_delta_by_cost.png — Oracle ceiling vs cost
  Fig_pnl_delta_by_reason.png  — PnL impact by exit reason
  Fig_scatter_actual_vs_hyp.png — Actual vs hypothetical exit comparison
tables/
  Tbl_trade_diagnostic.csv     — Per-trade D1 flip diagnostic (35 trades)
  x31_phase0_summary.json      — Phase 0A gate results
  x31_phase0_barrier_summary.json — Phase 0B oracle results
prompte/
  context.md                   — Initial hypothesis and decision matrix
```
