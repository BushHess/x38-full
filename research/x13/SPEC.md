# X13: Is Trail-Stop Churn Predictable?

## Central Question

X12 showed that 63% of E0+EMA1D21's trail stop exits are **churn** — false
stop-outs followed by re-entry within 20 bars. RATR (E5) was designed to fix
this but fails: it increases churn by +1.4pp.

**At the moment a trail stop fires, does information exist in available data
that distinguishes true reversals from false stop-outs (churn)?**

- If **NO** → churn is irreducible noise, E0+EMA1D21 is at the Pareto frontier
  ceiling for trail-stop trend-following on BTC H4. No trail-stop modification
  can improve on E0.
- If **YES** → the frontier is breakable in principle. The identified features
  define the design space for potential exit logic improvements (but filter
  design is NOT part of this study).

## Prior: X12 Churn Findings (50 bps RT)

| Metric              | E0         | E5         |
|---------------------|------------|------------|
| Trades              | 186        | 199        |
| Trail stop exits    | 168        | 183        |
| Churn events        | 106 (63.1%)| 118 (64.5%)|
| Churn PnL           | +$329,680  | +$423,372  |
| Non-churn trail PnL | -$128,136  | -$154,894  |

**Critical observation:** Churn trades are NET POSITIVE. Trail stop fires during
strong trends, capturing profits at local peaks. The trend resumes → re-entry.
Non-churn trail stops (actual trend endings) are net negative.

**Implication:** "Fixing churn" is not obviously desirable. Suppressing churn
exits means holding through pullbacks instead of capturing profits at local
peaks. Phase 0 will determine whether the cost savings from fewer roundtrips
outweigh the lost profit-taking.

## Hypotheses

**H_null:** Trail stop triggers contain no predictive information about whether
the stop is churn or true reversal. The 63% churn rate is a necessary cost of
trend-following. No feature available at the exit bar can improve on base-rate
guessing. E0 is at the frontier ceiling.

**H_alt:** At least one feature available at the exit bar carries statistically
significant information about churn vs true reversal. The trail stop's decision
is improvable in principle.

## Design Overview

| Phase | Purpose                      | Method                                      |
|-------|------------------------------|---------------------------------------------|
| P0    | Is improvement possible?     | Oracle sim with perfect future knowledge     |
| P1    | What information is available?| Extract 10 features at each trail stop exit  |
| P2    | Single-feature predictability| Mann-Whitney U per feature, Bonferroni       |
| P3    | Joint predictability bound   | LOO logistic regression + permutation AUC    |
| P4    | Out-of-sample robustness     | 500 VCBB bootstrap                          |
| P5    | Definition sensitivity       | Churn windows [10, 15, 20, 30, 40] bars     |

Single strategy (E0+EMA1D21), single parameter set, harsh cost (50 bps RT).
No sweep, no tuning. E5 excluded — X12 showed it's noise-equivalent to E0.

## Parameters (frozen, inherited from X12)

| Param       | Value                   |
|-------------|-------------------------|
| slow_period | 120                     |
| fast_period | 30                      |
| trail_mult  | 3.0                     |
| vdo_threshold| 0.0                    |
| d1_ema_period| 21                     |
| atr_period  | 14                      |
| cost        | 50 bps RT               |
| data        | 2019-01-01 to 2026-02-20|
| warmup      | 365 days                |
| CASH        | 10,000                  |

## Phase 0: Oracle Ceiling

**Purpose:** Determine the MAXIMUM possible improvement from perfect churn
prediction. If the ceiling is low, Phases 1-5 are still run for understanding
but the practical conclusion is settled: churn is not worth fixing.

**Method: Forward-looking oracle sim**

Modified `sim_e0_d1()` with oracle logic. At each bar where the trail stop
would trigger:

1. Look ahead `CHURN_WINDOW` (20) bars into the future
2. Check if the entry condition (`EMA_fast > EMA_slow AND VDO > 0 AND
   D1_regime`) would be active at any bar in the lookahead window
3. If **YES** → this would be a churn exit → oracle **SUPPRESSES** the exit
   (position stays open, trail continues to evolve from current peak)
4. If **NO** → this is a true reversal → oracle **ALLOWS** the exit

The oracle uses future information intentionally — it computes the ceiling,
not a tradeable strategy.

**Trail dynamics under suppression:** When a churn exit is suppressed, the
trail stop level continues from its current position. The trail is a ratchet
(only moves up), so after the pullback resolves and price resumes upward, the
trail resets above the suppression point. The oracle does NOT lose trail
protection — it holds through a temporary pullback that DOES recover (because
the oracle verified re-entry would occur).

**Key edge case:** oracle_d_sharpe could be **NEGATIVE**. If churn exits are
actually capturing profits at local peaks efficiently, suppressing them means
holding through drawdowns that the normal strategy avoided. This would prove
churn is a FEATURE, not a bug.

**Outputs:**
- `baseline`: {sharpe, cagr, mdd, trades} — normal E0+EMA1D21
- `oracle`: {sharpe, cagr, mdd, trades} — oracle sim
- `d_sharpe`: oracle - baseline
- `d_cagr`: oracle_cagr - baseline_cagr
- `d_mdd`: oracle_mdd - baseline_mdd
- `n_suppressed`: number of churn exits suppressed
- `n_allowed`: number of true exits allowed through
- `cost_saved`: total roundtrip cost saved by suppression (n_suppressed × 2 × CPS × avg_position)

**Artefact:** included in `x13_results.json`

**Verdict gate V0:** `d_sharpe > 0.10` → ceiling worth pursuing.
(0.10 threshold = comparable to E5-E0 gap of 0.096, which is noise at P=46.4%.
Improvement must exceed the noise floor to be meaningful.)

**If d_sharpe < 0:** Churn is BENEFICIAL. Oracle verdict = `CHURN_IS_OPTIMAL`.
Skip to final conclusion: trail stop's "false exits" are profit-taking, not
errors.

## Phase 1: Feature Census

**Purpose:** Extract candidate predictors at each trail stop exit bar.
All features use ONLY information available at or before the exit bar (no
look-ahead). Each feature is economically motivated — not data-mined.

**Features (10):**

| #  | Name             | Formula                                    | Motivation                          |
|----|------------------|--------------------------------------------|-------------------------------------|
| F1 | ema_ratio        | EMA_fast[i] / EMA_slow[i]                 | Trend strength at exit              |
| F2 | bars_held        | i - entry_bar                              | Trade maturity / duration           |
| F3 | atr_pctl         | percentile of ATR[i] in ATR[i-99:i+1]     | Volatility regime (high = unusual)  |
| F4 | bar_range_atr    | (high[i] - low[i]) / ATR[i]               | Exit bar character (>1 = wide bar)  |
| F5 | dd_from_peak     | (peak_close - close[i]) / peak_close       | Drawdown severity from trade peak   |
| F6 | bars_since_peak  | i - peak_bar                               | Time since high water mark          |
| F7 | close_position   | (close[i] - low[i]) / (high[i] - low[i])  | Intra-bar position (0=low, 1=high)  |
| F8 | vdo_at_exit      | VDO[i]                                     | Volume confirmation of the move     |
| F9 | d1_regime_str    | (D1_close - D1_EMA21) / D1_close          | Higher timeframe regime health      |
| F10| trail_tightness  | trail_mult × ATR[i] / close[i]            | Relative trail width (tight=more trigger-prone)|

**Economic reasoning for each feature:**

- **F1 (ema_ratio):** If fast EMA is still well above slow EMA at the moment of
  trail stop, the trend structure is intact → pullback more likely than reversal.
  High ema_ratio → more likely churn.

- **F2 (bars_held):** Young positions may be more prone to churn (entered near
  local high, quick pullback). Or long positions may have extended peaks that
  pull back naturally. Direction unclear ex ante → let data speak.

- **F3 (atr_pctl):** If ATR just spiked to 90th+ percentile, the trail distance
  3×ATR was "normal" but the trigger bar was abnormally volatile → more likely
  false stop. High atr_pctl → more likely churn.

- **F4 (bar_range_atr):** A single wide bar (range >> ATR) can trigger the trail
  stop without sustained selling. Wide exit bar → more likely churn.

- **F5 (dd_from_peak):** A shallow drawdown from peak (just barely hit 3×ATR)
  may indicate a routine pullback. A deep drawdown may indicate real reversal.
  Shallow dd → more likely churn.

- **F6 (bars_since_peak):** Many bars since peak = extended decline, more likely
  true reversal. Few bars since peak = sharp but brief pullback → churn.

- **F7 (close_position):** Closing near the low of the exit bar = bearish, more
  likely true reversal. Closing near the high = recovering during the bar →
  more likely churn.

- **F8 (vdo_at_exit):** Negative VDO at exit = volume confirming the down move →
  more likely true reversal. Positive/neutral VDO → more likely churn.

- **F9 (d1_regime_str):** If the daily regime is still strongly bullish (close
  well above D1 EMA21), the exit is against the higher timeframe trend → more
  likely churn.

- **F10 (trail_tightness):** If 3×ATR/close is small (tight trail), the stop
  triggers more easily on small moves → more likely churn.

**Labels:**
- 1 = churn (trail stop exit followed by re-entry within CHURN_WINDOW bars)
- 0 = true reversal (no re-entry within CHURN_WINDOW)

**Sample size:** ~168 trail stop exits (E0 at SLOW=120).
Expected split: ~106 churn (63%), ~62 true (37%).

**Correlation note:** Some features are correlated (bars_held/bars_since_peak,
ema_ratio/d1_regime_str). Phase 3's L1 regularisation handles this; Phase 2
tests each independently so correlation doesn't affect univariate results.

**Artefact:** `x13_features.csv` (one row per trail stop exit, 10 features + label)

## Phase 2: Univariate Predictability

**Purpose:** Test each feature independently for association with the churn
label. This answers: does ANY single feature carry information?

**Method (per feature):**

1. **Mann-Whitney U test** (scipy.stats.mannwhitneyu)
   - Non-parametric, no distributional assumption
   - Compares feature distribution: churn group vs true-reversal group
   - Two-sided test (we don't assume direction for all features)

2. **Cliff's delta** (effect size)
   - d = (#{x1 > x2} - #{x1 < x2}) / (n1 × n2) for all pairs
   - |d| < 0.147: negligible
   - |d| < 0.33: small
   - |d| < 0.474: medium
   - |d| >= 0.474: large
   - Effect size is critical — with N=168, even noise can have small p-values

3. **Multiple testing correction:** Bonferroni (10 tests, α=0.05 → per-test
   α=0.005)

**Outputs (per feature):**
- U statistic
- p_raw, p_bonferroni
- cliffs_delta, effect_size_category
- mean_churn, mean_true, mean_ratio
- direction (which group has higher values)

**Artefact:** `x13_univariate.csv`

**Verdict gate V1:** At least 1 feature with Bonferroni p < 0.05 → information
exists in at least one dimension.

## Phase 3: Multivariate Predictability Bound

**Purpose:** Test whether the COMBINED feature set predicts churn better than
random. Individual features might be weak but jointly informative. This is the
strongest test of H_alt.

**Method:**

1. **Model:** L1-regularised logistic regression
   - Implemented with `scipy.optimize.minimize` (no sklearn dependency)
   - L1 penalty for automatic feature selection (critical with 10 features / 168 samples)
   - Features standardised (zero mean, unit variance) before fitting

2. **Evaluation:** Leave-One-Out Cross-Validation (LOOCV)
   - Maximises training data for small samples
   - Each of 168 exits predicted by a model trained on the other 167
   - Predictions collected → compute ROC AUC

3. **Regularisation selection:**
   - C values: [0.001, 0.01, 0.1, 1.0, 10.0]
   - Inner LOOCV nested within outer LOOCV to select C
   - (Simplified approach: select C by LOOCV AUC on full data, then report
     LOOCV AUC. Slight optimistic bias in C selection, acceptable for a
     ceiling test.)

4. **Permutation test (gold standard for small samples):**
   - Observed: LOOCV AUC on real labels
   - For k = 1..1000: shuffle labels randomly, compute LOOCV AUC → null dist
   - p = (1 + #{null_AUC >= observed_AUC}) / (1 + 1000)
   - This is assumption-free: no distributional requirements, accounts for
     all sources of bias including feature correlation and small-sample effects

5. **Feature importance:** L1 coefficients from full-data model at best C.
   Non-zero coefficients indicate which features survive regularisation.

**Sample size assessment:**
- 168 samples, 10 features, minority class = 62
- Events per variable = 6.2 (below ideal 10 per Peduzzi et al. 1996)
- L1 regularisation mitigates by shrinking/zeroing weak features
- LOOCV + permutation = assumption-free evaluation regardless of sample size
- The permutation test is the final arbiter — if AUC is within null, the
  conclusion is NO regardless of any individual metric

**Outputs:**
- loocv_auc (observed)
- permutation_null: mean, std, p5, p95
- permutation_p
- l1_coefficients (10 features)
- n_nonzero_features
- best_C
- confusion matrix at Youden's J threshold

**Artefact:** `x13_multivariate.json`

**Verdict gate V2:** `permutation_p < 0.05 AND loocv_auc > 0.60` → jointly
predictable beyond chance.

**AUC thresholds:**
- 0.50 = random (no information)
- 0.55 = negligible discrimination
- 0.60 = weak discrimination (minimum for "information exists")
- 0.70 = acceptable discrimination
- 0.80 = good (extremely unlikely with 10 simple features on 168 samples)

## Phase 4: Bootstrap OOS

**Purpose:** Test whether Phase 2/3 findings survive out-of-sample. In-sample
predictability means nothing if it's path-specific.

**Method:** 500 VCBB paths (block=60, seed=42, repo convention).

For each path:
1. Run E0+EMA1D21 sim on the VCBB price path
2. Extract trail stop exits, label churn (re-entry within CHURN_WINDOW bars)
3. Extract 10 features at each trail stop exit bar
4. Compute LOOCV AUC (same model as Phase 3, best C from Phase 3)
5. Compute best univariate Mann-Whitney p-value (lowest p across 10 features)

**Skip condition:** If a bootstrap path has < 20 trail stop exits, skip it
(too few samples for meaningful LOOCV). Record skip rate.

**Outputs:**
- auc_distribution: median, p5, p95, mean
- P(AUC > 0.60): fraction of paths with meaningful AUC
- P(AUC > 0.55): fraction with any discrimination
- best_univariate_p_distribution: median, P(p < 0.05)
- n_skipped: paths with too few trail stop exits
- correlation(auc, headline_nav): is predictability related to strategy perf?

**Artefact:** `x13_bootstrap_auc.csv`

**Verdict gate V3:** `median AUC > 0.55 AND P(AUC > 0.60) > 0.30` → OOS robust.

## Phase 5: Churn Window Sensitivity

**Purpose:** The 20-bar churn window is a design choice inherited from X12. Test
whether all findings are robust to this definition.

**Method:** Repeat Phase 0 + Phase 2 + Phase 3 at each of:
`CHURN_WINDOWS = [10, 15, 20, 30, 40]` bars

At each window:
- Churn label changes (different window → different churn/true split)
- Oracle sim uses the corresponding window for lookahead
- Univariate and multivariate tests re-run on the re-labelled data

**Outputs (per window):**
- churn_rate (fraction of trail stops labelled as churn)
- oracle_d_sharpe
- best_univariate_p (lowest Bonferroni p)
- loocv_auc + permutation_p
- V0/V1/V2 pass/fail at this window

**Stability criterion:** V0/V1/V2 direction consistent in >= 4/5 windows.

**Artefact:** `x13_window_sensitivity.csv`

**Verdict gate V4:** Findings stable across >= 4/5 windows → definition-robust.

## Verdict Gates

| Gate | Condition | Meaning |
|------|-----------|---------|
| **V0** | oracle d_sharpe > 0.10 (P0) | Ceiling of improvement worth pursuing |
| **V1** | Any Bonferroni p < 0.05 (P2) | Information exists in at least one feature |
| **V2** | Permutation p < 0.05 AND AUC > 0.60 (P3) | Jointly predictable beyond chance |
| **V3** | Median bootstrap AUC > 0.55 AND P(AUC>0.60) > 0.30 (P4) | OOS robust |
| **V4** | Findings stable >= 4/5 churn windows (P5) | Definition-robust |

## Decision Matrix

| V0 | V1 | V2 | V3 | V4 | Verdict |
|----|----|----|----|----|---------|
| <0 | *  | *  | *  | *  | **CHURN_IS_OPTIMAL** — suppressing churn hurts; trail stop's "false exits" are profit-taking, not errors |
| F  | *  | *  | *  | *  | **CEILING_TOO_LOW** — even perfect prediction can't meaningfully improve E0 |
| T  | F  | F  | *  | *  | **NO_INFORMATION** — churn is irreducible; E0 at Pareto frontier |
| T  | T  | F  | *  | *  | **WEAK_SIGNAL** — univariate hints but no joint predictability |
| T  | T  | T  | F  | *  | **IN_SAMPLE_ONLY** — predictability doesn't survive OOS |
| T  | T  | T  | T  | F  | **FRAGILE** — depends on churn window definition |
| T  | T  | T  | T  | T  | **INFORMATION_EXISTS** — frontier is breakable; features identify design space |

### Interpretation of Each Verdict

**CHURN_IS_OPTIMAL:** The most decisive outcome. Trail stop churn is not an
error — it's the system capturing profits at local peaks during strong trends.
The roundtrip cost of churn is outweighed by the profit-taking benefit.
Conclusion: E0's exit logic is not just at the frontier — it's BETTER than
what we'd get by "fixing" churn. Stop looking at exit modifications entirely.

**CEILING_TOO_LOW:** Even with a perfect oracle (P=46.4% → P=100% prediction),
the Sharpe improvement is < 0.10 — below the noise floor established by X12's
bootstrap. No practical filter could capture even this small ceiling. E0 is at
the frontier. Research direction: improvement (if any) must come from entry
logic, position sizing, or entirely different strategy class.

**NO_INFORMATION:** Perfect prediction would help, but no feature at the exit
bar carries signal. The trail stop's trigger is not distinguishable from noise
using price/volume/regime data at H4/D1 resolution. Possible next step:
higher-frequency data (H1, M15) might carry signal, but that's a different
strategy class.

**WEAK_SIGNAL:** Some univariate correlation exists (e.g., VDO at exit
correlates weakly with churn) but the signals don't combine into a useful
predictor. Suggestive for understanding mechanism, not actionable.

**IN_SAMPLE_ONLY:** Predictability exists on 2019-2026 BTC but doesn't survive
bootstrap. Likely driven by a few unusual market periods (e.g., COVID crash,
2021 bull). Building a filter would overfit to the historical path.

**FRAGILE:** Results depend on the arbitrary churn window definition. The
"churn" concept itself may be a labelling artefact rather than a real market
phenomenon.

**INFORMATION_EXISTS:** The most actionable outcome. The L1 coefficients and
feature importances identify WHICH features carry signal (e.g., "ema_ratio >
1.02 at trail stop fire → 78% churn probability"). This defines the design
space for a potential exit filter. But filter design, parameter tuning, and
validation are a SEPARATE study (X14), not part of X13. X13 only answers the
existence question.

### What This Does NOT Do

- Does not design, propose, or test any exit filter
- Does not modify E0+EMA1D21 in any way
- Does not change the PRIMARY status of E5+EMA1D21
- Does not sweep strategy parameters
- Does not study E5 (noise-equivalent to E0 per X12)
- Only determines whether the information-theoretic ceiling is non-trivial

### Relationship to Prior Work

| Study | Finding | X13 extends |
|-------|---------|-------------|
| X12 T0 | 63% churn rate, E5 doesn't fix it | X13 asks if ANYTHING can fix it |
| X12 T5 | P(E5>E0) = 46.4% bootstrap | X13 sets oracle ceiling at this noise floor |
| vtrend/x1 | 67% path-state driven | X13 tests if the path trigger point is predictable |
| Trail sweep | Monotonic return/risk tradeoff | X13 tests if the frontier can be broken |

## Output Files

```
x13/
  SPEC.md                      # this file
  benchmark.py                 # single script, all phases P0-P5
  x13_results.json             # nested dict of all results
  x13_features.csv             # P1: feature matrix + labels
  x13_univariate.csv           # P2: per-feature test results
  x13_multivariate.json        # P3: LOOCV AUC + permutation + coefficients
  x13_bootstrap_auc.csv        # P4: 500-path AUC distribution
  x13_window_sensitivity.csv   # P5: churn window robustness
```

## Dependencies

```python
import numpy as np
from scipy.stats import mannwhitneyu, percentileofscore
from scipy.optimize import minimize       # L1-logistic (no sklearn)
from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
```

No sklearn dependency. Logistic regression implemented manually with
scipy.optimize.minimize and L1 penalty.

## Estimated Runtime

- P0 (oracle sim): ~2s
- P1 (feature extraction): ~1s
- P2 (univariate tests): ~1s
- P3 (LOOCV + 1000 permutations): ~60s
- P4 (500 bootstrap paths × sim + LOOCV): ~400s
- P5 (5 windows × P0 + P2 + P3): ~300s
- Total: ~12 min
