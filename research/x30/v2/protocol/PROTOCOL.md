# X30-V2: ML Exit Optimization — Reformed Protocol

**Status**: DRAFT — awaiting variant definition
**Methodology**: Report 21 compliant (2026-03-13 reform)
**Base**: VTREND E5+EMA1D21 (primary, Sharpe ~1.43 @ 50bps, ~1.60 @ 25bps)

---

## 0. Integrity & Leakage Prevention (binding for all phases)

These rules apply to ALL code in V2. Violations → automatic REJECT, no override.

### 0a. Integrity violations (hard reject, non-negotiable)
- **Lookahead / future leakage**: No feature may use information from after the prediction point.
- **Post-hoc thresholding**: Thresholds and decision rules must be selected within training folds,
  never on test/OOS data.
- **Full-sample transforms before CV/WFO**: Fitting any transform (scaler, calibrator, feature
  selector) on all data before splitting is leakage.

### 0b. Mandatory pipeline within each fold
```
Per WFO/CV fold:
  1. Split: train / test (temporal, no shuffle)
  2. Impute (if needed): fit on train, transform both
  3. Scale: fit StandardScaler on train, transform both
     → NEVER fit scaler on full data during research
     → Deployment freeze (fit on all data) is a SEPARATE pipeline,
        documented in resource/spec/master_reproducibility_spec.md.
        Do NOT copy deployment logic into research CV/WFO.
  4. Fit model: train on scaled train data
  5. Calibrate (conditional): fit calibrator on train ONLY IF actuator
     uses calibrated probabilities directly. If actuator uses ranking/percentile,
     calibration fitting is optional (adds variance without benefit).
     Calibration EVALUATION (ECE, reliability diagram) is always mandatory.
  6. Predict: apply to scaled test data
  7. Threshold: use threshold selected in step 4 (from train), not re-tuned on test
```

### 0c. Feature timestamping
Every feature must document its information boundary:
- Bar-level features (EMA, ATR, VDO): available at bar close time
- Trade-context features (bars_held, dd_from_peak): available at trail-stop event time
- Derived features: must not use future bars relative to prediction point

---

## 1. V1 Priors (conditioned observations, not V2 constraints)

V1 produced 3 observations under V1's specific conditions (7 features, fractional actuator,
V1's data split). These are **priors to be aware of**, not binding constraints for V2.
V2 may find different results with different features, labeling, actuator, or regularization.

1. **Churn score IS discriminative** (V1 OOS AUC = 0.803) but discrimination alone
   did not translate to portfolio improvement in V1.
2. **V1's fractional actuator MDD benefit was 85% trivial** (exposure reduction, not timing).
   V2 must test whether its actuator avoids this failure mode.
3. **V1 found l1_ratio = 0.0 optimal** on V1's 7 features. This does NOT preclude
   V2 finding l1_ratio > 0 optimal with different features or labeling.
   V2 resource documents show a model with l1_ratio = 0.25 — V2 must evaluate
   regularization path independently.

## 2. V2 Design Space

> **[TO BE DEFINED]** — variant specifics TBD. This protocol provides the
> evaluation framework. The user will specify the exact mechanism.

Possible directions (non-exhaustive):
- Different actuator: delay exit instead of partial exit
- Different labeling: regime-aware targets, multi-horizon
- Different features: add V2-era features (funding, OI if available)
- Different threshold selection: WFO-nested α selection
- Combination with existing overlays (Mon V2)

---

## 3. Three Categories of Checks

Protocol distinguishes three categories. They are NOT interchangeable.

| Category | Nature | Failure consequence | Override? |
|----------|--------|--------------------|----|
| **Integrity violations** (§0) | Design flaws | Automatic REJECT | No |
| **Feasibility prerequisites** (Phase A) | Sample/model minimum viability | STOP — study cannot proceed meaningfully | No (must fix and re-run) |
| **Evidence layers** (Phase B-D) | Strength of empirical support | Weighed in multi-layer verdict | No single layer has veto |

This means: "No single **evidence layer** has veto" applies to Phase B-D evidence.
Integrity violations and feasibility prerequisites are NOT evidence layers — they are
prerequisites for the evidence to be meaningful.

---

## 4. Validation Checklist — 16 Techniques (mandatory)

V1 completed 9/16. V2 must complete ALL 16. Organized into 4 phases with early stopping.

### Phase A: Model Quality — Feasibility Prerequisites (7 techniques)

> Trả lời: "Model có sound không? Có thực sự học được pattern hay chỉ memorize data?"

| # | Technique | Question | Method | V1 | V2 |
|---|-----------|----------|--------|----|----|
| T01 | **Time-series CV** | Generalize qua thời gian? | K-fold expanding (train past → test future), AUC mỗi fold. Pipeline §0b mandatory. | ✓ | ✓ |
| T02 | **Discrimination** | Phân biệt được outcome? | ROC AUC, PR AUC, average_precision, precision@action_rate, lift@action_rate | ✓ | ✓ |
| T03 | **Calibration** | Score quality? | Brier score, ECE, reliability diagram. Evaluation mandatory; calibrator fitting conditional (§0b.5). | ✓ | ✓ |
| T04 | **Feature stability** | Model consistent qua thời gian? | Selection frequency (% folds feature active), sign consistency on active coefficients, coefficient dispersion after standardization | ~ | ✓ |
| T05 | **Feature ablation** | Mỗi feature đóng góp? | Drop-one-feature AUC delta. Note: with correlated features, low delta ≠ redundant (partner compensates). Report alongside permutation importance if available. | ✗ | **✓** |
| T06 | **Regularization path** | L1/L2 ratio optimal? | Grid search C × l1_ratio, CV AUC surface | ✓ | ✓ |
| T07 | **Sample adequacy** | Enough independent data for this model? | ESS, class support, EPV — see gate definition below | ✗ | **✓** |

#### T02 Discrimination — required outputs:
```
{
  "roc_auc": float,              // coarse screen
  "pr_auc": float,               // accounts for class imbalance
  "average_precision": float,    // area under PR curve
  "ap_over_prevalence": float,   // lift over random (AP / base_rate)
  "precision_at_action_rate": float,  // precision at chosen actuator threshold
  "lift_at_action_rate": float,       // lift at chosen actuator threshold
  "action_rate": float,               // fraction of events acted upon
  "base_rate": float                  // prevalence of positive class
}
```
Note: If actuator threshold is TBD, report precision/lift at P25, P50, P75 of score distribution.

#### T04 Feature stability — metrics:
```
Per feature, across WFO/CV folds:
  - selection_frequency: fraction of folds where |β| > 0 (for L1/Elastic Net)
  - sign_consistency: fraction of folds with same sign (among folds where feature active)
  - coeff_cv: coefficient of variation of standardized β across folds

Model-level:
  - rank_correlation: Spearman ρ of predictions between adjacent folds on overlapping data
    (if available), or on a held-out reference set
```

#### T07 Sample adequacy — gate definition:
```
{
  "ess_total": int,               // cluster-adjusted total ESS
  "effective_pos": int,           // effective positive-class count
  "effective_neg": int,           // effective negative-class count
  "n_features": int,              // raw feature count
  "df_proxy": float,              // effective degrees of freedom (see below)
  "epv_eff": float,               // min(effective_pos, effective_neg) / df_proxy
  "zone": "comfort / warning / stop"
}

df_proxy estimation (pragmatic, not pseudo-precise):
  - If model is sparse (l1_ratio > 0.3 and >20% coefficients zeroed):
      df_proxy = count of non-zero coefficients
  - If model is near-ridge (l1_ratio < 0.1 or negligible shrinkage observed):
      df_proxy = raw feature count (conservative)
  - Otherwise:
      df_proxy = count of coefficients with |β_standardized| > 0.01

  Do NOT use trace-of-hat-matrix unless implementation is verified and numerically stable.
  Describe observed shrinkage behavior in report, not just a number.
```

#### Phase A stop rules (feasibility prerequisites):
```
HARD STOP (study cannot proceed):
  - ESS_total < 50
  - min(effective_pos, effective_neg) < 20
  - EPV_eff < 5

HARD STOP (model cannot discriminate):
  - ROC AUC < 0.60 AND ap_over_prevalence < 1.5
  (Either metric alone is WARNING, not STOP.
   ROC < 0.60 alone: model may still have useful tail discrimination.
   AP/prev < 1.5 alone: model barely better than random even at action point.)

WARNING (proceed with caution):
  - EPV_eff 5 to <10 (warning zone — coefficients may be unstable)
  - ROC AUC < 0.60 but ap_over_prevalence >= 1.5 (tail-useful model)
  - ap_over_prevalence < 2.0 (weak lift)

COMFORT:
  - EPV_eff >= 10
  - ROC AUC >= 0.65 AND ap_over_prevalence >= 2.0
```

If STOP: write `verdict.json` with `"verdict": "REJECT"`, reason, and skip Phase B-D.

#### Phase A output:
```
phase_a_model_quality.json:
{
  "discrimination": { ... T02 outputs ... },
  "calibration": { "ece": float, "brier": float },
  "feature_stability": { ... T04 outputs ... },
  "feature_ablation": { "deltas": {"feat": delta_auc, ...}, "notes": "..." },
  "regularization": { "best_C": float, "best_l1_ratio": float, "cv_surface": [...] },
  "sample_adequacy": { ... T07 outputs ... },
  "phase_a_status": "proceed / warning / stop",
  "warnings": [...],
  "stop_reason": null / "string"
}
```

---

### Phase B: Strategy Impact — Evidence Layers (5 techniques)

> Trả lời: "Model có cải thiện strategy không? Discrimination → portfolio value?"
>
> V1 insight: AUC=0.803 nhưng permutation p=1.0. Discrimination ≠ portfolio value.
> Phase B detects whether V2 closes this gap.

| # | Technique | Question | Method | V1 | V2 |
|---|-----------|----------|--------|----|----|
| T08 | **WFO** (Walk-Forward) | Retrain + apply OOS thắng Base? | 4-fold expanding, retrain model per fold (pipeline §0b), ΔSh OOS | ✓ | ✓ |
| T09 | **Permutation test** (strategy-level) | ML score ordering adds strategy value? | Moving-block permutation by event order within WFO OOS fold (see below) | ✓ | ✓ |
| T10 | **Cost sweep** | Thắng ở cost nào? | 9 cost levels (5, 10, 15, 17, 20, 25, 35, 50, 100 bps) | ✓ | ✓ |
| T11 | **Economic frontier** | Better than "just reduce f"? | ε-Pareto non-dominance vs Base(f) frontier (see below) | ✓ | ✓ |
| T12 | **Exposure attribution** | Thắng nhờ skill hay giảm exposure? | Decompose: ΔMdd = exposure_component + timing_component | ✓ | ✓ |

#### WFO fold definitions (same as V1, X18):
```
Fold 1: Train 2019-01 → 2021-06, OOS 2021-07 → 2022-12
Fold 2: Train 2019-01 → 2022-12, OOS 2023-01 → 2024-06
Fold 3: Train 2019-01 → 2024-06, OOS 2024-07 → 2025-06
Fold 4: Train 2019-01 → 2025-06, OOS 2025-07 → 2026-02

Per fold: full pipeline §0b (split → scale on train → fit → predict on test).
Threshold/decision rule: selected within training fold, frozen for OOS.
```

#### T09 Permutation test — single restricted null:
```
Method: Moving-block permutation by event order
  - Within each WFO OOS fold:
    1. Collect all trail-stop events with their scores
    2. Define block length: max(2, floor(n_events / 10))
    3. Permute score assignments using moving blocks of events
       (preserves local event clustering, breaks score↔outcome association)
    4. Apply FROZEN threshold/decision rule from training fold (do NOT re-tune)
    5. Run strategy with permuted scores → compute test statistic
  - Repeat 1000 times
  - p-value = fraction of permutations where test_statistic >= observed

This is the ONLY permitted null generator. Do not try multiple permutation schemes
and report the best one — that creates hidden DOF.
```

#### T11 Economic frontier — ε-Pareto non-dominance:
```
Base frontier construction:
  - Sweep f for Base strategy: f ∈ {0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40}
  - For each f: compute (MDD, Sharpe) at primary cost (25 bps)
  - Plot frontier: Sharpe vs MDD for Base at different f

Dominance test:
  - Candidate point: (MDD_cand, Sharpe_cand)
  - ε_sharpe = 0.02 (tolerance for Sharpe comparison)
  - ε_mdd = 1.0 pp (tolerance for MDD comparison)
  - Candidate is DOMINATED if there exists Base(f) such that:
      Base(f).Sharpe >= Candidate.Sharpe - ε_sharpe AND
      Base(f).MDD <= Candidate.MDD + ε_mdd
  - Dominated → strong negative evidence (complexity not justified)
  - Non-dominated → positive evidence (ML adds value beyond simple f adjustment)

Grid is for visualization. Dominance check is the decision-relevant output.
```

#### T12 Exposure attribution — reporting:
```
Report timing vs exposure decomposition as DIAGNOSTIC:
  - timing_pct and exposure_pct are informational
  - NOT a hard gate (removed: timing > 50% requirement)
  - If timing < 20%: strong warning — benefit is mostly trivial exposure reduction
  - Frontier test (T11) is the hard economic test, not the decomposition ratio
```

#### Phase B output:
```
phase_b_strategy_impact.json:
{
  "wfo": {
    "folds": [
      {"fold": 1, "base_sh": float, "cand_sh": float, "delta_sh": float, "win": bool},
      ...
    ],
    "win_rate": "X/4",
    "mean_delta_sh": float,
    "aggregate_oos_sharpe": float,
    "aggregate_oos_mdd": float
  },
  "permutation": {
    "real_score": float,
    "p_value": float,
    "n_permutations": 1000,
    "null_type": "moving-block event-order within WFO fold",
    "block_length": int
  },
  "cost_sweep": {
    "results": [{"cost_bps": int, "base_sh": float, "cand_sh": float, "delta_sh": float}, ...],
    "beats_base_count": "X/9",
    "crossover_bps": float / null,
    "at_17bps": {"delta_sh": float, "positive": bool}
  },
  "frontier": {
    "base_frontier": [{"f": float, "sharpe": float, "mdd": float}, ...],
    "candidate_point": {"sharpe": float, "mdd": float},
    "dominated": bool,
    "epsilon_sharpe": 0.02,
    "epsilon_mdd": 1.0
  },
  "exposure_attribution": {
    "mdd_from_exposure_pct": float,
    "mdd_from_timing_pct": float,
    "timing_warning": bool     // true if timing < 20%
  }
}
```

#### Phase B — WFO 0/4 handling:
```
WFO 0/4 = DEFAULT REJECT.
Override is permitted ONLY if a documented methodological defect is found
in the WFO run itself:
  ✓ Verified bug in WFO code (reproducible)
  ✓ Data split error (train/test overlap)
  ✓ Missing warmup in OOS period
  ✓ Feature leakage in fold pipeline

NOT valid override reasons:
  ✗ "OOS periods happened to be unfavorable market regimes"
  ✗ "Model wasn't optimized for OOS"
  ✗ "Other evidence layers are strong"

If override invoked: document proof of defect, fix defect, re-run WFO.
The new WFO result replaces the defective one — it is NOT ignored.
```

---

### Phase C: Robustness — Evidence Layers (4 techniques)

> Trả lời: "Kết quả có bền vững không? 2 năm tới có giữ được không?"

| # | Technique | Question | Method | V1 | V2 |
|---|-----------|----------|--------|----|----|
| T13 | **Jackknife** (leave-one-fold-out) | Kết quả phụ thuộc 1 giai đoạn? | Drop mỗi fold, tính lại full metric → count negative folds | ✗ | **✓** |
| T14 | **PSR** (Probabilistic Sharpe Ratio) | Sharpe > 0 đáng tin? | Bailey & López de Prado PSR, adjust for skew/kurtosis/sample size | ✗ | **✓** |
| T15 | **Paired bootstrap** (VCBB) | Thắng trên random paths? | 500 synthetic paths (block=60), paired ΔSh per path | ✓ | ✓ (diagnostic) |
| T16 | **DOF correction** | Overfit do test nhiều configs? | Count K configs → Holm/Bonferroni correction on best | ✗ | **✓** |

#### Jackknife design (T13):
```
6 jackknife folds (drop ~14 months each):
  JK1: drop 2019-01 → 2020-02, eval rest
  JK2: drop 2020-03 → 2021-04, eval rest
  JK3: drop 2021-05 → 2022-06, eval rest
  JK4: drop 2022-07 → 2023-08, eval rest
  JK5: drop 2023-09 → 2024-10, eval rest
  JK6: drop 2024-11 → 2026-02, eval rest

Per fold: retrain model on remaining data (pipeline §0b), compute ΔSh vs Base.
Report: count of folds where ΔSh < 0 (negative contribution).
```

#### PSR design (T14):
```
PSR = Prob(true Sharpe > 0) given observed Sharpe, skewness, kurtosis, sample size.
Compute on candidate's OOS return series (aggregate WFO OOS).
Report: PSR value.

PSR is a STRONG DIAGNOSTIC, not a hard promote gate:
  PSR >= 0.95 → strong support for promote
  PSR 0.90-0.95 → moderate support, note sample size limitation
  PSR < 0.90 → warning, investigate if sample-driven or real weakness
```

#### Bootstrap semantics (T15 — §8a binding):
```
P(d>0) is reported as DIAGNOSTIC ONLY:
  - "P(ΔSh>0) = XX.X% — directional resampling score"
  - NO comparison to α thresholds
  - NO automatic promote/reject based on this number alone
  - Present alongside other layers for human review
```

#### DOF correction (T16):
```
K = total number of candidate configurations evaluated in Phase B.
If K > 1:
  - Report raw best and Holm-adjusted significance
  - Bonferroni threshold = 0.05 / K
  - If only 1 config tested: no correction needed
If K > 10:
  - MANDATORY Holm correction
  - Report effective DOF (Nyholt M_eff if configs correlated)
```

#### Phase C output:
```
phase_c_robustness.json:
{
  "jackknife": {
    "folds": [
      {"fold": 1, "dropped": "2019-01 to 2020-02", "delta_sh": float, "negative": bool},
      ...
    ],
    "negative_count": "X/6",
    "stability": "stable / one-fold-dependent / unstable"
  },
  "psr": {
    "candidate_psr": float,
    "observed_sharpe": float,
    "skewness": float,
    "kurtosis": float,
    "n_bars": int,
    "assessment": "strong_support / moderate_support / warning"
  },
  "bootstrap": {
    "p_delta_sh_pos": float,
    "median_delta_sh": float,
    "mean_delta_sh": float,
    "p_delta_mdd_neg": float,
    "median_delta_mdd": float,
    "interpretation": "string"
  },
  "dof_correction": {
    "K_configs_tested": int,
    "correction_method": "none / Holm / Bonferroni",
    "raw_best_p": float,
    "corrected_p": float,
    "m_eff": float / null
  }
}
```

---

### Phase D: Consensus Verdict

> Trả lời: "Tất cả layers nói gì khi nhìn cùng nhau?"

| # | Technique | Question | Method | V1 | V2 |
|---|-----------|----------|--------|----|----|
| — | **Multi-layer consensus** | All layers coherent? | Human-reviewed integration of T01-T16 | ✗ | **✓** |

#### Phase D process:
```
1. Compile all 16 technique results from Phases A-C
2. Verify integrity (§0): no leakage, pipeline correct, timestamps valid
3. Check feasibility (Phase A): all prerequisites met
4. Assess evidence layers:
   - WFO: win rate, mean ΔSh, fold-by-fold pattern
   - Permutation: strategy-level signal strength
   - Cost sweep: cost-dependent or cost-invariant value?
   - Frontier: dominated by Base(f) or genuinely non-dominated?
   - Exposure attribution: timing vs exposure mix
   - Jackknife: temporal stability
   - PSR: confidence in Sharpe estimate
   - Bootstrap: directional diagnostic
5. Economic analysis:
   - At X33 measured cost (17 bps): positive or negative?
   - Cost crossover point?
   - Mechanism plausibility: why should this work?
   - Prior from V1/X16/X17/X19: how does V2 differ?
6. Human verdict with SPECIFIC reasoning:
   → Name each layer that supports / opposes
   → State which layers were decisive and why
   → No single evidence layer has veto
```

---

## 5. Consensus Definitions

### PROMOTE (strong expectation, all criteria weighed together):
- WFO ≥ 3/4 (strong expectation; 2/4 is insufficient for promote, see HOLD)
- JK ≤ 2/6 negative
- PSR ≥ 0.95 (strong diagnostic support, not absolute gate)
- Economic: positive at X33 measured cost (17 bps)
- Frontier: not dominated by Base(f) with ε-tolerance
- Permutation p ≤ 0.10 at strategy level
- NO single criterion is sufficient alone — human review confirms coherence
- If timing attribution < 20%: requires explicit justification why complexity is warranted

### HOLD if:
- Some layers positive, some ambiguous
- WFO 2/4 (regime-dependent — need more OOS data)
- Effect size in underpowered range (ΔSh < 0.15 per §8c)
- PSR 0.90-0.95 with short OOS sample
- More data needed to resolve

### REJECT if:
- WFO 0/4 (default reject — override only per §Phase B WFO 0/4 handling)
- WFO 1/4 (strong negative — only one temporal period works)
- Economic: negative at all realistic costs (5-35 bps)
- Frontier: clearly dominated by Base(f) (complexity adds no value)
- Multiple independent evidence layers point negative
- Permutation p ≥ 0.50 (no strategy-level signal)

---

## 6. Terminology Discipline (§8c binding)

| Term | When | Example |
|------|------|---------|
| Underpowered | ΔSharpe small relative to sample noise | ΔSh=0.06 with 186 trades |
| Inconclusive | Evidence neither confirms nor denies | WFO 2/4, bootstrap 52% |
| Cost-dependent | Effect sign changes with cost level | X18: negative <35 bps |
| Regime-dependent | Effect present in some periods only | Mon V2: WFO 2/8 |
| Rejected | Strong evidence of no value or harm | V1: permutation p=1.0 |

**NEVER**: "noise", "proven noise", "just noise" for small/underpowered effects.

## 7. Bootstrap P(d>0) Semantics (§8a binding)

- P(d>0) is a **directional resampling score**, NOT a p-value
- NO automatic promote/reject threshold
- It is ONE diagnostic among many — report alongside other layers
- Do NOT compare to α=0.05 or any significance level
- Prohibited claims (from Report 21):
  1. "P(d>0) = 62% means 62% probability of being better" — WRONG
  2. "P(d>0) < 55% → noise" — WRONG
  3. "P(d>0) > X% → promote" — WRONG
  4. Multiplying P(d>0) across overlays — WRONG

---

## 8. Anti-Overfitting Controls

1. **DOF budget**: Report K configs tested. K > 10 → mandatory Holm correction.
2. **WFO retrain**: Model retrained each fold with full pipeline §0b. Full-sample model is cheating.
3. **Nested threshold selection**: If α/percentile is a parameter, select within training fold.
4. **Economic frontier**: Must not be dominated by Base(f) — the simplest zero-DOF alternative.
5. **Prior from V1**: V1 REJECT at P=0.436 is the prior. V2 must overcome this.
6. **Prior from X16/X17/X19**: Delay/modify exit family all failed. V2 must explain why it differs.
7. **Pipeline integrity**: §0b enforced — scaler fit within fold, no full-sample transforms.

## 9. Comparison Requirements

### 9a. Primary comparison (the real bar)
- **vs Base E5+EMA1D21** (no overlay, zero DOF)
- At 25 bps AND at X33 measured cost (17 bps)

### 9b. Economic frontier benchmark
- **vs Base(f_sweep)**: ε-Pareto non-dominance test (T11)
- If dominated → complexity adds no value over adjusting position size

### 9c. Context comparisons
- vs V1 best (discrete_pf90): did V2 improve on V1?
- vs X14_D, X18 (binary suppress): is V2 actuator genuinely better?
- Same cost level (25 bps), same metrics

---

## 10. Reporting Template

### Per-candidate report:

```
Candidate: [name]
Mechanism: [one sentence — what it does and why it should work]

--- Phase A: Model Quality ---
T01 Time-series CV: AUC per fold = [...], pipeline §0b verified
T02 Discrimination: ROC AUC = X.XXX, PR AUC = X.XXX, AP/prev = X.X,
     precision@action_rate = X.XX, lift@action_rate = X.X
T03 Calibration: Brier = X.XXX, ECE = X.XXX
     Calibrator fitted: [yes/no — conditional on actuator design]
T04 Feature stability: selection_freq = [...], sign_consistency = [...]
     coeff_cv = [...], rank_correlation = X.XX
T05 Feature ablation: [most/least important, notes on correlated features]
T06 Regularization: best C = X.X, best l1_ratio = X.X
T07 Sample adequacy: ESS = XXX, eff_pos = XXX, eff_neg = XXX,
     df_proxy = X.X, EPV_eff = X.X, zone = [comfort/warning]

--- Phase B: Strategy Impact ---
T08 WFO: X/4 folds win, mean ΔSh OOS = +X.XXX
     Fold-by-fold: [F1: +/-, F2: +/-, F3: +/-, F4: +/-]
T09 Permutation: p = X.XXX (moving-block event-order, N=1000, block=X)
T10 Cost sweep: beats Base at X/9 costs, crossover = XX bps
     At 17 bps (X33): ΔSh = +X.XXX
T11 Frontier: [dominated / non-dominated] by Base(f), ε = (0.02, 1.0pp)
T12 Exposure attribution: XX% exposure, XX% timing
     [warning if timing < 20%]

--- Phase C: Robustness ---
T13 Jackknife: X/6 negative folds, stability = [stable/unstable]
T14 PSR: X.XXXX — [strong_support / moderate_support / warning]
T15 Bootstrap (diagnostic): P(ΔSh>0) = XX.X%, median ΔSh = +X.XXX
T16 DOF correction: K = XX configs, method = [Holm/none], corrected p = X.XXX

--- Phase D: Consensus ---
Supporting layers: [list]
Opposing layers: [list]
Decisive factors: [which layers tipped the verdict and why]

VERDICT: [PROMOTE / HOLD / INCONCLUSIVE / REJECT]
```

---

## 11. Execution Order (with early stopping)

```
Phase 0: Integrity check
  0.1 Verify pipeline §0b is implemented correctly
  0.2 Verify feature timestamping (§0c)
  0.3 Verify no full-sample transforms before CV/WFO

Phase A: Model Quality (feasibility)
  A1. Train model (CV for C × l1_ratio, pipeline §0b)  → T01, T06
  A2. Discrimination + calibration                      → T02, T03
  A3. Feature ablation (drop-one, with caveats)         → T05
  A4. Feature stability (selection freq, sign, coeff)   → T04
  A5. Sample adequacy (ESS, class support, EPV_eff)     → T07
  → STOP if feasibility prerequisites fail

Phase B: Strategy Impact (evidence)
  B1. Full-sample backtest (candidate vs Base)           → T10 (in sweep)
  B2. WFO 4-fold (retrain per fold, pipeline §0b)       → T08
  B3. Permutation test (moving-block event, 1000 perm)   → T09
  B4. Economic frontier (Base f-sweep, ε-Pareto)         → T11
  B5. Exposure attribution                               → T12
  → WFO 0/4: default reject (override only per §Phase B rules)

Phase C: Robustness (evidence)
  C1. Jackknife (6-fold leave-one-out)                   → T13
  C2. PSR (strong diagnostic)                            → T14
  C3. Bootstrap VCBB (500 paths, diagnostic)             → T15
  C4. DOF correction (if K > 1)                          → T16

Phase D: Consensus
  D1. Compile all 16 technique results
  D2. Multi-layer human verdict with reasoning
  D3. Write verdict.json and final report
```

---

## 12. Resource Directory — READ-ONLY

```
v2/resource/                          ← FROZEN (read-only)
├── spec/                             ← research protocol, implementation spec, deployment freeze
│   ├── master_spec_package_summary.md
│   ├── implementation_spec.md
│   ├── research_protocol_appendix.md
│   ├── acceptance_test_plan.md
│   ├── shadow_mode_plan.md
│   ├── master_reproducibility_spec.md
│   ├── deployment_freeze_spec.json
│   ├── final_verdict_summary.json
│   └── artifact_manifest.csv
└── confirms_winner/                  ← winner confirmation reports
    ├── final_confirms_winner_report.md
    ├── final_project_report.md
    ├── final_implementation_spec.md
    ├── final_acceptance_test_plan.md
    ├── final_shadow_mode_plan.md
    ├── final_deployment_freeze_spec.json
    └── final_artifact_manifest.csv
```

### Rules:
1. **NEVER modify** any file inside `v2/resource/`. These are canonical reference documents.
2. **READ only** — use these documents for context, specifications, and acceptance criteria.
3. **If you need to adapt or extend** a resource document:
   - Copy it to `v2/code/`, `v2/results/`, or another working directory first.
   - Modify the copy, not the original.
   - Reference the original with a note: `"Adapted from resource/spec/X.md"`
4. **Rationale**: `resource/` preserves the exact state of specifications and decisions
   at the time they were frozen. Modifications would break traceability and reproducibility.
5. **Research vs deployment pipelines**: `resource/spec/master_reproducibility_spec.md` describes
   a deployment freeze pipeline (StandardScaler fit on all data). This is correct for deployment
   but MUST NOT be used in research CV/WFO. Research pipeline follows §0b (fit within fold).

---

## 13. Artifacts

```
v2/
├── protocol/
│   └── PROTOCOL.md                ← this file
├── code/
│   └── [implementation scripts]
├── results/
│   ├── phase_a_model_quality.json
│   ├── phase_b_strategy_impact.json
│   ├── phase_c_robustness.json
│   └── verdict.json               ← final verdict + all layers
└── figures/
    ├── Fig_cv_auc.png             ← AUC per fold (ROC + PR)
    ├── Fig_calibration.png        ← reliability diagram
    ├── Fig_feature_ablation.png   ← drop-one AUC deltas
    ├── Fig_feature_stability.png  ← selection frequency + sign consistency
    ├── Fig_regularization.png     ← C × l1_ratio AUC surface
    ├── Fig_wfo_bars.png           ← ΔSh per fold
    ├── Fig_permutation.png        ← null distribution + observed
    ├── Fig_cost_sweep.png         ← ΔSh vs cost
    ├── Fig_frontier.png           ← Sharpe vs MDD frontier + candidate point
    ├── Fig_jackknife.png          ← JK fold deltas
    ├── Fig_bootstrap_violin.png   ← ΔSh distribution (diagnostic)
    └── Fig_exposure_attribution.png
```
