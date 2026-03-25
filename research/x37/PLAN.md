# X37 — Master Plan

`x37` là **research arena** để nhiều agent có thể mở các discovery session độc lập
trên cùng protocol V4 mà vẫn giữ được isolation, preregistration, và benchmark embargo.

## Current Operating State

- Study status: `READY_NO_ACTIVE_SESSIONS`
- Current prompt: `docs/gen1/RESEARCH_PROMPT_V4.md`
- Open sessions: none
- Cross-session analysis: not yet active

Root study-status rule:
- `READY_NO_ACTIVE_SESSIONS`: không có session `ACTIVE`
- `ACTIVE_SESSIONS_PRESENT`: có ít nhất 1 session `ACTIVE`

## X37 vs X34–X36

| Pattern cũ | X37 tương đương | Ý nghĩa |
|------------|------------------|---------|
| `branches/<branch>/` | `sessions/sNN_<descriptor>/` | Mỗi session là full research run |
| `program/` ở root | phase artifacts nằm trong session | Program docs gắn với từng run |
| `shared/` | `shared/` | Chỉ chứa infrastructure dùng lại |
| `resource/` | `resource/` | Frozen prior discoveries để so sánh / weak prior |

## Session Registry

| ID | Directory | Agent | Prompt | Status | Phase reached | Verdict | Notes |
|----|-----------|-------|--------|--------|---------------|---------|-------|
| *(chưa có session)* | | | | | | | |

Registry authority:
- `manifest.json` là canonical source.
- Bảng ở đây chỉ là mirror để đọc nhanh.

## Dependency Graph

```text
session PLAN preregistered
        │
        ▼
phase0 protocol freeze
        │
        ▼
phase1 data decomposition
        │
        ▼
phase2 hypotheses locked
        │
        ▼
phase3 minimal design
        │
        ▼
phase4 parameter selection
        │
        ▼
phase5 freeze -> holdout -> mandatory evals
        │
        ▼
Appendix A unlock
        │
        ▼
phase6 benchmark comparison
        │
        ▼
verdict + root registry update
```

## Root-Level Guardrails

- Root wrapper `code/run_all.py` chỉ chạy **phase được yêu cầu rõ**; không scan rồi
  chạy tuần tự mọi `run_phase*.py` như một pipeline tự động.
- Phase 5 là checkpoint bất khả đảo ngược: khi freeze artifact đã xuất hiện
  (`frozen_spec.md`, `frozen_spec.json`, hoặc holdout artifact), không được rerun
  qua root wrapper.
- Phase 6 cũng được coi là touched ngay khi artifact benchmark đầu tiên xuất hiện;
  từ điểm đó, mọi rerun phải qua human review thay vì root wrapper.
- Phase 6 chỉ mở khi Phase 5 đã có đủ các artifacts bắt buộc: holdout, regime,
  cost, bootstrap #7a, trade distribution.
- `analysis/` chỉ đọc sessions đã `DONE` hoặc `ABANDONED`; không bao giờ viết ngược
  vào session.

## Frozen Inputs

### Prompt history

| Version | File | Role |
|---------|------|------|
| V0 | `docs/gen1/RESEARCH_PROMPT_V0.md` | Historical prompt snapshot |
| V1 | `docs/gen1/RESEARCH_PROMPT_V1.md` | Historical prompt snapshot |
| V2 | `docs/gen1/RESEARCH_PROMPT_V2.md` | Historical prompt snapshot |
| V3 | `docs/gen1/RESEARCH_PROMPT_V3.md` | Historical prompt snapshot |
| V4 | `docs/gen1/RESEARCH_PROMPT_V4.md` | Current protocol |

### Prior discovery runs

| Resource | Role | Allowed use |
|----------|------|-------------|
| `resource/gen1/v1_dipD1/` | Prior system | Weak prior, pipeline sanity check, post-Phase 6 comparison |
| `resource/gen1/v2_trendvol_d1_only/` | Prior system | Weak prior, pipeline sanity check, post-Phase 6 comparison |
| `resource/gen1/v3_macroHyst/` | Prior system | Weak prior, post-Phase 6 comparison |
| `resource/gen1/v4_macroHystB/` | Prior system (x37v4) | V4_COMPETITIVE vs E5_ema21D1 (Branch A, 2026-03-17) |

Allowed use follows `RESEARCH_PROMPT_V4`:
- Use as weak prior or comparator.
- Do not skip Phase 1 measurement because of them.
- Do not use them to suppress a direction before current unseen-data evidence exists.

## Branches (x36-style)

Focused comparison tasks that don't follow the full Phase 0-6 discovery pipeline.
These use x36-style `branches/` layout, authorized by researcher.

| Branch | Purpose | Status | Verdict | Notes |
|--------|---------|--------|---------|-------|
| `a_v4_vs_e5_fair_comparison` | V4 macroHystB (x37v4) vs E5_ema21D1 at standardized 20 bps RT | **DONE** | V4_COMPETITIVE (3/4) | [PLAN](branches/a_v4_vs_e5_fair_comparison/PLAN.md), [REPORT](branches/a_v4_vs_e5_fair_comparison/REPORT.md) |

## Operational Notes

- Session creation flow lives in [sessions/README.md](sessions/README.md).
- Cross-session outputs belong in [analysis/README.md](analysis/README.md).
- Detailed write/read-zone and lifecycle rules live in [x37_RULES.md](x37_RULES.md).
- Consistency audit lives in [code/audit_x37.py](code/audit_x37.py).
