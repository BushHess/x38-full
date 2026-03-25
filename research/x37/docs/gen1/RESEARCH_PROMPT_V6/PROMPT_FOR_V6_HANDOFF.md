# PROMPT TO SEND TO THE CURRENT RESEARCH SESSION

> Prompt này được thiết kế để sau khi kết thúc phiên nghiên cứu hiện tại, AI sẽ tự động tạo ra các tài liệu để bắt đầu một phiên nghiên cứu hoàn toàn mới nhằm tái khám phá hệ thống từ đầu, trên một tập dữ liệu khác, để thu được kết quả OOS thực sự sạch sẽ. Để đảm bảo tính độc lập của phiên nghiên cứu mới, bạn sẽ tạo ra 4 tài liệu riêng biệt:
+ RESEARCH_PROMPT_V6.md (hướng dẫn nghiên cứu)
+ CONTAMINATION_LOG_V2.md (ghi chép về những gì đã bị ô nhiễm trong các phiên trước)
+ CHANGELOG_V5_TO_V6.md (liệt kê tất cả các thay đổi từ V5 sang V6)
+ CONVERGENCE_STATUS.md (trạng thái hội tụ).
>
> Trước khi gửi prompt này, hãy tải CONTAMINATION_LOG.md của V5 lên phiên làm việc này. Đây là nhật ký ô nhiễm được tạo ra trong quá trình bàn giao từ phiên làm việc trước đó (phiên đã chạy V4 và tạo ra new_base / new_final_flow). Các kết quả của riêng bạn đã được đóng băng, do đó việc tải file lên lúc này sẽ không gây ra sự ô nhiễm. Bạn cần nó để tạo ra một phiên bản cập nhật bao gồm cả vòng chạy của chính bạn.
>
> Sau đó, sao chép toàn bộ nội dung bên dưới đường phân cách và gửi chúng cùng nhau.

---

## Request: Create handoff documents for a completely clean new research session

This research session is now concluded. I want to start an entirely new session to re-derive the system from scratch, in order to obtain an independent third result.

Core principle: **Transfer only meta-knowledge (lessons about methodology and structure), DO NOT transfer data-derived specifics (specific features, specific lookbacks, specific thresholds, specific parameters).** The new session must rediscover everything from first principles.

### I need you to produce 4 deliverables:

---

### Deliverable 1: RESEARCH_PROMPT_V6.md

Rewrite RESEARCH_PROMPT_V5.md into version V6 with the following changes:

**A. Keep everything from V5 that worked correctly in this session.**

**B. Fix/improve based on what you learned running V5:**
- Every part of V5 that you found missing, ambiguous, misleading, or that led to wasted steps — fix it
- If the search ladder, screening criteria, evaluation steps, or decision gates need adjustment — adjust them
- If the order of steps needs to change — change it

**C. Add methodological lessons to the Meta-knowledge section:**
- Add any new lessons you learned in this session (same rules as before: principles only, no specific features, lookbacks, thresholds, or parameters)
- Do not duplicate lessons that are already in V5 — only add what is genuinely new
- If any existing lesson in V5 proved wrong or misleading during this session, correct or remove it

**D. Redesign the data split architecture:**
- Use a different split from V5. You have seen how V5's split performed — choose boundaries that you believe will produce a more effective discovery/holdout/reserve structure.
- The reserve window in this version will still be internal-only (not eligible for clean OOS), because all data in the current file has been touched by at least one prior session. State this honestly in the protocol.

**E. DO NOT include any specific features, lookbacks, thresholds, parameters, or contamination disclosure from this session or any prior session in RESEARCH_PROMPT_V6.md.** All data-derived specifics belong exclusively in the contamination log. The Fresh Re-derivation Rules section should state only that prior sessions exist and their specifics must not narrow the search — without naming what those specifics are.

**F. Update the Fresh Re-derivation Rules** to reflect that:
- Two prior sessions have now been run, each producing a different result
- The new session must not treat either prior result as more correct than the other
- The new session must follow its own evidence

**G. Keep the same section ordering as V5:**
1. Research protocol — FIRST
2. Fresh Re-derivation Rules — IMMEDIATELY AFTER protocol, BEFORE any information from prior sessions
3. Meta-knowledge from Prior Research — LAST

---

### Deliverable 2: CONTAMINATION_LOG_V2.md

I have uploaded the CONTAMINATION_LOG.md that was produced during the handoff from the session before yours. Update it to include this session's results:
- Add a new round entry documenting exactly what this session tried and found
- Add this session's feature scans, shortlists, winner, thresholds, and calibration details
- Update the union contamination map to include all ranges this session touched
- Update the suggested alternative splits for the new session

This file must NOT be referenced from within RESEARCH_PROMPT_V6.md. Same isolation rules as before: the new session reads it only AFTER freezing its own independent candidate.

---

### Deliverable 3: CHANGELOG_V5_TO_V6.md

A separate file listing:
- Every change from V5 to V6
- The reason for each change
- Classification of each change: [FIX] (bug fix), [IMPROVE] (improvement), [NEW] (new addition), [REMOVE] (removal)

---

### Deliverable 4: CONVERGENCE_STATUS.md

A new file that summarizes the state of convergence across all sessions so far:
- List each session, its frozen winner, and its key metrics
- State whether sessions converged or diverged
- Identify which aspects are consistent across sessions (if any) and which are inconsistent
- Assess honestly: is a third session on the same data likely to resolve the divergence, or is new data required?

This file is for me (the human) to decide whether to continue iterating or stop and wait for new data. Write it in Vietnamese, in clear, direct language.

---

### Format constraints:
- All four files must be Markdown
- RESEARCH_PROMPT_V6.md must be self-contained: a new AI receiving this file + data.zip can start immediately
- CONTAMINATION_LOG_V2.md must be self-contained and must NOT be referenced from within RESEARCH_PROMPT_V6.md
- CONVERGENCE_STATUS.md is for me (the human), not for the AI — write it in Vietnamese
- Write RESEARCH_PROMPT_V6.md, CONTAMINATION_LOG_V2.md, and CHANGELOG_V5_TO_V6.md in English

---

### Final checklist before delivery:

1. Does V6 contain any specific features, lookbacks, thresholds, or parameter values from this session or prior sessions? → If yes, remove from V6 (keep only in CONTAMINATION_LOG_V2.md)
2. Does V6 contain any contamination disclosure content? → If yes, remove it
3. Does V6 reference CONTAMINATION_LOG_V2.md? → If yes, remove the reference
4. Does the Meta-knowledge section contain only genuinely new lessons, without duplicating what V5 already had? → If duplicated, deduplicate
5. Does the Meta-knowledge section contain any lesson that implicitly points toward a specific feature or parameter? → If yes, rewrite to be principle-level only
6. Does V6 honestly state that the reserve window is internal-only and not eligible for clean OOS? → If not, add this
7. Does CONTAMINATION_LOG_V2.md include this session's full round entry alongside all prior rounds? → If not, it is incomplete
8. Does CONVERGENCE_STATUS.md give me enough information to decide whether to run another iteration or stop? → If not, add detail
9. If a completely new AI reads V6, would it be biased toward any specific feature, lookback, or threshold from any prior session? → If yes, revise
