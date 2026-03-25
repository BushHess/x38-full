# Clean OOS Handoff Prompt — Bản tiếng Việt (tham chiếu)

Đây là bản dịch tham chiếu của prompt handoff clean OOS. Bản chính thức (authoritative) để gửi cho AI là file `PROMPT_FOR_V6_CLEAN_OOS_V2[en].md`.

---

## Bảng tóm tắt các thay đổi so với V1

| Hạng mục | Điểm yếu cũ | Hướng chỉnh sửa |
|---|---|---|
| Phiên bản | Prompt vẫn tham chiếu thế hệ cũ (`V5→V6`, tên contamination log cũ) | Cập nhật theo dòng hiện tại (`V7→V8`, `V3→V4`) |
| Cách đặt bài toán | Prompt cũ xem vòng sau như một session mới chung chung | Định vị lại thành **session clean OOS trong tương lai**, xây trên nền một vòng audit cùng file đã hoàn tất |
| Logic clean OOS | Hàm ý rằng chỉ cần tách dữ liệu là *tự động* thành `CLEAN OOS CONFIRMED` | Sửa lại: tách cấu trúc chỉ làm clean OOS **đủ điều kiện**, không tự động xác nhận |
| Kiến trúc dữ liệu | Dữ liệu cũ + mới có thể bị hiểu quá lỏng | Tách rõ **archive lịch sử** và **reserve tương lai được append** |
| Cách dùng reserve | Câu chữ cũ chưa chặn hẳn chuyện đổi winner sau khi mở reserve | Thêm luật **leader-first clean reserve**; nếu chấm ứng viên khác thì chỉ để chẩn đoán, không dùng để chọn |
| Kiểm soát biên dữ liệu | Quy tắc bắt đầu reserve còn mơ hồ về thao tác | Reserve phải bắt đầu **ngay sau archive end**, được suy ra từ chính các file |
| Đóng gói dữ liệu | Việc gộp file vẫn còn bỏ ngỏ | Quy tắc mặc định: **giữ archive và append tách riêng**, kèm manifest |
| Kiểm soát ô nhiễm | Người dùng có thể vô tình xem trước reserve tương lai | Thêm quy tắc **không preview / không backtest / chỉ kiểm tra integrity** trên append data |
| Hướng dẫn dữ liệu | Có ích nhưng chưa đủ chặt | Bổ sung cấu trúc file, hash/manifest, kiểm tra continuity, overlap/gap, thứ tự upload, và phương án reserve quá ngắn |
| Tính trung thực khoa học | Prompt cũ làm mờ ranh giới giữa "có thể clean OOS" và "đã clean OOS confirmed" | Tách bạch **đủ điều kiện về cấu trúc**, **kết quả reserve thật**, và **trường hợp inconclusive** |

---

## Nội dung prompt (bản dịch tham chiếu)

# PROMPT GỬI CHO SESSION CÙNG-FILE VỪA HOÀN TẤT

> Prompt này chỉ nên được dùng **sau khi** session audit-hội-tụ trên cùng một file hiện tại đã đóng băng xong candidate và hoàn tất toàn bộ output nghiên cứu của nó. Mục tiêu là tạo bộ handoff cho một session trong tương lai, nơi **clean out-of-sample validation trở nên khả thi về mặt cấu trúc nhờ dữ liệu tương lai được append thật sự**.
>
> Trước khi gửi prompt này:
> 1. Chờ cho session hiện tại đóng băng xong candidate và hoàn tất các deliverable của nó.
> 2. Upload contamination log mới nhất từ lần handoff trước (hiện tại là `CONTAMINATION_LOG_V3.md`) cùng với các artifact của session hiện tại cần thiết để cập nhật đầy đủ. Upload ở giai đoạn này là chấp nhận được vì freeze đã hoàn tất.
> 3. **Không** upload contamination log vào session clean-OOS trong tương lai ngay từ lúc khởi động. Session tương lai đó phải mù đối với các data-derived specifics cũ cho đến khi nó tự đóng băng candidate của chính nó.
> 4. Sau đó gửi toàn bộ yêu cầu bên dưới trong một message.

---

## Yêu cầu: Chuẩn bị handoff cho một session nghiên cứu mới có thể thực hiện CLEAN OOS trên dữ liệu tương lai được append

Kết quả của session hiện tại vẫn chỉ là internal đối với archive hiện tại. Bây giờ tôi muốn một session nghiên cứu trong tương lai giữ lại các bài học phương pháp đã học được, nhưng đồng thời làm cho một phép test clean OOS thật sự trở nên khả thi về mặt cấu trúc.

Cách hợp lệ duy nhất để làm việc đó là:
- xem **toàn bộ dữ liệu đã có trong các file hiện tại** là **historical archive**;
- dùng historical archive đó cho discovery, selection và internal stress testing;
- chỉ dành **dữ liệu BTC/USDT mới thật sự, có timestamp bắt đầu nghiêm ngặt sau archive end** cho bài test clean OOS trong tương lai.

Session tương lai phải tự tái khám phá candidate từ first principles. Nó không được kế thừa các data-derived specifics từ những session trước.

### Nguyên tắc cốt lõi

- Chỉ chuyển giao **meta-knowledge** về phương pháp và cấu trúc, không chuyển giao data-derived specifics.
- Historical archive có thể dùng cho discovery, selection, calibration và các kiểm tra robustness nội bộ, nhưng **không đủ điều kiện** để được gọi là clean OOS.
- Clean OOS reserve phải chỉ bao gồm **dữ liệu tương lai được append** mà chưa từng tồn tại trong bất kỳ file nào đã được dùng ở các session trước.
- Việc tách dữ liệu đúng cách chỉ làm cho clean OOS **có thể được chứng nhận**, chứ **không tự động** làm kết quả trở thành `CLEAN OOS CONFIRMED`.
- Sau khi mở clean reserve, phải **không có redesign, không retune, không đổi winner, và không được cứu kết quả bằng cách chuyển sang runner-up**.

### Tôi cần bạn tạo 4 deliverables:

---

### Deliverable 1: RESEARCH_PROMPT_V8.md

Viết lại `RESEARCH_PROMPT_V7.md` thành phiên bản V8 với các thay đổi sau:

**A. Giữ lại những gì đúng và hữu ích.**
- Giữ mọi phần của V7 đã hoạt động đúng trong lần chạy same-file convergence-audit vừa hoàn tất.
- Giữ lại những phần của V7 đã cải thiện governance, isolation, provenance control và scientific honesty.

**B. Sửa và nâng cấp protocol dựa trên những gì hiện nay đã học được.**
- Sửa mọi phần của V7 còn mơ hồ, governance yếu, awkward về thao tác, hoặc dễ bị misuse.
- Tăng độ chặt ở mọi nơi cần thiết để session clean-OOS trong tương lai khó bị contaminate hơn và khó bị lạm dụng cho post-hoc selection hơn.
- Mọi thay đổi phải giữ ở mức phương pháp. Không được import data-derived specifics từ bất kỳ session nào trước đó.

**C. Thiết kế lại kiến trúc dữ liệu theo tách biệt nghiêm ngặt archive/append.**
V8 phải phân biệt rõ hai vai trò dữ liệu:

1. **Historical archive**
   - Đây là toàn bộ dữ liệu đã có sẵn trong các file hiện tại.
   - Nó có thể được dùng cho context, warmup, discovery, candidate-selection holdout và nếu muốn thì thêm một archive-internal reserve hoặc stress slice.
   - Nó **không đủ điều kiện** cho clean OOS certification.

2. **Fresh appended reserve**
   - Phần này chỉ được chứa dữ liệu có timestamp bắt đầu **nghiêm ngặt sau** timestamp lớn nhất đang có trong historical archive.
   - Đây là phần **duy nhất** đủ điều kiện cho clean OOS evaluation.

Các quy tắc cho V8:
- Protocol phải suy ra ranh giới archive/append từ chính raw files thay vì hardcode một ngày cụ thể.
- Protocol phải kỳ vọng **raw archive files riêng** và **raw append files riêng** cho từng timeframe.
- Protocol phải định nghĩa raw schema kỳ vọng, logic nhận diện vai trò file, và các kiểm tra xác thực ranh giới.
- Discovery, search, calibration và frozen-leader selection phải hoàn tất **mà không mở appended reserve**.
- Nếu V8 có dùng một archive-internal reserve slice, slice đó phải được gắn nhãn **internal only** và tuyệt đối không được nhầm với clean OOS.

**D. Cập nhật governance của reserve để clean OOS được đo một cách sạch sẽ.**
V8 phải ép buộc tất cả các điều sau:
- Exact frozen leader phải được chọn bằng **archive-only evidence**.
- Fresh appended reserve phải được giữ kín cho đến khi frozen leader và frozen comparison set đã được ghi nhận.
- **Lần clean reserve evaluation chính thức đầu tiên** phải được thực hiện trên đúng frozen leader.
- Nếu các frozen candidate khác được chấm trên fresh reserve sau đó, các kết quả đó phải được gắn nhãn **post-verdict diagnostics only** và không được dùng để đổi winner.
- Nếu frozen leader fail trên clean reserve, session phải báo cáo thất bại đó một cách trung thực. Không được cứu kết quả bằng cách chuyển sang candidate khác.

**E. Cập nhật logic evidence-label một cách trung thực.**
V8 phải nêu rõ rằng:
- reserve nằm ngoài historical archive làm cho **clean OOS validation đủ điều kiện**;
- điều kiện về cấu trúc đó là **cần nhưng chưa đủ** cho kết luận `CLEAN OOS CONFIRMED`;
- verdict của clean reserve vẫn phải phụ thuộc vào performance thật của frozen leader dưới protocol đã predeclare;
- nếu clean reserve quá ngắn, quá ít trade, hoặc quá yếu về mặt inferential power, session phải dùng nhãn **inconclusive** trung thực thay vì nói quá mức chắc chắn.

**F. Giữ V8 sạch khỏi data-derived specifics và prior-result leakage.**
- `RESEARCH_PROMPT_V8.md` KHÔNG được chứa bất kỳ feature cụ thể, lookback, threshold, parameter value, calibration detail, named winner hoặc named prior system nào từ các session trước.
- Mọi data-derived specifics chỉ được nằm trong `CONTAMINATION_LOG_V4.md`.
- Phần Fresh Re-derivation Rules chỉ được nói rằng có các session trước đó và specifics của chúng không được làm hẹp search.
- V8 có thể nêu sự thật phương pháp chung rằng historical archive chỉ là internal-only và appended future data mới là clean reserve đủ điều kiện.
- V8 KHÔNG được chứa contamination narrative mang tính session-specific.

**G. Cập nhật Fresh Re-derivation Rules.**
Các rules phải phản ánh tất cả những điều sau:
- hiện nay đã có nhiều session trước đó;
- data-derived specifics của chúng không được làm hẹp search mới;
- session clean-OOS trong tương lai phải đi theo evidence của chính nó;
- việc tồn tại các prior winner không biến bất kỳ winner nào thành mục tiêu mặc định;
- search space phải được giữ mở.

**H. Định vị V8 cho đúng.**
- V8 phải được viết như protocol đầu tiên trong chuỗi nghiên cứu này có khả năng thực hiện một phép appended-data OOS test thật sự sạch.
- Nó không được viết như phần tiếp theo của việc tối ưu thêm trên cùng một file.
- Nó phải làm rõ rằng các cải thiện chỉ dùng archive có thể tăng chất lượng governance, nhưng tự nó không tạo ra clean OOS evidence.

**I. Giữ cùng thứ tự section như V7.**
1. Research protocol — ĐẦU TIÊN
2. Fresh Re-derivation Rules — NGAY SAU protocol, TRƯỚC mọi thông tin từ các session trước
3. Meta-knowledge from Prior Research — CUỐI CÙNG

**J. Không được tham chiếu `CONTAMINATION_LOG_V4.md` ở bất kỳ đâu bên trong V8.**

---

### Deliverable 2: CONTAMINATION_LOG_V4.md

Tôi đã upload `CONTAMINATION_LOG_V3.md` từ lần handoff trước. Hãy cập nhật nó thành `CONTAMINATION_LOG_V4.md` để bao gồm đầy đủ session vừa hoàn tất.

Các cập nhật bắt buộc:
- Thêm một round entry mới ghi rõ chính xác session này đã thử gì và tìm thấy gì.
- Thêm feature scans, shortlists, frozen winner, thresholds, calibration details, comparison steps, reserve/internal findings và mọi data-derived specifics khác cần thiết cho contamination accounting đầy đủ.
- Cập nhật union contamination map để bao gồm mọi range mà session này đã chạm tới.
- Ghi lại chính xác archive-end timestamps cho từng raw file mà session hiện tại đã dùng.
- Nói rõ liệu có còn range nào bên trong archive vẫn globally untouched bởi các vai trò nghiên cứu trước đó hay không. Nếu không còn, hãy nói thẳng.
- Phân biệt rõ giữa:
  - contaminated historical-archive ranges;
  - các split archive-internal chấp nhận được cho research và internal stress testing;
  - yêu cầu rằng mọi clean reserve trong tương lai phải bắt đầu nghiêm ngặt **sau** archive end và phải đến từ dữ liệu newly appended thật sự.
- Cập nhật suggested split templates cho một session clean-OOS trong tương lai dựa trên kiến trúc archive + append.

Tệp này phải hoàn toàn self-contained và **KHÔNG** được tham chiếu từ bên trong `RESEARCH_PROMPT_V8.md`.

---

### Deliverable 3: CHANGELOG_V7_TO_V8.md

Tạo một tệp riêng liệt kê mọi thay đổi quan trọng từ V7 sang V8.

Với mỗi thay đổi, hãy ghi:
- thay đổi chính xác là gì;
- lý do của thay đổi;
- phân loại: `[FIX]`, `[IMPROVE]`, `[NEW]`, hoặc `[REMOVE]`.

Changelog phải bao gồm không chỉ các chỉnh sửa protocol, mà còn cả:
- thay đổi về kiến trúc dữ liệu archive/append;
- thay đổi về governance của reserve;
- thay đổi về evidence-label;
- làm rõ các isolation rules;
- thay đổi về package-boundary và provenance control;
- mọi nỗ lực rõ ràng nhằm ngăn post-reserve winner switching hoặc kiểu salvage trên cùng dữ liệu.

---

### Deliverable 4: DATA_PREPARATION_GUIDE.md

Viết một hướng dẫn rõ ràng, từng bước để tôi chuẩn bị gói dữ liệu cho session clean-OOS trong tương lai.

Nó phải bao gồm tất cả các mục sau:

1. **Tôi đã có dữ liệu gì**
   - mô tả exact date range, schema, timeframe coverage và vai trò của từng file trong historical archive hiện tại;
   - nếu cần, xác định archive end riêng cho H4 và D1.

2. **Tôi cần tải thêm dữ liệu gì**
   - chỉ rõ source, market type, pair và các timeframe cần để khớp chính xác với archive;
   - định nghĩa start timestamp là **bar đầu tiên nằm nghiêm ngặt sau archive end**;
   - định nghĩa end timestamp là thời điểm tôi chọn tải dữ liệu, hoặc muộn hơn nếu tôi chủ động chờ lâu hơn để có reserve mạnh hơn.

3. **Khuyến nghị độ dài tối thiểu của clean reserve**
   - phải đưa ra cả:
     - một **khuyến nghị thời gian chờ theo lịch**, và
     - một **khuyến nghị target trade-count**,
     dựa trên trade frequency thực sự quan sát được trong frontier cạnh tranh của session hiện tại;
   - giải thích trade-off giữa bắt đầu sớm hơn (nhanh hơn nhưng inference yếu hơn) và chờ lâu hơn (chậm hơn nhưng bằng chứng mạnh hơn);
   - giải thích chuyện gì xảy ra nếu tôi vẫn tiến hành với clean reserve bị underpowered.

4. **Đóng gói dữ liệu như thế nào**
   - nói rõ nên giữ archive và append tách riêng hay gộp lại;
   - kỳ vọng mặc định: **giữ tách riêng**;
   - cung cấp folder structure, filename convention và zip layout được khuyến nghị;
   - kèm một package-manifest template, tối thiểu gồm:
     - filename,
     - role (`archive` hoặc `append`),
     - timeframe,
     - row count,
     - min/max timestamp,
     - source,
     - timezone,
     - schema confirmation,
     - file hash.

5. **Các bước verification**
   - cách xác nhận append data khớp archive schema hoàn toàn;
   - cách xác nhận timestamps dùng cùng timezone và cùng semantics;
   - cách xác nhận **không có overlap** và **không có unintended gap** ở boundary archive/append;
   - cách xác nhận append files là native bars và không bị resample hoặc edit tay.

6. **Các biện pháp tránh contamination**
   - phải nói rõ rằng tôi **không được** preview, chart-inspect, backtest hoặc pre-screen append data ngoài các kiểm tra integrity cơ bản;
   - kiểm tra integrity cơ bản thì được, nhưng kiểm tra performance thì không.

7. **Cần upload gì vào session clean-OOS tương lai**
   - liệt kê chính xác các file cần upload;
   - cung cấp exact startup prompt để dùng;
   - startup prompt phải đơn giản và **KHÔNG** được chứa bất kỳ feature cụ thể, lookback, threshold, parameter value, named prior winner hoặc contamination-log content nào;
   - phải nói rõ rằng `CONTAMINATION_LOG_V4.md` **không** được upload ngay lúc khởi động.

8. **Làm gì nếu append reserve ngắn hơn mức khuyến nghị**
   - giải thích tôi nên chờ lâu hơn hay không;
   - nếu tôi chọn không chờ, giải thích rằng session vẫn có thể chạy nhưng phải sẵn sàng cho một reserve verdict **inconclusive** trung thực.

---

### Ràng buộc format

- Cả bốn file đều phải là Markdown.
- `RESEARCH_PROMPT_V8.md` phải self-contained: một AI mới chỉ cần nhận file này cùng data package đã chuẩn bị là có thể bắt đầu ngay.
- `CONTAMINATION_LOG_V4.md` phải self-contained và KHÔNG được tham chiếu từ bên trong `RESEARCH_PROMPT_V8.md`.
- `DATA_PREPARATION_GUIDE.md` là dành cho tôi (con người), không phải cho AI, và phải được viết rõ ràng, có thể hành động ngay.
- Viết mọi thứ bằng tiếng Anh.
- Hãy regenerate cả bốn tài liệu từ đầu. Không được tạo partial patches. Đảm bảo bốn tài liệu nhất quán với nhau.

---

### Checklist cuối cùng trước khi giao

1. V8 có phân biệt rõ contaminated **historical archive** và clean **appended future reserve** không?
   - Nếu không, hãy thiết kế lại.

2. Boundary của append reserve có được định nghĩa từ chính raw files thay vì hardcode ngày hay không?
   - Nếu không, hãy sửa.

3. V8 có nói rõ rằng appended future data chỉ làm clean OOS **đủ điều kiện**, chứ không tự động bảo đảm `CLEAN OOS CONFIRMED`, hay không?
   - Nếu không, hãy chỉnh lại.

4. V8 có cấm post-reserve redesign, retuning, winner switching và rescue by runner-up không?
   - Nếu không, hãy thêm các lệnh cấm đó.

5. V8 có chứa feature cụ thể, lookback, threshold, parameter value, calibration detail, named prior winner hoặc named prior system nào không?
   - Nếu có, hãy xóa khỏi V8 và chỉ giữ chúng trong `CONTAMINATION_LOG_V4.md`.

6. V8 có tránh contamination narrative mang tính session-specific và tránh tham chiếu trực tiếp hoặc gián tiếp đến `CONTAMINATION_LOG_V4.md` không?
   - Nếu không, hãy chỉnh lại.

7. `CONTAMINATION_LOG_V4.md` có bao gồm full round entry của session hiện tại, archive-end timestamps và một câu nói rõ liệu có còn within-archive clean OOS nào không?
   - Nếu không, tệp đó là chưa hoàn chỉnh.

8. `DATA_PREPARATION_GUIDE.md` có nói tôi phải giữ archive và append tách riêng, kèm manifest, kiểm continuity/no-overlap/no-gap và tránh preview performance của append hay không?
   - Nếu không, hãy bổ sung.

9. Startup prompt trong `DATA_PREPARATION_GUIDE.md` có sạch và tối giản không?
   - Nếu không, hãy viết lại.

10. Nếu tôi làm đúng y như guide, thì trong session tương lai một phép appended-data OOS test thật sự sạch có khả thi về mặt cấu trúc hay không — đồng thời vẫn cho phép xuất hiện kết quả inconclusive trung thực?
    - Nếu không, có gì đó sai. Hãy sửa.

11. Version numbers và tên file có nhất quán với trạng thái hiện tại của dòng nghiên cứu hay không?
    - Nếu không, hãy sửa.

Không được hỏi lại để làm rõ. Mọi thứ cần thiết đã có trong prompt, prior artifacts và completed session outputs.
