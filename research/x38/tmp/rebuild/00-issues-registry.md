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
| Firewall | 002, 004, 009, 016, 017 |
| Identity/Versioning | 008, 011, 015, 018 |
| Campaign model | 001, 010, 013, 016 |
| Convergence | 001, 010, 013, 017 |
| Clean OOS | 001, 010, 016, 017 |
| Search-space | 003, 006, 008, 013, 015, 017, 018 |
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
**Impact**: Blocks Topic 003 (Wave 3) because 003 waits on 016+017.
**Fix**: Explicit activation rule: "When deps X, Y, Z all CLOSED -> activate immediately."

### C-03. Topic 013 <-> Topic 017 circular dependency buried
**Severity**: HIGH
**Where**: Topic 013 SSE-04-THR judgment call, Topic 017 ESP findings
**Problem**: 013 needs 017's consumption framework to set numeric floors. 017 needs 013's production metrics to set passing criteria. Topic 013 CLOSED with numerics deferred — but "CLOSED" is misleading because it must reopen or jointly reconcile when 017 closes.
**Impact**: Specs embed deferred numerics as if frozen. Implementation will hit "spec says X, but that was deferred".
**Fix**: Create explicit joint integration issue before either topic's decisions become binding on specs.

### C-04. No closure-to-integration workflow
**Severity**: MEDIUM
**Where**: All closed topics -> open topic consumers
**Problem**: When a topic closes, no "what this means for you" summary is sent to dependent open topics. Each downstream topic must hunt through closed topic's final-resolution.md.
**Evidence**: Topics 003 and 006 don't reflect Topic 018 routed obligations in their findings-under-review.md (018 closed 2026-03-27, consumer sync incomplete).
**Fix**: Post-closure integration guide per closed topic, or centralized routing table.

### C-05. Topic 003 overloaded as integration hub
**Severity**: MEDIUM
**Where**: Topic 003 (Protocol Engine)
**Problem**: Depends on outputs from 001, 002, 004, 015, 016, 017, 018. Has 16 cross-topic tensions. Any upstream change forces 003 to reopen. "Wave 3 last" designation makes it most volatile, not most stable.
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
| §11 Epistemic Search Policy | Topic 017 (OPEN) |
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
5. **C-03**: 013<->017 circular dependency buried, both "closed"
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
**Problem**: Plan proposed INTERFACE FREEZE but Topic 017 has 16 OPEN findings. Cannot freeze interface of undecided domain.
**Status**: CORRECTED in 03-dependency-rules.md (changed to PENDING, added correct approach).

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

### Issues resolved in debate (no blueprint action needed)
- **A-05** (F-19 not a finding): F-19 demoted to supporting evidence in debate (2026-03-31).
  Blueprint already planned this. ✓
- **F-02** (003/006 not synced with 018): Routing propagated to consumer topics (2026-04-01).
  Partially resolved in debate, but rebuild still needed for full structural fix.
- **C-03 direction** (013↔017 circular): Resolution strategy added to 017. Consistent
  with blueprint's PENDING approach.

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
| I. Post-Blueprint Sync | 5 | 0 | 0 | 0 |
| **TOTAL** | **50** | **14** | **22** | **8** |

> Category I issues are ALL CORRECTED in blueprint files (2026-04-02).
> They are logged for audit trail — no open action items remain.
> Original 45 issues (A-H) unchanged. 5 sync issues (I) added and resolved.

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
| I. Post-Blueprint Sync | 5 | 0 | 0 | 0 |
| J. Genesis Export & Import | 3 | 3 | 0 | 0 |
| **TOTAL** | **53** | **17** | **22** | **8** |

> 3 new HIGH issues (J-01, J-02, J-03) all addressed by 07-genesis-pipeline.md.
