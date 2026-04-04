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

##### Patch 1: `x38_RULES.md` §5 — Thêm participant

Hiện tại:
```markdown
| Agent | Vai trò | Thế mạnh |
|-------|---------|----------|
| `claude_code` | Architect + opening critic | Đã thiết kế sơ bộ; hiểu btc-spot-dev sâu |
| `codex` | Reviewer + adversarial critic | Fresh perspective; phản biện thiết kế |
```

Thay bằng:
```markdown
| Agent | Vai trò | Thế mạnh |
|-------|---------|----------|
| `claude_code` | Architect + opening critic | Đã thiết kế sơ bộ; hiểu btc-spot-dev sâu |
| `codex` | Reviewer + adversarial critic | Fresh perspective; phản biện thiết kế |
| `chatgpt_pro` | Reviewer + independent critic | Góc nhìn bổ sung; phát hiện blind spots |
```

Lý do: Khai báo chatgpt_pro là canonical participant thay vì external advisor. Vai trò
Reviewer + independent critic phản ánh đúng thế mạnh: model khác, training khác, bias
khác → bổ sung cho cả claude_code lẫn codex.

##### Patch 2: `debate/rules.md` — 5 section cần sửa

**§7 Steel-man mở rộng cho 3 bên:**

Thêm sau §7(c):
```markdown
   (d) Khi có 3 bên tranh luận: trước khi đánh dấu `hội tụ`, agent phải
       steel-man **vị trí mạnh nhất còn lại** bất kể ai giữ vị trí đó.
       Nếu 2 agent còn lại giữ 2 vị trí KHÁC nhau, phải steel-man cả hai.
       Steel-man được gửi tới từng agent giữ vị trí đó để xác nhận.
       Tối đa 2 lần thử per position; nếu sau 2 lần vẫn bị từ chối,
       issue tự động chuyển thành `Judgment call` với ghi chú
       `steel-man impasse (3-way)`.
```

Lý do: Protocol hiện tại chỉ xử lý 1 vị trí đối lập. Với 3 agents, có thể có 2 vị trí
khác nhau cần steel-man. Mỗi agent sở hữu vị trí phải xác nhận steel-man là fair.

**§13 Max rounds:**
```markdown
13. Mặc định `max_rounds_per_topic = 9`, trừ khi topic đó ghi rõ khác.
```

**§14 Timeout to Judgment call:**
```markdown
14. Sau `max_rounds_per_topic`, mọi issue còn `Open` phải chuyển thành
    `Judgment call`, kèm tradeoff rõ ràng, dissent record nếu có, và
    artifact mới nhất từ cả ba bên.
```

**§14b Round parity mở rộng:**
```markdown
14b. Trước khi chuyển sang Judgment call hoặc closure, tất cả 3 bên phải
    có tổng round chênh lệch ≤ 1, HOẶC bất đối xứng phải được ghi nhận
    kèm lý do trong `final-resolution.md`.
    Ngoại lệ: Round 1 parallel (B và C viết cùng round-1 nhưng A chỉ có
    round-1 opening) — đây là bất đối xứng by design, không cần ghi nhận.
```

**Thêm §26 — Convergence 3 bên:**
```markdown
26. Quy tắc convergence cho 3 bên tranh luận:

    (a) `Converged` = 3/3 unanimous + steel-man xác nhận per §7(d).
        Đây là hội tụ thật duy nhất.

    (b) `Majority-dissent` = 2/3 đồng ý, 1 bất đồng. Tự động chuyển
        thành `Judgment call`. Dissent record bắt buộc ghi:
        - Vị trí bất đồng (ai giữ, argument cụ thể)
        - Evidence hỗ trợ dissent
        - Majority rationale: tại sao majority cho rằng dissent không
          đứng vững, kèm evidence pointer
        Agent dissent PHẢI hoàn thành steel-man cho majority position
        trước khi ghi dissent — đảm bảo dissent không phải vì chưa hiểu.

    (c) `3-way split` = 3 vị trí khác nhau, không ai nhượng bộ.
        Sau max rounds → `Judgment call` với 3 vị trí đầy đủ.
        Human researcher chọn hoặc tổng hợp.

    (d) Trong bảng trạng thái, ghi rõ vị trí từng agent (CC/CX/GP)
        để human researcher thấy alignment pattern.
```

##### Patch 3: `debate/prompt_template.md` — Redesign Prompt A/B/C

**Prompt A — Mở phiên** (gửi cho architect, thường là claude_code):

Sửa dòng `Các bên tranh luận`:
```
Các bên tranh luận: Claude Code ↔ Codex ↔ ChatGPT Pro
```

Phần còn lại giữ nguyên — architect vẫn mở đầu như cũ.

**Prompt B1 — Phản biện độc lập Round 1** (gửi cho Reviewer 1):

Thêm mới, chèn giữa Prompt A và Prompt B hiện tại:
```
ROUND 1 — Phản biện độc lập

- Bối cảnh: Chúng ta đang thiết kế kiến trúc cho Alpha-Lab — một framework
  offline để nghiên cứu và phát triển thuật toán trading từ nền trắng.

- Thiết kế tổng quan: `docs/design_brief.md`
- Danh sách các điểm cần tranh luận: `debate/{TOPIC_DIR}/findings-under-review.md`
- Quy tắc tranh luận: `debate/rules.md`
- Opening critique: `debate/{TOPIC_DIR}/{architect_agent}/round-1_opening-critique.md`

Các bên tranh luận: Claude Code ↔ Codex ↔ ChatGPT Pro

⚠️ QUAN TRỌNG: Đây là phản biện ĐỘC LẬP. KHÔNG đọc artifact của reviewer
kia. Chỉ đọc opening critique của architect và findings. Mục đích: tránh
anchoring bias — mỗi reviewer đưa ra góc nhìn riêng trước khi biết reviewer
kia nghĩ gì.

Nhiệm vụ:
1. Đọc context (AGENTS.md, online_vs_offline.md, x38_RULES.md, rules.md).
2. Đọc README.md TRƯỚC (SPLIT guard + dependency gate).
3. Đọc opening critique + findings + evidence.
4. Phản biện từng issue, kèm evidence pointer.
5. Kết thúc bằng bảng trạng thái (3 cột vị trí: CC/CX/GP).

Sau khi bạn nêu ý kiến, tôi sẽ chuyển cho bên tiếp theo phản biện.
```

**Prompt B2 — Phản biện độc lập Round 1** (gửi cho Reviewer 2):

Giống B1, gửi song song. Human orchestrator đảm bảo R2 không thấy artifact R1.

**Prompt B-next — Round-robin (Round 2+)** (thay thế Prompt B hiện tại):

Sửa thành:
```
ROUND N — Phản biện (round-robin)

- Bối cảnh: [giữ nguyên]

Các bên tranh luận: Claude Code ↔ Codex ↔ ChatGPT Pro

- TẤT CẢ round files hiện có trong topic dir (đọc theo thứ tự thời gian).
- Ý kiến mới nhất: `debate/{TOPIC_DIR}/{agent}/round-{N-1}_[message-type].md`

Nhiệm vụ:
1. Đọc TẤT CẢ round files hiện có (cả 3 agents).
2. Phản biện từng issue CÒN OPEN, kèm evidence pointer.
3. Với issue mà 2/3 đã đồng ý: nếu bạn là agent thứ 3, hoặc steel-man và
   chấp nhận (→ Converged 3/3), hoặc ghi dissent record per §26(b).
4. Nhắc lại: steel-man bắt buộc (§7), cấm nhượng bộ mềm (§8).
5. Kết thúc bằng bảng trạng thái cập nhật (3 cột CC/CX/GP).

Sau khi bạn nêu ý kiến, tôi sẽ chuyển cho bên tiếp theo.
```

**Prompt C — Closure**: Sửa Participants:
```
**Participants**: claude_code, codex, chatgpt_pro
```

##### Patch 4: Directory structure — Thêm `chatgpt_pro/`

Cấu trúc hiện tại:
```text
debate/NNN-slug/
  ├── README.md
  ├── findings-under-review.md
  ├── final-resolution.md
  ├── claude_code/round-N_*.md
  └── codex/round-N_*.md
```

Thêm:
```text
debate/NNN-slug/
  ├── README.md
  ├── findings-under-review.md
  ├── final-resolution.md
  ├── claude_code/round-N_*.md
  ├── codex/round-N_*.md
  └── chatgpt_pro/round-N_*.md      ← MỚI
```

Ghi trong `debate/rules.md` §cấu trúc:
```markdown
  NNN-slug/
    README.md
    findings-under-review.md
    input_*.md
    final-resolution.md
    codex/round-N_[message-type].md
    claude_code/round-N_[message-type].md
    chatgpt_pro/round-N_[message-type].md
```

Lưu ý: Thư mục `chatgpt_pro/` chỉ tạo khi topic thực sự bắt đầu debate (không
pre-create cho topics CLOSED trước khi trilateral protocol có hiệu lực).

##### Patch 5: Template D — `final-resolution.md`

Sửa header:
```markdown
**Participants**: claude_code, codex, chatgpt_pro
```

Thêm cột `Dissent` trong decision table:
```markdown
| Issue ID | Finding | Resolution | Type | Round closed | Dissent |
|----------|---------|------------|------|-------------|---------|
| X38-D-01 | ... | Accepted | Converged (3/3) | 5 | — |
| X38-D-02 | ... | Modified | Judgment call (2/3) | 7 | codex: [tóm tắt vị trí] |
| X38-D-03 | ... | Deferred | Judgment call (3-way) | 9 | 3 vị trí — xem round 8-9 |
```

Thêm section `## Dissent records` cho issues có majority-dissent:
```markdown
## Dissent records

### X38-D-02 — [tên issue]

**Majority position** (claude_code, chatgpt_pro): [vị trí]
**Dissent** (codex): [vị trí]
**Dissent evidence**: [evidence pointers]
**Majority rationale**: [tại sao dissent không đứng vững]
**Human decision**: [chọn majority / chọn dissent / tổng hợp / defer]
```

##### Patch 6: Bảng trạng thái — Mở rộng 3 cột vị trí

Hiện tại:
```markdown
| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ |
```

Thay bằng:
```markdown
| Issue ID | Điểm | Phân loại | Trạng thái | CC | CX | GP | Steel-man | Lý do bác bỏ |
|---|---|---|---|---|---|---|---|---|
| X38-D-01 | Campaign model | JC | Open | A | B | A | — | — |
| X38-D-02 | Typed schema | TS | Converged | A | A | A | [steel-man] | [lý do] |
| X38-D-03 | Pipeline scope | JC | JC (2/3) | A | B | A | codex steel-man: ... | ... |
```

Legend:
- **CC** = claude_code, **CX** = codex, **GP** = chatgpt_pro
- Giá trị: tên vị trí ngắn (A/B/C) hoặc `—` nếu chưa phát biểu
- Khi 2 cột giống nhau = majority đang hình thành → agent thứ 3 phải
  steel-man hoặc ghi dissent

##### Patch 7: `debate-index.md` — Governance update

Thêm note ở đầu file:
```markdown
> **Protocol upgrade (YYYY-MM-DD)**: Trilateral debate protocol có hiệu lực.
> 3 canonical participants: claude_code, codex, chatgpt_pro.
> Topics CLOSED trước ngày này vẫn giữ bilateral records (claude_code + codex).
> Topics OPEN từ ngày này áp dụng trilateral rules (§26, max_rounds=9).
```

---

#### Orchestration thực tế (human researcher workflow)

##### Bước chạy 1 topic

```
Bước 1 — Opening:
  Human → Claude Code CLI: paste Prompt A + {TOPIC_DIR}
  Claude Code viết: claude_code/round-1_opening-critique.md
  Human lưu artifact vào repo

Bước 2 — Parallel independent critique:
  Human → Codex: paste Prompt B1 + opening critique (KHÔNG kèm ChatGPT artifact)
  Human → ChatGPT Pro: paste Prompt B2 + opening critique (KHÔNG kèm Codex artifact)
  (2 requests SONG SONG — không chờ nhau)
  Human lưu: codex/round-1_rebuttal.md, chatgpt_pro/round-1_rebuttal.md

Bước 3 — Round-robin (Round 2+):
  Thứ tự cố định: claude_code → codex → chatgpt_pro → claude_code → ...
  Mỗi lượt: Human paste Prompt B-next + TẤT CẢ round files hiện có
  Agent đọc tất cả, viết rebuttal/response
  Human lưu artifact

Bước 4 — Convergence check sau mỗi round:
  Nếu TẤT CẢ issues = Converged (3/3) hoặc Judgment call → chuyển Bước 5
  Nếu còn Open → tiếp round-robin
  Nếu đạt round 9 → mọi Open → Judgment call

Bước 5 — Closure:
  Human → bất kỳ agent: paste Prompt C
  Agent tạo/sync final-resolution.md
  Human review, quyết định Judgment calls, cập nhật debate-index.md
```

##### Tips cho human orchestrator

1. **Copy-paste discipline**: Khi paste vào ChatGPT Pro / Codex, đảm bảo context
   đầy đủ (findings + rules + round history). Các agent này không có file system
   access — mọi thứ phải nằm trong prompt.

2. **Round 1 isolation**: Đây là điểm quan trọng nhất. Nếu reviewer thấy artifact
   của reviewer kia, giá trị independent perspective bị mất. Human phải kiểm soát
   chặt bước này.

3. **Agent rotation cho architect role**: Mặc định claude_code mở đầu (vì hiểu
   codebase sâu nhất). Nhưng cho topics không cần codebase knowledge (ví dụ:
   governance, protocol flow), có thể rotate architect role sang codex hoặc
   chatgpt_pro để tránh framing bias.

4. **Context window management**: ChatGPT Pro và Codex có context window khác nhau.
   Nếu round history quá dài, human nên cung cấp condensed summary thay vì full
   history — nhưng phải ghi chú `[condensed by human, full history in repo]`.

5. **Backward compatibility**: Topics đã CLOSED trước trilateral protocol không cần
   re-debate. Chỉ topics OPEN mới áp dụng 3-agent protocol.

---

#### Tóm tắt thay đổi

| # | File | Thay đổi | Mức độ |
|---|------|----------|--------|
| 1 | `x38_RULES.md` §5 | Thêm `chatgpt_pro` participant | Nhỏ |
| 2 | `debate/rules.md` §7,§13,§14,§14b + §26 mới | Steel-man 3-way, max 9, convergence rules | Lớn |
| 3 | `debate/prompt_template.md` | Thêm Prompt B1/B2, sửa B→B-next, sửa Participants | Lớn |
| 4 | Directory structure | Thêm `chatgpt_pro/` per topic | Nhỏ |
| 5 | Template D (`final-resolution.md`) | Thêm Dissent cột + section | Trung bình |
| 6 | Status table format | Thêm 3 cột CC/CX/GP | Trung bình |
| 7 | `debate-index.md` | Governance upgrade note | Nhỏ |

**Tổng**: 2 file thay đổi lớn (rules.md, prompt_template.md), 5 file thay đổi nhỏ-trung bình.
Không breaking change cho topics đã CLOSED.

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

**Đề xuất giữ nguyên**: 9 rounds (3 per agent, 3 full trilateral cycles). Nếu hội tụ sớm, đóng sớm — 9 chỉ là ceiling, không phải target.

#### 4. `canonical_participants` per-domain vs. global §5

**Vị trí B.2**: Khai báo trong domain README: `canonical_participants: [claude_code, codex, chatgpt_pro]`. Dynamic per domain.

**Tôi chấp nhận điểm này của B.2** — nó linh hoạt hơn Patch 1 của B.1 (global §5).

Lý do: Có domains nơi chỉ 2 agent phù hợp (ví dụ: domain đòi hỏi deep codebase knowledge mà ChatGPT Pro không có access). Per-domain declaration cho phép human researcher quyết định từng trường hợp.

**Sửa đổi B.1**: Thay Patch 1 (global §5 thêm row) bằng:
- §5 liệt kê 3 agents là **available** participants
- Mỗi domain README khai báo `canonical_participants` cho domain đó
- Default: `[claude_code, codex, chatgpt_pro]` trừ khi domain ghi khác

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

---

### Bảng trạng thái

| # | Điểm | CC | GP | Trạng thái |
|---|------|----|----|-----------|
| 1 | Advisory vs. Canonical ngay | Canonical ngay | Advisory trước | **Open** |
| 2 | "One writer, three thinkers" | Đã ngầm định trong B.1, không cần MCP riêng | Cần orchestrator/MCP | **Open** |
| 3 | Max rounds: 9 vs 6 | 9 | 6 | **Open** |
| 4 | `canonical_participants` per-domain | **Chấp nhận** (sửa B.1 Patch 1) | Per-domain README | **Hội tụ** (CC chấp nhận vị trí GP) |
| 5 | Metadata cho artifacts | **Chấp nhận** + mở rộng (Patch 8) | Metadata schema | **Hội tụ** (CC chấp nhận + bổ sung) |
| 6 | Round 1 parallel format | Parallel-then-converge | Chưa phát biểu | **Open** (chờ GP) |
| 7 | Convergence rules §26 | §26 bổ sung rebuild taxonomy | Dùng rebuild taxonomy đơn thuần | **Open** |

**Hội tụ**: 5 (H1-H5) + 2 (điểm 4, 5) = **7 mục**
**Open**: 5 mục (điểm 1, 2, 3, 6, 7 — trong đó điểm 6 chờ GP phát biểu)

## C.2. Phản biện của ChatGPT Pro cho Claude Code
