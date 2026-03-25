# WFO Evaluation Policy: Low-Trade and Zero-Trade Windows

**Status:** Active policy
**Applies to:** All WFO suite runs via `validation/suites/wfo.py`
**Date:** 2026-02-24
**Prerequisite reading:** `btc-spot/v10/docs/LOW_FREQUENCY_VALIDATION_METHODOLOGY.md`

---

## 1. Definitions

### 1.1 Invalid Window

A WFO window where no meaningful delta can be computed.

**Criteria** (implemented in `_window_invalid_reason()`):

| Condition | `invalid_reason` value | Effect |
|-----------|----------------------|--------|
| Candidate has zero trades | `candidate_zero_trade_count` | `valid_window = False`, `delta_harsh_score = NaN` |
| Baseline has zero trades | `baseline_zero_trade_count` | Same |
| Both have zero trades | `both_zero_trade_counts` | Same |
| Any core metric (score, CAGR, max_dd, Sharpe) is NaN/Inf on candidate | `candidate_non_finite_core_metrics` | Same |
| Any core metric is NaN/Inf on baseline | `baseline_non_finite_core_metrics` | Same |
| Both sides non-finite | `both_non_finite_core_metrics` | Same |
| Computed delta is non-finite despite both sides appearing valid | `delta_non_finite` | Same |

**Key invariant:** If `valid_window = False`, then `delta_harsh_score` MUST be `NaN` and `invalid_reason` MUST NOT be `"none"`. This is enforced by assertion in `_evaluate_window_metrics()` (wfo.py:202-208).

Invalid windows are **never included** in any aggregation. They carry diagnostic value only (e.g., confirming that a long-only strategy correctly avoids the 2022 bear market).

### 1.2 Low-Power Window

A valid window where the trade count is too small for the per-window delta to carry statistical weight.

**Criteria** (implemented in `_low_trade_reason()`):

| Condition | `low_trade_reason` value |
|-----------|------------------------|
| Both sides have trades in `(0, min_trades_for_power)` | `both_below_min_trades_for_power` |
| Only candidate below threshold | `candidate_below_min_trades_for_power` |
| Only baseline below threshold | `baseline_below_min_trades_for_power` |

**Key invariant:** `low_trade_window = True` requires `valid_window = True`. A window cannot be both invalid and low-power.

### 1.3 Recommended Thresholds for `min_trades_for_power`

The current default is `min_trades_for_power = 5` (config.py:120). This section provides the justification and a method to compute strategy-specific thresholds.

**Why 5 is the minimum floor:**
- With < 5 trades, the sample standard deviation has 3 degrees of freedom. The t-distribution is extremely heavy-tailed at df=3 (kurtosis = infinity for df <= 4), making confidence intervals for the mean trade delta unreliable.
- A single outlier trade in a 4-trade window can swing the window delta by > 3 standard deviations, producing an apparent "win" or "loss" that is entirely noise.

**Strategy-specific threshold (when you have data):**

Compute the per-trade signal-to-noise ratio from matched trade deltas across the full backtest:

```
sigma_hat = std(delta_pnl per matched trade)
mu_hat    = mean(delta_pnl per matched trade)
cv        = sigma_hat / |mu_hat|          # coefficient of variation
```

Then the minimum trades per window for SNR >= 2.0 (95% confidence of correct sign):

```
N_min = ceil((2.0 * cv)^2)
```

| cv (sigma/|mu|) | N_min per window | Recommended `min_trades_for_power` |
|-----------------|------------------|-----------------------------------|
| < 3 | < 36 | 10 |
| 3-6 | 36-144 | 30 |
| 6-10 | 144-400 | Window-level stats are noise; use trade-level only |
| > 10 | > 400 | WFO window comparison is not viable |

**Empirical reference (V10/V11):**
- harsh scenario: cv = 2442/418 = 5.8, N_min = 136
- base scenario: cv = 3369/263 = 12.8, N_min = 656
- Median trades per 6-month window: 9
- Conclusion: WFO window-level deltas for V10-class strategies are statistical noise

**CLI implementation:**

```bash
# Default (conservative floor)
python -m validation.cli ... --min-trades-for-power 5

# After computing cv from matched trades
python -m validation.cli ... --min-trades-for-power 30
```

**Rule: If you haven't computed cv yet, use 10.** The default of 5 is too permissive for any strategy with fat-tailed trade PnL (which includes all BTC strategies we've tested). Change to 5 only if you have evidence that per-trade deltas have cv < 3.

---

## 2. Aggregation Rules

### 2.1 Dual Aggregation Blocks

The WFO suite produces two aggregation blocks in `wfo_summary.json`:

| Block | Filter | Purpose |
|-------|--------|---------|
| `stats_all_valid` | `valid_window = True` (includes low-power) | Conservative: what does the data say, warts and all? |
| `stats_power_only` | `valid_window = True AND low_trade_window = False` | Focused: only windows with enough trades to trust |

Both blocks compute identical fields:

```json
{
  "n_windows": int,
  "win_count": int,
  "win_rate": float,
  "mean_delta": float,
  "median_delta": float,
  "worst_delta": float,
  "best_delta": float
}
```

### 2.2 Which Stats to Compute on Which Block

| Statistic | `stats_all_valid` | `stats_power_only` | Rationale |
|-----------|:-:|:-:|-----------|
| **win_rate** | Report | **Gate on this** | Low-power windows dilute the denominator with coin-flip outcomes. Win rate from power-only windows is the actionable signal. |
| **median_delta** | Report | **Gate on this** | Median is robust to single-window outliers, but only meaningful when windows have enough trades. |
| **worst_delta** | Report | Report | Worst-case from all-valid catches catastrophic windows even with few trades. Worst-case from power-only avoids flagging noise-dominated windows as catastrophic. |
| **mean_delta** | Report | Report (do not gate) | Mean is sensitive to outliers from low-N windows. Never use mean as a gate criterion. |
| **best_delta** | Report | Report | Diagnostic only. Never gate on best case. |

### 2.3 Include/Exclude Rules for Low-Power Windows

**Default rule: Include low-power windows in `stats_all_valid`, exclude from `stats_power_only`.** Both blocks are always reported. The decision gate uses `stats_power_only` when it has >= 3 windows, otherwise falls back to `stats_all_valid` with a warning.

**Specific scenarios:**

| Scenario | n_valid | n_power | Gate source | Warning emitted? |
|----------|---------|---------|-------------|:--:|
| Healthy | 8 | 6 | `stats_power_only` | No |
| Mostly low-power | 8 | 2 | `stats_all_valid` (fallback) | Yes: `"wfo_insufficient_power_windows"` |
| All low-power | 8 | 0 | `stats_all_valid` (fallback) | Yes: `"wfo_all_windows_low_power"` |
| All invalid | 0 | 0 | Neither (WFO gate = `"info"`, not `"pass"`/`"fail"`) | Yes: `"wfo_no_valid_windows"` |
| Mixed | 6 | 4 | `stats_power_only` | No |

**Implementation rule:** The `wfo_robustness` gate in `decision.py` currently reads `stats_all_valid` (via `summary.get("win_rate")`). The proposed change:

```python
# In decision.py, WFO gate section:
power_stats = summary.get("stats_power_only", {})
all_stats = summary.get("stats_all_valid", {})

power_n = int(power_stats.get("n_windows", 0))
if power_n >= 3:
    gate_source = power_stats
    gate_source_label = "power_only"
else:
    gate_source = all_stats
    gate_source_label = "all_valid"

n_windows = int(gate_source.get("n_windows", 0))
win_rate = float(gate_source.get("win_rate", 0.0))
```

### 2.4 Reporting Format

Every WFO report MUST include both blocks with explicit labels:

```
## WFO Aggregation

### All valid windows (includes low-power)
- n_windows: 6
- win_rate: 0.500
- median_delta: +1.23
- worst_delta: -8.45

### Power-only windows (min_trades_for_power = 10)
- n_windows: 4
- win_rate: 0.750
- median_delta: +3.67
- worst_delta: -2.10

Gate source: power_only (4 >= 3 threshold)
```

This dual reporting prevents silent information hiding while making the gate source explicit.

---

## 3. When to Abandon Window-Level Sharpe/Score

### 3.1 Abandonment Criteria

Window-level composite score (the objective function) and per-window Sharpe should be **demoted to diagnostic-only** when ANY of the following holds:

**Criterion A: Median trade count below N_min.**

```python
median_trades = median(
    min(row["trade_count_candidate"], row["trade_count_baseline"])
    for row in rows if row["valid_window"]
)
if median_trades < min_trades_for_power:
    abandon_window_score = True
```

Rationale: If the typical window doesn't have enough trades, the composite score's trade-count bonus (`min(n/50, 1) * 5.0`) and Sharpe component (`8.0 * max(0, sharpe)`) are dominated by estimation noise. A 3-trade window's Sharpe has a standard error of approximately `sqrt((1 + sharpe^2/2) / (n-1))` which at n=3 is > 1.0 even for Sharpe = 0. The score is noise.

**Criterion B: More than half of valid windows are low-power.**

```python
low_power_ratio = low_trade_windows_count / max(valid_windows_count, 1)
if low_power_ratio > 0.50:
    abandon_window_score = True
```

Rationale: If the majority of your evidence base is underpowered, the aggregate (median, win_rate) is driven by noise windows. Trade-level analysis uses all trades regardless of which window they fall in.

**Criterion C: Window length produces < 500 return observations for Sharpe.**

```python
# 6-month window at 4H bars = ~1095 bars
# Minimum for Sharpe estimation with block bootstrap:
#   block_size * 2 = 40 (smallest bootstrap threshold)
# Minimum for Sharpe SE < 0.5:
#   n > (1 + sharpe^2/2) / 0.25 ~ 500 for sharpe ~ 1
window_bars = window_length_days * 6  # 4H bars per day
if window_bars < 500:
    abandon_window_sharpe = True
```

Note: Standard 6-month windows produce ~1095 bars, which is adequate for Sharpe estimation. This criterion catches custom short windows (e.g., 2-month test periods).

### 3.2 What "Abandon" Means in Practice

"Abandon" does NOT mean "stop computing." It means:

1. **Compute and report** the window-level scores and Sharpe ratios as before (they appear in `wfo_per_round_metrics.csv`).
2. **Do not gate on them.** The `wfo_robustness` gate switches to trade-level evidence when abandonment criteria are met.
3. **Add explicit flag** to `wfo_summary.json`:

```json
{
  "window_score_abandoned": true,
  "abandonment_reason": "median_trades_below_power (median=4, threshold=10)",
  "primary_evidence_source": "trade_level"
}
```

4. **The decision gate** checks this flag and requires the `trade_level` suite result when `window_score_abandoned = true`.

### 3.3 Implementation Pseudocode

```python
# In WFOSuite.run(), after computing rows and aggregation:
median_min_trades = median(
    min(r["trade_count_candidate"], r["trade_count_baseline"])
    for r in rows if r["valid_window"]
) if any(r["valid_window"] for r in rows) else 0

low_power_ratio = low_trade_windows_count / max(valid_windows_count, 1)

abandon = (
    median_min_trades < min_trades_for_power
    or low_power_ratio > 0.50
)

summary["window_score_abandoned"] = abandon
if abandon:
    summary["abandonment_reason"] = (
        f"median_trades_below_power (median={median_min_trades}, "
        f"threshold={min_trades_for_power})"
        if median_min_trades < min_trades_for_power
        else f"majority_low_power (ratio={low_power_ratio:.2f})"
    )
    summary["primary_evidence_source"] = "trade_level"
```

---

## 4. Alternative Evaluation Plan: Trade-Level Block Bootstrap

When WFO window-level scores are abandoned (Section 3), the following trade-level evaluation becomes the primary evidence for the candidate vs baseline comparison.

### 4.1 Trade Matching (Already Implemented)

The `TradeLevelSuite` in `validation/suites/trade_level.py` matches candidate trades to baseline trades by entry timestamp with tolerance = 4 hours (1 bar at H4 resolution).

**Required diagnostic:** Report match rate. If match_rate < 0.80, emit warning `"low_match_rate"` and flag that paired analysis may be unreliable.

### 4.2 What to Bootstrap

Bootstrap THREE quantities from the matched-trade delta series. Each serves a different diagnostic purpose:

**Quantity 1: Mean per-trade PnL delta** (primary gate metric)

```python
deltas_pnl = [pair["delta_pnl"] for pair in matched_trades]
# Bootstrap statistic: mean(resampled_deltas)
```

- **Why:** This is the most direct measure of "does the candidate make more money per trade?" It is denominated in dollars and directly interpretable.
- **Gate criterion:** 95% CI excludes zero on the favorable side, OR P(delta > 0) >= 0.80.

**Quantity 2: Mean per-trade return delta** (cost-sensitivity check)

```python
deltas_return = [pair["cand_return_pct"] - pair["base_return_pct"] for pair in matched_trades]
# Bootstrap statistic: mean(resampled_deltas)
```

- **Why:** Return-based delta removes position-sizing effects, isolating exit timing/quality. If PnL delta is positive but return delta is near zero, the candidate wins only by sizing (leverage), not by alpha. This is the cross-check against pure size-effect artifacts.
- **Not a gate** but mandatory reporting.

**Quantity 3: Score delta** (compatibility with window-level scoring)

```python
# Compute per-trade "micro-score" contribution is NOT recommended.
# Instead, compute score delta on the FULL matched-trade series:
# 1. Aggregate matched candidate trades -> synthetic summary (CAGR, MDD, Sharpe, PF, n_trades)
# 2. Aggregate matched baseline trades -> synthetic summary
# 3. score_delta = objective(candidate_summary) - objective(baseline_summary)
# 4. Bootstrap: resample matched pairs, recompute aggregate score_delta each time
```

- **Why:** Provides a bridge between trade-level and window-level scoring. If bootstrap score_delta is positive but WFO window score_delta is negative, the discrepancy is explained by WFO's data waste (30% of trades outside OOS windows) and equal-weighting bias.
- **Not a gate** but mandatory reporting.

### 4.3 Block Bootstrap Specification

**Method:** Circular moving block bootstrap (Politis & Romano 1994), identical to the implementation in `v10/research/bootstrap.py`.

**Block length selection:**

| Block size (in trades) | Maps to (approximate) | Purpose |
|------------------------|----------------------|---------|
| 5 trades | ~2-3 months at V10 frequency | Captures short-range autocorrelation (same-regime trade clusters) |
| 8 trades | ~4-6 months | Matches WFO window length for comparability |
| 12 trades | ~8-12 months | Captures regime-cycle-length dependence |

**Why these specific sizes:**
- V10 produces ~14 trades/year = ~7 trades per 6-month WFO window.
- Block size of 5 captures within-regime correlation (typical regime lasts 2-4 months, producing 2-5 trades).
- Block size of 8 approximately matches the WFO window's information content, making bootstrap SE comparable to WFO SE. This enables a direct comparison: if bootstrap SE << WFO SE, it proves WFO is wasting information.
- Block size of 12 spans approximately one regime cycle (the time for the market to move through 2-3 regime phases).

**For strategies with different trade frequency:** Scale block sizes proportionally:

```python
trades_per_year = total_matched_trades / total_years
block_sizes = [
    max(3, round(trades_per_year * 0.15)),   # ~2 months of trades
    max(5, round(trades_per_year * 0.40)),   # ~5 months of trades
    max(8, round(trades_per_year * 0.70)),   # ~8 months of trades
]
```

**Number of resamples:** 10,000 (not 2,000). Trade-level bootstrap is fast (no backtest rerun, just array resampling) so there is no cost reason to use fewer. More resamples reduce Monte Carlo error in the CI bounds.

**Seed:** Same as validation config seed (default: 1337) for reproducibility.

### 4.4 Implementation Specification

```python
def trade_level_block_bootstrap(
    matched_trades: list[dict],
    metric: str,  # "delta_pnl" | "delta_return_pct" | "score_delta"
    block_sizes: list[int],
    n_bootstrap: int = 10_000,
    seed: int = 1337,
) -> list[dict]:
    """
    Returns one result dict per block_size:
    {
        "metric": str,
        "block_size": int,
        "n_matched": int,
        "observed_mean": float,
        "bootstrap_mean": float,
        "bootstrap_std": float,
        "ci_lower_95": float,
        "ci_upper_95": float,
        "p_positive": float,
        "n_bootstrap": int,
    }
    """
```

**For `metric = "score_delta"`**, each bootstrap iteration:
1. Resample matched pairs using block indices
2. Aggregate resampled candidate trades into a synthetic summary dict
3. Aggregate resampled baseline trades into a synthetic summary dict
4. Compute `_objective_without_reject(cand_summary) - _objective_without_reject(base_summary)`

This is more expensive (~10x) than mean-delta bootstrap but still completes in < 30 seconds for 100 trades x 10,000 resamples.

### 4.5 CLI Integration

```bash
# Enable trade-level bootstrap as primary (when WFO is underpowered)
python -m validation.cli ... --suite all --trade-level \
    --bootstrap-block-sizes 5,8,12 --bootstrap 10000

# Quick mode (for iteration during development)
python -m validation.cli ... --suite trade --bootstrap 2000
```

### 4.6 Output Artifacts

| File | Contents |
|------|----------|
| `results/matched_trades.csv` | Per-pair: entry_time, delta_pnl, delta_return_pct |
| `results/trade_level_bootstrap.csv` | Per block_size per metric: CI, p_positive, observed |
| `results/trade_level_summary.json` | Gate-relevant fields: p_positive, ci_lower, ci_upper, match_rate |

### 4.7 Interpretation Guide

| Observation | Interpretation | Action |
|-------------|---------------|--------|
| All 3 block sizes agree on sign, P > 0.80 | Strong evidence of real effect | Weight as primary evidence |
| Block sizes disagree on sign | Autocorrelation structure matters; effect is fragile | Investigate which regimes drive the disagreement |
| P(delta > 0) in [0.60, 0.80] across all block sizes | Weak-to-moderate evidence | HOLD; collect more live data |
| PnL delta positive but return delta near zero | Candidate wins by sizing, not by alpha | Flag as `"size_effect_dominant"`; not sufficient for PROMOTE alone |
| Score delta negative but PnL delta positive | Scoring function penalizes low trade count or high drawdown | Report discrepancy; PnL delta is the ground truth |

---

## 5. Decision Gate Integration

### 5.1 New Fields in `decision.json`

Add the following fields to the top level of decision.json:

```json
{
  "wfo_diagnostics": {
    "n_windows_total": 8,
    "invalid_windows_count": 2,
    "low_trade_windows_count": 4,
    "power_windows_count": 2,
    "window_score_abandoned": true,
    "abandonment_reason": "majority_low_power (ratio=0.67)",
    "primary_evidence_source": "trade_level",
    "gate_source": "all_valid",
    "gate_source_reason": "power_windows < 3"
  }
}
```

### 5.2 Warning Escalation Rules

Warnings must propagate to the decision gate with explicit severity:

| Condition | Warning key | Severity | Effect on verdict |
|-----------|------------|----------|-------------------|
| `invalid_windows_count > 0` | `"wfo_has_invalid_windows"` | info | Logged in `decision.json.warnings`; no verdict impact |
| `invalid_windows_count > n_windows_total / 2` | `"wfo_majority_invalid"` | caution | Verdict cannot be PROMOTE; max = HOLD |
| `low_trade_windows_count > 0` | `"wfo_has_low_power_windows"` | info | Logged; no verdict impact |
| `low_trade_windows_count == n_windows_valid` | `"wfo_all_windows_low_power"` | caution | WFO gate result is `"info"` (neither pass nor fail); trade-level required |
| `window_score_abandoned = true` | `"wfo_score_abandoned"` | caution | WFO gate result is `"info"`; verdict requires trade-level evidence |
| `window_score_abandoned = true` AND trade_level suite not run | `"wfo_abandoned_no_fallback"` | hard | Verdict = HOLD (cannot promote without evidence) |

### 5.3 Preventing False Confidence

**Problem:** A WFO run with 6/8 low-power windows and 2 power windows that happen to be positive can report `stats_power_only.win_rate = 1.0`, which looks perfect but is meaningless (n=2).

**Rules to prevent this:**

**Rule 1: Minimum power windows for WFO gate pass.**

```python
# WFO gate can only PASS (not just "info") if:
power_n = int(power_stats.get("n_windows", 0))
if power_n < 3:
    # Cannot pass WFO gate on power_only; fall back to all_valid
    # If all_valid also has n < 3, WFO gate = "info" (no opinion)
    ...
```

**Rule 2: Confidence discount for small n.**

When the WFO gate passes but `n_windows` is small (3-5), add a disclosure:

```json
{
  "gate_name": "wfo_robustness",
  "passed": true,
  "severity": "soft",
  "detail": "win_rate=1.000, n_power_windows=3 (LOW CONFIDENCE: n < 6)",
  "confidence": "low"
}
```

The `"confidence": "low"` field is advisory. It does not change the gate outcome, but it MUST appear in the decision report and human-readable summary.

**Rule 3: Cross-validate WFO gate with trade-level when both are available.**

If WFO gate passes but trade-level bootstrap shows P(candidate > baseline) < 0.50, emit:

```json
{
  "warning": "wfo_trade_level_contradiction",
  "detail": "WFO win_rate=0.75 but trade_level P(delta>0)=0.42",
  "severity": "caution"
}
```

This contradiction means WFO is likely driven by a few large trades that happened to land in the right windows. The trade-level result is more trustworthy (more data, no windowing bias).

**Rule 4: Never promote on WFO alone when trade-level is available and contradicts.**

```python
# In decision.py:
wfo_passed = wfo_gate.passed
trade_level_p = deltas.get("matched_trade_p_positive")

if wfo_passed and trade_level_p is not None and trade_level_p < 0.50:
    # Override: WFO pass is unreliable
    warnings.append("wfo_trade_level_contradiction")
    # Downgrade WFO to "info"
    wfo_gate.passed = False
    wfo_gate.detail += " [overridden by trade-level contradiction]"
```

### 5.4 Modified Decision Flow

```
1. Run all suites (WFO, bootstrap, trade_level, holdout, etc.)

2. Check WFO diagnostics:
   a. If window_score_abandoned:
      - WFO gate = "info" (does not contribute to pass/fail)
      - Require trade_level suite result
   b. If not abandoned but power_n < 3:
      - WFO gate uses stats_all_valid
      - Emit "low confidence" advisory
   c. If not abandoned and power_n >= 3:
      - WFO gate uses stats_power_only (normal path)

3. Apply cross-validation (Rule 3 above)

4. Evaluate hard gates (lookahead, full_harsh_delta, holdout)
5. Evaluate soft gates (wfo_robustness, bootstrap, trade_level)
6. Apply verdict rules (REJECT / HOLD / PROMOTE)
```

### 5.5 Summary Decision Table

| WFO state | Trade-level available? | Bootstrap P >= 0.80? | Verdict ceiling |
|-----------|:---:|:---:|-----------------|
| Healthy (n_power >= 6, win_rate >= 0.60) | Either | Either | PROMOTE |
| Healthy but n_power = 3-5 | Yes, agrees | Either | PROMOTE (low confidence note) |
| Healthy but n_power = 3-5 | No | Either | HOLD |
| Abandoned (majority low-power) | Yes, P >= 0.80 | Yes | PROMOTE (trade-level primary) |
| Abandoned | Yes, P < 0.80 | Any | HOLD |
| Abandoned | No | Any | HOLD (no primary evidence) |
| All invalid | Any | Any | WFO = info; other gates decide |
| WFO pass, trade-level contradicts | Yes, P < 0.50 | Any | HOLD (contradiction) |

---

## 6. Parameter Equivalence Disclaimer

This policy does NOT claim that any specific parameter value in one space maps to a specific value in another space (e.g., "aggressive=0.28 is equivalent to aggressive=0.04 under different cost scenarios"). Such claims require:

1. **A parameter mapping heatmap**: Run the objective function across a grid of parameter values under both cost scenarios and identify the iso-score contours.
2. **A proof that the mapping is monotonic**: Show that the ordering of parameter values by score is preserved across scenarios.
3. **Cross-validation of the mapping**: Verify that the mapped parameter produces similar trade-level behavior (entry/exit timing, position sizes) under both scenarios.

Until such analysis is conducted and documented, treat parameters as scenario-specific and do not assume equivalence.

---

## 7. Implementation Checklist

Each rule in this document maps to a specific code change:

| Rule | File | Change type | Priority |
|------|------|-------------|:--------:|
| 1.3: Raise default `min_trades_for_power` to 10 | `validation/config.py:120` | Edit default | P0 |
| 2.3: WFO gate reads `stats_power_only` with fallback | `validation/decision.py` (WFO gate section) | Edit | P0 |
| 2.3: Emit warnings for low-power scenarios | `validation/suites/wfo.py` | Add warning logic | P0 |
| 3.3: Compute `window_score_abandoned` flag | `validation/suites/wfo.py` | Add to summary | P1 |
| 4.4: Implement `trade_level_block_bootstrap()` with 3 metrics | `validation/suites/trade_level.py` | Add function | P1 |
| 4.3: Configurable block sizes for trade-level | `validation/config.py` | Add field | P1 |
| 4.6: Write `trade_level_bootstrap.csv` | `validation/suites/trade_level.py` | Add output | P1 |
| 5.1: Add `wfo_diagnostics` to decision.json | `validation/decision.py` | Add to verdict | P1 |
| 5.2: Warning escalation rules | `validation/decision.py` | Add logic | P1 |
| 5.3 Rule 1: Min power windows for gate pass | `validation/decision.py` | Edit WFO gate | P0 |
| 5.3 Rule 3: Cross-validate WFO vs trade-level | `validation/decision.py` | Add logic | P2 |
| 5.3 Rule 4: Contradiction override | `validation/decision.py` | Add logic | P2 |
| 5.4: Modified decision flow | `validation/decision.py` | Restructure WFO section | P1 |

**Priority key:** P0 = implement before next validation run. P1 = implement before next promotion decision. P2 = implement when trade-level suite is routinely enabled.
