# X40 Clean Restart System Spec

## 1. Purpose

`x40` is the **operational research control layer** between:

- **x37** blank-slate discovery,
- **x39** residual / feature-invention exploration,
- **production validation** in the main repo,
- and **x38** downstream architecture/governance.

It does **not** search for the globally best algorithm by itself.  
It does **not** replace x37 or x39.  
It does **not** claim clean OOS from the same historical archive.

Its job is to answer, at any point in time:

1. **What is the active baseline in each league?**
2. **Is that baseline still durable, or is it decaying?**
3. **Is there a tracked challenger that deserves adjudication?**
4. **Should research continue inside the same league, escalate to x37, or pivot to richer data?**

---

## 2. Non-goals

`x40` must never become:

- another debate layer,
- a brute-force search engine,
- a live self-retuning runtime,
- a place where same-file results are mislabelled as clean OOS,
- a place where mixed cost regimes are compared as if they were the same,
- or a justification engine for already-favored candidates.

---

## 3. The four-system split

### 3.1 x37 — blank-slate discovery arena
Use x37 when the question is:

> "Starting from admitted raw data and a frozen methodology, what champion emerges from a fresh discovery session?"

x37 owns **session isolation**, **phase gating**, **freeze discipline**, and **blank-slate challenge sessions**.

### 3.2 x39 — residual discovery and invention lab
Use x39 when the question is:

> "Given an active baseline, what residual structure is still unexplained, and can a new concept family survive harsh testing?"

x39 owns **episode exploration**, **concept generation**, **family testing**, and **residual challengers**.

### 3.3 x40 — operational evidence and branch control
Use x40 when the question is:

> "Which baseline is the active reference, how durable is it, what challenger is tracked, and what branch should research take next?"

x40 owns **baseline qualification**, **comparison discipline**, **durability**, **crowding/decay measurement**, **challenger adjudication**, **next-action choice**, and **league pivot control**.

### 3.4 x38 — downstream architecture/governance
Use x38 after a survivor is real enough to deserve architecture, versioning, protocol and governance treatment.

x38 is **downstream** of discovery and qualification, not the place where feature invention starts.

---

## 4. Core design principles

### P1. Baseline qualification protocol comes before baseline worship
The foundation is not "the best baseline ever found."  
The foundation is a **strong, consistent baseline qualification protocol**.

### P2. Residual-first, not universe-first
Do **not** search the whole universe by default.  
Search the **unexplained residual** around the active baseline.

### P3. Feature invention is not feature selection
A valid invention workflow must create new measurable concepts, not just rescan a shelf of known formulas.

### P4. Story generates; data judges
Ideas may come from:
- anomaly observation,
- behavior → signature hypotheses,
- statistical invariants,
- cross-domain analogy.

But survival is decided by:
- falsification,
- robustness,
- incrementality,
- cost stress,
- durability over time.

### P5. Integration ladder is mandatory
Every new idea must move through this order:

1. `DIAGNOSTIC`
2. `FILTER`
3. `EXIT_OVERLAY`
4. `STANDALONE`

Skipping directly to standalone is prohibited.

### P6. League separation is mandatory
There is **no single universal baseline**.

At minimum x40 separates:

- `OHLCV_ONLY`
- `PUBLIC_FLOW`
- `RICHER_DATA`

### P7. Clean OOS only begins after freeze
Historical archive = discovery + internal evaluation only.  
True clean confirmation begins only on **appended data after `freeze_cutoff_utc`**.

### P8. No free-form live adaptation
`x40` permits only **bounded requalification**:
- canary,
- watch mode,
- pre-qualified profile switch,
- offline challenger session,
- league pivot.

It forbids unrestricted runtime self-retuning.

### P9. Low-power HOLD is a first-class case
A strategy can be:
- formally better than baseline in direction,
- still not machine-promotable,
- and still worthy of a tracked challenger workflow.

`x40` must not force these cases into either "promote now" or "discard now."

### P10. Apples-to-apples comparison is mandatory
No headline x40 claim may compare:
- different cost regimes,
- different metric domains,
- different execution assumptions,
- or source-native reports from different systems.

Every headline comparison must declare one explicit **comparison profile**.

---

## 5. Object model

### 5.1 League
A `league` defines:
- admitted data surface,
- baseline family types that are allowed,
- artifact schema,
- and which challengers are comparable.

Valid initial leagues:

- `OHLCV_ONLY`
- `PUBLIC_FLOW`
- `RICHER_DATA`

### 5.2 Baseline
A `baseline` is the active reference system for one league.

A baseline is a **reference model**, not a truth claim.

Required fields:
- `baseline_id`
- `league`
- `source_lineage`
- `system_role`
- `qualification_state`
- `durability_state`
- `freeze_cutoff_utc`
- `primary_comparison_profile_id`
- `manifest_path`

### 5.3 Challenger
A `challenger` is a candidate intended to improve the active baseline inside the same league.

Required fields:
- `challenger_id`
- `league`
- `target_baseline_id`
- `promotion_stage`
- `research_state`
- `formal_state`
- `x40_route`
- `tier3_route`
- `tracking_status`
- `primary_comparison_profile_id`
- `manifest_path`

### 5.4 Concept family
A `concept family` is the smallest unit of invention work that x40 accepts from x39.

A family contains:
- one concept card,
- multiple nearby formalizations,
- falsification plan,
- non-predictive validation plan,
- predictive replay summary,
- integration-stage recommendation.

### 5.5 Study
A `study` is a specific x40 audit or control procedure.

x40 has exactly nine core studies:

- `A00` source parity replay
- `A01` baseline qualification
- `A02` temporal decay audit
- `A03` alpha half-life audit
- `A04` capacity / crowding audit
- `A05` entry-vs-exit attribution
- `A06` formal challenger adjudication
- `A07` canary drift and bounded requalification
- `A08` league pivot bootstrap

---

## 6. Namespace separation

### 6.1 Research screening namespace
Issued upstream by x37/x39-style research:
- `SCREEN_PASS`
- `SCREEN_FAIL`

### 6.2 x40 baseline namespace
Issued by x40:
- `B0_INCUMBENT`
- `B1_QUALIFIED`
- `B2_CLEAN_CONFIRMED`
- `B_FAIL`

### 6.3 x40 durability namespace
Issued by x40:
- `DURABLE`
- `WATCH`
- `DECAYING`
- `BROKEN`

### 6.4 x40 challenger namespace
Issued by x40:
- `TRACKED`
- `FORMAL_HOLD`
- `FORMAL_PROMOTE`
- `ABANDONED`

### 6.5 x40 route namespace
Issued by x40 adjudication:
- `KEEP_TRACKED`
- `PROMOTE_TO_BASELINE_QUALIFICATION`
- `ARCHIVE`
- `REQUEST_TIER3_REVIEW`

### 6.6 Tier-3 deployment route namespace
Issued only if a production-scope human review is actually performed:
- `NOT_APPLICABLE`
- `SHADOW`
- `DEPLOY`
- `DEFER`
- `REJECT`

### 6.7 Production validation namespace
Owned by existing repo machinery, not x40:
- `PROMOTE`
- `HOLD`
- `REJECT`

These namespaces must never be mixed.

---

## 7. Comparison discipline

### 7.1 Source-native parity vs standardized comparison
`A00` is allowed to use source-native reporting conventions in order to prove parity with the upstream source system.

That is **not** the same thing as an x40 headline comparison.

After parity, x40 must restate all baselines and challengers on standardized comparison profiles.

### 7.2 Primary comparison profile
The default primary profile is:

- `comparison_profile_id`: `CP_PRIMARY_50_DAILYUTC`
- round-trip cost: `50 bps`
- metric domain: `daily UTC mark-to-market equity`
- instrument assumption: `spot, long-only, no leverage, no borrow`

This is the only profile allowed in:
- headline baseline tables,
- challenger-vs-baseline tables,
- decision-tree inputs,
- next-action reasoning,
- and cross-league control views.

### 7.3 Optional sensitivity profile
The default sensitivity profile is:

- `comparison_profile_id`: `CP_SENS_20_DAILYUTC`
- round-trip cost: `20 bps`
- metric domain: `daily UTC mark-to-market equity`
- same execution assumptions otherwise.

This profile is diagnostic only unless a future constitution explicitly upgrades it.

### 7.4 Comparison rules
1. Every comparative table must label `comparison_profile_id`.
2. Every comparative table must label metric domain.
3. No table may place a `20 bps` result and a `50 bps` result in the same comparison row without explicit separation.
4. Decision logic must consume `CP_PRIMARY_50_DAILYUTC`, not mixed-profile source tables.
5. If sensitivity is shown, it must appear as a separate appendix or separate columns clearly marked as sensitivity-only.

---

## 8. Initial league registry

### 8.1 `OHLCV_ONLY`
**Purpose**: control league for structure extractable from OHLCV without order-flow-specific fields.

**Initial active baseline**: `OH0_D1_TREND40`

**Why this baseline exists**:
- it is simple,
- native D1,
- one signal,
- no regime gate,
- no cross-timeframe mapping,
- easy to freeze,
- easy to replay,
- reserve-positive in its frozen source run.

### 8.2 `PUBLIC_FLOW`
**Purpose**: public data beyond pure OHLCV but still widely available, such as taker-side flow proxies.

**Initial active baseline**: `PF0_E5_EMA21D1`

**Initial tracked challenger**: `PF1_E5_VC07`

`PF0` is the practical incumbent, but not yet a clean-confirmed truth claim.

`PF1` exists because x39 has already produced a formally validated low-power improvement candidate around E5.  
It must be tracked and adjudicated, not ignored and not auto-promoted.

### 8.3 `RICHER_DATA`
**Purpose**: future league for information not already commoditized at the OHLCV/public-flow layer.

No active baseline exists at boot.  
This league activates only through `A08`.

---

## 9. Initial object definitions

### 9.1 `OH0_D1_TREND40`
- league: `OHLCV_ONLY`
- lineage: x37 gen1 v8 `S_D1_TREND`
- role: control baseline
- signal: `close_t / close_(t-40) - 1 > 0`
- timeframe: native D1
- data used by logic: D1 close only
- primary comparison profile: `CP_PRIMARY_50_DAILYUTC`
- state at x40 bootstrap: `B0_INCUMBENT`

### 9.2 `PF0_E5_EMA21D1`
- league: `PUBLIC_FLOW`
- lineage: VTREND E5
- role: practical incumbent
- timeframe: H4 + mapped D1 regime
- flow field usage: VDO uses taker-buy information
- primary comparison profile: `CP_PRIMARY_50_DAILYUTC`
- state at x40 bootstrap: `B0_INCUMBENT`

### 9.3 `PF1_E5_VC07`
- league: `PUBLIC_FLOW`
- target baseline: `PF0_E5_EMA21D1`
- role: tracked challenger
- mechanism: volatility compression entry gate
- default threshold: `0.7`
- sensitivity shadow reference: `0.6`
- primary comparison profile: `CP_PRIMARY_50_DAILYUTC`
- expected x40 initial state: `TRACKED` then `FORMAL_HOLD`

---

## 10. The nine x40 studies

### 10.1 `A00` — Source parity replay
Goal: prove that the x40 implementation can reproduce the intended source system.

Outputs:
- `parity_report.md`
- `parity_metrics.json`
- `parity_status.json`

Failure here blocks everything downstream.

### 10.2 `A01` — Baseline qualification
Goal: convert a prior incumbent into a qualified x40 baseline with frozen manifest, standardized comparison outputs, and forward ledger.

Outputs:
- `baseline_manifest.yaml`
- `qualification_report.md`
- `qualification_state.json`
- `metrics_CP_PRIMARY_50_DAILYUTC.json`
- `forward_evaluation_ledger.csv`

### 10.3 `A02` — Temporal decay audit
Goal: detect whether alpha is weakening across eras and rolling windows.

### 10.4 `A03` — Alpha half-life audit
Goal: test whether payoff realization is compressing toward earlier bars.

### 10.5 `A04` — Capacity / crowding audit
Goal: detect whether implementation assumptions are becoming less realistic.

### 10.6 `A05` — Entry-vs-exit attribution
Goal: locate where the remaining edge or damage actually sits.

Possible outputs:
- `ENTRY_EDGE`
- `EXIT_EDGE`
- `MIXED`
- `NONE_CLEAR`

### 10.7 `A06` — Formal challenger adjudication
Goal: handle tracked challengers properly, especially low-power HOLD cases.

Outputs:
- `challenger_manifest.yaml`
- `challenger_review.md`
- `challenger_decision.json`
- `pair_metrics_CP_PRIMARY_50_DAILYUTC.json`

### 10.8 `A07` — Canary drift and bounded requalification
Goal: run light forward monitoring after freeze and choose the least dangerous reaction.

### 10.9 `A08` — League pivot bootstrap
Goal: move beyond current public data if current leagues are decaying or exhausted.

---

## 11. Promotion ladder

Every new line must declare its current `promotion_stage`.

### Stage 0 — `DIAGNOSTIC`
The quantity explains bars/episodes but is not yet allowed to gate trades.

### Stage 1 — `FILTER`
The quantity may veto or qualify entries, but not control the full system.

### Stage 2 — `EXIT_OVERLAY`
The quantity may manage exits or de-risking for an existing baseline.

### Stage 3 — `STANDALONE`
The quantity may anchor a full alternative system.

**Rule**: the default path is upward through these four stages.  
Skipping levels requires an explicit written exception justified in the challenger pack.

---

## 12. Durability aggregation logic

Each of `A02`, `A03`, `A04`, and `A07` issues one of:
- `PASS`
- `WATCH`
- `FAIL`

Aggregation:

- **`DURABLE`** = no `FAIL`, at most one `WATCH`
- **`WATCH`** = no `FAIL`, two or more `WATCH`
- **`DECAYING`** = exactly one `FAIL` or severe but non-terminal deterioration
- **`BROKEN`** = two or more `FAIL`, or a terminal negative-confirmation event

A baseline can be `B1_QUALIFIED` yet `DECAYING`.  
Qualification state and durability state are independent.

---

## 13. Next-action outputs

Every completed first cycle must emit exactly one `primary_next_action`:

- `ADJUDICATE_TRACKED_CHALLENGER`
- `SAME_LEAGUE_RESIDUAL`
- `EXIT_FOCUSED_RESEARCH`
- `OPEN_X37_BLANK_SLATE`
- `PIVOT_RICHER_DATA`
- `HOLD_AND_ACCUMULATE_FORWARD_DATA`

It may also emit at most one `secondary_next_action`.

---

## 14. Hard prohibitions

x40 forbids:

1. using same-file evidence to claim clean OOS;
2. auto-swapping baselines because a challenger looks directionally better once;
3. launching a fresh x39 sprint while a tracked formal challenger in the same lane is still unadjudicated;
4. live self-retuning on streaming data;
5. using production verdicts and x40 states as if they were the same thing;
6. mixing different comparison profiles inside one headline claim;
7. declaring a league exhausted from a handful of failed ideas without recording the failure families and rationale.

---

## 15. Minimal success condition for x40

x40 is considered operationally successful when, after implementation, it can do all of the following without ambiguity:

1. qualify `OH0_D1_TREND40`,
2. qualify `PF0_E5_EMA21D1`,
3. ingest and adjudicate `PF1_E5_VC07`,
4. issue durability states for OHLCV-only and public-flow baselines,
5. publish one `next_action.md` based on `CP_PRIMARY_50_DAILYUTC`,
6. and open the correct next branch without debate.

If x40 cannot do that, it is not ready.
