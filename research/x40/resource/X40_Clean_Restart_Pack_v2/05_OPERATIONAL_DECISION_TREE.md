# Operational Decision Tree

## 1. Purpose

This file converts x40 evidence into one concrete next action.

It is deliberately opinionated.  
The point is to stop endless discussion after the first-cycle audit.

---

## 2. Inputs

The decision tree consumes exactly these inputs:

- `OH0` qualification state
- `OH0` durability state
- `PF0` qualification state
- `PF0` durability state
- current tracked challengers and their adjudication outcome
- `A05` entry-vs-exit attribution
- current existence or non-existence of a richer-data league
- the fact that all decision inputs have been normalized to `CP_PRIMARY_50_DAILYUTC`

---

## 3. Core rules

### Rule 1 — tracked challenger precedence
If a **formal tracked challenger in a league remains unadjudicated**, that adjudication outranks generic residual exploration in that same league.

### Rule 2 — no mixed-profile decision inputs
This tree may consume source-native tables for background reading, but it may only consume **standardized x40 evidence** for actual branch selection.

That means:
- one metric domain,
- one comparison profile,
- one execution assumption set.

---

## 4. Decision tree

### Case A — both `OH0` and `PF0` are `DURABLE`, no tracked challenger pending
#### Primary next action
`SAME_LEAGUE_RESIDUAL`

#### Secondary next action
If `A05` says `EXIT_EDGE`, set secondary to `EXIT_FOCUSED_RESEARCH`.

#### Interpretation
Public-data leagues are still healthy. Continue invention work, but keep it residual-first.

---

### Case B — both `OH0` and `PF0` are `DURABLE`, but a tracked challenger exists
#### Primary next action
`ADJUDICATE_TRACKED_CHALLENGER`

#### Interpretation
Do not open another generic sprint until the active challenger is resolved.

---

### Case C — `OH0` is `DURABLE`, `PF0` is `WATCH` or `DECAYING`
#### Primary next action
`ADJUDICATE_TRACKED_CHALLENGER` if any public-flow challenger exists,
otherwise `EXIT_FOCUSED_RESEARCH`.

#### Interpretation
The public-flow layer may be crowding/decaying before the control OHLCV layer.  
Focus on implementation damage, exit quality, and crowding mitigation before searching for new entry magic.

---

### Case D — `OH0` is `WATCH` or `DECAYING`, `PF0` is `DURABLE`
#### Primary next action
`SAME_LEAGUE_RESIDUAL` in `PUBLIC_FLOW`

#### Secondary next action
Keep `OH0` as control and continue monitoring.

#### Interpretation
The richer public-flow layer still adds value beyond pure OHLCV.

---

### Case E — both `OH0` and `PF0` are `WATCH`
#### Primary next action
`HOLD_AND_ACCUMULATE_FORWARD_DATA`

#### Secondary next action
If a tracked challenger exists, adjudicate it next.

#### Interpretation
Evidence suggests stress but not yet enough to justify a hard pivot or blank-slate reset.

---

### Case F — one baseline is `BROKEN`, the other is merely `WATCH` or `DECAYING`
#### Primary next action
If the broken baseline has a tracked challenger, adjudicate that challenger first.  
Otherwise `OPEN_X37_BLANK_SLATE` inside that league.

#### Interpretation
The league needs a structural challenge, not another tiny patch.

---

### Case G — both `OH0` and `PF0` are `DECAYING` or `BROKEN`
#### Primary next action
`PIVOT_RICHER_DATA`

#### Secondary next action
`OPEN_X37_BLANK_SLATE`

#### Interpretation
Publicly commoditized layers are no longer enough.  
Stop polishing the same surface.

---

### Case H — a tracked challenger is adjudicated as worthy of promotion
#### Primary next action
`ADJUDICATE_TRACKED_CHALLENGER` completed with outcome:
`PROMOTE_TO_BASELINE_QUALIFICATION`

#### Follow-on action
Immediately rerun `A00` and `A01` for that challenger as a candidate baseline version.

---

## 5. Exit-first rule

By default, x40 should bias toward **exit-focused research** only when all three conditions hold:

1. `A05` says remaining edge is mostly exit-side or not separable at entry,
2. there is no pending tracked entry challenger in the same league,
3. baseline durability does not demand a league pivot instead.

Without these conditions, "always exit-first" is too rigid.

---

## 6. When to open x37

`OPEN_X37_BLANK_SLATE` is appropriate only when at least one of these holds:

1. active baseline is `BROKEN`,
2. two consecutive residual sprints fail to produce a tracked challenger,
3. x40 suspects the active baseline family is a local optimum trap,
4. a new data league has just been bootstrapped and needs its first champion.

---

## 7. When to pivot to richer data

`PIVOT_RICHER_DATA` is appropriate when at least two of these are true:

1. both current public-data baselines are `DECAYING` or worse;
2. `A04` shows severe crowding / cost fragility;
3. no surviving challengers remain in current leagues;
4. recent residual work produces rediscoveries rather than new concept families;
5. canary drift keeps firing despite bounded requalification.

---

## 8. Decision output contract

Every decision run must emit:

- one `primary_next_action`,
- optional `secondary_next_action`,
- one `reasoning_summary`,
- one `evidence_table`,
- one `comparison_profile_id`.

No free-text-only decision is allowed.

---

## 9. Allowed primary next actions

Exactly one of:

- `ADJUDICATE_TRACKED_CHALLENGER`
- `SAME_LEAGUE_RESIDUAL`
- `EXIT_FOCUSED_RESEARCH`
- `OPEN_X37_BLANK_SLATE`
- `PIVOT_RICHER_DATA`
- `HOLD_AND_ACCUMULATE_FORWARD_DATA`

---

## 10. Anti-patterns

Invalid decision behavior includes:

1. "run a few more experiments first" when a tracked challenger is already pending;
2. "probably decay" without `A02/A03/A04/A07` outputs;
3. "pivot to richer data" just because new data sounds exciting;
4. "continue residual search" when both active baselines are already broken;
5. mixing `20 bps` and `50 bps` evidence in one headline branch decision.
