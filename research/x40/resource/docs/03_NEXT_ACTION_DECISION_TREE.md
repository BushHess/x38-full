# 03 — Next-Action Decision Tree

## 1. Mục tiêu

Tài liệu này ép vòng audit đầu tiên phải sinh ra **một hành động tiếp theo duy nhất**.

Không cho phép:
- “tiếp tục nghĩ thêm”
- “vừa residual vừa blank-slate vừa pivot”
- “cứ test thêm một ít rồi tính”

---

## 2. Output contract

`next_action.json` phải có tối thiểu:

```json
{
  "primary_action": "SHIFT_TO_EXIT_FOCUSED",
  "target_league_id": "OHLCV_ONLY",
  "active_baseline_id": "OH0_D1_TREND40",
  "research_focus": "EXIT_FOCUSED",
  "open_x37_challenge": false,
  "pivot_recommended": false,
  "reason_codes": ["A04_EXIT_VALUE", "OH0_WATCH_NOT_BROKEN"]
}
```

## Allowed `primary_action`
- `CONTINUE_SAME_LEAGUE_RESIDUAL`
- `SHIFT_TO_EXIT_FOCUSED`
- `PIVOT_TO_RICHER_DATA`

`open_x37_challenge` là escalation flag, **không** phải primary action.

---

## 3. Inputs

Decision tree dùng:
- baseline level cho `OH0`
- durability status cho `OH0`
- baseline level cho `PF0`
- durability status cho `PF0`
- A01 decay band
- A02 compression flags
- A03 crowding flags
- A04 entry-vs-exit attribution
- A07 league pivot evaluation
- availability của richer-data league

---

## 4. Precedence

Ưu tiên ra quyết định theo thứ tự sau:

1. **Broken / severe decay / severe crowding**
2. **League pivot need**
3. **Exit-vs-entry attribution**
4. **League selection**
5. **Whether to open x37 challenge**

Nghĩa là:
- nếu baseline đã broken, đừng tranh cãi entry vs exit trước;
- nếu cả league đang chết, đừng cố residual local;
- chỉ khi baseline còn sống mới bàn residual direction.

---

## 5. Primary branch logic

## 5.1 Branch 1 — CONTINUE_SAME_LEAGUE_RESIDUAL
Chọn branch này nếu tất cả điều sau đúng:

- có ít nhất một baseline active trong league mục tiêu với:
  - baseline level `B1_QUALIFIED` hoặc `B0_INCUMBENT`
  - durability status != `BROKEN`
- `A07` không yêu cầu pivot
- và A04 **không** cho tín hiệu “exit-first là bắt buộc”

### research_focus trong branch này có thể là:
- `GENERAL_RESIDUAL`
- `ENTRY_FOCUSED`
- `CHARACTERIZATION_ONLY`

`ENTRY_FOCUSED` chỉ được dùng nếu:
- A04 cho thấy entry residuals còn cơ hội thực,
- exit side không phải nơi rõ ràng hơn.

---

## 5.2 Branch 2 — SHIFT_TO_EXIT_FOCUSED
Chọn branch này nếu:
- baseline còn active (`B1` hoặc `B0`, durability != `BROKEN`),
- nhưng A04 cho thấy:
  - entry residuals lặp lại null,
  - exit overlays / path-quality / de-risking cải thiện trade quality,
- và A07 chưa yêu cầu pivot.

### research_focus trong branch này mặc định là:
- `EXIT_FOCUSED`

### Ví dụ các family ưu tiên
- rangepos / path-quality exits
- failed expansion exits
- maturity / exhaustion exits
- anti-vol / de-risking overlays

---

## 5.3 Branch 3 — PIVOT_TO_RICHER_DATA
Chọn branch này nếu:
- official baseline của league hiện tại là `DECAYING` hoặc `BROKEN`,
- crowding stress severe,
- residual challenger yield thấp,
- và richer-data league khả dụng.

Khi branch này được chọn:
- dừng mở residual sprint mới trong league cũ,
- chuyển nguồn lực sang defining richer-data admission,
- cân nhắc bật `open_x37_challenge = true` nếu cần discovery from scratch.

---

## 6. League selection logic

## 6.1 Nếu OH0 sống, PF0 yếu
Kết luận:
- `OHLCV_ONLY` vẫn còn giá trị control/reference,
- `PUBLIC_FLOW` có thể đang crowding hoặc execution-sensitive hơn.

Primary action thường là:
- `CONTINUE_SAME_LEAGUE_RESIDUAL` với `target_league_id = OHLCV_ONLY`, hoặc
- `SHIFT_TO_EXIT_FOCUSED` trong `PUBLIC_FLOW` nếu E5 vẫn practical nhưng yếu dần.

## 6.2 Nếu PF0 sống, OH0 yếu
Kết luận:
- public-flow đang tạo incremental value thực sự,
- OHLCV-only chỉ còn là control baseline.

Primary action thường là:
- `CONTINUE_SAME_LEAGUE_RESIDUAL` với `target_league_id = PUBLIC_FLOW`

## 6.3 Nếu cả hai cùng sống
Kết luận:
- chưa có lý do pivot,
- giữ `OH0` làm control,
- dùng `PF0` làm practical incumbent,
- residual sprint phải chọn league rõ ràng.

## 6.4 Nếu cả hai cùng decay/broken
Kết luận:
- nghi ngờ cấp market/public-data league,
- branch mặc định là `PIVOT_TO_RICHER_DATA`.

---

## 7. Escalation flag — open_x37_challenge

`open_x37_challenge = true` nếu có ít nhất một điều kiện:

1. cả baseline active và residual direction đều mơ hồ ở cấp kiến trúc, không phải chỉ thiếu một overlay;
2. hai residual sprints liên tiếp chết sạch;
3. baseline active bị `BROKEN` mà không có qualified replacement;
4. đang pivot sang league mới cần discovery from scratch;
5. cần challenge family hiện tại bằng blank-slate discovery thay vì vá cục bộ.

### `open_x37_challenge = false` nếu:
- việc còn lại chỉ là exit overlay / residual refinement cùng league,
- baseline active vẫn đủ khỏe để làm reference,
- chưa có lý do nghi ngờ kiến trúc family hiện tại.

---

## 8. Decision table (rút gọn)

| OH0 | PF0 | A04 | A07 | Primary action | Flag |
|---|---|---|---|---|---|
| DURABLE/WATCH | DURABLE/WATCH | entry viable | no pivot | CONTINUE_SAME_LEAGUE_RESIDUAL | false |
| DURABLE/WATCH | DURABLE/WATCH | exit stronger | no pivot | SHIFT_TO_EXIT_FOCUSED | false |
| DURABLE/WATCH | DECAYING/BROKEN | exit stronger in PF0 | no pivot | SHIFT_TO_EXIT_FOCUSED | false |
| BROKEN | DURABLE/WATCH | entry viable in PF0 | no pivot | CONTINUE_SAME_LEAGUE_RESIDUAL | false |
| DECAYING | DECAYING | weak challenger yield | pivot yes | PIVOT_TO_RICHER_DATA | true |
| BROKEN | BROKEN | irrelevant | pivot yes | PIVOT_TO_RICHER_DATA | true |

---

## 9. Không được làm gì sau khi ra next_action

Sau khi `next_action.md` đã ký:
- không mở sprint trái hướng decision tree,
- không chạy thử “cho vui” thêm branch khác,
- không sửa baseline manifest âm thầm để hợp thức hóa branch mới.

Nếu muốn đổi nhánh, phải mở decision revision có lý do và artifact mới.

---

## 10. Quy tắc một câu

Nếu baseline còn sống, tối ưu hướng challenge.  
Nếu baseline đang chết, ưu tiên đo nguyên nhân.  
Nếu cả league đang chết, rời league.  
Nếu câu hỏi đã là câu hỏi kiến trúc, mở x37.
