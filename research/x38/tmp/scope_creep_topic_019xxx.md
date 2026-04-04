# A. Phát hiện ban đầu
## A.1. Câu hỏi của human:
/var/www/trading-bots/btc-spot-dev/research/x38/debate hiện tại có còn bị lỗi sau đây không?

Scope creep 3 lần
Wave 1 : DFL-01→05 — discovery loop architecture. Đúng scope.
Wave 2 : DFL-06→12 — systematic data exploration + methodology + budget. Đây là research plan, không phải framework architecture.
Wave 3 : DFL-13→18 — data trustworthiness, non-stationarity, regime profiling. Đây là data quality infrastructure — hoàn toàn khác scope "discovery feedback loop".
DFL-13 (data trustworthiness) và DFL-17 (pipeline validation via synthetic data) không liên quan gì đến "discovery feedback loop". Chúng là concerns riêng bị nhét vào topic gần nhất thay vì mở topic mới.

## A.2. Trả lời của Claude Code cho A.1:

Phân nửa đã sửa, phân nửa vẫn còn.

Đã sửa: vấn đề thực tiễn (debate efficiency)
Split 2026-04-02 tách 019 thành 9 sub-topic, trong đó 019E/F/G được đánh dấu rõ:

"These are Tier 4 decisions, INDEPENDENT of the discovery loop architecture (Tier 1-3). Can be debated in PARALLEL with all other 019 sub-topics."

Debate wave cũng phản ánh đúng — 019E/F/G chạy song song, không chờ 019A:


019A (Tier 1 blocker) → 019B/C → 019D1/D2 → 019D3
019E/F/G (independent) ← song song, không phụ thuộc 019A
Chưa sửa: vấn đề khái niệm (scope identity)
3 dấu hiệu scope creep vẫn tồn tại:

1. Vẫn là sub-topic của 019 "Discovery Feedback Loop"

DFL-13 (data trustworthiness — "Binance volume có wash trading không?") và DFL-17 (pipeline calibration — "pipeline có detect được signal không?") không phải là feedback loop architecture. Chúng là data infrastructure và pipeline QA — concerns hoàn toàn khác.

2. Vẫn dùng prefix DFL- (Discovery Feedback Loop)

DFL-13 nghĩa là "Discovery Feedback Loop finding #13." Nhưng "cross-exchange volume validation" không liên quan gì đến discovery feedback loop.

3. Có topic phù hợp hơn tồn tại sẵn

Finding	Hiện tại	Topic phù hợp hơn
DFL-13 (data trustworthiness)	019E	009 (Data Integrity) — đúng layer: "data có đúng không?"
DFL-17 (pipeline validation via synthetic)	019E	012 (Quality Assurance) — pipeline calibration = QA
DFL-14 (non-stationarity protocol)	019F	Có thể argue thuộc 019, nhưng response protocol → 003 hoặc 012
DFL-15/16 (data scope, cross-asset)	019G	Scope decision → có thể là topic riêng
Tóm lại
Split đã giảm thiệt hại thực tiễn: debate không bị block, debaters không phải đọc 167KB cùng lúc. Nhưng scope creep về mặt tổ chức vẫn đúng như bạn mô tả — DFL-13 và DFL-17 vẫn bị nhét vào topic gần nhất thay vì đặt đúng chỗ. File gốc 019 thậm chí tự thừa nhận: line 13 ghi "DFL-13→18: Data foundation & quality assurance" — chính nó đã phân biệt scope khác nhưng vẫn giữ chung topic.

# B. Phân tích sâu hơn và Phản biện thực tế
## B.1. Đề xuất của ChatGPT Pro cho A.1 và A.2:

Kết luận thẳng: còn, nhưng không còn ở đúng hình dạng ban đầu. Cái lỗi “nhét 3 wave khác bản chất vào một topic 019” đã được giảm mạnh ở lớp tổ chức/debate scheduling vì registry hiện đã split 019 thành 9 sub-topics, và wave graph còn ghi rõ 019E/019F/019G là nhánh độc lập, chạy song song. Nhưng ở lớp scope identity / owner-of-record, lỗi vẫn tồn tại vì parent 019-discovery-feedback-loop vẫn giữ dossier cũ 18 findings, vẫn tuyên bố DFL-13→18 là “Data foundation & quality assurance” của Discovery Feedback Loop, và vẫn dùng prefix X38-DFL-*.

Phần đã sửa là có thật, không phải vá giả. debate-index.md hiện coi 019 là parent index đã split; 019E là “Data quality validation” chứa DFL-13 + DFL-17, 019F là “Regime dynamics” chứa DFL-14 + DFL-18, còn 019G là “Data scope” chứa DFL-15 + DFL-16. 019F còn nói rõ nó được regroup để xử lý trực tiếp xung đột DFL-14/DFL-18, và 019G ghép 15/16 vì 16 phụ thuộc vào 15. Về mặt vận hành, đây là một cải thiện thực chất.

Nhưng phần bạn gọi là “scope identity” thì vẫn lỗi. Cả 019E, 019F và 019G đều tự mô tả là independent of the discovery loop architecture, nhưng vẫn nằm trong series 19 và vẫn dùng prefix X38-DFL-. Nói cách khác, nội dung bảo “không phải discovery-loop architecture”, còn tên hệ thống lại bảo “đây là discovery-loop finding”. Parent dossier 019 còn tệ hơn: nó không hề phản ánh split, vẫn giữ cách mô tả cũ “DFL-13→18: Data foundation & quality assurance”, vẫn giữ prefix DFL, và thậm chí không nhắc tới 019E/F/G. Đây là dual truth, không phải cleanup hoàn chỉnh.

DFL-13 và DFL-17 là hai chỗ sai owner rõ nhất. Với DFL-13, chính 019E ghi tension với Topic 009 và mô tả nó là lớp “accuracy” nằm dưới integrity/completeness; đó là ngôn ngữ của data trustworthiness, không phải discovery loop. Với DFL-17, Topic 012 hiện đã có F-39 nói đúng domain này: automated correctness assurance, determinism regression, và pipeline integration tests trên synthetic dataset. Để DFL-17 tiếp tục sống dưới nhánh 19 chỉ vì nó “gần” DFL-06/07 là sai logic tổ chức.

Wave 2 cũng chưa sạch hẳn. 019C đã tách DFL-06/07 ra riêng, nhưng հենց DFL-06 tự thừa nhận nó đang trộn ARCHITECTURE content với RESEARCH PLAN content, và mở hẳn D-12 để quyết định “Architecture / Research plan / Split”. Tức là vấn đề đã được bóc riêng và gọi tên, nhưng chưa được xử lý xong. Ngoài ra, PLAN.md và EXECUTION_PLAN.md hiện vẫn mô tả Topic 019 như một monolith 18 findings ở Wave 2.5, nên người đọc đi từ planning surfaces vẫn sẽ hiểu repo theo mô hình cũ.

Tôi đề xuất sửa triệt để, không vá tiếp:

Biến 019 parent thành index-only, ngay lập tức. 019-discovery-feedback-loop/findings-under-review.md phải bị rewrite thành một file chỉ còn: mô tả ngắn, routing table sang 019A/B/C/D1/D2/D3, historical provenance, và deprecation notice. Không được giữ full bodies của 18 findings ở parent nữa, vì debate-index.md đã nói rõ parent split entries chỉ là index, findings sống ở sub-topics. Nếu không làm bước này, dual truth sẽ còn mãi.
Re-home theo semantic owner, không theo historical origin. Tôi khuyên mapping như sau: DFL-13 → 009A-data-trustworthiness; DFL-17 → 012A-discovery-pipeline-validation; 019F → top-level 020-regime-dynamics; 019G → top-level 021-data-scope; còn 019 chỉ giữ discovery-core: 019A, 019B, 019C, 019D1, 019D2, 019D3. Repo đã có precedent cho split dạng chữ/cấp con như 017A/017B và 019D1/D2/D3, nên 009A/012A là hoàn toàn tự nhiên, không phá style hiện tại.
Đổi prefix để tên ngừng nói dối. Những finding nào không còn thuộc discovery-core thì không được giữ X38-DFL-*. Giữ traceability bằng metadata kiểu historical_origin: 019/DFL-13, chứ không dùng prefix sai owner. Quy tắc nên là: nếu dossier tự ghi “independent of the discovery loop architecture”, nó không được nằm dưới namespace DFL nữa.
Đồng bộ toàn bộ ledgers và dependency graph. debate-index.md, PLAN.md, EXECUTION_PLAN.md, và mọi draft dependency header phải được sửa để phản ánh world model mới. Đặc biệt, 003 không nên “chờ 019” kiểu monolith nữa; ngay trong debate-index hiện tại, 003 thực chất chỉ cần 019A + 019D1 ở nhánh 19. Nếu không sync, scope creep sẽ tái sinh mỗi lần ai đó đọc PLAN.md hoặc EXECUTION_PLAN.md thay vì registry.
Thêm rule ngăn tái phát. Tôi sẽ viết hẳn một governance rule kiểu: “cross-topic tension không phải là lý do hợp lệ để giữ finding sai owner; owner phải được xác định theo artifact/spec bị thay đổi khi finding đó được resolve.” Kèm theo hai guardrail cứng: parent topic sau split không được chứa live findings; và nếu prefix không khớp semantic owner thì audit phải fail. Hiện repo đang vấp đúng hai lỗi này cùng lúc.

Tóm gọn một câu: practical split đã có, semantic ownership thì chưa. Tôi không khuyên giữ nguyên 019E/F/G như hiện tại rồi coi như xong; cách đó chỉ đổi hình thức, chưa sửa ontology. Fix đúng là: dọn 019 thành pure index, kéo DFL-13 sang nhánh 009, kéo DFL-17 sang nhánh 012, tách 019F và 019G ra top-level topics riêng, rồi sync lại toàn bộ plan/execution surfaces. Nếu không làm đủ chỗ đó, repo sẽ tiếp tục có hai bản đồ scope song song và bug này sẽ quay lại rất nhanh.

## B.2. Phản biện của Claude Code cho B.1:

Đã đọc đủ data. Đây là đánh giá phản biện từng điểm:

Phần ChatGPT Pro ĐÚNG (xác nhận bằng dữ liệu)
1. Parent 019 vẫn là monolith 3005 dòng — CONFIRMED
Parent file vẫn 3005 dòng, y hệt trước khi split. Dù debate-index ghi rõ "SPLIT entries (000, 017, 019, 019D) are parent indexes — findings live in sub-topics only", file thực tế không phản ánh điều đó. Header vẫn ghi:

18 findings about the Human-AI collaborative discovery loop

Đây đúng là dual truth — metadata nói "index", file vẫn là bản đầy đủ.

2. PLAN.md và EXECUTION_PLAN.md chưa sync — CONFIRMED
PLAN.md vẫn ghi:


019 | Discovery feedback loop | DFL-01→DFL-18 | OPEN
003 ← HARD-dep from ... + 019
EXECUTION_PLAN.md:


Topic 019 | OPEN. 18 findings (DFL-01→DFL-18)
019 (discovery feedback loop) ← chờ 018✅ + 002✅ + 004✅
Không file nào nhắc đến 019A-G/D1-D3. Ai đọc planning surfaces thay vì debate-index sẽ thấy 019 monolith.

3. "Practical split đã có, semantic ownership thì chưa" — ĐÚNG về chẩn đoán tổng thể
019E/F/G tự ghi "independent of the discovery loop architecture" nhưng vẫn nằm dưới 019 và dùng prefix DFL-. Contradiction có thật.

Phần ChatGPT Pro SAI hoặc OVERSTATED
4. "DFL-17 → 012 vì F-39 covers same domain" — SAI
ChatGPT Pro nói F-39 "nói đúng domain này: automated correctness assurance, determinism regression, và pipeline integration tests trên synthetic dataset". Nhưng F-39 và DFL-17 hỏi câu hỏi khác nhau hoàn toàn:

F-39 (012)	DFL-17 (019E)
Câu hỏi	Code có chạy đúng không?	Pipeline có đủ statistical power để detect signal không?
Synthetic data dùng để	Test determinism, stage gating, artifact correctness	Inject known IC=0.02→0.20, measure detection rate
Output	PASS/FAIL per test case	Minimum detectable IC, false positive rate at stage 5
Domain	Software engineering QA	Statistical methodology calibration
F-39 item 3 nói "pipeline integration tests on small synthetic dataset — verify stage gating works, artifacts produced correctly". DFL-17 nói "at each IC level, run 100 synthetic datasets, detection rate = fraction where pipeline detects X at each stage". Chung từ "synthetic" và "pipeline" nhưng test hoàn toàn khác layer.

Nói F-39 "covers same domain" là category error — nhầm software testing với statistical power testing.

5. "Đổi prefix DFL- vì tên đang nói dối" — MÂU THUẪN với convention hiện tại
Repo đã có precedent rõ ràng: prefix là batch ID cố định, không phải scope marker. Bằng chứng:

F-14, F-17 được move từ Topic 003 → Topic 015, vẫn giữ prefix F-
SSE-04-CELL route từ Topic 018 → Topic 017A, vẫn giữ prefix SSE-
SSE-08-CON route từ Topic 018 → Topic 017B, vẫn giữ prefix SSE-
Không finding nào bị đổi prefix khi chuyển topic. Prefix = "opened in batch X", không phải "owned by topic Y". Đổi DFL-13 thành DI-13 (Data Integrity) sẽ phá convention đang consistent và tạo precedent nguy hiểm (mỗi lần re-home phải rename).

ChatGPT Pro nói "giữ traceability bằng metadata historical_origin: 019/DFL-13" — nhưng prefix hiện tại đã là traceability. Đổi nó đi rồi thêm metadata để track cái cũ = thay đường thẳng bằng đường vòng.

6. "019F → top-level 020, 019G → top-level 021" — OVERSTATED cho 019F
019F chứa DFL-14 và DFL-18. Cả hai connect trực tiếp đến DFL-08 Stage 2 (graduation path):

DFL-14 line 165-169: "Stage 2 deep dive MUST include shelf-life classification"
DFL-18 line 325: "Stage 2 (deep dive) → ADD: regime-conditional profiling"
DFL-08 nằm ở 019D1
DFL-14/DFL-18 mở rộng graduation path — chúng là downstream extension của discovery pipeline. Gọi chúng là "hoàn toàn khác scope" là overstated. Chúng independent về tier (Tier 4 vs Tier 1-3) nhưng connected về functional dependency (cả hai extend DFL-08 Stage 2).

019G (DFL-15/16) thì argument mạnh hơn — data acquisition scope thực sự là upstream decision, không phải discovery loop architecture.

7. "DFL-13 → 009" — Hợp lý nhưng có tradeoff ẩn
ChatGPT Pro nói đúng: DFL-13 là data trustworthiness, 009 là data integrity, complementary. Nhưng:

009 hiện có 2 findings (F-10, F-11), mỗi cái ~40-60 dòng, authored by claude_code
DFL-13 đơn lẻ đã 174 dòng, authored by human researcher, depth rất khác
Re-homing DFL-13 vào 009 sẽ tạo asymmetry lớn: 1 finding nặng gấp 3 lần 2 findings còn lại cộng lại
009 là Wave 2 (debatable now), 019E là Wave 2.5. Move DFL-13 sẽ thay đổi scheduling — có thể tốt (debate sớm hơn) hoặc xấu (debaters 009 chưa expect scope mới)
Điểm này ChatGPT Pro bỏ qua hoàn toàn.

Phần ChatGPT Pro BỎ SÓT
8. Cost-benefit của remedy
ChatGPT Pro đề xuất: rewrite parent, re-home 4 findings, đổi prefix, tạo 2 topic mới, sync 4+ files, thêm governance rule. Đó là rất nhiều churn cho vấn đề hiện tại chỉ ảnh hưởng bookkeeping, không ảnh hưởng debate execution (019E/F/G đã debatable independently).

Không có dòng nào trong phân tích đó cân nhắc: "liệu chi phí sửa có tương xứng với thiệt hại đang chịu không?"

9. 019C cũng có scope mixing — nhận diện nhưng chưa phân tích kỹ
ChatGPT Pro nhắc D-12 (architecture vs research plan) trong DFL-06 nhưng chỉ nói "vấn đề đã được bóc riêng và gọi tên, nhưng chưa được xử lý xong" rồi bỏ qua. Thực tế, D-12 là deliberate design — 019C scope note ghi rõ debate phải quyết "Architecture / Research plan / Split". Đây không phải scope creep chưa sửa, mà là scope question đang chờ debate resolve. Hai thứ này khác nhau.

Verdict tổng thể
Claim	Đánh giá
Dual truth ở parent 019	Đúng — cần sửa
PLAN.md/EXECUTION_PLAN.md out of sync	Đúng — cần sửa
DFL-13 wrong-homed	Đúng — 009 phù hợp hơn
DFL-17 → 012 vì F-39 "same domain"	Sai — F-39 ≠ DFL-17, khác layer
Đổi prefix DFL-	Sai — phá existing convention
019F → top-level 020	Overstated — DFL-14/18 connect to DFL-08
019G → top-level 021	Có cơ sở nhưng benefit marginal
D-12 = scope creep chưa sửa	Sai — deliberate design choice chờ debate
Governance rule chống tái phát	Hợp lý về nguyên tắc nhưng rule "prefix must match owner" mâu thuẫn với convention
Cost-benefit analysis	Thiếu hoàn toàn
Tóm lại: Chẩn đoán 70% đúng, remedy 70% quá tay. Sửa đúng mức = (1) rewrite parent 019 thành index-only, (2) sync PLAN.md + EXECUTION_PLAN.md, (3) cân nhắc re-home DFL-13 → 009. Phần còn lại (đổi prefix, tạo topic 020/021, governance rule về prefix) gây churn nhiều hơn giá trị mang lại

## B.3. Phản biện của ChatGPT Pro cho B.2:
