1. Tải RESEARCH_PROMPT_V5.md + data.zip. Prompt kèm theo:

"This is the research prompt and the data. Read RESEARCH_PROMPT_V5.md completely, then execute the protocol from Step 1. Do not ask for clarification — everything you need is in the prompt and the data."

2. Prompt viết spec cho research protocol:

"Hãy viết hai tài liệu spec riêng biệt, đủ để một kỹ sư rebuild từ đầu mà không cần chat history, code gốc, hay bất kỳ tài liệu nào khác ngoài spec này và dữ liệu đầu vào. Spec 1 — Quá trình nghiên cứu (Research Reproduction Spec): Mô tả từng bước đã thực hiện để đi từ raw data đến Frozen winner: SF_EFF40_Q70_STATIC: gồm data pipeline, feature engineering, screening criteria, so sánh & loại bỏ ứng viên, và lý do chọn cuối cùng.... không được thiếu bước nào. Mỗi bước cần ghi rõ input → logic → output → decision rule. Spec 2 — Hệ thống frozen (System Specification): Mô tả chính xác final_practical_system.json ("SF_EFF40_Q70_STATIC"): toàn bộ tham số, signal logic, entry/exit rules, position sizing, regime gate — ở mức một kỹ sư có thể implement lại mà output khớp bit-level với bản gốc."


3. Tải CONTAMINATION_LOG.md. Prompt kèm theo:

"I am now uploading the contamination log from the prior research session. Compare your independently derived results against this log. Report whether your findings converged or diverged with the prior session, and assess whether your data splits were truly independent."

4. Copy phần prompt từ PROMPT_FOR_V6_CLEAN_OOS.md và paste vào vòng chát tiếp theo.
