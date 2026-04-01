# Online vs Offline — Phân biệt cốt lõi cho mọi agent tham gia x38

**Tại sao file này tồn tại**: Agents tham gia debate x38 PHẢI hiểu rằng gen1/gen2/gen3/gen4
(online) và Alpha-Lab (offline) là HAI PARADIGM KHÁC NHAU giải quyết cùng vấn đề.
Nhầm lẫn này dẫn đến lỗi nghiêm trọng: đề xuất "Alpha-Lab nên adopt gen4 pattern X"
khi thực tế Alpha-Lab cần giải pháp offline riêng cho cùng vấn đề.

---

## 1. Hai Paradigm

### Online (gen1, gen3, gen4) — "Document AI phải tuân theo"

| Khía cạnh | Mô tả |
|-----------|--------|
| **Execution** | AI chat session — human gửi prompt, AI phân tích/code/đo lường trong conversation |
| **Determinism** | Non-deterministic — cùng data + cùng protocol, AI khác nhau cho kết quả khác |
| **Governance** | Protocol là *tài liệu* AI phải tuân theo — enforcement bằng prompt engineering |
| **Contamination vector** | AI memory/context — AI "nhớ" kết quả trước dù protocol cấm |
| **State transfer** | State packs giữa sessions (human-operated, manual save/upload) |
| **Reproducibility** | Không — AI interpretation thay đổi giữa sessions |
| **Search coverage** | AI chọn hướng khám phá — có thể bỏ sót vùng search space |
| **Iteration** | Human gửi prompt → AI response → human review → next prompt |

### Offline (Alpha-Lab) — "Code tự enforce"

| Khía cạnh | Mô tả |
|-----------|--------|
| **Execution** | Deterministic code pipeline — không có AI conversation trong execution |
| **Determinism** | Reproducible — cùng data + cùng code + cùng seed = cùng kết quả |
| **Governance** | Protocol là *code* tự enforce — filesystem gating, chmod, automated checks |
| **Contamination vector** | Data/knowledge leakage qua code/filesystem — KHÁC với AI context |
| **State transfer** | Machine-enforced — campaign isolation, immutable sessions |
| **Reproducibility** | Có — pipeline deterministic (bootstrap reproducible khi seed frozen) |
| **Search coverage** | Exhaustive scan over declared search space — không phụ thuộc AI judgment |
| **Iteration** | Code chạy tự động qua stages → human review kết quả cuối |

---

## 2. Cùng vấn đề, khác giải pháp

| Vấn đề | Online giải quyết bằng | Offline giải quyết bằng |
|--------|------------------------|-------------------------|
| **Contamination** | Upload matrix, session boundaries, prompt isolation | Filesystem chmod, data-pipeline checksum binding, campaign isolation |
| **Winner divergence** | Convergence status doc (human review) | N independent deterministic sessions + statistical convergence test |
| **Constitution gaps** | Governance review chat (G0→G2) | Meta-Updater code (automated rule update between campaigns) |
| **Reproducibility** | State pack handoff (manual) | Deterministic pipeline (same input = same output) |
| **Search space lock-in** | "open search space" in prompt text | Machine-enforced: scanner covers declared space exhaustively |
| **Zero-trade trap** | Minimum-activity constraint in prompt | Exhaustive scan + automatic filter by trade count |
| **MDD cap** | Manual governance review → adjust cap | Parameterized hard constraints in config, not code |
| **Sub-hourly waste** | Guidance in prompt text | Search scope declared in config → enforced by scanner |
| **No ablation revision** | Intra-session revision rule in prompt | Pipeline built-in: ablation is automatic stage, revision is code path |
| **Meta-knowledge leakage** | AI "forgets" per prompt instruction | Typed schema + whitelist category + state machine (xem design_brief:51, F-04) |
| **Redesign control** | Redesign guardrails (trigger + cooldown + dossier) | Campaign model: new campaign = fresh start, meta-knowledge only flows at principle level |

---

## 3. Gen1/gen2/gen3/gen4 là evidence, KHÔNG phải template

### Đúng cách dùng gen3/gen4 trong x38 debate

- **"Gen3 thất bại vì zero-trade trap → Alpha-Lab cần giải quyết zero-trade trap"** ✓
  (Evidence về VẤN ĐỀ — vấn đề này có thể xảy ra ở cả online lẫn offline)

- **"Gen4 dùng MDD cap 45% → Alpha-Lab nên dùng MDD cap 45%"** ✓
  (Specific domain knowledge về BTC spot — không phụ thuộc paradigm)

- **"Gen4 dùng governance_failure_dossier PATTERN → Alpha-Lab nên có failure diagnosis mechanism"** ✓
  (Pattern paradigm-independent — chẩn đoán → gaps → fixes)

### Sai cách dùng gen3/gen4 trong x38 debate

- **"Alpha-Lab nên adopt gen4's redesign guardrails (trigger + cooldown + dossier)"** ✗
  (Redesign guardrails giải quyết vấn đề online: AI reactive redesign. Offline không
  có vấn đề này — campaign model tự isolation.)

- **"Alpha-Lab nên dùng gen4's upload matrix"** ✗
  (Upload matrix giải quyết vấn đề AI chat context. Offline pipeline không upload.)

- **"Alpha-Lab nên có session boundaries giống gen4"** ✗
  (Session boundaries ngăn AI drift giữa execution/discussion. Offline pipeline
  không drift — code chạy đúng stage nào thì stage đó.)

### Judgment zone — cần debate

- **Gen4's complexity caps** (max 3 layers, max 4 tunables): Domain knowledge hay
  online-specific? Nếu domain → adopt. Nếu vì AI không handle complexity → khác.

- **Gen4's evidence clock reset**: Concept "redesign resets OOS evidence" có apply
  cho offline campaign model? Campaign model tự reset bằng construction (new data).

- **Gen4's forward decision law** (cumulative, quarterly): Cadence constraint cho
  human operator (online) hay cũng cần cho automated pipeline (offline)?

---

## 4. Lineage đầy đủ + Vòng đời tiến hóa

### 4.1 Lineage

```
gen1 (V1→V8)    gen2            gen3            gen4             Alpha-Lab (x38)
── ONLINE ──    ── ONLINE ──    ── ONLINE ──    ── ONLINE ──     ── OFFLINE ──

Free-form AI    Structured      + Math-from-    + Version        Deterministic
conversation    kit, nhưng        data thay       lineage        code pipeline,
(human+AI)      CHỈ cho phép      thế TA-only   + Redesign       machine-enforced
8 vòng hội      TA indicators   + State pack      guards         governance
thoại           → không tìm     + Constitution  + Complexity
                được gì         → FAIL giữa       caps
                                  chừng

Prompts:        Prompts:        Prompts:        Prompts:         ← x38 designing
x37/docs/gen1/  x37/docs/gen2/  x37/docs/gen3/  x37/docs/gen4/     blueprint
Report:         Report:         Report:         Report:
(trong          docs/gen2/      docs/gen3/      docs/gen4/
resource/gen1/  report/         report/         report/
— xem dưới)    FAIL: TA-only   FAIL: 4 gaps    (chưa xong)

Resource        no resource     no resource     resource/gen4/
(bản sao khi    (failed)        (failed)        (rỗng, chờ
thành công):                                     kết quả)
x37/resource/
gen1/

Convention:
- docs/genN/report/ = KẾT QUẢ (luôn có, kể cả khi thất bại)
- resource/genN/ = BẢN SAO 1:1 report + spec KHI THÀNH CÔNG
  (chỉ thành công mới có spec; để tiện truy lục cho việc dựng mã)
- Gen thất bại: có report (failure dossier, etc.) nhưng KHÔNG
  có resource/ copy và KHÔNG có spec

            Evidence ────────────────────────────────► Design input
            (vấn đề gì xảy ra ở online)                (giải pháp offline)
```

### 4.2 Vòng đời tiến hóa tự sửa chữa (online)

Online framework có cơ chế tiến hóa built-in: **Governance Review (G0→G1→G2)**.

```
gen(N) seed discovery ──► FAIL?
     │                      │
     │ SUCCESS               │ constitution có lỗi
     ▼                      ▼
  forward eval          chạy G0 + G1 trong gen(N)
     │                      │
     ▼                      ▼
  promote/kill           gen(N+1) ra đời
     │                   (hiến pháp sửa lỗi)
     ▼                      │
  DONE                      └──► gen(N+1) seed discovery ──► ...
```

**Lịch sử thực tế**:
- **gen2** → FAIL: chỉ cho phép TA indicators, không tìm được gì từ raw data
  → tạo gen3 (mở search space cho math-from-data)
- **gen3 V1** → FAIL: constitution có 4 gaps (zero-trade trap, MDD cap, sub-hourly, ablation)
  → chạy G0+G1 → tạo gen4 (18 fixes)
- **gen4 V1** → IN PROGRESS. Nếu FAIL → chạy G0+G1 → tạo gen5
- **Kết thúc khi**: tìm được thuật toán HOẶC tuyên bố không còn đường phía trước

**Relevance cho Alpha-Lab**: Alpha-Lab cần cơ chế tương đương — **Meta-Updater**.
Nhưng khác biệt cốt lõi:
- Online: governance review là AI chat (G0→G1→G2), human quyết định
- Offline: Meta-Updater là code, cập nhật rules/anti-patterns/search heuristics
  giữa campaigns, KHÔNG cập nhật priors về đáp án

Cùng PATTERN (fail → diagnose → fix rules → retry), KHÁC IMPLEMENTATION.

---

## 5. Checklist cho agent trước khi đề xuất

Trước khi đề xuất "Alpha-Lab nên làm X giống gen4", kiểm tra:

- [ ] X giải quyết vấn đề ONLINE-SPECIFIC (AI context, prompt compliance, session drift)?
  → Nếu có: Alpha-Lab KHÔNG cần X — vấn đề không tồn tại trong offline.
- [ ] X giải quyết vấn đề DOMAIN-SPECIFIC (BTC drawdown, trade frequency, cost structure)?
  → Nếu có: Alpha-Lab CÓ THỂ adopt X — domain knowledge paradigm-independent.
- [ ] X là PATTERN paradigm-independent (failure diagnosis, evidence accumulation, convergence)?
  → Nếu có: Alpha-Lab nên EVALUATE pattern, thiết kế implementation offline riêng.
