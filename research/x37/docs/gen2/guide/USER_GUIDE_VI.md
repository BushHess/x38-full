# Hướng dẫn sử dụng Research Operating Kit v2

Tài liệu này giải thích cách dùng bộ kit bằng tiếng Việt.  
Mục tiêu là dùng đúng quy trình, tránh quá tải ngữ cảnh, tránh nhiễm bẩn đầu vào, và giữ cho mỗi phiên chat chỉ làm đúng một việc.

## 1. Tư duy đúng

Đừng nghĩ theo kiểu:
- session 1 = constitution v1
- session 2 = constitution v2
- session 3 = constitution v3
- rồi cứ tối ưu dần trên cùng dữ liệu cho đến khi ra “thuật toán tối nhất”

Cách đó là lặp lại lỗi cũ.

Cách đúng là:
- **constitution đổi rất hiếm**
- **session mở thường xuyên**
- **data mới append mới tạo ra evidence mới**
- **state pack là thứ mang sang session sau**
- **mỗi session chỉ làm một mode**

## 2. Bộ kit này dùng cho domain nào

Bộ kit này cố ý giới hạn domain:
- Binance Spot
- BTCUSDT
- dữ liệu: OHLCV + quote_volume + num_trades + taker_buy_*
- timeframe: 15m, 1h, 4h, 1d

Nó **không** cho mainline:
- funding
- open interest
- basis
- long/short ratio
- liquidation feed
- order book depth
- tick/aggTrade microstructure
- options
- cross-asset features

Lý do không phải vì chúng vô dụng tuyệt đối, mà vì mainline hiện tại phải hẹp và causal trước. Nếu sau này cần mở domain, đó là chuyện của governance review và major constitution mới.

## 3. Có mấy loại phiên chat

Có 4 loại, nhưng chỉ 3 loại tạo lineage.

### A. Seed discovery
Dùng **một lần duy nhất** trên historical snapshot hiện có.

Mục tiêu:
- tìm 1 champion seed
- tìm tối đa 2 challenger seeds
- freeze candidate
- tạo `state_pack_v1`

Prompt dùng trong **cùng một chat**:
1. `PROMPT_D0_PRECHECK_NEW_SESSION.md` — precheck
2. `PROMPT_D1a_DATA_INGESTION.md` — ingest + quality check
3. `PROMPT_D1b_MEASUREMENT.md` — feature measurement + signal analysis
4. `PROMPT_D1c_CANDIDATE_DESIGN.md` — design candidates + config matrix
5. `PROMPT_D1d_WALK_FORWARD.md` — walk-forward evaluation (14 folds, có thể gửi lại nếu timeout)
6. `PROMPT_D1e_HOLDOUT_RANKING.md` — holdout + reserve + ranking
7. `PROMPT_D1f_FREEZE_DRAFT.md` — freeze champion/challengers + draft output files
8. `PROMPT_D2_PACKAGE_STATE.md` — package state_pack_v1

Sau khi package xong thì **dừng chat**.

### B. Forward evaluation
Đây là loại phiên chat sẽ dùng lặp lại nhiều nhất.

Mục tiêu:
- đánh giá champion + challengers trên **data mới append**
- quyết định:
  - giữ champion
  - promote challenger
  - kill challenger
  - downgrade label
  - escalate governance concern

Prompt dùng trong **cùng một chat**:
1. `PROMPT_F0_PRECHECK_NEW_SESSION.md`
2. `PROMPT_F1_FORWARD_EVALUATION.md`
3. `PROMPT_F2_PACKAGE_STATE.md`

Sau khi package xong thì **dừng chat**.

### C. Governance review
Dùng hiếm.

Mục tiêu:
- xem hiến pháp có còn phù hợp không
- có cần major constitution mới không

Prompt dùng trong **cùng một chat**:
1. `PROMPT_G0_PRECHECK_NEW_SESSION.md`
2. `PROMPT_G1_GOVERNANCE_REVIEW.md`
3. `PROMPT_G2_RELEASE_PACKAGE.md`

### D. Discussion-only chat
Đây là chat để nói chuyện, tranh luận, học triết lý, bàn ý tưởng.

Nó **không thuộc lineage**:
- không freeze candidate
- không tạo state pack
- không được mang output của nó vào blind seed discovery như evidence

## 4. Tài liệu nào chỉ để người dùng đọc, không nên upload vào chat nghiên cứu

Bình thường **không upload** các file này vào execution chat:
- `README_EN.md`
- `USER_GUIDE_VI.md`
- `KIT_REVIEW_AND_FIXLOG_EN.md`
- `PROMPT_INDEX_EN.md`
- `UPLOAD_MATRIX_EN.md`

Các file này để bạn đọc và vận hành, không phải để AI cần nhìn trong mọi phiên.

## 5. Session 1 phải làm thế nào

### Mục tiêu
Dùng snapshot lịch sử hiện có để tạo đội hình xuất phát:
- 1 champion
- tối đa 2 challengers

### Những gì cần upload
Xem `UPLOAD_MATRIX_EN.md`, nhưng tóm gọn là:
- `research_constitution_v2.0.yaml`
- `FILE_AND_SCHEMA_CONVENTIONS_EN.md`
- raw history:
  - `spot_btcusdt_15m.csv`
  - `spot_btcusdt_1h.csv`
  - `spot_btcusdt_4h.csv`
  - `spot_btcusdt_1d.csv`
- `session_manifest.json`
- optional:
  - `input_hash_manifest.txt`
  - `snapshot_notes.md`

### Những gì tuyệt đối không upload
- state pack cũ
- winner cũ
- báo cáo cũ
- contamination log cũ
- bất kỳ artifact precomputed nào từ lineage khác

### Trình tự chat
Trong **một chat mới duy nhất**:
1. gửi `PROMPT_D0_PRECHECK_NEW_SESSION.md`
2. sau khi D0 ok, gửi lần lượt D1a → D1b → D1c → D1d → D1e → D1f
   - D1a: ingest + quality check
   - D1b: feature measurement + signal analysis
   - D1c: design candidates + config matrix (chưa chạy backtest)
   - D1d: walk-forward evaluation 14 folds (gửi lại nếu timeout)
   - D1e: holdout + reserve + bootstrap + ranking
   - D1f: freeze champion/challengers + draft output files
3. sau khi D1f xong, gửi `PROMPT_D2_PACKAGE_STATE.md`

### Kết quả cần lấy ra
- `state_pack_v1`
- trong đó phải có:
  - `candidate_registry.json`
  - `meta_knowledge_registry.json`
  - `portfolio_state.json`
  - `historical_seed_audit.csv`
  - `forward_evaluation_ledger.csv` (header only)
  - `contamination_map.md`
  - `frozen_system_specs/`

### Rất quan trọng
Sau khi đã có `state_pack_v1`, **không được mở lại seed discovery trên cùng snapshot đó nữa**.

## 6. Session 2 trở đi phải làm thế nào

### Điều kiện để mở forward evaluation chat
Bạn chỉ nên mở khi:
- đã có đủ data mới append cho kỳ review chuẩn, hoặc
- có emergency trigger

Mặc định kỳ review chuẩn:
- khoảng mỗi 90 ngày
- tối đa 180 ngày phải review một lần

### Những gì cần upload
- `research_constitution_v2.0.yaml`
- `state_pack_vN` mới nhất
- raw delta mới append
- warmup buffer nếu cần
- `session_manifest.json`
- optional `input_hash_manifest.txt`

### Không upload
- full history cũ nếu không cần làm warmup
- report seed cũ nằm ngoài state pack
- human guide / readme
- governance memo không liên quan

### Trình tự chat
Trong **một chat mới duy nhất**:
1. gửi `PROMPT_F0_PRECHECK_NEW_SESSION.md`
2. sau khi F0 ok, gửi `PROMPT_F1_FORWARD_EVALUATION.md`
3. sau khi F1 xong, gửi `PROMPT_F2_PACKAGE_STATE.md`

### Kết quả cần lấy ra
- `state_pack_vN+1`

### Logic quyết định
Forward evaluation bây giờ có 2 lớp metrics:
- **incremental**: riêng cửa sổ vừa mới append
- **cumulative**: tích lũy kể từ lúc candidate được freeze hoặc last promotion

Quyết định promote / kill / confirm dựa trên **cumulative basis**, không dựa vào một cửa sổ mới nhất đơn lẻ, trừ khi có emergency trigger.

## 7. Vì sao phải có `portfolio_state.json` mạnh hơn trước

Đây là một chỗ rất hay bị làm sai.

Nếu candidate đang:
- có vị thế mở,
- dùng trailing state,
- hoặc có path-dependent exit,

thì session sau phải biết trạng thái đó để tiếp tục mô phỏng đúng.

Vì vậy `portfolio_state.json` phải mang ít nhất:
- `position_state`
- `position_fraction`
- `entry_time_utc`
- `entry_price`
- `trail_state`
- `last_signal_time_utc`
- `reconstructable_from_warmup_only`

Nếu thiếu cái này, forward evaluation session sau có thể tính sai hoàn toàn.

## 8. Khi nào mới mở governance review

Chỉ mở khi có lý do cấp hiến pháp, ví dụ:
- objective hiện tại sai
- hard constraints quá chặt hoặc quá lỏng
- complexity law gây hại có hệ thống
- meta-knowledge policy đang lock-in sai
- forward review law gây churn hoặc delay vô lý
- forward evidence cho thấy charter có bug

Nếu chỉ là một candidate đang chạy dở hoặc thua tạm thời, đó **không phải** lý do mở governance review.

## 9. Bao giờ mới tạo constitution mới

Không phải sau mỗi session.

Chỉ khi có thay đổi cấp hiến pháp.  
Ví dụ:
- đổi objective
- đổi admitted data domain
- đổi execution model
- đổi selection law
- đổi complexity law
- đổi paired evaluation semantics

Nếu không có thay đổi kiểu đó, thì **giữ nguyên `research_constitution_v2.0.yaml`**.

## 10. Kỳ vọng đúng

Bộ này không hứa:
- tìm ra thuật toán tối ưu vĩnh viễn
- thắng mọi regime
- xóa bỏ nonstationarity

Bộ này hướng tới:
- chọn champion hợp lý trong domain đã khóa
- đánh giá nó trên data mới thật sự độc lập hơn
- giữ governance ổn định
- giảm tình trạng “mỗi session lại đổi luật chơi”

## 11. Checklist nhanh trước mỗi execution chat

### Trước seed discovery
- [ ] chat mới hoàn toàn
- [ ] không upload winner cũ / report cũ
- [ ] đúng raw history snapshot
- [ ] có `session_manifest.json`
- [ ] có constitution hiện hành

### Trước forward evaluation
- [ ] chat mới hoàn toàn
- [ ] có latest `state_pack_vN`
- [ ] có delta mới append
- [ ] có warmup nếu cần
- [ ] không mang theo tài liệu thừa

### Trước governance review
- [ ] chat mới hoàn toàn
- [ ] có latest state pack
- [ ] có forward ledger cập nhật
- [ ] có governance failure dossier
- [ ] không biến nó thành discovery trá hình

## 12. Câu ngắn nhất để nhớ

**Session mới thường mang theo state pack mới và data mới. Không phải constitution mới.**

**Historical snapshot chỉ để freeze đội hình xuất phát. Forward truth chỉ đến từ data append mới.**
