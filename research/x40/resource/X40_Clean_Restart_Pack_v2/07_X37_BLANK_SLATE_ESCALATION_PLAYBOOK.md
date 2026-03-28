# X37 Blank-Slate Escalation Playbook

## 1. Purpose

This playbook governs when x40 should escalate to x37 and how that escalation must be framed.

x37 is expensive.  
It should be used for **structural challenge**, not for patching.

---

## 2. When to escalate to x37

Open an x37 session only when at least one of these is true:

1. active baseline is `BROKEN`,
2. two consecutive x39 residual sprints fail to produce a serious tracked challenger,
3. x40 believes the current baseline family is a local optimum trap,
4. a new league has been bootstrapped and needs its first champion,
5. human review decides the current baseline family is no longer worth incremental patching.

---

## 3. When NOT to escalate

Do not open x37 when:

- a tracked challenger is still awaiting `A06`,
- baseline parity is not even established,
- durability is merely `WATCH`,
- or the real issue is implementation/crowding stress, not discovery.

---

## 4. Pre-escalation checklist

Before opening x37, x40 must produce:

- current active baseline manifest,
- current durability report,
- challenger registry snapshot,
- clear escalation reason,
- league definition,
- and banned leakage list.

---

## 5. Leakage boundary for x37

x37 is blank-slate discovery.  
That means:

### Allowed into Phases 1–4
- admitted raw data,
- methodology rules,
- league constitution,
- complexity budget,
- execution constraints.

### Forbidden in Phases 1–4
- current active winner formulas,
- challenger formulas,
- favorite thresholds,
- conclusions from current same-file residual work.

### Allowed only as late benchmark comparators
- incumbent baselines,
- tracked challengers,
- known production systems.

This preserves the point of a blank-slate challenge.

---

## 6. Minimal x37 charter from x40

Every x40-triggered x37 session must define:

- `session_id`
- `league`
- `reason_for_escalation`
- `admitted_data_surface`
- `hard_constraints`
- `benchmark_embargo_policy`
- `what counts as a useful outcome`

Useful outcomes are:
- champion,
- competitive alternative,
- or honest no-robust-candidate.

---

## 7. Return contract from x37 back to x40

A completed x37 session must return:

- session verdict,
- frozen candidate spec(s),
- benchmark comparison,
- known failure modes,
- and a short mechanism summary.

x40 then decides whether the x37 output becomes:
- a tracked challenger,
- a new baseline candidate,
- or archived evidence.

Before any headline x40 claim is made, the returned candidate must be restated on `CP_PRIMARY_50_DAILYUTC`.

---

## 8. Default x37 outcome mapping

### `SUPERIOR` or equivalent strong champion
Candidate becomes tracked challenger or direct baseline-qualification candidate.

### `COMPETITIVE`
Candidate becomes tracked challenger.

### `NO_ROBUST_IMPROVEMENT`
x40 records this as evidence against that escalation route and updates next-action logic.

### `ABANDONED`
x40 records the reason and prevents immediate reopening of the same dead-end.

---

## 9. Bootstrapping a new league through x37

If `A08` activates `RICHER_DATA`, x37 should usually provide the first champion for that league.

In that case x40 supplies:
- league constitution addendum,
- admitted data schema,
- objective floors,
- and benchmark/control references.

---

## 10. Anti-patterns

Invalid escalation behavior includes:

1. using x37 as a bigger x39,
2. leaking incumbent formulas into early discovery phases,
3. opening repeated blank-slate sessions without absorbing the last session’s verdict,
4. treating x37 output as instantly deployable without x40 qualification.
