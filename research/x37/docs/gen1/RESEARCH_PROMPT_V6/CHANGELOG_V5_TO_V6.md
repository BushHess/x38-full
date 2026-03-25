# CHANGELOG_V5_TO_V6

This document lists the substantive changes made when rewriting `RESEARCH_PROMPT_V5.md` into `RESEARCH_PROMPT_V6.md`.

## Summary

V6 keeps the core scientific philosophy of V5, but tightens three areas that proved weak in practice:

1. **provenance / independence control**,
2. **search-manifest / audit completeness**,
3. **split and fold design for a stronger internal test structure**.

## Change log

| Section / topic | Change in V6 | Reason | Class |
|---|---|---|---|
| Objective | Added “provenance-controlled” to the objective and clarified that current-session evidence outranks inherited beliefs. | The prior run showed that a session can look like a re-derivation while still depending on earlier artifacts. V6 needed to make independence an explicit design goal. | [IMPROVE] |
| New section: admissible inputs and provenance lock | Added a new pre-freeze rule that only the prompt and raw data files may be used before freeze. Explicitly banned prior reports, logs, JSON files, shortlist tables, and benchmark specs before freeze. | V5 did not explicitly forbid artifact-assisted selection, which allowed ambiguity between a clean re-derivation and an audit of prior outputs. | [FIX] |
| Provenance log requirement | Added a mandatory provenance log and a rule that any disallowed pre-freeze artifact access invalidates “clean independent re-derivation” status. | The earlier session made it clear that strategy evidence and session independence are separate questions and must be recorded separately. | [NEW] |
| Current-session table generation rule | Added a rule that every table used for candidate selection must be generated in the current session from raw data. | V5 did not make this explicit, which left room for reproduced tables. | [FIX] |
| Protocol lock | Expanded the protocol lock to include admissible inputs, discovery fold structure, feature-library manifest format, candidate-ledger format, and allowed calibration modes. | The original lock was good but incomplete for reproducibility and independence. | [IMPROVE] |
| Data audit | Expanded the audit to require machine-readable audit tables and an explicit anomaly-handling log. | The earlier work surfaced structural irregularities; V6 now requires the handling decision to be preserved, not merely described. | [IMPROVE] |
| Silent data repair | Added “do not silently repair anomalous rows” language. | Silent cleanup creates hidden degrees of freedom and complicates exact reproduction. | [FIX] |
| Warmup / live boundary | Moved the “no live trading before” boundary from 2019-01-01 to 2020-01-01. | V6 re-centers the discovery evaluation on denser unseen folds beginning in 2020 and treats earlier data as context / calibration only. | [IMPROVE] |
| Data split architecture | Replaced the V5 split with: context `2017-08-17` to `2019-12-31`, discovery `2020-01-01` to `2022-12-31`, selection holdout `2023-01-01` to `2024-06-30`, reserve/internal `2024-07-01` to dataset end. | The new split increases the internal reserve length and supports a denser discovery walk-forward structure. | [IMPROVE] |
| Reserve status in protocol | Made it explicit inside the protocol that the within-file reserve under V6 is internal only and cannot earn a clean OOS label. | The user requested honest wording, and the current file no longer supports a clean within-file OOS claim. | [FIX] |
| Discovery walk-forward | Replaced the V5 annual three-fold walk-forward with six semiannual folds across 2020–2022. | The prior run showed that too few unseen folds can overweight one subperiod. Denser slicing produces a stronger internal read. | [IMPROVE] |
| Stage 1: faster/native vs transported/slower-aligned signals | Added an explicit requirement to evaluate native faster-timeframe features separately from slower-timeframe transports aligned onto faster bars. | The prior run showed that transported slower-state can masquerade as independent fast evidence if not separated. | [NEW] |
| Stage 1 registry export | Added a mandatory machine-readable Stage 1 registry and result table for every scanned config. | The prior handoff lacked a fully serialized scan universe, which forced later reconstruction instead of exact replay. | [FIX] |
| Stage 1 measurement criteria | Added “whether the feature adds information beyond already-visible slower state” to the measurement checklist. | This directly addresses the transport-vs-incremental-information problem. | [NEW] |
| Stage 2 shortlist | Added a requirement to keep at least one simple frontier candidate and one layered alternative with a meaningfully different failure mode. | The prior run showed that a simpler candidate can ultimately be the best choice even when a more complex sibling leads earlier tables. | [IMPROVE] |
| Shortlist ledger | Added a keep / drop ledger with explicit reason codes. | V5 asked for documentation, but not at a sufficiently rigid artifact level. | [NEW] |
| Redundant transported clones | Added a rule that a transported slower-state clone does not count as a genuine orthogonal faster representative unless paired tests show incremental value. | V5 did not explicitly guard against this failure mode. | [FIX] |
| Stage 3 framing | Changed the wording so that layering is explicitly treated as a hypothesis rather than an expected destination. | V5 could still be read as gently steering toward layered systems; the prior run showed that this bias is not justified. | [FIX] |
| Stage 4 coarse search | Added a requirement to export the full tested grid for every serious family and to preserve a center-of-plateau representative. | The prior run reinforced that later audits need the grid, not just the winner. | [IMPROVE] |
| Stage 4 survivor rule | Added a rule that if a simple and complex representative are close enough that paired tests do not cleanly separate them, both should survive into the frozen comparison set. | The earlier selection dynamics showed that pre-reserve headline ranking can reverse later. | [NEW] |
| Stage 5 candidate selection | Changed the target of Stage 5 from “select the leading candidate” to “select the leading comparison set.” | The reserve stage should test a frozen rival set, not only one provisional winner. | [FIX] |
| Frozen comparison-set requirement | Added a mandatory frozen comparison-set ledger. | This was implicit in V5 but not serialized strongly enough. | [NEW] |
| Stage 6 exports | Added required pre-reserve exports: frozen system specification, frozen comparison-set ledger, final search tables, provenance declaration. | The earlier session showed that post hoc reconstruction is inferior to explicit serialization. | [NEW] |
| Stage 7 wording | Renamed the reserve stage to “reserve/internal evaluation” and clarified that no relabeling to clean OOS is allowed. | V5 already distinguished reserve from clean OOS, but V6 makes the internal-only status explicit in the stage itself. | [FIX] |
| Mandatory evaluation list | Added provenance audit as an explicit mandatory evaluation item. | Independence must be checked, not assumed. | [NEW] |
| Hard acceptance criteria | Added a provenance-contamination clause and a complexity tie-break: if a complex candidate lacks meaningful paired advantage over a simpler nearby rival, the simpler candidate wins. | The prior run showed that simplicity should win unless complexity earns its keep on paired evidence. | [IMPROVE] |
| Clean OOS hard-acceptance rule | Replaced the generic V5 clean-OOS condition with a V6-specific statement that clean OOS is unavailable from the supplied file alone. | This aligns the prompt with the actual evidence boundary of the current dataset. | [FIX] |
| Evidence labels | Kept the same label names, but clarified that `CLEAN OOS CONFIRMED` is reserved for future appended data and is not attainable from the current file alone. | Preserves continuity with V5 while removing a false implication that a within-file clean OOS may still be available here. | [IMPROVE] |
| Ranking criteria | Reworded reserve ranking as “reserve/internal result” rather than generic reserve. | Terminology now matches the actual evidentiary status. | [FIX] |
| Deliverables | Expanded deliverables to include machine-readable audit tables, full Stage 1 registry, shortlist ledger, frozen comparison-set ledger, frozen JSON, and provenance declaration. | V5 deliverables were not enough to guarantee exact later replay. | [IMPROVE] |
| Anti-patterns | Added explicit bans on importing prior shortlist / freeze tables, treating reproduced tables as current evidence, failing to export the manifest / ledger, and mistaking transported slower state for independent fast information. | These were concrete failure modes surfaced by the earlier session. | [FIX] |
| Fresh Re-derivation Rules | Updated the rules to reflect that two prior sessions already exist, they produced different outcomes, and neither should be privileged. | The research context changed materially after the second completed session. | [NEW] |
| Fresh Re-derivation Rules | Removed any implication that convergence with earlier work would validate the new session more than divergence would. | After two different frozen outcomes, the right rule is evidence-first, not majority vote. | [IMPROVE] |
| Fresh Re-derivation Rules | Added an explicit rule that reserve in this version is internal only and cannot be called clean OOS. | The user requested this to be stated plainly. | [FIX] |
| Meta-knowledge: layered multi-timeframe bias | Removed / softened prior wording that could be read as favoring slower+faster layered systems as the default strong architecture. | The just-completed session showed that a single-layer candidate can outperform layered alternatives. | [REMOVE] |
| Meta-knowledge: ancillary information types | Reframed prior wording so that ancillary layers are judged by incremental evidence, not by presumed role. | The goal is to reduce architecture bias in the new session. | [IMPROVE] |
| Meta-knowledge: provenance | Added lessons about provenance control, current-session table generation, and why imported artifacts invalidate strict re-derivation. | This was the most important methodological lesson from the completed V5 run. | [NEW] |
| Meta-knowledge: manifest completeness | Added a lesson that the full scan manifest and candidate ledger must be serialized, otherwise later handoffs become reconstruction exercises. | This directly addresses the biggest documentation gap encountered after V5. | [NEW] |
| Meta-knowledge: transport vs incremental information | Added a lesson distinguishing visible slower-state transport from genuinely new faster-timeframe information. | This was a new methodological clarification surfaced by the completed V5 run. | [NEW] |
| Meta-knowledge: denser unseen slicing | Added a lesson that denser chronological slicing can be more informative than a small number of coarse test windows. | This motivates the semiannual walk-forward redesign. | [NEW] |
| Meta-knowledge: simple frontier retention | Added a lesson to keep a simple family representative alive until final internal comparison. | The prior run showed that the simpler survivor can become the final winner even after trailing pre-reserve. | [NEW] |

## Net effect

V6 is intentionally stricter than V5 in two ways:

1. it is harder to accidentally contaminate the session while still calling it an independent re-derivation;
2. it is harder to lose exact auditability of what was scanned, compared, frozen, and rejected.
