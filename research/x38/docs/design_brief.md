# Alpha-Lab — Design Brief

Tóm tắt thiết kế sơ bộ đã thống nhất qua conversation (2026-03-18).
File này là **input cho debate**, không phải spec chính thức.
Sau debate, các quyết định sẽ được codify vào `drafts/` rồi `published/`.

---

## 1. Vấn đề cần giải quyết

Nghiên cứu thuật toán trading hiện tại chạy qua AI conversation (online):
- V4 → V5 → V6 → V7 → V8: mỗi vòng = 1 conversation với AI
- Handoff qua natural language prompts (lossy, không reproducible)
- Feature scan bị giới hạn bởi context window (~2,219 configs trong V6)
- Contamination tracking phụ thuộc kỷ luật tự báo cáo của AI
- Sessions diverge ở level family/architecture (CONVERGENCE_STATUS_V3.md)

**Mục tiêu**: Biên dịch quy trình online thành framework offline tự động.

---

## 2. Triết lý cốt lõi

> Kế thừa cách nghiên cứu, không kế thừa đáp án.

Từ feedback (2026-03-18):
- Framework KHÔNG hứa "cho ra thuật toán tốt nhất"
- Framework hứa: tìm candidate mạnh nhất TRONG search space đã khai báo
- `NO_ROBUST_IMPROVEMENT` là output hợp lệ, không phải failure
- "Tốt hơn online" = rộng hơn, reproducible hơn, ít contamination hơn, audit tốt hơn

---

## 3. Ba trụ cột (đã thống nhất sơ bộ)

### 3.1 Contamination Firewall

Tách cứng hai tầng knowledge:

**ĐƯỢC kế thừa giữa campaigns**:
- Provenance / audit / serialization rules
- Split hygiene heuristics
- Stop-discipline conditions
- Anti-patterns (methodology-level)

**BỊ CẤM kế thừa**:
- Feature names, lookback values, threshold values
- Winner identity, shortlist priors
- Bất kỳ lesson nào làm nghiêng cán cân family/architecture/calibration-mode

Metadata-level machine enforcement: typed schema + whitelist category + state
machine ký hash cho protocol transitions. Chặn parameter leakage (feature names,
thresholds) qua schema validation. Structural/semantic leakage được bounded qua
Tier 2 metadata (leakage grade, provenance, challenge) — không triệt tiêu (xem
MK-03: irreducible tradeoff). Filesystem read-only là guardrail phụ.

### 3.2 Protocol Engine

V6 protocol compiled thành executable pipeline (**BTC-v1 baseline** — rút từ
V6/V7/V8 lineage, không phải search ontology phổ quát; configurable cho assets khác):

```
Stage 1: Protocol lock
Stage 2: Data audit
Stage 3: Single-feature scan (exhaustive)
Stage 4: Orthogonal pruning
Stage 5: Layered architecture search
Stage 6: Parameter refinement + plateau
Stage 7: Freeze comparison set
Stage 8: Holdout + Internal Reserve evaluation
```

Phase gating: stage N+1 bị chặn cho đến khi stage N artifacts tồn tại.
Freeze checkpoint: sau Stage 7, discovery artifacts trở thành read-only.

### 3.3 Meta-Updater

Sau mỗi campaign, chỉ cập nhật:
- Provenance / audit / serialization rules
- Split hygiene heuristics
- Stop-discipline conditions
- Anti-patterns (methodology-level)

KHÔNG BAO GIỜ cập nhật priors về đáp án. Mọi lesson làm nghiêng cán cân
family, architecture, hoặc calibration-mode đều bị coi là contamination.

**Đã chốt (MK-17)**: Trên cùng exact dataset snapshot, mọi empirical
cross-campaign priors (Tier 2/3) là **shadow-only** trước freeze. Chỉ Tier 1
axioms active. Empirical priors chỉ activate trên genuinely new datasets.

---

## 4. Campaign → Session Model (đề xuất sơ bộ)

```
Campaign = {
    dataset cố định (data snapshot với SHA-256),
    protocol cố định,
    N sessions độc lập,
    convergence analysis,
    meta-knowledge output cho campaign tiếp theo
}
```

**Hai giai đoạn tách biệt**:

```
Giai đoạn 1: NGHIÊN CỨU (N campaigns HANDOFF, cùng data file)
  C1 (N sessions → convergence → meta-lessons L1)
    ↓ HANDOFF (kế thừa methodology, không đáp án; shadow-only on same dataset — MK-17)
  C2 (inherits L1 shadow-only → N sessions → convergence → meta-lessons L2)
    ↓ HANDOFF (hoặc STOP — hard stop governance)
  ... → winner chính thức hoặc NO_ROBUST_IMPROVEMENT

  LƯU Ý: Trên cùng dataset, MK-17 shadow-only nghĩa là C2 gần tương đương
  thêm batch sessions cho C1 — đây là BY DESIGN. Same-data campaigns chủ yếu
  phục vụ convergence audit hoặc corrective re-run (ví dụ: protocol bug fix).
  Meta-learning thực sự phát huy khi campaigns chạy trên genuinely new data.

Giai đoạn 2: CLEAN OOS (chỉ khi đã có winner, chờ data mới)
  Download data mới → replay frozen winner
    ├── CONFIRMED → kết thúc (winner validated)
    ├── INCONCLUSIVE → giữ INTERNAL_ROBUST_CANDIDATE, chờ thêm data (F-21)
    └── FAIL → Giai đoạn 3

Giai đoạn 3: NGHIÊN CỨU LẠI (chỉ khi FAIL, trên data mở rộng)
  Campaign mới trên toàn bộ data (cũ + mới)
  Search space mở, winner cũ FAIL lưu ở provenance (không phải anti-pattern)
  → Lặp lại: Giai đoạn 1 → 2 → ...
```

Clean OOS không phải loại campaign song song. Nó là giai đoạn **sau** khi
nghiên cứu kết thúc. Framework **tự động tạo nghĩa vụ** `PENDING_CLEAN_OOS`
khi (winner chính thức) AND (đủ data mới). Human được chọn thời điểm chạy,
được defer với lý do explicit + ngày review lại, nhưng KHÔNG được im lặng trì
hoãn vô hạn. FAIL không phải kết thúc — nó mở chu kỳ nghiên cứu mới.

Clean OOS evaluation:
- Discovery + selection holdout: đã xong ở giai đoạn 1 (trên data cũ)
- Clean reserve: **chỉ** data mới, chưa ai thấy — không redesign, chỉ replay.
  Phân biệt với "internal reserve" (Stage 8, trên cùng data file, đã contaminate).
- Clean reserve chỉ mở **đúng 1 lần**
- Boundary: executable timestamp contract (bar close_time), không phải date string

Nếu s001 đã mở reserve, s002 không còn clean trên cùng data đó. Giải pháp:
tất cả sessions freeze trên pre-boundary data trước, rồi mở reserve đúng 1 lần.

---

## 5. Cấu trúc thư mục (đề xuất sơ bộ)

```
/var/www/trading-bots/alpha-lab/
├── pyproject.toml
├── CLAUDE.md
├── src/alpha_lab/
│   ├── core/           # Engine (rebuilt, not vendored)
│   ├── features/       # Feature engine (registry + families)
│   ├── discovery/      # 8-stage pipeline
│   ├── validation/     # WFO, bootstrap, plateau, gates
│   ├── campaign/       # Campaign + session + meta
│   └── cli/            # Command-line interface
├── data/               # Refs to data-pipeline output + manifest
├── campaigns/          # Campaign outputs (grow over time)
├── knowledge/          # Accumulated meta-knowledge
└── tests/              # Unit + integration + regression
```

---

## 6. Engine: rebuild từ đầu (đề xuất sơ bộ)

Lý do không vendor từ v10:
- v10 phục vụ nhiều mục đích (live, paper, research, 40+ strategies)
- Framework chỉ cần long/flat backtest engine
- Clean rewrite = ít bug potential, API tối ưu cho framework
- Chỉ cần ~6 modules: types, data, engine, cost, metrics, audit

Data source: `/var/www/trading-bots/data-pipeline/output/` (parquet format).
- **Research scope**: 5 data types — `spot_klines/`, `futures_metrics/`,
  `futures_fundingRate/`, `futures_premiumIndexKlines/`, `aggtrades_bulk/`
- **Loại**: chỉ `bars_multi_4h.parquet` (X20 đã chứng minh multi-asset không hiệu quả)
- Quyết định dùng/loại từng loại thuộc về kết quả nghiên cứu, không thiết kế trước
- Mỗi campaign ghi SHA-256 checksum lúc tạo → reproducibility via checksum
- Không duplicate data — campaign.json trỏ đến data-pipeline output + verify checksum

---

## 7. Câu hỏi mở (cần debate)

1. Campaign model có phải abstraction đúng không? Alternatives?
2. Typed lesson schema + category whitelist: strictness tradeoff?
3. 8 stages hay nên gộp/tách khác?
4. Benchmark embargo bảo vệ selection cleanliness (không chỉ chặn AI peek) — giữ mặc định?
5. Rebuild vs vendor: tradeoff time-to-build vs clean architecture?
6. Feature registry: decorator pattern vs config-driven?
7. Cross-timeframe alignment: engine-level vs feature-level?
8. Stop conditions cho campaign: bao nhiêu sessions NO_ROBUST trước khi dừng?

---

## 8. Tài liệu nguồn

Thiết kế này dựa trên siêu kiến thức từ:

| Source | Key lesson |
|--------|-----------|
| V4 protocol | 6-phase structure, data-first discovery |
| V5 session | Full serialization critical; missing scan universe blocks reproduction |
| V6 session | Broader scan discovers candidates missed by narrow scan; reserve reverses rankings |
| V6 handoff | Transfer methodology not answers; contamination isolation |
| V7 handoff | V7 = final same-file convergence audit; no prior-result bias; same-file iteration has hard stop; reserve = internal-only; human chooses: run V7 / stop / wait new data |
| V8 session | Winner `S_D1_TREND` (simplest possible: 1 feature, 1 param) — khác V7 hoàn toàn. Governance tốt nhất (643 lines) vẫn KHÔNG đảm bảo exact winner convergence. Introduced SPEC_REQUEST_PROMPT (meta-prompt). Input→Logic→Output→Decision spec structure |
| V8 handoff | No same-file iteration beyond V8; contamination log V4 (8 rounds, 1692 lines) |
| Clean OOS doc | Future data for genuine OOS; automatic boundary detection |
| Convergence status | Same-data re-derivation has limits; need new data to arbitrate |
| x37 Rules | Session isolation, phase gating, appendix embargo |
| Contamination log | 8 rounds of specifics (V4 5 rounds + V5 + V6 + V7); union map covers entire file |
| V6/V7 specs | 9 design patterns (schema-first, numeric gates, redundancy audit) + 9 gaps |
| Expert feedback | 3 mandatory components; honest promise; V6 ≈ 80% of framework |
| V8 resource specs | spec_1 (866 lines, Input→Logic→Output→Decision), spec_2 (372 lines, bit-level system spec with test vectors) |

**Tài liệu bổ sung**: `docs/v6_v7_spec_patterns.md` — phân tích chi tiết design
patterns từ V6/V7 research specs và 9 gaps alpha-lab cần bổ sung.
