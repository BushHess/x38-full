[NOTE]:
- Khi Agent vô tình lần đầu tìm ra trend-following có hiệu suất thấp hơn benchmark thì prompt này chặn đường quay về trend-following và buộc agent phải tìm hướng khác. Vì vậy nó không tối ưu nó không phải thiết kế tối ưu để tìm system tốt nhất có thể — nó thiết kế để tìm system MỚI nhất có thể. Nên cần phải chỉnh sửa một vài chổ => V4.

- Prompt này đã giúp tìm ra thuật toán V1-dipD1

# BTC Spot Long-Only Trading System Discovery — First-Principles, Low-Bias Protocol

## Objective

Use the attached BTC/USDT spot data (H4 and D1, 2017-08 to 2026-02) to discover a
new long-only trading system from first principles, or conclude that the current
research frontier is already near-optimal.

The goal is not to reproduce any known architecture. The goal is to find the most
credible out-of-sample edge that survives realistic execution, broad parameter
perturbation, and regime changes.

Use the following canonical benchmark context:

- `E5+EMA21D1` (baseline robustness leader): Sharpe 1.638, CAGR 72.8%, MDD -38.5%,
  Trades 186. Bootstrap median Sharpe 0.766, median CAGR 24.4%, P(Sharpe>0) 96.8%.
- `V4` (best full-sample variant): Sharpe 1.830, CAGR 80.4%, MDD -33.6%, Trades 196.
  Bootstrap median Sharpe 0.733, median CAGR 21.7%, P(Sharpe>0) 96.6%. Strong
  full-sample, but weaker than `E5+EMA21D1` under resampling and fragile in 2025+
  with near-zero Sharpe.
- `V3` (reference variant, not frontier benchmark): Sharpe 1.533, CAGR 57.8%, MDD
  -37.3%, Trades 211. Bootstrap median Sharpe 0.516, median CAGR 12.2%,
  P(Sharpe>0) 89.4%. Useful as a regime-behavior reference, but not a target to beat.

Do not optimize specifically to beat any one benchmark metric in isolation. Use the
benchmarks to calibrate what is already known about the trade-off between full-sample
strength, bootstrap robustness, cost resilience, and regime stability.

## Fixed Execution Assumptions

- Market: BTC/USDT spot.
- Timeframes available: H4 and D1.
- Signal timing: compute signal at bar close.
- Fill model: execute at next bar open.
- Trading cost: 10 bps per side, 20 bps round-trip.
- Warmup: 365 days with no trading before any live evaluation.
- No lookahead, no intrabar assumptions, no future leakage through feature construction,
  normalization, parameter selection, or regime labeling.

## Research Philosophy

Start from raw data. Do not begin by assuming trend-following, mean reversion,
breakout, regime filter, EMA crossover, or any other named framework.

Prior studies are allowed as research priors, not as design mandates. They may help
de-prioritize low-value directions, but they do not overrule current-data evidence.
If you confirm a prior result, say so. If you contradict a prior result, the burden of
proof is higher and must come from unseen-data evidence.

Keep mechanism discovery open, but keep evaluation strict.

## Mandatory Process

### Phase 0: Lock the protocol before discovery

Before proposing any strategy, lock:
- data splits,
- evaluation metrics,
- validation tests,
- bootstrap method,
- plateau test,
- complexity budget.

Do not change these rules after seeing candidate results.

### Phase 1: Data decomposition

Measure what exploitable information exists in the data, including but not limited to:
- price trend and autocorrelation,
- momentum and return continuation/decay,
- volatility level, clustering, and expansion/compression,
- volume and order-flow imbalance,
- cross-timeframe alignment between H4 and D1,
- regime structure,
- seasonality/calendar effects,
- any other structure the data actually supports.

For each information channel, report:
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

From Phase 1, propose 3-5 candidate mechanisms. Each hypothesis must state:
- what market behavior it exploits,
- why that behavior may persist,
- what should cause it to fail,
- what observable evidence would falsify it.

At least one candidate should be materially different from the existing benchmark
family if the data supports such a direction.

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
- require a broad plateau around the selected setting.

### Phase 5: Freeze before final holdout

Once the final candidate is chosen, freeze the full specification before touching the
final holdout period. After that point, no redesign and no parameter retuning.

## Data Splits and Validation

Use a leakage-safe split:
- warmup only: 2017-08 to 2018-12,
- development period: 2019-01-01 to 2023-12-31,
- final untouched holdout: 2024-01-01 to 2026-02-20.

Within the development period, use walk-forward validation with unseen test windows.
The final holdout must remain untouched until the strategy is frozen.

After the final holdout evaluation, you may report full-sample 2019-2026 results as
descriptive context only, not as primary evidence for discovery quality.

## Mandatory Evaluation

Every serious candidate must be evaluated with:

1. Walk-forward validation on unseen development windows.
2. Final untouched holdout evaluation on 2024-01-01 to 2026-02-20.
3. Parameter plateau test with at least +/-20% perturbation on each tunable parameter.
4. Regime decomposition across major historical epochs.
5. Cost sensitivity analysis.
6. Component ablation to prove each module adds value.
7. Bootstrap robustness analysis, with block-size sensitivity reported as a diagnostic.
8. Trade-distribution analysis to detect winner truncation, churn, and hidden fragility.

## Hard Acceptance Criteria

A winner must satisfy all of the following:
- positive edge after 20 bps round-trip cost,
- positive walk-forward performance on unseen data overall,
- positive final holdout performance,
- no major historical epoch showing clear collapse,
- broad parameter plateau rather than a narrow optimum,
- no reliance on lookahead or post-hoc protocol changes.

If no candidate satisfies these conditions, conclude that the current frontier may
already be near-optimal under this execution model.

## Ranking Criteria

Among systems that pass the hard criteria, rank them by:

1. stronger unseen-data robustness,
2. better bootstrap profile,
3. lower drawdown at comparable growth,
4. wider plateau,
5. lower complexity,
6. stronger cost resilience,
7. stronger full-sample performance as a secondary check.

Interpret benchmark comparison carefully:
- beating `V4` on full-sample alone is not enough,
- beating `E5+EMA21D1` on bootstrap alone is not enough if the system collapses in a
  recent regime,
- `V3` should be treated as a diagnostic comparator for regime behavior, not as the
  primary benchmark frontier.

## How to Use Prior Research

You may use prior research in two ways only:
- as context for where alpha may already have been found,
- as context for where extensive effort has already failed.

You may not use prior research in these ways:
- as proof that a structure must be correct,
- as a reason to skip first-principles measurement,
- as a reason to overfit toward the weaknesses of a known benchmark.

If your final system is close to a prior benchmark, explain why first-principles
analysis led back to that region. If your final system is different, explain what
information the prior benchmark family was missing.

## Deliverables

Produce:
- a Phase 1 data-decomposition report,
- candidate hypotheses with explicit falsification logic,
- the final frozen system specification,
- full validation results,
- ablation results,
- a benchmark comparison table against `E5+EMA21D1` and `V4`, with `V3` included only
  as an optional diagnostic comparator,
- a verdict: `SUPERIOR`, `COMPETITIVE`, or `NO ROBUST IMPROVEMENT`,
- charts for equity, drawdown, walk-forward, bootstrap, regime breakdown, and cost sensitivity.

## Anti-Patterns

Reject any workflow that does any of the following:
- starts from a canned strategy family instead of measurement,
- optimizes on full sample and then calls it validation,
- treats prior studies as immutable truth,
- adds complexity without unseen-data evidence,
- chooses a winner from a sharp parameter spike,
- declares victory on full-sample Sharpe alone,
- quietly retunes after seeing holdout performance.
