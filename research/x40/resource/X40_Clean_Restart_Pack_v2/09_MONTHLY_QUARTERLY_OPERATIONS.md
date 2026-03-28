# Monthly and Quarterly Operations

## 1. Purpose

This manual defines the steady-state operating rhythm after the first x40 cycle is complete.

---

## 2. Monthly operations

Run monthly if new data has appended since the last cycle.

### Monthly tasks
1. append data to forward store,
2. update `forward_evaluation_ledger.csv` for each `B1`/`B2` baseline,
3. run `A07` canary for active baselines,
4. refresh challenger tracking statuses,
5. publish `monthly_monitoring_note.md`.

### Monthly outputs
- updated forward ledger,
- `canary_report.md`,
- `monthly_monitoring_note.md`.

### Monthly objective
Detect drift early without re-running heavy studies.

---

## 3. Quarterly operations

Run quarterly regardless of whether monthly canary is quiet.

### Quarterly tasks
1. rerun `A02` temporal decay,
2. rerun `A03` alpha half-life,
3. rerun `A04` capacity/crowding,
4. rerun `A05` entry-vs-exit attribution if the baseline is active for current research,
5. aggregate durability,
6. update `next_action.md` if state has changed,
7. refresh the standardized control panel on `CP_PRIMARY_50_DAILYUTC`.

### Quarterly outputs
- full durability refresh pack,
- updated `durability_state.json`,
- updated `next_action.md` if needed,
- updated `control_panel_CP_PRIMARY_50_DAILYUTC.md` if needed.

---

## 4. Semiannual operations

Run every 6 months.

### Semiannual tasks
1. revisit tracked challengers in `FORMAL_HOLD`,
2. check expiry rules,
3. decide whether to:
   - keep tracked,
   - request Tier-3 review,
   - archive,
   - or promote to baseline qualification.

---

## 5. Annual operations

Run annually.

### Annual tasks
1. baseline registry audit,
2. artifact completeness audit,
3. check whether any `B1` is now eligible for `B2`,
4. archive expired challengers,
5. review whether a richer-data pivot is now justified,
6. review whether comparison profiles still reflect operational reality.

---

## 6. Event-driven operations

Run immediately outside schedule if any of these occur:

- parity bug discovered,
- baseline hard failure,
- tracked challenger receives major new formal evidence,
- market-structure shock makes current assumptions obsolete,
- data schema changes.

---

## 7. Stable-state rules

Do not rerun heavy operations unnecessarily.

### Allowed monthly default
- canary only,
- forward ledger update,
- challenger status check.

### Not allowed monthly default
- opening new blank-slate session,
- baseline swap,
- league pivot without evidence.

---

## 8. Reporting cadence

Every scheduled cycle must produce one concise report:
- monthly: `monthly_monitoring_note.md`
- quarterly: `quarterly_state_report.md`
- semiannual: `challenger_review_roundup.md`
- annual: `annual_state_audit.md`

Every comparative report must label:
- `comparison_profile_id`,
- metric domain,
- and whether the report is headline or sensitivity-only.

---

## 9. Failure escalation ladder

If the canary fires:

### First occurrence
Mark `WATCH`.

### Repeated or stronger occurrence
Run the quarterly suite early.

### Confirmed deterioration
Move to `DECAYING`.

### Terminal deterioration
Move to `BROKEN` and trigger the main decision tree.

---

## 10. Anti-patterns

Invalid operations include:

1. waiting for quarterly review when monthly canary is already screaming;
2. re-running full studies every few days;
3. forgetting to update the forward ledger;
4. leaving tracked challengers unreviewed for months without an expiry policy;
5. publishing a quarterly comparison table that mixes different cost profiles in the same verdict.
