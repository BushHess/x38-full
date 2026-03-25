# Spec: Score Decomposition

**Status:** Draft — for Codex implementation
**Scope:** Structured breakdown of the objective score into named additive terms, with consistency checks and interpretation guidance.

---

## 1. Score Formula & Term Decomposition

### 1.1 Canonical Formula (from `objective.py`)

```
score = 2.5 * cagr_pct
      - 0.60 * max_drawdown_mid_pct
      + 8.0 * max(0, sharpe)
      + 5.0 * max(0, min(profit_factor, 3.0) - 1.0)
      + min(n_trades / 50, 1.0) * 5.0
```

Rejection override: if `n_trades < 10`, `score = -1,000,000`.

### 1.2 Required Terms

Every score output must include **all six** named terms in this fixed order:

| # | Term name | Formula | Sign | Coefficient | Input metric |
|---|-----------|---------|------|-------------|--------------|
| 1 | `return_term` | `2.5 * cagr_pct` | + | 2.5 | `cagr_pct` |
| 2 | `mdd_penalty` | `-0.60 * max_drawdown_mid_pct` | − | 0.60 | `max_drawdown_mid_pct` |
| 3 | `sharpe_term` | `8.0 * max(0, sharpe)` | + | 8.0 | `sharpe` (floored at 0) |
| 4 | `profit_factor_term` | `5.0 * max(0, min(pf, 3.0) - 1.0)` | + | 5.0 | `profit_factor` (capped at 3.0) |
| 5 | `trade_count_term` | `min(n_trades / 50, 1.0) * 5.0` | + | 5.0 | `trades` (saturates at 50) |
| 6 | `reject_term` | `-1,000,000` if `n_trades < 10`, else `0` | − | sentinel | `trades` |

### 1.3 Term Naming Convention

- **`*_term`**: Positive contribution (higher input → higher score)
- **`*_penalty`**: Negative contribution (higher input → lower score)
- **`reject_term`**: Sentinel; always 0 or −1M — never a partial value

### 1.4 Canonical Term Order

```python
OBJECTIVE_TERM_ORDER = (
    "return_term",
    "mdd_penalty",
    "sharpe_term",
    "profit_factor_term",
    "trade_count_term",
    "reject_term",
)
```

All CSV/JSON outputs must emit terms in this order. No additional terms may be added without updating `OBJECTIVE_TERM_ORDER`.

### 1.5 Rejection Behavior

When `n_trades < 10`:
- `reject_term` = −1,000,000
- All other terms = **0.0** (not computed)
- `total_score` = −1,000,000
- `rejected` = `true`
- `reject_reason` = `"n_trades_below_minimum"`

This zeroing prevents misleading partial breakdowns on rejected configs.

---

## 2. Consistency Rules

### 2.1 Summation Invariant

```
abs(total_score - sum(components[term] for term in OBJECTIVE_TERM_ORDER)) <= 1e-6
```

**Implementation:** Compute `residual = total_score - sum(terms)`. If `abs(residual) > 1e-6`, flag as `FAIL`.

This is already enforced in `score_decomposition.py:residual_within_tolerance()` with tolerance `1e-6`.

### 2.2 Per-Row Residual in CSV

Every row in `score_breakdown_full.csv` and `score_breakdown_holdout.csv` must include a `residual` column:

```
residual = total_score - (return_term + mdd_penalty + sharpe_term
           + profit_factor_term + trade_count_term + reject_term)
```

### 2.3 Aggregate Residual Check

The `score_decomposition_report.md` must report:
- `full_period_residual_max_abs` (max across all rows in full period)
- `holdout_residual_max_abs` (max across all rows in holdout period)
- Status: `PASS` if both ≤ `1e-6`, else `FAIL`

### 2.4 Invalid Input Handling

| Condition | Action | Rationale |
|-----------|--------|-----------|
| Any core metric is `None` or `NaN` | Mark row `invalid: true`, set `total_score: null`, set all terms to `null` | Don't emit a partial score that looks valid |
| `profit_factor` is `"inf"` (string) or `float('inf')` | Cap to 3.0, proceed normally | Already handled in `objective.py` lines 52-62 |
| `sharpe` is negative | Floor to 0.0 for `sharpe_term`, proceed normally | Negative Sharpe contributes 0, not a negative term |
| `cagr_pct` overflows | Use log-method fallback (already in `metrics.py`) | Avoids `Inf` in return_term |

**Rule:** Never emit `NaN` or `Infinity` in any term value in JSON output. Use `null` + `invalid: true` + `invalid_reason`.

### 2.5 WFO Non-Reject Variant

The WFO suite uses `_objective_without_reject()` which:
- Returns `NaN` (not −1M) for invalid/zero-trade windows
- Same formula otherwise
- Windows with `NaN` score are marked `valid_window: false` with explicit `invalid_reason`

**Consistency rule for WFO:** The non-reject formula must produce the same numeric result as the standard formula for all windows where `n_trades >= 10` and all inputs are finite. This is a testable invariant.

---

## 3. Delta Interpretation (Candidate − Baseline)

### 3.1 Per-Term Delta

For each scenario, compute:

```
delta[term] = candidate.components[term] - baseline.components[term]
```

### 3.2 Reading the Delta Table

| Delta sign | `return_term` | `mdd_penalty` | `sharpe_term` | `profit_factor_term` | `trade_count_term` |
|------------|--------------|---------------|---------------|---------------------|--------------------|
| **Positive** | Higher CAGR | **Less** drawdown (mdd_penalty is negative, so less-negative = positive delta) | Higher risk-adjusted return | Better profit factor | More trades (if < 50) |
| **Negative** | Lower CAGR | **More** drawdown | Worse risk-adjusted return | Worse profit factor | Fewer trades |

### 3.3 Top-Delta Reporting

Sort terms by `abs(delta)` descending. Report top 2 terms per scenario. This answers: "What drove the score change?"

Already implemented in `score_decomposition.py:build_score_decomposition_report()`.

### 3.4 Interpretation Examples

**Example A — Candidate improves returns but adds drawdown:**
```
return_term delta:   +15.0   (CAGR improved +6 pct pts)
mdd_penalty delta:   -12.0   (MDD worsened by 20 pct pts)
sharpe_term delta:    +2.0
total_score delta:    +5.0   (net positive, but fragile)
```
→ Reviewer concern: return gain comes at MDD cost. Check if TOPPING scenario MDD is acceptable.

**Example B — Candidate reduces trading activity:**
```
return_term delta:     -2.0
trade_count_term delta: -3.0   (went from 55 to 20 trades)
total_score delta:     -5.0
```
→ Reviewer concern: candidate is too conservative; may have overfitted a filter.

---

## 4. Bug-Detection Patterns

### 4.1 Sanity Checklist

Run these checks on every score decomposition output. Any failure = investigate before trusting.

| # | Check | Expected | Bug if violated |
|---|-------|----------|-----------------|
| 1 | `mdd_penalty <= 0` | Always (MDD ≥ 0, coefficient is −0.60) | MDD is negative → data or NAV computation bug |
| 2 | `return_term` sign matches CAGR sign | `return_term > 0` iff `cagr_pct > 0` | Sign flip → coefficient or input bug |
| 3 | `sharpe_term >= 0` | Always (floored at 0) | Negative sharpe_term → floor not applied |
| 4 | `profit_factor_term >= 0` | Always (floored at 0 via `max(0, ...)`) | Negative pf_term → floor or cap bug |
| 5 | `trade_count_term` in `[0, 5.0]` | Always (saturates at 5.0) | Out of range → formula bug |
| 6 | `reject_term` is 0 or −1M | Never any other value | Partial reject → logic bug |
| 7 | If `rejected == true`, all other terms == 0 | By construction | Non-zero term on rejected row → zeroing bug |
| 8 | `residual <= 1e-6` | Always | Summation bug or rounding drift |
| 9 | `mdd_penalty` delta < 0 but `return_term` delta > 0 with large `total_score` delta | Suspicious | Returns bought with drawdown — not a code bug but a red flag for review |
| 10 | `profit_factor_term` delta negative AND `return_term` delta positive | Suspicious | More profit but worse profit factor → check if turnover spiked |

### 4.2 Automated Assertions (implement as unit tests)

```python
def assert_decomposition_valid(bd: ObjectiveBreakdown) -> None:
    """Raise AssertionError if decomposition is incoherent."""
    c = bd.components

    # Summation invariant
    residual = bd.total_score - sum(c[t] for t in OBJECTIVE_TERM_ORDER)
    assert abs(residual) < 1e-6, f"residual {residual}"

    if bd.rejected:
        assert c["reject_term"] == -1_000_000.0
        for term in OBJECTIVE_TERM_ORDER:
            if term != "reject_term":
                assert c[term] == 0.0, f"{term} non-zero on rejected row"
        return

    # Sign & range checks
    assert c["reject_term"] == 0.0
    assert c["mdd_penalty"] <= 0.0, f"mdd_penalty positive: {c['mdd_penalty']}"
    assert c["sharpe_term"] >= 0.0, f"sharpe_term negative: {c['sharpe_term']}"
    assert c["profit_factor_term"] >= 0.0, f"pf_term negative: {c['profit_factor_term']}"
    assert 0.0 <= c["trade_count_term"] <= 5.0 + 1e-9, f"trade_count out of range: {c['trade_count_term']}"
```

### 4.3 Cross-Suite Consistency

When the same (strategy, scenario, dataset) is evaluated in both backtest and holdout suites, the scores will differ (different time ranges). But the **formula** must produce identical results given identical inputs. Test:

```python
# Same summary dict → same breakdown regardless of which suite calls it
bd1 = compute_objective_breakdown(summary)
bd2 = compute_objective_breakdown(summary)
assert bd1 == bd2  # frozen dataclass, deterministic
```

---

## 5. Output Schema

### 5.1 CSV Format (`score_breakdown_full.csv`, `score_breakdown_holdout.csv`)

| Column | Type | Description |
|--------|------|-------------|
| `model` | str | `"candidate"` or `"baseline"` |
| `scenario` | str | `"smart"`, `"base"`, `"harsh"` |
| `total_score` | float | Sum of all terms |
| `return_term` | float | 2.5 × cagr_pct |
| `mdd_penalty` | float | −0.60 × max_drawdown_mid_pct |
| `sharpe_term` | float | 8.0 × max(0, sharpe) |
| `profit_factor_term` | float | 5.0 × max(0, min(pf, 3.0) − 1.0) |
| `trade_count_term` | float | min(n/50, 1) × 5.0 |
| `reject_term` | float | 0 or −1,000,000 |
| `residual` | float | total_score − sum(terms) |
| `rejected` | bool | true if n_trades < 10 |
| `reject_reason` | str\|null | Reason string or null |

### 5.2 JSON Format (for `effective_config.json` co-emission)

```json
{
  "score_decomposition": {
    "total_score": 94.81,
    "components": {
      "return_term": 62.50,
      "mdd_penalty": -18.00,
      "sharpe_term": 32.00,
      "profit_factor_term": 10.00,
      "trade_count_term": 5.00,
      "reject_term": 0.0
    },
    "residual": 0.0,
    "rejected": false,
    "reject_reason": null,
    "input_metrics": {
      "cagr_pct": 25.0,
      "max_drawdown_mid_pct": 30.0,
      "sharpe": 4.0,
      "profit_factor": 3.0,
      "trades": 52
    }
  }
}
```

Including `input_metrics` enables downstream audit: anyone can verify `return_term == 2.5 * 25.0 == 62.5`.

### 5.3 Delta Report Format (in `score_decomposition_report.md`)

Already implemented. Required columns in the delta table:

```
| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |
```

Where `term_1`, `term_2` are the top-2 terms by `abs(delta)`.

---

## 6. WFO-Specific Considerations

### 6.1 Non-Reject Objective

The WFO suite's `_objective_without_reject()` must produce per-term breakdowns too (currently it returns only a scalar). Implementation task:

```python
def _objective_breakdown_without_reject(summary: Mapping) -> ObjectiveBreakdown:
    """Like compute_objective_breakdown but NaN instead of -1M for invalids."""
    # If any core metric non-finite → return invalid breakdown
    # Otherwise → same formula, reject_term always 0
```

### 6.2 Per-Window Delta Decomposition

For each WFO window, emit:

```json
{
  "window_id": 3,
  "candidate_breakdown": { ...components... },
  "baseline_breakdown": { ...components... },
  "delta_by_term": {
    "return_term": 5.2,
    "mdd_penalty": -3.1,
    "sharpe_term": 1.0,
    "profit_factor_term": 0.5,
    "trade_count_term": 0.0,
    "reject_term": 0.0
  },
  "total_delta": 3.6,
  "valid_window": true
}
```

This enables answering: "In which windows and through which terms does the candidate differ?"

---

## 7. Implementation Checklist

- [ ] Verify `ObjectiveBreakdown` dataclass has all 6 terms + `rejected` + `reject_reason` (already done in `objective.py`)
- [ ] Add `input_metrics` dict to `ObjectiveBreakdown` for audit trail
- [ ] Add `residual` field to CSV rows in backtest & holdout suites
- [ ] Implement `assert_decomposition_valid()` as a unit test (§4.2)
- [ ] Add non-reject breakdown variant for WFO (`_objective_breakdown_without_reject`)
- [ ] Add per-window delta decomposition to WFO CSV output (§6.2)
- [ ] Ensure all JSON outputs pass `json.loads()` — no NaN/Inf leakage
- [ ] Add integration test: for 3 known summaries, verify each term matches hand-computed values
- [ ] Add the 10-item sanity checklist (§4.1) as automated post-run assertions
- [ ] Verify `OBJECTIVE_TERM_ORDER` is the single source of truth for column ordering everywhere
