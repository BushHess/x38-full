# Findings Under Review — Data Integrity & Session Immutability

**Topic ID**: X38-T-09
**Opened**: 2026-03-22
**Split from**: Topic 000 (X38-T-00)
**Author**: claude_code (architect)

2 findings về data integrity (đầu vào) và session immutability (đầu ra).

---

## F-10: Data management — copies, không symlinks

- **issue_id**: X38-D-10
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Data files là **copies** (không symlinks) trong `data/btcusdt/`.
Mỗi campaign.json ghi SHA-256 của data file nó dùng.

Lý do:
- Symlink → ai đó update file gốc → campaign cũ mất reproducibility.
- Copy + SHA-256 → mỗi campaign gắn liền với exact data snapshot.
- Data file nhỏ (~50MB cho 18K H4 + 3K D1 rows) → disk waste negligible.

Mỗi campaign.json chứa:
```json
{
    "data_file": "data/btcusdt/bars_2017_2026q3.csv",
    "data_sha256": "abc123...",
    "data_h4_rows": 19891,
    "data_d1_rows": 3317,
    "data_start": "2017-08-17",
    "data_end": "2026-09-17"
}
```

**Evidence**:
- PROMPT_FOR_V[n]_CLEAN_OOS_V1.md §verification [extra-archive]: "how to confirm the new data is
  correctly formatted and continuous with the old data."

**Câu hỏi mở**:
- Khi có 20 campaigns (10 năm), 20 copies ~1GB — acceptable?
- Nên incremental (file mới chỉ chứa rows mới) hay full (mỗi file chứa
  toàn bộ history)?
- Git LFS cho data files hay .gitignore + external storage?

---

## F-11: Session immutability — filesystem-level

- **issue_id**: X38-D-11
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Session artifacts trở thành read-only theo lifecycle:

```
SCANNING → stages 1-6 writable
FROZEN → stages 1-6 read-only (chmod), chỉ holdout/reserve/verdict writable
CLOSED → toàn bộ session dir read-only
```

Enforcement bằng chmod 444 trên files, chmod 555 trên directories.

Lý do: ngăn post-hoc redesign (V6 anti-pattern "quietly retunes after holdout").
Code-level check là backup; filesystem permission là primary enforcement cho
**session immutability** (ngăn sửa artifacts sau freeze).

> **Lưu ý**: "Primary enforcement" ở đây nói về **session immutability** —
> khác với F-04 (contamination firewall) nơi primary enforcement là typed
> schema + state machine. Hai subsystem, hai cơ chế enforcement khác nhau:
> - **Contamination firewall** (F-04): ngăn knowledge leakage → typed schema
> - **Session immutability** (F-11): ngăn post-hoc redesign → filesystem chmod

**Evidence**:
- RESEARCH_PROMPT_V6.md §Stage 6 [extra-archive]: "No redesign or retuning is allowed after this point."
- x37_RULES.md §7.2 [extra-archive]: "Phase 5 là checkpoint bất khả đảo ngược."

**Câu hỏi mở**:
- chmod trên shared filesystem (multi-user) có vấn đề permission?
- Nếu freeze bị lỗi (incomplete artifacts), cách rollback? chmod lại?
- Alternative: hash-based verification thay vì chmod (check SHA-256 artifacts
  thay vì block write)?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | F-04 | F-11 session immutability uses chmod enforcement; F-04 contamination firewall uses typed schema + state machine — overlapping enforcement domains may conflict on which mechanism is authoritative for shared artifacts | 002 owns firewall enforcement; 009 owns immutability enforcement |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-10 | Data management — copies, không symlinks | Judgment call | Open |
| X38-D-11 | Session immutability — filesystem-level | Thiếu sót | Open |
