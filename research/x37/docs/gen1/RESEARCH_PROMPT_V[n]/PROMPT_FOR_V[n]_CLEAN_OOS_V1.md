# PROMPT TO SEND TO THE CURRENT RESEARCH SESSION

> Prompt này được thiết kế để sau khi kết thúc phiên nghiên cứu hiện tại, AI sẽ tự động tạo ra các tài liệu để bắt đầu một phiên nghiên cứu hoàn toàn mới nhằm tái khám phá hệ thống từ đầu, trên một tập dữ liệu khác, để thu được kết quả OOS thực sự sạch sẽ. Để đảm bảo tính độc lập của phiên nghiên cứu mới, bạn sẽ tạo ra 4 tài liệu riêng biệt: RESEARCH_PROMPT_V6.md (hướng dẫn nghiên cứu), CONTAMINATION_LOG_V2.md (ghi chép về những gì đã bị ô nhiễm trong các phiên trước), CHANGELOG_V5_TO_V6.md (liệt kê tất cả các thay đổi từ V5 sang V6), và DATA_PREPARATION_GUIDE.md (hướng dẫn chuẩn bị dữ liệu).
>
> Trước khi gửi prompt này, hãy tải CONTAMINATION_LOG.md lên phiên làm việc này. Đây là nhật ký ô nhiễm được tạo ra trong quá trình bàn giao từ phiên làm việc trước đó (phiên đã chạy V4 và tạo ra new_base / new_final_flow). Các kết quả của riêng bạn đã được đóng băng, do đó việc tải file lên lúc này sẽ không gây ra sự ô nhiễm. Bạn cần nó để tạo ra một phiên bản cập nhật bao gồm cả vòng chạy của chính bạn.
>
> Sau đó, sao chép toàn bộ nội dung bên dưới đường phân cách và gửi chúng cùng nhau.

---

## Request: Prepare handoff for a new session that can achieve CLEAN OOS CONFIRMED

The result of this session is INTERNAL ROBUST CANDIDATE because the reserve slice cannot be globally certified untouched. I want to fix this structurally for the next session.

The only way to achieve a true clean OOS proof is to use data that has never existed in any file sent to any prior session. I will download fresh BTC/USDT data from the exchange to extend beyond the current file's end date.

### I need you to produce 4 deliverables:

---

### Deliverable 1: RESEARCH_PROMPT_V6.md

Rewrite RESEARCH_PROMPT_V5.md into V6 with the following changes:

**A. Keep everything from V5 that worked correctly in this session.**

**B. Fix/improve based on what you learned running V5:**
- Every part of V5 that you found missing, ambiguous, misleading, or that led to wasted steps — fix it
- If the search ladder, screening criteria, evaluation steps, or decision gates need adjustment — adjust them
- Add any methodological lessons you learned in this session to the Meta-knowledge section (same rules as before: principles only, no specific features, lookbacks, thresholds, or parameters)

**C. Redesign the data split architecture to guarantee clean OOS:**

The new split must follow this structure:

- **Discovery + selection holdout:** use ONLY data from the CURRENT file (the one you already have). You decide the exact split boundaries based on what you learned about effective splitting.
- **Reserve window:** define it as starting AFTER the last date in the current file. This range will contain ONLY new data that I will download separately. It has never been seen by any session.
- Write the split so that the reserve window is automatically defined by "data that starts after the last date in the current file" rather than hardcoding a specific date, so it works regardless of exactly when I download the new data.

This design guarantees the reserve is globally untouched, which satisfies the CLEAN OOS CONFIRMED requirement.

**D. Update the evidence labeling rules** to reflect that:
- The reserve window in V6 IS eligible for CLEAN OOS CONFIRMED because it contains data from outside any prior session's file
- State this explicitly in the protocol so the new session knows it can certify the reserve

**E. DO NOT include any specific features, lookbacks, thresholds, parameters, or contamination disclosure from this session or any prior session in RESEARCH_PROMPT_V6.md.** All data-derived specifics belong exclusively in the contamination log. The Fresh Re-derivation Rules section should state only that prior sessions exist and their specifics must not narrow the search — without naming what those specifics are.

**F. Keep the same section ordering as V5:**
1. Research protocol — FIRST
2. Fresh Re-derivation Rules — IMMEDIATELY AFTER protocol, BEFORE any information from prior sessions
3. Meta-knowledge from Prior Research — LAST

---

### Deliverable 2: CONTAMINATION_LOG_V2.md

I have uploaded the CONTAMINATION_LOG.md that was produced during the handoff from the session before yours. Update it to include this session's results:
- Add a new round entry documenting exactly what this session tried and found
- Add this session's feature scans, shortlists, winner, thresholds, and calibration details
- Update the union contamination map to include all ranges this session touched
- Update the suggested alternative splits to reflect the new V6 design (reserve = new data after current file end)

This file must NOT be referenced from within RESEARCH_PROMPT_V6.md. Same isolation rules as before: the new session reads it only AFTER freezing its own independent candidate.

---

### Deliverable 3: CHANGELOG_V5_TO_V6.md

A separate file listing:
- Every change from V5 to V6
- The reason for each change
- Classification of each change: [FIX] (bug fix), [IMPROVE] (improvement), [NEW] (new addition), [REMOVE] (removal)

---

### Deliverable 4: DATA_PREPARATION_GUIDE.md

Write a clear, step-by-step guide for me to prepare the data package for the new session. Include:

1. **What data I already have:** describe the current file's exact date range and format
2. **What new data I need to download:** specify the source, pair, timeframes (H4 and D1), and the start date (= day after current file ends). End date = the day I download.
3. **Minimum reserve length recommendation:** based on the typical trade frequency you observed in this session, recommend how long I should wait before downloading new data so that the reserve window has enough trades to support meaningful inference. Be specific about the trade-off between waiting longer (more trades, stronger proof) and starting sooner (less waiting, weaker proof).
4. **How to package the data:** should I combine old + new into one file? Or keep them separate? What format and naming convention?
5. **Verification steps:** how to confirm the new data is correctly formatted and continuous with the old data (no gaps, same columns, same timezone)
6. **What to upload to the new session:** the exact list of files and the exact startup prompt to use. The startup prompt must be simple and must NOT contain any specific features, lookbacks, thresholds, or parameter values from any prior session.

---

### Format constraints:
- All four files must be Markdown
- RESEARCH_PROMPT_V6.md must be self-contained: a new AI receiving this file + the prepared data package can start immediately
- CONTAMINATION_LOG_V2.md must be self-contained and must NOT be referenced from within RESEARCH_PROMPT_V6.md
- DATA_PREPARATION_GUIDE.md is for me (the human), not for the AI — write it in clear, actionable language
- Write everything in English

---

### Final checklist before delivery:

1. Does the V6 data split guarantee that the reserve window contains ONLY data that has never existed in any prior session's file? → If not, redesign
2. Is the reserve window definition robust to different download dates? → If it depends on a hardcoded date that might be wrong, fix it
3. Does V6 contain any specific features, lookbacks, thresholds, or parameter values from this session or prior sessions? → If yes, remove from V6 (keep only in CONTAMINATION_LOG_V2.md)
4. Does V6 contain any contamination disclosure content? → If yes, remove it
5. Does V6 reference CONTAMINATION_LOG_V2.md? → If yes, remove the reference
6. Does CONTAMINATION_LOG_V2.md include this session's full round entry alongside all prior rounds? → If not, it is incomplete
7. Does DATA_PREPARATION_GUIDE.md include a minimum reserve length recommendation with concrete reasoning? → If not, add it
8. Does the startup prompt in DATA_PREPARATION_GUIDE.md contain any specific features, lookbacks, thresholds, or parameters from any session? → If yes, rewrite it to be clean
9. If I follow all steps in DATA_PREPARATION_GUIDE.md and start a new session with V6 + prepared data, is CLEAN OOS CONFIRMED structurally achievable? → If not, something is wrong — fix it
