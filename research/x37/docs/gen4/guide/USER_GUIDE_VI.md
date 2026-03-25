# Hướng dẫn sử dụng Research Operating Kit v4 (Versioned Systems)

Tài liệu này giải thích cách dùng bộ kit bằng tiếng Việt.
Mục tiêu là dùng đúng quy trình, tránh quá tải ngữ cảnh, tránh nhiễm bẩn đầu vào, và giữ cho mỗi phiên chat chỉ làm đúng một việc.

## 1. Thay đổi chính từ v3 sang v4

v4 giữ nguyên mọi thứ tốt của v3 (search space mở, contamination firewall, state pack handoff) và thêm ba thay đổi cốt lõi:

1. **Đơn vị evidence là `system_version_id`, không phải lineage.**
   v3 coi cả lineage như một đối tượng duy nhất. v4 tách ba trục:
   - `constitution_version`: luật chơi (charter này)
   - `program_lineage_id`: chương trình nghiên cứu (chuỗi version cùng mục tiêu)
   - `system_version_id`: thuật toán cụ thể đã freeze — đây là đơn vị kiếm OOS evidence

2. **Exploration là contaminated — rõ ràng.**
   Sandbox tự do nhưng không kiếm OOS credit.

3. **Redesign reset evidence clock.**
   Nếu dùng forward window để quyết định thay đổi gì, window đó không còn OOS cho version mới.

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

Có 6 loại, chia thành 2 nhóm:

### Sandbox (không thuộc lineage)

#### S1. Exploration
- Thử nghiệm tự do trên mọi data
- Không có OOS claim
- Không tạo state pack
- Kết quả là hypothesis, không phải evidence

#### S2. Discussion
- Tranh luận, triết lý, postmortem, học
- Không freeze candidate
- Không tạo state pack

### Mainline (version lineage)

#### M1. Seed discovery
Dùng **một lần duy nhất** trên historical snapshot.

Prompt chain: `D0 → D1a..D1f3 → D2`

Mục tiêu:
- tìm 1 champion seed + tối đa 2 challengers
- freeze candidate → tạo `system_version_id`
- tạo `state_pack_v1`

#### M2. Forward evaluation
Đây là loại chat lặp lại nhiều nhất.

Prompt chain: `F0 → F1 → F2`

Mục tiêu:
- đánh giá frozen candidates trên **data mới append**
- quyết định: giữ / promote / kill / downgrade / escalate
- **KHÔNG BAO GIỜ** trigger redesign trong chat này

#### M3. Redesign freeze
Dùng khi forward evidence cho thấy cần thay đổi thuật toán.

Prompt chain: `R0 → R1 → R2`

**Điều kiện bắt buộc (tất cả phải đúng):**
- Có redesign trigger hợp lệ (consecutive failure / emergency / proven bug / structural deficiency)
- Cooldown >= 180 ngày từ lần freeze cuối (trừ emergency/bug)
- Evidence >= 180 forward days + >= 6 entries
- Có redesign dossier mô tả đúng một thay đổi chính
- Budget: max 1 logic block, max 3 tunables, max 1 execution change

Kết quả:
- `system_version_id` mới
- Evidence clock reset về zero
- Forward evidence cũ KHÔNG chuyển sang version mới

#### M4. Governance review
Dùng hiếm. Chỉ khi charter có vấn đề.

Prompt chain: `G0 → G1 → G2`

Trước khi mở chat governance, phải tự chuẩn bị `governance_failure_dossier.md`
từ `template/governance_failure_dossier.template.md`. Đây là điều kiện đầu vào,
không phải artifact được tạo bên trong chuỗi prompt G.

## 4. Ma trận tóm tắt

| Mode | Loại | Prompt chain | State pack? | Freeze? |
|---|---|---|---|---|
| Exploration | sandbox | tự do | Không | Không |
| Discussion | sandbox | tự do | Không | Không |
| Seed discovery | mainline | `D0 → D1a..D1f3 → D2` | Có | Có (version mới) |
| Forward evaluation | mainline | `F0 → F1 → F2` | Có | Không |
| Redesign freeze | mainline | `R0 → R1 → R2` | Có | Có (version mới) |
| Governance review | mainline | `G0 → G1 → G2` | Không (chỉ governance package) | Không |

## 5. Tài liệu nào chỉ để người dùng đọc, không nên upload vào chat nghiên cứu

Bình thường **không upload** các file này vào execution chat:
- `README_EN.md`
- `USER_GUIDE_VI.md`
- `KIT_REVIEW_AND_FIXLOG_EN.md`
- `PROMPT_INDEX_EN.md`
- `UPLOAD_MATRIX_EN.md`

Các file này để bạn đọc và vận hành, không phải để AI cần nhìn trong mọi phiên.

## 6. Session 1: Seed discovery

### Mục tiêu
Dùng snapshot lịch sử hiện có để tạo đội hình xuất phát:
- 1 champion
- tối đa 2 challengers

### Những gì cần upload
Xem `UPLOAD_MATRIX_EN.md`, nhưng tóm gọn là:
- `research_constitution_v4.0.yaml`
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
2. sau khi D0 ok, gửi lần lượt:
   - D1a: ingest + quality check
   - D1b1 → D1b2 → D1b3 → D1b4: đo lường kênh (gửi lại nếu timeout)
   - D1c: design candidates + config matrix (chưa chạy backtest)
   - D1d1 → D1d2 → D1d3: implement, WFO batch (gửi lại nếu timeout), tổng hợp
   - D1e1 → D1e2 → D1e3: filter, holdout/reserve, bootstrap + ranking
   - D1f1 → D1f2 → D1f3: freeze + specs, registry + state, audit + ledger + map
3. sau khi D1f3 xong, gửi `PROMPT_D2_PACKAGE_STATE.md`

### Kết quả cần lấy ra
- `state_pack_v1`
- trong đó phải có:
  - `research_constitution_version.txt`
  - `program_lineage_id.txt`
  - `system_version_id.txt`
  - `system_version_manifest.json`
  - `candidate_registry.json`
  - `meta_knowledge_registry.json`
  - `portfolio_state.json`
  - `historical_seed_audit.csv`
  - `forward_daily_returns.csv` (header only)
  - `forward_evaluation_ledger.csv` (header only)
  - `contamination_map.md`
  - `input_hash_manifest.txt`
  - `frozen_system_specs/`
  - `impl/` (implementation code per candidate — dùng cho F1 reproduction check, tránh re-implementation drift)

### Rất quan trọng
Sau khi đã có `state_pack_v1`, **không được mở lại seed discovery trên cùng snapshot đó nữa**.

## 7. Session 2 trở đi: Forward evaluation

### Điều kiện để mở forward evaluation chat
Bạn chỉ nên mở khi:
- đã có đủ data mới append cho kỳ review chuẩn, hoặc
- có emergency trigger

Mặc định kỳ review chuẩn:
- khoảng mỗi 90 ngày
- tối đa 180 ngày phải review một lần

### Những gì cần upload
- `research_constitution_v4.0.yaml`
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
- redesign dossier (forward evaluation KHÔNG trigger redesign)

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
- **cumulative**: tích lũy kể từ `cumulative_anchor_utc` của candidate

Quyết định promote / kill / confirm dựa trên **cumulative basis**, không dựa vào một cửa sổ mới nhất đơn lẻ, trừ khi có emergency trigger.

**Lưu ý về hai scope cumulative:**
- Label `FORWARD_CONFIRMED` yêu cầu 180 ngày + 6 entries kể từ `freeze_cutoff_utc` (scope version)
- Ranking và quyết định promote/kill dùng metrics kể từ `cumulative_anchor_utc` (scope candidate, reset khi promote)

## 8. Redesign cycle

### Khi nào được redesign
Chỉ khi **tất cả** điều kiện sau đều đúng:
1. Có trigger hợp lệ (consecutive failure / emergency / proven bug / structural deficiency)
2. Cooldown >= 180 ngày từ lần freeze cuối
3. Evidence >= 180 forward days + >= 6 entries
4. Có redesign dossier chuẩn bị sẵn

### Quy trình
1. **Exploration** (sandbox): thử nghiệm tự do. Không tạo state pack.
2. **Redesign freeze** (mainline): chat mới, upload theo `UPLOAD_MATRIX_EN.md` cho redesign_freeze.
   - Gửi `PROMPT_R0_PRECHECK_NEW_SESSION.md`
   - Sau khi R0 ok, gửi `PROMPT_R1_REDESIGN_EXECUTION.md`
   - Sau khi R1 xong, gửi `PROMPT_R2_PACKAGE_STATE.md`
3. **Forward evaluation**: chờ data mới sau `freeze_cutoff_utc`, mở forward evaluation cho version mới.

### Rất quan trọng
- Evidence clock reset về zero cho version mới
- Forward evidence cũ KHÔNG chuyển sang version mới
- Tất cả data đã dùng để redesign = seen data cho version mới
- Max 1 major redesign per 180 ngày

## 9. Vì sao phải có `portfolio_state.json` mạnh

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

## 10. Khi nào mới mở governance review

Chỉ mở khi có lý do cấp hiến pháp, ví dụ:
- objective hiện tại sai
- hard constraints quá chặt hoặc quá lỏng
- complexity law gây hại có hệ thống
- meta-knowledge policy đang lock-in sai
- forward review law gây churn hoặc delay vô lý
- forward evidence cho thấy charter có bug

Nếu chỉ là một candidate đang chạy dở hoặc thua tạm thời, đó **không phải** lý do mở governance review.

## 11. Bao giờ mới tạo constitution mới

Không phải sau mỗi session.

Chỉ khi có thay đổi cấp hiến pháp.
Ví dụ:
- đổi objective
- đổi admitted data domain
- đổi execution model
- đổi selection law
- đổi complexity law
- đổi paired evaluation semantics

Nếu không có thay đổi kiểu đó, thì **giữ nguyên `research_constitution_v4.0.yaml`**.

## 12. Kỳ vọng đúng

Bộ này không hứa:
- tìm ra thuật toán tối ưu vĩnh viễn
- thắng mọi regime
- xóa bỏ nonstationarity

Bộ này hướng tới:
- chọn champion hợp lý trong domain đã khóa
- đánh giá nó trên data mới thật sự độc lập hơn
- giữ governance ổn định
- giảm tình trạng "mỗi session lại đổi luật chơi"
- **redesign có cửa sổ, có trigger, có dossier** — không phải muốn đổi lúc nào cũng được

## 13. Checklist nhanh trước mỗi execution chat

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
- [ ] không mang redesign dossier

### Trước redesign freeze
- [ ] chat mới hoàn toàn
- [ ] có latest `state_pack_vN`
- [ ] có full data (historical + appended)
- [ ] có `redesign_dossier.md` đã chuẩn bị
- [ ] có `session_manifest.json` với `mode: "redesign_freeze"`
- [ ] cooldown >= 180 ngày
- [ ] evidence >= 180 forward days + >= 6 entries

### Trước governance review
- [ ] chat mới hoàn toàn
- [ ] có latest state pack
- [ ] có forward ledger cập nhật
- [ ] có governance failure dossier
- [ ] không biến nó thành discovery trá hình

## 14. Câu ngắn nhất để nhớ

**Session mới thường mang theo state pack mới và data mới. Không phải constitution mới.**

**Historical snapshot chỉ để freeze đội hình xuất phát. Forward truth chỉ đến từ data append mới.**

**Redesign là phẫu thuật — cần trigger, cooldown, dossier, và evidence clock reset.**
