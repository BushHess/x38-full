# Final Resolution — Philosophy & Mission Claims

**Topic ID**: X38-T-07
**Opened**: 2026-03-22
**Closed**: 2026-03-23
**Rounds**: 4 (of 6 max)
**Participants**: claude_code (author), codex (reviewer)

**§14b Round asymmetry note**: 4 claude_code rounds vs 3 codex rounds.
Acceptable because: D-01, D-20, D-25 all reached Converged in R2 (before the
asymmetry). D-22 required R3 for §7 completion — claude_code submitted R3
author-reply with the steel-man, codex confirmed in R3 reviewer-reply. R4
(claude_code only) is a final acknowledgment that all 4 issues converged; it
introduces no new arguments and no issue status depends on it. All convergences
were confirmed by codex before R4 was written.

---

## Summary

Topic 007 debated 4 findings (F-01, F-20, F-22, F-25) covering the philosophical
foundation and claim model that all other x38 topics depend on.

- **Rounds 1-2**: All four issues debated. D-01, D-20, D-25 reached Converged
  (full §7 path completed in R2).
- **Rounds 3-4**: D-22 completed the §7 path (steel-man in R3 author, confirmed
  by Codex in R3 reviewer). R4 acknowledged final convergence.

**Final tally**: 4 Converged, 0 Judgment call, 0 Open. All issues resolved.

---

## Decisions

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| X38-D-01 | F-01 keeps the philosophical invariant; cross-tier ladder stays in F-20 | Accepted (narrowed) | Converged | 2 |
| X38-D-20 | Mission is charter framing; Campaign and Certification are the two formal verdict tiers | Accepted (modified) | Converged | 2 |
| X38-D-22 | Freeze 3-type evidence ladder; surface same-archive contradiction explicitly; keep below certification; leave subtype taxonomy open | Accepted (modified) | Converged | 3 |
| X38-D-25 | Allow evidence-backed internal conditional logic inside one frozen policy; forbid per-regime parameter tables, external classifiers, post-freeze switching | Accepted (modified) | Converged | 2 |

---

## Key design decisions (for drafts/)

### Decision 1: Philosophy invariant — inherit methodology, not answers

**Accepted position**: F-01 is a philosophical statement bounding framework
promises: find the strongest candidate WITHIN the declared search space, or
honestly conclude `NO_ROBUST_IMPROVEMENT`. It is not self-executing — it requires
operationalization through the contamination firewall (C-10) and other mechanisms.

**Rejected alternative**: Embedding the mission/operational split directly into
F-01 as a single source of truth. Rejected because F-20 already owns the formal
tier semantics, and C-10 already bounds F-01 to a non-self-executing statement.

**Rationale**: `docs/design_brief.md:24-30`, `PLAN.md:209-217` define the bounded
promise. `debate/000-framework-proposal/findings-under-review.md:32-35` (C-10)
establishes F-01 depends on firewall. Duplicating the tier ladder inside F-01
would create parallel authority.

### Decision 2: 3-tier claim separation

**Accepted position**: Three tiers, two of which bear verdicts:
- **Mission**: Charter framing ("find the best algorithm"). Named in prose.
  No verdict — it is an ongoing aspiration, not an evidence-bearing state.
- **Campaign**: Strongest leader within declared search space. Verdicts:
  `INTERNAL_ROBUST_CANDIDATE` or `NO_ROBUST_IMPROVEMENT`.
- **Certification**: Winner confirmed by independent evidence (Clean OOS).
  Verdicts: `CLEAN_OOS_CONFIRMED` / `CLEAN_OOS_INCONCLUSIVE` / `CLEAN_OOS_FAIL`.

**Rejected alternative**: Including Mission as a verdictless row in the formal
verdict table. Rejected because the verdict table models evidence-bearing claim
states; a verdictless row mixes non-verdict framing with evidence states.

**Rationale**: `PLAN.md:7-11` is charter language. Verdict-bearing states live in
research and Clean OOS outputs (`PLAN.md:35-37`, `PLAN.md:51-60`,
`PLAN.md:454-478`). `PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-81` [extra-archive]
distinguishes clean-OOS eligibility from confirmation.

### Decision 3: Phase 1 evidence taxonomy on exhausted archives

**Accepted position**: Three evidence types frozen:
1. **Coverage/process** (same-archive): "50K+ features scanned, all converge on
   D1 slow family."
2. **Deterministic convergence** (same-archive): "N deterministic sessions produce
   same leader."
3. **Clean adjudication** (new data): Requires appended data (Phase 2).

Semantic rule: if same-archive search (of either type) contradicts the historical
lineage, the artifact MUST surface that contradiction explicitly and keep it below
certification tier.

Sub-type taxonomy within same-archive categories is NOT frozen — dimensions remain
open for consuming topics (001, 010) to define as needed.

**Rejected alternative**: Encoding confirmation/divergence as formal sub-types
within coverage/process evidence. Rejected because confirmation/divergence is an
orthogonal polarity that cross-cuts both same-archive categories (a campaign can
deterministically converge on a different family — simultaneously
deterministic-convergence AND lineage divergence). Encoding it in one category
models the wrong semantic axis.

**Rationale**: `debate/007-philosophy-mission/findings-under-review.md:118-147`
defines the three categories by evidence source and claim ceiling. `PLAN.md:497-510`
keeps same-archive outputs below Clean OOS.
`x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:126-145` [extra-archive]
states same-file audit can clarify family convergence but not the scientific claim.

### Decision 4: Regime-aware policy structure

**Accepted position**: A single frozen policy object MAY contain evidence-backed
internal conditional logic (e.g., D1 EMA regime filter). Forbidden:
- Per-regime parameter tables
- External framework-provided regime classifiers
- Post-freeze winner switching between regime-specific sub-strategies

**Rejected alternative**: Bright-line ban on all regime-aware structure (stationary
only). Rejected because: (1) V8 bans regime-specific parameter sets, not all
internal conditional logic (`RESEARCH_PROMPT_V8.md:469-477` [extra-archive]);
(2) V8 explicitly permits layered mechanisms with paired evidence
(`RESEARCH_PROMPT_V8.md:312-331` [extra-archive]); (3) the current BTC archive
already contains a frozen policy with internal regime logic (E5_ema21D1 with D1
EMA(21) filter — removing it reduces Sharpe from 1.4545 to 1.0912).

**Rationale**: `DEPLOYMENT_CHECKLIST.md:4-18` [extra-archive] defines E5_ema21D1.
`MONITOR_V2_VALIDATION_REPORT.md:89-98` [extra-archive] quantifies regime filter
value. The blanket ban overreads V8 and misdescribes already-supported policy
structure.

---

## Unresolved tradeoffs (for human review)

No unresolved tradeoffs. All 4 issues reached genuine convergence (§7 complete).

The following items are deferred to downstream topics by design, not by
disagreement:

- **F-20 naming**: Exact terminology (Mission/Campaign/Certification vs
  alternatives) was not frozen — only the semantic structure. Naming may be
  revisited when `architecture_spec.md` is drafted.
- **F-22 investigation protocol**: What happens when same-archive search
  contradicts historical lineage (routing, escalation, judgment) is owned by
  topics 001 (campaign model) and 010 (clean OOS certification).
- **F-25 ablation gate strictness**: The boundary (internal conditional logic
  allowed, external classifiers forbidden) is frozen. Specific ablation gate
  thresholds for testing regime-aware structures belong to topic 003 (protocol
  engine).

---

## Cross-topic tensions (final state)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 001 (campaign-model) | X38-D-03 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be a valid campaign exit | 001 owns decision; 007 provides constraint |
| 002 (contamination-firewall) | X38-D-04 | C-10: F-01 operationalization depends on firewall | 002 owns decision; 007 provides constraint |
| 003 (protocol-engine) | X38-D-05 | F-25 regime prohibition constrains protocol stages — internal conditional logic allowed, per-regime tables forbidden | 003 owns decision; 007 provides constraint |
| 004 (meta-knowledge) | MK-17 | MK-17 shadow-only prerequisite for F-01 interpretation. CLOSED | shared — see C-02 |
| 010 (clean-oos-certification) | X38-D-12, X38-D-21 | F-22 + F-20 define Phase 1 vs. Certification boundary. Divergence investigation protocol owned by 001/010 | 001 + 010 shared ownership; 007 provides taxonomy + semantic rule |

---

## Draft impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `architecture_spec.md` | 3-tier claim model (F-20), evidence taxonomy (F-22), regime policy constraint (F-25), campaign stop conditions (F-01→F-03) | Create sections when upstream topics (001, 008, 010) also close |
| `meta_spec.md` | Philosophy statement (F-01), firewall interplay (C-10) | Create section when topic 002 also closes |
| `protocol_spec.md` | Regime-aware ablation gate (F-25→F-05), evidence type routing (F-22) | Create sections when topic 003 closes |
