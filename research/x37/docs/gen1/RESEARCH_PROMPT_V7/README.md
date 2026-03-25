Sau khi dán phần prompt trong PROMPT_FOR_V7_HANDOFF.md vào vòng chat tiếp theo, ta sẽ thu được 4 deliverables:
+ RESEARCH_PROMPT_V7.md
+ CONTAMINATION_LOG_V3.md
+ CHANGELOG_V6_TO_V7.md
+ CONVERGENCE_STATUS_V2.md
Đây là các tài liệu cần thiết để bắt đầu một phiên nghiên cứu mới.

Lưu ý: Trước khi gửi prompt PROMPT_FOR_V7_HANDOFF.md, phải tải lên file CONTAMINATION_LOG_V2.md trước.

# Các bước tiếp theo sẽ là:

1. Tải RESEARCH_PROMPT_V7.md + data.zip. Prompt kèm theo:

"This is the research prompt and the data. Read RESEARCH_PROMPT_V7.md completely, then execute the protocol from Step 1. Do not ask for clarification — everything you need is in the prompt and the data."

2. Prompt viết spec cho research protocol và final system:

/var/www/trading-bots/btc-spot-dev/research/x37/docs/gen1/RESEARCH_PROMPT_V7/SPEC_REQUEST_PROMPT.md


3. Tải CONTAMINATION_LOG_V3.md. Prompt kèm theo:

"I am now uploading the contamination log from the prior research session. Compare your independently derived results against this log. Report whether your findings converged or diverged with the prior session, and assess whether your data splits were truly independent."

Quang trọng: Nghiên cứu PROMPT_FOR_V8_HANDOFF
