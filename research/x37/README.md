# X37 — First-Principles Discovery Arena

**Status**: READY_NO_ACTIVE_SESSIONS  
**Current protocol**: `docs/gen1/RESEARCH_PROMPT_V4.md`

`x37` là arena để chạy các **discovery session độc lập**. Mỗi session là một
research run hoàn chỉnh từ Phase 0 đến Phase 6, không phải một sub-question nhỏ
kiểu `branches/a_...` như `x34-x36`.

## Operating model

- Mỗi session tự chứa toàn bộ hypothesis, code, output, và verdict của chính nó.
- `shared/` chỉ chứa infrastructure primitives dùng lại giữa sessions.
- `docs/` và `resource/` là frozen inputs, chỉ đọc.
- Root wrapper chỉ chạy **một phase được chỉ định rõ**; không auto-advance qua
  nhiều phase trong một lần gọi.

## Session Registry

| Session | Agent | Prompt | Status | Phase reached | Verdict | Ghi chú |
|---------|-------|--------|--------|---------------|---------|---------|
| *(chưa có session nào)* | | | | | | |

Authority:
- `manifest.json` là source of truth cho session registry.
- Bảng trong `README.md` và `PLAN.md` là human-readable mirrors của manifest.

## Frozen Inputs

| Path | Vai trò | Ghi chú |
|------|---------|---------|
| `docs/gen1/RESEARCH_PROMPT_V0.md` .. `docs/gen1/RESEARCH_PROMPT_V4.md` | Prompt history | V4 là current protocol |
| `resource/gen1/v1_dipD1/` | Prior discovery run | Read-only comparator / weak prior |
| `resource/gen1/v2_trendvol_d1_only/` | Prior discovery run | Read-only comparator / weak prior |
| `resource/gen1/v3_macroHyst/` | Prior discovery run | Read-only comparator / weak prior |
| `resource/gen1/v4_macroHystB/` | Prior discovery run (x37v4) | Read-only comparator. V4_COMPETITIVE vs E5_ema21D1 (Branch A) |

## Control Files

- [PLAN.md](PLAN.md): session registry, dependency graph, operating state
- [x37_RULES.md](x37_RULES.md): write/read zones, session lifecycle, phase gating
- [manifest.json](manifest.json): machine-readable architecture and session registry
- [sessions/README.md](sessions/README.md): cách mở session mới đúng chuẩn
- [analysis/README.md](analysis/README.md): rule cho cross-session analysis
- [code/run_all.py](code/run_all.py): phase runner an toàn cho session ACTIVE
- [code/audit_x37.py](code/audit_x37.py): consistency audit cho manifest, rules, templates, runner

## Branches (x36-style)

Ngoài session system, x37 có thêm `branches/` cho các **focused comparison tasks**
không phải full Phase 0-6 discovery. Pattern này giống `x34-x36`.

| Branch | Purpose | Status | Verdict |
|--------|---------|--------|---------|
| `a_v4_vs_e5_fair_comparison` | V4 macroHystB (x37v4) vs E5_ema21D1 head-to-head at 20 bps RT | **DONE** | V4_COMPETITIVE (3/4, WFO underpowered) |

## Root Layout

```text
x37/
├── README.md
├── PLAN.md
├── manifest.json
├── x37_RULES.md
├── docs/
│   ├── gen1/               # frozen prompt versions (V0-V8)
│   └── gen2/               # new generation prompts
├── resource/
│   ├── gen1/               # frozen prior discovery runs (v1-v8)
│   └── gen2/               # new generation session outputs
├── shared/                 # reusable infrastructure only
├── sessions/               # templates + session directories
├── branches/               # x36-style focused comparison branches
├── analysis/               # derivative analysis from completed sessions only
├── code/                   # root wrappers only
└── results/                # root index only
```

## References

- Protocol: [docs/gen1/RESEARCH_PROMPT_V4.md](docs/gen1/RESEARCH_PROMPT_V4.md)
- Global research rules: [../../docs/research/RESEARCH_RULES.md](../../docs/research/RESEARCH_RULES.md)
- Repo policy: [../../CLAUDE.md](../../CLAUDE.md)
