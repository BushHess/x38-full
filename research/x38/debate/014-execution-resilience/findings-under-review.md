# Findings Under Review — Execution & Resilience

**Topic ID**: X38-T-14
**Opened**: 2026-03-22
**Author**: claude_code (architect)

3 findings về compute orchestration và pipeline resilience.
ER-03 added 2026-03-31 (gap audit).

**Issue ID prefix**: `X38-ER-` (Execution & Resilience).

---

## F-32: Compute orchestration cho exhaustive scans

- **issue_id**: X38-ER-01
- **classification**: Thiếu sót
- **opened_at**: 2026-03-22
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

PLAN.md §1.3 nói framework cần "exhaustive scan (50K+ configs), parallel compute"
nhưng **không có thiết kế** cho compute orchestration. Quy trình online hiện tại
(V4→V8) chạy tuần tự trong 1 conversation — mỗi session scan 1,234 (V8) đến
2,219 (V6) configs. Framework cần scale lên 50K+.

**1. Scale target**:

| Stage | Configs ước lượng | Thời gian tuần tự (est.) | Parallel cần |
|-------|-------------------|--------------------------|--------------|
| Stage 3 (single-feature scan) | 50K+ | ~50 giờ (1 config/3.6s) | Rất cần |
| Stage 5 (layered search) | 500-2K | ~2 giờ | Có lợi |
| Stage 6 (parameter refinement) | 100-500 | ~30 phút | Ít cần |
| Stage 8 (holdout/reserve) | 1-5 | < 1 phút | Không cần |

Stage 3 là bottleneck. Không parallel → mỗi session mất >2 ngày cho feature scan.

**2. Execution model**:
- **Multiprocessing local** (ProcessPoolExecutor): đơn giản, đủ cho 8-32 cores.
  Mỗi worker chạy 1 config (backtest + metrics). Không cần shared state — mỗi
  config independent.
- **Distributed** (Dask, Ray, Celery): cần nếu 1 machine không đủ. Thêm
  complexity đáng kể (serialization, failure modes, scheduling).
- **Hybrid**: local cho stages nhỏ, distributed cho Stage 3 nếu cần.

**3. Data sharing**:
- Bars data (H4+D1 parquet từ data-pipeline): ~50MB loaded. Nếu mỗi worker load riêng → N×50MB RAM.
  Cần shared memory (mmap) hoặc copy-on-write (fork)?
- Feature cache: computed features shared across configs cùng family?
  Có thể tiết kiệm 60-80% compute nếu features cached.

**4. Result aggregation**:
- Mỗi worker output: config + metrics (Sharpe, CAGR, MDD, trades, ...).
- Aggregation: append vào parquet file? In-memory DataFrame? Streaming?
- Ordering: kết quả parallel arrive out-of-order → cần sort hoặc accept unordered.
- Determinism: parallel execution + floating-point → rounding differences?
  Framework claim "deterministic" → cần ensure bit-exact hoặc accept ε tolerance.

**5. Resource management**:
- Memory: 50K configs × N workers. Memory per worker? Cap?
- CPU: saturate tất cả cores hay reserve cho OS?
- Disk: intermediate results persisted → disk I/O bottleneck?

**Evidence**:
- PLAN.md §1.3: "Exhaustive scan (50K+ configs), parallel compute"
- research/x37/docs/gen1/RESEARCH_PROMPT_V6/ [extra-archive]: V6 scanned 2,219 configs within conversation (scan.py)
- research/x37/docs/gen1/RESEARCH_PROMPT_V8/ [extra-archive]: V8 scanned 1,234 configs (stage1_feature_registry.csv)
- btc-spot-dev/v10/core/engine.py [extra-archive]: v10 backtest engine ~3.6s per run (est. từ research scripts)
- docs/research/RESEARCH_RULES.md [extra-archive]: Pattern B (vectorized) vs Pattern A (engine)

**Câu hỏi mở**:
- Local multiprocessing đủ cho v1? Hay distributed là hard requirement?
- Feature caching: engine-level (trong core) hay orchestration-level (wrapper)?
- Determinism: bit-exact hay ε-tolerance? Ảnh hưởng reproducibility claim.
- Scale assumption: 50K là upper bound hay framework nên design cho 500K+?

---

## F-33: Pipeline checkpointing & crash recovery

- **issue_id**: X38-ER-02
- **classification**: Thiếu sót
- **opened_at**: 2026-03-22
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Pipeline 8 stages chạy hàng giờ (Stage 3 có thể >1 ngày nếu tuần tự). Crash
giữa chừng — mất điện, OOM, bug — là inevitable. Framework cần checkpointing
strategy.

**1. Checkpoint granularity**:

| Cấp độ | Ưu | Nhược |
|--------|-----|-------|
| Per-stage | Đơn giản. Stage N xong → persist artifacts → Stage N+1 bắt đầu. Crash → restart từ stage cuối. | Mất toàn bộ stage nếu crash giữa chừng. Stage 3 (50K configs) mất nhiều nhất. |
| Per-batch | Stage 3 chia thành batches (1K configs/batch). Crash → resume từ batch cuối. | Phức tạp hơn. Cần track batch progress. |
| Per-config | Mỗi config result persisted ngay. Crash → resume từ config cuối. | Disk I/O overhead. Nhưng safest. |

**2. Idempotency**:

Resuming sau crash PHẢI cho kết quả giống chạy liền:
- Cùng seed → cùng result (deterministic engine)
- Partial results + resume = full results (no duplication, no gap)
- Aggregation idempotent: re-running không tạo duplicate entries

**3. State file**:

Cần 1 file track pipeline progress:
```json
{
  "session_id": "s01",
  "current_stage": 3,
  "stage_3_progress": {"completed": 42000, "total": 50000, "last_batch": 42},
  "stages_completed": [1, 2],
  "started_at": "2026-03-22T10:00:00Z",
  "last_checkpoint": "2026-03-22T14:30:00Z"
}
```

Nhưng state file = thêm complexity + failure mode (corrupt state file).
Tradeoff: đơn giản (per-stage, no state file, artifact existence = checkpoint)
vs robust (per-batch, state file, resume chính xác).

**4. Cleanup sau crash**:

Partial artifacts từ stage bị crash:
- Delete và re-run toàn bộ stage? (safe, simple, wastes compute)
- Validate partial artifacts và resume? (efficient, complex, risk corrupt data)
- Stage 3 partial parquet: append-safe hay corrupt-on-crash?

**5. Human interaction model (CLI)**:

Framework cần commands cơ bản:
- `alpha-lab run` — chạy full pipeline (campaign + sessions)
- `alpha-lab resume` — resume từ checkpoint sau crash
- `alpha-lab status` — xem progress hiện tại
- `alpha-lab validate` — validate artifacts integrity

CLI là thin layer nhưng interaction model ảnh hưởng checkpointing design:
nếu CLI hỗ trợ resume → pipeline phải checkpointable. Nếu chỉ run/re-run
→ per-stage checkpoint đủ.

**Evidence**:
- PLAN.md §2.3: target directory có `campaigns/` (immutable after close)
  → artifacts phải persist reliably
- x37_RULES.md §7 [extra-archive]: "Chỉ bắt đầu Phase N+1 khi outputs tối thiểu
  của Phase N đã tồn tại" → phase gating = natural checkpoint
- PLAN.md §1.3: "Mọi intermediate result persisted (parquet/JSON)"
  → persistence already a goal, nhưng crash recovery chưa designed

**Câu hỏi mở**:
- Per-stage checkpoint đủ cho v1? Hay per-batch cần từ đầu (vì Stage 3 quá lớn)?
- State file hay artifact-existence-based? (simpler: "if stage3.parquet exists
  and has N rows → stage 3 done")
- Resume: automatic (detect crash, resume) hay manual (human chạy `resume`)?
- Partial artifact policy: delete-and-rerun hay validate-and-resume?

---

## F-40: Session concurrency model

- **issue_id**: X38-ER-03
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0 (gap audit)
- **current_status**: Open

**Chẩn đoán**:

Topic 001 (Campaign model) defines: "N sessions độc lập trên cùng dataset."
Nhưng "độc lập" chưa address:

1. **Serial hay parallel?** — N sessions chạy tuần tự (s001 xong → s002 bắt đầu)
   hay song song (s001 và s002 cùng lúc)?
   - Serial: đơn giản, không resource contention. Nhưng N sessions × Stage 3
     (50K configs) = N × 2 ngày = chậm.
   - Parallel: nhanh, nhưng cần resource isolation (RAM, CPU, disk I/O).

2. **Resource sharing**: Nếu parallel — sessions share data (cùng parquet files
   từ data-pipeline output)? Share feature cache? Per F-10: data-pipeline là
   shared source, campaign verifies checksum — không cần copy riêng.

3. **Independence guarantee**: "Độc lập" nghĩa là KHÔNG information leak giữa
   sessions. Parallel sessions trên cùng machine: shared filesystem, shared
   memory? Cần process isolation?

4. **Scale**: N = bao nhiêu? Topic 013 CA-02 says S_min=3, S_max=5. 5 parallel
   sessions × 50K configs = 250K backtests. Compute resource estimate?

**Câu hỏi cần debate**:

| Position | Mô tả | Tradeoff |
|----------|--------|----------|
| A: Serial sessions | s001 → s002 → ... → s00N. Simple. Independence by construction | Slow: N × 2+ days per campaign |
| B: Parallel sessions, shared data read-only | Sessions read same data-pipeline output (parquet, read-only). Each session writes to own directory. OS-level isolation | Fast, moderate complexity. No data duplication |
| C: Parallel sessions, full isolation | Each session gets own process space + own data-pipeline snapshot. Docker/VM per session | Maximum isolation, highest resource cost |
| D: v1 serial, v2 parallel | Ship simple, optimize later | Fast v1, but architectural decisions now may block parallelism later |

**Evidence**:
- Topic 001 D-03: "N sessions độc lập"
- Topic 013 CA-02: S_min=3, S_max=5 (provisional)
- F-10 (Topic 009): data-pipeline output + SHA-256 checksum — shared data source, campaign verifies integrity
- F-11 (Topic 009): session immutability — chmod enforcement
- ER-01 (this topic): compute orchestration addresses intra-session parallelism
  (50K configs), NOT inter-session parallelism. ER-03 addresses inter-session.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Execution model (F-32/F-33) depends on protocol stages being finalized — but 003 is Wave 3 (last), while 014 needs stage definitions to design orchestration and checkpointing | 003 owns stage definitions; 014 designs execution against preliminary stage structure |
| 005 | F-07 | Core engine rebuild (F-07) must be finalized before orchestration can design worker model — engine API (vectorized vs event-loop) determines parallelization strategy | 005 owns engine design; 014 adapts orchestration |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-ER-01 | Compute orchestration cho exhaustive scans | Thiếu sót | Open |
| X38-ER-02 | Pipeline checkpointing & crash recovery | Thiếu sót | Open |
| X38-ER-03 | Session concurrency model | Thiếu sót | Open |
