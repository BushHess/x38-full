# X34 Debate — Final Resolution

**Topic ID**: `X34-DB-01`
**Topic**: Các phát hiện của X34
**Closed at**: `2026-03-13T18:10:00Z`
**Rounds**: 3 (phiên mới)
**Participants**: claude_code, codex

---

## Summary

10 issues opened, all resolved: **8 Converged**, **2 Judgment call**.

## Converged Issues (8)

| Issue ID | Finding | Resolution | Round |
|---|---|---|---:|
| X34-D-01 | F-01: Entry logic wording | Sửa "positive flow → accelerating flow" thành "positive momentum of raw flow → positive momentum of volume-normalized flow vượt adaptive noise floor". Baseline cũng oscillator. | prior |
| X34-D-02 | F-03: Holdout overclaim | Sửa "không phải noise" thành "gợi ý conditional edge nhưng chưa xác lập thống kê". Wilcoxon/Bootstrap/PSR đều fail. | prior |
| X34-D-04 | F-10: Diagnostic GO vs REJECT | Giữ nguyên wording "Đây không phải chi tiết nhỏ — bài học phương pháp". Steel-man (anticipated path = low salience) bị bác: anticipated path ≠ trivial outcome; X34 data (ρ=0.887, 2x selectivity, +68% range) vẫn cho vivid illustration. Codex precision: thêm frequency flag 0.4774. | 3 |
| X34-D-05 | F-04: Veto breakdown | Thêm regime breakdown (50/50 high/low vol, 52/48 up/down) bác narrative "chỉ cắt rác". Thêm asymmetric impact: bull -48%, chop -41%, bear +15%. | 2 |
| X34-D-06 | F-08: Risk concentration | Giữ buy_fills_per_episode (8.94 vs 6.82) trong nuance section. Metric giải thích cơ chế nhưng không đổi kết luận core. | 2 |
| X34-D-07 | F-09: Cost/alpha tradeoff | Gross alpha loss > cost savings. Crossover ~75 bps >> measured 16.8 bps. | prior |
| X34-D-09 | Meta-insight: Causal overclaim | Sửa "vì" → "nhất quán với hiện tượng" (xem F-07). Thêm "X34 chưa có per-trade tail attribution." Minimal fix, consistent với F-07 corrections. | 2 |
| X34-D-10 | F-07: Win rate thiếu | Thêm: win rate +2.1pp (42.21% vs 40.10%), net 12 fewer wins / 26 fewer losses. Upside compression > downside compression. | 2 |

## Judgment Calls (2)

### X34-D-03 — F-02 tier placement

**Tradeoff**:
- **Tier 1** (codex): Ranh giới falsification (tested vs untested components) là structural bookkeeping. Spec/code tách `momentum`, `level`, `hysteresis` → xác định đối tượng bị falsify thay đổi hiểu biết cấu trúc.
- **Tier 2** (claude_code): Finding mô tả evidence scope, không phải system behavior. F-01/F-03 mô tả system behavior → Tier 1 core. F-02 mô tả coverage → Tier 2.

**Decision owner**: user
**Resolved in**: round 2

### X34-D-08 — F-05 cross-reference X16/X17

**Tradeoff**:
- **Bỏ cross-ref**: Dossier self-contained, reader không cần X16/X17 background (stateful exit, WATCH — rất khác scope).
- **Giữ cross-ref**: X34 nằm rõ hơn trong project-wide pattern (regime conditioning consistently hurts).

**Decision owner**: user
**Resolved in**: round 2

---

## Changes Applied to findings-under-review.md

1. **F-02**: Added Judgment call note (tier placement tradeoff, user decides)
2. **F-04**: Added veto regime breakdown + asymmetric impact data
3. **F-05**: Added Judgment call note (cross-ref tradeoff, user decides)
4. **F-07**: Added win rate +2.1pp observation with compression asymmetry
5. **F-08**: Updated review_status to Converged (nuance placement confirmed)
6. **F-10**: Updated review_status to Converged, added frequency flag 0.4774,
   adjusted wording "mọi signal metric" → "nhiều đặc tính signal-space"
7. **Meta-insight**: Replaced "vì" with "nhất quán với hiện tượng (xem F-07).
   X34 chưa có per-trade tail attribution."
8. **Issue Index**: Updated all statuses + added "Resolved in" column

---

## Artifact Trail

| Round | claude_code | codex |
|---:|---|---|
| 1 | [opening-critique](claude_code/2026-03-13/round-1_opening-critique.md) | [rebuttal](codex/2026-03-13/round-1_rebuttal.md) |
| 2 | [author-reply](claude_code/2026-03-13/round-2_author-reply.md) | [reviewer-reply](codex/2026-03-13/round-2_reviewer-reply.md) |
| 3 | [author-reply](claude_code/2026-03-13/round-3_author-reply.md) | [reviewer-reply](codex/2026-03-13/round-3_reviewer-reply.md) |
