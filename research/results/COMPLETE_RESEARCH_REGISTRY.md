# VTREND Complete Research Registry

All research studies conducted on btc-spot-dev, with scripts, results, and verdicts.
Re-run: 2026-03-02 (all 45 scripts, 0 failures, 9h 22m total).
Parity evaluation: 2026-03-05 (6-strategy comparison, validation + research T1-T7).
Deep research wave: 2026-03-10 to 2026-03-11 (X23-X28, 8-phase protocol studies).
Stacking & fractional actuator: 2026-03-11 (X29-X30).
Final closure & VP1 research: 2026-03-12 (X31-X32).
Execution cost & methodology reform: 2026-03-13 (X33).
X37 arena — external algorithm comparison: 2026-03-17 (x37v4 macroHystB).
Covers all 72 studies + infrastructure scripts.

---

## I. PROVEN COMPONENTS (survived bootstrap)

### 1. EMA Crossover Entry Signal
- **Script**: `research/multiple_comparison.py`
- **Results**: `results/multiple_comparison/`
- **Evidence**: p=0.0003, survives Bonferroni/Holm/BH correction
- **Mechanism**: Captures generic trend-following premium across 16 timescales
- **Verdict**: **PROVEN**

### 2. ATR Trail + EMA Cross-Down Exit
- **Script**: `research/multiple_comparison.py`, `research/creative_exploration.py`
- **Evidence**: ATR trail p=0.0003. E7 (trail-only, remove EMA exit) = MDD worse 3/16 (Sharpe 14/16 but MDD tradeoff)
- **Mechanism**: EMA cross-down genuinely complements ATR trail (controls drawdown)
- **Verdict**: **PROVEN** (both components necessary)

### 3. VDO Filter
- **Script**: `research/timescale_robustness.py`, `research/binomial_correction.py`
- **Results**: `results/timescale_robustness/`, `results/binomial_correction/`
- **Evidence**: 16/16 timescales, corrected p=0.031 (Galwey DOF). +0.20 Sharpe, -8% MDD
- **Mechanism**: Uses real taker_buy data (not OHLCV proxy). Consistent across ALL timescales
- **Verdict**: **PROVEN**

### 4. EMA(21d) Regime Filter ← NEW PROVEN COMPONENT
- **Script**: `research/ema_ablation.py`, `research/ema_regime_sweep.py`, `research/ema_regime_fine.py`
- **Results**: `results/ema_ablation/`, `results/ema_regime_sweep/`, `results/ema_regime_fine/`
- **Evidence**:
  - Binomial: 16/16 ALL metrics (Sharpe, CAGR, MDD, NAV), p=1.5e-5
  - PROVEN range: 15d–40d (8/18 tested periods pass ALL metrics)
  - Sweet spot: EMA(21d) = 126 H4 bars
  - Multi-coin: 11/14 coins improved on real data
  - BTC bootstrap 500 paths × 16 TS: CONFIRMED
- **Magnitude (per-path median at N=120)**:
  - P(Sharpe+) = 61.6%, median Sharpe: E0+EMA=0.4609 vs E0=0.4499
  - P(CAGR+) = 61.4%
  - P(MDD-) = 66.0%
- **Mechanism**: Only trade when close > EMA(21d on D1). Avoids entering during macro downtrends.
- **Verdict**: **PROVEN** (direction consistent 16/16; magnitude modest)

---

## II. PARAMETER STUDIES (tradeoffs, not free improvements)

### 5. Trail=4.5 vs Default Trail=3.0
- **Script**: `research/trail_sweep.py` (sweep trail 2.0–5.0), `research/config_compare.py` (old results in `results/config_compare/`)
- **Results**: `results/trail_sweep/trail_sweep.json`, `results/config_compare/config_compare.json` (stale, pre-rerun)
- **trail_sweep bootstrap (500 paths × 16 TS, slow=120)**:
  - Sharpe: 12/16 wins (p=0.038)
  - CAGR: 14/16 wins (p=0.002) → **PROVEN**
  - NAV: 14/16 wins (p=0.002) → **PROVEN**
  - MDD: 1/16 wins (p=0.999) → **PROVEN WORSE**
- **Verdict**: trail=4.5 is PROVEN better returns but PROVEN WORSE MDD. Return-for-risk tradeoff.

### 6. Config Compare: slow=200/fast=50/trail=3.0 vs Default 120/30/3.0
- **Script**: `research/config_compare.py`
- **Results**: `results/config_compare_200v120/config_compare.json`
- **Real data**: CUSTOM (200/50/3.0) Sh=1.432, CAGR=63.1%, MDD=41.8% vs DEFAULT Sh=1.276, CAGR=52.7%, MDD=41.5%
- **Bootstrap (500 paths × 16 TS)**: P(C>D): Sharpe 42.2%, CAGR 42.4%, MDD 46.0%, NAV 42.4% — ALL NOT SIG
- **Note**: Both configs share fast=slow/4 ratio, so they map to same strategy across timescale sweep (Δ=0.0000)
- **Verdict**: **REJECTED**. slow=200 has ZERO advantage over slow=120 at same trail.

### 7. Trail Multiplier Fine Sweep (2.0 to 5.0, step 0.25)
- **Script**: `research/trail_sweep.py`
- **Results**: `results/trail_sweep/trail_sweep.json`
- **Bootstrap (500 paths × 16 TS)**:
  - trail=2.75: MDD 15/16 (p=0.00026) **PROVEN LOWER MDD**, but Sharpe only 6/16
  - trail=4.5: Sharpe 12/16 (p=0.038), CAGR 14/16 (p=0.002), but MDD 1/16 **WORSE**
  - trail=4.75–5.0: Sharpe 16/16 (p=1.5e-5), CAGR 16/16, MDD 1/16 **WORSE**
- **Verdict**: Higher trail = more return + more MDD. Lower trail = less MDD + less return. **No free lunch.** trail=3.0 is the compromise.

### 8. VTREND Full Parameter Sensitivity
- **Script**: `research/vtrend_param_sensitivity.py`
- **Results**: `results/vtrend_param_sensitivity/vtrend_param_sensitivity.json`
- **Tested**: slow sweep, ATR period, VDO fast/slow, 2D slow×trail, 2D slow×ratio
- **Phase 1 peaks**: slow=138 (Sh 1.423), ATR=28 (Sh 1.303), VDO 12/20 (Sh 1.335)
- **Phase 3 bootstrap**: ALL candidates FAIL to beat default on ALL metrics simultaneously
  - slow=138/trail=2.5: Sharpe 4/16, CAGR 4/16, MDD 10/16 — NOT SIG
  - slow=138/trail=5.0: Sharpe 13/16 (p=0.011), MDD 4/16 — returns only
- **Verdict**: **REJECTED**. Default (120/30/3.0) is within robust plateau. No parameter combo beats it on ALL metrics.

---

## III. REJECTED ALGORITHMS (failed bootstrap)

### 9. VPULL — Pullback Entry
- **Script**: `research/pullback_strategy.py`
- **Results**: `results/pullback_strategy/`
- **Bootstrap**: p=1.0 (0/16 timescales). Pullback timing WORSE than random entry.
- **Verdict**: **REJECTED**

### 10. VBREAK — Donchian Breakout
- **Script**: `research/vbreak_test.py`
- **Results**: `results/vbreak_test/`
- **Real data**: CAGR +35.2%, Sharpe 1.179, 75 trades
- **Bootstrap**: breakout signal p=0.0026 (>0.001 threshold), ATR trail p=0.0472
- **Verdict**: **REJECTED** (p not < 0.001)

### 11. VCUSUM — Change-Point Detection
- **Script**: `research/vcusum_test.py`
- **Results**: `results/vcusum_test/`
- **Real data**: CAGR +25.2%, Sharpe 0.934, 80 trades
- **Bootstrap**: CUSUM signal p=0.0186, ATR trail p=0.0062
- **Verdict**: **REJECTED** (7x weaker than VBREAK)

### 12. VTWIN — Twin-Confirmed Trend
- **Script**: `research/vtwin_test.py`, `research/vexit_study.py`
- **Results**: `results/vtwin_test/`, `results/vexit_study/`
- **Bootstrap**: P(MDD-)=91% at N=120, reaches 97.5% only at N=720 (suboptimal timescale)
- **DOF correction**: nominal p=0.011 → corrected p=0.145 — NOT SIG
- **Verdict**: **REJECTED** (collapses under DOF correction)

### 13. Ratcheting ATR Trail
- **Script**: `research/vexit_study.py`
- **Results**: `results/vexit_study/`
- **Bootstrap**: P≈50% all metrics, all timescales (= coin flip)
- **Verdict**: **REJECTED** (zero effect)

### 14. PE / PE* Candle Quality
- **Script**: `research/pe_study.py`, `research/pe_study_v2.py`
- **Results**: `results/pe_study/`, `results/pe_study_v2/`
- **V1 (8 variants)**: Best P(MDD-)=78.6% — FAIL
- **V2 (10 variants)**: Best P(MDD-)=85.8% — FAIL
- **PE replacing VDO**: actively WORSE (P≈21%)
- **Verdict**: **REJECTED** (ZERO provable value)

### 15. E5 — Robust ATR (capped TR at Q90)
- **Script**: `research/e5_validation.py`, `research/binomial_correction.py`
- **Results**: `results/e5_validation/`, `results/binomial_correction/`
- **Real data**: 16/16 timescales win on NAV
- **Bootstrap (post-bugfix, 2000 paths × 16 TS)**:
  - Sharpe: 0/16 (p=1.0) — NOT SIG
  - CAGR: 0/16 (p=1.0) — NOT SIG
  - MDD: **16/16 (p=1.5e-5) → corrected p=0.004 — PROVEN**
  - NAV (real): 16/16 (p=1.5e-5) — PROVEN
- E5 reduces MDD but does NOT improve returns. MDD improvement survives DOF correction.
- **Multi-coin**: Catastrophic on altcoins (E5 HURTS on 7/14 coins)
- **Parity Eval (Study 41)**: Harsh Sharpe 1.365 (best E0-class), CAGR 57.0%, MDD 40.3%. WFO 4/8. Beats E0 at all 10 slow periods and all cost levels 0-75 bps.
- **Verdict**: **HOLD** (WFO 4/8 — 1 window below threshold; strongest E0-class performer)

### 16. E6 — Staleness Exit
- **Script**: `research/e6_staleness_study.py`
- **Results**: `results/e6_staleness_study/`
- **Real data**: Up to 16/16 wins for sb=12,18
- **Bootstrap**: ALL 64 combos P(NAV+) < 50%. Best only 31.8% (sb=48, mt=0.5).
- **Verdict**: **REJECTED** (smooth surface of DAMAGE)

### 17. E7 — Trail-Only Exit (remove EMA cross-down)
- **Script**: `research/creative_exploration.py`, `research/e7_study.py`
- **Results**: `results/creative_exploration/`, `results/e7_study/`
- **Bootstrap (creative_exploration)**: Sharpe wins 14/16, CAGR 10/16, MDD only 3/16 (p=0.998), NAV 10/16
- **Bootstrap (e7_study)**: E7 vs E0 P(NAV+)=40.4%, E7 vs E5 staleness contribution P(NAV+)=19.2%
- **Verdict**: **REJECTED** — E7 trades Sharpe for MDD. EMA cross-down controls drawdown.

### 18. Multi-Timescale Ensemble (6 timescales, equal-weight)
- **Script**: `research/creative_exploration.py`
- **Results**: `results/creative_exploration/`
- **Real data**: Ensemble (Sh=1.193, CAGR=46.5%) WORSE than E0@120 (Sh=1.276, CAGR=52.7%)
- **Bootstrap**: Wins/16: Sharpe=14, CAGR=14, MDD=16, NAV=14. MDD 16/16 PROVEN (p=0.0000).
- **Cross-timescale ρ=0.923** → diversification ceiling +3.4%
- **Verdict**: **NOT ADOPTED** — MDD improvement real but ensemble doesn't beat BEST single timescale on any metric

### 19. D1 EMA(200) Regime Filter
- **Script**: `research/d1_ema200_filter.py`
- **Results**: `results/d1_ema200_filter/d1_ema200_filter.json`
- **Bootstrap**: Sharpe 0/16, CAGR 1/16, NAV 2/16 — NOT SIG. MDD 16/16 PROVEN.
- **Multi-coin**: Mixed (SOL/ADA benefit, ETH/BNB hurt)
- **Verdict**: **REJECTED** (200-day EMA too slow — kills returns, only helps MDD)

### 20. EMA(63d) and EMA(126d) Regime Filters
- **Script**: `research/ema_regime_fine.py`
- **Results**: `results/ema_regime_21_63_126/`
- **Bootstrap**: Sharpe/CAGR NOT SIG. MDD 16/16 PROVEN (both).
- **Verdict**: **REJECTED** for full adoption (only MDD, not returns). >40d filters hurt returns.

---

## IV. SUPPORTING STUDIES

### 21. Timescale Robustness (16 timescales × 2000 paths)
- **Script**: `research/timescale_robustness.py`
- **Results**: `results/timescale_robustness/`
- **Findings**: Alpha from GENERIC trend-following. Productive: slow=30-720. Strong: 60-144. Sharpe plateau 0.425-0.442.

### 22. True WFO + Permutation Test
- **Script**: `research/true_wfo_compare.py`
- **Results**: `results/true_wfo_compare/`
- **Findings**: EMA signal p=0.000. VDO marginal p=0.060. VTREND vs V8: 5-5 draw.

### 23. V8 vs VTREND Bootstrap
- **Script**: `research/v8_vs_vtrend_bootstrap.py`
- **Results**: `results/v8_vs_vtrend_bootstrap/`
- **Findings**: V8 complexity (40+ params) adds ZERO value. V8 significantly worse on MDD.

### 24. Position Sizing
- **Script**: `research/position_sizing.py`
- **Results**: `results/position_sizing/`
- **Findings**: Sharpe ~0.43 invariant to sizing. Vol-target 15% ≈ f=0.30 optimal Calmar.

### 25. Regime Sizing
- **Script**: `research/regime_sizing.py`
- **Results**: `results/regime_sizing/`
- **Findings**: VTREND profits in ALL 6 regimes. No regime approach beats f=0.30.

### 26. Resolution Sweep (H1/H4/D1)
- **Script**: `research/resolution_sweep.py`
- **Results**: `results/resolution_sweep/`
- **Findings**: H1 ZERO alpha. H4 BEST. D1 productive but weaker. Crossover ~30d.

### 27. Cost Sensitivity
- **Script**: `research/cost_study.py`
- **Results**: `results/cost_study/`
- **Findings**: 15bps Sh 0.676, 25bps Sh 0.606, 50bps Sh 0.432.

### 28. Effective DOF Correction
- **Script**: `research/binomial_correction.py`, `research/lib/effective_dof.py`
- **Results**: `results/binomial_correction/`
- **Findings**: Binary Sharpe M_eff: Galwey 5.0. VDO corrected p=0.031 (still STRONG).

### 29. VCBB Bootstrap Fix
- **Script**: `research/lib/bootstrap.py`, `research/validate_bootstrap.py`
- **Results**: `results/validate_bootstrap/`
- **Findings**: VCBB recovers 76-100% vol clustering. Median Sharpe 0.43→0.54.

---

## V. MULTI-COIN STUDIES

### 30. Multi-Coin EMA(21d) Regime Filter
- **Script**: `research/multicoin_ema_regime.py`
- **Results**: `results/multicoin_ema_regime/`
- **Findings**: 11/14 coins improved. BTC PROVEN 16/16. SOL/LINK 16/16.

### 31. Multi-Coin 200 vs 120
- **Script**: `research/multicoin_200v120.py`
- **Results**: `results/multicoin_200v120/`
- **Findings**: 8/14 coin flip. No cross-asset evidence for slow=200.

### 32. Multi-Coin Exit Variants
- **Script**: `research/multicoin_exit_variants.py`
- **Results**: `results/multicoin_exit_variants/`
- **Findings**: E5 catastrophic on altcoins. E6/E7 neutral-to-bad.

### 33. Multi-Coin Diversification
- **Script**: `research/multicoin_diversification.py`
- **Results**: `results/multicoin_diversification/`
- **Findings**: Only 8/14 coins positive alpha. Portfolio Sharpe PROVEN, MDD WORSE. ρ=0.343.

---

## VI. INFRASTRUCTURE & AUDIT

### 34. Full System Audit
- **Scripts**: `research/audit_phase1_3.py`, `research/audit_phase4.py`
- **Results**: `results/FULL_AUDIT_REPORT.md`
- **Verdict**: 5/5 phases PASS, 12/12 studies PASS, 6/6 invariants PASS, 7/7 bootstrap checks PASS

### 35. Cross-Check vs VTrend Engine
- **Script**: `research/cross_check_vs_vtrend.py`
- **Verdict**: Indicators BIT-IDENTICAL. Aligned metrics within 0.2%.

### 36. Mathematical Invariant Tests
- **Script**: `research/invariant_tests.py`
- **Verdict**: 17/17 invariants PASS (scale invariance, cost monotonicity, determinism, etc.)

### 37. DSR Module
- **Script**: `research/lib/dsr.py`, `research/lib/test_dsr.py`
- **Verdict**: 19/19 unit tests PASS. Cross-validated vs VTrend (rel=1e-10).

### 38. Bug Audit & Fix
- **Findings**: CAGR off-by-one (62 occurrences), creative_exploration.py wrong constants, Group B latent bug (27 occurrences), rounding inconsistency, ANN 2190→2191.5, ddof inconsistency
- **Status**: ALL FIXED. 53/53 files pass syntax check.

---

## VII. VTREND-SM VARIANT (State-Machine, Vol-Targeted)

### 39. VTREND-SM Design & Implementation
- **Reports**: `research_reports/34_vtrend_sm_survey.md`, `34b_vtrend_sm_preintegration_audit.md`, `34c_vtrend_sm_design_contract.md`, `35_vtrend_sm_integration.md`
- **Source**: Ported from `Latch/research/vtrend_variants.py::run_vtrend_state_machine()`
- **Code**: `strategies/vtrend_sm/strategy.py` (VTrendSMStrategy, VTrendSMConfig)
- **Tests**: `tests/test_vtrend_sm.py` — 56/56 pass
- **Algorithm**:
  - Entry: EMA regime (fast > slow + slope) AND breakout (close > rolling_high) AND optional VDO
  - Exit: adaptive floor = max(rolling_low, ema_slow − atr_mult × ATR) OR optional regime break
  - Sizing: vol-targeted (target_vol / realized_vol), fractional 0.0–1.0
  - Rebalance: only when |target − current| ≥ min_rebalance_weight_delta
- **Key difference from E0**: Fractional vol-targeted sizing (~10% avg exposure) vs E0 binary all-in (~45%). Different entry (breakout) and exit (adaptive floor) mechanisms.
- **Default params**: slow_period=120, atr_mult=3.0, target_vol=0.15, slope_lookback=6
- **Integration**: Registered in all 5 integration points (strategy_factory, cli, config, candidates, validation)
- **Status**: Implemented and tested, 56/56 tests pass

### 40. VTREND-SM Evaluation & Validation
- **Reports**: `research_reports/36_vtrend_sm_evaluation.md`, `36b_vtrend_sm_validation_followup.md`, `36c_vtrend_sm_repo_hygiene.md`
- **Full data range (2017-08 to 2026-02):**

| Metric | SM base | E0 base |
|--------|---------|---------|
| CAGR % | 14.80 | 52.59 |
| Sharpe | 1.3895 | 1.1944 |
| Sortino | 1.1623 | 1.0495 |
| MDD % | 14.23 | 61.37 |
| Calmar | 1.0402 | 0.8568 |
| Trades | 76 | 226 |
| Avg Exposure | 0.1065 | 0.4523 |

- **PairDiagnostic**: materially_different (corr=0.729, near_equal_1bp=51.9%), boot_sharpe_p=0.214, boot_geo_p=0.989
- **Validation pipeline (2019-01 to 2026-02):**
  - 12/12 suites ran. Verdict: REJECT(2) — SM scores lower on CAGR-weighted objective
  - WFO: 5/8 windows SM wins (62.5%), PASS
  - Bootstrap harsh: p(SM Sharpe > E0 Sharpe) = 0.759
  - DSR: 1.0 across N=27..700 trials → SM Sharpe is robust
  - Cost sweep: SM dominates above 75 bps RT (low turnover 7.2×/yr vs E0 52.3×/yr)
  - Selection bias: PASS. Data integrity: PASS. Invariants: PASS
- **Regime decomposition**: SM MDD capped at 13.01% across ALL 6 regimes; SM Sharpe > E0 in SHOCK, BEAR, BULL
- **Verdict**: **EVALUATED — ALTERNATIVE PROFILE**. SM is a valid, distinct strategy with higher Sharpe (+16.3%), dramatically lower MDD (4.3×), but much lower CAGR (3.6×). Not a replacement for E0. Different risk/return tradeoff, not a strict improvement or rejection.

---

## VIII. PARITY EVALUATION (6-strategy comparison)

### 41. Parity Evaluation — E0, E5, SM, LATCH, EMA21, EMA21-D1
- **Script**: `research/parity_eval.py` (T1-T7), `validation/` framework (13 suites)
- **Results**: `results/parity_20260305/`, `research/results/parity_eval/`
- **Report**: `results/parity_20260305/PARITY_REPORT.md`
- **Date**: 2026-03-05
- **Strategies**:
  - E0: baseline (EMA cross + ATR trail)
  - E5: robust ATR (capped TR at Q90)
  - SM: state machine, vol-targeted fractional sizing
  - LATCH: hysteretic EMA regime, vol-targeted fractional sizing
  - EMA21: E0 + EMA(126) regime filter on H4
  - EMA21-D1: E0 + EMA(21) regime filter on D1

#### Validation Verdicts (13-suite framework vs E0 baseline)
| Strategy | Verdict | harsh_delta | holdout_delta | WFO |
|----------|---------|-------------|---------------|-----|
| E0 | HOLD | 0.000 | 0.000 | 0/8 |
| E5 | HOLD | +13.196 | +3.212 | 4/8 |
| SM | REJECT | -67.625 | -33.611 | 5/8 |
| LATCH | REJECT | -72.914 | -37.651 | 5/8 |
| EMA21 | REJECT | -2.820 | +24.880 | 5/8 |
| EMA21-D1 | **PROMOTE** | +7.370 | +5.980 | 6/8 |

#### Research T1-T7 Results
- **T1 Full Backtest**: E5 best CAGR (57.0%), SM best Sharpe (1.447), LATCH lowest MDD (11.2%)
- **T2 Permutation (10K)**: ALL pass at p < 0.001
- **T3 Timescale (16 TS)**: ALL positive Sharpe 15-16/16 timescales
- **T4 Bootstrap (500 × 16 TS)**: SM P(CAGR>0)=97.8%, E5 MDD 16/16, EMA21 CAGR 13/16
- **T5 Postmortem**: SM/LATCH zero DD>20% episodes. E0-class: 5 episodes each.
- **T6 Sensitivity**: E5 > E0 at all 10 slow periods. EMA21-D1 > E0 at 9/10.
- **T7 Cost**: SM/LATCH dominate at >50 bps. E5/EMA21-D1 > E0 at all cost levels.

- **Key conclusion**: EMA21-D1 is the ONLY strategy to pass ALL validation gates (PROMOTE). E5 is the strongest E0-class performer but held by WFO (4/8). SM and LATCH are valid alternative profiles with 3-4× lower CAGR/MDD, not E0 replacements.
- **Verdict**: **EMA21-D1 = PROMOTE; E5 = HOLD; SM/LATCH/EMA21 = REJECT**

### 42. 6-Strategy Comparative Evaluation — Tier 3
- **Script**: `research/eval_vtrend_latch_20260305/src/*_6s.py`
- **Results**: `research/eval_vtrend_latch_20260305/artifacts/*_6s.*`
- **Tests**: `research/eval_vtrend_latch_20260305/tests/test_6s.py` (26 tests)
- **Date**: 2026-03-06
- **Findings**:
  - Step 3 (factorial): E5 highest signal quality (Binary_100 Sharpe 1.208), SM/LATCH signal ≡ (99.8%)
  - Step 4 (frontier): LATCH/SM best at matched low risk, E5 beats E0 at ALL MDD levels
  - Step 5 (robustness): **0/15 pairs Holm-significant**; E5>E0 P=91%, EMA21-D1>E0 P=86%
- **Verdict**: Confirms Tier 1/2 direction with uncertainty bounds. No verdict changes.

### 43. E5_plus_EMA1D21 Full Evaluation — Tier 1+2+4
- **Script**: `research/eval_e5_ema1d21/src/run_jackknife_wfo.py`, `run_tier2_tier4.py`
- **Results**: `results/parity_20260306/`, `research/eval_e5_ema1d21/artifacts/`
- **Report**: `results/parity_20260306/E5_PLUS_EMA1D21_EVALUATION_REPORT.md`
- **Date**: 2026-03-06
- **Strategy**: E5_plus_EMA1D21 = robust ATR (Q90-capped TR + Wilder EMA) + D1 EMA(21) regime
- **Code**: `strategies/vtrend_e5_ema21_d1/`
- **Tier 1**: ALL 13 gates PASS. harsh_delta +21.64, holdout +9.54, WFO 5/8 (62.5%)
- **Tier 2**: Sharpe 1.432, CAGR 59.96%, MDD 41.57%. Perm p=0.0001. TS 16/16. Boot MDD h2h 16/16.
- **Tier 4**: Win rate 41.2%, PF 1.667, Jackknife -5 = -33.8% (most robust), Gini 0.620.
- **vs E0_plus_EMA1D21**: Wins 16/20 dimensions. E0_plus wins WFO (75% vs 62.5%) and boot Sharpe (12/16).
- **Verdict**: **PROMOTE** — dominates on real-data metrics; E0_plus stronger on OOS consistency (WFO)

---

## VIII-A. X-SERIES STRATEGY VARIANTS (X7-X9)

### 44. X7 — Crypto-Optimised Trend-Following (7-Filter Pyramid)
- **Script**: `research/x7/benchmark.py`
- **Results**: `research/x7/x7_results.json`, `x7_*.csv`
- **Report**: `research/x7/TECHNIQUE_COVERAGE_47.md` (264 lines)
- **Date**: 2026-03-09
- **Hypothesis**: 7 crypto-specific modifications (D1 continuity, ATR band, stretch cap, ratchet trail, soft exit, cooldown, dual VDO) improve E0.
- **Results (harsh cost)**:
  - X7: Sharpe 0.806 (-0.459), CAGR 22.5% (-29.5%), MDD 50.1% (+8.5%), trades 129, exposure 30.6%
  - Soft exit never triggers (0/129). D1 continuity too restrictive. EMA band kills entries.
  - 7-filter pyramid reduces exposure from 46.8% to 30.6% (-34.6%), cutting CAGR in half.
- **Verdict**: **REJECTED** — Tier 1 ERROR (2 hard gate failures). Restrictive entry conditions destroy returns without meaningful risk reduction.

### 45. X8 — E0 + Stretch Cap Only
- **Script**: `research/x8/benchmark.py`
- **Results**: `research/x8/x8_results.json`, `x8_*.csv`
- **Report**: `research/x8/TECHNIQUE_COVERAGE_47.md` (224 lines)
- **Date**: 2026-03-09
- **Hypothesis**: Stretch cap alone (1.5×ATR overextension filter) improves E0 without X7's other filters.
- **Results (harsh cost)**:
  - X8: Sharpe 1.085 (-0.180), CAGR 34.3% (-17.7%), MDD 39.8% (-1.8%), trades 126, exposure 28.6%
  - Cap blocks 34% of E0 entries, removing mostly profitable ones.
  - Cap sweep: optimal cap ≈ 1.0-1.2×ATR (Sharpe 1.305) still < E0 (1.265 Sharpe / 52.0% CAGR).
  - MDD wins 10/16 timescales but CAGR loss dominates.
- **Verdict**: **REJECTED** — Tier 1 exit code 2 (2 hard + 2 soft gate failures). Stretch cap blocks profitable momentum entries.

### 46. X9 — Break-Even Stop for E5+EMA21D1
- **Script**: `research/x9/benchmark.py`
- **Results**: `research/x9/x9_results.json`, `x9_*.csv`
- **Date**: 2026-03-09
- **Hypothesis**: Moving stop to entry price (breakeven) at X×R profit eliminates winning-to-losing trades.
- **Counter**: ATR trail mult=3.0 already provides organic breakeven protection. Hard BE may whipsaw out prematurely.
- **Variants**: E5 (baseline, no BE), BE_0.8 (BE at 0.8R), BE_1.0 (BE at 1.0R)
- **Tests**: T1 backtest, T2 timescale, T3 VCBB bootstrap, T4 BE threshold sweep, T5 trade anatomy, T6 organic BE analysis
- **Results (harsh cost)**:
  - E5: Sharpe 1.430, CAGR 59.85%, MDD 41.64%, 186 trades
  - BE_0.8: Sharpe 1.409 (-0.021), CAGR 58.48%, MDD 41.64%, 189 trades
  - BE_1.0: Sharpe 1.428 (-0.002), CAGR 59.73%, MDD 41.64%, 187 trades
  - Marginal differences — BE adds nothing. Counter-hypothesis confirmed: ATR trail already provides organic protection.
- **Verdict**: **REJECTED** — Negligible delta, zero MDD improvement. BE stop is redundant with ATR trail at mult=3.0.

---

## VIII-B. EXTENDED RESEARCH (X10-X15)

### 47. X10 — Multi-TP Ladder for E5+EMA21D1
- **Script**: `research/x10/benchmark.py`
- **Results**: `research/x10/x10_results.json`, `x10_*.csv`
- **Date**: 2026-03-09
- **Hypothesis**: Partial take-profit exits (1.5R, 2.2R, 3.0R) lock profit earlier, reducing MDD.
- **Counter**: Trend-following profits come from fat right tails. Fixed TPs cut winners.
- **Variants**: FULL (baseline), TP2 (50/50 at 1.5R), TP3 (30/30/20/20 at 1.5R/2.2R/3.0R)
- **Results (harsh cost)**:
  - FULL: Sharpe 1.432, CAGR 60.0%, MDD 41.6%
  - TP2: Sharpe 1.291, CAGR 42.3%, MDD 44.2% — worse on ALL metrics
  - TP3: Sharpe 1.057, CAGR 31.4%, MDD 48.3% — much worse
- **Verdict**: **REJECTED** — TPs destroy trend-following alpha. Counter-hypothesis confirmed.

### 48. X11 — Short-Side Complement for E5+EMA21D1
- **Script**: `research/x11/benchmark.py`
- **Results**: `research/x11/x11_results.json`, `x11_*.csv`
- **Date**: 2026-03-09
- **Hypothesis**: Short during regime OFF (bearish) generates independent alpha.
- **Results**:
  - Short-only (harsh): Sharpe -0.640, CAGR -24.6%, MDD 92.1% — catastrophic
  - Short negative at ALL 16 timescales
  - Combined (long+short harsh): Sharpe 1.254 vs long-only 1.432 — WORSE
  - Bootstrap h2h: Sharpe win 0%, CAGR win 0.4%, MDD win 63.2%
  - Correlation: pearson ρ=0.001 (uncorrelated but negative-EV)
  - No breakeven funding rate exists (negative at 0 bps)
- **Verdict**: **REJECTED** — BTC's upward drift makes trend-following shorts negative-EV.

### 49. X12 — Why Does E5 Win If It Doesn't Fix Churn?
- **Script**: `research/x12/benchmark.py`
- **Spec**: `research/x12/SPEC.md`
- **Results**: `research/x12/x12_results.json`, `x12_*.csv`
- **Date**: 2026-03-09
- **Central question**: E5's robust ATR doesn't fix churn. Where does its edge come from?
- **Tests**: T0 churn audit, T1 cascade map, T2 matched mechanism, T3 decomposition, T4 timescale, T5 bootstrap, T6 cost sweep
- **Key findings**:
  - E0: 63% trail stops are churn, churn PnL net positive (+$329K)
  - E5 doesn't reduce churn (64.5% vs 63.1%)
  - E5-E0 headline gap: P=46.4% bootstrap → **inconclusive** (see supersession note in REPORT.md)
  - Decomposition: path-state drives 67% of gap (matched trades differ in exit timing)
  - Cost sweep: cf_ret crossover at ~38 bps RT — E5 better at low cost, neutral at high cost
- **Verdict**: **CHURN_FAILS_BUT_TAIL_WINS** — E5's edge is from smoother ATR, not churn repair. Gap is inconclusive (P=46.4%, direction ambiguous) with cost-dependent value (crossover ~38 bps).

### 50. X13 — Is Trail-Stop Churn Predictable?
- **Script**: `research/x13/benchmark.py`
- **Spec**: `research/x13/SPEC.md`
- **Results**: `research/x13/x13_results.json`, `x13_*.csv`
- **Date**: 2026-03-09
- **Central question**: At trail stop trigger, does information exist to distinguish true reversals from churn?
- **Phases**: P0 Oracle, P1 Features, P2 Univariate, P3 Multivariate, P4 Bootstrap, P5 Sensitivity
- **Key findings**:
  - Oracle ceiling: +0.845 Sharpe (1.336→2.181), 186→82 trades
  - Top features: ema_ratio (+0.567 Cliff's d), bars_held (+0.520), d1_regime_str (+0.458)
  - LOOCV AUC=0.805, permutation p=0.002
  - Bootstrap median AUC=0.68, P(AUC>0.60)=86.8%
  - Stable across all 5 churn windows (10-40 bars)
- **Verdict**: **INFORMATION_EXISTS** — Pareto frontier is theoretically breakable.

### 51. X14 — Trail-Stop Churn Filter: Design & Validation
- **Script**: `research/x14/benchmark.py`
- **Spec**: `research/x14/SPEC.md`
- **Results**: `research/x14/x14_results.json`, `x14_*.csv`
- **Date**: 2026-03-09
- **Central question**: Can a simple filter capture X13's signal and survive OOS validation?
- **Designs** (fixed-sequence, simplest first):
  - A (0 params, entry-signal gate): FAIL G0 (d_sharpe=-0.069)
  - B (1 param, ema_ratio>1.035): FAIL G2 (bootstrap 57.6% < 60%)
  - C (2 params, ema_ratio+d1_regime): FAIL G1 (WFO 50% < 75%)
  - D (WFO logistic model): PASS all 6 gates
- **Design D results**:
  - In-sample: Sharpe 1.428 (+0.092), CAGR 64.0%, MDD 36.7% (-5.3pp), 133 trades
  - WFO: 3/4 wins (75%), mean d=+0.195
  - Bootstrap: P(d_sharpe>0)=65%, median d_mdd=+2.4pp
  - Jackknife: 0/6 negative, mean d=+0.084
  - PSR: 1.000 (DOF-corrected)
- **Assessment**: Only complex model (D) passes — simple filters insufficient for multivariate signal. Captures 11% of oracle ceiling. Bootstrap 65% above 60% gate.
- **Verdict**: **SCREEN_PASS_D** — passes all 6 research gates. Candidate for productionization alongside E5+EMA1D21.
- **Next**: X15 integration study — production retraining pipeline, regime monitor interaction, feature drift.
- **Conclusion**: Churn signal REAL, requires model-based approach. Design D = valid complementary filter.

### 52. X15 — Churn Filter Integration: Dynamic Filter & Feature Fix
- **Script**: `research/x15/benchmark.py`
- **Spec**: `research/x15/SPEC.md`
- **Results**: `research/x15/x15_results.json`, `x15_*.csv`
- **Date**: 2026-03-09
- **Central question**: X14's static mask zeros 3 trade-context features (bars_held, dd_from_peak, bars_since_peak). Does fixing this with dynamic evaluation at trail-stop time improve the filter?
- **Tests**: T0 feature fix, T1 ablation, T2 WFO, T3 bootstrap, T4 monitor interaction, T5 retrain sensitivity, T6 comparison
- **Key findings**:
  - X15 dynamic (10 features): Sharpe 1.030, **7 trades**, 15,020 suppressions, MDD 77.0% — **CATASTROPHIC**
  - X14 static (7 features): Sharpe 1.428, 133 trades, 821 suppressions, MDD 36.7% — works well
  - T1 ablation: 7-feature subset works (Sharpe 1.39). Adding trade-context features causes collapse.
  - bars_held (Cliff's d=0.520) + dd_from_peak cause model to predict nearly ALL trail stops as churn → over-suppress everything
  - T2 WFO: 50% win rate (FAIL, need 75%)
  - T3 bootstrap: P(d_sharpe>0)=77.4% (PASS) but median d_mdd=+10.83pp (FAIL)
  - T4 monitor: interaction penalty 0.096 (FAIL, need <0.05)
  - T5 retrain: max coeff drift 0.666 (FAIL, need <0.50), trail_tightness and vdo_at_exit most unstable
- **Critical insight**: X14's "feature mismatch bug" was actually **implicit regularization**. Zeroing trade-context features prevents the model from learning "almost all trail stops are followed by recovery" — true but useless as a filter. The static 7-feature mask IS the correct approach.
- **Gates**: G0 FAIL, G1 FAIL, G2 PASS, G3 FAIL, G4 FAIL, G5 FAIL (1/6 pass)
- **Verdict**: **ABORT** — Dynamic 10-feature model destroys the filter. Design D works BECAUSE of the static mask.

---

## IX. SUMMARY TABLE

| # | Study | Real Data | Bootstrap | Verdict |
|---|-------|-----------|-----------|---------|
| 1 | EMA crossover | — | p=0.0003 | **PROVEN** |
| 2 | ATR trail + EMA exit | — | E7 MDD=3/16 (Sh 14/16) | **PROVEN** |
| 3 | VDO filter | 16/16 TS | corrected p=0.031 | **PROVEN** |
| 4 | EMA(21d) regime filter | 11/14 coins | 16/16 ALL metrics | **PROVEN** |
| 5 | trail=4.5 (slow=120) | — | CAGR 14/16 but MDD 1/16 | TRADEOFF |
| 6 | slow=200/trail=3.0 | Sh 1.432 | P(C>D)=42% NOT SIG | REJECTED |
| 7 | Trail sweep (2.0–5.0) | — | Higher trail = return↑ MDD↑ | TRADEOFF |
| 8 | Param sensitivity (full) | peaks at 138 | FAIL all combos | REJECTED |
| 9 | VPULL | — | p=1.0 (0/16) | REJECTED |
| 10 | VBREAK | Sh 1.179 | p=0.0026 | REJECTED |
| 11 | VCUSUM | Sh 0.934 | p=0.0186 | REJECTED |
| 12 | VTWIN | MDD -17.5pp | P=91%, DOF→p=0.145 | REJECTED |
| 13 | Ratcheting ATR | real data + | P≈50% | REJECTED |
| 14 | PE / PE* | PE* Sh 1.53 | P(MDD-)=85.8% | REJECTED |
| 15 | E5 (robust ATR) | 16/16 real | Sh 0/16, MDD **16/16** | **HOLD** (WFO 4/8) |
| 16 | E6 (staleness) | 16/16 real | P(NAV+)=32% | REJECTED |
| 17 | E7 (trail-only) | — | Sh 14/16, MDD 3/16 | REJECTED (tradeoff) |
| 18 | Ensemble | worse real | MDD 16/16, Sh 14/16 | NOT ADOPTED |
| 19 | D1 EMA(200) | mixed | Sh 0/16, MDD 16/16 | REJECTED |
| 20 | EMA(63d/126d) | — | Sh NOT SIG, MDD only | REJECTED |
| 39 | VTREND-SM design | 56/56 tests | — | IMPLEMENTED |
| 40 | VTREND-SM eval | Sh 1.39, MDD 14.2% | boot_sharpe_p=0.214 | ALTERNATIVE PROFILE |
| 41 | Parity eval (6 strats) | EMA21-D1 best | ALL p<0.001, 15-16/16 TS | EMA21-D1 **PROMOTE** |
| 42 | Tier 3 comparative (6s) | E5 signal best | 0/15 Holm-sig | Confirms direction |
| 43 | E5_plus_EMA1D21 eval | Sh 1.432, 16/20 wins | MDD h2h 16/16, Sh h2h 4/16 | **PROMOTE** |
| 44 | X7: Crypto-Optimised 7-Filter | Sh 0.806 (-0.459), exposure 30.6% | 7-filter pyramid kills exposure | REJECTED |
| 45 | X8: Stretch Cap Only | Sh 1.085 (-0.180), E0+1 filter | Insufficient improvement | REJECTED |
| 46 | X9: Break-Even Stop | BE_0.8 Sh 1.409, BE_1.0 Sh 1.428 | Redundant with ATR trail | REJECTED |
| 47 | X10: Multi-TP Ladder | TP2 Sh 1.291, TP3 Sh 1.057 | — | REJECTED |
| 48 | X11: Short-Side Complement | Short Sh -0.640, MDD 92% | h2h Sharpe win 0% | REJECTED |
| 49 | X12: E5 Mechanism Forensics | E5-E0 gap P=46.4% | cf_ret crossover 38 bps | INCONCLUSIVE |
| 50 | X13: Churn Predictability | AUC=0.805, perm p=0.002 | median AUC=0.68 | INFORMATION_EXISTS |
| 51 | X14: Churn Filter Design | Design D Sh 1.530, CAGR 70.7%, MDD 35.9% (re-run 2026-03-17) | P(d_sharpe>0)=66.2%, 6/6 research gates | **SCREEN_PASS_D** |
| 52 | X15: Dynamic Filter Fix | X15 Sh 1.030, 7 trades | 1/6 gates pass | ABORT |
| 53 | X16: Stateful Exit (WATCH) | Design E Sh 1.424, WFO 4/4 | P(d>0)=49.8% bootstrap | ALL_FAIL |
| 54 | X17: Percentile WATCH | α=5% G=1, WFO 25% | G dilemma: G<4 no-op, G≥8 path-specific | NOT_TEMPORAL |
| 55 | X18: α-Percentile Static Mask | α=50% (consensus), Sh 1.548, CAGR 71.9%, MDD 36.9% (re-run 2026-03-17) | WFO 3/4 (75%), P(d>0)=63.4%, PSR=1.000 | **SCREEN_PASS** |
| 56 | X19: Alt Actuators (exit+re-enter, runner) | A: WFO 25%, B: WFO 50% (no-op) | Both fail G1, static suppress strictly optimal | CLOSE |
| 57 | X20: Cross-Asset VTREND Portfolio | BTC Sh 0.735 >> best portfolio 0.259 (BC) | Altcoins dilute BTC alpha. WFO 1/4. MDD worse. | **CLOSE** |
| 58 | X21: Conviction-Based Position Sizing | ABORT: CV IC = -0.039 < 0.05 | Entry features cannot predict trade returns | **CLOSE** |
| 59 | X22: Cost Sensitivity Analysis | Churn filters HURT at <30 bps. E5+EMA1D21 wins at 10-20 bps | All Sh>1.5 at 15 bps. Breakeven >999 bps. | **CHARACTERIZATION** |
| 60 | X23: State-Conditioned Exit Geometry | Sh 1.202 (-0.229 vs E5), 197 trades | 2/6 gates, bootstrap P(δ>0)=47.2% | REJECTED |
| 61 | X24: Trail Arming Isolation | Sh 1.365 (-0.067 vs E5), 180 trades | 2/6 gates, bootstrap P(δ>0)=52.8% | REJECTED |
| 62 | X25: Volume/TBR Entry Filter Lab | All 5 features p>0.39 | STOP at Phase 4, VDO near-optimal | KEEP_VDO |
| 63 | X26: Flat Period Mean-Reversion | Gross 3-9 bps vs 15-50 bps cost | STOP at Phase 4, underpowered | STOP_UNDERPOWERED |
| 64 | X27: Breakout vs EMA Crossover | Cand01 Sh 0.907, zero churn | Bench Sh 1.084 wins; all 8 gates for Cand01 | BENCHMARK_OPTIMAL |
| 65 | X28: From-Scratch Discovery | Cand01 Sh 1.251, 39 trades, 9/9 research gates | SCREEN_PASS but < VTREND E5+EMA1D21 (1.432) | SCREEN_PASS |
| 66 | X29: Optimal Stack | Mon Sh 1.733 full-sample, best combo Mon+X18 WFO 75% | T3 FAIL: P(d_sharpe>0)=45.8% < 55% | **RECOMMEND Mon V2 only** |
| 67 | X30: Fractional Actuator | discrete_pf90 best cand, WFO 2/4 | G2 FAIL, G3 FAIL, P(d>0)=43.6%, perm p=1.0 | **REJECT** |
| 68 | X31-A: D1 Regime Exit | Selectivity 0.21 << 1.5, winner cost 10.39% vs loser benefit 2.13% | Fat-tail constraint | STOP |
| 69 | X31-B: Re-entry Barrier Oracle | Oracle ΔSh +0.038 < +0.08 GO. Anti-oracle -0.204 (8.1x) | Economic ceiling | STOP |
| 70 | X32: VP1 Research | VP1 Sh 1.452 full-sample, ALL FAIL validation | Parameter overfit | CLOSED |
| 71 | X33: Execution Cost | Median RT=16.8 bps. X18 skip (econ), X14D skip (econ) | Empirical measurement | **DONE** |

**Score: 4 PROVEN / 2 TRADEOFFS / 19 REJECTED / 1 NOT ADOPTED / 1 ALTERNATIVE / 2 PROMOTE (production, now HOLD) / 3 SCREEN_PASS (research) / 1 INCONCLUSIVE / 1 INFO_EXISTS / 1 ABORT / 2 FAIL / 1 CLOSE / 2 CHARACTERIZATION / 3 STOP / 1 BENCHMARK_OPTIMAL / 1 KEEP / 1 RECOMMEND / 1 CLOSED**

> **Vocabulary note (2026-03-17)**: Research verdicts renamed PROMOTE → SCREEN_PASS.
> Production PROMOTE/HOLD/REJECT comes only from `decision.json`. Research SCREEN_PASS
> comes from standalone benchmarks with different (lenient) gate systems.
> See `STRATEGY_STATUS_MATRIX.md § Verdict Vocabulary Policy`.

---

## X. FINAL ALGORITHM: VTREND E0 + EMA(21d) on D1

Based on all 53 studies:
- **Entry**: Close > EMA(slow) AND VDO > 0.0 AND Close > EMA(21d on D1)
- **Exit**: Close < EMA(slow) OR Close < ATR trail stop
- **Default params**: slow=120, fast=30, trail_mult=3.0, vdo_threshold=0.0, ema_regime=126 H4 bars
- **Cost**: 25 bps per side (50 bps round-trip)
- **Resolution**: H4

The only algorithmic improvement found since the original "algorithm discovery complete" declaration is the **EMA(21d) regime filter on D1** — PROVEN 16/16 across ALL metrics with p=1.5e-5. Parity evaluation (Study 41) confirms EMA21-D1 is the ONLY strategy to pass ALL validation gates (PROMOTE verdict). Implementation: `strategies/vtrend_ema21_d1/`.

**Update (Study 43)**: E5_plus_EMA1D21 (robust ATR + D1 EMA(21) regime) also passes ALL validation gates and wins 16/20 comparison dimensions vs E0_plus_EMA1D21. Key advantages: +7.2% Sharpe on real data, stronger holdout (+9.54 vs +5.98), more jackknife-resilient. Key weakness: WFO 62.5% vs 75%, bootstrap Sharpe regression (E0_plus wins 12/16 h2h). Implementation: `strategies/vtrend_e5_ema21_d1/`.

**Update (Studies 47-51, 2026-03-09)**: Extended research on modifications to E0+EMA1D21:
- X10: Take-profit ladders REJECTED (destroy trend-following alpha)
- X11: Short-side complement REJECTED (BTC upward drift makes shorts negative-EV)
- X12: E5-E0 gap inconclusive (P=46.4%). Path-state mechanism, not churn repair.
- X13: Trail-stop churn IS predictable (AUC=0.805, perm p=0.002). Pareto frontier theoretically breakable.
- X14: Simple filters (A/B/C) all fail OOS. Design D (WFO logistic) passes ALL 6 research gates → **SCREEN_PASS_D**.
  Design D: Sharpe 1.428 (+0.092), MDD 36.7% (-5.3pp), WFO 3/4, JK 0/6 negative, bootstrap 65%.
- **Decision**: E5+EMA1D21 = PRIMARY. Design D (churn filter) = research SCREEN_PASS for future productionization.
- X15: Attempted to "fix" X14's zeroed trade-context features with dynamic evaluation → **ABORT** (7 trades, MDD 77%).
  X14's static mask IS the correct approach — zeroing bars_held/dd_from_peak/bars_since_peak acts as implicit regularization.
  Design D production integration should use X14's STATIC mask, not X15's dynamic filter.

**Update (Studies 53-55, 2026-03-10)**: Churn filter research completed (X16-X18):
- X16: WATCH state machine (stateful exit) — Design E Sharpe 1.424 in-sample but bootstrap P(d>0)=49.8% FAIL.
  Edge is path-specific autocorrelation that bootstrap destroys. ALL_FAIL verdict.
- X17: α-percentile + nested WFO + conservative WATCH (G=1-4) — WFO 25% FAIL.
  G dilemma confirmed: G<4 too short, G≥8 path-specific. No viable G window for WATCH.
- X18: α-percentile static mask + nested WFO — ALL 6 research gates PASS → **SCREEN_PASS** (α=40%).
  Sharpe 1.482 (+0.145), CAGR 66.6%, MDD 41.8%, WFO 100%, Bootstrap 62.6%, JK 1/6 neg.
  X18 > X14_D on returns (Sh 1.482 vs 1.428), X14_D better on MDD (36.7% vs 41.8%).
  Two SCREEN_PASS churn filters at different return/risk profiles.
- X19: Alternative actuators for churn score (exit+contingent re-entry, partial runner) — CLOSE.
  Branch A (exit+re-enter): WFO 25% FAIL. MDD improvement (35.6%) doesn't survive OOS — armed re-entries don't trigger.
  Branch B (partial runner): WFO 50% FAIL, deltas ≈ 0. Cost of partial exit + add-back (100 bps RT) destroys runner capture.
  Static suppress strictly dominates alternative actuators on positive-ΔU episodes (100% capture at zero cost).
  **Churn research series (X12-X19) COMPLETE. Static suppress confirmed as the only viable actuator.**

**Update (Studies 57-59, 2026-03-10)**: New research wave — breadth expansion beyond single-asset optimization:
- X20: Cross-Asset VTREND Portfolio — multi-asset diversification using E0+EMA1D21 (non-BTC) and E5+EMA1D21 (BTC/ETH).
  Prior evidence: E0+EMA1D21 generalizes to 11/14 coins (Study #30). E5 only works on BTC+ETH (Q16).
  Zero additional DOF (frozen per-asset params, analytical portfolio weights).
- X21: Conviction-Based Position Sizing — entry-time features predict trade quality, Kelly-like variable sizing.
  Prior evidence: churn score predicts exit quality (AUC=0.805). Entry prediction untested.
  +1 DOF (β sizing aggression). IC abort gate < 0.05.
- X22: Cost Sensitivity Analysis — characterize strategy performance across execution costs (2-100 bps).
  All 53 prior studies use 50 bps (3-10× harsher than reality). Zero gates (characterization only).
  Key question: is churn filter value from cost savings or genuine alpha?

**Update (Studies 60-65, 2026-03-10 to 2026-03-11)**: Deep research wave — 8-phase protocol studies:
- X23: State-Conditioned Exit Geometry — redesign exit with pullback multipliers. REJECT (2/6 gates, Sh -0.229 vs E5).
- X24: Trail Arming Isolation — trail arming as entry isolation. REJECT (2/6 gates, Sh -0.067 vs E5).
- X25: Volume/TBR Entry Filter Lab — STOP at Phase 4. VDO near-optimal, all features p>0.39.
- X26: Flat Period Mean-Reversion — STOP at Phase 4. Gross 3-9 bps vs 15-50 bps cost barrier.
- X27: Breakout vs EMA Crossover — Cand01 Sh 0.907 < bench 1.084. Zero churn but lower Sharpe.
- X28: From-Scratch Discovery — Cand01 Sh 1.251, 9/9 gates PASS, but < VTREND E5+EMA1D21 (Sh 1.432).
  Key discovery: avg_loser is #1 Sharpe predictor (partial R²=0.306); churn has zero predictive power (p=0.76).

**Update (Studies 66-67, 2026-03-11)**: Stacking and fractional actuator studies:
- X29: Optimal Stack — 12 combos (Mon, X14D, X18, T45). Mon full-sample best (Sh 1.733).
  Trail=4.5 always hurts Sharpe. Churn filters hurt at 25 bps. Synergies exist (X14D×T45 +0.275).
  At 25 bps: no stack beats base convincingly per X29 criteria. Objective-dependent trade-offs.
- X30: Fractional Actuator — partial exit at trail stop based on churn signal. All 3 candidates REJECT.
  Best (discrete_pf90): WFO 2/4, bootstrap P(d>0)=43.6%, permutation p=1.0. Signal preserved but no tradable edge.

---

## XI. DEEP RESEARCH WAVE (X23-X28, 8-Phase Protocol)

### 60. X23: State-Conditioned Exit Geometry Redesign
- **Script**: `research/x23/benchmark.py`
- **Results**: `research/x23/x23_results.json`, `research/x23/x23_report.md`
- **Date**: 2026-03-10
- **Hypothesis**: State-conditioned pullback multipliers (weak/normal/strong) improve exit geometry and reduce churn.
- **Results**:
  - X23-fixed: Sharpe 1.202, CAGR 47.8%, MDD 43.9%, 197 trades
  - Benchmark (E5): Sharpe 1.432, CAGR 60.0%, MDD 41.6%, 199 trades
  - ΔSharpe: -0.229 (FAIL G0)
  - Hard-stop exits 56 (vs 0 in E5), churn 63%→72%
- **Gates**: 2/6 PASS (G3: MDD, G5: PSR)
- **Verdict**: **REJECTED** — pullback multipliers increase hard stops and churn, degrading all return metrics.

### 61. X24: Trail Arming Isolation
- **Script**: `research/x24/benchmark.py`
- **Results**: `research/x24/x24_results.json`, `research/x24/x24_report.md`
- **Date**: 2026-03-10
- **Hypothesis**: Arm trail stop only after price moves k×ATR from entry, isolating confirmed trends.
- **Results**:
  - E5+ARM(1.5): Sharpe 1.365, CAGR 57.9%, MDD 45.5%, 180 trades
  - Benchmark (E5): Sharpe 1.432, CAGR 60.0%, MDD 41.6%, 199 trades
  - ΔSharpe: -0.067 (FAIL G0)
  - 53 never-armed entries, trend-exit count 16→53
  - k-sweep peak at k=2.0 (Sh 1.420, still -0.012 vs E5)
- **Gates**: 2/6 PASS (G3: MDD, G5: PSR)
- **Verdict**: **REJECTED** — trail arming creates large never-armed population with degraded exit quality.

### 62. X25: Volume/TBR Entry Filter Lab
- **Script**: `research/x25/code/` (phases 0-4)
- **Results**: `research/x25/07_final_report.md`, `research/x25/manifest.json`
- **Date**: 2026-03-10
- **Hypothesis**: Volume/taker-buy-ratio features can tighten or replace VDO > 0 filter.
- **8-Phase Protocol**: Stopped at Phase 4 (Go/No-Go: STOP_VDO_NEAR_OPTIMAL)
- **Key Evidence**:
  - All 5 volume/TBR entry features fail separation tests (p > 0.39, |rank-biserial| < 0.08)
  - TBR non-stationary (3-6 month half-cycles of sign oscillation)
  - MI(ΔU; V_t | P_t) ≤ 2% of win/lose variance
  - VDO marginal (p=0.086, d~0.29) but below MDE=0.406 — truncation artifact
- **Verdict**: **KEEP_VDO** — VDO is near-optimal; no volume feature improves on it.

### 63. X26: Flat Period Mean-Reversion
- **Script**: `research/x26/code/` (phases 1-4)
- **Results**: `research/x26/04_formalization.md`, `research/x26/manifest.json`
- **Date**: 2026-03-10
- **Hypothesis**: VTREND flat periods (57.4% of time) exhibit exploitable mean-reversion.
- **8-Phase Protocol**: Stopped at Phase 4 (Go/No-Go: STOP_FLAT_PERIODS_ARE_NOISE)
- **Key Evidence**:
  - Per-period VR(2) = 0.82 (p<0.0001) but bar-level ρ(1) = -0.054 (4.4× smaller)
  - Class A (single-bar contrarian): gross +2.9 bps, 17× below 50 bps cost
  - Class B (range reversion): best +9.1 bps at k=5 (p=0.088), reverses at k=20 (-27.9 bps)
  - Class C (VR-conditional filter): VR(k) zero correlation with trade return (ρ=0.053, p=0.515)
  - ALL 3 classes underpowered (|d|/MDE = 0.23 to 0.92)
- **Verdict**: **STOP_NOISE** — mean-reversion exists but is economically negligible vs transaction costs.

### 64. X27: Alternative Mechanism Search (Breakout vs EMA Crossover)
- **Script**: `research/x27/code/` (phases 1-7)
- **Results**: `research/x27/08_final_report.md`, `research/x27/phase7_results.json`, `research/x27/manifest.json`
- **Date**: 2026-03-11
- **Hypothesis**: Breakout or other entry mechanisms can beat VTREND's EMA crossover.
- **8-Phase Protocol**: Full 8 phases completed.
- **Candidates**:
  - Cand01 (breakout + ATR trail): Sharpe 0.907, CAGR 38.6%, MDD 41.4%, 70 trades, **0% churn**
  - Cand02 (breakout + ATR trail + D1 EMA21): Sharpe 0.920, redundant D1 filter
  - Cand03 (ROC threshold + ATR trail): Sharpe 0.450, HOLD
  - Benchmark (E5+EMA21D1): Sharpe 1.084, CAGR 58.2%, MDD 52.6%, 219 trades, 49% churn
- **Key Findings**:
  - Breakout eliminates churn entirely (0/70 vs benchmark 107/219 = 49%)
  - Alpha converges across mechanisms (Sh 0.91 ≈ Sh 1.08, same underlying phenomenon)
  - D1 regime filter redundant for breakout (blocked only 2/70 entries)
  - ALL entry types have >87% false positive rate; structural, not fixable
  - Breakout dominates only at >105 bps RT cost
- **Verdict**: **BENCHMARK_OPTIMAL** — VTREND EMA crossover still best mechanism below 105 bps cost.

### 65. X28: From-Scratch Algorithm Discovery
- **Script**: `research/x28/code/` (phases 1-7)
- **Results**: `research/x28/08_final_report.md`, `research/x28/manifest.json`, `research/x28/tables/`
- **Date**: 2026-03-11
- **Hypothesis**: From-scratch search (no prior assumptions) can discover algorithms beating E5+EMA1D21.
- **8-Phase Protocol**: Full 8 phases completed.
- **Candidates**:
  - Cand01 (EMA(20,90) + 8% fixed trail + D1 EMA(50)): **Sharpe 1.251**, CAGR 41.7%, MDD 52.0%, 39 trades
  - Cand02 (EMA(20,90) + composite exit + D1 EMA(50)): Sharpe 1.099, MDD 40.3%, 49 trades
  - Cand03 (60-bar breakout + ATR trail + D1 EMA(50)): Sharpe 0.888, MDD 45.0%, 110 trades
  - Benchmark (A_20_90 + Y_atr3, no filter): Sharpe 0.819, MDD 39.9%
  - All 3 SCREEN_PASS (9/9 research gates), Cand01 PRIMARY
- **Key Discoveries**:
  1. avg_loser is #1 Sharpe predictor (partial R²=0.306, p<1e-7)
  2. Churn has ZERO predictive power (p=0.76, partial R²=0.001)
  3. D1 EMA(50) filter +0.432 ΔSharpe, 98% is non-linear trade selection
  4. Volume features genuinely zero information (MI=0.006 bits, triple-confirmed)
  5. Prior art non-portable across codebases (Sh -0.424 vs claimed 1.08)
  6. Information concentrates at longer horizons (k=1: 0.013 → k=60: 0.034)
  7. Entry choice > exit choice for Sharpe variance
  8. All candidates negative Sharpe in bear regime (structural for long-only)
- **vs VTREND E5+EMA1D21**: Cand01 (Sh 1.251) < E5+EMA1D21 (Sh 1.432) on ALL major metrics
- **Verdict**: **SCREEN_PASS** — valid algorithm but confirms VTREND E5+EMA1D21 superiority.

---

## XII. STACKING & FRACTIONAL ACTUATOR (X29-X30)

### 66. X29: Optimal Stack — Overlay Combinations
- **Script**: `research/x29/code/x29_benchmark.py`
- **Results**: `research/x29/x29_results.json`, `research/x29/x29_report.md`
- **Date**: 2026-03-11
- **Central question**: Does combining validated overlays (Monitor V2, X14D churn, X18 churn, Trail=4.5) improve E5+EMA1D21?
- **Combos**: 12 strategies (Base, Base+T45, X14D, X14D+T45, X18, X18+T45, Mon, Mon+T45, Mon+X14D, Mon+X14D+T45, Mon+X18, Mon+X18+T45) × 9 costs
- **Key findings**:
  - S07 (Mon) best full-sample Sharpe 1.733 (+0.131 vs Base) at 25 bps
  - S09 (Mon+X14D) best MDD 31.1% and Calmar 2.354
  - Trail=4.5 always hurts Sharpe (every T45 variant worse)
  - Churn filters hurt at 25 bps: X14D Sh 1.462, X18 Sh 1.589, both < Base 1.602
  - X14D×T45 synergy +0.275 (penalties partially cancel, still < Base)
  - Mon approximately additive (interactions near zero)
- **Gates**: T0 PASS (Mon beats Base at all 9 costs), T1 WARN (X14D×T45 interaction >0.10), T2 PASS (Mon+X14D/X18 WFO 75%), **T3 FAIL** (best P(d_sharpe>0) = Mon 45.8% < 55%)
- **Verdict**: At 25 bps, no combination reliably improves Base per X29 criteria. Mon V2 best single overlay but P(d>0)=45.8% (inconclusive). Mon+X14D best for MDD/Calmar, Mon+X18 WFO 75%.
  **Updated (2026-03-13)**: X33 measured cost 17 bps. At this cost churn filters are economically negative (X22 crossover >35 bps). Mon V2 uncertain (WFO 2/8 instability). Deploy Base without overlays; arm X18 for cost >35 bps.

### 67. X30: Fractional Actuator — Partial Exit at Trail Stop
- **Script**: `research/x30/code/x30_signal.py`, `x30_actuator.py`, `x30_validate.py`
- **Results**: `research/x30/tables/validation_summary.json`
- **Date**: 2026-03-11
- **Central question**: Can partial exit (keep fraction of position at trail stop) outperform full exit, using churn signal for sizing?
- **4-Phase Protocol**: Signal anatomy → Actuator design → Validation → Synthesis
- **Candidates**: discrete_pf90, B2_mf60, B2_mf80
- **Key findings**:
  - Signal preserved (KS p=0.296), but no tradable edge
  - Best (discrete_pf90): WFO 2/4 (50%), bootstrap P(d_sharpe>0)=43.6%, median d_sharpe=-0.017
  - B2_mf60/B2_mf80: bootstrap P(d>0)=30.8%/34.0% — worse than coin flip
  - Permutation p=1.0, effect d=-0.207 — no detectable signal
  - MDD improves (P(d_mdd<0) up to 74.4%) but Sharpe degrades
- **Gates**: G2 FAIL, G3 FAIL
- **Verdict**: **REJECT** — partial exit degrades risk-adjusted returns. Confirms X19 finding: static suppress (full exit) strictly dominates fractional actuators.

---

## XIII. FINAL CLOSURE STUDIES (X31-X32, 2026-03-12)

### 68. X31-A: D1 Regime Exit — Mid-Trade D1 EMA Flip
- **Script**: `research/x31/code/x31a_regime_exit.py`
- **Results**: `research/x31/results/`
- **Date**: 2026-03-12
- **Central question**: Should E5+EMA1D21 exit when D1 EMA(21) flips bearish mid-trade?
- **Key findings**:
  - D1 EMA(21) flips during 35/199 trades (17.6%)
  - Timing: median 5 bars (20h) earlier than trail stop
  - Per-trade impact: loser benefit +2.13% vs winner cost -10.39%
  - Selectivity ratio 0.21 << 1.5 threshold
  - Same fundamental constraint as X5/X10/X23: fat-tail alpha concentration (top 5% = 129.5% of profits)
- **Verdict**: **STOP** — selectivity 0.21, any mid-trade exit risks cutting winners

### 69. X31-B: Re-entry Barrier Oracle
- **Script**: `research/x31/code/x31b_reentry_oracle.py`
- **Results**: `research/x31/results/`
- **Date**: 2026-03-12
- **Central question**: What is the ceiling for re-entry filtering (blocking bad re-entries after exit)?
- **Key findings**:
  - Oracle ΔSharpe: +0.033 (15bps), +0.038 (20bps), +0.026 (25bps) — all below +0.08 GO threshold
  - Anti-oracle: blocking good re-entries costs -0.204 Sharpe → error cost 8.1x benefit per event
  - Feature separability: AUC ≈ 0.5 for all features except bars_held_prev (0.357, p=0.038)
  - G3 PASS: top-3 concentration 20.9%. G4 PASS: LOYO stable (worst +0.019, 2022)
- **Verdict**: **STOP** — oracle ceiling too low (+0.038 < +0.08). Closure due to economic ceiling, not model quality.

### 70. X32: VP1 (VTREND-P1) Research — Full Comparison
- **Script**: `research/x32/` (3 branches: a_vp1_baseline, b_variants, c_comparison)
- **Results**: `research/x32/c_comparison/results/comparison_report.md`
- **Date**: 2026-03-12
- **Central question**: Does VP1 (Phase 1 performance-dominant leader) or any variant beat E5+EMA1D21?
- **Strategies tested**:
  - VP1: Original spec (slow=140, trail=2.5, d1_ema=28, standard Wilder ATR, prevday D1, per-bar VDO)
  - VP1-E5exit: VP1 structure + RATR only
  - VP1-FULL: VP1 structure + all E5 parameters (slow=120, trail=3.0, d1_ema=21, RATR)
  - E5+EMA1D21: Current primary (control)
- **Key findings (harsh, 50 bps RT)**:
  - VP1 Sh 1.452, VP1-E5exit Sh 1.488, VP1-FULL Sh 1.461, E5+EMA1D21 Sh 1.430
  - All VP1 variants beat E5+EMA1D21 FULL-SAMPLE but ALL FAIL validation:
    - VP1, VP1-E5exit: holdout FAIL (underperform E0 in 2024-2026)
    - VP1-FULL: WFO FAIL (Wilcoxon p=0.125)
  - RATR is single biggest improvement: VP1→VP1-E5exit = -3.88 pp MDD, +0.036 Sharpe
  - VP1 parameter set (slow=140, trail=2.5, d1_ema=28) overfits earlier regimes
  - VP1 wins 6/8 WFO windows (2022-2024) but loses last 2 (2025)
  - CHOP regime: VP1 Sh 0.60 vs E0 Sh 1.58 — slow=140 whipsaws
- **Transfer analysis**: 3 VP1 structural features (prevday D1, per-bar VDO, anomaly skip) have negligible impact on BTCUSDT. VP1-FULL (+0.031 Sharpe) is underpowered/inconclusive. No transfer warranted.
- **Evaluation**: Full 17-suite validation pipeline for all 3 VP1 variants
- **Verdict**: **CLOSED** — E5+EMA1D21 remains PRIMARY. No VP1 variant achieves PROMOTE.

---

## XIV. EXECUTION COST & METHODOLOGY REFORM (2026-03-13)

### 71. X33: State-Dependent Execution Cost Analysis
- **Script**: `data-pipeline/fetch_binance_aggtrades.py` (downloader), `research/x33/analyze_execution_cost.py` (analysis)
- **Results**: `research/x33/results/cost_summary.md`, `research/x33/results/cost_per_signal.csv`
- **Data**: `research/x33/aggtrades_windows.parquet` (32M aggTrades rows, 372 signals)
- **Date**: 2026-03-13
- **Central question**: What is the REAL execution cost at signal moments? Is there entry/exit cost asymmetry?
- **Method**: Downloaded Binance aggTrades for all 372 entry+exit signals (API for 2022+, Vision daily zips for 2019-2022). Computed effective spread (±1 min window), VWAP slippage by order size ($10k/$50k/$100k), entry vs exit asymmetry.
- **Key findings**:
  - Effective spread: entry median 0.28 bps, exit median 0.33 bps (ratio 1.17x — near symmetric)
  - VWAP slippage: minimal up to $100k (incremental < 1 bps)
  - Total cost per side (commission + spread/2 + slippage): entry 8.1 bps, exit 8.0-8.1 bps
  - **Median round-trip = 16.8 bps**, P75 = 19.0 bps
  - Entry/exit asymmetry is negligible on BTC/USDT (highest liquidity pair in crypto)
  - Signal moments are NOT significantly more expensive than average (contradicts prior hypothesis)
- **X22 re-evaluation at measured cost**:
  - At 17 bps: X18 ΔSh ≈ -0.03 → skip (economic condition: crossover ~35 bps unmet)
  - At 17 bps: X14D ΔSh ≈ -0.17 → skip (crossover ~70 bps far from measured cost)
  - Mon V2: cost-invariant → economic layer does not resolve; remains UNCERTAIN (WFO 2/8)
- **Production recommendation**: Deploy E5+EMA1D21 without overlays at measured cost. Arm X18 in code, activate if live cost measurement exceeds 35 bps RT.
- **Verdict**: **DONE** — empirical cost measurement validates X22 crossover analysis.

### Methodology Reform (2026-03-13)
- **Trigger**: Systematic review found 6 reasoning errors in overlay decision communication
- **Errors**: (1) P(d>0) conflated with p-value, (2) underpowered called "noise", (3) independence assumption in probability multiplication, (4) component p-values used to reject overlays, (5) ad-hoc DOF penalty formula, (6) X29 conclusion overstated
- **Corrections**: Multi-layer evidence framework (methodology.md §12), terminology discipline (§8c), bootstrap semantics (§8a), test type separation (§8b)
- **Binding principle**: No single gate has promote/reject authority (Report 21). Overlay skip decisions must state specific reason: economic condition unmet, temporal instability, or statistical rejection — never "noise".

### 72. X37 Branch A: x37v4 macroHystB vs E5_ema21D1
- **Code**: `research/x37/branches/a_v4_vs_e5_fair_comparison/code/` (v4_strategy.py, helpers.py, run_*.py)
- **Results**: `research/x37/branches/a_v4_vs_e5_fair_comparison/results/`
- **Report**: `research/x37/branches/a_v4_vs_e5_fair_comparison/REPORT.md`
- **Date**: 2026-03-17
- **Central question**: Is V4 macroHystB (3-feature hysteresis with yearly threshold calibration) superior to E5_ema21D1 at fair 20 bps RT cost?
- **Method**: 4-phase comparison — (1) V4 rebuild as v10 Strategy, (2) acceptance test vs frozen spec, (3) 12-technique validation suite (backtest, WFO head-to-head, paired bootstrap, cost sweep, regime, sensitivity, DSR, drawdown, lookahead), (4) verdict generation.
- **Key findings**:
  - V4 (x37v4): Sharpe 1.865, CAGR 67.1%, MDD 23.9%, 51 trades, WR 58.8%, PF 6.27
  - E5: Sharpe 1.607, CAGR 69.0%, MDD 35.4%, 162 trades, WR 44.4%, PF 1.90
  - V4 wins Sharpe (+16.1%) and MDD (−32.5% relative). E5 wins CAGR (+2.8%).
  - Paired bootstrap: P(V4>E5) = 93.6% (full period, block=20).
  - WFO head-to-head: V4 wins 5/7 valid windows, 2/3 power-only. But n=3 < min 6 for Wilcoxon → **underpowered**, TIE.
  - Cost: V4 Sharpe > E5 at ALL cost levels (10-100 bps). No crossover found.
  - Sensitivity: V4 spread 0.535 > E5 0.413 — V4 more fragile.
  - V4 acceptance test: ALL PASS (thresholds exact match, 51/51 trade path match).
- **Why not promoted**: (1) WFO underpowered (insufficient power windows), (2) ~10 params vs 4 (higher DOF), (3) yearly recalibration = implicit in-sample dependence, (4) only 51 trades (weak statistical power), (5) wider sensitivity spread.
- **Verdict**: **V4_COMPETITIVE** (3/4 dimensions, WFO TIE due to underpowered). NOT promoted over E5_ema21D1.
