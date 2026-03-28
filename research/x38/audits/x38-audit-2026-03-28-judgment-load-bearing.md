# X38 Judgment-Call Audit — Load-Bearing, Testability, and Deferral

**Scope**: `research/x38/debate/001`, `002`, `004`, `010`, `013`, `018`  
**Date**: 2026-03-28  
**Question**: Trong 16 judgment calls hiện có, cái nào thật sự load-bearing, cái nào test được, và debate đang tạo convergence hay organized deferral?

---

## Executive summary

### Headline

- **0/16** judgment calls là `cosmetic`.
- **5/16** là `governance-policy`.
- **11/16** là `structural-correctness`.
- **11/16** nằm trên **critical path** của spec theo nghĩa: nếu quyết sai, framework có thể chạy ra sai routing / sai admissibility / sai stop / sai winner semantics / sai proof semantics.

### Readiness split

Tách thành 3 mức thay vì nhị phân:

- **`READY`**: quyết định đủ cụ thể để implement ngay ở surface của chính nó.
- **`PARTIAL`**: đủ để draft/interface, nhưng còn phụ thuộc topic mở hoặc unresolved consumer.
- **`DEFERRAL`**: chủ yếu khóa ownership / boundary / methodology; real semantics vẫn nằm ở topic khác.

Kết quả:

- **8/16 READY**
- **6/16 PARTIAL**
- **2/16 DEFERRAL**

Nếu ép về nhị phân theo chuẩn **end-to-end spec readiness**:

- **8/16 spec-ready**
- **8/16 organized deferral-or-partial**

Nhưng ở **load-bearing subset** mới quan trọng:

- **5/11 READY**
- **6/11 PARTIAL/DEFERRAL**

=> Repo **không** gặp vấn đề ở “tổng số judgment calls” thuần túy. Vấn đề thật là: **đa số judgment calls nguy hiểm nhất chưa globally ready**.

### Core finding

Debate process hiện tại tạo ra:

- **local convergence** khá tốt ở governance layer,
- nhưng ở structural layer nó thường tạo ra **closure bằng interface freeze + downstream routing**, chưa phải end-to-end closure.

Nói ngắn gọn: **debate đang tạo cả convergence lẫn organized deferral, nhưng phần load-bearing nghiêng về organized deferral**.

---

## Matrix of 16 Judgment Calls

| ID | Topic | Short decision | Category | Critical path | TESTABLE | Readiness | Why it matters |
|----|-------|----------------|----------|---------------|----------|-----------|----------------|
| `X38-D-16` | 001 | HANDOFF routing contract | structural-correctness | YES | YES | PARTIAL | Sai thì mở sai campaign / sai corrective_re_run vs HANDOFF |
| `Facet E` | 002 | No new positive admissibility criterion | structural-correctness | YES | YES | READY | Sai thì firewall boundary leak hoặc over-block |
| `Facet A` | 002 | No v1 vocabulary expansion | structural-correctness | YES | YES | READY | Sai thì content gate sai shape |
| `Facet B-author` | 002 | GAP vs AMBIGUITY permanent law | structural-correctness | YES | YES | READY | Sai thì rule gap bị block oan hoặc admit bừa |
| `Facet B-codex` | 002 | Keep `PROVENANCE_AUDIT_SERIALIZATION` unsplit | governance-policy | NO | YES | READY | Granularity / maintainability, không phải runtime truth chính |
| `MK-03` | 004 | Minimum context manifest for future operating point | governance-policy | NO | PARTIAL | PARTIAL | Chủ yếu khóa guardrail v2+, chưa tác động runtime v1 |
| `MK-04` | 004 | Structured artifact mandatory for `Partially` | governance-policy | NO | YES | READY | Chống overclaim objectivity ở derivation test |
| `MK-07` | 004 | Interim `UNMAPPED` / vocabulary reconciliation | structural-correctness | YES | YES | DEFERRAL | Tự thân nó defer cho 002; sau này 002 mới biến thành law vĩnh viễn |
| `C1` | 004 | Compiler artifact must show `semantic_status: PENDING` | governance-policy | NO | YES | READY | Chống nhầm `PASS` = epistemic approval |
| `C2` | 004 | Freeze minimal auditor artifact schema | governance-policy | NO | YES | PARTIAL | Schema đóng, calibration/thresholds vẫn defer |
| `X38-D-23` | 010 | Pre-existing candidates vs x38 winners | structural-correctness | YES | PARTIAL | PARTIAL | Sai thì có thể uplift sai candidate dưới certification tier |
| `X38-CA-01` | 013 | Convergence metric + category semantics | structural-correctness | YES | YES | PARTIAL | Sai thì `FULLY_CONVERGED`/`PARTIALLY_CONVERGED` nghĩa sai |
| `X38-CA-02` | 013 | Stop law + bootstrap defaults | structural-correctness | YES | YES | READY | Sai thì dừng sớm / dừng muộn / lặp vô ích |
| `X38-SSE-09` | 013 | Holm default at `alpha_FWER=0.05` | structural-correctness | YES | YES | READY | Sai thì false discovery control sai ngay từ scan phase |
| `X38-SSE-04-THR` | 013 | Equivalence/anomaly methodology, numerics deferred | structural-correctness | YES | PARTIAL | DEFERRAL | Chính decision ghi nhận circular dependency với 017 |
| `SSE-D-05` | 018 | Recognition pre-freeze topology + working 5+5 minimum | structural-correctness | YES | PARTIAL | PARTIAL | Handoff cho 017/013, nhưng thresholds/consumption chưa đóng |

### Testability legend

- **YES**: có thể falsify bằng corpus tests, simulation, replay, adversarial fixtures, hoặc backtest/experiment.
- **PARTIAL**: có thể test một phần, nhưng end-to-end validation còn bị block bởi topic mở.

---

## Direct answers to the user questions

### 1. Judgment call nào là load-bearing?

**Load-bearing / structural-correctness (11):**

- `001/D-16`
- `002/Facet E`
- `002/Facet A`
- `002/Facet B-author`
- `004/MK-07`
- `010/D-23`
- `013/CA-01`
- `013/CA-02`
- `013/SSE-09`
- `013/SSE-04-THR`
- `018/SSE-D-05`

**Governance-policy (5):**

- `002/Facet B-codex`
- `004/MK-03`
- `004/MK-04`
- `004/C1`
- `004/C2`

**Cosmetic (0):**

- Không có judgment call nào hiện chỉ là naming/wording thuần túy.
- Đây là tín hiệu xấu hơn bề ngoài: repo không “đốt” judgment budget vào chuyện nhỏ; nó đang dùng judgment vào boundary, semantics, thresholds, ownership.

### 2. Judgment call nào falsify được bằng data?

**Empirical / simulation-testable ngay hoặc gần-ngay:**

- `013/CA-01`: replay V4→V8 rankings + synthetic ranking families
- `013/CA-02`: stop-too-early / stop-too-late replay
- `013/SSE-09`: false discovery simulation trên scan-phase
- `013/SSE-04-THR`: clustering / equivalence stability once 017 closes
- `018/SSE-D-05`: proof-yield / contradiction-yield / downstream recognition quality once 017+003 exist
- `010/D-23`: scenario fixtures once 008 exports same-family relation

**Deterministically testable bằng corpus / adversarial fixtures / schema checks:**

- `001/D-16`: routing decision-table fixtures
- `002/E/A/B-author/B-codex`: labeled lesson corpus + adversarial contamination set
- `004/MK-04`: artifact-schema validation
- `004/MK-07`: GAP vs AMBIGUITY corpus
- `004/C1`: compiler output contract tests
- `004/C2`: auditor artifact-schema tests

**Mostly policy-only / weakly falsifiable right now:**

- `004/MK-03` vì nó chủ yếu khóa manifest tối thiểu cho v2+ context declaration

### 3. Topic 013 không tự-converge, vậy convergence metric có đáng tin không?

**Kết luận ngắn**: đáng dùng như **governed measurement contract**, chưa đáng xem như **self-justifying truth**.

Lý do:

- Topic 013 đóng bằng **4/4 judgment calls**, không có row nào thật sự `Converged`.
- `CA-01` chỉ đóng được khi tách “measurement law + category semantics” khỏi “full routing matrix”. Nghĩa là 013 **không tự mang nổi toàn bộ semantics của chính output nó**.
- `SSE-04-THR` thừa nhận explicit **circular dependency** với Topic 017.

Điều vẫn đáng tin:

- Kendall's W, null-derived thresholds, category names, Holm default, stop-law structure.

Điều **chưa** đáng tin theo nghĩa “evidence-only”:

- `FULLY_CONVERGED` như một tiền đề đủ mạnh để hệ thống khác hành động mà không cần validation layer.

Nói chính xác hơn:

- `FULLY_CONVERGED` hiện là **governed prerequisite label**,
- chưa phải **empirically validated truth predicate**.

### 4. Bao nhiêu % là spec-ready, bao nhiêu % là organized deferral?

Theo chuẩn nghiêm:

- **Spec-ready end-to-end**: **8/16 = 50%**
- **Partial/deferral**: **8/16 = 50%**

Theo **load-bearing subset**:

- **Spec-ready**: **5/11 = 45.5%**
- **Partial/deferral**: **6/11 = 54.5%**

=> Nếu nhìn toàn bộ 16 call thì repo “đỡ xấu” hơn cảm giác ban đầu. Nhưng nếu nhìn đúng phần nguy hiểm nhất, **organized deferral đang chiếm đa số**.

---

## Topic-level diagnosis

### Topic 002 is the hardest load-bearing boundary

Không phải vì có nhiều call nhất, mà vì nó khóa **admissibility boundary**:

- admissible cái gì,
- unmapped xử lý thế nào,
- ambiguity fail-closed ra sao.

Nếu sai, toàn bộ meta-knowledge flow qua campaign boundary sẽ sai.

Topic 002 hiện đã đủ cụ thể để implement, nhưng **chưa được thực chứng bằng adversarial corpus**. Đây là “conservative choice under burden-of-proof”, không phải proof of correctness.

### Topic 013 is the most dangerous meta-instability

Nó vừa định nghĩa:

- metric convergence,
- stop law,
- correction law,
- equivalence/anomaly semantics,

và chính nó lại phải đóng bằng judgment.

Đây không tự động làm metric vô giá trị. Nhưng nó có nghĩa:

- mọi `CONVERGED` label downstream hiện đứng trên **governance-chosen semantics**,
- chưa đứng trên **validated semantics**.

### Topic 004 is less immediately dangerous, but not harmless

Đa phần 004 là governance-policy. Tuy nhiên:

- `MK-07` là ngoại lệ lớn, vì nó chạm trực tiếp vào `UNMAPPED` path và firewall boundary.

Nói cách khác: “Topic 004 là governance” đúng ở mặt bằng chung, nhưng **không đúng cho mọi judgment call trong topic**.

---

## Global consistency risk

Rủi ro người dùng nêu là thật:

- judgment call ở topic A được freeze trong local scope,
- rồi được topic B/C consume như invariant,
- nhưng chưa có một surface nào ép kiểm tra **global coherence**.

Dấu hiệu repo hiện tại:

- `drafts/architecture_spec.md` đã seed trực tiếp các decision từ `001/002/004/008/010/013/018`.
- Nhưng các consumer load-bearing vẫn đang mở: đặc biệt `015`, `017`, `016`, rồi mới đến `003`.
- Nghĩa là draft hiện đã hấp thụ nhiều local closures **trước khi network of obligations được reconcile toàn cục**.

Đây chính là mode failure “organized deferral looks like convergence”.

---

## Best remediation

### Recommendation 1 — Add a judgment register before any publish attempt

Tạo một artifact mới, ví dụ:

- `docs/judgment_register.md`

Mỗi row bắt buộc có:

- `judgment_id`
- `topic`
- `category`
- `critical_path`
- `testability`
- `readiness`
- `consumed_by`
- `depends_on_open_topics`
- `reopen_trigger`
- `global_invariants_touched`

Không có register này, spec cuối sẽ tiếp tục ghép từ local closures mà không ai thấy global contradiction graph.

### Recommendation 2 — Introduce a new pre-publish gate: `STRUCTURAL_JC_VALIDATED`

Rule mới đề xuất:

- Mọi judgment call thuộc `structural-correctness` muốn đi vào spec publish phải thỏa **một** trong hai điều kiện:
  - `READY + validation plan already executable`
  - hoặc `PARTIAL/DEFERRAL nhưng consumer topics đã CLOSED và integration audit PASS`

Nếu không, topic có thể `CLOSED` ở local debate sense, nhưng **không đủ điều kiện publish**.

### Recommendation 3 — Run 3 targeted validation programs

**A. Firewall validation pack (Topic 002)**

- corpus ~75 existing rules + adversarial contamination variants
- metrics:
  - false admit
  - false block
  - ambiguous-to-gap confusion
  - reviewer disagreement rate

**B. Convergence validation pack (Topic 013)**

- replay V4→V8
- synthetic rankings with known convergence ground truth
- compare:
  - false `FULLY_CONVERGED`
  - false `NOT_CONVERGED`
  - stop-too-early
  - stop-too-late
  - sensitivity to K and equivalence settings

**C. Routing/certification fixture pack (Topics 001 + 010)**

- scenario matrix:
  - defect fix / protocol preserved
  - methodology change
  - ambiguous preservation
  - same-family rediscovery
  - contradiction
  - `NO_ROBUST_IMPROVEMENT` with pre-existing candidate

### Recommendation 4 — Do not publish final architecture spec before `015` and `017` close

Lý do:

- `015` resolves invalidation scope, lineage, semantic change classes consumed by `001` and `018`.
- `017` resolves proof-consumption, cell-axis values, anomaly numerics consumed by `013` and `018`.

Nếu publish trước khi hai topic này đóng, repo sẽ publish một spec mà phần recognition/convergence/artifact semantics vẫn treo trên deferred obligations.

### Recommendation 5 — Add one explicit global reconciliation pass after 015/017/016 close and before 003 close

Đây nên là một audit riêng, không gộp vào topic local:

- input: all CLOSED topics + current drafts
- output:
  - contradiction table
  - duplicate-ownership table
  - missing-consumer table
  - stale-upstream table

Nếu pass này fail, phải reopen đúng topic gây conflict, không patch thẳng ở draft.

---

## Final assessment

### Is Topic 013 a self-referential failure?

**Yes, but in a precise sense**:

- Nó thất bại ở mức **self-grounding**,
- chưa thất bại ở mức **usability**.

Nó vẫn usable để seed methodology spec, nhưng chưa đủ validated để làm nền tuyệt đối cho mọi `CONVERGED` label khác.

### Is Topic 002 a chosen boundary rather than a proved boundary?

**Yes.**

Boundary hiện là:

- explicit,
- conservative,
- implementable,

nhưng chưa được proved bằng validation corpus. Vì vậy nó phải được đối xử như
`governed boundary under audit`, không phải “solved forever”.

### Is the debate process producing convergence or organized deferral?

**Both.**

Kết luận công bằng nhất là:

- governance layer: chủ yếu tạo **real convergence**
- structural layer: rất thường tạo **explicitly documented organized deferral**

Do đó vấn đề không phải “debate hỏng hoàn toàn”.

Vấn đề là repo hiện **chưa phân biệt đủ rõ**:

- local closure,
- global readiness,
- validated readiness.

Nếu không thêm phase reconciliation + validation, final spec rất dễ compile thành
một mạng cross-reference “đã quyết định” ở local scope nhưng chưa coherent ở global scope.
