# X38 Rebuild — Issues Registry

> Created: 2026-03-29
> Purpose: Comprehensive inventory of all structural problems to fix in rebuild.
> Status: REFERENCE — used as input for rebuild design.

---

## A. TAXONOMY & LABELING (5 issues)

### A-01. JC/Converged binary too coarse
**Severity**: HIGH
**Where**: All 8 closed topics (001, 002, 004, 007, 008, 010, 013, 018)
**Problem**: "Judgment Call" label conflates 4 fundamentally different decision types:
| Actual type | Count | Example |
|-------------|-------|---------|
| Genuine disagreement, human broke tie | 7 | D-16 (001), D-04-E/A/B-auth (002), D-23 (010), CA-01 (013), SSE-D-05 (018) |
| Human-authored spec addition (no disagreement) | 5 | MK-03, MK-04, C1, C2 (004), MK-07 (004) |
| Conventional engineering default | 3 | CA-02, SSE-09 (013), D-04-B-cod (002) |
| Forced deferral due to structural dependency | 2 | SSE-04-THR (013), SSE-04-THR items 3a/3b (013) |
**Impact**: Cannot assess decision quality or revisit risk without re-reading full debate history.
**Fix**: Replace binary with: `CONVERGED` / `ARBITRATED` / `AUTHORED` / `DEFAULT` / `DEFERRED`.

### A-02. D-03 (Topic 001) contradictory label
**Severity**: LOW
**Where**: Topic 001 final-resolution.md
**Problem**: Listed as "Judgment call" in one row, marked "CONVERGED" in status field.
**Fix**: Audit and reconcile during extraction.

### A-03. Routed findings mislabeled as "Open"
**Severity**: MEDIUM
**Where**: Topics 003, 006, 015
**Problem**: Findings routed from closed Topic 018 (SSE-D-03, SSE-D-04, SSE-07, SSE-08, SSE-04-INV) appear in findings-under-review.md with status "Open" — but they are frozen constraints from a closed topic, not open questions.
**Impact**: Agents may waste rounds re-debating closed decisions.
**Fix**: Distinguish "finding under review" from "imported constraint".

### A-04. Inconsistent finding ID prefixes
**Severity**: LOW
**Where**: All topics
**Problem**: Mixed prefixes without convention: F-NN (generic), X38-D-NN, X38-ER-NN (014), X38-BR-NN (016), X38-ESP-NN (017), X38-SSE-NN (018).
**Impact**: Search and cross-reference harder than necessary.
**Fix**: Standardize in rebuild (single prefix scheme or explicit convention doc).

### A-05. Topic 012 F-19 is not a finding
**Severity**: MEDIUM
**Where**: Topic 012 findings-under-review.md
**Problem**: F-19 ("Online framework evolution") is a precedent analysis/lessons-learned — it poses questions but proposes no design decision. No thesis to debate.
**Impact**: Cannot converge in debate because there is nothing to agree/disagree on.
**Fix**: Demote to "supporting evidence" or reframe as actionable finding.

---

## B. CROSS-TOPIC OVERLAP & FRAGMENTATION (6 issues)

### B-01. Same concept scattered across 3-5 topics
**Severity**: HIGH (root cause of "messy" feeling)
**Where**: Entire debate structure
**Problem**: Findings organized by debate-topic (process history), not by concept (product).
| Concept | Findings spread across |
|---------|----------------------|
| Firewall | 002, 004, 009, 016, 017A |
| Identity/Versioning | 008, 011, 015, 018 |
| Campaign model | 001, 010, 013, 016 |
| Convergence | 001, 010, 013, 017A |
| Clean OOS | 001, 010, 016, 017A |
| Search-space | 003, 006, 008, 013, 015, 017A/017B, 018 |
**Impact**: To understand 1 concept, must read 3-5 final-resolution.md files and mentally assemble.
**Fix**: Rebuild organizes findings by concept domain, not by debate topic.

### B-02. Topic 015 vs Topic 011 — sizing classification conflict
**Severity**: HIGH
**Where**: Topic 015 F-17 vs Topic 011 F-28
**Problem**: F-17 says "sizing change = semantic change = new algo_version". F-28 says "sizing = deployment concern = deploy_version, not algo_version". Direct contradiction, known but unresolved.
**Impact**: Whichever topic closes first constrains the other, but no serialization enforced.
**Fix**: Merge into single cross-topic decision, or enforce 011 closes before 015.

### B-03. Topic 011 findings should be 2, not 4
**Severity**: MEDIUM
**Where**: Topic 011 findings-under-review.md
**Problem**: F-27 (boundary), F-28 (unit-exposure), F-29 (version split) are 3 aspects of 1 decision: "What is the x38/deployment boundary and how is it versioned?" Debating them separately risks internal contradictions.
**Fix**: Merge F-27/F-28/F-29 into single multi-part finding. Keep F-26 separate.

### B-04. Topic 015 mixed provenance
**Severity**: MEDIUM
**Where**: Topic 015 findings-under-review.md
**Problem**: 5 findings from 2 different sources — F-14, F-17 (native) + SSE-07, SSE-08, SSE-04-INV (imported from 018). Integration between native and imported findings underspecified.
**Fix**: Separate "findings to debate" from "constraints to implement".

### B-05. Topic 006 — orphaned routed finding
**Severity**: LOW
**Where**: Topic 006 findings-under-review.md
**Problem**: SSE-D-03 (registry acceptance for auto-generated features) weakly connected to F-08 (registry pattern). Interaction not pinned down.
**Fix**: Merge into single finding or document exact interaction.

### B-06. Topic 005 vs Topic 014 — engine API circularity
**Severity**: MEDIUM
**Where**: Topics 005 and 014
**Problem**: Both ask "vectorized vs event-loop?" — 005 owns the answer but needs 014's execution constraints; 014 needs 005's API choice. Bidirectional dependency with no sequencing.
**Fix**: Explicitly order 005 before 014.

---

## C. DEPENDENCY & ORDERING (5 issues)

### C-01. Topic 014 scheduled prematurely
**Severity**: HIGH
**Where**: Topic 014 (Wave 2 OPEN), depends on Topic 003 (Wave 3)
**Problem**: 014 designs execution orchestration but doesn't know protocol stage structure (003's output). Forced to design "against preliminary stage structure" — likely requires rework after 003 closes.
**Fix**: Defer 014 to post-003, or explicitly scope as "provisional".

### C-02. Topics 016 & 017 — "backlog" status despite satisfied deps
**Severity**: MEDIUM
**Where**: debate-index.md, topic READMEs
**Problem**: Both marked "OPEN (backlog)" but hard dependencies are satisfied (002, 008, 010, 013 all CLOSED). No clear activation trigger documented.
**Impact**: Blocks Topic 003 (Wave 3) because 003 waits on 016+017A.
**Fix**: Explicit activation rule: "When deps X, Y, Z all CLOSED -> activate immediately."
> **UPDATE (2026-04-03)**: Topic 017 SPLIT into 017A + 017B. 017A has ALL deps
> satisfied (002✅ + 008✅ + 010✅ + 013✅ + 018✅). 003 only needs 017A.
> C-02 partially resolved for 017A — activation is now possible.

### C-03. Topic 013 <-> Topic 017A circular dependency buried
**Severity**: HIGH
**Where**: Topic 013 SSE-04-THR judgment call, Topic 017A ESP findings
**Problem**: 013 needs 017A's consumption framework to set numeric floors. 017A needs 013's production metrics to set passing criteria. Topic 013 CLOSED with numerics deferred — but "CLOSED" is misleading because it must reopen or jointly reconcile when 017A closes.
**Impact**: Specs embed deferred numerics as if frozen. Implementation will hit "spec says X, but that was deferred".
**Fix**: Create explicit joint integration issue before either topic's decisions become binding on specs.
> **UPDATE (2026-04-03)**: Narrowed from 013↔017 to 013↔017A. 017B (inter-campaign)
> does not interact with convergence numerics. Resolution strategy added to 017A findings.

### C-04. No closure-to-integration workflow
**Severity**: MEDIUM
**Where**: All closed topics -> open topic consumers
**Problem**: When a topic closes, no "what this means for you" summary is sent to dependent open topics. Each downstream topic must hunt through closed topic's final-resolution.md.
**Evidence**: Topics 003 and 006 don't reflect Topic 018 routed obligations in their findings-under-review.md (018 closed 2026-03-27, consumer sync incomplete).
**Fix**: Post-closure integration guide per closed topic, or centralized routing table.

### C-05. Topic 003 overloaded as integration hub
**Severity**: MEDIUM
**Where**: Topic 003 (Protocol Engine)
**Problem**: Depends on outputs from 001, 002, 004, 015, 016, 017A, 018, 019A/019D1. Has 16+ cross-topic tensions. Any upstream change forces 003 to reopen. "Wave 3 last" designation makes it most volatile, not most stable.
**Fix**: Create constraints register for 003; schedule strictly after all upstream; accept it as integration point rather than debate topic.

---

## D. GOVERNANCE & PROCESS OVERHEAD (6 issues)

### D-01. Multi-source truth — 6 files to update per closure
**Severity**: HIGH
**Where**: PLAN.md, EXECUTION_PLAN.md, debate-index.md, architecture_spec.md, downstream findings-under-review.md, topic final-resolution.md
**Problem**: Each topic closure requires manual updates to 6+ files. Audit (2026-03-27) confirms persistent drift between PLAN.md and EXECUTION_PLAN.md (conflicting topic counts, stale status).
**Impact**: Agents get conflicting info during onboarding. Re-sync is error-prone.
**Fix**: Single authoritative source (debate-index.md + final-resolution.md). Other docs marked "may be stale" or auto-generated.

### D-02. Cross-topic tensions rule (§21-24) creates maintenance burden
**Severity**: MEDIUM
**Where**: debate/rules.md §21-24 (added 2026-03-23)
**Problem**: Every topic README and findings-under-review.md must have `## Cross-topic tensions` table, updated when any other topic closes. No machine enforcement. Topics opened pre-2026-03-23 got retroactive waiver — inconsistent application.
**Fix**: Single routing table in debate-index.md instead of per-topic replication.

### D-03. 4-tier authority hierarchy overhead
**Severity**: MEDIUM
**Where**: x38_RULES.md §4
**Problem**: published/ > debate/NNN/ > docs/design_brief.md > PLAN.md. Every agent must internalize this before every round. Precedence rarely matters in practice but adds cognitive load.
**Fix**: Simplify to 2 tiers: "decisions (authoritative)" and "context (informational)".

### D-04. `[extra-archive]` rule unenforced
**Severity**: LOW
**Where**: debate/rules.md §18
**Problem**: External evidence pointers must be labeled `[extra-archive]`. No pre-commit hook. Audit admitted "selective, not exhaustive" check.
**Fix**: Either enforce or drop the rule. Convention-only rules create false confidence.

### D-05. design_brief.md frozen as historical snapshot
**Severity**: LOW
**Where**: docs/design_brief.md
**Problem**: Tier 3 authority ("wins over PLAN.md if conflict") but never updated after topic closures. No "last reviewed" date. Agents don't know if it's still aligned with closed decisions.
**Fix**: Either actively maintain or explicitly demote to "historical input — check final-resolution.md for current decisions".

### D-06. 19 topics is too many for a design project
**Severity**: MEDIUM (structural)
**Where**: Entire debate structure
**Problem**: 19 topics (from original 000 split + additions) with wave/tier dependencies creates project management overhead that rivals the design work itself. 88 debate rounds across 8 closed topics; 10 still open.
**Impact**: Critical path to publication remains long. Process overhead may exceed substance output.
**Fix**: Rebuild with fewer, concept-aligned modules (see B-01).

---

## E. SPEC DRAFT INTEGRITY (5 issues)

### E-01. Stub sections in architecture_spec.md
**Severity**: MEDIUM
**Where**: drafts/architecture_spec.md
**Problem**: 6 sections are literal `_Stub._` placeholders:
| Section | Waiting on |
|---------|-----------|
| §4 Data Management | Topic 009 (OPEN) |
| §8 Deployment Boundary | Topic 011 (OPEN) |
| §10 Bounded Recalibration | Topic 016 (OPEN) |
| §11 Epistemic Search Policy | Topic 017A/017B (SPLIT from 017) |
| §12 Breadth-Expansion | Partial (018 seeded) |
| §13 Discovery Routing | Partial (018 seeded) |
**Impact**: No gate prevents publishing before stubs are filled.
**Fix**: Pre-publish gate: "all stubs must be resolved before PUBLISHABLE status".

### E-02. meta_spec.md stubs not transcribed from Topic 004
**Severity**: MEDIUM
**Where**: drafts/meta_spec.md §2 (Lifecycle), §3 (Storage)
**Problem**: Topic 004 resolved lifecycle state machine and storage structure, but these were not transcribed into meta_spec. Stubs say "from Topic 004 §V1..." but content is missing.
**Fix**: Extract and transcribe as part of rebuild.

### E-03. Deferred JCs embedded in specs as if frozen
**Severity**: HIGH
**Where**: architecture_spec.md §7.1, §9.2-9.4; discovery_spec.md §2
**Problem**: Judgment calls with DEFERRAL status (MK-07, SSE-04-THR, SSE-D-05) are cited in specs without marking their provisional nature. Specs treat them as settled governance.
**Impact**: Implementation will build on decisions that are not yet final.
**Fix**: Every spec section sourced from a JC must carry provenance tag: `[source: JC, status: DEFERRED|FINAL, blocked_by: Topic NNN]`.

### E-04. Discovery ownership ambiguity (architecture_spec vs discovery_spec)
**Severity**: MEDIUM
**Where**: architecture_spec.md §12-13 vs discovery_spec.md
**Problem**: Both specs define discovery-related content after Topic 018 closure. Neither explicitly claims ownership. Breadth-expansion contract appears in both.
**Fix**: Clear ownership split: architecture_spec owns the contract interface; discovery_spec owns the implementation.

### E-05. No spec-readiness tiers
**Severity**: MEDIUM
**Where**: drafts/README.md lifecycle
**Problem**: Current lifecycle: SEEDED -> DRAFTING -> PUBLISHABLE -> PUBLISHED. But "topic-locally-CLOSED" != "cross-topic-integrated" != "spec-ready". A topic can close while its deferred items block spec publication.
**Fix**: Add intermediate tier: "INTEGRATED" (all cross-topic dependencies reconciled).

---

## F. STATUS TRACKING & SYNC (3 issues)

### F-01. PLAN.md vs EXECUTION_PLAN.md vs debate-index.md diverge
**Severity**: MEDIUM
**Where**: Root governance files
**Problem**: PLAN.md says "Topics CLOSED (6)", EXECUTION_PLAN.md says 8 CLOSED, debate-index.md says 8 CLOSED + 1 SPLIT. Audit (2026-03-27) flagged as [WARNING][PERSISTING].
**Fix**: Single authoritative ledger.

### F-02. Topics 003 and 006 not synced with Topic 018 routing
**Severity**: MEDIUM
**Where**: debate/003-protocol-engine/, debate/006-feature-engine/
**Problem**: Topic 018 closed 2026-03-27 and declared 6 consumer topics. Topics 003 and 006 findings-under-review.md do not reflect routed obligations. Violates rules.md §25.6.
**Fix**: Part of closure-to-integration workflow (C-04).

### F-03. No global deferred-items tracker
**Severity**: MEDIUM
**Where**: Entire project
**Problem**: Deferred decisions (from JCs, circular deps, topic splits) are scattered across individual final-resolution.md files. No single view of "what is still unresolved".
**Fix**: Centralized deferred-items registry, updated on every closure.

---

## Summary

| Category | Count | HIGH | MEDIUM | LOW |
|----------|-------|------|--------|-----|
| A. Taxonomy & Labeling | 5 | 1 | 2 | 2 |
| B. Cross-topic Overlap | 6 | 2 | 3 | 1 |
| C. Dependency & Ordering | 5 | 2 | 3 | 0 |
| D. Governance Overhead | 6 | 1 | 3 | 2 |
| E. Spec Draft Integrity | 5 | 1 | 4 | 0 |
| F. Status Tracking | 3 | 0 | 3 | 0 |
| **TOTAL** | **30** | **7** | **18** | **5** |

### 7 HIGH-severity issues driving the rebuild:
1. **A-01**: JC taxonomy too coarse (10/17 mislabeled)
2. **B-01**: Findings scattered by debate-topic, not by concept
3. **B-02**: Topic 015 vs 011 sizing conflict (unresolved contradiction)
4. **C-01**: Topic 014 scheduled before its dependency (003)
5. **C-03**: 013<->017A circular dependency buried, both "closed"
6. **D-01**: 6-file manual sync per closure (persistent drift)
7. **E-03**: Deferred JCs embedded in specs as if frozen

---

## G. SELF-AUDIT — Issues Found in Rebuild Plan Itself (2026-03-29)

### G-01. Finding count severely undercounted
**Severity**: CRITICAL
**Where**: 01-taxonomy.md, 02-concept-structure.md
**Problem**: Plan claimed 65 total findings. Actual: ~164 (79 closed + 85 open). Migration table had 17 JCs; actual 23+. Domain size estimates were speculative, not extracted from data.
**Status**: CORRECTED in 01-taxonomy.md and 02-concept-structure.md (audit notes added, estimates revised).
**Residual risk**: Exact counts still unknown — requires full extraction as rebuild Step 1.

### G-02. B-02 contradiction claimed "resolved" by colocation
**Severity**: HIGH
**Where**: 02-concept-structure.md
**Problem**: Plan said moving F-17 and F-28 to same file = resolved. Wrong — colocation makes contradiction visible but doesn't decide it. Still needs active debate/decision.
**Status**: CORRECTED in 02-concept-structure.md (explicit OPEN finding created, decision required).

### G-03. Circular dep 013<->017 claimed "INTERFACE FREEZE" prematurely
**Severity**: HIGH
**Where**: 03-dependency-rules.md
**Problem**: Plan proposed INTERFACE FREEZE but Topic 017 had 6 OPEN findings (now SPLIT: 017A has 3, 017B has 3). Cannot freeze interface of undecided domain.
**Status**: CORRECTED in 03-dependency-rules.md (changed to PENDING, narrowed to 013↔017A).

### G-04. Governance claimed "2 updates per closure" — actual 3-4
**Severity**: MEDIUM
**Where**: 04-governance.md
**Problem**: Overclaimed simplification. Honest count is 3-4 updates (still better than 6).
**Status**: CORRECTED in 04-governance.md (honest count, distinction between substantive vs mechanical updates).

### G-05. 00-status.md extraction process undefined
**Severity**: MEDIUM
**Where**: 06-tracking.md
**Problem**: Central ledger design exists but no process for populating it from ~164 scattered findings. Manual extraction is error-prone.
**Status**: OPEN — rebuild Step 1 must define extraction methodology before populating.

### Updated Summary

| Category | Count | HIGH | MEDIUM | LOW |
|----------|-------|------|--------|-----|
| A. Taxonomy & Labeling | 5 | 1 | 2 | 2 |
| B. Cross-topic Overlap | 6 | 2 | 3 | 1 |
| C. Dependency & Ordering | 5 | 2 | 3 | 0 |
| D. Governance Overhead | 6 | 1 | 3 | 2 |
| E. Spec Draft Integrity | 5 | 1 | 4 | 0 |
| F. Status Tracking | 3 | 0 | 3 | 0 |
| G. Plan Self-Audit | 5 | 2 | 2 | 0 |
| **TOTAL** | **35** | **9** | **20** | **5** |

### Rebuild execution prerequisite
Before starting rebuild, **Step 0** must complete:
- Full extraction of ALL findings from ALL 18 topic directories
- Exact count and classification of every finding
- Verified domain mapping with real counts (not estimates)
- Only then can Steps 1-6 proceed with accurate data

---

## H. SECOND SELF-AUDIT — Cross-File Consistency (2026-03-29)

### H-01. "19→9 domains" claim is wrong — actual 17 domain files
**Severity**: HIGH
**Where**: 02-concept-structure.md header vs 06-tracking.md final structure
**Problem**: Header says "9 concept domains" but open topics create 8 more files (10-17).
19→17 is barely a reduction. Overlap solved for closed topics only; open topics still ~1:1.
**Fix**: Either (a) merge more open-topic domains (e.g., 13-data into 03-identity, 15-qa into PLAN),
or (b) honestly state "19→17 files, but 8 closed-topic domains now consolidated".

### H-02. Domain code table doesn't match domain files
**Severity**: MEDIUM
**Where**: 01-taxonomy.md (18 codes) vs 06-tracking.md (17 files)
**Problem**: `ART` code has no domain file (absorbed into `03-identity-versioning`).
`DEP` exists but some deployment findings go to `03-identity-versioning`.
**Fix**: Remove `ART` code — its findings use `IDV` code. Clarify `DEP` scope.

### H-03. 11-engine-design drops real dependency on protocol engine
**Severity**: HIGH
**Where**: 03-dependency-rules.md DAG
**Problem**: Old 014 depended on 003 (protocol stages). Merging 005+014 and setting
`depends_on: [01]` silently removes this dependency. Engine execution model genuinely
needs protocol stage structure to design parallelization.
**Fix**: Add soft dependency: `11-engine-design soft_depends_on: [10-protocol-engine]`
with note: "Execution orchestration findings may need revision after 10 closes."

### H-04. 14-deployment missing from 16's depends_on
**Severity**: MEDIUM
**Where**: 03-dependency-rules.md DAG
**Problem**: Old 016 depended on old 011. After 011 splits into 03+14, only 03 appears
in 16's depends_on. 14-deployment (monitoring trigger) also constrains recalibration.
**Fix**: Add `14-deployment` to 16-bounded-recalibration depends_on list.

### H-05. Verify checklists use stale numbers
**Severity**: LOW
**Where**: 01-taxonomy.md, 04-governance.md checklists
**Problem**: Checklists still reference "65 findings", "17 JCs", "2 files per closure".
Body text was corrected but checklists not synced.
**Fix**: Update checklists to match corrected numbers.

### H-06. Spec gate SKELETON→DRAFTING blocks entire spec on any open domain
**Severity**: HIGH
**Where**: 05-spec-gates.md Solution 1
**Problem**: Gate requires ALL source domains to have zero OPEN findings before spec
reaches DRAFTING. architecture_spec sources from 12+ domains — will never reach DRAFTING
until near end of project. Gate should be per-section, not per-spec.
**Fix**: Replace spec-level gate with section-level gate:
"A spec SECTION advances to DRAFTING when its source domain has zero OPEN findings.
The spec's overall status = minimum across all sections."

### H-07. No reopening protocol
**Severity**: HIGH
**Where**: 03-dependency-rules.md (missing)
**Problem**: Closure workflow handles closing. No protocol for reopening a DECIDED
finding when new evidence or contradictions appear.
**Fix**: Add Solution 5: "Reopening Protocol" — conditions, impact on downstream,
status rollback rules.

### H-08. Debate/decision process for open findings undefined
**Severity**: HIGH
**Where**: 04-governance.md
**Problem**: Plan reorganizes findings and governance. But HOW remaining open findings
are decided is not specified. Old system used multi-round agent debate. New system says
"rules embedded in PLAN.md" but doesn't say what rules or what process.
**Fix**: Explicitly state whether debates continue (and under what rules) or a different
decision process replaces them for remaining open findings.

### H-09. 09-open-questions role confusion (domain vs tracking file)
**Severity**: LOW
**Where**: 02-concept-structure.md, 06-tracking.md
**Problem**: Listed as concept domain #9 but is actually a tracking/ledger file.
Mixing governance with domain content in the same numbering scheme.
**Fix**: Rename to `00-status.md` or move to `x38/STATUS.md` outside decisions/.

### H-10. 06-tracking example data inconsistent with corrections
**Severity**: LOW
**Where**: 06-tracking.md example tables
**Problem**: Domain Status uses old counts (e.g., meta=12 vs actual 20-26).
Circular Deps still says "INTERFACE FREEZE" (corrected to PENDING in 03).
Integration Log uses dates when domains didn't exist yet.
**Fix**: Mark all example tables as "[TEMPLATE — populate with real data during Step 0]".

### Updated Final Summary

| Category | Count | HIGH | MEDIUM | LOW |
|----------|-------|------|--------|-----|
| A. Taxonomy & Labeling | 5 | 1 | 2 | 2 |
| B. Cross-topic Overlap | 6 | 2 | 3 | 1 |
| C. Dependency & Ordering | 5 | 2 | 3 | 0 |
| D. Governance Overhead | 6 | 1 | 3 | 2 |
| E. Spec Draft Integrity | 5 | 1 | 4 | 0 |
| F. Status Tracking | 3 | 0 | 3 | 0 |
| G. Plan Self-Audit (round 1) | 5 | 2 | 2 | 0 |
| H. Plan Self-Audit (round 2) | 10 | 5 | 2 | 3 |
| **TOTAL** | **45** | **14** | **22** | **8** |

### 5 NEW HIGH issues from round 2:
8. **H-01**: 19→17 files, not 19→9 (overclaimed simplification)
9. **H-03**: Engine-design drops real dependency on protocol engine
10. **H-06**: Spec gate blocks entire spec, should be per-section
11. **H-07**: No reopening protocol
12. **H-08**: Decision process for open findings undefined

---

## I. POST-BLUEPRINT SYNC — Gap Audit (2026-04-02)

> Review of changes between blueprint creation (2026-03-29) and current
> debate state (2026-04-02). Blueprint files updated to address all gaps.

### I-01. Topic 019 missing from concept-structure and DAG
**Severity**: CRITICAL (was)
**Where**: 02-concept-structure.md, 03-dependency-rules.md, 06-tracking.md
**Problem**: Topic 019 (DFL, 18 findings — largest single topic) opened 2026-03-29
but was not mapped to any concept domain in 02. Not in dependency DAG (03).
Not in directory structure (06). Protocol-engine depends_on omitted 019.
**Status**: CORRECTED (2026-04-02). Added `18-discovery-feedback-loop.md` to all 3 files.
DAG: 10-protocol-engine now depends_on includes 18. Tier 3 (cross-cutting).

### I-02. DFL finding count understated
**Severity**: HIGH (was)
**Where**: 01-taxonomy.md
**Problem**: Stated "DFL-01 through DFL-10". Actual: DFL-01 through DFL-18 (18 findings).
Topic 019 expanded significantly 2026-03-31 (DFL-11→DFL-18 added: data foundation,
non-stationarity, cross-asset context, synthetic validation, regime profiling).
**Status**: CORRECTED (2026-04-02). Updated to DFL-01→DFL-18.

### I-03. Gap audit findings (2026-03-31) not mapped
**Severity**: HIGH (was)
**Where**: All blueprint files (no mention of F-36, F-37, F-38, F-39, ER-03)
**Problem**: Gap audit round 0 (2026-03-31) added 5 new findings to 4 open topics:
- F-36 (multi-asset pipeline) → 003 → 10-protocol-engine
- F-37 (human decision points) → 003 → 10-protocol-engine
- F-38 (feature family ontology) → 006 → 12-feature-engine
- F-39 (framework testing strategy) → 012 → 15-quality-assurance
- ER-03 (session concurrency) → 014 → 11-engine-design
Additionally, F-19 demoted to supporting evidence (resolves A-05).
**Status**: CORRECTED (2026-04-02). Finding counts updated in 02, 06. Domain
mappings noted in 01 (taxonomy codes). A-05 noted as resolved.

### I-04. Spec status stale
**Severity**: MEDIUM (was)
**Where**: 05-spec-gates.md, 06-tracking.md
**Problem**: discovery_spec.md expanded to DRAFTING (§6-§11 from 019, non-authoritative).
architecture_spec.md updated with §14 proposal from 019. methodology_spec.md
added (from 013 closure). None reflected in blueprint.
**Status**: CORRECTED (2026-04-02). Stub tracking and spec readiness tables updated.
Ownership map expanded for discovery_spec (DFL sections).

### I-05. Total finding count estimates outdated
**Severity**: MEDIUM (was)
**Where**: 01-taxonomy.md
**Problem**: Estimated ~85 open findings. Actual: 81 active (debate-index 2026-04-01)
with different composition (019 contributing 18, gap audit +5, F-19 demoted -1).
**Status**: CORRECTED (2026-04-02). Updated scale section with accurate breakdown.

### I-06. Topic 019 split into 6 sub-topics
**Severity**: INFO (structural change)
**Where**: debate/019-discovery-feedback-loop/, 06-tracking.md, 02-concept-structure.md, 03-dependency-rules.md
**Problem**: Topic 019 (18 findings, 3005 lines, 167KB) was too large for effective debate.
Split into 6 sub-topics (019A-019F) on 2026-04-02:
  - 019A: Discovery Foundations (DFL-04/05/09, Tier 1, debate FIRST)
  - 019B: AI Analysis & Reporting (DFL-01/02/03, Tier 2, after 019A)
  - 019C: Systematic Data Exploration (DFL-06/07, Tier 3, after 019A)
  - 019D: Discovery Governance (DFL-08/10/11/12, Tier 2-3, after 019A+B)
  - 019E: Data Quality & Validation (DFL-13/14/17, Tier 4, independent)
  - 019F: Data Scope & Profiling (DFL-15/16/18, Tier 4, independent)
**Impact**: Domain file `18-discovery-feedback-loop.md` in decisions/ will contain 6
sub-sections (18A-18F). Extraction must map findings to sub-domains. 06-tracking.md
Domain Status table now has 6 rows instead of 1 for domain 18. 10-protocol-engine
depends_on updated to reference 18A-D (not just 18).
**Status**: COMPLETED (2026-04-02). All rebuild files updated. SUPERSEDED by I-07.

### I-07. Topic 019 debate efficiency audit — 019D split + 019E/F regroup + 017 strategy
**Severity**: INFO (structural change)
**Where**: debate/019D*/, debate/019E*/, debate/019F*/, debate/019G*/, debate/017*/, 06-tracking.md
**Problem**: Content audit identified 3 debate efficiency issues:
  1. 019D (753 lines, 4 findings, 6+7 decisions): "3 debates in a trenchcoat" — DFL-11 (budget)
     would absorb all debate bandwidth, leaving pipeline and grammar under-examined.
  2. 019E/019F: DFL-14 (non-stationarity) and DFL-18 (regime profiling) have a documented
     tension (conflicting regime classifications) but were in different topics.
  3. 017 (488 lines, 6 findings, 18 debate items): cascading parametric decisions through
     "cell" concept dependency chain.
**Actions**:
  - 019D SPLIT → 019D1 (DFL-08+10, pipeline), 019D2 (DFL-11, budget), 019D3 (DFL-12, grammar)
  - 019E/F REGROUPED: DFL-14 moved 019E→019F, DFL-15+16 moved 019F→019G (new)
    019E = DFL-13+17 (data quality validation), 019F = DFL-14+18 (regime dynamics), 019G = DFL-15+16 (data scope)
  - 017: Two-pass debate strategy added to README (structural first, parametric second)
    → **SUPERSEDED by K-01**: 017 SPLIT (2026-04-03) into 017A (v1, 3 findings) + 017B (v2, 3 findings).
    Split replaces two-pass strategy with actual separate debate topics.
**Final sub-topic count**: 10 (019A, 019B, 019C, 019D1, 019D2, 019D3, 019E, 019F, 019G + parent 019 archived). 017 additionally split into 017A + 017B (not counted here — tracked in K-01).
**Status**: COMPLETED (2026-04-02). 017 portion SUPERSEDED by K-01 (2026-04-03).

### Issues resolved in debate (no blueprint action needed)
- **A-05** (F-19 not a finding): F-19 demoted to supporting evidence in debate (2026-03-31).
  Blueprint already planned this. ✓
- **F-02** (003/006 not synced with 018): Routing propagated to consumer topics (2026-04-01).
  Partially resolved in debate, but rebuild still needed for full structural fix.
- **C-03 direction** (013↔017A circular): Resolution strategy added to 017A. Consistent
  with blueprint's PENDING approach. 017 SPLIT (2026-04-03) narrows scope to 017A only.

### Updated Final Summary

| Category | Count | HIGH | MEDIUM | LOW |
|----------|-------|------|--------|-----|
| A. Taxonomy & Labeling | 5 | 1 | 2 | 2 |
| B. Cross-topic Overlap | 6 | 2 | 3 | 1 |
| C. Dependency & Ordering | 5 | 2 | 3 | 0 |
| D. Governance Overhead | 6 | 1 | 3 | 2 |
| E. Spec Draft Integrity | 5 | 1 | 4 | 0 |
| F. Status Tracking | 3 | 0 | 3 | 0 |
| G. Plan Self-Audit (round 1) | 5 | 2 | 2 | 0 |
| H. Plan Self-Audit (round 2) | 10 | 5 | 2 | 3 |
| I. Post-Blueprint Sync | 7 | 0 | 0 | 0 |
| **TOTAL** | **52** | **14** | **22** | **8** |

> Category I issues are ALL CORRECTED in blueprint files (2026-04-02).
> They are logged for audit trail — no open action items remain.
> Original 45 issues (A-H) unchanged. 7 sync issues (I) added and resolved.

---

## J. GENESIS EXPORT & EXTERNAL IMPORT (3 issues, 2026-04-02)

> Context: Rebuild output target is `alpha_lab/genesis/` (self-contained,
> asset-agnostic). X40 Pack v2 contains proven operational concepts that
> x38 has not yet debated. Both directions (export OUT, import IN) need
> defined mechanisms.

### J-01. No export path to alpha_lab/genesis/
**Severity**: HIGH
**Where**: All rebuild documents (missing)
**Problem**: Rebuild defines x38/decisions/ as output and x38/drafts/ → x38/published/
as spec lifecycle. But the actual deliverable is `alpha_lab/genesis/` — a self-contained
architecture specification independent of x38 and btc-spot-dev. No document defines:
(a) genesis/ directory structure, (b) domain→genesis section mapping, (c) export gate,
(d) abstraction requirements, (e) export procedure.
**Impact**: Without export contract, decisions stay trapped in x38's debate structure.
genesis/ either never materializes or is created ad-hoc without quality gates.
**Fix**: Define export contract in 07-genesis-pipeline.md (Solutions 1 + 3).

### J-02. X40 state machine concepts not surfaced for x38 debate
**Severity**: HIGH
**Where**: All rebuild documents (missing)
**Problem**: X40 Clean Restart Pack v2 has operationalized 3 formal state machines
(baseline lifecycle, durability assessment, challenger tracking) that x38's
narrative-heavy debate process is unlikely to produce independently. Most other X40
concepts (comparison discipline, promotion ladder, cadence, etc.) will emerge
naturally during domain debate. But state machines represent a modeling discipline
that needs explicit introduction.
**Impact**: genesis/ may lack formal lifecycle definitions for core entities.
**Fix**: X40 as reference material + 3 state machine concepts recommended for
Step 0 evaluation in 07-genesis-pipeline.md (Solution 2).

### J-03. No abstraction test for genesis/ self-containment
**Severity**: HIGH
**Where**: 05-spec-gates.md (missing)
**Problem**: Spec lifecycle (SKELETON→PUBLISHED) has no gate ensuring output is
asset-agnostic and self-contained. A spec can reach PUBLISHED while still containing
BTC-specific references, strategy names, concrete thresholds, and x38 internal IDs.
genesis/ requires zero prohibited references, parameterized values, and domain-agnostic
readability.
**Impact**: genesis/ would inherit x38's BTC-centric vocabulary, making it unusable
for other asset classes without manual cleanup.
**Fix**: Define abstraction test + EXPORTED status in 07-genesis-pipeline.md (Solutions 1 + 3).

### Updated Final Summary

| Category | Count | HIGH | MEDIUM | LOW |
|----------|-------|------|--------|-----|
| A. Taxonomy & Labeling | 5 | 1 | 2 | 2 |
| B. Cross-topic Overlap | 6 | 2 | 3 | 1 |
| C. Dependency & Ordering | 5 | 2 | 3 | 0 |
| D. Governance Overhead | 6 | 1 | 3 | 2 |
| E. Spec Draft Integrity | 5 | 1 | 4 | 0 |
| F. Status Tracking | 3 | 0 | 3 | 0 |
| G. Plan Self-Audit (round 1) | 5 | 2 | 2 | 0 |
| H. Plan Self-Audit (round 2) | 10 | 5 | 2 | 3 |
| I. Post-Blueprint Sync | 7 | 0 | 0 | 0 |
| J. Genesis Export & Import | 3 | 3 | 0 | 0 |
| **TOTAL** | **55** | **17** | **22** | **8** |

> 3 new HIGH issues (J-01, J-02, J-03) all addressed by 07-genesis-pipeline.md.

---

## K. POST-BLUEPRINT SYNC — Quality Audit (2026-04-03)

> Review of changes between I-series sync (2026-04-02) and current state (2026-04-03).
> Topic 017 SPLIT + debate quality improvements to 016, 019C, 019F.
> Cross-references in 4 downstream topics (003, 006, 015, 016) updated.

### K-01. Topic 017 SPLIT into 017A + 017B
**Severity**: INFO (structural change)
**Where**: debate/017*/, debate-index.md, 003/006/015/016 cross-references
**Problem**: Topic 017 (488 lines, 6 findings, 10 cross-topic tensions) was the
largest open topic. Split into 2 sub-topics along v1/v2 scope boundary:
  - 017A: Intra-campaign ESP (v1) — ESP-01, ESP-04, SSE-04-CELL (3 findings)
  - 017B: Inter-campaign ESP (v2) — ESP-02, ESP-03, SSE-08-CON (3 findings)
**Scheduling benefit**: 003 only needs 017A. 017B can run parallel with 003.
**Impact on rebuild**: Domain `17-epistemic-search.md` should contain 2 sub-sections
(17A intra-campaign, 17B inter-campaign). DAG: 10-protocol-engine depends on 17A
(not full 17). C-02 partially resolved (017A has explicit activation — all deps
satisfied). C-03 narrowed (013↔017A, not 013↔017 full).
**Status**: COMPLETED (2026-04-03). Debate files created, cross-references updated.

### K-02. Topic 016 — pre-debate burden of proof framework
**Severity**: INFO (debate quality improvement)
**Where**: debate/016-bounded-recalibration-path/README.md
**Actions**: Decision tree (Step 1→2→3), 4 proposer requirements with preponderance
evaluation (not unanimity), conditional reasoning allowed, F-34 Judgment call aligned.
**Impact on rebuild**: None — debate-level change, not structural. C-02 still applies.

### K-03. Topic 019C — debate scope clarification
**Severity**: INFO (debate quality improvement)
**Where**: debate/019C-systematic-data-exploration/README.md
**Actions**: Technical soundness (must debate) vs prioritization (campaign-level)
distinction. Condensed summary approach per rules.md §10.
**Impact on rebuild**: None — debate-level change.

### K-04. Topic 019F — DFL-14/DFL-18 conflict resolution strategy
**Severity**: INFO (debate quality improvement)
**Where**: debate/019F-regime-dynamics/README.md
**Actions**: 3 resolution options (Condition, Precedence, Dual metadata), recommended
debate ordering (regime conflict → D-17/D-21), DFL-13 upstream dependency noted.
**Impact on rebuild**: None — debate-level change.

### K-05. Cross-references updated in 4 downstream topics
**Severity**: INFO (consistency fix)
**Where**: 003 README + findings, 006 README + findings, 015 findings, 016 findings
**Actions**: All "017" generic references → "017A" or "017A/017B" with finding-level
specificity. 003 dependencies updated: 017→017A, 019→019A+019D1. 013 deferred
numerics integration noted in 003.
**Impact on rebuild**: Stale references in blueprint files (this document, 02, 03, 05,
06) should be updated — see below.

### Stale references in rebuild files — APPLIED (2026-04-03)

> **UPDATE**: All stale references in solution files (01-06) have been fixed.
> Active references in 00-issues-registry (B-01, C-02, C-03, C-05, E-01, G-03,
> HIGH summary, I-07, I-resolved) have also been updated to 017A/017B.
> Only purely historical titles (G-03 header, D-06 original count) left as-is.

| File | Issue | Status |
|------|-------|--------|
| 01-taxonomy | "blocked_by: 017" | Already fixed (017A) prior to this audit |
| 02-concept-structure | "017" in open topics list (line 70) | **FIXED** → 017A, 017B |
| 02-concept-structure | mapping table (line 85) | Already updated with SPLIT info |
| 03-dependency-rules | Problem summary C-02/C-03 | **FIXED** → 017A/017B, 013↔017A |
| 03-dependency-rules | Circular dep section | **FIXED** → 017A throughout |
| 03-dependency-rules | DAG (lines 53-56) | Already had 017A/017B |
| 05-spec-gates | §11 stub tracking | **FIXED** → 017A/017B split noted |
| 06-tracking | Domain Status table | **FIXED** → 17 SPLIT into 17A + 17B rows |
| 06-tracking | Deferred Items / Circular Deps | **FIXED** → 17A references |
| 06-tracking | Spec Readiness | **FIXED** → 17A/17B |
| 06-tracking | Directory structure | **FIXED** → 17 annotation, archive count |
| 00-issues-registry | G-03 "16 OPEN findings" | **FIXED** → "6 OPEN, now 3+3" |

### Updated Final Summary (pre-L)

| Category | Count | HIGH | MEDIUM | LOW |
|----------|-------|------|--------|-----|
| A. Taxonomy & Labeling | 5 | 1 | 2 | 2 |
| B. Cross-topic Overlap | 6 | 2 | 3 | 1 |
| C. Dependency & Ordering | 5 | 2 | 3 | 0 |
| D. Governance Overhead | 6 | 1 | 3 | 2 |
| E. Spec Draft Integrity | 5 | 1 | 4 | 0 |
| F. Status Tracking | 3 | 0 | 3 | 0 |
| G. Plan Self-Audit (round 1) | 5 | 2 | 2 | 0 |
| H. Plan Self-Audit (round 2) | 10 | 5 | 2 | 3 |
| I. Post-Blueprint Sync | 7 | 0 | 0 | 0 |
| J. Genesis Export & Import | 3 | 3 | 0 | 0 |
| K. Quality Audit (2026-04-03) | 5 | 0 | 0 | 0 |
| **TOTAL** | **60** | **17** | **22** | **8** |

> Category K issues are ALL INFO-level and COMPLETED. Stale rebuild file
> references logged in table above — ALL APPLIED (2026-04-03).

---

## L. CROSS-VALIDATION AUDIT — Rebuild vs debate-index.md (2026-04-03)

> Cross-checked all 8 rebuild files against debate-index.md (ground truth)
> and 03-dependency-rules.md's own activation rules. Found 5 issues: 3 HIGH
> (status/DAG consistency), 1 MEDIUM (missing DAG entries), 1 LOW (unresolved "or").

### L-01. Domain Status table uses ACTIVE for sub-domains with unmet internal deps
**Severity**: HIGH
**Where**: 06-tracking.md, Domain Status table (7 rows)
**Problem**: The rebuild plan defines activation rule: "A domain activates when ALL
items in depends_on have zero OPEN findings." But 7 sub-domains were listed as ACTIVE
despite having unmet internal dependencies:
| Sub-domain | Listed as | Should be | Blocked by |
|------------|-----------|-----------|------------|
| 17B-inter-campaign-esp | ACTIVE | BLOCKED | 17A |
| 18B-ai-analysis-reporting | ACTIVE | BLOCKED | 18A |
| 18C-systematic-data-exploration | ACTIVE | BLOCKED | 18A |
| 18D1-pipeline-structure | ACTIVE | BLOCKED | 18A + 18B |
| 18D2-statistical-budget | ACTIVE | BLOCKED | 18A + 18B |
| 18D3-grammar-expansion | ACTIVE | BLOCKED | 18D2 |
| 16-bounded-recalibration | ACTIVE | BLOCKED | 03-identity, 14-deployment |
Additionally, 18D2 note said "after 18A" but debate-index says "after 019A+B" → corrected
to "after 18A+B" for consistency with debate-index.md line 108.
**Status**: CORRECTED (2026-04-03). All 7 rows updated to BLOCKED with explicit wait list.

### L-02. 10-protocol-engine blocking list wrong
**Severity**: HIGH
**Where**: 06-tracking.md, Domain Status table, line 44
**Problem**: Listed as "BLOCKED (waits 16, 17A, 18A-D1/D2/D3)". Two errors:
(a) Missing 03-identity-versioning — which IS in depends_on (DAG line 69) and still
ACTIVE with OPEN findings.
(b) Includes 18D2, 18D3 — which are NOT in depends_on (DAG lists only 18A, 18D1).
**Correct**: "BLOCKED (waits 03-identity, 16, 17A, 18A, 18D1)" — 5 blockers derived
from DAG depends_on=[02✅, 03, 04✅, 05✅, 16, 17A, 18A, 18D1] minus closed domains.
**Status**: CORRECTED (2026-04-03).

### L-03. 018 internal DAG implies 18C blocks 18D1/D2
**Severity**: HIGH
**Where**: 03-dependency-rules.md, line 62-64 (Tier 3, 18-DFL internal structure)
**Problem**: Chain notation "18A → 18B + 18C → 18D1 + 18D2 → 18D3" implies 18C
is a dependency for 18D1/D2. But debate-index.md (line 107-108) says:
"019B + 019C (after 019A)" and "019D1 + 019D2 (after 019A+B)" — meaning 18D1/D2
need 18A + 18B only, NOT 18C. 18C (systematic data exploration, DFL-06/07) runs
in parallel with 18B but is not on the critical path to 18D1/D2.
**Fix**: Rewrote to explicit dependency lines:
"18A → 18B + 18C (parallel) / 18A + 18B → 18D1 + 18D2 (parallel; 18C NOT blocking)
/ 18D2 → 18D3 (sequential)."
**Status**: CORRECTED (2026-04-03).

### L-04. 14-deployment and 15-quality-assurance missing from DAG
**Severity**: MEDIUM
**Where**: 03-dependency-rules.md, Tier 2 section
**Problem**: DAG lists 8 Tier 2 domains (03, 11, 12, 13) but omits 14-deployment
and 15-quality-assurance. These are real domain files in the decisions/ directory
structure (06-tracking.md lines 243-249). Both have satisfied dependencies
(14: 01✅+06✅; 15: 01✅) so the omission didn't cause status errors, but the DAG
should be complete per rebuild principle "Every domain has a depends_on list."
16-bounded-recalibration correctly lists 14-deployment in its depends_on, which
references a domain not in the DAG — an internal inconsistency.
**Status**: CORRECTED (2026-04-03). Added both to Tier 2 with depends_on lists
derived from debate-index.md dependency section.

### L-05. 009 mapping unresolved "or" in concept-structure
**Severity**: LOW
**Where**: 02-concept-structure.md, open topic mapping table, line 79
**Problem**: Says "`03-identity-versioning.md` or standalone `13-data-integrity.md`"
but the decision was already made: 13-data-integrity.md IS standalone in the
directory structure (06-tracking.md line 245), DAG (03-dependency-rules.md Tier 2),
and Domain Status table. The "or" is stale.
**Status**: CORRECTED (2026-04-03). Resolved to standalone `13-data-integrity.md`.

### Updated Final Summary

| Category | Count | HIGH | MEDIUM | LOW |
|----------|-------|------|--------|-----|
| A. Taxonomy & Labeling | 5 | 1 | 2 | 2 |
| B. Cross-topic Overlap | 6 | 2 | 3 | 1 |
| C. Dependency & Ordering | 5 | 2 | 3 | 0 |
| D. Governance Overhead | 6 | 1 | 3 | 2 |
| E. Spec Draft Integrity | 5 | 1 | 4 | 0 |
| F. Status Tracking | 3 | 0 | 3 | 0 |
| G. Plan Self-Audit (round 1) | 5 | 2 | 2 | 0 |
| H. Plan Self-Audit (round 2) | 10 | 5 | 2 | 3 |
| I. Post-Blueprint Sync | 7 | 0 | 0 | 0 |
| J. Genesis Export & Import | 3 | 3 | 0 | 0 |
| K. Quality Audit (2026-04-03) | 5 | 0 | 0 | 0 |
| L. Cross-Validation Audit (2026-04-03) | 5 | 3 | 1 | 1 |
| **TOTAL** | **65** | **20** | **23** | **9** |

> Category L: 5 issues, ALL CORRECTED in blueprint files (2026-04-03).
> L-01/L-02 were the most impactful — 7 wrong status values in the Domain Status
> table template. L-03 fixed a DAG ambiguity that would have misled Step 0 extraction.
> L-04 closed an internal inconsistency (domain referenced in depends_on but missing
> from DAG). L-05 resolved a stale "or" from early design.

---

## M. DAG & TAXONOMY CONSISTENCY AUDIT (2026-04-03)

> Cross-checked all DAG depends_on lists against debate-index.md dependency
> section, and Domain Status Open/Constraint counts against 01-taxonomy.md
> rules (routed findings from closed topics = CONSTRAINT, not OPEN).

### M-01. 17A depends_on missing 08-search-expansion
**Severity**: MEDIUM
**Where**: 03-dependency-rules.md, Tier 3 (line 57)
**Problem**: 17A listed `depends_on: [04, 06, 07]` but debate-index has 5 deps:
002✅(=04) + 008✅(=03*) + 010✅(=06) + 013✅(=07) + 018✅(=08).
08-search-expansion (topic 018) was missing. All deps are DONE so no activation
impact, but inconsistent with other domains (e.g. 16 lists all deps including DONE).
*Topic 008 is in domain 03 — see M-03 for why it can't be listed.
**Status**: CORRECTED (2026-04-03). Added 08 to depends_on.

### M-02. 12-feature-engine depends_on missing 01-philosophy
**Severity**: LOW
**Where**: 03-dependency-rules.md, Tier 2 (line 47)
**Problem**: Listed `depends_on: [08]` but topic 006 also has soft-dep on
007✅(=01-philosophy). 01 is DONE. Convention from other domains (e.g. 16)
is to list all deps including satisfied ones.
**Status**: CORRECTED (2026-04-03). Added 01 to depends_on.

### M-03. Domain 03 implicit dependency undocumented (DAG limitation)
**Severity**: MEDIUM
**Where**: 03-dependency-rules.md (missing)
**Problem**: 5 Tier 2+ domains (11, 12, 13, 15, 17A) have SATISFIED dependencies
on Topic 008 (architecture-identity) decisions, which reside in domain
03-identity-versioning. These cannot be listed in `depends_on` because domain 03
also contains OPEN findings from Topics 011/015 — the activation rule
("ALL depends_on have zero OPEN") would falsely BLOCK these domains.
This is a known trade-off of domain-level DAG granularity. Without documentation,
Step 0 extraction could miss importing Topic 008 constraints into these domains.
**Status**: CORRECTED (2026-04-03). Explanatory note added after DAG block.
17A entry also annotated.

### M-04. 10-protocol-engine Open/Constraint count wrong
**Severity**: MEDIUM
**Where**: 06-tracking.md, Domain Status table (line 44)
**Problem**: Listed `Open=4, Constraints=?`. But SSE-D-04 is routed from closed
Topic 018 — per 01-taxonomy.md rules, routed findings from closed topics enter
as CONSTRAINT, not OPEN. Correct: `Open=3 (F-05, F-36, F-37), Constraints=1 (SSE-D-04)`.
Inconsistent with 17A/17B which correctly separate Open from Constraints.
**Status**: CORRECTED (2026-04-03).

### M-05. 12-feature-engine Open count wrong
**Severity**: LOW
**Where**: 06-tracking.md, Domain Status table (line 46)
**Problem**: Listed `Open=3, Constraints=1`. But SSE-D-03 (the Constraint) was
also counted in Open. 3 total findings = 2 Open (F-08, F-38) + 1 Constraint
(SSE-D-03). Open should be 2, not 3.
**Status**: CORRECTED (2026-04-03).

### Updated Final Summary

| Category | Count | HIGH | MEDIUM | LOW |
|----------|-------|------|--------|-----|
| A. Taxonomy & Labeling | 5 | 1 | 2 | 2 |
| B. Cross-topic Overlap | 6 | 2 | 3 | 1 |
| C. Dependency & Ordering | 5 | 2 | 3 | 0 |
| D. Governance Overhead | 6 | 1 | 3 | 2 |
| E. Spec Draft Integrity | 5 | 1 | 4 | 0 |
| F. Status Tracking | 3 | 0 | 3 | 0 |
| G. Plan Self-Audit (round 1) | 5 | 2 | 2 | 0 |
| H. Plan Self-Audit (round 2) | 10 | 5 | 2 | 3 |
| I. Post-Blueprint Sync | 7 | 0 | 0 | 0 |
| J. Genesis Export & Import | 3 | 3 | 0 | 0 |
| K. Quality Audit (2026-04-03) | 5 | 0 | 0 | 0 |
| L. Cross-Validation Audit (2026-04-03) | 5 | 3 | 1 | 1 |
| M. DAG & Taxonomy Consistency (2026-04-03) | 5 | 0 | 3 | 2 |
| **TOTAL** | **70** | **20** | **26** | **11** |

> Category M: 5 issues, ALL CORRECTED in blueprint files (2026-04-03).
> M-03 is the most significant — documents a structural DAG limitation that
> could mislead Step 0 extraction without the explanatory note.
> M-04/M-01 were consistency gaps that L-audit missed (L checked status values
> but not Open/Constraint taxonomy or complete dep lists).
