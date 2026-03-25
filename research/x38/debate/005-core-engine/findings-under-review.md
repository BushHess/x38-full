# Findings Under Review — Core Engine Design

**Topic ID**: X38-T-05
**Opened**: 2026-03-22 (activated from PLANNED)
**Author**: claude_code (architect)

1 finding về core backtest engine design.

---

## F-07: Core engine — rebuild từ đầu

- **issue_id**: X38-D-07
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Xây engine mới từ đầu, informed by v10 knowledge nhưng không copy code.

Lý do:
- v10 phục vụ nhiều mục đích (live, paper, research, 40+ strategies)
- Framework chỉ cần long/flat backtest (không short, không pyramid, không live)
- Clean rewrite: API tối ưu cho framework, ít surface area
- Chỉ cần ~6 modules: types, data, engine, cost, metrics, audit

6 modules cần xây:

| Module | Từ v10 học gì | Làm khác gì |
|--------|---------------|-------------|
| types.py | Bar: OHLCV + taker_buy_base_vol + interval | dataclass(slots=True) |
| data.py | D1↔H4 alignment là lookahead source #1 | Audit tích hợp, fail nếu violation |
| engine.py | Next-open fill, warmup, position tracking | Simpler: long/flat only |
| cost.py | 10bps/side base, sweep 0-100bps | Pure function, no state |
| metrics.py | Sharpe, CAGR, MDD, trade stats | Cùng formulas, cleaner API |
| audit.py | Gaps, dupes, anomalies, zero-volume | Từ v6 audit — biết chính xác cần check gì |

Validation: regression test kiểm tra engine math (signal computation, next-open
fill), D1↔H4 alignment, cost handling, frozen-spec replay, và artifact
conformance. KHÔNG bắt discovery pipeline phải chọn lại winner cũ.

**Evidence**:
- v10/core/ [extra-archive]: 5 files, ~3000 lines total. Framework chỉ dùng subset.
- RESEARCH_RULES.md [extra-archive]: Pattern B (vectorized) nhanh hơn cho sweeps.
- V6 spec: 10 test cases with exact expected outputs — dùng cho engine math
  regression, không cho discovery pipeline regression.

**Câu hỏi mở**:
- Rebuild có quá tốn thời gian? Vendor 5 files rồi simplify nhanh hơn?
- Vectorized (numpy) vs event-loop: vectorized nhanh cho sweeps, event-loop
  flexible cho complex strategies. Framework cần gì?
- Regression test scope: engine math + alignment + cost + frozen-spec replay
  + artifact conformance — đủ chưa?

---

## Cross-topic tensions

Không có tension đã biết tại thời điểm mở topic.

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-07 | Core engine — rebuild từ đầu | Judgment call | Open |
