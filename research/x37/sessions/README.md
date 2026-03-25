# X37 Sessions

`sessions/` chứa 2 loại nội dung:

- templates dùng để mở session mới
- các thư mục `sNN_<descriptor>/` là research sessions thật

## Open A New Session

1. Chọn session ID tiếp theo: `sNN_<descriptor>`.
2. Tạo session tree:

```bash
mkdir -p research/x37/sessions/sNN_<descriptor>/{phase0_protocol,phase1_decomposition/{code,results/figures},phase2_hypotheses,phase3_design/{code/candidates,results},phase4_parameters/{code,results},phase5_freeze/{code,results/figures},phase6_benchmark/{code,results},verdict/figures}
```

3. Copy template PLAN:

```bash
cp research/x37/sessions/SESSION_TEMPLATE.md research/x37/sessions/sNN_<descriptor>/PLAN.md
```

4. Copy protocol freeze template:

```bash
cp research/x37/sessions/PROTOCOL_FREEZE_TEMPLATE.json research/x37/sessions/sNN_<descriptor>/phase0_protocol/protocol_freeze.json
```

5. Điền đầy đủ:
- exact WFO windows
- `allow_exact_matches` bằng boolean thật
- agent / prompt / scope / deviation

6. Cập nhật root registry:
- `README.md`
- `PLAN.md`
- `manifest.json`

Manifest entry tối thiểu phải có dạng:

```json
{
  "id": "sNN_<descriptor>",
  "path": "sessions/sNN_<descriptor>/",
  "status": "PLANNED",
  "agent": "<agent label>",
  "prompt_version": "V4",
  "started_at": "YYYY-MM-DD",
  "phase_reached": 0,
  "verdict": null,
  "notes": "short note or null"
}
```

7. Chạy audit:

```bash
/var/www/trading-bots/.venv/bin/python research/x37/code/audit_x37.py
```

## Safe Execution

Root runner không tự chạy tất cả phases. Dùng rõ ràng:

```bash
/var/www/trading-bots/.venv/bin/python research/x37/code/run_all.py --session sNN_<descriptor> --phase 1
/var/www/trading-bots/.venv/bin/python research/x37/code/run_all.py --session sNN_<descriptor> --phase 3
```

Notes:

- Phase 2 là manual artifact: `phase2_hypotheses/hypotheses.md`
- Phase 5 là irreversible; khi freeze artifact đã tồn tại (`frozen_spec.md`,
  `frozen_spec.json`, hoặc holdout artifact), root runner sẽ chặn rerun
- Phase 6 chỉ mở khi Phase 5 mandatory outputs đã đủ
- Nếu Phase 5/6 đã bị chạm một phần, root runner không resume; phải human-review trước

## Registry Discipline

Mọi session phải được đăng ký nhất quán ở:

- `README.md`
- `PLAN.md`
- `manifest.json`

Khi session đóng (`DONE` hoặc `ABANDONED`), session directory trở thành read-only.
