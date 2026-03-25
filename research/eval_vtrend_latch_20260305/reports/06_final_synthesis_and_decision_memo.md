# Report 06 -- Final Synthesis and Decision Memo

**Date:** 2026-03-05
**Step:** 6 (Final)
**Author:** Claude (audit-grade research)
**Inputs:** Reports 00-05, 50+ artifacts, 4x3 factorial, 101-point frontier, 5000-rep bootstrap
**No new experiments run.** This memo synthesizes existing evidence only.

---

## 1. Objective of This Memo

Answer the practical questions that motivated this research branch:

1. Was the original LATCH rejection fair?
2. Which strategy should be preferred, under which deployment objective?
3. Which conclusions are actually supported by evidence, and which are overstatements?

Produce a decision-oriented synthesis with explicit evidence grades on every major claim.

---

## 2. Inputs Used

| Step | Key Artifacts | Purpose |
|------|--------------|---------|
| 0 | `reports/00_setup_and_scope.md` | Research questions Q1-Q6 |
| 1 | `reports/01_strategy_and_engine_inventory.md`, `artifacts/confounder_registry.csv` | Code-truth inventory, 20 confounders |
| 2 | `reports/02_parity_and_signal_extraction.md`, `artifacts/signal_concordance_matrix.csv` | Engine/indicator/signal parity |
| 3 | `reports/03_factorial_sizing_and_scoring_bias.md`, `artifacts/step3_master_results.json` | 4x3 factorial, scoring bias audit |
| 4 | `reports/04_matched_risk_frontier.md`, `artifacts/pairwise_diagnostics.json` | Matched-risk frontier, deploy comparison |
| 5 | `reports/05_statistical_robustness_and_temporal_stability.md`, `artifacts/holm_pvalues.json` | Bootstrap, temporal stability, evidence grades |

---

## 3. Reports Read Confirmation

- `reports/00_setup_and_scope.md` -- read in full
- `reports/01_strategy_and_engine_inventory.md` -- read in full
- `reports/02_parity_and_signal_extraction.md` -- read in full
- `reports/03_factorial_sizing_and_scoring_bias.md` -- read in full
- `reports/04_matched_risk_frontier.md` -- read in full
- `reports/05_statistical_robustness_and_temporal_stability.md` -- read in full

---

## 4. Assumption Delta

### Claims from Steps 3-4 that REMAIN VALID

1. **Engine equivalence** -- v10 engine and standalone Latch engine produce numerically identical results when configured equivalently. Max divergence: 7.7e-14%. (Step 2, ROBUST)
2. **Indicator parity** -- All shared indicators (EMA, ATR, RV, rolling HH/LL) are bit-identical or within machine epsilon across implementations. (Step 2, ROBUST)
3. **Signal parity** -- Integrated and standalone LATCH produce identical signal sequences (0 mismatches out of 18,542 bars). SM standalone = SM integrated (0 mismatches). (Step 2, ROBUST)
4. **Scoring formula is CAGR-dominated** -- The `2.5 * CAGR` term accounts for 108-182% of score deltas between strategies with different exposure levels. (Step 3, ROBUST)
5. **35% of the original score gap is sizing/exposure, not signal quality** -- Decomposed via factorial: signal contributes 65%, sizing 35%. (Step 3, ROBUST)
6. **External cash-scaling preserves Sharpe exactly** -- Verified mathematically and empirically (0.0% Sharpe range across k). (Step 4, ROBUST)
7. **LATCH cannot reach E0-level MDD without leverage** -- LATCH ceiling: 11.24% MDD. E0 ceiling: 63.30%. Structural property. (Step 4, ROBUST)

### Claims from Steps 3-4 that were DOWNGRADED by Step 5

8. **"E0 has a genuine signal-quality edge"** (Step 3) -- Point estimate: +0.14 Sharpe at EntryVol_12. Bootstrap 95% CI: [-0.27, +0.54]. P(>0)=74%. Holm-adjusted p=1.000. **DOWNGRADED from "established" to TENTATIVE.**

9. **"At matched MDD, LATCH dominates E0"** (Step 4) -- Point estimates: +2.2 pp CAGR at 5% MDD, +4.6 pp at 10% MDD. Bootstrap CIs include zero at all block lengths. P(>0)=75-77%. **DOWNGRADED from "established" to TENTATIVE.**

10. **"Crossover at ~20% MDD"** (Step 4) -- Rolling-window analysis: crossover ranges from 3% to 26.5%. Not a stable threshold. **DOWNGRADED from "point estimate" to UNSTABLE.**

### Claims that are UNSUPPORTED

11. **LATCH complexity premium over SM** -- Sharpe diff: +0.003. CI: [-0.048, +0.055]. P(>0)=55%. Neither statistical nor practical materiality criteria met. (Step 5, UNSUPPORTED)

12. **Any statistically proven pairwise Sharpe superiority** -- All 4 primary hypotheses have Holm-adjusted p=1.000. No pairwise Sharpe or CAGR difference achieves 95% significance. (Step 5, UNSUPPORTED)

### What This Means

The research did not fail. It succeeded in:
- Eliminating false confounders (engine, indicators)
- Isolating genuine confounders (sizing, exposure, scoring bias)
- Establishing correct point estimates
- Quantifying the uncertainty around those estimates

The honest conclusion is: **8.5 years of BTC H4 data lacks the statistical power to distinguish Sharpe differences of 0.1-0.3 at 95% confidence.** The CI widths (0.5-0.8 Sharpe) reflect this fundamental limitation.

---

## 5. Original Research Questions and Final Answers

### Q1: Signal Quality Isolation

*Are the performance differences primarily an artifact of sizing?*

**Short answer:** Partially yes. 35% of the score gap comes from sizing/exposure confounders. The remaining 65% reflects a genuine signal difference, but that difference is not statistically significant.

**Evidence status:** ROBUST (that the confounder exists and its magnitude), TENTATIVE (that E0's residual signal edge is real).

**Steps:** 3 (factorial decomposition), 5 (bootstrap).

**Practical implication:** Never compare E0 and LATCH by raw native score alone. The scoring formula mechanically favors high-exposure strategies.

### Q2: Sizing Decomposition

*What fraction of performance difference is attributable to signal, sizing, exposure, and fee drag?*

**Short answer:**
- Signal quality (at Binary_100): 65% of score delta
- Sizing + exposure + vol_floor: 35% of score delta
- Fee drag: E0 pays ~7%/yr vs LATCH ~0.8%/yr -- material but embedded in equity curves

**Evidence status:** ROBUST.

**Steps:** 3.

**Practical implication:** Any comparison must either equalize sizing or use matched-risk frontier. Raw CAGR is meaningless across exposure levels.

### Q3: Backtest Engine Equivalence

*Are the two engines semantically identical?*

**Short answer:** Yes, when configured equivalently. Max divergence: 7.7e-14% (floating-point noise).

**Evidence status:** ROBUST.

**Steps:** 2.

**Practical implication:** Engine differences are NOT a confounder. Both engines can be used interchangeably.

### Q4: Fair Head-to-Head

*Under identical conditions, which signal is superior?*

**Short answer:**
- At identical sizing (EntryVol_12): E0 leads by +0.14 Sharpe. Tentative evidence -- CI includes zero.
- At matched MDD (10%): LATCH leads by +4.6 pp CAGR. Tentative evidence -- CI includes zero.
- At high risk budgets (>20% MDD): E0 is the only option; LATCH cannot participate.

**Evidence status:** TENTATIVE for both directions of advantage.

**Steps:** 3, 4, 5.

**Practical implication:** There is no universal winner. The preferred strategy depends on the deployment risk budget.

### Q5: Regime Overlap

*Do the strategies agree on regime state?*

**Short answer:** SM and LATCH agree on 99.8% of trading decisions at defaults, despite fundamentally different regime logic (instantaneous vs hysteretic). P is 95.7% concordant with SM/LATCH.

**Evidence status:** ROBUST.

**Steps:** 2.

**Practical implication:** SM and LATCH are nearly the same signal generator. The hysteresis in LATCH provides marginal smoothing but does not change trading outcomes meaningfully.

### Q6: Complexity-Adjusted Value

*Does LATCH's additional complexity produce measurably better outcomes?*

**Short answer:** No. LATCH (15 params) does not outperform SM (8 params) on any metric. Sharpe difference: +0.003. Bootstrap CI centered on zero. P(>0)=55%.

**Evidence status:** ROBUST (that the premium is absent).

**Steps:** 2, 3, 5.

**Practical implication:** SM should replace LATCH as the preferred low-exposure candidate. LATCH's hysteretic regime, vol_floor, and 3-state machine add complexity without measurable benefit.

---

## 6. What Was Proven False or Overstated During the Research

### Overstatement 1: "LATCH is clearly worse than E0"

**Why it looked plausible:** The original evaluation showed E0 score=90.7, LATCH score=44.2. Delta=-46.5. The decision rule rejected LATCH decisively.

**What later evidence revealed:** The scoring formula's `2.5 * CAGR` term accounts for 134-182% of the score delta. CAGR scales with exposure. E0 runs at 45% exposure, LATCH at 9%. The score comparison conflates risk appetite with signal quality.

**Correct wording:** "The scoring formula rejected LATCH because it penalizes low-exposure strategies. At matched risk budgets, LATCH produces tentatively higher CAGR than E0."

### Overstatement 2: "E0's signal is proven better"

**Why it looked plausible:** Step 3 showed E0 Sharpe=1.08 vs LATCH Sharpe=0.91 at Binary_100 sizing, and E0 Sharpe=1.33 vs LATCH Sharpe=1.20 at EntryVol_12. Both favor E0.

**What later evidence revealed:** The bootstrap 95% CI for the EntryVol_12 Sharpe difference is [-0.27, +0.54]. The CI comfortably includes zero. P(>0)=74% -- directionally consistent but not statistically significant.

**Correct wording:** "Best available point estimate suggests E0 has a +0.14 Sharpe signal-quality advantage at identical sizing, but this is not statistically distinguishable from zero with 8.5 years of data."

### Overstatement 3: "LATCH dominates E0 at low risk"

**Why it looked plausible:** Step 4 showed LATCH delivers 1.84x the CAGR of E0 at matched 10% MDD. Clean, large advantage.

**What later evidence revealed:** Bootstrap CI for the CAGR difference at 10% MDD: [-4.8, +9.7] pp. Direction is consistent (P(>0)=76%) but the CI is very wide and includes zero. Additionally, starting from 2020-01 reverses the conclusion.

**Correct wording:** "Tentative evidence indicates LATCH produces higher CAGR than E0 at low-risk budgets (P(>0) ~76%), but the advantage is not statistically significant and reverses in some time periods."

### Overstatement 4: "The crossover is ~20% MDD"

**Why it looked plausible:** Step 4 computed a single full-sample crossover at approximately 20% MDD.

**What later evidence revealed:** Rolling-window analysis shows the crossover varies from 3% to 26.5% across 24/36-month windows. The 20% figure is a sample-dependent artifact.

**Correct wording:** "The MDD budget at which E0 overtakes LATCH in absolute CAGR is highly variable across time periods. The full-sample estimate of ~20% should not be treated as a stable boundary."

### Overstatement 5: "LATCH's extra complexity is justified"

**Why it looked plausible:** LATCH has the highest native Sharpe (1.315) and best Calmar ratio (0.998) among all candidates. It appeared that the hysteretic regime and vol_floor contributed to this.

**What later evidence revealed:** SM (8 params) matches LATCH (15 params) within 0.003 Sharpe. The 99.8% signal concordance (Step 2) shows the hysteresis barely changes trading decisions. The bootstrap confirms the difference is indistinguishable from zero (P(>0)=55%).

**Correct wording:** "Unsupported by current evidence. SM achieves equivalent performance with roughly half the parameters."

---

## 7. Final Evidence Ladder

### ROBUST (95% CI excludes 0 or structural/definitional property)

| # | Claim | Why Robust | Supporting Step |
|---|-------|-----------|----------------|
| R1 | The scoring formula has a structural exposure bias | CAGR term = 108-182% of delta; mathematical property | Step 3 |
| R2 | 35% of the original score gap is sizing/exposure, not signal | Factorial decomposition, bit-identical signals | Step 3 |
| R3 | The two backtest engines are functionally identical | Max divergence 7.7e-14%, 237 trades | Step 2 |
| R4 | Indicators are bit-identical across implementations | 6/7 bit-identical, 1/7 within machine epsilon | Step 2 |
| R5 | SM and LATCH produce 99.8% concordant trading decisions | 32 of 18,542 bars differ | Step 2 |
| R6 | LATCH's complexity premium over SM is absent | Sharpe +0.003, CI [-0.05, +0.06], P(>0)=55% | Step 5 |
| R7 | E0 has higher native risk capacity (MDD 63% vs 11-15%) | Structural: binary 100% sizing, no ceiling | Step 4 |
| R8 | External cash-scaling preserves Sharpe exactly | Mathematical property + empirical verification | Step 4 |
| R9 | LATCH cannot reach E0-level risk without leverage | LATCH max MDD=11.24%, no leverage permitted | Step 4 |

### TENTATIVE (direction mostly consistent, CI includes 0 or temporally unstable)

| # | Claim | Why Tentative | Supporting Step |
|---|-------|-------------|----------------|
| T1 | E0 has a signal-quality edge (+0.14 Sharpe at equal sizing) | CI=[-0.27, +0.54], P(>0)=74% | Steps 3, 5 |
| T2 | LATCH produces higher CAGR at 5% MDD budget (+1.2 pp) | CI=[-2.3, +5.6], P(>0)=77% | Steps 4, 5 |
| T3 | LATCH produces higher CAGR at 10% MDD budget (+2.3 pp) | CI=[-4.8, +9.7], P(>0)=76% | Steps 4, 5 |
| T4 | LATCH tends to outperform at low risk in 64-67% of rolling windows | Not overwhelmingly dominant (would need >80%) | Step 5 |
| T5 | E0 tends to outperform in bull markets; LATCH in bear/sideways | Calendar analysis; 2020-01 start reverses conclusions | Step 5 |
| T6 | LATCH's vol-targeted sizing adds ~0.12 Sharpe to its signal | Observed in factorial but not bootstrapped separately | Step 3 |

### UNSUPPORTED (CI includes 0 broadly or evidence absent)

| # | Claim | Why Unsupported | Supporting Step |
|---|-------|---------------|----------------|
| U1 | Any statistically proven pairwise Sharpe superiority | All Holm-adjusted p=1.000 | Step 5 |
| U2 | LATCH complexity premium over SM | Sharpe +0.003, coin-flip probability | Step 5 |
| U3 | Crossover at ~20% MDD is a stable boundary | Varies from 3% to 26.5% across windows | Step 5 |
| U4 | P adds unique non-dominated value | Lowest Sharpe (1.24), fewer trades, no unique regime | Steps 3, 4 |

---

## 8. Fair-Comparison Framework Going Forward

### 8.1 Signal-Quality Comparison

When comparing signal generators (entry/exit timing) in isolation:

1. **Hold sizing fixed.** Use a common sizing model (e.g., EntryVol at target_vol=0.12, no rebalance).
2. **Hold costs fixed.** Same CostModel for all strategies (e.g., 25 bps one-way).
3. **Hold data and timing fixed.** Same bar range, same warmup period, same data feed.
4. **Compare equal-overlay runs.** The run where only signal differs and everything else is identical.
5. **Use exposure-aware diagnostics.** Report CAGR/exposure and Sharpe/exposure alongside absolute metrics.
6. **Do not rely on raw CAGR alone.** CAGR scales with in-position time, which is a signal property, not a quality property.

### 8.2 Deploy-Outcome Comparison

When comparing strategies for actual deployment:

1. **Use native systems** (each strategy with its own sizing).
2. **Use matched-risk or matched-budget frontier** (external cash-scaling, k in [0,1]).
3. **No leverage > 1.**
4. **Use terminal wealth as primary objective** at matched drawdown budget.
5. **Use Calmar, Ulcer index, and recovery time as tie-breakers.**
6. **Acknowledge structural constraints** (LATCH ceiling at 11.24% MDD).

### 8.3 Never Do This Again

| Anti-Pattern | Why It Fails | What To Do Instead |
|-------------|-------------|-------------------|
| Mixing signal and sizing changes in one score | Cannot distinguish what helped | Factorial decomposition (Step 3) |
| Ranking systems only by native CAGR when exposure differs 5x | CAGR scales with exposure | Use matched-risk frontier or Sharpe |
| Treating a high-weight CAGR term as "objective fairness" | It mechanically favors high-exposure systems | Audit the scoring formula's exposure sensitivity |
| Inferring complexity value without a premium test | Complexity may add zero value | Bootstrap difference test with materiality threshold |
| Stating point estimates as established facts without CIs | Overstates certainty | Always attach bootstrap CIs and evidence grades |

---

## 9. Strategy-by-Strategy Verdict

### 9.1 E0 / VTREND

**Strengths:**
- Highest risk capacity: can fill any drawdown budget up to 63.3% MDD without leverage
- Simplest: 3 tunable parameters, binary in/out sizing
- Tentatively best signal quality: +0.14 Sharpe at equal sizing (direction consistent, P(>0)=74%)
- Dominant in strong bull markets (2017, 2020, 2021, 2024)
- Well-understood, extensively validated (40 prior research studies, 715 tests)

**Weaknesses:**
- Lowest native Sharpe (1.08) due to binary 100% sizing creating high volatility
- Highest native MDD (63.3%) -- requires risk scaling for any practical deployment
- At low risk budgets (MDD < 12%), uses only 6-13% of capital (extremely capital-inefficient)
- Signal-quality advantage not proven at 95% significance

**Where it is attractive:**
- High-risk mandates (MDD budget > 15-20%) where it is the only option
- Portfolios that can tolerate large drawdowns in exchange for maximum expected CAGR
- When simplicity and interpretability are paramount

**Where it is misleading if evaluated naively:**
- Raw native score (90.7) vastly overstates its advantage because it conflates risk capacity with signal quality
- Looks dominant when compared by native CAGR (45% vs 11%), but this is 5x exposure, not 5x skill

**Evidence status of signal edge:** TENTATIVE (P(>0)=74%, CI includes 0).

**Verdict: KEEP**

### 9.2 LATCH

**Strengths:**
- Highest native Sharpe (1.315) and Calmar (0.998) among all candidates
- Lowest native MDD (11.24%) -- minimal drawdown risk at full deployment
- Best capital efficiency: nearly 1:1 CAGR-to-MDD ratio
- Vol-targeting with vol_floor provides implicit risk management

**Weaknesses:**
- Most complex: 15 tunable parameters (13 active at defaults)
- Complexity premium over SM is unsupported (Sharpe +0.003, P(>0)=55%)
- 99.8% signal concordance with SM means hysteretic regime adds negligible value
- Limited risk capacity: ceiling at 11.24% MDD without leverage
- Low-risk advantage over E0 is tentative (P(>0)=76%, CI includes zero)
- Advantage reverses when 2018 bear market is excluded

**Where it appears attractive:**
- At face value, LATCH has the best risk-adjusted metrics. Its Calmar ratio of 0.998 is excellent.
- Low-risk mandates (MDD budget 5-10%) show LATCH delivering tentatively more CAGR than E0.

**Why its headline low-risk edge is only tentative:**
- Bootstrap CI for CAGR difference at 10% MDD: [-4.8, +9.7] pp
- 2020-01 start date reverses the conclusion
- LATCH wins in only 57-67% of rolling windows, not a dominant majority

**Why it should not be preferred over SM on current evidence:**
- SM achieves Sharpe within 0.003 of LATCH with 8 params vs 15
- SM has slightly more risk capacity (MDD ceiling 15.0% vs 11.2%)
- SM has identical signal concordance (99.8%)
- The pre-analysis plan required both statistical support and practical materiality; neither criterion was met

**Verdict: DEPRECATE** (replace with SM in the candidate set)

### 9.3 SM

**Strengths:**
- Second-highest native Sharpe (1.312) -- within 0.003 of LATCH
- Moderate complexity: 8 tunable parameters
- More risk capacity than LATCH: MDD ceiling 15.0% vs 11.2% (+34%)
- 99.8% concordant with LATCH but simpler
- Good Calmar ratio (0.927)

**Weaknesses:**
- Still cannot fill high-risk budgets (capped at 15% MDD)
- Signal quality tentatively below E0 at equal sizing
- No hysteresis -- potentially more whipsaw-prone in theory (not observed in practice at defaults)

**Relationship to LATCH:**
- SM is the lower-complexity substitute for LATCH
- Same signal (99.8% concordant), same Sharpe (within 0.003), more capacity, fewer parameters
- LATCH's hysteretic regime, vol_floor, and 3-state machine add zero measurable benefit

**Verdict: KEEP** (replaces LATCH as the preferred low-exposure candidate)

### 9.4 P

**Strengths:**
- Uses price-direct regime (`close > ema_slow`), which is the simplest regime definition
- Moderate complexity: 6 tunable parameters
- More trades (91 vs 77) and more time in position (38.2% vs 34.7%) than SM/LATCH

**Weaknesses:**
- Lowest Sharpe among low-exposure candidates (1.243 vs SM 1.312)
- Lowest Calmar (0.848 vs SM 0.927)
- The tighter atr_mult (1.5 vs 3.0) creates more frequent exits but does not improve risk-adjusted returns
- No unique risk/return profile -- SM dominates P on both Sharpe and Calmar

**Whether it adds unique non-dominated value:**
No. SM has higher Sharpe, higher Calmar, and more risk capacity than P. P sits strictly below the SM/LATCH efficient frontier. P's price-direct regime generates more trades without converting them into better risk-adjusted returns.

**Verdict: DEPRIORITIZE** (keep in codebase for research but remove from active candidate set)

---

## 10. Deployment Decision by Objective / Risk Mandate

### Decision Matrix

| Mandate | Preferred | Backup | Why | Evidence | Caveat |
|---------|----------|--------|-----|:--------:|--------|
| **Low-risk** (MDD < 10%) | SM | E0 (scaled) | SM: higher tentative CAGR at matched MDD (Sharpe 1.31 vs 1.08) | TENTATIVE | Advantage is direction-consistent (P(>0) ~76%) but not proven. E0 scaled may match or beat SM in some market regimes. |
| **Medium-risk** (MDD 10-20%) | SM or E0 | -- | SM preferred up to its ceiling (15% MDD); above that, only E0 is available | TENTATIVE to ROBUST | The crossover where E0 overtakes SM varies from 3% to 27% -- no stable boundary. |
| **High-risk** (MDD > 20%) | E0 | None | E0 is the only candidate that can fill this budget without leverage | ROBUST | Structural property. No alternative exists in this candidate set. |
| **Research-control** | SM | E0 | SM: 8 params, vol-targeted, lower complexity than LATCH, well-characterized | ROBUST | SM's simplicity advantage over LATCH is robustly established. |

### Key observations

1. **There is no universal winner.** The preferred strategy depends on the deployment risk budget.
2. **E0 and SM serve complementary roles.** E0 fills high-risk budgets; SM fills low-risk budgets. They do not compete directly except in the 10-15% MDD overlap zone.
3. **LATCH adds nothing over SM** at current evidence levels. SM should replace it in all mandates.
4. **P is dominated by SM** on every major metric. It should be deprioritized.
5. **All low-risk recommendations are tentative.** The evidence favors SM/LATCH over scaled E0 at low risk, but not at 95% significance.

---

## 11. Recommended Default Candidate, Backup Candidate, and Deprecated Candidates

### By mandate:

- **Default for high-risk growth mandate:** E0 / VTREND
  - Only candidate that can fill MDD budgets > 15%. Simplest (3 params). Well-proven baseline.

- **Default for low-risk capital-efficient mandate:** SM
  - Highest Sharpe (1.31) with moderate complexity (8 params). More capacity than LATCH.

- **Default for low-complexity research control:** SM
  - 8 params vs LATCH's 15. Equivalent performance. Easier to audit and validate.

### Summary:

- **Default candidate:** E0 (high risk) / SM (low risk)
- **Backup candidate:** SM (for high risk, up to its 15% MDD ceiling) / E0 scaled (for low risk, as safety fallback)
- **Deprecated candidate(s):**
  - **LATCH** -- replaced by SM. No complexity premium. 99.8% same signal, double the parameters.
  - **P** -- deprioritized. Dominated by SM on Sharpe, Calmar, and capacity.

---

## 12. What Should Change in Future Evaluation Practice

### Operating procedure for strategy evaluations:

1. **Always separate signal from sizing.** Run a factorial (signal x sizing) before drawing any conclusion. Never mix signal and sizing changes in one comparison.

2. **Always audit exposure and fee drag.** If two strategies have different average exposure, raw CAGR is not comparable. Normalize or use matched-risk frontier.

3. **Always validate engine equivalence before comparing implementations.** Even when using the same engine, configuration differences (thresholds, cost models) can create spurious performance gaps.

4. **Always use matched-risk frontier for deployment decisions.** External cash-scaling with k in [0,1] provides the correct framework. Match on MDD budget, compare CAGR.

5. **Never accept a complexity increase without evidence of a robust premium.** Require both statistical significance (95% CI excludes zero) and practical materiality (Sharpe > 0.05 or CAGR > 1pp at matched risk).

6. **Always label claims by evidence strength.** Every major claim must carry ROBUST, TENTATIVE, or UNSUPPORTED. Point estimates without uncertainty bounds should be treated as preliminary.

### Scoring formula policy:

The current scoring formula (`2.5*CAGR - 0.6*MDD + 8*Sharpe + 5*PF + 5*Trade`) has a documented structural exposure bias. The `2.5*CAGR` term dominates all other terms when comparing strategies with different exposure levels.

**Policy recommendation:** This formula should be retired from decision authority for cross-exposure comparisons. It may remain as one diagnostic metric among several, but it should not be the sole or primary criterion for strategy selection when candidates have materially different exposure levels (e.g., >2x difference in average exposure).

No replacement formula is proposed in this memo. Any future formula should be designed with explicit exposure-normalization and validated against the factorial framework established in this research.

---

## 13. Remaining Uncertainties

| # | Uncertainty | Blocks Action? | Limits Confidence? |
|---|-----------|:--------------:|:------------------:|
| 1 | **Statistical power** -- 8.5 years insufficient to distinguish Sharpe diffs of 0.1-0.3 at 95% | No | Yes, fundamentally |
| 2 | **Regime dependence** -- E0 vs LATCH/SM ranking reverses between bull and bear markets | No | Yes |
| 3 | **Start-date sensitivity** -- 2020-01 start reverses low-risk conclusions | No | Yes |
| 4 | **Crossover instability** -- MDD budget where E0 overtakes LATCH/SM varies 3-27% | No | Yes |
| 5 | **No out-of-sample validation** -- all analysis is in-sample with fixed default parameters | No | Yes |
| 6 | **Sample composition** -- 2018 bear market disproportionately favors LATCH/SM advantage | No | Yes |
| 7 | **Hysteresis at other parameters** -- SM/LATCH 99.8% concordance is at defaults only | No | Slightly |

None of these uncertainties blocks immediate action. They all limit confidence in the low-risk advantage of SM/LATCH over E0, but the structural findings (scoring bias, engine parity, complexity premium absent) are unaffected.

---

## 14. Final Bottom-Line Recommendation

### What to keep:

- **E0** as the default high-risk candidate. It is the only strategy that can fill MDD budgets above 15%. It is the simplest (3 params) and most extensively tested.
- **SM** as the default low-risk candidate. It matches LATCH's Sharpe with half the parameters and has 34% more risk capacity.

### What to stop overstating:

- Stop claiming E0 is "clearly superior" to LATCH/SM. The scoring formula created that illusion by conflating exposure with quality.
- Stop claiming LATCH "dominates" E0 at low risk. The bootstrap says this is a direction, not a proven fact.
- Stop citing the ~20% MDD crossover as a stable boundary. It varies wildly.
- Stop treating any pairwise Sharpe difference as statistically significant. None are, at current data length.

### What to deploy under which mandate:

| Mandate | Deploy | Evidence Grade |
|---------|--------|:--------------:|
| MDD budget > 15% | E0 at appropriate k | ROBUST (only option) |
| MDD budget 5-15% | SM at appropriate k | TENTATIVE (favored, not proven) |
| Research / interpretability | SM | ROBUST (simplicity advantage) |

### What to remove from the candidate set:

- **LATCH**: Deprecated. Replaced by SM. Zero complexity premium established by bootstrap (Step 5, H4).
- **P**: Deprioritized. Dominated by SM on all major metrics.

### Highest-ROI next step (optional):

If additional research is warranted, the single highest-ROI investigation would be an **out-of-sample walk-forward test** on post-February 2026 data as it becomes available. This would validate whether the in-sample point estimates (particularly SM's Sharpe advantage at low-risk budgets) hold on truly unseen data. No parameter re-optimization should be performed -- only forward application of current defaults.

---

*End of Report 06. Research branch synthesis-complete. No new experiments conducted. All claims carry explicit evidence grades.*
