# Topic 009 — Data Integrity & Session Immutability

**Topic ID**: X38-T-09
**Opened**: 2026-03-22
**Status**: OPEN
**Split from**: Topic 000 (cross-cutting)

## Scope

Cơ chế đảm bảo tính toàn vẹn dữ liệu và bất biến của session artifacts.
Hai mặt của cùng vấn đề: data-pipeline output + SHA-256 checksum (đầu vào)
và filesystem immutability (đầu ra).

**Findings**:
- F-10: Data management — data-pipeline output + SHA-256 checksum
- F-11: Session immutability — filesystem-level

## Dependencies

- **Upstream**: Topic 007 (philosophy), Topic 008 (architecture — F-09 directory structure)
- **Downstream**: Topic 002 (contamination firewall cần biết enforcement mechanism)

## Debate plan

- Ước lượng: 1 round
- Key battles:
  - F-10: Checksum mismatch policy (fail-closed vs re-snapshot)? Read lock khi pipeline write?
  - F-11: chmod vs hash-based verification? Rollback khi freeze lỗi?

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | F-04 | F-11 session immutability uses chmod enforcement; F-04 contamination firewall uses typed schema + state machine — overlapping enforcement domains may conflict on which mechanism is authoritative for shared artifacts | 002 owns firewall enforcement; 009 owns immutability enforcement |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 2 findings: F-10, F-11 |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
