# P1 Add-Throttle: Acceptance Rubric

**Status:** Acceptance criteria — governs PROMOTE/HOLD/REJECT for the add-throttle overlay
**Prerequisite reading:**
- `reports/spec_p1_add_throttle.md` (mechanism & parameter design)
- `reports/spec_trade_level_suite.md` (bootstrap design & gate logic)
- `btc-spot/validation/suites/churn_metrics.py` (churn field definitions)
- `btc-spot/v10/validation/decision.py` (gate evaluation)

---

## 0. Guiding Principle

WFO is low-power for this strategy (~3 trades per 6-month window). The trade-level
bootstrap on `r_diff` (per-H4-bar return difference) is the primary inference tool.
Pathology metrics (buy fills, emergency DD share, fee drag) are the primary *reason*
we are running this experiment. The bootstrap tells us whether we paid too much in
return for those pathology improvements. Both matter; neither alone is sufficient.

---

## 1. Pre-Flight: Sensitivity Sanity Check

### 1.1 What

Before evaluating the add-throttle candidate, run the trade-level suite on a
**deliberately different** pair: baseline vs. a config with a known, material change
(e.g., `trail_atr_mult` shifted by +1.0, or `emergency_dd_pct` raised from 0.28 to
0.35). The change must be large enough to produce visibly different equity curves.

### 1.2 Why This Is Mandatory

The user's selected bootstrap output shows all-zero deltas:

```json
"trade_level_bootstrap": {
  "mean_diff": 0.0, "ci95_low": 0.0, "ci95_high": 0.0, "p_gt_0": 0.0
}
```

If the suite produces zeros for a pair that *should* differ, every subsequent gate
evaluation is meaningless — a broken thermometer reads "normal" for everything. The
sensitivity check proves the instrument works before we trust its readings.

### 1.3 Pass Criteria

| Field | Requirement |
|-------|-------------|
| `mean_diff` | Non-zero (`abs(mean_diff) > 1e-10`) |
| `ci95_high - ci95_low` | > 0 (CI has non-zero width) |
| `p_gt_0` | Not exactly 0.0 or 1.0 (distribution has spread) |
| `n_obs` | > 0 (aligned return series is populated) |

### 1.4 CLI Check

```bash
python -m v10.validation.runner \
  --candidate configs/sensitivity_probe.yaml \
  --baseline configs/v12_baseline.yaml \
  --suite trade

# Inspect:
jq '.trade_level_bootstrap | {mean_diff, ci95_low, ci95_high, p_gt_0, n_obs}' \
  results/trade_level_summary.json
```

**If the sensitivity check fails:** Do not proceed. Debug the `r_diff` alignment
pipeline (`_aligned_nav_return_diff` in `trade_level.py`), the equity snap matching,
or the bootstrap resampler before evaluating the throttle candidate.

---

## 2. Primary Success Metrics (Ranked)

All metrics are computed on the **harsh** scenario. Candidate = throttle-enabled,
baseline = throttle-disabled (identical config otherwise).

### Rank 1: Pathology Reduction (the reason we're doing this)

| # | Metric | Source | Direction | How to compute |
|---|--------|--------|-----------|----------------|
| P1 | `mean_buy_fills_per_episode` | `trade_level_summary.json → add_diagnostics` | ↓ | Total buy fills during DD episodes (≥5% DD) ÷ number of episodes |
| P2 | `total_fees` candidate < baseline | `churn_metrics.csv` row where `strategy_id=candidate` | ↓ | Direct read; ratio `cand / base < 1.0` |
| P3 | `share_emergency_dd` in DD episodes | `churn_metrics.csv` | ↓ | Fraction of exits that are `emergency_dd` |

**Minimum bar:** At least P1 *or* P3 must improve (candidate < baseline). If neither
improves, the throttle is not doing its job and the experiment is uninformative —
verdict is HOLD regardless of bootstrap results.

### Rank 2: Hard Guardrails (must not violate)

| # | Metric | Source | Guardrail |
|---|--------|--------|-----------|
| G1 | `max_drawdown_mid_pct` | Backtest summary | Candidate MDD ≤ baseline MDD + 2.0 pp |
| G2 | Holdout `return_term` (harsh) | Score decomposition | Candidate `return_term` ≥ baseline `return_term` − 5.0 points (≈ 2% CAGR) |

**G1 rationale:** The throttle's purpose is to reduce drawdown pain. If MDD gets
*worse* by more than 2pp, something is fundamentally wrong (e.g., the throttle
blocks recovery adds, causing the strategy to ride losing positions longer).

**G2 rationale:** A 5-point `return_term` tolerance corresponds to ~2% annualized
CAGR loss (`5.0 / 2.5 coefficient = 2.0 pct`). This is generous — we accept modest
return sacrifice if MDD improves materially (≥3pp). If MDD does *not* improve
materially, tighten to 3.0 points (1.2% CAGR).

**G2 conditional tightening rule:**

```
if mdd_delta >= -3.0:   # MDD improved by ≥3pp
    return_term_tolerance = 5.0   # ~2% CAGR sacrifice OK
else:
    return_term_tolerance = 3.0   # only ~1.2% sacrifice OK without MDD benefit
```

### Rank 3: Secondary Diagnostics (informational, not gates)

| Metric | Source | Expected direction |
|--------|--------|--------------------|
| `cascade_leq3` | `churn_metrics.csv` | ↓ (fewer rapid re-entries after ED) |
| `throttle_activation_rate` | `add_diagnostics` | In [0.02, 0.30] for default params |
| `calmar` (CAGR / MDD) | Backtest summary | ↑ or flat |
| `fee_drag_pct` | `churn_metrics.csv` | ↓ |
| `buy_sell_ratio` | `churn_metrics.csv` | ↓ (fewer buy fills relative to sells) |

---

## 3. Trade-Level Bootstrap Gate

### 3.1 Context

WFO is low-power (< 3 power windows or > 50% low-trade windows). The trade-level
bootstrap on `r_diff` (H4-aligned return differences, block lengths 42/84/168,
10,000 resamples) is the primary statistical gate. The selected block length is the
largest eligible (most conservative CI).

### 3.2 Gate Definition

Read from `trade_level_summary.json → trade_level_bootstrap` (selected block):

```
mean_diff     = bootstrap mean of r_diff
ci95_low      = 2.5th percentile of bootstrap mean distribution
ci95_high     = 97.5th percentile
p_gt_0        = P(bootstrap mean > 0)
ci_crosses_zero = (ci95_low <= 0 <= ci95_high)
is_small       = abs(mean_diff) <= 0.0002  (SMALL_MEAN_IMPROVEMENT_THRESHOLD)
```

### 3.3 Evidence Classification

| Zone | Condition | Interpretation | Action |
|------|-----------|----------------|--------|
| **PROMOTE** | `p_gt_0 >= 0.80` AND NOT (`ci_crosses_zero` AND `is_small`) | Preponderance of evidence that candidate does not degrade returns | Proceed to robustness grid |
| **HOLD-with-rationale** | `p_gt_0 >= 0.55` AND `ci_crosses_zero` AND pathology metrics improved (P1 or P3 from §2) | Returns are a wash, but the throttle achieves its purpose | Acceptable — see §3.4 |
| **HOLD-insufficient** | `0.20 ≤ p_gt_0 < 0.55` | Cannot distinguish from noise | Do not promote; collect more data or adjust parameters |
| **REJECT-signal** | `p_gt_0 < 0.20` AND `ci95_high < 0` | Strong evidence of degradation | Hard stop; investigate why throttle hurts returns |
| **NOISE** | `ci_crosses_zero` AND `is_small` | Effect is both statistically ambiguous and economically negligible | Indistinguishable from zero; rely entirely on pathology metrics |

### 3.4 The "CI Crosses Zero but Pathology Improves" Case

This is the most likely outcome for an add-throttle overlay: the throttle reduces
drawdown pain (fewer emergency DD exits, lower fee drag) but the return difference
is statistically indistinguishable from zero because the throttle only activates
during 5–15% of bars.

**Rule:** If ALL of the following hold, the verdict may be HOLD-with-rationale
(acceptable to proceed to robustness grid):

1. `p_gt_0 >= 0.55` — the candidate is at least not *clearly* worse
2. `ci95_low > -0.0005` — the worst-case annualized drag is bounded
   (~0.0005 × 2190 bars/year ≈ 110% — but this is CI bound, not point estimate)
3. At least one pathology metric improved:
   - `mean_buy_fills_per_episode` candidate < baseline, OR
   - `share_emergency_dd` candidate < baseline
4. Hard guardrails G1 and G2 pass

**Documentation requirement:** When using HOLD-with-rationale, the CLI report must
include an explicit section:

```markdown
## Bootstrap: HOLD-with-rationale

- p_gt_0: {value} (>= 0.55 threshold: PASS)
- ci95_low: {value} (> -0.0005 threshold: PASS)
- Pathology improved: {which metric(s)} ({candidate_value} < {baseline_value})
- Rationale: Returns are a statistical wash; throttle achieves its
  intended purpose of reducing drawdown pathology without material cost.
```

### 3.5 What Counts as "Evidence" vs. "Noise"

| Signal | Evidence | Noise |
|--------|----------|-------|
| `mean_diff` | Consistent sign across all 3 block lengths | Sign flips between block lengths |
| `p_gt_0` | Stable across block lengths (all ≥ 0.55 or all < 0.45) | Swings from 0.3 to 0.8 across block lengths |
| `ci95` | CI width narrows or holds as block length increases | CI width *increases* dramatically (168-bar CI >> 42-bar CI by > 3×) |
| Pathology | Direction consistent across harsh + base scenarios | Improves in one scenario, worsens in another |

**Stability check across `all_blocks`:**

```python
p_values = [b["p_gt_0"] for b in all_blocks]
sign_consistent = all(p >= 0.50 for p in p_values) or all(p < 0.50 for p in p_values)
# If not sign_consistent → flag "unstable_across_blocks"
```

---

## 4. Failure Modes & Detection

Each failure mode maps to computable checks that the CLI can evaluate automatically.

### 4.1 Blocks Recovery Adds Too Aggressively

**Symptom:** The throttle prevents the strategy from re-building positions after
drawdowns that reverse (V-shaped recoveries). The strategy captures less upside in
BULL corrections.

**Detection:**

```python
# From trade_level_summary.json → add_diagnostics:
ratio = candidate_mean_buy_fills_per_episode / max(baseline_mean_buy_fills_per_episode, 1)
if ratio < 0.30:
    flag("recovery_blocking: candidate fills/episode < 30% of baseline")

# From score decomposition (harsh scenario):
if candidate_return_term < baseline_return_term - 8.0:  # >3.2% CAGR loss
    flag("excessive_return_loss: check if throttle is too aggressive")
```

**CLI output field:** `failure_mode_checks.recovery_blocking` = `true`/`false`

### 4.2 Does Nothing (Buy Fills / Episode Unchanged)

**Symptom:** The throttle never activates or activates so rarely that pathology
metrics are unchanged.

**Detection:**

```python
# From add_diagnostics:
if throttle_activation_rate < 0.01:
    flag("throttle_inactive: activation_rate < 1%")

fills_delta = baseline_mean_fills_ep - candidate_mean_fills_ep
if abs(fills_delta) < 0.5:
    flag("no_effect: mean_buy_fills_per_episode delta < 0.5")
```

**CLI output field:** `failure_mode_checks.does_nothing` = `true`/`false`

### 4.3 Shifts Losses from Emergency DD to Trailing Stop

**Symptom:** `share_emergency_dd` drops, but `share_trailing_stop` rises by a
similar amount. Total drawdown is unchanged — losses just arrive through a different
exit reason. The strategy holds losing positions longer (because it can't add enough
to hit emergency DD thresholds), then exits via trailing stop at a similar loss.

**Detection:**

```python
# From churn_metrics.csv:
ed_delta = candidate_share_emergency_dd - baseline_share_emergency_dd
ts_delta = candidate_share_trailing_stop - baseline_share_trailing_stop

if ed_delta < -0.05 and ts_delta > 0.05:
    # ED share dropped but trailing stop share rose proportionally
    if abs(ed_delta + ts_delta) < 0.03:  # they roughly cancel
        flag("exit_reason_shift: ED ↓ but trailing_stop ↑ by similar amount")

# Cross-check with MDD:
if candidate_mdd >= baseline_mdd - 0.5:  # MDD didn't actually improve
    flag("mdd_unchanged_despite_exit_shift")
```

**CLI output field:** `failure_mode_checks.exit_reason_shift` = `true`/`false`

### 4.4 Over-Throttles in CHOP (Trade Count Collapses)

**Symptom:** In CAUTION regime, the throttle stacks with `caution_mult` and the
strategy stops building positions entirely. Trade count in CAUTION drops
dramatically.

**Detection:**

```python
# From regime_trade_summary.csv (produced by trade_level suite):
# Compare candidate vs baseline trade counts in CAUTION regime
caution_cand = candidate_trades_in_caution
caution_base = baseline_trades_in_caution

if caution_base > 0:
    ratio = caution_cand / caution_base
    if ratio < 0.50:
        flag("chop_over_throttle: CAUTION trade count dropped >50%")

# Also check total trade count:
total_ratio = candidate_trades / max(baseline_trades, 1)
if total_ratio < 0.60:
    flag("trade_collapse: total trade count dropped >40%")
```

**CLI output field:** `failure_mode_checks.chop_over_throttle` = `true`/`false`

### 4.5 Failure Mode Summary Table

```
failure_mode_checks: {
  "recovery_blocking":   false,
  "does_nothing":        false,
  "exit_reason_shift":   false,
  "chop_over_throttle":  false,
  "any_failure":         false
}
```

Emit in `trade_level_summary.json → failure_mode_checks`. The `any_failure` field
is `true` if any individual check is `true`. Any failure flag triggers a warning in
the CLI output but does NOT auto-reject — the operator reviews and decides.

---

## 5. Minimal Robustness Grid

### 5.1 Grid Definition

| Parameter | Values | Notes |
|-----------|--------|-------|
| `add_throttle_dd1` | **0.06, 0.08, 0.10** | Early, default, late onset |
| `add_throttle_dd2` | **0.14, 0.18, 0.22** | Tight, default, wide full-throttle |
| `add_throttle_mult` | **0.20** (fixed) | Isolate DD threshold effects first |

**Constraint:** `dd2 > dd1 + 0.02` (minimum 2pp ramp width). This eliminates
degenerate cells where the linear interpolation zone is too narrow to matter.

**Valid cells:**

| dd1 \ dd2 | 0.14 | 0.18 | 0.22 |
|:----------:|:----:|:----:|:----:|
| **0.06** | ✓ | ✓ | ✓ |
| **0.08** | ✓ | ✓ | ✓ |
| **0.10** | ✓ | ✓ | ✓ |

All 9 cells are valid with the 2pp minimum gap. **Total: 9 runs.**

### 5.2 Per-Cell Reporting

For each cell, compute and report:

```json
{
  "dd1": 0.08,
  "dd2": 0.18,
  "mult": 0.20,
  "mdd_delta": -3.6,
  "return_term_delta": -1.2,
  "bootstrap_p_gt_0": 0.823,
  "share_emergency_dd_cand": 0.12,
  "share_emergency_dd_base": 0.18,
  "mean_fills_ep_cand": 3.2,
  "mean_fills_ep_base": 5.1,
  "fee_drag_pct_cand": 8.5,
  "fee_drag_pct_base": 11.2,
  "throttle_activation_rate": 0.089,
  "g1_pass": true,
  "g2_pass": true,
  "pathology_improved": true
}
```

Write to `results/add_throttle_grid.csv`.

### 5.3 What Constitutes Robustness

The throttle is robust if it **wins in a region, not at a single point.** Concretely:

**Required (all must hold):**

| # | Check | Threshold | Rationale |
|---|-------|-----------|-----------|
| R1 | G1 (MDD guardrail) passes | In ≥ 8/9 cells | One outlier is acceptable; systematic MDD worsening is not |
| R2 | G2 (return_term guardrail) passes | In ≥ 8/9 cells | Same logic |
| R3 | Pathology improves (P1 or P3) | In ≥ 7/9 cells | Throttle should help across most of the parameter space |
| R4 | `bootstrap_p_gt_0 >= 0.40` | In ALL 9 cells | No cell should show clear degradation |
| R5 | `mean_fills_ep_cand >= 1.0` | In ALL 9 cells | No cell should completely block adds |

**Desirable (strengthens confidence):**

| # | Check | Threshold | Interpretation |
|---|-------|-----------|----------------|
| D1 | MDD improves (candidate < baseline) | In ≥ 6/9 cells | Throttle reliably reduces drawdown |
| D2 | `bootstrap_p_gt_0 >= 0.55` | In ≥ 6/9 cells | Returns are not systematically hurt |
| D3 | The default cell (dd1=0.08, dd2=0.18) is in the best 50% | By `mdd_delta` rank | Default is well-placed, not an edge case |

### 5.4 Regional Win Pattern

A robust throttle shows a **connected region** of good cells, not a checkerboard.
Visual check on the 3×3 grid:

```
        dd2=0.14   dd2=0.18   dd2=0.22
dd1=0.06   [✓]       [✓]       [✓]      ← good: contiguous
dd1=0.08   [✓]       [✓]       [✓]         wins across most
dd1=0.10   [✓]       [~]       [~]         of the space

vs.

dd1=0.06   [✓]       [✗]       [✓]      ← bad: checkerboard
dd1=0.08   [✗]       [✓]       [✗]         suggests overfitting
dd1=0.10   [✓]       [✗]       [✓]         to specific cells
```

A cell is `[✓]` if R1–R5 all pass and at least one of D1–D2 holds.
A cell is `[~]` if R1–R5 pass but neither D1 nor D2 holds (neutral).
A cell is `[✗]` if any of R1–R5 fails.

**Robustness verdict:**
- `ROBUST`: ≥ 7 cells are `[✓]` and they form a connected region (share an edge)
- `MARGINAL`: 5–6 cells are `[✓]` or cells are not connected
- `NOT_ROBUST`: < 5 cells are `[✓]` or R4/R5 fails in any cell

### 5.5 Grid Output

Write summary to `reports/add_throttle_robustness.md`:

```markdown
## Add-Throttle Robustness Grid (3×3, mult=0.20)

### Grid Results

| dd1 | dd2 | MDD Δ | return_term Δ | P(>0) | ED share Δ | Fills/ep ratio | Act% | Verdict |
|----:|----:|------:|--------------:|------:|-----------:|---------------:|-----:|:-------:|
| 0.06|0.14 | ...   | ...           | ...   | ...        | ...            | ...  | ✓/~/✗   |
| ... | ... | ...   | ...           | ...   | ...        | ...            | ...  | ...     |

### Required Checks

- R1 G1 passes in ≥8/9: {n}/9 → {PASS|FAIL}
- R2 G2 passes in ≥8/9: {n}/9 → {PASS|FAIL}
- R3 Pathology improves in ≥7/9: {n}/9 → {PASS|FAIL}
- R4 P(>0) ≥ 0.40 in all: {n}/9 → {PASS|FAIL}
- R5 Fills/ep ≥ 1.0 in all: {n}/9 → {PASS|FAIL}

### Desirable Checks

- D1 MDD improves in ≥6/9: {n}/9
- D2 P(>0) ≥ 0.55 in ≥6/9: {n}/9
- D3 Default cell in top 50% by MDD: {YES|NO}

### Verdict: {ROBUST|MARGINAL|NOT_ROBUST}

### Recommended configuration

{dd1, dd2, mult} = {best cell or default if in good region}
```

---

## 6. End-to-End Decision Flow

```
Step 1: Pre-flight sensitivity check (§1)
  └─ FAIL → STOP, debug suite
  └─ PASS ↓

Step 2: Run candidate vs baseline (harsh scenario)
  ├─ Compute pathology metrics (§2 Rank 1)
  ├─ Compute guardrails (§2 Rank 2)
  ├─ Compute bootstrap (§3)
  └─ Compute failure mode checks (§4)

Step 3: Evaluate
  ├─ Pathology minimum bar not met? → HOLD ("throttle has no effect")
  ├─ G1 violated? → REJECT ("MDD worsened beyond tolerance")
  ├─ G2 violated? → REJECT ("returns degraded beyond tolerance")
  ├─ Any failure mode flag? → WARNING (human review required)
  ├─ Bootstrap PROMOTE zone? → proceed to grid
  ├─ Bootstrap HOLD-with-rationale? → proceed to grid with documented rationale
  ├─ Bootstrap HOLD-insufficient? → HOLD ("insufficient evidence")
  └─ Bootstrap REJECT-signal? → REJECT ("clear degradation")

Step 4: Robustness grid (§5, only if Step 3 passes)
  ├─ ROBUST → PROMOTE candidate with recommended config
  ├─ MARGINAL → HOLD (narrow the grid or adjust parameters)
  └─ NOT_ROBUST → REJECT ("effect is not robust to parameter variation")
```

---

## 7. CLI Computation Checklist

Every rule in this rubric must be computable from existing or specified output files.
No manual inspection required for gate evaluation.

| Rule | Input file(s) | Key field(s) |
|------|---------------|--------------|
| §1 Sensitivity | `trade_level_summary.json` | `trade_level_bootstrap.mean_diff`, `.p_gt_0`, `.n_obs` |
| §2 P1 | `trade_level_summary.json` | `add_diagnostics.mean_buy_fills_per_episode` |
| §2 P2 | `churn_metrics.csv` | `total_fees` (candidate vs baseline rows) |
| §2 P3 | `churn_metrics.csv` | `share_emergency_dd` |
| §2 G1 | Backtest summary JSON | `max_drawdown_mid_pct` (candidate vs baseline) |
| §2 G2 | `score_breakdown_holdout.csv` | `return_term` (candidate vs baseline, harsh) |
| §3 Gate | `trade_level_summary.json` | `trade_level_bootstrap.*` |
| §3 Stability | `trade_level_summary.json` | `trade_level_bootstrap.all_blocks[*].p_gt_0` |
| §4.1 | `trade_level_summary.json` + `score_breakdown_full.csv` | `add_diagnostics`, `return_term` |
| §4.2 | `trade_level_summary.json` | `add_diagnostics.throttle_activation_rate`, `.mean_buy_fills_per_episode` |
| §4.3 | `churn_metrics.csv` + backtest summary | `share_emergency_dd`, `share_trailing_stop`, `max_drawdown_mid_pct` |
| §4.4 | `regime_trade_summary.csv` | Trade counts per regime |
| §5 Grid | `add_throttle_grid.csv` | All per-cell fields |
