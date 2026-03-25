# P3.0 — Reconcile Phase 2 Reporting Discrepancy

## SUMMARY

Cross-check of `phase2_evaluation.md` against `p2_4_results.json` and CSV artifacts
found **2 discrepancies**, both reporting-layer bugs (no computation errors). Both fixed.
Zero impact on Phase 2 conclusions.

## FILES_INSPECTED

| File | Purpose |
|------|---------|
| `research/x0/phase2_evaluation.md` | P2.4 markdown report (audit target) |
| `research/x0/p2_4_results.json` | Source of truth (computed output) |
| `research/x0/p2_4_backtest_table.csv` | Vectorized sim results |
| `research/x0/p2_4_bootstrap_table.csv` | Bootstrap results |
| `research/x0/p2_4_delta_table.csv` | BacktestEngine-based deltas |
| `research/x0/p2_4_benchmark.py` | Benchmark script (pipeline logic) |

## FILES_CHANGED

| File | Action | Detail |
|------|--------|--------|
| `research/x0/phase2_evaluation.md` | EDITED | Fixed p_sharpe_gt0 (4 values), fixed delta table (12 values + footnote), updated SUMMARY |
| `research/x0/search_log.md` | UPDATED | Corrected P2.4 delta table, added P3.0 section |

No strategy, config, script, or data files were modified. No recomputation needed.

## DISCREPANCY_TABLE

| # | Location | Field | Wrong Value | Correct Value | Severity |
|---|----------|-------|-------------|---------------|----------|
| 1 | phase2_evaluation.md L127 | P(Sharpe>0) E0 | 0.632 | 0.776 | HIGH |
| 1 | phase2_evaluation.md L128 | P(Sharpe>0) E0_EMA21 | 0.612 | 0.744 | HIGH |
| 1 | phase2_evaluation.md L129 | P(Sharpe>0) E5 | 0.606 | 0.754 | HIGH |
| 1 | phase2_evaluation.md L130 | P(Sharpe>0) E5_EMA21 | 0.580 | 0.702 | HIGH |
| 2 | phase2_evaluation.md L138 | dSharpe smart | +0.129 (engine) | +0.120 (vectorized) | MEDIUM |
| 2 | phase2_evaluation.md L139 | dSharpe base | +0.117 (engine) | +0.108 (vectorized) | MEDIUM |
| 2 | phase2_evaluation.md L140 | dSharpe harsh | +0.105 (engine) | +0.096 (vectorized) | MEDIUM |
| 2 | phase2_evaluation.md L138 | dCAGR smart | +6.90 (engine) | +6.33 (vectorized) | MEDIUM |
| 2 | phase2_evaluation.md L139 | dCAGR base | +6.02 (engine) | +5.47 (vectorized) | MEDIUM |
| 2 | phase2_evaluation.md L140 | dCAGR harsh | +5.15 (engine) | +4.64 (vectorized) | MEDIUM |
| 2 | phase2_evaluation.md L138-140 | dTrades (all) | +14 (engine) | +13 (vectorized) | LOW |
| 2 | phase2_evaluation.md L140 | dMDD harsh | -0.41 (engine) | -0.42 (vectorized) | LOW |

## SOURCE_OF_TRUTH

| Artifact | Pipeline | Authoritative For |
|----------|----------|-------------------|
| `p2_4_results.json` | Both | All computed values (backtest, bootstrap, attribution) |
| `p2_4_backtest_table.csv` | Vectorized sim | Strategy performance across cost scenarios |
| `p2_4_bootstrap_table.csv` | VCBB | Bootstrap distributions, P(metric>0) |
| `p2_4_delta_table.csv` | BacktestEngine | Trade-level attribution deltas |
| `phase2_evaluation.md` | Report | Human-readable synthesis (now corrected) |

**Rule**: Markdown report values MUST be traceable to JSON/CSV artifacts. When two
pipelines produce different numbers for the same metric, the report must use values
from ONE pipeline consistently within a table, with a footnote if the other pipeline
is also referenced.

## ROOT_CAUSE_ANALYSIS

### Discrepancy 1 — p_sharpe_gt0

**Root cause**: Values were fabricated during markdown report generation. The script
`p2_4_benchmark.py` correctly computes `p_sharpe_gt0` and writes it to both JSON and CSV.
When the markdown report was written, the values were not copied from the JSON output
but instead hallucinated (all 4 values wrong, all biased low by ~0.12-0.15).

**Evidence**: JSON has `"p_sharpe_gt0": 0.776` (E0), CSV has `p_sharpe_gt0,0.776`.
Markdown had `0.632`. No computation path produces 0.632.

### Discrepancy 2 — Delta table pipeline mixing

**Root cause**: The P2.4 benchmark script uses two execution pipelines:
- **T1 (vectorized sim)**: lfilter-accelerated, processes full bar range including warmup.
  Produces 186 P1 trades, 199 P2 trades.
- **T3 (BacktestEngine)**: Trade-object-aware, uses `warmup_mode="no_trade"`.
  Produces 172 P1 trades, 186 P2 trades.

The delta table in the markdown report showed absolute values from T1 (vectorized)
alongside delta values from T3 (engine). The two pipelines agree on direction but
differ on magnitude due to different warmup handling.

**This is NOT a bug in the benchmark script** — both pipelines are correct for their
purposes. The bug was mixing values from different pipelines in one table without
noting the inconsistency.

## FIX_APPLIED_OR_JUSTIFICATION

### Fix 1 — p_sharpe_gt0
Replaced all 4 wrong values with correct values from `p2_4_results.json`:
- E0: 0.632 → **0.776**
- E0_EMA21 / X0: 0.612 → **0.744**
- E5: 0.606 → **0.754**
- E5_EMA21 / X0_E5EXIT: 0.580 → **0.702**

### Fix 2 — Delta table consistency
Replaced engine-derived deltas with vectorized-derived deltas (computed from the
absolute values already shown in the same table):

| Scenario | Old dSharpe | New dSharpe | Old dCAGR | New dCAGR | Old dTrades | New dTrades |
|----------|-------------|-------------|-----------|-----------|-------------|-------------|
| smart | +0.129 | +0.120 | +6.90 | +6.33 | +14 | +13 |
| base | +0.117 | +0.108 | +6.02 | +5.47 | +14 | +13 |
| harsh | +0.105 | +0.096 | +5.15 | +4.64 | +14 | +13 |

Added footnote explaining that `p2_4_delta_table.csv` contains engine-based deltas
(valid for trade-level attribution) and why the two pipelines differ.

Updated SUMMARY line to reflect corrected vectorized delta ranges.

Updated `search_log.md` P2.4 delta table to use vectorized values.

**No recomputation needed** — this was purely a reporting/formatting fix.

## IMPACT_ON_PHASE2_CONCLUSIONS

### Fix 1 impact: NONE (directionally strengthens conclusions)
The correct P(Sharpe>0) values are HIGHER than the wrong ones (e.g., E0: 0.776 vs 0.632).
This means bootstrap confidence is actually stronger than reported. All qualitative
conclusions ("bootstrap does NOT confirm the uplift" in the relative E5 vs E0 sense)
remain valid — E5-class still has lower P(Sharpe>0) than E0-class.

### Fix 2 impact: NONE (magnitude change, same direction)
Vectorized deltas are slightly smaller than engine deltas (e.g., harsh dSharpe +0.096
vs +0.105) but still unambiguously positive across all metrics and cost levels.
The conclusion "Phase 2 improves ALL metrics at ALL cost levels" is unchanged.

### Specific conclusions checked:
| Conclusion | Status |
|-----------|--------|
| X0_E5EXIT = E5_EMA21 BIT-IDENTICAL | UNCHANGED (parity, not affected) |
| Phase 2 improves on Phase 1 at all cost levels | UNCHANGED (all deltas still positive) |
| Bootstrap does not confirm uplift (E5 < E0 under resampling) | UNCHANGED |
| Uplift is broad-based (3 channels) | UNCHANGED (attribution unaffected) |
| Top 3 = 29.2% of matched delta | UNCHANGED (attribution unaffected) |
| Improvement hierarchy near-additive | UNCHANGED (backtest values unchanged) |

## BLOCKERS

None.

## NEXT_READY

P3.0 reconciliation complete. All Phase 2 reporting artifacts are now internally
consistent and traceable to source of truth. Ready for Phase 3 when authorized.
Not proceeding.
