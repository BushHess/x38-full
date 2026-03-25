# BTC/USDT Spot Long-Only System Discovery — Final Same-File Convergence Audit Protocol V8

## Research protocol

### Objective

Use the supplied BTC/USDT spot data to discover the strongest **scientifically defensible** long-only trading system supported by the data, under a leak-free, cost-aware, audit-ready, provenance-controlled protocol.

This version is a **final same-file convergence audit**. Its purpose is to test whether a tightened, better-governed protocol produces a stable internal result **without importing prior-session specifics**. Its purpose is **not** to imply that later same-file work is automatically better than earlier work, and it does **not** convert the current file into a source of clean new OOS evidence.

The target is **not** a claim of global optimum. The target is the best candidate found **inside a declared search space**, with honest evidence labeling and strict separation between:

1. measured evidence from the data,
2. design inference drawn from that evidence,
3. final selection judgment after robustness testing.

This protocol is written for **one last same-file audit only**. It is not an invitation to continue prompt-level iteration on the current file beyond V8.

### Admissible inputs and provenance lock

Before the frozen candidate is selected, the only admissible quantitative inputs are:

- this prompt,
- the raw BTC/USDT data files supplied for the session.

Expected raw files:

- one native H4 CSV,
- one native D1 CSV.

If filenames differ, identify them by the `interval` column.

Expected raw schema per file:

- `symbol`
- `interval`
- `open_time`
- `close_time`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `num_trades`
- `taker_buy_base_vol`
- `taker_buy_quote_vol`

Rules:

- Treat the schema above as the admissible raw market-data surface for this session.
- If extra columns exist, log them before using them. Do not silently expand the feature surface.
- Every table used for candidate selection must be generated inside the current session from raw data.
- Keep a **provenance log** listing every non-raw artifact consulted and when it was consulted.
- Keep a separate statement for:
  - **procedural independence before freeze**, and
  - **global cross-session split independence**.  
  These are different claims and must not be conflated.
- If any disallowed artifact is consulted before freeze, the session is **not** a clean independent re-derivation and that must be stated explicitly in the deliverables.
- Do not present reproduced or imported tables as if they were computed in the current session.

Not admissible before freeze:

- prior reports,
- prior session logs,
- prior system specifications,
- prior JSON outputs,
- prior shortlist tables,
- benchmark specifications,
- any precomputed tables or artifacts from earlier sessions.

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
- All timestamps must be interpreted as UTC unless the raw file explicitly proves otherwise.

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

Methodological tightening can improve governance and auditability, but it does not by itself create new independent evidence. Do not treat prompt editing on the same file as a hidden substitute for new data. Do not treat split changes after seeing another same-file result as hidden new evidence either.

### Protocol lock before discovery

Before proposing any final strategy, lock all of the following:

- execution model,
- admissible inputs,
- data split architecture,
- discovery fold structure,
- evaluation metrics,
- the exact feature-library manifest format,
- the exact feature-library manifest for this run,
- bootstrap method and parameters,
- random seeds for every stochastic procedure used in selection,
- plateau / perturbation specification,
- complexity budget,
- candidate progression gates,
- evidence labels,
- benchmark access rule,
- candidate-ledger format,
- pairwise-comparison matrix format,
- the operational definition of a **meaningful paired advantage**,
- threshold-calibration mode taxonomy allowed in the search,
- mixed-timeframe return-alignment convention for paired evaluation,
- segment trade-count convention,
- deterministic tie-break rule for paired-indeterminate candidates,
- anomaly-disposition register format,
- session-finality statement and stop condition for same-file prompt iteration.

Rules:

- The exact feature-library manifest must be frozen **before any Stage 1 results are inspected**.
- The exact bootstrap seed(s), resample count, and block-size set must be frozen **before any candidate-to-candidate paired comparison is computed**.
- If any of the locked items above changes after candidate results are seen, the research must be treated as restarted.

Under V8, repeated same-file prompt revision is itself a search dimension. This protocol is intended to freeze that dimension for one last same-file audit rather than to encourage further same-file prompt tuning.

### Data pipeline and audit

Before any feature research:

1. Parse timestamps to timezone-aware UTC.
2. Sort bars in ascending chronological order.
3. Check duplicates, missing values, malformed rows, irregular gaps, nonstandard bar durations, zero-activity rows, and impossible OHLC rows.
4. Record the exact date coverage of each timeframe.
5. Preserve native H4 and D1 frames separately.
6. Build a written **anomaly-disposition register** before Stage 1 begins. For every anomaly class, state whether the rule is:
   - retained exactly as supplied,
   - dropped by an explicit deterministic rule,
   - excluded from scoring but retained in audit tables.
7. Do not silently repair anomalous rows. Any exclusion, retention, de-duplication, masking, or execution-impact rule must be logged explicitly.
8. When joining slower features onto faster bars, use backward as-of alignment on slower **close_time** so only completed slower bars are visible.
9. Reconcile native D1 bars with day-aggregated native H4 bars on overlapping dates and log any material mismatch.
10. Keep a written audit report **and** machine-readable audit tables.
11. If the raw data has structural problems that materially break the execution assumptions, stop and report them before discovery.

### Data split architecture for this run

Use the following split for this version of the protocol:

- **Context / warmup only:** 2017-08-17 to 2019-12-31
- **Discovery window:** 2020-01-01 to 2023-06-30
- **Candidate-selection holdout:** 2023-07-01 to 2024-09-30
- **Reserve/internal window:** 2024-10-01 to dataset end

Rationale:

- discovery is long enough to contain multiple materially different market states,
- the holdout is long enough to discriminate among frozen candidates before reserve,
- the reserve remains a later internal stress slice rather than a tie-break design tool,
- keeping the same final-audit split avoids turning split selection itself into another same-file optimization pass after results have already been seen under earlier sessions.

Rules:

- The discovery window is the only zone allowed for measurement, hypothesis generation, coarse search, local refinement, and family promotion.
- The candidate-selection holdout stays sealed until the comparison set is frozen from discovery only.
- The reserve/internal window stays sealed until the exact frozen leader and the exact frozen comparison set are recorded.
- For this version of the protocol, the within-file reserve is **internal only** and is **not eligible** to be labeled clean OOS.
- If genuinely new data is appended after the current file end, that later appended period may be used for a clean OOS test. The current file alone may not earn that label.
- Treat this split as the final same-file convergence-audit split for the current file rather than as one step in an open-ended series of same-file prompt revisions.

### Discovery walk-forward structure

Within the discovery window, use quarterly, non-overlapping unseen test windows with chronological training / calibration:

- train / calibrate `< 2020-01-01`, test `2020-01-01` to `2020-03-31`
- train / calibrate `< 2020-04-01`, test `2020-04-01` to `2020-06-30`
- train / calibrate `< 2020-07-01`, test `2020-07-01` to `2020-09-30`
- train / calibrate `< 2020-10-01`, test `2020-10-01` to `2020-12-31`
- train / calibrate `< 2021-01-01`, test `2021-01-01` to `2021-03-31`
- train / calibrate `< 2021-04-01`, test `2021-04-01` to `2021-06-30`
- train / calibrate `< 2021-07-01`, test `2021-07-01` to `2021-09-30`
- train / calibrate `< 2021-10-01`, test `2021-10-01` to `2021-12-31`
- train / calibrate `< 2022-01-01`, test `2022-01-01` to `2022-03-31`
- train / calibrate `< 2022-04-01`, test `2022-04-01` to `2022-06-30`
- train / calibrate `< 2022-07-01`, test `2022-07-01` to `2022-09-30`
- train / calibrate `< 2022-10-01`, test `2022-10-01` to `2022-12-31`
- train / calibrate `< 2023-01-01`, test `2023-01-01` to `2023-03-31`
- train / calibrate `< 2023-04-01`, test `2023-04-01` to `2023-06-30`

Rules:

- Training / calibration data must always precede the test window in time.
- No test window may leak into its own training set.
- Context / warmup data may be used only to initialize historical calculations and early calibration, not to score candidate performance.
- All train-window calibrations must be recomputed fold by fold. Do not reuse a threshold table that saw the future fold.

### Search-space discipline

Search the space in layers. Do not jump directly to high-complexity systems.

#### Stage 1: raw measurement and single-feature state systems

Before any Stage 1 scoring, build and freeze a **finite feature-library manifest** using only transforms derivable from the admissible raw schema.

The manifest must span, at minimum:

- directional persistence / continuation,
- trend quality / return normalized by volatility,
- location within rolling range / distance to extremes,
- drawdown / pullback state,
- volatility level and clustering,
- participation / flow,
- candle-structure summaries,
- cross-timeframe relationships,
- calendar effects.

Manifest design rules:

- Cover both native timeframes where conceptually valid.
- Use predeclared parameter ladders that are monotone, sparse, and role-consistent, rather than many tightly adjacent near-duplicates.
- Declare, for every feature:
  - feature ID,
  - family,
  - formula description,
  - timeframe,
  - bucket,
  - admissible tails,
  - parameter ladder,
  - threshold-mode taxonomy,
  - calibration-mode taxonomy.
- The manifest may include transported slower-state audits on the faster timeframe, but only as a separate control bucket.
- No feature, transform, parameter ladder, threshold mode, or calibration mode may be added after Stage 1 results are inspected.

Run Stage 1 in the following order:

1. **Native D1 scan**
2. **Native H4 scan**
3. **Cross-timeframe relationship scan**
4. **Transported slower-state audit on H4**

Rules:

- Evaluate **native D1**, **native H4**, **cross-timeframe relations**, and **transported slower-state audits** as separate buckets.
- A transported slower-timeframe clone is admissible as a **redundancy control** and incremental-information test, but it does **not** count as an independent faster-timeframe frontier candidate unless it proves incremental value beyond both:
  - the corresponding native slower system, and
  - the best genuine native faster candidate in the same role.
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
  - parameter ladder,
  - threshold mode,
  - calibration mode,
  - exact result table for every scanned config.

Stage 1 promotion gate:

- positive edge after 20 bps round-trip cost on aggregate discovery walk-forward,
- at least 20 trades across discovery test windows combined unless a sparse-design exception is explicitly documented,
- at least half of discovery folds nonnegative after cost, or a documented sparse exception with compensating evidence,
- no obvious dependence on one isolated quarter,
- no unresolved leakage or anomaly-handling ambiguity.

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
- Freeze family representatives by **failure mode**, not by narrative attachment to a formula label.
- As a default cap, keep **no more than one primary and one backup representative** from a closely related family cluster for the same role unless a written orthogonality case is made from discovery evidence only.

#### Stage 3: minimal layered architectures

Construct candidate families in increasing complexity:

1. single-feature state systems,
2. two-layer systems: permission gate + state controller,
3. optional third layer: entry-only confirmation filter.

Rules:

- Start with the smallest defensible architecture.
- Layering is a hypothesis, not a default.
- Do not allow a third layer unless a two-layer core has already proven robust.
- Build layered candidates only from representatives that survived Stage 2.
- Do not brute-force the full cross-product of all Stage 1 features into layered search.
- Do not assume every layer belongs in entry, hold, and exit. Assign roles by evidence.
- If a layer materially improves entry quality but not hold quality, test it as entry-only before promoting it further.
- If a slower layer improves directional permission but degrades exit behavior, do not force it into exit logic without evidence.
- If a faster layer mostly restates a visible slower state, treat that as redundancy unless paired tests show incremental value.
- An entry-only confirmation layer must survive its own trade-count shrinkage. A small Sharpe uplift with a severe trade collapse is not enough.

#### Stage 4: coarse search, then local refinement

Parameter search is allowed only after the mechanism family is stated.

Rules:

- Search coarse first.
- Use broad, discrete grids before any local refinement.
- Search multiple calibration modes where conceptually justified.
- Refine only around broad, stable regions.
- Prefer the center of a plateau over the highest single-cell headline.
- Preserve and export the full tested grid for every serious family.
- Plateau testing must perturb every tunable quantity by at least ±20% or nearest-grid equivalent.
- A local maximum is not promotable unless the surrounding nearest-grid cells preserve the same directional story.
- Do not use holdout or reserve results to decide which discovery-region deserves local refinement.

#### Stage 5: candidate selection from internal evidence only

Run Stage 5 in three substeps.

**Stage 5A — discovery-only freeze of the comparison set**

Use discovery evidence only to freeze the comparison set:

- discovery walk-forward results,
- discovery-only paired comparisons,
- discovery-only plateau breadth,
- discovery-only ablation evidence,
- discovery-only cost resilience,
- discovery-only trade-quality diagnostics,
- discovery-only redundancy audit.

Rules:

- Freeze a **comparison set**, not only a provisional winner.
- The frozen comparison set must include the simplest viable representative from each surviving family cluster and the nearest serious internal rivals.
- The operational definition of a **meaningful paired advantage** must be locked before the first paired comparison is run.
- That definition must be driven primarily by **paired mean daily return on the common daily domain**, not by headline Sharpe alone.
- The candidate-selection holdout must still be untouched at the end of Stage 5A.

**Stage 5B — candidate-selection holdout ranking**

Open the candidate-selection holdout only after the comparison set is frozen.

Rules:

- Evaluate **only** frozen specifications on holdout.
- Do not add new candidates, new features, new layers, new calibration modes, new parameter cells, or new family clusters after the holdout is opened.
- Do not reopen local neighborhoods because holdout happens to favor nearby cells.
- Build a pairwise comparison matrix among the nearest serious rivals.

**Stage 5C — pre-reserve leader declaration**

Select the pre-reserve leader using:

- discovery walk-forward robustness,
- holdout robustness,
- paired comparisons among the nearest internal rivals,
- plateau breadth,
- ablation evidence,
- cost resilience,
- regime / epoch decomposition on pre-reserve data,
- trade-quality diagnostics,
- simplicity.

Decision rule:

- if a more complex candidate does not show a meaningful paired advantage over a simpler nearby rival, the simpler rival wins;
- if two candidates of equal complexity remain paired-indeterminate, apply this deterministic tie-break order:
  1. broader plateau,
  2. lower pre-reserve drawdown at comparable pre-reserve growth,
  3. stronger fold consistency,
  4. higher trade count,
  5. lower cross-timeframe dependence,
  6. fixed lexical order of candidate ID as final fallback.

At this stage, the reserve/internal window must still be untouched.

#### Stage 6: freeze

Before touching the reserve/internal window, freeze:

- exact features / transforms,
- exact lookbacks,
- exact threshold calibration rules,
- exact state machine,
- exact entry / hold / exit logic,
- exact position sizing,
- exact evaluation code path,
- exact comparison set,
- the pairwise comparison matrix,
- the anomaly-disposition register,
- the stochastic-evaluation settings,
- the common daily-return alignment rule,
- the segment trade-count convention.

Export, before reserve:

- the frozen system specification,
- the frozen comparison-set ledger,
- the pairwise comparison matrix,
- the final search tables needed to explain selection,
- the final plateau tables,
- the final ablation tables,
- the provenance declaration up to freeze,
- the serialized stochastic settings used in selection.

No redesign or retuning is allowed after this point.

#### Stage 7: reserve/internal evaluation

Evaluate the frozen system and the frozen comparison set exactly once on the reserve/internal window.

Rules:

- Report reserve/internal separately from discovery and selection holdout.
- Do not relabel reserve/internal as clean OOS.
- If reserve/internal activity is too sparse to support inference, say so explicitly.
- If reserve/internal contradicts the pre-reserve leader, report that contradiction plainly.
- Reserve/internal may corroborate, weaken, or downgrade confidence in the frozen leader, but it may **not** be used to retroactively promote a different winner or reopen the search.
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
2. candidate-selection holdout after the comparison set is frozen,
3. reserve/internal evaluation after freeze,
4. parameter plateau / perturbation test with at least ±20% perturbation or nearest-grid equivalent on each tunable quantity,
5. cost sensitivity analysis including a 50 bps round-trip stress test,
6. component ablation,
7. moving-block bootstrap on daily returns with multiple block sizes,
8. paired bootstrap versus nearby internal rivals and, if available, benchmarks,
9. regime / epoch decomposition **before reserve** and again on full internal data,
10. trade-distribution analysis,
11. rolling-window stability across multiple window lengths,
12. per-regime signal decomposition: effective, sign-reversed, or noise-only,
13. provenance audit confirming which artifacts were and were not consulted before freeze,
14. transport-vs-native redundancy audit for any slower-state feature reused on H4.

Additional mandatory conventions:

- All candidate-to-candidate paired tests must be performed on a common **daily UTC return** domain.
- Faster-timeframe strategies must therefore be aggregated to daily UTC returns before paired bootstrap or paired matrix ranking.
- The segment trade-count convention must be locked before scoring and applied consistently to discovery, holdout, reserve, and full-internal reporting.
- Every stochastic procedure that influences selection must have its seed and configuration serialized in the saved outputs.

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
- bottom-tail damage,
- positive discovery-fold share,
- worst discovery-fold CAGR.

Do not use full-sample Sharpe alone to select a winner.

### Hard acceptance criteria

A candidate must satisfy all of the following to be considered robust:

- positive edge after 20 bps round-trip cost on aggregate discovery walk-forward,
- positive performance after cost on the candidate-selection holdout,
- at least 20 trades across discovery test windows combined,
- at least 10 trades on the candidate-selection holdout unless the mechanism is explicitly designed to be sparse and the evidence burden is met elsewhere,
- at least half of discovery folds nonnegative after cost unless a sparse-design exception is explicitly defended,
- no clear collapse across major pre-reserve regimes,
- no strong pre-reserve evidence that the signal is sign-reversed in a major regime while still being treated as a general-purpose system,
- broad plateau rather than a narrow optimum,
- every retained layer earns its place by ablation,
- no lookahead, no post-freeze retuning, and no pre-freeze artifact contamination,
- every stochastic selection step must be reproducible from serialized settings or from explicitly frozen saved tables,
- a transported slower-state clone may not be the final leader without incremental paired evidence,
- if a more complex candidate does not show a meaningful paired advantage over a simpler nearby rival, the simpler rival wins.

Additional rule for this version:

- reserve/internal may change the confidence statement, but it may not change the frozen winner.

### Evidence labels

Use these labels exactly:

- **CLEAN OOS CONFIRMED**: reserved only for a later evaluation on genuinely appended future data after the current-file research is complete.
- **INTERNAL ROBUST CANDIDATE**: passes all hard criteria on discovery and selection holdout, with reserve/internal reported honestly as internal evidence only.
- **NO ROBUST IMPROVEMENT**: fails one or more hard criteria.

If benchmark comparison is performed, report it separately from the evidence label.

### Ranking criteria

Among candidates that pass the hard criteria, rank by:

1. stronger unseen-data robustness,
2. stronger holdout robustness,
3. stronger paired-bootstrap profile on the common daily domain,
4. broader plateau,
5. lower drawdown at comparable growth,
6. lower complexity,
7. stronger cost resilience,
8. better trade quality,
9. reserve/internal result as internal context only,
10. full-sample performance as descriptive context only.

### Deliverables

Produce:

- a data-audit report,
- machine-readable audit tables,
- the anomaly-disposition register,
- a Phase 1 data-decomposition report,
- the full Stage 1 feature registry and result table,
- the frozen Stage 1 feature-library manifest,
- the shortlist ledger with keep / drop reasons,
- the frozen comparison-set ledger,
- the pairwise comparison matrix,
- the frozen system specification,
- the frozen system JSON,
- full validation results,
- the reserve/internal evaluation result,
- the provenance declaration,
- the serialized stochastic settings used in selection,
- the evidence label,
- benchmark comparison only if benchmark specs are separately supplied after reserve/internal evaluation,
- charts for equity, drawdown, walk-forward, bootstrap, regime breakdown, cost sensitivity, plateau, and trade distribution,
- a session-finality statement explicitly confirming that this was the final same-file audit on the current file.

### Anti-patterns

Reject any workflow that does any of the following:

- starts from a favored architecture instead of from measurement,
- narrows the search space because of prior specific results,
- imports prior shortlist tables or frozen candidate tables before generating current-session results,
- treats reproduced tables as current-session evidence,
- treats prior work as proof,
- chooses a winner from full-sample Sharpe alone,
- uses the candidate-selection holdout to expand the candidate space after seeing results,
- uses the reserve/internal window to break ties before freeze,
- uses the reserve/internal window to replace the frozen winner after freeze,
- changes the split because another same-file run already produced an uncomfortable answer,
- runs stochastic selection procedures without serializing the seed and configuration,
- forces a single winner from paired-indeterminate simple rivals by narrative preference alone,
- promotes a transported slower-state clone as a genuine faster frontier without incremental proof,
- promotes a layer into entry / hold / exit without ablation evidence,
- adds complexity without paired evidence,
- selects a sharp spike over a broad plateau,
- quietly retunes after the candidate-selection holdout,
- quietly retunes after reserve/internal evaluation,
- confuses internally strong results with clean OOS proof,
- treats a later same-file result as automatically more correct merely because it is newer,
- uses V8 as justification for any further same-file prompt iteration beyond this final audit.

## Fresh Re-derivation Rules

1. This session must scan the declared search space from scratch. It must not use prior named features, prior named lookbacks, prior thresholds, or prior parameter values as narrowing priors.
2. Before freeze, do not consult any prior result files, logs, reports, system specifications, benchmark specifications, or serialized outputs.
3. Four prior research sessions have already been run and they produced different frozen outcomes. Treat none of them as privileged. The new session must follow its own evidence.
4. Divergence among prior sessions is not a reason to reconcile them by construction. Treat the search space as open.
5. Do not import prior frozen candidates, prior shortlists, prior favored feature families, prior parameter regions, or prior decision outcomes as narrowing priors.
6. This session must use the split defined in this document. Do not reopen split selection as an additional same-file search dimension.
7. The reserve window in this version is internal only and is not eligible for clean OOS.
8. If the new session converges on the same conclusion as earlier work, record that convergence explicitly after freeze.
9. If the new session diverges, do not treat earlier work as more correct. Follow the new evidence.
10. If no candidate clears the hard gates on discovery plus selection holdout, report **NO ROBUST IMPROVEMENT** rather than forcing a winner.
11. This protocol is the final same-file convergence audit for the current file. After V8, stop same-file iteration regardless of convergence or divergence. Stronger claims require new appended data.

## Meta-knowledge from Prior Research

### New methodological lessons

- Procedural blindness before freeze and globally clean within-file independence are different claims. Report them separately.
- If stochastic procedures influence selection, the seed and resample configuration are part of the frozen protocol and must be serialized.
- Mixed-timeframe paired evaluation needs a common daily-return domain and an explicit segment trade-count convention. Otherwise comparisons become ambiguous even when each standalone backtest is valid.
- Once a final same-file split has been declared and successfully executed without a governance failure, changing that split after seeing results is split-chasing rather than methodological improvement.
- Reserve/internal evidence can corroborate or contradict a frozen leader, but it cannot legitimately be used to retroactively promote a different winner without new data.
