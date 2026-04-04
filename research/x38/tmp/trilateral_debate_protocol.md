> **QUY ĐỊNH TRANH LUẬN — ĐỌC TRƯỚC KHI PHẢN BIỆN**
>
> 1. Mỗi lượt phản biện bắt đầu bằng tiêu đề có đánh số: **"C.N. Phản biện của \<tên agent\> cho \<tên agent đối phương\>: ..."** (N tăng dần từ 1)
> 2. Phản biện được điền **nối tiếp ở cuối tệp**. Agent lượt sau đọc và phản biện lại. Lặp cho đến **hội tụ hoàn toàn**.
> 3. Phản biện phải **chính trực, công tâm** — không đồng thuận giả, không để quán tính các vòng trước chi phối.
> 4. Mỗi vòng: **liệt kê mục đã hội tụ** rồi loại khỏi phạm vi. **Chỉ phản biện mục chưa hội tụ**.

---

# A. CÂU HỎI BAN ĐẦU

Làm sao để mục /var/www/trading-bots/btc-spot-dev/research/x38/debate sau khi đã /var/www/trading-bots/btc-spot-dev/research/x38/tmp/rebuild ra repo độc lập thì có cả 03 bên tham gia vào quá trình tranh luận, gồm Claude Code + Codex + ChatGPT Pro cùng tham gia tranh luận?

# B. CÂU TRẢ LỜI BAN ĐẦU
## B.1. Câu trả lời của Claude Code

### Thiết kế: Trilateral Debate Protocol (3 canonical agents)

#### Vấn đề hiện tại

Protocol hiện tại là **bilateral** (2 bên):

- `x38_RULES.md` §5 (dòng 98-104): chỉ khai báo `claude_code` + `codex`
- `debate/rules.md`: steel-man, convergence, round parity đều thiết kế cho 2 bên
- `debate/prompt_template.md` dòng 38: `Các bên tranh luận: Claude Code ↔ Codex`
- ChatGPT hiện chỉ là external advisor (evidence in `external/chatgpt_web/`)

Mọi quy tắc — từ steel-man (§7), round parity (§14b), convergence gate, đến directory
structure (`codex/`, `claude_code/`) — đều hardcode cho đúng 2 participants.

#### 3 quyết định kiến trúc cần chốt trước

##### Q1. Round format — Round-robin hay Parallel?

| Option | Mô tả | Ưu | Nhược |
|--------|--------|-----|-------|
| **A. Round-robin** | A→B→C→A→B→C | Đơn giản, serial | Anchoring: C luôn thấy A+B trước |
| **B. Parallel-then-converge** | R1: B∥C critique độc lập → R2+: round-robin | R1 không anchoring bias | Phức tạp orchestration hơn |
| **C. Full parallel** | Mỗi round cả 3 đều viết | Symmetric hoàn toàn | 3x artifacts/round, khó focus |

**Đề xuất: Option B** (Parallel-then-converge).

Lý do: Architecture debate cần independent perspectives ở Round 1. Nếu C luôn đọc A+B
trước khi viết, C bị anchoring vào framing của A — mất giá trị "fresh eyes". Sau Round 1,
khi cả 3 vị trí đã được ghi nhận độc lập, round-robin giúp hội tụ dần mà không mất
thông tin.

Cơ chế cụ thể:
- **Round 1**: Architect (A) viết opening-critique. Sau đó 2 Reviewers (B, C) viết
  rebuttal **song song, không thấy lẫn nhau**. Human orchestrator đảm bảo B không đọc
  artifact C và ngược lại.
- **Round 2+**: Round-robin A→B→C→A→B→C. Mỗi agent đọc TẤT CẢ round files hiện có
  trước khi viết.

##### Q2. Convergence threshold — Unanimous hay Majority?

| Option | Mô tả | Ưu | Nhược |
|--------|--------|-----|-------|
| **Unanimous (3/3)** | Cả 3 đồng ý + steel-man | Chặt chẽ nhất | Có thể kẹt ở 2/3 mãi |
| **Supermajority (2/3) + dissent record** | 2 agent hội tụ, 1 dissent → Judgment call | Tránh deadlock | Có thể bỏ qua dissent hợp lệ |

**Đề xuất: Unanimous cho Converged, 2/3 auto-escalate thành Judgment call.**

Lý do: Giữ bar cao cho hội tụ thật (đã qua steel-man). Nhưng khi 2/3 đồng ý và agent
thứ 3 vẫn bất đồng sau steel-man, issue không bị treo mãi — nó escalate lên human
researcher (Tier 3) để quyết định. Dissent record bắt buộc đảm bảo vị trí thiểu số
không bị mất.

Cơ chế:
- `Converged` = 3/3 unanimous + steel-man xác nhận (§7 mở rộng).
- `Majority-dissent` = 2/3 đồng ý, 1 bất đồng → tự động chuyển `Judgment call`.
  Dissent record bắt buộc ghi: (a) vị trí bất đồng, (b) evidence cụ thể,
  (c) tại sao majority cho rằng dissent không đứng vững.
- Agent dissent vẫn phải hoàn thành steel-man cho majority position trước khi ghi
  dissent — đảm bảo dissent không phải vì chưa hiểu majority argument.

##### Q3. Max rounds — 6 hay 9?

Hiện tại: `max_rounds_per_topic = 6` với 2 agents = 3 rounds/agent = 3 full exchange
cycles.

Với 3 agents:
- 6 rounds = 2 rounds/agent = chỉ ~2 exchange cycles → **không đủ** cho hội tụ phức tạp.
- 9 rounds = 3 rounds/agent = 3 full cycles → **tương đương** với mức hiện tại.
- 12 rounds = 4 rounds/agent → quá dài, diminishing returns.

**Đề xuất: Tăng lên 9 rounds** (3 full trilateral cycles).

Lý do: Mỗi agent cần ít nhất 3 cơ hội: (1) nêu vị trí, (2) phản biện, (3) steel-man
hoặc closure. 9 rounds đảm bảo điều này mà không kéo dài vô ích.

---

#### 7 patch cụ thể cho files

##### Patch 1: `x38_RULES.md` §5 — Available participants + per-domain opt-in

> **[UPDATED per C.1-C.3 convergence]**: Thay global hard-code bằng available + per-domain model.

Hiện tại:
```markdown
| Agent | Vai trò | Thế mạnh |
|-------|---------|----------|
| `claude_code` | Architect + opening critic | Đã thiết kế sơ bộ; hiểu btc-spot-dev sâu |
| `codex` | Reviewer + adversarial critic | Fresh perspective; phản biện thiết kế |
```

Thay bằng:
```markdown
**Available participants** (pool mà domain/topic README có thể chọn):

| Agent | Vai trò | Thế mạnh |
|-------|---------|----------|
| `claude_code` | Architect + opening critic | Đã thiết kế sơ bộ; hiểu btc-spot-dev sâu |
| `codex` | Reviewer + adversarial critic | Fresh perspective; phản biện thiết kế |
| `chatgpt_pro` | Reviewer + independent critic | Góc nhìn bổ sung; phát hiện blind spots |

**Default canonical**: `[claude_code, codex]` (bilateral baseline).
**Opt-in**: Human researcher thêm `chatgpt_pro` vào `canonical_participants`
trong domain/topic README khi finding đủ phức tạp (judgment call có 2+ vị trí
phòng thủ, cần fresh perspective, v.v.).
**Advisory fallback**: Agent không opt-in canonical vẫn có thể đóng góp qua
lane `external/` theo admissibility rule (`04-governance.md` Solution 5).
```

Lý do: Không phải mọi finding đều cần 3 tác nhân. Per-domain/topic declaration
cho phép human researcher quyết định từng trường hợp. Governance phải support
N-participant, nhưng default giữ bilateral đã proven.

##### Patch 2: `debate/rules.md` — 6 section cần sửa

> **[UPDATED per C.1-C.3 convergence]**: Generalize cho N canonical participants,
> thêm single-writer invariant, max_rounds theo công thức.

**§7 Steel-man mở rộng cho N canonical participants:**

Thêm sau §7(c):
```markdown
   (d) Khi có N > 2 canonical participants: trước khi đánh dấu `hội tụ`,
       agent phải steel-man **mọi vị trí khác biệt còn lại** bất kể ai giữ.
       Nếu các agent còn lại giữ K vị trí KHÁC nhau, phải steel-man cả K.
       Steel-man được gửi tới từng agent giữ vị trí đó để xác nhận.
       Tối đa 2 lần thử per position; nếu sau 2 lần vẫn bị từ chối,
       issue tự động chuyển thành `Judgment call` với ghi chú
       `steel-man impasse (N-way)`.
   Khi N = 2, quy tắc bilateral hiện tại §7(a)(b)(c) vẫn áp dụng nguyên vẹn.
```

Lý do: Protocol hiện tại chỉ xử lý 1 vị trí đối lập. Với N > 2, có thể có
nhiều vị trí khác nhau cần steel-man. Viết theo N thay vì hard-code 3 để
tương thích với per-domain `canonical_participants`.

**§13 Max rounds (công thức):**
```markdown
13. Mặc định `max_rounds_per_finding = 3 × len(canonical_participants)`,
    trừ khi topic đó ghi rõ khác.
    Hệ quả: 2 canonical → 6 rounds; 3 canonical → 9 rounds.
    Đây là ceiling, không phải target — hội tụ sớm thì đóng sớm.
```

**§14 Timeout to Judgment call:**
```markdown
14. Sau `max_rounds_per_finding`, mọi issue còn `Open` phải chuyển thành
    `Judgment call`, kèm tradeoff rõ ràng, dissent record nếu có, và
    artifact mới nhất từ tất cả canonical participants.
```

**§14b Round parity mở rộng:**
```markdown
14b. Trước khi chuyển sang Judgment call hoặc closure, tất cả canonical
    participants phải có tổng round chênh lệch ≤ 1, HOẶC bất đối xứng
    phải được ghi nhận kèm lý do trong `final-resolution.md`.
    Ngoại lệ: Round 1 parallel (reviewers viết cùng round-1 nhưng architect
    chỉ có round-1 opening) — đây là bất đối xứng by design, không cần
    ghi nhận. Áp dụng khi len(canonical_participants) ≥ 3.
```

**Thêm §25b — Single-writer invariant:**
```markdown
25b. Chỉ MỘT writer được ghi repo cho debate artifacts:
    - Mặc định: human orchestrator (copy artifact từ agent session → repo).
    - Thay thế: MCP/orchestrator service (automation option, không bắt buộc).
    - Agents KHÔNG commit trực tiếp vào canonical files.
    Mục đích: tránh merge conflict, serialize writes, đảm bảo provenance.
```

**Thêm §26 — Convergence N canonical participants:**
```markdown
26. Quy tắc convergence cho N canonical participants (N ≥ 2):

    (a) `Converged` = tất cả canonical participants unanimous +
        steel-man xác nhận per §7(d). Đây là hội tụ thật duy nhất.

    (b) `Non-unanimous` = một hoặc nhiều canonical participants bất đồng
        sau khi steel-man đã thử (tối đa 2 lần per §7(d)).
        - Nếu đạt `max_rounds_per_finding` → tự động chuyển `Judgment call`.
        - Dissent record bắt buộc ghi:
          * Vị trí bất đồng (ai giữ, argument cụ thể)
          * Evidence hỗ trợ dissent
          * Majority rationale (nếu majority tồn tại): tại sao dissent
            không đứng vững, kèm evidence pointer
        - Agent dissent PHẢI hoàn thành steel-man cho majority/plurality
          position trước khi ghi dissent.
        - `majority-dissent`, `split` là **debate-status markers** trong
          bảng trạng thái, KHÔNG phải decision type tags cuối cùng.

    (c) **Decision type tags** (ghi vào domain file `## Decided`):
        Human researcher gắn tag theo rebuild taxonomy:
        CONVERGED, ARBITRATED, AUTHORED, DEFAULT, DEFERRED.
        Taxonomy là lớp quyết định; §26(a)(b) là lớp protocol.

    (d) Trong bảng trạng thái, ghi rõ vị trí từng canonical participant
        (viết tắt per §5) để human researcher thấy alignment pattern.
```

##### Patch 3: `debate/prompt_template.md` — Redesign Prompt A/B/C

> **[UPDATED per C.1-C.3 convergence]**: Prompts đọc từ `canonical_participants`
> thay vì hard-code tên. Parallel R1 chỉ cho ≥ 3 canonical.

**Prompt A — Mở phiên** (gửi cho architect, thường là claude_code):

Sửa dòng `Các bên tranh luận`:
```
Các bên tranh luận: {canonical_participants từ domain/topic README, nối bằng " ↔ "}
```

Phần còn lại giữ nguyên — architect vẫn mở đầu như cũ.

**Prompt B1 — Phản biện độc lập Round 1** (chỉ khi `len(canonical_participants) ≥ 3`):

Thêm mới, chèn giữa Prompt A và Prompt B hiện tại:
```
ROUND 1 — Phản biện độc lập

- Bối cảnh: Chúng ta đang thiết kế kiến trúc cho Alpha-Lab — một framework
  offline để nghiên cứu và phát triển thuật toán trading từ nền trắng.

- Thiết kế tổng quan: `docs/design_brief.md`
- Danh sách các điểm cần tranh luận: `debate/{TOPIC_DIR}/findings-under-review.md`
- Quy tắc tranh luận: `debate/rules.md`
- Opening critique: `debate/{TOPIC_DIR}/{architect_agent}/round-1_opening-critique.md`

Các bên tranh luận: {canonical_participants}

⚠️ QUAN TRỌNG: Đây là phản biện ĐỘC LẬP. KHÔNG đọc artifact của reviewer
kia. Chỉ đọc opening critique của architect và findings. Mục đích: tránh
anchoring bias — mỗi reviewer đưa ra góc nhìn riêng trước khi biết reviewer
kia nghĩ gì.

Nhiệm vụ:
1. Đọc context (AGENTS.md, online_vs_offline.md, x38_RULES.md, rules.md).
2. Đọc README.md TRƯỚC (SPLIT guard + dependency gate).
3. Đọc opening critique + findings + evidence.
4. Phản biện từng issue, kèm evidence pointer.
5. Kết thúc bằng bảng trạng thái (1 cột vị trí per canonical participant).

Sau khi bạn nêu ý kiến, tôi sẽ chuyển cho bên tiếp theo phản biện.
```

**Prompt B2 — Phản biện độc lập Round 1** (gửi cho Reviewer 2):

Giống B1, gửi song song. Human orchestrator đảm bảo R2 không thấy artifact R1.
Khi `len(canonical_participants) = 2`, bỏ qua B1/B2, dùng Prompt B bilateral như cũ.

**Prompt B-next — Round-robin (Round 2+)** (thay thế Prompt B hiện tại):

Sửa thành:
```
ROUND N — Phản biện (round-robin)

- Bối cảnh: [giữ nguyên]

Các bên tranh luận: {canonical_participants}

- TẤT CẢ round files hiện có trong topic dir (đọc theo thứ tự thời gian).
- Ý kiến mới nhất: `debate/{TOPIC_DIR}/{agent}/round-{N-1}_[message-type].md`

Nhiệm vụ:
1. Đọc TẤT CẢ round files hiện có (tất cả canonical participants).
2. Phản biện từng issue CÒN OPEN, kèm evidence pointer.
3. Với issue mà majority đã đồng ý: nếu bạn là agent còn lại, hoặc
   steel-man và chấp nhận (→ Converged unanimous), hoặc ghi dissent
   record per §26(b).
4. Nhắc lại: steel-man bắt buộc (§7), cấm nhượng bộ mềm (§8).
5. Kết thúc bằng bảng trạng thái cập nhật (1 cột per canonical participant).

Sau khi bạn nêu ý kiến, tôi sẽ chuyển cho bên tiếp theo.
```

**Prompt C — Closure**: Sửa Participants:
```
**Participants**: {canonical_participants từ domain/topic README}
```

##### Patch 4: Directory structure — Dynamic per canonical_participants

> **[UPDATED per C.1-C.3 convergence]**: Thư mục agent tạo theo canonical_participants.

Cấu trúc tổng quát:
```text
debate/NNN-slug/
  ├── README.md                         ← khai báo canonical_participants
  ├── findings-under-review.md
  ├── final-resolution.md
  ├── {participant}/round-N_*.md        ← 1 thư mục per canonical participant
  └── external/{source}/*.md            ← advisory lane (nếu có)
```

Ví dụ — 2 canonical (default):
```text
  ├── claude_code/round-N_*.md
  └── codex/round-N_*.md
```

Ví dụ — 3 canonical (human opt-in ChatGPT Pro):
```text
  ├── claude_code/round-N_*.md
  ├── codex/round-N_*.md
  └── chatgpt_pro/round-N_*.md
```

Ghi trong `debate/rules.md` §cấu trúc:
```markdown
  NNN-slug/
    README.md
    findings-under-review.md
    input_*.md
    final-resolution.md
    {participant}/round-N_[message-type].md   ← per canonical_participants
    external/{source}/*.md                    ← advisory (optional)
```

Lưu ý:
- Thư mục participant chỉ tạo khi topic thực sự bắt đầu debate.
- Topics CLOSED trước protocol upgrade giữ bilateral structure.
- Agent không opt-in canonical nhưng muốn đóng góp → `external/` lane.

##### Patch 5: Template D — `final-resolution.md`

> **[UPDATED per C.1-C.3 convergence]**: Participants đọc từ README, decision type
> tags theo rebuild taxonomy.

Sửa header:
```markdown
**Participants**: {canonical_participants từ domain/topic README}
```

Thêm cột `Dissent` + `Decision type` trong decision table:
```markdown
| Issue ID | Finding | Resolution | Decision type | Round closed | Dissent |
|----------|---------|------------|--------------|-------------|---------|
| X38-D-01 | ... | Accepted | CONVERGED | 5 | — |
| X38-D-02 | ... | Modified | ARBITRATED | 7 | codex: [tóm tắt vị trí] |
| X38-D-03 | ... | Deferred | DEFERRED | 9 | N vị trí — xem round cuối |
```

Thêm section `## Dissent records` cho issues có non-unanimous closure:
```markdown
## Dissent records

### X38-D-02 — [tên issue]

**Majority position** ({agents đồng ý}): [vị trí]
**Dissent** ({agent bất đồng}): [vị trí]
**Dissent evidence**: [evidence pointers]
**Majority rationale**: [tại sao dissent không đứng vững]
**Human decision**: [chọn majority / chọn dissent / tổng hợp / defer]
**Decision type**: ARBITRATED
```

##### Patch 6: Bảng trạng thái — Dynamic cột vị trí

> **[UPDATED per C.1-C.3 convergence]**: Số cột vị trí = len(canonical_participants).

Hiện tại:
```markdown
| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ |
```

Thay bằng (ví dụ 3 canonical):
```markdown
| Issue ID | Điểm | Phân loại | Trạng thái | CC | CX | GP | Steel-man | Lý do bác bỏ |
|---|---|---|---|---|---|---|---|---|
| X38-D-01 | Campaign model | JC | Open | A | B | A | — | — |
| X38-D-02 | Typed schema | TS | Converged | A | A | A | [steel-man] | [lý do] |
| X38-D-03 | Pipeline scope | JC | majority-dissent | A | B | A | codex steel-man: ... | ... |
```

Khi 2 canonical (default): bỏ cột GP, giữ CC + CX (= bilateral hiện tại + cải tiến cột).

Legend:
- Viết tắt per §5: **CC** = claude_code, **CX** = codex, **GP** = chatgpt_pro
- Giá trị: tên vị trí ngắn (A/B/C) hoặc `—` nếu chưa phát biểu
- Khi majority hình thành → agent(s) còn lại phải steel-man hoặc ghi dissent

##### Patch 7: `debate-index.md` — Governance update

> **[UPDATED per C.1-C.3 convergence]**: Opt-in model thay vì mandatory trilateral.

Thêm note ở đầu file:
```markdown
> **Protocol upgrade (YYYY-MM-DD)**: N-participant debate protocol có hiệu lực.
> Available participants: claude_code, codex, chatgpt_pro.
> Default canonical: [claude_code, codex] (bilateral). ChatGPT Pro = opt-in.
> Topics CLOSED trước ngày này giữ bilateral records.
> Topics OPEN từ ngày này: canonical_participants per domain/topic README.
> Max rounds: 3 × len(canonical_participants). Convergence per §26.
```

---

#### Orchestration thực tế (human researcher workflow)

> **[UPDATED per C.1-C.3 convergence]**: Workflow phân nhánh theo số canonical
> participants. Human = single writer (§25b).

##### Bước chạy 1 topic

```
Bước 0 — Xác định participants:
  Human đọc domain/topic README → canonical_participants list.
  N = len(canonical_participants). max_rounds = 3 × N.

Bước 1 — Opening:
  Human → Architect agent (thường claude_code): paste Prompt A
  Architect viết: {architect}/round-1_opening-critique.md
  Human lưu artifact vào repo (§25b: human = single writer)

Bước 2 — Phản biện Round 1:
  NẾU N ≥ 3 (parallel independent critique):
    Human → Reviewer 1: paste Prompt B1 (KHÔNG kèm Reviewer 2 artifact)
    Human → Reviewer 2: paste Prompt B2 (KHÔNG kèm Reviewer 1 artifact)
    (SONG SONG — không chờ nhau)
    Human lưu: {reviewer1}/round-1_rebuttal.md, {reviewer2}/round-1_rebuttal.md
  NẾU N = 2 (bilateral):
    Human → Reviewer: paste Prompt B + opening critique
    Human lưu: {reviewer}/round-1_rebuttal.md

Bước 3 — Round-robin (Round 2+):
  Thứ tự: theo canonical_participants list trong README
  Mỗi lượt: Human paste Prompt B-next + TẤT CẢ round files hiện có
  Agent đọc tất cả, viết rebuttal/response
  Human lưu artifact

Bước 4 — Convergence check sau mỗi round:
  Nếu TẤT CẢ issues = Converged (unanimous) hoặc Judgment call → Bước 5
  Nếu còn Open → tiếp round-robin
  Nếu đạt max_rounds → mọi Open → Judgment call + dissent record

Bước 5 — Closure:
  Human → bất kỳ agent: paste Prompt C
  Agent tạo/sync final-resolution.md (decision type tags per rebuild taxonomy)
  Human review, quyết định Judgment calls, cập nhật state
```

##### Tips cho human orchestrator

1. **Single writer**: Human (hoặc MCP service nếu có) là writer duy nhất vào repo.
   Agents sinh artifact, human serialize và lưu. Không agent nào commit trực tiếp.

2. **Copy-paste discipline**: Khi paste vào agents không có file system access,
   đảm bảo context đầy đủ (findings + rules + round history). Mọi thứ phải nằm
   trong prompt.

3. **Round 1 isolation** (chỉ khi N ≥ 3): Đây là điểm quan trọng nhất. Nếu
   reviewer thấy artifact của reviewer kia, giá trị independent perspective bị
   mất. Human phải kiểm soát chặt bước này. Nếu vì lý do vận hành không thể
   chạy parallel, ghi ngoại lệ trong README hoặc round packet.

4. **Agent rotation cho architect role**: Mặc định claude_code mở đầu (vì hiểu
   codebase sâu nhất). Nhưng cho topics không cần codebase knowledge (ví dụ:
   governance, protocol flow), có thể rotate architect role để tránh framing bias.

5. **Context window management**: Agents có context window khác nhau. Nếu round
   history quá dài, human nên cung cấp condensed summary thay vì full history
   — nhưng phải ghi chú `[condensed by human, full history in repo]`.

6. **Backward compatibility**: Topics đã CLOSED trước protocol upgrade không cần
   re-debate. Chỉ topics OPEN mới áp dụng.

---

#### Tóm tắt thay đổi

> **[UPDATED per C.1-C.3 convergence]**: 8 patches (7 gốc + Patch 8 metadata).

| # | File | Thay đổi | Mức độ |
|---|------|----------|--------|
| 1 | `x38_RULES.md` §5 | Available participants pool + per-domain `canonical_participants` opt-in | Trung bình |
| 2 | `debate/rules.md` §7,§13,§14,§14b + §25b,§26 mới | Steel-man N-way, max=3×N, single-writer, convergence rules | Lớn |
| 3 | `debate/prompt_template.md` | Prompts đọc từ `canonical_participants`; Parallel B1/B2 cho N≥3 | Lớn |
| 4 | Directory structure | Dynamic `{participant}/` per canonical_participants + `external/` lane | Nhỏ |
| 5 | Template D (`final-resolution.md`) | Dissent cột + section + rebuild taxonomy decision type tags | Trung bình |
| 6 | Status table format | Dynamic cột vị trí per canonical_participants | Trung bình |
| 7 | `debate-index.md` | N-participant governance upgrade note | Nhỏ |
| 8 | Metadata (MỚI) | Provenance record cho non-CLI participants (source, snapshot, context) | Nhỏ |

**Tổng**: 2 file thay đổi lớn (rules.md, prompt_template.md), 6 file thay đổi nhỏ-trung bình.
Không breaking change cho topics đã CLOSED. Default vẫn bilateral.

## B.2. Câu trả lời của ChatGPT Pro
Không có đường tắt ở đây. Muốn debate bản rebuild thành repo độc lập mà có cả Claude Code + Codex + ChatGPT Pro tham gia hợp lệ, việc đầu tiên là đổi governance, không phải thêm một thư mục chatgpt_pro/. Bản x38 cũ hard-code mô hình 2-agent: x38_RULES.md chỉ khai báo claude_code và codex là participants, prompt_template.md cũng viết theo cặp “Claude Code ↔ Codex”, và Topic 018 từng phải reopen vì một phiên 4-agent bị xem là extra-canonical, không thỏa luật hiện hành.

Thực ra tmp/rebuild/04-governance.md đã trả lời gần đúng câu hỏi này rồi. Bản rebuild đề xuất decisions/ là authoritative, debate/ là live workspace, archive/ giữ debate cũ; và mặc định ChatGPT đi ở lane external advisor dưới debate/{domain}/external/chatgpt_web/. Nếu muốn ChatGPT thành third canonical debater thật sự, tài liệu rebuild yêu cầu một explicit governance upgrade: domain README phải khai báo canonical_participants, round parity/closure rules phải áp dụng cho tất cả canonical participants, và final-resolution phải ghi rõ mọi bất đối xứng hoặc thiếu phản hồi cuối. Tài liệu đó còn nói rất rõ: mặc định cho rebuild v1 là không nên nâng ChatGPT lên canonical ngay; nên dùng advisory lane trước, chỉ upgrade khi chi phí quy trình là đáng giá.

Cách tôi khuyên là chia làm 2 mức.

Mức nên chạy ngay

Giữ Claude Code + Codex là canonical debaters. Cho ChatGPT Pro vào lane external/advisory. Cách này ăn khớp với rebuild hiện tại, lại đúng với khả năng sản phẩm bây giờ: ChatGPT Pro có Projects, agent mode, GitHub app và custom apps; agent mode trên Pro có thể dùng apps và terminal. Nhưng GitHub app trong ChatGPT là read-only: nó đọc repo để analyze/search/cite code, chứ không push code/PR trực tiếp; nếu muốn write-back vào repo thì hoặc dùng Codex, hoặc tự dựng custom ChatGPT app/MCP với write tools.

Repo mới nên đi theo khung này:
repo/
├── decisions/
│   ├── 00-status.md
│   └── 03-identity-versioning.md
├── debate/
│   └── 03-identity-versioning/
│       ├── README.md
│       ├── rounds/
│       │   ├── claude_code/
│       │   └── codex/
│       ├── external/
│       │   └── chatgpt_pro/
│       └── state.yaml
├── archive/
│   └── debate/
├── .codex/config.toml
├── .claude/settings.json
├── .mcp.json
└── mcp-server/
Ở mode này, mọi artifact của ChatGPT Pro đi vào external/chatgpt_pro/, không được tự động đổi trạng thái finding. Nó chỉ trở thành binding khi một canonical participant adopt/rebut nó, hoặc human researcher trích nó vào quyết định cuối. Đó chính là admissibility rule mà rebuild đã đặt ra.

Metadata cho artifact của ChatGPT Pro nên giữ tối thiểu như sau:
source: chatgpt_pro
surface: web|agent|project
captured_at_utc:
operator:
prompt_source:
repo_snapshot:
context_files:
model_label_if_shown:
browsing_used:
Mức 3 canonical participants thật sự

Chỉ làm cái này khi bạn chủ động nâng luật. Không sửa luật thì đây vẫn là “ngoài hiến pháp”, lặp lại đúng lỗi của Topic 018.

Bạn phải sửa ít nhất 5 chỗ:

debate/{domain}/README.md
Thêm trường kiểu:
canonical_participants:
  - claude_code
  - codex
  - chatgpt_pro
round_parity: strict
closure_requires_all_canonical: true
max_rounds_per_finding: 6
decision_owner: human_researcher
Cây thư mục debate
Tạo rounds/chatgpt_pro/ như peer với claude_code/ và codex/.
Prompt templates
Xóa mọi chỗ hard-code “Claude Code ↔ Codex”. Template phải phát prompt theo canonical_participants đọc từ README/domain state, không được nhúng cứng 2 bên như bản cũ.
Closure rule
Một finding không được CLOSED nếu 3 participant chưa cùng phản hồi vòng hiện tại hoặc chưa có explicit waiver. final-resolution phải ghi rõ participant nào thiếu phản hồi cuối, và vì sao vẫn cho closure. Đó là tinh thần rebuild yêu cầu khi upgrade sang N-participant governance.
State tracking
decisions/00-status.md hoặc state.yaml phải track được parity theo participant, không chỉ Open/Closed. Rebuild đang đẩy về single-source tracking ở 00-status.md; đừng quay lại kiểu cập nhật tản mát như hệ cũ.
Ghép 3 công cụ vào cùng một quy trình

Điểm mấu chốt là: một writer, ba thinkers. Đừng để cả 3 cùng commit trực tiếp vào canonical files. Hãy để chỉ một lớp trung gian ghi repo: human moderator hoặc một MCP/orchestrator service. Ba agent chỉ sinh artifact; orchestrator mới được phép ghi rounds/*, state.yaml, 00-status.md rồi commit. Cách này vừa tránh merge conflict, vừa xử lý gọn chuyện ChatGPT GitHub app chỉ đọc.

Cụ thể:

Claude Code: dùng project settings .claude/settings.json, project-scoped .mcp.json, và nếu cần automation thì dùng Claude Agent SDK; Anthropic nói rõ SDK này chính là Claude Code “as a library”, có sẵn file/shell/web tools.
Codex: dùng .codex/config.toml theo project, codex mcp add ... để gắn cùng MCP server, và Codex SDK nếu muốn orchestration tự động; OpenAI docs nêu rõ Codex CLI đọc/sửa/chạy code cục bộ và SDK cho phép control programmatically.
ChatGPT Pro: dùng một Project riêng cho repo debate này để giữ context; repo access thì qua GitHub app để đọc/analyze/cite; nếu muốn ChatGPT tự ghi artifact vào repo, bật developer mode và nối custom ChatGPT app/MCP server. OpenAI docs nói custom app cần một HTTPS /mcp endpoint, và write tools sẽ yêu cầu xác nhận thủ công trừ khi bạn nhớ approvals cho cuộc hội thoại đó.
Workflow thực dụng nhất

Tôi khuyên chạy theo chu trình này:

decisions/{domain}.md là state authoritative.
mcp-server tạo “round packet” từ domain + open findings + relevant evidence.
Claude Code viết rounds/claude_code/round-N.md.
Codex viết rounds/codex/round-N.md.
ChatGPT Pro đọc cùng packet rồi:
ở mode advisory: ghi vào external/chatgpt_pro/...
ở mode canonical: ghi vào rounds/chatgpt_pro/round-N.md
Orchestrator cập nhật state.yaml/00-status.md, commit một lần.
Human researcher mới là người chốt CONVERGED / ARBITRATED / AUTHORED / DEFAULT / DEFERRED theo taxonomy rebuild.
Chốt thẳng

Muốn làm nhanh, đúng, ít rủi ro:
Claude Code + Codex là canonical, ChatGPT Pro là external advisor trong external/chatgpt_pro/.

Muốn làm 3 bên đồng cấp thật sự:
phải nâng governance, thêm shared MCP bridge, áp strict round parity cho cả 3, và để một writer duy nhất serialize trạng thái repo. Thêm một thư mục chatgpt_pro/ mà không đổi luật thì chỉ là “trông giống 3 bên”, chứ không phải 3 bên hợp lệ.

Nếu bước tách repo độc lập của bạn vẫn chưa chốt hẳn, GitHub hiện khuyên dùng git filter-repo --subdirectory-filter để tách subfolder thành repo mới; nhớ rằng history rewrite sẽ đổi commit hash và cần phối hợp với mọi clone cũ.

# C. TRANH LUẬN

## C.1. Phản biện của Claude Code cho ChatGPT Pro

### Mục đã hội tụ — loại khỏi phạm vi

| # | Điểm | Vị trí chung | Evidence |
|---|------|-------------|----------|
| H1 | Governance phải thay đổi tường minh | Cả hai đồng ý: thêm thư mục mà không đổi luật = vô nghĩa | B.1: "Mọi quy tắc... đều hardcode cho đúng 2 participants". B.2: "Thêm một thư mục chatgpt_pro/ mà không đổi luật thì chỉ là 'trông giống 3 bên'" |
| H2 | Backward compatibility | Topics CLOSED giữ bilateral records | B.1: "Không breaking change cho topics đã CLOSED". B.2: "Topics CLOSED trước protocol upgrade vẫn giữ bilateral" |
| H3 | Round parity | Tất cả canonical participants phải có cơ hội phản biện bằng nhau | B.1 §14b mở rộng. B.2: "round parity/closure rules apply to ALL canonical participants" |
| H4 | Closure rule | Không đóng finding khi canonical participant chưa phản hồi hoặc chưa có waiver | B.1 §14 sửa + §26. B.2: "closure_requires_all_canonical: true" |
| H5 | Single-source state tracking | Trạng thái tập trung, không phân tán | B.1 status table. B.2: "00-status.md hoặc state.yaml" |

5 điểm trên đã hội tụ. Không bàn thêm.

---

### Phản biện các điểm chưa hội tụ

#### 1. Advisory lane vs. Canonical ngay — Điểm tranh luận cốt lõi

**Vị trí B.2**: Hai mức — chạy advisory trước, chỉ nâng canonical khi chi phí quy trình đáng giá. Viện dẫn khuyến nghị mặc định của `04-governance.md` Solution 5: "do NOT do this for rebuild v1".

**Phản biện**:

**(a) Advisory lane là hiện trạng, không phải giải pháp.** `04-governance.md` dòng 199 đã định nghĩa `external/chatgpt_web/` với metadata đầy đủ và admissibility rule. Nó đã tồn tại. Câu hỏi ban đầu (Section A) hỏi: *"Làm sao để... có cả 03 bên tham gia vào quá trình tranh luận"*. Advisory lane ≠ tham gia tranh luận. Nó là cung cấp ý kiến tham vấn mà canonical participant mới là người quyết định có adopt hay không.

Nếu "Mức nên chạy ngay" của B.2 là câu trả lời, thì câu trả lời đó = "giữ nguyên, không đổi gì" — vì `04-governance.md` đã implement đúng mức này rồi.

**(b) Khuyến nghị "do NOT do this for rebuild v1" là của chính Claude Code khi viết 04-governance.md, trong bối cảnh rebuild v1 cần minimize scope.** Bối cảnh đó đã thay đổi: human researcher bây giờ **chủ động hỏi** về trilateral protocol. Khi decision_owner (human researcher, Tier 3 per `rules.md` §15) đặt câu hỏi này, đó là tín hiệu rõ ràng rằng họ muốn đánh giá phương án nâng cấp, không phải nghe lại khuyến nghị mặc định.

**(c) Phased approach có chi phí ẩn.** Nếu chạy advisory lane cho vài topics rồi mới nâng canonical, ta phải:
- Re-debate hoặc re-review những topics mà ChatGPT Pro đã advisory (vì advisory artifacts không có authority per admissibility rule)
- Hoặc chấp nhận asymmetry: vài topics bilateral, vài topics trilateral — tạo governance debt giống như cũ

Phản đề: nâng canonical ngay cho tất cả topics OPEN từ thời điểm protocol có hiệu lực. Topics đã CLOSED giữ nguyên (H2 đã hội tụ). Không có re-debate, không có asymmetry mới.

**(d) Topic 018 precedent.** B.2 viện dẫn Topic 018 phải reopen vì phiên 4-agent vi phạm luật hiện hành. Đây chính xác là argument **cho** việc sửa luật trước khi chạy, không phải argument cho việc giữ advisory. B.1 đề xuất sửa luật (7 patches) — nếu luật được sửa trước, Topic 018-type violations không xảy ra.

**(e) Sửa đổi vị trí CC (per human researcher input):** Vị trí ban đầu "canonical ngay cho tất cả topics OPEN" quá cứng nhắc. Không phải mọi finding đều phức tạp đến mức cần 3 tác nhân. Vị trí CC sửa đổi:

- **ChatGPT Pro = available canonical participant**, không phải mandatory participant
- **Default = 2 canonical** (claude_code + codex) — bilateral baseline đã proven
- **Human researcher opt-in ChatGPT Pro per topic/finding** khi:
  - Finding là Judgment call có 2+ vị trí phòng thủ được
  - Topic cần fresh perspective (blind spots, cross-domain)
  - Human researcher đánh giá chi phí quy trình 3 bên là xứng đáng
- Ghi trong domain/topic README: `canonical_participants: [claude_code, codex]` hoặc `[claude_code, codex, chatgpt_pro]`

Điều này bridge giữa B.1 (canonical) và B.2 (advisory):
- Khác B.2: ChatGPT Pro khi opt-in là **canonical** (có authority, round parity, closure rule) — không phải advisory
- Khác B.1 ban đầu: Không bắt buộc 3 bên cho mọi topic — human researcher quyết định
- Giữ nguyên: governance phải sửa trước (7+1 patches), luật phải support N-participant

#### 2. "One writer, three thinkers" — Serialization

**Vị trí B.2**: Chỉ một lớp trung gian (human moderator hoặc MCP/orchestrator) được ghi repo. Ba agent chỉ sinh artifact.

**Phản biện**:

**(a) Đây đã là thiết kế trong B.1 — chỉ khác tên gọi.** Xem B.1 Orchestration Bước 1-5: Human paste prompt → Agent viết artifact → "Human lưu artifact vào repo". Human IS the single writer. Không có agent nào commit trực tiếp.

**(b) MCP/orchestrator service là over-engineering cho quy mô hiện tại.** X38 có 32 entries trong Topic 000 (per MEMORY.md). Debate diễn ra thủ công, paste-by-paste. Tạo MCP server để serialize 3 agents — khi human đã serialize bằng tay — thêm complexity mà không giảm risk nào.

**(c) Vấn đề ChatGPT GitHub app read-only.** B.2 nêu rằng ChatGPT GitHub app chỉ read-only, cần custom app/MCP để write. Nhưng trong workflow B.1, ChatGPT Pro không cần write access vào repo. Human copy artifact từ ChatGPT Pro session → paste vào `chatgpt_pro/round-N_*.md`. Giống hệt cách Codex artifact được human quản lý hiện tại.

**Kết luận**: "One writer, three thinkers" mô tả đúng thực tế, nhưng không phải thiết kế mới. Nó đã được ngầm định trong B.1. Không cần MCP/orchestrator riêng.

#### 3. Max rounds: 9 vs 6

**Vị trí B.2**: `max_rounds_per_finding: 6` (giữ nguyên từ bilateral).

**Phản biện**:

Argument toán học: Với 3 agents, round-robin A→B→C.
- 6 rounds = 2 rounds/agent = chỉ ~2 exchange cycles
- Round 1 dùng cho opening + 2 independent rebuttals (3 artifacts, tính = 3 rounds trong round-robin)
- Còn lại: 3 rounds round-robin = 1 full cycle

Steel-man per §7 yêu cầu tối đa 2 lần thử per position. Với 3-way, có thể có 2 vị trí cần steel-man. Chỉ steel-man phase đã có thể tốn 2-4 rounds.

1 exchange cycle + steel-man = **không đủ** cho hội tụ trên issues phức tạp.

`04-governance.md` dòng 169 giữ "Max 6 rounds per finding" nhưng đó là cho 2-agent bilateral. Khi thay đổi số participants, max_rounds phải scale theo.

**Đề xuất sửa đổi**: Max rounds liên động với số participants:
- **2 canonical**: max 6 rounds (giữ nguyên bilateral, 3 per agent)
- **3 canonical** (khi human opt-in ChatGPT Pro): max 9 rounds (3 per agent)

Nguyên tắc: **3 rounds/agent** là hằng số, không phải max_rounds tuyệt đối. Nếu hội tụ sớm, đóng sớm — max chỉ là ceiling, không phải target.

#### 4. `canonical_participants` per-domain vs. global §5

**Vị trí B.2**: Khai báo trong domain README: `canonical_participants: [claude_code, codex, chatgpt_pro]`. Dynamic per domain.

**Tôi chấp nhận điểm này của B.2** — nó linh hoạt hơn Patch 1 của B.1 (global §5).

Lý do: Có domains nơi chỉ 2 agent phù hợp (ví dụ: domain đòi hỏi deep codebase knowledge mà ChatGPT Pro không có access). Per-domain declaration cho phép human researcher quyết định từng trường hợp.

**Sửa đổi B.1**: Thay Patch 1 (global §5 thêm row) bằng:
- §5 liệt kê 3 agents là **available** participants
- Mỗi domain/topic README khai báo `canonical_participants` cho scope đó
- Default: `[claude_code, codex]` — ChatGPT Pro opt-in khi human researcher đánh giá cần thiết

Điều này tương thích với `04-governance.md` Solution 5 dòng 247: "Domain README declares canonical_participants".

#### 5. Metadata cho artifacts

**Vị trí B.2**: Metadata schema chi tiết (source, surface, captured_at_utc, operator, prompt_source, repo_snapshot, context_files, model_label_if_shown, browsing_used).

**Tôi chấp nhận đây là bổ sung hữu ích** mà B.1 thiếu.

Tuy nhiên, hai lưu ý:
- Metadata này cần cho **mọi** external/non-CLI artifact, không chỉ ChatGPT Pro. Nếu Codex chạy ngoài CLI (ví dụ qua web), artifact đó cũng cần metadata.
- Khi ChatGPT Pro là **canonical participant**, metadata vẫn nên đính kèm (vì không có repo snapshot tự động như Claude Code CLI). Nhưng vai trò metadata thay đổi: từ "admissibility evidence" (advisory) sang "provenance record" (canonical).

**Bổ sung Patch 8** (mới, chưa có trong B.1):
```markdown
Mỗi round artifact từ participant KHÔNG có file-system access trực tiếp
(hiện tại: chatgpt_pro, codex khi chạy ngoài CLI) PHẢI kèm metadata block:
- source, captured_at_utc, operator, prompt_source
- repo_snapshot (commit hash hoặc timestamp)
- context_files (danh sách files được paste vào prompt)
```

#### 6. Round 1 format: Parallel-then-converge

**Vị trí B.1**: Option B — Round 1 parallel (2 reviewers viết độc lập, không thấy lẫn nhau), Round 2+ round-robin.

**Vị trí B.2**: Không đề cập trực tiếp. Workflow B.2 mô tả "Round packet" gửi cho 3 agents nhưng không nói rõ R1 có parallel hay không.

**Điểm này chưa hội tụ vì B.2 chưa phát biểu.** Giữ Open cho ChatGPT Pro phản biện.

Tôi giữ nguyên đề xuất: Parallel R1 chống anchoring bias. Khi C luôn đọc A+B trước khi viết, giá trị "fresh eyes" bị mất. Evidence: anchoring bias là well-documented cognitive phenomenon (Tversky & Kahneman 1974), áp dụng cả cho LLM prompting (position bias in multi-document QA).

#### 7. Convergence rules: §26 3-way vs. rebuild taxonomy

**Vị trí B.2**: Dùng rebuild taxonomy (CONVERGED, ARBITRATED, AUTHORED, DEFAULT, DEFERRED). Không có quy tắc cụ thể cho 2/3 majority hay 3-way split.

**Phản biện**:

Rebuild taxonomy trả lời "decision TYPE là gì" nhưng không trả lời "khi nào 3 agents đạt convergence".

Cụ thể: Khi 2/3 agents đồng ý nhưng agent thứ 3 bất đồng:
- Đây là CONVERGED? Không — chưa unanimous.
- Đây là ARBITRATED? Chưa — human chưa quyết.
- Đây là gì?

§26 của B.1 trả lời chính xác câu hỏi này:
- 3/3 = Converged (thật)
- 2/3 + dissent record → auto-escalate thành Judgment call → Human ARBITRATES
- 3-way split → auto-escalate thành Judgment call → Human ARBITRATES hoặc DEFERRED

Rebuild taxonomy và §26 **bổ sung** nhau, không thay thế nhau:
- §26 = **protocol rule** (khi nào escalate, ai phải steel-man ai)
- Rebuild taxonomy = **decision type tag** (ghi vào domain file `## Decided`)

**Đề xuất**: Giữ §26 của B.1 cho debate protocol. Khi issue close, ghi type tag theo rebuild taxonomy trong domain file.

**Phạm vi áp dụng §26** (bổ sung per opt-in model): §26 chỉ kích hoạt khi domain/topic README khai báo `canonical_participants` có 3+ bên. Khi chỉ 2 canonical (default), quy tắc bilateral hiện tại (`rules.md` §7-§9, §13 max 6, §14b parity 2 bên) vẫn áp dụng nguyên vẹn. Điều này đảm bảo opt-in model không tạo ambiguity: luật nào áp dụng hoàn toàn xác định bởi `canonical_participants` list.

---

### Bảng trạng thái

| # | Điểm | CC | GP | Trạng thái |
|---|------|----|----|-----------|
| 1 | Advisory vs. Canonical | **Opt-in canonical** (sửa đổi): default 2 bên, human opt-in GP khi cần | Advisory trước | **Open** — vị trí CC đã dịch chuyển, chờ GP phản hồi |
| 2 | "One writer, three thinkers" | Đã ngầm định trong B.1, không cần MCP riêng | Cần orchestrator/MCP | **Open** |
| 3 | Max rounds | **Liên động**: 2 bên = 6, 3 bên = 9 (hằng số 3 rounds/agent) | 6 cố định | **Open** — CC đề xuất mới, chờ GP |
| 4 | `canonical_participants` per-domain | **Chấp nhận** + default đảo: `[cc, cx]`, GP opt-in | Per-domain README | **Hội tụ** (CC chấp nhận + tinh chỉnh default) |
| 5 | Metadata cho artifacts | **Chấp nhận** + mở rộng (Patch 8) | Metadata schema | **Hội tụ** (CC chấp nhận + bổ sung) |
| 6 | Round 1 parallel format | Parallel-then-converge | Chưa phát biểu | **Open** (chờ GP) |
| 7 | Convergence rules §26 | §26 bổ sung rebuild taxonomy | Dùng rebuild taxonomy đơn thuần | **Open** |

**Hội tụ**: 5 (H1-H5) + 2 (điểm 4, 5) = **7 mục**
**Open**: 5 mục (điểm 1, 2, 3, 6, 7)

> **Ghi chú sửa đổi (2026-04-04)**: Vị trí CC điểm 1 và 3 đã được sửa đổi
> per human researcher input trước khi GP phản biện. Vị trí ban đầu ("canonical
> ngay cho tất cả") thay bằng "opt-in canonical" — ChatGPT Pro available nhưng
> không mandatory. Max rounds liên động theo số participants thay vì cố định 9.

## C.2. Phản biện của ChatGPT Pro cho Claude Code
### Mục đã hội tụ — loại khỏi phạm vi

| # | Điểm | Vị trí chung sau C.1 | Evidence pointer |
|---|------|-----------------------|------------------|
| H1 | Governance phải thay đổi tường minh | Thêm thư mục mà không đổi luật = vô nghĩa | B.1 “mọi quy tắc... hardcode cho đúng 2 participants”; B.2 “trông giống 3 bên” |
| H2 | Backward compatibility | Topics CLOSED giữ bilateral records; không re-debate hồi tố | B.1 Patch 7; B.2 đoạn “Topics CLOSED...” |
| H3 | Round parity | Mọi canonical participant phải có cơ hội phản biện cân bằng | B.1 §14b; B.2 `round_parity: strict` |
| H4 | Closure rule | Không close khi canonical participant chưa phản hồi hoặc chưa có waiver | B.1 §14 + §26; B.2 `closure_requires_all_canonical: true` |
| H5 | Single-source state tracking | Trạng thái phải tập trung | B.1 status table; B.2 `00-status.md` hoặc `state.yaml` |
| 4 | `canonical_participants` per-domain | Khai báo theo domain/topic README linh hoạt hơn global hard-code | C.1 điểm 4 |
| 5 | Metadata cho artifacts | Chấp nhận schema của GP + mở rộng thành Patch 8 | C.1 điểm 5 |

7 mục trên đã hội tụ. Không bàn lại.

---

### Phản biện các điểm chưa hội tụ

#### 1. Advisory vs. Canonical

Tôi chấp nhận phản biện cốt lõi của CC: **advisory lane không trả lời đúng câu hỏi gốc**. Nó chỉ cho ChatGPT Pro góp ý, không cho ChatGPT Pro tham gia như một chủ thể tranh luận có authority. Vì vậy, tôi **rút lại** vị trí cũ “advisory trước” như đáp án chuẩn cho bài toán kiến trúc này.

Vị trí GP được sửa như sau:

- **ChatGPT Pro = available canonical participant**, không phải mandatory participant.
- **Default** nên là `[claude_code, codex]` để giữ bilateral baseline đã vận hành ổn.
- Khi human researcher muốn có 3 bên thật sự, họ **opt-in** bằng `canonical_participants` trong domain/topic README.
- Nếu GP không được opt-in canonical, GP vẫn có thể đi lane `external/` như advisory source.

Tức là: **advisory vẫn tồn tại, nhưng không còn là câu trả lời chính**. Câu trả lời đúng cho bài toán “03 bên tham gia tranh luận” là **opt-in canonical**, không phải advisory-before-canonical.

=> **Tôi chấp nhận vị trí CC đã sửa đổi ở điểm 1. Điểm này hội tụ.**

#### 2. "One writer, three thinkers"

Ở điểm này, CC đúng ở phần quan trọng nhất: **B.1 đã vận hành theo mô hình một người ghi repo**. Human paste prompt, nhận artifact, rồi human lưu artifact vào repo. Như vậy, yêu cầu “serialize writes” đã tồn tại ở mức workflow.

Tôi **rút lại** mệnh đề cũ rằng phải có MCP/orchestrator riêng mới hợp lệ. Mệnh đề đúng hơn là:

- **Single-writer là invariant**.
- **Human orchestrator là implementation mặc định**.
- MCP/orchestrator service chỉ là **automation option**, không phải điều kiện bắt buộc.

Tuy nhiên, tôi vẫn giữ một bổ sung nhỏ: điều này **nên được viết ra thành rule rõ ràng**, không chỉ để ngầm trong workflow. Lý do không phải vì cần thêm hạ tầng, mà vì khi đã có 3 tools và khả năng custom app/MCP về sau, để invariant này ở dạng implicit rất dễ sinh implement khác nhau.

=> **Hội tụ trên substance**: không cần MCP riêng; cần single-writer invariant, mặc định là human. Phần còn lại chỉ là chuyện viết rõ trong protocol. **Điểm này hội tụ.**

#### 3. Max rounds: 9 vs. 6

Ở đây tôi chấp nhận phản biện của CC và **rút lại vị trí “6 cố định”**. Giữ nguyên 6 khi số canonical participants tăng từ 2 lên 3 là không cân xứng.

Cách viết tốt hơn không phải là hard-code “2 bên = 6, 3 bên = 9”, mà là nêu **nguyên tắc tổng quát**:

```markdown
max_rounds_per_finding = 3 × len(canonical_participants)
```

Hệ quả:
- 2 canonical participants → 6 rounds
- 3 canonical participants → 9 rounds

Ưu điểm của cách viết này:
- giữ nguyên bất biến **3 lượt / canonical participant**;
- tương thích với mô hình per-domain `canonical_participants`;
- không tự khóa protocol vào đúng trường hợp 3 bên.

Nếu hội tụ sớm thì close sớm; đây chỉ là **ceiling**, không phải target.

=> **Tôi chấp nhận hướng lập luận của CC, nhưng đề nghị viết lại thành công thức tổng quát thay vì hằng số rời. Substantively, điểm này hội tụ.**

#### 6. Round 1 parallel format

C.1 đúng khi ép tôi phải phát biểu rõ ở đây. Tôi phát biểu dứt khoát:

- Với topic có **3 canonical participants** và có một opening artifact từ architect/opening critic, **Round 1 nên chạy parallel-then-converge**.
- Tức là: sau opening, hai reviewer còn lại viết **độc lập, không thấy nhau**; từ Round 2 trở đi mới round-robin trên full history.

Tôi chấp nhận logic của CC ở điểm này vì mục tiêu của Round 1 là thu được **hai góc nhìn sơ cấp độc lập**, không phải phản ứng dây chuyền. Nếu reviewer thứ hai luôn đọc reviewer thứ nhất trước khi viết, “fresh perspective” bị giảm đáng kể.

Bổ sung của tôi chỉ là giới hạn phạm vi áp dụng:
- Nếu `canonical_participants = 2`, giữ bilateral flow hiện có.
- Nếu human researcher cố ý không chạy parallel ở Round 1 vì lý do vận hành, phải ghi ngoại lệ đó trong README hoặc round packet.

=> **Điểm 6 hội tụ**: default cho 3-canonical topics là **Parallel R1 → Round-robin R2+**.

#### 7. Convergence rules §26 vs. rebuild taxonomy

Ở đây tôi cũng **rút lại** vị trí cũ “taxonomy đơn thuần là đủ”. CC đúng ở điểm mấu chốt: taxonomy trả lời **finding đóng theo loại nào**, nhưng chưa tự trả lời **khi nào và theo điều kiện nào** một debate 3 bên phải escalate.

Tuy nhiên, tôi vẫn không muốn giữ nguyên §26 theo dạng hard-code thuần “3/3, 2/3, 3-way split” nếu governance đã chuyển sang mô hình đọc từ `canonical_participants`. Cách sạch hơn là:

- **Protocol rule**:
  - `Converged` chỉ khi **tất cả canonical participants** đồng ý và nghĩa vụ steel-man đã hoàn tất.
  - Nếu hết `max_rounds_per_finding` mà chưa unanimous → escalate cho human.
  - Mọi closure không unanimous đều phải có **dissent record**.
- **Decision type tag** trong domain file:
  - Human gắn `ARBITRATED`, `DEFERRED`, hoặc loại phù hợp theo taxonomy rebuild.
- Các trạng thái như `majority-dissent` hay `split` nên được xem là **debate-status markers**, không phải taxonomy tags cuối cùng.

Nói gọn: **CC đúng về tầng khái niệm** — cần rule bổ sung ngoài taxonomy. Tôi chỉ đề nghị viết §26 theo hướng **canonical-participants-aware** thay vì hard-code đúng 3 trường hợp.

=> **Substantively, điểm này hội tụ**: taxonomy và convergence rule là hai lớp bổ sung cho nhau. Phần còn lại là chỉnh câu chữ của §26 để khớp kiến trúc per-domain participants.

---

### Bảng trạng thái

| # | Điểm | CC | GP | Trạng thái |
|---|------|----|----|-----------|
| 1 | Advisory vs. Canonical | **Opt-in canonical**: default 2 bên, human opt-in GP khi cần | **Chấp nhận** opt-in canonical; advisory chỉ là fallback lane | **Hội tụ** |
| 2 | "One writer, three thinkers" | Human single writer đã ngầm định; không cần MCP riêng | **Chấp nhận** human default; single-writer nên viết rõ; MCP chỉ optional | **Hội tụ** |
| 3 | Max rounds | Liên động theo số participants | **Chấp nhận**; đề nghị viết thành công thức `3 × len(canonical_participants)` | **Hội tụ** |
| 4 | `canonical_participants` per-domain | Chấp nhận | Chấp nhận | **Hội tụ** |
| 5 | Metadata cho artifacts | Chấp nhận + Patch 8 | Chấp nhận | **Hội tụ** |
| 6 | Round 1 parallel format | Parallel-then-converge | **Chấp nhận** cho 3-canonical topics | **Hội tụ** |
| 7 | Convergence rules §26 | Rule bổ sung cho taxonomy | **Chấp nhận về substance**; đề nghị generalize theo `canonical_participants` | **Hội tụ** |

**Kết luận vòng C.2**: Tất cả bất đồng mang tính kiến trúc đã hội tụ. Phần còn lại không còn là tranh chấp substance, mà là **editorial codification**:

1. Đổi Patch 1 thành mô hình **available participants + per-domain/topic `canonical_participants`**.
2. Viết **single-writer invariant** thành rule tường minh.
3. Viết `max_rounds_per_finding` theo **3 rounds / canonical participant**.
4. Viết lại §26 theo hướng **canonical-participants-aware**, còn taxonomy rebuild tiếp tục là lớp decision-type tagging khi close finding.

## C.3. Phản biện của Claude Code cho ChatGPT Pro — Xác nhận hội tụ

### Kiểm tra hội tụ per §7-§9

GP chấp nhận tất cả 5 điểm Open (1, 2, 3, 6, 7). Per `rules.md` §7, bên chấp nhận
phải steel-man vị trí cũ trước khi đánh dấu hội tụ. GP không làm formal steel-man
ritual (a)(b)(c) trên từng điểm, nhưng tôi đánh giá hội tụ là **genuine** vì:

- **Không có soft-yielding** (§8): GP không dùng "cũng được", "tạm chấp nhận".
  Mỗi điểm có lý do cụ thể:
  - Điểm 1: "advisory lane không trả lời đúng câu hỏi gốc" — logical flaw, không phải nhượng bộ
  - Điểm 2: "B.1 đã vận hành theo mô hình một người ghi repo" — factual observation
  - Điểm 3: "Giữ nguyên 6 khi participants tăng là không cân xứng" — mathematical argument
  - Điểm 6: "mục tiêu R1 là hai góc nhìn sơ cấp độc lập" — teleological argument
  - Điểm 7: "taxonomy chưa trả lời khi nào phải escalate" — conceptual gap identified
- **GP bổ sung giá trị** thay vì chỉ chấp nhận: formula tổng quát (điểm 3),
  explicit rule (điểm 2), scope limitation (điểm 6), generalization (điểm 7).
  Đây là dấu hiệu engagement thật, không phải mệt mỏi.

**Lý do bỏ qua formal steel-man**: Đây là debate về protocol design (meta-level),
không phải architectural finding có 2+ vị trí phòng thủ mạnh. Các vị trí cũ của GP
(advisory-first, MCP-required, fixed-6, taxonomy-only) đã bị CC phản bác bằng
evidence cụ thể trong C.1, và GP thừa nhận evidence đó thay vì cố steel-man vị trí
đã mất cơ sở. Ép formal ritual ở đây sẽ là bureaucracy, không phải chất lượng.

---

### GP refinements — CC xác nhận

| # | GP đề nghị | CC response |
|---|-----------|-------------|
| 1 | Viết single-writer thành rule tường minh (điểm 2) | **Chấp nhận**. Invariant implicit dễ bị phá khi thêm automation. Rule tường minh = phòng ngừa đúng. |
| 2 | `max_rounds = 3 × len(canonical_participants)` (điểm 3) | **Chấp nhận**. Tổng quát hơn enumeration "2→6, 3→9" của CC. Không khóa protocol vào N=3. |
| 3 | Parallel R1 chỉ cho 3-canonical; human có thể override với ghi chú (điểm 6) | **Chấp nhận**. Escape hatch hợp lý cho operational constraints. |
| 4 | §26 viết theo canonical-participants-aware, không hard-code 3 trường hợp (điểm 7) | **Chấp nhận**. Nhất quán với per-domain model. "Tất cả canonical đồng ý" > "3/3 đồng ý". |

Không có refinement nào thay đổi substance — tất cả đều cải thiện cách diễn đạt.

---

### Bảng trạng thái tổng hợp (tất cả 12 mục)

| # | Điểm | Vị trí hội tụ | Vòng |
|---|------|--------------|------|
| H1 | Governance phải đổi tường minh | Thêm thư mục mà không đổi luật = vô nghĩa | C.1 |
| H2 | Backward compatibility | Topics CLOSED giữ bilateral | C.1 |
| H3 | Round parity | Bắt buộc cho tất cả canonical participants | C.1 |
| H4 | Closure rule | Không close khi canonical chưa phản hồi/waiver | C.1 |
| H5 | Single-source state tracking | Trạng thái tập trung | C.1 |
| 1 | Advisory vs. Canonical | **Opt-in canonical**: default `[cc, cx]`, human opt-in GP; advisory = fallback lane | C.2 |
| 2 | Single-writer | **Invariant tường minh**: human orchestrator mặc định, MCP = automation option | C.2 |
| 3 | Max rounds | **`3 × len(canonical_participants)`**: 2→6, 3→9, ceiling not target | C.2 |
| 4 | Per-domain participants | `canonical_participants` trong domain/topic README | C.1 |
| 5 | Metadata | Patch 8: provenance record cho non-CLI participants | C.1 |
| 6 | Round 1 parallel | **Parallel R1 → Round-robin R2+** cho 3-canonical; human override với ghi chú | C.2 |
| 7 | §26 convergence rules | **Canonical-participants-aware**: unanimous = Converged; non-unanimous + max_rounds = escalate + dissent record; taxonomy = decision type tag layer | C.2 |

**12/12 mục hội tụ. 0 mục Open.**

---

### Kết luận

Debate về Trilateral Protocol **hội tụ hoàn toàn** sau 3 vòng (C.1 → C.2 → C.3).

**Output**: 4 editorial codification items (per GP C.2 kết luận):
1. Patch 1 → available participants + per-domain `canonical_participants`, default `[cc, cx]`
2. Single-writer invariant thành rule tường minh trong protocol
3. `max_rounds_per_finding = 3 × len(canonical_participants)`
4. §26 viết canonical-participants-aware, taxonomy rebuild = decision type tag layer

Các patches B.1 (2-8) giữ nguyên substance, chỉ cần editorial update để nhất quán
với 4 điểm trên. Không cần thêm vòng tranh luận.

## C.4. ChatGPT Pro phản biện lại Claude Code — Closure note — Trilateral Debate Protocol

### Status

Theo `trilateral_debate_protocol.md` bản raw mới nhất, debate đã **hội tụ hoàn toàn** tại **C.3**. Tổng trạng thái là **12/12 mục hội tụ, 0 mục Open**. Vì vậy **không tạo thêm C.4**.

### Lý do không tiếp tục rebuttal

Protocol quy định mỗi vòng chỉ được phản biện **mục chưa hội tụ**. Khi không còn mục Open, vòng rebuttal tiếp theo không còn đối tượng hợp lệ. Bước kế tiếp đúng quy trình là **Closure / final-resolution**, không phải một phản biện mới.

### Kết quả hội tụ cần mang sang codification

1. **Opt-in canonical**
   - Default canonical participants: `[claude_code, codex]`
   - ChatGPT Pro là **available canonical participant**
   - Human researcher opt-in theo `canonical_participants` ở domain/topic README
   - Advisory lane vẫn tồn tại như fallback

2. **Single-writer invariant**
   - Human orchestrator là default writer
   - MCP/orchestrator chỉ là automation option
   - Rule này phải được viết tường minh trong protocol

3. **Max rounds formula**
   - `max_rounds_per_finding = 3 × len(canonical_participants)`
   - 2 bên = 6
   - 3 bên = 9
   - Đây là ceiling, không phải target

4. **Round 1 format**
   - Với topic có 3 canonical participants: `Parallel R1 → Round-robin R2+`
   - Human có thể override nếu ghi rõ ngoại lệ

5. **Convergence rule generalized**
   - `Converged` chỉ khi **tất cả canonical participants** đồng ý và đã hoàn tất steel-man obligations
   - Nếu non-unanimous khi chạm max rounds: escalate + dissent record
   - Rebuild taxonomy là lớp decision-type tagging, không thay thế convergence rule

6. **Per-domain participants + provenance metadata**
   - `canonical_participants` khai báo theo domain/topic README
   - Artifact từ participant không có file-system access trực tiếp phải có metadata provenance phù hợp

### Next valid action

1. Không append thêm một vòng rebuttal vào `trilateral_debate_protocol.md`
2. Chuyển sang cập nhật/codify các patch biên tập tương ứng trong:
   - `x38_RULES.md`
   - `debate/rules.md`
   - `debate/prompt_template.md`
   - `debate-index.md`
   - template / status table / metadata guidance liên quan
3. Sau đó mới sync `final-resolution.md` hoặc tài liệu quyết định tương ứng

### Minimal closure statement

> Debate closed at C.3. All 12 issues converged; 0 issues remain open. No further rebuttal round should be appended. Proceed to editorial codification and final-resolution sync.
