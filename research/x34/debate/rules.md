# QUY TẮC TRANH LUẬN
Tranh luận khoa học để tìm đáp án đúng nhất, không phải đồng thuận.

## Nguyên tắc cốt lõi

1. Không tìm đồng thuận; tìm đáp án đúng nhất theo bằng chứng.
2. Mỗi điểm phải có cơ sở: trích dẫn literature, bằng chứng thực nghiệm
   từ project, hoặc lập luận toán học. "Tôi nghĩ" hay "thường thì" không đủ.
   Mọi claim thực nghiệm phải kèm evidence pointer có thể kiểm chứng
   (đường dẫn file, dòng cụ thể, hoặc lệnh tái tạo).
3. Mỗi issue phải được gán đúng một `classification`:
   - `Sai khoa học`: vi phạm nguyên tắc thống kê/ML đã established. Phải sửa.
   - `Thiếu sót`: bỏ qua kỹ thuật, caveat, hoặc kiểm tra cần thiết. Nên bổ sung.
   - `Judgment call`: cả hai phía có lý. Phải ghi rõ tradeoff và ai quyết định.
4. Phản biện tấn công argument, không phải kết luận. Nếu đồng ý kết luận
   nhưng lý do sai, vẫn phải phản bác lý do.
5. Nghĩa vụ chứng minh thuộc bên đề xuất thay đổi. Văn bản hiện hành giữ
   nguyên trừ khi bên phản biện chứng minh nó sai hoặc thiếu.
6. Thứ bậc bằng chứng khi xung đột:
   - Bằng chứng toán học (proof) > thực nghiệm (empirical) > lý thuyết chung
   - Kết quả từ project này > kết quả domain khác (context-specific wins)
   - Peer-reviewed literature > blog / kinh nghiệm cá nhân

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
   Nếu muốn ghi chú lý do hội tụ, dùng cột riêng hoặc ghi trong round file,
   KHÔNG gộp vào giá trị `current_status` (ví dụ: KHÔNG viết
   `Converged sau khi sửa wording`).
   Nếu nghi ngờ hội tụ giả, bên kia có quyền challenge:
   `Hãy steel-man vị trí cũ của bạn trước khi chấp nhận.`
10. Không có điểm nhỏ. Nếu đáng nêu ra, đáng tranh luận đúng cách.
    Nếu thật sự không quan trọng, xóa khỏi danh sách thay vì chấp nhận
    cho xong.

## Quy trình

11. Mỗi round file phải kết thúc bằng bảng trạng thái theo mẫu bên dưới.
12. Không mở `topic` mới sau vòng 1 trong cùng phiên tranh luận.
    Được phép thêm `issue` mới trong cùng topic nếu và chỉ nếu:
    - nó là `Thiếu sót` hoặc `Sai khoa học` rút ra từ cùng evidence base,
      hoặc là hệ quả trực tiếp của issue đang mở
    - nó được ghi vào `findings-under-review.md` trước khi tranh luận sâu
    - nó không mở rộng scope của topic hiện tại sang một câu hỏi khác
    Nếu không thỏa cả ba điều kiện trên, phải mở topic hoặc phiên riêng.
13. Mặc định `max_rounds_per_topic = 6`, trừ khi topic đó ghi rõ khác ở
    dossier gốc.
14. Sau `max_rounds_per_topic`, mọi issue còn `Open` phải chuyển thành
    `Judgment call`, kèm tradeoff rõ ràng và artifact mới nhất.
15. Nếu chưa chỉ định khác, `decision_owner` mặc định là người duy trì
    dossier hiện hành của topic. `Judgment call` phải nêu rõ người này là ai.
16. Nếu `decision_owner` đồng thời là bên tranh luận, phần judgment phải
    ghi rõ: (a) vị trí mà họ đã bảo vệ trong cuộc tranh luận, và (b) lý do
    cụ thể tại sao judgment không bị thiên lệch bởi vị trí đó. Bên kia có
    quyền challenge nếu cho rằng judgment chỉ là vị trí cũ được reframe.

## Cấu trúc debate

Mỗi topic tranh luận nằm trong thư mục riêng theo quy tắc đặt tên bên dưới:

```text
debate/
  README.md
  rules.md
  debate-index.md
  prompt_template.md

  NNN-slug/                    # mỗi topic một thư mục
    README.md
    findings-under-review.md
    final-resolution.md        # tạo khi mọi issue đã Converged hoặc Judgment call
    codex/YYYY-MM-DD/round-N_[message-type].md
    claude_code/YYYY-MM-DD/round-N_[message-type].md
    issues/                    # optional, chỉ tạo khi số issue quá lớn
```

### Quy tắc đặt tên topic slug

Format: `NNN-<mô-tả-ngắn>`

- `NNN` — số thứ tự 3 chữ số, zero-padded (`001`, `002`, ...). Đảm bảo `ls`
  luôn hiển thị đúng thứ tự thời gian.
- `<mô-tả-ngắn>` — kebab-case, 2-5 từ, mô tả nội dung đợt tranh luận. Giúp
  nhận diện nhanh mà không cần mở file.

Quy tắc bổ sung:
- Không tái sử dụng số đã dùng (kể cả topic bị hủy).
- Slug không chứa topic ID (topic ID ghi trong file, không ghi trong tên thư
  mục — tránh dài dòng).

## Debate index

`debate-index.md` là chỉ mục toàn cục cho các topic đang được tranh luận
trong `debate/`.

Mỗi entry trong `debate-index.md` phải có tối thiểu:
- `topic_id`
- `topic`
- `opened_at`
- `current_status`
- `primary_dossier`
- `latest_artifact`

`debate-index.md` không chứa toàn bộ nội dung issue; nó chỉ giúp trả lời:
"Hiện có những topic nào, trạng thái của chúng ra sao, và nên mở file nào trước?"

## Findings under review

Mỗi chủ đề đang tranh luận phải có một file gốc làm nguồn tham chiếu cho danh sách
các nhận định đang bị tranh luận:

`findings-under-review.md`

Mục đích:
- giữ danh sách claim / omission ban đầu và wording gốc, tránh drift qua nhiều vòng
- cấp `issue_id` ổn định để truy vết về sau
- tách `danh sách điểm đang tranh luận` khỏi `round files`
- làm nguồn tham chiếu chuẩn cho phần tranh luận theo vòng

Quy tắc:
- Mỗi issue phải có `issue_id` ổn định; không đổi ID chỉ vì reorder hoặc đổi wording
- Mỗi issue phải có ít nhất:
  - `opened_at`
  - `opened_in_round`
  - `initial_claim` hoặc `initial_omission`
  - `classification`
  - `current_status`
  - `latest_artifact`
- Với file mới hoặc file đang được cập nhật, `current_status` chỉ dùng một trong ba giá trị:
  - `Open`
  - `Converged`
  - `Judgment call`
- KHÔNG gộp bất kỳ thông tin nào khác vào `current_status`. Ví dụ các giá trị
  SAI: `Open, low priority`, `Converged sau khi sửa wording`,
  `Hội tụ thật sau khi sửa câu overlap`. Nếu cần ghi chú, dùng field riêng.
- Nếu cần thể hiện mức ưu tiên, dùng field riêng như `priority: high|normal|low`;
  không gộp priority vào `current_status`
- Khi issue hội tụ hoặc chuyển thành judgment call, không xóa khỏi file; chỉ cập
  nhật trạng thái và link đến artifact mới nhất
- Các file theo vòng mới hoặc được sửa lại phải tham chiếu `issue_id` tương ứng
  thay vì mô tả mơ hồ như
  `Điểm 1`, `Item 3` đứng một mình
- Nếu `debate/` phát triển quá lớn, có thể tách thêm `issues/[issue_id]_[slug].md`
  nhưng `findings-under-review.md` vẫn phải giữ bảng chỉ mục ngắn gọn
- Nếu có phát hiện mới được chấp nhận là “thiếu sót trong danh sách hiện tại”, vẫn
  phải thêm vào `findings-under-review.md` trước khi tiếp tục tranh luận sâu
- `latest_artifact` phải trỏ tới artifact đang chứa lập luận mạnh nhất hoặc trạng thái
  mới nhất của issue đó
- Với artifact cũ chưa theo schema này, chuẩn hóa dần khi file được chạm tới lần kế tiếp

## Quy tắc đặt tên tệp phản biện

Mọi tệp chứa nội dung phản biện của từng tác nhân phải được lưu theo cấu trúc:

`NNN-slug/[thu_muc_tac_nhan]/YYYY-MM-DD/round-N_[message-type].md`

Quy ước:
- `[thu_muc_tac_nhan]`: thư mục ổn định của tác nhân phản biện, ví dụ:
  - `codex`
  - `claude_code`
- `YYYY-MM-DD`: ngày tạo tệp theo UTC; dùng làm thư mục thay vì nhét vào tên file
- `N`: số vòng phản biện, ví dụ `1`, `2`, `3`
- `[message-type]`: loại lượt trong phiên tranh luận. Không cố định là
  `reviewer-reply`; phải phản ánh đúng vai trò của chính nội dung trong vòng đó.
  Nên dùng một tập tên ổn định, ví dụ:
  - `opening-critique`
  - `reviewer-reply`
  - `author-reply`
  - `rebuttal`
  - `judgment-call`
  - `final-status`

Ví dụ:
- `001-x34-findings/codex/2026-03-13/round-3_reviewer-reply.md`
- `001-x34-findings/claude_code/2026-03-13/round-3_author-reply.md`
- `002-entry-filter-validity/codex/2026-03-14/round-4_judgment-call.md`

## Mẫu bảng trạng thái

Mỗi hàng trong bảng phải map 1:1 với một `issue_id` ổn định từ
`findings-under-review.md`. KHÔNG dùng số thứ tự (`#`, `1`, `2`) thay cho
`issue_id` — số thứ tự có thể thay đổi khi thêm/xóa issue, còn `issue_id`
thì không.

Cột `Steel-man` và `Lý do bác bỏ` chỉ bắt buộc khi `Trạng thái = Converged`.
Với `Open`, để `—`. Với `Judgment call`, cột cuối ghi tradeoff thay vì lý do
bác bỏ.

| Issue ID | Điểm | Phân loại | Trạng thái | Priority | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|---|
| X34-D-01 | ESS gate thiếu EPV | Sai khoa học | Converged | high | ESS >= 50 đủ vì penalized model co features | Sai, vì ESS không capture class imbalance; EPV là ràng buộc riêng |
| X34-D-02 | ROC vs PR-AUC | Thiếu sót | Open | normal | — | — |
| X34-D-03 | Timing hard gate | Judgment call | Judgment call | normal | — | Tradeoff: hard gate an toàn hơn, diagnostic linh hoạt hơn |
