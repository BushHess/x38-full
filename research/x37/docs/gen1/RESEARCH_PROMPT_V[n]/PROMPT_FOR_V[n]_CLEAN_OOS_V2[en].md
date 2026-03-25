# PROMPT TO SEND TO THE JUST-COMPLETED SAME-FILE SESSION

> This prompt is intended to be used only **after** the current same-file convergence-audit session has fully frozen its candidate and completed its own research outputs. Its purpose is to generate a handoff for a future session in which **clean out-of-sample validation becomes structurally possible through genuinely appended future data**.
>
> Before sending this prompt:
> 1. Wait until the current session has frozen its candidate and completed its deliverables.
> 2. Upload the latest contamination log from the previous handoff (currently `CONTAMINATION_LOG_V3.md`) plus any current-session artifacts needed for a complete update. Uploading those artifacts at this stage is acceptable because freeze is already complete.
> 3. Do **not** upload the contamination log to the future clean-OOS research session at startup. That future session must remain blind to prior data-derived specifics until it freezes its own candidate.
> 4. Then send the full request below in one message.

---

## Request: Prepare handoff for a new research session capable of CLEAN OOS validation on appended future data

The result of the current session is still internal with respect to the current archive. I now want a future research session that preserves the methodological lessons learned so far while making a genuinely clean OOS test structurally possible.

The only acceptable way to do that is this:
- treat **all data already present in the current files** as the **historical archive**;
- use that historical archive for discovery, selection, and internal stress testing only;
- reserve **only genuinely new BTC/USDT data whose timestamps begin strictly after the archive end** for the future clean OOS test.

The future session must rediscover its candidate from first principles. It must not inherit prior data-derived specifics.

### Core principles

- Transfer only **meta-knowledge** about methodology and structure, not data-derived specifics.
- The historical archive may support discovery, selection, calibration, and internal robustness checks, but it is **not eligible** for clean OOS certification.
- The clean OOS reserve must consist only of **appended future data** that did not exist in any file available to prior sessions.
- Structural separation makes clean OOS certification **possible**; it does **not** automatically make the final result **confirmed**.
- After the clean reserve is opened, there must be **no redesign, no retuning, no winner switching, and no salvage by moving to a runner-up**.

### I need you to produce 4 deliverables:

---

### Deliverable 1: RESEARCH_PROMPT_V8.md

Rewrite `RESEARCH_PROMPT_V7.md` into version V8 with the following changes:

**A. Preserve what was correct and useful.**
- Keep everything from V7 that worked correctly in the completed same-file convergence-audit run.
- Preserve the parts of V7 that improved governance, isolation, provenance control, and scientific honesty.

**B. Fix and improve the protocol based on what has now been learned.**
- Fix every part of V7 that proved ambiguous, weakly governed, operationally awkward, or vulnerable to misuse.
- Strengthen the protocol wherever needed so the future clean-OOS session is harder to contaminate and harder to misuse for post-hoc selection.
- Keep all changes at the methodological level only. Do not import any prior session's data-derived specifics.

**C. Redesign the data architecture around a strict archive/append separation.**
The V8 protocol must explicitly distinguish between two data roles:

1. **Historical archive**
   - This is all data already present in the current files.
   - It may be used for context, warmup, discovery, candidate-selection holdout, and optionally an archive-internal reserve or stress slice.
   - It is **not eligible** for clean OOS certification.

2. **Fresh appended reserve**
   - This must contain only data whose timestamps begin **strictly after** the latest timestamp present in the historical archive files.
   - It is the **only** range eligible for clean OOS evaluation.

Rules for V8:
- The protocol must infer the archive/append boundary from the raw files themselves rather than hardcoding a specific date.
- The protocol must expect **separate raw archive files** and **separate raw append files** for each timeframe.
- The protocol must define the expected raw schema, role-identification logic, and boundary-validation checks.
- Discovery, search, calibration, and frozen-leader selection must be completed **without opening the appended reserve**.
- If V8 uses an archive-internal reserve slice, that slice must be labeled **internal only** and must never be confused with clean OOS.

**D. Update reserve governance so clean OOS is measured cleanly.**
V8 must enforce all of the following:
- The exact frozen leader must be selected using **archive-only evidence**.
- The fresh appended reserve must remain sealed until the frozen leader and frozen comparison set are recorded.
- The **first official clean reserve evaluation** must be performed on the exact frozen leader.
- If alternate frozen candidates are evaluated on the fresh reserve afterward, those evaluations must be labeled **post-verdict diagnostics only** and must not be used to switch winners.
- If the frozen leader fails on the clean reserve, the session must report that failure honestly. It must not rescue the outcome by moving to another candidate.

**E. Update the evidence-label logic honestly.**
V8 must state clearly that:
- a reserve outside the historical archive makes **clean OOS validation eligible**;
- that structural eligibility is **necessary but not sufficient** for a `CLEAN OOS CONFIRMED` conclusion;
- a clean reserve verdict must still depend on the frozen leader's actual performance under the predeclared protocol;
- if the clean reserve is too short, too sparse, or otherwise underpowered, the session must use an honest **inconclusive** label rather than overstating certainty.

**F. Keep V8 free of data-derived specifics and prior-result leakage.**
- `RESEARCH_PROMPT_V8.md` must NOT include any specific features, lookbacks, thresholds, parameter values, calibration details, named winners, or named prior systems from any prior session.
- All data-derived specifics belong exclusively in `CONTAMINATION_LOG_V4.md`.
- The Fresh Re-derivation Rules section may state only that prior sessions exist and that their specifics must not narrow the search.
- V8 may state the generic methodological fact that the historical archive is internal-only and that appended future data is the only eligible clean reserve.
- V8 must NOT contain a session-specific contamination narrative.

**G. Update the Fresh Re-derivation Rules.**
The rules must reflect all of the following:
- multiple prior sessions now exist;
- their data-derived specifics must not narrow the new search;
- the future clean-OOS session must follow its own evidence;
- the existence of prior winners does not make any of them a default target;
- the search space must remain open.

**H. Position V8 correctly.**
- V8 should be written as the first protocol in this research line that is capable of a genuinely clean appended-data OOS test.
- It should not be written as a continuation of same-file optimization.
- It should make clear that archive-only improvements strengthen governance, but do not themselves create clean OOS evidence.

**I. Keep the same section ordering as V7.**
1. Research protocol — FIRST
2. Fresh Re-derivation Rules — IMMEDIATELY AFTER the protocol, BEFORE any information from prior sessions
3. Meta-knowledge from Prior Research — LAST

**J. Do not reference `CONTAMINATION_LOG_V4.md` anywhere inside V8.**

---

### Deliverable 2: CONTAMINATION_LOG_V4.md

I have uploaded `CONTAMINATION_LOG_V3.md` from the prior handoff. Update it into `CONTAMINATION_LOG_V4.md` to include the just-completed session in full.

Required updates:
- Add a new round entry documenting exactly what this session tried and found.
- Add this session's feature scans, shortlists, frozen winner, thresholds, calibration details, comparison steps, reserve/internal findings, and any other data-derived specifics needed for complete contamination accounting.
- Update the union contamination map to include every range this session touched.
- Record the exact archive-end timestamps for each raw file used by the current session.
- State explicitly whether any within-archive range remains globally untouched by prior research roles. If none remains, say so plainly.
- Distinguish clearly between:
  - contaminated historical-archive ranges;
  - acceptable archive-internal split designs for research and internal stress testing;
  - the requirement that any future clean reserve must begin strictly **after** the archive end and must come from genuinely newly appended data.
- Update the suggested split templates for a future clean-OOS session built on archive + append separation.

This file must remain fully self-contained and must **NOT** be referenced from within `RESEARCH_PROMPT_V8.md`.

---

### Deliverable 3: CHANGELOG_V7_TO_V8.md

Create a separate file listing every material change from V7 to V8.

For each change, include:
- the exact change;
- the reason for the change;
- the classification: `[FIX]`, `[IMPROVE]`, `[NEW]`, or `[REMOVE]`.

The changelog must include not only protocol edits, but also:
- archive/append data-architecture changes;
- reserve-governance changes;
- evidence-label changes;
- isolation-rule clarifications;
- package-boundary and provenance-control changes;
- any explicit effort to prevent post-reserve winner switching or same-data salvage logic.

---

### Deliverable 4: DATA_PREPARATION_GUIDE.md

Write a clear, step-by-step guide for me to prepare the data package for the future clean-OOS session.

It must include all of the following:

1. **What data I already have**
   - describe the current historical archive's exact date range, schema, timeframe coverage, and file roles;
   - identify the archive end separately for H4 and D1 if needed.

2. **What new data I need to download**
   - specify the source, market type, pair, and timeframes needed to match the archive exactly;
   - define the start timestamp as the **first bar strictly after the archive end**;
   - define the end timestamp as the time I choose to download, or later if I intentionally wait longer for a stronger reserve.

3. **Minimum clean-reserve recommendation**
   - recommend both:
     - a **calendar waiting recommendation**, and
     - a **target trade-count recommendation**,
     based on the trade frequency actually observed in the current session's competitive frontier;
   - explain the trade-off between starting sooner (faster but weaker inference) and waiting longer (slower but stronger inference);
   - explain what happens if I proceed with an underpowered clean reserve.

4. **How to package the data**
   - tell me whether to keep archive and append data separate or combine them;
   - default expectation: **keep them separate**;
   - provide a recommended folder structure, filename convention, and zip layout;
   - include a package-manifest template containing, at minimum:
     - filename,
     - role (`archive` or `append`),
     - timeframe,
     - row count,
     - min/max timestamp,
     - source,
     - timezone,
     - schema confirmation,
     - file hash.

5. **Verification steps**
   - how to confirm the append data matches the archive schema exactly;
   - how to confirm the timestamps are in the same timezone and semantics;
   - how to confirm there is **no overlap** and **no unintended gap** at the archive/append boundary;
   - how to confirm the append files contain native bars and were not resampled or manually edited.

6. **Contamination precautions**
   - explicitly tell me **not** to preview, chart-inspect, backtest, or manually pre-screen the append data beyond basic integrity checks;
   - basic integrity checks are allowed, but performance inspection is not.

7. **What to upload to the future clean-OOS session**
   - list the exact files to upload;
   - provide the exact startup prompt to use;
   - the startup prompt must be simple and must NOT contain any specific features, lookbacks, thresholds, parameter values, named prior winners, or contamination-log content;
   - explicitly state that `CONTAMINATION_LOG_V4.md` should **not** be uploaded at startup.

8. **What to do if the append reserve is shorter than recommended**
   - explain whether I should wait longer;
   - if I choose not to wait, explain that the session may still run but should be prepared to produce an honest **inconclusive** reserve verdict.

---

### Format constraints

- All four files must be Markdown.
- `RESEARCH_PROMPT_V8.md` must be self-contained: a new AI receiving only that file plus the prepared data package must be able to start immediately.
- `CONTAMINATION_LOG_V4.md` must be self-contained and must NOT be referenced from within `RESEARCH_PROMPT_V8.md`.
- `DATA_PREPARATION_GUIDE.md` is for me (the human), not for the AI, and must be written in clear, actionable language.
- Write everything in English.
- Regenerate all four documents from scratch. Do not produce partial patches. Ensure the four documents are mutually consistent.

---

### Final checklist before delivery

1. Does V8 clearly distinguish the contaminated **historical archive** from the clean **appended future reserve**?
   - If not, redesign.

2. Is the append-reserve boundary defined dynamically from the raw files rather than by a hardcoded date?
   - If not, fix it.

3. Does V8 state clearly that appended future data makes clean OOS **eligible**, but does not automatically guarantee `CLEAN OOS CONFIRMED`?
   - If not, revise it.

4. Does V8 forbid post-reserve redesign, retuning, winner switching, and rescue by runner-up?
   - If not, add those prohibitions.

5. Does V8 contain any specific features, lookbacks, thresholds, parameter values, calibration details, named prior winners, or named prior systems?
   - If yes, remove them from V8 and keep them only in `CONTAMINATION_LOG_V4.md`.

6. Does V8 avoid session-specific contamination narrative and avoid referencing `CONTAMINATION_LOG_V4.md` directly or indirectly?
   - If not, revise it.

7. Does `CONTAMINATION_LOG_V4.md` include the current session's full round entry, archive-end timestamps, and an explicit statement about whether any within-archive clean OOS remains?
   - If not, it is incomplete.

8. Does `DATA_PREPARATION_GUIDE.md` tell me to keep archive and append data separate, include a manifest, verify continuity/no-overlap/no-gap, and avoid previewing append performance?
   - If not, add those requirements.

9. Does the startup prompt in `DATA_PREPARATION_GUIDE.md` stay clean and minimal?
   - If not, rewrite it.

10. If I follow the guide exactly, is a genuinely clean appended-data OOS test structurally achievable in the future session — while still allowing the possibility of an honest inconclusive result?
    - If not, something is wrong. Fix it.

11. Are version numbers and file names internally consistent with the current state of the research line?
    - If not, fix them.

Do not ask clarifying questions. Everything needed is already available in the prompt, prior artifacts, and the completed session outputs.
