# Topic 001 — Campaign Model

**Topic ID**: X38-T-01
**Opened**: 2026-03-22 (activated from PLANNED)
**Status**: **CLOSED** (2026-03-23)
**Origin**: F-03 (summary in Topic 000), F-15 + F-16 (gen4 imports)

## Scope

Mô hình Campaign → Session: phân cấp nghiên cứu, HANDOFF giữa campaigns,
convergence analysis, metric scoping, và transition guardrails.

**Findings**:
- F-03: Campaign → Session model (từ Topic 000)
- F-15: Two cumulative scopes — version-scoped vs candidate-scoped (từ gen4)
- F-16: Campaign transition guardrails (từ gen4)

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- C-04: x38 hiện KHÔNG có bounded recalibration path
- C-06: Transition-law gap thật

## Dependencies

- **Upstream**: Topic 007 (philosophy — F-01 phải settled trước)
- **Downstream**: Topic 003 (protocol engine cần campaign model để design stages)

## Debate status

6 rounds hoàn tất (max_rounds_per_topic). 3/3 issues resolved:
2 Converged (D-03, D-15), 1 Judgment call §14 (D-16).
Xem `final-resolution.md` cho full decisions.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 (philosophy) | X38-D-01 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be valid exit | 007 CLOSED; constraint inherited, 001 owns operationalization |
| 002 (firewall) | X38-D-04 | Firewall determines what can flow at HANDOFF — F-16 guardrails constrain WHEN, firewall constrains WHAT | 002 owns firewall rules; 001 owns HANDOFF trigger/budget |
| 003 (protocol-engine) | F-05 | Protocol content definition determines what "protocol identity" means; routing contract references it | 003 owns protocol content; 001 owns routing contract |
| 008 (architecture-identity) | F-13 | Identity/version schema determines how protocol_identity is tracked | 008 owns identity schema; 001 owns one-way invariant that consumes it |
| 010 (clean-oos) | X38-D-12, X38-D-21 | Clean OOS (Phase 2) depends on campaign model defining Phase 1 exit criteria | 010 owns certification; 001 defines campaign-level verdicts |
| 013 (convergence) | F-15 scoping | Metric scoping determines what convergence analysis measures | 013 owns convergence methodology; 001 provides scope definitions |
| 015 (artifact-versioning) | F-17 | Semantic change classifier determines route classification: which code changes preserve vs alter protocol identity. D-16 route classification explicitly deferred to 015 / F-17 | 015 owns classifier; 001 owns structural HANDOFF law (invariant, package, governance) |
| 016 (bounded-recalibration) | C-04, C-12 | Cross-campaign methodology evolution overlaps with bounded recalibration | 016 owns decision; 001 provides HANDOFF mechanism + third scope definition |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 3 findings: F-03, F-15, F-16 |
| `final-resolution.md` | Final decisions: 2 Converged + 1 Judgment call (Position C routing contract) |
| `claude_code/` | Phản biện từ Claude Code (rounds 1-6) |
| `codex/` | Phản biện từ Codex (rounds 1-5) |
