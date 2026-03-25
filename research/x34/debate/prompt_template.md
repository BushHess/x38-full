## Prompt A — Mở phiên

Gửi cho bên mở đầu. Sửa round number nếu không phải round 1.
Thay `{TOPIC_DIR}` bằng thư mục topic thực tế (vd: `001-x34-findings`).

```
ROUND 1 — Mở phiên

- Bối cảnh: Chúng ta vừa trải qua đợt nghiên cứu sâu về thuật toán Q-VDO-RH.
  Trong quá trình nghiên cứu có một số phát hiện thú vị và có giá trị khoa học
  cao. Chúng ta cần rà soát lại những phát hiện này để đảm bảo rằng chúng ta
  đã liệt kê đầy đủ, hiểu đúng và có thể áp dụng chúng một cách hiệu quả.

- Thư mục làm việc: /var/www/trading-bots/btc-spot-dev/research/x34/
- Danh sách các phát hiện: /var/www/trading-bots/btc-spot-dev/research/x34/debate/{TOPIC_DIR}/findings-under-review.md
- Quy tắc tranh luận: /var/www/trading-bots/btc-spot-dev/research/x34/debate/rules.md
- Chỉ mục topic: /var/www/trading-bots/btc-spot-dev/research/x34/debate/debate-index.md

Các bên tranh luận: Claude Code ↔ Codex

Nhiệm vụ:
1. Đọc rules.md, findings-under-review.md, và debate-index.md.
2. Với mỗi issue có review_status = Open, đưa ra critique kèm:
   - classification (Sai khoa học / Thiếu sót / Judgment call)
   - evidence pointer cụ thể (file path, dòng, hoặc lệnh tái tạo)
   - lập luận tấn công argument, không phải kết luận
3. Kết thúc bằng bảng trạng thái theo mẫu trong rules.md §11.

Sau khi bạn nêu ý kiến, tôi sẽ chuyển cho bên kia phản biện. Vòng lặp tiếp
diễn cho đến khi mọi issue đều Converged hoặc Judgment call.
```

---

## Prompt B — Vòng phản biện tiếp theo

Gửi cho bên nhận phản biện. Sửa round number, `{TOPIC_DIR}`, và đường dẫn
artifact cho khớp vòng hiện tại.

```
ROUND N — Phản biện

- Bối cảnh: Chúng ta vừa trải qua đợt nghiên cứu sâu về thuật toán Q-VDO-RH.
  Trong quá trình nghiên cứu có một số phát hiện thú vị và có giá trị khoa học
  cao. Chúng ta cần rà soát lại những phát hiện này để đảm bảo rằng chúng ta
  đã liệt kê đầy đủ, hiểu đúng và có thể áp dụng chúng một cách hiệu quả.

- Thư mục làm việc: /var/www/trading-bots/btc-spot-dev/research/x34/
- Danh sách các phát hiện: /var/www/trading-bots/btc-spot-dev/research/x34/debate/{TOPIC_DIR}/findings-under-review.md
- Quy tắc tranh luận: /var/www/trading-bots/btc-spot-dev/research/x34/debate/rules.md
- Chỉ mục topic: /var/www/trading-bots/btc-spot-dev/research/x34/debate/debate-index.md

Các bên tranh luận: Claude Code ↔ Codex

- Ý kiến mới nhất của bên kia: /var/www/trading-bots/btc-spot-dev/research/x34/debate/{TOPIC_DIR}/{agent}/YYYY-MM-DD/round-N_[message-type].md

Nhiệm vụ:
1. Đọc artifact trên, đối chiếu với findings-under-review.md và evidence gốc.
2. Phản biện từng issue, kèm evidence pointer cụ thể.
3. Nhắc lại các quy tắc bắt buộc:
   - Tấn công argument, không phải kết luận (§4).
   - Trước khi chấp nhận bất kỳ điểm nào, phải steel-man vị trí cũ theo đúng
     quy trình (a)(b)(c) trong §7. Không hoàn thành = issue vẫn Open.
   - Cấm ngôn ngữ nhượng bộ mềm (§8): phải dùng bằng chứng cụ thể.
   - Không mở topic mới sau round 1 (§12).
4. Kết thúc bằng bảng trạng thái cập nhật (Open / Converged / Judgment call).

Sau khi bạn nêu ý kiến, tôi sẽ chuyển cho bên kia phản biện tiếp. Vòng lặp
tiếp diễn cho đến khi mọi issue đều Converged hoặc Judgment call.
```

---

## Prompt C — Chốt và áp dụng

Dùng khi mọi issue đã Converged hoặc Judgment call (hoặc đạt max rounds).
Sửa `{TOPIC_DIR}` và đường dẫn artifact vòng cuối cho đúng.

```
Chốt — Áp dụng thay đổi

- Bảng trạng thái vòng cuối: /var/www/trading-bots/btc-spot-dev/research/x34/debate/{TOPIC_DIR}/{agent}/YYYY-MM-DD/round-N_[message-type].md
- File cần cập nhật: /var/www/trading-bots/btc-spot-dev/research/x34/debate/{TOPIC_DIR}/findings-under-review.md

Quy tắc áp dụng:

1. HỘI TỤ THẬT (Converged + steel-man đã xác nhận):
   → Áp dụng correction vào findings-under-review.md.
   → Cập nhật review_status = Converged, ghi round đã chốt.

2. JUDGMENT CALL:
   → Ghi cả hai vị trí vào finding:
     NOTE (Judgment call, round N): [tradeoff]
     Lựa chọn: [X] — Lý do: [...]
     Decision owner: [tên]
   → Cập nhật review_status = Judgment call.

3. Issue còn Open, hội tụ giả, hoặc không rõ ràng:
   → KHÔNG áp dụng. Giữ nguyên, ghi chú lý do chưa chốt.

4. Sau khi xong:
   → Cập nhật debate-index.md (current round, status summary).
   → Tạo final-resolution.md trong {TOPIC_DIR}/ nếu mọi issue đã chốt.
```
