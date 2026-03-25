# Spec: Trade-Level Suite + Acceptance Gates for Sparse-Trade Regimes

**Status:** Implementable spec — for Codex implementation in Step 3B
**Scope:** When to trigger, matching rules, output schemas, bootstrap design, gate integration
**Prerequisite reading:**
- `reports/wfo_policy_low_trade.md` (WFO low-power policy)
- `btc-spot/validation/suites/trade_level.py` (current implementation)
- `btc-spot/validation/decision.py` (gate evaluation)

---

## 1. When to Trigger the Trade-Level Suite

### 1.1 Trigger Conditions

The trade-level suite MUST run when **any** of the following hold:

| # | Condition | Fields used | Source |
|---|-----------|------------|--------|
| T1 | Explicitly enabled | `validation_config.trade_level == True` | CLI `--trade-level` |
| T2 | Suite group includes it | `validation_config.suite in {"trade", "all"}` | CLI `--suite` |
| T3 | Auto-trigger: WFO is low-power | See §1.2 | Computed from WFO summary |
| T4 | Auto-trigger: sparse trade count | See §1.3 | Computed from backtest results |

**T3 and T4 require `auto_trade_level = True`** (config.py:156). When `auto_trade_level = False`, only T1 and T2 apply.

### 1.2 WFO Low-Power Detection (T3)

Read from `wfo_summary.json` (produced by the WFO suite):

```python
wfo_data = results.get("wfo", {}).data
summary = wfo_data.get("summary", {})
stats_power = summary.get("stats_power_only", {})
power_windows = int(stats_power.get("n_windows", 0))
valid_windows = int(summary.get("n_windows_valid", 0))
low_trade_count = int(summary.get("low_trade_windows_count", 0))

low_trade_ratio = low_trade_count / max(valid_windows, 1)

wfo_low_power = (power_windows < 3) or (low_trade_ratio > 0.5)
```

When `wfo_low_power == True`, auto-trigger the trade-level suite with bootstrap.

**Implementation note:** The WFO suite runs before the trade-level suite in the execution order (already guaranteed by `SUITE_ORDER` in `validation/runner.py`). The runner must check the WFO result and enable trade-level if the auto-trigger fires. This is already partially implemented via `auto_trade_level` logic in `TradeLevelSuite.skip_reason()` (trade_level.py:474-479). Extend the skip logic:

```python
def skip_reason(self, ctx: SuiteContext) -> str | None:
    cfg = ctx.validation_config
    if cfg.trade_level or cfg.suite in {"trade", "all"}:
        return None  # T1, T2: explicitly enabled

    if cfg.auto_trade_level:
        wfo_result = ctx.prior_results.get("wfo")
        if wfo_result is not None and wfo_result.status not in {"skip", "error"}:
            summary = wfo_result.data.get("summary", {})
            power_stats = summary.get("stats_power_only", {})
            power_n = int(power_stats.get("n_windows", 0))
            valid_n = int(summary.get("n_windows_valid", 0))
            low_trade_n = int(summary.get("low_trade_windows_count", 0))
            low_ratio = low_trade_n / max(valid_n, 1)
            if power_n < 3 or low_ratio > 0.5:
                return None  # T3: auto-triggered

        # T4: sparse trade count (checked against backtest summary)
        backtest_result = ctx.prior_results.get("backtest")
        if backtest_result is not None:
            for scenario_data in backtest_result.data.get("scenarios", {}).values():
                cand_trades = int(scenario_data.get("candidate", {}).get("trades", 0))
                base_trades = int(scenario_data.get("baseline", {}).get("trades", 0))
                min_trades = min(cand_trades, base_trades)
                total_years = _backtest_years(cfg)
                if total_years > 0 and min_trades / total_years < 20:
                    return None  # T4: fewer than 20 trades/year

    return "trade-level not triggered"
```

### 1.3 Sparse-Trade Detection (T4)

A strategy is "sparse-trade" when:

```
min(candidate_trades, baseline_trades) / backtest_years < 20
```

Where `backtest_years` is derived from `(end - start)` in the validation config, minus `warmup_days`. At H4 resolution with a typical 7-year backtest (2019-2026), 20 trades/year = ~140 total trades, or ~3 trades per 6-month WFO window.

**Rationale:** At < 20 trades/year, WFO windows contain < 3 trades on average, making window-level score comparisons statistically meaningless (see `wfo_policy_low_trade.md` §1.3).

### 1.4 Execution Dependencies

```
data_integrity → backtest → wfo → trade_level → decision
```

The trade-level suite requires:
- `backtest` results (trades, fills, equity) for both candidate and baseline
- `wfo` result (for auto-trigger detection and window definitions)
- Feed data (h4_bars, d1_bars) for regime classification

---

## 2. Trade Matching Rules

### 2.1 Entry Timestamp Tolerance

```python
MATCH_TOLERANCE_MS = H4_BAR_MS  # 14,400,000 ms = 4 hours = 1 H4 bar
```

A candidate trade matches a baseline trade when:
1. `abs(candidate.entry_ts_ms - baseline.entry_ts_ms) <= MATCH_TOLERANCE_MS`
2. `candidate.side == baseline.side` (both long or both short)

**Rationale:** ±1 bar tolerance accounts for minor timing differences when two config variants react to the same signal with slight parameter differences (e.g., different HMA period causing entry on the adjacent bar).

### 2.2 Tie-Breaking Rules

When multiple baseline trades are within tolerance of a single candidate trade, select the one with the **smallest tuple**:

```python
tiebreak_key = (
    abs(candidate_entry_ms - baseline_entry_ms),  # closest first
    baseline_entry_ms,                              # earlier baseline first
    baseline_trade_id,                              # lower ID first (deterministic)
)
```

This is already implemented in `_match_trades()` (trade_level.py:189-209). **No change needed.**

### 2.3 One-to-One Constraint

Each baseline trade may match at most one candidate trade. Once matched, it is removed from the candidate pool (`used_baseline_indices` set). This prevents double-counting.

### 2.4 Handling Adds (Position Increases)

**Definition:** An "add" is a trade where `exposure_at_entry > 0` (position already exists when the new entry fires). The engine records each entry-to-exit cycle as a separate `Trade` object, so adds appear as distinct trades with overlapping time windows.

**Matching policy: Treat adds as independent trades.**

- Each add produces its own `Trade` object with its own `entry_ts_ms`, `exit_ts_ms`, and `pnl`.
- Adds are matched to baseline adds using the same tolerance and tie-breaking rules.
- An add in the candidate may match a non-add in the baseline (or vice versa) if the entry timestamps are within tolerance. This is correct — it captures the case where the candidate decided to pyramid while the baseline did not.

**Diagnostic: Report add-matching quality.**

```python
# In matched trade output, flag adds:
"candidate_is_add": bool(float(matched_cand["exposure_at_entry"]) > 0.01),
"baseline_is_add": bool(float(matched_base["exposure_at_entry"]) > 0.01),
"add_mismatch": candidate_is_add != baseline_is_add,
```

If `sum(add_mismatch) / n_matched > 0.30`, emit warning `"high_add_mismatch_rate"`. This signals that the two configs have substantially different pyramiding behavior, and per-trade deltas may be dominated by position-sizing differences rather than signal quality.

### 2.5 Unmatched Trades

Trades that fail to match are separated into:
- `candidate_only_trades.csv`: Candidate trades with no baseline counterpart
- `baseline_only_trades.csv`: Baseline trades with no candidate counterpart

Already implemented. **No change needed.**

### 2.6 Match Rate Quality Gate

```python
match_rate = n_matched / max(n_candidate_trades, 1)
```

| match_rate | Interpretation | Action |
|-----------|---------------|--------|
| >= 0.80 | Good alignment | Proceed with paired analysis |
| 0.50 - 0.80 | Moderate divergence | Emit warning `"moderate_match_rate"`; paired analysis is usable but less reliable |
| < 0.50 | Severe divergence | Emit warning `"low_match_rate"`; paired bootstrap CI should be interpreted with caution; consider unpaired analysis |

---

## 3. Required Outputs

### 3.1 CSV: `trades_candidate.csv` / `trades_baseline.csv`

**Already implemented.** Schema (22 columns):

| Column | Type | Description |
|--------|------|-------------|
| `trade_id` | int | Sequential trade ID within the backtest |
| `side` | str | `"long"` or `"short"` |
| `entry_ts` | str | ISO 8601 UTC timestamp |
| `exit_ts` | str | ISO 8601 UTC timestamp |
| `return_pct` | float | Per-trade return as a decimal (0.05 = 5%) |
| `pnl_usd` | float | Absolute P&L in USD |
| `fees_usd` | float | Total fees for this trade |
| `n_buy_fills` | int | Number of buy fills during trade |
| `n_sell_fills` | int | Number of sell fills during trade |
| `entry_reason` | str | Strategy-level entry reason |
| `exit_reason` | str | Strategy-level exit reason |
| `max_exposure_during_trade` | float | Peak exposure as fraction of NAV |
| `exposure_at_entry` | float | Exposure at entry bar (> 0 implies add) |
| `exposure_at_exit` | float | Exposure at exit bar |
| `entry_ts_ms` | int | Entry timestamp in epoch milliseconds |
| `exit_ts_ms` | int | Exit timestamp in epoch milliseconds |
| `entry_price` | float | BTC price at entry |
| `exit_price` | float | BTC price at exit |
| `qty` | float | BTC quantity |
| `days_held` | float | Trade duration in days |
| `regime` | str | D1 regime at entry (`BULL`, `BEAR`, `CAUTION`, `UNKNOWN`) |
| `label` | str | `"candidate"` or `"baseline"` |

### 3.2 CSV: `matched_trades.csv`

**Already implemented.** Schema (28 columns). **Add 3 new columns** for add diagnostics:

| New column | Type | Description |
|-----------|------|-------------|
| `candidate_is_add` | int | 1 if `candidate.exposure_at_entry > 0.01` |
| `baseline_is_add` | int | 1 if `baseline.exposure_at_entry > 0.01` |
| `add_mismatch` | int | 1 if `candidate_is_add != baseline_is_add` |

### 3.3 CSV: `window_trade_counts.csv`

**Already implemented.** No changes needed.

### 3.4 CSV: `regime_trade_summary.csv`

**Already implemented.** No changes needed.

### 3.5 JSON: `trade_level_summary.json`

**Already implemented.** Extend with additional fields for gate integration:

```json
{
  "scenario": "harsh",
  "candidate_trades": 142,
  "baseline_trades": 138,
  "matched_trades": 125,
  "candidate_only_trades": 17,
  "baseline_only_trades": 13,
  "match_rate": 0.880282,
  "match_rate_warning": null,

  "matched_delta_pnl_mean": 12.345678,
  "matched_delta_pnl_median": 8.234567,
  "matched_delta_return_mean": 0.001234,
  "matched_delta_return_median": 0.000876,
  "matched_win_rate_baseline": 0.456000,
  "matched_win_rate_candidate": 0.512000,
  "matched_win_rate_delta": 0.056000,
  "matched_p_positive": 0.560000,

  "add_diagnostics": {
    "candidate_adds": 45,
    "baseline_adds": 38,
    "add_mismatch_count": 12,
    "add_mismatch_rate": 0.096000
  },

  "trade_level_bootstrap": {
    "mean_diff": 0.000234,
    "ci95_low": -0.000012,
    "ci95_high": 0.000480,
    "p_gt_0": 0.8234,
    "n_obs": 8760,
    "block_len": 168,
    "n_resamples": 10000,
    "seed": 1337,
    "ci_crosses_zero": true,
    "small_improvement_threshold": 0.0002,
    "is_small_improvement": false,
    "all_blocks": [
      { "block_len": 42, "mean_diff": 0.000234, "ci95_low": ..., "p_gt_0": ... },
      { "block_len": 84, "mean_diff": 0.000234, "ci95_low": ..., "p_gt_0": ... },
      { "block_len": 168, "mean_diff": 0.000234, "ci95_low": ..., "p_gt_0": ... }
    ],
    "n_timestamps": 8760
  }
}
```

### 3.6 JSON: `bootstrap_return_diff.json`

**Already implemented.** Contains the selected block's bootstrap summary. No changes needed.

### 3.7 Markdown: `trade_level_analysis.md`

**Already implemented.** Extend to include:
- Add diagnostics section (add mismatch summary)
- Bootstrap interpretation section (see §4.7)

---

## 4. Bootstrap Design

### 4.1 What to Bootstrap

**Primary series:** `r_diff` — the bar-by-bar (H4) return difference between candidate and baseline NAV curves.

```python
# Already implemented in _aligned_nav_return_diff():
cand_ret = diff(cand_nav) / cand_nav[:-1]
base_ret = diff(base_nav) / base_nav[:-1]
r_diff = cand_ret - base_ret  # one value per aligned H4 bar
```

**Why `r_diff` rather than per-trade PnL deltas:**
- `r_diff` uses ALL available data (every H4 bar), not just bars where trades occur. For a sparse-trade strategy with ~140 trades across 8,760 H4 bars, per-trade bootstrap uses 1.6% of available information.
- `r_diff` naturally incorporates position-sizing, fee drag, and time-in-market effects that per-trade PnL misses.
- `r_diff` time series has known autocorrelation structure that the block bootstrap handles correctly.
- Consistency: matches the existing `paired_block_bootstrap()` approach in `v10/research/bootstrap.py`.

### 4.2 Block Length Selection for H4

| Block length (H4 bars) | Calendar equivalent | Rationale |
|------------------------|-------------------|-----------|
| **42** | ~7 days (1 week) | Captures intra-week momentum/mean-reversion patterns; minimum viable block for serial dependence |
| **84** | ~14 days (2 weeks) | Spans typical trade duration (avg_hold ~3-5 days) plus reentry cooldown |
| **168** | ~28 days (1 month) | Captures regime-transition effects; a regime phase (BULL→CAUTION) typically lasts 1-3 months at D1 resolution, but H4 sub-patterns within a regime cluster over ~1 month |

```python
BOOTSTRAP_BLOCK_LENGTHS = (42, 84, 168)  # already defined in trade_level.py:30
```

**Why these specific lengths:**

1. **42 bars (7 days):** The minimum block length that captures meaningful serial dependence. H4 returns exhibit momentum clustering over 3-7 day windows (driven by the same HMA/ATR signals that generate entries). Shorter blocks (e.g., 6 bars = 1 day) would not preserve within-trade return autocorrelation.

2. **84 bars (14 days):** The median trade duration is 3-5 days, and the entry cooldown is 3 bars (~12h). A 14-day block encompasses a typical full trade cycle (entry → hold → exit → cooldown → re-entry). This block length makes each bootstrap resample preserve the trade-level structure.

3. **168 bars (28 days):** Regime transitions at the D1 level (50/200 EMA crossover) produce H4-level clustering effects that span ~1 month. The 28-day block captures the autocorrelation from regime-dependent entry frequency changes (e.g., fewer trades in CAUTION regime).

**Selection rule (already implemented):**

```python
n_obs = len(r_diff)
eligible = [b for b in BOOTSTRAP_BLOCK_LENGTHS if n_obs >= b]
selected_block_len = eligible[-1] if eligible else BOOTSTRAP_BLOCK_LENGTHS[0]
```

Use the **largest eligible** block length: it produces the most conservative (widest) confidence intervals by preserving longer-range dependence. Smaller blocks produce tighter CIs but may understate uncertainty.

### 4.3 Number of Resamples

```python
BOOTSTRAP_RESAMPLES = 10_000  # already defined in trade_level.py:31
```

**Rationale:** 10,000 resamples produce Monte Carlo standard error of ~0.5% on the 2.5th/97.5th percentiles (SE of a percentile ≈ `sqrt(p*(1-p)/n)` ≈ `sqrt(0.025*0.975/10000)` ≈ 0.0016). This is negligible relative to the bootstrap CI width.

### 4.4 Bootstrap Statistic: The Gate Metric

The bootstrap produces three quantities per block length:

| Statistic | Formula | Role |
|-----------|---------|------|
| `mean_diff` | `mean(r_diff)` observed | Point estimate of per-bar return advantage |
| `ci95_low`, `ci95_high` | 2.5th/97.5th percentile of bootstrap mean distribution | 95% confidence interval for `mean_diff` |
| `p_gt_0` | `P(bootstrap_mean > 0)` | One-sided test: probability that candidate outperforms |

**The gate metric** is the tuple `(mean_diff, ci95_low, ci95_high, p_gt_0)` from the **selected** (largest eligible) block length.

### 4.5 Gate Criteria

The trade-level bootstrap gate has two roles:

**Role A: Primary gate when WFO is low-power.**

When `wfo_low_power == True`, the trade-level bootstrap becomes the primary evidence for the candidate's superiority. The gate evaluates:

```python
# Sufficient evidence for PROMOTE:
bootstrap_promotes = (
    p_gt_0 >= 0.80                              # 80%+ probability of improvement
    and not (ci_crosses_zero and is_small_improvement)  # not ambiguous noise
)

# Sufficient evidence for REJECT:
bootstrap_rejects = (
    p_gt_0 < 0.20                               # 80%+ probability of degradation
    and ci95_high < 0.0                          # entire CI below zero
)

# Otherwise: HOLD (insufficient evidence)
```

**Role B: Advisory when WFO has power.**

When WFO has sufficient power windows, the trade-level bootstrap is a soft advisory that can trigger a HOLD if it contradicts WFO (see `wfo_policy_low_trade.md` §5.3 Rule 4):

```python
if wfo_gate_passed and p_gt_0 < 0.50:
    # Trade-level contradicts WFO → downgrade to HOLD
    warnings.append("wfo_trade_level_contradiction")
```

### 4.6 Interpretation When CI Crosses Zero

| Scenario | `ci95_low` | `ci95_high` | `mean_diff` | `p_gt_0` | Interpretation |
|----------|-----------|-------------|-------------|----------|---------------|
| **Clear winner** | > 0 | > 0 | > 0 | > 0.975 | Candidate is statistically significantly better |
| **Likely better** | < 0 | > 0 | > 0 | 0.80-0.975 | Candidate probably better, but not at 95% level; effect size matters |
| **Inconclusive** | < 0 | > 0 | ~0 | 0.40-0.60 | Cannot distinguish from noise; collect more data |
| **Likely worse** | < 0 | > 0 | < 0 | 0.025-0.20 | Candidate probably worse |
| **Clear loser** | < 0 | < 0 | < 0 | < 0.025 | Candidate is statistically significantly worse |

**The `is_small_improvement` flag** catches the "technically positive but economically meaningless" case:

```python
SMALL_MEAN_IMPROVEMENT_THRESHOLD = 0.0002  # 2 basis points per bar

is_small_improvement = abs(mean_diff) <= SMALL_MEAN_IMPROVEMENT_THRESHOLD
```

At H4 resolution, 0.0002 per bar × 2,190 bars/year ≈ 0.44 (44% annualized). This threshold is intentionally generous — it catches only truly negligible effects. **Do not tighten it** without recalibrating against the strategy's expected return distribution.

When `ci_crosses_zero AND is_small_improvement`:
- The effect is both statistically ambiguous and economically small.
- Gate verdict: **HOLD** (cannot distinguish from zero).
- Message: `"Trade-level bootstrap inconclusive: CI crosses 0 and mean_diff within noise threshold"`

When `ci_crosses_zero AND NOT is_small_improvement`:
- The effect may be real but the sample is insufficient to confirm.
- If `p_gt_0 >= 0.80`: gate passes (preponderance of evidence).
- If `p_gt_0 < 0.80`: gate does not pass (insufficient evidence).

### 4.7 Bootstrap Report Section (for `trade_level_analysis.md`)

Append to the existing analysis report:

```markdown
## Bootstrap: NAV return difference

- Series: aligned H4 return differences (candidate - baseline)
- Observations: {n_obs}
- Selected block length: {block_len} bars (~{block_len/6:.0f} days)

### Results by block length

| Block | mean_diff | CI 95% | p(>0) | Crosses 0? |
|------:|----------:|-------:|------:|:----------:|
|    42 | +0.000234 | [-0.000012, +0.000480] | 0.823 | Yes |
|    84 | +0.000234 | [-0.000045, +0.000513] | 0.812 | Yes |
|   168 | +0.000234 | [-0.000089, +0.000557] | 0.795 | Yes |

### Gate evaluation (block_len=168)

- p_gt_0: 0.795 (threshold: 0.80) → **below threshold**
- CI crosses zero: Yes
- Small improvement: No (|mean_diff| = 0.000234 > 0.0002)
- Gate result: **HOLD** (p_gt_0 below 0.80 threshold)
```

---

## 5. Decision Gate Integration

### 5.1 Gate Wiring in `decision.py`

The trade-level bootstrap gate is evaluated in two contexts:

**Context 1: WFO low-power (already partially implemented).**

In `evaluate_decision()`, lines 366-394 handle this case. The current implementation checks `ci_crosses_zero AND is_small_improvement` to detect inconclusive results. **Extend** to also detect the positive case:

```python
# After existing trade_level_bootstrap extraction:
if wfo_low_power and trade_level_bootstrap:
    tl_p_gt_0 = _safe_float(trade_level_bootstrap.get("p_gt_0"), 0.5)
    tl_ci_low = _safe_float(trade_level_bootstrap.get("ci95_low"))
    tl_ci_high = _safe_float(trade_level_bootstrap.get("ci95_high"))
    tl_mean = _safe_float(trade_level_bootstrap.get("mean_diff"))
    ci_crosses = tl_ci_low <= 0.0 <= tl_ci_high
    is_small = abs(tl_mean) <= _safe_float(
        trade_level_bootstrap.get("small_improvement_threshold"), 0.0002
    )

    if ci_crosses and is_small:
        # Inconclusive: HOLD
        gate_passed = False
        detail = f"inconclusive: CI crosses 0, mean_diff={tl_mean:.8f} within noise"
    elif tl_p_gt_0 >= 0.80:
        # Sufficient evidence: contributes to PROMOTE
        gate_passed = True
        detail = f"p_gt_0={tl_p_gt_0:.4f} >= 0.80"
    elif tl_p_gt_0 < 0.20 and tl_ci_high < 0:
        # Clear degradation: contributes to REJECT
        gate_passed = False
        detail = f"p_gt_0={tl_p_gt_0:.4f} < 0.20, CI entirely below 0"
        failures.append("trade_level_bootstrap_degradation")
    else:
        # Insufficient evidence: HOLD
        gate_passed = False
        detail = f"p_gt_0={tl_p_gt_0:.4f}, insufficient evidence"

    gates.append(GateCheck(
        gate_name="trade_level_bootstrap",
        passed=gate_passed,
        severity="soft",
        detail=detail,
    ))
    if not gate_passed:
        failures.append("trade_level_bootstrap_inconclusive")
        reasons.append("Trade-level bootstrap insufficient under low-power WFO")
```

**Context 2: WFO has power — cross-validation advisory.**

When WFO has power and the trade-level suite was also run (e.g., explicitly enabled), add a cross-validation check:

```python
if not wfo_low_power and trade_level_bootstrap:
    tl_p_gt_0 = _safe_float(trade_level_bootstrap.get("p_gt_0"), 0.5)
    if wfo_gate_passed and tl_p_gt_0 < 0.50:
        gates.append(GateCheck(
            gate_name="trade_level_cross_check",
            passed=False,
            severity="soft",
            detail=f"WFO passed but trade-level P(delta>0)={tl_p_gt_0:.4f} < 0.50",
        ))
        warnings.append("wfo_trade_level_contradiction")
```

### 5.2 Verdict Table (Complete)

| WFO state | Trade-level P(>0) | CI | Verdict |
|-----------|:-----------------:|:--:|---------|
| Healthy (power >= 6, win_rate >= 0.60) | N/A or >= 0.50 | N/A | PROMOTE (WFO-driven) |
| Healthy | < 0.50 | N/A | HOLD (contradiction) |
| Low-power | >= 0.80 | Not (crosses 0 + small) | PROMOTE (trade-level primary) |
| Low-power | 0.50-0.80 | Any | HOLD (insufficient) |
| Low-power | < 0.50 | Any | HOLD |
| Low-power | < 0.20 | Entirely < 0 | REJECT signal (soft) |
| Low-power | Any | Crosses 0 + small effect | HOLD (inconclusive) |

### 5.3 Required Decision Metadata

Add to `DecisionVerdict.metadata`:

```python
"trade_level_diagnostics": {
    "triggered_by": "auto_wfo_low_power" | "explicit" | "auto_sparse_trade",
    "match_rate": 0.880,
    "n_matched": 125,
    "n_candidate": 142,
    "add_mismatch_rate": 0.096,
    "bootstrap_block_len": 168,
    "bootstrap_n_obs": 8760,
    "bootstrap_p_gt_0": 0.823,
    "bootstrap_gate_result": "HOLD",
}
```

---

## 6. Implementation Checklist

| # | Task | File | Priority |
|---|------|------|:--------:|
| 1 | Extend `skip_reason()` with T3/T4 auto-trigger logic | `validation/suites/trade_level.py` | P0 |
| 2 | Add `candidate_is_add`, `baseline_is_add`, `add_mismatch` to `matched_trades.csv` | `validation/suites/trade_level.py` | P1 |
| 3 | Add `add_diagnostics` block to `trade_level_summary.json` | `validation/suites/trade_level.py` | P1 |
| 4 | Add `match_rate_warning` field and emit warnings for low match rate | `validation/suites/trade_level.py` | P1 |
| 5 | Extend bootstrap gate logic in `evaluate_decision()` for both contexts | `validation/decision.py` | P0 |
| 6 | Add `trade_level_diagnostics` to `DecisionVerdict.metadata` | `validation/decision.py` | P1 |
| 7 | Add bootstrap interpretation section to `trade_level_analysis.md` | `validation/suites/trade_level.py` | P2 |
| 8 | Add cross-validation advisory (WFO vs trade-level contradiction) | `validation/decision.py` | P2 |
| 9 | Add integration test: sparse-trade scenario auto-triggers trade-level | `tests/` | P1 |
| 10 | Add integration test: bootstrap gate correctly handles all verdict paths | `tests/` | P1 |

**Priority key:** P0 = implement in Step 3B. P1 = implement in Step 3B if time permits, else Step 4. P2 = implement in Step 4.
