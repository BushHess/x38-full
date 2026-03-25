# CHANGELOG_V6_TO_V7

This file lists the material changes made when moving from `RESEARCH_PROMPT_V6.md` to `RESEARCH_PROMPT_V7.md`.

## Summary intent of V7

V7 keeps the core first-principles structure of V6, but it changes the framing and governance: V7 is written as a **final same-file convergence audit**, not as another ordinary optimization pass. The main purpose of the changes is to tighten auditability, reduce same-file methodological drift, and make the scientific limits of the current file impossible to miss.

## Detailed changes

| Classification | Change | Reason |
|---|---|---|
| [NEW] | Repositioned V7 as a **final same-file convergence audit protocol** rather than a generic next research prompt. | The current file no longer supports clean within-file OOS proof. V7 therefore needs to be honest about what it can and cannot establish. |
| [NEW] | Added explicit objective text stating that later same-file work is not automatically better than earlier same-file work. | This prevents chronological bias and makes clear that stronger governance does not guarantee a stronger headline backtest. |
| [FIX] | Kept the full raw CSV schema explicit in the prompt: `symbol`, `interval`, `open_time`, `close_time`, `open`, `high`, `low`, `close`, `volume`, `quote_volume`, `num_trades`, `taker_buy_base_vol`, `taker_buy_quote_vol`. | V6 did not state the raw input surface in enough detail for a fully self-contained fresh run. |
| [FIX] | Strengthened the admissible-inputs section so any non-raw artifact consulted before freeze must be logged in a provenance record and disclosed in the deliverables. | V6 already aimed at blind re-derivation, but V7 makes provenance auditing harder to evade or under-specify. |
| [FIX] | Added an explicit anomaly-disposition register to both the protocol lock and the pre-discovery audit sequence. | V6 required anomaly logging, but it did not force the exact disposition rules to be frozen in a dedicated register before feature work began. |
| [IMPROVE] | Expanded the pre-discovery audit to include impossible-OHLC checks and mandatory D1-vs-H4 reconciliation on overlapping days. | This reduces ambiguity in raw-data acceptance and makes the audit sequence more reproducible. |
| [IMPROVE] | Redesigned the split architecture to `context 2017-08-17 to 2019-12-31`, `discovery 2020-01-01 to 2023-06-30`, `candidate-selection holdout 2023-07-01 to 2024-09-30`, and `reserve/internal 2024-10-01 to dataset end`. | The new split gives broader regime coverage inside discovery, more discriminative holdout length, and a later internal contradiction slice while staying honest that reserve is internal only. |
| [IMPROVE] | Replaced V6’s six semiannual discovery folds with quarterly discovery folds from `2020-Q1` through `2023-Q2`. | Denser unseen slicing gives better stability diagnostics and reduces dependence on a small number of coarse windows. |
| [NEW] | Added an explicit statement that the V7 split is the **final same-file convergence-audit split** for the current file. | This prevents the split itself from becoming another open-ended optimization axis. |
| [IMPROVE] | Reframed Stage 1 as an ordered sequence: native D1 scan, native H4 scan, cross-timeframe relationship scan, transported slower-state audit on H4. | V6 treated these buckets less explicitly. V7 makes their order and conceptual roles clearer. |
| [NEW] | Added a rule that transported slower-state clones count primarily as redundancy controls and do not qualify as genuine faster frontiers without incremental paired evidence. | This closes a loophole where slower information could be over-credited simply because it was made visible on fast bars. |
| [NEW] | Added a Stage 1 promotion gate requiring positive post-cost discovery evidence, minimum trade support, minimum fold consistency, and no obvious dependence on a single quarter. | V6 had acceptance logic later, but not a clean early gate for deciding which Stage 1 ideas deserved deeper attention. |
| [IMPROVE] | Added a rule that Stage 3 layered search may only use representatives that already survived Stage 2 orthogonal shortlist formation. | This reduces wasteful brute-force pair generation and keeps layered search tied to evidence already earned in simpler stages. |
| [NEW] | Raised the burden on optional entry-only third layers by requiring them to survive their own trade-count shrinkage and not just improve one headline metric. | V6 allowed entry-only tests, but V7 defines a clearer standard for when an extra layer is worth keeping. |
| [IMPROVE] | Split candidate selection into Stage 5A discovery-only freeze of the comparison set, Stage 5B holdout ranking of the frozen set, and Stage 5C pre-reserve leader declaration. | This removes interpretive ambiguity about when the holdout may be opened and what may still change after that point. |
| [NEW] | Added a mandatory pairwise-comparison matrix format to the protocol lock and freeze deliverables. | V7 requires the final pre-reserve judgment path to be exported in a structured, auditable form rather than left in narrative prose. |
| [NEW] | Added a deterministic tie-break rule for paired-indeterminate candidates of equal complexity. | V6 had ranking ideas, but V7 removes discretionary tie resolution when differences are too small to justify narrative preference. |
| [IMPROVE] | Added “lower cross-timeframe dependence” to the deterministic tie-break order. | When candidates are otherwise hard to separate, V7 favors the cleaner evidence object. |
| [NEW] | Made pre-reserve regime decomposition mandatory in candidate selection, not only in final validation. | V6 required regime analysis, but V7 moves it into the actual pre-reserve judgment path. |
| [IMPROVE] | Added a hard-criterion check against strong pre-reserve sign reversal in a major regime for systems still being treated as general-purpose candidates. | This reduces the risk that aggregate metrics hide unstable regime behavior until too late. |
| [IMPROVE] | Clarified that opening the candidate-selection holdout may not expand the candidate space in any way. | V6 implied this; V7 states it directly to remove loopholes. |
| [IMPROVE] | Expanded the freeze pack to include plateau tables, ablation tables, the pairwise comparison matrix, and the anomaly-disposition register. | This makes the pre-reserve decision path substantially easier to reconstruct and audit. |
| [IMPROVE] | Clarified that reserve/internal contradiction must be reported plainly but cannot trigger redesign or tie-breaking redesign after freeze. | V6 already forbade redesign after reserve; V7 makes the reporting obligation explicit. |
| [NEW] | Added transport-vs-native redundancy audit as a named mandatory evaluation item. | This formalizes an important lesson learned while running V6. |
| [NEW] | Added a session-finality statement and stop condition for same-file prompt iteration to the protocol lock and Fresh Re-derivation Rules. | Same-file prompt editing is itself a search dimension. V7 needs an explicit boundary so methodology does not become another hidden optimization surface. |
| [NEW] | Added anti-patterns rejecting workflows that treat later same-file results as automatically more correct or that use repeated same-file prompt editing as a hidden optimization axis. | These were real governance risks exposed by the sequence of same-file sessions. |
| [NEW] | Added Fresh Re-derivation language stating that three prior sessions exist, none is privileged, and the new session must not try to reconcile them by construction. | This reflects the current research history without leaking data-derived specifics. |
| [FIX] | Kept the reserve-honesty rule explicit: the within-file reserve remains internal only and cannot be labeled clean OOS. | The scientific status of the reserve window must be unambiguous in V7. |
| [REMOVE] | Removed wording that could be read as giving transported slower-state systems equal conceptual status to genuine native faster candidates before incrementality is proven. | V7 narrows this ambiguity directly. |
| [REMOVE] | Replaced V6-adjacent duplicate meta-lessons with genuinely new governance lessons about same-file iteration, stop conditions, and the limits of internal evidence. | The user required the V7 meta-knowledge section to add only genuinely new lessons and to avoid duplicate guidance already present in V6. |
