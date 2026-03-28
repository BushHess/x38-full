# X39 Residual Discovery Playbook

## 1. Purpose

This playbook defines how x39 should be used **after x40 exists**.

x39 is not the authoritative place to declare a new baseline.  
x39 is the place to generate, sharpen, and kill new ideas **around the active baseline**.

Its job is to answer:

> "What does the active baseline still fail to explain, and can a new concept family survive enough punishment to deserve formal challenger status?"

---

## 2. What x39 is allowed to optimize

x39 may optimize:

- visibility into failure episodes,
- quality of concept generation,
- family-level falsification,
- and early-stage evidence quality.

x39 must **not** optimize for:
- "most formulas tried,"
- "most categories covered,"
- or "most impressive same-file full-sample headline."

---

## 3. Residual-first rule

Every x39 sprint must start from one explicit `active_baseline_id`.

Allowed starting points:
- `OH0_D1_TREND40`
- `PF0_E5_EMA21D1`
- a newly qualified richer-data baseline

Every sprint must define one explicit residual question such as:
- missed moves,
- false entries,
- premature exits,
- post-stop continuation,
- path quality deterioration,
- crowding-sensitive fragility.

No x39 sprint may begin with "let's search broadly for anything interesting."

---

## 4. Idea generation sources

A concept may be generated from exactly one or more of these sources:

### G1. Anomaly observation
A visible pattern in bars or trade episodes that the active baseline does not explain.

### G2. Behavior → signature hypothesis
A candidate market behavior thought to leave an observable signature in admitted data.

### G3. Statistical gap hypothesis
A stylized or empirically stable relationship not yet encoded in the baseline.

### G4. Cross-domain analogy
Importing a structure from another domain such as information theory, control, physics, or queueing.

### G5. Residual decomposition
A systematic split of:
- trades won vs lost,
- early vs late trend,
- smooth vs ugly path,
- low- vs high-crowding periods.

Every concept card must declare its generator source(s).

---

## 5. Mandatory sprint workflow

## Step 1 — Define the residual slice
Choose:
- baseline,
- league,
- time span,
- and the exact failure slice.

Examples:
- E5 winners vs losers at entry,
- stop-out then continuation,
- large missed breakouts,
- compression-era vs non-compression-era trades.

## Step 2 — Build episode explorer views
Before any formula work, visualize episodes.

The explorer must support at least:
- bars before entry,
- first N bars after entry,
- exit neighborhood,
- missed-move windows,
- extreme value windows for candidate quantities.

This is where questions are found.

## Step 3 — Write a concept card
No formula search is allowed before a concept card exists.

The concept card must include:
- concept name,
- generator source,
- claim,
- non-claim,
- residual slice,
- why current baseline misses it,
- admissible data surface,
- expected failure modes,
- promotion-stage target.

## Step 4 — Generate a family, not a single formula
At least 3 nearby formalizations must be proposed.

Examples of neighborhood variation:
- different lookbacks,
- location vs ranking normalization,
- additive vs ratio form,
- persistence vs spike versions.

Single-formula lottery is prohibited.

## Step 5 — Falsification before predictive celebration
Before predictive backtests, the family must face:
- synthetic or deliberately broken nulls where the intended mechanism should disappear,
- sign sanity checks,
- monotonicity or counterexample checks,
- semantic admissibility checks.

## Step 6 — Non-predictive validation
Run in this order:
1. stability over time,
2. semantic validity ("does it measure what it says?"),
3. orthogonality versus current baseline components,
4. multi-timeframe behavior,
5. robustness to formalization.

Only after passing these may predictive replay begin.

## Step 7 — Predictive replay
Replay starts only after the family survives the first six steps.

If the family is intended to leave x39 and become a tracked challenger, its paired comparison must be restated on `CP_PRIMARY_50_DAILYUTC` before any headline claim is made.

## Step 8 — Promotion-stage assignment
Assign one:
- `DIAGNOSTIC`
- `FILTER`
- `EXIT_OVERLAY`
- `STANDALONE`

## Step 9 — Decide x39 outcome
Exactly one of:
- `KILL`
- `KEEP_DIAGNOSTIC`
- `PROMOTE_TO_FILTER_TEST`
- `PROMOTE_TO_EXIT_OVERLAY_TEST`
- `PACKAGE_AS_TRACKED_CHALLENGER`

---

## 6. Concept card requirements

Each concept card must explicitly state:

- what phenomenon it claims to capture,
- what it absolutely does **not** claim to capture,
- what data fields are required,
- whether it is league-compatible,
- what existing baseline element it is not redundant with,
- and why it deserves to exist despite the information ceiling.

This last point matters: OHLCV and public-flow are finite information surfaces.

---

## 7. Information ceiling rule

x39 must operate under the assumption that:
- transformation space is infinite,
- information content is not.

Therefore every sprint must include a short section:

### "Why this is not just another view of what we already have"
If that case cannot be made honestly, the sprint should not start.

---

## 8. Promotion ladder rules

### 8.1 `DIAGNOSTIC`
The quantity helps explain episodes but has no trade authority.

### 8.2 `FILTER`
The quantity may block or qualify entries.

### 8.3 `EXIT_OVERLAY`
The quantity may manage exits, de-risking, or maturity decisions.

### 8.4 `STANDALONE`
Only now may the quantity anchor a full alternative system.

Most good ideas will die before standalone.  
That is normal.

---

## 9. Kill battery

Every family must pass a kill battery harsher than current casual research validation.

Required kill battery dimensions:
- semantic admissibility,
- synthetic/null falsification,
- family robustness,
- temporal stability,
- orthogonality versus baseline,
- cost robustness,
- failure-slice usefulness,
- integration-stage fit.

A family can be beautiful and still be killed.

---

## 10. Exit-first bias — but only conditionally

Exit-focused work is favored when:
- x40 `A05` says edge is mainly exit-side or not separable at entry,
- and there is no pending tracked entry challenger.

This is a **conditional policy**, not a dogma.

---

## 11. Stop rules

A residual sprint must stop when any of these occurs:

1. the concept card collapses under semantic review;
2. nearby formalizations disagree wildly;
3. nulls produce similar "wins";
4. orthogonality is fake;
5. the family only works as one fragile formula;
6. the observed effect is too small relative to detection power;
7. x40 decision tree says another branch now outranks this sprint.

---

## 12. When x39 may emit a tracked challenger

Only if all are true:

1. a concept family survives the kill battery,
2. replay improvement is material enough to matter,
3. integration stage is at least `FILTER` or `EXIT_OVERLAY`,
4. the line can be reproduced canonically,
5. the package includes a standardized `CP_PRIMARY_50_DAILYUTC` comparison summary,
6. the package is strong enough to deserve `A06`.

Then x39 emits a **tracked challenger pack** instead of just another result note.

---

## 13. Anti-patterns

x39 must not:

1. screen a giant universe without concept cards;
2. rediscover textbook indicators and present them as invention;
3. use same-file full-sample best point as proof of validity;
4. keep exploring generic entry filters while a formal tracked challenger in that lane is already waiting for adjudication;
5. call a league exhausted just because one family failed;
6. export a challenger using mixed-profile source tables as its headline evidence.
