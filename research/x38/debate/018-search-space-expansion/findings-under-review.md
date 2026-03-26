# Findings Under Review — Search-Space Expansion

**Topic ID**: X38-T-18
**Opened**: 2026-03-25
**Status**: **REOPENED** (2026-03-26) — prior 4-agent closure revoked; standard 2-agent debate required
**Author**: claude_code (architect) + codex (advisor) — standard x38 participants
**Origin**: `docs/search-space-expansion/request.md` — VDO accidental discovery
exposed gap in x38: strong on validation, weak on discovery.

10 Open Issues for standard 2-agent re-evaluation. **0/10 debated under x38 rules.**
Prior 4-agent debate (7 rounds) serves as input evidence [extra-canonical].
Evidence archive: `docs/search-space-expansion/debate/` (4 proposals + 4×7 rounds).

**Issue ID prefix**: `SSE-` (Search-Space Expansion), mapped to `OI-` register.

---

## OI-01: Pre-lock generation lane ownership

- **issue_id**: SSE-D-01
- **classification**: Judgment call
- **opened_at**: 2026-03-25
- **opened_in_round**: 2
- **current_status**: Open (prior 4-agent: Converged)
- **prior_closed_at**: R5 (2026-03-26)

**Nội dung**: Discovery mechanisms fold into 6 existing topics
(006/015/017/013/008/003). No Topic 018 umbrella for substance.

**Resolution**: Ownership split with explicit object boundaries. New topic only
if downstream closure report reveals explicit unresolved gap.

---

## OI-02: Bounded ideation / cold-start

- **issue_id**: SSE-D-02, SSE-D-03
- **classification**: Thiếu sót
- **opened_at**: 2026-03-25
- **opened_in_round**: 1
- **current_status**: Open (prior 4-agent: Converged)
- **prior_closed_at**: R5 (2026-03-26)

**Nội dung**: Bounded ideation (4 hard rules: results-blind, compile-only,
OHLCV-only, provenance-tracked) replaces SSS. Grammar depth-1 seed is mandatory
capability with conditional cold-start activation.

**Resolution**: Two generation modes at protocol lock: `grammar_depth1_seed`
(default) and `registry_only` (conditional).

---

## OI-03: Surprise lane / recognition inventory

- **issue_id**: SSE-D-05
- **classification**: Thiếu sót
- **opened_at**: 2026-03-25
- **opened_in_round**: 2
- **current_status**: Open (prior 4-agent: Converged)
- **prior_closed_at**: R5 (2026-03-26)

**Nội dung**: Recognition topology: surprise_queue → equivalence_audit →
proof_bundle → freeze. 5 anomaly axes + 5-component proof bundle minimum.

**Resolution**: Obligation-level inventory locked. Exact thresholds deferred to
017/013.

---

## OI-04: 3-layer lineage

- **issue_id**: SSE-D-07
- **classification**: Thiếu sót
- **opened_at**: 2026-03-25
- **opened_in_round**: 2
- **current_status**: Open (prior 4-agent: Converged, routed)
- **prior_closed_at**: R5 (2026-03-26)
- **routed_to**: Topic 015 (X38-SSE-07)

**Nội dung**: Semantic split locked: `feature_lineage`, `candidate_genealogy`,
`proposal_provenance`. Field enumeration + invalidation = 015 scope.

---

## OI-05: Cross-campaign contradiction memory

- **issue_id**: SSE-D-08
- **classification**: Judgment call
- **opened_at**: 2026-03-25
- **opened_in_round**: 2
- **current_status**: Open (prior 4-agent: Converged, routed)
- **prior_closed_at**: R5 (2026-03-26)
- **routed_to**: Topics 015 (X38-SSE-08) + 017 (X38-SSE-08-CON)

**Nội dung**: Contradiction registry = descriptor-level, shadow-only (MK-17
ceiling). Storage contract → 015. Consumption semantics → 017.

---

## OI-06: Breadth-expansion interface contract

- **issue_id**: SSE-D-04
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 4
- **current_status**: Open (prior 4-agent: Converged)
- **prior_closed_at**: R6 (2026-03-26)

**Nội dung**: 7-field breadth-activation contract. Protocol MUST declare all 7
interface fields before breadth activation. Exact values deferred downstream.

---

## OI-07: Domain-seed hook

- **issue_id**: SSE-D-10
- **classification**: Judgment call
- **opened_at**: 2026-03-25
- **opened_in_round**: 2
- **current_status**: Open (prior 4-agent: Converged)
- **prior_closed_at**: R5 (2026-03-26)

**Nội dung**: Domain-seed = optional provenance hook. No replay semantics, no
session format. Composition provenance preserved via lineage.

---

## OI-08: Cell + equivalence + correction method

- **issue_id**: SSE-D-06
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 4
- **current_status**: Open (prior 4-agent: Converged)
- **prior_closed_at**: R6 (2026-03-26)

**Nội dung**: Hybrid equivalence: deterministic structural pre-bucket +
behavioral nearest-rival audit. No LLM judge. Gemini's AST-only position
withdrawn R6.

---

## NEW-01 (ChatGPT Pro): Multiplicity control

- **issue_id**: SSE-D-09
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 3
- **current_status**: Open (prior 4-agent: Converged, routed)
- **prior_closed_at**: R5 (2026-03-26)
- **routed_to**: Topic 013 (X38-SSE-09)

**Nội dung**: Breadth coupling locked via SSE-D-04 field 5. Exact correction
formula → 013. Invalidation → 015.

---

## NEW-01 (Claude): APE v1 scope

- **issue_id**: SSE-D-11
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 3
- **current_status**: Open (prior 4-agent: Converged)
- **prior_closed_at**: R5 (2026-03-26)

**Nội dung**: APE v1 = template parameterization only. No free-form code
generation (correctness guarantee absent).

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | X38-D-04 | Bounded ideation must not violate firewall | SSE-D-02 hard rule 1 (results-blind) |
| 004 | MK-17 | Same-dataset priors shadow-only | SSE-D-08 shadow-only |
| 006 | X38-D-08 | Registry must accept auto-generated features | SSE-D-03 generation_mode feeds 006 |
| 008 | X38-D-13 | Identity axes; candidate-level vocabulary TBD | SSE-D-04 field 3 routes identity_vocabulary |
| 013 | X38-CA-01 | Multiplicity correction for breadth expansion | SSE-D-04 field 5 (scan_phase_correction_method) |
| 015 | X38-D-14/17 | Lineage + invalidation for discovery pipeline | SSE-D-07 routes 3-layer lineage to 015 |
| 017 | X38-ESP-01/02 | Coverage/surprise/proof integration | SSE-D-05 topology within 017 scope |
| 003 | — | Stage wiring + breadth-activation blocker | SSE-D-04 breadth gate at protocol_lock |

## Prior 4-Agent Outcomes (archived, non-authoritative)

**Governance note**: The table below records outcomes from the prior 4-agent debate
(not per x38_RULES.md §5). These are **input evidence** for the standard 2-agent
re-debate, not binding decisions. The original `Defer` states were normalized to
`Converged (routed)` per canonical vocabulary.

| Issue ID | Finding | Phân loại | Prior 4-agent status |
|----------|---------|-----------|---------------------|
| SSE-D-01 | Ownership fold: no Topic 018 umbrella | Judgment call | Converged |
| SSE-D-02/03 | Bounded ideation + conditional cold-start | Thiếu sót | Converged |
| SSE-D-05 | Recognition stack minimum | Thiếu sót | Converged |
| SSE-D-07 | 3-layer lineage | Thiếu sót | Converged (routed → 015) |
| SSE-D-08 | Contradiction registry | Judgment call | Converged (routed → 015/017) |
| SSE-D-04 | 7-field breadth-activation contract | Thiếu sót | Converged |
| SSE-D-10 | Domain-seed = optional hook | Judgment call | Converged |
| SSE-D-06 | Hybrid equivalence | Thiếu sót | Converged |
| SSE-D-09 | Multiplicity control coupling | Thiếu sót | Converged (routed → 013) |
| SSE-D-11 | APE v1 = parameterization only | Thiếu sót | Converged |

**Current live status**: 0/10 issues debated under standard x38 2-agent rules. All issues Open for re-evaluation.
