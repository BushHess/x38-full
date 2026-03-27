# Step 3 — Claude Code Mode C: Closure of Topic 018

Paste this prompt into a **Claude Code session** (architect role).
This is the main closure procedure — it modifies multiple files.

---

```
Role: Claude Code (architect / closure)
Mode: closure
Scope: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07,
       SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11
Topic: 018 — Search-Space Expansion

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` is the git root.

If this prompt conflicts with canonical x38 sources, canonical sources win.

═══════════════════════════════════════════════════════════════════
PREREQUISITES (verify before proceeding):
═══════════════════════════════════════════════════════════════════

1. ALL issues in scope: Converged or Judgment call ✅
   - 10 Converged: SSE-D-01, D-02/03, D-04, D-06, D-07, D-08, D-09, D-10, D-11
   - 1 Judgment call: SSE-D-05
2. Human researcher has decided SSE-D-05 ✅ (see JUDGMENT section below)
3. Round symmetry (§14b): both agents have 6 rounds ✅
   - claude_code: rounds 1-6 (6 files)
   - codex: rounds 1-6 (6 files)
4. Codex closure audit: check if codex/judgment-call-memo.md exists.
   If it does, read it. If not, proceed — audit was recommended, not mandatory.

═══════════════════════════════════════════════════════════════════
HUMAN RESEARCHER JUDGMENT — SSE-D-05 (BINDING)
═══════════════════════════════════════════════════════════════════

This is the human researcher's final decision. Apply it exactly as written.

    Type: Judgment call (Round 6)
    Decision: Hybrid — Reviewer correct on status (Judgment call, not
    Converged); Author correct on handoff value (named working minimum
    inventory needed for downstream consumption).

    NOTE (Judgment call, round 6): Authoritative evidence locks pre-freeze
    recognition topology and minimum 5+5 floor, but does not cleanly lock
    a single exact label set without drift. However, downstream Topics
    017/013 need named objects to write thresholds and proof-consumption
    semantics.

    Lựa chọn: Topic 018 adopts a working minimum inventory for handoff:
    - Pre-freeze recognition topology:
      surprise_queue → equivalence_audit → proof_bundle → freeze
    - 5 anomaly axes: decorrelation_outlier, plateau_width_champion,
      cost_stability, cross_resolution_consistency, contradiction_resurrection
    - 5 proof components: nearest_rival_audit, plateau_stability_extract,
      cost_sensitivity_test, dependency_stressor, contradiction_profile
    - Proof item 4: family-level name = dependency_stressor;
      ablation_or_perturbation_test is valid alias/concrete form
    - NOT described as immutable historically-converged exact label set
    - Topology stops at freeze — does NOT include post-freeze extensions
      (freeze_comparison_set → candidate_phenotype → contradiction_registry)
    - Thresholds and proof-consumption rules: 017/013 own
    - Expansion beyond this minimum: requires explicit downstream finding

    Lý do: Archive evidence shows material label drift (4→5 dimensions,
    component 4 naming inconsistency, ChatGPT Pro deferred exact taxonomy
    downstream). Pure Converged overstates convergence. Pure unnamed family
    is operationally too weak for 017/013 handoff. Hybrid gives named
    working minimum at Judgment call authority level.

    Decision owner: human researcher

═══════════════════════════════════════════════════════════════════
OVERRIDE NOTES (special handling for reopened topic)
═══════════════════════════════════════════════════════════════════

A. FINAL-RESOLUTION.MD — REPLACE, DO NOT SYNC
   The existing `final-resolution.md` is NON-AUTHORITATIVE (prior 4-agent
   extra-canonical debate, marked ⚠️). Create a completely NEW document
   using Template D from `debate/prompt_template.md`. Do NOT sync with or
   preserve content from the old file. The old file's decisions are INPUT
   EVIDENCE only.

B. CLOSURE-AUDIT.MD — MARK AS SUPERSEDED
   The existing `closure-audit.md` covers the prior 4-agent debate and is
   STALE. Add a header note: "SUPERSEDED by standard 2-agent debate closure
   (2026-03-27). This file documents the prior extra-canonical audit only."
   If `codex/judgment-call-memo.md` exists, reference it as the current
   audit document.

C. FINDINGS-UNDER-REVIEW.MD — UPDATE HEADER + ALL ISSUES
   Current header says "0/10 debated under x38 rules" and "All issues Open."
   Update to reflect: 10/10 debated, 6 rounds completed, all resolved
   (10 Converged + 1 Judgment call).
   Update each issue's `current_status` field.

D. DEBATE ROUND COUNTS
   The standard 2-agent debate produced 12 round artifacts (6 per side).
   Global counts to update:
   - Standard debate rounds: 64 + 12 = 76
   - Topics closed: 6 + 1 = 7
   - Topics remaining: 12 - 1 = 11 (all OPEN, 0 REOPENED)
   - 018's 28 extra-canonical rounds are STILL not counted as standard

E. DISCOVERY_SPEC.MD — CREATE NEW
   `drafts/discovery_spec.md` does not exist yet. Create it as the primary
   target for Topic 018's design decisions (bounded ideation, surprise lane,
   APE). Also update `drafts/README.md` to list it.

═══════════════════════════════════════════════════════════════════
READ ORDER (before writing anything)
═══════════════════════════════════════════════════════════════════

Mandatory reads:
  1. AGENTS.md, docs/online_vs_offline.md
  2. x38_RULES.md, debate/rules.md, debate/prompt_template.md (Template D)
  3. debate/018-search-space-expansion/README.md
  4. debate/018-search-space-expansion/findings-under-review.md
  5. debate/018-search-space-expansion/final-resolution.md (NON-AUTH input)
  6. debate/018-search-space-expansion/closure-audit.md (STALE input)
  7. ALL claude_code/ round files (1-6) in topic dir
  8. ALL codex/ round files (1-6) in topic dir
  9. codex/judgment-call-memo.md (if exists — closure audit)
  10. debate/017-epistemic-search-policy/findings-under-review.md
  11. debate/debate-index.md
  12. EXECUTION_PLAN.md (sections: Topic 018, summary/counts, critical path)
  13. PLAN.md (sections mentioning Topic 018)
  14. drafts/README.md
  15. drafts/architecture_spec.md (current state, for Step 4)

═══════════════════════════════════════════════════════════════════
STEP 1 — CREATE NEW `final-resolution.md`
═══════════════════════════════════════════════════════════════════

Path: debate/018-search-space-expansion/final-resolution.md
Action: OVERWRITE existing non-authoritative file.
Format: Template D from prompt_template.md.

Header:
  # Final Resolution — Search-Space Expansion
  **Topic ID**: X38-T-18
  **Closed**: 2026-03-27
  **Rounds**: 6
  **Participants**: claude_code, codex
  **Prior debate**: 4-agent extra-canonical (7 rounds, input evidence only)

Decisions table — 11 rows:
  | Issue ID  | Finding | Resolution | Type | Round closed |
  | SSE-D-01  | Pre-lock generation lane ownership | Accepted | Converged | 2 |
  | SSE-D-02  | Bounded ideation (4 hard rules) | Accepted | Converged | 2 |
  | SSE-D-03  | Grammar depth-1 seed + conditional registry_only | Accepted | Converged | 2 |
  | SSE-D-04  | 7-field breadth-activation contract | Accepted | Converged | 4 |
  | SSE-D-05  | Recognition stack: pre-freeze topology + named working minimum inventory | Modified (Judgment call) | Judgment call | 6 |
  | SSE-D-06  | Hybrid equivalence (structural + behavioral, no LLM) | Accepted | Converged | 4 |
  | SSE-D-07  | 3-layer lineage semantic split | Accepted (routed → 015) | Converged | 2 |
  | SSE-D-08  | Contradiction registry: shadow-only, storage → 015, consumption → 017 | Accepted (routed → 015/017) | Converged | 2 |
  | SSE-D-09  | Multiplicity control coupling via SSE-D-04 field 5 | Accepted (routed → 013) | Converged | 3 |
  | SSE-D-10  | Domain-seed = optional provenance hook, no replay | Accepted | Converged | 2 |
  | SSE-D-11  | APE v1 = template parameterization only | Accepted | Converged | 3 |

Key design decisions section — write one subsection per decision:
  1. Lane ownership fold (SSE-D-01)
  2. Bounded ideation rules + cold-start activation (SSE-D-02/03)
  3. Breadth-expansion 7-field interface contract (SSE-D-04)
  4. Surprise lane recognition topology + working minimum inventory (SSE-D-05)
     — Include the full judgment call text from HUMAN RESEARCHER JUDGMENT above
  5. Hybrid equivalence method (SSE-D-06)
  6. 3-layer lineage semantic split (SSE-D-07, routed → 015)
  7. Contradiction memory: shadow-only (SSE-D-08, routed → 015/017)
  8. Multiplicity control coupling (SSE-D-09, routed → 013)
  9. Domain-seed hook provenance (SSE-D-10)
  10. APE v1 scope boundary (SSE-D-11)

  For each: Accepted position, Rejected alternative, Rationale (with evidence
  pointers to specific round files and line numbers).

Unresolved tradeoffs section:
  - SSE-D-05: Exact label set stability — named inventory adopted at Judgment
    call authority, not Converged. Future label changes require explicit finding.
  - Note: No other unresolved tradeoffs remain.

Cross-topic impact section:
  | Downstream topic | Routed from | Impact |
  | 006 (feature engine) | SSE-D-03 | generation_mode feeds registry acceptance |
  | 015 (artifact versioning) | SSE-D-07, SSE-D-08 | 3-layer lineage + contradiction storage |
  | 017 (epistemic search) | SSE-D-05, SSE-D-08-CON | Recognition topology + contradiction consumption |
  | 013 (convergence analysis) | SSE-D-09 | Multiplicity correction via SSE-D-04 field 5 |
  | 008 (architecture identity) | SSE-D-04 field 3 | identity_vocabulary routing |
  | 003 (protocol engine) | SSE-D-04 | breadth-activation blocker at protocol_lock |

Draft impact table:
  | Draft | Sections affected | Action needed |
  | discovery_spec.md | §1 Bounded ideation, §2 Recognition stack, §3 APE v1 | Create |
  | architecture_spec.md | §12 Breadth-expansion contract, §13 Lineage routing | Seed new sections |

═══════════════════════════════════════════════════════════════════
STEP 2 — UPDATE `findings-under-review.md`
═══════════════════════════════════════════════════════════════════

Path: debate/018-search-space-expansion/findings-under-review.md

Changes:
a. Header section:
   - Status line: change to "**CLOSED** (2026-03-27)"
   - Change "10 Open Issues" → "10 issues resolved (10 Converged + 1 Judgment call)"
   - Change "0/10 debated under x38 rules" → "10/10 debated, 6 rounds (standard 2-agent)"
   - Update "0 rounds completed" → "6 rounds completed (2026-03-27)"

b. Per-issue updates (use existing fields only, NO ad-hoc fields):
   - ALL issues: change `current_status: Open` → `Converged` (or `Judgment call` for SSE-D-05)
   - For SSE-D-05 specifically:
     * current_status: Judgment call
     * Update Resolution text to match the human researcher's judgment
   - For all other issues: current_status: Converged

c. Prior 4-Agent Outcomes table at bottom:
   - Add note: "Standard 2-agent debate (6 rounds, 2026-03-27) confirmed all
     prior outcomes. SSE-D-05 reclassified from Converged to Judgment call
     per human researcher decision."

d. Update "Current live status" line at bottom:
   - Change to: "10/10 issues resolved under standard x38 2-agent rules.
     10 Converged + 1 Judgment call. Topic CLOSED 2026-03-27."

═══════════════════════════════════════════════════════════════════
STEP 3 — UPDATE `debate-index.md` + topic `README.md`
═══════════════════════════════════════════════════════════════════

Path 1: debate/debate-index.md
Changes:
  - Topic 018 row: change status **REOPENED** → **CLOSED** (2026-03-27)
  - Update summary: "6 rounds (standard 2-agent). 10 Converged + 1 Judgment call.
    Downstream routing confirmed to 006/015/017/013/008/003."
  - Update totals: "19 topics (7 CLOSED, 1 SPLIT, 11 OPEN)"
    (was: 6 CLOSED, 1 REOPENED)
  - Remove or update REOPENED note about provisional routings → routings
    now confirmed
  - Update "Cập nhật" date line

Path 2: debate/018-search-space-expansion/README.md
Changes:
  - Status: change **REOPENED** → **CLOSED** (2026-03-27)
  - Update "Debate status" section:
    * "6 rounds completed (standard 2-agent, 2026-03-27)"
    * "10 Converged + 1 Judgment call (SSE-D-05)"
    * Reference final-resolution.md as authoritative
  - Update "Current status" line: "10/10 debated" → resolved
  - Governance note: mark prior 4-agent debate as "archived, superseded
    by standard 2-agent debate"

═══════════════════════════════════════════════════════════════════
STEP 3b — SYNC closure status across global files
═══════════════════════════════════════════════════════════════════

Path 1: EXECUTION_PLAN.md
Changes:
  - Topic 018 row: REOPENED → CLOSED (2026-03-27)
  - Debate rounds: 64 → 76 (add 12 standard rounds from 018)
  - Topics remaining: 12 → 11 (all OPEN, 0 REOPENED)
  - Remove "1 REOPENED" from counts
  - Critical path: mark 018 as ✅ (was: ← REOPENED)
  - Remove/update note about 018 extra-canonical rounds not counted:
    keep the note but add "standard 2-agent debate: 12 rounds counted"

Path 2: PLAN.md
  - Topic 018 entries: REOPENED → CLOSED
  - Summary status table: update counts (7 CLOSED, 11 OPEN)
  - Add closure reference blockquote near Topic 018 section:
    > **Closed 2026-03-27** — 6 rounds (standard 2-agent). 10 Converged +
    > 1 Judgment call (SSE-D-05). Discovery mechanisms distributed to
    > 006/015/017/013/008/003. Downstream routings confirmed.

Path 3: docs/evidence_coverage.md
  - Currently has NO Topic 018 references. Add a Topic 018 section if the
    file's structure warrants it, noting the evidence sources used:
    * Standard debate: 12 round files (claude_code + codex, R1-R6)
    * Extra-canonical archive: docs/search-space-expansion/debate/
    * Cross-topic evidence: 017 findings-under-review.md
  - If the file only covers topics through 012, add 018 at the appropriate
    position.

═══════════════════════════════════════════════════════════════════
STEP 3c — CHECK downstream unblocking
═══════════════════════════════════════════════════════════════════

Topic 018 closure confirms routings to 6 downstream topics.
Check EXECUTION_PLAN.md dependency notes for each:

  | Downstream | Routing | Status | Action |
  | 006 | SSE-D-03 generation_mode | OPEN | Update dep note: 018 ✅ |
  | 015 | SSE-D-07/08 lineage + contradiction | OPEN | Update dep note: 018 ✅ |
  | 017 | SSE-D-05 topology + SSE-D-08-CON | OPEN | Update dep note: 018 ✅ |
  | 013 | SSE-D-09 multiplicity control | OPEN | Update dep note: 018 ✅ |
  | 008 | SSE-D-04 identity_vocabulary | CLOSED | Already resolved (closed 2026-03-27) |
  | 003 | SSE-D-04 breadth-activation | OPEN | Update dep note: 018 ✅ |

For each OPEN downstream topic, add a note in EXECUTION_PLAN.md:
"Topic 018 CLOSED — SSE-D-{XX} routing confirmed. Actionable by this topic."

Also update debate-index.md note about provisional routings:
Change "provisional until 018 re-closes" → "confirmed (018 CLOSED 2026-03-27)"

═══════════════════════════════════════════════════════════════════
STEP 4 — CREATE/UPDATE draft specs in `drafts/`
═══════════════════════════════════════════════════════════════════

Path 1: drafts/discovery_spec.md — CREATE NEW
  This file does not exist yet. Create it with sections:

  §1 Bounded Ideation (SSE-D-02/03)
    - 4 hard rules: results-blind, compile-only, OHLCV-only, provenance-tracked
    - 2 generation modes: grammar_depth1_seed (default), registry_only (conditional)
    - Cold-start activation conditions
    - Trace: SSE-D-02, SSE-D-03 → final-resolution.md

  §2 Recognition Stack (SSE-D-05)
    - Pre-freeze topology: surprise_queue → equivalence_audit → proof_bundle → freeze
    - Working minimum inventory (Judgment call):
      * 5 anomaly axes (named)
      * 5 proof components (named)
      * dependency_stressor / ablation_or_perturbation_test alias note
    - Thresholds: deferred to 017/013
    - Expansion governance: explicit finding required
    - Trace: SSE-D-05 → final-resolution.md → human judgment

  §3 APE v1 Scope (SSE-D-11)
    - Template parameterization only
    - No free-form code generation (correctness guarantee absent in v1)
    - Trace: SSE-D-11 → final-resolution.md

  §4 Domain-Seed Hook (SSE-D-10)
    - Optional provenance hook
    - No replay semantics, no session format
    - Composition provenance via lineage
    - Trace: SSE-D-10 → final-resolution.md

  §5 Hybrid Equivalence (SSE-D-06)
    - Deterministic structural pre-bucket + behavioral nearest-rival audit
    - No LLM judge
    - Trace: SSE-D-06 → final-resolution.md

Path 2: drafts/architecture_spec.md — SEED NEW SECTIONS
  Add stub sections for 018-derived architecture decisions:

  §12 Breadth-Expansion Contract (SSE-D-04)
    - 7-field interface contract
    - Protocol must declare all 7 before breadth activation
    - Trace: SSE-D-04 → final-resolution.md

  §13 Discovery Pipeline Routing (SSE-D-01)
    - No Topic 018 umbrella for substance
    - Ownership distributed to 006/015/017/013/008/003
    - Trace: SSE-D-01 → final-resolution.md

  Update traceability table with new sections.

Path 3: drafts/README.md — ADD discovery_spec.md
  Add entry:
    - `discovery_spec.md` (Topic 018): SEEDED 2026-03-27
  Update dependency listing for architecture_spec.md to include Topic 018.

═══════════════════════════════════════════════════════════════════
STEP 5 — VERIFY no status drift
═══════════════════════════════════════════════════════════════════

Check that ALL of the following reflect Topic 018 = CLOSED:
  □ debate/018-search-space-expansion/README.md
  □ debate/018-search-space-expansion/findings-under-review.md
  □ debate/018-search-space-expansion/final-resolution.md (new, authoritative)
  □ debate/debate-index.md
  □ EXECUTION_PLAN.md
  □ PLAN.md

Check that no orphaned Open issues remain:
  □ findings-under-review.md: 0 issues with current_status = Open

Check counts consistency:
  □ debate-index.md totals: 7 CLOSED, 1 SPLIT, 11 OPEN = 19 total
  □ EXECUTION_PLAN.md: 76 standard debate rounds, 11 topics remaining
  □ PLAN.md: consistent with above

Check downstream routing confirmation:
  □ debate-index.md: no "provisional" routing notes for 018
  □ EXECUTION_PLAN.md: 018 ✅ in dependency notes for 006/015/017/013/003

Check draft specs:
  □ drafts/discovery_spec.md exists and traces to final-resolution.md
  □ drafts/architecture_spec.md has §12 and §13 stubs
  □ drafts/README.md lists discovery_spec.md

Report any discrepancies found.
```
