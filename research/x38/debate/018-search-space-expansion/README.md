# Topic 018 — Search-Space Expansion

**Topic ID**: X38-T-18
**Opened**: 2026-03-25
**Status**: **CLOSED** (2026-03-27) — standard 2-agent debate completed
**Origin**: `docs/search-space-expansion/request.md` — VDO accidental discovery
exposed gap: x38 strong on validation, weak on discovery.

### Reopening rationale (2026-03-26)

Prior 4-agent debate (claude_code, codex, gemini, chatgptpro) followed a special
procedure **not covered by x38_RULES.md §5** (2 canonical participants). The
debate rounds are in `docs/search-space-expansion/debate/` (extra-canonical),
not in the standard `claude_code/` + `codex/` topic directory structure.

**Decision**: Reopen and conduct standard 2-agent debate (claude_code + codex)
following x38 rules. The prior 4-agent debate and `final-resolution.md` serve
as **input evidence** (not authoritative decisions). Downstream routings
(SSE-04-IDV→008, SSE-07/08→015, SSE-08-CON→017, SSE-09→013, etc.) were
provisional until this topic re-closed under standard governance.
Routings confirmed upon closure (2026-03-27).

**Wave placement**: Wave 2 (early priority — routes to 6 downstream topics).
Upstream deps met: 007 ✅, 004 ✅.

## Scope

Cơ chế khám phá thuật toán cho Alpha-Lab Framework. Hai tầng:
1. **Tầng 1 (Exploration — pre-lock)**: Mở rộng search space trước protocol lock
   bằng deterministic grammar enumeration (GFS), template parameterization (APE),
   và optional bounded AI ideation (spec-only, results-blind, OHLCV-only).
   Sau protocol lock, toàn bộ execution là deterministic code — zero AI.
2. **Tầng 2 (Recognition — post-lock)**: Nhận diện kết quả bất ngờ hữu ích qua
   deterministic surprise queue, equivalence audit (no LLM), proof bundle, và
   tích hợp vào framework.

**Kết luận chính**: Tất cả cơ chế discovery fold vào 6 existing topics
(006/015/017/013/008/003). Không tạo Topic 018 riêng cho substance — topic này
chỉ tồn tại như debate registry entry cho synthesis artifact.

**Debate đặc biệt**: 4 agents (claude_code, codex, gemini, chatgptpro) thay vì
2 agents thông thường. 7 rounds (R7 = bookkeeping).

**Governance note**: Prior 4-agent debate was extra-canonical (not per
x38_RULES.md §5) — archived, superseded by standard 2-agent debate (2026-03-27).
Evidence archive: `docs/search-space-expansion/debate/` [extra-canonical].

**Findings (OIs)** — resolved via standard 2-agent debate (2026-03-27):
- OI-01: Pre-lock generation lane ownership (Converged → SSE-D-01)
- OI-02: Bounded ideation / cold-start (Converged → SSE-D-02, SSE-D-03)
- OI-03: Surprise lane / recognition inventory (Judgment call → SSE-D-05)
- OI-04: 3-layer lineage (Converged, routed → Topic 015)
- OI-05: Cross-campaign contradiction memory (Converged, routed → Topics 015/017)
- OI-06: Breadth-expansion interface (Converged → SSE-D-04)
- OI-07: Domain-seed hook (Converged → SSE-D-10)
- OI-08: Cell + equivalence + correction (Converged → SSE-D-06)
- NEW-01 (ChatGPT Pro): Multiplicity control (Converged, routed → Topic 013)
- NEW-01 (Claude): APE v1 scope (Converged → SSE-D-11)

**Current status**: 10/10 OIs resolved → 11 decisions (OI-02 expands to SSE-D-02 + SSE-D-03). 10 Converged + 1 Judgment call (SSE-D-05). Topic CLOSED.

## Dependencies

- **Upstream**: Topic 007 (philosophy), Topic 004 (meta-knowledge, MK-17 shadow-only)
- **Downstream**: Topics 006, 015, 017, 013, 008, 003 (receive ownership routing)

## Debate status

**CLOSED** (2026-03-27) — 6 rounds completed (standard 2-agent, claude_code + codex).
10 Converged + 1 Judgment call (SSE-D-05). See `final-resolution.md` (authoritative).
Prior 4-agent extra-canonical debate (7 rounds) archived as input evidence, superseded.

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
| 003 | X38-SSE-D-04 | Stage wiring + breadth-activation blocker | SSE-D-04 breadth gate at protocol_lock |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 10 OIs — all resolved (10 Converged + 1 Judgment call). |
| `final-resolution.md` | **AUTHORITATIVE** — standard 2-agent debate closure (2026-03-27). |
| `closure-audit.md` | Prior extra-canonical audit (SUPERSEDED). Current audit: `codex/judgment-call-memo.md`. |
| `docs/search-space-expansion/debate/` | Evidence archive: 4 proposals + 4×7 debate rounds |
