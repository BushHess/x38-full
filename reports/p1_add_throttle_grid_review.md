# P1 Add-Throttle Grid Review

**Verdict: NOT_ROBUST** — Abandon P1.

**Date:** 2026-02-24
**Inputs:** `btc-spot/results/p1_add_throttle_grid_3x3.csv`, `btc-spot/reports/p1_add_throttle_grid_3x3.md`

---

## 1. Selection Discipline

Selection is based on **FULL period only** (2019-01-01 to 2026-02-20, harsh scenario). HOLDOUT (last 20%) is reported for sanity-checking but does NOT influence the PASS/FAIL determination or region selection. This is confirmed in both the grid runner (`_evaluate_pass_full` governs selection; `_evaluate_holdout_ok` is informational) and the grid report header.

---

## 2. PASS_FULL Heatmap

```
             dd2=0.14    dd2=0.18    dd2=0.22
dd1=0.06      FAIL        FAIL        FAIL
dd1=0.08      FAIL        FAIL        FAIL
dd1=0.10      FAIL        FAIL        FAIL
```

**0/9 cells pass.** No connected PASS region exists. Not even a single passing cell.

Every cell fails on `ci95_high < 0` (bootstrap 95% CI entirely below zero). Six of nine cells additionally fail on `delta_mdd_pp > +2.0pp`.

---

## 3. Required Checks (per acceptance rubric §5.3)

| # | Check | Result | Detail |
|---|-------|--------|--------|
| R1 | G1 (MDD ≤ +2pp) passes in ≥ 8/9 | **FAIL: 3/9** | Only dd2=0.14 column passes (delta_mdd: 0.94–1.65pp). All dd2=0.18 cells show +3.97pp; dd2=0.22 shows +2.15–3.26pp. |
| R2 | G2 (return guardrail) passes in ≥ 8/9 | **FAIL: 0/9** | CAGR delta ranges from −18.6pp to −27.4pp, far beyond any tolerance. |
| R3 | Pathology improves in ≥ 7/9 | PASS: 9/9 (fees + emergency DD) | But the improvements are a side-effect of trade suppression, not targeted pathology reduction. |
| R4 | `p_gt_0 ≥ 0.40` in ALL 9 cells | **FAIL: 0/9** | p_gt_0 ranges from 0.0002 to 0.0053. The maximum across the entire grid is 0.53%. |
| R5 | `mean_fills_ep ≥ 1.0` in ALL 9 cells | PASS (trivially) | Fills per episode actually *increased* in 7/9 cells (see §5). |

**Three of five required checks fail.** R2 and R4 fail in every single cell. This is a categorical rejection — not a borderline case.

---

## 4. HOLDOUT Sanity Check (informational)

| dd1 | dd2 | HOLDOUT_OK | delta_score | ci95_high | activation |
|----:|----:|:----------:|------------:|----------:|-----------:|
| 0.06 | 0.14 | YES | −37.0 | +0.000024 | 0.806 |
| 0.06 | 0.18 | NO | −54.9 | −0.000017 | 0.573 |
| 0.06 | 0.22 | NO | −40.0 | −0.000010 | 0.032 |
| 0.08 | 0.14 | YES | −33.7 | +0.000030 | 0.817 |
| 0.08 | 0.18 | YES | −57.1 | +0.000004 | 0.776 |
| 0.08 | 0.22 | NO | −37.6 | −0.000006 | 0.045 |
| 0.10 | 0.14 | YES | −33.7 | +0.000030 | 0.817 |
| 0.10 | 0.18 | YES | −57.0 | +0.000004 | 0.776 |
| 0.10 | 0.22 | NO | −38.6 | −0.000007 | 0.047 |

Five holdout cells show HOLDOUT_OK = YES, but this does not rehabilitate P1. The YES cells still have massive negative score deltas (−33 to −57). The holdout's CI crossing zero in some cells reflects lower statistical power on the shorter sample, not a genuine improvement signal. The holdout confirms the direction of harm: score degrades everywhere.

**Notable:** dd2=0.22 holdout cells show `delta_emergency_dd_share_pp = +1.268` — emergency DD share actually *increases* in the holdout, contradicting the full-period improvement. This further undermines any case for the overlay.

---

## 5. Pathology vs. Return Trade-Off

### 5.1 Fees

`delta_fees_usd` is negative (fewer fees) in all 9 FULL cells: −$8,814 to −$11,613. This is not targeted fee-drag reduction — it is wholesale trade suppression. The throttle blocks 60–91% of add attempts (`add_blocked_count / add_attempt_count`), starving the strategy of position-building activity. Fewer trades mechanically means fewer fees, but also fewer opportunities to capture upside.

### 5.2 Buy Fills Per Episode

`delta_buy_fills_per_episode` is **positive** in 7/9 FULL cells (range: +0.6 to +15.3). Only two cells show marginally negative values: (0.08, 0.18) at +0.611 and (0.10, 0.18) at −0.689.

This is the opposite of the design intent. The throttle was supposed to reduce buy fills during drawdown episodes. Instead, because the throttle shrinks each fill to 20% of normal size, the strategy makes *more* individual fill attempts to build the same position, each filling at a smaller quantum. The net result: more fills (more churn), not fewer.

### 5.3 Emergency DD Share

`delta_emergency_dd_share_pp` is negative (fewer emergency DD exits) in all 9 FULL cells: −4.0 to −10.1pp. This is the one metric that moves in the intended direction. However, the mechanism is not "the throttle prevents cascade buildup" — it is "the strategy holds such small positions that it rarely reaches the emergency DD threshold." This is the §4.3 failure mode from the spec (exit reason shift): emergency DD exits drop, but losses materialize through other channels.

### 5.4 MDD

Despite fewer emergency DD exits, MDD **worsens** in all 9 cells (delta: +0.94 to +3.97pp). This confirms the exit-reason-shift pathology: the strategy avoids catastrophic emergency exits but bleeds more deeply through sustained drawdowns on under-sized positions that can't recover through adds.

### 5.5 Return Bootstrap

`ci95_high` is negative in all 9 cells (−0.000018 to −0.000046). `p_gt_0` never exceeds 0.53%. This is not a borderline "CI crosses zero" situation — the evidence is unambiguous that the throttle degrades returns with high confidence.

`delta_cagr_harsh` ranges from −18.6pp to −27.4pp. The mildest cell (dd1=0.10, dd2=0.22) still loses 18.7 percentage points of annualized return. This is a catastrophic performance cost.

### 5.6 Throttle Activation Rate

| dd2 | dd1=0.06 | dd1=0.08 | dd1=0.10 |
|----:|---------:|---------:|---------:|
| 0.14 | 91.4% | 91.4% | 91.1% |
| 0.18 | 76.8% | 82.0% | 83.4% |
| 0.22 | 61.8% | 63.2% | 65.7% |

The spec (§6.5) required activation rate in [2%, 30%] for the default cell. **Every cell exceeds 30% by at least 2x.** The mildest cell (dd1=0.06, dd2=0.22) activates 61.8% of the time. The default cell (dd1=0.08, dd2=0.18) activates 82.0%.

The root cause: the strategy's equity curve spends most of its life below its all-time peak. A dd1 threshold of 6–10% captures normal post-peak retracement as "drawdown," making the throttle a near-permanent position cap rather than a conditional stress overlay. The `add_throttle_stats.json` confirms: `mean_dd_depth_when_blocked` ranges from 0.23 to 0.29 — the throttle fires at average DD depths of 23–29%, well beyond the dd2 full-throttle level. The p90 depth is 0.33–0.37, meaning most blocked adds occur during deep drawdowns where the strategy would need to rebuild aggressively to capture recoveries.

---

## 6. Summary Diagnosis

The P1 add-throttle overlay is **too aggressive across the entire tested parameter space**:

1. **Signal is too sensitive.** Equity-peak-based DD with dd1 in [0.06, 0.10] means the throttle activates during normal market behavior (any pullback > 6–10% from ATH), not just stress episodes. The strategy naturally operates in drawdown from peak most of the time.

2. **Throttle blocks the recovery mechanism.** This strategy earns returns by building positions during dips and profiting on recovery. The throttle directly attacks this mechanism, preventing position buildup precisely when the strategy's edge is greatest.

3. **More fills, not fewer.** The 20% multiplier allows small adds, but the strategy compensates by making more attempts. The result is more churn, not less — the opposite of the design goal.

4. **MDD worsens despite fewer emergency exits.** The classic exit-reason-shift failure (spec §4.3). The strategy can't build large enough positions to profit from recovery, so it bleeds slowly through trailing stops instead of occasionally hitting emergency DD.

---

## 7. Verdict

**NOT_ROBUST.** 0/9 FULL cells pass. No connected PASS region exists. Three of five required robustness checks fail, and the two that pass (R3, R5) do so for the wrong reasons (trade suppression masquerading as pathology improvement; fills increasing rather than decreasing).

**Recommendation: Abandon P1.**

---

## 8. Next-Best Hypothesis

**Recommended: Exposure cap by rolling DD.**

The fundamental failure of P1 is that the equity-peak-based DD signal is too persistently elevated. The strategy's equity curve naturally spends 60–90% of its life below its all-time high, so a peak-based trigger captures normal behavior rather than stress episodes.

A rolling-window DD approach (e.g., max drawdown over the trailing 30–60 days, not from ATH) would:

- **Self-reset.** After a drawdown resolves, the rolling window forgets the old peak within the lookback period, allowing normal trading to resume. The equity-peak signal never resets until a new ATH is reached.
- **Target the same problem.** Cascade buildup during acute drawdowns would still be throttled, but normal post-peak retracement would not trigger the overlay.
- **Produce activation rates in the design target (2–30%).** A 30-day rolling DD exceeding 10% is genuinely unusual and flags acute stress, unlike a peak-based DD exceeding 8% which is the norm.

This hypothesis should be specified, not yet designed. Do not proceed to implementation until the spec is reviewed.
