# Baseline Qualification Constitution

## 1. Scope

This document defines how x40 turns an incumbent strategy into an x40 baseline.

It governs:

- source parity,
- historical qualification,
- standardized comparison,
- clean-confirmation setup,
- forward ledger opening,
- and baseline state transitions.

It applies to all leagues.  
League-specific rules are layered on top, not substituted in place of this constitution.

---

## 2. Terminology

### Physical file schema
The raw CSV or dataset may contain more fields than the strategy logic actually uses.

### Data surface used by logic
The subset of admitted fields that a given system is allowed to touch.

This separation is mandatory.  
A strategy is **not** reclassified into a richer league merely because the raw file physically contains extra columns that the logic never reads.

### Historical-seed evidence
Any evidence produced from a fixed historical archive available at qualification time.

### Clean-confirmation evidence
Any evidence produced only from data strictly later than `freeze_cutoff_utc`.

### Source-native parity evidence
Evidence produced under the source system’s own reporting conventions for the purpose of parity.

### Standardized comparison evidence
Evidence produced under an x40 comparison profile for apples-to-apples comparison.

---

## 3. League rules

### 3.1 `OHLCV_ONLY`
A baseline in `OHLCV_ONLY` may only use:
- `open`
- `high`
- `low`
- `close`
- `volume`
- timestamps
- native-bar counts / bar index

It may not use:
- `quote_volume`
- `num_trades`
- `taker_buy_*`
- derived order-flow proxies that depend on those fields

### 3.2 `PUBLIC_FLOW`
A baseline in `PUBLIC_FLOW` may use:
- all `OHLCV_ONLY` fields
- plus public flow proxies such as taker-buy fields or equivalent public venue-level fields

It may not use:
- private fills,
- private queue position,
- hidden order-book states,
- proprietary latency data.

### 3.3 `RICHER_DATA`
This league is bootstrapped only through `A08`.  
Its admitted fields must be declared explicitly in a league constitution addendum.

---

## 4. Initial BTC historical-seed window policy

For the current BTC historical snapshot, x40 adopts the same seed windows used by gen4 D0:

- **warmup**: through `2019-12-31 UTC`
- **discovery**: `2020-01-01` through `2023-06-30 UTC`
- **holdout**: `2023-07-01` through `2024-09-30 UTC`
- **internal reserve**: `2024-10-01` through `snapshot_end`

These windows are the default qualification windows for the current BTC archive unless a future revision explicitly replaces them.

---

## 5. Metric domain

To compare D1 and H4 systems fairly, x40 measures all headline performance metrics on a **common daily UTC equity domain**.

### Rules
1. Each system is first backtested on its native execution clock.
2. Native equity is then projected onto a daily UTC mark-to-market series.
3. Sharpe, CAGR, Calmar, drawdown, exposure and decay studies are computed on that common daily series unless a study explicitly says otherwise.
4. Trade-level diagnostics retain native trade timing.

This rule prevents D1 vs H4 comparability errors.

---

## 6. Comparison profiles

### 6.1 Profile registry
x40 maintains a registry of named comparison profiles in `registry/comparison_profiles.yaml`.

### 6.2 Default profiles
#### `CP_PRIMARY_50_DAILYUTC`
- round-trip cost: `50 bps`
- metric domain: `daily UTC mark-to-market equity`
- instrument assumption: `spot, long-only, no leverage, no borrow`
- role: **headline / decision profile**

#### `CP_SENS_20_DAILYUTC`
- round-trip cost: `20 bps`
- metric domain: `daily UTC mark-to-market equity`
- instrument assumption: same as primary
- role: **sensitivity only**

### 6.3 Rules
1. `A00` may use source-native parity evidence.
2. `A01`, `A06`, decision-tree inputs and next-action outputs must use `CP_PRIMARY_50_DAILYUTC`.
3. `CP_SENS_20_DAILYUTC` may be emitted only as a clearly labeled sensitivity appendix.
4. No headline x40 conclusion may mix source-native and standardized evidence in one row or one verdict.

---

## 7. `A00` source parity rules

### 7.1 Purpose
`A00` proves that the x40 implementation faithfully reproduces the intended source system.

### 7.2 Source parity classes
#### Class `EXACT_PARITY`
Bit-level or effectively exact metric/series match to a frozen source spec.

#### Class `SOURCE_PARITY_WITH_EXPLAINED_DELTA`
Differences exist, but are fully explained by:
- metric domain harmonization,
- data availability boundaries,
- or frozen-source ambiguities that are documented and resolved.

#### Class `PARITY_FAIL`
Material mismatch with no adequate explanation.

### 7.3 Baseline-specific parity expectations
#### `OH0_D1_TREND40`
Target: `EXACT_PARITY` to the x37/v8 frozen system spec.

#### `PF0_E5_EMA21D1`
Target: at least `SOURCE_PARITY_WITH_EXPLAINED_DELTA`, because the source lineage contains historical sections and validation reforms that must be normalized cleanly.

### 7.4 A00 required outputs
- `parity_report.md`
- `parity_metrics.json`
- `equity_source.csv`
- `equity_x40.csv`
- `delta_summary.json`

No baseline may enter `A01` if `A00` is `PARITY_FAIL`.

---

## 8. `A01` baseline qualification rules

A baseline becomes `B1_QUALIFIED` only if all the following are true:

1. `A00` is not `PARITY_FAIL`;
2. no hard failures exist for lookahead, data integrity, or impossible state transitions;
3. baseline manifest exists and is complete;
4. qualification report exists;
5. `freeze_cutoff_utc` is set;
6. `forward_evaluation_ledger.csv` exists and is initialized;
7. regime decomposition and cost sensitivity are recorded;
8. standardized profile metrics exist for `CP_PRIMARY_50_DAILYUTC`;
9. the strategy meets minimum viability floors on `CP_PRIMARY_50_DAILYUTC`;
10. human reviewer signs `qualification_decision.md`.

### 8.1 A01 required outputs
- `baseline_manifest.yaml`
- `qualification_report.md`
- `qualification_state.json`
- `metrics_CP_PRIMARY_50_DAILYUTC.json`
- `metrics_CP_SENS_20_DAILYUTC.json` (optional but recommended)
- `comparison_header.json`
- `forward_evaluation_ledger.csv`
- `qualification_decision.md`

---

## 9. Minimum viability floors

These floors are **baseline qualification floors**, not claims of production superiority.

For the current BTC historical-seed constitution the default floors are evaluated on `CP_PRIMARY_50_DAILYUTC`:

- `CAGR > 0`
- `MDD <= 0.45`
- `entries_per_year` within `[6, 80]`
- `exposure` within `[0.15, 0.90]`
- `no hard fail` on data integrity / lookahead / invariants

These mirror the minimum seed-governance stance visible in gen4 D0 and are intentionally conservative.

A baseline may still be held in `B0_INCUMBENT` if it is practically useful but not yet fully re-qualified under x40.

---

## 10. Baseline states

### 10.1 `B0_INCUMBENT`
Use when:
- the system is the best currently recognized incumbent for a league,
- but x40 qualification is incomplete.

### 10.2 `B1_QUALIFIED`
Use when:
- historical qualification is complete under this constitution,
- `freeze_cutoff_utc` is declared,
- and forward tracking has begun.

### 10.3 `B2_CLEAN_CONFIRMED`
Use when:
- the baseline is already `B1_QUALIFIED`,
- clean appended data exists after `freeze_cutoff_utc`,
- and minimum clean-confirmation requirements are satisfied.

#### Default clean-confirmation requirements
A baseline may be upgraded from `B1_QUALIFIED` to `B2_CLEAN_CONFIRMED` when:

- clean block length is at least `180` calendar days, and
- one of the following is true:
  - at least `6` clean trades have completed, or
  - clean exposure covers at least `20%` of the clean block.

These are implementation defaults, not eternal truths; they may be revised in a future constitution version.

### 10.4 `B_FAIL`
Use when:
- a hard invalidation occurs, or
- clean confirmation yields a clearly negative confirmation event, or
- parity/qualification collapses under corrected implementation.

`B_FAIL` is terminal for that baseline version.

---

## 11. Clean-confirmation policy

### 11.1 One freeze, one clean timeline
Once `freeze_cutoff_utc` is set for a baseline version:
- no redesign,
- no winner switching,
- no parameter edits,
- no rescue by runner-up inside the same version.

### 11.2 Forward ledger
Every `B1_QUALIFIED` baseline must open a `forward_evaluation_ledger.csv`.

Required columns:
- `as_of_utc`
- `baseline_id`
- `baseline_version`
- `comparison_profile_id`
- `append_block_start_utc`
- `append_block_end_utc`
- `n_bars_native`
- `n_days`
- `n_entries`
- `gross_return`
- `net_return_primary`
- `max_drawdown_primary`
- `exposure`
- `canary_status`
- `notes`

### 11.3 No retroactive clean claim
Historical seed windows, holdout, and internal reserve do **not** become clean OOS retroactively.

---

## 12. Required artifact bundle for every baseline

Each baseline must have:

- `baseline_manifest.yaml`
- `frozen_system_spec.md`
- `frozen_system_spec.json` or equivalent machine-readable system definition
- `qualification_report.md`
- `qualification_state.json`
- `parity_report.md`
- `metrics_CP_PRIMARY_50_DAILYUTC.json`
- `comparison_header.json`
- `regime_decomposition.csv`
- `cost_sensitivity.csv`
- `forward_evaluation_ledger.csv`
- `state_pack/` or equivalent bundle of versioned state
- `qualification_decision.md`

---

## 13. Baseline swap rules

An active baseline may be replaced only when all of the following hold:

1. a challenger has completed `A06`;
2. the challenger is accepted by x40 review as worthy of baseline qualification;
3. the promoted challenger itself passes `A00` and `A01` as the new baseline version;
4. the old baseline is retained in the registry as a superseded historical reference.

A tracked challenger does **not** become a baseline merely because it is directionally better in historical evidence.

---

## 14. League-specific initial baseline assignments

### `OHLCV_ONLY`
Initial baseline = `OH0_D1_TREND40`

### `PUBLIC_FLOW`
Initial baseline = `PF0_E5_EMA21D1`

### `RICHER_DATA`
No baseline at bootstrap.

---

## 15. Qualification decision options

The human qualification decision at the end of `A01` must choose exactly one:

- `QUALIFY_AS_B1`
- `KEEP_AS_B0`
- `FAIL_BASELINE`

No ambiguity is allowed.

---

## 16. Constitution anti-patterns

The following are explicitly invalid:

1. qualifying a baseline without a forward ledger;
2. comparing D1 and H4 metrics on different time domains without normalization;
3. labelling `B2` before any appended clean data exists;
4. using the physical raw schema to reclassify league when the logic does not actually use those fields;
5. promoting a tracked challenger into baseline status without a full baseline qualification pass;
6. quoting one baseline on `20 bps` and another on `50 bps` in the same headline comparison;
7. letting source-native parity tables leak into x40 decision logic.
