

# PROMPT TO SEND TO THE CURRENT RESEARCH AI SESSION

> Prompt này được thiết kế để sau khi kết thúc phiên nghiên cứu hiện tại, AI sẽ tự động tạo ra tài liệu để bắt đầu một phiên nghiên cứu hoàn toàn mới để tái khám phá hệ thống từ đầu, trên một tập dữ liệu khác, nhằm thu được kết quả OOS thực sự sạch sẽ. Để đảm bảo tính độc lập của phiên nghiên cứu mới, bạn sẽ tạo ra 3 tài liệu riêng biệt: RESEARCH_PROMPT_V5.md (hướng dẫn nghiên cứu), CONTAMINATION_LOG.md (ghi chép về những gì đã bị ô nhiễm trong phiên trước), và CHANGELOG_V4_TO_V5.md (liệt kê tất cả các thay đổi từ V4 sang V5).

> Tuy nhiên, phiên nghiên cứu mới cũng kế thừa được các kiến thức đã thu được trong các vòng nghiên cứu trước đó

> Sao chép toàn bộ nội dung bên dưới đường phân cách và gửi cho AI trong phiên nghiên cứu đã tạo ra báo cáo.

---

## Request: Create handoff documents for a completely clean new research session

This research session is now concluded. I want to start an entirely new session to re-derive the system from scratch, on a different data split, in order to obtain truly clean OOS results.

Core principle: **Transfer only meta-knowledge (lessons about methodology and structure), DO NOT transfer data-derived specifics (specific features, specific lookbacks, specific thresholds, specific parameters).** The new session must rediscover everything from first principles.

### I need you to produce 3 deliverables:

---

### Deliverable 1: RESEARCH_PROMPT_V5.md

Rewrite RESEARCH_PROMPT_V4.md into version V5 with the following changes:

**A. Keep as-is (what was already correct in V4):**
- The overall protocol structure, if it worked well
- Data pipeline logic, if it was stable
- Any steps that you assess ran correctly and need no modification

**B. Fix/improve (based on methodological lessons learned):**
- Every part of V4 that you discovered during research to be missing, ambiguous, misleading, or leading to redundant/incorrect steps — fix it
- If the order of steps needs to change — change it
- If any screening criteria need to be added/removed/clarified — do so
- If the protocol needs additional checkpoints or decision gates — add them

**C. New section — "META-KNOWLEDGE FROM PRIOR RESEARCH":**

Write a dedicated section in the prompt containing ALL methodological lessons you have extracted. This is the most important part. Include:

1. **Lessons on feature architecture:** What roles different feature types play (regime gate vs state controller vs entry filter), why this layering matters — BUT DO NOT name specific features or specific lookback periods
2. **Lessons on timeframe:** How multi-timeframe design works, what role each timeframe should play — speak at the level of principles, do not name specific combinations
3. **Lessons on robustness:** What distinguishes a real edge from an artifact, what signs you observed
4. **Lessons on process:** Which steps wasted time, which should have been done earlier, which traps you fell into
5. **Lessons on evaluation:** Which metrics are trustworthy, which are misleading, which perspectives helped you distinguish good from bad results
6. **Lessons on data splits:** Which splitting approaches caused contamination, which worked better
7. **Any other insights** you consider valuable for someone starting over from scratch

**D. New section — "FRESH RE-DERIVATION RULES":**

Mandatory rules for the new session:
- MUST scan the entire search space from scratch, MUST NOT use prior results to narrow it
- MUST use a different data split than the prior session
- IF the new session converges on the same conclusion as the prior session → that is genuine confirmation → record it
- IF it diverges → DO NOT treat the prior session as more correct → follow the new data
- TRUE OOS must be a data range never used in any round of any session

**E. DO NOT include Contamination Disclosure in RESEARCH_PROMPT_V5.md.**

Contamination Disclosure must go in a separate file (Deliverable 2 below). Reason: the new AI must form its research framework in a clean state, uninfluenced by any specific results from the prior session. The contamination file should only be read for cross-checking after independent results have been obtained.

**F. Mandatory section ordering within RESEARCH_PROMPT_V5.md:**

Arrange in exactly this order — DO NOT reorder:

1. **Research protocol** (methodology, data pipeline, scan rules, evaluation criteria) — FIRST
2. **Fresh Re-derivation Rules** — IMMEDIATELY AFTER protocol, BEFORE any information from the prior session
3. **Meta-knowledge from Prior Research** — LAST in the file

Reason: LLMs are affected by primacy effect — information read first will anchor all subsequent reasoning. The protocol must be loaded first so the AI builds its mental model of "what I will do" in a clean state. Anti-leakage rules must be installed before the AI sees any priors. Meta-knowledge is placed last to minimize anchoring bias.

---

### Deliverable 2: CONTAMINATION_LOG.md

A separate file, NOT included in RESEARCH_PROMPT_V5.md. Contains:
- Exactly which data ranges the prior session iterated on (list precisely)
- Which features, lookbacks, thresholds were tried and selected (list exhaustively)
- Which data splits have been contaminated
- Suggested alternative data splits for the new session (e.g., use a different period for dev, reserve a different period as true OOS)

Purpose of this file: the new session should only open and read it AFTER obtaining independent results, to cross-check whether it converged or diverged with the prior session. DO NOT load this file into context at the start.

---

### Deliverable 3: CHANGELOG_V4_TO_V5.md

A separate file listing:
- Every change from V4 to V5
- The reason for each change
- Classification of each change: [FIX] (bug fix), [IMPROVE] (improvement), [NEW] (new addition), [REMOVE] (removal)

---

### Format constraints:
- All three files must be Markdown
- RESEARCH_PROMPT_V5.md must be self-contained: an engineer/AI receiving this file + data.zip should have everything needed to start, nothing else required
- CONTAMINATION_LOG.md must be self-contained and MUST NOT be referenced from within RESEARCH_PROMPT_V5.md
- Do not reference the chat history or artifacts of this session
- Write in English (or keep the same language as V4)

---

### Final checklist before delivery:

Re-read RESEARCH_PROMPT_V5.md and ask yourself:
1. If a completely new AI reads this file, would it be biased toward any specific feature/lookback/threshold? → If yes, revise
2. Does it have enough methodological information to avoid repeating past mistakes? → If not, add more
3. Does it know which data ranges to avoid using as OOS? → If unclear, add disclosure
4. If the new session independently arrives at the same result as the prior session, would that truly be independent confirmation? → If data splits still overlap, then no — fix the splits
5. Does RESEARCH_PROMPT_V5.md contain any reference to CONTAMINATION_LOG.md? → If yes, REMOVE it — the two files must be completely independent
