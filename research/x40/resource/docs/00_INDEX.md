# X40 Operational Documentation Pack v1

## Mục đích

Bộ tài liệu này là **lớp vận hành sau-spec** cho `X40_Baseline_Forge_Durability_Residual_Spec_v3.md`.

Spec v3 trả lời câu hỏi **phải xây cái gì**.  
Bộ này trả lời câu hỏi **sau khi code dựng xong thì chạy cái gì trước, ai làm gì, khi nào dừng, khi nào rẽ nhánh, khi nào mở x39, khi nào phải mở x37, khi nào phải pivot league dữ liệu**.

## Authority order

Khi có xung đột, dùng thứ tự authority sau:

1. `00_REFERENCE_X40_Spec_v3.md`  
   Authority cao nhất trong pack này cho kiến trúc, namespace, study definitions A00–A07, baseline levels, durability statuses, artifact contracts.
2. `01_POST_IMPLEMENTATION_MASTER_RUNBOOK.md`  
   Authority cho trình tự vận hành sau khi code x40 đã dựng xong.
3. `02_FIRST_CYCLE_EXECUTION_CHECKLIST.md`  
   Checklist cực cụ thể cho vòng chạy đầu tiên.
4. `03_NEXT_ACTION_DECISION_TREE.md`  
   Decision logic để ép hệ thống ra kết luận hành động tiếp theo.
5. `04_X39_RESIDUAL_SPRINT_PLAYBOOK.md`  
   Playbook cho feature invention / residual challenge sau khi baseline đủ điều kiện.
6. `05_X37_BLANK_SLATE_CHALLENGE_PLAYBOOK.md`  
   Playbook mở discovery session mới từ gốc trắng.
7. `06_X40_MONTHLY_QUARTERLY_OPERATIONS_MANUAL.md`  
   Sổ tay vận hành định kỳ sau khi vòng đầu đã xong.
8. `07_ARTIFACTS_AND_TEMPLATES.md` + thư mục `templates/`  
   Mẫu file, schema thực dụng, checklist điền tay.
9. `08_SOURCE_BASIS_AND_ASSUMPTIONS.md`  
   Nơi phân biệt rõ cái nào là fact từ repo, cái nào là policy choice của x40.

## Bộ tài liệu này KHÔNG làm gì

- Không thay thế `decision_policy.md` của production validation.
- Không tự cho phép deploy.
- Không tự cho phép live self-retune.
- Không biến x39 thành nơi ra verdict authoritative.
- Không biến x38 thành invention engine.
- Không hứa tìm global optimum.

## Vòng lặp chuẩn

```text
build x40 code
  -> A00 source parity
  -> BQC-v1 qualification
  -> A01/A02/A03/A05 durability suite
  -> next_action
      -> x39 residual sprint
      -> hoặc x37 blank-slate challenge
      -> hoặc pivot richer-data
  -> forward evidence loop
  -> production validation
  -> x38 downstream consumption
```

## Đọc theo thứ tự nào

### Nếu bạn là research lead
Đọc:
1. `00_REFERENCE_X40_Spec_v3.md`
2. `01_POST_IMPLEMENTATION_MASTER_RUNBOOK.md`
3. `03_NEXT_ACTION_DECISION_TREE.md`
4. `08_SOURCE_BASIS_AND_ASSUMPTIONS.md`

### Nếu bạn là x40 operator
Đọc:
1. `01_POST_IMPLEMENTATION_MASTER_RUNBOOK.md`
2. `02_FIRST_CYCLE_EXECUTION_CHECKLIST.md`
3. `06_X40_MONTHLY_QUARTERLY_OPERATIONS_MANUAL.md`
4. `07_ARTIFACTS_AND_TEMPLATES.md`

### Nếu bạn là x39 sprint owner
Đọc:
1. `04_X39_RESIDUAL_SPRINT_PLAYBOOK.md`
2. `03_NEXT_ACTION_DECISION_TREE.md`
3. `07_ARTIFACTS_AND_TEMPLATES.md`

### Nếu bạn là x37 session owner
Đọc:
1. `05_X37_BLANK_SLATE_CHALLENGE_PLAYBOOK.md`
2. `03_NEXT_ACTION_DECISION_TREE.md`
3. `07_ARTIFACTS_AND_TEMPLATES.md`

## Thành phần chính của pack

- `00_REFERENCE_X40_Spec_v3.md` — bản copy spec v3 để pack tự chứa đầy đủ.
- `01_POST_IMPLEMENTATION_MASTER_RUNBOOK.md` — runbook đầy đủ từ lúc code x40 vừa dựng xong.
- `02_FIRST_CYCLE_EXECUTION_CHECKLIST.md` — checklist chi tiết cho vòng chạy đầu tiên.
- `03_NEXT_ACTION_DECISION_TREE.md` — luật ra quyết định sau vòng audit đầu tiên.
- `04_X39_RESIDUAL_SPRINT_PLAYBOOK.md` — cách làm residual research đúng, không trượt thành formula screening.
- `05_X37_BLANK_SLATE_CHALLENGE_PLAYBOOK.md` — khi nào và cách nào mở session x37 mới.
- `06_X40_MONTHLY_QUARTERLY_OPERATIONS_MANUAL.md` — vận hành định kỳ, canary, requalification, B2 progression.
- `07_ARTIFACTS_AND_TEMPLATES.md` — cấu trúc artifacts và templates.
- `08_SOURCE_BASIS_AND_ASSUMPTIONS.md` — source basis và policy assumptions.

## Kết quả cuối cùng mà bộ tài liệu này hướng tới

Sau khi làm xong hết, bạn phải có được 3 thứ:

1. **Một câu trả lời audit được** cho câu hỏi  
   “Baseline hiện tại còn sống, đang watch, đang decay, hay đã broken?”

2. **Một quyết định nhánh rõ ràng**  
   - tiếp tục same-league residual search, hoặc
   - shift sang exit-focused research, hoặc
   - pivot sang richer-data league.

3. **Một vòng bằng chứng đi tới tương lai**  
   nghĩa là baseline không còn chỉ là winner trong cùng historical archive, mà đã có `forward_evaluation_ledger.csv` và con đường lên `B2_CLEAN_CONFIRMED`.

## Ghi chú quan trọng

Bộ tài liệu này cố tình phân biệt rất chặt:

- **baseline qualification** != **production promotion**
- **residual invention** != **blank-slate discovery**
- **public-flow** != **OHLCV-only**
- **same-file historical evidence** != **clean appended evidence**
