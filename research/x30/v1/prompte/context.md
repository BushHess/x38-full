# X30: Context Document — Research History & Key Findings

Tài liệu này cung cấp context đầy đủ cho phiên nghiên cứu mới. Đọc trước khi
bắt đầu code.

---

## 1. Algorithm Pipeline

**VTREND E5+EMA1D21** là primary algorithm (promoted 2026-03-09).

```
Entry:  EMA(30) > EMA(120) AND VDO > 0 AND D1_close > D1_EMA(21)
Exit:   Price < Peak - 3.0 * RobustATR(20)  OR  EMA(30) < EMA(120)
Size:   f = 0.30 (vol-target 15%)
```

4 proven components: EMA crossover entry, ATR trail + EMA exit, VDO filter, EMA(21d) regime.
43+ studies completed. Nothing beats this base at realistic costs (15-30 bps RT).

## 2. Churn Filter Research (X12-X19) — Summary

| Study | What | Verdict |
|-------|------|---------|
| X12 | E5-E0 gap analysis | Path-state noise (P=46.4%) |
| X13 | Churn predictability | AUC=0.805, ceiling +0.845 Sh |
| X14 | 4 filter designs | Design D PROMOTE (L2 logistic, 7 features) |
| X15 | Dynamic evaluation | ABORT (7 trades, catastrophic) |
| X16 | WATCH state machine | ALL_FAIL (bootstrap 49.8%) |
| X17 | Percentile selective exit | NOT_TEMPORAL (WFO 25%) |
| X18 | α-percentile static mask | PROMOTE (6/6 gates, α=40%) |
| X19 | Alt actuators (exit+re-enter, partial runner) | CLOSE (both fail G1) |

Key conclusion: Static suppress is the only robust actuator. But it's binary.

## 3. X22 Cost Sensitivity — Critical Finding

Churn filters HURT at < 30 bps. E5+EMA1D21 (no filter) wins at 10-20 bps.
X18 crossover ~35 bps, X14D crossover ~70 bps.
At realistic Binance costs (20-30 bps RT): skip churn filter.

## 4. X29: Optimal Stack — What Was Tested

12 strategies = 2 (Monitor V2 ON/OFF) × 3 (Churn: NONE/X14D/X18) × 2 (Trail: 3.0/4.5)
108 backtests across 9 cost levels.

### Gate Results
- T0 PASS: S07 (Mon) beats Base at all 9 costs
- T1 WARN: X14D×T45 interaction > 0.10 at 9/9 costs
- T2 PASS: Mon+X14D 75%, Mon+X18 75% WFO win rate
- T3 FAIL: Best P(ΔSh>0) = 45.8% (Mon) < 55% threshold
- T4/T5 SKIPPED

### Full-Sample Winners at 25 bps
| Strategy | Sharpe | CAGR% | MDD% | Calmar |
|----------|--------|-------|------|--------|
| Base (S01) | 1.602 | 70.5 | 38.8 | 1.819 |
| Mon (S07) | **1.733** | **76.5** | 38.8 | 1.974 |
| Mon+X14D (S09) | 1.585 | 73.2 | **31.1** | **2.354** |
| Mon+X18 (S11) | 1.678 | 77.9 | 37.9 | 2.055 |

Verdict: No combination reliably beats Base in bootstrap → RECOMMEND Base.

## 5. X29 Signal Diagnostic — The Key Insight

### Sparse Guard Hypothesis (REJECTED)
- VCBB preserves bear market structure: 88.4% of bootstrap paths have RED bars
- Monitor is active on 85.2% of paths → not "too sparse" for bootstrap
- Conditional P(ΔSh>0) = 47.2% (not better than unconditional 40.2%)

### X18 Root Cause Decomposition
- At 0 cost (gross): X18 Sharpe LOWER by -0.060 → net alpha loss
- At 25 bps: cost savings = 161 bps/yr, but alpha loss > savings
- Crossover at exactly 35 bps (confirmed by X22)
- **Hypothesis: binary suppress destroys information in the signal gradient**
  (Plausible explanation, NOT yet proven — formal study must validate)

### Signal Appears Informative — REQUIRES OOS VALIDATION (Churn Score Quartiles)
```
Q1 (low score): n=46, avg ret=-3.44%, WR=8.7%
Q2:             n=46, avg ret=-0.40%, WR=41.3%
Q3:             n=45, avg ret=+1.20%, WR=53.3%
Q4 (high score): n=46, avg ret=+13.61%, WR=84.8%
```
Full-sample monotonic relationship. WARNING: This is IN-SAMPLE. The model was
trained on the same data it was evaluated on. Temporal stability and OOS
discrimination have NOT been tested. The quartile spread could be an artifact
of overfitting.

### X18(partial) Pilot — Fractional Actuator (UNVALIDATED)
Replace binary suppress with partial exit: sell (1-partial_frac) when trail fires
and score > threshold, keep partial_frac running with original trail.

Pilot results (partial_frac=0.50, single run, NOT optimized):
```
Cost   Base_Sh  X18partial_Sh  ΔSh    Base_MDD  X18partial_MDD  ΔMDD
10 bps  1.704    1.741        +0.037   37.6%     25.9%          -11.7pp
15 bps  1.670    1.711        +0.041   38.0%     26.2%          -11.8pp
25 bps  1.602    1.650        +0.048   38.8%     26.9%          -11.9pp
50 bps  1.432    1.499        +0.067   41.6%     29.9%          -11.7pp
100 bps 1.091    1.196        +0.105   50.1%     35.6%          -14.5pp
```

Full-sample results only. 153 trades (vs 199 Base).

CAVEATS — read before drawing conclusions:
- This is a SINGLE pilot run with a SINGLE arbitrary parameter (0.50)
- We are studying this BECAUSE the pilot looked good → selection bias
- MDD reduction (~12pp) could be entirely from reduced exposure (trivial)
  or from timing (genuine alpha) — mechanism UNKNOWN until decomposed
- Bootstrap P(ΔSh>0) = 37.2% — WORSE than coin flip
- ΔSh = +0.048 is small relative to strategy variance

### Bootstrap FAILS — The Hard Constraint
P(ΔSh>0) = 37.2% for X18(partial) at 25 bps (500 VCBB) < 55% threshold.
This means: on random price paths, X18(partial) is MORE LIKELY to HURT than help.
Full-sample improvement could be driven by a few specific historical episodes.

### Monitor V2 for Sizing — No Value
AMBER entries actually outperform NORMAL entries (WR 49.2% > 44.4%).
Monitor signal has no value for position sizing at entry time.

## 6. What X30 Must Answer

The pilot suggests fractional actuator MIGHT improve on binary suppress.
But the evidence is weak: single run, unvalidated, bootstrap-negative.
The formal study must HONESTLY determine whether this is real or noise:

1. Sweep partial_frac to find optimum
2. Test continuous sizing (use score directly, not just threshold)
3. WFO validate top configs
4. Bootstrap test
5. If bootstrap fails again: understand WHY (diagnostics, not bypassing)

The bar: P(ΔSh>0) >= 55% in VCBB bootstrap. If this fails, the finding
does not have sufficient statistical evidence to deploy — regardless of
how good the full-sample numbers look.

## 7. Critical Bug Reference

In `_sim_x18_partial()`, when a full exit fires after partial exits:
```python
# WRONG: cash = received  ← destroys partial exit cash
# RIGHT: total_received = cash + received; cash = total_received
```
This bug caused Sharpe=-2.568, MDD=100% before fix. Always preserve accumulated
cash from partial exits when computing full exit proceeds.
