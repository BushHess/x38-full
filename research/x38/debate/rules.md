# QUY TẮC TRANH LUẬN — X38

Kế thừa từ `research/x34/debate/rules.md`, điều chỉnh cho context thiết kế kiến trúc.

Tranh luận khoa học để tìm thiết kế đúng nhất, không phải đồng thuận.

## Nguyên tắc cốt lõi

1. Không tìm đồng thuận; tìm thiết kế đúng nhất theo bằng chứng và lập luận.
2. Mỗi điểm phải có cơ sở: nguyên tắc kỹ thuật phần mềm, bằng chứng thực nghiệm
   từ project (V4→V8, x37), lập luận toán học, hoặc prior art. "Tôi nghĩ" hay
   "thường thì" không đủ. Mọi claim phải kèm evidence pointer có thể kiểm chứng
   (đường dẫn file, dòng cụ thể, hoặc tham chiếu nguyên tắc).
3. Mỗi issue phải được gán đúng một `classification`:
   - `Sai thiết kế`: vi phạm nguyên tắc đã established (contamination leak,
     lookahead, broken isolation, ...). Phải sửa.
   - `Thiếu sót`: bỏ qua trường hợp, edge case, hoặc yêu cầu cần thiết. Nên bổ sung.
   - `Judgment call`: cả hai phía có lý. Phải ghi rõ tradeoff và ai quyết định.
4. Phản biện tấn công argument, không phải kết luận. Nếu đồng ý kết luận
   nhưng lý do sai, vẫn phải phản bác lý do.
5. Nghĩa vụ chứng minh thuộc bên đề xuất thay đổi. Thiết kế hiện hành giữ
   nguyên trừ khi bên phản biện chứng minh nó sai hoặc thiếu.
6. Thứ bậc bằng chứng khi xung đột:
   - Bằng chứng toán học (proof) > thực nghiệm (empirical) > lý thuyết chung
   - Kết quả từ project này (V4→V8, x37) > kết quả domain khác
   - Nguyên tắc đã chứng minh trong practice > ý kiến lý thuyết chưa kiểm chứng

## Chống đồng thuận giả

7. Cấm chấp nhận mà không phản bác. Trước khi đánh dấu `hội tụ`,
   bên chấp nhận PHẢI:
   (a) Nêu phản biện mạnh nhất còn lại (steel-man) cho vị trí cũ của mình.
   (b) Giải thích cụ thể tại sao phản biện đó không đứng vững, có trích dẫn
       bằng chứng thay vì chỉ nói "đã thuyết phục".
   (c) Bên kia xác nhận steel-man: `Đúng, đó là argument mạnh nhất`
       hoặc `Không, argument mạnh nhất là [X]`. Nếu bị từ chối, phải
       steel-man lại. Tối đa 2 lần thử; nếu sau 2 lần vẫn bị từ chối,
       issue tự động chuyển thành `Judgment call` với ghi chú
       `steel-man impasse`.
   Nếu không hoàn thành đủ (a)(b)(c), issue đó CHƯA hội tụ và vẫn là `Open`.
8. Cấm ngôn ngữ nhượng bộ mềm để đánh dấu hội tụ:
   - KHÔNG: `cũng được`, `tạm chấp nhận`, `không đáng tranh luận thêm`,
     `về cơ bản đồng ý`, `có lẽ bạn đúng`
   - PHẢI: `Tôi sai vì [bằng chứng cụ thể]` hoặc
     `Argument X mạnh hơn vì [lý do]`
9. Hai loại hội tụ:
   - `Hội tụ thật`: bên nhượng bộ chỉ ra bằng chứng hoặc logic cụ thể khiến
     vị trí cũ không đứng vững, và steel-man đã được xác nhận.
   - `Hội tụ giả`: nhượng bộ vì mệt, lịch sự, hoặc vì nghĩ điểm đó nhỏ.
     Hội tụ giả phải được xem là `Open`.
   Trong bảng trạng thái, `Converged` luôn có nghĩa là hội tụ thật (đã qua
   steel-man). Hội tụ giả không được ghi là `Converged`; nó vẫn là `Open`.
10. Không có điểm nhỏ. Nếu đáng nêu ra, đáng tranh luận đúng cách.
    Nếu thật sự không quan trọng, xóa khỏi danh sách thay vì chấp nhận
    cho xong.

## Quy trình

11. Mỗi round file phải kết thúc bằng bảng trạng thái theo mẫu bên dưới.
12. Không mở `topic` mới sau vòng 1 trong cùng phiên tranh luận.
    Được phép thêm `issue` mới trong cùng topic nếu và chỉ nếu:
    - nó là `Thiếu sót` hoặc `Sai thiết kế` rút ra từ cùng evidence base,
      hoặc là hệ quả trực tiếp của issue đang mở
    - nó được ghi vào `findings-under-review.md` trước khi tranh luận sâu
    - nó không mở rộng scope của topic hiện tại sang một câu hỏi khác
    Nếu không thỏa cả ba điều kiện trên, phải mở topic hoặc phiên riêng.
13. Mặc định `max_rounds_per_topic = 6`, trừ khi topic đó ghi rõ khác.
14. Sau `max_rounds_per_topic`, mọi issue còn `Open` phải chuyển thành
    `Judgment call`, kèm tradeoff rõ ràng và artifact mới nhất.
14b. Trước khi chuyển sang Judgment call hoặc closure, cả hai bên phải có
    số round bằng nhau, HOẶC bất đối xứng phải được ghi nhận kèm lý do
    trong `final-resolution.md`. Nếu bên A đã nộp round N nhưng bên B chưa
    phản hồi: (a) chạy round N của bên B trước khi closure, HOẶC (b) ghi
    rõ tại sao bất đối xứng chấp nhận được (ví dụ: mọi issue đã Converged
    trước round N, hoặc Judgment call độc lập với cả hai vị trí agent).
    Mục đích: tránh đóng topic khi một bên chưa được phản hồi lập luận
    cuối cùng của bên kia.
15. `decision_owner` mặc định là human researcher.
16. Nếu `decision_owner` đồng thời là bên tranh luận, phần judgment phải
    ghi rõ: (a) vị trí mà họ đã bảo vệ, và (b) lý do cụ thể tại sao
    judgment không bị thiên lệch bởi vị trí đó.

## Bổ sung riêng cho X38

17. **Evidence types mở rộng**: Ngoài empirical evidence, chấp nhận:
    - Nguyên tắc kỹ thuật phần mềm (separation of concerns, immutability, ...)
    - Prior art từ quantitative research frameworks
    - Meta-lessons từ V4→V8/x37 (principle-level, KHÔNG specifics)
    - Lập luận toán học về contamination/independence
    - Failure modes đã quan sát trong online research (ví dụ: divergence,
      thiếu serialization, handoff loss)

18. **Nhãn `extra-archive` cho evidence ngoài x38**: Mọi evidence pointer trỏ tới
    file ngoài `research/x38/` (ví dụ: `x37/`, `v10/`, `CLAUDE.md`) phải gắn nhãn
    `[extra-archive]` khi cite trong debate. Mục đích: phân biệt rõ evidence nội bộ
    (có thể kiểm chứng trong x38 canonical tree) và evidence ngoại vi (có thể thay đổi
    hoặc bị xóa ngoài tầm kiểm soát của x38).

18a. **Phạm vi áp dụng §2 và §18 cho round-0 dossiers**: `findings-under-review.md`
    là mandatory input trước khi viết round artifact (xem §25). Do đó, cả pointer rule
    (§2: mọi claim phải kèm evidence pointer có thể kiểm chứng) và label rule
    (§18: `[extra-archive]` cho evidence ngoài x38) áp dụng cho `findings-under-review.md`
    ngay từ round 0, không chỉ khi cite trong round artifact.

18b. **Severity rubric cho audit findings**: Khi audit phát hiện lỗi governance,
    phân loại severity như sau:
    - `[BLOCK-DEBATE]` / `[BLOCK-DRAFT]` / `[BLOCK-PUBLISH]`: Vi phạm ngăn workflow
      tiếp tục. Yêu cầu fix trước khi mở round/draft/publish.
    - `[WARNING]`: Lỗi thật ảnh hưởng correctness hoặc completeness ở surface
      vận hành chính (debate-index, status ledgers, evidence pointers cho gating
      topics). Cần fix trước khi surface đó được dùng trong quyết định.
    - `[NOTE]`: Lỗi thật nhưng ở surface phụ (summary docs, parallel copies),
      hoặc lỗi ở surface chính nhưng downstream surfaces khác đã gate đúng —
      risk chỉ là confusion, không phải incorrect routing/gating.

19. **Scope giới hạn**: Debate chỉ bàn về kiến trúc framework.
    KHÔNG tranh luận về:
    - Feature names, lookbacks, thresholds cụ thể
    - Thuật toán trading cụ thể (đó là việc của framework khi chạy)
    - Deployment, paper trading, production concerns

20. **Pseudocode thay cho code**: Dùng pseudocode, interface description,
    hoặc dataclass skeleton để minh họa. Không viết implementation code.

## Cấu trúc debate

Giống x34:

```text
debate/
  README.md
  rules.md
  debate-index.md
  prompt_template.md

  NNN-slug/
    README.md
    findings-under-review.md
    input_*.md                  (pre-debate: solution proposals, critiques)
    final-resolution.md         (tạo khi mọi issue đã chốt)
    codex/round-N_[message-type].md
    claude_code/round-N_[message-type].md
```

### Quy tắc đặt tên

- `NNN`: số thứ tự 3 chữ số, zero-padded. Không tái sử dụng.
- `slug`: kebab-case, 2-5 từ, mô tả quyết định kiến trúc đang tranh luận.
- **Issue ID prefix**: mỗi topic chọn prefix riêng, format `X38-{CODE}-NN`.
  Ví dụ: topic 000 dùng `X38-D-` (Design), topic 004 dùng `X38-MK-`
  (Meta-Knowledge). Prefix ghi trong `findings-under-review.md` của topic.
  **Ngoại lệ**: findings kế thừa từ topic 000 (split 2026-03-22) giữ nguyên
  ID gốc `X38-D-*` để không phá cross-references. Topic mới chỉ đặt prefix
  riêng cho findings MỚI tạo sau khi split.
- Round files: `round-N_[message-type].md`
  - message-type: `opening-critique`, `rebuttal`, `author-reply`,
    `reviewer-reply`, `judgment-call`, `final-status`

## Cross-topic tensions (bắt buộc)

21. Mỗi topic `README.md` PHẢI có section `## Cross-topic tensions` ngay trước
    `## Files` (hoặc cuối file nếu không có `## Files`). Mỗi
    `findings-under-review.md` PHẢI có section tương tự ngay trước
    `## Bảng tổng hợp`. Section này ghi nhận:
    - Tensions đã biết với findings ở topics KHÁC
    - Resolution path: topic nào own quyết định, hay tự resolve bên trong
    **Lưu ý**: Section này KHÁC với `**Convergence notes liên quan**`
    (tham chiếu shared reference C-XX). Convergence notes là thông tin nền;
    Cross-topic tensions là xung đột cụ thể cần resolution path.
    **Chuyển tiếp**: Topics mở trước 2026-03-23 sẽ bổ sung section này khi
    bắt đầu round debate đầu tiên. Không yêu cầu backfill retroactive.

22. Format bắt buộc:

    ```markdown
    ## Cross-topic tensions

    | Topic | Finding | Tension | Resolution path |
    |-------|---------|---------|-----------------|
    | 002   | F-04    | Firewall blocks recalibration | 016 owns decision |
    ```

    - **Topic**: ID topic bị tension.
    - **Finding**: finding cụ thể gây tension (không ghi chung "liên quan đến").
    - **Tension**: mô tả xung đột cụ thể — phá invariant nào, đá luật nào.
    - **Resolution path**: `NNN owns decision` (topic khác own) hoặc
      `within this topic` (tự resolve) hoặc `shared — see C-XX` (convergence
      note đã capture).

23. Topic owner có trách nhiệm cập nhật section này mỗi khi:
    - Round mới reference finding từ topic khác
    - Topic khác close và resolution ảnh hưởng topic này
    - Convergence note mới được thêm vào shared reference (000)

24. Nếu một topic KHÔNG có tensions nào, ghi:

    ```markdown
    ## Cross-topic tensions

    Không có tension đã biết tại thời điểm mở topic.
    ```

    Section vẫn phải TỒN TẠI — không được bỏ qua.

## Nạp context trước khi viết

25. Mỗi agent PHẢI đọc tài liệu theo thứ tự sau trước khi viết round artifact:

    1. `AGENTS.md` (nếu chưa có trong context).
    2. `docs/online_vs_offline.md` — **BẮT BUỘC** per AGENTS.md.
       Áp dụng sai online patterns vào offline design là lỗi nghiêm trọng nhất
       mà agent có thể mắc trong x38.
    3. `x38_RULES.md` — §1 mục tiêu, §4 authority, §5 participants, §6 debate rules.
    4. `debate/rules.md` — toàn bộ quy tắc tranh luận bao gồm steel-man (§7).
    5. `debate/prompt_template.md` — mẫu vòng (Prompt A/B/C).
    6. `debate/{TOPIC_DIR}/`:
       - `final-resolution.md` → nếu tồn tại, áp dụng closed-topic check theo mode
       - `findings-under-review.md`
       - `README.md`
       - `input_*.md` (nếu có — read-only reference, không phải authority)
    7. Artifact của bên kia (nếu đang phản biện — Prompt B).
    8. Round files gần nhất trong topic dir (chống lặp, đảm bảo liên tục).
       Mode C: đọc TẤT CẢ round files cần thiết cho closure.
       (KHÔNG dùng `debate-index.md` — nó chỉ mục topics, không phải rounds.)
    9. Evidence files liên quan đến scope từ bảng `x38_RULES.md` §7.
       Chỉ mở rộng phạm vi đọc khi scope issue thật sự yêu cầu.

---

## Mẫu bảng trạng thái

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-01 | Campaign model vs flat sessions | Judgment call | Open | — | — |
| X38-D-02 | Typed lesson schema | Thiếu sót | Converged | Whitelist quá strict, reject valid lesson | Sai, vì false negative (leak qua) nguy hiểm hơn false positive |
