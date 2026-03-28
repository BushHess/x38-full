# Tracked Challenger and Low-Power Adjudication

## 1. Purpose

This document defines how x40 handles challengers that are:

- too real to ignore,
- not clean enough to auto-promote,
- and too important to leave drifting inside x39 notes.

This is the missing operational lane between:
- x39 research findings,
- formal validation,
- low-power machine HOLDs,
- and baseline-qualification decisions.

---

## 2. Why this lane exists

Three cases must be distinguished:

1. **exploratory ideas** — stay in x39;
2. **formal challengers with enough evidence to matter** — enter x40 tracked-challenger lane;
3. **production-ready deployables** — remain under the main repo validation and deployment process.

Without this lane, x40 would either:
- ignore good low-power challengers,
- or swap baselines too early.

---

## 3. Challenger entry criteria

A candidate may enter x40 as a tracked challenger only if:

1. it has a stable identity (`challenger_id`);
2. its target baseline is explicit;
3. its league is explicit;
4. its promotion stage is explicit;
5. it has a research evidence pack;
6. it has a formal validation pack or equivalent canonical replay pack;
7. it has no unresolved hard-fail issue;
8. it can be restated on `CP_PRIMARY_50_DAILYUTC` for x40 comparison.

---

## 4. Challenger sources

Valid sources:

### 4.1 x39 formal validation
A line from x39 may enter as tracked challenger if:
- simplified exploration produced a promising line,
- canonical reproduction exists,
- formal validation has been run,
- and the result is at least informative enough to matter.

### 4.2 x37 completed session
A completed x37 session may return a champion that challenges the active baseline.

### 4.3 richer-data league bootstrap
A candidate born inside a new league may enter as tracked challenger before that league has a stable incumbent.

---

## 5. Challenger fields

Required fields in `challenger_manifest.yaml`:

- `challenger_id`
- `league`
- `target_baseline_id`
- `source_project`
- `source_artifacts`
- `promotion_stage`
- `research_state`
- `formal_state`
- `x40_route`
- `tier3_route`
- `mechanism_summary`
- `known_failure_modes`
- `recommended_action`
- `expiry_policy`
- `primary_comparison_profile_id`
- `owner`

---

## 6. Challenger states

### 6.1 `TRACKED`
A candidate is important enough to reserve bandwidth for formal adjudication.

### 6.2 `FORMAL_HOLD`
Formal validation exists, no hard reject exists, but machine evidence is insufficient for automatic promotion.

### 6.3 `FORMAL_PROMOTE`
Formal validation has no soft blockers.

### 6.4 `ABANDONED`
The line is no longer active.

---

## 7. Route fields

### 7.1 `x40_route`
This is the x40 operational route chosen at the end of `A06`:
- `KEEP_TRACKED`
- `PROMOTE_TO_BASELINE_QUALIFICATION`
- `ARCHIVE`
- `REQUEST_TIER3_REVIEW`

### 7.2 `tier3_route`
This is **not** an x40 state. It is populated only if a production-scope human deployment review is actually run.

Allowed values:
- `NOT_APPLICABLE`
- `SHADOW`
- `DEPLOY`
- `DEFER`
- `REJECT`

These two fields must never be collapsed into one.

---

## 8. Required evidence pack for `A06`

A tracked challenger cannot enter adjudication without all of these:

1. frozen challenger spec,
2. source and target baseline identifiers,
3. reproduction summary,
4. formal validation summary,
5. cost sensitivity summary,
6. paired comparison note on `CP_PRIMARY_50_DAILYUTC`,
7. mechanism robustness note,
8. known failure modes,
9. proposed research route if not promoted.

---

## 9. `A06` adjudication procedure

### Step 1 — Intake
Verify artifact completeness and league compatibility.

### Step 2 — Formal-state classification
Classify the challenger as:
- `FORMAL_PROMOTE`
- `FORMAL_HOLD`
- `ABANDONED`

### Step 3 — Pair review for low-power cases
If the challenger is `FORMAL_HOLD` but has no hard fail, run a documented pair review.

### Step 4 — Choose `x40_route`
Choose exactly one:
- `KEEP_TRACKED`
- `PROMOTE_TO_BASELINE_QUALIFICATION`
- `ARCHIVE`
- `REQUEST_TIER3_REVIEW`

### Step 5 — Optional Tier-3 route
If and only if a production-scope human deployment review is actually run, populate `tier3_route` with:
- `SHADOW`
- `DEPLOY`
- `DEFER`
- `REJECT`

Otherwise `tier3_route = NOT_APPLICABLE`.

### Step 6 — Registry update
Write:
- `challenger_review.md`
- `challenger_decision.json`
- registry update in the active x40 manifest.

---

## 10. What low-power HOLD means in x40

Low-power HOLD means:

- evidence is **not negative**,
- evidence is **not sufficient for automatic machine promotion**,
- the candidate may still be the best available improvement,
- and the correct next action is **documented adjudication**, not silence.

This is exactly why tracked challengers exist.

---

## 11. Current tracked challenger: `PF1_E5_VC07`

This clean-restart pack initializes one tracked challenger:

### Identity
- `challenger_id`: `PF1_E5_VC07`
- league: `PUBLIC_FLOW`
- target baseline: `PF0_E5_EMA21D1`
- primary comparison profile: `CP_PRIMARY_50_DAILYUTC`

### Mechanism
Volatility compression entry filter on top of E5.

### Preferred threshold
`0.7` is the primary threshold for formal adjudication.

### Sensitivity shadow
`0.6` remains a shadow sensitivity reference, not the default active tracked challenger.

### Why this line is tracked
Because it has crossed the line from "interesting x39 idea" into "formal low-power challenger that must be adjudicated."

---

## 12. Current policy for `PF1_E5_VC07`

1. `PF1` is **not** automatically the new `PUBLIC_FLOW` baseline.
2. `PF1` must pass through `A06`.
3. Until `A06` completes, no new generic `PUBLIC_FLOW` residual sprint may preempt it.
4. If `PF1` is accepted for baseline qualification, x40 updates the branch plan accordingly.
5. If `PF1` is deferred, its expiry condition must be explicit.

---

## 13. Challenger expiry rules

A tracked challenger cannot live forever without decision.

Each challenger must define one expiry rule:

- `AFTER_NEXT_A06`
- `AFTER_180D_FORWARD_DATA`
- `AFTER_NEW_BASELINE_SWAP`
- `AFTER_FAILED_SHADOW`
- `MANUAL_ARCHIVE`

Expired challengers are archived, not silently forgotten.

---

## 14. When a challenger may become a baseline

Promotion path:

1. `TRACKED`
2. `A06` completed
3. `x40_route = PROMOTE_TO_BASELINE_QUALIFICATION`
4. candidate reruns `A00` as a would-be baseline
5. candidate reruns `A01`
6. only then may it become `B1_QUALIFIED`

No shortcut is allowed.

---

## 15. Anti-patterns

Invalid behaviors include:

1. skipping pair review because WFO is underpowered;
2. declaring "best possible in league" after a single challenger success;
3. letting x39 continue generic same-lane exploration while an unadjudicated formal challenger already exists;
4. using the challenger’s existence as proof that the current baseline is wrong;
5. pretending a `FORMAL_HOLD` is the same as a failed candidate;
6. mixing `x40_route` with `tier3_route`.
