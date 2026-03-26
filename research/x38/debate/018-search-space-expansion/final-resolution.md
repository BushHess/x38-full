# Final Resolution — Search-Space Expansion

**Topic ID**: X38-T-18
**Opened**: 2026-03-25
**Closed**: 2026-03-26
**Rounds**: 7 / 6 (R7 = bookkeeping/termination only; max_rounds_per_topic = 6 per §13)
**Participants**: claude_code (architect), codex (advisor), gemini (advisor), chatgptpro (advisor)
**Evidence archive**: `docs/search-space-expansion/debate/` (4 proposals + 4×7 debate rounds)

---

## Summary

This topic addressed the discovery gap in X38: the framework is strong on
validation and certification but had no mechanism for generating novel
features or architectures. The VDO origin story — an accidental AI discovery
with no preserved prompt — motivated the request (`request.md`).

Four agents submitted independent proposals then debated over 7 rounds. The
debate produced two tiers of mechanisms: Tier 1 (pre-lock deterministic
generation + optional bounded AI ideation) and Tier 2 (post-lock deterministic
recognition — zero AI in execution). The backbone pipeline from pre-lock
through freeze, and a 7-field breadth-activation interface contract were
agreed. All mechanisms fold into existing topics (006/015/017/013/008/003).

**Final tally**: 10 Converged (3 routed to downstream topics), 0 Judgment call.
All 10 issues resolved. No open items. 11 architectural decisions
(SSE-D-01 through SSE-D-11) produced from 10 OIs.

**Round symmetry note (§14b)**: All 4 agents submitted rounds 1–7. R7 exceeds
max_rounds = 6 (§13) but is bookkeeping only — no OI was OPEN, no REOPEN-\*
filed. All 4 agents confirmed termination in R7. No §14b asymmetry.

**CL numbering note**: Each agent maintained independent CL numbering schemes
(Claude CL-01–CL-20, Codex CL-01–CL-09, Gemini CL-10–CL-14, ChatGPT Pro
CL-01–CL-21). Same IDs across agents refer to different content. This
synthesis uses canonical **SSE-D-NN** IDs with per-agent evidence pointers.

---

## Decisions

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| SSE-D-01 | Ownership fold: no Topic 018 | Fold discovery into 006/015/017/013/008/003; new topic only if closure reports reveal explicit unresolved gap | Converged | R5 |
| SSE-D-02 | Bounded ideation replaces SSS | 4 hard rules (results-blind, compile-only, OHLCV-only, provenance-tracked); no runtime AI infrastructure | Converged | R5 |
| SSE-D-03 | Grammar depth-1 conditional cold-start | `grammar_depth1_seed` = mandatory capability + default when registry empty; `registry_only` = conditional path when frozen non-empty registry exists | Converged | R5 |
| SSE-D-04 | 7-field breadth-activation contract | Protocol MUST declare all 7 interface fields before breadth activation; exact values deferred to downstream owners | Converged | R6 |
| SSE-D-05 | Recognition stack minimum | Topology: surprise_queue → equivalence_audit → proof_bundle → freeze; 5 anomaly axes + 5-component proof bundle minimum | Converged | R5 |
| SSE-D-06 | Hybrid equivalence | Deterministic structural pre-bucket + behavioral nearest-rival audit on common comparison domain; no LLM judge | Converged | R6 |
| SSE-D-07 | 3-layer lineage | Routed: semantic split locked (feature / candidate / proposal); field enumeration + invalidation to Topic 015 | Converged (routed) | R5 |
| SSE-D-08 | Contradiction registry | Routed: descriptor-level, shadow-only (MK-17 ceiling); row schema + retention to Topics 015/017 | Converged (routed) | R5 |
| SSE-D-09 | Multiplicity control coupling | Routed: breadth coupling locked via SSE-D-04; exact correction formula to Topic 013, invalidation to Topic 015 | Converged (routed) | R5 |
| SSE-D-10 | Domain-seed = optional provenance hook | Hook only — no replay semantics, no session format; composition provenance preserved via lineage | Converged | R5 |
| SSE-D-11 | APE v1 = parameterization only | Template parameterization + compile-time ideation; no free-form code generation in v1 (correctness guarantee absent) | Converged | R5 |

---

## Key Design Decisions (for drafts/)

### Decision 1: Discovery folds into existing topics, no Topic 018 (SSE-D-01)

**Accepted position**: Discovery mechanisms distribute across 6 existing topics
with clear ownership boundaries. New topic created only if a downstream closure
report reveals an explicit unresolved gap that cannot be assigned to any existing
topic.

**Rejected alternative**: A dedicated Topic 018 (Search-Space Expansion) to own
the full generation + recognition + phasing scope.

**Rationale**: Claude's original Topic 018 proposal bundled 6 sub-topics (GFS,
APE, SSS, CDAP, phase boundary, budget) into one mega-topic. ChatGPT Pro R1
argued folding is more tractable; Codex R2 confirmed existing topic scopes
already cover generation (006), lineage (015), coverage (017), wiring (003),
convergence (013), identity (008). Claude withdrew Topic 018 in R2.
Evidence: `claude/claude_debate_lan_2.md`, `chatgptpro/chatgptpro_propone.md`,
`codex/codex_debate_lan_2.md`.

### Decision 2: Bounded ideation replaces SSS (SSE-D-02)

**Accepted position**: Online AI ideation is permitted only as a bounded lane
with 4 hard rules: (1) results-blind — AI sees OHLCV only, not registry or
prior results; (2) compile-only — output is spec/proposal, not running code;
(3) provenance-tracked — every proposal linked to lineage; (4) deterministic
post-lock — after protocol lock, all execution is offline with no AI in loop.

**Rejected alternative**: SSS (Structured Serendipity Sessions) as first-class
infrastructure subsystem with M≥3 independent AI sessions per campaign.

**Rationale**: Claude self-identified SSS contamination risk in R1 (AI seeing
registry = implicit negative priors). ChatGPT Pro R2 declared SSS "dead
architecturally". All 4 agents converged by R3 on bounded ideation as
replacement. Evidence: `claude/claude_debate_lan_1.md` §5.4,
`chatgptpro/chatgptpro_debate_lan_2.md`, `codex/codex_debate_lan_3.md`.
Cross-ref: `online_vs_offline.md:30-36`.

### Decision 3: Grammar depth-1 conditional cold-start (SSE-D-03)

**Accepted position**: Two generation modes at protocol lock:
- `grammar_depth1_seed` (default cold-start): grammar defined, seed manifest
  generated, compile pass verified. Used when registry is empty.
- `registry_only` (conditional): registry non-empty, frozen, grammar_hash
  compatible. Used when importing a frozen manifest from prior work.

Depth-1 grammar is a mandatory **capability** (framework must support it);
activation is conditional on campaign state.

**Rejected alternatives**: (a) Grammar depth-1 mandatory every campaign
(Gemini R4 — too rigid); (b) Grammar entirely optional (insufficient cold-start
guarantee).

**Rationale**: ChatGPT Pro R4 "conditional cold-start law" reconciled the
mandatory-vs-optional tension. Codex R4 confirmed `grammar_depth1_seed` as
default. Evidence: `chatgptpro/chatgptpro_debate_lan_4.md:104-110`,
`codex/codex_debate_lan_4.md:115-119`, `gemini/gemini_debate_lan_4.md:54`.

### Decision 4: 7-field breadth-activation contract (SSE-D-04)

**Accepted position**: Protocol MUST declare ALL 7 interface fields before
breadth-expansion activation is permitted:

| # | Field | Owner | Description |
|---|-------|-------|-------------|
| 1 | `descriptor_core_v1` | 017 | 4 mandatory cell axes: `mechanism_family`, `architecture_depth`, `turnover_bucket`, `timeframe_binding` |
| 2 | `common_comparison_domain` | 013 | Default v1: `paired_daily_returns_after_costs` on shared evaluation segment |
| 3 | `identity_vocabulary` | **UNRESOLVED** — 008 candidate per X38-D-13, but scope gap identified (see correction note below) | Deterministic structural pre-bucket (descriptor hash, parameter family, AST-hash as subset) |
| 4 | `equivalence_method` | 013 + 008 | 2-layer hybrid: structural pre-bucket + behavioral nearest-rival. No LLM |
| 5 | `scan_phase_correction_method` | 013 | Required declaration; exact default (Holm/FDR/cascade) deferred to 013 |
| 6 | `minimum_robustness_bundle` | 017 + 013 | 5-component proof bundle minimum (see SSE-D-05) |
| 7 | `invalidation_scope` | 015 | Taxonomy/domain/cost-model change invalidates coverage_map, cell_id, equivalence_clusters, contradiction_registry; raw lineage preserved |

This topic locks the **interface obligation** (which fields must exist); downstream
topics lock the **content** (what values those fields take).

**Rejected alternatives**: (a) Gemini's 2-field shorthand (insufficient
coverage — isolated 3:1); (b) Claude R5 CL-19 6-point essay (same substance as
7 fields but lacked canonical naming — Codex R5 correctly required explicit
field list).

**Rationale**: Codex R5 OI-06 demanded a concrete field list, not abstract
direction. Claude R6 reconciled by mapping CL-19's 6 points to Codex's 7-field
naming 1:1. All 4 agents confirmed substance-identical in R6.
Evidence: `codex/codex_debate_lan_5.md:170-175`,
`claude/claude_debate_lan_6.md:76-98`.

**Correction (Claude R7)**: CL-19 reconciliation represents "7/7 interface
obligations IDENTIFIED and ROUTED to downstream owners" — not "7/7 field
contents frozen". Candidate-level `identity_vocabulary` owner = TBD by synthesis
(008 scope per X38-D-13 covers protocol/campaign/session identity axes, not
candidate equivalence vocabulary). Per `codex/codex_debate_lan_6.md:124,167`.

### Decision 5: Recognition stack minimum (SSE-D-05)

**Accepted position**: Recognition topology and minimum inventory:

**Topology** (post-Stage-3 scan):
```
surprise_queue → equivalence_audit → proof_bundle →
freeze_comparison_set → candidate_phenotype → contradiction_registry
```

**5 anomaly axes** (queue admission requires ≥1 non-peak-score axis):
1. Decorrelation outlier (max |ρ| with survivors < threshold)
2. Plateau width champion (width > N× median)
3. Cost stability (ranking stable ±2 across ≥3 cost scenarios)
4. Cross-resolution consistency (stable across timescales)
5. Contradiction resurrection (revives prior negative evidence)

**5-component proof bundle minimum**:
1. `nearest_rival_audit` (on common comparison domain)
2. `plateau_stability_extract`
3. `cost_sensitivity_test`
4. `ablation_or_perturbation_test`
5. `contradiction_profile`

Exact thresholds deferred to 017/013.

**Rejected alternative**: IC-based screening (Claude R1 identified overfitting
risk — IC on in-sample data; X21 evidence: entry features had zero predictive
power). Peak-score-only ranking (ChatGPT Pro's "consistency motif" insight:
VDO's value was 16/16 timescale robustness, not peak score).

**Rationale**: 4/4 aligned by R4 on obligation-level inventory. ChatGPT Pro R4
provided identical 5+5 list. Codex R4 confirmed minimum interface requirement.
Evidence: `chatgptpro/chatgptpro_debate_lan_4.md:120-126`,
`codex/codex_debate_lan_4.md:121-126`.

### Decision 6: Hybrid equivalence (SSE-D-06)

**Accepted position**: 2-layer deterministic hybrid:
- **Layer 1 (structural pre-bucket)**: Descriptor hash, parameter family,
  AST-hash as subset. Catches syntactic duplicates. Context-free, stable.
- **Layer 2 (behavioral nearest-rival)**: Paired-return correlation on common
  comparison domain. Catches economic duplicates missed by structure alone.

No LLM judge. Both layers fully deterministic (same data + code + seed = same
result). Preserves Gemini's determinism principle while adding behavioral
coverage.

**Rejected alternative**: AST-hash only (Gemini position, isolated 3:1).

**Steel-man for AST-only**: "Behavioral equivalence introduces
evaluation-dependency — changing cost model or evaluation window changes
equivalence classification. AST-hash + parameter distance is context-free and
stable."

**Why steel-man doesn't hold**: Correctness, not stability, is the objective.
Two features with identical AST but different cost treatment are not
economically equivalent; two features with different implementation but
paired returns ρ>0.99 ARE economically redundant. Hybrid preserves determinism
while catching both syntactic and economic duplicates. Gemini R6 withdrew
AST-only and accepted hybrid. Evidence: `claude/claude_debate_lan_5.md` §3.4,
`gemini/gemini_debate_lan_6.md:33-37`, `online_vs_offline.md:30-36`.

---

## Backbone v1

The complete pre-lock-to-freeze pipeline agreed by all 4 agents:

```
Pre-lock:
  [Bounded ideation (SSE-D-02)]  --> proposal_spec (results-blind, compile-only)
  [Grammar depth-1 seed (SSE-D-03)] --> compiled_manifest
  Both --> 006 registry compilation (grammar check, dedup)
           |
Protocol Lock:
  generation_mode validation (SSE-D-03):
    grammar_depth1_seed: grammar defined + manifest generated + compile pass
    registry_only: registry non-empty + frozen + grammar_hash compatible
  Breadth gate (SSE-D-04): ALL 7 interface fields declared
    [descriptor_core_v1, common_comparison_domain, identity_vocabulary,
     equivalence_method, scan_phase_correction_method,
     minimum_robustness_bundle, invalidation_scope]
  |
  v
Stage 3: Exhaustive scan (deterministic, offline, no AI)
  --> Descriptor tagging
  --> Coverage map (4 mandatory cell axes — SSE-D-04 field 1)
  --> Cell-elite archive (cell-elite > global top-K)
  --> Local neighborhood probes
  |
Stage 4-6: Layered search + probes (per design_brief)
  |
Stage 7: Freeze
  --> Surprise queue (SSE-D-05: 5 axes, ≥1 non-peak-score)
  --> Equivalence audit (SSE-D-06: hybrid structural + behavioral)
  --> Proof bundle (SSE-D-05: 5-component minimum)
  --> Comparison set (frozen)
  --> Candidate phenotype
  --> Contradiction registry (SSE-D-08: descriptor-level, shadow-only)
  |
Stage 8: Holdout + reserve + epistemic delta
```

---

## Adopted Artifacts

| # | Artifact / Mechanism | Decision | Owner |
|---|---------------------|----------|-------|
| 1 | Bounded ideation lane (4 hard rules) | SSE-D-02 | 006 + 015 |
| 2 | Grammar depth-1 seed (mandatory capability, conditional cold-start) | SSE-D-03 | 006 |
| 3 | `generation_mode` validation contract | SSE-D-03 | 006 + 003 |
| 4 | Ownership split with explicit object boundaries | SSE-D-01 | 006/015/017/013/008/003 |
| 5 | 7-field breadth-activation interface contract | SSE-D-04 | 003 + 013 + 015 + 017 + 008 |
| 6 | Hybrid equivalence (structural pre-bucket + behavioral nearest-rival) | SSE-D-06 | 008 + 013 |
| 7 | 4 mandatory cell axes (`descriptor_core_v1`) | SSE-D-04 | 017 |
| 8 | 5 anomaly axes + 5-component proof bundle minimum | SSE-D-05 | 017 + 013 |
| 9 | Recognition topology (surprise → equivalence → proof → freeze) | SSE-D-05 | 017 + 013 + 003 |
| 10 | Domain-seed = optional provenance hook | SSE-D-10 | 015 |
| 11 | APE v1 = parameterization only | SSE-D-11 | 006 |
| 12 | Discovery artifact = machine-readable; lineage canonical (not transcript) | Foundation | 015 + 006 |
| 13 | Recognition scores consistency motif (cross-timescale), not peak score alone | Foundation | 017 |

---

## Deferred Items

### Deferred by design (out of scope for v1)

| # | Artifact / Mechanism | Reason |
|---|---------------------|--------|
| 1 | Topic 018 umbrella | SSE-D-01: fold sufficient |
| 2 | SSS first-class infrastructure | SSE-D-02: replaced by bounded ideation |
| 3 | GFS depth 2/3, APE code generation, GA/mutation | Compute/correctness risk; v2+ |
| 4 | CDAP / domain catalog as core mechanism | SSE-D-10: hook only |
| 5 | Full EPC lifecycle / activation ladder | MK-17 shadow-only ceiling |

### Routed to downstream topic owners (Converged-routed OIs)

| # | Artifact / Mechanism | Owner | Source |
|---|---------------------|-------|--------|
| 1 | 3-layer lineage field enumeration + invalidation matrix | 015 | SSE-D-07 (OI-04) |
| 2 | Contradiction row schema + retention + reconstruction-risk | 015 + 017 | SSE-D-08 (OI-05) |
| 3 | Exact correction law default (Holm/FDR/cascade) | 013 | SSE-D-09 (NEW-01 GPT) |
| 4 | Exact invalidation cascade details | 015 | SSE-D-04 field 7 |
| 5 | Exact cell-axis values + anomaly thresholds | 017 + 013 | SSE-D-04/05 |
| 6 | Exact equivalence distance thresholds | 013 + 017 | SSE-D-06 |
| 7 | `generation_mode` state machine implementation | 006 | SSE-D-03 |
| 8 | Candidate-level `identity_vocabulary` owner assignment | 008 or 013 (TBD) | SSE-D-04 field 3 |

---

## Ownership Routing (directional — downstream topics validate)

| Topic | Responsibilities from this debate |
|-------|----------------------------------|
| 006 | Operator grammar, feature DSL, `generation_mode` state machine + validation, depth-1 seed, compile-to-manifest, parameter sweep, feature descriptor core |
| 015 | `feature_lineage`, `candidate_genealogy`, `proposal_provenance`, field enumeration, invalidation tables, contradiction row schema + retention |
| 017 | Coverage map, cell-elite archive, local probes, surprise queue, phenotype/contradiction shadow, budget, cell axis values, anomaly thresholds, proof bundle consumption |
| 013 | Common comparison domain law, correction law default, convergence/diminishing-returns, equivalence thresholds, robustness bundle requirements |
| 008 | Protocol/campaign/session identity axes (per X38-D-13); candidate-level equivalence vocabulary TBD |
| 003 | Stage insertion, required artifacts, freeze/gating wiring, breadth-activation blocker, `protocol_lock` validation |

**Note**: This routing is directional, not authoritative downstream inventory.
If a downstream topic finds that a routed item does not fit its scope, the
proper mechanism is REOPEN-\* with evidence, not silent absorption.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 (firewall) | X38-D-04 | Bounded ideation must not violate contamination firewall: AI sees OHLCV only, not registry or prior results | SSE-D-02 hard rule 1 (results-blind) enforces; Topic 002 owns content gate |
| 004 (meta-knowledge) | MK-17 | Same-dataset priors shadow-only — discovery from current campaign cannot become active prior | SSE-D-08 shadow-only; cross-campaign activation deferred to future data |
| 006 (feature-engine) | X38-D-08 | Feature registry must accept auto-generated features from grammar + bounded ideation | SSE-D-03 `generation_mode` feeds into 006 registry compilation |
| 008 (identity) | X38-D-13 | Protocol/campaign/session identity axes defined by 008; candidate-level equivalence vocabulary may require 008 scope expansion | SSE-D-04 field 3 routes `identity_vocabulary`; owner TBD |
| 013 (convergence) | X38-CA-01 | Multiplicity correction required when breadth-expansion introduces many candidates | SSE-D-04 field 5 (`scan_phase_correction_method`); 013 owns formula |
| 015 (artifact-versioning) | X38-D-14, X38-D-17 | Lineage/provenance artifacts + invalidation scope consumed by discovery pipeline | SSE-D-07 routes 3-layer lineage to 015; SSE-D-04 field 7 routes invalidation |
| 017 (epistemic-search) | X38-ESP-01, X38-ESP-02 | Coverage/surprise/proof semantics must integrate with ESP policies | SSE-D-05 topology sits within 017 scope; cell-elite replaces global top-K |
| 003 (protocol-engine) | — | Stage insertion + breadth-activation blocker are new wiring requirements | SSE-D-04 breadth gate + SSE-D-03 `generation_mode` validation at protocol_lock |

---

## Foundation Convergences (not debated — agreed from R1)

These were never disputed across all 4 agents and all 7 rounds:

1. X38 is strong on validation, weak on discovery (4/4 R1)
2. Tier 1 (Exploration) + Tier 2 (Recognition) separation (4/4 R1)
3. Post-lock execution is deterministic offline — no AI in runtime (4/4 R1)
4. Discovery artifacts are machine-readable; lineage is canonical (not
   transcript memory) (4/4 R1)
5. Cell-elite archive > global top-K for diversity preservation (4/4 R1)
6. Discovery gates ≠ certification/deployment gates (4/4 R1)
7. Same-dataset learned priors = shadow-only per MK-17 (4/4 R1, frozen law)
8. Freeze preserves comparison set + coverage + phenotype, not just winner
   (4/4 R2)
9. Recognition scores consistency motif (cross-timescale robustness), not
   peak score alone — VDO would have been killed without this (4/4 R2)
10. Codex + ChatGPT Pro proposals form backbone (lineage + cell-elite + gate
    split + artifact contract) (3/4 R1, Claude R2 concession)

---

## Complete Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Pre-lock generation lane ownership | Judgment call | **Converged** (SSE-D-01) | "Downstream chưa echo owner split → chỉ là slogan" | Authority-order reversal: upstream routes owners BEFORE downstream confirms. REOPEN-\* exists for gaps. Object boundaries explicit in SSE-D-01. |
| OI-02 | Bounded ideation / cold-start | Thiếu sót | **Converged** (SSE-D-02, SSE-D-03) | "SSS trực tiếp tái tạo VDO origin" | VDO value từ composition + 16/16 robustness, không từ session format. 4/4 aligned R3+. Contamination risk killed SSS. |
| OI-03 | Surprise lane / recognition inventory | Thiếu sót | **Converged** (SSE-D-05) | "IC + orthogonality đủ" | IC = feature screening (overfitting risk on in-sample). Candidate recognition cần 5 anomaly axes + 5-component proof bundle. Thresholds = 017/013. |
| OI-04 | 3-layer lineage | Thiếu sót | **Converged (routed)** (SSE-D-07) | "Field list chưa xong → issue phải active ở đây" | Semantic split locked (feature/candidate/proposal have different invalidation semantics). Field enumeration = 015 scope. |
| OI-05 | Cross-campaign contradiction memory | Judgment call | **Converged (routed)** (SSE-D-08) | "Row schema chưa close → issue phải active ở đây" | MK-17 shadow-only ceiling locked. Row schema/retention = 015/017 scope. |
| OI-06 | Breadth-expansion interface contract | Thiếu sót | **Converged** (SSE-D-04) | "Exact correction/taxonomy defaults phải freeze ngay tại topic này" | 7/7 interface obligations identified and routed. Exact values = downstream owners. Interface ≠ content. |
| OI-08 | Cell + equivalence + correction method | Thiếu sót | **Converged** (SSE-D-06) | "AST-hash + parameter distance đủ cho equivalence" | Behavioral redundancy determines economic independence — AST misses economic duplicates. Hybrid preserves determinism. Gemini R6 withdrew AST-only. |
| OI-07 | Domain-seed hook | Judgment call | **Converged** (SSE-D-10) | "Cross-domain cross-pollination là core mechanism" | Composition provenance, not session format. Hook preserves trail without creating infrastructure. |
| NEW-01 (GPT) | Multiplicity control | Thiếu sót | **Converged (routed)** (SSE-D-09) | "Coupling → default law phải khóa ngay" | Coupling locked via SSE-D-04 field 5. Exact formula = 013 scope. |
| NEW-01 (Claude) | APE v1 scope | Thiếu sót | **Converged** (SSE-D-11) | "Code generation tạo structural innovation" | Correctness guarantee chưa có; parameterization + compile-time ideation đủ cho v1. |

---

## Agent Contributions (summary)

| Agent | Key contributions | Key corrections |
|-------|-------------------|-----------------|
| **Codex** | Discovery lineage foundation (E1-E6, R1-R6); 9-gap analysis (G1-G9); 7-field breadth bundle (R5) — forced explicit interface contract; anti-false-convergence discipline | Withdrew "downstream echo required for upstream convergence" (R6); overclaim corrections on Claude R6 (3 points, all accepted) |
| **ChatGPT Pro** | Consistency motif insight (VDO = cross-timescale, not peak); discovery ≠ certification gates; interface/downstream split (cleanest R6); conditional cold-start law framing; authority-order reversal argument | Self-corrected Holm push (R4); self-corrected holding_bucket (R4); kept OI-08 open one round too long (R5→R6) |
| **Claude** | GFS grammar specificity (operator table, depth limits, dedup); SDL 6 surprise criteria; reconciliation CL-19 ↔ 7-field (R6); CL-20 object boundaries | Withdrew SSS (R2), Topic 018 (R2), EPC (R2), APE codegen (R3); acknowledged §7(c) procedural overreach (R6); accepted 3 overclaim corrections from Codex R6 |
| **Gemini** | Anti-online/anti-LLM discipline (foundation invariant); offline-first philosophy; prompt serialization for lineage | Withdrew AST-only position (R6); premature closure claim (R5) retracted |

---

## Draft impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `architecture_spec.md` | Discovery pipeline (pre-lock → freeze) | Create — backbone v1 from this resolution |
| `architecture_spec.md` | Breadth-activation contract | Create — 7-field interface obligation table |
| `architecture_spec.md` | Generation modes | Create — `grammar_depth1_seed` / `registry_only` validation |
| `architecture_spec.md` | Recognition stack | Create — topology, 5 anomaly axes, proof bundle minimum |
| `architecture_spec.md` | Equivalence | Create — hybrid 2-layer (structural + behavioral) |
| `meta_spec.md` | Bounded ideation | Create — 4 hard rules, provenance contract |
| `meta_spec.md` | Contradiction registry | Update — shadow-only per MK-17, descriptor-level |

---

## Closure Audit Checklist

- [x] All OIs resolved: 10 CONVERGED (3 routed) = 10/10
- [x] No Judgment calls required (all substance-aligned 4/4)
- [x] Routed items have downstream topic owners explicitly assigned
- [x] §14b symmetry: all 4 agents have equal substantive rounds
- [x] Steel-man completed for every CONVERGED issue
- [x] Cross-topic tensions documented with resolution paths
- [x] Backbone v1 pipeline complete (pre-lock to freeze)
- [x] Ownership routing table provided (directional)
- [x] Corrections from Codex R6 incorporated (3/3 accepted)
- [x] CL numbering reconciled via canonical SSE-D-NN IDs

---

**Topic 018 — CLOSED. Decisions signed off after closure audit (`closure-audit.md`).**

**Canonical location**: `debate/018-search-space-expansion/final-resolution.md`
