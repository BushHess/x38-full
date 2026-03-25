# D1f2 Report — Registries & Portfolio State

## Candidate Registry

Đã tạo `candidate_registry.json`

**Tóm tắt:**

| Field | Value |
|---|---|
| `program_lineage_id` | btc_spot_mainline_lineage_001 |
| `constitution_version` | 4.0 |
| `system_version_id` | V1 |
| `parent_system_version_id` | null |
| `freeze_cutoff_utc` | 2026-03-18T23:59:59.999000+00:00 |
| `design_inputs_end_utc` | 2026-03-18T23:59:59.999000+00:00 |
| `evidence_clean_since_utc` | 2026-03-19T00:00:00+00:00 |
| `active_champion_id` | btcsd_20260318_c3_trade4h15m |

**Live candidates:**

- `btcsd_20260318_c3_trade4h15m` — role champion, status active, holdout_flag PASS
- `btcsd_20260318_c1_av4h` — role challenger, status active, holdout_flag FAIL

**Retired candidates:**

- `btcsd_20260318_c2_flow1hpb` — retired pre-freeze vì không có config đại diện nào sống qua discovery hard constraints, và không có ablation simplification hợp lệ để thay slot.

Mỗi live candidate đã có:

- `current_evidence_label` = INTERNAL_SEED_CANDIDATE
- `cumulative_anchor_utc` = 2026-03-19
- `decision_eligibility` = {days: 90, entries: 6}
- `cumulative_forward_metrics` khởi tạo về 0/null
- rule refs đúng theo vai trò champion/challenger

## Meta-Knowledge Registry

Đã tạo `meta_knowledge_registry.json`

**Số lượng entry theo tier:**

| Tier | Count |
|---|---|
| Tier1_Axiom | 4 |
| Tier2_StructuralPrior | 2 |
| Tier3_SessionNote | 9 |

**Các nhóm nội dung chính:**

- **Tier 1:** no lookahead, UTC alignment, next-open execution, no synthetic bar repair
- **Tier 2:** microstructure không thuộc mainline swing-horizon; layering là giả thuyết cần chứng minh chứ không phải mặc định
- **Tier 3:** các phát hiện phiên này như D1/H4 slow-trend mạnh nhất, taker-flow thiên về exhaustion/reversal, relative volume mạnh về magnitude hơn direction, daily gaps nhiễu, blind stacking 1h→15m yếu, c1 fail holdout activity, c3 pass holdout nhưng reserve yếu, và cả hai live candidates đều còn cờ ABLATION_FAIL

Mỗi entry đều có đủ:

- `rule_id`, `statement`, `tier`, `basis`, `scope`
- `authority`, `provenance`, `overlap_guard`
- `challenge_rule`, `expiry`, `status`

## Portfolio State

Đã tạo `portfolio_state.json`

**Trạng thái top-level:**

| Field | Value |
|---|---|
| `state_pack_version` | state_pack_v1 |
| `active_champion_id` | btcsd_20260318_c3_trade4h15m |
| `active_challenger_ids` | ["btcsd_20260318_c1_av4h"] |
| `current_forward_status` | not_started |
| `forward_boundary_utc` | 2026-03-18T23:59:59.999000+00:00 |
| `last_evaluated_timestamp_by_timeframe_utc` | tất cả null |

**Per-candidate state từ `d1e_terminal_states.json`:**

### `btcsd_20260318_c3_trade4h15m`

- `position_state`: flat
- `position_fraction`: 0.0
- `entry_time_utc`: null
- `entry_price`: null
- `trail_state`: null
- `custom_state` giữ nguyên từ terminal state
- `last_signal_time_utc`: 2026-03-18T23:29:59.999000+00:00
- `reconstructable_from_warmup_only`: true

### `btcsd_20260318_c1_av4h`

- `position_state`: flat
- `position_fraction`: 0.0
- `entry_time_utc`: null
- `entry_price`: null
- `trail_state`: null
- `custom_state` giữ nguyên từ terminal state
- `last_signal_time_utc`: 2026-03-18T15:59:59.999000+00:00
- `reconstructable_from_warmup_only`: true

**Warmup requirements đã ghi rõ để replay xác định:**

| Timeframe | Requirement |
|---|---|
| 15m | 168 closed bars |
| 1h | 0 (không có live candidate nào dùng trực tiếp) |
| 4h | 168 closed bars |
| 1d | 448 closed bars, kèm cờ `full_prior_history_required = true` vì candidate champion có daily trade model cần refit trên toàn bộ D1 history đã đóng trước forward boundary để replay bit-identical |

## Evidence Labels

Tất cả live candidates đều được gán: **INTERNAL_SEED_CANDIDATE**

## Files Created

- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`

---

**Sẵn cho D1f3.**
