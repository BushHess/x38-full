# X16: Stateful Exit — WATCH State & Adaptive Trail — Report

**Date**: 2026-03-10
**Verdict**: ALL_FAIL (Design E passes G0+G1, fails G2 bootstrap — edge is path-specific)

## Central Question

X14 proved churn IS predictable (AUC=0.805) and a static logistic filter captures
10.9% of the oracle ceiling. X15 proved dynamic per-bar evaluation causes a
feedback loop (suppress-forever). Can a STATEFUL exit — querying the model ONCE
at first trail breach, then running a bounded grace window — break the feedback
loop while capturing more of the +0.845 Sharpe oracle ceiling?

## Design Summary

### Design F: Regime-Gated Adaptive Trail (no model, 1 param δ)
- Wider trail (`trail_mult + δ`) when trend+regime are favourable
- No model, no state machine — simple adaptive trail

### Design E: WATCH State Machine (3 params: τ, G, δ)
- States: FLAT → LONG_NORMAL → LONG_WATCH
- At first trail breach: query logistic model ONCE
- If P(churn) > τ AND trend+regime positive → enter WATCH state
- WATCH: grace window of G bars, deeper fallback stop at `trail + δ × ATR`
- Exit WATCH on: reclaim (back above original trail), deeper stop, timeout, trend reversal

## Results

### T0: MFE/MAE GO/NO-GO

168 trail stops (106 churn, 62 non-churn). GO confirmed.

| G | Churn MFE | Churn MAE | Reclaim% | Non-churn Deeper% |
|---|-----------|-----------|----------|-------------------|
| 2 | 312 | 248 | 50% | 50% |
| 4 | 564 | 342 | 70% | 70% |
| 8 | 967 | 435 | 80% | 80% |
| 12 | 1236 | 471 | 90% | 90% |
| 20 | 1633 | 776 | 90% | 90% |

At G=8: churn trades see 2.2× more favourable than adverse excursion.
Non-churn trades hit the deeper stop 80% of the time — the deeper stop works.

### T1: Risk-Coverage Curve (160 configs)

| Config | Sharpe | d_Sharpe | MDD | Suppression% |
|--------|--------|----------|-----|-------------|
| τ=0.85 G=8 δ=2.0 | 1.424 | +0.088 | 38.9% | 42% |
| τ=0.70 G=8 δ=1.5 | 1.411 | +0.075 | 35.7% | 64% |
| τ=0.70 G=6 δ=2.0 | 1.400 | +0.064 | 35.4% | 62% |
| τ=0.90 G=8 δ=2.0 | 1.398 | +0.062 | 38.9% | 24% |

Best in-sample: τ=0.85, G=8, δ=2.0 → +0.088 Sharpe (10.4% of oracle ceiling).

### T2: In-Sample Screening

| Design | Best Params | Sharpe | d_Sharpe | Trades | G0 |
|--------|-------------|--------|----------|--------|----|
| F | δ=2.0 | 1.330 | -0.006 | 121 | **FAIL** |
| E | τ=0.85,G=8,δ=2.0 | 1.424 | +0.088 | 162 | PASS |

Design F: Adaptive trail has zero in-sample lift. The trail-width advantage is
cancelled by occasional larger losses when the wider trail holds through reversals.

Design E WATCH statistics (in-sample):
- 88 WATCH entries out of 210 trail events (42%)
- 66 reclaimed (75%) — price recovered above original trail
- 10 hit deeper stop (11%)
- 12 timed out at G=8 bars (14%)
- 0 trend exits during WATCH
- 122 direct trail exits (model score < τ or conditions not met)

### T3: Walk-Forward Validation (4 folds)

| Fold | Year | τ | E0 Sharpe | E Sharpe | d_Sharpe | Result |
|------|------|---|-----------|----------|----------|--------|
| 1 | 2022 | 0.85 | -0.930 | -0.863 | +0.067 | WIN |
| 2 | 2023 | 0.80 | 1.203 | 1.442 | +0.239 | WIN |
| 3 | 2024 | 0.85 | 1.696 | 1.782 | +0.087 | WIN |
| 4 | 2025 | 0.85 | 0.069 | 0.093 | +0.023 | WIN |

Win rate: **100%**, mean d_sharpe: **+0.104**

**G1: PASS** — remarkably consistent. All 4 OOS folds positive.

### T4: Bootstrap (500 VCBB paths)

| Metric | Value |
|--------|-------|
| d_sharpe median | +0.000 |
| d_sharpe [p5, p95] | [-0.057, +0.085] |
| d_sharpe mean | +0.008 |
| P(d_sharpe > 0) | 49.8% |
| d_mdd median | +0.0pp |
| d_mdd [p5, p95] | [-4.1pp, +3.1pp] |

**G2: FAIL** (49.8% < 60%)
**G3: PASS** (+0.0pp ≤ +5.0pp)

The WATCH mechanism shows zero edge on synthetic bootstrap paths.
The 100% WFO win rate on real data doesn't replicate when price paths are reshuffled.

## Gate Summary

| Gate | Condition | Result |
|------|-----------|--------|
| G0 | In-sample d_sharpe > 0 | PASS (+0.088) |
| G1 | WFO ≥ 75% | PASS (100%) |
| G2 | Bootstrap P(d>0) > 60% | **FAIL** (49.8%) |
| G3 | Median d_mdd ≤ +5pp | (PASS, +0.0pp) |
| G4 | Jackknife ≤ 2 negative | (not reached) |
| G5 | PSR > 0.95 | (not reached) |

Design F: FAIL at G0 (no in-sample lift).
Design E: FAIL at G2 (bootstrap edge = 0).

## Key Insight

**The WATCH mechanism captures real-path autocorrelation that bootstrap destroys.**

WFO shows 100% wins because BTC's actual H4 returns have specific mean-reversion
patterns after trail breaches that are consistent across 2022-2025. The logistic
model (trained on the same price series) learns these patterns. But VCBB bootstrap
resamples return blocks, breaking the local structure that makes WATCH effective.

This means:
1. The +0.088 Sharpe lift is real on THIS specific BTC path
2. It depends on path-specific autocorrelation structure
3. On a structurally different path (different coin, regime shift), the edge vanishes
4. Bootstrap correctly identifies this as non-robust alpha

Comparison with X14 Design D:
- X14 D: static mask, Sharpe 1.428, bootstrap P(d>0)=65% → PASS
- X16 E: WATCH state, Sharpe 1.424, bootstrap P(d>0)=49.8% → FAIL
- Both capture ~10% of oracle. X14's static approach is more robust.

## Why Design F Failed

Adaptive trail (wider in trend+regime) fails because:
1. The wider trail prevents exit during genuine reversals too
2. d_sharpe = -0.006 — essentially neutral
3. The problem isn't trail WIDTH but trail TIMING (which bars to hold through)
4. This confirms X12's finding: trail-stop mechanics are not the bottleneck

## Implications for Trail-Stop Churn Research

The X12-X16 series has thoroughly explored the churn problem:

| Study | Approach | Verdict |
|-------|----------|---------|
| X12 | Mechanism forensics | Churn = path-state, not repairable |
| X13 | Predictability | AUC=0.805, oracle +0.845 Sharpe |
| X14 | Static logistic filter | PROMOTE_D (7-feature, 10.9% ceiling) |
| X15 | Dynamic filter | ABORT (feedback loop, 7 trades) |
| X16 | Stateful exit (WATCH) | ALL_FAIL (path-specific, not robust) |

**Conclusions:**
1. ~10% of the oracle ceiling is capturable (X14 D and X16 E both reach ~0.088)
2. The robust 10% comes from X14's static market-state features, not trade-context
3. Stateful approaches (WATCH) exploit path autocorrelation that doesn't generalize
4. The remaining 90% of the oracle ceiling is not accessible with current methods
5. **Design D (X14 static mask) remains the only bootstrap-validated churn filter**

## Decision

Per SPEC.md decision matrix: ALL designs fail → **HOLD current algorithm**.
Design D from X14 remains the only promoted churn filter.

No further X-series churn studies recommended — the ceiling is mapped.

## Artifacts

- `x16_results.json` — all test results
- `x16_mfe_mae.csv` — T0 MFE/MAE by grace window
- `x16_risk_coverage.csv` — T1 160-config sweep
- `x16_screening.csv` — T2 design screening
- `x16_wfo.csv` — T3 WFO fold details
- `x16_bootstrap.csv` — T4 bootstrap distributions
- `x16_comparison.csv` — T7 strategy comparison
