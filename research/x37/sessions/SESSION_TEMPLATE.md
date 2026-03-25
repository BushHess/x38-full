# Session sNN_<descriptor> — PLAN

Copy file này thành `sessions/sNN_<descriptor>/PLAN.md` rồi thay toàn bộ placeholder.
Quick start nằm ở [sessions/README.md](README.md).

## Preregistration

- **Session ID**: sNN
- **Prompt version**: V4
- **Agent**: <agent_name> (model, version)
- **Date started**: <YYYY-MM-DD>
- **Data file**: `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- **Prior completed sessions read**: None | `sNN_<descriptor>` (weak prior only)
- **Cross-session analysis used**: None | `analysis/...`

## Scope (from RESEARCH_PROMPT_V4)

- Market: BTC/USDT spot, long-only
- Timeframes available: H4, D1
- Signal timing: bar close → next bar open
- Cost: 10 bps/side, 20 bps round-trip (stress test: 50 bps RT)
- Warmup: 2017-08-17 → 2018-12-31 (no trading)
- Development: 2019-01-01 → 2023-12-31
- WFO: ≥ 4 non-overlapping test windows, each ≤ 12 months (exact windows in protocol_freeze.json)
- Holdout (untouched until Phase 5 freeze checkpoint): 2024-01-01 → 2026-02-20
- Complexity: max 4 tunables, broad plateau required
- D1-H4 alignment: <SPECIFY: `allow_exact_matches` = true or false, see protocol_freeze.json>

## Governance Acknowledgements

- Appendix A benchmark specs are embargoed until Phase 5 mandatory outputs are complete.
- Session logic stays inside this session directory; `shared/` is infrastructure-only.
- This session does not read `research/x0/` .. `research/x36/` directly.

## Protocol deviations

(Liệt kê mọi deviation so với RESEARCH_PROMPT_V4, hoặc ghi "None")

## Phase tracker

| Phase | Status | Key outputs |
|-------|--------|-------------|
| 0 — Protocol lock | PENDING | `protocol_freeze.json` |
| 1 — Data decomposition | PENDING | measurements.csv, channel_report.md, d1_h4_alignment.json |
| 2 — Hypothesis generation | PENDING | hypotheses.md (3–5 candidates) |
| 3 — Minimal system design | PENDING | candidate code + ablation results |
| 4 — Parameter selection | PENDING | search_results.csv, plateau_test.csv |
| 5 — Freeze + holdout | PENDING | frozen_spec.json → holdout → evals #2,4,5,7a,8 |
| 6 — Benchmark comparison | PENDING | Appendix A unlocked → paired bootstrap (eval #7b) |

## Mandatory Evaluation Checklist

8 evaluations từ RESEARCH_PROMPT_V4, mỗi eval thuộc về phase cụ thể:

**Phase 3 (design):**
- [ ] #6 Component ablation — mỗi component phải earn its place trên unseen data

**Phase 4 (parameters):**
- [ ] #3 Parameter plateau test (±20% perturbation)

**Phase 3–4 (ongoing):**
- [ ] #1 Walk-forward validation on unseen development windows

**Phase 5 (freeze → holdout → evals, TRƯỚC khi đọc Appendix A):**
- [ ] #2 Final untouched holdout evaluation
- [ ] #4 Regime decomposition across major epochs
- [ ] #5 Cost sensitivity analysis (including 50 bps RT stress)
- [ ] #7a Bootstrap robustness with block-size sensitivity (standalone, unpaired)
- [ ] #8 Trade-distribution analysis (winner truncation, churn, fragility)

**Phase 6 (benchmark comparison, SAU Phase 5 hoàn thành + Appendix A unlocked):**
- [ ] #7b Paired bootstrap vs benchmarks (same resampled paths)

## Verdict

*(Ghi sau Phase 6, hoặc khi abandon)*

Canonical verdict nằm ở `verdict/verdict.json` (machine-readable) và
`verdict/final_report.md` (human-readable). Khi viết xong, copy verdict summary
vào block dưới đây để PLAN.md tự chứa đầy đủ.

**Authority**: `verdict/verdict.json` là authoritative. Block dưới đây là mirror.

```json
{
  "verdict": "SUPERIOR | COMPETITIVE | NO_ROBUST_IMPROVEMENT | ABANDONED",
  "system_name": "",
  "full_sample_sharpe": null,
  "holdout_sharpe": null,
  "holdout_cagr": null,
  "holdout_trades": null,
  "phase_reached": null,
  "abandon_reason": null
}
```

## Abandon reason

*(Chỉ ghi nếu verdict = ABANDONED. Xem x37_RULES.md mục Abandon Criteria.)*
