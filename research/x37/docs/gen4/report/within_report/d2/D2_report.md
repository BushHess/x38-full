# D2 Report — State Pack Packaging

## Packaged Files

Đã đóng gói xong:

- `state_pack_v1.zip`
- `state_pack_v1_inventory.txt`

**Bên trong `state_pack_v1` có đủ các artifact yêu cầu:**

- `research_constitution_version.txt`
- `program_lineage_id.txt`
- `system_version_id.txt`
- `system_version_manifest.json`
- `session_summary.md`
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_daily_returns.csv` (header-only)
- `forward_evaluation_ledger.csv` (header-only)
- `contamination_map.md`
- `input_hash_manifest.txt` — dùng nguyên bản manifest đã có trong bundle đầu vào
- `frozen_system_specs/`
  - `btcsd_20260318_c3_trade4h15m.md`
  - `btcsd_20260318_c1_av4h.md`
- `impl/`
  - `btcsd_20260318_c3_trade4h15m.py`
  - `btcsd_20260318_c1_av4h.py`
- `warmup_buffers/`
  - `raw/spot_btcusdt_15m.csv`
  - `raw/spot_btcusdt_4h.csv`
  - `raw/spot_btcusdt_1d.csv`
  - `warmup_manifest.json`

**Ghi chú đóng gói:**

- `warmup_buffers/` được đưa vào vì cả hai live candidates đều có `reconstructable_from_warmup_only: true`, và warmup_requirements có bar count khác 0.
- 1d warmup dùng full prior history tới forward boundary vì champion cần refit daily trade-surprise trên toàn bộ D1 history đã đóng trước boundary để replay bit-identical.
- `forward_daily_returns.csv` đã được tạo header-only để forward evaluation chat sau chỉ việc append.

## Champion Status After Packaging

Không thay đổi sau đóng gói:

- **Champion:** `btcsd_20260318_c3_trade4h15m`
- **Challenger:** `btcsd_20260318_c1_av4h`

**Trạng thái evidence vẫn giữ nguyên:**

- cả hai đều là `INTERNAL_SEED_CANDIDATE`
- chưa có clean forward evidence
- `system_version_id` = V1
- `current_forward_status` = not_started

## Allowed Next Action

Mở chat mới cho `forward_evaluation` khi có delta dữ liệu mới sau `2026-03-18T23:59:59.999000+00:00`, và dùng chính `state_pack_v1` này làm machine handoff duy nhất. Chat mới đó sẽ:

- nạp `state_pack_v1`
- nạp appended forward delta
- cập nhật `forward_daily_returns.csv`
- cập nhật `forward_evaluation_ledger.csv`
- cập nhật `candidate_registry.json` và `portfolio_state.json`
- tạo `state_pack_v2` sau review window phù hợp

## Forbidden Next Action

- Không tiếp tục forward evaluation trong chat hiện tại
- Không rescore, redesign, hay refreeze trong chat này
- Không dùng holdout hoặc reserve_internal như clean forward evidence
- Không chạy seed discovery lại trên cùng snapshot đã freeze
- Không thay đổi bất kỳ frozen candidate nào trong V1

---

**STOP THIS CHAT. OPEN A NEW CHAT FOR FORWARD EVALUATION WHEN THE NEXT REVIEW WINDOW IS READY.**
