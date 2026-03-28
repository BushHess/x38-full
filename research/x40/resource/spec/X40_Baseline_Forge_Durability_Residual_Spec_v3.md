# X40 — Baseline Forge, Durability Audit, and Residual Discovery Spec v3

**Status:** Proposed operational spec  
**Authoring intent:** implementation-ready design for repo integration  
**Primary goal:** establish a clean, replayable, league-specific baseline program **before** further residual discovery, and make durability / crowding / decay first-class evaluation objects.

**Revision note (v3):** this revision keeps all v2 fixes and adds nine more load-bearing corrections: (1) durability status now applies to active monitored baselines rather than only already-qualified baselines, (2) source-parity work is specified explicitly as A00, (3) run artifacts are separated from persistent baseline-level artifacts, (4) `forward_evaluation_ledger.csv` now has a declared schema, (5) the common daily UTC metric domain is defined exactly, (6) soft negative-confirmed evidence now maps to `B_FAIL` instead of lingering as ambiguous `B0` state, (7) `B2_CLEAN_CONFIRMED` now has a minimum appended-data floor, (8) A03 proxy liquidity metrics are aligned to the execution bar and tied to a declared deployment notional, and (9) final durability status is now assigned by an explicit aggregation policy across A01/A02/A03/A05.

---

## 0. Executive decision

The program is split into four roles and they must not be conflated:

1. **x37** remains the template for **blank-slate discovery sessions** and phase-gated freezing.
2. **x39** remains the **feature invention / residual ideation lab**.
3. **x40** is added as a new branch for **baseline qualification, durability audit, crowding audit, drift detection, and bounded requalification triggers**.
4. **x38** remains downstream **architecture / governance / contamination / protocol**; it should consume only survivors, not originate discovery.

The immediate operational baselines are:

- **OHLCV-only control baseline:** `OH0_D1_TREND40` (ported directly from x37/gen1/v8 `S_D1_TREND`)
- **Public-flow incumbent:** `PF0_E5_EMA21D1` (ported from VTREND E5 / production HOLD state)

The system must treat these as **different leagues**. No cross-league comparison is authoritative unless explicitly normalized and declared as such.

---

## 1. Why this spec exists

The repo already has three distinct but incomplete capabilities:

- x37 gives a strong **session isolation and freeze discipline**.
- x39 gives a practical **residual-feature experiment lab**, but its current replay is simplified and therefore diagnostic rather than authoritative.
- x38 is building the long-run **framework architecture**, but critical topics for recalibration and execution resilience remain open.

What is missing is the layer in between:

> a **Baseline Forge** that can say, rigorously and repeatedly, which baseline is qualified, how long it remains qualified, when it is decaying, when discovery should continue, and when the league itself should be abandoned or expanded.

This spec defines that missing layer.

---

## 2. Design principles

### 2.1 Principles carried forward

The system MUST encode the following principles:

1. **Feature invention is not feature selection.**  
   Discovery and screening are different activities.
2. **Story generates; data judges.**  
   Behavior stories, anomaly observation, and cross-domain analogy may generate ideas, but survival is decided only by falsification and incremental value.
3. **Validation order is strict.**  
   Stability -> semantic validity -> orthogonality -> multi-timeframe / multi-era consistency -> predictiveness.
4. **Falsification comes before celebration.**  
   Synthetic/null destruction and robustness-to-formalization are mandatory before a concept is allowed to claim economic content.
5. **Plateau beats spike.**  
   A robust mechanism should survive nearby formalizations or neighboring parameter values.
6. **Freeze before reserve.**  
   No holdout / reserve touch until the candidate is frozen under a declared protocol.
7. **Detect before adapt.**  
   The live program should detect decay first; bounded recalibration is an explicit separate path, not silent continuous self-retuning.
8. **Leagues stay separate.**  
   OHLCV-only, public-flow, and richer-data systems must not share one baseline namespace.
9. **The protocol is the foundation, not the winner.**  
   The deepest source of truth is the evaluation constitution, not a specific strategy.

### 2.2 Non-goals

This spec does **not** attempt to:

- prove a global optimum over all possible strategies,
- let live systems self-retune continuously,
- let x38 become the invention engine,
- let x39 simplified replay issue authoritative promotion decisions,
- pretend historical snapshot results are clean external OOS.

---

## 3. Core architecture

### 3.1 Branch responsibilities

#### x37 — Discovery arena
Use for:
- blank-slate sessions,
- phase-gated search,
- mechanism discovery,
- frozen candidate emission.

#### x39 — Residual invention lab
Use for:
- residual feature ideation,
- small targeted experiments,
- fast diagnostic comparisons,
- concept family exploration.

x39 is **not** authoritative for final baseline qualification.

#### x40 — Baseline Forge and durability branch
Use for:
- authoritative incumbent replay,
- league-specific baseline qualification,
- temporal decay audits,
- alpha half-life audits,
- capacity/crowding stress,
- canary / drift monitoring,
- bounded requalification triggers,
- pivot decisions about whether to continue invention in the same data league.

#### x38 — Downstream framework governance
Use for:
- contamination firewall,
- protocol architecture,
- artifact/version governance,
- formal specification of survivors.

### 3.2 Research flow

```text
blank-slate discovery (x37)
        │
        ├── emits frozen candidates
        │
        ├── residual challenger ideas (x39)
        │
        ▼
baseline qualification + durability/crowding audit (x40)
        │
        ├── survivors become official baselines / challengers
        │
        └── failures either die or trigger league pivot
        ▼
x38 spec/governance/protocol downstream
```

---

## 4. League model

### 4.1 Required league IDs

The implementation MUST support at least these leagues:

- `OHLCV_ONLY`
- `PUBLIC_FLOW`  
  (OHLCV + public aggressor-flow style fields such as `taker_buy_base_vol`)
- `RICHER_DATA`  
  (order book, open interest, funding, liquidation, on-chain, etc.)

### 4.2 League isolation rules

1. Every baseline, challenger, experiment, result table, and forward ledger MUST declare `league_id`.
2. No strategy may be promoted as a league baseline without a valid `league_id`.
3. Residual discovery MUST compare against the active baseline in the **same** league.
4. Cross-league comparisons are allowed only as diagnostics, never as authoritative qualification.
5. League identity is determined by **fields consumed by logic**, not by incidental extra columns physically present in a canonical raw file schema.

---

## 5. Baseline namespace and statuses

### 5.1 Baseline levels

Each baseline candidate MUST carry exactly one baseline-level verdict:

- `B0_INCUMBENT` — best-known current reference, but not yet qualified under full constitution.
- `B1_QUALIFIED` — qualified internal baseline under frozen constitution and same-snapshot evidence.
- `B2_CLEAN_CONFIRMED` — baseline remained acceptable on appended post-freeze data.
- `B_FAIL` — baseline candidate rejected.

### 5.2 Durability statuses

Every **active monitored baseline** with level `B0_INCUMBENT`, `B1_QUALIFIED`, or `B2_CLEAN_CONFIRMED` MUST also carry exactly one durability status:

- `DURABLE`
- `WATCH`
- `DECAYING`
- `BROKEN`

`B_FAIL` is not an active monitored baseline and therefore does not carry a live durability status.

These are separate from baseline levels. Example:
- a baseline may be `B0_INCUMBENT + WATCH`
- a baseline may be `B1_QUALIFIED + WATCH`
- a baseline may later become `B2_CLEAN_CONFIRMED + DECAYING`

### 5.3 Object type

Every strategy/result object MUST declare one of:

- `baseline`
- `standalone`
- `overlay`
- `from_scratch`
- `characterization`

This mirrors the repo’s existing strategy object-type separation and prevents invalid A/B comparisons.

### 5.4 Namespace separation from production verdicts

The x40 namespace MUST NOT override or masquerade as production validation authority.

- `B0/B1/B2/B_FAIL` and `DURABLE/WATCH/DECAYING/BROKEN` are **x40 research-operational baseline states**; they are not a substitute for production validation authority.
- `PROMOTE/HOLD/REJECT` remain **production machine-validation verdicts** issued by the production validation pipeline.
- A baseline can be `B1_QUALIFIED + DURABLE` and still be non-deployable until the production pipeline says otherwise.

---

## 6. Official baseline selection in v1

### 6.1 OHLCV-only official incumbent

#### ID
`OH0_D1_TREND40`

#### Source of truth
Port directly from:
`research/x37/resource/gen1/v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md`

#### Role
This is the **control baseline** for `OHLCV_ONLY`.

#### Why chosen
Because it is the cleanest balance of:
- extreme simplicity,
- exact frozen specification,
- native D1 execution,
- no regime gate,
- no cross-timeframe logic,
- no parameter calibration from data,
- positive internal reserve under both 20 bps and 50 bps round-trip cost.

#### Exact rule summary
- compute `mom40 = close_t / close_(t-40) - 1`
- signal = long iff `mom40 > 0`
- signal observed at D1 close
- position applied at next D1 open
- 100% long or 0% flat
- 10 bps per side / 20 bps RT canonical cost in frozen spec
- no resample, no gap fill, no volatility filter, no regime filter, no cross-timeframe dependence.

#### Qualification target in x40
Promote to `B1_QUALIFIED` **only after** source-parity replay and active x40 qualification replay both pass their required gates.

### 6.2 Public-flow incumbent

#### ID
`PF0_E5_EMA21D1`

#### Source of truth
Port directly from an explicit source pack that MUST include at minimum:
- `docs/algorithm/VTREND_BLUEPRINT.md`
- latest authoritative production decision artifact for E5 (for example `results/full_eval_e5_ema21d1*/reports/decision.json`)
- latest comprehensive report / status-matrix artifacts that pin the current production posture
- exact strategy configuration and replay code entry points used by the authoritative production outputs

The blueprint alone is **not** sufficient because it contains preserved historical sections and explicit outdated material.

#### Role
This is the current incumbent for the `PUBLIC_FLOW` league.

#### Important note
This is **not** OHLCV-only. It requires `taker_buy_base_vol` for VDO in the current blueprint.

#### Qualification target in x40
Start as `B0_INCUMBENT`.

Reason: production status is still `HOLD` / underresolved on WFO robustness, so it should not be treated as a fully qualified public-flow baseline until x40 first passes source-parity replay and then re-qualifies it under the active x40 constitution.

### 6.3 Shadow benchmarks

The implementation MAY keep stronger but more complex shadow benchmarks for context, but they are not official baselines unless promoted through this spec.

Initial shadow benchmark recommendation:
- `OH1_D1RET60_H4TRENDQ84_HYST` (from x37/gen1/v3-style family)

Purpose:
- protect residual search from rediscovering trivial improvements,
- while keeping `OH0_D1_TREND40` as the official clean control.

---

## 7. Baseline Qualification Constitution (BQC-v1)

### 7.1 Authority hierarchy

1. **BQC-v1** is the highest authority for x40 qualification.
2. Baseline spec files are second-level authority.
3. Run manifests and result artifacts are evidentiary outputs.
4. Human narrative reports do not override hard-gate failures.

### 7.2 Snapshot and window-profile semantics

The constitution MUST distinguish four things that v1 left too implicit:

- `source_snapshot_id` — the snapshot used by the authoritative source artifacts of a ported baseline,
- `source_window_profile_id` — the exact split architecture used by those source artifacts,
- `qualification_snapshot_id` — the active x40 archive snapshot,
- `qualification_window_profile_id` — the split architecture used for current x40 qualification.

The constitution MUST also declare `freeze_cutoff_utc`, which is the end of the active x40 archive. Only data appended **after** `freeze_cutoff_utc` is eligible for `B2_CLEAN_CONFIRMED`.

For any **ported** incumbent, x40 MUST run in two distinct stages:

1. `SOURCE_PARITY_REPLAY` — reproduce the source system on `source_snapshot_id + source_window_profile_id` and match the authoritative frozen artifacts.
2. `X40_QUALIFICATION_REPLAY` — rerun the same frozen system on `qualification_snapshot_id + qualification_window_profile_id` to produce current x40 evidence.

These two stages MUST NOT be merged into one verdict artifact. Source parity failure blocks qualification. Source parity success does **not** imply x40 qualification success.

For historical-seed qualification runs in x40, the default `qualification_window_profile_id` is `GEN4_HIST_SEED_V1`:

- warmup: through `2019-12-31`
- discovery: `2020-01-01` to `2023-06-30`
- holdout: `2023-07-01` to `2024-09-30`
- reserve_internal: `2024-10-01` to `snapshot_end`

These windows are borrowed from x37/gen4 and also match the frozen V8 same-file architecture, but they apply only to the x40 qualification replay unless the source artifacts themselves used the same profile.

### 7.3 Admitted inputs

Every x40 run MUST declare exact admitted raw inputs.

#### Minimum for `OHLCV_ONLY`
- native BTC/USDT spot CSVs at required native timeframe(s)
- canonical 13-column schema
- UTC timestamps

#### Minimum for `PUBLIC_FLOW`
- all of the above, plus required public-flow fields such as `taker_buy_base_vol`

### 7.4 Contamination statement

All x40 qualification runs MUST state:

- historical snapshot evidence is **internal only**,
- holdout and internal reserve remain contaminated for discovery purposes,
- `B2_CLEAN_CONFIRMED` requires appended post-freeze data.

### 7.4B Metric-domain and alignment semantics

BQC-v1 MUST declare both:

- `source_metric_domain_id` (if porting a source system whose authoritative artifacts use a specific metric domain),
- `qualification_metric_domain_id` for the active x40 qualification run.

Default x40 rule:

- qualification Sharpe / CAGR / MDD and all cross-baseline A01 / A03 comparisons MUST be computed on a **common daily UTC return domain**,
- native-bar return horizons may be used only for within-strategy diagnostics such as A02 half-life / horizon compression,
- if source artifacts use a different domain, source parity must reproduce the source domain exactly first, then x40 qualification must re-express results on the x40 qualification domain.


### 7.4C Exact common daily UTC metric domain

To prevent D1/H4 systems from being compared on inconsistent bar domains, BQC-v1 MUST define the daily UTC metric domain exactly:

1. Replay the frozen strategy on its native execution clock and generate the fully cost-adjusted native interval return series `r_i`.
2. Assign each native interval return to the UTC calendar day containing that interval’s `close_time`.
3. For each UTC day `d`, compound all native interval returns whose `close_time` falls in day `d`:

   `r_daily[d] = Π_i (1 + r_i) - 1`

4. Days with no native intervals are allowed only if the raw archive itself has no bars for that day; in such a case the day is omitted rather than filled.
5. Sharpe / CAGR / MDD for x40 qualification and all cross-baseline A01 / A03 comparisons MUST be computed from this `r_daily` series.
6. Native-bar metrics remain authoritative for within-strategy diagnostics such as A02 horizon compression, trade holding bars, and event-timing analysis.

The run MUST emit both:
- `return_series_native.csv`
- `return_series_daily_utc.csv`

`metric_domain_summary.json` MUST document the transformation and confirm the number of native intervals mapped into each UTC day series.

### 7.5 Required run artifact set for `X40_QUALIFICATION_REPLAY`

For every full active-snapshot qualification replay (after A00 parity has passed), the run MUST produce:

- `baseline_manifest.json`
- `input_hash_manifest.txt`
- `constitution_hash.txt`
- `frozen_spec.md`
- `frozen_spec.json`
- `source_parity_summary.json`
- `replay_parity.json`
- `metric_domain_summary.json`
- `segment_metrics.csv`
- `fold_metrics.csv`
- `regime_metrics.csv`
- `cost_sensitivity.csv`
- `trade_list.csv`
- `return_series_native.csv`
- `return_series_daily_utc.csv`
- `bootstrap_summary.csv`
- `walk_forward_summary.csv`
- `durability_summary.json`
- `capacity_summary.json`
- `verdict.json`

### 7.5A Persistent baseline-level artifacts

The following are **baseline-level persistent artifacts**, not per-run ephemeral outputs:

- `source_reference.md`
- `baseline_manifest.json`
- `frozen_spec.md`
- `frozen_spec.json`
- `forward_evaluation_ledger.csv`

A qualification run may create or update these, but they must live at the baseline root and survive across multiple appended-data evaluation blocks.

### 7.5B Forward evaluation ledger schema

`forward_evaluation_ledger.csv` MUST contain at least these columns:

- `baseline_id`
- `league_id`
- `eval_block_id`
- `block_start_utc`
- `block_end_utc`
- `data_mode` (`historical_seed`, `appended_shadow`, `appended_live`, `realized_execution`)
- `metric_domain_id`
- `n_native_intervals`
- `n_completed_trades`
- `sharpe`
- `cagr`
- `mdd`
- `expectancy_per_trade`
- `avg_holding_bars`
- `a05_canary_state`
- `durability_status_before`
- `durability_status_after`
- `requalification_action`
- `verdict_path`
- `notes`

### 7.5C Source reference contract

For every ported baseline, `source_reference.md` MUST pin:

- exact authoritative source files,
- authoritative output artifacts,
- source snapshot coverage,
- source window profile,
- source metric domain,
- verification targets and tolerances,
- code entry points used for source parity replay,
- any known outdated or historical documents that must **not** override the authoritative source pack.

For `PF0_E5_EMA21D1`, the source reference MUST explicitly identify which E5 production output directory and `decision.json` are authoritative for parity, because the blueprint itself preserves historical sections.

### 7.6 Required hard gates for B1

A candidate cannot become `B1_QUALIFIED` unless all hard gates pass:

1. **Replay parity gate**  
   If porting an existing frozen system, x40 MUST first match the authoritative source artifacts on `source_snapshot_id + source_window_profile_id` before any active-snapshot qualification is allowed. Exact integer fields (for example `trade_count_entries`, bar counts, transition counts) MUST match exactly. Floating summary metrics MUST match within declared tolerance. Source-parity artifacts and active x40 qualification artifacts MUST be stored separately.
2. **Data integrity gate**  
   Schema, timestamps, ordering, duplicate handling, null policy.
3. **Lookahead/alignment gate**  
   Especially strict for any cross-timeframe system.
4. **Invariants gate**  
   No impossible positions, negative quantities, or contract violations.
5. **Output contract gate**  
   All mandatory artifacts exist and conform to schema.
6. **Cost-model declaration gate**  
   Cost assumptions must be explicit and consistent.

### 7.6A Default parity tolerances

Unless the source spec demands something stricter:

- integer counts and state-transition counts: exact equality
- interval / daily return series values when the source series is available: absolute tolerance `1e-10`
- summary metrics: absolute tolerance `1e-6`

If the source spec demands exact matching of published verification targets, the source spec overrides these defaults.

### 7.7 Required soft gates for baseline qualification

A candidate should normally pass these to become `B1_QUALIFIED`:

1. **Segment positivity / acceptability**  
   Holdout and reserve must not collapse to non-viability under canonical harsh cost.
2. **WFO acceptability**  
   Evidence may be low power, but it must not be strongly negative.
3. **Cost resilience**  
   Performance should not collapse immediately under modest cost stress.
4. **Simplicity / replayability**  
   The baseline should be minimal for its league.
5. **No hidden calibration**  
   Thresholds or knobs may not have been silently re-fit after seeing holdout/reserve.

Soft evidence in x40 has three states:

- `ACCEPTABLE` — enough support for `B1_QUALIFIED`
- `UNDERRESOLVED` — not negative-confirmed, but not strong enough for `B1_QUALIFIED`
- `NEGATIVE_CONFIRMED` — materially negative evidence against baseline qualification

### 7.8 Promotion logic

- If any hard gate fails: `B_FAIL`
- If all hard gates pass and soft evidence is `ACCEPTABLE`: `B1_QUALIFIED`
- If all hard gates pass and soft evidence is `UNDERRESOLVED`: `B0_INCUMBENT`
- If all hard gates pass but soft evidence is `NEGATIVE_CONFIRMED`: `B_FAIL`

Examples of `NEGATIVE_CONFIRMED` include:
- holdout and internal reserve both non-viable under the declared harsh-cost regime,
- WFO is negative-confirmed by the declared protocol rather than merely low-power,
- source-parity succeeds but the candidate violates its own frozen acceptance targets on the active qualification replay,
- hidden post-holdout redesign or silent recalibration is detected.

### 7.8A Minimum floor for `B2_CLEAN_CONFIRMED`

`B2_CLEAN_CONFIRMED` is impossible until appended post-freeze data exists and the following minimum evidence floor is met:

- at least `180` calendar days of appended data after `freeze_cutoff_utc`, and
- at least one completed appended evaluation block under A05 cadence, and
- non-zero executed exposure or at least one completed round trip in the appended block.

Below this floor, the baseline remains at `B1_QUALIFIED` (or `B0_INCUMBENT`) with updated durability status only.

---

## 8. x40 directory layout

```text
research/x40/
├── README.md
├── PLAN.md
├── SESSION_GUIDE.md
├── BASELINE_QUALIFICATION_CONSTITUTION_V1.yaml
├── manifest.json
├── baselines/
│   ├── OH0_D1_TREND40/
│   │   ├── source_reference.md
│   │   ├── frozen_spec.md
│   │   ├── frozen_spec.json
│   │   ├── qualification/
│   │   └── forward_evaluation_ledger.csv
│   ├── PF0_E5_EMA21D1/
│   │   ├── source_reference.md
│   │   ├── frozen_spec.md
│   │   ├── frozen_spec.json
│   │   ├── qualification/
│   │   └── forward_evaluation_ledger.csv
│   └── shadow/
│       └── OH1_D1RET60_H4TRENDQ84_HYST/
├── studies/
│   ├── A00_source_parity.md
│   ├── A01_temporal_decay.md
│   ├── A02_alpha_half_life.md
│   ├── A03_capacity_crowding.md
│   ├── A04_entry_exit_attribution.md
│   ├── A05_canary_drift.md
│   ├── A06_bounded_requalification.md
│   └── A07_league_pivot_gate.md
├── shared/
│   ├── loaders/
│   ├── replay/
│   ├── metrics/
│   ├── bootstrap/
│   ├── wfo/
│   ├── capacity/
│   ├── canary/
│   └── reporting/
├── experiments/
├── results/
└── output/
```

### 8.1 Write boundaries

x40 MUST follow the same spirit as x37:
- `shared/` contains reusable infrastructure only,
- baseline definitions are frozen by version,
- study specs are read-only inputs for a single run,
- result folders are append-only after a successful run.

---

## 9. Baseline manifest schema

Every official baseline MUST have a `baseline_manifest.json` with at least:

```json
{
  "baseline_id": "OH0_D1_TREND40",
  "league_id": "OHLCV_ONLY",
  "source_of_truth": "research/x37/resource/gen1/v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md",
  "source_snapshot_id": "<SOURCE_SNAPSHOT_ID_FROM_SOURCE_PACK>",
  "source_window_profile_id": "<SOURCE_WINDOW_PROFILE_ID_FROM_SOURCE_PACK>",
  "qualification_snapshot_id": "<ACTIVE_X40_SNAPSHOT_ID>",
  "qualification_window_profile_id": "GEN4_HIST_SEED_V1",
  "object_type": "baseline",
  "baseline_level": "B1_QUALIFIED",
  "durability_status": "WATCH",
  "constitution_version": "BQC_v1",
  "freeze_cutoff_utc": "<ACTIVE_X40_SNAPSHOT_END_UTC>",
  "cost_model_id": "canonical_20bps_rt",
  "stress_cost_model_ids": ["harsh_50bps_rt", "extreme_75bps_rt", "extreme_100bps_rt"],
  "execution_clock": "native_d1_next_open",
  "live_start_utc": "2020-01-01T00:00:00Z",
  "physical_input_schema_id": "canonical_13col_btcusdt_native",
  "physical_input_fields_present": [
    "symbol",
    "interval",
    "open_time",
    "close_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "num_trades",
    "taker_buy_base_vol",
    "taker_buy_quote_vol"
  ],
  "data_surface_used_by_logic": ["close"],
  "qualification_metric_domain_id": "daily_utc_common_domain",
  "deployment_notional_reference_quote": 100000,
  "notes": "OHLCV_ONLY is defined by fields consumed by logic, not by every extra column physically present in the canonical raw file."
}
```

The JSON above is a **schema example**, not an authoritative literal manifest. Placeholder IDs such as snapshot names and cost-model labels MUST be replaced by the exact IDs used by the actual run.

For `OHLCV_ONLY`, `data_surface_used_by_logic` MUST be declared explicitly. For `PUBLIC_FLOW`, the same manifest MUST declare both the physical schema and the public-flow fields actually consumed by logic. Every active baseline manifest MUST also declare `deployment_notional_reference_quote`, because A03 uses it as the minimum practical notional threshold.


## 9A. Study A00 — Source parity replay

### 9A.1 Purpose
Confirm that a ported baseline has been reimplemented faithfully enough to reproduce the authoritative source artifacts **before** any active x40 qualification verdict is issued.

### 9A.2 Scope
A00 is mandatory for every ported incumbent or ported challenger. It is not optional diagnostic work.

### 9A.3 Inputs
- `source_reference.md`
- authoritative source artifacts
- declared source snapshot and source window profile
- frozen x40 replay implementation for the same baseline

### 9A.4 Required checks
A00 MUST verify at minimum:

- input schema and raw-row counts expected by the source pack
- timestamp ordering and bar-alignment semantics
- exact signal-state transitions
- exact entry / exit timestamps
- integer counts such as completed trades, bars processed, transition counts
- summary metrics in the source metric domain
- return series parity if the source series is available

### 9A.5 Outputs
- `a00_source_pack_checklist.md`
- `source_parity_summary.json`
- `replay_parity.json`
- `a00_parity_diff_report.md`

### 9A.6 Decision rule
- If A00 fails, x40 MUST stop and issue `B_FAIL` for that port attempt.
- If A00 passes, x40 may proceed to `X40_QUALIFICATION_REPLAY`.
- A00 pass does **not** imply `B1_QUALIFIED`; it only unlocks qualification.

---

## 10. Study A01 — Temporal decay audit

### 10.1 Purpose
Measure whether the baseline’s alpha is weakening over time.

### 10.2 Inputs
- frozen baseline spec
- canonical replay engine for that baseline
- full historical return series and trade list

### 10.3 Required views
A01 MUST compute both:

1. **Fixed era splits**
2. **Rolling windows**

### 10.4 Default era splits
Use the strategy’s actual live-trade domain.

For current BTC spot baselines, default fixed eras are:

- `ERA_1_EARLY = 2020-01-01 .. 2021-12-31`
- `ERA_2_MID = 2022-01-01 .. 2023-12-31`
- `ERA_3_RECENT = 2024-01-01 .. snapshot_end`

If a baseline began later, eras must be shifted accordingly.

Unless a baseline-specific source pack declares otherwise, the default `reference_era_id` for A02 / A03 / A05 comparisons is the earliest fixed era with at least one completed round trip; if `ERA_1_EARLY` has zero completed trades, use the next earliest era with non-zero completed trades.

### 10.5 Rolling windows
Default rolling audit:
- window length: 18 months
- step: 3 months
- metrics computed on each window independently

### 10.6 Metrics
A01 MUST compute at minimum:

- Sharpe
- CAGR
- Max drawdown
- Calmar
- exposure
- trade count
- completed round trips
- expectancy per completed trade
- win rate
- average holding bars
- median holding bars
- average winner
- average loser
- max adverse excursion (MAE)
- max favorable excursion (MFE)

### 10.7 Decay diagnostics
A01 MUST also compute:

- linear trend of rolling Sharpe over time
- bootstrap CI for recent-vs-early delta in Sharpe and expectancy
- ratio `recent_sharpe / early_sharpe`
- ratio `recent_expectancy / early_expectancy`

For A01, “significantly negative” means the slope estimate of rolling Sharpe over window midpoints is negative and its 95% bootstrap CI excludes zero.

If `early_sharpe` or `early_expectancy` is numerically zero (absolute value < `1e-12`), the corresponding ratio is treated as undefined; A01 must then rely on signed recent-level metrics and delta diagnostics rather than dividing by a near-zero denominator.

### 10.8 A01 decay band (input to final durability aggregation)

A01 does **not** directly issue the final `durability_status`. It issues an intermediate `a01_decay_band` used later by the durability aggregation policy.

#### `DURABLE`
All conditions hold:
- recent-era Sharpe > 0
- recent-era expectancy > 0
- rolling-Sharpe slope not significantly negative
- recent/early Sharpe ratio >= 0.60
- recent/early expectancy ratio >= 0.60

#### `WATCH`
Any one of:
- recent/early Sharpe ratio in `[0.40, 0.60)`
- recent/early expectancy ratio in `[0.40, 0.60)`
- negative rolling slope but CI overlaps zero

#### `DECAYING`
Any two of:
- recent-era Sharpe <= 0
- recent-era expectancy <= 0
- recent/early Sharpe ratio < 0.40
- recent/early expectancy ratio < 0.40
- rolling slope significantly negative

#### `BROKEN`
All conditions hold:
- recent-era Sharpe <= 0
- recent-era CAGR <= 0 under harsh cost
- recent-era expectancy <= 0
- and at least two consecutive latest rolling windows are negative-Sharpe

### 10.9 Required outputs
- `a01_era_metrics.csv`
- `a01_rolling_metrics.csv`
- `a01_decay_summary.json`
- `a01_decay_fig_equity_by_era.png`
- `a01_decay_fig_rolling_sharpe.png`

---

## 11. Study A02 — Alpha half-life and horizon compression

### 11.1 Purpose
Measure whether the market is realizing the strategy’s edge faster than before.

### 11.2 Concept
If the strategy still works but its edge is crowded or structurally compressed, the expected return curve after entry may peak earlier and decay faster.

### 11.3 Procedure
For each entry event, compute cumulative forward return from entry open to horizons:

`h in {1, 2, 4, 8, 16, 32}` bars on the native execution clock.

Compute separately for each fixed era and each rolling window:

- mean cumulative return curve,
- median cumulative return curve,
- peak horizon `h*`,
- area under the forward-return curve,
- ratio of 1-4 bar realization to 8-32 bar realization.

### 11.4 Metrics
- `peak_horizon`
- `half_life_ratio = return_at_4bars / return_at_32bars`
- `late_realization_share = (ret_16 + ret_32) / sum_positive_horizons`

If `sum_positive_horizons <= 0`, `late_realization_share` MUST be set to `0` and the run must flag the event as an edge-case observation.

### 11.5 Interpretation
- Earlier `peak_horizon` over time = compression warning
- Lower `late_realization_share` over time = crowding / faster information absorption warning

### 11.6 Compression flags
A02 MUST emit:

- `compression_warning = true` if `peak_horizon` shifts earlier by at least 1 bucket versus the reference era or if `late_realization_share` falls by at least 10% relative.
- `compression_severe = true` if `peak_horizon` shifts earlier by at least 2 buckets and `late_realization_share` falls by at least 25% relative.

### 11.7 Outputs
- `a02_forward_curve_by_era.csv`
- `a02_half_life_summary.json`
- `a02_fig_forward_curve.png`

---

## 12. Study A03 — Capacity and crowding audit

### 12.1 Purpose
Estimate whether the signal is becoming harder to monetize in practice.

### 12.2 Important limitation
Without true order-book / fill data, x40 MUST treat crowding estimates as **proxy diagnostics**, not ground truth. Rising volume, falling volume, or higher slippage proxies alone do **not** prove crowding. Crowding is inferred from **signal-conditioned implementation deterioration**: worsening shortfall, shrinking practical capacity, or faster alpha realization / exhaustion after entry.

### 12.3 Two modes

#### Mode 1 — Proxy-only (required)
Available using OHLCV / public-flow bar data.

#### Mode 2 — Realized execution (optional pre-deploy, mandatory once fills exist)
Activated if actual fill logs or order-book snapshots exist. For any deployed or shadowed baseline with real fills, this mode becomes mandatory for subsequent durability reviews.

### 12.4 Proxy-only measurements

Definitions:
- `decision_bar` = the native bar whose close produces the signal.
- `execution_bar` = the next native bar where the position change becomes effective.

For each entry and exit, proxy measurements MUST be aligned to the **execution bar**, not the decision bar:

- execution-bar quote volume
- next-bar quote volume
- signal-conditioned close-to-open gap from `decision_bar.close` to `execution_bar.open`
- first-bar adverse excursion after entry
- first 4-bar adverse excursion after entry
- participation proxy for scenario notional ladder

When a baseline is native D1, “execution bar quote volume” means the D1 bar that opens with the new position state. When a baseline is native H4, it means the H4 bar that opens with the new state.

### 12.5 Scenario notional ladder
At minimum:
- 10k
- 50k
- 100k
- 500k
- 1m
- 5m quote notional

### 12.6 Participation proxy
For notional `N` and bar quote volume `QV`:

`participation = N / QV`

Compute on:
- execution bar,
- next bar,
- min(execution bar, next bar)

If any required `QV <= 0`, participation for that observation is undefined; the row must be logged as a data anomaly and excluded from capacity quantile summaries rather than imputed.

### 12.7 Capacity tables
For each baseline and era, report:

- P10 / P25 / median / P75 of `quote_volume` on execution bars
- notional capacity at participation caps:
  - 0.01%
  - 0.05%
  - 0.10%
  - 0.25%
  - 0.50%

### 12.8 Cost-stress sweep
Every baseline MUST be replayed at:
- canonical cost
- 35 bps RT
- 50 bps RT
- 75 bps RT
- 100 bps RT

### 12.9 Crowding diagnostics
A03 MUST flag crowding risk if any of the following occur in recent eras:

- expected return is highly front-loaded while adverse excursion rises,
- recent performance collapses under modest cost stress (35–50 bps RT),
- execution-bar quote-volume distribution shifts downward by at least 25% at the median versus the reference era,
- capacity at 0.05% participation falls below `deployment_notional_reference_quote`.

A03 MUST emit both:
- `crowding_warning`
- `crowding_severe`

`crowding_warning = true` if at least one crowding-risk condition holds.
`crowding_severe = true` if at least two crowding-risk conditions hold simultaneously.

### 12.10 Outputs
- `a03_capacity_curve.csv`
- `a03_cost_sensitivity.csv`
- `a03_entry_liquidity_summary.csv`
- `a03_crowding_summary.json`
- `a03_fig_cost_sweep.png`
- `a03_fig_entry_quote_volume.png`

---

## 13. Study A04 — Entry vs exit attribution

### 13.1 Purpose
Determine whether remaining value is more likely to come from entry innovation or exit innovation.

### 13.2 Motivation
If entry residuals are exhausted but exit behavior remains loose, future discovery effort should shift toward exit overlays, path-quality rules, and de-risking logic.

### 13.3 Procedure
For the active baseline:

1. **Entry-side characterization**
   - measure predictive content of candidate residual features at entry for fixed forward horizons.
2. **Exit-side characterization**
   - measure whether candidate path-quality / rangepos / maturity / anti-vol features improve realized trade quality when applied during open positions.
3. **Counterfactual decomposition**
   - keep entry fixed, vary exit
   - keep exit fixed, vary entry

### 13.4 Outputs
- `a04_entry_feature_summary.csv`
- `a04_exit_feature_summary.csv`
- `a04_counterfactual_decomposition.csv`
- `a04_directional_research_advice.json`

### 13.5 Decision rule
If entry-side residuals are repeatedly null while exit-side overlays improve trade quality, the next discovery sprint SHOULD prioritize exit research.

---

## 14. Study A05 — Canary and drift detection

### 14.1 Purpose
Detect live or appended-data deterioration without allowing silent self-retuning.

### 14.2 Trigger cadence
Run on every appended evaluation block. Default cadence:
- monthly if bar frequency <= 4h,
- quarterly for D1-only baselines.

If no appended evaluation block exists yet, A05 MUST emit `a05_canary_state = NOT_RUN` and the final durability aggregation MUST treat A05 as neutral.

### 14.3 Canary metrics
At minimum:
- rolling expectancy over last 12 completed trades
- rolling Sharpe over last 6 months
- hit-rate delta vs baseline historical median
- MAE worsening vs historical median
- half-life compression change vs historical reference

### 14.4 Trigger rules

Allowed A05 states are:
- `NOT_RUN`
- `OK`
- `TRIGGERED`

If an appended block exists but fewer than 12 completed trades are available, rolling-expectancy diagnostics MUST use all available completed trades and flag the block as low-power.

A canary is `TRIGGERED` if any two are true:

- rolling expectancy < 0
- rolling Sharpe < 0
- MAE has worsened by >25% vs reference era
- half-life peak horizon is earlier by >= 2 buckets and `late_realization_share` has fallen by >= 25% relative vs the reference era

### 14.5 Outputs
- `a05_canary_state.json`
- `a05_canary_history.csv`
- `a05_trigger_report.md`

### 14.6 Final durability aggregation policy

The final `durability_status` is assigned **after** A01, A02, A03, and A05 are all available. No single study except an explicit `B_FAIL` may unilaterally set the final baseline durability state.

Aggregation precedence:

1. `BROKEN` if any of the following hold:
   - baseline level is `B_FAIL`,
   - `a01_decay_band = BROKEN`,
   - `A05` is `TRIGGERED` in two consecutive appended evaluation blocks,
   - `a01_decay_band = DECAYING` and `crowding_severe = true`.

2. `DECAYING` if any of the following hold:
   - `a01_decay_band = DECAYING`,
   - `compression_severe = true` and `crowding_severe = true`,
   - `A05` is `TRIGGERED` once and `a01_decay_band` is at least `WATCH`.

3. `WATCH` if any of the following hold:
   - `a01_decay_band = WATCH`,
   - `compression_warning = true`,
   - `crowding_warning = true`,
   - `A05` is `TRIGGERED` transiently but not enough for `DECAYING`.

4. `DURABLE` otherwise.

`durability_summary.json` MUST record both the component signals (`a01_decay_band`, `compression_warning`, `compression_severe`, `crowding_warning`, `crowding_severe`, `a05_canary_state`) and the final aggregated `durability_status`. If `a05_canary_state = NOT_RUN`, aggregation proceeds using A01/A02/A03 only.

---

## 15. Study A06 — Bounded requalification and recalibration path

### 15.1 Purpose
Define what happens after decay is detected.

### 15.2 Core rule
x40 MUST **not** allow unconstrained live self-retuning.

### 15.3 Allowed responses
In order of escalation:

1. **No action**  
   if canary warning is transient.
2. **WATCH mode**  
   continue trading / shadowing with explicit alert.
3. **Profile switch**  
   only if the alternative profile was pre-qualified **before** the trigger and belongs to the same league.
4. **Offline requalification session**  
   launch new baseline or challenger session under frozen appended-data protocol.
5. **League pivot recommendation**  
   if repeated decay and crowding persist.

### 15.4 Forbidden actions
- re-fit live parameters continuously,
- change thresholds silently,
- mix appended-data diagnosis with historical redesign inside the same verdict,
- rescue a broken baseline by post-hoc rule insertion without opening a new qualification session.

### 15.5 Outputs
- `a06_requalification_decision.json`
- `a06_trigger_to_action_log.csv`

---

## 16. Study A07 — League pivot gate

### 16.1 Purpose
Decide whether continued search in the current data league is still rational.

### 16.2 Pivot logic
The program SHOULD recommend a pivot away from the current league if:

- the official baseline is `DECAYING` or `BROKEN`,
- crowding stress is severe,
- residual discovery has repeatedly failed to add incremental value,
- and a richer-data league is available.

### 16.3 Minimum league-pivot outputs
- `a07_pivot_summary.json`
- `a07_go_no_go.md`

### 16.4 Example decisions

#### Continue same league
If:
- `OH0_D1_TREND40` remains `DURABLE` or `WATCH`, and
- recent residual challengers still show incremental value.

#### Continue public-flow but not OHLCV-only
If:
- `OH0` degrades materially,
- `PF0` remains viable.

#### Pivot to richer data
If:
- `OH0` and `PF0` both show sustained decay under recent windows and cost stress,
- and recent residual challenger yield is poor.

---

## 17. x39 integration rules

### 17.1 x39 remains ideation-first
x39 may continue to run fast experiments, but authoritative decisions must not be issued from simplified replay.

### 17.2 Mandatory x39 -> x40 promotion package
Any x39 experiment that appears promising MUST emit a package containing:

- `concept_card.md`
- `feature_family.md`
- exact formula(s)
- neighborhood robustness grid
- null / falsification summary
- simplified replay delta vs active baseline
- recommendation: `entry`, `exit`, `filter`, `replace`, or `characterization`

### 17.3 Promotion gate
No x39 result may become part of an official baseline unless x40 replays it under the canonical baseline engine and the relevant league constitution.

### 17.4 Residual sprint launch condition
A new x39 residual sprint SHOULD start only if at least one active baseline in the target league is:

- `B1_QUALIFIED` or higher, and
- not `BROKEN`.

### 17.5 Residual research focus guidance
- If A04 says entry residuals are weak and exit residuals are promising, x39 SHOULD prioritize exit overlays.
- If A03 says crowding dominates, x39 SHOULD stop micro-optimizing public-data entry filters and instead prepare league-pivot proposals.

---

## 18. x37 integration rules

### 18.1 New baseline candidacy
Any brand-new baseline family that is not just an overlay SHOULD originate from x37-style blank-slate discovery, not from x39-only tinkering.

### 18.2 Required replication
A brand-new baseline family should not become official solely because one search session found it. At least one of the following must be true:

- replicated mechanism across >= 2 blank-slate sessions, or
- overwhelmingly superior same-snapshot evidence with broad plateau and strong simplicity advantage.

### 18.3 Plateau rule
If Phase 4 shows only sharp spikes with no broad plateau, the candidate should not be elevated to baseline candidacy.

---

## 19. x38 downstream integration rules

### 19.1 x38 consumes survivors, not raw exploration
Only the following should be routed downstream into x38 governance/spec topics:

- baseline specs that reached `B1_QUALIFIED` or higher,
- challenger specs that survived x40 qualification,
- bounded recalibration / pivot policies already operationalized in x40.

### 19.2 Current x38 dependency implication
Because execution/resilience and bounded recalibration remain open debate topics, x40 is allowed to operate as an interim operational layer **provided it is explicit, frozen, and versioned**.

### 19.3 Reconciliation later
When x38 topic 014 / 016 / 017 close, x40 policies may be reconciled into x38, but x40 must not wait for that closure to become operational.

---

## 20. File-level specs to create first

The first implementation wave MUST create these files:

1. `research/x40/README.md`
2. `research/x40/PLAN.md`
3. `research/x40/SESSION_GUIDE.md`
4. `research/x40/BASELINE_QUALIFICATION_CONSTITUTION_V1.yaml`
5. `research/x40/baselines/OH0_D1_TREND40/source_reference.md`
6. `research/x40/baselines/OH0_D1_TREND40/frozen_spec.md`
7. `research/x40/baselines/PF0_E5_EMA21D1/source_reference.md`
8. `research/x40/baselines/PF0_E5_EMA21D1/frozen_spec.md`
9. `research/x40/studies/A00_source_parity.md`
10. `research/x40/studies/A01_temporal_decay.md`
11. `research/x40/studies/A02_alpha_half_life.md`
12. `research/x40/studies/A03_capacity_crowding.md`
13. `research/x40/studies/A04_entry_exit_attribution.md`
14. `research/x40/studies/A05_canary_drift.md`
15. `research/x40/studies/A06_bounded_requalification.md`
16. `research/x40/studies/A07_league_pivot_gate.md`

---

## 21. Implementation order

### Phase M0 — Scaffold
- create x40 tree
- write constitution
- write manifest schema
- write `A00_source_parity.md`
- wire canonical loaders and baseline replay wrappers

### Phase M1 — Exact incumbent replay
- finalize `source_reference.md` for `OH0_D1_TREND40`
- finalize `source_reference.md` for `PF0_E5_EMA21D1`
- run `SOURCE_PARITY_REPLAY` for `OH0_D1_TREND40`
- run `SOURCE_PARITY_REPLAY` for `PF0_E5_EMA21D1`
- emit parity artifacts separate from active-snapshot qualification artifacts

### Phase M2 — Qualification pass
- run BQC-v1 on both baselines
- assign `B0/B1`
- create forward ledgers

### Phase M3 — Durability suite
- run A01/A02/A03 on both baselines
- run A05 aggregation inputs where appended blocks exist
- assign final `DURABLE/WATCH/DECAYING/BROKEN` via the aggregation policy

### Phase M4 — Residual direction choice
- run A04
- decide whether next x39 sprint focuses on entry, exit, or league pivot

### Phase M5 — Canary activation
- implement A05 and A06
- establish monthly/quarterly appended-data process

### Phase M6 — League pivot or continuation
- run A07
- decide whether to keep investing in OHLCV_ONLY / PUBLIC_FLOW or move to richer data

---

## 22. Immediate operational recommendations

### 22.1 What to do first
1. Implement `OH0_D1_TREND40` replay exactly.
2. Build explicit source packs for `OH0_D1_TREND40` and `PF0_E5_EMA21D1`.
3. Port `PF0_E5_EMA21D1` into x40 as a separate league baseline.
4. Run A00/A01/A02/A03 on both.
5. Do **not** open a new x39 residual sprint until the two baseline manifests, verdicts, forward ledgers, and durability summaries exist.

### 22.2 What not to do
- do not treat E5 as OHLCV-only,
- do not let x39 simplified replay issue final baseline verdicts,
- do not begin self-adaptive live tuning before drift detection is operational,
- do not compare overlay results against a baseline from another league,
- do not wait for all x38 debates to finish before making x40 operational.

---

## 23. Minimal acceptance criteria for initial rollout

This spec is considered implemented only if all are true:

1. `OH0_D1_TREND40` source-parity replay is reproducible from the declared source snapshot and artifacts.
2. `PF0_E5_EMA21D1` source-parity replay is reproducible from its declared inputs and source artifacts.
3. Both also have active-snapshot qualification replays, manifests, verdicts, and forward evaluation ledgers.
4. A00/A01/A02/A03 outputs exist for both.
5. At least one durability verdict is machine-generated for each baseline through the aggregation policy.
6. `forward_evaluation_ledger.csv` exists with the declared schema for each active baseline.
7. x39 promotion package format exists and is enforced for new challengers.
8. x40 can issue one of:
   - continue same-league residual search,
   - shift to exit-focused research,
   - recommend richer-data pivot.

---

## 24. Final interpretation rule

The purpose of x40 is **not** to prove that a baseline is eternally “the best.”

The purpose of x40 is to make the following statement true and auditable:

> “At this moment, under this league, under this constitution, this is the cleanest and most durable baseline we have, and we know whether it is stable, decaying, crowded, or ready to be challenged.”

That is the foundation strong enough to make residual search meaningful.

---

## Appendix R — Source files this spec intentionally builds on

- `research/x37/README.md`
- `research/x37/x37_RULES.md`
- `research/x37/resource/gen4/within_report/d0/D0_report.md`
- `research/x37/resource/gen1/v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md`
- `research/x39/PLAN.md`
- `research/x39/SESSION_GUIDE.md`
- `research/x39/specs/exp12_rangepos_exit.md`
- `research/x39/specs/exp30_and_gate_walk_forward.md`
- `research/x38/PLAN.md`
- `research/x38/debate/debate-index.md`
- `docs/algorithm/VTREND_BLUEPRINT.md`
- `docs/validation/decision_policy.md`
