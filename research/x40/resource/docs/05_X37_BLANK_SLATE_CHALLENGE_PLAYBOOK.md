# 05 — X37 Blank-Slate Challenge Playbook

## 1. Khi nào phải mở x37

x37 chỉ nên được mở khi vấn đề đã là **câu hỏi cấp kiến trúc**, không còn là residual patching.

Mở x37 nếu có ít nhất một điều kiện:
- baseline active bị `BROKEN` mà không có replacement đủ gần;
- hai x39 sprints liên tiếp chết sạch;
- cần kiểm tra xem family hiện tại có đang khóa mình trong local optimum;
- đang pivot sang league dữ liệu mới;
- `open_x37_challenge = true` trong `next_action`.

Nếu chưa có các điều này, đừng mở x37.

---

## 2. Vai trò của x37

x37 là arena cho:
- discovery from blank slate,
- phase gating,
- protocol freeze,
- champion/challenger emission,
- session isolation.

x37 **không** phải nơi vá nhanh một filter hoặc exit overlay nhỏ.  
Nếu câu hỏi là “thêm một overlay có giúp không?”, đó là việc của x39/x40, không phải x37.

---

## 3. Biến thể session cho baseline forge

x37 mặc định cho phép đọc một số weak priors.  
Nhưng khi dùng để challenge baseline chính thức, khuyến nghị mở profile nghiêm hơn:

## 3.1 Strict baseline-challenge profile
Ở Phase 1–4:
- không đọc benchmark numbers,
- không dùng kết quả selection từ E5 làm direction bias,
- không import strategy logic từ baseline incumbent,
- không ưu tiên architecture incumbent trừ khi Phase 5/6 mới dùng để benchmark.

## 3.2 Vì sao
Mục tiêu là kiểm tra:
- incumbent có thật sự mạnh trong search space mở hay không,
- hay chỉ mạnh vì search bị kéo lệch bởi priors cũ.

---

## 4. Mở session như thế nào

## 4.1 Tạo session ID
Theo x37 rules:
```text
sNN_<short_name>
```

Ví dụ:
```text
s01_baseline_forge_oh0_challenge
```

## 4.2 Cập nhật root registry
Trước khi chạy phase code, phải cập nhật:
- `research/x37/README.md`
- `research/x37/PLAN.md`
- `research/x37/manifest.json`

## 4.3 Tạo tree chuẩn
Session phải có đầy đủ phase tree theo x37 rules.

---

## 5. Phase-by-phase intent

## Phase 0
Freeze protocol:
- admitted data
- windows
- no-lookahead / alignment policy
- complexity caps
- session-specific embargo notes

## Phase 1
Decomposition / measurement.
Không được nhìn benchmark numbers để suppress mechanism.

## Phase 2
Hypotheses.
Viết hypotheses đủ rõ để sau này biết mình đang test concept nào.

## Phase 3
Design.
Sinh candidates theo hypotheses, không được để strategy logic leak vào `shared/` nếu logic đó chỉ có nghĩa cho session này.

## Phase 4
Parameter / family robustness.
Nếu không có broad plateau mà chỉ còn sharp spikes => abandon.

## Phase 5
Freeze.
Checkpoint bất khả đảo ngược.
Một khi `frozen_spec.*` và holdout artifacts đã bị chạm thì không được retune.

## Phase 6
Benchmark.
Lúc này mới head-to-head với incumbent / comparators.

---

## 6. Abandon criteria cần nhớ

Session phải `ABANDONED` nếu:
- no channel above noise floor,
- component ablation giết hết candidate,
- Phase 4 chỉ còn spikes, không plateau,
- candidate duy nhất fail hard criteria,
- muốn tiếp tục thì phải post-hoc rationalize hoặc vi phạm protocol.

Đây là điểm rất quan trọng.  
x37 không tồn tại để cứu bằng được một idea.  
x37 tồn tại để giết idea sai theo cách kỷ luật.

---

## 7. Output session tối thiểu

Một x37 challenge hợp lệ phải trả ra:
- `verdict/verdict.json`
- `verdict/final_report.md`
- frozen champion spec nếu có champion
- benchmark comparison
- phase artifacts đầy đủ theo rules

Ngoài ra, để dùng được cho x40 tiếp theo, challenge winner nên có:
- source pack draft,
- snapshot/window profile rõ,
- artifact list đủ replay.

---

## 8. Handoff từ x37 sang x40

Không có winner nào từ x37 tự động trở thành baseline chính thức.

Handoff chuẩn:
1. x37 phát hành winner/challenger
2. đóng gói source pack
3. x40 chạy A00 parity (nếu cần port)
4. x40 chạy qualification replay
5. x40 gán `B0/B1/B_FAIL`
6. x40 chạy durability suite

Chỉ sau đó winner x37 mới được phép cạnh tranh baseline chính thức.

---

## 9. Khi nào x37 challenge nên là same-league, khi nào nên là new-league

## Same-league x37 challenge
Dùng khi:
- muốn kiểm tra local optimum,
- baseline current league đang đáng nghi nhưng chưa tới mức pivot.

## New-league x37 challenge
Dùng khi:
- A07 đã khuyến nghị pivot,
- hoặc existing league không còn rational để đầu tư.

---

## 10. Không được nhầm x37 với x39

Nếu mục tiêu là:
- tạo concept card,
- test 5–20 variants quanh một idea,
- xem overlay này có giúp không,

thì đó là x39.

Nếu mục tiêu là:
- mở search từ gốc trắng dưới protocol phase-gated,
- challenge cả family incumbent,

thì đó là x37.

---

## 11. Quy tắc một câu

Chỉ mở x37 khi câu hỏi đã là  
“family này còn đúng không?”  
chứ không còn là  
“overlay nào giúp thêm được một chút?”.
