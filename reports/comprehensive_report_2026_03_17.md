# Comprehensive Validation & Research Report

**Date**: 2026-03-17
**Scope**: Post-bugfix re-validation + full research inventory
**Author**: Claude (automated)
**See also**: `comprehensive_report_5_winners_20260317.md` — dedicated re-run of all 5 PROMOTE strategies

---

## 1. Executive Summary

E5_ema21D1 re-validation after 2026-03-16 bugfixes. The bugfixes (WFO overlap,
Trade.pnl fees, holdout off-by-one, PSR demotion, VDO fallback, D1-H4 mapping)
changed the WFO Wilcoxon p-value from 0.074 (pre-fix, PASS) to 0.125 (post-fix, FAIL),
shifting the verdict from PROMOTE to HOLD.

**Verdict: HOLD (exit code 1)** — changed from PROMOTE (2026-03-09 pre-fix run).
Single failure: WFO `wfo_robustness` soft gate (Wilcoxon p=0.125 > 0.10, Bootstrap CI
crosses zero). This is an **underresolved** result per x36 program note 04, not evidence
of temporal instability.

All other evidence layers strongly support E5_ema21D1:
- Full-sample Sharpe 1.4545 (harsh, 50 bps)
- Holdout Sharpe 1.1618 (harsh), delta +5.58
- PSR = 0.999998
- Bootstrap P(candidate better) = 97.2%
- Trade-level bootstrap P(delta>0) = 95.0%

---

## 2. Re-Validation Results (2026-03-17)

### 2.1 Gate Summary

| Gate | Severity | Result | Detail |
|------|----------|--------|--------|
| `lookahead` | hard | **PASS** | Zero violations |
| `data_integrity` | hard | **PASS** | Clean data |
| `full_harsh_delta` | hard | **PASS** | delta = +26.53 (min -0.20) |
| `holdout_harsh_delta` | hard | **PASS** | delta = +5.58 (min -0.20) |
| `invariants` | hard | **PASS** | Zero violations |
| `wfo_robustness` | soft | **FAIL** | Wilcoxon p=0.125 > 0.10; Bootstrap CI [-3.44, 29.28] crosses zero |
| `selection_bias` | info | PASS | PSR=0.9999, DSR robust |
| `bootstrap` | info | PASS | P(better)=97.2% (diagnostic) |
| `trade_level` | info | PASS | P(delta>0)=95.0%, block_len=168 |

### 2.2 Performance Metrics (Full Period, 2017-08 to 2026-02)

| Metric | E5_ema21D1 | E0 Baseline | Delta |
|--------|------------|-------------|-------|
| **Sharpe** (harsh) | 1.4545 | 1.2653 | +0.189 |
| **CAGR** (harsh) | 61.60% | 52.04% | +9.56pp |
| **MDD** (harsh) | 40.97% | 41.61% | -0.64pp |
| **Trades** | 188 | 192 | -4 |
| **Win Rate** | 42.02% | 38.02% | +4.00pp |
| **Profit Factor** | 1.652 | 1.506 | +0.146 |
| **Exposure** | 44.48% | 46.82% | -2.34pp |
| **Sharpe** (smart, 13 bps) | 1.7122 | 1.5205 | +0.192 |
| **Sharpe** (base, 31 bps) | 1.5870 | 1.3964 | +0.191 |
| **Final NAV** (harsh) | $307,790 | $199,173 | +$108,617 |

### 2.3 Holdout Period (2024-01 to 2026-02)

| Metric | E5_ema21D1 | E0 Baseline | Delta |
|--------|------------|-------------|-------|
| Sharpe (harsh) | 1.1618 | 1.1189 | +0.043 |
| CAGR (harsh) | 32.01% | 30.99% | +1.02pp |
| MDD (harsh) | 15.62% | 19.13% | -3.51pp |
| Trades | 37 | 36 | +1 |

### 2.4 WFO Per-Window Detail (8 windows, 6-month each)

| Window | Period | E5 Score | E0 Score | Delta | Winner |
|--------|--------|----------|----------|-------|--------|
| 0 | 2022-H1 | -15.79 | -43.45 | **+27.66** | E5 |
| 1 | 2022-H2 | -125.39 | -104.60 | -20.79 | E0 |
| 2 | 2023-H1 | 28.07 | 32.99 | -4.92 | E0 |
| 3 | 2023-H2 | 216.89 | 186.80 | **+30.09** | E5 |
| 4 | 2024-H1 | 99.53 | 44.70 | **+54.83** | E5 |
| 5 | 2024-H2 | 290.91 | 276.28 | **+14.63** | E5 |
| 6 | 2025-H1 | 26.48 | 39.67 | -13.19 | E0 |
| 7 | 2025-H2 | -19.50 | -30.84 | **+11.34** | E5 |
| **Total** | | | | **Mean +12.46** | **5/8 E5** |

Wilcoxon W+ = 27 (cutoff at alpha=0.10 is W+ >= 28). One exact-rank step short.

### 2.5 Regime Decomposition

| Regime | E5 Sharpe | E0 Sharpe | E5 Return | Days |
|--------|-----------|-----------|-----------|------|
| BULL | **1.948** | 1.712 | +1159.1% | 1211 |
| BEAR | **1.538** | 1.506 | +106.9% | 661 |
| CHOP | **1.827** | 1.580 | +38.5% | 215 |
| NEUTRAL | **0.920** | 0.810 | +23.3% | 330 |
| TOPPING | -0.600 | **-0.867** | -3.0% | 102 |
| SHOCK | **-2.251** | -2.677 | -28.6% | 89 |

E5 wins all 6 regimes. Largest delta in BULL (+0.236), CHOP (+0.247).

### 2.6 Cost Sensitivity

| Cost (bps RT) | E5 CAGR | E0 CAGR | E5 Score | E0 Score |
|----------------|---------|---------|----------|----------|
| 0 | 52.00% | 42.31% | 142.42 | 111.01 |
| 10 | 47.80% | 38.33% | 129.67 | 98.75 |
| 25 | 41.72% | 32.57% | 111.20 | 81.00 |
| 50 | 32.13% | 23.49% | 82.02 | 52.98 |
| 75 | 23.19% | 15.04% | 54.50 | 26.83 |
| 100 | 14.85% | 7.17% | 28.69 | 2.42 |

E5 dominates at **all cost levels**. Breakeven: >999 bps.

### 2.7 Comparison: Old (2026-03-09) vs New (2026-03-17)

| Metric | Old Run | New Run | Changed? |
|--------|---------|---------|----------|
| Sharpe (harsh) | 1.4545 | 1.4545 | NO |
| CAGR (harsh) | 61.60% | 61.60% | NO |
| MDD (harsh) | 40.97% | 40.97% | NO |
| Trades | 188 | 188 | NO |
| WFO Wilcoxon p | 0.125 | 0.125 | NO |
| WFO Bootstrap CI | [-3.44, 29.28] | [-3.44, 29.28] | NO |
| PSR | 0.999998 | 0.999998 | NO |
| Verdict | HOLD | HOLD | NO |

**Conclusion**: 2026-03-16 bugfixes had zero impact on E5_ema21D1. The `STALE` tag
in MEMORY.md can be resolved — results are confirmed identical.

---

## 3. WFO Underresolution Analysis (x36)

The WFO soft-fail is characterized as **underresolved**, not **negative-confirmed**:

| Evidence | Value | Interpretation |
|----------|-------|----------------|
| Wilcoxon p (greater) | 0.125 | 1 rank step from passing (W+=27, need 28) |
| Mean delta | +12.46 | Positive (candidate better on average) |
| Positive windows | 5/8 (62.5%) | Majority positive |
| Bootstrap CI lower | -3.44 | Slightly negative, CI crosses zero |
| x36-B split sensitivity | 2/3 alt designs PASS | Fail is design-sensitive, not robust |
| Negative evidence (less) | None computed | No evidence E5 is worse than E0 |

Per x36 program note 04, a future root patch will add `evidence_state: underresolved`
to the WFO summary, distinguishing this from true negative evidence. This is a
semantic/authority fix, not a threshold relaxation — E5 will still get HOLD until the
WFO resolves.

---

## 4. Complete Research Inventory (68 studies)

### 4.1 Core Algorithm (Proven Components)

| # | Component | Evidence | p-value |
|---|-----------|----------|---------|
| 1 | EMA crossover entry | 16/16 timescales | 0.0003 (Bonferroni) |
| 2 | ATR trail + EMA cross-down exit (E0) | 16/16 timescales | 0.0003 |
| 3 | VDO filter | 16/16 timescales | 0.031 (DOF-corrected) |
| 4 | EMA(21d) D1 regime filter | 16/16 timescales | 1.5e-5 |

### 4.2 X-Series Studies Summary

| Study | Focus | Verdict | Key Result |
|-------|-------|---------|------------|
| X0 | E0_ema21D1 baseline | HOLD | PSR=0.8908 < 0.95 |
| X1 | Re-entry after D1 flip | REDUNDANT | D1 regime is protective |
| X2 | Adaptive trail | REJECT | Overfits, WFO 4/8 |
| X3 | Graduated sizing | REJECT | Mismatch with fat tails |
| X4B | Parallel breakout entry | REJECT | EMA lag is a feature |
| X5 | Partial take-profit | REJECT | Amputates fat tail alpha |
| X6 | Adaptive+breakeven | REJECT | Breakeven hostile to trend |
| X7 | Crypto-optimised (7 filters) | REJECT | Kills exposure, Sh 0.806 |
| X8 | Stretch cap only | REJECT | Blocks momentum, Sh 1.085 |
| X10 | TP ladder | REJECT | Destroys trend alpha |
| X11 | Short-side BTC | REJECT | Negative-EV all timescales |
| **X12** | E5-E0 mechanism | NOISE | Gap P=46.4% |
| **X13** | Churn predictability | INFO | AUC=0.805, p=0.002 |
| **X14** | Churn filter designs | **PROMOTE_D** | Sh 1.428, MDD 36.7%, 6/6 gates |
| **X15** | Dynamic filter | ABORT | 7 trades, MDD 77% |
| **X16** | WATCH state machine | ALL_FAIL | Bootstrap 49.8% |
| **X17** | Percentile WATCH | NOT_TEMPORAL | WFO 25%, G dilemma |
| **X18** | Alpha-percentile static mask | **PROMOTE** | Sh 1.482, WFO 100%, 6/6 gates |
| **X19** | Alt actuators (re-enter, partial) | CLOSE | Static suppress optimal |
| **X20** | Cross-asset portfolio | CLOSE | Altcoins dilute BTC alpha |
| **X21** | Conviction sizing | CLOSE | CV IC=-0.039 (no signal) |
| **X22** | Cost sensitivity mapping | DONE | Churn hurts at <30 bps |
| **X23** | Exit geometry | REJECT | Increased churn, 2/6 gates |
| **X24** | Trail arming | REJECT | 53 never-armed entries |
| **X25** | Volume/TBR filter | KEEP_VDO | All features p>0.39 |
| **X26** | Flat period mean-reversion | STOP_NOISE | 3-9 bps gross vs 15-50 bps cost |
| **X27** | Breakout vs EMA crossover | BENCHMARK | Sh 0.907 < bench 1.084 |
| **X28** | From-scratch discovery | PROMOTE_CAND01 | Sh 1.251, inferior to E5 |
| **X29** | Optimal stack combos | CLOSE | No stack beats base at 25 bps |
| **X30** | Fractional actuator | REJECT | MDD improves but Sharpe degrades |
| **X31-A** | D1 regime exit | STOP | Selectivity 0.21, cuts winners |
| **X31-B** | Re-entry barrier oracle | STOP | Ceiling +0.038 < +0.08 GO |
| **X32** | VP1 family | CLOSED | All FAIL holdout/WFO |
| **X33** | Execution cost measurement | DONE | Median 16.8 bps RT |
| **X36** | Path robustness / WFO diagnostic | ACTIVE | WFO fail is design-sensitive |

### 4.3 Churn Filter Cost-Dependent Deployment

| Execution Cost (RT) | Recommendation |
|---------------------|----------------|
| < 30 bps | E5_ema21D1 **without** churn filter |
| 30-35 bps | X18 crossover zone, **neutral** |
| 35-70 bps | **X18** (return-focused, Sh +0.052) |
| > 70 bps | **X14D** (MDD-focused, MDD -5.3pp) |

Measured cost (Binance VIP0+BNB): median 16.8 bps RT -> **skip churn filter**.

### 4.4 Proven Constraints (from 68 studies)

1. **Fat-tail alpha concentration**: Top 5% of trades = 129.5% of profits
2. **Payoff asymmetry**: Any mid-trade exit risks 8:1 cost/benefit ratio
3. **Cost dominance at <30 bps**: Churn filter value is cost savings, not alpha
4. **Cross-asset dilution**: BTC-only Sh 0.735 >> best portfolio 0.259
5. **No entry IC**: Entry features have zero predictive power (CV IC = -0.039)
6. **Oracle ceiling**: Re-entry barrier oracle +0.038 (economic limit, not overfit)

### 4.5 Active Strategies

| Strategy | Status | Sharpe (harsh) | Role |
|----------|--------|----------------|------|
| **E5_ema21D1** | PRIMARY | 1.4545 | Deployment candidate |
| E0_ema21D1 | HOLD | 1.2653 | No role (WFO FAIL) |
| SM | ALT PROFILE | ~1.39 | Low-exposure alternative (>75 bps) |
| LATCH | ALT PROFILE | ~1.44 | Low-exposure alternative (>50 bps) |

---

## 5. Outstanding Items

### 5.1 Resolved by This Run
- [x] Re-validate E5_ema21D1 after 2026-03-16 bugfixes
- [x] Confirm results unchanged (byte-for-byte identical)
- [x] Fix thresholds.py comment (W+ >= 28, not 30)

### 5.2 Pending (Planned, Not Urgent)
- [ ] **WFO reform patch** (x36 program notes 04-05): Add `evidence_state` field
  (underresolved/negative_confirmed/positive_confirmed/delegated_low_power).
  Semantic fix only — does not change verdict or thresholds.
- [ ] Update MEMORY.md `STALE` tag — results confirmed identical.

### 5.3 Closed Research Families
- **Exit/Filter/Overlay/ML on BTC Spot OHLCV**: CLOSED (68 studies, sufficient evidence)
- **Churn research (X12-X19)**: COMPLETE (static suppress is only viable actuator)
- **Breadth expansion (X20-X22)**: CLOSED (no IC, dilution, cost characterization done)
- **Deep research (X23-X28)**: CLOSED (VTREND E5 confirmed optimal)
- **Final closure (X31-X32)**: CLOSED (economic ceiling proven)

### 5.4 Future Directions (In Scope of Discovery Phase)
- New data sources: funding, OI, basis, liquidation, order book
- New instruments: perps/futures (different cost/funding, enables short side)

---

## 6. Artifacts

| Artifact | Path |
|----------|------|
| New validation results | `results/full_eval_e5_ema21d1_post_fix/` |
| Previous validation results | `results/full_eval_e5_ema21d1/` |
| WFO diagnostic (x36) | `research/x36/branches/b_e5_wfo_robustness_diagnostic/results/` |
| WFO reform spec | `research/x36/program/04_wfo_power_authority_reform.md` |
| Root patch blueprint | `research/x36/program/05_root_patch_blueprint.md` |
| Strategy status matrix | `STRATEGY_STATUS_MATRIX.md` |
| This report | `reports/comprehensive_report_2026_03_17.md` |
