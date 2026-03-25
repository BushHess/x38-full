# Step 4 Report — Final Synthesis and Decision Memo

> **SUPERSEDED (2026-03-09):** Primary/fallback recommendations below are outdated.
> After framework reform (Wilcoxon WFO, PSR gate, bootstrap CI):
> - **E5+EMA1D21 = PRIMARY** (PROMOTE, PSR=0.9993)
> - **X0 / E0+EMA1D21 = HOLD** (PSR=0.8908 < 0.95)
> See `CHANGELOG.md` (2026-03-09). Methodology below preserved as historical record.

**Date**: 2026-03-06
**Scope**: Integrate old portfolio branch with Steps 1-3 trade-structure / fragility branch into final research conclusion
**Status**: SUPERSEDED — see header note

---

## 1. Executive Summary

**The final research conclusion is ready now.** Step 5 is not needed to determine the candidate ranking or produce deployment recommendations. It is recommended only for live sign-off hardening.

**The old "no universal winner" conclusion still holds.** No single candidate dominates all mandates and latency tiers. The correct deployment framework is a mandate x latency matrix, not a single "best" pick.

**Primary recommendations:**

- **LT1 / M1 (return-seeking, <4h auto)**: **E5_plus_EMA1D21** — highest Sharpe (1.430), CAGR (59.9%). Requires strict automation.
- **LT1 / M2 (balanced, <4h auto)**: **E0_plus_EMA1D21** — only strategy to pass ALL Tier 1 gates. WFO 6/8. Most defensible.
- **LT2 (degraded, 4-16h)**: **E0** — least delay-fragile binary (D4: -29.5% loss).
- **LT3 / M3 (manual, >16h)**: **SM** — only viable candidate (D4: -4.0% loss).

**Dropped as redundant**: LATCH (near-duplicate of SM, higher complexity, zero measurable benefit).

**Step 5**: Not needed for research conclusion. Recommended for live sign-off. Could not realistically change candidate ranking.

---

## 2. Evidence Base and Precedence Rules

### 2.1 Sources Integrated

| Layer | Source | Authority |
|-------|--------|-----------|
| A — Portfolio | Old parity branch (Studies #41-43) | Canonical for CAGR/Sharpe/MDD/WFO/bootstrap |
| B — Trade structure | Steps 1-2 | Canonical for home-run dependence, style labels, behavioral fragility |
| C — Operational fragility | Steps 2-3 | Step 3 is canonical for replay-dependent fragility (supersedes Step 2 proxy) |
| D — Complexity/redundancy | Steps 0-3 combined | Synthesized across all evidence |

### 2.2 Precedence

- Step 0 remains source of truth for candidate mapping, period, fee model
- If Steps 2 and 3 both address the same question (e.g., behavioral fragility), Step 3 replay results take precedence over Step 2 post-hoc proxy
- Old-branch verdicts (PROMOTE/HOLD/REJECT) are respected as valid under CAGR-weighted scoring but are superseded by the mandate x latency framework for deployment decisions

### 2.3 Evidence Conflicts

**None found.** The old-branch REJECT for SM/LATCH is not a conflict with Step 3's finding that they are operationally robust — the old branch was testing CAGR-weighted composite performance, not operational fragility. Different questions, consistent answers.

---

## 3. Old Portfolio-Branch Recap (Layer A)

### 3.1 Harsh-Scenario Portfolio Metrics

| Candidate | Sharpe | CAGR% | MDD% | Calmar | WFO | Trades | Turnover/yr | Old Verdict |
|-----------|--------|-------|------|--------|-----|--------|-------------|-------------|
| E0 | 1.265 | 52.04 | 41.61 | 1.251 | 0/8* | 192 | 52.3 | HOLD |
| E5 | 1.357 | 56.62 | 40.37 | 1.403 | 4/8 | 207 | 56.2 | HOLD |
| SM | 1.444 | 16.00 | 15.09 | 1.060 | 5/8 | 65 | 7.2 | REJECT |
| LATCH | 1.443 | 12.82 | 11.24 | 1.141 | 5/8 | 65 | 5.6 | REJECT |
| E0_plus_EMA1D21 | 1.325 | 54.70 | 42.05 | 1.301 | 6/8 | 172 | 47.1 | PROMOTE |
| E5_plus_EMA1D21 | 1.430 | 59.85 | 41.64 | 1.437 | 5/8 | 186 | 50.5 | PROMOTE |

*E0 WFO 0/8 is a self-vs-self artifact (baseline = candidate), not a strategy failure.

### 3.2 Bootstrap Robustness (500 paths, SP=120, harsh)

| Candidate | Sharpe_med | MDD_med% | P(CAGR>0) | MDD wins vs E0 |
|-----------|-----------|---------|-----------|----------------|
| E0 | 0.697 | 58.49 | 88.2% | — |
| E5 | 0.689 | 57.34 | 88.2% | 16/16 |
| SM | 0.918 | 16.50 | 97.8% | 16/16 |
| LATCH | 0.936 | 13.41 | 97.8% | 15/16 |
| E0_plus_EMA1D21 | 0.562 | 52.17 | 84.6% | 16/16 |
| E5_plus_EMA1D21 | NA | NA | NA | NA (not in parity T4) |

SM/LATCH have the strongest bootstrap robustness: highest median Sharpe (0.918/0.936), lowest MDD (16.5%/13.4%), highest P(CAGR>0) (97.8%). E0_plus has the weakest bootstrap Sharpe (0.562) among binary candidates despite having the strongest WFO (6/8).

### 3.3 Cost Sensitivity

E5 > E0 at ALL cost levels 0-75 bps. E0_plus > E0 at ALL cost levels 0-100 bps. SM/LATCH dominate above 50-75 bps due to 7x lower turnover.

---

## 4. Trade-Structure / Home-Run Recap (Layer B, Steps 1-2)

### 4.1 Style Classifications

| Candidate | Native Style | Unit Style | Native Shape | Unit Shape | Overall |
|-----------|-------------|-----------|-------------|-----------|---------|
| E0 | home-run | home-run | cliff-like | cliff-like | home-run |
| E5 | hybrid | home-run | cliff-like | cliff-like | hybrid |
| SM | hybrid | home-run | **smooth** | cliff-like | hybrid |
| LATCH | hybrid | home-run | **smooth** | cliff-like | hybrid |
| E0_plus_EMA1D21 | home-run | home-run | cliff-like | cliff-like | home-run |
| E5_plus_EMA1D21 | hybrid | home-run | cliff-like | cliff-like | hybrid |

All 6 are home-run dependent in unit-size view. SM/LATCH alone show smooth native dependence due to vol-target sizing.

### 4.2 Key Concentration Metrics

| Candidate | Top-5 PnL% | Native ZC | Unit ZC | Eff N | Worst Skip dS |
|-----------|-----------|-----------|---------|-------|---------------|
| E0 | 90.2% | 3.1% | 5.7% | 57.4 | -0.263 |
| E5 | 79.0% | 3.9% | 6.3% | 64.7 | -0.213 |
| SM | 81.9% | 10.8% | 9.2% | 24.8 | -0.175 |
| LATCH | 81.5% | 10.8% | 9.2% | 24.4 | -0.159 |
| E0_plus | 83.4% | 4.1% | 7.0% | 51.9 | -0.195 |
| E5_plus | 73.8% | 4.3% | 7.5% | 59.1 | -0.252 |

E5_plus is the least concentrated (73.8% top-5). SM/LATCH are the most resilient natively (ZC at 10.8%). All candidates are behaviorally fragile (skip-after-2 harmful: dS -0.159 to -0.263).

### 4.3 SM/LATCH Near-Duplicate Finding

Step 2 found SM and LATCH near-duplicates across all 20 metrics tested. Same trade count, same hold time, same zero-cross, same cliff scores, same style labels. The hysteresis mechanism in LATCH produces no measurable structural differentiation.

---

## 5. Replay Fragility Recap (Layer C, Step 3)

### 5.1 Three Disruption Classes

| Dimension | Binary (E0-class) | Vol-Target (SM/LATCH) |
|-----------|-------------------|----------------------|
| Random miss K=1 CV | 0.32-0.38% | 1.48-1.51% |
| Outage 168h worst % loss | 5.6-5.7% | 9.1-9.4% |
| **Delay D4 % Sharpe loss** | **29.5-40.7%** | **4.0%** |

### 5.2 Binary Delay Sensitivity (Sorted by D4 Delta)

| Candidate | D1 | D2 | D3 | D4 | Trades Lost at D4 |
|-----------|-----|-----|-----|-----|-------------------|
| E0 | -0.031 | -0.200 | -0.251 | **-0.336** | 28 |
| E0_plus | -0.047 | -0.202 | -0.290 | -0.372 | 24 |
| E5 | -0.052 | -0.297 | -0.364 | -0.453 | 33 |
| E5_plus | -0.081 | -0.309 | -0.419 | **-0.517** | 28 |

E0 is the least delay-fragile binary. E5_plus is the most. The ordering is perfectly inversely correlated with baseline Sharpe — a fundamental performance-fragility tradeoff.

### 5.3 Dominant Finding

Entry delay is the dominant operational fragility axis. Random miss and outage are bounded and moderate. Binary strategies require sub-4h automated execution for full performance. SM/LATCH are viable under any operational condition.

---

## 6. Candidate-by-Candidate Synthesis

### E0 — CONDITIONAL_DEPLOY

**Strengths**: Simplest implementation (3 params). Least delay-fragile binary (D4: -29.5%). Proven track record as baseline.
**Weaknesses**: Most concentrated (top-5 = 90.2%). Lowest binary Sharpe (1.265). WFO 0/8 (self-baseline artifact).
**Role**: LT2 fallback binary. Deploy when automated execution cannot be guaranteed at LT1 but manual execution is not acceptable.
**Evidence**: [C08, C15] in evidence registry.

### E5 — CONDITIONAL_DEPLOY

**Strengths**: Beats E0 at ALL cost levels 0-75 bps. Better win rate (43.5% vs 41.7%). Robust ATR reduces sensitivity to outlier bars.
**Weaknesses**: WFO 4/8 (marginal). Higher turnover (56.2/yr). More delay-fragile than E0 (D4: -36.9%).
**Role**: LT2 alternative when robust ATR is preferred. Secondary to E5_plus under LT1.
**Evidence**: [C15] in evidence registry.

### SM — PRIMARY_DEPLOY

**Strengths**: Operationally robust at all latency tiers (D4: -4.0%). Highest bootstrap P(CAGR>0) = 97.8%. MDD 15.1% (vs 40-42% binary). Turnover 7.2/yr. Only manual-viable candidate.
**Weaknesses**: CAGR 16.0% (3.3x lower than E0). Old-branch REJECT under CAGR-weighted scoring.
**Role**: Primary deploy under M3 (resilience-first) at any latency. Only viable candidate under LT3.
**Evidence**: [C09, C10] in evidence registry.

### LATCH — DROP_REDUNDANT

**Strengths**: Lowest turnover (5.6/yr). Lowest MDD (11.2%). Marginally higher Sharpe than SM (+0.001).
**Weaknesses**: Near-duplicate of SM across all dimensions (Steps 2, 3). Higher complexity (~20 params vs 15). Zero measurable complexity premium.
**Role**: None. Dropped as redundant.
**Evidence**: [C02, C03] in evidence registry.

### E0_plus_EMA1D21 — PRIMARY_DEPLOY

**Strengths**: Only strategy to pass ALL Tier 1 validation gates. WFO 6/8 (best). Sharpe 1.325. Beats E0 at all cost levels.
**Weaknesses**: Bootstrap Sharpe_med = 0.562 (lowest binary). MDD 42.1% (highest). More delay-fragile than E0 (D4: -31.7%).
**Role**: Primary binary deploy under M2 (balanced) at LT1. Most defensible deployment story.
**Evidence**: [C04, C07] in evidence registry.

### E5_plus_EMA1D21 — PRIMARY_DEPLOY

**Strengths**: Highest raw Sharpe (1.430). Highest CAGR (59.9%). Lowest PnL concentration (top-5 = 73.8%). Lowest giveback (median 1.05x).
**Weaknesses**: Worst delay degradation (D4: -40.7%). WFO 5/8 (weaker than E0_plus). Performance crossover with E5 at D3+.
**Role**: Primary binary deploy under M1 (return-seeking) at LT1. Strictly LT1-only.
**Evidence**: [C05, C06] in evidence registry.

---

## 7. Redundancy / Complexity-Premium Decisions

### 7.1 SM vs LATCH — **DROP LATCH**

- **Trade structure**: Near-duplicate across all 20 metrics (Step 2)
- **Replay fragility**: Identical across all 3 disruption classes (Step 3)
- **Complexity premium**: NONE. Hysteresis adds ~5 parameters with zero benefit
- **Decision**: Keep SM as sole vol-target representative. Drop LATCH.

### 7.2 E0 vs E0_plus_EMA1D21 — **KEEP BOTH (different latency roles)**

- **EMA overlay adds**: +0.060 Sharpe, +2.66pp CAGR, +0.7pp win rate, passes ALL gates
- **EMA overlay costs**: +0.036 worse D4 delta Sharpe, higher MDD, lower bootstrap Sharpe
- **Complexity premium**: YES — validation gate passage and WFO 6/8 are decision-relevant
- **Decision**: E0_plus is primary under LT1. E0 is fallback under LT2. Both serve distinct roles.

### 7.3 E5 vs E5_plus_EMA1D21 — **KEEP BOTH (different latency roles)**

- **EMA overlay adds**: +0.073 Sharpe, +3.23pp CAGR, lowest concentration
- **EMA overlay costs**: +0.064 worse D4 delta, performance crossover at D3-D4
- **Complexity premium**: YES — highest absolute performance under LT1
- **Decision**: E5_plus is primary under M1/LT1. E5 is fallback under LT2. At D3+, E5 overtakes.

### 7.4 Overall Redundancy Clusters

| Cluster | Members | Representative | Dropped |
|---------|---------|---------------|---------|
| vol_target | SM, LATCH | SM | LATCH |
| binary_base | E0 | E0 | — |
| binary_enhanced | E5 | E5 | — |
| binary_ema_balanced | E0_plus_EMA1D21 | E0_plus_EMA1D21 | — |
| binary_ema_aggressive | E5_plus_EMA1D21 | E5_plus_EMA1D21 | — |

---

## 8. Mandate x Latency Recommendation Matrix

| | LT1 (<4h auto) | LT2 (4-16h degraded) | LT3 (>16h manual) |
|---|---|---|---|
| **M1 (return-seeking)** | **E5_plus_EMA1D21** (alt: E5) | **E0** (alt: E0_plus) | **SM** (alt: LATCH) |
| **M2 (balanced)** | **E0_plus_EMA1D21** (alt: E5) | **E0** (alt: E0_plus) | **SM** (alt: LATCH) |
| **M3 (resilience-first)** | **SM** (alt: LATCH) | **SM** (alt: LATCH) | **SM** (alt: LATCH) |

**Excluded from all cells**: LATCH (redundant with SM, listed as alt only for completeness).
**Binary candidates excluded from LT3**: All lose >29% Sharpe at D4 delay.
**E5_plus excluded from LT2+**: Performance crossover with E5 at D3; loses 40.7% at D4.

---

## 9. Final Candidate Set and Exclusions

### 9.1 Minimal Non-Redundant Set (5 candidates)

| Candidate | Disposition | Primary Role |
|-----------|------------|-------------|
| E5_plus_EMA1D21 | PRIMARY_DEPLOY | M1/LT1 — max return |
| E0_plus_EMA1D21 | PRIMARY_DEPLOY | M2/LT1 — balanced default |
| SM | PRIMARY_DEPLOY | M3/any LT — resilience |
| E0 | CONDITIONAL_DEPLOY | LT2 fallback binary |
| E5 | CONDITIONAL_DEPLOY | LT2 alt / LT1 secondary |

### 9.2 Dropped

| Candidate | Reason |
|-----------|--------|
| LATCH | Redundant with SM — identical structure and fragility, higher complexity |

### 9.3 Not Recommended

| Candidate | Regime | Reason |
|-----------|--------|--------|
| E0, E5, E0_plus, E5_plus | LT3 | All binary candidates lose >29% Sharpe at 16h delay |
| E5_plus_EMA1D21 | LT2 | Performance crossover with E5 at D3; 40.7% loss at D4 |

---

## 10. Answers to the 12 Mandatory Questions

### Q9.1 After integrating Step 1-3, is the old conclusion "no universal winner" still true?

**YES.** Three independent evidence layers confirm it. Binary strategies dominate on raw performance but are operationally fragile. Vol-target strategies are operationally robust but low-CAGR. No single candidate serves all mandates and latency tiers.

### Q9.2 Which candidate is the best default choice under LT1 for a return-seeking mandate?

**E5_plus_EMA1D21.** Sharpe 1.430, CAGR 59.9%, lowest PnL concentration. Requires strict LT1.

### Q9.3 Which candidate is the best default choice under LT2?

**E0.** Least delay-fragile binary (D4: -29.5% vs -31.7% to -40.7% for peers). Simplest implementation.

### Q9.4 Which candidate, if any, is viable under LT3?

**SM only.** 4% Sharpe loss at D4 vs 29-41% for binary. CAGR 16% is the accepted price.

### Q9.5 Is any binary candidate acceptable for manual or semi-manual deployment?

**NO.** All binary candidates lose >29% of Sharpe at 4-bar (16h) delay. Manual execution would destroy the strategy's edge.

### Q9.6 Is there any evidence-based reason to keep LATCH if SM exists?

**NO.** Steps 2 and 3 confirm SM and LATCH are near-duplicates on every dimension tested. LATCH's hysteresis mechanism adds ~5 parameters with zero measurable structural or operational benefit. SM is the preferred representative.

### Q9.7 Do EMA1D overlays deserve their own deployment slots?

**YES, conditionally.** Under LT1, EMA overlays add +0.060 to +0.073 Sharpe and improve selectivity. Under LT2+, the added delay fragility makes the base variants (E0, E5) preferable. EMA overlays earn conditional deployment slots, not unconditional preference. The condition is: LT1 latency must be guaranteed.

### Q9.8 What is the minimal non-redundant candidate set?

**5 candidates**: E0, E5, SM, E0_plus_EMA1D21, E5_plus_EMA1D21. LATCH is the only candidate dropped.

### Q9.9 Candidate dispositions?

| Candidate | Disposition |
|-----------|------------|
| E0 | CONDITIONAL_DEPLOY |
| E5 | CONDITIONAL_DEPLOY |
| SM | PRIMARY_DEPLOY |
| LATCH | DROP_REDUNDANT |
| E0_plus_EMA1D21 | PRIMARY_DEPLOY |
| E5_plus_EMA1D21 | PRIMARY_DEPLOY |

### Q9.10 Does Step 3 change the earlier view that missing isolated trades is not the main problem, but entry latency is?

**YES — confirms and strengthens it.** Step 2 showed home-run dependence (missing the best trades is catastrophic). Step 3 shows that random misses are nearly harmless (CV < 1.5%) while entry delay is devastating (29-41% Sharpe loss at D4). The dominant operational risk is not "will I miss the signal?" but "how quickly will I execute it?"

### Q9.11 Is Step 5 required to reach the final research conclusion?

**NO.** The candidate ranking is stable across all 4 evidence layers. Step 5 would refine confidence bounds but could not flip any recommendation.

### Q9.12 Could Step 5 realistically change the candidate ranking?

**NO.** The performance-fragility tradeoff is structural (not an artifact). The SM vs LATCH redundancy is definitive. The binary vs vol-target class boundary is driven by a 7x delay sensitivity gap. Only the E0 vs E0_plus LT2 recommendation has non-zero (but low) probability of changing under exit-delay testing.

---

## 11. Step 5 Necessity Verdict

**Step 5 is NOT NEEDED for the research conclusion.**

It is RECOMMENDED only for live sign-off hardening. Specifically:
1. Validate replay harness against BacktestEngine under disruption scenarios
2. Test combined disruptions (simultaneous miss + delay)
3. Test exit delay (which Step 3 did not cover)
4. Test stochastic delay model for more realistic degraded-ops simulation

None of these could change the candidate ranking. They would only refine operational confidence.

---

## 12. Limitations

1. **Ulcer index not available.** The old-branch `full_backtest_detail.json` does not include Ulcer ratio. This metric is NA for all candidates.

2. **E5_plus bootstrap not in old-branch T4 table.** E5_plus_EMA1D21 was evaluated in Study #43 (separate from the 6-way parity), so its bootstrap Sharpe_med is not directly comparable to the parity T4 table. The jackknife -33.8% drop (more robust than E0_plus -40.9%) partially compensates.

3. **Matched-risk frontier not formally computed.** The old branch discusses SM/LATCH dominance "above 75 bps RT" from the cost-sweep, which serves as a proxy for matched-risk frontier behavior. No formal efficient-frontier analysis exists.

4. **Exit delay not tested.** Step 3 tested entry delay only. Exit delays (late stop-loss execution) could differentially affect candidates and may be more damaging. This is the largest remaining gap.

5. **Old-branch EMA21 (H4) vs EMA21-D1.** The old branch tested both. Step 4 uses only EMA21-D1 (E0_plus_EMA1D21, E5_plus_EMA1D21). The H4 variant was REJECT in the old branch and is not part of the 6-candidate set.

---

## 13. Artifact Index

### 13.1 Report

| File | Description |
|------|-------------|
| `reports/step4_report.md` | This report (13 sections) |

### 13.2 Machine-Readable Artifacts (`artifacts/step4/`)

| File | Description |
|------|-------------|
| `step4_input_manifest.csv` | 25 input artifacts with roles and sources |
| `final_evidence_registry.csv` | 17 conclusions with traceable evidence paths |
| `portfolio_branch_snapshot.csv` | 6 candidates, old-branch metrics |
| `candidate_synthesis_matrix.csv` | 6 candidates, 15 synthesis dimensions |
| `candidate_disposition_matrix.csv` | 6 candidates, dispositions + regime statuses |
| `mandate_latency_recommendation_matrix.csv` | 9 cells (3 mandates x 3 latency tiers) |
| `pairwise_redundancy_decisions.csv` | 3 mandatory pairs with verdicts |
| `final_candidate_set.json` | Machine-readable final set + operational conditions |
| `step4_summary.json` | Machine-readable summary of all Step 4 conclusions |

### 13.3 Human-Readable Companion Documents (`artifacts/step4/`)

| File | Description |
|------|-------------|
| `final_decision_memo.md` | Blunt deploy/no-deploy memo for PM/research lead |
| `step5_need_assessment.md` | Detailed Step 5 necessity analysis |
| `cross_branch_synthesis_notes.md` | How old and new branches integrate |

### 13.4 Figures (`artifacts/step4/`)

| File | Description |
|------|-------------|
| `recommendation_map.png` | Mandate x latency color-coded recommendation matrix |
| `latency_regime_recommendation.png` | Sharpe vs delay with LT boundaries overlaid |

### 13.5 Code (`code/step4/`)

| File | Description |
|------|-------------|
| `run_step4_final_synthesis.py` | Figure generation script (~150 lines) |

---

**STEP 4 VERDICT: RESEARCH CONCLUSION READY. NO UNIVERSAL WINNER. MANDATE x LATENCY FRAMEWORK REQUIRED.**

*End of Step 4 Report*
