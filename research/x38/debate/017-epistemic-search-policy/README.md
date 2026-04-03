# Topic 017 — Epistemic Search Policy (SPLIT)

**Topic ID**: X38-T-17
**Opened**: 2026-03-24
**Status**: **SPLIT** (2026-04-03)

## Split rationale

Topic 017 had 6 findings (488 lines), 212-line README, and 10 cross-topic tensions
— the largest open topic in the system. The internal staging (Stage A: v1, Stage B:
v2) already acknowledged two distinct decision domains:

1. **Intra-campaign** (v1): What a single campaign produces + how it allocates compute
2. **Inter-campaign** (v2): Memory contracts between campaigns + promotion lifecycle

Splitting along this boundary yields two benefits:

1. **Reduced debate complexity**: 3 findings per sub-topic instead of 6 + 10 tensions
2. **Scheduling improvement**: Topic 003 (protocol engine) only needs 017A (v1 pipeline
   modifications). 017B (v2 contracts) can debate in parallel with 003 — no longer on
   the critical path.

The dependency chain is **not linear** as originally claimed (ESP-01→02→03→04):
```
SSE-04-CELL → ESP-01 → ESP-02 → ESP-03
                ↓
              ESP-04
```
ESP-04 depends on ESP-01 (cells), not ESP-02/03. This means 017A (ESP-01, ESP-04,
SSE-04-CELL) and 017B (ESP-02, ESP-03, SSE-08-CON) are naturally separable with
017A outputs feeding 017B inputs.

## Sub-topics

| Sub-topic | Dir | Findings | Scope | Deps |
|-----------|-----|----------|-------|------|
| **017A** | `017A-intra-campaign-esp/` | ESP-01, ESP-04, SSE-04-CELL (3) | v1: illumination, budget governor, cell axes | All CLOSED (002, 008, 010, 013, 018) |
| **017B** | `017B-inter-campaign-esp/` | ESP-02, ESP-03, SSE-08-CON (3) | v2: phenotype contracts, promotion ladder, contradiction consumption | 017A (must close first) |

## Finding index

| Issue ID | Finding | Sub-topic | Status |
|----------|---------|-----------|--------|
| X38-ESP-01 | Intra-campaign illumination (Stages 3-8) | 017A | Open |
| X38-ESP-04 | Budget governor & anti-ratchet | 017A | Open |
| X38-SSE-04-CELL | Cell-axis values + anomaly thresholds | 017A | Open |
| X38-ESP-02 | CandidatePhenotype & StructuralPrior contracts | 017B | Open |
| X38-ESP-03 | Inter-campaign promotion ladder | 017B | Open |
| X38-SSE-08-CON | Contradiction consumption semantics | 017B | Open |

## Wave assignment (updated)

```
Wave 2.5:  017A (intra-campaign ESP) — parallel with 016, 019
           017B (inter-campaign ESP) — sequential after 017A
               ↓
Wave 3:    003 (protocol engine) — needs 017A; 017B can run parallel
```

## Original files (preserved for reference)

| File | Purpose |
|------|---------|
| `findings-under-review.md` | Original 6 findings (488 lines) — canonical copy now in 017A + 017B |
