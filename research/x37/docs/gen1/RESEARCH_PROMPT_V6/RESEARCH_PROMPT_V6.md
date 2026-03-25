# BTC/USDT Spot Long-Only System Discovery — First-Principles Protocol V6

## Research protocol

### Objective

Use the attached BTC/USDT spot data (H4 and D1) to discover the strongest **scientifically defensible** long-only trading system supported by the data, under a leak-free, cost-aware, audit-ready, provenance-controlled protocol.

The target is **not** a claim of global optimum. The target is the best candidate found **inside a declared search space**, with honest evidence labeling and strict separation between:

1. measured evidence from the data,
2. design inference drawn from that evidence,
3. final selection judgment after robustness testing.

### Admissible inputs and provenance lock

Before the frozen candidate is selected, the only admissible quantitative inputs are:

- this prompt,
- the raw BTC/USDT data files supplied for the session.

Not admissible before freeze:

- prior reports,
- prior contamination logs,
- prior system specifications,
- prior JSON outputs,
- prior shortlist tables,
- benchmark specifications,
- any precomputed tables or artifacts from earlier sessions.

Rules:

- Every table used for candidate selection must be generated inside the current session from raw data.
- Keep a **provenance log** listing every non-raw artifact consulted and when it was consulted.
- If any disallowed artifact is consulted before freeze, the session is **not** a clean independent re-derivation and that must be stated explicitly in the deliverables.
- Do not present reproduced or imported tables as if they were computed in the current session.

### Fixed execution assumptions

- Market: BTC/USDT spot, long-only.
- Timeframes available: H4 and D1.
- Signal timing: compute signal at bar close.
- Fill model: execute at next bar open.
- Trading cost: 10 bps per side, 20 bps round-trip.
- Warmup: no live trading before 2020-01-01; earlier data may be used for context and calibration only.
- Cross-timeframe alignment: when using slower-timeframe features on faster-timeframe bars, only the most recently completed slower bar may be visible. A slower bar is not available until its close time has passed.
- No lookahead, no intrabar assumptions, no future leakage through feature construction, normalization, threshold calibration, parameter selection, regime labeling, or benchmark comparison.
- Use native raw bars only. Do not resample raw OHLCV into synthetic bars. Do not fill missing price bars with invented data.
- Evaluate realized strategy returns using the actual execution convention above, not close-to-close proxy returns.

Available columns per bar: `open_time`, `close_time`, `open`, `high`, `low`, `close`, `volume`, `taker_buy_base_vol`, `quote_volume`, `interval`.

### Research philosophy

Start from raw data. Measure what exploitable structure exists before choosing a mechanism family.

Prefer:

- simple mechanisms before complex ones,
- orthogonal evidence before redundant feature stacking,
- role-consistent architectures before “one signal does everything” logic,
- broad plateaus before sharp maxima,
- paired comparisons before narrative preference,
- current-session evidence before inherited beliefs,
- honest evidence labels before impressive wording.

Novelty has no intrinsic value. Familiarity has no intrinsic cost. The data decides.

### Protocol lock before discovery

Before proposing any final strategy, lock all of the following:

- execution model,
- admissible inputs,
- data split architecture,
- discovery fold structure,
- evaluation metrics,
- bootstrap method and parameters,
- plateau / perturbation specification,
- complexity budget,
- candidate progression gates,
- evidence labels,
- benchmark access rule,
- feature-library manifest format,
- candidate-ledger format,
- threshold-calibration modes allowed in the search.

If any of those rules change after candidate results are seen, the research must be treated as restarted.

### Data pipeline and audit

Before any feature research:

1. Parse timestamps to timezone-aware UTC.
2. Sort bars in ascending chronological order.
3. Check duplicates, missing values, malformed rows, irregular gaps, nonstandard bar durations, and zero-volume anomalies.
4. Record the exact date coverage of each timeframe.
5. Preserve native H4 and D1 frames separately.
6. When joining slower features onto faster bars, use backward as-of alignment on bar close time so only completed slower bars are visible.
7. Keep a written audit record **and** machine-readable audit tables.
8. If the raw data has structural problems that materially affect execution assumptions, stop and report them before discovery.
9. Do not silently repair anomalous rows. Any exclusion, retention, or de-duplication rule must be logged explicitly.

### Data split architecture for this run

Use the following split for this version of the protocol:

- **Context / warmup only:** 2017-08-17 to 2019-12-31
- **Discovery window:** 2020-01-01 to 2022-12-31
- **Candidate-selection holdout:** 2023-01-01 to 2024-06-30
- **Reserve/internal window:** 2024-07-01 to dataset end

Rules:

- The discovery window is the only zone allowed for measurement, hypothesis generation, coarse search, local refinement, and internal model comparison.
- The candidate-selection holdout stays sealed until one conceptually frozen candidate and one frozen comparison set are chosen from discovery only.
- The reserve/internal window stays sealed until the exact final specification and the exact frozen comparison set are recorded.
- For this version of the protocol, the within-file reserve is **internal only** and is **not eligible** to be labeled clean OOS.
- If genuinely new data is appended after the current file end, that later appended period may be used for a clean OOS test. The current file alone may not earn that label.

### Discovery walk-forward structure

Within the discovery window, use semiannual, non-overlapping unseen test windows with chronological training / calibration:

- train / calibrate `< 2020-01-01`, test `2020-01-01` to `2020-06-30`
- train / calibrate `< 2020-07-01`, test `2020-07-01` to `2020-12-31`
- train / calibrate `< 2021-01-01`, test `2021-01-01` to `2021-06-30`
- train / calibrate `< 2021-07-01`, test `2021-07-01` to `2021-12-31`
- train / calibrate `< 2022-01-01`, test `2022-01-01` to `2022-06-30`
- train / calibrate `< 2022-07-01`, test `2022-07-01` to `2022-12-31`

Rules:

- Training / calibration data must always precede the test window in time.
- No test window may leak into its own training set.
- Context / warmup data may be used only to initialize historical calculations and early calibration, not to score candidate performance.

### Search-space discipline

Search the space in layers. Do not jump directly to high-complexity systems.

#### Stage 1: raw measurement and single-feature state systems

Measure a broad but finite library spanning, at minimum:

- directional persistence / continuation,
- trend quality / return normalized by volatility,
- location within rolling range / distance to extremes,
- drawdown / pullback state,
- volatility level and clustering,
- participation / flow,
- candle-structure summaries,
- cross-timeframe relationships,
- calendar effects.

Rules:

- Evaluate **native D1**, **native H4**, and **aligned cross-timeframe transports** as separate buckets.
- Do not assume that a fast-timeframe signal is genuinely fast information merely because it is visible on a fast bar.
- Convert each serious feature into an executable long/flat state system under the exact execution model.
- For each feature or channel, measure:
  - predictive content on unseen discovery folds,
  - decay horizon,
  - turnover and trade count,
  - cost sensitivity,
  - regime dependence,
  - redundancy versus nearby transforms,
  - whether it adds information beyond already-visible slower state.
- Export the full machine-readable Stage 1 registry:
  - feature name,
  - family,
  - formula description,
  - timeframe,
  - admissible tails,
  - lookback grid,
  - threshold grid,
  - calibration modes,
  - exact result table for every scanned config.

Do not rely on correlation alone. Require realized, executable performance.

#### Stage 2: orthogonal shortlist formation

From Stage 1, shortlist the strongest **orthogonal** representatives rather than many near-duplicates.

At minimum, keep:

- the strongest slower-timeframe context candidates,
- the strongest faster-timeframe **native** state / timing candidates,
- any participation / filter candidates that appear helpful,
- at least one credible **simple frontier** candidate,
- at least one credible layered alternative with a meaningfully different failure mode.

Rules:

- Prune near-duplicates early.
- Maintain a **keep / drop ledger** explaining why each serious candidate survives or is removed.
- A transported clone of slower information does not count as an orthogonal faster-timeframe representative unless it adds incremental evidence after paired comparison.
- Do not eliminate the simplest viable representative of a strong family merely because a more complex sibling has a slightly better headline metric.

#### Stage 3: minimal layered architectures

Construct candidate families in increasing complexity:

1. single-feature state systems,
2. two-layer systems: permission gate + state controller,
3. optional third layer: entry-only confirmation filter.

Rules:

- Start with the smallest defensible architecture.
- Layering is a hypothesis, not a default.
- Do not allow a third layer unless a two-layer core has already proven robust.
- Do not assume every layer belongs in entry, hold, and exit. Assign roles by evidence.
- If a layer materially improves entry quality but not hold quality, test it as entry-only before promoting it further.
- If a slower layer improves directional permission but degrades exit behavior, do not force it into exit logic without evidence.
- If a faster layer mostly restates a visible slower state, treat that as redundancy unless paired tests show incremental value.

#### Stage 4: coarse search, then local refinement

Parameter search is allowed only after the mechanism family is stated.

Rules:

- Search coarse first.
- Use broad, discrete grids before any local refinement.
- Search multiple calibration modes where conceptually justified.
- Refine only around broad, stable regions.
- Prefer the center of a plateau over the highest single-cell headline.
- Preserve and export the full tested grid for every serious family.
- If a simpler representative and a more complex representative are close enough that paired tests do not cleanly separate them, keep both alive into the frozen comparison set rather than discarding the simpler one too early.

#### Stage 5: candidate selection from internal evidence only

Select the leading comparison set using:

- discovery walk-forward results,
- candidate-selection holdout results,
- paired comparisons among the nearest internal rivals,
- plateau breadth,
- ablation evidence,
- cost resilience,
- trade-quality diagnostics,
- simplicity.

Rules:

- Freeze a **comparison set**, not only a provisional winner.
- The frozen comparison set must include the simplest viable representative from each surviving family cluster and the nearest serious internal rivals.
- At this stage, the reserve/internal window must still be untouched.

#### Stage 6: freeze

Before touching the reserve/internal window, freeze:

- exact features / transforms,
- exact lookbacks,
- exact threshold calibration rules,
- exact state machine,
- exact entry / hold / exit logic,
- exact position sizing,
- exact evaluation code path,
- exact comparison set.

Export, before reserve:

- the frozen system specification,
- the frozen comparison-set ledger,
- the final search tables needed to explain selection,
- the provenance declaration up to freeze.

No redesign or retuning is allowed after this point.

#### Stage 7: reserve/internal evaluation

Evaluate the frozen system and the frozen comparison set exactly once on the reserve/internal window.

- Report reserve/internal separately from discovery and selection holdout.
- Do not relabel reserve/internal as clean OOS.
- If reserve/internal activity is too sparse to support inference, say so explicitly.
- No redesign, retuning, or tie-breaking redesign is allowed after reserve/internal is seen.

#### Stage 8: benchmark comparison

If benchmark specifications are separately supplied, do not consult them until after the frozen candidate has completed reserve/internal evaluation.

When comparing:

- use paired evaluation where possible,
- use the same synthetic paths for paired bootstrap,
- separate **relative performance** from **evidence cleanliness**.

### Complexity budget

For the main scientific search:

- maximum three logical layers,
- maximum one slower contextual layer,
- maximum one faster state layer,
- maximum one optional entry-only confirmation layer,
- maximum six tunable quantities in the final frozen candidate,
- no regime-specific parameter sets,
- no leverage, no pyramiding, no discretionary overrides.

If a more complex system wins, the burden of proof is higher: it must beat the simpler frontier on paired tests and show a comparably broad or broader plateau.

### Mandatory evaluation

Every serious candidate must be evaluated with:

1. discovery walk-forward on unseen windows,
2. candidate-selection holdout,
3. reserve/internal evaluation after freeze,
4. parameter plateau / perturbation test with at least ±20% perturbation or nearest-grid equivalent on each tunable quantity,
5. cost sensitivity analysis including a 50 bps round-trip stress test,
6. component ablation,
7. moving-block bootstrap on daily returns with multiple block sizes,
8. paired bootstrap versus nearby internal rivals and, if available, benchmarks,
9. regime / epoch decomposition,
10. trade-distribution analysis,
11. rolling-window stability across multiple window lengths,
12. per-regime signal decomposition: effective, sign-reversed, or noise-only,
13. provenance audit confirming which artifacts were and were not consulted before freeze.

### Metric requirements

Use, at minimum:

- daily-return Sharpe,
- CAGR,
- max drawdown,
- trade count,
- exposure,
- win rate,
- mean and median trade return,
- mean and median holding period,
- top-winner concentration,
- bottom-tail damage.

Do not use full-sample Sharpe alone to select a winner.

### Hard acceptance criteria

A candidate must satisfy all of the following to be considered robust:

- positive edge after 20 bps round-trip cost on aggregate discovery walk-forward,
- positive performance after cost on the candidate-selection holdout,
- at least 20 trades across discovery test windows combined,
- at least 10 trades on the candidate-selection holdout unless the mechanism is explicitly designed to be sparse and the evidence burden is met elsewhere,
- no clear collapse across major historical regimes,
- broad plateau rather than a narrow optimum,
- every retained layer earns its place by ablation,
- no lookahead, no post-freeze retuning, and no pre-freeze artifact contamination,
- if a more complex candidate does not show a meaningful paired advantage over a simpler nearby rival, the simpler rival wins.

Additional rule for a **clean OOS** claim:

- not available from the supplied file alone under V6;
- a clean OOS claim requires a later evaluation on genuinely appended future data that was not present during discovery, selection, or reserve/internal analysis.

### Evidence labels

Use these labels exactly:

- **CLEAN OOS CONFIRMED**: reserved only for a later evaluation on genuinely appended future data after the current-file research is complete.
- **INTERNAL ROBUST CANDIDATE**: passes all hard criteria on discovery and selection holdout, with reserve/internal reported honestly as internal evidence only.
- **NO ROBUST IMPROVEMENT**: fails one or more hard criteria.

If benchmark comparison is performed, report it separately from the evidence label.

### Ranking criteria

Among candidates that pass the hard criteria, rank by:

1. stronger unseen-data robustness,
2. stronger paired-bootstrap profile,
3. lower drawdown at comparable growth,
4. broader plateau,
5. lower complexity,
6. stronger cost resilience,
7. better trade quality,
8. stronger reserve/internal result,
9. full-sample performance as descriptive context only.

### Deliverables

Produce:

- a data-audit report,
- machine-readable audit tables,
- a Phase 1 data-decomposition report,
- the full Stage 1 feature registry and result table,
- the shortlist ledger with keep / drop reasons,
- the frozen comparison-set ledger,
- the frozen system specification,
- the frozen system JSON,
- full validation results,
- the reserve/internal evaluation result,
- the provenance declaration,
- the evidence label,
- benchmark comparison only if benchmark specs are separately supplied after reserve/internal evaluation,
- charts for equity, drawdown, walk-forward, bootstrap, regime breakdown, cost sensitivity, and trade distribution.

### Anti-patterns

Reject any workflow that does any of the following:

- starts from a favored architecture instead of from measurement,
- narrows the search space because of prior specific results,
- imports prior shortlist tables or frozen candidate tables before generating current-session results,
- treats reproduced tables as current-session evidence,
- treats prior work as proof,
- chooses a winner from full-sample Sharpe alone,
- uses the reserve/internal window to break ties before the comparison set is frozen,
- promotes a layer into entry / hold / exit without ablation evidence,
- adds complexity without paired evidence,
- selects a sharp spike over a broad plateau,
- quietly retunes after the candidate-selection holdout,
- quietly retunes after reserve/internal evaluation,
- confuses internally strong results with clean OOS proof,
- fails to export the full scan manifest and candidate ledger,
- mistakes a faster transport of slower state for independent incremental information.

## Fresh Re-derivation Rules

1. This session must scan the declared search space from scratch. It must not use prior named features, prior named lookbacks, prior thresholds, or prior parameter values as narrowing priors.
2. Before freeze, do not consult any prior result files, logs, reports, system specifications, benchmark specifications, or serialized outputs.
3. Two prior sessions have already been run and they produced different frozen outcomes. Treat neither as privileged. The new session must follow its own evidence.
4. This session must use the split defined in this document. Do not revert to older splits.
5. The reserve window in this version is internal only and is not eligible for clean OOS.
6. If the new session converges on the same conclusion as earlier work, record that convergence explicitly after freeze.
7. If the new session diverges, do not treat earlier work as more correct. Follow the new evidence.
8. If no candidate clears the hard gates on discovery plus selection holdout, report **NO ROBUST IMPROVEMENT** rather than forcing a winner.

## Meta-knowledge from Prior Research

### New or corrected methodological lessons

- A layer must prove **incremental information**, not merely higher-frequency visibility of information already available from a slower completed bar.
- Layering is a hypothesis, not a default. A simpler single-layer system can be the strongest result if extra layers mainly restate the same edge.
- Evaluate native faster-timeframe signals separately from transported slower-timeframe state. They are not interchangeable evidence objects.
- Preserve at least one simple representative from each viable family cluster until final internal comparison. A pre-reserve headline leader is not automatically the most defensible final choice.
- A session is not a clean re-derivation if it imports prior tables or frozen comparison sets before generating its own evidence from raw data.
- Export the full scan manifest, tested grids, candidate ledger, and keep / drop reasons. Otherwise later audits degrade into partial reconstruction instead of exact reproduction.
- All summary tables used in selection should be generated inside the current session from raw data.
- Denser chronological test slicing can be more informative than a small number of coarse unseen windows when the search space is wide.
