# F-06 Category Coverage Investigation

**Date**: 2026-03-23
**Author**: claude_code (investigation), human researcher (commission)
**Purpose**: Pre-debate input for Topic 002. Tests whether F-04's 4 whitelist
categories cover the actual V4-V8 meta-knowledge inventory.
**Status**: Read-only reference (not authority per `debate/prompt_template.md`)
**Triggered by**: MK-07 audit — interim rule "ambiguous -> non-admissible" found
to be under-specified and potentially wrong-direction for structural priors.

---

## 1. Background

Topic 004 (CLOSED) established:
- **MK-07**: F-06 categories (content filter) are orthogonal to 3-tier taxonomy
  (governance filter). Two independent dimensions.
- **MK-07 interim rule**: "ambiguous category mapping -> non-admissible pending
  human review. No force-fitting."
- **MK-02 Harm #3**: Implicit data leakage through structural rules is
  irreducible — data-derived lessons become universal-looking methodology.

Topic 002 / F-04 defines 4 whitelist categories (`findings-under-review.md:41-49`):
1. `PROVENANCE_AUDIT_SERIALIZATION`
2. `SPLIT_HYGIENE`
3. `STOP_DISCIPLINE`
4. `ANTI_PATTERN`

F-04 already asks (`findings-under-review.md:78`): "Typed schema co qua
restrictive? Lesson hop le nhung khong fit categories?"

**This investigation answers that question with data.**

---

## 2. Method

Inventory all transferable rules/lessons from V4-V8 / x37. Map each to
F-06 categories. Classify results as:
- **Clean**: exactly one category fits naturally
- **Ambiguous**: multiple categories fit plausibly
- **Gap**: no category fits without stretching

Sources searched (10):
1. V5 meta-knowledge (17 lessons) — `x37/docs/gen1/RESEARCH_PROMPT_V5/RESEARCH_PROMPT_V5.md:350-378` [extra-archive]
2. V6 meta-knowledge (8 lessons) — `x37/docs/gen1/RESEARCH_PROMPT_V6/RESEARCH_PROMPT_V6.md:436-447` [extra-archive]
3. V7 meta-knowledge (4 lessons) — `x37/docs/gen1/RESEARCH_PROMPT_V7/RESEARCH_PROMPT_V7.md:579-586` [extra-archive]
4. V8 meta-knowledge (5 lessons) — `x37/docs/gen1/RESEARCH_PROMPT_V8/RESEARCH_PROMPT_V8.md:635-643` [extra-archive]
5. V8 Handoff transfer principles (5) — `x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` [extra-archive]
6. Convergence Status governance lessons (8) — `x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` [extra-archive]
7. V6/V7 spec patterns + gaps (18) — `docs/v6_v7_spec_patterns.md`
8. Gen3/Gen4 meta-knowledge registries (7 transferable) — `x37/docs/gen3/report/` and `x37/docs/gen4/report/` [extra-archive]
9. V8 protocol absorbed rules (4+) — traced from MK-02 references
10. Topic 004 governance rules (for completeness; these are META-rules, not F-06 subjects)

---

## 3. Inventory Summary

**Total transferable rules found**: ~75 (inventoried in appendix; additional V5
evaluation/data-split bullets exist but are omitted as they map cleanly to
existing categories and do not affect the gap analysis)

| Category fit | Count | Percentage |
|---|---|---|
| **Clean** (exactly 1 category) | ~60 | ~80% |
| **Gap** (no category fits) | ~10 | **~13%** |
| **Ambiguous** (multiple fit) | ~5 | ~7% |

---

## 4. Clean-Fit Distribution

| F-06 Category | Clean-fit count | Examples |
|---|---|---|
| `PROVENANCE_AUDIT_SERIALIZATION` | ~23 | Lookahead prohibition (T1-1), seed serialization (V8-2), protocol freeze (G-02), provenance declaration (P-08), export manifests (V6-6) |
| `ANTI_PATTERN` | ~23 | Ablation as gate (V5-15), coarse-before-fine (V5-13), redundancy pruning (V5-14), complexity not proven superior (T2-3), delay enhancements until core exists (V5-16) |
| `SPLIT_HYGIENE` | ~9 | Reserve != clean OOS (CS-2), within-file = stress slice only (CS-1), split-chasing (V8-4), blind != independent (CS-3), denser slicing (V6-8) |
| `STOP_DISCIPLINE` | ~3 | Same-file iteration limit (V7-2), reserve cannot retroactively promote (V8-5), same-file scientific productivity exhausted (CS-8) |

**Observation**: `PROVENANCE_AUDIT_SERIALIZATION` and `ANTI_PATTERN` are heavily
loaded (~25+ each). `STOP_DISCIPLINE` is thin (3 rules). Distribution is
unbalanced but functional for clean-fit rules.

---

## 5. Gap Rules — The Core Finding

**~10 rules fit NO category without stretching.** These are all **Tier 2
structural priors**: empirical observations from V4-V8 BTC data that have been
elevated to methodology-sounding principles.

### 5.1 Complete List of Gap Rules

| ID | Rule (abbreviated) | Source | Why no category fits |
|---|---|---|---|
| V5-3 | "Slower directional context and faster state persistence complement each other" | V5 meta-knowledge | Empirical observation about BTC price structure. Not an anti-pattern (doesn't say "don't do X"). Not audit/split/stop. |
| V5-4 | "Flow information may improve selection but not be main engine" | V5 meta-knowledge | Empirical observation about BTC order flow signal strength. |
| V5-6 | "Multi-TF: slower = whether to accept risk, faster = timing and churn" | V5 meta-knowledge | Partially principled (separation of concerns), partially BTC-derived (slower/faster TF role assignment). |
| V6-2 | "Layering is a hypothesis, not a default" | V6 meta-knowledge | Half Occam's razor (axiom — would be `ANTI_PATTERN`), half V4-V5 BTC evidence that multi-layer didn't help. |
| T2-1 | "Layering is a hypothesis to be justified by measured edge" | Gen3/Gen4 registry | Same as V6-2. Formalized in registry as Tier 2 structural prior. |
| T2-2 | "Microstructure excluded from mainline swing horizon" | Gen3/Gen4 registry | Scope/budget decision — not methodology, not anti-pattern, not audit. Defines what search space excludes. |
| CS-6 | "Complexity has not proven stable superiority" | Convergence Status V3 | Pure empirical observation from 5 V4-V8 sessions. Not generalizable as axiom — might not hold on other assets or data periods. |
| A-1 | "Transported clone needs incremental paired evidence" | V8 protocol (absorbed from V6) | Partially valid methodology (test claims properly), partially V4/V5 BTC-specific experience (D1 EMA transport looked good but restated D1 info). |
| A-2 | "14 quarterly folds" as discovery default | V8 protocol | Pure data-derived: quarterly slicing works for BTC. Monthly or yearly might suit other assets. |
| P-09 | "Default quarterly fold, isolation-quarter filter" | V6/V7 spec patterns | Same as A-2. Partially principled (more folds = less dependence), partially BTC-specific. |

### 5.2 Why These Rules Matter

These are not edge cases. They are the **Tier 2 structural priors** — the most
dangerous rules identified in MK-02 Harm #3 ("information laundering"):

> "data-specific lessons become universal-looking rules. A new AI cannot
> distinguish genuine methodology from data-derived heuristics."
> (`004-meta-knowledge/findings-under-review.md:114-116`)

They are the exact rules the firewall must handle with the most care.

### 5.3 Common Properties

All gap rules share:
- **Empirical content**: derived from observing BTC data (V4-V8 experience)
- **Methodology disguise**: phrased as general principles
- **Not blockable**: they SHOULD be admitted (with Tier 2 + SHADOW governance), not rejected
- **No F-06 home**: stretching `ANTI_PATTERN` to fit them destroys discriminating power

---

## 6. Ambiguous Rules (~5)

| ID | Rule | Categories that fit | Type of ambiguity |
|---|---|---|---|
| A-1 | "Transported clone needs incremental evidence" | `ANTI_PATTERN` + gap (structural prior) | Content spans methodology AND empirical |
| V6-2 / T2-1 | "Layering is hypothesis" | `ANTI_PATTERN` + gap (structural prior) | Content spans axiom AND experience |
| P-09 | "Quarterly fold default" | `SPLIT_HYGIENE` + gap (data-derived) | Content spans hygiene AND BTC-specific |
| V5-6 | "Slower = whether, faster = timing" | `ANTI_PATTERN` + gap (structural prior) | Separation of concerns + BTC observation |
| V8-3 | "Mixed-TF needs common daily-return domain" | `PROVENANCE_AUDIT_SERIALIZATION` (primary) + `SPLIT_HYGIENE` (secondary) | Clean primary, weak secondary |

**Observation**: 4 of 5 ambiguous rules are ALSO gap rules. The ambiguity is
between a forced-fit into an existing category and recognition that no category
is adequate. Only V8-3 is genuinely ambiguous between two valid categories
(PROVENANCE vs SPLIT).

---

## 7. MK-07 Interim Rule Problem

Current MK-07 interim rule: "ambiguous -> non-admissible pending human review."

Applied to the gap rules:

1. Implementer encounters V5-3 ("slower context + faster persistence complement")
2. Tries to map to 4 categories — does not fit
3. Declares "ambiguous" -> non-admissible -> rule blocked
4. Human reviews -> **no category to assign** (force-fitting is prohibited by MK-07)
5. Rule stuck in limbo: cannot be admitted, cannot be assigned

**This is the wrong outcome.** These rules should be:
- **Admitted** (they contain real methodology content, not pure answer priors)
- **Governed** as Tier 2 + SHADOW (per MK-17, same-dataset priors are shadow-only)
- **Tagged** with explicit provenance (per MK-01, no implicit absorption)

The interim rule blocks rules that should flow through. The fail-closed
assumption (ambiguous = probably contamination) is wrong for structural priors
(ambiguous = mixed content, needs careful governance, not rejection).

---

## 8. Root Cause Analysis

The 4 F-06 categories were designed for a **binary** world:

- **ALLOWED**: methodology rules that any researcher could derive independently
  (provenance, splits, stops, anti-patterns)
- **BLOCKED**: data-derived specifics (features, thresholds, winner identity)

But MK-02 Harm #3 proved the world is **not binary**. There exists a third
class: **empirical lessons elevated to principles** — rules that are partially
derivable from first principles and partially informed by data experience.

The 4 categories cover the ALLOWED side well (~65 rules). The BLOCKED side is
handled by schema validation (features, thresholds, parameters are caught by
typed schema, not by category). But the **middle ground** — structural priors
with mixed content — has no F-06 home.

```
ALLOWED (methodology)       MIDDLE (structural priors)     BLOCKED (answer priors)
├─ PROVENANCE_AUDIT         ├─ V5-3 (TF roles)            ├─ feature names
├─ SPLIT_HYGIENE            ├─ V6-2 (layering)            ├─ lookback values
├─ STOP_DISCIPLINE          ├─ T2-2 (scope/budget)        ├─ thresholds
└─ ANTI_PATTERN             ├─ CS-6 (complexity)          ├─ winner identity
                            └─ ... (~10 rules)            └─ shortlist priors
    4 categories cover          NO CATEGORY                  Schema validation
    ~65 rules cleanly           ~10 rules homeless           catches these
```

---

## 9. Findings for Topic 002 Debate

### Finding A: F-06 categories have a structural gap for Tier 2 priors

The 4 categories cover ~80% of actual V4-V8 rules. The remaining ~12% are
Tier 2 structural priors that have no category home. These are not edge cases
— they are the rules MK-02 identified as the most dangerous (information
laundering) and therefore require the most careful firewall handling.

**Evidence**: 10 specific rules listed in §5.1, all from V4-V8 evidence base.

**Question for debate**: Should F-06 add a 5th category (e.g.,
`STRUCTURAL_PRIOR` or `EMPIRICAL_METHODOLOGY`) for rules with mixed
first-principles and data-derived content? Or should the existing categories
be redefined to accommodate them?

### Finding B: MK-07 interim rule blocks rules that should be admitted

"Ambiguous -> non-admissible" is wrong-direction for structural priors. These
rules should be admitted with Tier 2 + SHADOW governance, not blocked.

**Evidence**: Walkthrough in §7 — implementer cannot resolve gap rules under
current interim rule without violating MK-07's own no-force-fit constraint.

**Question for debate**: What should the interim rule be for rules that don't
fit any category? Options:
- (a) Admit with `UNCLASSIFIED` tag + mandatory Tier 2 + SHADOW (permissive)
- (b) Reject until Topic 002 expands categories (strict, current direction)
- (c) Admit provisionally with human-assigned ad-hoc category + review flag

### Finding C: STOP_DISCIPLINE may be too thin to justify a dedicated category

Only 3 rules map cleanly to `STOP_DISCIPLINE`. All 3 could also fit
`ANTI_PATTERN` (stopping too late = anti-pattern) or `SPLIT_HYGIENE` (stopping
after seeing results = split violation). This is not blocking — 3 rules is
small enough to absorb. But debate should consider whether 4 categories is the
right number or whether consolidation + expansion serves better.

**Evidence**: V7-2, V8-5, CS-8 are the only clean STOP_DISCIPLINE rules.

### Finding D: PROVENANCE_AUDIT_SERIALIZATION is overloaded

~25+ rules in one category. This category covers: data provenance, audit
trails, serialization formats, session independence, export manifests, hash
verification, freeze protocols, and comparison conventions. These are related
but operationally distinct concerns. An implementer mapping a new rule to this
category has no discriminating power — almost any infrastructure rule "fits."

**Question for debate**: Should `PROVENANCE_AUDIT_SERIALIZATION` be split into
finer-grained categories? This affects discriminating power but increases
classification burden.

---

## 10. Implications for MK-07 Amendment

Based on this investigation, MK-07's addendum in Topic 004's
`final-resolution.md` should be amended to:

1. **Replace** "ambiguous -> non-admissible" with a rule that distinguishes
   GAP (no category fits) from AMBIGUITY (multiple categories fit)
2. **For gaps**: flag for Topic 002 category expansion; do not block rules that
   pass the tier/governance filter (MK-05, MK-17)
3. **For ambiguity**: existing fail-closed default can remain (multiple
   plausible categories means the content is within F-06's scope — the question
   is which category, not whether to admit)

The specific amendment text depends on Topic 002's debate outcome. If Topic 002
adds a `STRUCTURAL_PRIOR` category, the gap disappears. If not, MK-07 needs a
permanent governance procedure for unmappable rules.

---

## Appendix: Full Rule Inventory

### A.1 V5 Meta-Knowledge (16 rules)

| ID | Rule | Category | Fit |
|---|---|---|---|
| V5-1 | Distinguish context, state, and entry confirmation — different jobs | ANTI_PATTERN | Clean |
| V5-2 | Each information type in its natural role, not forced to do everything | ANTI_PATTERN | Clean |
| V5-3 | Slower directional context + faster state persistence complement | — | **Gap** |
| V5-4 | Flow info may improve selection but not be main engine | — | **Gap** |
| V5-5 | If signal improves entries but weakens holds, keep in entry-only | ANTI_PATTERN | Clean |
| V5-6 | Multi-TF: slower = whether, faster = timing/state/churn | — | **Gap** |
| V5-7 | Faster layers look better in-sample but become chop | ANTI_PATTERN | Clean |
| V5-8 | Cross-TF alignment is first-class scientific issue | PROVENANCE_AUDIT | Clean |
| V5-9 | Real edge survives multiple views (WFO, holdout, bootstrap, ...) | ANTI_PATTERN | Clean |
| V5-10 | Artifact signatures: parameter spikes, weak OOS, outsized winners, churn | ANTI_PATTERN | Clean |
| V5-11 | Nearby transforms all working = stronger than one isolated winner | ANTI_PATTERN | Clean |
| V5-12 | Single-feature executable systems tested early | ANTI_PATTERN | Clean |
| V5-13 | Coarse search before refinement | ANTI_PATTERN | Clean |
| V5-14 | Redundancy pruning early | ANTI_PATTERN | Clean |
| V5-15 | Ablation as gate, not cosmetic appendix | ANTI_PATTERN | Clean |
| V5-16 | Delay enhancements until clean core exists | ANTI_PATTERN | Clean |

(V5-3,4,6 in §5.1 footnote: partially principled, partially BTC-derived.)

### A.2 V6 Meta-Knowledge (8 rules)

| ID | Rule | Category | Fit |
|---|---|---|---|
| V6-1 | Layer must prove incremental info, not higher-freq restatement | ANTI_PATTERN | Clean |
| V6-2 | Layering is hypothesis, not default | — | **Gap** (axiom + BTC experience) |
| V6-3 | Evaluate native faster-TF vs transported slower-TF separately | PROVENANCE_AUDIT | Clean |
| V6-4 | Preserve one simple representative from each viable family cluster | ANTI_PATTERN | Clean |
| V6-5 | Session not clean if it imports prior tables before generating own evidence | PROVENANCE_AUDIT | Clean |
| V6-6 | Export full scan manifest, grids, ledger, keep/drop reasons | PROVENANCE_AUDIT | Clean |
| V6-7 | Summary tables generated inside session from raw data | PROVENANCE_AUDIT | Clean |
| V6-8 | Denser chronological slicing more informative than few coarse windows | SPLIT_HYGIENE | Clean |

### A.3 V7 Meta-Knowledge (4 rules)

| ID | Rule | Category | Fit |
|---|---|---|---|
| V7-1 | Later same-file sessions not automatically better | ANTI_PATTERN | Clean |
| V7-2 | Same-file editing is search dimension; freeze + explicit stop | STOP_DISCIPLINE | Clean |
| V7-3 | Divergent winners = frontier instability, record not reconcile | ANTI_PATTERN | Clean |
| V7-4 | Internal reserve useful for contradiction, not independent proof | SPLIT_HYGIENE | Clean |

### A.4 V8 Meta-Knowledge (5 rules)

| ID | Rule | Category | Fit |
|---|---|---|---|
| V8-1 | Blind-per-procedure != independent-per-data, report separately | PROVENANCE_AUDIT | Clean |
| V8-2 | Seed + resample config = part of frozen protocol | PROVENANCE_AUDIT | Clean |
| V8-3 | Mixed-TF needs common daily-return domain + segment convention | PROVENANCE_AUDIT_SERIALIZATION | **Ambiguous** (primary PROVENANCE, secondary SPLIT_HYGIENE) |
| V8-4 | Changing split after seeing results = split-chasing | SPLIT_HYGIENE | Clean |
| V8-5 | Reserve cannot retroactively promote different winner | STOP_DISCIPLINE | Clean |

### A.5 Handoff Transfer Principles (5 rules)

| ID | Rule | Category | Fit |
|---|---|---|---|
| H-1 | Transfer only meta-knowledge, NOT data-derived specifics | PROVENANCE_AUDIT | Clean |
| H-2 | Later iterations not automatically better | ANTI_PATTERN | Clean |
| H-3 | Prior sessions' results not assumed more correct | ANTI_PATTERN | Clean |
| H-4 | Divergence not reconciled by construction | ANTI_PATTERN | Clean |
| H-5 | No import of prior candidates, shortlists, parameter regions | PROVENANCE_AUDIT | Clean |

### A.6 Convergence Status Governance (8 rules)

| ID | Rule | Category | Fit |
|---|---|---|---|
| CS-1 | Within-file reserve = internal stress slice only | SPLIT_HYGIENE | Clean |
| CS-2 | Same-file prompt tightening != clean OOS | SPLIT_HYGIENE | Clean |
| CS-3 | Blind-per-procedure != independent-per-data | SPLIT_HYGIENE | Clean |
| CS-4 | Redesign after holdout/reserve increases contamination | ANTI_PATTERN | Clean |
| CS-5 | 5 sessions, 5 different winners = frontier instability | ANTI_PATTERN | Clean |
| CS-6 | Complexity has not proven stable superiority | — | **Gap** (empirical observation) |
| CS-7 | No within-file clean OOS remains | SPLIT_HYGIENE | Clean |
| CS-8 | Same-file iteration beyond V8 has no scientific productivity | STOP_DISCIPLINE | Clean |

### A.7 Gen3/Gen4 Registry — Transferable Rules (7 rules)

| ID | Rule | Category | Fit |
|---|---|---|---|
| T1-1 | No lookahead (signals use only info up to decision bar close) | PROVENANCE_AUDIT | Clean |
| T1-2 | All timestamps/splits/signals in UTC | PROVENANCE_AUDIT | Clean |
| T1-3 | Signals at bar close, executed at next bar open | PROVENANCE_AUDIT | Clean |
| T1-4 | No synthetic bar repair | PROVENANCE_AUDIT | Clean |
| T2-1 | Layering is hypothesis, not default (= V6-2) | — | **Gap** |
| T2-2 | Microstructure excluded from mainline swing horizon | — | **Gap** (scope/budget) |
| T2-3 | Prefer smallest defensible design | ANTI_PATTERN | Clean |

(10 Tier 3 session notes intentionally excluded — session-scoped, not transferable.)

### A.8 V6/V7 Spec Patterns (9 patterns + 9 gaps)

| ID | Rule | Category | Fit |
|---|---|---|---|
| P-01 | Anomaly register auto-created from data audit, locked before Stage 3 | PROVENANCE_AUDIT | Clean |
| P-02 | Feature engine: fixed schema, centralized threshold-grid, explicit tail semantics | PROVENANCE_AUDIT | Clean |
| P-03 | Bucket summary mandatory after Stage 1 | PROVENANCE_AUDIT | Clean |
| P-04 | All checklist gates with expected numeric value, auto-compare | PROVENANCE_AUDIT | Clean |
| P-05 | All decision rules must have numeric threshold, prose = docs only | ANTI_PATTERN | Clean |
| P-06 | Freeze before reserve; reserve confirms/contradicts, not tie-break | SPLIT_HYGIENE | Clean |
| P-07 | Auto-clone slower-TF to faster-TF, scan both, flag high-rho | ANTI_PATTERN | Clean |
| P-08 | Auto-provenance declaration, lock input list, record versions, runtime verify | PROVENANCE_AUDIT | Clean |
| P-09 | Quarterly fold default, isolation-quarter filter | SPLIT_HYGIENE | **Ambiguous** (partially BTC-derived) |
| G-01 | Seed frozen before bootstrap, saved in protocol_freeze.json | PROVENANCE_AUDIT | Clean |
| G-02 | frozen_spec.json mandatory, machine-parseable | PROVENANCE_AUDIT | Clean |
| G-03 | Fixed schema for pairwise comparison matrix | PROVENANCE_AUDIT | Clean |
| G-04 | Explicit function for mixed-TF daily UTC alignment | PROVENANCE_AUDIT | Clean |
| G-05 | Deterministic segment trade-count convention | PROVENANCE_AUDIT | Clean |
| G-06 | verdict.json with exactly 3 labels, machine-verifiable | PROVENANCE_AUDIT | Clean |
| G-07 | Benchmark specs physically inaccessible until reserve artifact exists | PROVENANCE_AUDIT | Clean |
| G-08 | Auto-compare frozen winners after N sessions | PROVENANCE_AUDIT | Clean |
| G-09 | Auto-propose structured lesson candidates after session close | PROVENANCE_AUDIT | Clean |

### A.9 Absorbed Protocol Rules (traced from MK-02)

| ID | Rule | Category | Fit |
|---|---|---|---|
| A-1 | Transported clone needs incremental paired evidence | — | **Gap** (methodology + V4/V5 BTC experience) |
| A-2 | 14 quarterly folds as discovery default | — | **Gap** (pure BTC-derived) |
| A-3 | Stage 3 binding: layering is hypothesis + 7 sub-rules | ANTI_PATTERN | Clean (but sub-rules may have gaps) |
| A-4 | Divergent same-file winners = frontier instability | ANTI_PATTERN | Clean |
