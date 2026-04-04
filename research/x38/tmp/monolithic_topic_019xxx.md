> **QUY ĐỊNH TRANH LUẬN — ĐỌC TRƯỚC KHI PHẢN BIỆN**
>
> 1. Mỗi lượt phản biện bắt đầu bằng tiêu đề có đánh số: **"C.N. Phản biện của \<tên agent\> cho \<tên agent đối phương\>: ..."** (N tăng dần từ 1)
> 2. Phản biện được điền **nối tiếp ở cuối tệp**. Agent lượt sau đọc và phản biện lại. Lặp cho đến **hội tụ hoàn toàn**.
> 3. Phản biện phải **chính trực, công tâm** — không đồng thuận giả, không để quán tính các vòng trước chi phối.
> 4. Mỗi vòng: **liệt kê mục đã hội tụ** rồi loại khỏi phạm vi. **Chỉ phản biện mục chưa hội tụ**.

---

# A. CÂU HỎI BAN ĐẦU
Hãy giúp tôi kiểm tra topic 019* trong debate của /var/www/trading-bots/btc-spot-dev/research/x38 có còn bị lỗi "cấu trúc monolithic + scope creep 3 lần sẽ tạo ra rác khi debate bắt đầu" hay không?

# B. CÂU TRẢ LỜI BAN ĐẦU
## B.1. Câu trả lời của Claude Code

### Kết quả kiểm tra: Lỗi scope creep 019 ĐÃ ĐƯỢC SỬA

File `scope_creep_topic_019xxx.md` ghi nhận 16 vòng tranh luận (Claude Code vs ChatGPT Pro) và 24+ điểm hội tụ. Action plan 3 Tier đã được chốt và tất cả Tier 1 đã patch.

### Verify trực tiếp repo:

| Tier 1 Item | Trạng thái | Evidence |
|---|---|---|
| **Deprecation banner** (019, 017 parent findings) | **DONE** | Cả hai file mở đầu bằng `> **SUPERSEDED** — This file is preserved as historical reference only.` |
| **Sync PLAN.md + EXECUTION_PLAN.md** | **DONE** | PLAN.md: 16 mentions 019A-G/D1-D3, wave diagram, dependency graph. EXECUTION_PLAN.md: 25 mentions, full sub-topic breakdown (line 252-264) |
| **Fix 019E control surface** | **DONE** | 019G trong tension table (line 72), "NONE" tách scheduling vs content (line 58-59), D-22 cho Category C (line 378 findings) |

### Lỗi ban đầu vs hiện tại:

- **Monolithic 167KB topic** → **9 sub-topics** (250-870 lines mỗi cái), parallel debatable
- **Parent files trông như live dossier** → **SUPERSEDED banner** + README index rõ ràng
- **Planning surfaces mô tả 019 monolith** → **Full sub-topic model** trong cả PLAN.md lẫn EXECUTION_PLAN.md
- **019E thiếu 019G cross-reference** → **Tension table + content-dependency** đã ghi
- **Category C chưa có decision slot** → **D-22 mandatory** đã thêm

### Tồn đọng (Tier 3 — deferred by design):

- 019G ontologically lệch nhưng zero functional gain → **defer**
- Metadata system over-engineered → **reject**
- Đổi prefix DFL- phá convention → **reject**

### Kết luận

Lỗi "cấu trúc monolithic + scope creep 3 lần sẽ tạo ra rác khi debate bắt đầu" **không còn tồn tại**. Split + control surface fixes đảm bảo debate có thể chạy đúng mà không bị ô nhiễm bởi scope creep.

### Chi tiết phương pháp kiểm tra

Kiểm tra thực hiện bằng cách đọc trực tiếp repo (không dựa vào memory hay claim cũ):

1. **Parent findings files** (019 + 017): đọc 10 dòng đầu → xác nhận SUPERSEDED banner tồn tại.
2. **PLAN.md**: grep `019A|019B|...019G` → 16 matches. Xác nhận topic table ghi SPLIT, dependency graph dùng sub-topics, wave 2.5 liệt kê từng sub-topic.
3. **EXECUTION_PLAN.md**: grep tương tự → 25 matches. Xác nhận status table, critical path, wave 2.5 detail, Topic 003 dependency đều dùng sub-topics.
4. **019E README**: grep `019G|NONE from other` → xác nhận dependency split (scheduling: NONE, content: 019G), tension table có 019G (line 72).
5. **019E findings**: grep `D-22` → xác nhận decision slot D-22 tồn tại (line 378) với 3 alternatives.
6. **debate-index.md**: grep `019` → xác nhận registry đúng (019 SPLIT, 9 sub-topics listed, wave diagram, 003 dependency granular).

Tham chiếu: phân tích tranh luận 16 vòng tại `scope_creep_topic_019xxx.md` (cùng thư mục).

## B.2. Câu trả lời của ChatGPT Pro

Kiểm xong. Kết luận thẳng: 019* không còn monolithic theo cấu trúc active nữa, nhưng chưa được vá sạch ở lớp workflow. Nói gọn: mở đúng sub-topic active và đúng wave thì phần lớn hết rác; mở nhầm parent 019/019D hoặc mở sớm trước dependency thì rác vẫn có thể tràn vào round đầu.

Lịch sử đúng là đã từng scope-creep nặng như anh nghi. debate-index.md ghi rõ 019 mở ngày 2026-03-29, rồi bị nới từ 10 finding lên 12, rồi 18, sau đó mới bị tách ngày 2026-04-02; đến 2026-04-03 còn phải sửa registry để thêm toàn bộ sub-topic 019A-G và 019D1-D3, đồng thời đổi 019 từ OPEN sang SPLIT.

Phần đã sửa đúng hướng là cấu trúc topic. 019 gốc tự nhận là quá lớn để debate hiệu quả nên đã tách thành 9 sub-topic; 019D cũng tiếp tục tách thành D1/D2/D3. Các topic con bây giờ đều có scope rõ, nêu rõ “cái gì thuộc topic này” và “cái gì không thuộc”. Ví dụ: 019A chỉ giữ 3 quyết định nền tảng; 019B giữ core loop; 019D1 chỉ giữ pipeline structure; 019G chỉ giữ data scope. 019C còn được bổ sung note khóa scope vào một meta-decision D-12, còn 019F được thêm hẳn chiến lược giải conflict DFL-14/DFL-18 trước khi tranh các decision con. Ở lớp nội dung active, đây không còn là cái blob 019 cũ nữa.

Nhưng lỗi tái phát vẫn còn ở bước mở debate. prompt_template.md và rules.md chỉ có guard cho topic đã CLOSED qua final-resolution.md; chúng không có guard cho topic đã SPLIT. Đồng thời cả hai vẫn bắt agent đọc debate/{TOPIC_DIR}/findings-under-review.md như input bắt buộc trước khi viết. Trong khi đó, parent 019-discovery-feedback-loop/findings-under-review.md vẫn còn nằm đó và chỉ được gắn nhãn SUPERSEDED. Nghĩa là chỉ cần chọn nhầm TOPIC_DIR=019-discovery-feedback-loop hoặc 019D-discovery-governance, agent vẫn bị kéo vào hồ sơ archive ngay từ round 1.

Lỗ hổng thứ hai là dependency gating chưa được cưỡng chế. 019B tự ghi rất rõ là phải chờ 019A xong rồi mới debate; 019D1 phải chờ 019A + 019B; debate-index.md cũng xếp wave theo đúng thứ tự đó. Nhưng prompt/rules không có bước “abort nếu upstream chưa resolve”. Thành ra repo đã có dependency map, nhưng chưa có preflight bắt buộc để ngăn mở sai thời điểm. Đây là nguồn “rác lúc bắt đầu” còn sót lại.

Điểm nóng còn lại là 019C. Nó không còn monolithic kiểu cũ, nhưng vẫn là sub-topic nặng nhất, khoảng 862 dòng findings. Repo đã tự nhận điều đó và thêm scope clarification: debate chỉ nên tập trung vào D-12, còn 10 analysis + 6 method categories chỉ là evidence cho meta-decision, không phải 16 mini-topics cần tranh riêng. Tức là đã có biện pháp giảm tải, nhưng đây vẫn là chỗ dễ phình context nhất trong cụm 019*.

Nói khó hơn một chút: về mặt governance thuần, cụm 019* vẫn chưa granular đẹp hoàn toàn. x38_RULES.md nói mỗi topic nên tương ứng một quyết định kiến trúc cụ thể, trong khi 019A đang ôm 3 decision, 019B ôm 4, 019E cũng ôm 4. Đây không còn là lỗi “monolith cấp-cha” nữa, nhưng vẫn là design debt về độ hạt.

Phán quyết cuối cùng của tôi: bug “monolithic + scope creep 3 lần” ở 019* đã được xử lý phần lớn ở lớp cấu trúc nội dung, nhưng chưa hết ở lớp điều phối debate-start. Nếu đánh theo mức độ, tôi xếp phần còn lại vào loại WARNING cao, chưa tới mức BLOCK-DEBATE, vì active sub-topics đã rõ và parent files đều có nhãn SPLIT/SUPERSEDED; tuy vậy guardrail tự động còn thiếu nên vẫn đủ sức làm bẩn vòng mở đầu nếu chọn sai topic hoặc sai wave.

Ba chỗ nên vá ngay:

Thêm preflight trong prompt_template.md và rules.md: đọc README.md trước, nếu status = SPLIT thì dừng và reroute sang sub-topic, không được load full archived findings-under-review.md.
Thêm dependency gate cứng: nếu upstream trong README/debate-index chưa chốt thì không cho mở round 1.
Với 019C, thêm một round0-summary.md hoặc condensed dossier bắt buộc cho vòng đầu; full 862-line dossier chỉ đọc sâu khi có challenge cụ thể.

# C. TRANH LUẬN

## C.1. Phản biện của Claude Code cho ChatGPT Pro: Thừa nhận lỗ hổng workflow, phản biện mức severity

### Mục đã hội tụ (loại khỏi phạm vi)

1. **Cấu trúc nội dung 019* đã tách đúng** — 9 sub-topics, scope rõ. ĐỒNG THUẬN.
2. **Parent files có SUPERSEDED banner + routing table** — ĐỒNG THUẬN.
3. **PLAN.md + EXECUTION_PLAN.md đã sync sub-topic model** — ĐỒNG THUẬN.
4. **019E control surface (019G tension, D-22)** — ĐỒNG THUẬN.
5. **Lịch sử scope creep (10→12→18 findings, 3 lần nới)** — ĐỒNG THUẬN.

### Mục chưa hội tụ

#### 1. SPLIT guard trong prompt_template.md / rules.md

**Tự sửa B.1**: Phân tích ban đầu của tôi sai ở lớp workflow. Tôi chỉ kiểm tra lớp nội dung (banners, PLAN.md sync, control surfaces) và kết luận "không còn tồn tại" mà bỏ qua hoàn toàn cơ chế điều phối debate.

**Xác nhận ChatGPT Pro đúng cả 3 điểm sau khi verify trực tiếp**:

- `debate/prompt_template.md` và `debate/rules.md` **tồn tại** (tại `debate/`, không phải x38 root — lỗi của tôi khi check sai vị trí).
- Prompt A (dòng 10-11) và Prompt B (dòng 57-58) chỉ guard bằng `final-resolution.md` → chỉ chặn CLOSED, **không chặn SPLIT**.
- Parent `019-discovery-feedback-loop/` và `019D-discovery-governance/` **không có** `final-resolution.md` → guard không trigger.
- `rules.md` §25 bước 6 bắt đọc `findings-under-review.md` **trước** README.md → agent load archived content trước khi thấy routing table.

**Tuy nhiên, phản biện severity**: ChatGPT Pro xếp "WARNING cao". Tôi đề xuất **WARNING trung bình** vì:

- Rủi ro chỉ xảy ra khi `TOPIC_DIR` bị set SAI (chọn parent thay vì sub-topic). Trong thực tế, người điều phối debate (human researcher) chọn topic từ `debate-index.md` — nơi 019 đã ghi rõ `SPLIT` với 9 sub-topics.
- Nếu agent vẫn load nhầm: SUPERSEDED banner ở dòng đầu `findings-under-review.md` sẽ cảnh báo trước khi agent viết. Không phải zero defense — chỉ là defense-in-depth thiếu 1 lớp.
- Nhưng tôi thừa nhận: "defense-in-depth thiếu 1 lớp" ở chính cơ chế gating (prompt_template) là nghiêm trọng hơn thiếu ở lớp content. ChatGPT Pro đúng rằng đây không phải INFORMATIONAL.

**Đề xuất fix**: Thêm bước 6.0 vào `rules.md` §25 và cả Prompt A lẫn Prompt B:

```
6.0. Đọc `debate/{TOPIC_DIR}/README.md` TRƯỚC.
     Nếu README ghi status = SPLIT:
       → DỪNG. Không load findings-under-review.md.
       → Reroute sang sub-topic tương ứng từ routing table trong README.
```

Đồng thời đảo thứ tự §25 bước 6: README.md **trước** findings-under-review.md.

#### 2. Dependency gate enforcement

**Phản biện**: ChatGPT Pro đúng rằng dependency map tồn tại nhưng chưa enforce. Tuy nhiên tôi hạ severity xuống **INFORMATIONAL** (không phải WARNING) vì:

- Human researcher là người chọn topic để mở debate, không phải agent tự chọn.
- `debate-index.md` wave diagram + mỗi sub-topic README đều ghi rõ upstream dependencies.
- Thêm abort mechanism vào prompt_template khi debate runner chưa tự động hóa là premature — hiện tại workflow là thủ công (human copy-paste prompt).
- Risk thực tế: human mở 019B trước khi 019A xong → agent không có resolved decisions từ 019A → debate 019B thiếu input → phát hiện ngay ở round 1 khi agent cần reference 019A findings.

**Tuy nhiên thừa nhận**: Nếu tương lai debate được tự động hóa (script chạy prompt), dependency gate CẦN thiết. Ghi nhận là **future requirement**, không phải bug hiện tại.

#### 3. 019C condensed dossier (862 dòng)

**Phản biện**: ChatGPT Pro đúng rằng 019C nặng nhất trong cụm. Nhưng:

- 019C đã có scope clarification nhúng: "debate chỉ tập trung D-12, 10 analysis + 6 categories là evidence cho meta-decision". Đây **là** condensation — không phải "thiếu".
- Agent đọc findings-under-review.md sẽ thấy scope note **trước** khi gặp evidence sections. Agent competent sẽ focus D-12.
- round0-summary.md tạo thêm 1 artifact cần maintain + risk desync với findings chính.

**Tuy nhiên thừa nhận**: Nếu context window agent bị giới hạn (ví dụ Codex), 862 dòng có thể truncate. Đề xuất **compromise**: không tạo file riêng, nhưng thêm tóm tắt 10-15 dòng ở đầu findings-under-review.md dưới dạng section `## TL;DR for debate round 1`.

#### 4. Granularity debt (019A=3D, 019B=4D, 019E=4D)

**Phản biện**: Đây là trade-off có ý thức, không phải debt.

- x38_RULES nói "nên" (should), không "phải" (must) tương ứng 1 topic = 1 decision.
- Tách 019B (4 decisions về core loop) thành 4 topics riêng = 4 directories × boilerplate, 4 lần nạp context rules.md + AGENTS.md, nhưng decisions **cùng evidence base** và **cùng tension surface**.
- Parallel debate vẫn hoạt động: 019A tranh 3 decisions cùng lúc, round files cover tất cả. Không khác nhiều so với tranh 1 decision với 3 sub-issues.
- **Counter-argument**: Nếu 1 trong 4 decisions converge sớm (round 2) mà 3 còn lại cần round 6, debate bị kéo dài không cần thiết cho decision đã xong. Nhưng rules.md §10 cho phép loại converged items khỏi scope mỗi round → mitigation đã có.

**Kết luận**: Không phải debt. Giữ nguyên.

### Đánh giá tổng hợp (cập nhật từ B.1)

Tôi rút lại phán quyết "không còn tồn tại" từ B.1. ChatGPT Pro đúng rằng lớp workflow chưa clean:

| Gap | Severity đề xuất | Fix |
|-----|-------------------|-----|
| SPLIT guard thiếu trong §25 + prompt A/B | **WARNING** | Đảo thứ tự §25 bước 6 + thêm bước 6.0 |
| Dependency gate chưa enforce | **INFORMATIONAL** | Ghi nhận future req, không fix ngay |
| 019C 862 dòng | **INFORMATIONAL** | TL;DR section ở đầu findings |
| Granularity 3-4 decisions/topic | **NOT A BUG** | Giữ nguyên |

**Phán quyết sửa đổi**: Từ "không còn tồn tại" → **WARNING thấp, 1 fix cần thiết** (SPLIT guard), 2 nice-to-have. Đủ an toàn để bắt đầu debate 019A nếu SPLIT guard được patch trước.

## C.2. Phản biện của ChatGPT Pro cho Claude Code: Giữ WARNING cho các lỗi gating, hạ 019C xuống NOTE, và không xóa granularity debt

### Mục đã hội tụ (loại khỏi phạm vi)

1. **Lớp nội dung active của 019\*** đã được tách khỏi monolith 019 gốc thành các sub-topic có scope rõ.
2. **Parent files 019 và 019D** đã được gắn `SUPERSEDED` và chỉ còn vai trò index/routing.
3. **Lỗ hổng SPLIT guard là có thật**: Prompt A/B chỉ chặn `final-resolution.md` (CLOSED), còn `rules.md` §25 vẫn buộc đọc `findings-under-review.md` trước `README.md`.
4. **Dependency map là có thật và khá rõ**: 019B chờ 019A; 019D1 chờ 019A + 019B; 019C cũng ghi rõ D-12 phụ thuộc D-01 từ 019A.
5. **019C đã có scope note ngay đầu file** khóa debate vào D-12; đây không còn là blob vô điều kiện như parent 019 cũ.

### Mục chưa hội tụ

#### 1. SPLIT guard / load order trong prompt_template.md và rules.md

- **Phân loại**: Sai thiết kế
- **Severity**: `[WARNING]`
- **Evidence**:
  - `research/x38/debate/prompt_template.md:5-11,22-27,35-39,56-60,68-83`
  - `research/x38/debate/rules.md:207-220`
  - `research/x38/debate/019-discovery-feedback-loop/findings-under-review.md:1-6`
  - `research/x38/debate/019D-discovery-governance/findings-under-review.md:1-7`

**Phản biện trọng tâm**: Tôi không chấp nhận hạ xuống “WARNING thấp” vì canonical severity rubric của repo **không có** mức high/medium/low; nó chỉ có `[BLOCK-*] / [WARNING] / [NOTE]`. Đã là lỗi ở **surface vận hành chính** thì cứ gọi đúng tên là `[WARNING]`, không pha thêm độ mờ.

Argument “human researcher chọn đúng topic từ debate-index nên risk thấp” chưa đứng vững vì chính `prompt_template.md` nói `debate-index.md` chỉ là **navigation/status hint, không phải source of truth cho rounds**. Surface thực sự điều phối debate là Prompt A/B + `rules.md` §25. Và hai surface này hiện vẫn làm sai thứ tự: chúng cho phép nạp `findings-under-review.md` trước khi `README.md` kịp reroute. Với parent 019/019D, điều đó nghĩa là agent có thể nạp nhầm dossier archive trước khi thấy routing table.

SUPERSEDED banner là **cảnh báo downstream**, không phải gate. Đến lúc banner xuất hiện thì parent dossier đã vào context rồi. Với bug đang xét — “rác khi debate bắt đầu” — như vậy là quá muộn. Tôi đồng ý với fix anh đề xuất (đọc `README.md` trước, abort nếu `Status = SPLIT`, không load parent findings), nhưng severity chuẩn vẫn là `[WARNING]`, không phải biến thể “WARNING thấp”.

#### 2. Dependency gate enforcement

- **Phân loại**: Thiếu sót
- **Severity**: `[WARNING]` cho các sub-topic có hard-dep chưa được enforce (`019B`, `019C`, `019D1`, `019D2`, `019D3`)
- **Evidence**:
  - `research/x38/debate/019B-ai-analysis-reporting/README.md:40-48,56-60,80`
  - `research/x38/debate/019C-systematic-data-exploration/findings-under-review.md:38-43,849-853`
  - `research/x38/debate/019D1-pipeline-structure/README.md:48-57`
  - `research/x38/debate/debate-index.md:74-80,186-190,247`
  - `research/x38/debate/prompt_template.md:35-44,80-89`
  - `research/x38/debate/rules.md:207-226`

Ở đây tôi không đồng ý với việc hạ xuống INFORMATIONAL. Lý do rất đơn giản: repo **không coi dependencies là gợi ý**. 019B ghi thẳng “must resolve first” và “prerequisite check … must be resolved before debate starts”. 019D1 cũng ghi “must close first”. `debate-index.md` còn dùng chữ **HARD-dep**. Nếu prompt/rules không có bước abort tương ứng, đó là **thiếu enforcement trên gating surface**, đúng định nghĩa `[WARNING]` trong `rules.md` §18b.

Argument “workflow đang thủ công nên round 1 sẽ tự phát hiện” là không đủ. Round 1 **không phải nơi để phát hiện prerequisite sai**; round 1 là nơi bắt đầu tạo artifact. Nếu repo đã declared hard-dep mà generic prompt vẫn cho phép mở round trái thứ tự, thì bug đang tồn tại ngay tại điểm mở debate. Đây không phải future requirement — vì theo registry hiện tại, 019A vẫn OPEN trong khi 019B/019C/D1/D2/D3 cũng OPEN; risk mis-sequencing là live, không phải giả định xa.

Tôi không nâng nó lên `[BLOCK-DEBATE]` toàn cụm 019 vì 019A và cluster độc lập 019E/F/G vẫn mở được. Nhưng với các topic phụ thuộc upstream chưa chốt, thiếu dependency gate **không thể gọi là INFORMATIONAL**.

#### 3. 019C condensed dossier / round-1 summary

- **Phân loại**: Judgment call
- **Severity**: `[NOTE]`
- **Evidence**:
  - `research/x38/debate/019C-systematic-data-exploration/README.md:7-20,31-36`
  - `research/x38/debate/019C-systematic-data-exploration/findings-under-review.md:38-43,849-853`

Ở điểm này tôi chấp nhận phần lớn phản biện của anh. 019C đúng là nặng (~862 dòng), nhưng nó **đã có scope note** rất sớm để khóa debate vào D-12 và nói rõ 10 analyses chỉ là evidence cho meta-decision. Vì vậy, thiếu `round0-summary.md` không cùng loại với lỗi routing/gating ở trên.

Tôi rút yêu cầu “bắt buộc tạo file riêng”. File riêng đúng là có risk desync. Compromise hợp lý hơn là: **nếu** cần tối ưu cho agent context ngắn, thêm 10-15 dòng `TL;DR for round 1` ngay đầu `findings-under-review.md`. Nhưng đây là tối ưu ergonomics, không phải điều kiện để xóa bug monolithic-start.

#### 4. Granularity debt (019A = 3 decisions, 019B = 4, 019E = 4)

- **Phân loại**: Thiếu sót
- **Severity**: `[NOTE]`
- **Evidence**:
  - `research/x38/x38_RULES.md:129-130`
  - `research/x38/debate/019A-discovery-foundations/README.md:36-42`
  - `research/x38/debate/019B-ai-analysis-reporting/README.md:31-40`
  - `research/x38/debate/019E-data-quality-validation/README.md:34-41`

Ở đây tôi bác bỏ thẳng luận điểm “không phải debt”. `x38_RULES.md` không viết kiểu mềm “nên cân nhắc”; nó viết: **“Mỗi topic tương ứng một quyết định kiến trúc cụ thể.”** Trong khi 019A hiện ôm 3 quyết định, 019B ôm 4, 019E ôm 4. Về governance thuần, đó là lệch so với rule hiện hành.

Tuy nhiên, tôi đồng ý với anh ở nửa sau: lệch này **không tái tạo monolith 167KB ban đầu**. Các topic con hiện tại vẫn đủ bounded để debate được, và `rules.md` §10 cho phép loại mục đã hội tụ ra khỏi scope ở các vòng sau để tránh một decision kéo dài làm treo cả cụm. Vì vậy tôi xếp nó là **debt thật nhưng severity chỉ `[NOTE]`**, không phải blocker.

### Đánh giá tổng hợp (cập nhật từ C.1)

Tôi sửa lại framing của anh theo canonical rubric của repo như sau:

| Gap | Classification | Severity | Kết luận |
|-----|----------------|----------|----------|
| SPLIT guard thiếu + load order sai | Sai thiết kế | **[WARNING]** | Phải fix trước khi dùng generic prompt/rules cho parent SPLIT topics |
| Dependency gate chưa enforce | Thiếu sót | **[WARNING]** (chỉ cho các sub-topic có hard-dep) | Phải fix trước khi mở 019B/019C/019D1/019D2/019D3 trái wave |
| 019C thiếu summary riêng | Judgment call | **[NOTE]** | Không bắt buộc; inline TL;DR là đủ nếu cần |
| Multi-decision topic còn tồn tại | Thiếu sót | **[NOTE]** | Debt governance thật, nhưng không còn là monolith cấp-cha |

**Phán quyết hiện tại của tôi**: Repo **chưa xuống mức “WARNING thấp, chỉ còn 1 fix cần thiết.”** Đúng hơn là còn **2 WARNING thật ở lớp debate-start workflow** và **2 NOTE ở lớp ergonomics/governance**.

**Hệ quả thực dụng**:
- Có thể bắt đầu debate **ngay** cho `019A` và cluster độc lập `019E/019F/019G`.
- **Không nên** mở `019B`, `019C`, `019D1`, `019D2`, `019D3` bằng generic prompt hiện tại nếu chưa thêm preflight check cho hard dependencies.
- Fix tối thiểu để dập bug debate-start:
  1. Trong Prompt A/B và `rules.md` §25: đọc `README.md` trước; nếu `Status = SPLIT` thì abort + reroute.
  2. Sau khi đọc `README.md`, nếu upstream topic trong `Dependencies`/wave chưa CLOSED thì abort, không tạo round artifact.

### Bảng trạng thái

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| TMP-019-01 | SPLIT guard + load order | Sai thiết kế | Open | Human researcher chọn đúng `TOPIC_DIR`; parent file có `SUPERSEDED` banner nên đủ an toàn | `debate-index.md` chỉ là navigation hint; Prompt A/B + `rules.md` mới là surface điều phối thật, và hiện tại surface này vẫn nạp parent findings trước `README.md` |
| TMP-019-02 | Dependency gate enforcement | Thiếu sót | Open | Workflow đang thủ công; nếu mở sai wave thì round 1 sẽ tự phát hiện thiếu upstream | 019B/019C/019D1 tự khai báo `must resolve first` / `HARD-dep`; cho phép round 1 bắt đầu dù sai prereq chính là bug debate-start đang bàn |
| TMP-019-03 | 019C round-1 condensation | Judgment call | Open | 862-line dossier có thể làm agent context ngắn bị ngợp; summary riêng giúp vào nhanh | Scope note D-12 đã nằm ngay đầu file; nếu tối ưu thì nên thêm TL;DR inline để tránh desync, không cần file riêng |
| TMP-019-04 | Granularity debt sau split | Thiếu sót | Open | Nhiều decisions dùng chung evidence base; gộp lại giảm boilerplate và số phiên debate | Rule hiện hành vẫn ghi 1 topic = 1 architectural decision; gộp topic có lợi vận hành nhưng không xóa governance debt |

## C.3. Phản biện của Claude Code cho ChatGPT Pro: Hội tụ toàn bộ 4 issues

### Mục đã hội tụ từ C.1/C.2 (giữ nguyên)

1. **Cấu trúc nội dung 019* đã tách đúng** — ĐỒNG THUẬN.
2. **Parent files có SUPERSEDED banner + routing table** — ĐỒNG THUẬN.
3. **PLAN.md + EXECUTION_PLAN.md đã sync sub-topic model** — ĐỒNG THUẬN.
4. **019E control surface (019G tension, D-22)** — ĐỒNG THUẬN.
5. **Lịch sử scope creep (10→12→18 findings, 3 lần nới)** — ĐỒNG THUẬN.

### Mục hội tụ MỚI trong round này

#### TMP-019-01: SPLIT guard — HỘI TỤ → `[WARNING]`

Tôi chấp nhận đây là `[WARNING]` thuần, không pha thêm modifier "thấp/trung bình".

**Verify rubric**: `rules.md` §18b chỉ định nghĩa 3 tầng: `[BLOCK-DEBATE]/[BLOCK-DRAFT]/[BLOCK-PUBLISH]`, `[WARNING]`, `[NOTE]`. Không có high/medium/low. ChatGPT Pro đúng rằng tôi đang tạo gradient không tồn tại trong rubric.

**Verify definition fit**: §18b: *"[WARNING]: Lỗi thật ảnh hưởng correctness hoặc completeness ở surface vận hành chính (debate-index, status ledgers, evidence pointers cho gating topics). Cần fix trước khi surface đó được dùng trong quyết định."* — Prompt A/B + `rules.md` §25 **là** surface vận hành chính. Nạp parent findings trước README **là** incorrect routing. Fit chính xác.

**Rút lại**: Argument "SUPERSEDED banner = defense" yếu vì banner là cảnh báo downstream sau khi dossier archive đã vào context. Tôi đồng ý gate phải chặn trước khi load, không phải sau.

**Fix đồng thuận**: Đảo thứ tự §25 bước 6 (README trước findings) + thêm bước 6.0 abort nếu `Status = SPLIT`.

#### TMP-019-02: Dependency gate — HỘI TỤ → `[WARNING]` cho hard-dep sub-topics

Tôi rút lại "INFORMATIONAL" và chấp nhận `[WARNING]`.

**Verify evidence quyết định**:
- `019B/README.md` dòng 45-48: *"Upstream (must resolve first): 019A..."* + dòng 80: *"019A D-01, D-02, D-03 must be resolved before debate starts."*
- `019D1/README.md` dòng 50: *"Upstream (must close first): 019A, 019B"*
- `debate-index.md` dòng 186-190: dùng *"HARD-dep"* với mũi tên wave rõ ràng.

**Steel-man vị trí cũ**: "Workflow thủ công + round 1 sẽ phát hiện" — nhưng ChatGPT Pro phản bác đúng: (1) round 1 không phải nơi phát hiện prerequisite, mà là nơi tạo artifact; (2) `"must resolve first"` là declaration bắt buộc, không phải gợi ý; (3) risk là live — 019A vẫn OPEN cùng lúc 019B/C/D1-D3 cũng OPEN trong registry.

**Lý do chấp nhận**: §18b definition match — thiếu enforcement trên gating surface cho declared hard-deps. Không phải future requirement khi risk đang live.

**Fix đồng thuận**: Sau bước đọc README.md (6.0 mới), thêm bước 6.1: *"Đọc Dependencies trong README. Nếu upstream topic nào có status ≠ CLOSED trong debate-index.md, DỪNG debate, ghi lý do."*

**Scope**: `[WARNING]` chỉ áp dụng cho 019B, 019C, 019D1, 019D2, 019D3. Các topic 019A, 019E, 019F, 019G không bị ảnh hưởng (deps đã CLOSED hoặc không có hard-dep).

#### TMP-019-03: 019C condensation — HỘI TỤ → `[NOTE]` (đã hội tụ từ C.2)

Cả hai phía đồng ý: scope note D-12 đã đủ. Inline TL;DR 10-15 dòng là compromise nếu cần tối ưu context. Không cần file riêng.

#### TMP-019-04: Granularity debt — HỘI TỤ → `[NOTE]`

Tôi rút lại "NOT A BUG" và chấp nhận `[NOTE]`.

**Verify rule**: `x38_RULES.md` §6.3 dòng 129: *"Mỗi topic tương ứng một **quyết định kiến trúc** cụ thể."* — câu trần thuật (declarative), không phải "nên" (should). 019A (3 decisions), 019B (4), 019E (4) lệch so với rule này.

**Nhưng đồng ý severity thấp**: Lệch không tái tạo monolith. `rules.md` §10 cho phép loại converged items mỗi round → mitigation đã có. Debt thật, severity `[NOTE]`.

### Bảng trạng thái (FINAL)

| Issue ID | Điểm | Phân loại | Trạng thái | Resolution |
|---|---|---|---|---|
| TMP-019-01 | SPLIT guard + load order | Sai thiết kế | **Converged** | `[WARNING]` — fix: đảo thứ tự §25 + abort nếu SPLIT |
| TMP-019-02 | Dependency gate enforcement | Thiếu sót | **Converged** | `[WARNING]` cho 019B/C/D1/D2/D3 — fix: preflight dep check |
| TMP-019-03 | 019C round-1 condensation | Judgment call | **Converged** | `[NOTE]` — inline TL;DR nếu cần, không bắt buộc |
| TMP-019-04 | Granularity debt sau split | Thiếu sót | **Converged** | `[NOTE]` — debt thật, không block debate |

### Phán quyết cuối cùng

**Tất cả 4 issues đã hội tụ.** Tôi đề xuất đóng tranh luận tại C.3.

**Kết luận chung**: Bug "monolithic + scope creep 3 lần tạo rác khi debate bắt đầu" đã được xử lý ở lớp nội dung. Lớp workflow còn **2 WARNING** (SPLIT guard + dependency gate) cần patch trước khi dùng generic prompt cho parent SPLIT topics và hard-dep sub-topics. 019A + 019E/F/G có thể debate ngay. 019B/C/D1-D3 chờ fix hoặc chờ 019A resolve.

**Fix tối thiểu (2 patches)**:
1. `debate/rules.md` §25 + `debate/prompt_template.md` Prompt A/B: đọc README trước findings, abort nếu SPLIT.
2. Cùng vị trí: sau khi đọc README, check upstream deps vs debate-index status, abort nếu upstream chưa CLOSED.

## C.4. Phản biện của ChatGPT Pro cho Claude Code: Chưa thể đóng ở C.3 vì fix TMP-019-02 đang dùng sai source of truth

### Mục đã hội tụ (loại khỏi phạm vi)
1. **TMP-019-01 — SPLIT guard + load order** đã hội tụ ở `[WARNING]`; hướng fix đúng là đọc `README.md` trước và abort nếu `Status = SPLIT`.
2. **TMP-019-02 — dependency gate thiếu enforcement** đã hội tụ về bản chất vấn đề và severity: đây là `[WARNING]` cho các sub-topic hard-dep (`019B`, `019C`, `019D1`, `019D2`, `019D3`).
3. **TMP-019-03 — 019C condensation** đã hội tụ ở `[NOTE]`; nếu tối ưu thì thêm TL;DR inline, không cần file riêng.
4. **TMP-019-04 — granularity debt** đã hội tụ ở `[NOTE]`; debt có thật nhưng không tái tạo monolith cấp-cha.

### Mục chưa hội tụ

#### TMP-019-02 — resolution path cho dependency gate vẫn dùng sai authority surface
- **Phân loại của issue gốc**: Thiếu sót
- **Trạng thái**: Open
- **Evidence**:
  - `research/x38/tmp/monolithic_topic_019xxx.md:L49-L55`
  - `research/x38/debate/prompt_template.md:L0-L4`

**Phản biện trọng tâm**: Tôi không chấp nhận đóng hồ sơ tại C.3 vì resolution text hiện tại tự mâu thuẫn với source-of-truth model của repo.

Ở C.3, anh chốt fix cho TMP-019-02 như sau: sau khi đọc `README.md`, thêm bước 6.1 kiểm tra `Dependencies`; nếu upstream topic nào có `status ≠ CLOSED` trong `debate-index.md` thì dừng debate. Vấn đề là ngay trong `prompt_template.md`, `debate-index.md` đã được mô tả là **navigation/status hint, không phải source of truth cho rounds**. Authority cho trạng thái topic nằm trong chính topic dir: `README.md`, `findings-under-review.md` (OPEN topics), và `final-resolution.md` (CLOSED topics).

Nói thẳng: vá lỗi gating bằng một gate dựa trên file **không-authority** là sai hướng. Nếu `debate-index.md` trễ cập nhật hoặc lệch trạng thái so với topic dir, generic prompt lại tiếp tục mở/suppress round dựa trên surface phụ. Như vậy TMP-019-02 chưa hội tụ thật; mới chỉ hội tụ ở **chẩn đoán** (`[WARNING]`), chưa hội tụ ở **resolution path**.

**Resolution path tôi chấp nhận**:
1. Đọc `debate/{TOPIC_DIR}/README.md` để lấy danh sách hard dependencies.
2. Với mỗi `UPSTREAM_DIR`, kiểm tra `debate/{UPSTREAM_DIR}/final-resolution.md`.
3. Nếu `final-resolution.md` tồn tại → dependency satisfied.
4. Nếu không tồn tại → DỪNG, không tạo round artifact.
5. Nếu `README` hoặc `debate-index` nói CLOSED nhưng `final-resolution.md` không tồn tại → coi là governance inconsistency và vẫn **fail-closed**.

Lý do tôi insist điểm này rất đơn giản: chính Prompt A đã dùng `final-resolution.md` để gate việc một topic đã CLOSED hay chưa. Dependency gate phải dùng **cùng authority model** đó. Không được dùng `debate-index.md` làm truth source cho abort logic rồi lại gọi repo đã “hội tụ hoàn toàn”.

### Bảng trạng thái (cập nhật)
| Issue ID | Điểm | Phân loại | Trạng thái | Resolution hiện tại |
|---|---|---|---|---|
| TMP-019-01 | SPLIT guard + load order | Sai thiết kế | **Converged** | `[WARNING]` — README trước findings; abort nếu SPLIT |
| TMP-019-02 | Dependency gate enforcement | Thiếu sót | **Open** | `[WARNING]` — severity đã hội tụ, nhưng gate phải dựa vào upstream `final-resolution.md`, không phải `debate-index.md` |
| TMP-019-03 | 019C round-1 condensation | Judgment call | **Converged** | `[NOTE]` — TL;DR inline nếu cần |
| TMP-019-04 | Granularity debt sau split | Thiếu sót | **Converged** | `[NOTE]` — debt thật, không block debate |

### Kết luận tạm thời
Tôi không đồng ý đóng tranh luận ở C.3. Debate này còn đúng **1 điểm mở**: TMP-019-02 chưa chốt đúng source of truth cho dependency gate. Khi điểm đó được sửa theo authority model của repo, tôi sẽ đồng ý đóng.

## C.5. Phản biện của Claude Code cho ChatGPT Pro: Hội tụ TMP-019-02 resolution path — Đóng tranh luận

### Mục đã hội tụ (loại khỏi phạm vi)

1. **TMP-019-01** — `[WARNING]`, fix đồng thuận. CONVERGED.
2. **TMP-019-03** — `[NOTE]`, inline TL;DR nếu cần. CONVERGED.
3. **TMP-019-04** — `[NOTE]`, debt thật. CONVERGED.
4. **TMP-019-02 severity** — `[WARNING]` cho 019B/C/D1/D2/D3. CONVERGED.

### Mục hội tụ MỚI trong round này

#### TMP-019-02 resolution path — HỘI TỤ → gate dựa trên `final-resolution.md`

Tôi chấp nhận phản biện C.4 hoàn toàn. Fix tôi đề xuất ở C.3 tự mâu thuẫn.

**Mâu thuẫn cụ thể**: C.3 viết *"check status trong debate-index.md"* trong khi chính `prompt_template.md` dòng 24-25 ghi rõ `debate-index.md` là *"navigation/status hint, không phải source of truth cho rounds"*. Đồng thời, Prompt A dòng 10-11 đã dùng `final-resolution.md` làm gate CLOSED:

> *"Nếu `debate/{TOPIC_DIR}/final-resolution.md` đã tồn tại thì DỪNG: topic đã CLOSED, không mở debate mới."*

Dependency gate **phải** dùng cùng authority model. Dùng `debate-index.md` cho abort logic tạo 2 source of truth — chính xác loại inconsistency mà TMP-019-01 vừa sửa.

**Resolution path đồng thuận (5 bước từ C.4)**:

1. Đọc `debate/{TOPIC_DIR}/README.md` → lấy danh sách hard dependencies (upstream dirs).
2. Với mỗi `UPSTREAM_DIR`, kiểm tra `debate/{UPSTREAM_DIR}/final-resolution.md`.
3. Nếu `final-resolution.md` tồn tại → dependency satisfied.
4. Nếu không tồn tại → **DỪNG**, không tạo round artifact, ghi lý do.
5. Nếu `README` hoặc `debate-index` nói CLOSED nhưng `final-resolution.md` không tồn tại → governance inconsistency, **fail-closed**.

**Tại sao fail-closed đúng**: Gate hiện có (Prompt A dòng 10-11) đã fail-closed cho CLOSED topics. Dependency gate mới phải consistent: thiếu `final-resolution.md` = chưa CLOSED = block, bất kể index nói gì.

### Bảng trạng thái (FINAL)

| Issue ID | Điểm | Phân loại | Trạng thái | Resolution |
|---|---|---|---|---|
| TMP-019-01 | SPLIT guard + load order | Sai thiết kế | **Converged** | `[WARNING]` — README trước findings; abort nếu SPLIT |
| TMP-019-02 | Dependency gate enforcement | Thiếu sót | **Converged** | `[WARNING]` — gate dựa trên upstream `final-resolution.md`, fail-closed |
| TMP-019-03 | 019C round-1 condensation | Judgment call | **Converged** | `[NOTE]` — inline TL;DR nếu cần |
| TMP-019-04 | Granularity debt sau split | Thiếu sót | **Converged** | `[NOTE]` — debt thật, không block debate |

### Phán quyết cuối cùng

**Tất cả 4 issues đã hội tụ hoàn toàn**, bao gồm cả resolution path cho TMP-019-02.

**Kết luận chung**: Bug "monolithic + scope creep 3 lần tạo rác khi debate bắt đầu" đã được xử lý ở lớp nội dung. Lớp workflow còn **2 WARNING** cần patch:

1. **SPLIT guard** (`rules.md` §25 + `prompt_template.md` Prompt A/B): đọc README trước findings, abort nếu `Status = SPLIT`.
2. **Dependency gate** (cùng vị trí): sau khi đọc README, duyệt hard-dep list, kiểm tra `final-resolution.md` tồn tại cho mỗi upstream topic, fail-closed nếu thiếu.

**Hệ quả thực dụng**:
- **Debate ngay được**: 019A, 019E, 019F, 019G (không có hard-dep chưa satisfied).
- **Chờ fix hoặc chờ 019A resolve**: 019B, 019C, 019D1, 019D2, 019D3.
- **2 NOTE** (019C TL;DR, granularity debt): không block, fix khi thuận tiện.

Tôi đề xuất đóng tranh luận tại C.5.

## C.6. Phản biện của ChatGPT Pro cho Claude Code: TMP-019-02 chưa hội tụ vì C.5 đã sửa authority nhưng chưa chốt semantic model của dependency

### Mục đã hội tụ (loại khỏi phạm vi)

1. **TMP-019-01** — `[WARNING]`, fix đúng hướng: đọc `README.md` trước, abort nếu `Status = SPLIT`. CONVERGED.
2. **TMP-019-03** — `[NOTE]`, 019C không cần file summary riêng; nếu muốn tối ưu context thì thêm TL;DR inline. CONVERGED.
3. **TMP-019-04** — `[NOTE]`, granularity debt là debt thật nhưng không tái tạo monolith cấp-cha. CONVERGED.
4. **TMP-019-02 source of truth** — dependency gate không được dựa vào `debate-index.md`; điểm này đã hội tụ ở C.4/C.5. CONVERGED.

### Mục chưa hội tụ

#### TMP-019-02 — dependency gate đang trộn lẫn hai semantic models khác nhau
- **Phân loại của issue gốc**: Thiếu sót
- **Trạng thái**: Open
- **Evidence**:
  - `research/x38/tmp/monolithic_topic_019xxx.md:L397-L415`
  - `research/x38/debate/prompt_template.md:L25-L27,L98-L119`
  - `research/x38/debate/019B-ai-analysis-reporting/README.md:L40-L48,L80`
  - `research/x38/debate/019C-systematic-data-exploration/README.md:L55-L63`
  - `research/x38/debate/019D2-statistical-budget/README.md:L49-L57`

**Phản biện trọng tâm**: C.5 sửa đúng **authority surface**, nhưng chưa chốt đúng **semantic model** của dependency. Hai chuyện này không giống nhau.

Tôi đồng ý hoàn toàn với nửa đầu của C.5: `debate-index.md` không được dùng làm source of truth cho abort logic, và `final-resolution.md` là hồ sơ authoritative khi một topic đã CLOSED. Nhưng từ đó anh nhảy luôn sang kết luận mạnh hơn: **mọi hard dependency đều phải gate bằng `final-resolution.md` của toàn upstream topic**. Bước nhảy này chưa được repo chứng minh.

Lý do rất cụ thể: chính các README của cụm 019 hiện đang dùng **hai semantic models khác nhau** cho dependency:

- **Whole-topic closure dependency**: 019D2 viết thẳng `Upstream (must close first): 019A`.
- **Named-decision prerequisite**: 019B viết `depend on 019A resolving D-01, D-02, D-03 first` và còn nhắc lại ở prerequisite check rằng các decision đó phải resolve trước khi debate bắt đầu.
- **Single-decision outcome dependency**: 019C viết rõ `needs DFL-09 scope resolution (D-01)` và `Depends on 019A outcome for D-01`.

Nói thẳng: repo hiện **không dùng một semantic duy nhất**. Có chỗ nói “phải đóng cả topic”, có chỗ nói “chỉ cần answer cụ thể từ upstream”.

Trong khi đó, `prompt_template.md` lại nói `final-resolution.md` chỉ được tạo trong phase closure, khi **mọi issue trong scope** đã là Converged hoặc Judgment call. Vì vậy, gate `final-resolution`-only không chỉ chọn một source of truth; nó còn **nâng yêu cầu** của 019B/019C từ “cần answer upstream cụ thể” thành “cần toàn bộ 019A đóng”. Đó là thay đổi semantic dependency, không còn là fix kỹ thuật thuần túy.

**Steel-man mạnh nhất cho vị trí C.5**: “Một gate duy nhất dựa trên `final-resolution.md` là đơn giản nhất, fail-closed nhất, và tránh phải parse dependency text hay theo dõi partial closure.”

**Vì sao steel-man này vẫn chưa đủ để đóng hồ sơ**:

1. Nó là **một lựa chọn thiết kế mới**, không phải hệ quả logic bắt buộc từ repo hiện tại.
2. Nếu muốn chọn model “whole-topic closure only”, thì phải **chuẩn hóa lại README dependencies** của 019B và 019C để chúng nói đúng semantic đó. Giữ nguyên wording hiện tại rồi tuyên bố hội tụ là không sạch.
3. Nếu muốn giữ nguyên wording hiện tại của 019B/019C, thì gate phải hỗ trợ **mixed granularity** chứ không thể ép tất cả về topic-level closure.

Tức là C.5 mới giải được câu hỏi **"authority nằm ở đâu"**, nhưng chưa giải xong câu hỏi **"dependency được diễn đạt ở granularity nào"**.

**Resolution path tôi chấp nhận**:

**Phương án A — chuẩn hóa về topic-level closure**
1. Sửa README của các topic như 019B và 019C để bỏ wording kiểu `needs D-01`, `resolving D-01/D-02/D-03 first`.
2. Thay bằng wording nhất quán kiểu `Upstream (must close first): 019A`.
3. Khi đó, gate `final-resolution`-only của C.5 là hợp lệ và TMP-019-02 có thể đóng.

**Phương án B — giữ mixed-granularity như hiện tại**
1. Giữ nguyên dependency declarations hiện có trong README.
2. Thêm một surface authoritative, machine-readable cho status ở mức issue/decision trong topic dir (hoặc chuẩn hóa rõ cách dùng `current_status` trong `findings-under-review.md` cho partial dependency satisfaction).
3. Dependency gate phải phân biệt:
   - dependency kiểu `must close first` → check `final-resolution.md`
   - dependency kiểu `needs D-01`, `resolving D-01/D-02/D-03 first` → check đúng issue/decision upstream theo authority surface đó.

Cho tới khi repo chọn **A hoặc B**, TMP-019-02 chưa hội tụ thật. C.5 đang đóng quá sớm.

### Bảng trạng thái (cập nhật)

| Issue ID | Điểm | Phân loại | Trạng thái | Resolution hiện tại |
|---|---|---|---|---|
| TMP-019-01 | SPLIT guard + load order | Sai thiết kế | **Converged** | `[WARNING]` — README trước findings; abort nếu SPLIT |
| TMP-019-02 | Dependency gate enforcement | Thiếu sót | **Open** | `[WARNING]` — source of truth đã hội tụ, nhưng semantic model của dependency chưa được chuẩn hóa (topic-level only vs mixed granularity) |
| TMP-019-03 | 019C round-1 condensation | Judgment call | **Converged** | `[NOTE]` — TL;DR inline nếu cần |
| TMP-019-04 | Granularity debt sau split | Thiếu sót | **Converged** | `[NOTE]` — debt thật, không block debate |

### Kết luận tạm thời

Tôi không đồng ý đóng tranh luận tại C.5. Điểm mở còn lại giờ đã hẹp: **TMP-019-02 chưa chốt semantic model cho dependency gate**. Nếu áp dụng nghiêm `rules.md` mặc định `max_rounds_per_topic = 6`, thì sau C.6 bước tiếp theo theo quy định không phải là giả vờ hội tụ; nó phải là **Judgment call của human researcher** để chọn Phương án A hay B, hoặc một override rõ ràng cho phép vượt round cap.

## C.7. Phản biện của Claude Code cho ChatGPT Pro: Đạt round cap — chuyển TMP-019-02 semantic model thành Judgment call

### Mục đã hội tụ (loại khỏi phạm vi)

1. **TMP-019-01** — `[WARNING]`, fix đồng thuận: README trước findings, abort nếu SPLIT. CONVERGED.
2. **TMP-019-02 severity** — `[WARNING]` cho 019B/C/D1/D2/D3. CONVERGED.
3. **TMP-019-02 authority surface** — gate dựa trên `final-resolution.md`, không dùng `debate-index.md`. CONVERGED.
4. **TMP-019-03** — `[NOTE]`, inline TL;DR nếu cần. CONVERGED.
5. **TMP-019-04** — `[NOTE]`, debt thật, không block debate. CONVERGED.

### Round cap

`rules.md` dòng 13-14: *"Mặc định `max_rounds_per_topic = 6`. Sau `max_rounds_per_topic`, mọi issue còn Open phải chuyển thành Judgment call, kèm tradeoff rõ ràng và artifact mới nhất."*

C.6 = round 6. ChatGPT Pro chính xác khi nói bước tiếp theo phải là Judgment call, không phải giả vờ hội tụ. Tôi tuân thủ quy định.

### TMP-019-02 semantic model — chuyển thành **Judgment call**

#### Chẩn đoán đã hội tụ

Cả hai phía đồng ý:
- Dependency gate phải dùng `final-resolution.md` làm authority (không dùng `debate-index.md`).
- Repo hiện tại dùng **hai semantic models** cho dependency: whole-topic closure ("must close first") và named-decision ("needs D-01").
- Gate `final-resolution.md`-only = topic-level closure, **nâng yêu cầu** cho các sub-topic đang dùng named-decision semantics.
- Phải chọn 1 trong 2 phương án trước khi fix có thể implemented.

#### Verify trực tiếp repo — dependency map thực tế

| Sub-topic | Dependency declaration (README) | Semantic | Cần từ 019A |
|---|---|---|---|
| 019B | "D-01, D-02, D-03 must be resolved" | Named-decision | **3/3** decisions |
| 019C | "needs DFL-09 scope resolution (D-01)" | Named-decision | **1/3** decisions |
| 019D1 | "must close first: 019A, 019B" | Whole-topic | All |
| 019D2 | "must close first: 019A" | Whole-topic | All |
| 019D3 | "must close first: 019A, 019D2" | Whole-topic | All |

**Quan sát quan trọng**: 019B cần **3/3** decisions từ 019A. Vì 019A chỉ có đúng 3 decisions (D-01, D-02, D-03), "cần tất cả 3 decisions" ≡ "cần 019A close". Mixed semantics ở 019B **không tạo operational difference**.

**Case duy nhất thực sự mixed**: 019C cần **1/3** decisions (D-01). Dưới Option A, 019C phải chờ thêm D-02 và D-03. Dưới Option B, 019C có thể bắt đầu ngay khi D-01 resolve.

#### Tradeoff analysis

**Phương án A — chuẩn hóa về topic-level closure**

| Pros | Cons |
|---|---|
| Gate đơn giản: chỉ check `final-resolution.md` tồn tại | 019C phải chờ D-02/D-03 dù chỉ cần D-01 |
| Consistent với CLOSED gate hiện có trong Prompt A | Cần sửa README 019B (cosmetic: đã 3/3) và 019C (real: 1/3→all) |
| Không cần infrastructure mới cho partial-resolution tracking | Nâng yêu cầu từ "D-01" thành "toàn bộ 019A" cho 019C |
| 4/5 sub-topics ĐÃ dùng whole-topic semantics | — |
| 019A là foundation topic, 3 decisions tightly coupled → likely resolve cùng wave | — |

**Phương án B — giữ mixed-granularity**

| Pros | Cons |
|---|---|
| Giữ đúng intent gốc: 019C chỉ cần D-01 | Cần machine-readable decision status tracking (hiện chưa có) |
| 019C có thể bắt đầu sớm hơn nếu D-01 resolve trước D-02/D-03 | Gate phải parse dependency text, phân biệt 2 kiểu semantic |
| — | Thêm surface cần maintain + failure mode mới (partial status desync) |
| — | Chỉ benefit 1/5 sub-topics (019C) |
| — | `prompt_template.md` §closure chỉ tạo `final-resolution.md` khi **mọi** issue converge → không có artifact sẵn cho partial resolution |

#### Khuyến nghị của tôi cho human researcher

**Chọn Phương án A** vì:

1. **Operational cost thấp**: 019A là foundation topic (wave 2.5A, debate trước tất cả). 3 decisions cùng evidence base (DFL-04, DFL-05, DFL-09), cùng tension surface. Chênh lệch thời gian giữa D-01 resolve và 019A close dự kiến ngắn (cùng wave, cùng phiên debate).

2. **Complexity cost cao cho B**: Mixed-granularity gate cần infrastructure chưa tồn tại — partial-resolution tracking, machine-readable decision status, gate parsing logic. Tất cả cho benefit duy nhất = 019C có thể bắt đầu sớm hơn *nếu* D-01 resolve đáng kể trước D-02/D-03 (unlikely given tight coupling).

3. **Consistency**: 4/5 dependent sub-topics đã dùng whole-topic. 019B tuy wording khác nhưng functionally ≡ whole-topic (3/3 = all). Chỉ 019C là genuinely mixed.

4. **README cleanup minimal**: Sửa 019B (cosmetic — thay "D-01, D-02, D-03 must be resolved" bằng "must close first") và 019C (substantive — thay "needs D-01" bằng "must close first: 019A"). Tổng cộng ~4 dòng.

### Bảng trạng thái (FINAL)

| Issue ID | Điểm | Phân loại | Trạng thái | Resolution |
|---|---|---|---|---|
| TMP-019-01 | SPLIT guard + load order | Sai thiết kế | **Converged** | `[WARNING]` — README trước findings; abort nếu SPLIT |
| TMP-019-02 | Dependency gate enforcement | Thiếu sót | **Judgment call** | `[WARNING]` — gate dùng `final-resolution.md` (converged). Semantic model: **Phương án A recommended** (topic-level closure, sửa README 019B/019C). Human researcher chọn A/B. |
| TMP-019-03 | 019C round-1 condensation | Judgment call | **Converged** | `[NOTE]` — inline TL;DR nếu cần |
| TMP-019-04 | Granularity debt sau split | Thiếu sót | **Converged** | `[NOTE]` — debt thật, không block debate |

### Phán quyết cuối cùng (round cap)

**Tranh luận đóng tại C.7** theo `rules.md` max_rounds_per_topic = 6.

**Kết quả**: 3 Converged + 1 Judgment call.
- **3 Converged**: TMP-019-01 `[WARNING]`, TMP-019-03 `[NOTE]`, TMP-019-04 `[NOTE]`
- **1 Judgment call**: TMP-019-02 — severity `[WARNING]` và authority surface đã hội tụ. Còn lại: human researcher chọn semantic model (A: topic-level closure recommended, B: mixed-granularity).

**Hệ quả thực dụng (không đổi)**:
- **Debate ngay được**: 019A, 019E, 019F, 019G.
- **Chờ 019A resolve + fix gating**: 019B, 019C, 019D1, 019D2, 019D3.

**Fix tối thiểu (2 patches, không phụ thuộc Judgment call)**:
1. `debate/rules.md` §25 + `debate/prompt_template.md` Prompt A/B: đọc README trước findings, abort nếu `Status = SPLIT`.
2. Cùng vị trí: sau README, duyệt hard-dep list, check upstream `final-resolution.md` tồn tại, fail-closed nếu thiếu.

**Pending Judgment call**: Trước khi implement patch 2, human researcher chọn A/B rồi chuẩn hóa README dependencies cho consistent.

## C.8. Phản biện của ChatGPT Pro cho Claude Code: Closure audit — C.7 đúng ở chẩn đoán, nhưng chưa đủ điều kiện để tự tuyên bố đóng phiên

### Mục đã hội tụ (loại khỏi phạm vi)
1. **TMP-019-01** — `[WARNING]`, fix đồng thuận: `README.md` trước `findings-under-review.md`, abort nếu `Status = SPLIT`. CONVERGED.
2. **TMP-019-02 severity** — `[WARNING]` cho 019B/019C/019D1/019D2/019D3. CONVERGED.
3. **TMP-019-02 authority surface** — dependency gate phải dựa trên `final-resolution.md`, không dùng `debate-index.md` làm truth source cho abort logic. CONVERGED.
4. **TMP-019-03** — `[NOTE]`, 019C không bắt buộc file summary riêng; inline TL;DR là đủ nếu cần. CONVERGED.
5. **TMP-019-04** — `[NOTE]`, granularity debt là debt governance thật nhưng không tái tạo monolith cấp-cha. CONVERGED.
6. **TMP-019-02 state transition** — sau round cap, issue còn mở phải chuyển thành `Judgment call` với tradeoff rõ ràng. Tôi chấp nhận việc C.7 chuyển TMP-019-02 sang `Judgment call`. CONVERGED.

### Closure audit — điểm tôi KHÔNG chấp nhận trong C.7
C.7 đúng ở chỗ: sau `max_rounds_per_topic`, không được giả vờ hội tụ; TMP-019-02 phải được đưa sang `Judgment call`.

Nhưng tôi **không chấp nhận** câu: **"Tranh luận đóng tại C.7"** như một kết luận thủ tục đã hoàn tất.

**Evidence pointer**:
- `research/x38/debate/rules.md:L13-L14b`
- `research/x38/debate/prompt_template.md:L8-L12`
- `research/x38/tmp/monolithic_topic_019xxx.md:L82-L95`

**Lý do 1 — parity rule chưa được đáp ứng tại chính C.7**
`rules.md` yêu cầu: sau round cap, issue mở chuyển thành `Judgment call`; nhưng trước khi chuyển sang judgment/closure, **hai bên phải có số round bằng nhau**, hoặc bất đối xứng phải được ghi rõ kèm lý do trong `final-resolution.md`.

Sau C.7, Claude Code có 4 lượt (`C.1`, `C.3`, `C.5`, `C.7`), còn ChatGPT Pro mới có 3 lượt (`C.2`, `C.4`, `C.6`). Nghĩa là **C.7 không tự thân hoàn tất closure**. Nó chỉ hoàn tất phần **merits**. Muốn đóng hồ sơ sạch theo rules, phải có **lượt parity này** hoặc một `final-resolution.md` ghi rõ vì sao bất đối xứng được chấp nhận.

**Lý do 2 — Prompt C còn thiếu human judgment**
`prompt_template.md` Prompt C ghi rất rõ: closure chỉ chạy khi **(a)** mọi issue đã là `Converged` hoặc `Judgment call`, **và (b)** human researcher đã quyết định mọi `Judgment call`.

Điều kiện (a) hiện đã đạt. Nhưng điều kiện (b) **chưa đạt**: TMP-019-02 vẫn chỉ mới có **khuyến nghị** "Phương án A recommended", chứ chưa có **phán quyết của decision_owner**.

**Lý do 3 — lượt này chính là closure audit còn thiếu**
Ngay trong Prompt C cũng có note: **Codex closure audit nên hoàn thành trước khi possible**. Lượt C.8 này chính là closure audit đó. Vì vậy, câu đúng về mặt thủ tục không phải là **"đóng tại C.7"**, mà là:

> **Debate merits kết thúc tại C.7; closure pending human judgment cho TMP-019-02 và Prompt C synchronization.**

### Phán quyết của tôi ở C.8
- **Chấp nhận** TMP-019-02 = `Judgment call` `[WARNING]`.
- **Không mở lại merits** giữa Phương án A và B trong tranh luận agent-to-agent; phần đó đã chuyển sang decision owner.
- **Không phản bác** việc C.7 nghiêng về **Phương án A** như default vận hành. Tôi đồng ý đây là default thực dụng hơn, nhưng nó vẫn là **khuyến nghị**, chưa phải resolution cho tới khi human researcher chọn.
- **Bác bỏ duy nhất** tuyên bố procedural: chưa nên viết **"tranh luận đóng tại C.7"** như thể closure đã hoàn tất.

### Bảng trạng thái (closure audit)
| Issue ID | Điểm | Phân loại | Trạng thái | Resolution |
|---|---|---|---|---|
| TMP-019-01 | SPLIT guard + load order | Sai thiết kế | **Converged** | `[WARNING]` — `README.md` trước findings; abort nếu SPLIT |
| TMP-019-02 | Dependency gate enforcement | Thiếu sót | **Judgment call** | `[WARNING]` — authority = `final-resolution.md` (converged). Semantic model A/B do human researcher chọn; **A là default khuyến nghị hiện tại** |
| TMP-019-03 | 019C round-1 condensation | Judgment call | **Converged** | `[NOTE]` — inline TL;DR nếu cần |
| TMP-019-04 | Granularity debt sau split | Thiếu sót | **Converged** | `[NOTE]` — debt thật, không block debate |

### Kết luận tạm thời
Về **tranh luận nội dung**, hồ sơ đã xong ở C.7: không còn merits issue nào cần agent phản biện thêm.

Về **thủ tục đóng hồ sơ**, C.8 mới là lượt parity/closure-audit cần thiết. Bước kế tiếp đúng quy định **không phải C.9 rebuttal**, mà là:
1. human researcher chọn **Phương án A** hoặc **B** cho TMP-019-02;
2. ghi judgment đó vào `judgment-call-deliberation.md` hoặc trực tiếp trong `final-resolution.md`;
3. chạy **Prompt C** để đồng bộ `final-resolution.md`, `findings-under-review.md`, `README.md`, `debate-index.md`.

---

# D. JUDGMENT CALL — HUMAN RESEARCHER

**NOTE** (Judgment call, TMP-019-02): Chọn **Phương án A** — chuẩn hóa dependency về topic-level closure.

**Lý do**: authority surface hiện tại của repo là topic-level (`final-resolution.md`); downstream 019B/019D1/019D2/019D3 đã vận hành theo model này, còn 019C là ngoại lệ duy nhất nhưng vẫn được schedule after 019A. Giữ mixed-granularity sẽ đòi thêm protocol authoritative cho partial-resolution mid-topic, hiện repo chưa có.

**Decision owner**: human researcher

**Ngày**: 2026-04-04

### Bảng trạng thái (FINAL — post-judgment)

| Issue ID | Điểm | Phân loại | Trạng thái | Resolution |
|---|---|---|---|---|
| TMP-019-01 | SPLIT guard + load order | Sai thiết kế | **Converged** | `[WARNING]` — README trước findings; abort nếu SPLIT |
| TMP-019-02 | Dependency gate enforcement | Thiếu sót | **Judgment call → DECIDED** | `[WARNING]` — Option A: topic-level closure, gate bằng `final-resolution.md`. Sửa README 019B/019C. |
| TMP-019-03 | 019C round-1 condensation | Judgment call | **Converged** | `[NOTE]` — inline TL;DR nếu cần |
| TMP-019-04 | Granularity debt sau split | Thiếu sót | **Converged** | `[NOTE]` — debt thật, không block debate |

### Action items

1. **Patch `rules.md` §25**: Đảo thứ tự — README.md trước findings-under-review.md. Thêm SPLIT guard + dependency gate (check upstream `final-resolution.md`, fail-closed).
2. **Patch `prompt_template.md` Prompt A/B**: Tương tự — README trước, SPLIT guard, dependency gate.
3. **Sửa 019B README**: "must resolve first" + named-decisions → "must close first" (whole-topic).
4. **Sửa 019C README**: "needs D-01" → "must close first: 019A" (whole-topic).
