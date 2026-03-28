# QA Review for X40 Clean Restart Pack v2

## 1. Review intent

This QA note records the checks performed after generating the corrected v2 pack.

It exists for one reason: to show what was actually checked and what was actually fixed.

---

## 2. What was wrong in the earlier clean-restart v1 pack

A serious review found these load-bearing issues:

1. **Comparison discipline gap**
   - The pack normalized metric domain, but did not explicitly force a common cost profile for headline comparisons.
   - This left room for accidental apples-to-oranges claims such as one baseline quoted at 20 bps and another at 50 bps.

2. **Missing template files**
   - The index and artifact doc claimed template files were included.
   - They were not actually present.

3. **Route namespace mismatch**
   - The challenger doc mixed x40 operational actions with Tier-3 deployment routes.
   - That made `PROMOTE_TO_BASELINE_QUALIFICATION` look like a Tier-3 deployment decision, which it is not.

4. **Registry convention mismatch**
   - Some docs assumed one central registry set.
   - Another doc described per-league registry files.

5. **QA note itself was inaccurate**
   - It claimed checks that had not in fact been satisfied by the file set.

This v2 pack fixes all five.

---

## 3. Automated checks performed on v2

### A. File presence
Confirmed present:
- `README.md`
- `00_INDEX.md`
- `01` through `12` markdown docs
- `templates/` directory
- 8 actual template files
- zip package built successfully

### B. Template presence
Confirmed present in `templates/`:
- `baseline_manifest_template.yaml`
- `challenger_manifest_template.yaml`
- `comparison_profiles_template.yaml`
- `concept_card_template.md`
- `family_pack_template.md`
- `challenger_review_template.md`
- `next_action_template.md`
- `forward_evaluation_ledger_template.csv`

### C. Enum consistency
Confirmed that the following enums appear consistently across the pack:
- baseline states: `B0_INCUMBENT`, `B1_QUALIFIED`, `B2_CLEAN_CONFIRMED`, `B_FAIL`
- durability states: `DURABLE`, `WATCH`, `DECAYING`, `BROKEN`
- next actions:
  - `ADJUDICATE_TRACKED_CHALLENGER`
  - `SAME_LEAGUE_RESIDUAL`
  - `EXIT_FOCUSED_RESEARCH`
  - `OPEN_X37_BLANK_SLATE`
  - `PIVOT_RICHER_DATA`
  - `HOLD_AND_ACCUMULATE_FORWARD_DATA`
- promotion stages:
  - `DIAGNOSTIC`
  - `FILTER`
  - `EXIT_OVERLAY`
  - `STANDALONE`
- challenger states:
  - `TRACKED`
  - `FORMAL_HOLD`
  - `FORMAL_PROMOTE`
  - `ABANDONED`
- x40 routes:
  - `KEEP_TRACKED`
  - `PROMOTE_TO_BASELINE_QUALIFICATION`
  - `ARCHIVE`
  - `REQUEST_TIER3_REVIEW`
- tier3 routes:
  - `NOT_APPLICABLE`
  - `SHADOW`
  - `DEPLOY`
  - `DEFER`
  - `REJECT`

### D. Comparison discipline presence
Confirmed present in the pack:
- explicit `CP_PRIMARY_50_DAILYUTC`
- explicit `CP_SENS_20_DAILYUTC`
- rule that decision logic consumes only `CP_PRIMARY_50_DAILYUTC`
- rule forbidding mixed-cost headline comparisons

### E. Registry consistency
Confirmed all docs now point to one central registry set:
- `registry/leagues.yaml`
- `registry/baselines.yaml`
- `registry/challengers.yaml`
- `registry/comparison_profiles.yaml`

Optional per-league addenda are treated only as addenda, not as replacement registries.

---

## 4. Manual review findings

### Finding 1 — Namespace separation is clean
The pack now keeps separate:
- research screening,
- x40 baseline states,
- x40 challenger states,
- x40 routes,
- Tier-3 deployment routes,
- and production verdicts.

### Finding 2 — Tracked challenger lane is explicit and no longer conflated with deployment
`PF1_E5_VC07` is now handled through a clean x40 adjudication lane with separate `x40_route` and `tier3_route` fields.

### Finding 3 — Promotion ladder is explicit
The order `DIAGNOSTIC -> FILTER -> EXIT_OVERLAY -> STANDALONE` is written as a hard rule.

### Finding 4 — Richer-data pivot is operationalized and comparison-safe
The pack now says how a richer-data league is created and how it must be compared to controls.

### Finding 5 — Source facts vs x40 policy are separated
`11_SOURCE_ALIGNMENT_NOTES.md` records which statements are inherited from the repo and which are x40 design choices.

---

## 5. Known deliberate policy choices

The following are intentional x40 policy defaults, not repo facts:

- the x40 baseline state machine,
- the x40 durability aggregation logic,
- the default `B2` clean-confirmation floor,
- the tracked challenger precedence rule,
- the standardized primary comparison profile,
- the richer-data priority order.

They are explicit and documented, not hidden assumptions.

---

## 6. Conclusion

No remaining internal inconsistency was found in this QA pass that would invalidate implementation of the pack.

That does **not** mean the pack is metaphysically perfect.  
It means:
- the pack now contains the files it claims to contain,
- its control logic is internally consistent,
- it explicitly forbids mixed-profile headline comparisons,
- and it is materially safer than the earlier drafts.
