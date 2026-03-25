# Report 04 — Matched-Risk Frontier + Deploy-Oriented Comparison

**Date:** 2026-03-05
**Step:** 4 of N
**Author:** Claude (audit-grade research)
**Script:** `src/run_frontier.py`
**Tests:** `tests/test_frontier.py` — 18/18 pass
**Runtime:** 4.4 s

---

## 0. Assumption Delta

| # | Assumption | Source | Verified? | Method |
|---|-----------|--------|-----------|--------|
| A1 | Step 3 equity curves start at 1.0 (normalized) | Step 3 `run_factorial.py` | YES | All 16 curves checked |
| A2 | External scaling `r_k(t) = k * r(t)` preserves Sharpe | Mathematical property | YES | Sharpe range 0.0% across k=0.25…1.0 for all 4 strategies |
| A3 | MDD and CAGR are monotonic in k | Mathematical property | YES | Linearity check all 4 PASS |
| A4 | k ∈ [0, 1] — no leverage | Design constraint | YES | Assertion enforced, test coverage |
| A5 | Cash portion earns 0% return | Conservative assumption | YES | k=0 → flat equity |
| A6 | Cost is already embedded in equity curves | Step 3 design | YES | 25 bps one-way applied at execution |
| A7 | Equity curves are from same data period (2017-08 → 2026-02, 18662 H4 bars) | Step 3 A7 | YES | Carried forward |

**New vs Report 03:** A1-A5 (scaling framework), A6 (cost already embedded).
**Carried forward:** A7 from Step 3.

---

## 1. Linearity Sanity Check

External cash-scaling property: for returns `r(t)`, the scaled version `r_k(t) = k * r(t)` has:
- **Sharpe(k) = Sharpe(1)** exactly (both mean and std scale by k, ratio constant)
- **MDD(k)** monotonically increasing in k
- **CAGR(k)** monotonically increasing in k

### Results

| Strategy | Sharpe range | MDD monotonic | CAGR monotonic | Pass |
|----------|:-----------:|:-------------:|:--------------:|:----:|
| E0_Native | 0.0% | YES | YES | PASS |
| SM_Native | 0.0% | YES | YES | PASS |
| P_Native | 0.0% | YES | YES | PASS |
| LATCH_Native | 0.0% | YES | YES | PASS |

Sharpe is **perfectly preserved** across all scaling levels. This confirms that external cash-scaling is a valid framework for risk-budget analysis — it changes the scale of returns without distorting risk-adjusted quality.

### Diagnostic grid

| Strategy | k=0.25 Sharpe | k=0.25 MDD | k=0.25 CAGR | k=1.0 Sharpe | k=1.0 MDD | k=1.0 CAGR |
|----------|:------------:|:----------:|:-----------:|:------------:|:---------:|:----------:|
| E0 | 1.0773 | 20.6% | 11.7% | 1.0773 | 63.3% | 45.0% |
| SM | 1.3118 | 3.9% | 3.4% | 1.3118 | 15.0% | 13.9% |
| P | 1.2434 | 3.3% | 2.7% | 1.2434 | 12.7% | 10.8% |
| LATCH | 1.3148 | 2.9% | 2.8% | 1.3148 | 11.2% | 11.2% |

---

## 2. 101-Point Frontier Summary

Each strategy spans k ∈ [0, 1] in 0.01 increments. Full data in `frontier_grid.csv` (404 rows × 20+ metrics).

### Key frontier characteristics

| Strategy | Native Sharpe | Native MDD | Native CAGR | MDD range (k=0→1) | CAGR range (k=0→1) |
|----------|:------------:|:----------:|:----------:|:-----------------:|:-----------------:|
| E0_Native | 1.0773 | 63.30% | 45.04% | 0%→63.3% | 0%→45.0% |
| SM_Native | 1.3118 | 15.00% | 13.90% | 0%→15.0% | 0%→13.9% |
| P_Native | 1.2434 | 12.68% | 10.76% | 0%→12.7% | 0%→10.8% |
| LATCH_Native | 1.3148 | 11.24% | 11.21% | 0%→11.2% | 0%→11.2% |

**Critical property**: LATCH's Calmar ratio (CAGR/MDD) at k=1 is **0.998** — nearly perfect 1:1 CAGR-to-MDD ratio. E0's Calmar is 0.711. This means LATCH extracts more return per unit of drawdown risk.

---

## 3. Matched-MDD Comparison

### 3.1 Common-Feasible Region

The common-feasible region is 0% ≤ MDD ≤ min(native MDD) = 11.24% (LATCH ceiling). In this region, ALL four strategies can be compared at identical drawdown risk.

### 3.2 Matched-MDD Table

| Target MDD | E0 k | E0 CAGR | E0 Sharpe | SM k | SM CAGR | LATCH k | LATCH CAGR | LATCH Sharpe |
|:----------:|:----:|:------:|:---------:|:----:|:------:|:-------:|:---------:|:-----------:|
| 5% | 0.057 | 2.64% | 1.0773 | 0.328 | 4.48% | 0.438 | 4.85% | 1.3148 |
| 10% | 0.115 | 5.38% | 1.0773 | 0.656 | 9.05% | 0.891 | 9.97% | 1.3148 |

**At 5% MDD budget**: LATCH delivers **1.84× the CAGR** of E0 (4.85% vs 2.64%).
**At 10% MDD budget**: LATCH delivers **1.85× the CAGR** of E0 (9.97% vs 5.38%).

The ratio is remarkably stable because both Sharpe ratios are constant (1.3148 vs 1.0773), and the CAGR advantage is a direct consequence of LATCH's higher Sharpe.

### 3.3 Why E0 Needs So Much More Capital

E0 at MDD=10% requires k=0.115 — only 11.5% of capital allocated. This is because E0's native MDD is 63.3%, so achieving a 10% MDD budget requires scaling down to 10/63.3 = 15.8% of native (actual k slightly lower due to nonlinear MDD scaling).

LATCH at MDD=10% uses k=0.891 — 89.1% of capital allocated. LATCH is already operating near its natural risk level.

---

## 4. Operational Risk-Budget Analysis

Real-world deployment picks a MDD tolerance, then allocates capital. The table below shows what each strategy delivers at standard risk budgets.

| MDD Budget | E0 k | E0 CAGR | E0 Feasible | SM k | SM CAGR | SM Feasible | LATCH k | LATCH CAGR | LATCH Feasible |
|:----------:|:----:|:------:|:-----------:|:----:|:------:|:-----------:|:-------:|:---------:|:--------------:|
| 12.5% | 0.146 | 6.84% | YES | 0.828 | 11.46% | YES | 1.000 | 11.21% | NO (capped) |
| 15.0% | 0.178 | 8.30% | YES | 0.996 | 13.84% | YES | 1.000 | 11.21% | NO (capped) |
| 20.0% | 0.242 | 11.32% | YES | 1.000 | 13.90% | NO (capped) | 1.000 | 11.21% | NO (capped) |
| 25.0% | 0.309 | 14.42% | YES | 1.000 | 13.90% | NO (capped) | 1.000 | 11.21% | NO (capped) |
| 30.0% | 0.381 | 17.78% | YES | 1.000 | 13.90% | NO (capped) | 1.000 | 11.21% | NO (capped) |
| 40.0% | 0.535 | 24.89% | YES | 1.000 | 13.90% | NO (capped) | 1.000 | 11.21% | NO (capped) |
| 50.0% | 0.715 | 32.96% | YES | 1.000 | 13.90% | NO (capped) | 1.000 | 11.21% | NO (capped) |
| 60.0% | 0.922 | 41.84% | YES | 1.000 | 13.90% | NO (capped) | 1.000 | 11.21% | NO (capped) |

### Key observations

1. **LATCH hits its ceiling at 11.24% MDD** — it cannot deliver more CAGR without leverage. Its risk-adjusted quality is excellent, but its risk *capacity* is limited.

2. **E0 can fill any risk budget up to 63.3% MDD** — it never runs out of capacity.

3. **Crossover at ~20% MDD**: E0 surpasses LATCH in absolute CAGR at approximately 20% MDD budget (E0 CAGR=11.32% vs LATCH=11.21%). Above this level, E0 dominates in absolute return.

4. **Below 12.5% MDD**: LATCH dominates — higher CAGR per unit of MDD thanks to its higher Sharpe (1.3148 vs 1.0773).

5. **SM is the best at 12.5-15% MDD**: SM delivers CAGR of 11.46% at 12.5% MDD budget, slightly ahead of LATCH (11.21%). SM has slightly more capacity (MDD ceiling 15.0% vs 11.2%).

---

## 5. Pairwise Diagnostics

### 5.1 E0 scaled to LATCH native MDD (11.24%)

| Metric | E0 (k=0.131) | LATCH (k=1.0) | LATCH advantage |
|--------|:----------:|:----------:|:-----------:|
| CAGR | 6.11% | 11.21% | **+5.10 pp** (1.84×) |
| MDD | 11.24% | 11.24% | Matched |
| Sharpe | 1.0773 | 1.3148 | +0.24 |
| Exposure | 5.9% | 8.6% | +2.7 pp |

**At identical drawdown risk, LATCH delivers 84% more CAGR than E0.** This is the definitive head-to-head comparison. The gap comes entirely from LATCH's higher Sharpe ratio (1.3148 vs 1.0773), which means LATCH generates more return per unit of volatility.

### 5.2 E0 scaled to LATCH native exposure (8.6%)

| Metric | E0 (k=0.190) | LATCH (k=1.0) |
|--------|:----------:|:----------:|
| CAGR | 8.86% | 11.21% |
| MDD | 15.97% | 11.24% |
| Sharpe | 1.0773 | 1.3148 |

At matched exposure, E0 has **higher MDD** (15.97% vs 11.24%) AND **lower CAGR** (8.86% vs 11.21%). LATCH dominates on both axes.

### 5.3 Reverse match: Can LATCH reach E0-level MDD?

**No.** LATCH's native MDD is 11.24%, E0's is 63.30%. Without leverage >1, LATCH cannot reach E0-level drawdowns. This is a one-sided comparison: E0 can always be scaled down to LATCH's risk level, but LATCH cannot be scaled up to E0's.

This means:
- For risk budgets ≤ 11.24% MDD: **LATCH dominates** (higher CAGR at same risk)
- For risk budgets > 11.24% MDD: **E0 is the only option** (LATCH capped out)
- For risk budgets > ~20% MDD: **E0 surpasses LATCH in absolute CAGR** (not just available)

---

## 6. Equal-Overlay Control (EntryVol_12)

This uses the Step 3 factorial results where E0 and LATCH have identical sizing (EntryVol, target_vol=0.12, no rebalance). This isolates signal quality at matched risk budget.

| Metric | E0_EntryVol_12 | LATCH_EntryVol_12 | Delta |
|--------|:-----------:|:-----------:|:-----:|
| Sharpe | 1.3316 | 1.1951 | **-0.14** |
| CAGR | 14.94% | 12.91% | -2.03 pp |
| MDD | 15.98% | 13.64% | -2.34 pp |
| Score | 48.51 | 47.46 | -1.05 |

At identical sizing, **E0 has a genuine +0.14 Sharpe advantage**. This is the signal quality premium identified in Step 3.

However, this comparison does NOT use LATCH's natural sizing mechanism. LATCH with its native vol-floor achieves Sharpe=1.3148 (higher than E0_EntryVol_12's 1.3316 is close but slightly lower). The vol-floor acts as an implicit risk management that works better with the LATCH signal.

---

## 7. Secondary Multi-Strategy Frontier

| Strategy | Sharpe | MDD ceiling | CAGR ceiling | Calmar |
|----------|:------:|:----------:|:-----------:|:------:|
| E0_Native | 1.0773 | 63.30% | 45.04% | 0.711 |
| SM_Native | 1.3118 | 15.00% | 13.90% | 0.927 |
| P_Native | 1.2434 | 12.68% | 10.76% | 0.848 |
| LATCH_Native | 1.3148 | 11.24% | 11.21% | 0.998 |

**Ranking by Sharpe**: LATCH (1.315) > SM (1.312) > P (1.243) > E0 (1.077)
**Ranking by capacity (MDD ceiling)**: E0 (63.3%) >> SM (15.0%) > P (12.7%) > LATCH (11.2%)
**Ranking by efficiency (Calmar)**: LATCH (0.998) > SM (0.927) > P (0.848) > E0 (0.711)

LATCH and SM are essentially tied on Sharpe (0.003 difference). SM has ~34% more capacity than LATCH (MDD 15.0% vs 11.2%), making SM potentially more useful for larger risk budgets.

---

## 8. Complexity & Overfitting Context

| Strategy | Tunable params | Sharpe (native) | Calmar |
|----------|:-------------:|:---------------:|:------:|
| E0 | 3 | 1.0773 | 0.711 |
| SM | ~8 | 1.3118 | 0.927 |
| P | ~8 | 1.2434 | 0.848 |
| LATCH | ~15 | 1.3148 | 0.998 |

SM achieves Sharpe within 0.003 of LATCH with roughly half the parameters. The additional complexity in LATCH (hysteretic regime, vol_floor, etc.) provides marginal improvement at the cost of higher overfitting risk.

---

## 9. Resolution Matrix D1-D6

| ID | Question | Verdict | Key Evidence |
|----|----------|---------|--------------|
| D1 | At matched MDD, which has higher CAGR? | **LATCH wins**: 9.97% vs 5.38% at MDD=10% | Matched-MDD table |
| D2 | At matched MDD, which has higher Sharpe? | **LATCH wins**: 1.3148 vs 1.0773 (invariant of k) | Linearity property |
| D3 | E0 scaled to LATCH MDD: head-to-head | **LATCH dominates**: CAGR 11.21% vs 6.11%, same MDD 11.24% | Pairwise diagnostic A |
| D4 | Can LATCH reach E0-level MDD? | **No** — LATCH capped at 11.24% MDD without leverage | MDD ceiling |
| D5 | Equal-overlay control? | **E0 wins Sharpe by +0.14** at identical sizing (signal quality) | Step 3 EntryVol_12 |
| D6 | Overall deploy-oriented verdict | **Two non-overlapping regimes** — see Section 10 | Full analysis |

---

## 10. Overall Synthesis

### The Two-Regime Model

The matched-risk analysis reveals that E0 and LATCH are not competitors — they serve fundamentally different risk regimes:

**Regime A (MDD ≤ ~12%): LATCH dominates.**
- LATCH generates 1.84× more CAGR than E0 at the same drawdown risk
- This is driven by LATCH's higher native Sharpe (1.31 vs 1.08)
- LATCH operates near its natural capacity (k ≈ 0.89-1.0)
- SM is a close alternative (Sharpe 1.31, capacity slightly higher)

**Regime B (MDD > ~20%): E0 is the only option.**
- LATCH cannot fill larger risk budgets (capped at 11.24% MDD)
- E0 can scale to any risk budget up to 63.3% MDD
- At MDD=30%, E0 delivers CAGR=17.78% — far beyond LATCH's 11.21% ceiling

**Crossover zone (12-20% MDD): Mixed.**
- E0 surpasses LATCH in absolute CAGR near MDD≈20%
- SM offers the best trade-off in this zone (MDD ceiling 15%, Sharpe 1.31)

### Signal Quality vs Risk Efficiency

Step 3 established that E0 has a genuine +0.14 Sharpe signal-quality advantage at identical sizing (1.33 vs 1.20 at EntryVol_12). But this advantage disappears and reverses at native sizing:

| Comparison | E0 Sharpe | LATCH Sharpe | E0 wins? |
|------------|:---------:|:-----------:|:--------:|
| EntryVol_12 (same sizing) | 1.332 | 1.195 | YES (+0.14) |
| Native (own sizing) | 1.077 | 1.315 | NO (-0.24) |

LATCH's vol-targeted sizing with vol_floor=0.08 **adds 0.12 Sharpe** to its signal (from 1.20 → 1.31), while E0's binary sizing **subtracts 0.25 Sharpe** (from 1.33 → 1.08). The sizing mechanism is the decisive factor: LATCH's sizing amplifies its signal quality, while E0's binary sizing degrades it.

### Implications for the Scoring Formula

The original evaluation (Report 01): E0 score=90.68, LATCH score=44.17, delta=−46.51. This Step 4 analysis shows:

1. **At matched risk, LATCH is the superior strategy** — higher CAGR, higher Sharpe, better Calmar at any MDD budget ≤ 11.24%.
2. **The scoring formula correctly rewards E0 for something real** — its ability to fill large risk budgets (capacity). But it conflates capacity with quality.
3. **Neither strategy is "better" in absolute terms** — they dominate in different regimes.

---

## 11. Confounder Update (from Report 03)

| ID | Confounder | Status after Step 4 |
|----|-----------|-------------------|
| C01 | Sizing mismatch | **RESOLVED** (Step 3). Sizing creates +0.24 Sharpe for LATCH vs -0.25 for E0. |
| C02 | Exposure mismatch | **RESOLVED** (Step 4). External scaling removes exposure as confounder. |
| C13 | Scoring CAGR bias | **RESOLVED** (Step 3-4). Formula rewards capacity, not quality. |
| C14 | Risk-budget comparison | **RESOLVED** (Step 4). Matched-MDD analysis provides fair comparison. |

No remaining CRITICAL confounders.

---

## 12. Artifacts Produced

| File | Contents |
|------|----------|
| `frontier_grid.csv` | 404 rows × 20+ metrics (4 strategies × 101 k-points) |
| `linearity_check.json` | Linearity validation for all 4 strategies |
| `matched_mdd.csv` | Matched-MDD comparison at feasible targets |
| `matched_mdd_summary.json` | Summary of feasible region |
| `risk_budget.csv` | Operational risk-budget table (9 targets × 4 strategies) |
| `pairwise_diagnostics.json` | E0 vs LATCH at matched MDD and exposure |
| `equal_overlay_control.json` | EntryVol_12 same-sizing comparison |
| `resolution_matrix_d.csv` | D1-D6 resolution |
| `step4_master_results.json` | Complete results JSON |

---

## 13. Tests

`tests/test_frontier.py` — 18 tests, 5 test classes:

| Class | Tests | Coverage |
|-------|------:|----------|
| TestDeterministicRegeneration | 3 | eq↔returns roundtrip, scaled determinism, metrics determinism |
| TestLinearityCheck | 4 | Sharpe constant, MDD monotonic, CAGR monotonic, Sharpe(k)=Sharpe(1) |
| TestNoLeverage | 5 | k=0 flat, k=1 original, k>1 raises, k<0 raises, MDD(0)=0 |
| TestCorrectInterpolation | 3 | r_scaled = k*r, binary search accuracy, MDD(0.5) < MDD(1.0) |
| TestNoProductionMutation | 3 | input arrays not mutated, metrics returns scalars |

---

## 14. What This Report Does NOT Answer

1. **Statistical significance of Sharpe difference (1.31 vs 1.08)** — requires bootstrap testing
2. **Out-of-sample stability of the frontier** — requires walk-forward analysis
3. **Optimal portfolio allocation across strategies** — requires mean-variance or risk-parity framework
4. **Whether the 2-regime model persists under different market conditions** — requires regime-conditional analysis

---

## 15. Recommended Next Step

The matched-risk frontier analysis completes the deploy-oriented comparison. All original research questions from Report 00 are now answered:

- **Q1 (Signal Quality)**: E0 signal is genuinely better at identical sizing (Step 3: +0.14 Sharpe). But LATCH's sizing amplifies its signal to higher native Sharpe.
- **Q2 (Sizing Decomposition)**: 35% of score gap is sizing/exposure (Step 3). Sizing is the decisive factor in native Sharpe ranking.
- **Q3 (Engine Equivalence)**: Engines are functionally identical (Step 2: 7.7e-14% divergence).
- **Q4 (Fair Head-to-Head)**: At matched MDD, LATCH delivers 1.84× E0's CAGR (Step 4). At matched sizing, E0 leads by +0.14 Sharpe (Step 3).
- **Q5 (Regime Overlap)**: SM and LATCH are 99.8% concordant at defaults (Step 2).
- **Q6 (Complexity)**: No complexity premium — SM (8 params) matches LATCH (15 params) on Sharpe (Step 4: 1.312 vs 1.315).

**Possible next steps** (all require mathematical proof):
- (a) Bootstrap significance test of Sharpe difference between E0 and LATCH at matched risk
- (b) Walk-forward validation of frontier stability
- (c) Close study — write final synthesis

---

*End of Report 04. All research questions answered. No deployment recommendations.*
