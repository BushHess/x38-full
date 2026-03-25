# BTC/USDT Spot Long-Only System Discovery — First-Principles Protocol V5

## Research protocol

### Objective

Use the attached BTC/USDT spot data (H4 and D1) to discover the strongest **scientifically defensible** long-only trading system supported by the data, under a leak-free, cost-aware, audit-ready protocol.

The target is **not** a claim of global optimum. The target is the best candidate found **inside a declared search space**, with honest evidence labeling and strict separation between:

1. measured evidence from the data,
2. design inference drawn from that evidence,
3. final selection judgment after robustness testing.

### Fixed execution assumptions

- Market: BTC/USDT spot, long-only.
- Timeframes available: H4 and D1.
- Signal timing: compute signal at bar close.
- Fill model: execute at next bar open.
- Trading cost: 10 bps per side, 20 bps round-trip.
- Warmup: no live trading before 2019-01-01; earlier data may be used for context and calibration only.
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
- honest evidence labels before impressive wording.

Novelty has no intrinsic value. Familiarity has no intrinsic cost. The data decides.

### Protocol lock before discovery

Before proposing any final strategy, lock all of the following:

- execution model,
- data split architecture,
- evaluation metrics,
- bootstrap method and parameters,
- plateau / perturbation specification,
- complexity budget,
- candidate progression gates,
- evidence labels,
- benchmark access rule.

If any of those rules change after candidate results are seen, the research must be treated as restarted.

### Data pipeline and audit

Before any feature research:

1. Parse timestamps to timezone-aware UTC.
2. Sort bars in ascending chronological order.
3. Check duplicates, missing values, malformed rows, and irregular gaps.
4. Record the exact date coverage of each timeframe.
5. Preserve native H4 and D1 frames separately.
6. When joining slower features onto faster bars, use backward as-of alignment on bar close time so only completed slower bars are visible.
7. Keep a written audit record. If the raw data has structural problems that materially affect execution assumptions, stop and report them before discovery.

### Data split architecture for this run

Use the following split for this version of the protocol:

- **Context / warmup only:** 2017-08-17 to 2018-12-31
- **Discovery window:** 2019-01-01 to 2022-12-31
- **Candidate-selection holdout:** 2023-01-01 to 2024-12-31
- **Reserve window:** 2025-01-01 to dataset end

Rules:

- The discovery window is the only zone allowed for measurement, hypothesis generation, coarse search, local refinement, and internal model comparison.
- The candidate-selection holdout stays sealed until one conceptually frozen candidate is chosen from discovery only.
- The reserve window stays sealed until the exact final specification is frozen and the selection-holdout results are recorded.
- The reserve window may be called **true OOS** only if it can be certified that the range has never been used in any earlier round of any session. If that certification does not exist, label it **reserve/internal only**, not true OOS.
- If no within-file range can be certified as globally untouched, the correct output is a frozen candidate plus internal evidence — not a false OOS claim.

### Discovery walk-forward structure

Within the discovery window, use annual, non-overlapping unseen test windows with chronological training:

- train `< 2020-01-01`, test `2020-01-01` to `2020-12-31`
- train `< 2021-01-01`, test `2021-01-01` to `2021-12-31`
- train `< 2022-01-01`, test `2022-01-01` to `2022-12-31`

Training data must always precede test data in time. No test window may leak into its own training set.

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

For each feature or channel, measure:

- predictive content on unseen discovery folds,
- decay horizon,
- turnover and trade count,
- cost sensitivity,
- regime dependence,
- redundancy versus nearby transforms.

Then evaluate **single-feature state systems** on unseen discovery folds. Do not rely on correlation alone. Require realized, executable performance.

#### Stage 2: orthogonal shortlist formation

From Stage 1, shortlist the strongest **orthogonal** representatives rather than many near-duplicates.

At minimum, keep:

- the strongest slower-timeframe context candidates,
- the strongest faster-timeframe state/timing candidates,
- any participation / flow / filter candidates that appear helpful,
- at least one credible alternative family that differs in failure mode.

Document why each shortlisted candidate survives and why obvious near-duplicates are dropped.

#### Stage 3: minimal layered architectures

Construct candidate families in increasing complexity:

1. single-feature state systems,
2. two-layer systems: slower context gate + faster state controller,
3. optional third layer: entry-only confirmation filter.

Rules:

- Start with the smallest defensible architecture.
- Do not allow a third layer unless a two-layer core has already proven robust.
- Do not assume every layer belongs in entry, hold, and exit. Assign roles by evidence.
- If a layer materially improves entry quality but not hold quality, test it as entry-only before promoting it further.
- If a slower layer improves directional permission but degrades exit behavior, do not force it into exit logic without evidence.

#### Stage 4: coarse search, then local refinement

Parameter search is allowed only after the mechanism family is stated.

Rules:

- Search coarse first.
- Use broad, discrete quantile grids before any local refinement.
- Search multiple calibration modes where conceptually justified, including expanding history and rolling-history variants.
- Refine only around broad, stable regions.
- Prefer the center of a plateau over the highest single-cell headline.
- Report the full tested grid for every serious family.

#### Stage 5: candidate selection from internal evidence only

Select the leading candidate using:

- discovery walk-forward results,
- candidate-selection holdout results,
- paired comparisons among the nearest internal rivals,
- plateau breadth,
- ablation evidence,
- cost resilience,
- trade-quality diagnostics,
- simplicity.

At this stage, the reserve window must still be untouched.

#### Stage 6: freeze

Before touching the reserve window, freeze:

- exact features,
- exact lookbacks,
- exact threshold calibration rules,
- exact state machine,
- exact entry / hold / exit logic,
- exact position sizing,
- exact evaluation code path,
- exact comparison set.

No redesign or retuning is allowed after this point.

#### Stage 7: reserve evaluation

Evaluate the frozen system exactly once on the reserve window.

- If the reserve window is globally certified untouched, it is true OOS.
- If it is not certified, report it as reserve/internal only.
- If reserve activity is too sparse to support inference, say so explicitly.

#### Stage 8: benchmark comparison

If benchmark specifications are separately supplied, do not consult them until after the frozen candidate has completed reserve evaluation.

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
3. reserve evaluation after freeze,
4. parameter plateau / perturbation test with at least ±20% perturbation or nearest-grid equivalent on each tunable quantity,
5. cost sensitivity analysis including a 50 bps round-trip stress test,
6. component ablation,
7. moving-block bootstrap on daily returns with multiple block sizes,
8. paired bootstrap versus nearby internal rivals and, if available, benchmarks,
9. regime / epoch decomposition,
10. trade-distribution analysis.
11. rolling-window stability across multiple window lengths,
12. per-regime signal decomposition: effective, sign-reversed, or noise-only.

### Metric requirements

Use, at minimum:

- daily-return Sharpe,
- CAGR,
- max drawdown,
- trade count,
- exposure,
- win rate,
- median and mean trade return,
- median and mean holding period,
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
- no lookahead or post-freeze retuning.

Additional rule for a **clean OOS** claim:

- the reserve window must be globally certified untouched and must remain positive after cost with enough activity to support inference.

If that certification or activity requirement is absent, the result may still be robust internally, but it is **not** a clean OOS proof.

### Evidence labels

Use these labels exactly:

- **CLEAN OOS CONFIRMED**: passes all hard criteria and the reserve window is globally certified untouched with positive post-cost performance and sufficient activity.
- **INTERNAL ROBUST CANDIDATE**: passes all hard criteria on discovery and selection holdout, but the reserve window is uncertified, insufficient, or unavailable for a clean OOS claim.
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
8. stronger reserve result if eligible,
9. full-sample performance as descriptive context only.

### Deliverables

Produce:

- a data-audit report,
- a Phase 1 data-decomposition report,
- the full shortlist of serious candidate families,
- the frozen system specification,
- full validation results,
- the reserve evaluation result,
- the evidence label,
- benchmark comparison only if benchmark specs are separately supplied after freeze,
- charts for equity, drawdown, walk-forward, bootstrap, regime breakdown, cost sensitivity, and trade distribution.

### Anti-patterns

Reject any workflow that does any of the following:

- starts from a favored architecture instead of from measurement,
- narrows the search space because of prior specific results,
- treats prior work as proof,
- chooses a winner from full-sample Sharpe alone,
- uses the reserve window to break ties during design,
- promotes a layer into entry / hold / exit without ablation evidence,
- adds complexity without paired evidence,
- selects a sharp spike over a broad plateau,
- quietly retunes after the candidate-selection holdout,
- quietly retunes after reserve evaluation,
- confuses internally strong results with clean OOS proof.

## Fresh Re-derivation Rules

1. This session must scan the declared search space from scratch. It must not use prior named features, prior named lookbacks, prior thresholds, or prior parameter values as narrowing priors.
2. This session must use the split defined in this document. Do not revert to older splits.
3. Do not consult any disclosure of prior specific results, prior parameterizations, or prior data-range usage before the independent candidate is frozen and the reserve metrics are recorded.
4. If the new session converges on the same conclusion as earlier work, record that convergence explicitly as independent confirmation.
5. If the new session diverges, do not treat earlier work as more correct. Follow the new evidence.
6. A range may be called **true OOS** only if it was never used in any earlier round of any session. If that cannot be proven, label it reserve/internal only.
7. If no true OOS range exists inside the supplied file, do not manufacture one by relabeling internal data. Freeze the candidate and stop with an honest evidence label.

## Meta-knowledge from Prior Research

### Lessons on feature architecture

- Distinguish **context**, **state**, and **entry confirmation**. These are different jobs.
- A real system often improves when each information type is given the role it naturally supports instead of being forced to do everything.
- Slower directional context and faster state persistence often complement each other better than either one alone.
- Participation / flow-like information may improve trade selection without being strong enough to act as the main directional engine.
- If a signal improves entries but weakens holding behavior, keep it in entry-only tests rather than automatically extending it into hold or exit logic.

### Lessons on timeframe design

- Multi-timeframe systems work best when slower data defines whether directional risk should be accepted at all, while faster data manages timing, state persistence, and churn control.
- Faster layers can make a system look better in-sample by reacting quickly, but that speed can become chop and turnover if the layer is asked to carry the entire edge.
- Cross-timeframe alignment must be treated as a first-class scientific issue, not a coding detail. A good idea with bad alignment is not a valid result.

### Lessons on robustness

- Real edge tends to survive multiple views of the same question: walk-forward, holdout, bootstrap, cost stress, regime decomposition, and ablation.
- Artifacts often show one or more of these signatures: sharp parameter spikes, strong full-sample numbers with weak unseen data, dependence on a few outsized winners, churn-heavy trade logs, or collapse in one market regime.
- If several nearby transforms of the same underlying phenomenon all work, that is stronger evidence than one isolated transform winning by a small margin.

### Lessons on process

- Single-feature executable state systems should be tested early. They reveal where the edge actually lives and reduce wasted exploration.
- Coarse search should come before refinement. Local search without a good coarse map wastes time and invites overfitting.
- Redundancy pruning should happen early. Too many near-duplicate candidates create noise, false breadth, and slow decision-making.
- Ablation should be used as a gate, not as a cosmetic appendix. If a component does not earn its place, remove it.
- Delay any “practical enhancement” until a clean core mechanism exists. Otherwise the research turns into uncontrolled feature stacking.

### Lessons on evaluation

- Paired comparisons are more trustworthy than separate headline metrics when candidates are close.
- Trade quality matters. Hit rate, median trade, hold-time distribution, winner concentration, and turnover often explain why two similar Sharpe numbers are not equally trustworthy.
- Full-sample results are descriptive only. They are useful for context, not for winner selection.
- A candidate chosen from the center of a plateau is usually more defensible than the highest single grid cell.

### Lessons on data splits and evidence labeling

- One holdout is not enough when the search is wide. A disciplined sequence of discovery, selection holdout, freeze, and reserve is cleaner.
- Any range used to redesign, retune, or even repeatedly interpret candidates is no longer clean final evidence.
- Evidence cleanliness and strategy quality are separate questions. A strong internal candidate may still lack a clean OOS proof.
- If the reserve slice is uncertified or too short, the right answer is “internal only” or “insufficient proof,” not overclaiming.

### Additional guidance

- Prefer the simplest representative from a winning cluster of redundant transforms.
- Do not reward novelty. Do not penalize resemblance. Reward evidence.
- If a slower layer hurts exits, demote it from exit logic rather than defending it on theory.
- If a faster layer mainly improves timing, keep it in that role.
- Honest negative findings are part of the output. A clean rejection is better than an overfit winner.
