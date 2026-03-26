# Alpha-Lab — Exploration & Systematization Proposal

**Status**: advisory memo from user request  
**Date**: 2026-03-25  
**Scope**: đề xuất cho bài toán "tạo ra tai nạn tốt" và "nhận diện + hệ thống hóa"
dựa trên `PLAN.md`, `docs/design_brief.md`, `drafts/architecture_spec.md`,
`drafts/meta_spec.md`, các topic `001/002/004/007/010` đã chốt, các topic
`003/006/008/013/015/017` còn mở, lineage V4->V8, và case VDO/VDR trong
workspace.

---

## 1. Chẩn đoán ngắn

X38 hiện mạnh ở **phòng thủ**:
- chống contamination,
- khóa protocol,
- ghi lại meta-knowledge,
- tách Clean OOS ra khỏi same-file evidence.

Nhưng X38 chưa đủ mạnh ở **tấn công khám phá**:
- chưa có cơ chế buộc search phải để lại coverage artifact tái dùng được,
- chưa có contract để giữ lại "candidate bất ngờ nhưng đáng đào sâu",
- chưa có genealogy để biết một thuật toán mới xuất hiện từ tổ hợp nào,
- chưa có quy trình distill "surprise" thành tri thức an toàn qua firewall.

Case VDO cho thấy hai việc khác nhau nhưng phải đi cùng nhau:

1. **Tạo điều kiện cho surprise xuất hiện**  
   VDO không xuất hiện vì prompt "thần kỳ"; nó xuất hiện vì có lúc AI được đi
   qua một vùng search space có:
   - raw channel mới (`taker_buy_base_vol` / order-flow),
   - transform đủ mở,
   - ít bias family-level,
   - đủ tự do để tổ hợp thành một oscillator hữu ích.

2. **Không để surprise thất lạc**  
   Prompt gốc bị mất. Điều này nói thẳng rằng Alpha-Lab không thể dựa vào
   transcript/prompt memory. Framework phải lưu **lineage có cấu trúc** của
   feature/candidate.

Kết luận: Alpha-Lab cần thêm một vòng lặp rõ ràng:

```text
Frontier scan
  -> diversity-preserving exploration
  -> surprise triage
  -> proof bundle
  -> freeze
  -> phenotype distillation
  -> shadow-safe memory for future campaigns
```

---

## 2. Foundation bắt buộc: Discovery Lineage

Trước khi nói tới Tầng 1 hay Tầng 2, X38 cần một invariant mới:

> **Mọi feature, transform, candidate, và mutation phải có lineage machine-readable.**

Nếu không có lineage:
- "tai nạn tốt" không tái lập được,
- không biết candidate mới là khám phá thật hay clone ngụy trang,
- không thể distill candidate thành phenotype an toàn.

**Artifact tối thiểu nên có**:
- `discovery_lineage.json`
- `operator_registry.json`
- `candidate_genealogy.json`

**Lineage tối thiểu nên lưu**:
- raw channel nguồn,
- operator chain,
- parent candidate(s),
- role assignment (`permission`, `state`, `entry_confirm`, `exit_control`),
- threshold mode,
- timeframe binding,
- session/campaign provenance,
- hash của protocol + data snapshot.

Artifact này là cách thay thế vĩnh viễn cho "prompt bị mất".

---

## 3. Tầng 1 — Cơ chế Exploration

### 3.1 Mục tiêu thiết kế

Tầng 1 không có mục tiêu "chọn winner".  
Mục tiêu của nó là:
- mở rộng vùng search thực sự được đi qua,
- giữ diversity đủ lâu,
- tạo lineage rõ,
- tạo đủ nhiều tổ hợp hợp lệ để VDO-type discoveries xuất hiện lặp lại.

### 3.2 Đề xuất cơ chế

| Cơ chế | Mục đích | Input | Output | Cách tích hợp |
|---|---|---|---|---|
| **E1. Manifest-first transform grammar** | Mở search space theo raw channel + operator, không chỉ theo feature list viết tay. Cho AI tự do đề xuất tổ hợp nhưng chỉ trong grammar đã khóa. | Raw bar schema, feature families, operator library, threshold modes, protocol lock | `feature_manifest.json`, `transform_registry.parquet`, `operator_registry.json` | Mở rộng Topic `006` và Stage 3 của Topic `003`. Đây là cách biến "AI tự do thử" thành "AI tự do trong sandbox có kiểm soát". |
| **E2. Descriptor-tagged frontier scan** | Biến scan từ "quét config" thành "quét có bản đồ". Không chỉ biết ai mạnh nhất, mà biết vùng nào đã cover. | Stage 1 registry, descriptor taxonomy, bucket definitions | `coverage_map.parquet`, `bucket_summary.json`, `descriptor_scan_stats.json` | Khớp trực tiếp với stub `§11.1` của `architecture_spec.md` và finding `ESP-01`. Cần Topic `017` + `013`. |
| **E3. Cell-elite archive thay cho global top-K** | Giữ lại nhiều "mầm bất ngờ" thay vì collapse sớm về vài config đứng đầu toàn cục. | Coverage map, per-cell metrics, redundancy audit, keep/drop rules | `cell_elite_archive.parquet`, `keep_drop_ledger.json` | Thay logic Stage 4 hiện đang nghiêng về shortlist toàn cục trong Topic `003`. Đây là cơ chế tạo "good accidents" quan trọng nhất. |
| **E4. Structured mutation & recombination operators** | Tạo biến thể thuật toán có kiểm soát: add/remove layer, đổi role, đổi timeframe, oscillatorize, swap channel, replace threshold mode. Đây là bản offline của "AI vô tình tổ hợp". | Cell elites, operator grammar, role grammar, complexity budget | `variant_registry.parquet`, `candidate_genealogy.json`, `mutation_batch_report.json` | Thuộc Stage 5. Nên tách rõ "operator grammar" khỏi "feature registry". Nếu không, Topic `006` vẫn quá hẹp. |
| **E5. Contradiction-driven resurrection queue** | Buộc framework quay lại vùng có tín hiệu "có gì đó sai với prior hiện tại": rank flip, underdog có plateau rộng, cell variance cao, reserve contradiction. | `contradiction_profile`, pairwise matrix, plateau stats, coverage gaps | `resurrection_queue.json`, `contradiction_probe_results.parquet` | Gắn với Topic `017` budget governor và HANDOFF dossier của Topic `001`. Dùng để biến surprise từ event ngẫu nhiên thành workflow bắt buộc. |
| **E6. Mandatory scout budget / coverage floor** | Luôn chừa compute cho vùng chưa được yêu thích. Không cho leader hiện tại nuốt hết budget. | Total budget, coverage obligations, active/shadow priors, cell density | `budget_allocation.json`, `coverage_floor_report.json` | Thuộc `ESP-04`. Trên same-dataset vẫn tương thích MK-17 vì chỉ ảnh hưởng ordering/depth, không đẩy answer prior vào selection. |

Lưu ý vận hành:
- Trong Alpha-Lab, **AI freedom nên nằm ở lớp khai báo trước protocol lock**:
  đề xuất operator pack, transform pack, hoặc candidate templates.
- Sau khi manifest đã khóa, execution phải quay lại đúng paradigm offline:
  deterministic scan, deterministic pruning, deterministic artifact production.

### 3.3 Ý nghĩa riêng với case VDO

Nếu Alpha-Lab có đủ `E1 + E3 + E4 + discovery_lineage`, VDO-type discovery sẽ
không còn phụ thuộc vào:
- một prompt "đúng lúc",
- một AI cụ thể,
- hoặc trí nhớ của người nghiên cứu.

Framework sẽ biết:
- raw channel nào tạo edge,
- transform chain nào sinh candidate,
- candidate đó xuất hiện từ cell nào,
- và candidate đó có phải thực sự orthogonal hay chỉ là clone của một family đã biết.

---

## 4. Tầng 2 — Nhận diện, chứng minh, hệ thống hóa

### 4.1 Mục tiêu thiết kế

Tầng 2 không được nhầm "surprise" với "value".

`Unexpected` chỉ nên là:
- **tín hiệu để ưu tiên review**,
- không phải quyền đi thẳng vào winner lane.

Do đó Tầng 2 phải làm ba việc:
- phân loại surprise nào đáng đào sâu,
- chứng minh nó là real, không phải clone/noise,
- distill nó thành tri thức có thể tái dùng mà không leak đáp án.

### 4.2 Đề xuất cơ chế

| Cơ chế | Mục đích | Input | Output | Cách tích hợp |
|---|---|---|---|---|
| **R1. Surprise triage gate** | Phân loại candidate bất ngờ thành: chỉ quan sát, probe thêm, đưa vào comparison set, hoặc loại bỏ như clone/noise. | Candidate registry, coverage map, contradiction profile, equivalence clusters, robustness stats | `surprise_queue.json`, `triage_decisions.json` | Đặt giữa Stage 6 và Stage 7. Đây là chỗ biến "ngạc nhiên" thành đối tượng xử lý chuẩn, không phải cảm hứng của người review. |
| **R2. Equivalence / redundancy audit** | Trả lời câu hỏi: candidate này có thực sự mới không, hay chỉ là phiên bản đổi tên của thứ đã có? | Common daily paired-return domain, descriptor bundles, transported-clone audit, nearest-neighbor comparisons | `equivalence_clusters.json`, `redundancy_report.json`, `identity_relation.json` | Cần phối hợp Topic `008` (identity), `013` (distance/convergence), `017` (phenotype). Đây là lớp bảo vệ chống "ảo giác khám phá". |
| **R3. Proof bundle cho candidate bất ngờ** | Chuẩn hóa bằng chứng phải có trước khi tích hợp surprise vào framework. | Candidate, nearest simpler rival, nearest family rival, plateau grids, cost sweep, split perturbation, ablation, paired tests | `proof_bundle/`, `plateau_extract.json`, `ablation_report.json`, `paired_matrix.parquet`, `power_assessment.json` | Mở rộng Stage 6-7 và state pack của Topic `015`. Nếu không có proof bundle, surprise chỉ là curiosity. |
| **R4. Phenotype distillation + reconstruction-risk gate** | Chuyển candidate đã được chứng minh thành memory an toàn cho campaign sau. | Proof bundle, descriptors, genealogy, firewall context | `candidate_phenotype.json`, `reconstruction_risk_report.json`, `structural_prior_candidate.json` | Map trực tiếp vào `ESP-02` và `ESP-03`. Giữ nguyên nguyên tắc của Topic `002`: không mang feature names/lookbacks/thresholds qua firewall. |
| **R5. Dual archive: winner memory + negative evidence memory** | Giữ lại không chỉ winner mà cả "vùng thất bại có ý nghĩa" ở mức descriptor. | Proof bundles, contradiction results, dropped-candidate reasons, coverage map | `winner_archive.json`, `negative_evidence_registry.json`, `campaign_epistemic_delta.json` | Trong v1, negative memory nên ở descriptor-level và shadow-only; nếu vượt boundary hiện tại của Topic `002`, giữ local-to-campaign hoặc `UNMAPPED + SHADOW`. |
| **R6. Activation ladder cho tri thức đã distilled** | Chỉ cho structural prior tăng lực dần theo evidence thật. | Phenotype archive, contradiction history, clean OOS verdicts, context distance | `prior_registry.json`, lifecycle transitions `OBSERVED -> REPLICATED_SHADOW -> ACTIVE -> DEFAULT_METHOD_RULE` | Thuộc Topic `017` + Topic `004` + Topic `010`. Trên same dataset vẫn dừng ở shadow-only theo MK-17. |

### 4.3 Quy trình sàng lọc đề xuất

Một candidate bất ngờ nên đi qua đúng chuỗi này:

```text
interesting_outlier
  -> surprise_queue
  -> equivalence audit
  -> proof bundle
  -> frozen comparison set
  -> INTERNAL_ROBUST_CANDIDATE hoặc NO_ROBUST_IMPROVEMENT
  -> candidate_phenotype
  -> REPLICATED_SHADOW memory
  -> (chỉ sau dữ liệu mới) ACTIVE_STRUCTURAL_PRIOR
```

Điểm quan trọng:
- `unexpected` không đủ để được freeze,
- `performance` không đủ để được distill,
- `same-file replication` không đủ để được activate.

---

## 5. Gap hiện tại của X38

| Gap | Evidence trong X38 hiện tại | Vì sao quan trọng cho 2 tầng |
|---|---|---|
| **G1. Chưa có discovery-lineage contract** | Không topic/spec nào hiện định nghĩa artifact genealogy cho feature/candidate; Topic `015` mới dừng ở state pack chung | Không có lineage thì mọi "good accident" vẫn có thể bị mất như prompt VDO. |
| **G2. Descriptor taxonomy chưa được chốt xuyên suốt 006 <-> 017** | Topic `006` mới nói family registry; Topic `017` mới nói descriptor tagging/phenotype ở mức finding | Không có taxonomy chung thì coverage map, cell archive, phenotype memory, equivalence audit sẽ lệch nhau. |
| **G3. Chưa có scan-phase multiplicity control** | Topic `003` đã tự nêu open question về FDR/Holm/cascade sufficiency | Exploration rộng mà không có control sẽ đẩy nhiều false positive vào surprise lane. |
| **G4. Chưa có identity/equivalence metric cho "same thing in disguise"** | Topic `008` mới chạm same-family identity; Topic `013` chưa định nghĩa distance metric | Không giải quyết được "candidate mới thật hay clone". |
| **G5. Chưa có serendipity triage lane** | `ESP-01` có `epistemic_delta.json` nhưng chưa có queue/gate để xử lý outlier | Surprise sẽ lại phụ thuộc người review có để ý hay không. |
| **G6. Chưa có negative-evidence governance** | Topic `004`/`002` mạnh ở lesson admissibility, nhưng chưa có artifact an toàn cho "vùng đã probe và fail vì lý do gì" | Không hệ thống hóa thất bại thì campaign sau vẫn lặp công và khó chống ratchet theo cách minh bạch. |
| **G7. Chưa có artifact spec cho coverage/phenotype/proof bundle** | Topic `015` mới nêu state pack ở mức chung; `017` thêm artifact nhưng chưa đóng contract | Không có schema chuẩn thì exploration không reproducible và khó invalidate đúng phạm vi. |
| **G8. Chưa có convergence metric ở descriptor-space** | Topic `013` mới nói family/architecture/parameter/performance convergence | Tầng 2 cần biết "ta đã học thêm gì về search space", không chỉ "winner có đổi không". |
| **G9. Chưa có operator grammar cho recombination có kiểm soát** | Topic `006` hiện thiên về registry pattern và threshold modes | Nếu chỉ có registry tĩnh, framework giỏi scan nhưng chưa giỏi phát minh biến thể. |

---

## 6. Đề xuất bổ sung cho X38

### 6.1 Nếu muốn giữ số topic hiện tại

**Mở rộng Topic `006` (Feature Engine)**
- Thêm ownership cho:
  - transform grammar,
  - role grammar,
  - mutation operators,
  - channel taxonomy.
- Lý do:
  - hiện `006` mới giải bài toán "enumerate feature",
  - chưa giải bài toán "tạo feature/candidate mới một cách có hệ thống".

**Mở rộng Topic `017` (Epistemic Search Policy)**
- Thêm ownership cho:
  - `surprise_queue`,
  - `resurrection_queue`,
  - `budget_allocation.json`,
  - serendipity triage semantics,
  - acceptance criteria cho exploration engine.
- Lý do:
  - `017` đang là nơi gần nhất với bài toán "học cách search tốt hơn",
  - nhưng hiện vẫn nghiêng về coverage/phenotype/budget hơn là full serendipity loop.

**Mở rộng Topic `013` (Convergence Analysis)**
- Thêm:
  - descriptor-space convergence,
  - marginal information gain,
  - diminishing returns trên coverage map, không chỉ winner identity.
- Lý do:
  - stop condition cho exploration phải dựa trên "đã học gì thêm", không chỉ "winner có đổi nữa không".

**Mở rộng Topic `015` (Artifact & Version Management)**
- Bắt buộc enum thêm:
  - `discovery_lineage.json`
  - `coverage_map.parquet`
  - `cell_elite_archive.parquet`
  - `candidate_genealogy.json`
  - `proof_bundle/`
  - `candidate_phenotype.json`
  - `prior_registry.json`
- Lý do:
  - nếu các artifact này không được state-pack hóa, proposal này sẽ không sống được qua implementation.

**Mở rộng Topic `008` (Architecture & Identity)**
- Thêm:
  - identity relation fields cho family / architecture / phenotype / equivalence cluster.
- Lý do:
  - cần phân biệt "same family", "same phenotype", "same exact system", "same surprise re-discovered".

### 6.2 Nếu muốn tách ownership cho sạch hơn

Nếu không muốn nhồi thêm vào `006` và `017`, nên mở thêm 2 topic mới:

**Topic 018 — Discovery Lineage & Operator Grammar**
- Giải quyết:
  - operator grammar,
  - mutation/recombination rules,
  - lineage artifact contract,
  - invalidation semantics khi operator taxonomy đổi.
- Vì sao cần topic riêng:
  - nó cắt ngang `006`, `015`, `017`,
  - và chính là chỗ giải quyết bài toán "đừng để mất VDO lần nữa".

**Topic 019 — Serendipity Triage & Negative Evidence Governance**
- Giải quyết:
  - `surprise_queue`,
  - proof bundle thresholds,
  - negative evidence registry,
  - resurrection triggers,
  - descriptor-level rejection memory.
- Vì sao cần topic riêng:
  - `017` đã rộng,
  - còn phần "candidate bất ngờ nào đáng biến thành tri thức" là một decision architecture riêng.

### 6.3 Spec mới nên có

Tối thiểu nên thêm 3 spec mới trong `drafts/` sau khi ownership được chốt:

1. **`exploration_spec.md`**
   - Owner đề xuất: `003 + 006 + 017`
   - Nội dung:
     - transform grammar,
     - descriptor taxonomy,
     - cell-elite archive,
     - mutation operators,
     - scout budget.

2. **`epistemic_artifact_spec.md`**
   - Owner đề xuất: `015 + 017`
   - Nội dung:
     - `coverage_map`,
     - `epistemic_delta`,
     - `proof_bundle`,
     - `candidate_phenotype`,
     - `prior_registry`,
     - lineage artifacts.

3. **`identity_equivalence_spec.md`**
   - Owner đề xuất: `008 + 013`
   - Nội dung:
     - family relation,
     - phenotype relation,
     - redundancy classes,
     - equivalence thresholds,
     - convergence granularity.

---

## 7. Kỹ thuật nên bổ sung hoặc tích hợp đầy đủ hơn

1. **Transform grammar / operator library**
   - Giải quyết bài toán AI tạo biến thể có kiểm soát.

2. **Scan-phase multiple-testing control**
   - FDR, step-down, hoặc formal cascade law.
   - Giải quyết false positive khi quét 50K+ configs.

3. **Equivalence clustering trên common daily paired-return domain**
   - Giải quyết "candidate mới hay clone".

4. **Descriptor-space coverage metrics**
   - Giải quyết stop condition và search visibility.

5. **Proof bundle compiler**
   - Auto-build ablation, plateau, perturbation, pairwise matrix, contradiction profile.
   - Giải quyết chuẩn hóa chứng minh.

6. **Reconstruction-risk estimator**
   - Giải quyết phenotype memory mà không lách firewall.

7. **Negative evidence distillation**
   - Giải quyết reuse của thất bại mà không biến thành answer prior.

---

## 8. Thứ tự ưu tiên khuyến nghị

Nếu phải chọn đường ngắn nhất nhưng có ích thật cho Alpha-Lab, thứ tự nên là:

1. **Khóa `discovery_lineage.json` + operator grammar**
   - Đây là lớp chống "mất VDO" trực tiếp nhất.

2. **Thay global top-K bằng `cell_elite_archive`**
   - Đây là lớp tăng xác suất "tai nạn tốt" trực tiếp nhất.

3. **Thêm `surprise_queue` + `proof_bundle`**
   - Đây là lớp nhận diện và chứng minh.

4. **Thêm `candidate_phenotype.json` + reconstruction-risk gate**
   - Đây là lớp hệ thống hóa an toàn qua firewall.

5. **Giữ mọi cross-campaign activation ở shadow-only cho tới khi có data mới**
   - Đây là lớp giữ proposal này không phá hỏng triết lý MK-17 hiện có.

---

## 9. Kết luận

X38 hiện đã có nền rất mạnh để **ngăn framework tự lừa mình**.  
Để Alpha-Lab thật sự tìm được các VDO tiếp theo, X38 cần thêm cơ chế để:

- **khám phá có chủ đích nhưng không bóp chết bất ngờ,**
- **xem surprise như một object phải xử lý, không phải cảm hứng,**
- **và lưu lại genealogy + phenotype để "tai nạn tốt" trở thành tài sản của framework.**

Ngắn gọn:
- Tầng 1 cần **exploration engine**,
- Tầng 2 cần **surprise triage + proof + phenotype distillation**,
- và cả hai đều cần **discovery lineage** làm xương sống.
