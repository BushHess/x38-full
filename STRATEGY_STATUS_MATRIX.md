# Strategy Status Matrix

**Last updated**: 2026-03-17 (vocabulary reform + full re-run + x37v4 macroHystB comparison)
**Authoritative verdicts**: `results/full_eval_*/reports/decision.json`
**Latest report**: `reports/comprehensive_report_5_winners_20260317.md`

---

## Verdict Vocabulary Policy

Production and research use **separate verdict namespaces**. A research pass does
NOT imply production deployability.

| Label | Authority | Meaning |
|-------|-----------|---------|
| **PROMOTE** | Production (`decision.json`) | Passed all production gates. Deployable. |
| **HOLD** | Production (`decision.json`) | One or more production gates unresolved. Not deployable yet. |
| **REJECT** | Production (`decision.json`) | Failed hard gate. Not viable. |
| **SCREEN_PASS** | Research (standalone benchmark) | Passed all research-internal gates. Candidate for future productionization. |
| **SCREEN_FAIL** | Research (standalone benchmark) | Failed one or more research gates. Not a candidate. |

**Rules**:
1. Only production pipeline (`validation/decision.py`) may issue PROMOTE/HOLD/REJECT.
2. Research benchmarks (`research/xNN/benchmark.py`) issue SCREEN_PASS or SCREEN_FAIL.
3. A SCREEN_PASS strategy is NOT comparable to a production HOLD/PROMOTE — different
   gate systems, different WFO designs, different statistical tests.
4. To deploy a SCREEN_PASS strategy, it must first be ported to `strategies/`,
   registered in `STRATEGY_REGISTRY`, and run through the full production pipeline.
5. Low-power cases (few trades, few WFO windows) require human pair review
   per `docs/validation/pair_review_workflow.md`.

**Object types** (strategies must be compared within the same type):

| Type | Description | Example |
|------|-------------|---------|
| **standalone** | Complete strategy, runs independently | E5_ema21D1, E0_ema21D1 |
| **overlay** | Filter/modifier on top of a base strategy | X14_D (on E0), X18 (on E0) |
| **from-scratch** | Independent discovery, own benchmark | X28 Cand01 |
| **characterization** | No strategy output, analysis only | X22, X33 |

---

## Latency Tier Summary

E5_ema21D1 is LT1-only (≤4h automated). See [`LATENCY_TIER_DEPLOYMENT_GUIDE.md`](docs/algorithm/LATENCY_TIER_DEPLOYMENT_GUIDE.md) for full decision matrix.

| Tier | Strategy | Note |
|------|----------|------|
| LT1 (<4h) | **E5_ema21D1** | PRIMARY — requires 4h restart SLA |
| LT2 (4-16h) | E0_ema21D1 | Fallback — lower delay fragility |
| LT3 (>16h) | SM or flatten | Only vol-target survives manual execution |

---

## Active Strategies (Production Authority)

| Strategy | Code Path | Authority | Type | Verdict | Date | Key Metrics (harsh) | Notes |
|----------|-----------|-----------|------|---------|------|---------------------|-------|
| **E5_ema21D1** | `strategies/vtrend_e5_ema21_d1/` | **Production** | standalone | **HOLD** | 2026-03-17 | Sh 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades | PRIMARY. 6/7 gates PASS; WFO FAIL (Wilcoxon p=0.125). Bootstrap P(>E0)=97.2%. Underresolved, not negative-confirmed. |
| E0_ema21D1 | `strategies/vtrend_ema21_d1/` | **Production** | standalone | **HOLD** | 2026-03-17 | Sh 1.3536, CAGR 56.62%, MDD 40.01%, 174 trades | WFO FAIL (Wilcoxon p=0.191). Bootstrap P(>E0)=94.1%. |
| E0 (baseline) | `strategies/vtrend/` | Production | baseline | Baseline | — | — | Control strategy for A/B testing. Not a deployment candidate. |
| E5 (standalone) | `strategies/vtrend_e5/` | Production | standalone | **HOLD** | 2026-03-09 | — | WFO 4/8, insufficient OOS proof without D1 regime. |

## Research Candidates (Research Authority — NOT deployable without productionization)

| Strategy | Code Path | Authority | Type | Base | Verdict | Date | Key Metrics (harsh) | Notes |
|----------|-----------|-----------|------|------|---------|------|---------------------|-------|
| X14 Design D | `research/x14/` | **Research** | overlay | E0_ema21D1 | **SCREEN_PASS_D** | 2026-03-17 | Sh 1.530, CAGR 70.7%, MDD 35.9%, 148 trades | 6/6 research gates. MDD-focused churn filter. Cost crossover ~70 bps. |
| X18 α=50% | `research/x18/` | **Research** | overlay | E0_ema21D1 | **SCREEN_PASS** | 2026-03-17 | Sh 1.548, CAGR 71.9%, MDD 36.9%, 145 trades | 6/6 research gates. Return-focused churn filter. Cost crossover ~35 bps. |
| X28 Cand01 | `research/x28/` | **Research** | from-scratch | own benchmark | **SCREEN_PASS** | 2026-03-17 | Sh 1.251, CAGR 41.7%, MDD 52.0%, 39 trades | 9/9 research gates. Inferior to E5_ema21D1 on all metrics. |

**To deploy any SCREEN_PASS strategy**: port to `strategies/`, register in `STRATEGY_REGISTRY`, run full production pipeline. For overlays, rebase onto live base (E5_ema21D1, not E0).

## Alternative Profiles (not replacements for E5_ema21D1)

| Strategy | Code Path | Status | Date | Key Difference | Notes |
|----------|-----------|--------|------|----------------|-------|
| SM (State Machine) | `strategies/vtrend_sm/` | **ALT PROFILE** | 2026-03-06 | Low exposure (10.7%), turnover 7.2x/yr | Dominates E0 above 75 bps RT. Different risk/return tradeoff. |
| LATCH (Hysteretic) | `strategies/latch/` | **ALT PROFILE** | 2026-03-05 | Low exposure (9.5%), turnover 5.6x/yr | Dominates E0 above 50 bps RT. Different risk/return tradeoff. |

## Rejected Strategies

| Strategy | Code Path | Status | Reason |
|----------|-----------|--------|--------|
| EMA(126/H4) regime | `strategies/vtrend_ema21/` | **REJECT** | H4-timeframe regime doesn't work |
| VBREAK | `strategies/vbreak/` | **REJECT** | p=0.0026, threshold 0.001 |
| VCUSUM | `strategies/vcusum/` | **REJECT** | p=0.0186 |
| VTWIN | `strategies/vtwin/` | **REJECT** | DOF-corrected p=0.145 |
| v12 (EMDD ref fix) | `strategies/v12_emdd_ref_fix/` | **REJECT** | Legacy alternative |
| v13 (add throttle) | `strategies/v13_add_throttle/` | **REJECT** | Legacy alternative |
| P (pending) | `strategies/vtrend_p/` | **REJECT** | Evaluation incomplete |

## X-Series Research Variants (btc-spot-claude only)

All X-series variants were evaluated against E5_ema21D1 base. See `research/X_CONCEPT_AUDIT.md` for full analysis.

| Variant | Code Path | Classification | Reason |
|---------|-----------|----------------|--------|
| X0 (research anchor) | `strategies/vtrend_x0/` | Duplicate | **IDENTICAL to E0_ema21D1** (`vtrend_ema21_d1`). Created as X-series research baseline. |
| X0_E5exit | `strategies/vtrend_x0_e5exit/` | Duplicate | **Near-identical to E5_ema21D1** (`vtrend_e5_ema21_d1`). Lacks optional regime monitor. |
| X0-Volsize | `strategies/vtrend_x0_volsize/` | Research | Vol-targeted sizing variant |
| X1 (re-entry split) | `strategies/vtrend_x1/` | **REDUNDANT** | D1 regime is protective, not obstructive |
| X2 (adaptive trail) | `strategies/vtrend_x2/` | **REJECTED** | Conflicting with E5; overfits. WFO 4/8. |
| X3 (graduated sizing) | `strategies/vtrend_x3/` | **REJECTED** | Structural mismatch with fat-tailed alpha |
| X4B (parallel breakout) | `strategies/vtrend_x4b/` | **REJECTED** | EMA lag is a feature; breakout degrades quality |
| X5 (partial TP) | `strategies/vtrend_x5/` | **REJECTED** | Amputates fat tail. Tradeoff: -CAGR, -MDD. |
| X6 (adaptive+breakeven) | `strategies/vtrend_x6/` | **REJECTED** | Breakeven floor hostile to trend-following. WFO 4/8. |
| X7 (crypto-optimised) | `strategies/vtrend_x7/` | **REJECTED** | 7-filter pyramid kills exposure (30.6%). Sharpe 0.806 (-0.459 vs E0). Dead soft exit. |
| X8 (stretch cap only) | `strategies/vtrend_x8/` | **REJECTED** | E0 + stretch cap only. Sharpe 1.085 (-0.180). Blocks profitable momentum entries. |
| E5S (simplification) | `strategies/vtrend_e5s_ema21_d1/` | Research | Simplified E5 variant, not promoted |

## Churn Filter Research (X12-X19) — COMPLETE

| Study | Code Path | Classification | Reason |
|-------|-----------|----------------|--------|
| X12 (E5 mechanism) | `research/x12/` | NOISE | E5-E0 gap = noise P=46.4% |
| X13 (churn predictability) | `research/x13/` | INFO_EXISTS | AUC=0.805, perm p=0.002 |
| X14 (churn filter design) | `research/x14/` | **SCREEN_PASS_D** | Design D: Sh 1.530, CAGR 70.7%, MDD 35.9%, all 6 research gates pass (re-run 2026-03-17) |
| X15 (dynamic filter) | `research/x15/` | ABORT | 7 trades, MDD 77%, 1/6 gates |
| X16 (WATCH state machine) | `research/x16/` | ALL_FAIL | Bootstrap 49.8%, path-specific autocorrelation |
| X17 (percentile WATCH) | `research/x17/` | NOT_TEMPORAL | WFO 25%, G dilemma: G<4 no-op, G≥8 path-specific |
| X18 (α-percentile static mask) | `research/x18/` | **SCREEN_PASS** | α=50% (consensus), Sh 1.548, CAGR 71.9%, MDD 36.9%, WFO 75%, Bootstrap 63.4%, all 6 research gates pass (re-run 2026-03-17) |
| X19 (alt actuators) | `research/x19/` | **CLOSE** | Branch A WFO 25%, Branch B ≈ no-op. Static suppress strictly optimal |

**Summary**: Two SCREEN_PASS churn filters — X14_D (MDD-focused: 35.9%) and X18 (return-focused: Sh 1.548). Both use 7-feature logistic static suppress. Alternative actuators (X19: exit+re-enter, partial runner), WATCH (X16/X17), and dynamic filters (X15) all fail. **Churn research COMPLETE — static suppress is the only viable actuator.** Note: SCREEN_PASS = passed research gates only, not production-validated.

**Cost-Dependent Deployment Guidance** (from X22, 2026-03-10):
- X18 ΔSharpe crossover: ~35 bps RT. **Negative** below 35 bps, **positive** above.
- X14D ΔSharpe crossover: ~70 bps RT. **Negative** below 70 bps.
- At Binance VIP 0 + BNB (7.5 bps/side, 20-30 bps RT with slippage): **skip both churn filters**.
- Deploy X18 only if execution cost consistently > 35 bps RT (large size, low liquidity).
- Churn filter value is mostly cost savings, not genuine alpha (X22 T2 linear relationship).

---

## New Research Wave (X20-X22)

Breadth expansion beyond single-asset single-strategy optimization.

| Study | Code Path | Classification | Focus |
|-------|-----------|----------------|-------|
| X20 (cross-asset portfolio) | `research/x20/` | **CLOSE** | BTC-only Sh 0.735 >> best portfolio 0.259. Altcoins dilute alpha. WFO 1/4. |
| X21 (conviction sizing) | `research/x21/` | **CLOSE** | ABORT at T-1: CV IC = -0.039 < 0.05. Entry features cannot predict trade returns. |
| X22 (cost sensitivity) | `research/x22/` | **DONE** | Churn filters HURT at <30 bps. E5_ema21D1 wins at 10-20 bps. All Sh>1.5 at 15 bps. Breakeven >999 bps. Retail (Binance VIP0+BNB, 20-30 bps): skip churn filter. |

**Rationale**: IR = IC × √BR. IC near ceiling after 53 studies.
**Results**: X20 CLOSED (dilution), X21 CLOSED (no IC), X22 DONE (characterization — churn filter is cost-dependent, not genuine alpha).

**Realistic Cost Guidance** (Binance VIP 0 + BNB, 7.5 bps/side):
- Smart execution: 18-20 bps RT → E5_ema21D1 Sh ~1.64, **skip churn filter**
- Normal retail: 25-30 bps RT → E5_ema21D1 Sh ~1.57, **skip churn filter**
- Conservative: 35 bps RT → X18 crossover point, **neutral**
- Drawdown shock: 50 bps RT → X18 ΔSh +0.034, **use X18 as insurance**

---

## Deep Research Wave (X23-X28, 2026-03-10 to 2026-03-11)

Structured 8-phase protocol studies exploring exits, entries, volume, flat periods, and from-scratch discovery.

| Study | Code Path | Classification | Focus |
|-------|-----------|----------------|-------|
| X23 (exit geometry) | `research/x23/` | **REJECT** | State-conditioned pullback multipliers. Sh 1.202 (-0.229 vs E5). 2/6 gates. Increased churn 63%→72%. |
| X24 (trail arming) | `research/x24/` | **REJECT** | Trail arming isolation. Sh 1.365 (-0.067 vs E5). 2/6 gates. 53 never-armed entries. |
| X25 (volume filter) | `research/x25/` | **KEEP_VDO** | Volume/TBR entry filters. STOP at Phase 4. All 5 features p>0.39. VDO near-optimal, can't tighten. |
| X26 (flat periods) | `research/x26/` | **STOP_NOISE** | FLAT period mean-reversion. STOP at Phase 4. Gross 3-9 bps vs 15-50 bps cost. Untradeable. |
| X27 (alt mechanisms) | `research/x27/` | **BENCHMARK_OPTIMAL** | Breakout vs EMA crossover. Cand01 Sh 0.907 < bench 1.084. Zero churn but lower Sharpe. |
| X28 (from-scratch) | `research/x28/` | **SCREEN_PASS** | From-scratch discovery. Cand01 Sh 1.251, 9/9 research gates. avg_loser #1 driver. Inferior to VTREND E5_ema21D1. |

**Key conclusions from X23-X28**:
- VTREND E5_ema21D1 remains PRIMARY — no study found a superior algorithm
- X28 Cand01 (Sh 1.251) is the best from-scratch result but still < E5_ema21D1 (Sh 1.432)
- X27 breakout eliminates churn entirely (0%) but trades Sharpe (-0.177)
- X25/X26 confirm: volume features are noise, flat periods are untradeable
- X28 finding: avg_loser is #1 Sharpe predictor (partial R²=0.306); churn has ZERO predictive power (p=0.76)

---

## X37 Arena — External Algorithm Comparison

| Study | Code Path | Classification | Focus |
|-------|-----------|----------------|-------|
| X37 Branch A (x37v4 macroHystB) | `research/x37/branches/a_v4_vs_e5_fair_comparison/` | **V4_COMPETITIVE** | V4 macroHystB vs E5_ema21D1 at 20 bps RT. V4 wins Sharpe (1.865 vs 1.607), MDD (23.9% vs 35.4%), bootstrap P=93.6%. WFO underpowered (3 power windows, Wilcoxon p=1.0). NOT promoted — higher complexity (~10 vs 4 params), yearly recalibration, wider sensitivity spread. |

**x37v4 key numbers (20 bps RT, full period 2020-2026)**:
- Sharpe 1.865, CAGR 67.1%, MDD 23.9%, 51 trades, WR 58.8%, PF 6.27
- V4 Sharpe > E5 at ALL cost levels (no crossover). CAGR slightly below E5 (67.1% vs 69.0%).
- Report: `research/x37/branches/a_v4_vs_e5_fair_comparison/REPORT.md`

---

## Final Closure Studies (X31-X32, 2026-03-12)

| Study | Code Path | Classification | Focus |
|-------|-----------|----------------|-------|
| X31-A (D1 regime exit) | `research/x31/` | **STOP** | Mid-trade D1 EMA flip. Selectivity 0.21 << 1.5. Fat-tail alpha concentration blocks all mid-trade exits. |
| X31-B (re-entry barrier) | `research/x31/` | **STOP** | Oracle ceiling +0.038 < +0.08 GO threshold. Error cost 8.1x benefit. Economic ceiling, not overfit. |
| X32 (VP1 research) | `research/x32/` | **CLOSED** | VP1 family vs E5_ema21D1. All VP1 variants beat full-sample but FAIL holdout/WFO. No transfer warranted. |

### VP1 Variant Verdicts (X32)

| Strategy | Code Path | Sharpe | MDD % | Validation | Verdict |
|----------|-----------|--------|-------|------------|---------|
| VP1 | `strategies/vtrend_vp1/` | 1.452 | 40.5 | Holdout FAIL | **ERROR** |
| VP1-E5exit | `strategies/vtrend_vp1_e5exit/` | 1.488 | 36.6 | Holdout FAIL | **ERROR** |
| VP1-FULL | `strategies/vtrend_vp1_full/` | 1.461 | 41.0 | WFO FAIL (p=0.125) | **ERROR** |
| E5_ema21D1 | `strategies/vtrend_e5_ema21_d1/` | 1.430 | 41.6 | 6/7 gates (WFO underresolved) | **HOLD** |

**Key finding**: VP1 parameter set (slow=140, trail=2.5, d1_ema=28) overfits earlier regimes. VP1 structural features (prevday D1, per-bar VDO, anomaly) are irrelevant on BTCUSDT. RATR is the single most valuable change (-3.88 pp MDD). E5_ema21D1 confirmed PRIMARY.

---

## Naming Convention

**Full reference**: [`docs/NAMING_CONVENTION.md`](docs/NAMING_CONVENTION.md)

### Canonical Strategy IDs

| Short ID | Code name | Directory | Description |
|----------|-----------|-----------|-------------|
| **E0** | `vtrend` | `strategies/vtrend/` | Standard ATR(14) trail + EMA cross-down exit. 3 params. Baseline. |
| **E5** | `vtrend_e5` | `strategies/vtrend_e5/` | Robust ATR(20, Q90 cap) trail + EMA cross-down exit. 3 params. |
| **E0_ema21D1** | `vtrend_ema21_d1` | `strategies/vtrend_ema21_d1/` | E0 + D1 EMA(21) regime filter. 4 params. |
| **E5_ema21D1** | `vtrend_e5_ema21_d1` | `strategies/vtrend_e5_ema21_d1/` | E5 + D1 EMA(21) regime filter. 4 params. **PRIMARY**. |

### External Algorithm IDs (X37 Arena)

| Short ID | Algorithm | Code Path | Verdict | Notes |
|----------|-----------|-----------|---------|-------|
| **x37v4** | macroHystB | `research/x37/branches/a_v4_vs_e5_fair_comparison/` | **V4_COMPETITIVE** | 3-feature hysteresis, ~10 params. NOT a VTREND variant. |

### Research-Origin Duplicates

| Research ID | Directory | Canonical equivalent | Relationship |
|-------------|-----------|---------------------|--------------|
| X0 | `strategies/vtrend_x0/` | **E0_ema21D1** | IDENTICAL (same algo, same defaults) |
| X0_E5exit | `strategies/vtrend_x0_e5exit/` | **E5_ema21D1** | Near-identical (E5_ema21D1 adds optional regime monitor) |

### Historical Directory Name Variants

| You see... | It means... |
|------------|------------|
| `ema21_d1` (strategy dirs) | D1 EMA(21) regime filter |
| `ema1d21` (research dirs) | Same thing — legacy naming |
| `ema21d1` (result dirs) | Same thing — no underscore variant |
| `full_eval_x0_ema21d1/` | E0_ema21D1 validation results |

---

## Production Readiness Research (2026-03-09)

Studies in `research/prod_readiness_e5_ema1d21/` (E5_ema21D1). These are PROVEN and DEPLOYED components.

| Study | Verdict | Key Finding | Artifact |
|-------|---------|-------------|----------|
| **Regime Monitor V2** | **SCREEN_PASS** | MDD-only dual-window. Sharpe +0.158, CAGR +7.3%, MDD -5.7%. Blocks 17 false entries, 0 forced exits. | `monitoring/regime_monitor.py` |
| **E5S Validation** | **KEEP E5** | Simplified ATR(20) loses 0.088 Sharpe vs robust ATR. Does NOT qualify as simplification (threshold 0.02). | `E5S_VALIDATION_REPORT.md` |
| **DOF Correction** | **SUGGESTIVE** | 16 timescales = ~4.35 effective (Nyholt). E5 vs X0: p=0.0625 (93.8%). E5 vs E5S: p=0.0312 (96.9%). | `E5_DOF_CORRECTION_REPORT.md` |

### Regime Monitor V2 Operational Parameters

| Parameter | Value |
|-----------|-------|
| AMBER (6m MDD) | > 45% |
| AMBER (12m MDD) | > 60% |
| RED (6m MDD) | > 55% |
| RED (12m MDD) | > 70% |
| Mechanism | Entry prevention (not exit forcing) |
| V1 | REJECTED — raw ATR structurally broken (71.6% false RED) |

---

## Production Validation Framework (2026-03-09 reform, updated 2026-03-17)

Machine validation produces AUTO_PROMOTE / AUTO_HOLD / AUTO_REJECT.
This is **not** the final deployment decision — see 3-Tier Authority Model below.

**Hard gates** (fail → AUTO_REJECT):
1. `lookahead` — zero violations
2. `full_harsh_delta` — ΔScore ≥ -0.2
3. `holdout_harsh_delta` — ΔScore ≥ -0.2

**Soft gates** (fail → AUTO_HOLD):
4. `wfo_robustness` — Wilcoxon p ≤ 0.10 OR Bootstrap CI > 0 (OR logic, not AND)
5. `trade_level_bootstrap` — conditional (auto-enabled when WFO low-power)
6. `selection_bias` — method_fallback or PBO fail → soft. PSR → **info only** (no veto)

**Diagnostics** (no veto power):
7. `bootstrap` — info only since Report 21
8. PSR — info only, demoted 2026-03-16

**Canonical source**: `docs/validation/decision_policy.md`

**Authoritative results** (latest 2026-03-17 re-run):
- E5_ema21D1: `results/full_eval_e5_ema21d1_20260317/`
- E0_ema21D1: `results/full_eval_e0_ema21d1_20260317/`
- X14: `research/x14/x14_results.json` (research authority)
- X18: `research/x18/x18_results.json` (research authority)
- X28: `research/x28/tables/` (research authority)

---

## 3-Tier Authority Model

Framework separates three distinct questions, each with its own authority:

| Tier | Question | Authority | Artifact |
|------|----------|-----------|----------|
| **1. Research Screening** | Is this worth productionizing? | Research benchmark (`benchmark.py`) | SCREEN_PASS / SCREEN_FAIL |
| **2. Machine Validation** | Is OOS evidence sufficient? | Production pipeline (`decision.json`) | AUTO_PROMOTE / AUTO_HOLD / AUTO_REJECT |
| **3. Deployment Decision** | Should we run this live now? | Human researcher (pair review) | `deployment_decision.md` |

**Rules**:
- Tier 1 SCREEN_PASS does NOT imply Tier 2 will pass. Different gate systems.
- Tier 2 AUTO_HOLD does NOT mean "do not deploy". It means "automated evidence
  is insufficient to confirm" — the strategy may still be the best available option.
- Tier 3 is the **final authority** for live deployment. Uses all evidence from
  Tier 1 + Tier 2 + economic analysis + human judgment.
- Hard gates (lookahead, data integrity, regression) are absolute blockers at
  all tiers — no human override.

**Why AUTO_HOLD ≠ "not deployable"**: With n=8 WFO windows and small effect sizes
(ΔSharpe ~0.10-0.19), Wilcoxon signed-rank has low power. AUTO_HOLD means
"rank-based test cannot confirm", not "evidence is against the strategy".
E5_ema21D1 has bootstrap P(>E0)=97.2%, holdout delta +5.58, PSR=1.000 — all
pointing positive. The WFO test is **underresolved**, not negative.

See `docs/validation/pair_review_workflow.md` for Tier 3 decision process.
