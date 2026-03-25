# PROMPT TO SEND TO THE CURRENT RESEARCH SESSION (V6)

> Before sending this prompt, upload CONTAMINATION_LOG_V2.md to this session. This is the contamination log produced by the V5 session during its handoff (it covers all rounds from the V4 session plus the V5 session's own round). Your own results are already frozen, so uploading it now will not cause contamination. You need it in order to produce an updated version that includes your own round.
>
> Then copy all content below the divider and send it together.

---

## Request: Prepare documents for a possible final same-file convergence audit

This research session is now concluded. The human researcher will decide whether to run one final same-file re-derivation (V7), stop same-file iteration now, or wait for new data. The documents you produce must support any of these decisions. The documents you produce must reflect the scientific limits honestly: on the current file, the reserve window can provide internal evidence only and is not eligible for clean within-file OOS proof.

Use the artifacts already produced in this session as source material where relevant, including the prior prompt, prior contamination log, the completed V6 research outputs/specs, and the current session’s conclusions about convergence, contamination, and governance. Regenerate all four files from scratch so they are internally consistent with each other.

Core principle: **Transfer only meta-knowledge (lessons about methodology and structure), DO NOT transfer data-derived specifics (specific features, specific lookbacks, specific thresholds, specific parameters).** The new session must rediscover everything from first principles.

Another core principle: **Do not treat later same-file iterations as automatically “better” than earlier ones.** The point of V7 is to run a cleaner final same-file convergence audit, not to bias the search toward any prior result.

### I need you to produce 4 deliverables:

---

### Deliverable 1: RESEARCH_PROMPT_V7.md

Rewrite `RESEARCH_PROMPT_V6.md` into version V7 with the following changes:

**A. Preserve what was correct and useful.**
- Keep everything from V6 that worked correctly in the completed V6 run.
- Also keep any valid structural improvements that were already identified while drafting V7 in this session, as long as they do not violate the isolation rules below.

**B. Fix and improve the protocol based on lessons learned from running V6.**
- Every part of V6 that proved missing, ambiguous, misleading, weakly governed, or wasteful must be fixed.
- If the search ladder, screening criteria, evaluation stages, decision gates, tie-break rules, or ordering of steps need adjustment, adjust them.
- Strengthen governance where needed so the protocol is harder to misuse and less likely to drift into same-file prompt overfitting.

**C. Add only genuinely new methodological lessons to the Meta-knowledge section.**
- Add new lessons learned in this session at the principle level only.
- Do not duplicate lessons that were already present in V6.
- If any prior lesson proved misleading, incomplete, or poorly worded, correct or remove it.
- Do not include any lesson that implicitly points toward a particular feature family, lookback region, threshold level, or parameter setting.

**D. Reassess the data split architecture.**
- Choose the best justified split for a final same-file convergence audit. If different from V6, explain why; if the same split is genuinely best, justify keeping it.
- State explicitly in the protocol that the reserve window in V7 is **internal-only** and **not eligible for clean OOS proof on the current file**.
- Do not include session-specific contamination details, prior date-range maps, or prior-session outcomes inside V7.

**E. Keep V7 free of data-derived specifics and prior-result leakage.**
- `RESEARCH_PROMPT_V7.md` must NOT include any specific features, lookbacks, thresholds, parameter values, calibration details, named winners, or named prior systems from any prior session.
- All data-derived specifics belong exclusively in `CONTAMINATION_LOG_V3.md`.
- The Fresh Re-derivation Rules section may state only that prior sessions exist and that their specifics must not narrow the search.
- V7 may include the generic methodological statement that reserve is internal-only and not clean OOS on the current file, but it must not include any session-specific contamination narrative or detailed disclosure.

**F. Update the Fresh Re-derivation Rules.**
The rules must reflect all of the following:
- Three prior research sessions now exist, and they produced different frozen results.
- The new session must not assume any prior result is more correct than the others.
- The new session must follow its own evidence.
- Divergence among prior sessions is not a reason to “reconcile” them by construction; the search space must remain open.
- The new session must not import prior frozen candidates, prior shortlists, prior favored feature families, prior parameter regions, or prior decision outcomes as narrowing priors.

**G. Position V7 correctly.**
- V7 should be written as a **final same-file convergence audit protocol**, not as an invitation to endless further same-file prompt iteration.
- The protocol should make clear that same-file methodological tightening can improve governance, but does not create clean new OOS evidence on its own.

**H. Keep the same section ordering as V6.**
1. Research protocol — FIRST
2. Fresh Re-derivation Rules — IMMEDIATELY AFTER the protocol, BEFORE any information from prior sessions
3. Meta-knowledge from Prior Research — LAST

**I. Do not reference `CONTAMINATION_LOG_V3.md` anywhere inside V7.**

---

### Deliverable 2: CONTAMINATION_LOG_V3.md

I have uploaded `CONTAMINATION_LOG_V2.md` from the prior research sequence. Update it into `CONTAMINATION_LOG_V3.md` to include this completed V6 session in full.

Required updates:
- Add a new round entry documenting exactly what this session tried and found.
- Add this session’s feature scans, shortlists, frozen winner, thresholds, calibration details, comparison steps, reserve/internal findings, and any other data-derived specifics needed for complete contamination accounting.
- Update the union contamination map to include every range this session touched.
- State explicitly whether any within-file range remains globally untouched by prior research roles. If none remains, say so plainly.
- Document the split rationale used in this session. If suggesting alternative splits, label them as historical notes for provenance, not as recommendations for further same-file iteration (since V7 is the final same-file audit).
- Distinguish clearly between:
  - acceptable **internal-only** split designs for one final same-file audit; and
  - the requirement of **newly appended data not present in the current files** for any future clean OOS validation.

This file must remain fully self-contained and must **NOT** be referenced from within `RESEARCH_PROMPT_V7.md`.

---

### Deliverable 3: CHANGELOG_V6_TO_V7.md

Create a separate file listing every material change from V6 to V7.

For each change, include:
- the exact change;
- the reason for the change;
- the classification: `[FIX]`, `[IMPROVE]`, `[NEW]`, or `[REMOVE]`.

The changelog must include not only protocol edits, but also governance changes, isolation-rule clarifications, step-order changes, split-architecture changes, and any explicit effort to reduce same-file methodological overfitting.

---

### Deliverable 4: CONVERGENCE_STATUS_V2.md

Update the convergence status to include all sessions so far:
- the V4 rounds;
- the V5 session;
- the completed V6 session.

This file is for me (the human), not for the AI. Write it in **Vietnamese**, in clear, direct language.

It must:
- list each session, its frozen winner, and its key metrics;
- state where the sessions converged and where they diverged;
- identify which aspects appear consistent across sessions, and which aspects remain inconsistent;
- assess honestly whether a fourth session on the same data is likely to resolve the divergence;
- state clearly whether new appended data is required for clean resolution;
- give a direct recommendation on whether running V7 once is still worthwhile as a final same-file convergence audit, or whether further iteration should stop now;
- state clearly whether any same-file iteration beyond V7 is scientifically productive or not.

The goal of `CONVERGENCE_STATUS_V2.md` is to help me decide among three actions:
1. run V7 once as a final same-file convergence audit;
2. stop same-file iteration immediately;
3. wait for new data before making stronger claims.

---

### Format constraints

- All four files must be Markdown.
- `RESEARCH_PROMPT_V7.md` must be self-contained: a new AI receiving only that file plus the raw data files must be able to start immediately.
- `CONTAMINATION_LOG_V3.md` must be self-contained and must NOT be referenced from within `RESEARCH_PROMPT_V7.md`.
- `CONVERGENCE_STATUS_V2.md` is for me, the human, and must be written in Vietnamese.
- `RESEARCH_PROMPT_V7.md`, `CONTAMINATION_LOG_V3.md`, and `CHANGELOG_V6_TO_V7.md` must be written in English.
- Regenerate all four documents from scratch. Do not produce partial patches. Ensure the four documents are mutually consistent.

---

### Final checklist before delivery

1. Does `RESEARCH_PROMPT_V7.md` contain any specific features, lookbacks, thresholds, parameter values, calibration details, named prior winners, or named prior systems?
   - If yes, remove them from V7 and keep them only in `CONTAMINATION_LOG_V3.md`.

2. Does `RESEARCH_PROMPT_V7.md` avoid session-specific contamination details while still honestly stating that the reserve window is internal-only and not eligible for clean OOS on the current file?
   - If not, revise it.

3. Does `RESEARCH_PROMPT_V7.md` reference `CONTAMINATION_LOG_V3.md` directly or indirectly?
   - If yes, remove the reference.

4. Does the Meta-knowledge section contain only genuinely new, principle-level lessons, without duplicating what V6 already had?
   - If duplicated, deduplicate.

5. Does any lesson in V7 implicitly point toward a specific feature family, lookback region, threshold level, or parameter choice?
   - If yes, rewrite it so it stays purely methodological.

6. Does V7 clearly frame itself as a **final same-file convergence audit**, rather than an open-ended attempt to keep optimizing on the current file?
   - If not, add that framing.

7. Does `CONTAMINATION_LOG_V3.md` include this session’s full round entry and explicitly state whether any within-file clean OOS remains?
   - If not, it is incomplete.

8. Does `CONVERGENCE_STATUS_V2.md` give me enough information to choose among:
   - running V7 once;
   - stopping now;
   - waiting for new data?
   - If not, add more detail.

9. Are all four documents internally consistent about the reserve/internal-only status, the scientific limits of the current file, and the recommendation after V7?
   - If not, fix the inconsistency.

10. If a completely new AI reads V7, would it be biased toward any specific feature, lookback, threshold, or prior result from earlier sessions?
    - If yes, revise V7 again.

Do not ask clarifying questions. Everything needed is already available in the prompt, prior artifacts, and the completed session outputs.
