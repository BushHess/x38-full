# CHANGELOG_V4_TO_V5

This changelog lists every material change made when rewriting V4 into V5.

| ID | Class | Change | Reason |
|---|---|---|---|
| 1 | [IMPROVE] | Reframed the objective from “discover the strongest system” toward “discover the strongest scientifically defensible system inside a declared search space.” | Reduces overclaiming and aligns the prompt with finite-data, non-stationary reality. |
| 2 | [FIX] | Added an explicit distinction between evidence, inference, and final design judgment. | Prevents the research narrative from silently converting observations into unjustified certainty. |
| 3 | [FIX] | Added a formal data-audit step before discovery. | Raw-data integrity and time semantics are prerequisite scientific checks, not optional setup. |
| 4 | [FIX] | Clarified that realized strategy returns must follow the actual execution path and not close-to-close proxies. | Prevents metric drift and hidden execution inconsistency. |
| 5 | [FIX] | Strengthened the cross-timeframe rule: slower bars become visible only after their close, via backward as-of logic. | The higher-timeframe merge is a core leakage risk and needed firmer wording. |
| 6 | [FIX] | Added explicit “no resampling synthetic bars / no invented gap fill” language. | V4 described leakage risk but did not fully lock raw-bar handling. |
| 7 | [NEW] | Replaced the old two-zone split with a three-zone structure: discovery, candidate-selection holdout, reserve. | A wide search benefits from a separate selection holdout and a later frozen reserve check. |
| 8 | [NEW] | Added the rule that a reserve window counts as true OOS only if it is certified untouched across all prior rounds of all sessions. | This fixes the false-security problem where a “holdout” exists inside a file that has already been reused elsewhere. |
| 9 | [NEW] | Added evidence labels: `CLEAN OOS CONFIRMED`, `INTERNAL ROBUST CANDIDATE`, `NO ROBUST IMPROVEMENT`. | Separates evidence cleanliness from model quality and forces honest reporting. |
| 10 | [FIX] | Added a structured search ladder: raw measurement -> single-feature state systems -> orthogonal shortlist -> minimal layered systems -> local refinement. | The earlier process was too open-ended and allowed redundant or premature complexity. |
| 11 | [NEW] | Added explicit redundancy pruning / orthogonal representative selection. | Prior work showed many top candidates were just transforms of the same underlying phenomenon. |
| 12 | [FIX] | Added role discipline across layers: context gate, state controller, optional entry-only confirmation. | Prevents the same feature from being forced into entry, hold, and exit without evidence. |
| 13 | [NEW] | Added the rule that an optional third layer may be entry-only and cannot be introduced before a robust two-layer core exists. | Prevents premature feature stacking and keeps the search interpretable. |
| 14 | [FIX] | Expanded parameter-search guidance to require coarse search first and local refinement only around broad plateaus. | The research process benefited when local tuning happened after, not before, a coarse map of the space. |
| 15 | [FIX] | Strengthened plateau guidance to prefer the center of a plateau over the single best cell. | Reduces sharp-peak selection bias. |
| 16 | [FIX] | Made paired bootstrap mandatory for close internal rivals, not only for benchmark comparison. | This proved essential for distinguishing genuinely better candidates from noise. |
| 17 | [NEW] | Added trade-quality diagnostics as a mandatory evaluation block. | Similar Sharpe numbers can hide very different trade distributions, churn, and winner concentration. |
| 18 | [FIX] | Clarified that full-sample performance is descriptive only and cannot overrule weaker unseen-data robustness. | V4 said this implicitly; V5 makes the decision rule explicit. |
| 19 | [NEW] | Added an explicit complexity budget tied to layer count and tunable count. | Keeps the search from drifting toward hard-to-audit feature stacks. |
| 20 | [NEW] | Added a candidate-freeze requirement that records exact logic, calibration rules, and comparison set before reserve evaluation. | Prevents quiet post-hoc movement of the goalposts. |
| 21 | [NEW] | Added a rule for sparse reserve windows: if reserve activity is insufficient, the session must say so explicitly. | Avoids overclaiming from too little reserve evidence. |
| 22 | [REMOVE] | Removed the benchmark headline figures and benchmark appendix from the main prompt body. | Specific benchmark numbers create anchoring pressure before independent discovery. |
| 23 | [IMPROVE] | Replaced “How to Use Prior Research” with stronger operational rules in the new `Fresh Re-derivation Rules` section. | V4 allowed too much room for implicit narrowing from prior specifics. |
| 24 | [NEW] | Added the `Fresh Re-derivation Rules` section immediately after the protocol. | This installs anti-leakage behavior before any methodological priors are read. |
| 25 | [NEW] | Added the `Meta-knowledge from Prior Research` section at the end of the file. | Preserves methodological lessons while minimizing anchoring from primacy effects. |
| 26 | [FIX] | Rewrote the philosophy section to reward evidence over novelty and evidence over resemblance. | Prior work showed both novelty bias and anti-resemblance bias are harmful. |
| 27 | [NEW] | Added an explicit rule that practical refinement, if attempted, must remain limited and must be justified against the simpler frozen core before reserve. | Keeps practical enhancements from becoming uncontrolled retuning. |
| 28 | [REMOVE] | Kept contamination disclosure out of V5. | Specific contaminated ranges and prior chosen parameters belong in a separate document so the new session can begin clean. |
| 29 | [FIX] | Expanded the anti-pattern list to forbid using the reserve window to break ties and to forbid consulting prior specific results before freeze. | These were important failure modes not stated sharply enough in V4. |
| 30 | [IMPROVE] | Tightened the deliverables so the session must output both the frozen specification and the evidence label, plus reserve status. | Makes the final output auditable and honest even when clean OOS proof is unavailable. |