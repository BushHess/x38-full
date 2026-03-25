# BTC Spot Long-Only Trading System Discovery — First-Principles Protocol

## Objective

Use the attached BTC/USDT spot data (H4 and D1, 2017-08 to 2026-02) to discover
the strongest long-only trading system from first principles.

Start from raw data measurement. Let the data determine the system — do not start
from any known architecture or strategy family.

For calibration only: existing research on this dataset has produced systems with
full-sample Sharpe ratios roughly between 1.0 and 1.8 at 20 bps round-trip cost,
using various mechanism families. Detailed benchmark specifications appear in
Appendix A, which you must not consult until Phase 5 is complete and your candidate
is frozen.

## Fixed Execution Assumptions

- Market: BTC/USDT spot, long-only.
- Timeframes available: H4 and D1.
- Signal timing: compute signal at bar close.
- Fill model: execute at next bar open.
- Trading cost: 10 bps per side, 20 bps round-trip.
- Warmup: 365 days with no trading before any live evaluation.
- Cross-timeframe alignment: when using D1 features on H4 bars, only the most
  recently completed D1 bar may be visible. A D1 bar is not available until its
  close time has passed. This prevents lookahead from incomplete higher-timeframe
  bars.
- No lookahead, no intrabar assumptions, no future leakage through feature
  construction, normalization, parameter selection, or regime labeling.

Available columns per bar: `open_time`, `close_time`, `open`, `high`, `low`,
`close`, `volume`, `taker_buy_base_vol` (buyer-initiated volume — real exchange
data, not derived from OHLC), `quote_volume`, `interval` ("4h" or "1d").

## Research Philosophy

Start from raw data. Measure what exploitable structure exists before choosing any
mechanism family. The goal is the strongest system the data supports, regardless of
whether it resembles or differs from anything that has been tried before.

Novelty has no intrinsic value. Familiarity has no intrinsic cost.

Prior studies may inform your search as weak priors — they may help de-prioritize
directions where extensive effort has already been invested, but they do not overrule
current-data evidence. If Phase 1 measurement supports a direction that prior work
rejected, the data takes precedence. If you confirm a prior finding, say so. If you
contradict one, the burden of proof is higher and must come from unseen-data
evidence.

Keep mechanism discovery open. Keep evaluation strict.

## Mandatory Process

### Phase 0: Lock the protocol before discovery

Before proposing any strategy, lock:
- data splits,
- evaluation metrics,
- validation tests (including walk-forward structure),
- bootstrap method and parameters,
- plateau test specification,
- complexity budget.

Do not change these rules after seeing candidate results.

### Phase 1: Data decomposition

Measure what exploitable information exists in the data. Do not pre-filter by
mechanism family. Let the measurements determine which channels carry real edge.

Potential channels include but are not limited to: autocorrelation and persistence,
momentum and return continuation or decay, mean-reversion at various horizons,
volatility level and clustering, volume and order-flow patterns, cross-timeframe
relationships between H4 and D1, regime structure, distribution tails and extreme
events, range and gap behavior, seasonality and calendar effects.

For each channel where you find meaningful signal, report:
- predictive content on unseen data,
- decay horizon,
- sensitivity to trading cost and turnover,
- regime dependence,
- redundancy versus other channels.

Distinguish clearly between:
- measured facts from this dataset,
- prior findings from older studies,
- your inference about mechanism.

### Phase 2: Hypothesis generation

From Phase 1 measurements, propose 3–5 candidate mechanisms. Each must state:
- what market behavior it exploits,
- why that behavior may persist,
- what should cause it to fail,
- what observable evidence would falsify it.

Select candidates based on measured signal strength. Do not exclude any mechanism
because it resembles known work. Do not include any mechanism that Phase 1 does not
support, regardless of novelty.

### Phase 3: Minimal system design

Design entry, exit, position management, and sizing only after the mechanism is
stated.

Rules:
- start from the smallest defensible design,
- add components only if each one earns its place,
- every component must be validated by ablation on unseen data,
- avoid hidden complexity from stacked filters or path-dependent logic.

### Phase 4: Parameter selection

Parameter search is allowed only after the system design is frozen conceptually.

Rules:
- search coarse first,
- report all tested configurations,
- prefer fewer tunable parameters,
- reject sharp peaks,
- require a broad plateau around the selected setting,
- account for selection bias when evaluating many configurations (report total
  number tested).

### Phase 5: Freeze before final holdout

Once the final candidate is chosen, freeze the full specification before touching
the final holdout period. After that point, no redesign and no parameter retuning.

### Phase 6: Benchmark comparison

Only after the candidate is frozen and holdout results are recorded, consult
Appendix A for benchmark specifications. Run a fair comparison:
- use paired evaluation where possible (same resampled paths for both systems in
  bootstrap),
- report the comparison honestly regardless of outcome.

## Data Splits and Validation

Use a leakage-safe split:
- warmup only: 2017-08 to 2018-12,
- development period: 2019-01-01 to 2023-12-31,
- final untouched holdout: 2024-01-01 to 2026-02-20.

Within the development period, use walk-forward validation with at least 4
non-overlapping unseen test windows, each no longer than 12 months, with training
always preceding test chronologically. The final holdout must remain untouched until
the strategy is frozen.

After the final holdout evaluation, you may report full-sample 2019–2026 results as
descriptive context only, not as primary evidence for discovery quality.

## Mandatory Evaluation

Every serious candidate must be evaluated with:

1. Walk-forward validation on unseen development windows.
2. Final untouched holdout evaluation on 2024-01-01 to 2026-02-20.
3. Parameter plateau test with at least ±20% perturbation on each tunable parameter.
4. Regime decomposition across major historical epochs.
5. Cost sensitivity analysis (including 50 bps round-trip as a stress test).
6. Component ablation to prove each module adds value.
7. Bootstrap robustness analysis with block-size sensitivity reported as a
   diagnostic. When comparing against benchmarks (Phase 6), use paired resampling
   (same synthetic paths for both systems) so distributions are directly comparable.
8. Trade-distribution analysis to detect winner truncation, churn, and hidden
   fragility.

## Hard Acceptance Criteria

A candidate must satisfy all of the following:
- positive edge after 20 bps round-trip cost,
- positive walk-forward performance on unseen data overall,
- positive final holdout performance,
- at least 10 trades in the holdout period and at least 20 trades across all
  walk-forward test windows combined,
- no major historical epoch showing clear collapse,
- broad parameter plateau rather than a narrow optimum,
- no reliance on lookahead or post-hoc protocol changes.

If no candidate satisfies these conditions, conclude that no improvement was found
under this protocol.

## Ranking Criteria

Among candidates that pass the hard criteria, rank by:

1. stronger unseen-data robustness (walk-forward consistency),
2. better bootstrap profile (higher median, tighter CI, stable across block sizes),
3. lower drawdown at comparable growth,
4. wider parameter plateau,
5. lower complexity (fewer tunables, simpler logic),
6. stronger cost resilience,
7. stronger full-sample performance as a secondary check.

## Verdict Definitions

After Phase 6 benchmark comparison:

- **SUPERIOR**: passes all hard criteria AND paired bootstrap shows the candidate
  improves on the best benchmark with P(delta > 0) ≥ 0.90 AND no regime where the
  candidate materially underperforms benchmarks.
- **COMPETITIVE**: passes all hard criteria, positive on unseen data, but does not
  meet the SUPERIOR threshold on paired comparison.
- **NO ROBUST IMPROVEMENT**: fails one or more hard criteria, or is clearly
  dominated by benchmarks across all evaluation dimensions.

## How to Use Prior Research

You may use prior research in two ways only:
- as context for where exploitable structure may exist,
- as context for where extensive effort has already been invested.

You may not use prior research in these ways:
- as proof that a structure must be correct,
- as a reason to skip first-principles measurement,
- as a prohibition against exploring a direction that prior work rejected.

If your final system resembles a known system, explain why first-principles
measurement led to the same region. If it differs, explain what information the
prior work was missing.

## Deliverables

Produce:
- a Phase 1 data-decomposition report,
- candidate hypotheses with explicit falsification logic,
- the final frozen system specification,
- full validation results (walk-forward, holdout, bootstrap, plateau, ablation),
- benchmark comparison table (Phase 6),
- a verdict: SUPERIOR, COMPETITIVE, or NO ROBUST IMPROVEMENT,
- charts for equity, drawdown, walk-forward, bootstrap, regime breakdown, and cost
  sensitivity.

## Anti-Patterns

Reject any workflow that does any of the following:
- starts from a known strategy family instead of from measurement,
- optimizes on full sample and then calls it validation,
- treats prior studies as immutable truth,
- adds complexity without unseen-data evidence,
- chooses a winner from a sharp parameter spike,
- declares victory on full-sample Sharpe alone,
- quietly retunes after seeing holdout performance,
- avoids a mechanism because it resembles existing benchmarks,
- pursues a weaker mechanism solely because it is novel,
- anchors hypothesis generation to benchmark architecture rather than Phase 1
  measurements,
- consults benchmark specifications before the candidate is frozen.

---

## Appendix A — Benchmark Specifications (do not read until Phase 5 is complete)

**Important**: These benchmarks exist for fair comparison only. They must not
influence mechanism selection, system design, or parameter tuning.

- `Benchmark A` (robustness leader): Sharpe 1.638, CAGR 72.8%, MDD −38.5%,
  Trades 186. Bootstrap median Sharpe 0.766, median CAGR 24.4%, P(Sharpe>0) 96.8%.
- `Benchmark B` (best full-sample variant): Sharpe 1.830, CAGR 80.4%, MDD −33.6%,
  Trades 196. Bootstrap median Sharpe 0.733, median CAGR 21.7%, P(Sharpe>0) 96.6%.
  Strong full-sample but weaker under resampling and fragile in recent data with
  near-zero Sharpe.
- `Benchmark C` (diagnostic comparator, not frontier): Sharpe 1.533, CAGR 57.8%,
  MDD −37.3%, Trades 211. Bootstrap median Sharpe 0.516, median CAGR 12.2%,
  P(Sharpe>0) 89.4%.

When comparing, use paired bootstrap (same resampled paths) so that differences
reflect system quality, not resampling noise.
